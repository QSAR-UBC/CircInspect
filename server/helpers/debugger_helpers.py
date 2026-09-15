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
import matplotlib

matplotlib.use("Agg")
from server.command import Command
from server import helpers
from pennylane.tape import QuantumScript


def get_full_tree(root_command, code, annotated_queue, user_transforms, method_names, env=None):
    """Constructs a hierarchical command tree for the debugger, incorporating quantum transforms.

    This function builds a series of command trees starting from the base circuit
    and iteratively applying each transform found in the code. It creates a "root"
    debugger command that holds these trees as branches, allowing the user to
    navigate between the original code and its transformed states.

    Args:
        root_command (Command): The root command of the un-transformed circuit.
        code (string): The raw source code of the circuit.
        annotated_queue (AnnotatedQueue): The PennyLane operation queue.
        env (dict): The execution environment dictionary.

    Returns:
        tuple(Command, List[Command Object]): The top-level 'root' command containing
        all debugger-visible branches, and the flattened list of every command in that
        tree (already computed here, so callers don't need to flatten it again).
    """
    transforms = helpers.get_transform_details(code)
    debugger_commands = [root_command]
    transformed_tape = qp.tape.QuantumScript.from_queue(annotated_queue)

    if user_transforms and len(user_transforms) > 0:
        for transform_index, transform in enumerate(user_transforms):
            transform_root = Command(
                parent_function=None,
                line_number=transforms[transform_index][1],
                code_line=transforms[transform_index][0],
                line_type="transform",
                quantum_or_classical="classical",
                indent=root_command.indent,
            )
            transform_root.tree_node_name = root_command.tree_node_name
            debugger_commands.append(transform_root)

            transformed_tape = helpers.get_transformed_queue_items(
                [user_transforms[transform_index]],
                transformed_tape.circuit,
            )

            transform_root = helpers.generate_transformed_command_tree(
                transform_root, transformed_tape, method_names
            )

    debugger_root = Command(
        parent_function=None,
        line_number=None,
        code_line=None,
        line_type="root",
        quantum_or_classical=None,
        indent=0,
    )

    debugger_root.children = debugger_commands
    flat_commands = helpers.flatten_tree(debugger_root)
    # Splice each clobbered command (if/else statements) back into flat_commands, positioned right before the branch that
    # replaced it so debugger stepping visits it in the correct execution order.

    clobbered_conditions = getattr(root_command, "clobbered_conditions", None) or []
    for clobbered in clobbered_conditions:
        if not clobbered.children:
            continue
        anchor = clobbered.children[0]
        if anchor not in flat_commands:
            continue
        clobbered.children = []
        flat_commands.insert(flat_commands.index(anchor), clobbered)

    helpers.update_identifier_numbers(flat_commands)
    debugger_update_identifier_called_from(flat_commands)

    for clobbered in clobbered_conditions:
        if clobbered.clobbered_parent is not None:
            clobbered.parent_id = clobbered.clobbered_parent.identifier

    return debugger_root, flat_commands


def debugger_update_identifier_called_from(debugger_commands):
    """Recursively updates the parent_id attribute for children.

    Args:
        debugger_commands (List[Command Objects]): A list of command nodes to process.
    """
    for command in debugger_commands:
        for child in command.children:
            child.parent_id = command.identifier
        debugger_update_identifier_called_from(command.children)


def set_active_debug_command(commands, debug_index):
    """Updates the active_debug attribute on the command that the debugger is currently on to true, and makes it false for all the other commands.

    Uses a boolean mask array where only the position at debug_index is True.

    Args:
        commands (List[Command Objects]): List of command objects, each may have children.
        debug_index (int): the index of the command in the commands list which is currently active.
    """
    mask = [i == debug_index for i in range(len(commands))]
    for command, is_active in zip(commands, mask):
        command.active_debug = is_active


def run_pennylane_commands(commands, device_name, num_shots, num_wires, last_command, debug_identifier):
    """Takes pennylane commands from commands list and runs them to get circuit output.

    Args:
        commands (List[Command Objects]): A list of commands
        device_name (string): The name of the device to use
        num_wires (int): The number of wires in the circuit
        num_shots (int): The number of shots to use
        last_command (List[qp.Operation]): The last command in the circuit, usually measurements
        debug_identifier (int): The identifier of the command to break at

    Returns:
        The output of evaluating the sequence of PennyLane operations in a circuit.
    """
    try:
        dev = qp.device(device_name)
    except:
        dev = qp.device(device_name, wires=num_wires)

    @qp.set_shots(shots=num_shots or None)
    @qp.qnode(dev)
    def circuit():
        for c in commands:
            if c.identifier == debug_identifier:
                break
            if c.quantum_or_classical == "classical" or len(c.children) > 0:
                continue
            if c.line_type == "measurement":
                continue
            if c.quantum_or_classical == "quantum":
                qp.apply(c.code_line)
        return [qp.apply(i) for i in last_command]

    return circuit()


def pop_transform(transform_stack, commands):
    """Removes the most recent transform from the stack and returns the
    active transform identifier and its index in the commands list.

    Args:
        transform_stack (List[int]): The stack of identifiers for active transforms.
        commands (List[Command Objects]): The full list of commands for the current execution.

    Returns:
        current_transform (int): The new current transform identifier.
        current_transform_index (int): The index of the new current transform in the commands list.
        Returns -1 and 1 if the stack becomes empty.
    """
    NO_ACTIVE_TRANSFORM = -1
    DEFAULT_INDEX = 1

    transform_stack.pop()
    if len(transform_stack) == 0:
        return NO_ACTIVE_TRANSFORM, DEFAULT_INDEX
    else:
        current_transform = transform_stack[-1]
        for i, cmd in enumerate(commands):
            if cmd.identifier == current_transform:
                return current_transform, i
