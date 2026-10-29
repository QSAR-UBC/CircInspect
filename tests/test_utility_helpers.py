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
Tests for server/helpers/utility_helpers.py.
"""

import io
import tokenize
import base64

import matplotlib
import matplotlib.figure
import numpy as np
import pennylane as qp

matplotlib.use("Agg")
from matplotlib import pyplot as plt

from server.command import Command
from server.helpers import utility_helpers as uh


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


def make_quantum_cmd(op, line_type="line", identifier=0):
    """Factory for a quantum Command wrapping a PennyLane operation."""
    cmd = make_cmd(quantum_or_classical="quantum", line_type=line_type)
    cmd.code_line = op
    cmd.identifier = identifier
    return cmd


# ===========================================================================
# json_default
# ===========================================================================


def test_json_default_range_returns_json_string():
    """A range object should be serialised to a JSON array string."""
    result = uh.json_default(range(3))
    assert result == "[0, 1, 2]"


def test_json_default_empty_range():
    """An empty range should produce an empty JSON array."""
    result = uh.json_default(range(0))
    assert result == "[]"


def test_json_default_numpy_array_returns_list():
    """A numpy array should be converted to a plain Python list."""
    arr = np.array([1.0, 2.0, 3.0])
    result = uh.json_default(arr)
    assert result == [1.0, 2.0, 3.0]


def test_json_default_measurement_value_returns_string():
    """A MeasurementValue should be converted to its string representation."""
    with qp.queuing.AnnotatedQueue():
        mv = qp.measure(0)
    result = uh.json_default(mv)
    assert isinstance(result, str)


# ===========================================================================
# check_for_restricted_code
# ===========================================================================


def test_check_for_restricted_code_allows_pennylane():
    """Clean pennylane code should pass without any restriction errors."""
    code = "import pennylane as qp\nqp.PauliX(0)"
    assert uh.check_for_restricted_code(code) == ""


def test_check_for_restricted_code_blocks_os():
    """'import os' must be caught and return a 2-element error list."""
    result = uh.check_for_restricted_code("import os")
    assert len(result) == 2


def test_check_for_restricted_code_blocks_sys():
    """'import sys' must be caught."""
    result = uh.check_for_restricted_code("import sys")
    assert len(result) == 2


def test_check_for_restricted_code_blocks_open():
    """Use of open() must be caught."""
    result = uh.check_for_restricted_code('open("file.txt")')
    assert len(result) == 2


def test_check_for_restricted_code_blocks_exec():
    """Use of exec() must be caught."""
    result = uh.check_for_restricted_code('exec("code")')
    assert len(result) == 2


def test_check_for_restricted_code_blocks_eval():
    """Use of eval() must be caught."""
    result = uh.check_for_restricted_code('eval("1+1")')
    assert len(result) == 2


def test_check_for_restricted_code_blocks_breakpoint():
    """Use of breakpoint() must be caught."""
    result = uh.check_for_restricted_code("breakpoint()")
    assert len(result) == 2


def test_check_for_restricted_code_reports_correct_line_number():
    """The restriction error should mention the actual line number where the violation occurs."""
    code = "import pennylane as qp\nimport os"
    result = uh.check_for_restricted_code(code)
    assert "2" in result[1]


# ===========================================================================
# get_method_names
# ===========================================================================


def test_get_method_names_single_function():
    """A single function definition should return a set with that function name."""
    code = "def my_func():\n    pass"
    assert uh.get_method_names(code) == {"my_func"}


def test_get_method_names_multiple_functions():
    """Multiple function definitions should each appear in the returned set."""
    code = "def alpha():\n    pass\ndef beta():\n    pass"
    assert uh.get_method_names(code) == {"alpha", "beta"}


def test_get_method_names_no_functions():
    """Code with no function definitions should return an empty set."""
    code = "x = 1\nprint(x)"
    assert uh.get_method_names(code) == set()


def test_get_method_names_ignores_non_def_lines():
    """Lines that contain 'def' as part of a variable name should not be matched."""
    code = "define = 5\ndef real_func():\n    pass"
    # 'define' should not be matched; only 'real_func'
    result = uh.get_method_names(code)
    assert "real_func" in result


# ===========================================================================
# find_first_qnode_decorator
# ===========================================================================


def _tokenize(code):
    return list(tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline))


def test_find_first_qnode_decorator_basic():
    """Should return the (0-based) line index of the @qp.qnode decorator."""
    code = "import pennylane as qp\ndev = qp.device('default.qubit', wires=1)\n@qp.qnode(dev)\ndef circuit():\n    return qp.probs()\n"
    tokens = _tokenize(code)
    result = uh.find_first_qnode_decorator(tokens)
    assert result == 2  # 0-based: line 3 is index 2


def test_find_first_qnode_decorator_with_transform_above():
    """When a transform decorator precedes @qp.qnode, the qnode line index is still returned."""
    code = "import pennylane as qp\ndev = qp.device('default.qubit', wires=1)\n@some_transform\n@qp.qnode(dev)\ndef circuit():\n    return qp.probs()\n"
    tokens = _tokenize(code)
    result = uh.find_first_qnode_decorator(tokens)
    assert result == 3  # @qp.qnode is on line 4 → index 3


def test_find_first_qnode_decorator_returns_none_when_absent():
    """Returns None when no @qp.qnode decorator is present."""
    code = "def plain_function():\n    pass\n"
    tokens = _tokenize(code)
    assert uh.find_first_qnode_decorator(tokens) is None


# ===========================================================================
# get_qnode_name
# ===========================================================================


def test_get_qnode_name_basic():
    """Should return the name of the QNode when it exists in method_names."""
    code = "import pennylane as qp\n@qp.qnode(dev)\ndef circuit():\n    pass"
    method_names = {"circuit"}
    assert uh.get_qnode_name(code, method_names) == "circuit"


def test_get_qnode_name_not_in_method_names():
    """Should return None if the identified function is not in method_names."""
    code = "import pennylane as qp\n@qp.qnode(dev)\ndef circuit():\n    pass"
    method_names = {"other_func"}
    assert uh.get_qnode_name(code, method_names) is None


def test_get_qnode_name_with_comments_and_decorators():
    """Should find the QNode name even if there are comments/other decorators in between."""
    code = "@some_transform\n# a comment\n@qp.qnode(dev)\n# another comment\n@another_deco\ndef my_qnode():\n    pass"
    method_names = {"my_qnode"}
    assert uh.get_qnode_name(code, method_names) == "my_qnode"


def test_get_qnode_name_no_qnode():
    """Should return None if no @qp.qnode is present."""
    code = "def my_func():\n    pass"
    method_names = {"my_func"}
    assert uh.get_qnode_name(code, method_names) is None


# ===========================================================================
# newline_cleanup
# ===========================================================================


def test_newline_cleanup_collapses_multiline_args():
    """Arguments spanning multiple lines should be collapsed onto one line."""
    code = "qp.PauliX(\n    wires=0\n)\n"
    result = uh.newline_cleanup(code)
    assert "\n" not in result.split("(")[1].split(")")[0]


def test_newline_cleanup_no_change_for_single_line():
    """Single-line code should pass through unchanged (modulo whitespace normalisation)."""
    code = "qp.PauliX(wires=0)\n"
    result = uh.newline_cleanup(code)
    assert "qp.PauliX(wires=0)" in result


def test_newline_cleanup_preserves_outer_newlines():
    """Newlines outside of parentheses should be preserved."""
    code = "line1\nline2\n"
    result = uh.newline_cleanup(code)
    assert "line1" in result
    assert "line2" in result


# ===========================================================================
# comment_cleanup
# ===========================================================================


def test_comment_cleanup_removes_inline_comment():
    """An end-of-line comment should be stripped."""
    code = "x = 1  # this is a comment\n"
    result = uh.comment_cleanup(code)
    assert "# this is a comment" not in result
    assert "x = 1" in result


def test_comment_cleanup_removes_standalone_comment():
    """A line that is just a comment should become an empty line."""
    code = "# full line comment\nx = 1\n"
    result = uh.comment_cleanup(code)
    assert "# full line comment" not in result


def test_comment_cleanup_preserves_hash_in_string():
    """A '#' inside a string literal should NOT be treated as a comment."""
    code = 'print("#not a comment")\n'
    result = uh.comment_cleanup(code)
    assert "#not a comment" in result


# ===========================================================================
# code_cleanup
# ===========================================================================


def test_code_cleanup_combines_newline_and_comment_cleanup():
    """code_cleanup applies both newline and comment cleanup."""
    code = "qp.PauliX(\n    wires=0\n)\n# wire\n"
    result = uh.code_cleanup(code)
    assert "# wire" not in result
    assert "qp.PauliX" in result


# ===========================================================================
# flatten_tree
# ===========================================================================


def test_flatten_tree_single_node():
    """A tree consisting only of a root should return a list containing just the root."""
    root = make_cmd()
    root.identifier = 0
    assert uh.flatten_tree(root) == [root]


def test_flatten_tree_root_then_children():
    """The root should be first in the flattened list, followed by its children."""
    root = make_cmd()
    root.identifier = 0
    child = make_cmd()
    child.identifier = 1
    root.children = [child]
    result = uh.flatten_tree(root)
    assert result[0] is root
    assert result[1] is child


def test_flatten_tree_depth_first_order():
    """flatten_tree must recurse depth-first: root → child1 → grandchild → child2."""
    root = make_cmd()
    root.identifier = 0
    child1 = make_cmd()
    child1.identifier = 1
    grandchild = make_cmd()
    grandchild.identifier = 2
    child2 = make_cmd()
    child2.identifier = 3

    child1.children = [grandchild]
    root.children = [child1, child2]

    result = uh.flatten_tree(root)
    assert [c.identifier for c in result] == [0, 1, 2, 3]


def test_flatten_tree_all_nodes_present():
    """Every node in the tree should appear exactly once in the flattened list."""
    root = make_cmd()
    root.identifier = 0
    c1 = make_cmd()
    c1.identifier = 1
    c2 = make_cmd()
    c2.identifier = 2
    root.children = [c1, c2]

    result = uh.flatten_tree(root)
    assert len(result) == 3


# ===========================================================================
# get_children_from_identifier
# ===========================================================================


def test_get_children_from_identifier_returns_matching_commands():
    """Commands whose parent_id matches the query should be returned."""
    parent = make_cmd()
    parent.identifier = 0
    child = make_cmd()
    child.identifier = 1
    child.parent_id = 0

    result = uh.get_children_from_identifier(0, [parent, child])
    assert child in result
    assert parent not in result


def test_get_children_from_identifier_no_match_returns_empty():
    """No match should yield an empty list."""
    cmd = make_cmd()
    cmd.identifier = 1
    cmd.parent_id = 99

    assert uh.get_children_from_identifier(0, [cmd]) == []


def test_get_children_from_identifier_multiple_children():
    """Multiple commands with the same parent identifier should all be returned."""
    c1 = make_cmd()
    c1.identifier = 1
    c1.parent_id = 0
    c2 = make_cmd()
    c2.identifier = 2
    c2.parent_id = 0

    result = uh.get_children_from_identifier(0, [c1, c2])
    assert c1 in result
    assert c2 in result


# ===========================================================================
# get_sibling_commands
# ===========================================================================


def test_get_sibling_commands_returns_commands_with_same_parent():
    """Commands sharing the same parent identifier are siblings."""
    c1 = make_cmd()
    c1.identifier = 1
    c1.parent_id = 0
    c2 = make_cmd()
    c2.identifier = 2
    c2.parent_id = 0

    result = uh.get_sibling_commands([c1, c2], c1)
    assert c1 in result
    assert c2 in result


def test_get_sibling_commands_excludes_different_parent():
    """Commands with a different parent should not appear in the sibling list."""
    c1 = make_cmd()
    c1.identifier = 1
    c1.parent_id = 0
    c2 = make_cmd()
    c2.identifier = 2
    c2.parent_id = 5  # different parent

    result = uh.get_sibling_commands([c1, c2], c1)
    assert c2 not in result


def test_get_sibling_commands_single_command_returns_itself():
    """A command with no siblings should return only itself."""
    c = make_cmd()
    c.identifier = 1
    c.parent_id = 0
    result = uh.get_sibling_commands([c], c)
    assert result == [c]


# ===========================================================================
# get_command_by_identifier
# ===========================================================================


def test_get_command_by_identifier_finds_existing():
    """Should return the command with the matching identifier."""
    cmd = make_cmd()
    cmd.identifier = 42
    result = uh.get_command_by_identifier([cmd], 42)
    assert result is cmd


def test_get_command_by_identifier_returns_none_for_missing():
    """Should return None if no command has the given identifier."""
    cmd = make_cmd()
    cmd.identifier = 1
    assert uh.get_command_by_identifier([cmd], 999) is None


def test_get_command_by_identifier_returns_first_match():
    """Should return the first command whose identifier matches (list ordering)."""
    c1 = make_cmd()
    c1.identifier = 5
    c2 = make_cmd()
    c2.identifier = 5
    result = uh.get_command_by_identifier([c1, c2], 5)
    assert result is c1


# ===========================================================================
# collect_quantum_commands
# ===========================================================================


def test_collect_quantum_commands_includes_quantum_commands():
    """Quantum commands should be included in the output."""
    q_cmd = make_quantum_cmd(qp.PauliX(0))
    result = uh.collect_quantum_commands([q_cmd])
    assert q_cmd in result


def test_collect_quantum_commands_excludes_classical_commands():
    """Classical line commands should not be included."""
    classical_cmd = make_cmd(line_type="line", quantum_or_classical="classical")
    result = uh.collect_quantum_commands([classical_cmd])
    assert classical_cmd not in result


def test_collect_quantum_commands_includes_terminal_measurements():
    """Terminal measurement commands (line_type='measurement') should always be included."""
    m_cmd = make_cmd(line_type="measurement", quantum_or_classical="classical")
    m_cmd.code_line = [qp.expval(qp.PauliZ(0))]
    result = uh.collect_quantum_commands([m_cmd])
    assert m_cmd in result


def test_collect_quantum_commands_recurses_into_children():
    """collect_quantum_commands must descend into children."""
    parent = make_cmd(line_type="scf")
    child = make_quantum_cmd(qp.Hadamard(0), identifier=1)
    parent.children = [child]

    result = uh.collect_quantum_commands([parent])
    assert child in result


# ===========================================================================
# get_image_bs64_bytecode
# ===========================================================================


def test_get_image_bs64_bytecode_returns_string():
    """get_image_bs64_bytecode should return a non-empty string."""
    fig = plt.figure()
    result = uh.get_image_bs64_bytecode(fig)
    plt.close(fig)
    assert isinstance(result, str)
    assert len(result) > 0


def test_get_image_bs64_bytecode_is_valid_base64():
    """The returned string should be valid base64."""

    fig = plt.figure()
    result = uh.get_image_bs64_bytecode(fig)
    plt.close(fig)
    # Should not raise
    base64.b64decode(result)


# ===========================================================================
# get_wires_recursive
# ===========================================================================


def test_get_wires_recursive_quantum_gate():
    """A quantum gate command should contribute its wires to the result."""
    cmd = make_quantum_cmd(qp.PauliX(2))
    result = uh.get_wires_recursive(cmd)
    assert 2 in result


def test_get_wires_recursive_classical_command_no_wires():
    """A classical command should contribute no wires."""
    cmd = make_cmd(quantum_or_classical="classical")
    result = uh.get_wires_recursive(cmd)
    assert result == set()


def test_get_wires_recursive_descends_into_children():
    """Wires from child commands should be included in the parent's result."""
    parent = make_cmd(line_type="scf", quantum_or_classical="classical")
    child = make_quantum_cmd(qp.PauliZ(3), identifier=1)
    parent.children = [child]

    result = uh.get_wires_recursive(parent)
    assert 3 in result


