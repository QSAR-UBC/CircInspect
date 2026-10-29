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
Tests for server/helpers/frontend_helpers.py.
"""

import matplotlib
import matplotlib.figure
import networkx as nx
import pennylane as qp

matplotlib.use("Agg")

from server.command import Command
from server.helpers import frontend_helpers as fh


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


def make_quantum_cmd(op, line_type="line", identifier=0, tree_node_name=None):
    """Factory for a quantum Command wrapping a PennyLane operation."""
    cmd = make_cmd(quantum_or_classical="quantum", line_type=line_type)
    cmd.code_line = op
    cmd.identifier = identifier
    cmd.tree_node_name = tree_node_name or op.label()
    return cmd


# ===========================================================================
# dim_all_nodes
# ===========================================================================


def test_dim_all_nodes_single_command():
    """A single command's node_dimmed should be set to True."""
    cmd = make_cmd()
    cmd.node_dimmed = False
    fh.dim_all_nodes([cmd])
    assert cmd.node_dimmed is True


def test_dim_all_nodes_multiple_commands():
    """All commands in the list should have node_dimmed set to True."""
    cmds = [make_cmd() for _ in range(4)]
    for c in cmds:
        c.node_dimmed = False
    fh.dim_all_nodes(cmds)
    assert all(c.node_dimmed is True for c in cmds)


def test_dim_all_nodes_already_true_stays_true():
    """Commands already dimmed stay dimmed after the call."""
    cmd = make_cmd()
    cmd.node_dimmed = True
    fh.dim_all_nodes([cmd])
    assert cmd.node_dimmed is True


def test_dim_all_nodes_empty_list():
    """An empty list should not raise any exception."""
    fh.dim_all_nodes([])


# ===========================================================================
# generate_networkx_command_tree
# ===========================================================================


def test_generate_networkx_command_tree_root_added():
    """The root command should appear as a node in the returned DiGraph."""
    root = make_cmd(parent_function="circuit", line_number=1, line_type="call")
    root.identifier = 0
    # generate_networkx_command_tree only includes nodes that touch a real
    # quantum wire (directly or via a descendant), so give root a quantum child.
    root.children = [make_quantum_cmd(qp.Hadamard(0), identifier=1)]
    Tree = fh.generate_networkx_command_tree(root, nx.DiGraph())
    assert root in Tree.nodes


def test_generate_networkx_command_tree_node_attributes():
    """Node attributes on the root should match the Command fields."""
    root = make_cmd(
        parent_function="circuit",
        line_number=5,
        code_line="qp.H(0)",
        line_type="line",
        quantum_or_classical="quantum",
    )
    root.identifier = 0
    root.tree_node_name = "H"
    # root's own code_line is a plain string (kept so the assertions below can
    # check it), so give it a quantum child to satisfy the wires filter.
    root.children = [make_quantum_cmd(qp.Hadamard(0), identifier=1)]
    Tree = fh.generate_networkx_command_tree(root, nx.DiGraph())
    attrs = Tree.nodes[root]
    assert attrs["parent_function"] == "circuit"
    assert attrs["line_number"] == 5
    assert attrs["code_line"] == "qp.H(0)"
    assert attrs["line_type"] == "line"
    assert attrs["quantum_or_classical"] == "quantum"
    assert attrs["tree_node_name"] == "H"


def test_generate_networkx_command_tree_child_added():
    """Children of the root must also be present as nodes."""
    root = make_cmd(line_number=1, quantum_or_classical="quantum")
    root.identifier = 0
    child = make_quantum_cmd(qp.Hadamard(0), identifier=1)
    root.children = [child]
    tree = fh.generate_networkx_command_tree(root, nx.DiGraph())
    assert child in tree.nodes


def test_generate_networkx_command_tree_edge_created():
    """An edge from the root to its child must be present in the graph."""
    root = make_cmd(line_number=1, line_type="call")
    root.identifier = 0
    child = make_quantum_cmd(qp.Hadamard(0), identifier=1)
    root.children = [child]
    Tree = fh.generate_networkx_command_tree(root, nx.DiGraph())
    assert (root, child) in Tree.edges


def test_generate_networkx_command_tree_recurses_into_grandchildren():
    """generate_networkx_command_tree must recurse — grandchildren should also
    appear as nodes with an edge from their parent."""
    root = make_cmd(line_number=1, line_type="call")
    root.identifier = 0
    child = make_cmd(line_number=2, line_type="scf")
    child.identifier = 1
    grandchild = make_quantum_cmd(qp.Hadamard(0), identifier=2)
    child.children = [grandchild]
    root.children = [child]
    tree = fh.generate_networkx_command_tree(root, nx.DiGraph())
    assert grandchild in tree.nodes
    assert (child, grandchild) in tree.edges


