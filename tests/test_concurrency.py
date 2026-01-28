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
This test group confirms that the application works concurrently for
mutiple users without holding global state related to a user's session
on the backend.
"""

import json
import time
import random
import string


def test_standalone_visualize_circuit(client):
    """Ensure repeated visualizeCircuit calls give the same correct result
    WARNING: this test might randomly fail due to pickle changing parts
    of the encoded string for no apparant reason.
    """
    with open("test_cases/circuit1.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )
        assert json.loads(res.data.decode("utf-8"))["num_wires"] == 6


def test_expand_method_names(client):
    """Confirm that handling a visualizeCircuit inbetween does not change the
    result of connected visualizeCircuit and expandMethod operations by
    checking the number and names of children returned by expandMethod
    """
    body = None
    with open("test_cases/circuit3.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )
        body = json.loads(res.data.decode("utf-8"))

    with open("test_cases/circuit2.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )
    print("BODY", body)
    res_extend = client.post(
        "/expandMethod",
        data=json.dumps(
            {
                "commands": body["commands"],
                "device_name": body["device_name"],
                "id": 0,
                "num_wires": body["num_wires"],
                "num_shots": body["num_shots"],
                "end_idx": -1,
                "real_time": False,
                "name": "TEST",
                "timestamp": time.time(),
                "session_id": "TEST_"
                + str(time.time())
                + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                "token": "TESTUSER",
                "policy_accepted": True,
            }
        ),
    )
    body_extend = json.loads(res_extend.data.decode("utf-8"))
    assert len(body_extend["children"]) == 8
    assert body_extend["children"][0]["name"] == "load_pattern"
    assert body_extend["children"][1]["name"] == "set_up"
    assert body_extend["children"][2]["name"] == "reset_qubits"
    assert body_extend["children"][3]["name"] == "load_pattern"
    assert body_extend["children"][4]["name"] == "load_pattern"
    assert body_extend["children"][5]["name"] == "set_up"
    assert body_extend["children"][6]["name"] == "reset_qubits"
    assert body_extend["children"][7]["name"] == "load_pattern"


def test_expand_method_args(client):
    """Confirm that handling a visualizeCircuit inbetween does not change the
    result of connected visualizeCircuit and expandMethod operations by
    checking the number and arguments of children returned by expandMethod
    """
    body = None
    with open("test_cases/circuit3.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )
        body = json.loads(res.data.decode("utf-8"))

    with open("test_cases/circuit2.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )

    res_extend = client.post(
        "/expandMethod",
        data=json.dumps(
            {
                "commands": body["commands"],
                "device_name": body["device_name"],
                "id": 0,
                "num_wires": body["num_wires"],
                "num_shots": body["num_shots"],
                "end_idx": -1,
                "real_time": False,
                "name": "TEST",
                "timestamp": time.time(),
                "session_id": "TEST_"
                + str(time.time())
                + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                "token": "TESTUSER",
                "policy_accepted": True,
            }
        ),
    )
    body_extend = json.loads(res_extend.data.decode("utf-8"))
    assert len(body_extend["children"]) == 8
    assert body_extend["children"][0]["arguments"] == [["pattern", "11"]]
    assert body_extend["children"][1]["arguments"] == [
        ["number_of_patterns", 2],
        ["idx", 0],
        ["pattern_len", 2],
    ]
    assert body_extend["children"][2]["arguments"] == [["len_of_pattern", 2]]
    assert body_extend["children"][3]["arguments"] == [["pattern", "11"]]
    assert body_extend["children"][4]["arguments"] == [["pattern", "10"]]
    assert body_extend["children"][5]["arguments"] == [
        ["number_of_patterns", 2],
        ["idx", 1],
        ["pattern_len", 2],
    ]
    assert body_extend["children"][6]["arguments"] == [["len_of_pattern", 2]]
    assert body_extend["children"][7]["arguments"] == [["pattern", "10"]]


def test_expand_method_in_debugger(client):
    """Confirm that handling a visualizeCircuit inbetween does not change the
    result of connected visualizeCircuit and expandMethod operations by
    checking the number, names, and arguments of children returned by
    expandMethod when debugger stops at line 92 of circuit 3 for the
    first time
    """
    body = None
    with open("test_cases/circuit3.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )
        body = json.loads(res.data.decode("utf-8"))

    with open("test_cases/circuit2.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )

    res_extend = client.post(
        "/expandMethod",
        data=json.dumps(
            {
                "commands": body["commands"],
                "device_name": body["device_name"],
                "id": 0,
                "num_wires": body["num_wires"],
                "num_shots": body["num_shots"],
                "end_idx": 62,  # breakpoint on line 92, first pass
                "real_time": False,
                "name": "TEST",
                "timestamp": time.time(),
                "session_id": "TEST_"
                + str(time.time())
                + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                "token": "TESTUSER",
                "policy_accepted": True,
            }
        ),
    )
    body_extend = json.loads(res_extend.data.decode("utf-8"))
    assert len(body_extend["children"]) == 3
    assert body_extend["children"][0]["name"] == "load_pattern"
    assert body_extend["children"][1]["name"] == "set_up"
    assert body_extend["children"][2]["name"] == "reset_qubits"
    assert body_extend["children"][0]["arguments"] == [["pattern", "11"]]
    assert body_extend["children"][1]["arguments"] == [
        ["number_of_patterns", 2],
        ["idx", 0],
        ["pattern_len", 2],
    ]
    assert body_extend["children"][2]["arguments"] == [["len_of_pattern", 2]]


def test_simple_concurrency(client):
    """Confirm that handling a visualizeCircuit inbetween does not change the
    result of connected visualizeCircuit and debugNext operations.
    """

    body = None
    with open("test_cases/circuit1.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )
        body = json.loads(res.data.decode("utf-8"))

    with open("test_cases/circuit2.txt", "r") as file:
        data = file.read()
        res = client.post(
            "/visualizeCircuit",
            data=json.dumps(
                {
                    "data": data,
                    "timestamp": time.time(),
                    "session_id": "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                    "token": "TESTUSER",
                    "policy_accepted": True,
                }
            ),
        )

    res_debug = client.post(
        "/debugNext",
        data=json.dumps(
            {
                "data": "6 ",
                "device_name": body["device_name"],
                "commands": body["commands"],
                "debug_index": body["debug_index"],
                "num_wires": body["num_wires"],
                "num_shots": body["num_shots"],
                "debug_action": "next_breakpoint",
                "timestamp": time.time(),
                "session_id": "TEST_"
                + str(time.time())
                + "".join(random.choices(string.ascii_letters + string.digits, k=9)),
                "token": "TESTUSER",
                "policy_accepted": True,
            }
        ),
    )

    body_debug = json.loads(res_debug.data.decode("utf-8"))
    assert "[0.,0.,0.,0.,1.,0.,0.,0.]" in body_debug["circuit_output"]
