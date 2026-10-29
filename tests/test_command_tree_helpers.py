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
Tests for server/helpers/command_tree_helpers.py.
"""

import numpy as np
import pennylane as qp
from pennylane.measurements import MidMeasureMP

from server.command import Command
from server.helpers import command_tree_helpers as cth


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
# update_identifier_numbers
# ===========================================================================


def test_update_identifier_numbers_assigns_sequential_ids():
    """Identifiers should be 0-based sequential integers matching list position."""
    cmds = [make_cmd() for _ in range(4)]
    cth.update_identifier_numbers(cmds)
    assert [c.identifier for c in cmds] == [0, 1, 2, 3]


def test_update_identifier_numbers_single_command():
    """A single-element list should receive identifier 0."""
    cmds = [make_cmd()]
    cth.update_identifier_numbers(cmds)
    assert cmds[0].identifier == 0


def test_update_identifier_numbers_overwrites_existing_ids():
    """Any pre-existing identifier values must be overwritten."""
    cmds = [make_cmd() for _ in range(3)]
    for c in cmds:
        c.identifier = 99  # garbage value
    cth.update_identifier_numbers(cmds)
    assert [c.identifier for c in cmds] == [0, 1, 2]


def test_update_identifier_numbers_empty_list():
    """An empty command list should not raise any exception."""
    cth.update_identifier_numbers([])


# ===========================================================================
# update_parent_id
# ===========================================================================


def test_update_parent_id_root_has_no_parent():
    """The root command (index 0) keeps parent_id as None."""
    root = make_cmd(line_type="call", indent=0)
    root.identifier = 0
    child = make_cmd(line_type="line", indent=4)
    child.identifier = 1
    cth.update_parent_id([root, child])
    assert root.parent_id is None


def test_update_parent_id_child_points_to_root():
    """A simple child command should be linked to the root identifier."""
    root = make_cmd(line_type="call", indent=0, code_line="circuit()")
    root.identifier = 0
    child = make_cmd(line_type="line", indent=4, code_line="qp.H(0)")
    child.identifier = 1
    cth.update_parent_id([root, child])
    assert child.parent_id == 0


def test_update_parent_id_scf_linked_to_parent():
    """An scf (structured control flow) command should be linked to the enclosing scope."""
    root = make_cmd(line_type="call", indent=0, code_line="circuit()")
    root.identifier = 0
    scf = make_cmd(line_type="scf", indent=4, code_line="for i in range(3):")
    scf.identifier = 1
    cth.update_parent_id([root, scf])
    assert scf.parent_id == 0


def test_update_parent_id_sibling_scf_pops_previous():
    """Two scf nodes at the same indent level (e.g. if/elif) are siblings —
    the second should NOT be a child of the first; it should pop the first scf
    frame and link to the shared enclosing parent."""
    root = make_cmd(line_type="call", indent=0, code_line="circuit()")
    root.identifier = 0
    scf1 = make_cmd(line_type="scf", indent=4, code_line="if True:")
    scf1.identifier = 1
    scf2 = make_cmd(line_type="scf", indent=4, code_line="elif False:")
    scf2.identifier = 2
    cth.update_parent_id([root, scf1, scf2])
    assert scf2.parent_id == 0


def test_update_parent_id_return_pops_call_frame():
    """After a 'return' command the enclosing 'call' frame must be popped cleanly
    (no exception expected, structure should remain coherent)."""
    root = make_cmd(line_type="call", indent=0, code_line="circuit()")
    root.identifier = 0
    child = make_cmd(line_type="line", indent=4, code_line="qp.H(0)")
    child.identifier = 1
    ret = make_cmd(line_type="return", indent=4, code_line="return qp.probs()")
    ret.identifier = 2
    cth.update_parent_id([root, child, ret])  # must not raise


def test_update_parent_id_nested_scf_and_method_call():
    """Models a circuit function containing a for-loop that itself contains a
    sub-function call.  Verifies that every command is linked to the correct
    enclosing scope after the full traversal.

    The simulated execution trace represents this code structure:

        def circuit():          # cmd0 — root call frame (no "def " so scf branch fires for cmd1)
            for i in range(2):  # cmd1 — scf, pushed onto stack
                some_func()     # cmd2 — call site, inside for-loop scope
                def some_func():# cmd3 — inside some_func call
                    qp.H(0)    # cmd4 — inside some_func call
                    return      # cmd5 — ends some_func, pops call frame
                qp.X(0)        # cmd6 — back inside for-loop scope after return

    Expected parent_id values:
        cmd1 → 0  (for-loop is a child of circuit / cmd0)
        cmd2 → 1  (call site some_func() is inside the for-loop)
        cmd3 → 2  (def some_func itself lives inside the for-loop; becomes call frame)
        cmd4 → 2  (qp.H(0) is inside some_func)
        cmd5 → 2  (return is linked to the top of the stack — some_func's own
                   frame — before that frame is popped)
        cmd6 → 1  (after some_func returns the stack is back to the for-loop frame)
    """
    # cmd0: root — code_line must NOT contain "def " so the scf branch fires for cmd1
    cmd0 = make_cmd(parent_function="circuit", line_type="call", code_line="circuit", indent=0)
    cmd0.identifier = 0

    # cmd1: for-loop scf — should be linked to cmd0 via the scf branch
    cmd1 = make_cmd(
        parent_function="circuit",
        line_type="scf",
        code_line="for i in range(2):",
        indent=4,
    )
    cmd1.identifier = 1

    # cmd2: call site of some_func inside the for-loop — prev (cmd1) has no "def "
    # so goes through the else branch and gets linked to the for-loop frame (cmd1)
    cmd2 = make_cmd(parent_function="circuit", line_type="line", code_line="some_func()", indent=8)
    cmd2.identifier = 2

    # cmd3: the def line of some_func — prev (cmd2 = "some_func()") has no "def ",
    # so cmd3 also goes through else and gets linked to cmd1 (for-loop).
    # When cmd4 is processed, prev=cmd3 has "def " → cmd3 is upgraded to a call frame.
    cmd3 = make_cmd(
        parent_function="circuit",
        line_type="call",
        code_line="def some_func():",
        indent=8,
    )
    cmd3.identifier = 3

    # cmd4: first line inside some_func — prev=cmd3 has "def " → "def" branch fires;
    # cmd3 becomes call frame, pushed onto stack; cmd4 linked to cmd3
    cmd4 = make_cmd(parent_function="some_func", line_type="line", code_line="qp.H(0)", indent=12)
    cmd4.identifier = 4

    # cmd5: return inside some_func — linked to the top of the stack (some_func's
    # call frame, cmd3) first; the frame is only popped afterward
    cmd5 = make_cmd(parent_function="some_func", line_type="return", code_line="return", indent=12)
    cmd5.identifier = 5

    # cmd6: next gate back in the for-loop — after the call frame was popped the
    # stack top is the for-loop scf frame (cmd1), so cmd6 is linked to cmd1
    cmd6 = make_cmd(parent_function="circuit", line_type="line", code_line="qp.X(0)", indent=8)
    cmd6.identifier = 6

    commands = [cmd0, cmd1, cmd2, cmd3, cmd4, cmd5, cmd6]
    cth.update_parent_id(commands)

    assert cmd1.parent_id == 0, "for-loop must be child of circuit"
    assert cmd2.parent_id == 1, "call site must be inside for-loop"
    assert cmd3.parent_id == 2, "def line must sit inside for-loop"
    assert cmd4.parent_id == 2, "gate must be inside some_func"
    assert cmd5.parent_id == 2, "return must be inside some_func"
    assert cmd6.parent_id == 1, "after return, gate must be back in for-loop"


def test_update_parent_id_return_from_nested_scf_inside_call_pops_call_frame():
    """A helper whose last statement is nested in an if/else must fully unwind its call frame on return, so later siblings (cmd6, cmd7) land back under my_circuit (cmd0), not helper (cmd2)."""
    cmd0 = make_cmd(parent_function="my_circuit", line_type="call", code_line="@qp.qnode(dev)", indent=0)
    cmd0.identifier = 0

    cmd1 = make_cmd(parent_function="my_circuit", line_type="line", code_line="qp.Hadamard(wires=0)", indent=4)
    cmd1.identifier = 1

    cmd2 = make_cmd(parent_function="my_circuit", line_type="line", code_line="helper(0)", indent=4)
    cmd2.identifier = 2

    cmd3 = make_cmd(parent_function="helper", line_type="call", code_line="def helper(i):", indent=0)
    cmd3.identifier = 3

    cmd4 = make_cmd(parent_function="helper", line_type="scf", code_line="if i == 1:", indent=4)
    cmd4.identifier = 4

    cmd5 = make_cmd(parent_function="helper", line_type="return", code_line="qp.Y(0)", indent=8)
    cmd5.identifier = 5

    cmd6 = make_cmd(parent_function="my_circuit", line_type="line", code_line="qp.CNOT(wires=[0, 1])", indent=4)
    cmd6.identifier = 6

    cmd7 = make_cmd(parent_function="my_circuit", line_type="measurement", code_line="return qp.probs()", indent=4)
    cmd7.identifier = 7

    commands = [cmd0, cmd1, cmd2, cmd3, cmd4, cmd5, cmd6, cmd7]
    cth.update_parent_id(commands)

    assert cmd2.parent_id == 0, "helper(0) call site must be a child of my_circuit"
    assert cmd4.parent_id == 2, "the if/else must be linked inside helper's call frame"
    assert cmd5.parent_id == 4, "qp.Y(0) must be linked inside the else branch"
    assert cmd6.parent_id == 0, "CNOT after helper() returns must be back inside my_circuit, not helper"
    assert cmd7.parent_id == 0, "the measurement after helper() returns must be back inside my_circuit, not helper"


def test_update_parent_id_return_matching_loop_header_stays_nested_in_loop():
    """When a helper's last statement is a for-loop, the loop's final header revisit (cmd8, relabelled "return") must stay nested under the loop (cmd6), while later siblings (cmd9, cmd10) still land back under my_circuit."""
    cmd0 = make_cmd(parent_function="my_circuit", line_type="call", code_line="@qp.qnode(dev)", indent=0)
    cmd0.identifier = 0

    cmd1 = make_cmd(parent_function="my_circuit", line_type="line", code_line="qp.Hadamard(wires=0)", indent=4)
    cmd1.identifier = 1

    cmd2 = make_cmd(parent_function="my_circuit", line_type="line", code_line="helper(10)", indent=4)
    cmd2.identifier = 2

    cmd3 = make_cmd(parent_function="helper", line_type="call", code_line="def helper(i):", indent=0)
    cmd3.identifier = 3

    cmd4 = make_cmd(parent_function="helper", line_type="scf", code_line="if i == 1:", indent=4)
    cmd4.identifier = 4

    cmd5 = make_cmd(parent_function="helper", line_type="line", code_line="qp.Y(0)", indent=8)
    cmd5.identifier = 5

    cmd6 = make_cmd(parent_function="helper", line_type="scf", code_line="for i in range(3):", indent=4)
    cmd6.identifier = 6

    cmd7 = make_cmd(parent_function="helper", line_type="line", code_line="qp.RX(1, 1)", indent=8)
    cmd7.identifier = 7

    # cmd8 is the loop header's final revisit, relabelled "return" on frame exit.
    cmd8 = make_cmd(parent_function="helper", line_type="return", code_line="for i in range(3):", indent=4)
    cmd8.identifier = 8
    cmd8.line_number = cmd6.line_number

    cmd9 = make_cmd(parent_function="my_circuit", line_type="line", code_line="qp.CNOT(wires=[0, 1])", indent=4)
    cmd9.identifier = 9

    cmd10 = make_cmd(parent_function="my_circuit", line_type="measurement", code_line="return qp.probs()", indent=4)
    cmd10.identifier = 10

    commands = [cmd0, cmd1, cmd2, cmd3, cmd4, cmd5, cmd6, cmd7, cmd8, cmd9, cmd10]
    cth.update_parent_id(commands)

    assert cmd6.parent_id == 2, "the for-loop must be linked inside helper's call frame"
    assert cmd8.parent_id == cmd6.identifier, "the loop's final-check/return row must stay nested inside the for-loop, not hoisted to helper"
    assert cmd9.parent_id == 0, "CNOT after helper() returns must be back inside my_circuit, not helper"
    assert cmd10.parent_id == 0, "the measurement after helper() returns must be back inside my_circuit, not helper"


# ===========================================================================
# update_command_parent_function
# ===========================================================================


def test_update_command_parent_function_for_loop():
    """Children of a 'for' scf node should have parent_function set to 'for'."""
    parent = make_cmd(line_type="scf", indent=0, code_line="for i in range(3):")
    parent.identifier = 0
    child = make_cmd(line_type="line", indent=4)
    child.identifier = 1
    child.parent_id = 0
    cth.update_command_parent_function([parent, child])
    assert child.parent_function == "for"


def test_update_command_parent_function_while_loop():
    """Children of a 'while' scf node should have parent_function set to 'while'."""
    parent = make_cmd(line_type="scf", indent=0, code_line="while True:")
    parent.identifier = 0
    child = make_cmd(line_type="line", indent=4)
    child.identifier = 1
    child.parent_id = 0
    cth.update_command_parent_function([parent, child])
    assert child.parent_function == "while"


def test_update_command_parent_function_if_block():
    """Children of an 'if' scf node should have parent_function set to 'if'."""
    parent = make_cmd(line_type="scf", indent=0, code_line="if x > 0:")
    parent.identifier = 0
    child = make_cmd(line_type="line", indent=4)
    child.identifier = 1
    child.parent_id = 0
    cth.update_command_parent_function([parent, child])
    assert child.parent_function == "if"


def test_update_command_parent_function_non_scf_parent_unchanged():
    """Command whose parent is NOT an scf node should keep its original parent_function."""
    root = make_cmd(
        parent_function="circuit",
        line_type="call",
        code_line="def circuit():",
        indent=0,
    )
    root.identifier = 0
    child = make_cmd(parent_function="circuit", line_type="line", code_line="qp.H(0)", indent=4)
    child.identifier = 1
    child.parent_id = 0
    cth.update_command_parent_function([root, child])
    assert child.parent_function == "circuit"


def test_update_command_parent_function_empty_list():
    """Empty command list should be handled gracefully without raising."""
    cth.update_command_parent_function([])


def test_update_command_parent_function_missing_parent_id():
    """A command whose parent_id does not match any command
    should not raise and should leave parent_function unchanged."""
    cmd = make_cmd(parent_function="circuit", line_type="line")
    cmd.identifier = 5
    cmd.parent_id = 999  # no command has id 999
    cth.update_command_parent_function([cmd])
    assert cmd.parent_function == "circuit"


# ===========================================================================
# update_command_children
# ===========================================================================


def test_update_command_children_child_appended_to_parent():
    """A child node must appear in its parent's children list after the update."""
    parent = make_cmd(indent=0)
    parent.identifier = 0
    child = make_cmd(indent=4)
    child.identifier = 1
    child.parent_id = 0
    cth.update_command_children([parent, child])
    assert child in parent.children


