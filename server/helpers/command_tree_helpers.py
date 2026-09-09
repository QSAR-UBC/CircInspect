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
from pennylane.measurements import MidMeasureMP
from server.command import Command
import time
from server import helpers

SCF_KEYWORDS = ["for ", "while ", "match ", "if ", "elif ", "for(", "while(", "match(", "if(", "elif("]

CLASSICAL_CONDITION_KEYWORDS = ("if ", "elif ", "if(", "elif(")

QUANTUM_KEYWORDS = {
    "qp.measure": "mid_measurement",
    "qp.cond": "cond",
    "qp.adjoint": "adjoint",
    "qp.ctrl": "controlled"
}

def generate_command_tree(executed_commands_info, method_names, code, annotated_queue):
    """Returns a command object, which is the root of the command tree

    Args:
        executed_commands_info(List[List]): List of executed command information from execution trace stack, where each list item represents a different executed command and contains trace information about that command as a list
        method_names(List[string]): List of method names
        code(string): String representation of user code
        annotated_queue(List[qp.Operation]): pennylane queue

    Returns:
        root_command(Command Object): Command object, root node of command tree; all other nodes can be accessed from here.
        This object acts as the reference/entry point to the command tree.
    """
    commands = []
    code_arr = code.split("\n")
    curr_id = 0
    circuit_name = ""
    # iterates through stack trace and generates commands based on info
    for i in range(len(executed_commands_info)):
        command_datum = executed_commands_info[i]

        if command_datum[0] in method_names and command_datum[-3] == "<string>":
            parent_function = command_datum[0]
            line_num = command_datum[1]
            code_line = code_arr[line_num - 1].strip()
            line_type = command_datum[-2]
            indent = len(code_arr[command_datum[1] - 1]) - len(code_arr[command_datum[1] - 1].lstrip())
            arg_info = command_datum[-1]

            if "@qp." in code_line:
                circuit_name = parent_function
            
            if circuit_name == "":
                continue

            return_match = next(
                (
                    prev
                    for prev in reversed(commands)
                    if prev.line_number == line_num
                    and prev.code_line == code_line
                    and prev.line_type not in ("return", "measurement")
                ),
                None,
            ) if line_type == "return" else None

            if return_match is not None:
                if "return qp." in code_line:
                    return_match.line_type = "measurement"
                else:
                    return_match.line_type = "return"
                continue

            elif "qp." in code_line and any(quantum_keyword in code_line for quantum_keyword in QUANTUM_KEYWORDS):
                if line_type != "return":
                    line_type = next(QUANTUM_KEYWORDS[quantum_keyword] for quantum_keyword in QUANTUM_KEYWORDS if quantum_keyword in code_line)
                command = Command(parent_function, line_num, code_line, line_type, "quantum", indent)
                command.arguments = helpers.get_relevant_args(code_line, arg_info)
                command.identifier = curr_id
                curr_id += 1
                commands.append(command)

            elif "qp." in code_line:
                command = Command(parent_function, line_num, code_line, line_type, "quantum", indent)
                command.arguments = helpers.get_relevant_args(code_line, arg_info)
                command.identifier = curr_id
                curr_id += 1
                commands.append(command)

            elif any(scf_keyword in code_line for scf_keyword in SCF_KEYWORDS):
                command = Command(parent_function, line_num, code_line, "scf", "classical", indent)
                command.arguments = helpers.get_relevant_args(code_line, arg_info)
                command.identifier = curr_id
                curr_id += 1
                commands.append(command)

            else:
                command = Command(parent_function, line_num, code_line, line_type, "classical", indent)
                command.arguments = helpers.get_relevant_args(code_line, arg_info)
                command.identifier = curr_id
                curr_id += 1
                commands.append(command)

    # link all nodes to their parent and children to create tree structure
    update_parent_id(commands)    
    update_command_parent_function(commands)
    update_command_children(commands)
    update_condition_context(commands)
    clobbered_conditions = []
    clobber_classical_conditions([commands[0]], commands, clobbered_conditions)
    merge_scf_calls([commands[0]], clobbered_conditions)
    align_quantum_operations(commands)


    flat_commands = helpers.flatten_tree(commands[0])
    if update_quantum_code_lines(commands, annotated_queue, flat_commands):
        return {"error": ["Please run exactly one quantum node."]}, None
    helpers.link_mid_circuit_measurements(commands, flat_commands)
    update_tree_node_names(commands, method_names)

    for command in reversed(commands):
        if command.line_type == "measurement":
            last_circuit_command = command
            break
            
    last_circuit_command.code_line = []
    for i in range(len(annotated_queue) - 1, -1, -1):
        if "pennylane.measurement" not in str(type(annotated_queue[i])):
            break
        last_circuit_command.code_line.append(annotated_queue[i])


    root_command = commands[0]
    # Not reachable via .children (clobbered out of the render tree), but kept
    # here so the debugger can still step onto if/elif condition checks.
    root_command.clobbered_conditions = clobbered_conditions

    return root_command


