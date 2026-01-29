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
A set of helper functions used by server/app.py and execserver/app.py
"""

import pennylane as qml
import numpy as np
import matplotlib
matplotlib.use("Agg") 
from matplotlib import pyplot as plt
import base64
import io
from collections import deque
from flask import Flask, render_template, request, jsonify
from server.magically_trace_stack import MagicallyTraceStack
import re
import tokenize
from server.command import Command
import time
import json
from flask.json.provider import _default as _json_default


def json_default(o):
    """JSON encoder for Python objects that cannot be jsonified
    automatically by the json library.

    Args:
        o: A python object

    Returns:
        JSON encoding of the object
    """
    if type(o) is range:
        return json.dumps([*o])
    if type(o) is qml.measurements.MeasurementValue:
        return str(o)
    return _json_default(o)


def check_for_restricted_code(code):
    """Checks if code has imports that are not allowed and if exec or eval is being used in code

    Args:
        code (String): code
    """

    banned_imports = {"lane", "json", "csv", "sys", "os", "urllib", "requests", "pathlib"}

    lines = code.split("\n")
    i = 0
    for line in lines:
        i += 1
        ls = re.split(r"[ ,.:=(]+", line)
        # stop banned imports
        if "import" in ls:
            for b in banned_imports:
                if b in ls:
                    return ["No module named: " + b, " line " + str(i)]

        # stop open, exec, eval
        if "open" in ls:
            return ["Filesystem functionality such as open() is disabled. ", " line " + str(i)]

        if "exec" in ls:
            return ["exec() function is disabled. ", " line " + str(i)]

        if "eval" in ls:
            return ["eval() function is disabled. ", " line " + str(i)]

        if "breakpoint" in ls:
            return ["Other debuggers cannot be used inside CircInspect. ", " line " + str(i)]
    return ""


def get_method_names(code):
    """Returns the names of methods in a code

    Args:
        code (string): The code

    Returns:
        Array[string]: Names of methods in the code.
    """
    code_arr = code.split("\n")
    method_names = set()
    for line in code_arr:
        if "def " in line:
            fcn_name = line.split(" ")[1].split("(")[0]
            method_names.add(fcn_name)
    return method_names


def find_first_qnode_decorator(tokens):
    """Find the index (line number - 1) for the qnode decorator that is on
        the smallest line number. There should be a single qnode in the program
        in regular operation.

    Args:
        code (string): the code sent by the frontend

    Returns:
        index (line number - 1) of the first qnode, if a qnode is found.
        -1, if no qnode decorator is found.
    """
    tokens = list(tokens)
    
    for i, t in enumerate(tokens[:-4]):
        if t.type == tokenize.OP and t.string == "@":

            if (
                tokens[i+1].string == "qml"
                and tokens[i+2].string == "."
                and tokens[i+3].string == "qnode"
            ):
                return t.start[0] - 1  # line index

    return -1


def comment_out_transforms(code):
    """Comments out transforms from the code and returns it

    Args:
        code (string): The code

    Returns:
        String: The code updated with transforms commented out
    """

    tokens = tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline)
    idx = find_first_qnode_decorator(tokens) 
    code_arr = code.split("\n") 

    j = idx - 1 
    
    while j >= 0: 
        if len(code_arr[j]) == 0 or code_arr[j][0] == "#": 
            j -= 1
        elif "@" == code_arr[j][0]: 
            code_arr[j] = "#" + code_arr[j] 
            j -= 1
        else:
            break

   
    k = idx + 1 
    while k < len(code_arr):
        if len(code_arr[k]) == 0 or code_arr[k][0] == "#": 
            k += 1
        elif "@" == code_arr[k][0]:
            code_arr[k] = "#" + code_arr[k]
            k += 1
        else:
            break

    return "\n".join(code_arr)


def get_transform_details(code):
    """Returns the following information about transforms:
       names of transforms applied to QNode and line numbers on which
       they are applied

    Args:
        code (string): The code
        starting_idx (int): The starting index for transforms

    Returns:
        Array[[string, int]]: Array of arrays of transform name and
        line number on which its applied
    """
    transforms_details = deque([])
    code_arr = code.split("\n")
    tokens = list(tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline))
    idx = find_first_qnode_decorator(tokens) 

    # find possible transform decorators (type is OP, string is @ and
    # not a qnode) from tokens and get a list of their line numbers
    possible_transforms = list(
        map(
            lambda t: t.start[0] - 1,
            filter(
                lambda t: t.type == tokenize.OP and t.string == "@" and "@qml.qnode(" not in t.line, tokens
            ),
        )
    )

    j = idx - 1
    while j >= 0:
        if len(code_arr[j]) == 0 or code_arr[j][0] == "#":
            j -= 1
        elif j in possible_transforms:
            transforms_details.appendleft([code_arr[j], j + 1])
            j -= 1
        else:
            break

    k = idx + 1
    while k < len(code_arr):
        if len(code_arr[k]) == 0 or code_arr[k][0] == "#":
            k += 1
        if k in possible_transforms:
            transforms_details.append([code_arr[k], k + 1])
            k += 1
        else:
            break

    return transforms_details


def get_num_shots(info):
    """Returns number of shots

    Args:
        info (list): List of lists of information in stack

    Returns:
        Int: number of shots
    """
    num_shots = 0
    for event in info:
        if event[0] == "device" and event[2] is not None:
            if hasattr(event[2], "short_name"):
                device_name = event[2].short_name
            else:
                device_name = event[2].name
            if event[2].wires is not None:
                num_wires = len(event[2].wires)
            if event[2].shots:
                num_shots = event[2].shots.total_shots
    return num_shots


def get_device_name(info):
    """Returns device name

    Args:
        info (list): List of lists of information in stack

    Returns:
        String: Name of device
    """
    device_name = ""

    if device_name == "":
        # Find device through the QNode info in module args
        for i in info[-1][5]:
            if type(i) is dict:
                for v in i.values():
                    if type(v) is qml.QNode:
                        if hasattr(v.device, "short_name"):
                            device_name = v.device.short_name
                        else:
                            device_name = v.device.name

    return device_name


def get_device_info(info, annotated_queue):
    """Returns device name, number of wires and shots for device being used

    Args:
        info (list): List of lists of information in stack
        annotated_queue(AnnotatedQueue): PennyLane annotated queue

    Returns:
        tuple(string, int, int): Device name, number of shots used and number of wires
    """
    device_name = get_device_name(info)
    num_shots = get_num_shots(info)
    num_wires = 0

    set_wires = set()
    #finds exactly what wires are used during execution
    for j in annotated_queue.queue: 
        if j.wires is None:
            set_wires.update()
        set_wires.update(j.wires)

    if len(set_wires) != 0:
        num_wires = max(set_wires) + 1

    return (device_name, num_shots, num_wires)


def get_list_of_commands(info, method_names, code, annotated_queue):
    """Returns a list of command objects

    Args:
        info(list): List of lists of information in stack
        method_names(list): List of method names
        code(string): Code string
        annotated_queue: pennylane queue

    Returns:
        list(command): List of command objects
    """
    commands = []
    code_arr = code.split("\n")


    #finds and labels all the classical commands as classical (specifically for defined functions)
    for i in range(len(info)):
        ith_info = info[i]
        if ith_info[0] in method_names and ith_info[-3] == "<string>":
            if (
                len(commands) > 0
                and commands[-1].code_line == code_arr[ith_info[1] - 1].strip() 
                and ith_info[-2] == "return" 
            ):
                commands[-1].line_type = "return"
                continue
            else:
                command = Command(
                    ith_info[0], 
                    ith_info[1], 
                    code_arr[ith_info[1] - 1].strip(), 
                    ith_info[-2], 
                    "classical", 
                )
                command.arguments = ith_info[-1]
                commands.append(command)
   
    circuit_commands = []
    circuit_name = ""
    for c in commands:
        if "@qml.qnode" in c.code_line:
            circuit_name = c.function
        if circuit_name != "":
            circuit_commands.append(c)
            if c.function == circuit_name and c.line_type == "return":
                break
    commands = circuit_commands


    i = 0
    for j in range(len(commands)):
        command = commands[j]
        if "qml.adjoint" in command.code_line:
            command.function = "adjoint of " + command.function
        elif (
            command.code_line[0:3] == "qml"
            or "return qml." in command.code_line
            or ("qml" in command.code_line and command.code_line[0] != "@")
        ):
            command.code_line = annotated_queue[i]
            command.quantum_or_classical = "quantum"
            i += 1

    commands[-1].code_line = []
    for i in range(len(annotated_queue) - 1, -1, -1):
        if "pennylane.measurement" not in str(
            type(annotated_queue[i])
        ) or "pennylane.measurements.mid" in str(type(annotated_queue[i])):
            break
        commands[-1].code_line.append(annotated_queue[i])
    update_identifier_numbers(commands)
    update_identifier_its_called_from(commands)

    return commands


def get_quantum_methods(commands):
    """Return all methods that have quantum operations being used in code

    Args:
        commands(list): List of command objects

    Returns:
        quantum_methods(set): Set of method names that have quantum operators in code
    """
    quantum_methods = set()
    for command in commands:
        if command.quantum_or_classical == "quantum":
            quantum_methods.add(command.function)

    return quantum_methods


def get_all_commands_in_function(function_name, commands, quantum_methods):
    """Return all commands in a particular function

    Args:
        function_name(string): Function name for which we get all commands
        commands(list): List of command objects
        quantum_methods(set): A set of methods that have quantum operations in code
    """
    commands_in_function = []
    for c in commands:
        if c.function == function_name:
            if c.quantum_or_classical == "quantum":
                commands_in_function.append(c)
            else:
                if "()" in c.code_line:
                    if c.code_line[:-2] in quantum_methods:
                        commands_in_function.append(c)
    return commands_in_function


def update_identifier_numbers(commands):
    """Updates identifier number for each command

    Args:
        commands(list): List of command objects
    """
    for i in range(len(commands)):
        commands[i].identifier = i


def update_identifier_its_called_from(commands):
    """Updates the identifier its called from for each command

    Args:
        commands(list): List of command objects
    """
    stack = [commands[0].identifier]
    for i in range(1, len(commands)):
        command = commands[i]
        if type(command.code_line) is str and "def " in command.code_line:
            command.identifier_its_called_from = stack[-1]
            stack.append(commands[i - 1].identifier)
        else:
            command.identifier_its_called_from = stack[-1]
            if command.line_type == "return":
                stack.pop()


def get_commands_to_execute_for_identifier(commands, identifier):
    """Get commands from list of commands that are called from the argument identifier

    Args:
        commands(list): List of command objects
        identifier(int): Identifier

    Returns:
        Returns the list of commands that are called from the argument identifier
    """
    commands_called_from_identifier = []
    for i in range(len(commands)):
        command = commands[i]
        if command.identifier_its_called_from == identifier:
            commands_called_from_identifier.append(command)

    return commands_called_from_identifier

def draw_circuit(commands, device_name, num_wires, num_shots, last_command, all_commands):
    """
    Draw a quantum circuit given a list of commands

    Args:
        commands (list): List of command objects.
        device_name (str): Name of the PennyLane device.
        num_wires (int): Number of wires in the circuit.
        num_shots (int): Number of shots for the device.
        last_command (list): List of PennyLane operations for the last step.
        all_commands (list): All commands in the program for wiring info.

    Returns:
        matplotlib.figure.Figure: Figure object of the circuit.
    """

    dev = qml.device(device_name, wires=num_wires or 1)
    @qml.set_shots(shots = num_shots or None)
    @qml.qnode(dev)
    def circuit():
        for i, command in enumerate(commands):
            if command.quantum_or_classical == "classical" and command.line_type == "call":
                set_command_wires = set()
                for c in all_commands:
                    if (
                        i > 0
                        and c.identifier_its_called_from == commands[i - 1].identifier
                        and c.quantum_or_classical == "quantum"
                    ):
                        set_command_wires.update(c.code_line.wires)
                set_command_wires = sorted(set_command_wires) or range(num_wires)

                # Custom operation
                class Func(qml.operation.Operation):
                    grad_method = "A"

                    def __init__(self, wires, op_name, id=None):
                        self.__class__.__name__ = op_name
                        super().__init__(wires=wires, id=id)

                    @classmethod
                    def compute_decomposition(cls, wires):
                        return [qml.QubitUnitary(np.eye(len(wires)), wires=wires)]

                Func(wires=set_command_wires, op_name=command.function)

            # Quantum operations
            elif command.quantum_or_classical == "quantum" and not isinstance(command.code_line, list):
                qml.apply(command.code_line)

        return [qml.apply(op) for op in last_command]

    fig = qml.draw_mpl(circuit, decimals=2)()[0]
    plt.close(fig)

    return fig


def get_image_bs64_bytecode(img):
    """Return the base 64 image bytecode

    Args:
        img(image): Image

    Returns:
        base64bytecode: The base 64 byte code of image
    """
    base_64_byte_code = ""
    plt.ioff()
    with io.BytesIO() as buffer:  # use buffer memory
        img.savefig(buffer, format="png")
        buffer.seek(0)
        buffer_val = buffer.getvalue()

        img_bytecode = base64.b64encode(buffer_val)
        base_64_byte_code = str(img_bytecode)[2:-1]

    return base_64_byte_code


def get_fcn_output(commands, device_name, num_wires, num_shots, last_command):
    """Return main function output for circuit

    Args:
        commands(list): List of command objects
        device_name(string): Device name
        num_wires(int): Number of wires in quantum circuit
        num_shots(int): Number of shots
        last_command(pennylane operation): Last command for circuit

    Returns:
        Output for circuit
    """
    dev = qml.device(device_name, wires=num_wires)
    if num_shots != 0:
        dev = qml.device(device_name, wires=num_wires, shots=num_shots)

    @qml.qnode(dev)
    def circuit():
        for c in commands:
            if c.quantum_or_classical == "quantum":
                qml.apply(c.code_line)
        return [qml.apply(i) for i in last_command.code_line]

    exec_time = time.time()
    output = circuit()
    return output, time.time() - exec_time


def get_function_output(fcn, code_received):
    """Get function output result

    Args:
        fcn (Command): Function we would like to evaluate
        code_received: The code

    Returns:
        The evaluation of the the function circuit

    """
    fcn_call = "ispa=" + fcn.function
    fcn_call = fcn_call + "("

    if len(fcn.arguments.args) > 0:
        for key in fcn.arguments.args:
            fcn_call = fcn_call + key + "=" + str(fcn.arguments.locals[key]) + ","
        fcn_call = fcn_call[0:-1]
    fcn_call = fcn_call + ")"

    code_received.append(fcn_call)

    data = {}
    exec_start_time = time.time()
    exec("\n".join(code_received), globals(), data)
    return data["ispa"], time.time() - exec_start_time


def get_transform_image(fcn, code_received):
    """Get the transform image

    Args:
        fcn (Command): Function we would like to evaluate
        code_received: The code

    Returns:
        The transform image

    """
    img_call = "awa=qml.draw_mpl(" + fcn.function + ")" + "("
    if len(fcn.arguments.args) > 0:
        for key in fcn.arguments.args:
            img_call = img_call + key + "=" + str(fcn.arguments.locals[key]) + ","
        img_call = img_call[0:-1]
    img_call = img_call + ")"
    code_received.append(img_call)
    data = {}
    exec_start_time = time.time()
    exec("\n".join(code_received), globals(), data)

    return get_image_bs64_bytecode(data["awa"][0]), time.time() - exec_start_time


def expand_methods(
    commands,
    identifier,
    device_name,
    num_wires,
    num_shots,
    annotated_queue,
    show_measurements,
    all_commands,
):
    """Expand methods and get children data

    Args:
        commands (List of commands): List of command objects
        identifier (int): Identifier of command
        device_name (String): Device name
        num_wires (int): Number of wires
        num_shots (int) : number of shots
        annotated_queue (Annotated Queue): The annotated queue of tape
    """
    commands_to_execute_for_identifier = get_commands_to_execute_for_identifier(
        commands, identifier
    )

    children_fcn_calls = []
    for i in range(len(commands_to_execute_for_identifier)):
        command = commands_to_execute_for_identifier[i]
        if command.quantum_or_classical == "classical" and command.line_type == "call":
            commands_to_execute_for_identifier_child = get_commands_to_execute_for_identifier(
                commands, commands_to_execute_for_identifier[i - 1].identifier
            )

            has_children = False
            for c in commands_to_execute_for_identifier_child:
                if c.line_type == "call":
                    has_children = True
                    break

            circuit_img_child_byte_code = get_image_bs64_bytecode(
                draw_circuit(
                    commands_to_execute_for_identifier_child,
                    device_name,
                    num_wires,
                    num_shots,
                    [],
                    all_commands,
                )
            )
            arg_vals_child = []
            args = command.arguments.args
            locals = command.arguments.locals
            for arg in args:
                arg_vals_child.append([arg, locals[arg]])

            arg_vals = []
            args = command.arguments.args
            locals = command.arguments.locals
            for arg in args:
                arg_vals.append([arg, locals[arg]])

            if len(arg_vals) == 0:
                arg_vals = None

            more_information_children = {"Arguments": arg_vals}

            children_fcn_calls.append(
                {
                    "name": command.function,
                    "image": circuit_img_child_byte_code,
                    "id": commands_to_execute_for_identifier[i - 1].identifier,
                    "line_number": commands_to_execute_for_identifier[i - 1].line_number,
                    "children": [],
                    "more_information": more_information_children,
                    "arguments": arg_vals,
                    "has_children": has_children,
                }
            )

    return {"children": children_fcn_calls}


def run_pennylane_commands(
    commands, device_name, num_wires, num_shots, last_command, debug_identifier
):
    """Takes pennylane commands from commands list and runs them to get final result

    Args:
        commands (List of commands): A list of commands

    Returns:
        Returns the pennylane commands evaluated
    """
    dev = qml.device(device_name, wires=num_wires)
    if num_shots != 0:
        dev = qml.device(device_name, wires=num_wires, shots=num_shots)

    @qml.qnode(dev)
    def circuit():
        for c in commands:
            if c.identifier == debug_identifier:
                break
            if c.quantum_or_classical == "quantum":
                qml.apply(c.code_line)
        return [qml.apply(i) for i in last_command]

    return circuit()


def get_quantum_lines(code):
    """Get the lines in the code that have quantum code

    Args:
        code (String): The code

    Returns:
        Returns a set of line numbers with quantum code
    """
    lines = set()
    for i in range(len(code)):
        c = code[i]
        if "qml." in c:
            lines.add(i + 1)
    return lines


def newline_cleanup(code):
    """Sometimes users put newlines such that the a code line that
        CircInspect expects to process as a single line gets divided
        up into multiple lines. This function safely removes the newlines
        inside paranthesis and puts them after the paranthesis ends.
        E.g.
        ---
        qml.PauliX(
            wires=0
            )
        ---
        is transformed to
        ---
        qml.PauliX(wires=0)


        ---
        (newlines are added back after the PauliX)

    Args:
        code (String): Code that has new line characters inside qml operation parameters

    Returns:
        String: Code after new line characters have been cleaned up
    """
    newline_num = 0
    open_parentheses = 0
    i = 0
    while i < len(code):
        c = code[i]

        if c == "(":
            open_parentheses += 1
        elif c == ")":
            open_parentheses -= 1
            if open_parentheses == 0:
                # Re-insert the newlines that were removed inside parentheses
                j = code.find("\n", i)
                if j != -1:
                    code = code[: j + 1] + ("\n" * newline_num) + code[j + 1 :]
                i += newline_num
                newline_num = 0
        elif c == "\n" and open_parentheses > 0:
            # Remove newlines inside parentheses
            code = code[:i] + code[i + 1 :]
            newline_num += 1
            i -= 1

        i += 1

    
    def collapse_spaces(match):
        """Normalize whitespace inside a parenthesized expression.

            This helper is intended for use with `re.sub`. Given a regex match
            representing the contents inside parentheses, it collapses all
            sequences of whitespace (including newlines and tabs) into a single
            space and trims leading/trailing spaces.

            Example:
                Input match: "(a,\n   b,   c)"
                Output: "(a, b, c)"

        Args:
            match (re.Match): A regex match object where group(1) contains
                the inner contents of a parenthesized expression.

        Returns:
            str: The reconstructed parenthesized string with normalized
            whitespace.
        """

        inner = match.group(1)
        inner = re.sub(r"\s+", " ", inner)  # replace any whitespace with single space
        return f"({inner.strip()})"

    code = re.sub(r"\((.*?)\)", collapse_spaces, code, flags=re.DOTALL)

    return code



def comment_cleanup(code):
    """Replace comments from the code with empty lines
    
     Args:
        code (String): Code to remove comments from

    Returns:
        String: Code after comments have been removed
    """
    # type tokenize.COMMENT indicates that the token is a comment
    tokens = filter(
        lambda t: t.type == tokenize.COMMENT, tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline)
    )
    for t in tokens:
        code = code.replace(t.string, "")
    return code

def code_cleanup(code):
    """Cleans up the new line characters inside qml operation parameters and cleans up comments

    Args:
        code (String): Code to clean up

    Returns:
        String: Code after new line characters and comments have been removed
    """
    newline_cleaned_up_code = newline_cleanup(code)
    commented_cleaned_up_code = comment_cleanup(newline_cleaned_up_code)
    return commented_cleaned_up_code
