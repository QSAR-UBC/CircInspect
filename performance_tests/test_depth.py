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
quantum circuit depth. NUM_QUBITS is fixed; depth (number of layers)
is swept.
"""
import textwrap
import time

from helpers import vis_circuit_timed

RERUNS_PER_CASE = 10
MIN_DEPTH = 2
MAX_DEPTH = 21
NUM_QUBITS = 10


def depth_test_generator(num_qubits, depth):
    return textwrap.dedent(f"""\
        import pennylane as qp

        wires = {num_qubits}
        depth = {depth}
        dev = qp.device("default.qubit", wires=wires)


        def add_layer(wires):
            for w in range(wires):
                qp.Hadamard(wires=w)


        @qp.qnode(dev)
        def circuit(iters):
            for _ in range(iters):
                add_layer(wires)
            return qp.expval(qp.Z(0))


        circuit(depth)
    """)


def run():
    with open(f"depth_results_{time.time()}.csv", "w") as results_file:
        results_file.write("depth,total_time,processing_time,execution_time\n")
        for depth in range(MIN_DEPTH, MAX_DEPTH):
            print("Starting run, num_qubits:", NUM_QUBITS, "depth(iterations):", depth)
            for _ in range(RERUNS_PER_CASE):
                result = vis_circuit_timed(depth_test_generator(NUM_QUBITS, depth))
                if result is not None:
                    results_file.write(
                        f"{depth},{result['total']},{result['processing']},{result['execution']}\n"
                    )


if __name__ == "__main__":
    run()
