# Copyright 2025 UBC Quantum Software and Algorithms Research Lab

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
This module is the flask application for code execution.
To mitigate some security risks, we divided our backend
to two seperate flask apps that are meant to run on
two completely seperate servers. This one includes the
arbitrary code execution, so it is seperated from the
flask application that directly interacts with the user
and the database.
"""

import time
import json
import traceback
from multiprocessing import Process, Pipe
import resource
from flask import Flask, request, jsonify, Response
import dill as pickle
from server.magically_trace_stack import MagicallyTraceStack
from server import helpers
import pennylane as qml


def get_trace(code):
    """Execute user code and trace the result to get more information

    Args:
        code (string): user code

    Returns
        1. Code trace
        2. Time it took to execute code with tracing
    """
    lines_of_quantum_code = helpers.get_quantum_lines(code.split("\n"))
    exec_time_start = time.time()
    try:
        with MagicallyTraceStack(lines_of_quantum_code) as trace:
            exec(code, globals())
    except Exception:
        exceptiondata = traceback.format_exc().splitlines()
        exceptionarray = [exceptiondata[-1]] + exceptiondata[1:-1]
        line_num = ""
        for e in exceptionarray:
            if '"<string>"' in e:
                line_num = e.split(",")[1]
        return [exceptionarray[0], line_num], 0
    return trace, time.time() - exec_time_start


def code_cleanup(code):
    """Cleans up the new line characters inside qml operation parameters and cleans up comments

    Args:
        code (String): Code to clean up

    Returns:
        String: Code after new line characters and comments have been removed
    """
    newline_cleaned_up_code = helpers.newline_cleanup(code)
    commented_cleaned_up_code = helpers.comment_cleanup(newline_cleaned_up_code)
    return commented_cleaned_up_code


def get_wires(annotated_queue):
    """Get the wires used in the code

    Args:
        annotated_queue (Object): Object to maintain basic queue of operations

    Returns:
        Set: the set of wires used
    """
    set_wires = set()
    for j in annotated_queue.queue:
        if j.wires is None:
            set_wires.update()
        set_wires.update(j.wires)

    return set_wires


def initialize_resource_limits():
    """Initialize resource limits"""
    soft_limit, hard_limit = resource.getrlimit(resource.RLIMIT_AS)
    resource.setrlimit(resource.RLIMIT_AS, (2147483648, hard_limit))  # 2GB


def get_transform_results_after_uncommenting_transforms(
    commands, code, code_received_transforms_commented_arr, exec_time_list, main_fcn_output
):
    """Get the circuit output and visualization of each transform

    Args:
        commands (Object): command objkect
        code (String): the code user inputs
        code_received_transforms_commented_arr (Array): an array of each line of the code with transforms commented
        exec_time_list (Array): list of execution times
        main_fcn_output (String): output of the qnode as a string

    Returns:
        Array: qnode output and visualization after uncommenting transforms
    """
    transform_results_after_uncommenting_transforms = []
    transform_names_and_line_numbers = helpers.get_transform_details(
        code, starting_idx=commands[-1].identifier + 1
    )
    i = len(transform_names_and_line_numbers) - 1

    while i >= 0:
        t = transform_names_and_line_numbers[i]
        code_received_transforms_commented_arr[t[1] - 1] = code_received_transforms_commented_arr[
            t[1] - 1
        ][1:]
        code_received_transforms_commented_str = "\n".join(code_received_transforms_commented_arr)
        exec_time = time.time()
        exec(code_received_transforms_commented_str, globals())
        exec_time_list.append(time.time() - exec_time)
        _, exec_time = get_trace(code_received_transforms_commented_str)
        exec_time_list.append(exec_time)

        transform_eval = (helpers.get_image_bs64_bytecode(circuit_img[0]), res)
        eval_str = ""
        for char in str(main_fcn_output):
            if char == " ":
                eval_str = eval_str + char

            if char != "\n":
                eval_str = eval_str + char

        transform_results_after_uncommenting_transforms.append(
            [
                transform_eval[0],
                repr(transform_eval[1]).replace("\n", "").replace(" ", ""),
                t[0],
                t[1] + 1 + commands[-1].identifier,
                t[1],
            ]
        )
        i -= 1

    return transform_results_after_uncommenting_transforms


def add_image_commands_to_code_array(code_received_transforms_commented_arr, commands):
    """Add image commands to code array

    Args:
        code_received_transforms_commented_arr (Array): an array of code lines where transforms are commented
        commands (Array): an array of command objects
    """
    i = len(code_received_transforms_commented_arr) - 1
    while i >= 0:
        if commands[0].function in code_received_transforms_commented_arr[i]:
            code_received_transforms_commented_arr.append(
                "res = " + code_received_transforms_commented_arr[i]
            )
            img_command = "circuit_img = qml.draw_mpl("
            first_bracket_reached = False
            for char in code_received_transforms_commented_arr[i]:
                if char == "(" and first_bracket_reached is False:
                    first_bracket_reached = True
                    img_command = img_command + ")"
                    img_command = img_command + "("
                else:
                    img_command = img_command + char

            code_received_transforms_commented_arr.append(img_command)
            break
        i -= 1


def get_information_of_subroutines(
    commands_to_execute_for_identifier, commands, device_name, num_wires, num_shots
):
    """Get name, circuit visualization, line number, arguments and id of subroutines

    Args:
        commands_to_execute_for_identifier (Array): array of command objects for a function
        commands (Array): array of all command objects
        device_name (String): name of device used
        num_wires (Int): number of wires
        num_shots (Int): number of shots

    Returns:
        Array: an array of the following information of each subroutig - name,
        circuit visualization, line number, arguments and id of subroutines
    """
    children_fcn_calls = []
    for i in range(len(commands_to_execute_for_identifier)):
        command = commands_to_execute_for_identifier[i]
        if command.quantum_or_classical == "classical" and command.line_type == "call":
            commands_to_execute_for_identifier_child = (
                helpers.get_commands_to_execute_for_identifier(commands, command.identifier)
            )
            circuit_img_child_byte_code = helpers.get_image_bs64_bytecode(
                helpers.draw_circuit(
                    commands_to_execute_for_identifier_child[:-1],
                    device_name,
                    num_wires,
                    num_shots,
                    commands[-1].code_line,
                    commands,
                )
            )
            arg_vals_child = []
            args_child = command.arguments.args
            locals_child = command.arguments.locals
            for arg in args_child:
                arg_vals_child.append([arg, locals_child[arg]])

            if len(arg_vals_child) == 0:
                arg_vals = None
            children_fcn_calls.append(
                {
                    "name": command.function,
                    "image": circuit_img_child_byte_code,
                    "id": command.identifier,
                    "line_number": command.line_number,
                    "children": [],
                    "arguments": arg_vals_child,
                }
            )
    return children_fcn_calls


def get_argument_information(commands):
    """Get argument information for qnode

    Args:
        commands (Array): array of commands

    Returns:
        Array: arguments of qnode
    """
    arg_vals = []
    args = commands[0].arguments.args
    locals = commands[0].arguments.locals
    for arg in args:
        arg_vals.append([arg, str(locals[arg])])

    if len(arg_vals) == 0:
        arg_vals = None

    return arg_vals


def remove_exection_time_from_processing_time(exec_time_list, process_start_time, process_end_time):
    """Remove exec times from processing time

    Args:
        exec_time_list (Array): array of execution times
        process_start_time (Float): process start time
        process_end_time (Float): process end time

    Returns:
        Float: the processing time
    """
    processing_time = process_end_time - process_start_time
    for n in exec_time_list:
        processing_time -= n

    return processing_time


def process_code(code, conn):
    """Execute and process the user code to extract commands and
        other useful information. Jsonify the results and send back
        to the main process.

    Args:
        code (string): user code
        conn (Python Connection Object): one end of the duplex pipe required to
            communicate between two processes.
    """
    initialize_resource_limits()

    process_start_time = time.time()
    exec_time_list = []

    # code clean up
    code = code_cleanup(code)

    # check for syntax errors
    trace, exec_time = get_trace(code)
    exec_time_list.append(exec_time)
    if type(trace) != MagicallyTraceStack:
        print(trace)
        return conn.send(jsonify({"error": trace}))

    # comment out transforms and get method names
    code_received_transforms_commented = helpers.comment_out_transforms(code)
    method_names = helpers.get_method_names(code)

    # get stack trace and execution time of code
    trace = None
    trace, exec_time = get_trace(code_received_transforms_commented)
    exec_time_list.append(exec_time)
    if type(trace) != MagicallyTraceStack:
        return conn.send(jsonify({"error": trace}))

    if not trace.get_stack():
        return jsonify({"error": ["Please run exactly one quantum node."]})

    # get device information
    annotated_queue = trace.get_stack()["commands"]
    device_name, num_shots, num_wires = helpers.get_device_info(trace.info, annotated_queue)

    code_received_transforms_commented_arr = code_received_transforms_commented.split("\n")

    # get list of command objects and main qnode output
    commands = helpers.get_list_of_commands(
        trace.info, method_names, code_received_transforms_commented, annotated_queue.queue
    )
    main_fcn_output, exec_time = helpers.get_fcn_output(
        commands[:-1], device_name, num_wires, num_shots, commands[-1]
    )

    exec_time_list.append(exec_time)

    add_image_commands_to_code_array(code_received_transforms_commented_arr, commands)

    transform_results_after_uncommenting_transforms = (
        get_transform_results_after_uncommenting_transforms(
            commands, code, code_received_transforms_commented_arr, exec_time_list, main_fcn_output
        )
    )
    transform_results_after_uncommenting_transforms.sort(key=lambda x: x[3])

    commands_to_execute_for_identifier = helpers.get_commands_to_execute_for_identifier(
        commands, commands[0].identifier
    )
    circuit_img_base_64_byte_code = helpers.get_image_bs64_bytecode(
        helpers.draw_circuit(
            commands_to_execute_for_identifier[:-1],
            device_name,
            num_wires,
            num_shots,
            commands[-1].code_line,
            commands,
        )
    )

    children_fcn_calls = get_information_of_subroutines(
        commands_to_execute_for_identifier, commands, device_name, num_wires, num_shots
    )

    arg_vals = get_argument_information(commands)
    more_information_main_fcn = {
        "Arguments": arg_vals,
        "Output": repr(main_fcn_output).replace("\n", "").replace(" ", ""),
    }

    # end processing
    processing_time = remove_exection_time_from_processing_time(
        exec_time_list, process_start_time, time.time()
    )

    conn.send(
        jsonify(
            {
                "name": commands[0].function,
                "id": commands[0].identifier,
                "image": circuit_img_base_64_byte_code,
                "line_number": commands[0].line_number,
                "children": children_fcn_calls,
                "has_children": len(children_fcn_calls) > 0,
                "more_information": more_information_main_fcn,
                "arguments": arg_vals,
                "transform_details": transform_results_after_uncommenting_transforms,
                "device_name": device_name,
                "commands": pickle.dumps((commands, annotated_queue.queue)).hex(),
                "debug_index": -1,
                "num_wires": num_wires,
                "num_shots": num_shots,
                "processing_time_no_exec_times": processing_time,
                "exec_times_list": exec_time_list,
            }
        )
    )


def create_app(test_config=None):
    """Main flask application builder function

    Returns:
        flask application
    """
    app = Flask(__name__, instance_relative_config=True)

    app.json.default = helpers.json_default

    @app.route("/", methods=["POST"])
    def main():
        """Entry point to exec server, executes code and
            responds to main server with information gathered.

        Returns:
            JSON to be used by the main server and frontend for
            various purposes.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            parent_conn, child_conn = Pipe()
            p = Process(
                target=process_code,
                args=(
                    body["data"],
                    child_conn,
                ),
            )
            p.start()
            start_time = time.time()
            while p.is_alive():
                if parent_conn.poll():
                    return parent_conn.recv()
                if (time.time() - start_time) > 10:
                    p.terminate()
                    return Response(status=418)
        return Response(status=400)

    return app
