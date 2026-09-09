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

import os
import time
import traceback
import multiprocessing
import queue
import importlib.metadata
import dill as pickle
from flask import Flask, request, jsonify
from server.sandbox.quantum_stack_trace import QuantumStackTrace
from server import helpers

# Robustness guard against a hung/oversized circuit, not a security boundary.
EXEC_TIMEOUT_SECONDS = float(os.environ.get("CIRCINSPECT_EXEC_TIMEOUT_SECONDS", 30))
EXEC_MEMORY_LIMIT_BYTES = int(os.environ.get("CIRCINSPECT_EXEC_MEMORY_MB", 4096)) * 1024 * 1024


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
        helpers.update_command_images(qnode, device_name, num_wires, num_shots, flat_commands, postselect_overrides, is_qnode=True)

    graph_data = helpers.get_graph_data(root_command, flat_commands)

    initial_circuit_img_base_64_byte_code = helpers.get_image_bs64_bytecode(
        helpers.draw_circuit(
            root_command.children[0].children,
            device_name, num_wires, num_shots, flat_commands, postselect_overrides,
        )
    )

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


def _execute_in_child(code, postselect_overrides, result_queue):
    """Entry point for the isolated child process. Runs process_code() and
    ships the result back to the parent via dill. The memory cap is enforced
    by the parent polling this process's actual resident memory (see
    run_process_code_isolated) rather than a virtual-address-space rlimit --
    JIT runtimes like JAX/XLA (used by pennylane-catalyst) reserve several GB
    of virtual address space at startup regardless of how much memory the
    circuit actually uses, so RLIMIT_AS produces false positives here.
    """
    result, root_command, flat_commands = process_code(code, postselect_overrides)
    result_queue.put(pickle.dumps((result, root_command, flat_commands)))


def _get_rss_bytes(pid):
    """Reads a process's current resident set size (actual physical memory
    in use) from /proc. Returns 0 if the process is gone or unreadable.
    """
    try:
        with open(f"/proc/{pid}/status") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1]) * 1024
    except (FileNotFoundError, ProcessLookupError, ValueError):
        pass
    return 0


def run_process_code_isolated(code, postselect_overrides):
    """Runs process_code() in a separate process with a wall-clock timeout and
    a memory cap, so a buggy circuit (infinite loop, unbounded allocation)
    can't hang or crash the shared dev server. This is a robustness guard,
    not a security boundary.

    Returns:
        Same shape as process_code(): (result_dict, root_command, flat_commands).
    """
    ctx = multiprocessing.get_context("fork")
    result_queue = ctx.Queue()
    proc = ctx.Process(target=_execute_in_child, args=(code, postselect_overrides, result_queue))
    proc.start()

    # Drain the queue instead of proc.join()-ing first: a result larger than
    # the pipe's OS buffer would otherwise deadlock the child on Queue.put().
    deadline = time.time() + EXEC_TIMEOUT_SECONDS
    payload = None
    memory_exceeded = False
    while payload is None and time.time() < deadline:
        try:
            payload = result_queue.get(timeout=0.1)
        except queue.Empty:
            if not proc.is_alive():
                break
            if _get_rss_bytes(proc.pid) > EXEC_MEMORY_LIMIT_BYTES:
                memory_exceeded = True
                break

    if payload is not None:
        proc.join(5)
        if proc.is_alive():
            proc.terminate()
            proc.join()
        return pickle.loads(payload)

    if proc.is_alive():
        proc.terminate()
        proc.join(5)
        if proc.is_alive():
            proc.kill()
            proc.join()
        if memory_exceeded:
            return {
                "error": [
                    "Circuit execution exceeded the "
                    f"{EXEC_MEMORY_LIMIT_BYTES // (1024 * 1024)}MB memory limit.",
                    "line unknown",
                ]
            }, None, None
        return {"error": [f"Execution timed out after {EXEC_TIMEOUT_SECONDS:.0f} seconds.", "line unknown"]}, None, None

    # Process exited without ever producing a result -- crashed unexpectedly.
    proc.join()
    return {"error": ["Circuit execution failed unexpectedly.", "line unknown"]}, None, None


