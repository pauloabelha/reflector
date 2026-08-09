"""Integration contract for the live v1 runner.

These tests deliberately exercise only the seam that ``experiment.py`` must
own.  The graph, ledger, Qwen protocol, and census each have their own unit
tests; duplicating them here would hide integration mistakes behind mocks.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping


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


def test_graph_event_batch_is_one_atomic_outer_commit_and_replays_exactly(tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    workspace_id = "batch-workspace"
    state = GRAPH.GraphState()
    graph_events = []
    for index in range(4):
        event = GRAPH.object_event(
            state,
            kind="schema",
            created_by="r2",
            identity={"index": index},
            payload={"predicate": f"p{index}"},
            event_key=f"schema:{index}",
        )
        state = GRAPH.apply_event(state, event)
        graph_events.append(event)

    legacy = RUNNER.persist_graph_events(root, workspace_id, graph_events[:1])
    persisted = RUNNER.persist_graph_events(root, workspace_id, graph_events[1:])

    assert len(legacy) == 1
    assert legacy[0]["event_type"] == "EpistemicGraphEvent"
    assert len(persisted) == 1
    assert persisted[0]["event_type"] == "EpistemicGraphBatch"
    assert persisted[0]["payload"]["graph_event_count"] == 3
    documents = LEDGER.graph_event_documents(LEDGER.list_events(root), root)
    assert documents == [GRAPH.event_document(event) for event in graph_events]
    rebuilt, replayed = RUNNER.rebuild_graph(root)
    assert rebuilt == state
    assert replayed == tuple(graph_events)


def test_uncommitted_graph_batch_blob_is_invisible_to_recovery(tmp_path: Path) -> None:
    state = GRAPH.GraphState()
    event = GRAPH.object_event(
        state,
        kind="schema",
        created_by="r2",
        identity={"name": "orphan"},
        payload={"predicate": "orphan"},
        event_key="orphan",
    )
    document = GRAPH.event_document(event)
    LEDGER.put_blob(
        tmp_path,
        {
            "protocol": "shared-attention-graph-batch-v1",
            "count": 1,
            "first_revision": document["seq"],
            "last_revision": document["seq"],
            "first_prev_hash": document["prev_hash"],
            "last_event_hash": document["event_hash"],
            "documents": [document],
        },
    )

    assert LEDGER.graph_event_documents(LEDGER.list_events(tmp_path), tmp_path) == []


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


def test_matching_criticism_deduplicates_same_witness_across_actions() -> None:
    state = GRAPH.GraphState()
    proposal = GRAPH.object_event(
        state,
        kind="schema",
        created_by="qwen",
        identity={"name": "ambiguous"},
        payload={"conditions": []},
        event_key="qwen:ambiguous",
    )
    state = GRAPH.apply_event(state, proposal)
    proposal_id = state.objects[0].object_id
    witness = {"status": "ambiguous", "grounding_count": 5, "effect_pair_count": 3}
    criticism = GRAPH.ingest_structured_criticism(
        state,
        worker="r2",
        target_id=proposal_id,
        status="ambiguous-grounding",
        criticism_key="action-8",
        payload={"observation_digest": "first", "structured_witness": witness},
    )

    found = RUNNER.matching_structured_criticism(
        criticism.state,
        worker="r2",
        target_id=proposal_id,
        status="ambiguous-grounding",
        witness=witness,
    )

    assert found is not None
    assert found.object_id == criticism.object_ids[0]
    assert len(GRAPH.find_objects(criticism.state, kind="structured_criticism")) == 1


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


def test_ambiguous_grounding_witnesses_preserve_competing_pairs() -> None:
    state = {
        "entities": [
            {"id": "f00", "area": 45, "outline_class": "o1", "interior_layout_class": "i1"},
            {"id": "f01", "area": 45, "outline_class": "o1", "interior_layout_class": "i2"},
            {"id": "f02", "area": 45, "outline_class": "o1", "interior_layout_class": "i2"},
            {"id": "f03", "area": 316, "outline_class": "hud", "interior_layout_class": "hud"},
        ],
        "relations": [
            {"predicate": "SameArea", "arguments": [left, right]}
            for left, right in (("f00", "f01"), ("f00", "f02"), ("f01", "f02"))
        ]
        + [
            {"predicate": "DifferentArea", "arguments": [left, "f03"]}
            for left in ("f00", "f01", "f02")
        ],
    }
    conditions = (
        ("SameArea", ("?a", "?b")),
        ("DifferentArea", ("?a", "?c")),
    )
    template = RUNNER.V0.V0.Template(
        conditions=conditions,
        operator="Decrease",
        effect_variables=("?a", "?b"),
        canonical_hash="ambiguous",
        provenance="externally-proposed",
    )

    witness = RUNNER.AMBIGUITY.compile_ambiguity_witness(template, state)

    pairs = {
        tuple(item["effect_pair"])
        for item in witness["effect_pairs"]
    }
    assert pairs == {("f00", "f01"), ("f00", "f02"), ("f01", "f02")}
    assert witness["candidate_substitutions"]
    assert "exactly one" in witness["refinement_goal"]


def test_failed_progress_atomically_preserves_readable_checkpoint(tmp_path: Path, monkeypatch: Any) -> None:
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr(RUNNER, "ARTIFACTS", artifacts)
    job = {"profile_id": "balanced", "game": "ar25", "arm_id": "shared_attention_qwen"}
    path = artifacts / "progress" / "balanced--ar25--shared_attention_qwen.json"
    RUNNER.LEDGER.atomic_json(
        path,
        {
            "status": "running",
            "actions": 16,
            "levels_completed": 0,
            "graph_metrics": {"object_count": 6816},
        },
    )

    recorded = RUNNER.write_failed_progress(job, "RuntimeError: synthetic failure")
    persisted = json.loads(path.read_text(encoding="utf-8"))

    assert persisted == recorded
    assert persisted["status"] == "failed"
    assert persisted["error"] == "RuntimeError: synthetic failure"
    assert persisted["actions"] == 16
    assert persisted["graph_metrics"] == {"object_count": 6816}
    assert persisted["game"] == "ar25"


def test_run_census_catch_marks_failed_job_progress(tmp_path: Path, monkeypatch: Any) -> None:
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr(RUNNER, "ARTIFACTS", artifacts)
    monkeypatch.setattr(RUNNER, "append_status", lambda _message: None)

    class FakeQueue:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            self.stopped = False

        def stop(self, *, drain: bool = True) -> None:
            self.stopped = drain

    monkeypatch.setattr(RUNNER.QC, "ResidentServerQueue", FakeQueue)

    def fail(_job: Any, _fifo: Any) -> Any:
        path = artifacts / "progress" / "balanced--ar25--r2_only.json"
        RUNNER.LEDGER.atomic_json(path, {"status": "running", "actions": 7})
        raise ValueError("observable")

    monkeypatch.setattr(RUNNER, "run_episode", fail)
    summary = RUNNER.run_census(
        {
            "games": ["ar25"],
            "profiles": {"balanced": {}},
            "arms": ["r2_only"],
            "max_parallel_arc_workers": 1,
            "qwen": {"endpoint": "unused"},
        },
        {},
    )
    progress = json.loads(
        (artifacts / "progress" / "balanced--ar25--r2_only.json").read_text(
            encoding="utf-8"
        )
    )

    assert summary["complete"] is False
    assert summary["failures"][0]["error"] == "ValueError: observable"
    assert progress["status"] == "failed"
    assert progress["error"] == "ValueError: observable"
    assert progress["actions"] == 7
    failed_result = json.loads(
        (artifacts / "results" / "balanced--ar25--r2_only.json").read_text(encoding="utf-8")
    )
    assert failed_result["status"] == "failed"


def test_independent_census_failure_does_not_cancel_other_jobs(tmp_path: Path, monkeypatch: Any) -> None:
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr(RUNNER, "ARTIFACTS", artifacts)
    monkeypatch.setattr(RUNNER, "append_status", lambda _message: None)

    class FakeQueue:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def stop(self, *, drain: bool = True) -> None:
            assert drain

    monkeypatch.setattr(RUNNER.QC, "ResidentServerQueue", FakeQueue)

    def mixed(job: Mapping[str, Any], _fifo: Any) -> dict[str, Any]:
        if job["arm_id"] == "r2_only":
            raise ConnectionError("job-local environment loss")
        return {
            "profile_id": job["profile_id"],
            "game": job["game"],
            "arm_id": job["arm_id"],
            "levels_completed": 1,
            "actions": 9,
            "graph_metrics": {"grounded_pickup_directions": {}},
            "replay_verified": True,
            "support_authority_violations": 0,
        }

    monkeypatch.setattr(RUNNER, "run_episode", mixed)
    summary = RUNNER.run_census(
        {
            "games": ["ar25"],
            "profiles": {"balanced": {}},
            "arms": ["r2_only", "shared_attention_qwen"],
            "max_parallel_arc_workers": 2,
            "qwen": {"endpoint": "unused"},
        },
        {},
    )

    assert len(summary["results"]) == 1
    assert len(summary["failures"]) == 1
    assert summary["failures"][0]["failure_classification"] == {
        "scope": "job",
        "category": "independent_job_failure",
        "request_cancellation": False,
    }
    assert summary["cancelled_jobs"] == []
    assert summary["cancellation_requested"] is False
    assert summary["counts"] == {
        "total": 2,
        "completed": 1,
        "failed": 1,
        "cancelled": 0,
        "independent_job_failures": 1,
        "global_invariant_failures": 0,
    }


def test_failure_classifier_cancels_only_explicit_global_invariants() -> None:
    ordinary = RUNNER.classify_census_failure(TimeoutError("one game timed out"))
    replay = RUNNER.classify_census_failure(RuntimeError("replay successor mismatch"))
    ledger = RUNNER.classify_census_failure(RUNNER.LEDGER.LedgerError("event chain is not contiguous"))
    support = RUNNER.classify_census_failure(result={"support_authority_violations": 1})

    assert ordinary["request_cancellation"] is False
    assert replay["category"] == "replay_or_workspace_invariant"
    assert ledger["category"] == "ledger_integrity_violation"
    assert support["category"] == "support_authority_violation"
    assert replay["request_cancellation"] is True
    assert ledger["request_cancellation"] is True
    assert support["request_cancellation"] is True


def test_reported_support_authority_violation_requests_global_cancellation(
    tmp_path: Path, monkeypatch: Any
) -> None:
    artifacts = tmp_path / "artifacts"
    monkeypatch.setattr(RUNNER, "ARTIFACTS", artifacts)
    monkeypatch.setattr(RUNNER, "append_status", lambda _message: None)

    class FakeQueue:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            pass

        def stop(self, *, drain: bool = True) -> None:
            assert drain

    monkeypatch.setattr(RUNNER.QC, "ResidentServerQueue", FakeQueue)
    monkeypatch.setattr(
        RUNNER,
        "run_episode",
        lambda job, _fifo: {
            "profile_id": job["profile_id"],
            "game": job["game"],
            "arm_id": job["arm_id"],
            "support_authority_violations": 2,
        },
    )

    summary = RUNNER.run_census(
        {
            "games": ["ar25"],
            "profiles": {"balanced": {}},
            "arms": ["r2_only"],
            "max_parallel_arc_workers": 1,
            "qwen": {"endpoint": "unused"},
        },
        {},
    )

    assert summary["cancellation_requested"] is True
    assert summary["counts"]["global_invariant_failures"] == 1
    assert summary["failures"][0]["failure_classification"]["category"] == "support_authority_violation"


def test_initial_full_object_count_supports_compact_and_legacy_encodings() -> None:
    compact = {
        "document": {
            "full_materialization": {"object_columns": {"created_revision_deltas": [0, 1, 1]}},
            "object_index": {"encoding": "columnar-v1", "ids": ["o0", "o1", "o2"]},
        }
    }
    legacy = {
        "document": {
            "full_materialization": {"objects": [{"id": "a"}, {"id": "b"}]},
            "object_index": [{"id": "a"}, {"id": "b"}],
        }
    }

    assert RUNNER.initial_full_object_count((compact,)) == 3
    assert RUNNER.initial_full_object_count((legacy,)) == 2
    assert RUNNER.initial_full_object_count(({"document": {"full_materialization": None}},)) == 0


def test_qwen_successor_is_queued_only_after_durable_activation(monkeypatch: Any, tmp_path: Path) -> None:
    order: list[str] = []
    state = GRAPH.GraphState()

    def activate(*_args: Any, **_kwargs: Any) -> tuple[Any, list[dict[str, Any]]]:
        order.append("activate-durable")
        return state, [{"status": "bound"}]

    def reread(_root: Any) -> tuple[Any, tuple[Any, ...]]:
        assert order == ["activate-durable"]
        order.append("reread-ledger")
        return state, ()

    def queue(*_args: Any, **_kwargs: Any) -> tuple[str, str, str]:
        assert order == ["activate-durable", "reread-ledger"]
        order.append("queue-successor")
        return ("task", "turn", "future")

    monkeypatch.setattr(RUNNER, "activate_visible_qwen", activate)
    monkeypatch.setattr(RUNNER, "graph_state", reread)
    monkeypatch.setattr(RUNNER, "queue_qwen", queue)
    history = tuple({"index": index} for index in range(8))

    _state, _events, pending, task_count, records = RUNNER.activate_then_maybe_queue_qwen(
        tmp_path,
        "workspace",
        state,
        (),
        None,
        live_qwen=True,
        controller=object(),
        grid=((0,),),
        legal=(1,),
        history=history,
        profile={},
        activated=set(),
        config={"qwen": {"trigger_action_counts": [8], "max_calls_per_episode": 3}},
        fifo=object(),
        task_count=1,
    )

    assert order == ["activate-durable", "reread-ledger", "queue-successor"]
    assert pending == ("task", "turn", "future")
    assert task_count == 2
    assert records == [{"status": "bound"}]
