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
import numpy as np
import matplotlib

matplotlib.use("Agg")
from matplotlib import pyplot as plt
import base64
import io
import re
import tokenize
import json
from flask.json.provider import _default as _json_default
import ast
from server.code_security_validator import CodeSecurityValidator


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
    if type(o) is qp.measurements.MeasurementValue:
        return str(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.generic, np.number)):
        return o.item()
    if isinstance(o, complex):
        return str(o)
    if callable(o):
        return f"<Callable: {getattr(o, '__name__', type(o).__name__)}>"
    try:
        return _json_default(o)
    except TypeError:
        return str(o)

def check_for_restricted_code(code):
    """Checks if code has imports that are not allowed and if exec or eval is being used in code.

    Args:
        code(string): String representation of user code
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return [f"Syntax Error: {e.msg}", f" line {e.lineno}"]

    validator = CodeSecurityValidator()
    validator.visit(tree)
    if validator.error:
        return validator.error
    
    return ""


def get_method_names(code):
    """Returns the names of methods in a code.

    Args:
        code(string): String representation of user code

    Returns:
        set[string]: Names of methods in the code.
    """
    code_arr = code.split("\n")
    method_names = set()
    for line in code_arr:
        if "def " in line:
            fcn_name = line.split(" ")[1].split("(")[0]
            method_names.add(fcn_name)
    return method_names


def find_first_qnode_decorator(tokens):
    """Find the code array index (line number - 1) for the qnode decorator that is on
        the smallest line number. There should be a single qnode in the program
        in regular operation.

    Args:
        tokens(list): List of tokens from user code

    Returns:
        index (line number - 1) of the first qnode, if a qnode is found.
        -1, if no qnode decorator is found.
    """

    for i, t in enumerate(tokens[:-4]):
        if t.type == tokenize.OP and t.string == "@":
            if "".join([tokens[k].string for k in range(i + 1, i + 4)]) == "qp.qnode":
                return t.start[0] - 1  # line index

    return None


def get_qnode_name(code, method_names):
    """Returns the name of the function decorated with @qp.qnode.

    Args:
        code(string): String representation of user code
        method_names(set[string]): Names of methods in the code.

    Returns:
        string: Name of the QNode function, or None.
    """
    try:
        tokens = list(tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline))
        idx = find_first_qnode_decorator(tokens)
        if idx is not None:
            code_arr = code.split("\n")
            # The line after the decorator should be the function definition.
            for i in range(idx + 1, len(code_arr)):
                line = code_arr[i].strip()
                if not line or line.startswith("#") or line.startswith("@"):
                    continue
                if line.startswith("def "):
                    potential_name = line.split("def ")[1].split("(")[0].strip()
                    if potential_name in method_names:
                        return potential_name
                    break
    except:
        pass
    return None


def get_device_info(info, annotated_queue):
    """Returns device name, number of shots, and number of wires.

    Dev Note:
        Num wires may not be required in the future as pennylane no longer requires explicit setting of num_wires.

    Args:
        info(List[List[Any]]): List of lists of information in stack
        annotated_queue(AnnotatedQueue): PennyLane annotated queue

    Returns:
        device_name(string): Name of the device
        num_shots(int): Number of shots
        num_wires(int): Number of wires
    """
    device_name = ""
    num_shots = 0
    num_wires = 0

    for event in info:
        if event[0] == "device" and event[2] is not None:
            device = event[2]
            if not device_name:
                device_name = device.short_name if hasattr(device, "short_name") else device.name
            if device.shots:
                num_shots = device.shots.total_shots
            if device.wires is not None:
                num_wires = len(device.wires)
            break
    # Fallback: find device via QNode in module args
    if not device_name or num_wires == 0:
        for i in info[-1][5]:
            if isinstance(i, dict):
                for v in i.values():
                    if isinstance(v, qp.QNode):
                        d = v.device
                        if not device_name:
                            device_name = d.short_name if hasattr(d, "short_name") else d.name
                        if num_wires == 0 and d.wires is not None:
                            num_wires = len(d.wires)

    # Fallback: infer wires from the annotated queue
    if num_wires == 0:
        set_wires = set()
        for op in annotated_queue.queue:
            if op.wires is not None:
                set_wires.update(op.wires)
        if set_wires:
            num_wires = max(set_wires) + 1

    return device_name, num_shots, num_wires


def get_relevant_args(source_line: str, arg_info):
    """Given a source line and its ArgInfo, return only the variables
    that are directly referenced in that line.

    Args:
        source_line(str): The source code line
        arg_info(ArgInfo): ArgInfo object with .args, .varargs, .keywords, .locals

    Returns:
        dict{string: Any}: for variables actually used in the line
    """
    source_line = source_line.strip()

    if "@qp.qnode" in source_line:
        return arg_info.locals

    local_vars = arg_info.locals
    if not local_vars:
        return {}

    referenced_names = set()
    clean = source_line.rstrip(":")

    for attempt in [
        source_line,
        source_line + "\n    pass",
        clean,
        f"({clean})",
    ]:
        try:
            tree = ast.parse(attempt, mode="exec")
            referenced_names = (
                {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
                | {node.arg for node in ast.walk(tree) if isinstance(node, ast.arg)}
            )
            break
        except SyntaxError:
            continue
    else:
        raise SyntaxError(f"Could not parse source line: {source_line!r}")

    return {name: local_vars[name] for name in referenced_names if name in local_vars}


def newline_cleanup(code):
    """Cleans up extra newlines inside qp operation parameters by removing the newlines
        inside paranthesis and putting them after the paranthesis ends.
        E.g.
        ---
        qp.PauliX(
            wires=0
            )
        ---
        is transformed to
        ---
        qp.PauliX(wires=0)


        ---
        (newlines are added back after the PauliX)

    Args:
        code(string): Code that has new line characters inside qp operation parameters

    Returns:
        code(string): Code after new line characters have been cleaned up
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
                Input match: "(a,      b,   c)"
                Output: "(a, b, c)"

        Args:
            match(re.Match): A regex match object where group(1) contains
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
    """Replace comments from the code with empty lines.

     Args:
        code(string): Code to remove comments from

    Returns:
        code(string): Code after comments have been removed
    """
    tokens = filter(
        lambda t: t.type == tokenize.COMMENT,
        tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline),
    )
    for t in tokens:
        code = code.replace(t.string, "")

    return code


