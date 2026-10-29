# Copyright 2026 UBC Quantum Software and Algorithms Research Lab

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tests for server/helpers/midcircuit_measurement_helpers.py.
"""

import pennylane as qp
import pytest
from pennylane.measurements import MidMeasureMP

from server.command import Command
from server.helpers import midcircuit_measurement_helpers as mcm


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def make_cmd(
    parent_function="root",
    line_number=1,
    code_line="print(1)",
    line_type="line",
    quantum_or_classical="classical",
    indent=0,
):
    """Factory that returns a Command with all required fields pre-populated."""
    return Command(parent_function, line_number, code_line, line_type, quantum_or_classical, indent)


def make_mid_measure_cmd(wire=0, postselect=None, identifier=1):
    """Factory: a mid_measurement Command wrapping a real MidMeasureMP."""
    mid_op = MidMeasureMP(wires=qp.wires.Wires([wire]), postselect=postselect, meas_uid=str(identifier))
    cmd = make_cmd(line_type="mid_measurement", quantum_or_classical="quantum")
    cmd.code_line = mid_op
    cmd.identifier = identifier
    return cmd


def make_cond_cmd(meas_val, identifier=2):
    """Factory: a cond Command wrapping a qp.ops.Conditional on the given MeasurementValue."""
    cond_op = qp.ops.Conditional(meas_val, qp.PauliX(0))
    cmd = make_cmd(line_type="cond", quantum_or_classical="quantum")
    cmd.code_line = cond_op
    cmd.identifier = identifier
    return cmd


def make_root_with_children(*children):
    """Factory: a root Command whose tree children are the supplied commands."""
    root = make_cmd(line_type="root", line_number=0, code_line="root")
    root.identifier = 0
    root.parent_id = None
    root.children = list(children)
    for child in children:
        child.parent_id = 0
    return root


# ===========================================================================
# cond_references_measurement
# ===========================================================================


def test_cond_references_measurement_returns_true_when_referenced():
    """A Conditional wrapping a MeasurementValue from mid_op should return True."""
    with qp.queuing.AnnotatedQueue() as q:
        mid_op = qp.measure(0)

    cond_op = qp.ops.Conditional(mid_op, qp.PauliX(0))
    assert mcm.cond_references_measurement(cond_op, mid_op.measurements[0]) is True


def test_cond_references_measurement_returns_false_for_different_measurement():
    """A Conditional for a different mid-circuit measurement should return False."""
    with qp.queuing.AnnotatedQueue():
        mid_op1 = qp.measure(0)
        mid_op2 = qp.measure(1)

    cond_op = qp.ops.Conditional(mid_op1, qp.PauliX(0))
    assert mcm.cond_references_measurement(cond_op, mid_op2.measurements[0]) is False


def test_cond_references_measurement_meas_val_without_measurements_attr():
    """If meas_val has no 'measurements' attribute the function should return False."""
    cond_op = qp.ops.Conditional(qp.measure(0), qp.PauliX(0))
    # Override meas_val with an object that has no .measurements
    cond_op.__dict__["meas_val"] = object()
    # Should not raise; should return False
    mid_op = MidMeasureMP(wires=qp.wires.Wires([0]))
    assert mcm.cond_references_measurement(cond_op, mid_op) is False


# ===========================================================================
# link_mid_circuit_measurements
# ===========================================================================


def _build_mid_cond_tree():
    """Helper: tree with one mid_measurement and one dependent cond child."""
    with qp.queuing.AnnotatedQueue():
        meas_val = qp.measure(0)

    mid_cmd = make_cmd(line_type="mid_measurement", quantum_or_classical="quantum")
    mid_cmd.code_line = meas_val.measurements[0]
    mid_cmd.identifier = 1

    cond_cmd = make_cond_cmd(meas_val, identifier=2)

    root = make_root_with_children(mid_cmd, cond_cmd)
    return root, mid_cmd, cond_cmd


def test_link_mid_circuit_measurements_assigns_matching_index():
    """The mid_measurement and its dependent cond should share the same mid_measurement_index."""
    root, mid_cmd, cond_cmd = _build_mid_cond_tree()
    mcm.link_mid_circuit_measurements([root])
    assert hasattr(mid_cmd, "mid_measurement_index")
    assert hasattr(cond_cmd, "mid_measurement_index")
    assert mid_cmd.mid_measurement_index == cond_cmd.mid_measurement_index


def test_link_mid_circuit_measurements_index_starts_at_one():
    """The first linked mid-circuit measurement should receive index 1."""
    root, mid_cmd, _ = _build_mid_cond_tree()
    mcm.link_mid_circuit_measurements([root])
    assert mid_cmd.mid_measurement_index == 1


def test_link_mid_circuit_measurements_sets_is_mid_measure():
    """link_mid_circuit_measurements must set is_mid_measure=True on mid_measurement commands."""
    root, mid_cmd, _ = _build_mid_cond_tree()
    mcm.link_mid_circuit_measurements([root])
    assert mid_cmd.is_mid_measure is True


def test_link_mid_circuit_measurements_no_cond_no_index():
    """A mid_measurement with no dependent cond should NOT receive a mid_measurement_index."""
    mid_cmd = make_cmd(line_type="mid_measurement", quantum_or_classical="quantum")
    mid_cmd.code_line = MidMeasureMP(wires=qp.wires.Wires([0]))
    mid_cmd.identifier = 1

    root = make_root_with_children(mid_cmd)
    mcm.link_mid_circuit_measurements([root])
    assert not hasattr(mid_cmd, "mid_measurement_index")


def test_link_mid_circuit_measurements_increments_index_per_measurement():
    """Each independent mid-circuit measurement that has dependents gets a unique index."""
    with qp.queuing.AnnotatedQueue():
        meas_val1 = qp.measure(0)
        meas_val2 = qp.measure(1)

    mid_cmd1 = make_cmd(line_type="mid_measurement", quantum_or_classical="quantum")
    mid_cmd1.code_line = meas_val1.measurements[0]
    mid_cmd1.identifier = 1

    mid_cmd2 = make_cmd(line_type="mid_measurement", quantum_or_classical="quantum")
    mid_cmd2.code_line = meas_val2.measurements[0]
    mid_cmd2.identifier = 2

    cond_cmd1 = make_cond_cmd(meas_val1, identifier=3)
    cond_cmd2 = make_cond_cmd(meas_val2, identifier=4)

    root = make_root_with_children(mid_cmd1, mid_cmd2, cond_cmd1, cond_cmd2)
    mcm.link_mid_circuit_measurements([root])

    assert mid_cmd1.mid_measurement_index != mid_cmd2.mid_measurement_index


# ===========================================================================
# apply_postselect_to_commands
# ===========================================================================


def test_apply_postselect_to_commands_sets_hyperparameter():
    """apply_postselect_to_commands must update _hyperparameters['postselect'] on the MidMeasureMP."""
    cmd = make_mid_measure_cmd(wire=0, postselect=None)
    cmd.mid_measurement_index = 1

    mcm.apply_postselect_to_commands([cmd], {"1": 0})
    assert cmd.code_line._hyperparameters["postselect"] == 0


def test_apply_postselect_to_commands_sets_postselect_value_on_command():
    """The command's postselect_value attribute should be updated to the override value."""
    cmd = make_mid_measure_cmd(wire=0, postselect=None)
    cmd.mid_measurement_index = 1

    mcm.apply_postselect_to_commands([cmd], {"1": 1})
    assert cmd.postselect_value == 1


