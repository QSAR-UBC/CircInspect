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
Tests for server/helpers/transform_helpers.py.
"""

import pennylane as qp
import pytest

from server.command import Command
from server.helpers import transform_helpers as th
from pennylane.measurements import MidMeasureMP


# ---------------------------------------------------------------------------
# Load circuit fixtures from test_cases/
# ---------------------------------------------------------------------------

with open("test_cases/transform_simple_circuit.txt", "r") as f:
    SIMPLE_CIRCUIT = f.read()

with open("test_cases/transform_no_transform_circuit.txt", "r") as f:
    CIRCUIT_NO_TRANSFORM = f.read()

with open("test_cases/transform_multiple_transforms_circuit.txt", "r") as f:
    CIRCUIT_MULTIPLE_TRANSFORMS = f.read()

with open("test_cases/transform_custom_transform_circuit.txt", "r") as f:
    CUSTOM_TRANSFORM_CIRCUIT = f.read()

with open("test_cases/transform_already_commented_circuit.txt", "r") as f:
    ALREADY_COMMENTED_TRANSFORM = f.read()


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


# ===========================================================================
# comment_out_transforms
# ===========================================================================


def test_comment_out_transforms_single_transform():
    """A single PennyLane transform decorator should be commented out."""
    result = th.comment_out_transforms(SIMPLE_CIRCUIT)
    lines = result.split("\n")
    commented = [
        l
        for l in lines
        if "#@qp.transforms.merge_rotations" in l or "# @qp.transforms.merge_rotations" in l
    ]
    assert len(commented) == 1, "Expected exactly one commented-out transform line"


def test_comment_out_transforms_qnode_decorator_preserved():
    """The @qp.qnode decorator must NOT be commented out."""
    result = th.comment_out_transforms(SIMPLE_CIRCUIT)
    lines = result.split("\n")
    qnode_lines = [l for l in lines if "@qp.qnode(" in l and not l.lstrip().startswith("#")]
    assert len(qnode_lines) == 1, "@qp.qnode decorator must remain uncommented"


def test_comment_out_transforms_no_transforms_unchanged():
    """Code with no transforms should be returned unchanged (line count stays same)."""
    result = th.comment_out_transforms(CIRCUIT_NO_TRANSFORM)
    assert result == CIRCUIT_NO_TRANSFORM


def test_comment_out_transforms_multiple_transforms_all_commented():
    """All PennyLane transform decorators should be commented out."""
    result = th.comment_out_transforms(CIRCUIT_MULTIPLE_TRANSFORMS)
    lines = result.split("\n")
    commented = [l for l in lines if ("@qp.transforms." in l) and l.lstrip().startswith("#")]
    assert len(commented) == 2, "Expected both transform decorators to be commented out"


def test_comment_out_transforms_already_commented_stays_commented():
    """A line that is already commented out should stay commented and not get a double '#'."""
    result = th.comment_out_transforms(ALREADY_COMMENTED_TRANSFORM)
    lines = result.split("\n")
    double_hashed = [l for l in lines if l.lstrip().startswith("##")]
    assert len(double_hashed) == 0, "No line should be double-commented"


def test_comment_out_transforms_returns_string():
    """Return type must always be a string."""
    result = th.comment_out_transforms(SIMPLE_CIRCUIT)
    assert isinstance(result, str)


def test_comment_out_transforms_preserves_line_count():
    """Commenting out transforms must not add or remove lines."""
    original_lines = SIMPLE_CIRCUIT.count("\n")
    result_lines = th.comment_out_transforms(SIMPLE_CIRCUIT).count("\n")
    assert original_lines == result_lines


# ===========================================================================
# get_transform_details
# ===========================================================================


def test_get_transform_details_returns_list_like():
    """Return value must be iterable (deque or list) with expected content."""
    result = th.get_transform_details(SIMPLE_CIRCUIT)
    assert hasattr(result, "__len__") or hasattr(result, "__iter__")


def test_get_transform_details_single_transform_count():
    """One transform in the code → one entry in the returned details."""
    result = list(th.get_transform_details(SIMPLE_CIRCUIT))
    assert len(result) == 1


def test_get_transform_details_single_transform_name():
    """The transform entry should contain the decorator string."""
    result = list(th.get_transform_details(SIMPLE_CIRCUIT))
    assert "@qp.transforms.merge_rotations" in result[0][0]


def test_get_transform_details_single_transform_line_number():
    """The line number stored is 1-based and must be positive."""
    result = list(th.get_transform_details(SIMPLE_CIRCUIT))
    line_num = result[0][1]
    assert isinstance(line_num, int) and line_num > 0


def test_get_transform_details_no_transforms_empty():
    """Code without transforms should return an empty result."""
    result = list(th.get_transform_details(CIRCUIT_NO_TRANSFORM))
    assert len(result) == 0


def test_get_transform_details_multiple_transforms_count():
    """Two transforms in the code → two entries."""
    result = list(th.get_transform_details(CIRCUIT_MULTIPLE_TRANSFORMS))
    assert len(result) == 2


def test_get_transform_details_multiple_transforms_order():
    """Transforms should be returned in order of application
    (outermost / first applied first)."""
    result = list(th.get_transform_details(CIRCUIT_MULTIPLE_TRANSFORMS))
    # cancel_inverses is closer to @qp.qnode, so it is applied first
    assert "cancel_inverses" in result[0][0]
    assert "merge_rotations" in result[1][0]


def test_get_transform_details_custom_transform_detected():
    """A user-defined @qp.transform should also be detected."""
    result = list(th.get_transform_details(CUSTOM_TRANSFORM_CIRCUIT))
    assert len(result) == 1
    assert "my_custom_transform" in result[0][0]


def test_get_transform_details_entry_structure():
    """Each entry must be a 2-element sequence [decorator_string, line_number]."""
    result = list(th.get_transform_details(SIMPLE_CIRCUIT))
    entry = result[0]
    assert len(entry) == 2
    assert isinstance(entry[0], str)
    assert isinstance(entry[1], int)


# ===========================================================================
# get_transform_func
# ===========================================================================


def test_get_transform_func_builtin_transform_returns_callable():
    """A known PennyLane transform should resolve to a callable."""
    transform_entry = ["@qp.transforms.merge_rotations", 4]
    env = {"qp": qp}
    func = th.get_transform_func(transform_entry, env=env)
    assert callable(func)


def test_get_transform_func_builtin_cancel_inverses_callable():
    """cancel_inverses transform should also resolve to a callable."""
    transform_entry = ["@qp.transforms.cancel_inverses", 4]
    env = {"qp": qp}
    func = th.get_transform_func(transform_entry, env=env)
    assert callable(func)


def test_get_transform_func_with_leading_whitespace():
    """Leading whitespace before the '@' should be stripped correctly."""
    transform_entry = ["    @qp.transforms.merge_rotations", 4]
    env = {"qp": qp}
    func = th.get_transform_func(transform_entry, env=env)
    assert callable(func)


def test_get_transform_func_invalid_transform_returns_none():
    """An unrecognised transform string should return None (not raise)."""
    transform_entry = ["@nonexistent_module.fake_transform", 4]
    env = {"qp": qp}
    result = th.get_transform_func(transform_entry, env=env)
    assert result is None


def test_get_transform_func_uses_global_env_when_none():
    """When env=None, the function should fall back to globals() without raising."""
    transform_entry = ["@qp.transforms.merge_rotations", 4]
    try:
        th.get_transform_func(transform_entry, env=None)
    except Exception as exc:
        pytest.fail(f"get_transform_func raised unexpectedly: {exc}")


# ===========================================================================
# get_transformed_queue_items
# ===========================================================================


def _build_simple_tape():
    """Helper: returns a simple QuantumScript with an H gate and expval measurement."""
    ops = [qp.Hadamard(wires=0)]
    measurements = [qp.expval(qp.PauliZ(0))]
    return qp.tape.QuantumScript(ops=ops, measurements=measurements)


def test_get_transformed_queue_items_returns_tape():
    """With no transforms, the function should return a QuantumScript."""
    result = th.get_transformed_queue_items([], [qp.Hadamard(wires=0), qp.expval(qp.PauliZ(0))])
    assert isinstance(result, qp.tape.QuantumScript)


def test_get_transformed_queue_items_no_transforms_preserves_ops():
    """With an empty transform list the operations should pass through unchanged."""
    ops = [qp.PauliX(wires=0)]
    measurements = [qp.expval(qp.PauliZ(0))]
    queue = ops + measurements
    tape = th.get_transformed_queue_items([], queue)
    assert len(tape.operations) == 1
    assert isinstance(tape.operations[0], qp.PauliX)


def test_get_transformed_queue_items_single_transform_applied():
    """cancel_inverses should eliminate S followed by S† from the operation list."""
    ops = [qp.S(wires=0), qp.adjoint(qp.S)(wires=0)]
    measurements = [qp.expval(qp.PauliZ(0))]
    queue = ops + measurements
    func = qp.transforms.cancel_inverses
    result = th.get_transformed_queue_items([func], queue)
    assert isinstance(result, qp.tape.QuantumScript)
    assert len(result.operations) == 0


def test_get_transformed_queue_items_measurements_preserved():
    """The terminal measurement must still exist on the resulting tape."""
    ops = [qp.Hadamard(wires=0)]
    measurements = [qp.expval(qp.PauliZ(0))]
    queue = ops + measurements
    result = th.get_transformed_queue_items([], queue)
    assert len(result.measurements) == 1


def test_get_transformed_queue_items_empty_queue():
    """An empty queue with no transforms should produce an empty tape without raising."""
    result = th.get_transformed_queue_items([], [])
    assert isinstance(result, qp.tape.QuantumScript)
    assert len(result.operations) == 0


def test_get_transformed_queue_items_multiple_transforms():
    """Applying merge_rotations after cancel_inverses should both be applied in sequence."""
    ops = [
        qp.S(wires=0),
        qp.adjoint(qp.S)(wires=0),
        qp.RZ(0.5, wires=0),
        qp.RZ(0.3, wires=0),
    ]
    measurements = [qp.expval(qp.PauliZ(0))]
    queue = ops + measurements
    transforms = [qp.transforms.cancel_inverses, qp.transforms.merge_rotations]
    result = th.get_transformed_queue_items(transforms, queue)
    assert isinstance(result, qp.tape.QuantumScript)
    assert len(result.operations) == 1
    assert isinstance(result.operations[0], qp.RZ)


# ===========================================================================
# generate_transformed_command_tree
# ===========================================================================


def _make_root_cmd(name="circuit"):
    """Helper: build a root Command suitable for generate_transformed_command_tree."""
    root = make_cmd(
        parent_function=name,
        line_number=1,
        code_line=f"def {name}():",
        line_type="call",
        quantum_or_classical="quantum",
        indent=0,
    )
    root.identifier = 0
    root.tree_node_name = name
    return root


def _build_tape_with_ops():
    """Helper: tape with PauliX and expval measurement."""
    ops = [qp.PauliX(wires=0)]
    measurements = [qp.expval(qp.PauliZ(0))]
    return qp.tape.QuantumScript(ops=ops, measurements=measurements)


def test_generate_transformed_command_tree_returns_root():
    """The function must return the same root Command object that was passed in."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    result = th.generate_transformed_command_tree(root, tape, ["circuit"])
    assert result is root


