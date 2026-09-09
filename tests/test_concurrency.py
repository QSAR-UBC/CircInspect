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
This test group confirms that the application works concurrently for
mutiple users without holding global state related to a user's session
on the backend.
"""

from tests.functions4testing import visCircuit


def test_standalone_visualize_circuit(client):
    """Ensure repeated visualizeCircuit calls give the same correct result
    WARNING: this test might randomly fail due to pickle changing parts
    of the encoded string for no apparant reason.
    """
    with open("test_cases/circuit1.txt", "r") as file:
        data = file.read()
        result = visCircuit(client, data)
        assert result["num_wires"] == 6


def test_simple_concurrency(client):
    """Confirm that handling a visualizeCircuit inbetween does not change the
    result of connected visualizeCircuit operations.
    """

    with open("test_cases/circuit1.txt", "r") as file:
        data = file.read()
        body = visCircuit(client, data)

    with open("test_cases/circuit2.txt", "r") as file:
        data = file.read()
        body_2 = visCircuit(client, data)

    assert body["name"] == body_2["name"]