def code_cleanup(code):
    """Cleans up the new line characters inside qp operation parameters and cleans up comments.

    Args:
        code(string): String representation of user code

    Returns:
        code(string): Code after new line characters and comments have been removed
    """
    newline_cleaned_up_code = newline_cleanup(code)
    commented_cleaned_up_code = comment_cleanup(newline_cleaned_up_code)

    return commented_cleaned_up_code


def flatten_tree(root):
    """Flattens the command tree into a list of command objects.

    Args:
        root(Command Object): The root of the command tree

    Returns:
        result(List[Command Object]): List of command objects in execution order
    """
    result = [root]
    for child in root.children:
        result.extend(flatten_tree(child))
    return result


def get_children_from_identifier(identifier, commands):
    """Get the children of a command given its idenitfier.

    Args:
        identifier(int): The identifier of the command you want to find the children off
        commands(List[Command Object]): List of command objects

    Returns:
        children(List[Command Object]): List of children of specified command
    """
    children = []
    for command in commands:
        if command.parent_id == identifier:
            children.append(command)
    return children


def get_sibling_commands(commands, current_command):
    """Get the sibling of a given command.

    Args:
        commands(List[Command Object]): List of command objects
        current_command(Command Object): The command to get the siblings of

    Returns:
        sibling_command(List[Command Object]): List of sibling commands of specified command
    """
    sibling_commands = []
    for command in commands:
        if command.parent_id == current_command.parent_id:
            sibling_commands.append(command)

    return sibling_commands


def get_command_by_identifier(commands, identifier):
    """Gets a command with a specific idenitifier.

    Args:
        commands(List[Command Object]): List of command objects
        identifier(int): The identifier of the command to get

    Returns:
        command(Command Object): The command with the specified identifier
            or None if no such command exists.

    """
    for command in commands:
        if command.identifier == identifier:
            return command
    return None


