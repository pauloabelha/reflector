from __future__ import annotations

import importlib.util
import sys
import threading
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest


HERE = Path(__file__).resolve().parent


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GRAPH = load("shared_attention_cognition_test_graph", HERE / "epistemic_graph.py")
COGNITION = load("shared_attention_cognition_tests", HERE / "qwen_cognition.py")


def add_object(
    state: Any,
    events: list[Any],
    *,
    kind: str,
    creator: str,
    name: str,
    dependencies: tuple[str, ...] = (),
    payload: dict[str, Any] | None = None,
) -> tuple[Any, Any]:
    event = GRAPH.object_event(
        state,
        kind=kind,
        created_by=creator,
        identity={"name": name},
        payload=payload or {"label": name},
        dependency_ids=dependencies,
        event_key=f"{creator}:{kind}:{name}",
    )
    next_state = GRAPH.apply_event(state, event)
    events.append(event)
    created = next(item for item in next_state.objects if item.created_revision == event.seq)
    return next_state, created


def graph_fixture() -> tuple[Any, list[Any], dict[str, Any]]:
    state = GRAPH.GraphState()
    events: list[Any] = []
    state, left = add_object(state, events, kind="entity", creator="environment", name="left")
    state, right = add_object(state, events, kind="entity", creator="environment", name="right")
    state, r2_schema = add_object(
        state,
        events,
        kind="schema",
        creator="r2",
        name="relation",
        dependencies=(left.object_id, right.object_id),
    )
    state, binding = add_object(
        state,
        events,
        kind="binding",
        creator="r2",
        name="binding",
        dependencies=(left.object_id, right.object_id, r2_schema.object_id),
    )
    distractors = []
    for index in range(5):
        state, item = add_object(
            state,
            events,
            kind="explanation",
            creator="r2",
            name=f"distractor-{index}",
            payload={"text": "x" * 180, "index": index},
        )
        distractors.append(item)
    return state, events, {
        "left": left,
        "right": right,
        "schema": r2_schema,
        "binding": binding,
        "distractors": distractors,
    }


def empty_response(turn: Any, **updates: Any) -> dict[str, Any]:
    value = {
        "protocol": COGNITION.RESPONSE_PROTOCOL,
        "request_id": turn.request_id,
        "basis_revision": turn.basis_revision,
        "schema_writes": [],
        "explanation_writes": [],
        "attention_contributions": [],
        "expansion_requests": [],
    }
    value.update(updates)
    return value


def test_initial_full_then_ordered_lossless_deltas_from_durable_cursor() -> None:
    state, events, items = graph_fixture()
    orientation = COGNITION.Orientation("private-ar25-workspace-a")
    initial = COGNITION.build_turn(
        state,
        events,
        orientation,
        request_id="req-0",
        token_budget=1800,
    )

    assert initial.mode == "initial-full"
    assert len(initial.document["full_materialization"]["objects"]) == len(state.objects)
    assert initial.document["ordered_lossless_deltas"] == []
    assert "private-ar25-workspace-a" not in COGNITION.stable_json(initial.document)
    assert initial.document["through_cursor"] == {
        "revision": state.revision,
        "head_hash": state.head_hash,
    }
    cut_ids = {item["id"] for item in initial.document["sparse_cut"]["objects"]}
    assert items["binding"].object_id in cut_ids
    assert set(items["binding"].dependency_ids).issubset(cut_ids)
    assert initial.document["sparse_cut"]["dependency_closed"] is True

    with pytest.raises(COGNITION.CognitionError, match="request ID leaks"):
        COGNITION.build_turn(
            state,
            events,
            orientation,
            request_id="ar25-turn",
            token_budget=1800,
        )

    compilation = COGNITION.compile_response(empty_response(initial), initial)
    advanced = COGNITION.advance_orientation(orientation, initial, compilation)
    state, novel = add_object(
        state,
        events,
        kind="explanation",
        creator="r2",
        name="novel-after-cursor",
    )
    delta = COGNITION.build_turn(
        state,
        events,
        advanced,
        request_id="req-1",
        token_budget=1800,
    )

    assert delta.mode == "ordered-deltas"
    assert delta.document["full_materialization"] is None
    assert [item["seq"] for item in delta.document["ordered_lossless_deltas"]] == [novel.created_revision]
    assert delta.document["ordered_lossless_deltas"][0] == COGNITION.event_document(events[-1])

    with pytest.raises(COGNITION.CognitionError, match="history length"):
        COGNITION.build_turn(
            state,
            events[:-1],
            advanced,
            request_id="gap",
            token_budget=1800,
        )