def align_quantum_operations(commands):
    for command in commands:
        if "adjoint" in command.code_line and len(command.children) > 0:
            helpers.adjust_for_adjoint(command, command.line_number)


def update_quantum_code_lines(commands, annotated_queue, flat_commands=None):
    aligned_quantum_commands = helpers.get_quantum_leaves(commands[0], flat_commands)

    for i, command in enumerate(aligned_quantum_commands):
        if type(command.code_line) is str and "@qp.qnode" in command.code_line:
            return [{"error": ["Please run exactly one quantum node."]}, None]
        command.code_line = annotated_queue[i] 


def update_identifier_numbers(commands):
    """Updates identifier number for each command

    Args:
        commands(List[Command Objects]): List of command objects
    """
    for i in range(len(commands)):
        commands[i].identifier = i


def update_parent_id(commands):
    """Updates the identifier its called from for each command

    Args:
        commands(List[Command Objects]): List of command objects
    """
    id_lookup = {cmd.identifier: cmd for cmd in commands}
    stack = [(commands[0].identifier, commands[0].line_type, commands[0].indent)]

    for i, curr_command in enumerate(commands[1:], start=1):
        prev_command = commands[i - 1]

        if type(curr_command.code_line) is str and "def " in curr_command.code_line and curr_command.line_type == "call":
            if prev_command.line_type:
                prev_command.line_type = "call"
            prev_command.arguments = curr_command.arguments
            curr_command.line_type = "line"
            stack.append(
                (
                    prev_command.identifier,
                    prev_command.line_type,
                    prev_command.indent,
                )
            )
            curr_command.parent_id = stack[-1][0]

        elif curr_command.line_type == "scf":
            # Pop any scf frames that are at the same or deeper indent (handles same-level scf chains like if/elif/else)
            while len(stack) > 1 and stack[-1][1] == "scf" and stack[-1][2] >= curr_command.indent:
                stack.pop()
            curr_command.parent_id = stack[-1][0]
            stack.append((curr_command.identifier, curr_command.line_type, curr_command.indent))

        elif curr_command.line_type in ("return", "measurement"):
            # A loop's final header revisit can also be labelled "return"; keep it nested in the loop's scf frame, not popped past it.
            top_cmd = id_lookup.get(stack[-1][0])
            is_same_loop_final_check = (
                stack[-1][1] == "scf"
                and top_cmd is not None
                and top_cmd.code_line == curr_command.code_line
                and top_cmd.line_number == curr_command.line_number
            )

            if not is_same_loop_final_check:
                # Pop any scf frames that we've outdented past
                while len(stack) > 1 and stack[-1][1] == "scf" and stack[-1][2] >= curr_command.indent:
                    stack.pop()

            curr_command.parent_id = stack[-1][0]

            # Unwind remaining scf frames and the call frame so later siblings land in the right scope.
            while len(stack) > 1 and stack[-1][1] == "scf":
                stack.pop()
            if len(stack) > 1:
                stack.pop()

        else:
            # Pop any scf frames that we've outdented past
            while len(stack) > 1 and stack[-1][1] == "scf" and stack[-1][2] >= curr_command.indent:
                stack.pop()

            curr_command.parent_id = stack[-1][0]


def update_command_parent_function(commands):
    """Updates the parent function for each command to ensure
    children of scf commands are correctly assigned to their parent scf command

    Args:
        commands(List[Command Objects]): List of command objects
    """

    if commands:
        id_lookup = {cmd.identifier: cmd for cmd in commands}
        for command in commands:
            parent_id = command.parent_id
            if parent_id in id_lookup.keys():
                for keyword in SCF_KEYWORDS:
                    if keyword in id_lookup[parent_id].code_line:
                        command.parent_function = keyword.strip()
                        break


def update_command_children(commands):
    """Updates the children for each command

    Args:
        commands(List[Command Objects]): List of command objects
    """
    if commands:
        for command in commands:
            command.children = []

        id_lookup = {cmd.identifier: cmd for cmd in commands}

        for command in commands:
            parent_id = command.parent_id
            if parent_id is not None and parent_id in id_lookup:
                id_lookup[parent_id].children.append(command)


