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
This set of tests confirm that fixed bugs that do not belong to any
test groups are not reintroduced.
"""

from tests.functions4testing import visCircuit


def test_multiple_runs_different_qnodes(client):
    """This test confirms that running multiple qnodes does not break
    the application.
    """
    with open("test_cases/multiple_runs_different_qnodes.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_multiple_runs_same_qnode(client):
    """This test confirms that running multiple instances of the same
    qnode does not break the application.
    """
    with open("test_cases/multiple_runs_different_qnodes.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_top_level_classical_functions(client):
    """This test confirms that having classical functions outside the qnode
    does not break the application.
    """
    with open("test_cases/top_level_classical_functions.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_qml_operations_in_multiple_lines(client):
    """This test confirms that writing qml operations in multiple lines
    do not result in unexpected errors. For example:
    qml.CNOT(
        wires=[
            0,
            1
        ]
    )
    """
    with open("test_cases/qml_operations_in_multiple_lines.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None
