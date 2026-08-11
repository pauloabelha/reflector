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


GRAPH = load("parallel_workspace_v14_test_graph", HERE / "epistemic_graph.py")
COGNITION = load("parallel_workspace_v14_test_cognition", HERE / "qwen_cognition.py")


def test_conservative_request_count_covers_full_schema_images_and_margin(monkeypatch) -> None:
    seen = []
    monkeypatch.setattr(
        COGNITION,
        "model_token_count",
        lambda text, qwen: seen.append(text) or 100,
    )
    request = {
        "max_tokens": 512,
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "complete prompt"},
            {"type": "image_url", "image_url": {"url": "data:image/png;base64,secret"}},
        ]}],
        "response_format": {"json_schema": {"schema": {"const": "required-schema"}}},
    }
    counted = COGNITION.conservative_request_prompt_tokens(
        request,
        {"image_max_tokens": 128, "chat_template_token_margin": 256},
    )
    assert counted == 100 + 128 + 256
    assert "required-schema" in seen[0]
    assert "complete prompt" in seen[0]
    assert "base64,secret" not in seen[0]
    assert "<image>" in seen[0]

    admitted = COGNITION.admit_request_context(
        request,
        {"context_window_tokens": 4096, "reserved_tokens": 1024},
        prompt_token_counter=lambda value: 2048,
    )
    assert admitted.reserved_output_tokens == 2048


def add_object(
    state: Any,
    events: list[Any],
    *,
    kind: str,
    creator: str,
    name: str,
    payload: dict[str, Any],
    dependencies: tuple[str, ...] = (),
    identity: dict[str, Any] | None = None,
) -> tuple[Any, Any]:
    event = GRAPH.object_event(
        state,
        kind=kind,
        created_by=creator,
        identity=identity or {"name": name},
        payload=payload,
        dependency_ids=dependencies,
        event_key=f"{creator}:{kind}:{name}",
    )
    state = GRAPH.apply_event(state, event)
    events.append(event)
    return state, next(item for item in state.objects if item.created_revision == event.seq)


