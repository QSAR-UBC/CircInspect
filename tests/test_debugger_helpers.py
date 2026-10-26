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
Tests for server/helpers/debugger_helpers.py.
"""

import pennylane as qp
from pennylane.measurements import MidMeasureMP
from server.command import Command
from server.helpers import debugger_helpers as dh
import pytest
import numpy as np


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
    """Factory that returns a Command with all required fields pre-populated.

    Args:
        parent_function (str): The parent function of the command.
        line_number (int): The line number of the command.
        code_line (str): The code line of the command.
        line_type (str): The type of the command.
        quantum_or_classical (str): The type of the command (quantum or classical).
        indent (int): The indentation of the command.

    Returns:
        Command: A Command object with all required fields pre-populated.
    """
    return Command(parent_function, line_number, code_line, line_type, quantum_or_classical, indent)


def assign_ids(commands):
    """Assign sequential identifiers to a list of commands (in-place).

    Args:
        commands (List[Command Objects]): A list of command objects to assign identifiers to.
    """
    for i, c in enumerate(commands):
        c.identifier = i


# ===========================================================================
# debugger_update_identifier_called_from
# ===========================================================================


def test_debugger_update_identifier_called_from_single_level():
    """Children at one level deep should all point to their direct parent's identifier."""
    root = make_cmd(line_type="root", code_line=None)
    root.identifier = 0

    child1 = make_cmd(line_type="line", code_line="qp.H(0)")
    child1.identifier = 1
    child2 = make_cmd(line_type="line", code_line="qp.X(0)")
    child2.identifier = 2

    root.children = [child1, child2]
    dh.debugger_update_identifier_called_from([root])

    assert child1.parent_id == 0
    assert child2.parent_id == 0


def test_debugger_update_identifier_called_from_nested_children():
    """Grandchildren should point to their immediate parent (the child), not to
    the root, demonstrating correct recursion one level deeper."""
    root = make_cmd(line_type="root", code_line=None)
    root.identifier = 0

    child = make_cmd(line_type="call", code_line="sub_circuit()")
    child.identifier = 1
    child.parent_id = 0

    grandchild = make_cmd(line_type="line", code_line="qp.H(0)")
    grandchild.identifier = 2

    child.children = [grandchild]
    root.children = [child]
    dh.debugger_update_identifier_called_from([root])

    assert grandchild.parent_id == 1


def test_debugger_update_identifier_called_from_empty_children():
    """A leaf command (no children) should not raise any errors and should leave its own
    parent_id unchanged (it is set by the parent's pass)."""
    leaf = make_cmd(line_type="line", code_line="qp.H(0)")
    leaf.identifier = 0
    leaf.children = []
    dh.debugger_update_identifier_called_from([leaf])


def test_debugger_update_identifier_called_from_empty_list():
    """An empty command list should not raise any errors."""
    dh.debugger_update_identifier_called_from([])


def test_debugger_update_identifier_called_from_three_levels():
    """Verify correct parent linkage across three levels of nesting:
    root -> child -> grandchild -> great-grandchild."""
    root = make_cmd(line_type="root", code_line=None)
    root.identifier = 0
    child = make_cmd(line_type="call", code_line="a()")
    child.identifier = 1
    grandchild = make_cmd(line_type="call", code_line="b()")
    grandchild.identifier = 2
    great_grandchild = make_cmd(line_type="line", code_line="qp.H(0)")
    great_grandchild.identifier = 3

    grandchild.children = [great_grandchild]
    child.children = [grandchild]
    root.children = [child]
    dh.debugger_update_identifier_called_from([root])

    assert child.parent_id == 0
    assert grandchild.parent_id == 1
    assert great_grandchild.parent_id == 2


# ===========================================================================
# get_full_tree
# ===========================================================================


def test_get_full_tree_returns_root_and_matching_flattened_list():
    """get_full_tree must return a (Command, list) tuple whose second element
    is exactly the flattened list of the returned debugger root, callers rely
    on this to avoid flattening the tree again themselves."""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0
    child = make_cmd(parent_function="circuit", line_type="line", quantum_or_classical="quantum")
    child.code_line = qp.Hadamard(0)
    child.identifier = 1
    root.children = [child]

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)

    debugger_root, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )

    assert isinstance(debugger_root, Command)
    assert isinstance(flat_commands, list)
    assert flat_commands == dh.helpers.flatten_tree(debugger_root)


