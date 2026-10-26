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

import subprocess
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, call, MagicMock
from server import container_manager

class StopLoopException(Exception):
    pass

def test_reaper_loop_no_expired_sessions():
    """
    Test that the reaper loop does not call stop_container when all sessions
    have been active recently enough and are not expired.
    """
    with patch("server.container_manager.time.sleep") as mock_sleep, \
         patch("server.container_manager.time.time") as mock_time, \
         patch("server.container_manager._reconcile_with_docker"), \
         patch("server.container_manager.stop_container") as mock_stop_container, \
         patch.dict("server.container_manager._session_last_active", {"session1": 1000, "session2": 2000}, clear=True):

        mock_sleep.side_effect = [None, StopLoopException]
        mock_time.return_value = 2500

        try:
            container_manager._reaper_loop()
        except StopLoopException:
            pass

        assert mock_sleep.call_count == 2
        mock_stop_container.assert_not_called()

def test_reaper_loop_with_expired_sessions():
    """
    Test that the reaper loop calls stop_container for a single session
    that has exceeded the inactivity timeout, while leaving others alone.
    """
    with patch("server.container_manager.time.sleep") as mock_sleep, \
         patch("server.container_manager.time.time") as mock_time, \
         patch("server.container_manager._reconcile_with_docker"), \
         patch("server.container_manager.stop_container") as mock_stop_container, \
         patch.dict("server.container_manager._session_last_active", {"session1": 1000, "session2": 2000, "session3": 3000}, clear=True):

        mock_sleep.side_effect = [None, StopLoopException]
        mock_time.return_value = 5000

        try:
            container_manager._reaper_loop()
        except StopLoopException:
            pass

        assert mock_sleep.call_count == 2
        mock_stop_container.assert_called_once_with("session1")

def test_reaper_loop_multiple_expired_sessions():
    """
    Test that the reaper loop calls stop_container for all sessions
    that have exceeded the inactivity timeout.
    """
    with patch("server.container_manager.time.sleep") as mock_sleep, \
         patch("server.container_manager.time.time") as mock_time, \
         patch("server.container_manager._reconcile_with_docker"), \
         patch("server.container_manager.stop_container") as mock_stop_container, \
         patch.dict("server.container_manager._session_last_active", {"session1": 1000, "session2": 2000, "session3": 5000}, clear=True):

        mock_sleep.side_effect = [None, StopLoopException]
        mock_time.return_value = 6000

        try:
            container_manager._reaper_loop()
        except StopLoopException:
            pass

        assert mock_sleep.call_count == 2
        mock_stop_container.assert_has_calls([call("session1"), call("session2")], any_order=True)
        assert mock_stop_container.call_count == 2


def test_reaper_loop_survives_reconcile_failure():
    """
    A `docker ps` reconciliation failure must not kill the reaper thread 
    reaping of already-known sessions should still proceed on every pass.
    """
    with patch("server.container_manager.time.sleep") as mock_sleep, \
         patch("server.container_manager.time.time") as mock_time, \
         patch("server.container_manager._reconcile_with_docker", side_effect=RuntimeError("docker ps failed")), \
         patch("server.container_manager.stop_container") as mock_stop_container, \
         patch.dict("server.container_manager._session_last_active", {"session1": 1000}, clear=True):

        mock_sleep.side_effect = [None, None, StopLoopException]
        mock_time.return_value = 5000

        try:
            container_manager._reaper_loop()
        except StopLoopException:
            pass

        assert mock_sleep.call_count == 3
        assert mock_stop_container.call_count == 2  # one per completed pass


