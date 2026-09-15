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


class PlaceholderOperation(qp.operation.Operation):
    """Placeholder gate used by draw_circuit to render a collapsed command
    tree block (a call or scf node) as a single named box on the circuit
    diagram, instead of expanding its individual operations.
    """

    grad_method = "A"

    def __init__(self, wires, op_name, id=None):
        self.op_name = op_name
        super().__init__(wires=wires, id=id)

    def label(self, decimals=None, base_label=None, cache=None):
        return super().label(decimals=decimals, base_label=base_label or self.op_name, cache=cache)

    @classmethod
    def compute_decomposition(cls, wires):
        return [qp.QubitUnitary(np.eye(len(wires)), wires=wires)]
