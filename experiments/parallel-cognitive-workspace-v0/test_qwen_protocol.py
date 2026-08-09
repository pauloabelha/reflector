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
        ],
        "basis_events": list(range(13)),
        "history_summary": {"interventions": 6, "next_action": "must-not-leak"},
    }


def snapshot() -> dict:
    return PROTOCOL.serialize_snapshot(materialization(), request_id="request-12", basis_revision=12)


def snapshot_with_objects(*objects: dict) -> dict:
    value = materialization()
    value["cognitive_objects"].extend(objects)
    return PROTOCOL.serialize_snapshot(value, request_id="request-12", basis_revision=12)


def initial_snapshot_without_objects() -> dict:
    value = materialization()
    value["cognitive_objects"] = []
    value["transitions"] = []
    return PROTOCOL.serialize_snapshot(value, request_id="request-12", basis_revision=12)


def assert_no_zero_length_array_schema(value: object) -> None:
    if isinstance(value, dict):
        assert value.get("maxItems") != 0
        for item in value.values():
            assert_no_zero_length_array_schema(item)
    elif isinstance(value, list):
        for item in value:
            assert_no_zero_length_array_schema(item)


def empty_response(**updates: object) -> dict:
    phase = str(updates.pop("write_phase", PROTOCOL.SCHEMA_EXPLANATION_PHASE))
    value = {
        "protocol": PROTOCOL.RESPONSE_PROTOCOL,
        "request_id": "request-12",
        "basis_revision": 12,
        "write_phase": phase,
    }
    value.update({key: [] for key in PROTOCOL.active_write_keys(phase)})
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
    assert properties["write_phase"] == {"const": PROTOCOL.SCHEMA_EXPLANATION_PHASE}
    assert properties["schema_writes"]["maxItems"] == 1
    assert properties["explanation_writes"]["maxItems"] == 1
    assert "counterfactual_writes" not in properties
    assert "discriminating_experiment_writes" not in properties
    assert '"maxItems":0' not in PROTOCOL.stable_json(schema)
    assert "__no_reference_available__" not in PROTOCOL.stable_json(schema)
    assert set(schema["required"]) == {
        "protocol",
        "request_id",
        "basis_revision",
        "write_phase",
        "schema_writes",
        "explanation_writes",
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
    assert serialized["requested_write_phase"] == PROTOCOL.SCHEMA_EXPLANATION_PHASE
    assert "_compiler_forbidden_tokens" not in serialized
    assert "arc-action:2" not in content


def test_true_initial_phase_has_only_active_keys_and_omits_unavailable_supersedes() -> None:
    state = initial_snapshot_without_objects()
    schema = PROTOCOL.response_schema(state)
    properties = schema["properties"]

    assert set(properties) == {
        "protocol",
        "request_id",
        "basis_revision",
        "write_phase",
        "schema_writes",
        "explanation_writes",
    }
    assert_no_zero_length_array_schema(schema)
    assert "__no_reference_available__" not in PROTOCOL.stable_json(schema)
    schema_item = properties["schema_writes"]["items"]
    explanation_item = properties["explanation_writes"]["items"]
    assert "supersedes" not in schema_item["properties"]
    assert "supersedes" not in schema_item["required"]
    assert "supersedes" not in explanation_item["properties"]
    assert "supersedes" not in explanation_item["required"]

    proposed_schema = schema_write()
    proposed_schema.pop("supersedes")
    proposed_explanation = {
        "schema_ref": {"source": "response", "schema_write_index": 0},
        "bindings": [
            {"variable": "?a", "entity": {"id": "e00", "generation": 0}},
            {"variable": "?b", "entity": {"id": "e01", "generation": 1}},
        ],
        "basis_events": [12],
    }
    result = PROTOCOL.compile_response(
        empty_response(
            schema_writes=[proposed_schema],
            explanation_writes=[proposed_explanation],
        ),
        state,
    )
    assert result["valid_json_contract"] is True
    assert len(result["accepted"]) == 1
    assert result["audited_writes"]["explanation_writes"][0]["status"] == "accepted"
    assert result["rejected"] == []

    smuggled = dict(proposed_schema, supersedes=[])
    result = PROTOCOL.compile_response(
        empty_response(schema_writes=[smuggled]), state
    )
    assert result["accepted"] == []
    assert result["rejected"][0]["reason"] == "supersedes-without-persisted-reference"


def test_phase_stays_revision_until_external_schema_is_uniquely_bound() -> None:
    r2_explanation = {
        "ref": "r2-explanation-0",
        "kind": "explanation",
        "status": "live",
        "summary": {"provenance": ["r2"]},
    }
    r2_only = snapshot_with_objects(r2_explanation)
    assert r2_only["recent_transitions"]
    assert PROTOCOL.write_phase(r2_only) == PROTOCOL.SCHEMA_EXPLANATION_PHASE

    for status in ("ambiguous", "unbound"):
        state = snapshot_with_objects(
            {
                "ref": f"schema:{status}",
                "kind": "schema",
                "status": status,
                "summary": {"origin": "externally-proposed", "effect_pair": None},
            },
            r2_explanation,
        )
        assert PROTOCOL.write_phase(state) == PROTOCOL.SCHEMA_EXPLANATION_PHASE
        schema = PROTOCOL.response_schema(state)
        assert set(schema["properties"]) >= {"schema_writes", "explanation_writes"}
        # The failed schema remains visible as a revision/supersession target.
        encoded = PROTOCOL.stable_json(schema)
        assert f"schema:{status}" in encoded
        assert "counterfactual_writes" not in schema["properties"]

    nominally_active_without_pair = snapshot_with_objects(
        {
            "ref": "schema:not-uniquely-grounded",
            "kind": "schema",
            "status": "active-zero-evidence",
            "summary": {"origin": "externally-proposed", "effect_pair": None},
        },
        r2_explanation,
    )
    assert PROTOCOL.write_phase(nominally_active_without_pair) == PROTOCOL.SCHEMA_EXPLANATION_PHASE

    bound = snapshot_with_objects(
        {
            "ref": "schema:bound",
            "kind": "schema",
            "status": "active-zero-evidence",
            "summary": {"origin": "externally-proposed", "effect_pair": ["e00", "e01"]},
        },
        r2_explanation,
    )
    assert PROTOCOL.write_phase(bound) == PROTOCOL.COUNTERFACTUAL_PHASE
    assert set(PROTOCOL.response_schema(bound)["properties"]) == {
        "protocol",
        "request_id",
        "basis_revision",
        "write_phase",
        "counterfactual_writes",
    }

    confirmed = snapshot_with_objects(
        {
            "ref": "schema:confirmed",
            "kind": "schema",
            "status": "locally-confirmed",
            "summary": {"origin": "externally-proposed", "effect_pair": ["e00", "e01"]},
        },
        r2_explanation,
    )
    assert PROTOCOL.write_phase(confirmed) == PROTOCOL.COUNTERFACTUAL_PHASE


def test_compiler_returns_v0_templates_and_audits_situated_writes() -> None:
    state = snapshot()
    schema_only = PROTOCOL.compile_response(
        {"parsed": empty_response(schema_writes=[schema_write()])}, state
    )
    assert schema_only["valid_json_contract"] is True
    assert len(schema_only["accepted"]) == 1
    assert schema_only["audited_writes"]["explanation_writes"] == []

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
    first = PROTOCOL.compile_response(empty_response(schema_writes=[schema_write()]), state)
    persisted = {
        "ref": "schema:persisted",
        "kind": "schema",
        "status": "live",
        "summary": {"canonical_hash": first["accepted"][0]["canonical_hash"]},
    }
    persisted_state = snapshot_with_objects(persisted)
    compilation = PROTOCOL.compile_response(
        empty_response(schema_writes=[schema_write("?c", "?d")]), persisted_state
    )

    assert compilation["accepted"] == []
    assert [item["reason"] for item in compilation["rejected"]] == [
        "duplicate-existing-or-alpha-template"
    ]

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
    smuggled_inactive = empty_response(counterfactual_writes=[])
    rejected = PROTOCOL.compile_response(smuggled_inactive, state)
    assert rejected["valid_json_contract"] is False
    assert rejected["rejected"] == [{"reason": "top-level-contract"}]

    too_many = empty_response(
        schema_writes=[schema_write(), schema_write("?c", "?d")],
        explanation_writes=[{}],
    )
    capped = PROTOCOL.compile_response(too_many, state)
    assert capped["valid_json_contract"] is False
    assert capped["rejected"][0]["reason"] == "phase-write-cap"
    assert capped["rejected"][0]["observed"] == {"schema_writes": 2}

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
    assert rejected["rejected"] == [{"reason": "request-basis-or-phase-contract"}]


def test_counterfactual_and_discriminating_experiment_remain_audited_not_templates() -> None:
    state = snapshot_with_objects(
        {
            "ref": "schema:bound",
            "kind": "schema",
            "status": "active-zero-evidence",
            "summary": {"origin": "externally-proposed", "effect_pair": ["e00", "e01"]},
        },
        {"ref": "explanation:old", "kind": "explanation", "status": "live", "summary": {}}
    )
    schema = PROTOCOL.response_schema(state)
    assert PROTOCOL.write_phase(state) == PROTOCOL.COUNTERFACTUAL_PHASE
    assert "schema_writes" not in schema["properties"]
    assert "explanation_writes" not in schema["properties"]
    assert schema["properties"]["counterfactual_writes"]["maxItems"] == 1
    assert "discriminating_experiment_writes" not in schema["properties"]
    assert '"maxItems":0' not in PROTOCOL.stable_json(schema)
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
        empty_response(
            write_phase=PROTOCOL.COUNTERFACTUAL_PHASE,
            counterfactual_writes=[counterfactual],
        ),
        state,
    )
    assert result["accepted"] == []
    assert result["audited_writes"]["counterfactual_writes"][0]["status"] == "accepted"

    experiment_state = snapshot_with_objects(
        {
            "ref": "schema:bound",
            "kind": "schema",
            "status": "active-zero-evidence",
            "summary": {"origin": "externally-proposed", "effect_pair": ["e00", "e01"]},
        },
        {"ref": "explanation:old", "kind": "explanation", "status": "live", "summary": {}},
        {"ref": "cf:left", "kind": "counterfactual", "status": "live", "summary": {}},
        {"ref": "cf:right", "kind": "counterfactual", "status": "live", "summary": {}},
    )
    experiment_schema = PROTOCOL.response_schema(experiment_state)
    assert PROTOCOL.write_phase(experiment_state) == PROTOCOL.DISCRIMINATION_PHASE
    assert "schema_writes" not in experiment_schema["properties"]
    assert "explanation_writes" not in experiment_schema["properties"]
    assert "counterfactual_writes" not in experiment_schema["properties"]
    assert experiment_schema["properties"]["discriminating_experiment_writes"]["maxItems"] == 1
    assert '"maxItems":0' not in PROTOCOL.stable_json(experiment_schema)
    experiment = {
        "counterfactual_refs": ["cf:left", "cf:right"],
        "basis_events": [12],
        "supersedes": [],
    }
    result = PROTOCOL.compile_response(
        empty_response(
            write_phase=PROTOCOL.DISCRIMINATION_PHASE,
            discriminating_experiment_writes=[experiment],
        ),
        experiment_state,
    )
    assert result["accepted"] == []
    assert result["audited_writes"]["discriminating_experiment_writes"][0]["status"] == "accepted"