def test_reaper_loop_survives_stop_container_failure_and_reaps_others():
    """
    One container failing to stop (e.g. a `docker stop` hiccup) must not
    prevent the reaper from attempting the rest of the expired sessions,
    and must not kill the loop for future passes.
    """
    with patch("server.container_manager.time.sleep") as mock_sleep, \
         patch("server.container_manager.time.time") as mock_time, \
         patch("server.container_manager._reconcile_with_docker"), \
         patch("server.container_manager.stop_container") as mock_stop_container, \
         patch.dict("server.container_manager._session_last_active", {"session1": 1000, "session2": 1000}, clear=True):

        mock_sleep.side_effect = [None, StopLoopException]
        mock_time.return_value = 5000
        mock_stop_container.side_effect = [RuntimeError("docker daemon hiccup"), None]

        try:
            container_manager._reaper_loop()
        except StopLoopException:
            pass

        assert mock_sleep.call_count == 2
        assert mock_stop_container.call_count == 2


def test_reaper_loop_calls_reconcile_each_pass():
    with patch("server.container_manager.time.sleep") as mock_sleep, \
         patch("server.container_manager.time.time", return_value=0), \
         patch("server.container_manager._reconcile_with_docker") as mock_reconcile, \
         patch("server.container_manager.stop_container"), \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):

        mock_sleep.side_effect = [None, None, StopLoopException]

        try:
            container_manager._reaper_loop()
        except StopLoopException:
            pass

        assert mock_reconcile.call_count == 2


def test_reap_if_still_expired_reaps_expired_session():
    with patch("server.container_manager.time.time", return_value=5000), \
         patch("server.container_manager.stop_container") as mock_stop, \
         patch.dict("server.container_manager._session_last_active", {"session1": 1000}, clear=True):
        container_manager._reap_if_still_expired("session1")
        mock_stop.assert_called_once_with("session1")


def test_reap_if_still_expired_skips_reactivated_session():
    """
    Regression test for the race condition where a session that was flagged
    expired by a stale snapshot gets reactivated (e.g. a concurrent request
    bumps its activity) before the reaper actually stops it.
    """
    with patch("server.container_manager.time.time", return_value=5000), \
         patch("server.container_manager.stop_container") as mock_stop, \
         patch.dict("server.container_manager._session_last_active", {"session1": 4999}, clear=True):
        container_manager._reap_if_still_expired("session1")
        mock_stop.assert_not_called()


def test_reap_if_still_expired_skips_already_removed_session():
    with patch("server.container_manager.time.time", return_value=5000), \
         patch("server.container_manager.stop_container") as mock_stop, \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):
        container_manager._reap_if_still_expired("session1")
        mock_stop.assert_not_called()


def test_reap_if_still_expired_swallows_stop_container_exception():
    with patch("server.container_manager.time.time", return_value=5000), \
         patch("server.container_manager.stop_container", side_effect=RuntimeError("docker daemon hiccup")) as mock_stop, \
         patch.dict("server.container_manager._session_last_active", {"session1": 1000}, clear=True):
        container_manager._reap_if_still_expired("session1")  # must not raise
        mock_stop.assert_called_once_with("session1")


def test_container_started_at_parses_nanosecond_timestamp():
    """Docker reports StartedAt with nanosecond precision; Python's %f caps at 6 digits."""
    result = MagicMock(returncode=0, stdout="2024-01-01T12:00:00.123456789Z\n")
    with patch("server.container_manager.subprocess.run", return_value=result):
        ts = container_manager._container_started_at("circinspect-sandbox-abc")

    expected = datetime.strptime(
        "2024-01-01T12:00:00.123456Z", "%Y-%m-%dT%H:%M:%S.%fZ"
    ).replace(tzinfo=timezone.utc).timestamp()
    assert ts == expected


def test_container_started_at_returns_none_on_inspect_failure():
    result = MagicMock(returncode=1, stdout="")
    with patch("server.container_manager.subprocess.run", return_value=result):
        assert container_manager._container_started_at("circinspect-sandbox-abc") is None


def test_container_started_at_returns_none_on_unparseable_timestamp():
    result = MagicMock(returncode=0, stdout="not-a-timestamp\n")
    with patch("server.container_manager.subprocess.run", return_value=result):
        assert container_manager._container_started_at("circinspect-sandbox-abc") is None


