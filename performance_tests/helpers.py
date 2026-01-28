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

""" Helper functions to run performace tests """

import time
import random
import string
import json
import requests

TEST_TOKEN = "NOT_A_REAL_TOKEN"  # GENERATE NEW TOKEN IF RUNNING WITH DATABASE AND AUTH


def visCircuit(code):
    """Run a visualizeCircuit API call on the test server
    Args:
        client: Flask test client
        code (string): user code
    Returns:
        A dict of data returned from the test server
    """
    res = requests.post(
        "http://127.0.0.1:5000/visualizeCircuit",
        data=json.dumps(
            {
                "data": code,
                "timestamp": time.time(),
                "session_id": (
                    "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9))
                ),
                "token": TEST_TOKEN,
            }
        ),
    )
    return res.json()["processing_time_no_exec_times"]


def vis_circuit_server(code):
    res = requests.post(
        "https://circinspect.ece.ubc.ca/visualizeCircuit",
        data=json.dumps(
            {
                "data": code,
                "timestamp": time.time(),
                "session_id": (
                    "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9))
                ),
                "token": "NOT_A_REAL_TOKEN",
            }
        ),
    )
    return res.json().get("error", None) is None


def debug_circuit(code, breakpoint_index):
    """Run a debugNext API call on the test server
        after preparing the call via visualizeCircuit API call
    Args:
        client: Flask test client
        code (string): user code
    Returns:
        A dict of data returned from the test server
    """
    res = requests.post(
        "http://127.0.0.1:5000/visualizeCircuit",
        data=json.dumps(
            {
                "data": code,
                "timestamp": time.time(),
                "session_id": (
                    "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9))
                ),
                "token": TEST_TOKEN,
            }
        ),
    )

    breakpoints = str(breakpoint_index)

    start = time.time()
    res = requests.post(
        "http://127.0.0.1:5000/debugNext",
        data=json.dumps(
            {
                "data": breakpoints,
                "debug_index": res.json()["debug_index"],
                "device_name": res.json()["device_name"],
                "num_wires": res.json()["num_wires"],
                "num_shots": res.json()["num_shots"],
                "debug_action": "next_breakpoint",
                "commands": res.json()["commands"],
                "timestamp": time.time(),
                "session_id": (
                    "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9))
                ),
                "token": TEST_TOKEN,
            }
        ),
    )

    return time.time() - start, res.json()["processing_time_no_exec_times"]
