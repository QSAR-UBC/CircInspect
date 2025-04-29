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
This group of tests confirm that backend will safely raise an error instead
of running user code that includes malicious activities such as reading a
file, writing a file and accessing the web.
"""

from tests.functions4testing import visCircuit


def run_hack_test(client, user_code_file):
    with open(user_code_file, "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is not None


def test_write_file_hack_1(client):
    run_hack_test(client, "test_cases/write_file_hack_1.txt")


def test_write_file_hack_2(client):
    run_hack_test(client, "test_cases/write_file_hack_2.txt")


def test_write_file_hack_3(client):
    run_hack_test(client, "test_cases/write_file_hack_3.txt")


def test_write_file_hack_4(client):
    run_hack_test(client, "test_cases/write_file_hack_4.txt")


def test_read_file_hack_1(client):
    run_hack_test(client, "test_cases/read_file_hack_1.txt")


def test_read_file_hack_2(client):
    run_hack_test(client, "test_cases/read_file_hack_2.txt")


def test_read_file_hack_3(client):
    run_hack_test(client, "test_cases/read_file_hack_3.txt")


def test_access_web_hack_1(client):
    run_hack_test(client, "test_cases/access_web_hack_1.txt")


def test_access_web_hack_2(client):
    run_hack_test(client, "test_cases/access_web_hack_2.txt")
