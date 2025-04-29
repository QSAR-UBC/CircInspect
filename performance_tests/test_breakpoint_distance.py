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
An experiment to characterize how execution time is affected by breakpoint
distance
"""

import time
from helpers import debug_circuit

RERUNS_PER_CASE = 10
MIN_DIST = 10
MAX_DIST = 200


def test_generator(num_lines):
    code = """
import pennylane as qml
dev = qml.device("default.qubit", wires=1)
@qml.qnode(dev)
def circuit():"""
    for _ in range(num_lines):
        code += """
    qml.Hadamard(wires=0)"""
    code += """
    return qml.probs()
circuit()
"""
    return code


with open("breakpoint_distance_results_" + str(time.time()) + ".csv", "w") as results_file:
    results_file.write(
        "Breakpoint Distance,Total Processing Time(s),CircInspect Functionality Time(s)\n"
    )
    code = test_generator(MAX_DIST)
    for dist in range(MIN_DIST, MAX_DIST, 10):
        print("Starting run, dist:", dist)
        for i in range(RERUNS_PER_CASE):
            processing_time, no_exec_time = debug_circuit(code, dist)
            if processing_time > 0:
                results_file.write(
                    str(dist) + "," + str(processing_time) + "," + str(no_exec_time) + "\n"
                )
