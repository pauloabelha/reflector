from __future__ import annotations

import importlib.util
import sys
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("shared_attention_epistemic_graph", HERE / "epistemic_graph.py")
assert SPEC is not None and SPEC.loader is not None
GRAPH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GRAPH
SPEC.loader.exec_module(GRAPH)


def add_object(
    state,
    events: list,
    *,
    kind: str,
    creator: str,
    name: str,
    payload: dict | None = None,
    dependencies: tuple[str, ...] = (),
):
    event = GRAPH.object_event(
        state,
        kind=kind,
        created_by=creator,
        identity={"name": name},
        payload=payload or {"label": name},
        dependency_ids=dependencies,
        event_key=f"object:{creator}:{kind}:{name}",
    )
    next_state = GRAPH.apply_event(state, event)
    events.append(event)
    created = next(item for item in next_state.objects if item.created_revision == event.seq)
    return next_state, created


def add_edge(
    state,
    events: list,
    *,
    kind: str,
    source: str,
    target: str,
    creator: str = "environment",
):
    event = GRAPH.edge_event(
        state,
        kind=kind,
        source_id=source,
        target_id=target,
        created_by=creator,
        event_key=f"edge:{kind}:{source}:{target}",
    )
    next_state = GRAPH.apply_event(state, event)
    events.append(event)
    return next_state


def add_attention(
    state,
    events: list,
    *,
    worker: str,
    object_id: str,
    key: str,
    weight: int = 3,
    basis: tuple[str, ...] = (),
):
    event = GRAPH.attention_event(
        state,
        worker=worker,
        object_id=object_id,
        weight=weight,
        channel="frontier",
        basis_ids=basis,
        contribution_key=key,
    )
    next_state = GRAPH.apply_event(state, event)
    events.append(event)
    return next_state


def test_stable_ids_and_first_class_records_are_immutable() -> None:
    first = GRAPH.make_object(
        kind="schema",
        created_by="qwen",
        created_revision=0,
        identity={"operator": "Decrease", "arguments": ["?a", "?b"]},
        payload={"conditions": ["SameOutline"]},
    )
    reordered = GRAPH.make_object(
        kind="schema",
        created_by="qwen",
        created_revision=0,
        identity={"arguments": ["?a", "?b"], "operator": "Decrease"},
        payload={"conditions": ["SameOutline"]},
    )

    assert first.object_id == reordered.object_id
    assert first == reordered
    with pytest.raises(FrozenInstanceError):
        first.kind = "binding"
    changed_copy = first.payload
    changed_copy["conditions"] = []
    assert first.payload == {"conditions": ["SameOutline"]}


def test_support_changes_only_through_environment_evidence_edges() -> None:
    state = GRAPH.GraphState()
    events: list = []
    state, schema = add_object(state, events, kind="schema", creator="qwen", name="schema")
    state, evidence = add_object(
        state,
        events,
        kind="environment_evidence",
        creator="environment",
        name="transition-3",
        payload={"transition_digest": "abc"},
    )
    initial_support = GRAPH.support(state, schema.object_id)
    state = add_attention(state, events, worker="r2", object_id=schema.object_id, key="inspect")
    assert GRAPH.support(state, schema.object_id) == initial_support == 0

    illegal = GRAPH.edge_event(
        state,
        kind="supports",
        source_id=evidence.object_id,
        target_id=schema.object_id,
        created_by="qwen",
    )
    with pytest.raises(GRAPH.EpistemicGraphError, match="environment evidence authority"):
        GRAPH.apply_event(state, illegal)

    state = add_edge(
        state,
        events,
        kind="supports",
        source=evidence.object_id,
        target=schema.object_id,
    )
    assert GRAPH.evidence_counts(state, schema.object_id) == (1, 0)
    assert GRAPH.support(state, schema.object_id) == 1

    with pytest.raises(GRAPH.EpistemicGraphError, match="assert empirical support"):
        GRAPH.make_object(
            kind="explanation",
            created_by="r2",
            created_revision=state.revision + 1,
            identity={"name": "illegal"},
            payload={"support": 99},
        )


def test_worker_attention_is_separate_and_salience_is_worker_specific() -> None:
    state = GRAPH.GraphState()
    events: list = []
    state, binding = add_object(state, events, kind="binding", creator="r2", name="binding")
    state, explanation = add_object(
        state, events, kind="explanation", creator="qwen", name="explanation"
    )
    before = (GRAPH.salience(state, "r2", binding.object_id), GRAPH.salience(state, "qwen", binding.object_id))
    state = add_attention(
        state,
        events,
        worker="qwen",
        object_id=explanation.object_id,
        key="qwen-focus",
        weight=5,
    )

    assert GRAPH.support(state, explanation.object_id) == 0
    assert len(state.attention) == 1
    assert GRAPH.salience(state, "qwen", explanation.object_id) > GRAPH.salience(
        state, "r2", explanation.object_id
    )
    assert before[0] != before[1]
    assert GRAPH.salience(state, "qwen", explanation.object_id) == GRAPH.salience(
        state, "qwen", explanation.object_id
    )