def test_apply_postselect_to_commands_none_value_sets_none():
    """A None override value should set postselect to None (clearing any prior postselection)."""
    cmd = make_mid_measure_cmd(wire=0, postselect=1)
    cmd.mid_measurement_index = 1

    mcm.apply_postselect_to_commands([cmd], {"1": None})
    assert cmd.postselect_value is None
    assert cmd.code_line._hyperparameters["postselect"] is None


def test_apply_postselect_to_commands_skips_non_mid_measurement():
    """A command that is not mid_measurement type should not be touched."""
    cmd = make_cmd(line_type="line")
    cmd.mid_measurement_index = 1
    # postselect_value should be left as None
    mcm.apply_postselect_to_commands([cmd], {"1": 0})
    assert cmd.postselect_value is None


def test_apply_postselect_to_commands_skips_unmatched_index():
    """A mid_measurement whose index is not in postselect_overrides should be unchanged."""
    cmd = make_mid_measure_cmd(wire=0, postselect=None)
    cmd.mid_measurement_index = 99  # not in overrides

    mcm.apply_postselect_to_commands([cmd], {"1": 0})
    assert cmd.postselect_value is None


def test_apply_postselect_to_commands_skips_cmd_without_index():
    """A mid_measurement command with no mid_measurement_index attribute should be skipped."""
    cmd = make_mid_measure_cmd(wire=0, postselect=None)
    # no mid_measurement_index set

    mcm.apply_postselect_to_commands([cmd], {"1": 0})
    assert cmd.postselect_value is None


