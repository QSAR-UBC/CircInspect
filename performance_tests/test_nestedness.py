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
the nestedness of subroutines in the user code, independent of gate
count/circuit depth.
"""
import textwrap
import time

from helpers import vis_circuit_timed

RERUNS_PER_CASE = 10
MIN_CALLS = 10  # required to be at least 1
MAX_CALLS = 200


def test_generator(num_calls):
    funcs = ["def f0():\n    pass"]
    funcs += [f"def f{i}():\n    f{i - 1}()" for i in range(1, num_calls)]
    func_defs = "\n\n".join(funcs)

    return textwrap.dedent("""\
        import pennylane as qp

        {func_defs}


        dev = qp.device("default.qubit", wires=1)


        @qp.qnode(dev)
        def circuit():
            f{last}()
            return qp.probs()
        circuit()
    """).format(func_defs=func_defs, last=num_calls - 1)


def run():
    with open(f"nestedness_results_{time.time()}.csv", "w") as results_file:
        results_file.write("nestedness,total_time,processing_time,execution_time\n")
        for num_calls in range(MIN_CALLS, MAX_CALLS, 10):
            print("Starting run, nestedness:", num_calls)
            for _ in range(RERUNS_PER_CASE):
                result = vis_circuit_timed(test_generator(num_calls))
                if result is not None:
                    results_file.write(
                        f"{num_calls},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