def update_tree_node_names(commands, method_names):
    """Updates the tree node name on each command for the frontend to use.

    Args:
        commands (List[Command Objects]): List of command objects
    """
    for command in commands:
        if command.tree_node_name is not None:
            continue
        if "@qp.qnode" in str(command.code_line):
            command.tree_node_name = command.parent_function
            
        elif command.quantum_or_classical == "quantum" and command.line_type != "measurement":
            op = command.code_line

            if command.line_type == "call" and "@qp.qnode" not in str(op):
                method = next(method for method in method_names if method in op)
                if method:
                    command.tree_node_name = method

            elif isinstance(op, (qp.ops.Controlled, qp.ops.Adjoint, qp.ops.Conditional)):
                base_label, num_controls, is_adjoint = helpers.unwrap_op(op)
                adjoint_suffix = "†" if is_adjoint else ""
                command.tree_node_name = "C" * num_controls + base_label + adjoint_suffix

            else:
                command.tree_node_name = op.label()

        # Quantum measurement
        elif command.line_type == "measurement":
            command.tree_node_name = "⎋"

        else:
            code_line = command.code_line

            if command.line_type == "scf":
                for keyword in SCF_KEYWORDS:
                    if code_line.startswith(keyword.strip() + " ") or code_line.startswith(
                        keyword.strip() + ":"
                    ):
                        command.tree_node_name = keyword.strip()
                        break
                else:
                    command.tree_node_name = "scf"  # Fallback for scf

            elif "def " in code_line:
                command.tree_node_name = code_line.split("def ")[1].split("(")[0].strip()

            elif "(" in code_line:
                command.tree_node_name = code_line.split("(")[0].strip().split(".")[-1]

            elif command.line_type == "return":
                command.tree_node_name = "return"

            # Fallback
            else:
                command.tree_node_name = code_line



def update_condition_context(commands):
    """Updates the condition context for each command.

    Args:
        commands (List[Command Objects]): List of command objects
    """
    for command in commands:
        if command.parent_function in ("if", "elif", "if(", "elif("):
            parent_command = helpers.get_command_by_identifier(
                commands, command.parent_id
            )
            command.condition_context = (
                f"(line {parent_command.line_number}) {parent_command.code_line}"
            )


def clobber_classical_conditions(commands, all_commands, clobbered_nodes=None):
    """
    Recursively removes scf nodes with 'if'/'elif' in their code_line from the tree.
    Replaces each such node with its children, updating parent_id accordingly.
    Processes bottom-up so nested conditionals are handled correctly.

    Args:
        commands (List[Command Objects]): List of command objects
        all_commands (List[Command Objects]): Flattened list of all command objects in the command tree
        clobbered_nodes (List[Command Objects], optional): if provided, every if/elif
            node removed from the tree is appended here (with clobbered_parent set to
            its true parent) so it can still be found later, e.g. for debugger stepping,
            even though it's no longer reachable via the tree's children.
    """
    if commands:
        for command in commands:
            if command.children:
                clobber_classical_conditions(command.children, all_commands, clobbered_nodes)

        parent_command = helpers.get_command_by_identifier(
            all_commands, commands[0].parent_id
        )

        # flattening out any scf if/elif nodes
        new_children = []
        for command in commands:
            code_line = command.code_line
            if command.line_type == "scf" and any(keyword in code_line for keyword in CLASSICAL_CONDITION_KEYWORDS):
                # Reparent the scf node's children before flattening
                for child in command.children:
                    child.parent_id = command.parent_id
                new_children.extend(command.children)
                if clobbered_nodes is not None:
                    command.clobbered_parent = parent_command
                    clobbered_nodes.append(command)
            else:
                new_children.append(command)

        if parent_command:
            parent_command.children = new_children


def update_command_images(
    commands,
    device_name,
    num_wires,
    num_shots,
    all_commands,
    postselect_overrides=None,
    is_qnode=False,
):
    """Updates the subtree circuit img for each command in the command tree

    Args:
        root_command(Command Object): the root command in the command tree
        device_name (string): Name of the PennyLane device
        num_wires (int): Number of wires in the circuit
        num_shots (int): Number of shots for the device
        postselect_overrides (dict{string: int}): mapping of mid circuit measurement command id -> postselect value (0 or 1) in debugger mode
    """

    if is_qnode:
        commands = [commands]

    for command in commands:
        if len(command.children) > 0:
            command.subtree_circuit_img = helpers.get_image_bs64_bytecode(
                helpers.draw_circuit(
                    command.children,
                    device_name,
                    num_wires,
                    num_shots,
                    all_commands,
                    postselect_overrides,
                )
            )
            update_command_images(
                command.children,
                device_name,
                num_wires,
                num_shots,
                all_commands,
                postselect_overrides,
            )