def test_get_wires_recursive_list_code_line():
    """When code_line is a list of operations (terminal measurement), all wires are collected."""
    cmd = make_cmd(line_type="measurement", quantum_or_classical="quantum")
    cmd.code_line = [qp.expval(qp.PauliZ(0)), qp.expval(qp.PauliZ(1))]
    result = uh.get_wires_recursive(cmd)
    assert 0 in result
    assert 1 in result


def test_get_wires_recursive_conditional_gate():
    """A Conditional operation should contribute the base gate's wires."""
    with qp.queuing.AnnotatedQueue():
        meas_val = qp.measure(0)

    cond_op = qp.ops.Conditional(meas_val, qp.PauliX(1))
    cmd = make_cmd(line_type="cond", quantum_or_classical="quantum")
    cmd.code_line = cond_op
    result = uh.get_wires_recursive(cmd)
    # The conditional acts on wire 1 via its base
    assert 1 in result


# ===========================================================================
# get_device_info
# ===========================================================================


def test_get_device_info_shots():
    dev = qp.device("default.qubit", wires=1, shots=100)
    info = [["device", None, dev]]
    queue = qp.queuing.AnnotatedQueue()
    _, num_shots, _ = uh.get_device_info(info, queue)
    assert num_shots == 100


def test_get_device_info_name():
    dev = qp.device("default.qubit", wires=1)

    @qp.qnode(dev)
    def circuit():
        return qp.expval(qp.PauliZ(0))

    info = [["module", 0, 0, 0, 0, [{"qnode": circuit}]]]
    queue = qp.queuing.AnnotatedQueue()
    device_name, _, _ = uh.get_device_info(info, queue)
    assert device_name == "default.qubit"


