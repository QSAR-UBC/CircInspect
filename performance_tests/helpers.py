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
import random
import string
import json
import requests

BASE_URL = "http://127.0.0.1:5000"


def _make_session_id():
    """Generate a unique TEST_ session ID."""
    return (
        "TEST_"
        + str(time.time())
        + "".join(random.choices(string.ascii_letters + string.digits, k=9))
    )


def _session_enter():
    """Start a new sandbox session.

    Returns:
        (session_id, port) tuple on success.

    Raises:
        RuntimeError: if the server cannot allocate a sandbox port.
    """
    session_id = _make_session_id()
    res = requests.post(
        f"{BASE_URL}/dc/sessionEnter",
        data=json.dumps(
            {
                "session_id": session_id,
            }
        ),
    )
    body = res.json()
    if "port" not in body:
        raise RuntimeError(
            f"sessionEnter failed (no port returned): {body.get('error', body)}"
        )
    return session_id, body["port"]


def _session_exit(session_id):
    """Stop and clean up a sandbox session."""
    requests.post(
        f"{BASE_URL}/dc/sessionExit",
        data=json.dumps(
            {
                "session_id": session_id,
            }
        ),
    )


def _post_visualize(code, port, session_id=None):
    """POST to /visualizeCircuit against an already-warmed sandbox port.
    No session lifecycle (enter/exit) is performed -- the caller owns the
    port and is responsible for starting/stopping the sandbox.

    Args:
        code (string): user code
        port (int): port of a running sandbox
        session_id (string, optional): session ID to report activity
            against; a fresh throwaway ID is used if omitted.

    Returns:
        tuple(dict, error): the parsed JSON response body, and its
        "error" field (None on success).
    """
    res = requests.post(
        f"{BASE_URL}/visualizeCircuit",
        data=json.dumps(
            {
                "data": code,
                "postselect_overrides": {},
                "port": port,
                "session_id": session_id or _make_session_id(),
            }
        ),
    )
    body = res.json()
    return body, body.get("error")


def vis_circuit_timed(code, port, session_id=None):
    """Run a single timed visualizeCircuit API call against an
    already-warmed sandbox port. Safe to call repeatedly against the same
    container -- see _post_visualize() for session/port ownership.

    Args:
        code (string): user code
        port (int): port of a running sandbox
        session_id (string, optional): session ID to report activity
            against; a fresh throwaway ID is used if omitted.

    Returns:
        dict with "total" (client-side wall-clock time for the call),
        "processing" (CircInspect's own processing time, excluding
        PennyLane execution), and "execution" (summed PennyLane execution
        time) in seconds, or None on error.
    """
    try:
        start = time.time()
        body, error = _post_visualize(code, port, session_id)
        end = time.time()
        if error is not None:
            return None
        return {
            "total": end - start,
            "processing": body["processing_time_no_exec_times"],
            "execution": sum(body["exec_times_list"]),
        }
    except Exception as e:
        print("vis_circuit_timed error:", e)
        return None


def vis_circuit(code):
    """Run a visualizeCircuit API call on the test server using a fresh
    sandbox session that is cleaned up afterwards.

    Args:
        code (string): user code

    Returns:
        dict with "total" (client-side wall-clock time for the whole call),
        "processing" (CircInspect's own processing time, excluding
        PennyLane execution), and "execution" (summed PennyLane execution
        time) in seconds, or None on error.
    """
    try:
        session_id, port = _session_enter()
    except RuntimeError as e:
        print("vis_circuit session error:", e)
        return None
    try:
        return vis_circuit_timed(code, port, session_id=session_id)
    finally:
        _session_exit(session_id)


def prepare_debug_with_port(code, port, session_id=None):
    """Send the one-time visualizeCircuit call debugOutput depends on,
    against an already-warmed sandbox port.

    Args:
        code (string): user code
        port (int): port of a running sandbox
        session_id (string, optional): session ID to report activity
            against; a fresh throwaway ID is used if omitted.

    Raises:
        RuntimeError: if visualizeCircuit reports an error.
    """
    _, error = _post_visualize(code, port, session_id)
    if error is not None:
        raise RuntimeError(f"visualizeCircuit failed: {error}")


def debug_output_timed(port, breakpoint_index):
    """Run a single timed debugOutput API call against an already-warmed
    sandbox port that has already been prepared via
    prepare_debug_with_port(). No session lifecycle is performed -- the
    caller owns the port, so this is safe to call repeatedly against the
    same container/prepared circuit.

    Args:
        port (int): port of a running, already-prepared sandbox
        breakpoint_index (int): number of node IDs to pass as the breakpoint

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
                    "port": port,
                    "node_ids": list(range(breakpoint_index)),
                    "transform_root_idx": 0,
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


def debug_circuit(code, breakpoint_index):
    """Run a debugOutput API call on the test server after preparing via
    visualizeCircuit. Creates a fresh sandbox session and cleans it up
    afterwards.

    Args:
        code (string): user code
        breakpoint_index (int): number of node IDs to pass as the breakpoint

    Returns:
        dict with "total", "processing", and "execution" timings in
        seconds (see debug_output_timed()), or None on error.
    """
    session_id, port = _session_enter()
    try:
        prepare_debug_with_port(code, port, session_id=session_id)
        return debug_output_timed(port, breakpoint_index)
    finally:
        _session_exit(session_id)