def merge_scf_calls(commands, clobbered_nodes=None):
    """Collapses consecutive duplicate scf nodes into one, merging their children

    Example:

    given some code:

    for _ in range(2):
        qp.X(0)

    Upon execution the trace would reflect 3 separate 'for' calls,
    the first and second both having a child of qp.X(0), and the last is simply
    a final comparison check to see if the loop has iterated past its bounds and signals to return,

    After merging this scf call, there will only be one 'for' call
    that has 2 qp.X(0) in its children attribute

    This can scale up to as many iterations of the loop there is.

    Args:
        commands (List[Command Objects]): List of command objects with unmerged scf calls
        clobbered_nodes (List[Command Objects], optional): if/elif nodes already clobbered
            out of the tree (see clobber_classical_conditions). A clobbered node's
            clobbered_parent may point at a duplicate scf node that this function is
            about to discard; when that happens, clobbered_parent is redirected to the
            surviving merged node so it stays resolvable later (e.g. for debugger stepping).
    Returns:
        commands (List[Command Objects]): List of command objects with the duplicate scf calls merged

    """
    for command in commands:
        if len(command.children) > 0:
            merge_scf_calls(command.children, clobbered_nodes)

    scf_commands = [cmd for cmd in commands if cmd.line_type == "scf" and len(cmd.children) > 0]

    # Merge duplicates by building a new list
    merged = []
    for scf in scf_commands:
        if (
            merged
            and scf.code_line == merged[-1].code_line
            and scf.line_number == merged[-1].line_number
            and scf.parent_id == merged[-1].parent_id
        ):
            merged[-1].children.extend(scf.children)
            for child in merged[-1].children:
                child.parent_id = merged[-1].identifier
            if clobbered_nodes is not None:
                for clobbered in clobbered_nodes:
                    if clobbered.clobbered_parent is scf:
                        clobbered.clobbered_parent = merged[-1]
        else:
            merged.append(scf)

    # Rebuild commands in-place: keep non-scf nodes, replace scf nodes with merged ones
    merged_iter = iter(merged)
    new_commands = []
    current_merged = next(merged_iter, None)

    for command in commands:
        if command.line_type == "scf" and len(command.children) > 0:  # ignore empty scf
            if current_merged is None:
                pass
            elif (
                command.code_line == current_merged.code_line
                and command.line_number == current_merged.line_number
                and command.parent_id == current_merged.parent_id
            ):
                if not new_commands or new_commands[-1] is not current_merged:
                    new_commands.append(current_merged)
            else:
                current_merged = next(merged_iter, None)
                if current_merged is not None:
                    new_commands.append(current_merged)
        elif command.line_type != "scf":  # keep all non-scf nodes
            new_commands.append(command)

    commands[:] = new_commands
    return commands


def get_fcn_output_from_tree(root, device_name, num_shots, num_wires):
    """Return the main QNode output by executing all quantum operations in the command tree.

    Collects quantum commands from the tree in depth-first order, separates measurement
    operations from gate operations, and runs them through a PennyLane QNode.

    Args:
        root (Command Object): The root command node of the tree. Its children are traversed
            to collect all quantum operations.
        device_name (string): Name of the PennyLane device to run the circuit on (e.g. "default.qubit").
        num_wires (int): Number of wires in the quantum circuit.
        num_shots (int): Number of shots for the device. If 0, runs in exact (analytic) mode.

    Returns:
        tuple(Any, float): A tuple of:
            - The QNode output (e.g. expectation values, samples, or probabilities).
            - The time in seconds taken to execute the circuit.
    """
    try:
        dev = qp.device(device_name)
    except:
        dev = qp.device(device_name, wires=num_wires)

    quantum_commands = helpers.collect_quantum_commands(root.children)

    # Mid-circuit measurements should be part of the regular execution.
    # Terminal measurements are those that define the QNode return.
    terminal_measurement_commands = [
        c for c in quantum_commands if c.line_type == "measurement"
    ]
    non_terminal_measurement_commands = [
        c for c in quantum_commands if c.line_type != "measurement" and type(c.code_line) != str
    ]
    if not terminal_measurement_commands:
        # Fallback if no terminal measurements found
        @qp.set_shots(shots=num_shots or None)
        @qp.qnode(dev)
        def circuit():
            for c in non_terminal_measurement_commands:
                qp.apply(c.code_line)
            return qp.state()

    else:
        last_command = terminal_measurement_commands[-1]

        @qp.set_shots(shots=num_shots or None)
        @qp.qnode(dev)
        def circuit():
            for c in non_terminal_measurement_commands:
                qp.apply(c.code_line)
            return [qp.apply(i) for i in reversed(last_command.code_line)]

    exec_time = time.time()
    output = circuit()

    return output, time.time() - exec_time
