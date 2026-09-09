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
the number of qubits used by the quantum circuit. DEPTH is fixed;
num_qubits is swept.
"""
import textwrap
import time

from helpers import vis_circuit_timed

RERUNS_PER_CASE = 10
MIN_QUBIT = 2
MAX_QUBIT = 21
DEPTH = 1


def num_qubits_test_generator(num_qubits, depth):
    return textwrap.dedent(f"""\
        import pennylane as qp

        num_qubits = {num_qubits}
        depth = {depth}
        dev = qp.device("default.qubit", wires=num_qubits)


        def add_layer(wires):
            for w in range(wires):
                qp.Hadamard(wires=w)


        @qp.qnode(dev)
        def circuit(num_qubits, depth):
            for _ in range(depth):
                add_layer(num_qubits)
            return qp.expval(qp.Z(0))


        circuit(num_qubits, depth)
    """)


def run():
    with open(f"num_qubits_results_{time.time()}.csv", "w") as results_file:
        results_file.write("num_qubits,total_time,processing_time,execution_time\n")
        for num_qubits in range(MIN_QUBIT, MAX_QUBIT, 2):
            print("Starting run, num_qubits:", num_qubits, "depth:", DEPTH)
            for _ in range(RERUNS_PER_CASE):
                result = vis_circuit_timed(num_qubits_test_generator(num_qubits, DEPTH))
                if result is not None:
                    results_file.write(
                        f"{num_qubits},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
