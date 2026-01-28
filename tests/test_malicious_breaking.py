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
This set of tests confirm that backend will safely raise an error
instead of running user code that can break the code execution server.
"""

from tests.functions4testing import visCircuit


def run_hack_test(client, user_code_file):
    with open(user_code_file, "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is not None


def test_memory_fill_hack_1(client):
    run_hack_test(client, "test_cases/memory_fill_hack_1.txt")


def test_memory_fill_hack_2(client):
    run_hack_test(client, "test_cases/memory_fill_hack_2.txt")


def test_infinite_loop_hack_1(client):
    run_hack_test(client, "test_cases/infinite_loop_hack_1.txt")


def test_infinite_loop_hack_2(client):
    run_hack_test(client, "test_cases/infinite_loop_hack_2.txt")


def test_heavy_processing_hack(client):
    run_hack_test(client, "test_cases/heavy_processing_hack.txt")