def test_generate_networkx_command_tree_no_children_no_edges():
    """A leaf command (no children) should produce a node but no outgoing edges."""
    leaf = make_quantum_cmd(qp.Hadamard(0), identifier=0)
    tree = fh.generate_networkx_command_tree(leaf, nx.DiGraph())
    assert leaf in tree.nodes
    assert len(list(tree.edges)) == 0


def test_generate_networkx_command_tree_wireless_measurement_included():
    """Terminal measurements like `return qp.probs()`, `qp.state()`, and
    `qp.sample()` (no explicit wires) have an empty wire set, but must still
    be included in the tree since line_type == "measurement" is whitelisted
    regardless of wires."""
    root = make_cmd(line_number=1, line_type="call")
    root.identifier = 0
    measurement = make_cmd(line_number=2, line_type="measurement", quantum_or_classical="quantum")
    measurement.identifier = 1
    measurement.code_line = [qp.probs()]
    root.children = [measurement]

    tree = fh.generate_networkx_command_tree(root, nx.DiGraph())

    assert measurement in tree.nodes
    assert (root, measurement) in tree.edges


# ===========================================================================
# jsonify_graph_for_frontend
# ===========================================================================


def _build_simple_graph(parent_identifier=0, child_identifier=1):
    """Helper: returns a 2-node DiGraph (parent → child) ready for jsonification."""
    parent = make_cmd(parent_function="circuit", line_number=1, line_type="call")
    parent.identifier = parent_identifier
    parent.tree_node_name = "circuit"

    # A real op (rather than a plain string code_line) is needed so the child
    # touches an actual wire and passes generate_networkx_command_tree's filter.
    child = make_quantum_cmd(qp.Hadamard(0), identifier=child_identifier)
    child.parent_function = "circuit"
    child.line_number = 2
    child.parent_id = parent_identifier
    parent.children = [child]

    return fh.generate_networkx_command_tree(parent, nx.DiGraph())


def test_jsonify_graph_returns_nodes_and_edges_keys():
    """The returned dict must contain 'nodes' and 'edges' top-level keys."""
    graph = _build_simple_graph()
    result = fh.jsonify_graph_for_frontend(graph)
    assert "nodes" in result
    assert "edges" in result


def test_jsonify_graph_nodes_have_correct_id():
    """Each node entry must have an 'id' field equal to command.identifier."""
    graph = _build_simple_graph(parent_identifier=0, child_identifier=1)
    result = fh.jsonify_graph_for_frontend(graph)
    ids = {n["id"] for n in result["nodes"]}
    assert 0 in ids
    assert 1 in ids


def test_jsonify_graph_node_fields_present():
    """Every node dict must contain all expected field keys."""
    required_keys = {
        "id",
        "parent_function",
        "line_number",
        "code_line",
        "line_type",
        "quantum_or_classical",
        "children",
        "arguments",
        "tree_node_name",
        "subtree_circuit_img",
        "node_dimmed",
        "active_debug",
        "parent_id",
        "output",
        "condition_context",
        "is_mid_measure",
        "postselect_value",
        "mid_measurement_index",
    }
    graph = _build_simple_graph()
    result = fh.jsonify_graph_for_frontend(graph)
    for node in result["nodes"]:
        assert required_keys.issubset(node.keys()), f"Missing keys: {required_keys - node.keys()}"


def test_jsonify_graph_children_field_contains_identifiers():
    """The 'children' field of a parent node must list its child identifiers, not
    Command objects."""
    graph = _build_simple_graph(parent_identifier=10, child_identifier=20)
    result = fh.jsonify_graph_for_frontend(graph)
    parent_node = next(n for n in result["nodes"] if n["id"] == 10)
    assert parent_node["children"] == [20]


def test_jsonify_graph_edges_have_source_and_target():
    """Each edge dict must have 'source' and 'target' fields holding identifiers."""
    graph = _build_simple_graph(parent_identifier=0, child_identifier=1)
    result = fh.jsonify_graph_for_frontend(graph)
    assert len(result["edges"]) == 1
    edge = result["edges"][0]
    assert edge["source"] == 0
    assert edge["target"] == 1


def test_jsonify_graph_empty_graph():
    """An empty graph should return empty nodes and edges lists without raising errors."""
    result = fh.jsonify_graph_for_frontend(nx.DiGraph())
    assert result == {"nodes": [], "edges": []}


# ===========================================================================
# jsonify_flat_commands_for_frontend
# ===========================================================================


def _build_flat_commands_with_classical_child():
    """Helper: root -> [classical_child, quantum_child], as a flat list (not a graph)."""
    root = make_cmd(parent_function="circuit", line_number=1, line_type="call")
    root.identifier = 0
    root.tree_node_name = "circuit"

    classical_child = make_cmd(parent_function="circuit", line_number=2, line_type="line", quantum_or_classical="classical")
    classical_child.identifier = 1
    classical_child.parent_id = 0

    quantum_child = make_quantum_cmd(qp.Hadamard(0), identifier=2)
    quantum_child.parent_function = "circuit"
    quantum_child.line_number = 3
    quantum_child.parent_id = 0

    root.children = [classical_child, quantum_child]
    return [root, classical_child, quantum_child]


