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
An experiment to characterize how execution time is affected by
the number of qubits used by the quantum circuit
"""
from helpers import visCircuit
import time

RERUNS_PER_CASE = 10
MIN_QUBIT = 2
MAX_QUBIT = 21
DEPTH = 10


def num_qubits_test_generator(num_qubits, depth):
    return (
        """num_qubits = """
        + str(num_qubits)
        + """
depth = """
        + str(depth)
        + """

import pennylane as qml
import numpy as np
import random

def add_gates(i):
     qml.IsingYY(random.uniform(0,1) * 3.14, [i,i+1])

dev = qml.device('default.qubit', wires=num_qubits)
@qml.qnode(dev)
def circuit(num_qubits,depth):
    for _ in range(depth):
        j = 0
        while j < num_qubits - 1:
            add_gates(j)
            j += 2
    return qml.expval(qml.Z(0))
circuit(num_qubits,depth)"""
    )


with open("num_qubits_results_" + str(time.time()) + ".csv", "w") as results_file:
    results_file.write("num_qubits,s_total,s_processing_no_exec\n")
    for num_qubits in range(MIN_QUBIT, MAX_QUBIT, 2):
        print("Starting run, num_qubits:", num_qubits, "depth:", DEPTH)
        for i in range(RERUNS_PER_CASE):
            start = time.time()
            processing_time = visCircuit(num_qubits_test_generator(num_qubits, DEPTH))
            end = time.time()
            if processing_time > 0:
                results_file.write(
                    str(num_qubits) + "," + str(end - start) + "," + str(processing_time) + "\n"
                )
