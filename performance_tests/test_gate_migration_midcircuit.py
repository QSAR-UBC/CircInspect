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
An experiment combining the gate-migration and mid-circuit measurement
benchmarks: the "unit" being moved from inline-in-the-qnode to an
individual outside helper function is a mid-circuit measurement paired
with a conditional gate. The total number of units stays fixed at
TOTAL_UNITS; only the inside/outside split changes.
"""
import textwrap
import time

from helpers import vis_circuit_timed

RERUNS_PER_CASE = 10
TOTAL_UNITS = 12
STEP = 2


def test_generator(units_outside, total_units=TOTAL_UNITS):
    units_inside = total_units - units_outside

    helper_defs = "\n\n".join(
        f"def helper_unit_{i}():\n    m = qp.measure(0)\n    qp.cond(m, qp.X)(wires=1)"
        for i in range(units_outside)
    )
    body_lines = [
        f"    m_in_{i} = qp.measure(0)\n    qp.cond(m_in_{i}, qp.X)(wires=1)"
        for i in range(units_inside)
    ]
    body_lines += [f"    helper_unit_{i}()" for i in range(units_outside)]
    body = "\n".join(body_lines)

    return textwrap.dedent("""\
        import pennylane as qp
        dev = qp.device("default.qubit")

        {helper_defs}

        @qp.qnode(dev)
        def circuit():
        {body}
            return qp.probs(wires=[0, 1])
        circuit()
    """).format(helper_defs=helper_defs, body=body)


def run():
    with open(f"gate_migration_midcircuit_results_{time.time()}.csv", "w") as results_file:
        results_file.write("units_outside,total_time,processing_time,execution_time\n")
        for units_outside in range(0, TOTAL_UNITS + 1, STEP):
            print("Starting run, units_outside:", units_outside)
            for _ in range(RERUNS_PER_CASE):
                result = vis_circuit_timed(test_generator(units_outside))
                if result is not None:
                    results_file.write(
                        f"{units_outside},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
