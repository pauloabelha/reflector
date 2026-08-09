from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest


HERE = Path(__file__).resolve().parent
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"
V19 = HERE.parent / "parallel-cognitive-workspace-v1-9"
V112 = HERE.parent / "parallel-cognitive-workspace-v1-12"


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DIAGNOSTICS = load("grounding_diagnostics_v114_test", HERE / "grounding_diagnostics.py")
QC = load("qwen_cognition_v114_test", V14 / "qwen_cognition.py")
EVIDENCE = load("evidence_revision_v114_test", V19 / "evidence_revision.py")
EVIDENCE.install(QC)
REVISION = load("revision_response_v114_test", V112 / "revision_response.py")
REVISION.install(QC)
DIAGNOSTICS.install(QC)


def complete_grounding() -> dict[str, Any]:
    return {
        "protocol": EVIDENCE.GROUNDING_PROTOCOL,
        "population_complete": True,
        "truncated": False,
        "entities_truncated": False,
        "relations_truncated": False,
        "entities": [
            {
                "id": "f0",
                "descriptor": {
                    "area": 4,
                    "centroid2": [0, 0],
                    "outline_class": "x",
                    "interior_layout_class": "a",
                },
            },
            {
                "id": "f1",
                "descriptor": {
                    "area": 4,
                    "centroid2": [0, 2],
                    "outline_class": "x",
                    "interior_layout_class": "b",
                },
            },
            {
                "id": "f2",
                "descriptor": {
                    "area": 4,
                    "centroid2": [2, 4],
                    "outline_class": "x",
                    "interior_layout_class": "b",
                },
            },
        ],
        "relations": [
            {"predicate": "MovedTogether", "arguments": ["f0", "f2"]},
            {"predicate": "MovedWhileStationary", "arguments": ["f1", "f2"]},
            {"predicate": "Touches", "arguments": ["f0", "f1"]},
        ],
    }


def executed_judgments() -> dict[str, Any]:
    return {
        "binding_columns": ["effect_pair"],
        "bindings": [
            [["f0", "f1"]],
            [["f0", "f2"]],
            [["f1", "f2"]],
        ],
        "judgment_columns": [
            "binding_index",
            "observed_delta",
            "predicted_delta",
            "modeled",
        ],
        "judgments": [
            [0, [0, -2], [0, -2], True],
            [0, [0, -2], [0, -2], True],
            [1, [0, 0], [0, 0], True],
            [2, [0, 0], None, False],
        ],
    }


def object_document(object_id: str, kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": object_id,
        "kind": kind,
        "created_by": "r2",
        "identity": {},
        "payload": payload,
        "dependencies": [],
        "support": 0,
        "salience": 1,
    }


def turn() -> Any:
    grounding = complete_grounding()
    criticism = object_document(
        "crit",
        "structured_criticism",
        {
            "status": EVIDENCE.STATUS,
            "structured_witness": {"grounding_state": grounding},
        },
    )
    target = object_document(
        "target",
        "schema",
        {
            "conditions": [{"predicate": "SameOutline", "arguments": ["?a", "?b"]}],
            "preferred_consequence": {
                "operator": "Decrease",
                "measure": "TranslationAlignmentResidual",
                "arguments": ["?a", "?b"],
            },
        },
    )
    relation_set = object_document(
        "relations",
        "relation_set",
        {"relations": grounding["relations"]},
    )
    objects = [criticism, target, relation_set]
    return QC.CognitionTurn(
        request_id="request",
        workspace_id="workspace",
        basis_revision=4,
        basis_hash="head",
        mode="ordered-deltas",
        document={
            "revision_task": {
                "chain_ref": "chain",
                "derivation_id": "derivation",
                "semantic_target_id": "target",
                "criticism_id": "crit",
                "criticism_status": EVIDENCE.STATUS,
                "target_alpha_signature": QC.alpha_schema_signature(target["payload"]),
                "candidate_refs": [],
            },
            "sparse_cut": {"objects": objects, "edges": []},
            "object_index": [
                {"id": item["id"], "kind": item["kind"], "dependencies": []}
                for item in objects
            ],
            "ordered_lossless_deltas": [],
            "full_materialization": None,
        },
        validation_context={
            "exact_grounding_state_digest": QC.stable_hash(grounding),
            "schema_alpha_signatures": [],
        },
    )


def row(table: dict[str, Any], predicate: str) -> dict[str, Any]:
    return next(item for item in table["predicate_rows"] if item["predicate"] == predicate)


def test_every_allowed_predicate_has_a_complete_unordered_pair_row() -> None:
    table = DIAGNOSTICS.enumerate_predicate_pairs(QC, complete_grounding())
    assert table["protocol"] == DIAGNOSTICS.PROTOCOL
    assert table["effect_pair_population"] == [
        ["f0", "f1"],
        ["f0", "f2"],
        ["f1", "f2"],
    ]
    assert [item["predicate"] for item in table["predicate_rows"]] == list(QC.PREDICATES)
    assert row(table, "SameOutline")["classification"] == "ambiguous"
    assert row(table, "SameInteriorLayout") == {
        "predicate": "SameInteriorLayout",
        "retained_effect_pairs": [["f1", "f2"]],
        "retained_pair_count": 1,
        "classification": "unique",
    }
    assert row(table, "MovedTogether")["retained_effect_pairs"] == [["f0", "f2"]]
    assert row(table, "MovedWhileStationary")["retained_effect_pairs"] == [["f1", "f2"]]
    assert row(table, "ChangedTogether")["classification"] == "empty"


