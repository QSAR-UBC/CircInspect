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

"""
An experiment to characterize how execution/processing time is affected by
the number of mid-circuit measurements (each paired with a conditional
gate) in the user code. Isolates the cost of CircInspect's mid-circuit
measurement linking (link_mid_circuit_measurements) as a function of count.
"""
import time
from helpers import vis_circuit_timed

RERUNS_PER_CASE = 10
MIN_MEASUREMENTS = 2
MAX_MEASUREMENTS = 13
STEP = 2


def test_generator(num_measurements):
    code = """
import pennylane as qp
dev = qp.device("default.qubit")
@qp.qnode(dev)
def circuit():"""
    for i in range(num_measurements):
        code += """
    m""" + str(i) + """ = qp.measure(0)
    qp.cond(m""" + str(i) + """, qp.X)(wires=1)
"""
    code += """
    return qp.probs(wires=[0, 1])
circuit()
"""
    return code


def run():
    with open("midcircuit_measurements_results_" + str(time.time()) + ".csv", "w") as results_file:
        results_file.write("num_mid_measurements,total_time,processing_time,execution_time\n")
        for num_measurements in range(MIN_MEASUREMENTS, MAX_MEASUREMENTS, STEP):
            print("Starting run, num_mid_measurements:", num_measurements)
            for i in range(RERUNS_PER_CASE):
                result = vis_circuit_timed(test_generator(num_measurements))
                if result is not None:
                    results_file.write(
                        f"{num_measurements},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
