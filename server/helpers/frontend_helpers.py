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

import pennylane as qp
from pennylane.measurements import MeasurementValue, MidMeasureMP
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
import networkx as nx
from server import helpers
from server.helpers.placeholder_operation import PlaceholderOperation


def draw_circuit(commands, device_name, num_wires, num_shots, all_commands, postselect_overrides=None):
    """Draw a quantum circuit given a list of commands.

    Args:
        commands (List[Command Objects]): List of command objects.
        device_name (string): Name of the PennyLane device.
        num_wires (int): Number of wires in the circuit.
        num_shots (int): Number of shots for the device.
        postselect_overrides (dict{string: int}): mapping of mid circuit measurement command id -> postselect value (0 or 1) in debugger mode

    Returns:
        matplotlib.figure.Figure: Figure object of the circuit.
    """
    dev = qp.device(device_name, wires=num_wires or 1)

    @qp.set_shots(shots=num_shots or None)
    @qp.qnode(dev)
    def circuit():
        applied_measurements = set()

        for command in commands:
            if command.line_type == "call" or command.line_type == "scf":
                set_command_wires = set()
                all_mid_measurements = set()
                for c in command.children:
                    set_command_wires.update(helpers.get_wires_recursive(c))
                    all_mid_measurements.update(helpers.get_mid_measurements_recursive(c))
                    command.measurements = all_mid_measurements

                set_command_wires = sorted(set_command_wires)

                block_name = command.tree_node_name

                valid_measurements = [m for m in command.measurements if m in applied_measurements]

                if valid_measurements and (any(c.line_type == "mid_measurement" for c in helpers.get_sibling_commands(all_commands, command))) and len(set_command_wires) > 0:
                    with qp.QueuingManager.stop_recording():
                        func_op = PlaceholderOperation(wires=set_command_wires, op_name=block_name)
                    combined_meas_val = MeasurementValue(
                        measurements=valid_measurements,
                        processing_fn=lambda *results: all(results),
                    )
                    qp.ops.Conditional(combined_meas_val, func_op)
                else:
                    if len(set_command_wires) > 0:
                        PlaceholderOperation(wires=set_command_wires, op_name=block_name)

            elif command.quantum_or_classical == "quantum" and type(command.code_line) != str:
                if isinstance(command.code_line, list):
                    terminal_measurement = command.code_line[0]
                    meas_value = getattr(terminal_measurement, "mv", None)
                    if meas_value:
                        meas_values = meas_value if isinstance(meas_value, list) else [meas_value]
                        referenced_measurements = [m for mv in meas_values for m in mv.measurements]
                        if not all(m in applied_measurements for m in referenced_measurements):
                            type(terminal_measurement)(wires=terminal_measurement.wires)
                            continue
                    qp.apply(terminal_measurement)
                    continue

                elif command.line_type == "mid_measurement":
                    qp.apply(command.code_line)
                    applied_measurements.add(command.code_line)
                    continue

                elif command.line_type == "cond":
                    valid_measurements = [m for m in command.code_line.meas_val.measurements if m in applied_measurements]
                    
                    new_meas_val = MeasurementValue(
                        measurements=valid_measurements,
                        processing_fn=command.code_line.meas_val.processing_fn,
                    )
                    qp.ops.Conditional(new_meas_val, command.code_line.base)
                    continue

                elif helpers.unwrap_to_conditional(command.code_line) is not None:
                    inner_cond = helpers.unwrap_to_conditional(command.code_line)
                    new_meas_val = MeasurementValue(
                        measurements=[],
                        processing_fn=lambda: True,
                    )
                    qp.ops.Conditional(new_meas_val, inner_cond.base)
                    continue

                else:
                    qp.apply(command.code_line)

        return

    fig = qp.draw_mpl(circuit, decimals=2)()[0]
    plt.close(fig)

    return fig


def generate_networkx_command_tree(command, tree):
    """Recursively generates a command tree structure and returns a networkX DiGraph object.

    Args:
        command (Command Object): The first command (the root node of the tree) that runs
        tree (NetworkX DiGraph): A tree object that gets populated with all the commands

    Returns:
        tree (NetworkX DiGraph): Populated tree object
    """
    visualized_line_types = ["scf", "call", "mid_measurement", "cond", "transform"]

    if ((command.line_type in visualized_line_types or command.quantum_or_classical == "quantum") and len(helpers.get_wires_recursive(command)) > 0) or command.line_type == "measurement":
        tree.add_node(command, **vars(command))

    for child in command.children:
        if ((child.line_type in visualized_line_types or child.quantum_or_classical == "quantum") and len(helpers.get_wires_recursive(child)) > 0) or child.line_type == "measurement":
            tree.add_edge(command, child)
            generate_networkx_command_tree(child, tree)

    return tree


