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
Runs every performance test in one process.

Usage:
    python3 run_all.py
"""
import time

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

TESTS = [
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
    for module in TESTS:
        print(f"\n=== Running {module.__name__} ===")
        start = time.time()
        module.run()
        print(f"=== Finished {module.__name__} in {time.time() - start:.1f}s ===")


if __name__ == "__main__":
    main()
