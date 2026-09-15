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
import io
from collections import deque
import tokenize
from server.command import Command
from server import helpers


def comment_out_transforms(code):
    """Comments out all transforms from the code and returns it

    Args:
        code(string): String representation of user code

    Returns:
        String: The code updated with all transforms commented out
    """
    code_arr = code.split("\n")
    transform_lines = [t[1] for t in get_transform_details(code)]

    for i in range(len(code_arr)):
        if (i + 1) in transform_lines:  # add 1 to account for 0-based indexing of code_arr
            if not code_arr[i].lstrip().startswith("#"):
                code_arr[i] = "#" + code_arr[i]

    return "\n".join(code_arr)


def get_transform_details(code):
    """Returns the names of transforms applied to QNode and line numbers on which
       they are applied

    Args:
        code(string): String representation of user code

    Returns:
        List[[string, int]]: List of lists of transform name and
        line number on which its applied
    """
    transforms_details = deque([])
    code_arr = code.split("\n")
    tokens = list(tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline))
    idx = helpers.find_first_qnode_decorator(tokens)

    # find possible transform decorators (type is OP, string is @ and
    # not a qnode) from tokens and get a list of their line numbers
    possible_transforms = list(
        map(
            lambda t: t.start[0] - 1,
            filter(
                lambda t: (
                    t.type == tokenize.OP and t.string == "@" and "@qp.qnode(" not in t.line
                ),
                tokens,
            ),
        )
    )

    for possible_transform_index in possible_transforms:
        if _is_valid_transform(code_arr[possible_transform_index], code_arr):
            transforms_details.append(
                [code_arr[possible_transform_index], possible_transform_index + 1]
            )

    transforms_details.reverse()  # reverse so that the list is in order of transform application

    return transforms_details


def _is_valid_transform(line, code_arr):
    """Checks if a potential transform is a valid transform

    Args:
        line(string): The decorator line from the code
        code_arr(List[string]): The full code as a list of lines

    Returns:
        bool: True if it's a valid transform, False otherwise
    """
    name = line.strip().lstrip("@").split("(")[0].split(".")[-1]
    obj = getattr(qp.transforms, name, None)
    if isinstance(obj, qp.transforms.core.TransformDispatcher):
        return True  # valid pennylane transform
    else:
        for i, line in enumerate(code_arr):
            stripped = line.strip()
            if stripped in ("@qp.transform", "@qp.transform()"):
                next_lines = [l.strip() for l in code_arr[i + 1 :] if l.strip()]
                if next_lines and next_lines[0].startswith(f"def {name}("):
                    return True  # valid custom transform
    return False


def get_transform_func(transform, env=None):
    """Evaluates and returns the transform function from its string representation

    Args:
        transform(List[string, int]): Array containing transform string and line number
        env(dict): Environment to evaluate the transform in

    Returns:
        Function: The evaluated transform function
    """
    transform_string = transform[0].lstrip().lstrip("@")
    if env is None:
        env = globals()
    try:
        func = eval(transform_string, env)
        return func
    except Exception as e:
        print(f"Failed to evaluate transform {transform_string}: {e}", flush=True)


def get_transformed_queue_items(transform_functions, queue):
    """Applies a list of transforms to the operation queue and returns the transformed tape

    Args:
        transform_functions(Array[Function]): List of PennyLane transform functions
        queue(Array[qp.operation.Operation]): List of PennyLane operations and measurements

    Returns:
        qp.tape.QuantumScript: The transformed tape containing operations and measurements
    """

    try:
        ops = [
            op
            for op in queue
            if isinstance(op, qp.operation.Operation) or isinstance(op, qp.ops.MidMeasure)
        ]
        measurements = [op for op in queue if isinstance(op, qp.measurements.MeasurementProcess)]

        tape = qp.tape.QuantumScript(ops=ops, measurements=measurements)

        for transform in transform_functions:
            tapes, fn = transform(tape)  # standard PennyLane transform contract
            tape = tapes[0]

        return tape

    except Exception as e:
        print(f"Transform application failed: {e}", flush=True)


def generate_transformed_command_tree(root_command, tape, method_names):
    """Generates a command tree for transformed operations and attaches it to the root command

    Args:
        root_command(Command Object): The root command to attach children to
        tape(qp.tape.QuantumScript): The transformed tape containing circuit operations

    Returns:
        Command Object: The updated root command with transformed children
    """

    TYPE_MAP = {
        qp.ops.MidMeasure: "mid_measurement",
        qp.ops.Conditional: "cond",
        qp.measurements.MeasurementProcess: "measurement",
    }

    transformed_commands = []

    for op in tape.circuit:
        line_type = next(
            (line_type for data_type, line_type in TYPE_MAP.items() if isinstance(op, data_type)),
            "line",
        )
        transformed_commands.append(
            Command(
                parent_function=root_command.tree_node_name,
                line_number=None,
                code_line=op if op in tape.operations else [op],
                line_type=line_type,
                quantum_or_classical="quantum",
                indent=0,
            )
        )
    root_command.children = transformed_commands
    helpers.update_identifier_numbers([root_command] + transformed_commands)
    helpers.update_tree_node_names([root_command] + transformed_commands, method_names)
    for command in transformed_commands:
        command.parent_id = root_command.identifier
    helpers.link_mid_circuit_measurements([root_command] + transformed_commands)

    return root_command


def get_user_transforms(code, method_names, qnode):
    """Retrieves the compile pipeline from the given QNode.

    Args:
        code(string): String representation of user code (unused, kept for API compatibility).
        method_names(set[string]): Names of methods in the code (unused, kept for API compatibility).
        qnode: The QNode object to extract the compile pipeline from.

    Returns:
        TransformProgram or None: The extracted compile pipeline.
    """
    try:
        pipeline = qnode.compile_pipeline
        return pipeline
    except Exception as e:
        print(f"DEBUG: Error extracting compile pipeline: {e}")
    return None