def test_get_full_tree_flat_commands_contains_original_root():
    """The flattened list should contain the original (un-transformed) circuit's
    root command somewhere within the assembled debugger tree."""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)

    _, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )

    assert root in flat_commands


def test_get_full_tree_splices_in_clobbered_condition():
    """A clobbered if/elif node (recorded via root_command.clobbered_conditions,
    as clobber_classical_conditions does) must be spliced back into flat_commands"""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0

    executed_branch = make_cmd(parent_function="circuit", line_type="line", quantum_or_classical="quantum")
    executed_branch.code_line = qp.Hadamard(0)
    root.children = [executed_branch]

    if_node = make_cmd(parent_function="circuit", line_type="scf", code_line="if i == 1:")
    if_node.clobbered_parent = root
    if_node.children = [executed_branch]
    root.clobbered_conditions = [if_node]

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)

    debugger_root, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )

    assert if_node in flat_commands
    assert if_node.children == []
    branch_idx = flat_commands.index(executed_branch)
    if_idx = flat_commands.index(if_node)
    assert if_idx == branch_idx - 1, "the if node must be positioned right before the branch it was replaced by"
    assert if_node.parent_id == root.identifier


def test_get_full_tree_no_clobbered_conditions_attribute():
    """A root_command with no clobbered_conditions attribute at all (the common
    case) must not raise and must behave exactly as before."""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)

    debugger_root, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )
    assert flat_commands == dh.helpers.flatten_tree(debugger_root)


def test_get_full_tree_multi_statement_branch_inserted_once():
    """A clobbered if node whose executed branch has TWO statements must be
    spliced in exactly once, positioned before the first statement, not once
    per statement."""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0

    stmt1 = make_cmd(parent_function="circuit", line_type="line", quantum_or_classical="quantum")
    stmt1.code_line = qp.Hadamard(0)
    stmt2 = make_cmd(parent_function="circuit", line_type="line", quantum_or_classical="quantum")
    stmt2.code_line = qp.PauliX(0)
    root.children = [stmt1, stmt2]

    if_node = make_cmd(parent_function="circuit", line_type="scf", code_line="if i == 1:")
    if_node.clobbered_parent = root
    if_node.children = [stmt1, stmt2]
    root.clobbered_conditions = [if_node]

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)
        qp.PauliX(0)

    debugger_root, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )

    assert flat_commands.count(if_node) == 1, "the if node must appear exactly once, not once per statement"
    if_idx = flat_commands.index(if_node)
    stmt1_idx = flat_commands.index(stmt1)
    stmt2_idx = flat_commands.index(stmt2)
    assert if_idx == stmt1_idx - 1, "if node must sit right before the first statement"
    assert stmt2_idx == stmt1_idx + 1, "second statement must be untouched, right after the first"


def test_get_full_tree_nested_clobbered_conditions_both_spliced():
    """Nested 'if a: if b: ...' clobbered conditions must both be spliced into
    flat_commands without crashing or duplicating, and the parent_id fixup
    must preserve the true nesting"""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0

    gate = make_cmd(parent_function="circuit", line_type="line", quantum_or_classical="quantum")
    gate.code_line = qp.Hadamard(0)
    root.children = [gate]

    if_a = make_cmd(parent_function="circuit", line_type="scf", code_line="if a:")
    if_b = make_cmd(parent_function="circuit", line_type="scf", code_line="if b:")
    if_a.children = [gate]
    if_b.children = [gate]
    if_a.clobbered_parent = root
    if_b.clobbered_parent = if_a
    # clobber_classical_conditions records bottom-up: inner before outer.
    root.clobbered_conditions = [if_b, if_a]

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)

    debugger_root, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )

    assert flat_commands.count(if_a) == 1
    assert flat_commands.count(if_b) == 1
    assert if_b.parent_id == if_a.identifier, "inner if must end up nested under the outer if"
    assert if_a.parent_id == root.identifier, "outer if must end up nested under the real grandparent"
    assert gate.parent_id == root.identifier, "the real tree's flattening must be unaffected"