def dim_all_nodes(commands):
    """Updates the node_dimmed attribute on each command to false.

    Args:
        commands (List[Command Objects]): List of command objects, each may have children.
    """
    for command in commands:
        command.node_dimmed = True


def _command_json_fields(node, attrs):
    """Builds the JSON-serializable field dict shared by both graph serializers.

    Args:
        node (Command Object): the command whose identifier/children should be serialized
        attrs (dict): the command's attributes (e.g. from nx node data or vars(command))
    Returns:
        a dict of JSON-serializable fields for this node
    """
    return {
        "id": node.identifier,
        "parent_function": attrs.get("parent_function"),
        "line_number": attrs.get("line_number"),
        "code_line": str(attrs.get("code_line", "")),
        "line_type": attrs.get("line_type"),
        "quantum_or_classical": attrs.get("quantum_or_classical"),
        "children": [c.identifier for c in (attrs.get("children") or [])],
        "arguments": attrs.get("arguments"),
        "tree_node_name": attrs.get("tree_node_name"),
        "subtree_circuit_img": attrs.get("subtree_circuit_img"),
        "node_dimmed": attrs.get("node_dimmed"),
        "active_debug": attrs.get("active_debug"),
        "visible": attrs.get("visible", False),
        "parent_id": attrs.get("parent_id"),
        "output": attrs.get("output"),
        "condition_context": attrs.get("condition_context"),
        "is_mid_measure": attrs.get("is_mid_measure", False),
        "measurement_id": (
            str(attrs.get("mid_measurement_index"))
            if attrs.get("line_type") == "mid_measurement"
            and attrs.get("mid_measurement_index") is not None
            else None
        ),
        "postselect_value": attrs.get("postselect_value"),
        "mid_measurement_index": attrs.get("mid_measurement_index"),
    }


def jsonify_graph_for_frontend(graph):
    """Convert a NetworkX graph with Command nodes to a JSON-serializable dictionary.

    Args:
        graph (nx.DiGraph): a nx tree that we want to convert into a JSON-serializable dictionary
    Returns:
        a dictionary of JSON-serializable nodes and edges
    """
    nodes = [_command_json_fields(node, attrs) for node, attrs in graph.nodes(data=True)]
    edges = [{"source": u.identifier, "target": v.identifier} for u, v in graph.edges()]

    return {"nodes": nodes, "edges": edges}


def jsonify_flat_commands_for_frontend(flat_commands):
    """Convert a flat list of Command objects (e.g. from helpers.flatten_tree) into
    the same JSON-serializable {nodes, edges} shape as jsonify_graph_for_frontend,
    but including every command rather than only the ones visible in the tree.

    Args:
        flat_commands (List[Command Object]): every command in the tree, in any order
    Returns:
        a dictionary of JSON-serializable nodes and edges
    """
    nodes = [_command_json_fields(command, vars(command)) for command in flat_commands]
    edges = [
        {"source": command.parent_id, "target": command.identifier}
        for command in flat_commands
        if command.parent_id is not None
    ]

    return {"nodes": nodes, "edges": edges}


def get_graph_data(root_command, flat_commands=None):
    """Get the graph data used for the front end: the full command tree, with each
    node tagged with whether it's visible in the rendered command-tree visualization.

    Args:
        root_command (Command Object): The root command of the tree to collect the graph data of.
        flat_commands (List[Command Object], optional): every command to include in the output
            Defaults to a fresh flatten of root_command.children if not provided.
    Returns:
        graph_data(dict{str: List[dict]}): A jsonified dictionary of every command in the
        tree.
    """
    nx_command_tree = generate_networkx_command_tree(root_command, nx.DiGraph())
    visible_ids = {command.identifier for command in nx_command_tree.nodes()}

    if flat_commands is None:
        flat_commands = helpers.flatten_tree(root_command)
    for command in flat_commands:
        command.visible = command.identifier in visible_ids

    return jsonify_flat_commands_for_frontend(flat_commands)