def test_compact_alias_projection_builds_a_second_turn_schema() -> None:
    state, events, _items = graph_fixture()
    orientation = COGNITION.Orientation("private-workspace")
    initial = COGNITION.build_turn(
        state,
        events,
        orientation,
        request_id="req-compact-0",
        token_budget=1800,
        compact_ids=True,
    )
    compiled = COGNITION.compile_response(empty_response(initial), initial)
    orientation = COGNITION.advance_orientation(orientation, initial, compiled)
    state, _novel = add_object(
        state,
        events,
        kind="explanation",
        creator="r2",
        name="compact-novel",
    )
    second = COGNITION.build_turn(
        state,
        events,
        orientation,
        request_id="req-compact-1",
        token_budget=1800,
        compact_ids=True,
    )

    assert second.mode == "ordered-deltas"
    assert second.document["ordered_lossless_deltas"][0][0] == "O"
    assert second.document["ordered_lossless_deltas"][0][1].startswith("o")
    schema = COGNITION.response_schema(second)
    assert schema["properties"]["request_id"]["const"] == "req-compact-1"

def test_expansion_prioritizes_stable_id_and_orientation_is_reconstructable_not_model_authority() -> None:
    state, events, items = graph_fixture()
    target = items["distractors"][-1].object_id
    base = COGNITION.Orientation("workspace-b")
    initial = COGNITION.build_turn(
        state,
        events,
        base,
        request_id="req-base",
        token_budget=1800,
    )
    compilation = COGNITION.compile_response(
        empty_response(initial, expansion_requests=[target]), initial
    )
    expanded_orientation = COGNITION.advance_orientation(base, initial, compilation)
    persisted = COGNITION.orientation_document(expanded_orientation)
    rebuilt = COGNITION.orientation_from_document(persisted, workspace_id="workspace-b")
    assert "workspace-b" not in COGNITION.stable_json(persisted)
    expanded = COGNITION.build_turn(
        state,
        events,
        rebuilt,
        request_id="req-expanded",
        token_budget=1800,
    )

    expanded_ids = {item["id"] for item in expanded.document["sparse_cut"]["objects"]}
    assert target in expanded_ids
    assert rebuilt == expanded_orientation
    spec = COGNITION.orientation_object_spec(rebuilt)
    assert spec["kind"] == "qwen_orientation"
    assert "support" not in spec["payload"]
    graph_object = GRAPH.make_object(created_revision=state.revision + 1, **spec)
    assert GRAPH.support(state, items["schema"].object_id) == 0
    assert graph_object.created_by == "qwen"

    orientation_event = GRAPH.object_event(
        state,
        event_key="persist-orientation",
        **spec,
    )
    orientation_state = GRAPH.apply_event(state, orientation_event)
    assert COGNITION.latest_orientation(orientation_state, "workspace-b") == rebuilt

    # The turn is rebuilt entirely from graph state/events plus the durable
    # orientation. No model conversation/cache value enters its identity.
    repeated = COGNITION.build_turn(
        state,
        events,
        rebuilt,
        request_id="req-expanded",
        token_budget=1800,
    )
    assert repeated == expanded


def test_strict_writes_compile_to_zero_support_and_reject_authority_or_game_leakage() -> None:
    state, events, items = graph_fixture()
    turn = COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("workspace-c"),
        request_id="req-write",
        token_budget=10_000,
    )
    schema = {
        "local_ref": "s0",
        "conditions": [{"predicate": "SameOutline", "arguments": ["?a", "?b"]}],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "basis_ids": [items["schema"].object_id],
    }
    explanation = {
        "local_ref": "e0",
        "schema_ref": "s0",
        "bindings": [
            {"variable": "?a", "object_id": items["left"].object_id},
            {"variable": "?b", "object_id": items["right"].object_id},
        ],
        "claim": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "basis_ids": [items["binding"].object_id],
    }
    attention = {
        "object_id": items["schema"].object_id,
        "weight": 17,
        "channel": "causal",
        "basis_ids": [items["binding"].object_id],
    }
    result = COGNITION.compile_response(
        empty_response(
            turn,
            schema_writes=[schema],
            explanation_writes=[explanation],
            attention_contributions=[attention],
        ),
        turn,
    )

    assert result["valid_json_contract"] is True
    assert result["rejected"] == []
    assert [item["kind"] for item in result["accepted"]] == ["schema", "explanation", "attention"]
    assert all(item["support"] == 0 and item["evidence"] == [] for item in result["accepted"])
    encoded_schema = COGNITION.stable_json(COGNITION.response_schema(turn))
    assert '"support"' not in encoded_schema

    smuggled = dict(schema, support=2)
    rejected = COGNITION.compile_response(
        empty_response(turn, schema_writes=[smuggled]), turn
    )
    assert rejected["valid_json_contract"] is False
    assert rejected["rejected"][0]["reason"] == "forbidden-action-game-or-authority-token"

    leaked = COGNITION.compile_response(
        empty_response(turn, expansion_requests=["ar25"]), turn
    )
    assert leaked["valid_json_contract"] is False
    assert leaked["rejected"][0]["reason"] == "forbidden-action-game-or-authority-token"
    assert "ar25" not in COGNITION.PROMPT.lower()
    assert "arc-action" not in COGNITION.PROMPT.lower()

    applied = COGNITION.apply_compilation(state, result, response_key="response-0")
    created = [item for item in applied.state.objects if item.created_revision > state.revision]
    assert [item.kind for item in created] == ["schema", "explanation"]
    assert all(item.created_by == "qwen" for item in created)
    assert all(COGNITION.GRAPH.support(applied.state, item.object_id) == 0 for item in created)
    assert len(applied.state.attention) == 1
    assert applied.state.attention[0].worker == "qwen"
    assert set(applied.local_refs) == {"s0", "e0"}
    explanation_object = next(item for item in created if item.kind == "explanation")
    assert applied.local_refs["s0"] in explanation_object.dependency_ids