def fixture(*, explicit_derivation: bool = True, truncated: bool = False) -> tuple[Any, list[Any], dict[str, Any]]:
    state = GRAPH.GraphState()
    events: list[Any] = []
    state, frame = add_object(
        state,
        events,
        kind="frame",
        creator="environment",
        name="frame",
        payload={"width": 16, "height": 16, "pixel_digest": "opaque-frame"},
    )

    def entity(name: str, centroid: list[int]) -> Any:
        nonlocal state
        state, item = add_object(
            state,
            events,
            kind="entity",
            creator="r2",
            name=name,
            dependencies=(frame.object_id,),
            payload={
                "area": 9,
                "centroid2": centroid,
                "outline_class": "outline-shared",
                "interior_layout_class": f"interior-{name}",
                "grounding": {
                    "frame_id": frame.object_id,
                    "local_component_ref": name,
                    "mask_digest": f"mask-{name}",
                },
            },
        )
        return item

    anchor = entity("anchor", [2, 2])
    horizontal = entity("horizontal", [8, 2])
    diagonal = entity("diagonal", [8, 8])
    relations = [
        {"predicate": "SameOutline", "arguments": [anchor.object_id, horizontal.object_id]},
        {"predicate": "SameOutline", "arguments": [anchor.object_id, diagonal.object_id]},
        {"predicate": "AlignedHorizontal", "arguments": [anchor.object_id, horizontal.object_id]},
        {"predicate": "Disjoint", "arguments": [anchor.object_id, horizontal.object_id]},
        {"predicate": "Disjoint", "arguments": [anchor.object_id, diagonal.object_id]},
    ]
    state, relation_set = add_object(
        state,
        events,
        kind="relation_set",
        creator="r2",
        name="relations",
        dependencies=(frame.object_id, anchor.object_id, horizontal.object_id, diagonal.object_id),
        payload={"frame_id": frame.object_id, "relations": relations},
    )
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
        name="target",
        payload=target_payload,
    )
    state, derivation = add_object(
        state,
        events,
        kind="qwen_derivation",
        creator="qwen",
        name="derivation",
        dependencies=(target.object_id, relation_set.object_id),
        identity={
            "response_id": "opaque-response",
            "write_index": 0,
            "semantic_object_id": target.object_id,
        },
        payload={"write_kind": "schema", "response_id": "opaque-response", "write_index": 0},
    )
    witness = {
        "protocol": "bounded-grounding-witness-v1",
        "status": "ambiguous-grounding",
        "target_alpha_signature": COGNITION.alpha_schema_signature(target_payload),
        "template_hash": COGNITION.alpha_schema_signature(target_payload),
        "template_conditions": target_payload["conditions"],
        "effect_variables": ["?a", "?b"],
        "grounding_count_observed": 2,
        "effect_pair_count_observed": 2,
        "enumeration_truncated": truncated,
        "candidate_substitutions": [
            {
                "candidate_id": "gw:first",
                "substitution": [["?a", anchor.object_id], ["?b", horizontal.object_id]],
                "effect_pair": [anchor.object_id, horizontal.object_id],
                "distinguishing_relations": [
                    {
                        "predicate": "AlignedHorizontal",
                        "variable_arguments": ["?a", "?b"],
                        "entity_arguments": [anchor.object_id, horizontal.object_id],
                    }
                ],
                "relations_truncated": False,
            },
            {
                "candidate_id": "gw:second",
                "substitution": [["?a", anchor.object_id], ["?b", diagonal.object_id]],
                "effect_pair": [anchor.object_id, diagonal.object_id],
                "distinguishing_relations": [],
                "relations_truncated": False,
            },
        ],
        "candidate_substitutions_truncated": False,
        "effect_pairs": [
            {"effect_pair": [anchor.object_id, horizontal.object_id], "distinguishing_predicates": ["AlignedHorizontal"], "relations_truncated": False},
            {"effect_pair": [anchor.object_id, diagonal.object_id], "distinguishing_predicates": [], "relations_truncated": False},
        ],
        "effect_pairs_truncated": False,
        "refinement_goal": "retain one effect pair",
    }
    criticism_dependencies = [target.object_id, relation_set.object_id]
    criticism_identity = {
        "worker": "r2",
        "target_id": target.object_id,
        "status": "ambiguous-grounding",
        "criticism_key": "grounding-review",
    }
    criticism_payload: dict[str, Any] = {
        "status": "ambiguous-grounding",
        "structured_witness": witness,
    }
    if explicit_derivation:
        criticism_dependencies.append(derivation.object_id)
        criticism_identity["derivation_id"] = derivation.object_id
        criticism_payload["derivation_id"] = derivation.object_id
    state, criticism = add_object(
        state,
        events,
        kind="structured_criticism",
        creator="r2",
        name="criticism",
        dependencies=tuple(criticism_dependencies),
        identity=criticism_identity,
        payload=criticism_payload,
    )
    return state, events, {
        "frame": frame,
        "anchor": anchor,
        "horizontal": horizontal,
        "diagonal": diagonal,
        "relation_set": relation_set,
        "target": target,
        "derivation": derivation,
        "criticism": criticism,
    }


def turn_for(
    state: Any, events: list[Any], *, focus_ids: tuple[str, ...] = ()
) -> Any:
    return COGNITION.build_turn(
        state,
        events,
        COGNITION.Orientation("opaque-workspace", focus_ids=focus_ids),
        request_id="req-revision",
        token_budget=10_000,
        compact_ids=False,
    )


def empty_response(turn: Any) -> dict[str, Any]:
    return {
        "protocol": COGNITION.RESPONSE_PROTOCOL,
        "request_id": turn.request_id,
        "basis_revision": turn.basis_revision,
        "schema_revision": None,
        "explanation_set": None,
        "attention_contributions": [],
        "expansion_requests": [],
    }