def test_frontier_is_dependency_closed_and_preserves_all_live_competing_bindings() -> None:
    state = GRAPH.GraphState()
    events: list = []
    state, entity_a = add_object(state, events, kind="entity", creator="environment", name="a")
    state, entity_b = add_object(state, events, kind="entity", creator="environment", name="b")
    state, schema = add_object(state, events, kind="schema", creator="qwen", name="schema")
    dependencies = (entity_a.object_id, entity_b.object_id, schema.object_id)
    state, binding_one = add_object(
        state,
        events,
        kind="binding",
        creator="r2",
        name="candidate-one",
        dependencies=dependencies,
    )
    state, binding_two = add_object(
        state,
        events,
        kind="binding",
        creator="r2",
        name="candidate-two",
        dependencies=dependencies,
    )
    for index in range(5):
        state, _distractor = add_object(
            state,
            events,
            kind="explanation",
            creator="qwen",
            name=f"distractor-{index}",
            payload={"text": "x" * 80},
        )

    frontier = GRAPH.build_frontier(state, worker="r2", token_budget=10_000)
    mandatory_only = GRAPH.build_frontier(
        state, worker="r2", token_budget=10_000, root_limit=0
    )
    one_optional_root = GRAPH.frontier(
        state, worker="r2", profile="default", budget=10_000, root_limit=1
    )

    assert frontier.used_tokens <= frontier.token_budget
    assert set(frontier.mandatory_binding_ids) == {binding_one.object_id, binding_two.object_id}
    assert {binding_one.object_id, binding_two.object_id, *dependencies}.issubset(frontier.object_ids)
    for object_id in frontier.object_ids:
        assert set(GRAPH.dependency_ids(state, object_id)).issubset(frontier.object_ids)
    assert mandatory_only.root_limit == 0
    assert mandatory_only.selected_root_ids == ()
    assert set(mandatory_only.object_ids) == {
        binding_one.object_id,
        binding_two.object_id,
        *dependencies,
    }
    assert mandatory_only.omitted_root_ids
    assert one_optional_root.root_limit == 1
    assert len(one_optional_root.selected_root_ids) == 1
    assert one_optional_root.document["selection"] == {
        "root_limit": 1,
        "mandatory_binding_roots_exempt": True,
        "selected_optional_roots": list(one_optional_root.selected_root_ids),
        "omitted_optional_root_count": len(one_optional_root.omitted_root_ids),
    }
    with pytest.raises(GRAPH.FrontierBudgetError) as failure:
        GRAPH.build_frontier(state, worker="r2", token_budget=1)
    assert failure.value.required > failure.value.budget


def test_pickups_detect_both_directions_once_without_changing_support() -> None:
    state = GRAPH.GraphState()
    events: list = []
    state, qwen_schema = add_object(state, events, kind="schema", creator="qwen", name="qwen-schema")
    state, r2_binding = add_object(
        state,
        events,
        kind="binding",
        creator="r2",
        name="r2-binding",
        dependencies=(qwen_schema.object_id,),
    )
    qwen_to_r2 = GRAPH.pickup_events(state)[0]
    grounded = GRAPH.grounded_pickup_event(
        state,
        pickup_id=qwen_to_r2.pickup_id,
        downstream_object_id=r2_binding.object_id,
        worker="r2",
        payload={"grounding": "bound roles"},
    )
    state = GRAPH.apply_event(state, grounded)
    events.append(grounded)
    state, r2_experiment = add_object(
        state, events, kind="experiment", creator="r2", name="r2-experiment"
    )
    state = add_attention(
        state,
        events,
        worker="qwen",
        object_id=r2_experiment.object_id,
        key="read-r2-experiment",
    )
    state = add_attention(
        state,
        events,
        worker="qwen",
        object_id=r2_experiment.object_id,
        key="read-r2-experiment-again",
    )

    pickups = GRAPH.pickup_events(state)
    assert [item.direction for item in pickups] == ["qwen->r2", "r2->qwen"]
    assert len(pickups) == 2
    assert GRAPH.support(state, qwen_schema.object_id) == 0
    assert GRAPH.support(state, r2_experiment.object_id) == 0
    report = GRAPH.metrics(state)
    assert report["pickup_exposure_count"] == 2
    assert report["pickup_trigger_kinds"] == {"attention": 1, "dependency": 1}
    assert report["grounded_pickup_count"] == 1
    assert report["grounded_pickup_directions"] == {"qwen->r2": 1}