def test_apply_postselect_to_commands_multiple_commands():
    """Only the command whose index matches the override dict key should be updated."""
    cmd1 = make_mid_measure_cmd(wire=0, postselect=None, identifier=1)
    cmd1.mid_measurement_index = 1

    cmd2 = make_mid_measure_cmd(wire=1, postselect=None, identifier=2)
    cmd2.mid_measurement_index = 2

    mcm.apply_postselect_to_commands([cmd1, cmd2], {"2": 1})

    assert cmd1.postselect_value is None
    assert cmd2.postselect_value == 1


# ===========================================================================
# get_postselect_id_map
# ===========================================================================


def test_get_postselect_id_map_returns_dict_for_postselected_measurement():
    """A mid_measurement with a non-None postselect should appear in the returned map."""
    cmd = make_mid_measure_cmd(wire=0, postselect=1)
    root = make_root_with_children(cmd)

    id_map = mcm.get_postselect_id_map(root)
    assert cmd.code_line.meas_uid in id_map
    assert id_map[cmd.code_line.meas_uid] == 1


def test_get_postselect_id_map_excludes_unpostselected_measurement():
    """A mid_measurement without postselect (None) should NOT appear in the map."""
    cmd = make_mid_measure_cmd(wire=0, postselect=None)
    root = make_root_with_children(cmd)

    id_map = mcm.get_postselect_id_map(root)
    assert cmd.code_line.meas_uid not in id_map


def test_get_postselect_id_map_empty_for_no_mid_measurements():
    """A tree with no mid_measurement commands should return an empty dict."""
    classical_cmd = make_cmd(line_type="line")
    root = make_root_with_children(classical_cmd)

    id_map = mcm.get_postselect_id_map(root)
    assert id_map == {}


def test_get_postselect_id_map_multiple_measurements():
    """Each postselected mid_measurement should have its own entry in the map."""
    cmd1 = make_mid_measure_cmd(wire=0, postselect=0, identifier=1)
    cmd2 = make_mid_measure_cmd(wire=1, postselect=1, identifier=2)
    root = make_root_with_children(cmd1, cmd2)
    id_map = mcm.get_postselect_id_map(root)
    assert len(id_map) == 2
    assert id_map[cmd1.code_line.meas_uid] == 0
    assert id_map[cmd2.code_line.meas_uid] == 1


def test_get_postselect_id_map_with_precomputed_flat_commands_matches_default():
    """Passing an already-flattened list via flat_commands must produce the same
    result as letting get_postselect_id_map flatten the tree itself, which proves the
    optional param is a pure perf shortcut, not a behavior change."""
    cmd1 = make_mid_measure_cmd(wire=0, postselect=0, identifier=1)
    cmd2 = make_mid_measure_cmd(wire=1, postselect=1, identifier=2)
    root = make_root_with_children(cmd1, cmd2)

    flat_commands = [root, cmd1, cmd2]
    id_map_from_param = mcm.get_postselect_id_map(root, flat_commands)
    id_map_default = mcm.get_postselect_id_map(root)

    assert id_map_from_param == id_map_default
    assert id_map_from_param == {cmd1.code_line.meas_uid: 0, cmd2.code_line.meas_uid: 1}


# ===========================================================================
# is_conditional_node
# ===========================================================================


def test_is_conditional_node_true_for_cond_line_type():
    """A command whose line_type is 'cond' is always a conditional node."""
    cmd = make_cmd(line_type="cond")
    assert mcm.is_conditional_node(cmd) is True