def test_update_command_children_stale_data_cleared():
    """Previously-stale children should be cleared; only commands whose
    parent_id matches should appear after the call."""
    parent = make_cmd(indent=0)
    parent.identifier = 0
    stale = make_cmd(indent=4)
    stale.identifier = 99
    parent.children = [stale]  # pre-populate with stale data

    child = make_cmd(indent=4)
    child.identifier = 1
    child.parent_id = 0
    cth.update_command_children([parent, child])
    assert stale not in parent.children
    assert child in parent.children


def test_update_command_children_root_stays_empty():
    """The root command (parent_id=None) should not be
    added as a child to any other command."""
    root = make_cmd(indent=0)
    root.identifier = 0
    root.parent_id = None
    cth.update_command_children([root])
    assert root.children == []


def test_update_command_children_multiple_children_same_parent():
    """Multiple commands pointing to the same parent should all appear in
    that parent's children list."""
    parent = make_cmd(indent=0)
    parent.identifier = 0
    c1 = make_cmd(indent=4)
    c1.identifier = 1
    c1.parent_id = 0
    c2 = make_cmd(indent=4)
    c2.identifier = 2
    c2.parent_id = 0
    cth.update_command_children([parent, c1, c2])
    assert c1 in parent.children
    assert c2 in parent.children


