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

"""This module provides the command object used for code processing"""


class Command:
    """A command object representing one line of quantum or classical operation

    Attributes:
        function: the name of the function this line is a part of.
        line_number: the line number of the code related to this operation
        code_line: string of the line written by the user or the pennylane operation
        line_type: string or pennylane operation
        quantum_or_classical: whether the operation is a pennylane operation or classical python operation.
    """

    def __init__(
        self,
        parent_function,
        line_number,
        code_line,
        line_type,
        quantum_or_classical,
        indent,
    ):
        self.parent_function = parent_function
        self.line_number = line_number
        self.code_line = code_line
        self.line_type = line_type
        self.quantum_or_classical = quantum_or_classical
        self.identifier = None
        self.parent_id = None
        self.children = []
        self.arguments = None
        self.indent = indent
        self.tree_node_name = None
        self.subtree_circuit_img = None
        self.node_dimmed = False
        self.active_debug = False
        self.visible = False
        self.clobbered_parent = None
        self.output = None
        self.condition_context = None
        self.postselect_value = None
        self.is_mid_measure = False
        self.measurements = set()

    def __repr__(self):
        return (
            "Command"
            + "\n    parent_function: "
            + str(self.parent_function)
            + "\n    line_number: "
            + str(self.line_number)
            + "\n    code_line: "
            + str(self.code_line)
            + "      $TYPE: "
            + str(type(self.code_line))
            + "\n    line_type: "
            + str(self.line_type)
            + "\n    quantum_or_classical: "
            + str(self.quantum_or_classical)
            + "\n    identifier: "
            + str(self.identifier)
            + "\n    parent_id: "
            + str(self.parent_id)
            + "\n    children: "
            + str(self.children)
            + "\n    arguments: "
            + str(self.arguments)
            + "\n    indent: "
            + str(self.indent)
            + "\n    tree_node_name: "
            + str(self.tree_node_name)
            + "\n    condition_context: "
            + str(self.condition_context)
            + "\nEnd of Command"
        )
