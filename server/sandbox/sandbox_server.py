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

import sys
import time
import traceback
import dill as pickle
from flask import Flask, request, jsonify
from import_restrictor import ImportRestrictor
from quantum_stack_trace import QuantumStackTrace
from server import helpers


def _install_restrictions():
    """Installs module import restrictions onto the system path.

    Reads the allowed modules from the configured allowlist and injects an
    ImportRestrictor instance to block disallowed imports within the sandbox.
    """
    try:
        with open("/sandbox/allowed_modules.txt", "r") as f:
            allowed = frozenset(line.strip() for line in f if line.strip() and not line.lstrip().startswith("#"))
        sys.meta_path.insert(0, ImportRestrictor(allowed))
    except FileNotFoundError:
        raise FileNotFoundError("allowed_modules.txt not found in /sandbox")

_install_restrictions()


def process_code(code, postselect_overrides):
    """Processes, traces, and analyzes the user's quantum circuit code.

    Args:
        code (str): The Python code payload to execute.
        postselect_overrides (dict): Measurements forced to specific post-selection values.

    Returns:
        tuple(dict, Command, List[Command Object]): A comprehensive dictionary object
        with nodes, images, errors, and execution metrics; the root command of the
        processed tree; and the flattened list of every command in that tree. The
        latter two are None on any error path.
    """
    process_start_time = time.time()
    exec_time_list = []

    code = helpers.code_cleanup(code)

    # check for syntax errors
    trace, exec_time = run_trace(code)
    exec_time_list.append(exec_time)
    if not isinstance(trace, QuantumStackTrace):
        return {"error": trace}, None, None

    code_no_transforms = helpers.comment_out_transforms(code)
    method_names = helpers.get_method_names(code)
    qnode = trace.get_qnode()
    user_transforms = helpers.get_user_transforms(code, method_names, qnode)

    trace, exec_time_base = run_trace(code_no_transforms)
    exec_time_list.append(exec_time_base)
    if not isinstance(trace, QuantumStackTrace):
        return {"error": trace}, None, None

    if not trace.get_stack():
        return {"error": ["Please run exactly one QNode."]}, None, None

    annotated_queue = trace.get_stack()["commands"]
    device_name, num_shots, num_wires = helpers.get_device_info(trace.info, annotated_queue)

    root_command = helpers.generate_command_tree(
        trace.info, method_names, code_no_transforms, annotated_queue.queue
    )

    if root_command == ({"error": ["Please run exactly one quantum node."]}, None):
        error_result, _ = root_command
        return error_result, None, None

    if postselect_overrides:
        all_cmds = helpers.flatten_tree(root_command)
        helpers.apply_postselect_to_commands(all_cmds, postselect_overrides)
        ps_id_map = helpers.get_postselect_id_map(root_command, all_cmds)
        helpers.prune_unexecuted_commands(root_command, ps_id_map)

    root_command, flat_commands = helpers.get_full_tree(root_command, code, annotated_queue, user_transforms, method_names, globals())
    for qnode in root_command.children:
        try:
            qnode_output, exec_time = helpers.get_fcn_output_from_tree(qnode, device_name, num_shots, num_wires)
            qnode.output = repr(qnode_output).replace("\n", "").replace(" ", "")
        except (ValueError, ZeroDivisionError, TypeError) as e:
            return {"error": ["Invalid state: Post-selected measurement probability is 0"]}, None, None

        exec_time_list.append(exec_time)
        # Draw the qnode's own circuit image once here so it can be reused
        # below as the initial image, rather than rendering the identical
        # content a second time.
        qnode.subtree_circuit_img = helpers.get_image_bs64_bytecode(
            helpers.draw_circuit(
                qnode.children, device_name, num_wires, num_shots, flat_commands, postselect_overrides,
            )
        )
        helpers.update_command_images(qnode.children, device_name, num_wires, num_shots, flat_commands, postselect_overrides)

    graph_data = helpers.get_graph_data(root_command, flat_commands)

    initial_circuit_img_base_64_byte_code = root_command.children[0].subtree_circuit_img

    transform_details = list(helpers.get_transform_details(code))

    processing_time = time.time() - process_start_time - sum(exec_time_list)

    return {
        "name": root_command.parent_function,
        "id": root_command.identifier,
        "image": initial_circuit_img_base_64_byte_code,
        "line_number": root_command.line_number,
        "transform_details": transform_details,
        "device_name": device_name,
        "commands": pickle.dumps(root_command).hex(),
        "debug_index": -1,
        "num_wires": num_wires,
        "num_shots": num_shots,
        "processing_time_no_exec_times": processing_time,
        "exec_times_list": exec_time_list,
        "graph_data": graph_data,
    }, root_command, flat_commands


