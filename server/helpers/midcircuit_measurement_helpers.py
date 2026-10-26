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
import matplotlib

matplotlib.use("Agg")
from server import helpers


def unwrap_to_conditional(op):
    """Peel off any Adjoint/Controlled layers and return the inner Conditional,
    or None if no Conditional is found anywhere in the wrapper chain.

    Args:
        op(qp.Operation): The operation to unwrap.

    Returns:
        qp.ops.Conditional or None: The innermost Conditional if present.
    """
    current = op
    while current is not None:
        if isinstance(current, qp.ops.Conditional):
            return current
        if isinstance(current, (qp.ops.Adjoint, qp.ops.Controlled)) and hasattr(current, "base"):
            current = current.base
        else:
            break
    return None


def cond_references_measurement(cond_op, mid_op):
    """Check if a Conditional operation references a specific MidMeasureMP.

    Args:
        cond_op(qp.ops.Conditional): A PennyLane Conditional operation.
        mid_op(qp.measurements.MidMeasureMP): A PennyLane MidMeasureMP operation.

    Returns:
        bool: True if the Conditional references the given mid-circuit measurement.
    """
    meas_val = cond_op.meas_val
    if hasattr(meas_val, "measurements"):
        return mid_op in meas_val.measurements
    return False


def get_mid_measurements_recursive(command):
    """Recursively get all mid-circuit measurements in a command.

    Args:
        command(Command Object): The command we want to get the mid-circuit measurements of

    Returns:
        set[qp.measurements.MidMeasureMP]: The set of mid-circuit measurements
    """
    mid_measurements = set()
    if command.quantum_or_classical == "quantum" and type(command.code_line) is not str:
        inner_cond = unwrap_to_conditional(command.code_line)
        if inner_cond is not None:
            mid_measurements.update(inner_cond.meas_val.measurements)

    for child in command.children:
        mid_measurements.update(get_mid_measurements_recursive(child))
    return mid_measurements
    

def get_first_leaf_meas_val(command):
    """Finds the first quantum leaf inside a command and returns its Conditional meas_val if present."""
    if command.quantum_or_classical == "quantum" and type(command.code_line) is not str:
        inner = unwrap_to_conditional(command.code_line)
        if inner is not None:
            return inner.meas_val
    for child in command.children:
        res = get_first_leaf_meas_val(child)
        if res is not None:
            return res
    return None

def link_mid_circuit_measurements(commands, flat_commands=None):
    """Link conditional operations to their corresponding mid-circuit measurement command nodes
    by assigning them a shared index.

    Args:
        commands(List[Command Objects]): List of all command objects
        flat_commands(List[Command Object], optional): Pre-flattened commands rooted at
            commands[0], if the caller already has them, to avoid flattening again.
    """
    all_commands = flat_commands if flat_commands is not None else helpers.flatten_tree(commands[0])

    mid_measure_cmds = [c for c in all_commands if c.line_type == "mid_measurement"]
    
    cond_cmds = []
    for c in all_commands:
        if c.line_type == "cond":
            cond_cmds.append(c)
        elif c.quantum_or_classical == "quantum" and unwrap_to_conditional(c.code_line) is not None:
            if c not in cond_cmds:
                cond_cmds.append(c)
        elif c.line_type == "call" and isinstance(c.code_line, str) and "qp.cond" in c.code_line:
            if c not in cond_cmds:
                cond_cmds.append(c)

    mid_index = 1
    for mid_cmd in mid_measure_cmds:
        mid_cmd.is_mid_measure = True
        mid_op = mid_cmd.code_line

        has_dependents = False
        for cond_cmd in cond_cmds:
            meas_val = get_first_leaf_meas_val(cond_cmd)
            if meas_val is not None:
                if hasattr(meas_val, "measurements") and mid_op in meas_val.measurements:
                    cond_cmd.mid_measurement_index = mid_index
                    has_dependents = True

        if has_dependents:
            mid_cmd.mid_measurement_index = mid_index
            mid_index += 1


