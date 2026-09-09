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
An experiment to characterize how execution time is affected by
the number of subroutine calls in the main subroutine, independent of
circuit depth/gate count (that relationship is covered separately by
test_depth.py). The called subroutine is a no-op, so the circuit has no
real gates regardless of call count.
"""
import time
from helpers import vis_circuit_timed

RERUNS_PER_CASE = 10
MIN_CALLS = 10  # required to be at least 1
MAX_CALLS = 200


def test_generator(num_calls):
    code = """
import pennylane as qp
def a():
    pass
dev = qp.device("default.qubit", wires=1)
@qp.qnode(dev)
def circuit():"""
    for _ in range(num_calls):
        code += """
    a()"""
    code += """
    return qp.probs()
circuit()
"""
    return code


def run():
    with open("num_subroutine_calls_results_" + str(time.time()) + ".csv", "w") as results_file:
        results_file.write("num_subroutine_calls,total_time,processing_time,execution_time\n")
        for num_calls in range(MIN_CALLS, MAX_CALLS, 10):
            print("Starting run, num_subroutine_calls:", num_calls)
            for i in range(RERUNS_PER_CASE):
                result = vis_circuit_timed(test_generator(num_calls))
                if result is not None:
                    results_file.write(
                        f"{num_calls},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