def safe_version(pkg):
    try:
        return importlib.metadata.version(pkg)
    except Exception:
        return "unavailable"


_cached_sessions = {}

app = Flask(__name__)
app.json.default = helpers.json_default


@app.route("/health", methods=["GET"])
def health():
    """Liveness probe used to confirm the server is ready."""
    return "ok", 200


@app.route("/library_version")
def version():
    return jsonify(
        {
            "pennylane": safe_version("pennylane"),
            "numpy": safe_version("numpy"),
            "autograd": safe_version("autograd"),
            "jax": safe_version("jax"),
            "torch": safe_version("torch"),
            "tensorflow": safe_version("tensorflow"),
        }
    )


@app.route("/visualizeCircuit", methods=["POST"])
def visualize_circuit():
    """Endpoint that handles code execution requests from the client.

    Accepts a JSON payload with the user's code and any postselect overrides.

    Returns:
        Response: A Flask response containing the JSON of the execution trace and results.
    """
    body = request.get_json(force=True, silent=True)
    if not body:
        return jsonify({"error": ["No code provided.", "line unknown"]}), 400

    code_received = body.get("data", "")
    postselect_overrides = body.get("postselect_overrides") or {}
    session_id = body.get("session_id") or "default"

    restricted_code = helpers.check_for_restricted_code(code_received)
    if restricted_code != "":
        return jsonify({"error": restricted_code})

    exec_start = time.time()
    result, root_command, flat_commands = run_process_code_isolated(code_received, postselect_overrides)
    exec_time = time.time() - exec_start

    if root_command is not None:
        _cached_sessions[session_id] = {
            "root_command": root_command,
            "device_name": result.get("device_name"),
            "num_shots": result.get("num_shots"),
            "num_wires": result.get("num_wires"),
            "flat_commands": flat_commands,
        }

    result["exec_time"] = exec_time
    return jsonify(result)


@app.route("/debugOutput", methods=["POST"])
def debug_output():
    """Endpoint to render the circuit up to a certain debug index.

    Accepts:
        node_ids: list of command identifiers to include in render
        transform_root_idx: the index of the root transform being viewed in the list of flat commands
        postselect_overrides: dictionary of postselect overrides
    """
    body = request.get_json(force=True, silent=True)
    if not body:
        return jsonify({"error": "No body provided"}), 400

    node_ids = set(body.get("node_ids", []))
    transform_root_idx = body.get("transform_root_idx")
    postselect_overrides = body.get("postselect_overrides", {})
    session_id = body.get("session_id") or "default"

    process_start_time = time.time()
    exec_time_list = []

    session = _cached_sessions.get(session_id)
    if session is None:
        return jsonify({"error": "No cached session available"}), 400

    root_command = session["root_command"]
    flat_commands = session["flat_commands"]
    device_name = session.get("device_name")
    num_shots = session.get("num_shots")
    num_wires = session.get("num_wires")

    # Find the last command in flat_commands order that is in node_ids
    last_cmd = helpers.get_command_by_identifier(flat_commands, max(node_ids))

    target_depth = helpers.get_depth(last_cmd, flat_commands)

    # Commands for circuit image: depth-filtered to current level
    active_commands = [
        cmd for cmd in flat_commands
        if cmd.identifier in node_ids and helpers.get_depth(cmd, flat_commands) == target_depth
    ]

    if not active_commands:
        return jsonify({
            "image": None,
            "circuit_output": "",
            "processing_time_no_exec_times": time.time() - process_start_time,
            "exec_times_list": exec_time_list,
        })

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
        exec_time_list.append(time.time() - exec_start)
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

    processing_time = time.time() - process_start_time - sum(exec_time_list)

    return jsonify({
        "image": circuit_img_base_64,
        "circuit_output": repr(circuit_output).replace("\n", "").replace(" ", ""),
        "processing_time_no_exec_times": processing_time,
        "exec_times_list": exec_time_list,
    })


if __name__ == "__main__":
    # Port 5000 matches client/package.json's dev-server proxy. threaded=True
    # so a long circuit execution doesn't block other requests.
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)
