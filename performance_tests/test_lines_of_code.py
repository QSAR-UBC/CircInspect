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
the number of lines in the user code
"""
import time
from helpers import visCircuit

RERUNS_PER_CASE = 10
MIN_LINES = 10  # required to be at least 7
MAX_LINES = 200


def test_generator(num_lines):
    code = """
import pennylane as qml
dev = qml.device("default.qubit", wires=1)
@qml.qnode(dev)
def circuit():"""
    for _ in range(num_lines - 6):  # -6 for 6 lines that are required to be in the code
        code += """
    qml.Hadamard(wires=0)"""
    code += """
    return qml.probs()
circuit()
"""
    return code


with open("num_lines_of_code_results_" + str(time.time()) + ".csv", "w") as results_file:
    results_file.write("num_lines_of_code,s_total,s_processing_no_exec\n")
    for num_lines in range(MIN_LINES, MAX_LINES, 10):
        print("Starting run, num_lines:", num_lines)
        for i in range(RERUNS_PER_CASE):
            start = time.time()
            processing_time = visCircuit(test_generator(num_lines))
            end = time.time()
            if processing_time > 0:
                results_file.write(
                    str(num_lines) + "," + str(end - start) + "," + str(processing_time) + "\n"
                )
