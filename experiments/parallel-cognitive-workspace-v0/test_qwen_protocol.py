from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("parallel_qwen_protocol", HERE / "qwen_protocol.py")
assert SPEC is not None and SPEC.loader is not None
PROTOCOL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PROTOCOL
SPEC.loader.exec_module(PROTOCOL)


def materialization() -> dict:
    entities = [
        {
            "id": f"e{index:02d}",
            "generation": index % 2,
            "kind": "Figure",
            "salience": 10 - index,
            "area": index + 1,
            "centroid2": [index * 2, 0],
            "palette": "must-not-leak",
        }
        for index in range(10)
    ]
    relations = []
    for left in range(8):
        for right in range(left + 1, 8):
            relations.extend(
                [
                    {"predicate": "SameOutline", "arguments": [f"e{left:02d}", f"e{right:02d}"]},
                    {"predicate": "Disjoint", "arguments": [f"e{left:02d}", f"e{right:02d}"]},
                ]
            )
    relations.append({"predicate": "Unsupported", "arguments": ["e00", "e01"]})
    transitions = [
        {
            "event_seq": index,
            "before_revision": index,
            "after_revision": index + 1,
            "action_id": "z-model",
            "relation_changes": [{"predicate": "MovedTogether", "arguments": ["e00", "e01"]}],
        }
        for index in range(1, 7)
    ]
    return {
        "observation_version": 12,
        "observation_digest": "observation-12",
        "legal_action_count": 7,
        "entities": entities,
        "relations": relations,
        "transitions": transitions,
        "intervention_models": [
            {"model_id": "z-model", "support": 3, "effect": {"relative_delta2": [2, 0]}},
            {"action_id": "arc-action:2", "support": 1, "effect": {"relative_delta2": [0, -2]}},
        ],
        "cognitive_objects": [
            {"ref": "schema:old", "kind": "schema", "status": "live", "summary": {"atoms": 2}},
            {"ref": "explanation:old", "kind": "explanation", "status": "live", "summary": {}},
            {"ref": "cf:left", "kind": "counterfactual", "status": "live", "summary": {}},
            {"ref": "cf:right", "kind": "counterfactual", "status": "live", "summary": {}},
        ],
        "basis_events": list(range(13)),
        "history_summary": {"interventions": 6, "next_action": "must-not-leak"},
    }


def snapshot() -> dict:
    return PROTOCOL.serialize_snapshot(materialization(), request_id="request-12", basis_revision=12)


def empty_response(**updates: object) -> dict:
    value = {
        "protocol": PROTOCOL.RESPONSE_PROTOCOL,
        "request_id": "request-12",
        "basis_revision": 12,
        "schema_writes": [],
        "explanation_writes": [],
        "counterfactual_writes": [],
        "discriminating_experiment_writes": [],
    }
    value.update(updates)
    return value


def schema_write(left: str = "?a", right: str = "?b") -> dict:
    return {
        "conditions": [
            {"predicate": "SameOutline", "arguments": [left, right]},
            {"predicate": "SameInteriorLayout", "arguments": [left, right]},
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": PROTOCOL.MEASURE,
            "arguments": [left, right],
        },
        "basis_events": [8, 12],
        "supersedes": [],
    }


def test_snapshot_is_compact_deterministic_and_anonymizes_models() -> None:
    first = snapshot()
    second = snapshot()

    assert first == second
    assert len(first["entities"]) == 8
    assert len(first["relations"]) == 48
    assert [item["event_seq"] for item in first["recent_transitions"]] == [3, 4, 5, 6]
    assert first["recent_transitions"][-1]["relation_changes"][0]["predicate"] == "MovedTogether"
    assert [item["id"] for item in first["intervention_models"]] == ["im00", "im01"]
    encoded = PROTOCOL.stable_json(first)
    assert "z-model" in encoded  # compiler-only denylist retains originals locally
    assert "arc-action:2" in encoded
    public = PROTOCOL._public_snapshot(first)
    public_encoded = PROTOCOL.stable_json(public)
    assert "z-model" not in public_encoded
    assert "arc-action:2" not in public_encoded
    assert "must-not-leak" not in public_encoded
    assert public["opaque_legal_action_count"] == 7
    assert public["history_summary"] == {"interventions": 6}


def test_dynamic_schema_and_payload_pin_request_and_basis(tmp_path: Path) -> None:
    state = snapshot()
    schema = PROTOCOL.response_schema(state)
    properties = schema["properties"]
    assert schema["additionalProperties"] is False
    assert properties["protocol"] == {"const": PROTOCOL.RESPONSE_PROTOCOL}
    assert properties["request_id"] == {"const": "request-12"}
    assert properties["basis_revision"] == {"const": 12}
    assert set(schema["required"]) == {
        "protocol",
        "request_id",
        "basis_revision",
        *PROTOCOL.WRITE_KEYS,
    }
    prompt = tmp_path / "PROMPT.txt"
    prompt.write_text("GENERIC\nINPUT_SNAPSHOT:\n", encoding="utf-8")
    config = {
        "qwen": {
            "model": "qwen-test",
            "temperature": 0,
            "top_p": 1,
            "seed": 7,
            "max_tokens": 360,
            "reasoning_budget_tokens": 64,
        }
    }
    payload = PROTOCOL.build_request_payload(state, config, prompt_path=prompt)

    assert payload["model"] == "qwen-test"
    assert payload["reasoning_budget_tokens"] == 64
    assert payload["response_format"]["json_schema"]["strict"] is True
    content = payload["messages"][0]["content"]
    serialized = json.loads(content.split("INPUT_SNAPSHOT:\n", 1)[1])
    assert serialized["request_id"] == "request-12"
    assert "_compiler_forbidden_tokens" not in serialized
    assert "arc-action:2" not in content


