# Copyright 2025 UBC Quantum Software and Algorithms Research Lab

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
having multiple test clients send requests at the same time
"""

import concurrent.futures
import time
import random

from helpers import vis_circuit_server

MIN_CLIENTS = 5
MAX_CLIENTS = 31
TESTING_TIME_SECONDS = 10

num_of_calls_per_thread = []


def generate_code():
    code = """
import pennylane as qml
dev = qml.device("default.qubit", wires=1)
@qml.qnode(dev)
def circuit():"""
    code += (
        """
    qml.RX("""
        + str(random.random())
        + """, wires=0)"""
    )
    code += """
    return qml.probs()
circuit()
"""
    return code


def task():
    num_calls = 0
    errors = 0
    start = time.time()
    while time.time() - start < TESTING_TIME_SECONDS:
        done = vis_circuit_server(generate_code())
        if done:
            num_calls += 1
        else:
            errors += 1
    print("Thread Successes:", num_calls, "Errors:", errors)
    return num_calls


if __name__ == "__main__":
    with open("concurrency_results_" + str(time.time()) + ".csv", "w") as results_file:
        results_file.write("Number of clients,Calls responded per second\n")
        for num_clients in range(MIN_CLIENTS, MAX_CLIENTS, 5):
            time.sleep(10)  # allow time for server to garbage collect after previous test
            with concurrent.futures.ThreadPoolExecutor(max_workers=num_clients) as executor:
                futures = [executor.submit(task) for _ in range(num_clients)]
            results = [f.result() for f in futures]
            total_num_of_calls = sum(results)
            calls_per_sec = total_num_of_calls / TESTING_TIME_SECONDS
            print("Num clients:", str(num_clients), " | Calls per second:", str(calls_per_sec))
            results_file.write(str(num_clients) + "," + str(calls_per_sec) + "\n")