def test_is_conditional_node_true_for_wrapped_conditional():
    """A quantum command whose code_line unwraps to a Conditional (e.g. under an
    Adjoint/Controlled wrapper) is a conditional node, even if its own line_type
    is not 'cond'."""
    with qp.queuing.AnnotatedQueue():
        meas_val = qp.measure(0)
    cond_op = qp.ops.Conditional(meas_val, qp.PauliX(0))
    wrapped = qp.ops.Adjoint(cond_op)

    cmd = make_cmd(line_type="line", quantum_or_classical="quantum")
    cmd.code_line = wrapped
    assert mcm.is_conditional_node(cmd) is True


def test_is_conditional_node_true_for_call_site_string():
    """A 'call' command whose source line contains 'qp.cond' is a conditional node."""
    cmd = make_cmd(line_type="call", code_line="qp.cond(m, qp.PauliX)(wires=0)")
    assert mcm.is_conditional_node(cmd) is True


def test_is_conditional_node_false_for_plain_quantum_gate():
    """A regular quantum gate command is not a conditional node."""
    cmd = make_cmd(line_type="line", quantum_or_classical="quantum")
    cmd.code_line = qp.PauliX(0)
    assert mcm.is_conditional_node(cmd) is False


def test_is_conditional_node_false_for_plain_classical_line():
    """A plain classical line is not a conditional node."""
    cmd = make_cmd(line_type="line", quantum_or_classical="classical")
    assert mcm.is_conditional_node(cmd) is False


def test_is_conditional_node_false_for_call_site_without_qp_cond():
    """A 'call' command whose source line does not mention qp.cond is not a
    conditional node."""
    cmd = make_cmd(line_type="call", code_line="some_func()")
    assert mcm.is_conditional_node(cmd) is False


# ===========================================================================
# resolve_conditional_outcome
# ===========================================================================


def test_resolve_conditional_outcome_returns_none_when_map_incomplete():
    """If not every measurement the conditional depends on has a postselect
    override yet, the outcome cannot be resolved and must be None."""
    with qp.queuing.AnnotatedQueue():
        meas_val1 = qp.measure(0)
        meas_val2 = qp.measure(1)
    combined = meas_val1 & meas_val2

    ps_id_map = {meas_val1.measurements[0].meas_uid: 1}  # meas_val2 missing
    assert mcm.resolve_conditional_outcome(combined, ps_id_map) is None


def test_resolve_conditional_outcome_returns_true():
    """A fully-mapped condition that concretizes to True should return True."""
    with qp.queuing.AnnotatedQueue():
        meas_val = qp.measure(0)
    condition = meas_val == 1

    ps_id_map = {meas_val.measurements[0].meas_uid: 1}
    assert mcm.resolve_conditional_outcome(condition, ps_id_map) is True


def test_resolve_conditional_outcome_returns_false():
    """A fully-mapped condition that concretizes to False should return False."""
    with qp.queuing.AnnotatedQueue():
        meas_val = qp.measure(0)
    condition = meas_val == 1

    ps_id_map = {meas_val.measurements[0].meas_uid: 0}
    assert mcm.resolve_conditional_outcome(condition, ps_id_map) is False


def test_resolve_conditional_outcome_raises_value_error_on_concretize_failure():
    """If MeasurementValue.concretize() raises, resolve_conditional_outcome must
    wrap it in a ValueError rather than letting the original exception escape."""

    class _FakeMeasurement:
        def __init__(self, meas_uid):
            self.meas_uid = meas_uid

    class _FailingMeasVal:
        def __init__(self, meas_uid):
            self.measurements = [_FakeMeasurement(meas_uid)]

        def concretize(self, ps_vals):
            raise RuntimeError("boom")

    fake_meas_val = _FailingMeasVal("fake-uid")
    with pytest.raises(ValueError, match="Could not concretize measurement value"):
        mcm.resolve_conditional_outcome(fake_meas_val, {"fake-uid": 1})


# ===========================================================================
# prune_unexecuted_commands
# ===========================================================================


def _make_cond_child_with_postselect(meas_val, postselect_val, identifier=10):
    """Helper: a cond child Command with a Conditional that evaluates to postselect_val."""
    cond_op = qp.ops.Conditional(meas_val, qp.PauliX(0))
    child = make_cmd(line_type="cond", quantum_or_classical="quantum")
    child.code_line = cond_op
    child.identifier = identifier
    child.parent_id = 0
    return child