def test_update_command_children_empty_list():
    """Empty command list should not raise."""
    cth.update_command_children([])


# ===========================================================================
# update_tree_node_names
# ===========================================================================


def test_update_tree_node_names_standard_gate():
    """A standard Hadamard gate operation should produce tree_node_name='H'."""
    cmd = make_cmd(quantum_or_classical="quantum", line_type="line")
    cmd.code_line = qp.Hadamard(0)
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "H"


def test_update_tree_node_names_mid_measure():
    """A MidMeasureMP operation should use op.label() output."""
    mid_op = MidMeasureMP(wires=qp.wires.Wires([0]))
    cmd = make_cmd(quantum_or_classical="quantum", line_type="mid_measurement")
    cmd.code_line = mid_op
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == mid_op.label()


def test_update_tree_node_names_adjoint_gate():
    """An adjoint-type command should use op.label() for the tree node name."""
    op = qp.adjoint(qp.S)(0)
    cmd = make_cmd(quantum_or_classical="quantum", line_type="adjoint")
    cmd.code_line = op
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == op.label()


def test_update_tree_node_names_terminal_measurement():
    """A terminal measurement command should always produce '⎋'."""
    cmd = make_cmd(quantum_or_classical="quantum", line_type="measurement")
    cmd.code_line = []  # terminal measurements store a list of ops
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "⎋"