def test_get_device_info_wires():
    dev = qp.device("default.qubit", wires=3)
    info = [["device", None, dev]]
    queue = qp.queuing.AnnotatedQueue()
    _, _, num_wires = uh.get_device_info(info, queue)
    assert num_wires == 3


def test_get_device_info_wires_mid_circuit_measurement():
    dev = qp.device("default.qubit", wires=2)
    info = [["device", None, dev]]
    with qp.queuing.AnnotatedQueue() as queue:
        qp.Hadamard(wires=0)
        m = qp.measure(0)
        qp.cond(m, qp.PauliX)(wires=1)

    _, _, num_wires = uh.get_device_info(info, queue)
    assert num_wires == 2


def test_get_depth():
    cmd1 = Command("parent", 1, "parent()", "call", "classical", 0)
    cmd1.identifier = 1

    cmd2 = Command("child", 2, "child()", "call", "classical", 4)
    cmd2.identifier = 2
    cmd2.parent_id = 1

    cmd3 = Command("grandchild", 3, "grandchild()", "call", "classical", 8)
    cmd3.identifier = 3
    cmd3.parent_id = 2

    flat_commands = [cmd1, cmd2, cmd3]

    assert uh.get_depth(cmd1, flat_commands) == 0
    assert uh.get_depth(cmd2, flat_commands) == 1
    assert uh.get_depth(cmd3, flat_commands) == 2