def valid_revision(turn: Any, items: dict[str, Any]) -> dict[str, Any]:
    task = turn.document["revision_task"]
    value = empty_response(turn)
    value["schema_revision"] = {
        "local_ref": "s0",
        "chain_ref": task["chain_ref"],
        "revises_schema_id": items["target"].object_id,
        "conditions": [
            {"predicate": "SameOutline", "arguments": ["?a", "?b"]},
            {"predicate": "AlignedHorizontal", "arguments": ["?a", "?b"]},
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "evidence_ids": [items["relation_set"].object_id],
    }
    return value


def test_alpha_canonicalization_rejects_renames_reordering_and_symmetric_reversal() -> None:
    first = {
        "conditions": [
            {"predicate": "AlignedHorizontal", "arguments": ["?a", "?b"]},
            {"predicate": "SameOutline", "arguments": ["?a", "?b"]},
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
    }
    renamed = {
        "conditions": [
            {"predicate": "SameOutline", "arguments": ["?d", "?c"]},
            {"predicate": "AlignedHorizontal", "arguments": ["?c", "?d"]},
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?d", "?c"],
        },
    }
    assert COGNITION.alpha_canonical_schema(first) == COGNITION.alpha_canonical_schema(renamed)
    assert COGNITION.alpha_schema_signature(first) == COGNITION.alpha_schema_signature(renamed)


def test_only_explicit_dependency_link_produces_compact_exact_revision_task() -> None:
    state, events, items = fixture()
    turn = turn_for(state, events)
    task = turn.document["revision_task"]
    assert task["derivation_id"] == items["derivation"].object_id
    assert task["semantic_target_id"] == items["target"].object_id
    assert task["criticism_id"] == items["criticism"].object_id
    assert task["candidate_refs"] == ["gw:first", "gw:second"]
    assert set(task) == {
        "chain_ref",
        "derivation_id",
        "semantic_target_id",
        "criticism_id",
        "criticism_status",
        "target_alpha_signature",
        "candidate_refs",
    }
    request = COGNITION.request_payload(
        turn,
        {"model": "opaque-model", "max_tokens": 512},
    )
    rendered = COGNITION.stable_json(request)
    assert "opaque-workspace" not in rendered
    assert "game_id" not in rendered
    assert "action_id" not in rendered
    assert "validation_context" not in rendered
    assert turn.validation_context["schema_alpha_signatures"]

    unlinked_state, unlinked_events, _ = fixture(explicit_derivation=False)
    assert turn_for(unlinked_state, unlinked_events).document["revision_task"] is None


def test_evidence_citing_semantic_revision_uniquely_grounds_and_carries_lineage() -> None:
    state, events, items = fixture()
    turn = turn_for(state, events)
    compiled = COGNITION.compile_response(valid_revision(turn, items), turn)
    assert compiled["valid_json_contract"] is True
    assert compiled["rejected"] == []
    assert compiled["schema_revision_accepted"] is True
    schema = next(item for item in compiled["accepted"] if item["kind"] == "schema")
    assert schema["support"] == 0
    assert schema["payload"]["revision_of"] == items["target"].object_id
    assert {
        items["derivation"].object_id,
        items["target"].object_id,
        items["criticism"].object_id,
        items["relation_set"].object_id,
    }.issubset(schema["dependency_ids"])
    COGNITION.require_integration_alpha_novelty(state, schema)
    applied = COGNITION.apply_compilation(
        state, compiled, response_key="opaque-v14-response"
    )
    assert applied.local_refs["s0"] in {item.object_id for item in applied.state.objects}
    assert GRAPH.support(applied.state, applied.local_refs["s0"]) == 0


def test_initial_live_schema_bootstraps_with_null_lineage_and_spoof_is_rejected() -> None:
    state, events, items = fixture(explicit_derivation=False)
    turn = turn_for(state, events)
    assert turn.document["revision_task"] is None
    value = empty_response(turn)
    value["schema_revision"] = {
        "local_ref": "s0",
        "chain_ref": None,
        "revises_schema_id": None,
        "conditions": [
            {"predicate": "AlignedHorizontal", "arguments": ["?a", "?b"]}
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "evidence_ids": [items["relation_set"].object_id],
    }
    compiled = COGNITION.compile_response(value, turn)
    assert compiled["rejected"] == []
    assert compiled["schema_write_mode"] == "initial-proposal"
    proposal = next(item for item in compiled["accepted"] if item["kind"] == "schema")
    assert proposal["support"] == 0
    assert proposal["dependency_ids"] == [items["relation_set"].object_id]
    assert "revision_of" not in proposal["payload"]
    assert "causal_chain_ref" not in proposal["payload"]

    spoof = empty_response(turn)
    spoof["schema_revision"] = {
        **value["schema_revision"],
        "chain_ref": "c:invented",
        "revises_schema_id": items["target"].object_id,
    }
    rejected = COGNITION.compile_response(spoof, turn)
    assert rejected["schema_write_mode"] is None
    assert rejected["rejected"][0]["reason"] == "initial-proposal-lineage-must-be-null"


def test_alpha_repeat_and_truncated_grounding_are_rejected_before_control_gate() -> None:
    state, events, items = fixture()
    turn = turn_for(state, events)
    repeated = valid_revision(turn, items)
    repeated["schema_revision"]["conditions"] = [
        {"predicate": "SameOutline", "arguments": ["?c", "?d"]}
    ]
    repeated["schema_revision"]["preferred_consequence"]["arguments"] = ["?d", "?c"]
    result = COGNITION.compile_response(repeated, turn)
    assert result["schema_revision_accepted"] is False
    assert result["rejected"][0]["reason"] == "alpha-repeat"

    truncated_state, truncated_events, truncated_items = fixture(truncated=True)
    truncated_turn = turn_for(truncated_state, truncated_events)
    result = COGNITION.compile_response(
        valid_revision(truncated_turn, truncated_items), truncated_turn
    )
    assert result["schema_revision_accepted"] is False
    assert result["rejected"][0]["reason"] == "grounding-validation-truncated"


def test_revision_requires_visible_post_criticism_prospective_evidence_citation() -> None:
    state, events, items = fixture()
    state, prediction = add_object(
        state,
        events,
        kind="prediction",
        creator="r2",
        name="prospective-prediction",
        dependencies=(items["frame"].object_id,),
        payload={"prediction_id": "opaque-prediction", "modeled": True},
    )
    state, proposal = add_object(
        state,
        events,
        kind="action_proposal",
        creator="r2",
        name="prospective-proposal",
        dependencies=(prediction.object_id,),
        payload={"plan_id": "opaque-plan", "selected_prediction_objects": [prediction.object_id]},
    )
    state, evidence = add_object(
        state,
        events,
        kind="environment_evidence",
        creator="environment",
        name="prospective-evidence",
        dependencies=(prediction.object_id, proposal.object_id),
        payload={
            "prospective": {
                "plan_id": "opaque-plan",
                "judgments": [{"status": "refutes", "prediction_id": "opaque-prediction"}],
            },
            "observation_changed": True,
        },
    )
    turn = turn_for(state, events, focus_ids=(evidence.object_id,))
    assert turn.validation_context[
        "visible_post_criticism_prospective_evidence_ids"
    ] == [evidence.object_id]

    missing = COGNITION.compile_response(valid_revision(turn, items), turn)
    assert missing["schema_revision_accepted"] is False
    assert missing["rejected"][0]["reason"] == "missing-prospective-evidence-citation"

    relation_missing = valid_revision(turn, items)
    relation_missing["schema_revision"]["evidence_ids"] = [evidence.object_id]
    rejected = COGNITION.compile_response(relation_missing, turn)
    assert rejected["rejected"][0]["reason"] == "missing-relation-evidence-citation"

    cited = valid_revision(turn, items)
    cited["schema_revision"]["evidence_ids"].append(evidence.object_id)
    accepted = COGNITION.compile_response(cited, turn)
    assert accepted["rejected"] == []
    schema = next(item for item in accepted["accepted"] if item["kind"] == "schema")
    assert items["relation_set"].object_id in schema["dependency_ids"]
    assert evidence.object_id in schema["dependency_ids"]


def test_nonqualifying_prospective_evidence_does_not_create_requirement() -> None:
    state, events, items = fixture()
    state, prediction = add_object(
        state,
        events,
        kind="prediction",
        creator="r2",
        name="unadjudicated-prediction",
        payload={"prediction_id": "opaque-unadjudicated"},
    )
    state, proposal = add_object(
        state,
        events,
        kind="action_proposal",
        creator="r2",
        name="unadjudicated-proposal",
        dependencies=(prediction.object_id,),
        payload={"plan_id": "opaque-unadjudicated-plan"},
    )
    state, evidence = add_object(
        state,
        events,
        kind="environment_evidence",
        creator="environment",
        name="unadjudicated-evidence",
        dependencies=(prediction.object_id, proposal.object_id),
        payload={"prospective": None},
    )
    turn = turn_for(state, events, focus_ids=(evidence.object_id,))
    assert turn.validation_context[
        "visible_post_criticism_prospective_evidence_ids"
    ] == []
    accepted = COGNITION.compile_response(valid_revision(turn, items), turn)
    assert accepted["rejected"] == []


def test_two_competing_explanations_accept_bounded_open_port_and_reject_bad_domain() -> None:
    state, events, items = fixture()
    turn = turn_for(state, events)
    value = empty_response(turn)
    value["explanation_set"] = {
        "mode": "competing",
        "schema_ref": items["target"].object_id,
        "alternatives": [
            {
                "local_ref": "e0",
                "bindings": [
                    {"variable": "?a", "object_id": items["anchor"].object_id},
                    {
                        "variable": "?b",
                        "object_id": "OPEN",
                        "candidate_refs": ["gw:first", "gw:second"],
                    },
                ],
                "claim": {
                    "operator": "Preserve",
                    "measure": "OutlineDisagreement",
                    "arguments": ["?a", "?b"],
                },
                "evidence_ids": [items["relation_set"].object_id],
            },
            {
                "local_ref": "e1",
                "bindings": [
                    {"variable": "?a", "object_id": items["anchor"].object_id},
                    {"variable": "?b", "object_id": items["horizontal"].object_id},
                ],
                "claim": {
                    "operator": "Decrease",
                    "measure": "TranslationAlignmentResidual",
                    "arguments": ["?a", "?b"],
                },
                "evidence_ids": [items["relation_set"].object_id],
            },
        ],
        "discriminator": {
            "kind": "open_port",
            "variable": "?b",
            "candidate_refs": ["gw:first", "gw:second"],
            "basis_id": items["criticism"].object_id,
        },
    }
    compiled = COGNITION.compile_response(value, turn)
    assert compiled["rejected"] == []
    assert compiled["explanation_alternative_count"] == 2
    explanations = [item for item in compiled["accepted"] if item["kind"] == "explanation"]
    assert len(explanations) == 2
    assert explanations[0]["payload"]["open_ports"] == ["?b"]
    assert explanations[0]["payload"]["open_candidate_refs"]["?b"] == (
        "gw:first",
        "gw:second",
    )
    assert all(item["support"] == 0 for item in explanations)

    invalid = empty_response(turn)
    invalid["explanation_set"] = value["explanation_set"] | {
        "alternatives": [
            value["explanation_set"]["alternatives"][0]
            | {
                "bindings": [
                    {"variable": "?a", "object_id": items["anchor"].object_id},
                    {
                        "variable": "?b",
                        "object_id": "OPEN",
                        "candidate_refs": ["gw:first", "gw:missing"],
                    },
                ]
            },
            value["explanation_set"]["alternatives"][1],
        ]
    }
    rejected = COGNITION.compile_response(invalid, turn)
    assert rejected["explanation_alternative_count"] == 0
    assert rejected["rejected"][0]["reason"] == "open-candidate-ref"


def test_v14_schema_caps_competing_alternatives_at_two() -> None:
    state, events, _items = fixture()
    schema = COGNITION.response_schema(turn_for(state, events))
    branches = schema["properties"]["explanation_set"]["oneOf"]
    competing = next(
        branch
        for branch in branches
        if branch.get("properties", {}).get("mode", {}).get("const") == "competing"
    )
    alternatives = competing["properties"]["alternatives"]
    assert alternatives["minItems"] == alternatives["maxItems"] == 2


def test_runner_helpers_link_criticism_and_close_post_basis_alpha_race() -> None:
    state, _events, items = fixture()
    link = COGNITION.explicit_criticism_link(
        items["derivation"].object_id,
        target_schema=items["target"].payload,
        witness={"target_alpha_signature": "opaque-signature"},
        evidence_ids=(items["relation_set"].object_id,),
    )
    assert link["payload"]["derivation_id"] == items["derivation"].object_id
    assert set(link["basis_ids"]) == {
        items["derivation"].object_id,
        items["relation_set"].object_id,
    }
    assert (
        link["payload"]["structured_witness"]["target_alpha_signature"]
        == COGNITION.alpha_schema_signature(items["target"].payload)
    )

    repeated_write = {
        "kind": "schema",
        "payload": items["target"].payload,
    }
    try:
        COGNITION.require_integration_alpha_novelty(state, repeated_write)
    except COGNITION.CognitionError as error:
        assert str(error).startswith("integration-alpha-repeat:")
    else:
        raise AssertionError("post-basis alpha repeat was admitted")
