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

""" This set of tests confirm that code parsing works """

from tests.functions4testing import visCircuit


def test_single_line_comment_with_qnode(client):
    """Ensure that parsing does not fail when
    there is a qnode decorator in a single line comment.
    """
    with open("test_cases/single_line_comment_with_qnode.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_multiline_comment_with_qnode(client):
    """Ensure that parsing does not fail when
    there is a qnode decorator in a multi-line comment.
    """
    with open("test_cases/multiline_comment_with_qnode.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None


def test_transforms_and_multiline_comment_with_qnode(client):
    """Ensure that parsing transforms does not fail when
    there is a qnode decorator in a multi-line comment.
    """
    with open("test_cases/transforms_and_multiline_comment_with_qnode.txt", "r") as f:
        assert visCircuit(client, f.read()).get("error", None) is None