def test_complete_missing_explicit_fact_is_false_and_validation_reports_empty() -> None:
    current = turn()
    with pytest.raises(QC.CognitionError, match="^grounding-validation-empty$"):
        DIAGNOSTICS.validate_complete_closed_world(
            QC,
            [{"predicate": "ChangedTogether", "arguments": ["?a", "?b"]}],
            current,
        )


def test_validation_reports_ambiguous_and_accepts_a_unique_pair() -> None:
    current = turn()
    with pytest.raises(QC.CognitionError, match="^grounding-validation-ambiguous$"):
        DIAGNOSTICS.validate_complete_closed_world(
            QC,
            [{"predicate": "SameOutline", "arguments": ["?a", "?b"]}],
            current,
        )
    DIAGNOSTICS.validate_complete_closed_world(
        QC,
        [{"predicate": "SameInteriorLayout", "arguments": ["?a", "?b"]}],
        current,
    )


def test_turn_augmentation_surfaces_diagnostics_without_mutating_grounding() -> None:
    current = turn()
    original = json.dumps(current.document, sort_keys=True)
    augmented = DIAGNOSTICS.augment_turn(QC, current)
    assert json.dumps(current.document, sort_keys=True) == original
    table = augmented.document["revision_task"]["grounding_diagnostics"]
    assert row(table, "SameInteriorLayout")["classification"] == "unique"
    assert augmented.validation_context == current.validation_context


def test_control_leverage_uses_temporal_facts_after_empirical_judgments() -> None:
    leverage = DIAGNOSTICS.derive_control_leverage(
        complete_grounding(), executed_judgments()
    )
    by_pair = {tuple(item["effect_pair"]): item for item in leverage["pair_rows"]}
    assert by_pair[("f0", "f1")]["classification"] == "relative_motion_observed"
    assert by_pair[("f0", "f1")]["observed_nonzero_count"] == 2
    assert by_pair[("f0", "f1")]["predicted_nonzero_count"] == 2
    assert by_pair[("f0", "f2")]["classification"] == "invariant"
    assert by_pair[("f0", "f2")]["provenance"] == "executed_probe_judgment"
    assert by_pair[("f0", "f2")]["consistency"] == "consistent"
    assert by_pair[("f1", "f2")]["judgment_classification"] == "no-model"
    assert by_pair[("f1", "f2")]["classification"] == "relative_motion_observed"
    assert by_pair[("f1", "f2")]["provenance"] == "temporal_relation"
    assert by_pair[("f1", "f2")]["consistency"] == "judgment_non_adjudicating"

    absent = DIAGNOSTICS.derive_control_leverage(complete_grounding(), None)
    absent_by_pair = {
        tuple(item["effect_pair"]): item for item in absent["pair_rows"]
    }
    assert absent_by_pair[("f0", "f1")]["classification"] == "unknown"
    assert absent_by_pair[("f0", "f2")]["classification"] == "invariant"
    assert absent_by_pair[("f0", "f2")]["provenance"] == "temporal_relation"
    assert absent_by_pair[("f1", "f2")]["classification"] == "relative_motion_observed"


def test_no_model_survives_when_no_exact_temporal_fact_covers_the_pair() -> None:
    grounding = complete_grounding()
    grounding["relations"] = [
        item
        for item in grounding["relations"]
        if item["predicate"] != "MovedWhileStationary"
    ]
    leverage = DIAGNOSTICS.derive_control_leverage(grounding, executed_judgments())
    pair = next(
        item for item in leverage["pair_rows"] if item["effect_pair"] == ["f1", "f2"]
    )
    assert pair["classification"] == "no-model"
    assert pair["provenance"] == "executed_probe_judgment"


def test_unique_predicates_are_ranked_only_when_their_pair_has_observed_leverage() -> None:
    table = DIAGNOSTICS.enumerate_predicate_pairs(
        QC,
        complete_grounding(),
        executed_probe_judgments=executed_judgments(),
    )
    ranked = table["ranked_unique_predicates_with_leverage"]
    assert [item["rank"] for item in ranked] == list(range(1, len(ranked) + 1))
    assert {item["predicate"] for item in ranked} == {
        "AlignedVertical",
        "MovedWhileStationary",
        "SameInteriorLayout",
        "Touches",
    }
    assert "MovedTogether" not in {item["predicate"] for item in ranked}
    assert next(
        item for item in ranked if item["predicate"] == "SameInteriorLayout"
    )["effect_pair"] == ["f1", "f2"]


