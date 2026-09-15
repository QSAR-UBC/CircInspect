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
An experiment to characterize how execution time is affected by breakpoint
distance
"""

import time
from helpers import _make_session_id, debug_output_timed, prepare_debug

RERUNS_PER_CASE = 10
MIN_DIST = 10
MAX_DIST = 200


def test_generator(num_lines):
    code = """
import pennylane as qp
dev = qp.device("default.qubit", wires=1)
@qp.qnode(dev)
def circuit():"""
    for _ in range(num_lines):
        code += """
    qp.Hadamard(wires=0)"""
    code += """
    return qp.probs()
circuit()
"""
    return code


def run():
    session_id = _make_session_id()
    code = test_generator(MAX_DIST)
    prepare_debug(code, session_id)
    with open("breakpoint_distance_results_" + str(time.time()) + ".csv", "w") as results_file:
        results_file.write("breakpoint_distance,total_time,processing_time,execution_time\n")
        for dist in range(MIN_DIST, MAX_DIST, 10):
            print("Starting run, dist:", dist)
            for i in range(RERUNS_PER_CASE):
                result = debug_output_timed(session_id, dist)
                if result is not None:
                    results_file.write(
                        f"{dist},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