def test_update_tree_node_names_scf_for_fallback():
    """A typical 'for i in ...:' scf line does NOT match the startswith check
    (scf_keywords already has a trailing space, so the check becomes 'for  i...')
    and falls back to the 'scf' default."""
    cmd = make_cmd(line_type="scf", code_line="for i in range(3):")
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "for"


def test_update_tree_node_names_scf_for_keyword_match():
    """A bare 'for :' code_line matches startswith(keyword + ':') and returns
    the keyword value 'for ' as the tree node name."""
    cmd = make_cmd(line_type="scf", code_line="for :")
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "for"


def test_update_tree_node_names_scf_if_fallback():
    """A typical 'if x > 0:' scf line falls back to the 'scf' default because the
    source checks startswith('if  ') (double space) which does not match."""
    cmd = make_cmd(line_type="scf", code_line="if x > 0:")
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "if"


def test_update_tree_node_names_scf_if_keyword_match():
    """A bare 'if :' code_line triggers the keyword match and returns 'if '."""
    cmd = make_cmd(line_type="scf", code_line="if :")
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "if"


def test_update_tree_node_names_scf_while_fallback():
    """'while True:' falls back to 'scf' because 'while True' does not start
    with 'while  ' (double space)."""
    cmd = make_cmd(line_type="scf", code_line="while True:")
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "while"