def test_response_schema_exposes_only_visible_ids_but_can_request_indexed_expansion() -> None:
    state, events, items = graph_fixture()
    initial = COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("workspace-visible"),
        request_id="req-visible",
        token_budget=10_000,
    )
    document = dict(initial.document)
    document["full_materialization"] = None
    document["ordered_lossless_deltas"] = []
    document["sparse_cut"] = {
        **initial.document["sparse_cut"],
        "objects": [
            item
            for item in initial.document["sparse_cut"]["objects"]
            if item["id"] == items["left"].object_id
        ],
    }
    turn = replace(initial, mode="ordered-deltas", document=document)
    schema = COGNITION.response_schema(turn)
    properties = schema["properties"]

    basis_enum = properties["schema_writes"]["items"]["properties"]["basis_ids"]["items"]["enum"]
    binding_enum = (
        properties["explanation_writes"]["items"]["properties"]["bindings"]["items"]
        ["properties"]["object_id"]["enum"]
    )
    schema_ref_enum = properties["explanation_writes"]["items"]["properties"]["schema_ref"]["enum"]
    expansion_enum = properties["expansion_requests"]["items"]["enum"]
    assert basis_enum == [items["left"].object_id]
    assert binding_enum == [items["left"].object_id, "OPEN"]
    assert schema_ref_enum == ["s0", "s1"]
    assert items["schema"].object_id in expansion_enum

    hidden_schema_write = empty_response(
        turn,
        explanation_writes=[
            {
                "local_ref": "e0",
                "schema_ref": items["schema"].object_id,
                "bindings": [{"variable": "?a", "object_id": items["left"].object_id}],
                "claim": {
                    "operator": "Preserve",
                    "measure": "OutlineDisagreement",
                    "arguments": ["?a"],
                },
                "basis_ids": [items["left"].object_id],
            }
        ],
    )
    compiled = COGNITION.compile_response(hidden_schema_write, turn)
    assert compiled["accepted"] == []
    assert compiled["rejected"][0]["reason"] == "unknown-schema-ref"


def test_one_resident_fifo_serializes_requests_across_game_workspaces() -> None:
    observed: list[tuple[str, int]] = []
    active = 0
    maximum_active = 0
    lock = threading.Lock()

    def poster(_endpoint: str, request: Any, _timeout: float) -> dict[str, Any]:
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        observed.append((request["workspace"], request["ordinal"]))
        with lock:
            active -= 1
        return {"parsed": {"ordinal": request["ordinal"]}, "transport_error": None}

    resident = COGNITION.ResidentServerQueue("http://resident.invalid", poster=poster)
    futures = [
        resident.submit("workspace-a", {"workspace": "workspace-a", "ordinal": 0}),
        resident.submit("workspace-b", {"workspace": "workspace-b", "ordinal": 1}),
        resident.submit("workspace-a", {"workspace": "workspace-a", "ordinal": 2}),
    ]
    results = [future.result(timeout=3) for future in futures]
    resident.stop()

    assert observed == [
        ("workspace-a", 0),
        ("workspace-b", 1),
        ("workspace-a", 2),
    ]
    assert [item.sequence for item in results] == [0, 1, 2]
    assert [item.workspace_id for item in results] == ["workspace-a", "workspace-b", "workspace-a"]
    assert maximum_active == 1