def test_jsonify_flat_commands_includes_every_command():
    """Unlike jsonify_graph_for_frontend, every command must appear in nodes,
    including the classical one that generate_networkx_command_tree would drop."""
    flat_commands = _build_flat_commands_with_classical_child()
    result = fh.jsonify_flat_commands_for_frontend(flat_commands)
    ids = {n["id"] for n in result["nodes"]}
    assert ids == {0, 1, 2}


def test_jsonify_flat_commands_edges_reflect_parent_id():
    """Edges must be built from each command's parent_id, not tree membership."""
    flat_commands = _build_flat_commands_with_classical_child()
    result = fh.jsonify_flat_commands_for_frontend(flat_commands)
    edges = {(e["source"], e["target"]) for e in result["edges"]}
    assert edges == {(0, 1), (0, 2)}


def test_jsonify_flat_commands_root_has_no_edge():
    """A command with parent_id=None (the root) must not produce an edge."""
    flat_commands = _build_flat_commands_with_classical_child()
    result = fh.jsonify_flat_commands_for_frontend(flat_commands)
    targets = {e["target"] for e in result["edges"]}
    assert 0 not in targets


def test_jsonify_flat_commands_visible_field_passes_through():
    """The 'visible' field on each node must reflect command.visible directly."""
    flat_commands = _build_flat_commands_with_classical_child()
    root, classical_child, quantum_child = flat_commands
    root.visible = True
    classical_child.visible = False
    quantum_child.visible = True

    result = fh.jsonify_flat_commands_for_frontend(flat_commands)
    visible_by_id = {n["id"]: n["visible"] for n in result["nodes"]}
    assert visible_by_id == {0: True, 1: False, 2: True}


def test_jsonify_flat_commands_empty_list():
    """An empty flat list should return empty nodes and edges lists."""
    result = fh.jsonify_flat_commands_for_frontend([])
    assert result == {"nodes": [], "edges": []}


# ===========================================================================
# get_graph_data
# ===========================================================================


def test_get_graph_data_graph_data_has_nodes_and_edges():
    """The first element (graph_data) must have 'nodes' and 'edges' keys."""
    root = make_cmd(line_type="call", line_number=1)
    root.identifier = 0
    graph_data = fh.get_graph_data(root)
    assert "nodes" in graph_data
    assert "edges" in graph_data


def test_get_graph_data_marks_classical_nodes_not_visible():
    """graph_data must include every command (classical included, e.g. for the
    debugger to step through), but only mark nodes that pass the tree-visibility
    filter as visible=True — a plain classical 'line' child stays present but
    visible=False, while a quantum node is visible=True."""
    root = make_cmd(line_type="call", line_number=1)
    root.identifier = 0

    classical_child = make_cmd(line_type="line", quantum_or_classical="classical")
    classical_child.identifier = 1
    quantum_child = make_cmd(line_type="line", quantum_or_classical="quantum")
    quantum_child.identifier = 2
    quantum_child.code_line = qp.Hadamard(0)

    root.children = [classical_child, quantum_child]
    graph_data = fh.get_graph_data(root)

    nodes_by_id = {n["id"]: n for n in graph_data["nodes"]}
    assert 1 in nodes_by_id  # classical node still present, for debugger stepping
    assert 2 in nodes_by_id  # quantum node present
    assert nodes_by_id[1]["visible"] is False
    assert nodes_by_id[2]["visible"] is True


# ===========================================================================
# draw_circuit
# ===========================================================================


def test_draw_circuit_returns_figure_for_quantum_command():
    """draw_circuit should return a matplotlib Figure without raising errors when given
    a simple quantum gate command."""

    cmd = make_quantum_cmd(qp.Hadamard(0), line_type="line", identifier=0)

    fig = fh.draw_circuit([cmd], "default.qubit", 1, 0, [])
    assert isinstance(fig, matplotlib.figure.Figure)


def test_draw_circuit_empty_commands_no_error():
    """An empty command list should produce a valid (empty) circuit figure."""

    fig = fh.draw_circuit([], "default.qubit", 1, 0, [])
    assert isinstance(fig, matplotlib.figure.Figure)


def test_draw_circuit_multiple_quantum_gates():
    """A list of multiple quantum gate commands should render without error."""

    h_cmd = make_quantum_cmd(qp.Hadamard(0), identifier=0)
    x_cmd = make_quantum_cmd(qp.PauliX(1), identifier=1)

    fig = fh.draw_circuit([h_cmd, x_cmd], "default.qubit", 2, 0, [])
    assert isinstance(fig, matplotlib.figure.Figure)
