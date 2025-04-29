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
quantum circuit depth
"""
import time
from helpers import visCircuit

RERUNS_PER_CASE = 10
MIN_DEPTH = 2
MAX_DEPTH = 21
NUM_QUBITS = 10


def depth_test_generator(num_qubits, depth):
    return (
        """wires = """
        + str(num_qubits)
        + """
depth = """
        + str(depth)
        + """
import pennylane as qml
import numpy as np
import random
from functools import partial
dev = qml.device('default.qubit', wires=wires)

def add_gates(i):
     qml.IsingYY(random.uniform(0,1) * 3.14, [i,i+1])

@qml.qnode(dev)
def circuit(iters):
  for _ in range(iters):
    for i in range(wires - 1):
      add_gates(i)
  return qml.expval(qml.Z(0))

circuit(depth)
"""
    )


with open("depth_results_" + str(time.time()) + ".csv", "w") as results_file:
    results_file.write("iterations,s_total,s_processing_no_exec\n")
    for depth in range(MIN_DEPTH, MAX_DEPTH, 1):
        print("Starting run, num_qubits:", NUM_QUBITS, "depth(iterations):", depth)
        for i in range(RERUNS_PER_CASE):
            start = time.time()
            processing_time = visCircuit(depth_test_generator(NUM_QUBITS, depth))
            end = time.time()
            if processing_time > 0:
                results_file.write(
                    str(depth) + "," + str(end - start) + "," + str(processing_time) + "\n"
                )