def apply_postselect_to_commands(commands, postselect_overrides):
    """Apply postselect values to MidMeasureMP operations in the command list.

    Args:
        commands(List[Command Objects]): List of all command objects
        postselect_overrides(dict{string: int}): mapping of mid circuit measurement command id -> postselect value (0 or 1) in debugger mode
    """
    for command in commands:
        if command.line_type == "mid_measurement" and hasattr(command, "mid_measurement_index"):
            measurement_id = str(command.mid_measurement_index)
            if measurement_id in postselect_overrides:
                postselect_value = postselect_overrides[measurement_id]
                if isinstance(command.code_line, MidMeasureMP):
                    mid_measure_op = command.code_line
                    postselect_val = int(postselect_value) if postselect_value is not None else None

                    # Developer Note: In PennyLane 0.44.0, postselection outcomes
                    # are stored within the `_hyperparameters` dictionary.
                    # We update it manually here to enforce the debugger's custom
                    # postselect values during tracing.
                    mid_measure_op._hyperparameters["postselect"] = postselect_val

                    command.postselect_value = postselect_val


def get_postselect_id_map(root_command, flat_commands=None):
    """Returns a map of measurement IDs to their postselect values.

    Args:
        root_command(Command Object): The root command of the quantum circuit
        flat_commands(List[Command Object], optional): Pre-flattened commands, if the
            caller already has them, to avoid flattening the tree again.

    Returns:
        id_map(dict{string: int}): mapping of measurement ID -> postselect value (0 or 1)
    """
    all_cmds = flat_commands if flat_commands is not None else helpers.flatten_tree(root_command)
    id_map = {}
    for cmd in all_cmds:
        if cmd.line_type == "mid_measurement" and isinstance(cmd.code_line, MidMeasureMP):
            if cmd.code_line.postselect is not None:
                id_map[cmd.code_line.meas_uid] = cmd.code_line.postselect
    return id_map


def is_conditional_node(command):
    """Determine whether a command represents a conditional operation: either
    a direct Conditional/qp.cond leaf, or a call site invoking qp.cond.

    Args:
        command(Command Object): The command to check

    Returns:
        bool: True if the command is a conditional node
    """
    if command.line_type == "cond":
        return True
    if command.quantum_or_classical == "quantum" and unwrap_to_conditional(command.code_line) is not None:
        return True
    if command.line_type == "call" and isinstance(command.code_line, str) and "qp.cond" in command.code_line:
        return True
    return False


def resolve_conditional_outcome(meas_val, ps_id_map):
    """Resolve whether a conditional's measurement value evaluates to True,
    given the fixed postselect outcomes recorded in ps_id_map.

    Args:
        meas_val(qp.measurements.MeasurementValue): The conditional's measurement value
        ps_id_map(dict{string: int}): mapping of measurement ID -> postselect value (0 or 1)

    Returns:
        bool or None: The concretized boolean outcome, or None if not all measurements
        this conditional depends on have a postselect override yet.

    Raises:
        ValueError: If PennyLane's MeasurementValue.concretize() fails.
    """
    if not all(measurement.meas_uid in ps_id_map for measurement in meas_val.measurements):
        return None

    ps_vals = {
        measurement: ps_id_map[measurement.meas_uid] for measurement in meas_val.measurements
    }
    try:
        return meas_val.concretize(ps_vals)
    except Exception as e:
        # Catching general Exception because PennyLane's MeasurementValue.concretize() can fail
        raise ValueError(f"Could not concretize measurement value: {str(e)}") from e


def prune_unexecuted_commands(command, ps_id_map):
    """Recursively removes children that are conditionally False.
    Only prunes if all measurements in the condition have a postselect override.

    Args:
        command(Command Object): The command object to prune
        ps_id_map(dict{string: int}): mapping of measurement ID -> postselect value (0 or 1)
    """
    if not command.children:
        return

    new_children = []
    for child in command.children:
        should_keep = True

        if is_conditional_node(child):
            meas_val = get_first_leaf_meas_val(child)
            if meas_val is not None:
                outcome = resolve_conditional_outcome(meas_val, ps_id_map)
                # `outcome` is None when not all measurements this condition
                # depends on have a postselect override yet.
                if outcome is not None and not outcome:
                    should_keep = False

        if should_keep:
            new_children.append(child)
            prune_unexecuted_commands(child, ps_id_map)

    command.children = new_children
