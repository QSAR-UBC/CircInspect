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

""" This module includes helper functions for testing """

import json
import time


def visCircuit(client, code, postselect_overrides=None):
    """Run a visualizeCircuit API call on the test server
    Args:
        client: Flask test client
        code (string): user code
        postselect_overrides (dict{string: int}): mapping of mid circuit
            measurement id -> postselect value (0 or 1), if any
    Returns:
        A dict of data returned from the test server
    """
    res = client.post(
        "/visualizeCircuit",
        data=json.dumps(
            {
                "data": code,
                "postselect_overrides": postselect_overrides or {},
                "timestamp": time.time(),
            }
        ),
    )
    return json.loads(res.data.decode("utf-8"))