def test_update_tree_node_names_scf_while_keyword_match():
    """A bare 'while :' code_line triggers the keyword match."""
    cmd = make_cmd(line_type="scf", code_line="while :")
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "while"


def test_update_tree_node_names_def_extracts_function_name():
    """A 'def' code line should extract everything between 'def ' and '(' as
    the tree node name."""
    cmd = make_cmd(code_line="def my_gate(wires):")
    cth.update_tree_node_names([cmd], ["my_gate"])
    assert cmd.tree_node_name == "my_gate"


def test_update_tree_node_names_function_call_extracts_callable():
    """A classical function call line should extract the final dotted segment
    before '(' as the tree node name."""
    cmd = make_cmd(code_line="my_module.helper(arg1, arg2)")
    cth.update_tree_node_names([cmd], ["helper"])
    assert cmd.tree_node_name == "helper"


def test_update_tree_node_names_return_line():
    """A return-type command with no parentheses should have tree_node_name='return'."""
    cmd = make_cmd(line_type="return", code_line="return value")
    cth.update_tree_node_names([cmd], [])
    assert cmd.tree_node_name == "return"


def test_update_tree_node_names_qnode_replaced_by_parent_function():
    """If a command resolves to 'qnode' as the tree_node_name, it should be
    overridden by command.parent_function."""
    cmd = make_cmd(parent_function="circuit", code_line="@qp.qnode(dev)")
    cth.update_tree_node_names([cmd], ["circuit"])
    assert cmd.tree_node_name == "circuit"


# ===========================================================================
# update_condition_context
# ===========================================================================


def test_update_condition_context_if_child_gets_context():
    """A command whose parent_function is 'if' should receive a condition_context
    string containing the parent's line number and code_line."""
    parent = make_cmd(line_number=5, code_line="if x == 1:", line_type="scf")
    parent.identifier = 0
    child = make_cmd(parent_function="if", line_number=6, code_line="qp.H(0)")
    child.identifier = 1
    child.parent_id = 0
    cth.update_condition_context([parent, child])
    assert "(line 5)" in child.condition_context
    assert "if x == 1:" in child.condition_context


def test_update_condition_context_elif_child_gets_context():
    """A command whose parent_function is 'elif' should also receive a
    condition_context string."""
    parent = make_cmd(line_number=8, code_line="elif y == 2:", line_type="scf")
    parent.identifier = 0
    child = make_cmd(parent_function="elif", line_number=9)
    child.identifier = 1
    child.parent_id = 0
    cth.update_condition_context([parent, child])
    assert child.condition_context is not None
    assert "elif y == 2:" in child.condition_context


def test_update_condition_context_for_loop_child_unchanged():
    """A command inside a 'for' loop (parent_function='for') should NOT
    receive a condition_context."""
    parent = make_cmd(line_number=3, code_line="for i in range(3):", line_type="scf")
    parent.identifier = 0
    child = make_cmd(parent_function="for", line_number=4)
    child.identifier = 1
    child.parent_id = 0
    cth.update_condition_context([parent, child])
    assert child.condition_context is None


def test_update_condition_context_unrelated_parent_function_unchanged():
    """Commands with parent_function values that are not 'if'/'elif'
    should be left untouched (condition_context stays None)."""
    cmd = make_cmd(parent_function="circuit")
    cmd.identifier = 0
    cmd.parent_id = None
    cth.update_condition_context([cmd])
    assert cmd.condition_context is None


# ===========================================================================
# clobber_classical_conditions
# ===========================================================================


