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
the nestedness of subroutines in the user code
"""
import time
from helpers import visCircuit


RERUNS_PER_CASE = 10
MIN_CALLS = 10  # required to be at least 1
MAX_CALLS = 200


def test_generator(num_calls):
    code = """
import pennylane as qml
def f0():
    qml.Hadamard(wires=0)
"""
    for i in range(1, num_calls):
        code += (
            """
def f"""
            + str(i)
            + """():
    f"""
            + str(i - 1)
            + """()
"""
        )
    code += (
        """
dev = qml.device("default.qubit", wires=1)
@qml.qnode(dev)
def circuit():
    f"""
        + str(num_calls - 1)
        + """()
    return qml.probs()
circuit()
"""
    )
    return code


with open("nestedness_results_" + str(time.time()) + ".csv", "w") as results_file:
    results_file.write("nestedness,s_total,s_processing_no_exec\n")
    for num_calls in range(MIN_CALLS, MAX_CALLS, 10):
        print("Starting run, nestedness:", num_calls)
        for i in range(RERUNS_PER_CASE):
            start = time.time()
            processing_time = visCircuit(test_generator(num_calls))
            end = time.time()
            if processing_time > 0:
                results_file.write(
                    str(num_calls) + "," + str(end - start) + "," + str(processing_time) + "\n"
                )