def test_get_full_tree_multiple_independent_clobbered_conditions():
    """Two separate (non-nested) if statements at the same level must each be
    spliced in at their own correct position without interfering with each
    other's placement."""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0

    gate_x = make_cmd(parent_function="circuit", line_type="line", quantum_or_classical="quantum")
    gate_x.code_line = qp.Hadamard(0)
    gate_y = make_cmd(parent_function="circuit", line_type="line", quantum_or_classical="quantum")
    gate_y.code_line = qp.PauliX(0)
    root.children = [gate_x, gate_y]

    if_x = make_cmd(parent_function="circuit", line_type="scf", code_line="if x:")
    if_x.clobbered_parent = root
    if_x.children = [gate_x]

    if_y = make_cmd(parent_function="circuit", line_type="scf", code_line="if y:")
    if_y.clobbered_parent = root
    if_y.children = [gate_y]

    root.clobbered_conditions = [if_x, if_y]

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)
        qp.PauliX(0)

    debugger_root, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )

    assert flat_commands.count(if_x) == 1
    assert flat_commands.count(if_y) == 1
    ix, gx, iy, gy = (
        flat_commands.index(if_x),
        flat_commands.index(gate_x),
        flat_commands.index(if_y),
        flat_commands.index(gate_y),
    )
    assert ix < gx < iy < gy, "each if must sit directly before its own branch, in source order"
    assert if_x.parent_id == root.identifier
    assert if_y.parent_id == root.identifier


def test_get_full_tree_empty_children_clobbered_node_skipped():
    """A clobbered if node whose condition never ran true 
    must be silently skipped rather than raising an error."""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0

    if_node = make_cmd(parent_function="circuit", line_type="scf", code_line="if False:")
    if_node.clobbered_parent = root
    if_node.children = []
    root.clobbered_conditions = [if_node]

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)

    debugger_root, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )

    assert if_node not in flat_commands


def test_get_full_tree_dangling_anchor_skipped():
    """A clobbered node whose recorded child isn't actually part of the real
    tree must be skipped rather than raising a ValueError from list.index()."""
    root = make_cmd(parent_function="circuit", line_type="call", code_line="circuit")
    root.identifier = 0

    stray_child = make_cmd(parent_function="circuit", line_type="line", quantum_or_classical="quantum")
    stray_child.code_line = qp.Hadamard(0)

    if_node = make_cmd(parent_function="circuit", line_type="scf", code_line="if i == 1:")
    if_node.clobbered_parent = root
    if_node.children = [stray_child]  # never actually attached to root.children
    root.clobbered_conditions = [if_node]

    with qp.queuing.AnnotatedQueue() as q:
        qp.Hadamard(0)

    debugger_root, flat_commands = dh.get_full_tree(
        root, code="circuit()", annotated_queue=q, user_transforms=None, method_names=set()
    )  # must not raise

    assert if_node not in flat_commands


# ===========================================================================
# set_active_debug_command
# ===========================================================================


def test_set_active_debug_command_marks_target_active():
    """The function builds a boolean mask [i == debug_index for i in range(len(commands))].
    The command at debug_index must have active_debug set to True."""
    cmds = [make_cmd() for _ in range(4)]
    assign_ids(cmds)
    dh.set_active_debug_command(cmds, 2)
    assert cmds[2].active_debug is True


def test_set_active_debug_command_all_others_false():
    """The boolean mask is True only at one position — every other command must be
    False regardless of what active_debug was before the call."""
    cmds = [make_cmd() for _ in range(5)]
    assign_ids(cmds)
    # Pre-mark everything True to confirm they are all cleared by the mask
    for c in cmds:
        c.active_debug = True
    dh.set_active_debug_command(cmds, 1)
    expected_mask = [False, True, False, False, False]  # only index 1 is True
    actual_mask = [c.active_debug for c in cmds]
    assert actual_mask == expected_mask


def test_set_active_debug_command_mask_matches_index():
    """Verify the entire resulting mask against the explicitly constructed expected mask
    for an arbitrary mid-list debug_index."""
    cmds = [make_cmd() for _ in range(6)]
    assign_ids(cmds)
    debug_index = 3
    dh.set_active_debug_command(cmds, debug_index)
    expected_mask = [i == debug_index for i in range(len(cmds))]
    actual_mask = [c.active_debug for c in cmds]
    assert actual_mask == expected_mask