def test_event_replay_and_frontier_are_deterministic_and_hash_checked() -> None:
    state = GRAPH.GraphState()
    events: list = []
    state, entity = add_object(state, events, kind="entity", creator="environment", name="entity")
    state, schema = add_object(state, events, kind="schema", creator="qwen", name="schema")
    state, _binding = add_object(
        state,
        events,
        kind="binding",
        creator="r2",
        name="binding",
        dependencies=(entity.object_id, schema.object_id),
    )
    state = add_attention(state, events, worker="r2", object_id=schema.object_id, key="pickup")

    first_replay = GRAPH.replay(events)
    second_replay = GRAPH.replay(tuple(events))
    first_frontier = GRAPH.build_frontier(first_replay, worker="qwen", token_budget=10_000)
    second_frontier = GRAPH.build_frontier(second_replay, worker="qwen", token_budget=10_000)

    assert first_replay == second_replay == state
    assert first_frontier == second_frontier
    tampered = replace(events[-1], event_hash="0" * 64)
    with pytest.raises(GRAPH.EpistemicGraphError, match="hash mismatch"):
        GRAPH.replay([*events[:-1], tampered])


def test_runner_ingestion_serialization_deltas_and_metrics_round_trip() -> None:
    state = GRAPH.GraphState()
    all_events: list = []
    qwen = GRAPH.ingest_qwen_writes(
        state,
        [
            {
                "kind": "schema",
                "identity": {"relation": "SameOutline", "operator": "Decrease"},
                "payload": {"conditions": ["SameOutline"]},
            }
        ],
        response_id="response-1",
    )
    state = qwen.state
    all_events.extend(qwen.events)
    schema_id = qwen.object_ids[0]
    grounding = GRAPH.ingest_groundings(
        state,
        [
            {
                "binding_key": "schema-1:f00:f01",
                "payload": {"roles": ["f00", "f01"]},
                "dependency_ids": [schema_id],
            }
        ],
        source="r2",
    )
    state = grounding.state
    all_events.extend(grounding.events)
    binding_id = grounding.object_ids[0]
    evidence = GRAPH.ingest_environment_evidence(
        state,
        transition_id="transition-7",
        payload={"before": "a", "after": "b"},
        judgments=[{"kind": "supports", "target_id": binding_id}],
    )
    state = evidence.state
    all_events.extend(evidence.events)
    summary = GRAPH.ingest_r2_runtime_summary(
        state,
        {"schema_count": 12, "binding_count": 3},
        observation_key="observation-7",
        basis_ids=evidence.object_ids,
    )
    state = summary.state
    all_events.extend(summary.events)

    serialized = [GRAPH.event_document(event) for event in all_events]
    rebuilt = GRAPH.replay(GRAPH.event_from_document(value) for value in serialized)
    recent = GRAPH.deltas(rebuilt, cursor=0)
    report = GRAPH.metrics(rebuilt)
    document = GRAPH.state_document(rebuilt)
    view = GRAPH.frontier(rebuilt, worker="qwen", profile="default", budget=10_000)

    assert rebuilt == state
    assert document["state_hash"] == GRAPH.stable_hash(
        {key: value for key, value in document.items() if key != "state_hash"}
    )
    assert recent["through_revision"] == rebuilt.revision
    assert recent["from_revision_exclusive"] == 0
    assert report["object_kinds"] == {
        "binding": 1,
        "environment_evidence": 1,
        "qwen_derivation": 1,
        "runtime_summary": 1,
        "schema": 1,
    }
    assert report["edge_kinds"] == {"supports": 1}
    assert report["pickup_directions"] == {"qwen->r2": 1}
    assert GRAPH.support(rebuilt, binding_id) == 1
    assert binding_id in view.mandatory_binding_ids

    repeated = GRAPH.ingest_environment_evidence(
        rebuilt,
        transition_id="transition-7",
        payload={"before": "a", "after": "b"},
        judgments=[{"kind": "supports", "target_id": binding_id}],
    )
    assert repeated.state == rebuilt
    assert repeated.events == ()