def test_generate_transformed_command_tree_children_populated():
    """After the call, root.children must be non-empty (one entry per circuit element)."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    assert len(root.children) > 0


def test_generate_transformed_command_tree_child_count_matches_tape():
    """Number of children should equal the number of elements in tape.circuit."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    assert len(root.children) == len(tape.circuit)


def test_generate_transformed_command_tree_children_are_commands():
    """Each child must be a Command instance."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    for child in root.children:
        assert isinstance(child, Command)


def test_generate_transformed_command_tree_op_child_line_type():
    """A plain operation (PauliX) child must have line_type='line'."""
    root = _make_root_cmd()
    tape = qp.tape.QuantumScript(ops=[qp.PauliX(wires=0)], measurements=[qp.expval(qp.PauliZ(0))])
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    op_child = root.children[0]
    assert op_child.line_type == "line"


def test_generate_transformed_command_tree_measurement_child_line_type():
    """A terminal measurement child must have line_type='measurement'."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    meas_child = root.children[-1]
    assert meas_child.line_type == "measurement"


def test_generate_transformed_command_tree_children_quantum():
    """All generated children must be quantum commands."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    for child in root.children:
        assert child.quantum_or_classical == "quantum"


def test_generate_transformed_command_tree_children_linked_to_root():
    """Each child's parent_id must equal the root's identifier."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    for child in root.children:
        assert child.parent_id == root.identifier


