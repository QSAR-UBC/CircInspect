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

"""
Regression tests using a real, algorithmically complex circuit (QPE-based
Shor's algorithm) as a test case. This circuit has deeply nested loops with
subroutine calls, several helper functions with returns at varying indent
levels, and mid-circuit measurements that later loop iterations condition
on via qp.cond — the exact shape of circuit that exposed bugs in:

  - command_tree_helpers.update_parent_id (return commands inside nested
    scf/call frames being attributed to the wrong enclosing scope)
  - frontend_helpers.draw_circuit (collapsed loop/subroutine blocks whose
    placeholder gate, or the qnode's terminal return measurement, referenced
    mid-circuit measurements that were never queued onto the synthetic
    drawing tape, crashing PennyLane's drawer)
"""

from tests.functions4testing import visCircuit


def _load_shor_code():
    with open("test_cases/shor_algorithm.txt", "r") as f:
        return f.read()


def _postselectable_measurement_ids(graph_data):
    """Mid-circuit measurement node ids in graph_data that have a qp.cond
    depending on them, and are therefore eligible for a postselect override.
    """
    return [
        n["measurement_id"]
        for n in graph_data["nodes"]
        if n.get("line_type") == "mid_measurement" and n.get("measurement_id") is not None
    ]


def test_shor_algorithm_runs_without_error(client, sandbox_port):
    """The full QPE-based Shor's-algorithm circuit should execute and
    render without raising a backend error."""
    result = visCircuit(client, _load_shor_code(), sandbox_port)
    assert result.get("error", None) is None


def test_shor_algorithm_produces_circuit_image(client, sandbox_port):
    """A base64 PNG circuit image must be returned for the top-level qnode."""
    result = visCircuit(client, _load_shor_code(), sandbox_port)
    assert result.get("error", None) is None
    assert isinstance(result["image"], str)
    assert len(result["image"]) > 0


def test_shor_algorithm_graph_data_has_nodes_and_edges(client, sandbox_port):
    """The command graph returned to the frontend should be well-formed and
    non-empty for such a large, deeply nested circuit."""
    result = visCircuit(client, _load_shor_code(), sandbox_port)
    assert result.get("error", None) is None
    graph_data = result["graph_data"]
    assert len(graph_data["nodes"]) > 0
    assert len(graph_data["edges"]) > 0


def test_shor_algorithm_return_commands_stay_inside_their_call_frame(client, sandbox_port):
    """Every helper function in this circuit (repeated_squaring,
    modular_inverse, doubly_controlled_adder, ...) ends with a return
    statement nested inside for/while loops. Regression test for
    update_parent_id misattributing those return commands to an outer
    scope instead of the call frame they belong to: no node should be its
    own ancestor, and every non-root node must resolve to the qnode root
    within a bounded number of parent hops.
    """
    result = visCircuit(client, _load_shor_code(), sandbox_port)
    assert result.get("error", None) is None

    nodes = result["graph_data"]["nodes"]
    by_id = {n["id"]: n for n in nodes}
    root_ids = {n["id"] for n in nodes if n.get("parent_id") is None}
    assert len(root_ids) == 1

    for node in nodes:
        seen = set()
        current = node
        while current["parent_id"] is not None:
            assert current["id"] not in seen, "cycle detected in command tree parentage"
            seen.add(current["id"])
            parent_id = current["parent_id"]
            assert parent_id in by_id, f"node {current['id']} points to a nonexistent parent"
            current = by_id[parent_id]
        assert current["id"] in root_ids


def test_shor_algorithm_mid_circuit_measurements_linked(client, sandbox_port):
    """At least one mid-circuit measurement should be recognized as having
    a dependent qp.cond and therefore be assigned a measurement_id - this is
    what makes it eligible for postselect overrides in the UI."""
    result = visCircuit(client, _load_shor_code(), sandbox_port)
    assert result.get("error", None) is None
    assert len(_postselectable_measurement_ids(result["graph_data"])) > 0


def test_shor_algorithm_postselect_override_zero(client, sandbox_port):
    """Forcing the first postselect-able mid-circuit measurement to 0 must
    not error and must still return a rendered image.

    Regression test for the frontend_helpers.draw_circuit crash where a
    collapsed loop's placeholder gate (or the qnode's terminal return
    measurement) referenced mid-circuit measurements that were never queued
    onto the synthetic drawing tape, causing PennyLane's drawer to crash
    trying to sort real and missing bit indices together.
    """
    baseline = visCircuit(client, _load_shor_code(), sandbox_port)
    assert baseline.get("error", None) is None
    target_id = _postselectable_measurement_ids(baseline["graph_data"])[0]

    result = visCircuit(
        client, _load_shor_code(), sandbox_port, postselect_overrides={target_id: 0}
    )
    assert result.get("error", None) is None
    assert len(result["image"]) > 0


def test_shor_algorithm_postselect_override_one(client, sandbox_port):
    """Same as test_shor_algorithm_postselect_override_zero but forcing the
    postselect value to 1."""
    baseline = visCircuit(client, _load_shor_code(), sandbox_port)
    assert baseline.get("error", None) is None
    target_id = _postselectable_measurement_ids(baseline["graph_data"])[0]

    result = visCircuit(
        client, _load_shor_code(), sandbox_port, postselect_overrides={target_id: 1}
    )
    assert result.get("error", None) is None
    assert len(result["image"]) > 0