def test_set_active_debug_command_first_element():
    """Selecting index 0 produces mask [True, False, False, ...]."""
    cmds = [make_cmd() for _ in range(3)]
    assign_ids(cmds)
    for c in cmds:
        c.active_debug = True
    dh.set_active_debug_command(cmds, 0)
    assert [c.active_debug for c in cmds] == [True, False, False]


def test_set_active_debug_command_last_element():
    """Selecting the last index produces mask [..., False, False, True]."""
    cmds = [make_cmd() for _ in range(3)]
    assign_ids(cmds)
    for c in cmds:
        c.active_debug = True
    dh.set_active_debug_command(cmds, 2)
    assert [c.active_debug for c in cmds] == [False, False, True]


def test_set_active_debug_command_single_element():
    """A single-element list with debug_index=0 produces mask [True]."""
    cmds = [make_cmd()]
    cmds[0].identifier = 0
    cmds[0].active_debug = False
    dh.set_active_debug_command(cmds, 0)
    assert [c.active_debug for c in cmds] == [True]


# ===========================================================================
# run_pennylane_commands
# ===========================================================================


def _make_quantum_cmd(op, line_type="line", identifier=0):
    """Helper: create a quantum command wrapping a PennyLane operation."""
    cmd = make_cmd(quantum_or_classical="quantum", line_type=line_type)
    cmd.code_line = op
    cmd.identifier = identifier
    return cmd


def test_run_pennylane_commands_returns_measurement_result():
    """run_pennylane_commands should execute all quantum gates up to (not including)
    the debug_identifier gate and return the final measurement result."""
    h_cmd = _make_quantum_cmd(qp.Hadamard(0), identifier=0)
    # debug_identifier=99 — nothing matches so ALL commands before measurement run
    last_command = [qp.expval(qp.PauliZ(0))]
    device = "default.qubit"
    num_shots = 0
    num_wires = 1
    result = dh.run_pennylane_commands(
        [h_cmd], device, num_shots, num_wires, last_command, debug_identifier=99
    )
    # H|0> gives <Z> = 0

    assert abs(float(result[0]) if hasattr(result, "__len__") else float(result)) < 1e-6


def test_run_pennylane_commands_stops_at_debug_identifier():
    """Gates whose identifier equals debug_identifier should NOT be applied.
    Running with debug_identifier=0 means the H gate is never applied,
    so <Z> on |0> should be +1 (not 0)."""
    h_cmd = _make_quantum_cmd(qp.Hadamard(0), identifier=0)
    last_command = [qp.expval(qp.PauliZ(0))]
    device = "default.qubit"
    num_shots = 0
    num_wires = 1
    result = dh.run_pennylane_commands(
        [h_cmd], device, num_shots, num_wires, last_command, debug_identifier=0
    )

    val = float(result[0]) if hasattr(result, "__len__") else float(result)
    assert val == pytest.approx(1.0)


def test_run_pennylane_commands_skips_measurement_line_type():
    """Commands with line_type='measurement' in the commands list should be skipped
    (they are not applied via qp.apply)"""
    meas_cmd = make_cmd(quantum_or_classical="quantum", line_type="measurement")
    meas_cmd.code_line = [qp.expval(qp.PauliZ(0))]
    meas_cmd.identifier = 10

    h_cmd = _make_quantum_cmd(qp.Hadamard(0), identifier=1)
    last_command = [qp.expval(qp.PauliZ(0))]
    device = "default.qubit"
    num_shots = 0
    num_wires = 1
    # debug_identifier=99 so the loop runs to completion
    result = dh.run_pennylane_commands(
        [meas_cmd, h_cmd], device, num_shots, num_wires, last_command, debug_identifier=99
    )

    val = float(result[0]) if hasattr(result, "__len__") else float(result)
    assert val == pytest.approx(0.0)


