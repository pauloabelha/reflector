from __future__ import annotations

import importlib.util
import json
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
AMBIGUITY = load("shared_attention_ambiguity_tests", HERE / "ambiguity.py")


def add_object(
    state: Any,
    events: list[Any],
    *,
    kind: str,
    creator: str,
    name: str,
    dependencies: tuple[str, ...] = (),
    payload: dict[str, Any] | None = None,
    identity: dict[str, Any] | None = None,
) -> tuple[Any, Any]:
    event = GRAPH.object_event(
        state,
        kind=kind,
        created_by=creator,
        identity=identity or {"name": name},
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
    descriptor = {
        "area": 4,
        "centroid2": [4, 4],
        "outline_class": "outline_class_00",
        "interior_layout_class": "interior_class_00",
    }
    state, left = add_object(
        state,
        events,
        kind="entity",
        creator="environment",
        name="left",
        payload={**descriptor, "centroid2": [4, 4]},
    )
    state, right = add_object(
        state,
        events,
        kind="entity",
        creator="environment",
        name="right",
        payload={**descriptor, "centroid2": [8, 4]},
    )
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


def relational_triad_fixture() -> tuple[Any, list[Any], dict[str, Any]]:
    state = GRAPH.GraphState()
    events: list[Any] = []
    state, frame = add_object(
        state,
        events,
        kind="frame",
        creator="environment",
        name="initial-frame",
        payload={"width": 64, "height": 64, "pixel_digest": "frame-digest"},
    )

    def entity_payload(
        local_ref: str,
        *,
        area: int,
        interior: str,
        outline: str,
        centroid2: list[int],
        full_frame: bool = False,
    ) -> dict[str, Any]:
        return {
            "kind": "Figure",
            "area": area,
            "centroid2": centroid2,
            "outline_class": outline,
            "interior_layout_class": interior,
            "grounding": {
                "frame_id": frame.object_id,
                "frame_index": 0,
                "local_component_ref": local_ref,
                "bbox_height": 64 if full_frame else 9,
                "bbox_width": 64 if full_frame else 9,
                "mask_digest": f"mask-{local_ref}",
                "mask_rle_rc": [[row, 0, 63 if full_frame else 8] for row in range(64)],
            },
        }

    state, background = add_object(
        state,
        events,
        kind="entity",
        creator="r2",
        name="f03",
        dependencies=(frame.object_id,),
        payload=entity_payload(
            "f03",
            area=316,
            interior="interior_class_00",
            outline="outline_class_00",
            centroid2=[75, 75],
            full_frame=True,
        ),
    )
    state, odd = add_object(
        state,
        events,
        kind="entity",
        creator="r2",
        name="f00",
        dependencies=(frame.object_id,),
        payload=entity_payload(
            "f00",
            area=45,
            interior="interior_class_01",
            outline="outline_class_01",
            centroid2=[46, 36],
        ),
    )
    state, matching_a = add_object(
        state,
        events,
        kind="entity",
        creator="r2",
        name="f01",
        dependencies=(frame.object_id,),
        payload=entity_payload(
            "f01",
            area=45,
            interior="interior_class_02",
            outline="outline_class_01",
            centroid2=[78, 36],
        ),
    )
    state, matching_b = add_object(
        state,
        events,
        kind="entity",
        creator="r2",
        name="f02",
        dependencies=(frame.object_id,),
        payload=entity_payload(
            "f02",
            area=45,
            interior="interior_class_02",
            outline="outline_class_01",
            centroid2=[108, 96],
        ),
    )
    relations = [
        {"predicate": "SameOutline", "arguments": ["f00", "f01"]},
        {"predicate": "SameOutline", "arguments": ["f00", "f02"]},
        {"predicate": "SameOutline", "arguments": ["f01", "f02"]},
        {"predicate": "SameArea", "arguments": ["f00", "f01"]},
        {"predicate": "SameArea", "arguments": ["f00", "f02"]},
        {"predicate": "SameArea", "arguments": ["f01", "f02"]},
        {"predicate": "SameInteriorLayout", "arguments": ["f01", "f02"]},
        {"predicate": "Disjoint", "arguments": ["f01", "f02"]},
        {"predicate": "DifferentInteriorLayout", "arguments": ["f00", "f01"]},
        {"predicate": "DifferentInteriorLayout", "arguments": ["f00", "f02"]},
    ]
    state, relation_set = add_object(
        state,
        events,
        kind="relation_set",
        creator="r2",
        name="initial-relations",
        dependencies=(
            frame.object_id,
            background.object_id,
            odd.object_id,
            matching_a.object_id,
            matching_b.object_id,
        ),
        payload={"frame_id": frame.object_id, "relations": relations},
    )
    state, summary = add_object(
        state,
        events,
        kind="runtime_summary",
        creator="r2",
        name="summary",
        dependencies=(relation_set.object_id,),
        payload={
            "binding_count": 234,
            "schema_ids": [f"opaque-schema-{index:03d}" for index in range(80)],
            "shadow_statuses": {f"opaque-{index:03d}": "idle" for index in range(40)},
            "workspace_blob": "workspace-digest",
        },
    )
    return state, events, {
        "frame": frame,
        "background": background,
        "odd": odd,
        "matching_a": matching_a,
        "matching_b": matching_b,
        "relation_set": relation_set,
        "summary": summary,
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


def test_exact_context_admission_reserves_2048_and_fails_before_overflow() -> None:
    state, events, _items = graph_fixture()
    turn = COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("private-context-admission"),
        request_id="req-context-admission",
        token_budget=1_800,
    )
    qwen = {
        "model": "test-model",
        "context_window_tokens": 16_384,
        "max_tokens": 2_048,
        "thinking_budget_tokens": 1_024,
    }
    request = COGNITION.request_payload(turn, qwen)
    seen: list[Any] = []

    def exact_counter(value: Any) -> int:
        seen.append(value)
        # Calibrated full multimodal/chat-template occupancy is supplied by the
        # serving boundary; cognition never substitutes a byte heuristic.
        return 13_154

    admitted = COGNITION.admit_request_context(
        request,
        qwen,
        prompt_token_counter=exact_counter,
    )
    assert seen == [request]
    assert request["max_tokens"] == 2_048
    assert admitted == COGNITION.ContextAdmission(
        prompt_tokens=13_154,
        reserved_output_tokens=2_048,
        occupied_tokens=15_202,
        context_window_tokens=16_384,
        headroom_tokens=1_182,
        occupancy_fraction=15_202 / 16_384,
    )

    with pytest.raises(COGNITION.ContextAdmissionError) as captured:
        COGNITION.admit_request_context(
            request,
            qwen,
            prompt_token_counter=lambda _request: 14_400,
        )
    overflow = captured.value.report
    assert overflow.occupied_tokens == 16_448
    assert overflow.headroom_tokens == -64
    assert overflow.occupancy_fraction > 1
    assert "exceeds context window 16384 by 64 tokens" in str(captured.value)

    # Exactly full is admissible, and configuration/request drift is not.
    exact_fit = COGNITION.admit_request_context(
        request,
        qwen,
        prompt_token_counter=lambda _request: 14_336,
    )
    assert exact_fit.headroom_tokens == 0
    with pytest.raises(COGNITION.CognitionError, match="differs"):
        COGNITION.admit_request_context(
            request,
            {**qwen, "max_tokens": 3_000},
            prompt_token_counter=lambda _request: 1,
        )
    with pytest.raises(COGNITION.CognitionError, match="nonnegative integer"):
        COGNITION.admit_request_context(
            request,
            qwen,
            prompt_token_counter=lambda _request: True,
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
    assert second.document["delta_codec"]["fidelity"].startswith("mixed compact")
    assert "small-lossy" in second.document["delta_codec"]["G"]
    assert "small-lossy" in COGNITION.PROMPT
    rolling_index = COGNITION._object_index_documents(second.document["object_index"])
    assert {item["id"] for item in rolling_index} == {
        item["id"] for item in second.document["sparse_cut"]["objects"]
    }
    assert len(rolling_index) < len(state.objects)
    schema = COGNITION.response_schema(second)
    assert schema["properties"]["request_id"]["const"] == "req-compact-1"


def test_relational_projection_keeps_triad_and_relation_facts_without_large_payloads() -> None:
    state, events, items = relational_triad_fixture()
    turn = COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("private-triad"),
        request_id="req-triad",
        token_budget=1400,
        compact_ids=True,
    )
    alias_for = {real: alias for alias, real in turn.id_aliases}
    cut = turn.document["sparse_cut"]
    cut_ids = {item["id"] for item in cut["objects"]}
    assert {
        alias_for[items["odd"].object_id],
        alias_for[items["matching_a"].object_id],
        alias_for[items["matching_b"].object_id],
        alias_for[items["relation_set"].object_id],
    }.issubset(cut_ids)

    by_id = {item["id"]: item for item in cut["objects"]}
    matching = by_id[alias_for[items["matching_a"].object_id]]
    assert matching["payload"]["grounding"]["mask_digest"] == "mask-f01"
    assert matching["payload"]["grounding"]["frame_id"] == alias_for[items["frame"].object_id]
    assert "mask_rle_rc" not in matching["payload"]["grounding"]
    assert matching["projection"]["exact_payload_location"] == "authoritative_graph_ledger"
    relation_payload = by_id[alias_for[items["relation_set"].object_id]]["payload"]
    assert any(
        fact["predicate"] == "SameInteriorLayout"
        and fact["arguments"] == ["f01", "f02"]
        for fact in relation_payload["relations"]
    )

    compact_schema = {
        "local_ref": "s0",
        "conditions": [
            {"predicate": "SameInteriorLayout", "arguments": ["?a", "?b"]},
            {"predicate": "Disjoint", "arguments": ["?a", "?b"]},
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "basis_ids": [alias_for[items["relation_set"].object_id]],
    }
    compact_explanation = {
        "local_ref": "e0",
        "schema_ref": "s0",
        "bindings": [
            {"variable": "?a", "object_id": alias_for[items["matching_a"].object_id]},
            {"variable": "?b", "object_id": alias_for[items["matching_b"].object_id]},
        ],
        "claim": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "basis_ids": [alias_for[items["relation_set"].object_id]],
    }
    compact_compilation = COGNITION.compile_response(
        empty_response(
            turn,
            schema_writes=[compact_schema],
            explanation_writes=[compact_explanation],
        ),
        turn,
    )
    assert compact_compilation["rejected"] == []
    assert [item["kind"] for item in compact_compilation["accepted"]] == [
        "schema",
        "explanation",
    ]

    # Projection never rewrites the canonical graph payload.
    canonical_matching = next(
        value for value in state.objects if value.object_id == items["matching_a"].object_id
    )
    assert "mask_rle_rc" in canonical_matching.payload["grounding"]
    canonical_summary = next(
        value for value in state.objects if value.object_id == items["summary"].object_id
    )
    assert len(canonical_summary.payload["schema_ids"]) == 80


def test_ambiguity_witness_preserves_bounded_substitutions_pairs_and_contrasts() -> None:
    _state, _events, items = relational_triad_fixture()
    relation_state = {
        "relations": items["relation_set"].payload["relations"],
    }
    template = {
        "canonical_hash": "generic-template-digest",
        "conditions": [
            {"predicate": "SameOutline", "arguments": ["?a", "?b"]},
            {"predicate": "SameArea", "arguments": ["?a", "?b"]},
        ],
        "effect_variables": ["?a", "?b"],
    }
    witness = AMBIGUITY.compile_ambiguity_witness(
        template,
        relation_state,
        max_candidates=3,
        max_effect_pairs=3,
        max_relations_per_candidate=4,
    )

    assert witness["protocol"] == AMBIGUITY.PROTOCOL
    assert witness["status"] == "ambiguous-grounding"
    assert witness["grounding_count_observed"] == 6
    assert witness["effect_pair_count_observed"] == 3
    assert len(witness["candidate_substitutions"]) == 3
    assert {tuple(item["effect_pair"]) for item in witness["candidate_substitutions"]} == {
        ("f00", "f01"),
        ("f00", "f02"),
        ("f01", "f02"),
    }
    assert all(item["substitution"] for item in witness["candidate_substitutions"])
    matching = next(
        item
        for item in witness["candidate_substitutions"]
        if item["effect_pair"] == ["f01", "f02"]
    )
    assert {item["predicate"] for item in matching["distinguishing_relations"]} >= {
        "SameInteriorLayout",
        "Disjoint",
    }
    assert all(
        item["predicate"] not in {"SameOutline", "SameArea"}
        for candidate in witness["candidate_substitutions"]
        for item in candidate["distinguishing_relations"]
    )

    bounded = AMBIGUITY.compile_ambiguity_witness(
        template,
        relation_state,
        max_candidates=2,
        max_effect_pairs=2,
        max_relations_per_candidate=1,
    )
    assert len(bounded["candidate_substitutions"]) == 2
    assert len(bounded["effect_pairs"]) == 2
    assert bounded["candidate_substitutions_truncated"] is True
    assert bounded["effect_pairs_truncated"] is True
    assert bounded == AMBIGUITY.compile_ambiguity_witness(
        template,
        relation_state,
        max_candidates=2,
        max_effect_pairs=2,
        max_relations_per_candidate=1,
    )


def test_ambiguous_criticism_cut_keeps_witness_target_and_current_relations() -> None:
    state, events, items = relational_triad_fixture()
    target_payload = {
        "conditions": [
            {"predicate": "SameOutline", "arguments": ["?a", "?b"]},
            {"predicate": "SameArea", "arguments": ["?a", "?b"]},
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
    }
    state, target = add_object(
        state,
        events,
        kind="schema",
        creator="qwen",
        name="ambiguous-template",
        payload=target_payload,
    )
    witness = AMBIGUITY.compile_ambiguity_witness(
        {**target_payload, "canonical_hash": target.object_id},
        {"relations": items["relation_set"].payload["relations"]},
        max_candidates=3,
        max_effect_pairs=3,
    )
    criticism_result = GRAPH.ingest_structured_criticism(
        state,
        worker="r2",
        target_id=target.object_id,
        status="ambiguous-grounding",
        criticism_key="ambiguous-template-grounding",
        payload=witness,
    )
    state = criticism_result.state
    events.extend(criticism_result.events)
    criticism_id = criticism_result.object_ids[0]

    turn = COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("private-ambiguity"),
        request_id="req-ambiguity",
        token_budget=4_000,
        compact_ids=True,
    )
    aliases = {real: alias for alias, real in turn.id_aliases}
    by_id = {item["id"]: item for item in turn.document["sparse_cut"]["objects"]}
    expected = {
        criticism_id,
        target.object_id,
        items["relation_set"].object_id,
        items["odd"].object_id,
        items["matching_a"].object_id,
        items["matching_b"].object_id,
    }
    assert {aliases[item] for item in expected}.issubset(by_id)
    criticism = by_id[aliases[criticism_id]]
    assert criticism["payload"]["status"] == "ambiguous-grounding"
    assert len(criticism["payload"]["candidate_substitutions"]) == 3
    assert criticism["payload"]["effect_pair_count_observed"] == 3
    assert target.object_id in next(
        item for item in state.objects if item.object_id == criticism_id
    ).dependency_ids
    assert "refine the schema conditions to retain exactly one effect pair" in COGNITION.PROMPT
    assert "ar25" not in COGNITION.PROMPT.lower()


def test_balanced_production_budget_fits_complete_ambiguity_unit() -> None:
    state, events, items = relational_triad_fixture()
    target_payload = {
        "conditions": [{"predicate": "SameOutline", "arguments": ["?a", "?b"]}],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
    }
    state, target = add_object(
        state,
        events,
        kind="schema",
        creator="qwen",
        name="production-budget-template",
        payload=target_payload,
    )
    witness = AMBIGUITY.compile_ambiguity_witness(
        {**target_payload, "canonical_hash": target.object_id},
        {"relations": items["relation_set"].payload["relations"]},
    )
    criticism = GRAPH.ingest_structured_criticism(
        state,
        worker="r2",
        target_id=target.object_id,
        status="ambiguous-grounding",
        criticism_key="production-budget-criticism",
        payload=witness,
    )
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    turn = COGNITION.build_turn(
        criticism.state,
        [*events, *criticism.events],
        COGNITION.Orientation("production-budget-workspace"),
        request_id="production-budget-request",
        token_budget=config["profiles"]["balanced"]["frontier_token_budget"],
        compact_ids=True,
    )
    cut = turn.document["sparse_cut"]
    budget = config["profiles"]["balanced"]["frontier_token_budget"]
    assert budget == 4_000
    assert cut["used_tokens"] <= budget
    aliases = {real: alias for alias, real in turn.id_aliases}
    rendered = {item["id"] for item in cut["objects"]}
    assert aliases[target.object_id] in rendered
    assert aliases[criticism.object_ids[0]] in rendered
    assert aliases[items["relation_set"].object_id] in rendered


def test_latest_criticized_qwen_derivation_is_an_exact_mandatory_causal_unit() -> None:
    state, events, items = relational_triad_fixture()
    schema_payload = {
        "conditions": [{"predicate": "SameOutline", "arguments": ["?a", "?b"]}],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
    }
    state, target = add_object(
        state,
        events,
        kind="schema",
        creator="qwen",
        name="causal-target",
        payload=schema_payload,
    )
    state, criticized_derivation = add_object(
        state,
        events,
        kind="qwen_derivation",
        creator="qwen",
        name="criticized-write",
        identity={
            "response_id": "response-before-criticism:s0",
            "semantic_object_id": target.object_id,
            "write_index": 0,
        },
        payload={
            "response_id": "response-before-criticism:s0",
            "write_index": 0,
            "write_kind": "schema",
            "call_local_payload": {"provenance": "externally-proposed"},
        },
        dependencies=(target.object_id, items["matching_a"].object_id),
    )
    witness = AMBIGUITY.compile_ambiguity_witness(
        {**schema_payload, "canonical_hash": target.object_id},
        {"relations": items["relation_set"].payload["relations"]},
    )
    criticism_result = GRAPH.ingest_structured_criticism(
        state,
        worker="r2",
        target_id=target.object_id,
        status="ambiguous-grounding",
        criticism_key="causal-result",
        payload={"structured_witness": witness},
    )
    state = criticism_result.state
    events.extend(criticism_result.events)
    criticism_id = criticism_result.object_ids[0]
    # This later alpha-identical call has not itself produced a criticism and
    # therefore must not be retroactively paired with the older R2 result.
    state, uncriticized_derivation = add_object(
        state,
        events,
        kind="qwen_derivation",
        creator="qwen",
        name="later-uncriticized-write",
        identity={
            "response_id": "response-after-criticism:s0",
            "semantic_object_id": target.object_id,
            "write_index": 0,
        },
        payload={
            "response_id": "response-after-criticism:s0",
            "write_index": 0,
            "write_kind": "schema",
            "call_local_payload": {"provenance": "externally-proposed"},
        },
        dependencies=(target.object_id, items["matching_b"].object_id),
    )

    turn = COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("private-causal-unit"),
        request_id="req-causal-unit",
        token_budget=10_000,
        compact_ids=False,
    )
    cut = turn.document["sparse_cut"]
    assert cut["pinned_causal_units"] == [
        {
            "protocol": "qwen-r2-causal-unit-v1.0",
            "fidelity": "exact-canonical-objects",
            "derivation_id": criticized_derivation.object_id,
            "semantic_target_id": target.object_id,
            "criticism_id": criticism_id,
            "derivation_revision": criticized_derivation.created_revision,
            "criticism_revision": next(
                item.created_revision for item in state.objects if item.object_id == criticism_id
            ),
        }
    ]
    by_id = {item["id"]: item for item in cut["objects"]}
    canonical = {item.object_id: item for item in state.objects}
    for object_id in (criticized_derivation.object_id, target.object_id, criticism_id):
        rendered, source = by_id[object_id], canonical[object_id]
        assert rendered["fidelity"] == "exact-canonical-object"
        assert rendered["created_revision"] == source.created_revision
        assert rendered["identity"] == source.identity
        assert rendered["payload"] == source.payload
        assert rendered["dependencies"] == list(GRAPH.dependency_ids(state, object_id))
    assert cut["dependency_closed"] is True
    assert uncriticized_derivation.object_id != criticized_derivation.object_id

    # Find the exact minimum feasible frontier and prove that one unit below it
    # fails rather than emitting a partial causal chain.
    lower, upper = 1, cut["used_tokens"]
    while lower < upper:
        middle = (lower + upper) // 2
        try:
            COGNITION.sparse_cut(state, token_budget=middle)
        except COGNITION.GRAPH.FrontierBudgetError:
            lower = middle + 1
        else:
            upper = middle
    minimum = lower
    minimum_cut = COGNITION.sparse_cut(state, token_budget=minimum)
    assert minimum_cut["pinned_causal_units"]
    with pytest.raises(COGNITION.GRAPH.FrontierBudgetError):
        COGNITION.sparse_cut(state, token_budget=minimum - 1)
    assert "exact Qwen-derivation -> semantic-target" in COGNITION.PROMPT



def test_large_initial_materialization_is_columnar_and_request_stays_below_eight_k() -> None:
    state, events, items = relational_triad_fixture()
    schemas = []
    for index in range(31):
        state, schema = add_object(
            state,
            events,
            kind="schema",
            creator="r2",
            name=f"bulk-schema-{index}",
            dependencies=(items["relation_set"].object_id,),
            payload={
                "conditions": [
                    {"predicate": "SameOutline", "arguments": ["?a", "?b"]}
                ],
                "preferred_consequence": {
                    "operator": "Decrease",
                    "measure": "TranslationAlignmentResidual",
                    "arguments": ["?a", "?b"],
                },
            },
        )
        schemas.append(schema)
    for index in range(234):
        state, _binding = add_object(
            state,
            events,
            kind="r2_binding",
            creator="r2",
            name=f"bulk-binding-{index}",
            dependencies=(
                schemas[index % len(schemas)].object_id,
                items["odd"].object_id,
                items["matching_a"].object_id,
            ),
            payload={
                "binding_key": f"binding-{index}",
                "assignments": {"?a": "f00", "?b": "f01"},
            },
        )
    # Match the measured live shape: hundreds of initial frontier exposures
    # must aggregate rather than reappear as verbose contribution dictionaries.
    for index in range(265):
        event = GRAPH.attention_event(
            state,
            worker="r2",
            object_id=items["relation_set"].object_id,
            weight=1,
            channel="compare",
            basis_ids=(),
            contribution_key=f"bulk-attention-{index}",
        )
        state = GRAPH.apply_event(state, event)
        events.append(event)

    assert len(state.objects) == 272
    assert len(events) == 537
    turn = COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("private-bulk"),
        request_id="req-bulk",
        token_budget=2400,
        compact_ids=True,
    )
    materialization = turn.document["full_materialization"]
    index = COGNITION._object_index_documents(turn.document["object_index"])
    assert len(index) == 272
    assert len(materialization["object_columns"]["dependency_ordinals"]) == 272
    assert len(materialization["object_columns"]["identity_payload_digest8_pairs"]) == 272
    assert materialization["attention_fidelity"].startswith("small-lossy aggregation")
    assert len(materialization["attention_rows"]) == 1
    assert materialization["attention_rows"][0][3:6] == [265, 265, 1]

    aliases = {real: alias for alias, real in turn.id_aliases}
    cut_ids = {item["id"] for item in turn.document["sparse_cut"]["objects"]}
    assert {
        aliases[items["odd"].object_id],
        aliases[items["matching_a"].object_id],
        aliases[items["matching_b"].object_id],
        aliases[items["relation_set"].object_id],
    }.issubset(cut_ids)
    request = COGNITION.request_payload(turn, {"model": "test-model"})
    assert GRAPH.estimate_tokens(request) < 8_000