def test_reconcile_with_docker_adds_untracked_running_container():
    """
    Regression test for containers Docker knows about but this process has
    no activity record for (e.g. left over from a server crash/restart).
    They should be seeded with their real Docker start time so the reaper
    can eventually reclaim them, while already-tracked sessions are left alone.
    """
    ps_result = MagicMock(returncode=0, stdout="circinspect-sandbox-abc\ncircinspect-sandbox-def\n")
    inspect_result = MagicMock(returncode=0, stdout="2024-01-01T12:00:00.123456789Z\n")

    with patch("server.container_manager.subprocess.run") as mock_run, \
         patch.dict("server.container_manager._session_last_active", {"abc": 1000.0}, clear=True):
        mock_run.side_effect = [ps_result, inspect_result]

        container_manager._reconcile_with_docker()

        assert container_manager._session_last_active["abc"] == 1000.0  # untouched

        expected = datetime.strptime(
            "2024-01-01T12:00:00.123456Z", "%Y-%m-%dT%H:%M:%S.%fZ"
        ).replace(tzinfo=timezone.utc).timestamp()
        assert container_manager._session_last_active["def"] == expected

        # Only the untracked container ("def") should trigger an inspect call.
        inspect_calls = [c for c in mock_run.call_args_list if c.args[0][1] == "inspect"]
        assert len(inspect_calls) == 1
        assert inspect_calls[0].args[0][-1] == "circinspect-sandbox-def"


def test_reconcile_with_docker_skips_when_all_tracked():
    ps_result = MagicMock(returncode=0, stdout="circinspect-sandbox-abc\n")
    with patch("server.container_manager.subprocess.run", return_value=ps_result) as mock_run, \
         patch.dict("server.container_manager._session_last_active", {"abc": 1000.0}, clear=True):
        container_manager._reconcile_with_docker()
        assert mock_run.call_count == 1  # only the `docker ps` call, no inspects
        assert container_manager._session_last_active == {"abc": 1000.0}


def test_reconcile_with_docker_handles_docker_ps_failure():
    ps_result = MagicMock(returncode=1, stdout="")
    with patch("server.container_manager.subprocess.run", return_value=ps_result), \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):
        container_manager._reconcile_with_docker()  # must not raise
        assert container_manager._session_last_active == {}


def _docker_result(returncode=0, stdout=b"", stderr=b""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


def test_stop_container_runs_docker_stop_with_correct_container_name():
    with patch("server.container_manager.subprocess.run", return_value=_docker_result()) as mock_run, \
         patch.dict("server.container_manager._session_ports", {}, clear=True), \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):

        container_manager.stop_container("session1")

        mock_run.assert_called_once_with(
            ["docker", "stop", "--time", "1", "circinspect-sandbox-session1"],
            capture_output=True,
        )


def test_stop_container_clears_tracking_dicts():
    with patch("server.container_manager.subprocess.run", return_value=_docker_result()), \
         patch.dict("server.container_manager._session_ports", {"session1": 1234}, clear=True), \
         patch.dict("server.container_manager._session_last_active", {"session1": 1000}, clear=True):

        container_manager.stop_container("session1")

        assert "session1" not in container_manager._session_ports
        assert "session1" not in container_manager._session_last_active


def test_stop_container_is_safe_when_session_untracked():
    """stop_container may be called for a session that was never registered
    (e.g. the preemptive call at the start of start_container) - it must not
    raise, and must leave unrelated sessions alone."""
    with patch("server.container_manager.subprocess.run", return_value=_docker_result()), \
         patch.dict("server.container_manager._session_ports", {"other": 5678}, clear=True), \
         patch.dict("server.container_manager._session_last_active", {"other": 2000}, clear=True):

        container_manager.stop_container("session1")  # must not raise

        assert container_manager._session_ports == {"other": 5678}
        assert container_manager._session_last_active == {"other": 2000}


