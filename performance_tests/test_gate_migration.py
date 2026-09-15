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
An experiment to characterize how execution/processing time changes as
gates move from being inline inside a qnode to living in individual
single-gate helper functions called from the qnode. The total gate count
stays fixed at TOTAL_GATES; only the split between "inline" and "via a
one-gate helper function" changes.
"""
import textwrap
import time

from helpers import vis_circuit_timed

RERUNS_PER_CASE = 10
TOTAL_GATES = 200
STEP = 10


def test_generator(gates_outside, total_gates=TOTAL_GATES):
    gates_inside = total_gates - gates_outside

    helper_defs = "\n\n".join(
        f"def helper_gate_{i}():\n    qp.Hadamard(wires=0)" for i in range(gates_outside)
    )
    body_lines = ["    qp.Hadamard(wires=0)"] * gates_inside
    body_lines += [f"    helper_gate_{i}()" for i in range(gates_outside)]
    body = "\n".join(body_lines)

    return textwrap.dedent("""\
        import pennylane as qp
        dev = qp.device("default.qubit", wires=1)

        {helper_defs}

        @qp.qnode(dev)
        def circuit():
        {body}
            return qp.probs()
        circuit()
    """).format(helper_defs=helper_defs, body=body)


def run():
    with open(f"gate_migration_results_{time.time()}.csv", "w") as results_file:
        results_file.write("gates_outside,total_time,processing_time,execution_time\n")
        for gates_outside in range(0, TOTAL_GATES + 1, STEP):
            print("Starting run, gates_outside:", gates_outside)
            for _ in range(RERUNS_PER_CASE):
                result = vis_circuit_timed(test_generator(gates_outside))
                if result is not None:
                    results_file.write(
                        f"{gates_outside},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