def test_control_schema_is_executable_and_situated_conditions_are_fact_checked() -> None:
    state, events, items = relational_triad_fixture()
    turn = COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("private-grounding"),
        request_id="req-grounding",
        token_budget=10_000,
    )
    response_contract = COGNITION.response_schema(turn)["properties"]
    control = response_contract["schema_writes"]["items"]["properties"]["preferred_consequence"]
    semantic = response_contract["explanation_writes"]["items"]["properties"]["claim"]
    assert control["properties"]["operator"]["enum"] == ["Decrease", "Increase"]
    assert control["properties"]["measure"]["enum"] == ["TranslationAlignmentResidual"]
    assert "AreaDifference" in semantic["properties"]["measure"]["enum"]
    assert "Preserve" in semantic["properties"]["operator"]["enum"]

    executable_schema = {
        "local_ref": "s0",
        "conditions": [
            {"predicate": "SameOutline", "arguments": ["?a", "?b"]},
            {"predicate": "SameInteriorLayout", "arguments": ["?a", "?b"]},
            {"predicate": "Disjoint", "arguments": ["?a", "?b"]},
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "basis_ids": [items["relation_set"].object_id],
    }
    correct_explanation = {
        "local_ref": "e0",
        "schema_ref": "s0",
        "bindings": [
            {"variable": "?a", "object_id": items["matching_a"].object_id},
            {"variable": "?b", "object_id": items["matching_b"].object_id},
        ],
        "claim": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "basis_ids": [items["relation_set"].object_id],
    }
    accepted = COGNITION.compile_response(
        empty_response(
            turn,
            schema_writes=[executable_schema],
            explanation_writes=[correct_explanation],
        ),
        turn,
    )
    assert accepted["rejected"] == []
    assert [item["kind"] for item in accepted["accepted"]] == ["schema", "explanation"]

    non_executable = {
        **executable_schema,
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "AreaDifference",
            "arguments": ["?a", "?b"],
        },
    }
    rejected_control = COGNITION.compile_response(
        empty_response(turn, schema_writes=[non_executable]), turn
    )
    assert rejected_control["accepted"] == []
    assert rejected_control["rejected"][0]["reason"] == "unsupported-consequence"

    same_area_schema = {
        **executable_schema,
        "conditions": [{"predicate": "SameArea", "arguments": ["?a", "?b"]}],
    }
    false_grounding = {
        **correct_explanation,
        "bindings": [
            {"variable": "?a", "object_id": items["background"].object_id},
            {"variable": "?b", "object_id": items["odd"].object_id},
        ],
    }
    rejected_false = COGNITION.compile_response(
        empty_response(
            turn,
            schema_writes=[same_area_schema],
            explanation_writes=[false_grounding],
        ),
        turn,
    )
    assert [item["kind"] for item in rejected_false["accepted"]] == ["schema"]
    assert rejected_false["rejected"][0]["reason"] == "condition-false"

    missing_binding = {
        **correct_explanation,
        "bindings": [{"variable": "?a", "object_id": items["matching_a"].object_id}],
        "claim": {
            "operator": "Preserve",
            "measure": "InteriorLayoutDisagreement",
            "arguments": ["?a"],
        },
    }
    rejected_missing = COGNITION.compile_response(
        empty_response(
            turn,
            schema_writes=[executable_schema],
            explanation_writes=[missing_binding],
        ),
        turn,
    )
    assert rejected_missing["rejected"][0]["reason"] == "missing-condition-binding"

    open_explanation = {
        **correct_explanation,
        "bindings": [
            {"variable": "?a", "object_id": items["matching_a"].object_id},
            {"variable": "?b", "object_id": "OPEN"},
        ],
        "claim": {
            "operator": "Preserve",
            "measure": "InteriorLayoutDisagreement",
            "arguments": ["?a", "?b"],
        },
    }
    accepted_open = COGNITION.compile_response(
        empty_response(
            turn,
            schema_writes=[executable_schema],
            explanation_writes=[open_explanation],
        ),
        turn,
    )
    assert accepted_open["rejected"] == []


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