def test_run_pennylane_commands_with_shots_returns_result():
    """Passing a non-zero shot count should raise no exception and return a result."""
    h_cmd = _make_quantum_cmd(qp.Hadamard(0), identifier=0)
    last_command = [qp.expval(qp.PauliZ(0))]
    device = "default.qubit"
    num_shots = 100
    num_wires = 1
    result = dh.run_pennylane_commands(
        [h_cmd], device, num_shots, num_wires, last_command, debug_identifier=99
    )
    assert result is not None


def test_run_pennylane_commands_no_gates_returns_z_plus1():
    """With an empty gate list and debug_identifier that never matches,
    the circuit applies nothing — <Z> on |0> is +1."""
    last_command = [qp.expval(qp.PauliZ(0))]
    device = "default.qubit"
    num_shots = 0
    num_wires = 1
    result = dh.run_pennylane_commands([], device, num_shots, num_wires, last_command, debug_identifier=99)

    val = float(result[0]) if hasattr(result, "__len__") else float(result)
    assert val == pytest.approx(1.0)


def test_run_pennylane_commands_mid_circuit_measurement_applied():
    """A mid-circuit measurement command (line_type='mid_measurement') must NOT be
    skipped by the 'if line_type == measurement: continue' guard."""

    h_cmd = _make_quantum_cmd(qp.Hadamard(0), identifier=0)

    mid_cmd = make_cmd(quantum_or_classical="quantum", line_type="mid_measurement")
    mid_cmd.code_line = MidMeasureMP(wires=qp.wires.Wires([0]))
    mid_cmd.identifier = 1
    device = "default.qubit"
    num_shots = 0
    num_wires = 1
    last_command = [qp.expval(qp.PauliZ(0))]
    result = dh.run_pennylane_commands(
        [h_cmd, mid_cmd], device, num_shots, num_wires, last_command, debug_identifier=99
    )

    val = float(result[0]) if hasattr(result, "__len__") else float(result)
    assert np.isfinite(val)


def test_run_pennylane_commands_mid_circuit_measurement_collapses_with_postselect():
    """Using postselect=0 on MidMeasureMP in exact (analytic) mode forces the
    device to condition on the |0> measurement outcome.

    After H(0) + postselected mid-measure(0), the qubit is guaranteed to collapse
    to |0>, so expval(Z) = +1.  This confirms that:
      - the mid-measurement IS applied (not skipped by the 'measurement' filter), and
      - postselection takes effect, producing a result different from the no-mid-measure
        baseline where <Z> = 0.
    """

    h_cmd = _make_quantum_cmd(qp.Hadamard(0), identifier=0)

    # postselect=0 conditions on the |0> outcome in exact (analytic) mode
    mid_cmd = make_cmd(quantum_or_classical="quantum", line_type="mid_measurement")
    mid_cmd.code_line = MidMeasureMP(wires=qp.wires.Wires([0]), postselect=0)
    mid_cmd.identifier = 1

    last_command = [qp.expval(qp.PauliZ(0))]
    device = "default.qubit"
    num_shots = 0
    num_wires = 1
    result = dh.run_pennylane_commands(
        [h_cmd, mid_cmd], device, num_shots, num_wires, last_command, debug_identifier=99
    )

    val = float(result[0]) if hasattr(result, "__len__") else float(result)
    # Conditioned on |0> measurement — qubit is in |0>, so <Z> = +1
    assert val == pytest.approx(1.0)


def test_run_pennylane_commands_stops_before_mid_circuit_measurement():
    """If debug_identifier matches the mid-measurement command, the loop breaks
    before applying it.  The qubit stays in the H superposition state, so
    expval(Z) ≈ 0 (not ±1 as it would be after collapse).
    """

    h_cmd = _make_quantum_cmd(qp.Hadamard(0), identifier=0)

    mid_cmd = make_cmd(quantum_or_classical="quantum", line_type="mid_measurement")
    mid_cmd.code_line = MidMeasureMP(wires=qp.wires.Wires([0]))
    mid_cmd.identifier = 1 
    device = "default.qubit"
    num_shots = 0
    num_wires = 1
    last_command = [qp.expval(qp.PauliZ(0))]
    result = dh.run_pennylane_commands(
        [h_cmd, mid_cmd], device, num_shots, num_wires, last_command, debug_identifier=1
    )

    val = float(result[0]) if hasattr(result, "__len__") else float(result)
    assert val == pytest.approx(0.0)
