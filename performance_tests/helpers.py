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

"""Helper functions to run performance tests"""

import time
import uuid
import json
import requests

BASE_URL = "http://127.0.0.1:5000"


def _make_session_id():
    """Generate a session id for a debug flow, so it doesn't collide with
    a debug session left behind by another run."""
    return "TEST_" + uuid.uuid4().hex


def vis_circuit_timed(code):
    """Run a single timed visualizeCircuit API call on the test server.

    Args:
        code (string): user code

    Returns:
        dict with "total" (client-side wall-clock time for the call),
        "processing" (CircInspect's own processing time, excluding
        PennyLane execution), and "execution" (summed PennyLane execution
        time) in seconds, or None on error.
    """
    try:
        start = time.time()
        res = requests.post(
            f"{BASE_URL}/visualizeCircuit",
            data=json.dumps(
                {
                    "data": code,
                    "postselect_overrides": {},
                    "timestamp": time.time(),
                }
            ),
        )
        end = time.time()
        body = res.json()
        if body.get("error") is not None:
            return None
        return {
            "total": end - start,
            "processing": body["processing_time_no_exec_times"],
            "execution": sum(body["exec_times_list"]),
        }
    except Exception as e:
        print("vis_circuit_timed error:", e)
        return None


def prepare_debug(code, session_id):
    """Send the one-time visualizeCircuit call debug_output_timed depends
    on, caching the command tree under session_id on the server.

    Args:
        code (string): user code
        session_id (string): session id to cache the command tree under

    Raises:
        RuntimeError: if visualizeCircuit reports an error.
    """
    res = requests.post(
        f"{BASE_URL}/visualizeCircuit",
        data=json.dumps(
            {
                "data": code,
                "postselect_overrides": {},
                "session_id": session_id,
                "timestamp": time.time(),
            }
        ),
    )
    body = res.json()
    if body.get("error") is not None:
        raise RuntimeError(f"visualizeCircuit failed: {body['error']}")


def debug_output_timed(session_id, breakpoint_index):
    """Run a single timed debugOutput API call against a session already
    prepared via prepare_debug().

    Args:
        session_id (string): session id prepared via prepare_debug()
        breakpoint_index (int): number of qnode body lines to apply

    Returns:
        dict with "total" (client-side wall-clock time for the call),
        "processing" (CircInspect's own processing time, excluding
        PennyLane execution), and "execution" (PennyLane execution time)
        in seconds, or None on error.
    """
    try:
        start = time.time()
        res = requests.post(
            f"{BASE_URL}/debugOutput",
            data=json.dumps(
                {
                    "session_id": session_id,
                    "node_ids": list(range(2, breakpoint_index + 3)),
                    "transform_root_idx": 1,
                    "postselect_overrides": {},
                }
            ),
        )
        end = time.time()
        body = res.json()
        if body.get("error") is not None:
            return None
        return {
            "total": end - start,
            "processing": body["processing_time_no_exec_times"],
            "execution": sum(body["exec_times_list"]),
        }
    except Exception as e:
        print("debug_output_timed error:", e)
        return None