def get_depth(cmd, flat_commands):
    """Calculates the depth of a command in the command tree hierarchy.

    Args:
        cmd (Command): The command object to find the depth for.
        flat_commands (list): A flat list of all command objects in the tree.

    Returns:
        int: The depth level of the command (0 if it has no parent).
    """
    depth = 0
    current = cmd
    while current.parent_id is not None:
        current = get_command_by_identifier(flat_commands, current.parent_id)
        if current is None:
            break
        depth += 1
    return depth


def collect_quantum_commands(commands):
    """Recursively collect all quantum commands from the tree in depth-first order,
    matching the execution order of quantum operations.

    Args:
        commands (list[Command Object]): List of sibling command objects at some level of the tree.

    Returns:
        list[Command Object]: All quantum command objects in execution order, collected
        depth-first across the entire subtree.
    """
    result = []
    for command in commands:
        if command.quantum_or_classical == "quantum" or command.line_type == "measurement":
            result.append(command)
        if command.children:
            result.extend(collect_quantum_commands(command.children))
    return result


def adjust_for_adjoint(command, line_num):
    command.children.reverse()
    for child in command.children:
        child.line_number = line_num
        adjust_for_adjoint(child, line_num)
            
            
def get_quantum_leaves(root_command, flat_commands=None):
    result = []
    commands = flat_commands if flat_commands is not None else flatten_tree(root_command)
    for command in commands:
        if command.quantum_or_classical == "quantum" and len(command.children) == 0:
            result.append(command)

    return result

def get_image_bs64_bytecode(img):
    """Return the base 64 image bytecode.

    Args:
        img(matplotlib.figure.Figure): Figure object of the circuit.

    Returns:
        base64bytecode(string): The base 64 byte code of image
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


def get_wires_recursive(command):
    """Recursively gets the wires used by a command and its children.

    Args:
        command(Command Object): The command we want to get the wires of

    Returns:
        wires(set): The set of wires used by the command
    """
    wires = set()
    if command.quantum_or_classical == "quantum" and type(command.code_line) is not str:
        if isinstance(command.code_line, qp.ops.Conditional):
            wires.update(command.code_line.wires)
            if hasattr(command.code_line.base, "wires"):
                wires.update(command.code_line.base.wires)
        elif isinstance(command.code_line, list):
            for op in command.code_line:
                wires.update(op.wires)
        else:
            wires.update(command.code_line.wires)

    for child in command.children:
        wires.update(get_wires_recursive(child))
    return wires


def _print_tree(node, level=0):
    """Visualizes a command tree, used purely for debugging reasons.

    Args:
        node(Command Object): The command node
        level(int): The level the command node is on in the tree
    """
    indent = "    " * level
    children_str = ", ".join([str(child.identifier) for child in node.children])

    print(
        f"{indent}|--{node.code_line} id: {node.identifier} parent_id: {node.parent_id} children: [{children_str}] linetype: {node.line_type} args: {node.arguments} condition_context: {node.condition_context}", flush=True
    )
    for child in node.children:
        _print_tree(child, level + 1)


def unwrap_op(op):
    """Recursively unwrap a PennyLane operator that may be a combination of
    Controlled, Adjoint, and Conditional wrappers in any order and any depth.

    Args:
        op(qp.Operation): The operation to unwrap

    Returns:
        base_label (str): The label of the innermost (unwrapped) gate, e.g. "Y"
        num_controls (int): Total number of control wires accumulated across all Controlled wrappers
        is_adjoint (bool): True if an odd number of Adjoint wrappers are present
    """
    num_controls = 0
    is_adjoint = False

    current = op
    while True:
        if isinstance(current, qp.ops.Controlled):
            num_controls += len(current.control_wires)
            current = current.base
        elif isinstance(current, qp.ops.Adjoint):
            is_adjoint = not is_adjoint
            current = current.base
        elif isinstance(current, qp.ops.Conditional):
            # Conditional is transparent – the visible gate is its base
            current = current.base
        else:
            # Reached the actual base gate
            break

    base_label = current.label()
    return base_label, num_controls, is_adjoint