def test_empirical_observation_wins_and_temporal_conflict_is_explicit() -> None:
    grounding = complete_grounding()
    grounding["relations"].append(
        {"predicate": "MovedTogether", "arguments": ["f0", "f1"]}
    )
    leverage = DIAGNOSTICS.derive_control_leverage(grounding, executed_judgments())
    pair = next(
        item for item in leverage["pair_rows"] if item["effect_pair"] == ["f0", "f1"]
    )
    assert pair["classification"] == "relative_motion_observed"
    assert pair["provenance"] == "executed_probe_judgment"
    assert pair["temporal_classification"] == "invariant"
    assert pair["consistency"] == "conflict"


def test_turn_augmentation_joins_the_live_columnar_probe_cohort() -> None:
    current = turn()
    document = {
        **current.document,
        "causal_revision_packet": {
            "executed_probe_judgments": executed_judgments()
        },
    }
    current = QC.CognitionTurn(
        request_id=current.request_id,
        workspace_id=current.workspace_id,
        basis_revision=current.basis_revision,
        basis_hash=current.basis_hash,
        mode=current.mode,
        document=document,
        id_aliases=current.id_aliases,
        validation_context=current.validation_context,
    )
    augmented = DIAGNOSTICS.augment_turn(QC, current)
    diagnostics = augmented.document["revision_task"]["grounding_diagnostics"]
    assert diagnostics["ranked_unique_predicates_with_leverage"]
    pair_rows = diagnostics["control_leverage"]["pair_rows"]
    assert next(
        item for item in pair_rows if item["effect_pair"] == ["f0", "f1"]
    )["classification"] == "relative_motion_observed"


def test_actual_revision_request_text_receives_strong_executable_rule() -> None:
    augmented = DIAGNOSTICS.augment_turn(QC, turn())
    payload = QC.request_payload(
        augmented,
        {"model": "opaque", "max_tokens": 256},
    )
    text = payload["messages"][0]["content"]
    assert isinstance(text, str)
    rule = DIAGNOSTICS.REVISION_DIAGNOSTIC_RULE.strip()
    assert text.count(rule) == 1
    assert "MUST retain exactly one effect pair" in text
    assert "copy ONLY its rank=1 predicate into conditions as exactly one atom" in text
    assert "using the same effect variables; do not add any other predicate" in text
    assert "retained-pair intersection is exactly one pair" in text
    assert "Remove inherited conditions that preserve other pairs" in text
    assert "never emit a predicate classified ambiguous" in text
    assert text.index(rule) < text.index("EPISTEMIC_INPUT=")


def test_multimodal_request_injection_is_immutable_and_preserves_image_parts() -> None:
    augmented = DIAGNOSTICS.augment_turn(QC, turn())
    qwen = {"model": "opaque", "max_tokens": 256}
    visuals = [{"label": "current", "data_url": "data:image/png;base64,AA=="}]
    inherited = QC._GROUNDING_DIAGNOSTICS_V114_BASE_REQUEST_PAYLOAD(
        augmented, qwen, visual_evidence=visuals
    )
    inherited_before = json.dumps(inherited, sort_keys=True)
    payload = QC.request_payload(augmented, qwen, visual_evidence=visuals)
    assert json.dumps(inherited, sort_keys=True) == inherited_before
    inherited_parts = inherited["messages"][0]["content"]
    parts = payload["messages"][0]["content"]
    assert isinstance(parts, list) and isinstance(inherited_parts, list)
    assert DIAGNOSTICS.REVISION_DIAGNOSTIC_RULE.strip() not in inherited_parts[0]["text"]
    assert parts[0]["text"].count(DIAGNOSTICS.REVISION_DIAGNOSTIC_RULE.strip()) == 1
    assert parts[1:] == inherited_parts[1:]


def test_request_without_diagnostics_is_delegated_unchanged() -> None:
    current = turn()
    qwen = {"model": "opaque", "max_tokens": 256}
    inherited = QC._GROUNDING_DIAGNOSTICS_V114_BASE_REQUEST_PAYLOAD(current, qwen)
    wrapped = QC.request_payload(current, qwen)
    assert wrapped == inherited


def test_diagnostic_projection_contains_no_operation_or_task_identity() -> None:
    rendered = json.dumps(
        DIAGNOSTICS.enumerate_predicate_pairs(QC, complete_grounding()),
        sort_keys=True,
    ).lower()
    assert "action" not in rendered
    assert "game" not in rendered
    assert "button" not in rendered
    assert "command" not in rendered
    assert "policy" not in rendered


def test_installed_validator_uses_closed_world_and_install_is_idempotent() -> None:
    DIAGNOSTICS.install(QC)
    first_builder = QC.build_turn
    first_validator = QC._validate_unique_revision
    DIAGNOSTICS.install(QC)
    assert QC.build_turn is first_builder
    assert QC._validate_unique_revision is first_validator
    with pytest.raises(QC.CognitionError, match="^grounding-validation-empty$"):
        QC._validate_unique_revision(
            [{"predicate": "ChangedTogether", "arguments": ["?a", "?b"]}],
            turn(),
        )
