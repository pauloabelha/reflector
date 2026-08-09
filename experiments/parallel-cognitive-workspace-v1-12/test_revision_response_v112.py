from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
V111 = HERE.parent / "parallel-cognitive-workspace-v1-11"
FIXTURE_ROOT = V111 / "artifacts/workspaces/generic_prospective--ar25--shared_live_qwen"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V111_MODULE = load("v112_test_base", V111 / "experiment.py")
QC = V111_MODULE.BASE.QC
ADAPTER = load("v112_revision_response", HERE / "revision_response.py")
PACKET = load("v112_revision_packet_for_response_test", HERE / "causal_packet.py")
ADAPTER.install(QC)


def saved_repair_turn():
    state = V111_MODULE.BASE.graph_state(FIXTURE_ROOT)[0]
    orientation = QC.Orientation(
        workspace_id="response-fixture",
        initialized=True,
        cursor_revision=state.revision,
        cursor_hash=state.head_hash,
    )
    return PACKET.build_revision_turn(
        QC,
        state,
        orientation,
        request_id="response-fixture",
        token_budget=6400,
        compact_ids=True,
    )


def test_saved_v111_repair_turn_gets_exactly_revision_or_abstain() -> None:
    turn = saved_repair_turn()
    schema = QC.response_schema(turn)
    assert set(schema) == {"oneOf"}
    assert len(schema["oneOf"]) == 2
    assert [branch["required"] for branch in schema["oneOf"]] == [
        ["revision"],
        ["abstain"],
    ]
    assert all(branch["additionalProperties"] is False for branch in schema["oneOf"])
    rendered = json.dumps(schema, sort_keys=True)
    for forbidden in (
        "explanation_set",
        "attention_contributions",
        "expansion_requests",
        "candidate_refs",
        "bindings",
    ):
        assert forbidden not in rendered


def test_abstain_is_valid_and_every_hybrid_or_bloated_branch_is_rejected() -> None:
    turn = saved_repair_turn()
    accepted = QC.compile_response({"parsed": {"abstain": True}}, turn)
    assert accepted["valid_json_contract"] is True
    assert accepted["accepted"] == []
    assert accepted["revision_decision"] == "abstain"
    for bad in (
        {"abstain": False},
        {"abstain": True, "revision": {}},
        {"revision": {}, "attention_contributions": []},
        {"explanation_set": None},
    ):
        rejected = QC.compile_response({"parsed": bad}, turn)
        assert rejected["valid_json_contract"] is False
        assert rejected["rejected"][0]["reason"] == "revision-exclusive-branch"


def test_revision_still_crosses_authoritative_causal_and_evidence_compiler() -> None:
    turn = saved_repair_turn()
    task = turn.document["revision_task"]
    object_index, visible = QC._v14_visible(turn)
    relation_ids = sorted(
        object_id
        for object_id in visible
        if object_index[object_id]["kind"] == "relation_set"
    )
    assert relation_ids
    raw = {
        "local_ref": "s0",
        "chain_ref": "c:wrong",
        "revises_schema_id": task["semantic_target_id"],
        "conditions": [
            {"predicate": "SameInteriorLayout", "arguments": ["?a", "?b"]}
        ],
        "preferred_consequence": {
            "operator": "Decrease",
            "measure": "TranslationAlignmentResidual",
            "arguments": ["?a", "?b"],
        },
        "relation_evidence_id": turn.document["causal_revision_packet"]["current_relation_set"]["id"],
        "prospective_evidence_id": turn.document["revision_task"]["causing_evidence_ids"][0],
    }
    wrong_chain = QC.compile_response({"parsed": {"revision": raw}}, turn)
    assert wrong_chain["valid_json_contract"] is True
    assert wrong_chain["schema_revision_accepted"] is False
    assert wrong_chain["rejected"][0]["reason"] == "causal-chain-mismatch"

    raw["chain_ref"] = task["chain_ref"]
    grounding_checked = QC.compile_response({"parsed": {"revision": raw}}, turn)
    assert grounding_checked["schema_revision_accepted"] is True
    accepted_schema = next(
        item for item in grounding_checked["accepted"] if item["kind"] == "schema"
    )
    aliases = dict(turn.id_aliases)
    assert set(accepted_schema["dependency_ids"]) >= {
        aliases[turn.document["causal_revision_packet"]["current_relation_set"]["id"]],
        aliases[turn.document["revision_task"]["causing_evidence_ids"][0]],
    }

    target = QC._visible_object_documents(turn)[task["semantic_target_id"]]["payload"]
    raw["conditions"] = target["conditions"]
    raw["preferred_consequence"] = target["preferred_consequence"]
    alpha_checked = QC.compile_response({"parsed": {"revision": raw}}, turn)
    assert alpha_checked["schema_revision_accepted"] is False
    assert alpha_checked["rejected"][0]["reason"] == "alpha-repeat"


def test_revision_request_uses_small_contract_but_keeps_exact_turn_and_visuals() -> None:
    turn = saved_repair_turn()
    payload = QC.request_payload(
        turn,
        {
            "model": "opaque-model",
            "max_tokens": 2048,
            "revision_max_tokens": 768,
            "thinking_budget_tokens": 1024,
            "revision_thinking_budget_tokens": 640,
        },
        visual_evidence=[{"label": "current", "data_url": "data:image/png;base64,AA=="}],
    )
    assert payload["max_tokens"] == 768
    assert payload["thinking_budget_tokens"] == 640
    content = payload["messages"][0]["content"]
    assert content[0]["text"].startswith(ADAPTER.REVISION_PROMPT)
    assert turn.document["revision_task"]["chain_ref"] in content[0]["text"]
    assert content[2]["image_url"]["url"].startswith("data:image/png")
    assert "attention writes" in content[0]["text"]
    assert "relation_evidence_id and prospective_evidence_id" in content[0]["text"]
    assert "exactly one unordered pair" in content[0]["text"]


def test_revision_schema_makes_both_evidence_address_classes_mandatory() -> None:
    turn = saved_repair_turn()
    revision_branch = QC.response_schema(turn)["oneOf"][0]
    revision = revision_branch["properties"]["revision"]
    assert "evidence_ids" not in revision["properties"]
    assert revision["properties"]["relation_evidence_id"] == {
        "const": turn.document["causal_revision_packet"]["current_relation_set"]["id"]
    }
    assert revision["properties"]["prospective_evidence_id"] == {
        "enum": turn.document["revision_task"]["causing_evidence_ids"]
    }


def test_saved_turn_response_schema_is_materially_smaller() -> None:
    report = ADAPTER.schema_size_report(QC, saved_repair_turn())
    assert report["revision_schema_bytes"] < report["legacy_schema_bytes"] * 0.55
    assert report["byte_reduction_fraction"] > 0.45
