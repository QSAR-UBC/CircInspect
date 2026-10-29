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
Concurrency benchmark — COLD sandbox variant (no warm pool).

Each /visualizeCircuit call creates a fresh sandbox session, uses it once,
then tears it down. This is the baseline to compare against the warm-pool
version in test_concurrent_performance.py.
"""

import concurrent.futures
import random
import textwrap
import time

from helpers import vis_circuit

MIN_CLIENTS = 5
MAX_CLIENTS = 31
STEP = 5
TESTING_TIME_SECONDS = 10


def generate_code():
    angle = random.random()
    return textwrap.dedent(f"""\
        import pennylane as qp
        dev = qp.device("default.qubit", wires=1)


        @qp.qnode(dev)
        def circuit():
            qp.RX({angle}, wires=0)
            return qp.probs()


        circuit()
    """)


def task():
    """Each call spins up a fresh sandbox, makes one request, and tears it down."""
    num_calls = 0
    errors = 0
    start = time.time()
    while time.time() - start < TESTING_TIME_SECONDS:
        done = vis_circuit(generate_code())
        if done:
            num_calls += 1
        else:
            errors += 1
    print("Thread Successes:", num_calls, "Errors:", errors)
    return num_calls


if __name__ == "__main__":
    with open("concurrency_cold_results_" + str(time.time()) + ".csv", "w") as results_file:
        results_file.write("Number of Clients,Calls responded per second\n")
        for num_clients in range(MIN_CLIENTS, MAX_CLIENTS, STEP):
            print(f"\n--- Round: {num_clients} client(s) ---")
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_clients) as executor:
                futures = [executor.submit(task) for _ in range(num_clients)]
            results = [f.result() for f in futures]
            total_num_of_calls = sum(results)
            calls_per_sec = total_num_of_calls / TESTING_TIME_SECONDS
            print(
                f"Num clients: {num_clients}  | Calls per second: {calls_per_sec}"
            )
            results_file.write(str(num_clients) + "," + str(calls_per_sec) + "\n")
            results_file.flush()

            time.sleep(10)  # longer cooldown, sandbox churn needs time to settle