def _build_if_tree():
    """Helper: root -> if_node -> [child1, child2]."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    if_node = make_cmd(line_type="scf", code_line="if True:", indent=4)
    if_node.identifier = 1
    if_node.parent_id = 0

    child1 = make_cmd(line_type="line", code_line="qp.H(0)", indent=8)
    child1.identifier = 2
    child1.parent_id = 1

    child2 = make_cmd(line_type="line", code_line="qp.X(0)", indent=8)
    child2.identifier = 3
    child2.parent_id = 1

    if_node.children = [child1, child2]
    root.children = [if_node]
    return root, if_node, child1, child2


def test_clobber_classical_conditions_if_node_removed():
    """After clobbering, the 'if' scf node should no longer be in its parent's
    children list; instead its own children should be there."""
    root, if_node, child1, child2 = _build_if_tree()
    cth.clobber_classical_conditions([if_node], [root, if_node, child1, child2])
    assert if_node not in root.children
    assert child1 in root.children
    assert child2 in root.children


def test_clobber_classical_conditions_children_reparented():
    """Children of a removed 'if' node must have their parent_id
    updated to point to the grandparent."""
    root, if_node, child1, child2 = _build_if_tree()
    cth.clobber_classical_conditions([if_node], [root, if_node, child1, child2])
    assert child1.parent_id == root.identifier
    assert child2.parent_id == root.identifier


def test_clobber_classical_conditions_for_node_preserved():
    """An scf 'for' node should NOT be removed by clobber_classical_conditions."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None
    for_node = make_cmd(line_type="scf", code_line="for i in range(3):", indent=4)
    for_node.identifier = 1
    for_node.parent_id = 0
    gate = make_cmd(line_type="line", code_line="qp.H(0)", indent=8)
    gate.identifier = 2
    gate.parent_id = 1
    for_node.children = [gate]
    root.children = [for_node]
    cth.clobber_classical_conditions([for_node], [root, for_node, gate])
    assert for_node in root.children


def test_clobber_classical_conditions_nested_if_inside_for():
    """An 'if' node nested inside a 'for' loop should also be clobbered when
    recursion descends into the for loop's children."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None
    for_node = make_cmd(line_type="scf", code_line="for i in range(2):", indent=4)
    for_node.identifier = 1
    for_node.parent_id = 0
    if_node = make_cmd(line_type="scf", code_line="if cond:", indent=8)
    if_node.identifier = 2
    if_node.parent_id = 1
    gate = make_cmd(line_type="line", code_line="qp.H(0)", indent=12)
    gate.identifier = 3
    gate.parent_id = 2
    if_node.children = [gate]
    for_node.children = [if_node]
    root.children = [for_node]
    cth.clobber_classical_conditions(root.children, [root, for_node, if_node, gate])
    # The 'if' node should have been removed from for_node.children
    assert if_node not in for_node.children
    assert gate in for_node.children


def test_clobber_classical_conditions_records_clobbered_node():
    """When a clobbered_nodes list is passed, the removed if/elif node must be
    appended to it, with clobbered_parent set to its true (grandparent) parent
    so callers (e.g. the debugger) can still find it after it's been removed
    from the tree."""
    root, if_node, child1, child2 = _build_if_tree()
    clobbered = []
    cth.clobber_classical_conditions([if_node], [root, if_node, child1, child2], clobbered)
    assert clobbered == [if_node]
    assert if_node.clobbered_parent is root


def test_clobber_classical_conditions_no_list_no_error():
    """Omitting clobbered_nodes (the default) must not raise and must not
    attempt to record anything."""
    root, if_node, child1, child2 = _build_if_tree()
    cth.clobber_classical_conditions([if_node], [root, if_node, child1, child2])
    assert if_node.clobbered_parent is None


def test_clobber_classical_conditions_for_node_not_recorded():
    """A 'for' node is never clobbered, so it must not be appended to
    clobbered_nodes."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None
    for_node = make_cmd(line_type="scf", code_line="for i in range(3):", indent=4)
    for_node.identifier = 1
    for_node.parent_id = 0
    gate = make_cmd(line_type="line", code_line="qp.H(0)", indent=8)
    gate.identifier = 2
    gate.parent_id = 1
    for_node.children = [gate]
    root.children = [for_node]
    clobbered = []
    cth.clobber_classical_conditions([for_node], [root, for_node, gate], clobbered)
    assert clobbered == []


