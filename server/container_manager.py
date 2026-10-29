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

import socket
import time
import json
import requests
import subprocess
import threading
import traceback
import importlib
import importlib.metadata
from datetime import datetime, timezone
from flask import Flask, request, jsonify, Response
from server import helpers


_session_ports = {}  # session_id -> host port for the sandbox HTTP server
_session_last_active = {}  # session_id -> last activity timestamp (time.time())

_CONTAINER_NAME_PREFIX = "circinspect-sandbox-"

_SANDBOX_CLOSED_MESSAGE = "Your sandbox was forcibly closed. Please refresh the page to restart it."

# How long to wait for the sandbox Flask server to become ready after container start
_HEALTH_CHECK_TIMEOUT = 10.0  # seconds
_HEALTH_CHECK_INTERVAL = 0.05  # seconds

_INACTIVITY_TIMEOUT = 3600  # seconds (1 hour)
_REAPER_INTERVAL = 60  # seconds between reaper checks


def _reap_if_still_expired(sid):
    """Stops sid's container if it is still expired.

    Re-reads sid's last-active time immediately before stopping, since a
    concurrent request may have refreshed it after sid was flagged expired.
    Any failure to stop the container is swallowed so it can't kill the
    reaper thread.

    Args:
        sid (str): The session identifier to check.
    """
    last = _session_last_active.get(sid)
    if last is None or time.time() - last < _INACTIVITY_TIMEOUT:
        return
    try:
        stop_container(sid)
    except Exception:
        traceback.print_exc()


