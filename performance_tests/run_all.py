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
Runs every sequential (non-concurrency) performance test against a single
shared sandbox container, instead of each test script spinning up its own.
The concurrency benchmarks (test_concurrent_performance[.py/_cold.py])
intentionally manage their own pool of containers to measure multi-client
behaviour, so they are run separately and are not included here.

Usage:
    python3 run_all.py
"""
import time

from helpers import _session_enter, _session_exit

import test_depth
import test_num_qubits
import test_lines_of_code
import test_subroutine_calls
import test_nestedness
import test_gate_migration
import test_gate_migration_single_helper
import test_gate_migration_midcircuit
import test_midcircuit_measurements
import test_breakpoint_distance

SEQUENTIAL_TESTS = [
    test_depth,
    test_num_qubits,
    test_lines_of_code,
    test_subroutine_calls,
    test_nestedness,
    test_gate_migration,
    test_gate_migration_single_helper,
    test_gate_migration_midcircuit,
    test_midcircuit_measurements,
    test_breakpoint_distance,
]


def main():
    session_id, port = _session_enter()
    try:
        for module in SEQUENTIAL_TESTS:
            print(f"\n=== Running {module.__name__} ===")
            start = time.time()
            module.run(port)
            print(f"=== Finished {module.__name__} in {time.time() - start:.1f}s ===")
    finally:
        _session_exit(session_id)


if __name__ == "__main__":
    main()