def test_repeated_qwen_semantics_deduplicate_but_keep_distinct_derivations() -> None:
    state = GRAPH.GraphState()
    events: list = []
    state, basis_one = add_object(
        state, events, kind="entity", creator="r2", name="basis-one"
    )
    state, basis_two = add_object(
        state, events, kind="entity", creator="r2", name="basis-two"
    )
    semantic_write = {
        "kind": "schema",
        "identity": {
            "origin": "qwen",
            "conditions": [{"predicate": "SameArea", "arguments": ["?a", "?b"]}],
            "preferred_consequence": {
                "operator": "Decrease",
                "measure": "AreaDifference",
                "arguments": ["?a", "?b"],
            },
        },
        "payload": {
            "conditions": [{"predicate": "SameArea", "arguments": ["?a", "?b"]}],
            "preferred_consequence": {
                "operator": "Decrease",
                "measure": "AreaDifference",
                "arguments": ["?a", "?b"],
            },
            "provenance": "externally-proposed",
            "eligible_step": 8,
        },
        "dependency_ids": [basis_one.object_id],
    }
    first = GRAPH.ingest_qwen_writes(state, (semantic_write,), response_id="response-a")
    second_write = {
        **semantic_write,
        "payload": {**semantic_write["payload"], "eligible_step": 16},
        "dependency_ids": [basis_two.object_id],
    }
    second = GRAPH.ingest_qwen_writes(
        first.state, (second_write,), response_id="response-b"
    )

    assert first.object_ids == second.object_ids
    schema_id = first.object_ids[0]
    explanation_write = {
        "kind": "explanation",
        "identity": {
            "origin": "qwen",
            "schema_ref": schema_id,
            "bindings": {"?a": basis_one.object_id, "?b": basis_two.object_id},
        },
        "payload": {
            "bindings": {"?a": basis_one.object_id, "?b": basis_two.object_id},
            "claim": {
                "operator": "Decrease",
                "measure": "AreaDifference",
                "arguments": ["?a", "?b"],
            },
            "provenance": "externally-proposed",
        },
        "dependency_ids": [schema_id, basis_one.object_id, basis_two.object_id],
    }
    first_explanation = GRAPH.ingest_qwen_writes(
        second.state, (explanation_write,), response_id="response-c"
    )
    second_explanation = GRAPH.ingest_qwen_writes(
        first_explanation.state,
        ({**explanation_write, "dependency_ids": [schema_id]},),
        response_id="response-d",
    )

    assert first_explanation.object_ids == second_explanation.object_ids
    schemas = [item for item in second_explanation.state.objects if item.kind == "schema"]
    explanations = [
        item for item in second_explanation.state.objects if item.kind == "explanation"
    ]
    derivations = [
        item for item in second_explanation.state.objects if item.kind == "qwen_derivation"
    ]
    assert len(schemas) == 1
    assert len(explanations) == 1
    assert len(derivations) == 4
    assert {item.payload["response_id"] for item in derivations} == {
        "response-a",
        "response-b",
        "response-c",
        "response-d",
    }
    assert all(
        schemas[0].object_id in item.dependency_ids
        for item in derivations
        if item.payload["write_kind"] == "schema"
    )
    assert schema_id in explanations[0].dependency_ids
    assert basis_one.object_id in explanations[0].dependency_ids
    assert basis_two.object_id in explanations[0].dependency_ids
    assert any(basis_one.object_id in item.dependency_ids for item in derivations)
    assert any(basis_two.object_id in item.dependency_ids for item in derivations)
    assert GRAPH.support(second_explanation.state, schemas[0].object_id) == 0
    assert GRAPH.support(second_explanation.state, explanations[0].object_id) == 0


def test_structured_criticism_is_visible_dependency_linked_and_not_support() -> None:
    state = GRAPH.GraphState()
    events: list = []
    state, schema = add_object(
        state, events, kind="schema", creator="qwen", name="unsupported-schema"
    )
    criticism = GRAPH.ingest_structured_criticism(
        state,
        worker="r2",
        target_id=schema.object_id,
        status="unsupported-potential",
        criticism_key="grounding-at-step-8",
        payload={"reason": "measure-not-executable", "measure": "AreaDifference"},
    )
    criticism_id = criticism.object_ids[0]
    item = next(value for value in criticism.state.objects if value.object_id == criticism_id)

    assert item.kind == "structured_criticism"
    assert item.created_by == "r2"
    assert schema.object_id in item.dependency_ids
    assert GRAPH.support(criticism.state, schema.object_id) == 0
    assert GRAPH.support(criticism.state, criticism_id) == 0
    assert criticism.state.edges == ()
    qwen_frontier = GRAPH.build_frontier(
        criticism.state, worker="qwen", token_budget=10_000
    )
    assert criticism_id in qwen_frontier.object_ids
    assert schema.object_id in qwen_frontier.object_ids
    assert any(
        pickup.direction == "qwen->r2" and pickup.object_id == schema.object_id
        for pickup in criticism.state.pickups
    )
