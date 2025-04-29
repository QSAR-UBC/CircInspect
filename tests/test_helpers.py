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
This module is a set of tests for helper functions located at server/helpers.py

Some of the helper functions are hard to test alone as they transform large objects
to other large objects. There is a large set of end-to-end tests in the tests/ folder
that covers these functions.
"""

import tokenize
import io
import pytest

from server import helpers
from server import command


def test_json_default():
    """Test the json_deault() function with a range object which is known to fail with the standard JSON encoder."""
    o = range(2)
    returned = helpers.json_default(o)
    assert returned == "[0, 1]"


def test_check_for_restricted_code():
    """Tests that the restricted code check responds with an error with
    restricted imports and functions but does not respond with an error
    in a common allowed case.
    """
    assert len(helpers.check_for_restricted_code("import os")) == 2
    assert len(helpers.check_for_restricted_code("import  lane")) == 2
    assert len(helpers.check_for_restricted_code('import pennylane\nopen("hello.py")')) == 2
    assert len(helpers.check_for_restricted_code('import pennylane\nexec("hello.py")')) == 2
    assert len(helpers.check_for_restricted_code('eval("hello.py")')) == 2
    assert len(helpers.check_for_restricted_code("import pennylane as qml\nqml.breakpoint()")) == 2
    assert len(helpers.check_for_restricted_code("import pennylane")) == 0


def test_get_method_names():
    """Check that get_method_names() is able to retrive function names if
    one or more functions are present in the code. It also returns and
    empty set if no functions are present.
    """
    assert {"a"} == helpers.get_method_names("def a():\n    print(1)")
    assert {"a", "b"} == helpers.get_method_names("def a():\n    print(1)\ndef b():\n    print(2)")
    assert len(helpers.get_method_names("print(1)")) == 0


def test_find_first_qnode_decorator():
    """Test that the function is able to find the qnode even when a
    transform is present
    """
    code = """
import pennylane as qml
dev = qml.device("default.qubit", wires=2)
@cancel_inverses
@qml.qnode(dev)
def circuit():
    qml.H(0)
    return qml.probs()
"""
    tokens = tokenize.tokenize(io.BytesIO(code.encode("utf-8")).readline)
    returned = helpers.find_first_qnode_decorator(tokens)
    assert returned == 4


def test_comment_out_transforms():
    """Check that the function can correctly comment out a transform"""
    code = """
import pennylane as qml
dev = qml.device("default.qubit", wires=2)
@cancel_inverses
@qml.qnode(dev)
def circuit():
    qml.H(0)
    return qml.probs()
"""
    expected = """
import pennylane as qml
dev = qml.device("default.qubit", wires=2)
#@cancel_inverses
@qml.qnode(dev)
def circuit():
    qml.H(0)
    return qml.probs()
"""

    returned = helpers.comment_out_transforms(code)
    assert returned == expected


def test_get_transform_details():
    """Check that the returned transform name is correct"""
    code = """
import pennylane as qml
dev = qml.device("default.qubit", wires=2)
@cancel_inverses
@qml.qnode(dev)
def circuit():
    qml.H(0)
    return qml.probs()
"""
    returned = helpers.get_transform_details(code, 3)
    assert returned[0][0] == "@cancel_inverses"


def test_get_quantum_methods():
    """Given a ist of commands, check that the function can distinguish
    quantum and classical functions correctly.
    """
    commands = [
        command.Command("a", 12, "qml.H(0)", "quantum", "quantum"),
        command.Command("b", 22, "print(1)", "string", "classical"),
    ]
    returned = helpers.get_quantum_methods(commands)
    assert returned == {"a"}


def test_get_all_commands_in_function():
    """Given a function name and commands, check that the function can
    find the associated quantum commands. It should not add classical
    commands associated with the function, or any commands not associated
    with the function.
    """
    fname = "a"
    commands = [
        command.Command("a", 12, "qml.H(0)", "quantum", "quantum"),
        command.Command("b", 22, "qml.H(0)", "quantum", "quantum"),
        command.Command("b", 22, "print(1)", "string", "classical"),
        command.Command("a", 13, "print(2)", "string", "classical"),
    ]
    returned = helpers.get_all_commands_in_function(fname, commands, None)
    assert returned == [commands[0]]


def test_get_identifier_numbers():
    """Test that command identifiers are set properly"""
    commands = [
        command.Command("a", 12, "qml.H(0)", "quantum", "quantum"),
        command.Command("b", 22, "print(1)", "string", "classical"),
    ]
    helpers.update_identifier_numbers(commands)
    assert commands[0].identifier == 0
    assert commands[1].identifier == 1


def test_get_quantum_lines():
    """Test for a simple user code that the function can distinguish
    the quantum lines and return their line numbers.
    """
    code = """
import pennylane as qml
dev = qml.device("default.qubit", wires=2)
@qml.qnode(dev)
def circuit():
    qml.H(0)
    return qml.probs()
"""
    expected = set([3, 4, 6, 7])
    returned = helpers.get_quantum_lines(code.split("\n"))
    assert returned == expected


def test_newline_cleanup():
    """Test the newline cleanup returns the code in the expected shape."""
    code = """
qml.PauliX(
wires=0
)
"""
    expected = """
qml.PauliX(wires=0)


"""
    returned = helpers.newline_cleanup(code)
    assert returned == expected


def test_comment_cleanup():
    """Test that comment cleanup can distinguish between comments and other
    objects with the "#" in them. Check that the comment is correctly
    removed, leaving an empty line.
    """
    code = """
# comment
print("#not comment")
"""
    expected = """

print("#not comment")
"""
    returned = helpers.comment_cleanup(code)
    assert returned == expected
