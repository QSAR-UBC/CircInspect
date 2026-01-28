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

""" This module includes helper functions for testing """

import json
import time
import random
import string


def visCircuit(client, code):
    """Run a visualizeCircuit API call on the test server
    Args:
        client: Flask test client
        code (string): user code
    Returns:
        A dict of data returned from the test server
    """
    res = client.post(
        "/visualizeCircuit",
        data=json.dumps(
            {
                "data": code,
                "timestamp": time.time(),
                "session_id": (
                    "TEST_"
                    + str(time.time())
                    + "".join(random.choices(string.ascii_letters + string.digits, k=9))
                ),
                "token": "TESTUSER",
                "policy_accepted": True,
            }
        ),
    )
    return json.loads(res.data.decode("utf-8"))
