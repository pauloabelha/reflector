"""Integration contract for the live v1 runner.

These tests deliberately exercise only the seam that ``experiment.py`` must
own.  The graph, ledger, Qwen protocol, and census each have their own unit
tests; duplicating them here would hide integration mistakes behind mocks.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GRAPH = load("shared_attention_runner_test_graph", HERE / "epistemic_graph.py")
LEDGER = load("shared_attention_runner_test_ledger", HERE / "ledger.py")
RUNNER = load("shared_attention_runner_tests", HERE / "experiment.py")


def add_entity(state: Any, *, name: str) -> tuple[Any, Any]:
    event = GRAPH.object_event(
        state,
        kind="entity",
        created_by="environment",
        identity={"name": name},
        payload={"shape": "solid", "area": 4},
        event_key=f"entity:{name}",
    )
    state = GRAPH.apply_event(state, event)
    item = next(value for value in state.objects if value.created_revision == event.seq)
    return state, (event, item)


def test_job_matrix_uses_a_fresh_workspace_for_every_profile_arm_pair(tmp_path: Path) -> None:
    config = {
        "games": ["ar25", "bp35"],
        "arms": ["r2_only", "shared_attention_qwen"],
        "profiles": {"balanced": {}, "wide_frontier": {}},
    }

    jobs = RUNNER.build_jobs(config, artifacts_root=tmp_path)

    assert len(jobs) == 8
    roots = [Path(job["workspace_root"]) for job in jobs]
    assert len(set(roots)) == len(roots)
    assert all(not root.exists() for root in roots)
    assert {
        (job["profile_id"], job["game"], job["arm_id"])
        for job in jobs
    } == {
        (profile, game, arm)
        for profile in config["profiles"]
        for game in config["games"]
        for arm in config["arms"]
    }
    for profile in config["profiles"]:
        for game in config["games"]:
            pair = [job for job in jobs if job["profile_id"] == profile and job["game"] == game]
            assert len(pair) == 2
            assert len({job["pair_id"] for job in pair}) == 1


def test_graph_events_and_control_events_rebuild_from_one_ledger(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    workspace_id = "balanced--ar25--r2_only"
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="WorkspaceStarted",
        actor="coordinator",
        payload={"job_key": "frozen-job"},
    )
    state = GRAPH.GraphState()
    state, (entity_event, entity) = add_entity(state, name="object-a")

    persisted = RUNNER.persist_graph_events(root, workspace_id, (entity_event,))
    assert len(persisted) == 1
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="InitialObservation",
        actor="environment",
        payload={"observation_blob": LEDGER.put_blob(root, {"digest": "initial"})},
    )

    rebuilt_state, rebuilt_events = RUNNER.rebuild_graph(root)
    assert rebuilt_state == state
    assert rebuilt_events == (entity_event,)
    assert rebuilt_state.objects[0].object_id == entity.object_id
    assert [event["event_type"] for event in LEDGER.list_events(root)] == [
        "WorkspaceStarted",
        "EpistemicGraphEvent",
        "InitialObservation",
    ]


def test_qwen_local_schema_reference_becomes_real_dependency_and_attention_not_support() -> None:
    state = GRAPH.GraphState()
    events: list[Any] = []
    state, (event_a, entity_a) = add_entity(state, name="a")
    events.append(event_a)
    state, (event_b, entity_b) = add_entity(state, name="b")
    events.append(event_b)
    compilation = {
        "valid_json_contract": True,
        "accepted": [
            {
                "kind": "schema",
                "local_ref": "s0",
                "identity": {"conditions": [{"predicate": "SameOutline", "arguments": ["?a", "?b"]}]},
                "payload": {
                    "conditions": [{"predicate": "SameOutline", "arguments": ["?a", "?b"]}],
                    "preferred_consequence": {
                        "operator": "Decrease",
                        "measure": "TranslationAlignmentResidual",
                        "arguments": ["?a", "?b"],
                    },
                },
                "dependency_ids": [entity_a.object_id, entity_b.object_id],
                "support": 0,
                "evidence": [],
            },
            {
                "kind": "explanation",
                "local_ref": "e0",
                "schema_ref": "s0",
                "identity": {"schema_ref": "s0", "bindings": {"?a": entity_a.object_id, "?b": entity_b.object_id}},
                "payload": {
                    "bindings": {"?a": entity_a.object_id, "?b": entity_b.object_id},
                    "claim": {
                        "operator": "Decrease",
                        "measure": "TranslationAlignmentResidual",
                        "arguments": ["?a", "?b"],
                    },
                },
                "dependency_ids": [entity_a.object_id, entity_b.object_id],
                "support": 0,
                "evidence": [],
            },
        ],
        "rejected": [],
        "expansion_requests": [],
    }

    result = RUNNER.ingest_qwen_compilation(
        state,
        compilation,
        response_id="response-0",
        proposal_attention_boost=2.0,
    )
    by_kind = {item.kind: item for item in result.state.objects if item.created_by == "qwen"}
    schema = by_kind["schema"]
    explanation = by_kind["explanation"]

    assert schema.object_id in explanation.dependency_ids
    assert explanation.payload["bindings"] == {"?a": entity_a.object_id, "?b": entity_b.object_id}
    assert GRAPH.support(result.state, schema.object_id) == 0
    assert GRAPH.support(result.state, explanation.object_id) == 0
    boosted = {item.object_id: item.weight for item in result.state.attention}
    assert boosted[schema.object_id] > 0
    assert boosted[explanation.object_id] > 0
    assert all(item.worker == "qwen" for item in result.state.attention)


def test_r2_frontier_pickup_is_recorded_only_when_selected_then_grounded() -> None:
    state = GRAPH.GraphState()
    state, (_entity_event, entity) = add_entity(state, name="ground")
    proposal = GRAPH.object_event(
        state,
        kind="schema",
        created_by="qwen",
        identity={"name": "candidate"},
        payload={"conditions": []},
        dependency_ids=(entity.object_id,),
        event_key="qwen:candidate",
    )
    state = GRAPH.apply_event(state, proposal)
    proposal_id = next(item.object_id for item in state.objects if item.created_by == "qwen")

    noticed = RUNNER.record_frontier_pickups(
        state,
        worker="r2",
        object_ids=(proposal_id,),
        previously_exposed_ids=(),
        exposure_key="r2-frontier-0",
    )
    assert len(noticed.state.pickups) == 1
    pickup = noticed.state.pickups[0]
    assert pickup.direction == "qwen->r2"

    binding = GRAPH.object_event(
        noticed.state,
        kind="binding",
        created_by="r2",
        identity={"name": "grounded-candidate"},
        payload={"assignments": {"?a": entity.object_id}},
        dependency_ids=(proposal_id, entity.object_id),
        event_key="r2:grounded-candidate",
    )
    bound_state = GRAPH.apply_event(noticed.state, binding)
    binding_id = next(item.object_id for item in bound_state.objects if item.created_revision == binding.seq)
    grounded = RUNNER.record_grounded_pickup(bound_state, pickup.pickup_id, binding_id, worker="r2")

    assert any(edge.kind == "grounds_pickup" for edge in grounded.state.edges)
    # Re-rendering the same frontier must not create another pickup/attention event.
    repeated = RUNNER.record_frontier_pickups(
        grounded.state,
        worker="r2",
        object_ids=(proposal_id,),
        previously_exposed_ids=(proposal_id,),
        exposure_key="r2-frontier-1",
    )
    assert repeated.events == ()


def test_initial_r2_workspace_is_first_class_groundable_and_compact(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    workspace_id = "compact-initial"
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="WorkspaceStarted",
        actor="coordinator",
        payload={"job_key": "test"},
    )
    grid = ((0, 0, 0), (0, 1, 0), (0, 0, 0))
    cognition = RUNNER.V0.R2Cognition(grid)
    state, _entities = RUNNER.ingest_initial_graph(
        root, workspace_id, GRAPH.GraphState(), cognition, grid, (1, 2)
    )

    kinds = {item.kind for item in state.objects}
    assert {"frame", "entity", "schema", "r2_binding", "runtime_summary"} <= kinds
    binding = next(item for item in state.objects if item.kind == "r2_binding")
    assert binding.payload["resolved_assignments"][0]["visual_grounding"] == "OPEN"
    rebuilt, events = RUNNER.rebuild_graph(root)
    assert rebuilt == state
    turn = RUNNER.QC.build_turn(
        state,
        events,
        RUNNER.QC.Orientation(workspace_id=workspace_id),
        request_id="qr:compact-test",
        token_budget=2400,
        max_deltas=10_000,
        compact_ids=True,
    )
    assert GRAPH.estimate_tokens(turn.document) < 8192


def test_unsupported_qwen_schema_returns_structured_non_support_criticism(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    workspace_id = "criticism"
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="WorkspaceStarted",
        actor="coordinator",
        payload={"job_key": "test"},
    )
    state = GRAPH.GraphState()
    proposal = GRAPH.object_event(
        state,
        kind="schema",
        created_by="qwen",
        identity={"name": "unsupported"},
        payload={
            "conditions": [{"predicate": "SameArea", "arguments": ["?a", "?b"]}],
            "preferred_consequence": {
                "operator": "Decrease",
                "measure": "AreaDifference",
                "arguments": ["?a", "?b"],
            },
        },
        event_key="proposal",
    )
    state = RUNNER.apply_graph_event(root, workspace_id, state, proposal)
    proposal_id = state.objects[0].object_id
    attention = GRAPH.attention_event(
        state,
        worker="qwen",
        object_id=proposal_id,
        weight=100,
        channel="inspect",
        basis_ids=(),
        contribution_key="proposal-attention",
    )
    state = RUNNER.apply_graph_event(root, workspace_id, state, attention)

    state, records = RUNNER.activate_visible_qwen(
        root,
        workspace_id,
        state,
        RUNNER.V0.WorkspaceController(),
        ((0, 0, 0), (0, 1, 0), (0, 0, 0)),
        (1, 2),
        (),
        {"frontier_token_budget": 2400, "frontier_root_limit": 12, "attention_half_life_actions": 12},
        set(),
        0,
    )

    assert records[0]["status"] == "unsupported-potential"
    criticism = next(item for item in state.objects if item.kind == "structured_criticism")
    assert proposal_id in criticism.dependency_ids
    assert GRAPH.support(state, criticism.object_id) == 0
    assert not any(edge.kind in {"supports", "refutes", "invalidates"} for edge in state.edges)
