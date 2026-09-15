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
the number of lines in the user code, independent of circuit depth/gate
count (that relationship is covered separately by test_depth.py). Each
added line is a no-op assignment (`i = 0`), not a gate, the generated
circuit contains no quantum gates at all, so only the source size grows.
"""
import textwrap
import time

from helpers import vis_circuit_timed

RERUNS_PER_CASE = 40  # bumped from 10: with a cheap/fast call, more reruns
# dilutes the effect of the occasional slow outlier call (GC pause,
# scheduling jitter, etc.) that was dominating the error bars.
MIN_LINES = 10  # required to be at least 7
MAX_LINES = 200


def test_generator(num_lines):
    num_filler_lines = num_lines - 7  # -7 for the 7 lines required to be in the code
    filler = "\n".join(["    i = 0"] * num_filler_lines)

    return textwrap.dedent("""\
        import pennylane as qp
        dev = qp.device("default.qubit", wires=1)


        @qp.qnode(dev)
        def circuit():
        {filler}
            return qp.probs()
        circuit()
    """).format(filler=filler)


def run():
    with open(f"num_lines_of_code_results_{time.time()}.csv", "w") as results_file:
        results_file.write("num_lines_of_code,total_time,processing_time,execution_time\n")
        for num_lines in range(MIN_LINES, MAX_LINES, 10):
            print("Starting run, num_lines:", num_lines)
            for _ in range(RERUNS_PER_CASE):
                result = vis_circuit_timed(test_generator(num_lines))
                if result is not None:
                    results_file.write(
                        f"{num_lines},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