def test_clobber_classical_conditions_nested_if_records_both_with_chain():
    """A nested 'if a: if b: ...' must record both condition nodes exactly
    once each."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    if_a = make_cmd(line_type="scf", code_line="if a:", indent=4)
    if_a.identifier = 1
    if_a.parent_id = 0

    if_b = make_cmd(line_type="scf", code_line="if b:", indent=8)
    if_b.identifier = 2
    if_b.parent_id = 1

    gate = make_cmd(line_type="line", code_line="qp.H(0)", indent=12)
    gate.identifier = 3
    gate.parent_id = 2

    if_b.children = [gate]
    if_a.children = [if_b]
    root.children = [if_a]

    clobbered = []
    cth.clobber_classical_conditions([if_a], [root, if_a, if_b, gate], clobbered)

    assert clobbered == [if_b, if_a], "inner if must be recorded before the outer one (bottom-up)"
    assert if_b.clobbered_parent is if_a, "inner if's true parent is the outer if"
    assert if_a.clobbered_parent is root, "outer if's true parent is the real grandparent"
    assert gate in root.children, "the executed gate must end up flattened all the way to root"


def test_clobber_classical_conditions_untaken_branch_still_recorded():
    """An if node whose condition never ran true (no children) must still be
    appended to clobbered_nodes"""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    if_node = make_cmd(line_type="scf", code_line="if False:", indent=4)
    if_node.identifier = 1
    if_node.parent_id = 0
    if_node.children = []
    root.children = [if_node]

    clobbered = []
    cth.clobber_classical_conditions([if_node], [root, if_node], clobbered)

    assert clobbered == [if_node]
    assert if_node.children == []


# ===========================================================================
# merge_scf_calls
# ===========================================================================


def _make_for_node(identifier, called_from, children, line_number=1):
    """Helper: create a for-loop scf command with pre-set children."""
    node = make_cmd(
        line_type="scf",
        code_line="for i in range(3):",
        indent=0,
        line_number=line_number,
    )
    node.identifier = identifier
    node.parent_id = called_from
    node.children = children
    return node


def test_merge_scf_calls_duplicate_for_nodes_merged():
    """Three consecutive identical 'for' scf nodes (same code_line, line_number,
    parent_id) should be collapsed into one node whose children
    list contains all children from the original nodes."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    gate1 = make_cmd(line_type="line", code_line="qp.X(0)")
    gate1.identifier = 2
    gate2 = make_cmd(line_type="line", code_line="qp.X(0)")
    gate2.identifier = 4
    gate3 = make_cmd(line_type="line", code_line="qp.X(0)")
    gate3.identifier = 6

    root.children = [
        _make_for_node(1, 0, [gate1]),
        _make_for_node(3, 0, [gate2]),
        _make_for_node(5, 0, [gate3]),
    ]
    cth.merge_scf_calls(root.children)

    assert len(root.children) == 1
    assert root.children[0].line_type == "scf"
    assert len(root.children[0].children) == 3


def test_merge_scf_calls_distinct_line_numbers_not_merged():
    """Two 'for' nodes at different line_numbers must NOT be merged."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    gate1 = make_cmd(line_type="line", code_line="qp.H(0)")
    gate1.identifier = 2
    gate2 = make_cmd(line_type="line", code_line="qp.X(0)")
    gate2.identifier = 4

    root.children = [
        _make_for_node(1, 0, [gate1], line_number=3),
        _make_for_node(3, 0, [gate2], line_number=7),  # different line → distinct
    ]
    cth.merge_scf_calls(root.children)
    assert len(root.children) == 2


def test_merge_scf_calls_empty_scf_excluded():
    """An scf node with no children is treated as empty and excluded from the
    merged output while non-scf nodes are still preserved."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    empty_for = make_cmd(line_type="scf", code_line="for i in range(3):", indent=0)
    empty_for.identifier = 1
    empty_for.parent_id = 0
    empty_for.children = []

    non_scf = make_cmd(line_type="line", code_line="qp.H(0)")
    non_scf.identifier = 2
    non_scf.parent_id = 0

    root.children = [empty_for, non_scf]
    cth.merge_scf_calls(root.children)
    assert non_scf in root.children


def test_merge_scf_calls_non_scf_nodes_preserved():
    """Non-scf nodes interspersed with scf nodes should remain in the result
    after merging."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    gate_before = make_cmd(line_type="line", code_line="qp.H(0)")
    gate_before.identifier = 1
    gate_before.parent_id = 0

    gate_child = make_cmd(line_type="line", code_line="qp.X(0)")
    gate_child.identifier = 3

    gate_after = make_cmd(line_type="line", code_line="qp.RZ(0.5, 1)")
    gate_after.identifier = 4
    gate_after.parent_id = 0

    root.children = [gate_before, _make_for_node(2, 0, [gate_child]), gate_after]
    cth.merge_scf_calls(root.children)

    assert gate_before in root.children
    assert gate_after in root.children


def test_merge_scf_calls_children_reparented_after_merge():
    """After merging, all children of the merged node must point to the
    surviving node's identifier, not the discarded duplicates."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    gate1 = make_cmd(line_type="line", code_line="qp.X(0)")
    gate1.identifier = 2
    gate1.parent_id = 1
    gate2 = make_cmd(line_type="line", code_line="qp.X(0)")
    gate2.identifier = 4
    gate2.parent_id = 3

    root.children = [_make_for_node(1, 0, [gate1]), _make_for_node(3, 0, [gate2])]
    cth.merge_scf_calls(root.children)

    surviving = root.children[0]
    for child in surviving.children:
        assert child.parent_id == surviving.identifier