def run_trace(code):
    """Executes the given user code within the quantum stack trace context.

    Disables restricted builtins like open, exec, eval, and compile for safety.

    Args:
        code (str): The code to run.

    Returns:
        tuple: A tuple containing the QuantumStackTrace object (or an error list)
        and the total execution duration in seconds.
    """
    restricted_globals = {
        "__builtins__": __builtins__.copy() if isinstance(__builtins__, dict) else __builtins__.__dict__.copy()
    }
    for fn in ("open", "exec", "eval", "compile"):
        restricted_globals["__builtins__"].pop(fn, None)

    try:
        exec_start = time.time()
        with QuantumStackTrace() as trace:
            exec(code, restricted_globals)
        return trace, time.time() - exec_start
    except Exception:
        exceptiondata = traceback.format_exc().splitlines()
        exceptionarray = [exceptiondata[-1]] + exceptiondata[1:-1]
        line_num = ""
        for e in exceptionarray:
            if '"<string>"' in e:
                line_num = e.split(",")[1]
        return [exceptionarray[0], line_num], 0

_cached_session = {}

app = Flask(__name__)
app.json.default = helpers.json_default

@app.route("/health", methods=["GET"])
def health():
    """Liveness probe used by the host to confirm the server is ready."""
    return "ok", 200


@app.route("/execute", methods=["POST"])
def execute():
    """Endpoint that handles code execution requests from the main execserver.

    Accepts a JSON payload indicating source code, active transforms, and postselect overrides.

    Returns:
        Response: A Flask response containing the JSON of the execution trace and results.
    """
    body = request.get_json(force=True, silent=True)
    if not body or "code" not in body:
        return jsonify({"error": ["No code provided.", "line unknown"]}), 400

    result, root_command, flat_commands = process_code(
        body["code"],
        body.get("postselect_overrides") or {},
    )
    if root_command is not None:
        _cached_session["root_command"] = root_command
        _cached_session["device_name"] = result.get("device_name")
        _cached_session["num_shots"] = result.get("num_shots")
        _cached_session["num_wires"] = result.get("num_wires")
        _cached_session["flat_commands"] = flat_commands
    return jsonify(result)

@app.route("/debugOutput", methods=["POST"])
def debug_output():
    """Endpoint to render the circuit up to a certain debug index.
    
    Accepts:
        node_ids: list of command identifiers to include in render
        transform_root_idx: the index of the root transform being viewed in the list of flat commands
        postselect_overrides: dictionary of postselect overrides
    """
    process_start_time = time.time()

    body = request.get_json(force=True, silent=True)
    if not body:
        return jsonify({"error": "No body provided"}), 400

    node_ids = set(body.get("node_ids", []))
    transform_root_idx = body.get("transform_root_idx")
    postselect_overrides = body.get("postselect_overrides", {})

    if "root_command" not in _cached_session:
        return jsonify({"error": "No cached session available"}), 400

    root_command = _cached_session["root_command"]
    flat_commands = _cached_session["flat_commands"]
    device_name = _cached_session.get("device_name")
    num_shots = _cached_session.get("num_shots")
    num_wires = _cached_session.get("num_wires")

    # Find the last command in flat_commands order that is in node_ids
    last_cmd = helpers.get_command_by_identifier(flat_commands, max(node_ids))

    target_depth = helpers.get_depth(last_cmd, flat_commands)

    # Commands for circuit image: depth-filtered to current level
    active_commands = [
        cmd for cmd in flat_commands
        if cmd.identifier in node_ids and helpers.get_depth(cmd, flat_commands) == target_depth
    ]

    if not active_commands:
        return jsonify({"image": None, "circuit_output": ""})

    # Commands for circuit output
    output_commands = []
    for cmd in flat_commands:
        if cmd.identifier == last_cmd.identifier:
            output_commands.append(cmd)
            break
        if transform_root_idx is None or cmd.parent_id == flat_commands[transform_root_idx].identifier or cmd.identifier == flat_commands[transform_root_idx].identifier:
            output_commands.append(cmd)

    # Find final measurement of the entire circuit
    final_measurement = []
    for cmd in reversed(flat_commands):
        if cmd.line_type == "measurement":
            final_measurement = cmd.code_line
            if type(final_measurement) is not list:
                final_measurement = [final_measurement]
            break

    try:
        exec_start = time.time()
        circuit_output = helpers.run_pennylane_commands(
            output_commands,
            device_name,
            num_shots,
            num_wires,
            final_measurement,
            last_cmd.identifier,
        )
        exec_time = time.time() - exec_start
    except (ValueError, ZeroDivisionError, TypeError) as e:
        if "infs or NaNs" in str(e) or "zero-size" in str(e):
            return jsonify({"error": "Invalid state: Post-selected measurement probability is 0"}), 400
        else:
            return jsonify({"error": str(e)}), 400

    try:
        circuit_img_base_64 = helpers.get_image_bs64_bytecode(
            helpers.draw_circuit(active_commands, device_name, num_wires, num_shots, flat_commands, postselect_overrides)
        )
    except Exception as e:
        print(f"Error creating circuit image: {e}", flush=True)
        circuit_img_base_64 = None

    processing_time = time.time() - process_start_time - exec_time

    return jsonify({
        "image": circuit_img_base_64,
        "circuit_output": repr(circuit_output).replace("\n", "").replace(" ", ""),
        "processing_time_no_exec_times": processing_time,
        "exec_times_list": [exec_time],
    })



if __name__ == "__main__":
    # Runs the Flask dev server — port 8080, all interfaces inside the container.
    # The host only reaches this via the 127.0.0.1-bound published port.
    app.run(host="0.0.0.0", port=8080, debug=False, use_reloader=False)