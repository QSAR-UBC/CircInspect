#!/usr/bin/env bash
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

# One-command local launcher for CircInspect:
#     ./launch.sh
# Starts the backend and the frontend, then opens CircInspect in your browser. Press Ctrl+C to stop everything,
# including any sandbox containers.
set -euo pipefail
cd "$(dirname "$0")"

ROOT="$(pwd)"
STATE_DIR="$ROOT/.circinspect-launch"
BACKEND_LOG="$STATE_DIR/backend.log"
BACKEND_PORT=5000  # client/package.json proxies API calls here
BACKEND_PID=""

log() { echo "[circinspect] $*"; }
die() { log "ERROR: $*" >&2; exit 1; }
port_open() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }

# Stops everything this script started. Runs on any exit, including Ctrl+C.
cleanup() {
    trap - EXIT INT TERM HUP
    log "Shutting down..."
    if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
        kill "$BACKEND_PID" 2>/dev/null || true
        wait "$BACKEND_PID" 2>/dev/null || true
    fi
    local containers
    containers="$(docker ps -aq --filter "name=circinspect-sandbox-" 2>/dev/null || true)"
    if [ -n "$containers" ]; then
        log "Stopping sandbox containers..."
        # shellcheck disable=SC2086  # one argument per container id
        docker rm -f $containers >/dev/null 2>&1 || true
    fi
    log "Done."
}
trap cleanup EXIT
trap 'exit 130' INT TERM HUP

# ---- prerequisites
command -v docker >/dev/null 2>&1 || die "Docker is not installed."
docker info >/dev/null 2>&1 || die "Docker is not running, or your user can't run docker without sudo."
command -v poetry >/dev/null 2>&1 || die "poetry is not installed (https://python-poetry.org/docs/#installation)."
command -v npm >/dev/null 2>&1 || die "npm is not installed. Install Node.js first."
port_open "$BACKEND_PORT" && die "Port $BACKEND_PORT is already in use. Stop whatever is using it and try again."
mkdir -p "$STATE_DIR"

PY="$(poetry env info --executable 2>/dev/null || true)"
if [ -z "$PY" ] || [ ! -x "$PY" ]; then
    log "Installing Python dependencies (poetry install)..."
    poetry install --no-interaction
    PY="$(poetry env info --executable)"
fi

if [ ! -d client/node_modules ]; then
    log "Installing frontend dependencies (npm install)..."
    (cd client && npm install)
fi

if ! docker image inspect circinspect-sandbox >/dev/null 2>&1; then
    log "Building the sandbox Docker image (first run can take several minutes)..."
    docker build -t circinspect-sandbox -f server/sandbox/Dockerfile .
fi

# ---- backend
log "Starting the backend (logs: $BACKEND_LOG)..."
# Unbuffered so printed output reaches the log immediately.
PYTHONUNBUFFERED=1 "$PY" -m flask --app server.container_manager run --port "$BACKEND_PORT" >"$BACKEND_LOG" 2>&1 &
BACKEND_PID=$!
for _ in $(seq 1 60); do
    port_open "$BACKEND_PORT" && break
    kill -0 "$BACKEND_PID" 2>/dev/null || die "The backend failed to start; see $BACKEND_LOG"
    sleep 1
done
port_open "$BACKEND_PORT" || die "The backend did not start within 60s; see $BACKEND_LOG"

# ---- frontend (runs in the foreground until Ctrl+C)
log "Starting the frontend; CircInspect will open at http://localhost:3000"
log "Press Ctrl+C to stop."
(cd client && npm start)