def test_merge_scf_calls_redirects_clobbered_parent_to_survivor():
    """Regression test: an if node clobbered from inside a for-loop body has
    its clobbered_parent set to whichever specific for-loop iteration object
    it happened to sit under (clobbering runs before merging). If that exact
    iteration is then discarded as a duplicate here, clobbered_parent must be
    redirected to the surviving merged node -- otherwise it's left pointing
    at an object that's now unreachable and never gets a valid identifier,
    producing a dangling parent_id downstream (e.g. in graph_data)."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    gate1 = make_cmd(line_type="line", code_line="qp.X(0)")
    gate1.identifier = 2
    gate2 = make_cmd(line_type="line", code_line="qp.Y(0)")
    gate2.identifier = 4

    for_1 = _make_for_node(1, 0, [gate1])
    for_2 = _make_for_node(3, 0, [gate2])  # duplicate of for_1, will be discarded
    root.children = [for_1, for_2]

    # Simulate an if node clobbered out from inside for_2's body specifically
    # (as clobber_classical_conditions would have already done, before merging).
    if_node = make_cmd(line_type="scf", code_line="if phase != 0:")
    if_node.clobbered_parent = for_2
    clobbered_nodes = [if_node]

    cth.merge_scf_calls(root.children, clobbered_nodes)

    assert len(root.children) == 1, "for_1 and for_2 must still merge into one node"
    survivor = root.children[0]
    assert if_node.clobbered_parent is survivor, "clobbered_parent must be redirected to the survivor, not left pointing at the discarded for_2"


def test_merge_scf_calls_no_clobbered_nodes_no_error():
    """Omitting clobbered_nodes (the default) must not raise, even when scf
    duplicates get merged and discarded."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    gate1 = make_cmd(line_type="line", code_line="qp.X(0)")
    gate1.identifier = 2
    gate2 = make_cmd(line_type="line", code_line="qp.Y(0)")
    gate2.identifier = 4

    root.children = [_make_for_node(1, 0, [gate1]), _make_for_node(3, 0, [gate2])]
    cth.merge_scf_calls(root.children)  # must not raise
    assert len(root.children) == 1


# ===========================================================================
# get_fcn_output_from_tree
# ===========================================================================


def _build_simple_tree():
    """Helper: root -> [H gate, terminal measurement (expval Z)]."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    h_cmd = make_cmd(quantum_or_classical="quantum", line_type="line", indent=4)
    h_cmd.identifier = 1
    h_cmd.parent_id = 0
    h_cmd.code_line = qp.Hadamard(0)

    meas_cmd = make_cmd(quantum_or_classical="quantum", line_type="measurement", indent=4)
    meas_cmd.identifier = 2
    meas_cmd.parent_id = 0
    meas_cmd.code_line = [qp.expval(qp.PauliZ(0))]

    root.children = [h_cmd, meas_cmd]
    return root


def test_get_fcn_output_from_tree_returns_tuple():
    """get_fcn_output_from_tree must return a 2-tuple (output, exec_time)."""
    result = cth.get_fcn_output_from_tree(_build_simple_tree(), "default.qubit", 0, 1)
    assert isinstance(result, tuple) and len(result) == 2


def test_get_fcn_output_from_tree_exec_time_non_negative():
    """The execution time component of the returned tuple must be >= 0."""
    _, exec_time = cth.get_fcn_output_from_tree(_build_simple_tree(), "default.qubit", 0, 1)
    assert exec_time >= 0


def test_get_fcn_output_from_tree_expval_hadamard_near_zero():
    """H|0⟩ should give ⟨Z⟩ ≈ 0. The function returns a list when code_line is
    a list of operations, so we extract the first element before comparing."""
    output, _ = cth.get_fcn_output_from_tree(_build_simple_tree(), "default.qubit", 0, 1)
    value = output[0] if isinstance(output, (list, np.ndarray)) else output
    assert abs(float(value)) < 1e-6


def test_get_fcn_output_from_tree_no_measurement_falls_back_to_state():
    """When no terminal measurement command is present, the function should
    fall back to returning the quantum state without raising an exception."""
    root = make_cmd(line_type="call", code_line="circuit()", indent=0)
    root.identifier = 0
    root.parent_id = None

    h_cmd = make_cmd(quantum_or_classical="quantum", line_type="line", indent=4)
    h_cmd.identifier = 1
    h_cmd.parent_id = 0
    h_cmd.code_line = qp.Hadamard(0)
    root.children = [h_cmd]

    output, _ = cth.get_fcn_output_from_tree(root, "default.qubit", 0, 1)
    assert output is not None


def test_get_fcn_output_from_tree_with_shots():
    """Running with a non-zero shot count (positional arg) should still return
    a valid result without raising an exception."""
    # num_shots is the 4th positional argument, not a keyword argument
    output, _ = cth.get_fcn_output_from_tree(_build_simple_tree(), "default.qubit", 100, 1)
    assert output is not None