def test_compiler_returns_v0_templates_and_audits_situated_writes() -> None:
    state = snapshot()
    explanation = {
        "schema_ref": {"source": "response", "schema_write_index": 0},
        "bindings": [
            {"variable": "?a", "entity": {"id": "e00", "generation": 0}},
            {"variable": "?b", "entity": {"id": "e01", "generation": 1}},
        ],
        "basis_events": [12],
        "supersedes": ["schema:old"],
    }
    response = empty_response(schema_writes=[schema_write()], explanation_writes=[explanation])
    compilation = PROTOCOL.compile_response({"parsed": response}, state)

    assert compilation["valid_json_contract"] is True
    assert len(compilation["accepted"]) == 1
    assert compilation["accepted"][0]["provenance"] == "externally-proposed"
    assert compilation["accepted_schema_writes"][0]["index"] == 0
    assert compilation["audited_writes"]["explanation_writes"][0]["status"] == "accepted"
    assert compilation["rejected"] == []
    templates = PROTOCOL.templates_from_compilation(compilation)
    assert len(templates) == 1
    assert isinstance(templates[0], PROTOCOL.V0.Template)
    assert templates[0].canonical_hash == compilation["accepted"][0]["canonical_hash"]


def test_compiler_alpha_deduplicates_and_rejects_disconnected_or_unbound_effects() -> None:
    state = snapshot()
    alpha_duplicate = schema_write("?c", "?d")
    response = empty_response(schema_writes=[schema_write(), alpha_duplicate])
    compilation = PROTOCOL.compile_response(response, state)

    assert len(compilation["accepted"]) == 1
    assert [item["reason"] for item in compilation["rejected"]] == ["duplicate-alpha-template"]

    disconnected = schema_write()
    disconnected["conditions"].append(
        {"predicate": "Disjoint", "arguments": ["?c", "?d"]}
    )
    rejected = PROTOCOL.compile_response(empty_response(schema_writes=[disconnected]), state)
    assert rejected["accepted"] == []
    assert rejected["rejected"][0]["reason"] == "disconnected-condition-graph"

    unbound = schema_write()
    unbound["preferred_consequence"]["arguments"] = ["?a", "?c"]
    rejected = PROTOCOL.compile_response(empty_response(schema_writes=[unbound]), state)
    assert rejected["rejected"][0]["reason"] == "ungrounded-effect-variable"


def test_compiler_enforces_total_write_cap_basis_and_action_model_denylist() -> None:
    state = snapshot()
    too_many = empty_response(
        schema_writes=[schema_write(), schema_write("?c", "?d")],
        explanation_writes=[{}],
    )
    capped = PROTOCOL.compile_response(too_many, state)
    assert capped["valid_json_contract"] is False
    assert capped["rejected"] == [{"reason": "total-write-cap", "observed": 3}]

    future = schema_write()
    future["basis_events"] = [13]
    rejected = PROTOCOL.compile_response(empty_response(schema_writes=[future]), state)
    assert rejected["rejected"][0]["reason"] == "unknown-or-future-basis-event"

    token = schema_write()
    token["supersedes"] = ["im00"]
    rejected = PROTOCOL.compile_response(empty_response(schema_writes=[token]), state)
    assert rejected["rejected"][0]["reason"] == "forbidden-action-or-model-token"

    wrong_basis = empty_response(basis_revision=11)
    rejected = PROTOCOL.compile_response(wrong_basis, state)
    assert rejected["valid_json_contract"] is False
    assert rejected["rejected"] == [{"reason": "request-or-basis-contract"}]


def test_counterfactual_and_discriminating_experiment_remain_audited_not_templates() -> None:
    state = snapshot()
    counterfactual = {
        "explanation_ref": {"source": "workspace", "object_ref": "explanation:old"},
        "intervention_effect": {
            "kind": "HypotheticalDisplacement",
            "entity": {"id": "e00", "generation": 0},
            "delta_centroid2": [2, 0],
        },
        "prediction": {
            "operator": "Decrease",
            "measure": PROTOCOL.MEASURE,
            "arguments": [
                {"id": "e00", "generation": 0},
                {"id": "e01", "generation": 1},
            ],
        },
        "horizon": 1,
        "basis_events": [12],
        "supersedes": [],
    }
    result = PROTOCOL.compile_response(
        empty_response(counterfactual_writes=[counterfactual]), state
    )
    assert result["accepted"] == []
    assert result["audited_writes"]["counterfactual_writes"][0]["status"] == "accepted"

    experiment = {
        "counterfactual_refs": ["cf:left", "cf:right"],
        "basis_events": [12],
        "supersedes": [],
    }
    result = PROTOCOL.compile_response(
        empty_response(discriminating_experiment_writes=[experiment]), state
    )
    assert result["accepted"] == []
    assert result["audited_writes"]["discriminating_experiment_writes"][0]["status"] == "accepted"