def _container_started_at(container_name):
    """Looks up when a running container actually started, per Docker.

    Args:
        container_name (str): Name of the container to inspect.

    Returns:
        float: Unix timestamp of container start, or None if it can't be
        determined (container gone, unexpected output, etc.).
    """
    result = subprocess.run(
        ["docker", "inspect", "-f", "{{.State.StartedAt}}", container_name],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return None
    raw = result.stdout.strip()
    try:
        if "." in raw:
            head, frac_and_zone = raw.split(".", 1)
            frac = frac_and_zone.rstrip("Z")[:6]  # %f supports up to microseconds
            raw = f"{head}.{frac}Z"
        started = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S.%fZ")
        return started.replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        return None


def _reconcile_with_docker():
    """Picks up sandbox containers Docker is running that this process has
    no activity record for, such as containers left over from a server
    crash/restart, or one that leaked before it was registered.

    Each is seeded with its real Docker start time as a stand-in last-active
    time, so the reaper can still eventually reclaim it instead of never
    being able to see it at all.
    """
    result = subprocess.run(
        ["docker", "ps", "--filter", f"name={_CONTAINER_NAME_PREFIX}", "--format", "{{.Names}}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return
    for name in result.stdout.splitlines():
        name = name.strip()
        if not name.startswith(_CONTAINER_NAME_PREFIX):
            continue
        session_id = name[len(_CONTAINER_NAME_PREFIX):]
        if session_id in _session_last_active:
            continue
        started_at = _container_started_at(name)
        if started_at is not None:
            _session_last_active[session_id] = started_at


def _reaper_loop():
    """Background thread that stops containers idle for longer than _INACTIVITY_TIMEOUT.

    Reconciles against the Docker daemon on every pass so containers this
    process lost track of (crash/restart, a registration that never
    happened) still eventually get reaped, and isolates every fallible step
    in its own try/except so one bad `docker` call can't silently kill the
    loop for the rest of the process's life.
    """
    while True:
        time.sleep(_REAPER_INTERVAL)
        try:
            _reconcile_with_docker()
        except Exception:
            traceback.print_exc()

        now = time.time()
        expired = [
            sid
            for sid, last in list(_session_last_active.items())
            if now - last >= _INACTIVITY_TIMEOUT
        ]
        for sid in expired:
            _reap_if_still_expired(sid)


_reaper_thread = threading.Thread(target=_reaper_loop, daemon=True)
_reaper_thread.start()

def create_app():

    app = Flask(__name__, instance_relative_config=True)

    @app.route("/visualizeCircuit", methods=["POST"])
    def visualize_on_exec_server():
        """Send the user code to the execution server after
        the restricted code checks pass.

        Returns:
            The response sent back by the execution server
            is returned to user as a response.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            code_received = body["data"]
            postselect_overrides = body.get("postselect_overrides", {})
            port = body.get("port")
            # initial check for malicious code
            restricted_code = helpers.check_for_restricted_code(code_received)
            if restricted_code != "":
                return jsonify({"error": restricted_code})

            exec_start = time.time()

            # send code to exec server to get the trace
            if not _is_healthy(port):
                return jsonify({
                    "error": ["Sandbox session closed", _SANDBOX_CLOSED_MESSAGE]
                })
            try:
                response = requests.post(
                    f"http://127.0.0.1:{port}/execute",
                    json={
                        "code": code_received,
                        "postselect_overrides": postselect_overrides or {},
                    },
                    timeout=30,
                )
                exec_time = time.time() - exec_start
                if response.status_code != 200:
                    return jsonify({
                        "error": [
                            f"Sandbox HTTP error {response.status_code}: {response.text}",
                            "line unknown",
                        ]
                    })
                result = response.json()
                result["exec_time"] = exec_time
                session_id = body.get("session_id")
                if session_id:
                    _session_last_active[session_id] = time.time()

            except requests.exceptions.Timeout:
                return jsonify({
                    "error": ["Sandbox execution timed out.", "line unknown"]
                })
            except Exception as e:
                return jsonify({"error": [str(e), "line unknown"]})


            if response.status_code == 400:
                return jsonify({"error": ["Please run a quantum circuit", "line unknown"]})
            
            return jsonify(result), 200


    @app.route("/debugOutput", methods=["POST"])
    def debug_output():
        """Pass the debug endpoint information to the container manager
        to fetch the output and circuit image.

        Returns:
            JSON for frontend to render circuit output and image.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if body:
            port = body.get("port")
            node_ids = body.get("node_ids", [])
            transform_root_idx = body.get("transform_root_idx")
            postselect_overrides = body.get("postselect_overrides", {})

            if not _is_healthy(port):
                return jsonify({
                    "error": ["Sandbox session closed", _SANDBOX_CLOSED_MESSAGE]
                })

            sandbox_url = f"http://127.0.0.1:{port}/debugOutput"
            try:
                response = requests.post(sandbox_url, json={
                    "node_ids": node_ids,
                    "transform_root_idx": transform_root_idx,
                    "postselect_overrides": postselect_overrides
                    }, timeout=30)
                
                if response.status_code == 200:
                    session_id = body.get("session_id")
                    if session_id:
                        _session_last_active[session_id] = time.time()
                    return jsonify(response.json()), 200
                else:
                    return jsonify({"error": f"Error {response.status_code}: {response.text}"})
            except Exception as e:
                return jsonify({"error": str(e)})
        return Response(status=400)


    @app.route("/dc/sessionEnter", methods=["POST"])
    def collect_session_enter():
        """Start a sandbox container for the session when the user enters
            the application.

        Returns:
            JSON response with sandbox port, or appropriate error status.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if not body:
            return Response(status=400)

        session_id = body.get("session_id") or "default"
        try:
            port = start_container(session_id)
            return jsonify({"port": port}), 200
        except Exception as e:
            print(f"Failed to start sandbox for session {session_id}: {e}")
            return jsonify({"error": str(e)})


    @app.route("/dc/sessionExit", methods=["POST"])
    def collectSessionExit():
        """Stop the sandbox container for the session when the user exits.

        Returns:
            Empty REST response with appropriate status code.
        """
        if request.data == b"":
            body = request.form
        else:
            body = json.loads(request.data.decode("utf-8"))
        if not body:
            return Response(status=400)

        session_id = body.get("session_id") or "default"
        try:
            stop_container(session_id)
        except Exception as e:
            print(f"Failed to stop sandbox for session {session_id}: {e}")

        return Response(status=204)


    @app.route("/library_version")
    def version():
        return jsonify(
            {
                "pennylane": safe_version("pennylane"),
                "numpy": safe_version("numpy"),
                "autograd": safe_version("autograd"),
                "jax": safe_version("jax"),
                "torch": safe_version("torch"),
                "tensorflow": safe_version("tensorflow"),
            }
        )

    return app


def start_container(session_id):
    """Starts a new Docker sandbox container for the given session.
    Allocates a dynamic port, spawns a container, and waits for it to become healthy.

    Args:
        session_id (str): The session identifier.

    Raises:
        RuntimeError: If the docker run command fails.
        TimeoutError: If the sandbox does not pass health checks in time.
    """
    stop_container(session_id)

    container_name = f"{_CONTAINER_NAME_PREFIX}{session_id}"
    result = subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--rm",
            "--name",
            container_name,
            "--network",
            "bridge",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--memory",
            "4g",
            "--cpus",
            "2",
            "-p",
            f"127.0.0.1::8080",
            "circinspect-sandbox",
        ],
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"docker run failed: {result.stderr.decode().strip()}")

    container_id = result.stdout.decode().strip()

    try:
        inspect = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{(index (index .NetworkSettings.Ports \"8080/tcp\") 0).HostPort}}",
                container_id,
            ],
            capture_output=True,
            text=True,
        )
        if inspect.returncode != 0:
            raise RuntimeError(f"docker inspect failed: {inspect.stderr.strip()}")
        port = int(inspect.stdout.strip())

        # Wait until the Flask server is accepting connections.
        _wait_for_ready(port)
    except Exception:
        # Something went wrong after the container was already started
        # stop it so it doesn't leak as an untracked running container,
        # then propagate the original failure.
        stop_container(session_id)
        raise

    # Only record the port after the server is confirmed healthy.
    _session_ports[session_id] = port
    _session_last_active[session_id] = time.time()

    return port


def stop_container(session_id):
    """Stops and removes the running sandbox container for the session.

    Args:
        session_id (str): The session identifier.
    """
    container_name = f"{_CONTAINER_NAME_PREFIX}{session_id}"
    subprocess.run(["docker", "stop", "--time", "1", container_name], capture_output=True)
    _session_ports.pop(session_id, None)
    _session_last_active.pop(session_id, None)


def _find_free_port():
    """Ask the OS for a free localhost port by binding to port 0.

    Returns:
        int: A free system port number on localhost.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_ready(port):
    """Poll GET /health until the sandbox server responds or we time out.

    Args:
        port (int): The local port where the sandbox is exposed.

    Raises:
        TimeoutError: If the server fails to respond within the configured timeout.
    """
    deadline = time.time() + _HEALTH_CHECK_TIMEOUT
    url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        try:
            r = requests.get(url, timeout=1)
            if r.status_code == 200:
                return
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(_HEALTH_CHECK_INTERVAL)
    raise TimeoutError(
        f"Sandbox container did not become ready within " f"{_HEALTH_CHECK_TIMEOUT}s on port {port}"
    )


def _is_healthy(port):
    """Checks if the sandbox Flask server on the given port responds to /health.

    Args:
        port (int): The local port to check.

    Returns:
        bool: True if the server returns a 200 OK status, False otherwise.
    """
    try:
        r = requests.get(f"http://127.0.0.1:{port}/health", timeout=1)
        return r.status_code == 200
    except Exception:
        return False


def safe_version(pkg):
    try:
        return importlib.metadata.version(pkg)
    except Exception:
        return "unavailable"