def test_start_container_docker_run_failure_raises_without_inspect():
    run_result = _docker_result(returncode=1, stdout=b"", stderr=b"no such image")

    with patch("server.container_manager.subprocess.run", return_value=run_result) as mock_run, \
         patch.dict("server.container_manager._session_ports", {}, clear=True), \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):

        with pytest.raises(RuntimeError):
            container_manager.start_container("session1")

        inspect_calls = [c for c in mock_run.call_args_list if c.args[0][1] == "inspect"]
        assert inspect_calls == []
        assert "session1" not in container_manager._session_ports
        assert "session1" not in container_manager._session_last_active


def test_start_container_stops_leaked_container_on_inspect_failure():
    run_result = _docker_result(returncode=0, stdout=b"container123\n")
    inspect_result = _docker_result(returncode=1, stdout="", stderr="inspect failed")

    def side_effect(cmd, **kwargs):
        if cmd[1] == "run":
            return run_result
        if cmd[1] == "inspect":
            return inspect_result
        return _docker_result()

    with patch("server.container_manager.subprocess.run", side_effect=side_effect), \
         patch("server.container_manager.stop_container") as mock_stop, \
         patch.dict("server.container_manager._session_ports", {}, clear=True), \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):

        with pytest.raises(RuntimeError):
            container_manager.start_container("session1")

        # Called once to preempt a name collision, once to clean up the leak.
        assert mock_stop.call_count == 2
        mock_stop.assert_called_with("session1")
        assert "session1" not in container_manager._session_ports
        assert "session1" not in container_manager._session_last_active


def test_start_container_stops_leaked_container_on_unparseable_port():
    run_result = _docker_result(returncode=0, stdout=b"container123\n")
    inspect_result = _docker_result(returncode=0, stdout="not-a-port", stderr="")

    def side_effect(cmd, **kwargs):
        if cmd[1] == "run":
            return run_result
        if cmd[1] == "inspect":
            return inspect_result
        return _docker_result()

    with patch("server.container_manager.subprocess.run", side_effect=side_effect), \
         patch("server.container_manager.stop_container") as mock_stop, \
         patch.dict("server.container_manager._session_ports", {}, clear=True), \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):

        with pytest.raises(ValueError):
            container_manager.start_container("session1")

        assert mock_stop.call_count == 2
        assert "session1" not in container_manager._session_ports


def test_start_container_stops_container_on_health_check_timeout():
    run_result = _docker_result(returncode=0, stdout=b"container123\n")
    inspect_result = _docker_result(returncode=0, stdout="32768", stderr="")

    def side_effect(cmd, **kwargs):
        if cmd[1] == "run":
            return run_result
        if cmd[1] == "inspect":
            return inspect_result
        return _docker_result()

    with patch("server.container_manager.subprocess.run", side_effect=side_effect), \
         patch("server.container_manager._wait_for_ready", side_effect=TimeoutError("not ready")), \
         patch("server.container_manager.stop_container") as mock_stop, \
         patch.dict("server.container_manager._session_ports", {}, clear=True), \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):

        with pytest.raises(TimeoutError):
            container_manager.start_container("session1")

        assert mock_stop.call_count == 2
        assert "session1" not in container_manager._session_ports
        assert "session1" not in container_manager._session_last_active


def test_start_container_registers_session_on_success():
    run_result = _docker_result(returncode=0, stdout=b"container123\n")
    inspect_result = _docker_result(returncode=0, stdout="32768", stderr="")

    def side_effect(cmd, **kwargs):
        if cmd[1] == "run":
            return run_result
        if cmd[1] == "inspect":
            return inspect_result
        return _docker_result()

    with patch("server.container_manager.subprocess.run", side_effect=side_effect), \
         patch("server.container_manager._wait_for_ready"), \
         patch.dict("server.container_manager._session_ports", {}, clear=True), \
         patch.dict("server.container_manager._session_last_active", {}, clear=True):

        port = container_manager.start_container("session1")

        assert port == 32768
        assert container_manager._session_ports["session1"] == 32768
        assert "session1" in container_manager._session_last_active