def test_generate_transformed_command_tree_identifiers_assigned():
    """After the call, all children (and root) must have numeric identifiers."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    for child in root.children:
        assert child.identifier is not None
        assert isinstance(child.identifier, int)


def test_generate_transformed_command_tree_tree_node_names_set():
    """After the call, children must have non-None tree_node_name values."""
    root = _make_root_cmd()
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    for child in root.children:
        assert child.tree_node_name is not None


def test_generate_transformed_command_tree_empty_tape():
    """An empty tape (no ops, no measurements) should produce no children."""
    root = _make_root_cmd()
    tape = qp.tape.QuantumScript(ops=[], measurements=[])
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    assert root.children == []


def test_generate_transformed_command_tree_replaces_existing_children():
    """Pre-existing children on root must be replaced, not appended to."""
    root = _make_root_cmd()
    stale_child = make_cmd()
    root.children = [stale_child]
    tape = _build_tape_with_ops()
    th.generate_transformed_command_tree(root, tape, ["circuit"])
    assert stale_child not in root.children


# ===========================================================================
# Combined: mid-circuit measurements + qp.cond + transforms
# ===========================================================================


def _build_mid_measure_tape():
    """Returns a QuantumScript with one MidMeasureMP, one Conditional(PauliX),
    and one terminal expval measurement — built without executing a QNode."""

    mid_op = MidMeasureMP(wires=qp.wires.Wires([0]))
    meas_val = qp.measurements.MeasurementValue([mid_op], processing_fn=lambda v: v)
    cond_op = qp.ops.Conditional(meas_val, qp.PauliX(wires=1))
    terminal = qp.expval(qp.PauliZ(1))
    return qp.tape.QuantumScript(ops=[mid_op, cond_op], measurements=[terminal])


def test_get_transformed_queue_items_defer_removes_mid_measure():
    """Applying defer_measurements to a queue with a MidMeasureMP + Conditional
    should eliminate the mid-circuit measurement and leave at least one controlled op."""

    tape = _build_mid_measure_tape()
    result = th.get_transformed_queue_items([qp.transforms.defer_measurements], list(tape.circuit))
    assert isinstance(result, qp.tape.QuantumScript)
    mid_ops = [op for op in result.operations if isinstance(op, MidMeasureMP)]
    assert len(mid_ops) == 0, "defer_measurements must remove all MidMeasureMP ops"
    assert len(result.operations) >= 1, "At least one controlled op must remain"


def test_generate_transformed_command_tree_mid_measure_cond_line_types():
    """A tape with MidMeasureMP + Conditional + expval must produce children with
    line_types ['mid_measurement', 'cond', 'measurement'] in that order."""
    root = _make_root_cmd()
    tape = _build_mid_measure_tape()
    th.generate_transformed_command_tree(root, tape, [])
    types = [c.line_type for c in root.children]
    assert types == ["mid_measurement", "cond", "measurement"]


def test_generate_transformed_command_tree_after_defer_no_mid_measure_or_cond():
    """After applying defer_measurements the resulting tree must contain no
    'mid_measurement' or 'cond' children — both are replaced by standard gates."""
    root = _make_root_cmd()
    tape = _build_mid_measure_tape()
    deferred_tape = th.get_transformed_queue_items(
        [qp.transforms.defer_measurements], list(tape.circuit)
    )
    th.generate_transformed_command_tree(root, deferred_tape, [])
    types = [c.line_type for c in root.children]
    assert "mid_measurement" not in types
    assert "cond" not in types


# ===========================================================================
# get_user_transforms
# ===========================================================================


def test_get_user_transforms_basic():
    """Should return the compile pipeline when the QNode exists in the environment."""
    dev = qp.device("default.qubit", wires=1)

    @qp.qnode(dev)
    def my_circuit():
        return qp.expval(qp.PauliZ(0))

    code = "@qp.qnode(dev)\ndef my_circuit():\n    pass"
    method_names = {"my_circuit"}

    result = th.get_user_transforms(code, method_names, my_circuit)
    assert result is my_circuit.compile_pipeline


def test_get_user_transforms_missing_qnode():
    """Should return None if the identified QNode is not in the environment."""
    code = "@qp.qnode(dev)\ndef my_circuit():\n    pass"
    method_names = {"my_circuit"}

    result = th.get_user_transforms(code, method_names, None)
    assert result is None


def test_get_user_transforms_no_qnode_in_code():
    """Should return None if no QNode decorator is found in the code."""
    code = "def plain_func():\n    pass"
    method_names = {"plain_func"}

    result = th.get_user_transforms(code, method_names, lambda: None)
    assert result is None


def test_get_user_transforms_custom_transform():
    """Should return the compile pipeline when a custom transform is applied."""
    dev = qp.device("default.qubit", wires=1)

    @qp.transform
    def my_custom_transform(tape):
        return [tape], lambda results: results[0]

    @my_custom_transform
    @qp.qnode(dev)
    def circuit():
        return qp.expval(qp.PauliZ(0))

    code = CUSTOM_TRANSFORM_CIRCUIT
    method_names = {"circuit", "my_custom_transform"}

    result = th.get_user_transforms(code, method_names, circuit)
    assert result is circuit.compile_pipeline
    assert len(result) == 1
    assert result[0].transform.__name__ == "my_custom_transform"