def test_prune_unexecuted_commands_removes_false_branch():
    """A cond child whose condition evaluates to False (postselect=0 for '== 1' check)
    should be removed from the parent's children."""
    with qp.queuing.AnnotatedQueue():
        meas_val = qp.measure(0)

    mid_op = meas_val.measurements[0]
    mid_op._hyperparameters["postselect"] = 0

    ps_id_map = {mid_op.meas_uid: 0}

    parent = make_cmd(line_type="root")
    parent.identifier = 0

    # meas_val == 1? postselect=0, so this is False → should be pruned
    false_branch = _make_cond_child_with_postselect(meas_val == 1, postselect_val=False)
    parent.children = [false_branch]

    mcm.prune_unexecuted_commands(parent, ps_id_map)
    assert false_branch not in parent.children


def test_prune_unexecuted_commands_removes_bare_meas_val_false_branch():
    """qp.cond(m, ...) with a bare MeasurementValue (no `== 1` comparison) must
    also be pruned when postselect is 0."""
    with qp.queuing.AnnotatedQueue():
        meas_val = qp.measure(0)

    mid_op = meas_val.measurements[0]
    mid_op._hyperparameters["postselect"] = 0

    ps_id_map = {mid_op.meas_uid: 0}

    parent = make_cmd(line_type="root")
    parent.identifier = 0

    # bare meas_val, postselect=0 -> concretizes to int 0, falsy -> pruned
    false_branch = _make_cond_child_with_postselect(meas_val, postselect_val=False)
    parent.children = [false_branch]

    mcm.prune_unexecuted_commands(parent, ps_id_map)
    assert false_branch not in parent.children


def test_prune_unexecuted_commands_keeps_true_branch():
    """A cond child whose condition evaluates to True should be kept."""
    with qp.queuing.AnnotatedQueue():
        meas_val = qp.measure(0)

    mid_op = meas_val.measurements[0]
    mid_op._hyperparameters["postselect"] = 1

    ps_id_map = {mid_op.meas_uid: 1}

    parent = make_cmd(line_type="root")
    parent.identifier = 0

    # meas_val == 1? postselect=1, so this is True → should be kept
    true_branch = _make_cond_child_with_postselect(meas_val == 1, postselect_val=True)
    parent.children = [true_branch]

    mcm.prune_unexecuted_commands(parent, ps_id_map)
    assert true_branch in parent.children


def test_prune_unexecuted_commands_keeps_non_cond_children():
    """Non-cond children (regular quantum gates) should never be pruned."""
    parent = make_cmd(line_type="root")
    parent.identifier = 0

    gate_cmd = make_cmd(line_type="line", quantum_or_classical="quantum")
    gate_cmd.code_line = qp.PauliX(0)
    gate_cmd.identifier = 5
    gate_cmd.parent_id = 0
    parent.children = [gate_cmd]

    mcm.prune_unexecuted_commands(parent, {})
    assert gate_cmd in parent.children


def test_prune_unexecuted_commands_no_children_no_error():
    """Calling prune on a leaf command (no children) should not raise."""
    leaf = make_cmd(line_type="line")
    leaf.identifier = 0
    mcm.prune_unexecuted_commands(leaf, {})  # must not raise


def test_prune_unexecuted_commands_partial_map_keeps_cond():
    """If not all measurements in the condition are in ps_id_map, the cond must be kept
    (it cannot be safely resolved, so we err on the side of keeping it)."""
    with qp.queuing.AnnotatedQueue():
        meas_val1 = qp.measure(0)
        meas_val2 = qp.measure(1)

    combined = meas_val1 & meas_val2

    parent = make_cmd(line_type="root")
    parent.identifier = 0

    cond_child = _make_cond_child_with_postselect(combined, postselect_val=True)
    parent.children = [cond_child]

    # Only provide the map for meas_val1, not meas_val2
    ps_id_map = {meas_val1.measurements[0].meas_uid: 1}
    mcm.prune_unexecuted_commands(parent, ps_id_map)
    assert cond_child in parent.children
