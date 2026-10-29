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
having multiple test clients send requests at the same time.

Strategy: before each round, pre-warm exactly num_clients sandbox sessions
so every thread gets a dedicated port from a ready pool. Threads borrow a
port from the queue, make a /visualizeCircuit call, then return the port.
After the timed window closes, all sandboxes are torn down before the next
round begins.
"""

import concurrent.futures
import queue
import random
import textwrap
import time

from helpers import _session_enter, _session_exit, vis_circuit_timed

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


def warm_up_pool(num_clients):
    """Start num_clients sandbox sessions sequentially and return a
    (port_queue, sessions) pair where sessions is a list of (session_id, port)
    tuples needed for teardown."""
    sessions = []
    port_queue = queue.Queue()
    print(f"  Warming up {num_clients} sandbox(es)...", end=" ", flush=True)
    for _ in range(num_clients):
        try:
            session_id, port = _session_enter()
        except RuntimeError as e:
            print(f"\n  warm-up session error: {e}", end=" ", flush=True)
            continue
        sessions.append((session_id, port))
        port_queue.put(port)
    print(f"done ({len(sessions)}/{num_clients} ready).")
    return port_queue, sessions


def tear_down_pool(sessions):
    """Stop all sandbox sessions from a previous warm-up."""
    print(f"  Tearing down {len(sessions)} sandbox(es)...", end=" ", flush=True)
    for session_id, _port in sessions:
        _session_exit(session_id)
    print("done.")


def task(port_queue):
    """Worker: borrow a port from the shared pool, make a request, return
    the port, repeat until TESTING_TIME_SECONDS has elapsed."""
    num_calls = 0
    errors = 0
    start = time.time()
    while time.time() - start < TESTING_TIME_SECONDS:
        port = port_queue.get()
        try:
            done = vis_circuit_timed(generate_code(), port)
            if done:
                num_calls += 1
            else:
                errors += 1
        finally:
            port_queue.put(port)  # always return the port
    print("Thread Successes:", num_calls, "Errors:", errors)
    return num_calls


if __name__ == "__main__":
    with open("concurrency_results_" + str(time.time()) + ".csv", "w") as results_file:
        results_file.write("Number of Clients,Calls responded per second\n")
        for num_clients in range(MIN_CLIENTS, MAX_CLIENTS, STEP):
            print(f"\n--- Round: {num_clients} client(s) ---")

            port_queue, sessions = warm_up_pool(num_clients)

            if not sessions:
                print(f"Num clients: {num_clients}  | No sandboxes came up, skipping round.")
                results_file.write(str(num_clients) + ",0.0\n")
                results_file.flush()
                time.sleep(5)
                continue

            active_clients = len(sessions)
            with concurrent.futures.ThreadPoolExecutor(max_workers=active_clients) as executor:
                futures = [executor.submit(task, port_queue) for _ in range(active_clients)]
            results = [f.result() for f in futures]

            tear_down_pool(sessions)

            total_num_of_calls = sum(results)
            calls_per_sec = total_num_of_calls / TESTING_TIME_SECONDS
            print(
                f"Num clients: {num_clients}  | Calls per second: {calls_per_sec}"
            )
            results_file.write(str(num_clients) + "," + str(calls_per_sec) + "\n")
            results_file.flush()

            time.sleep(5)  # brief cooldown between rounds
