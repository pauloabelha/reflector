from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


HERE = Path(__file__).resolve().parent
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ADAPTER = load("evidence_revision_v19_test", HERE / "evidence_revision.py")
QC = load("qwen_cognition_v19_test", V14 / "qwen_cognition.py")


def grounding_state(*, complete: bool = True) -> dict[str, Any]:
    return {
        "protocol": ADAPTER.GROUNDING_PROTOCOL,
        "population_complete": complete,
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
            {"predicate": "AlignedHorizontal", "arguments": ["f0", "f1"]},
            {"predicate": "AlignedVertical", "arguments": ["f0", "f2"]},
        ],
    }


def object_document(
    object_id: str, kind: str, payload: dict[str, Any], dependencies: list[str] | None = None
) -> dict[str, Any]:
    return {
        "id": object_id,
        "kind": kind,
        "created_by": "r2",
        "identity": {},
        "payload": payload,
        "dependencies": dependencies or [],
        "support": 0,
        "salience": 1,
    }


def validator_turn(*, complete: bool = True) -> Any:
    state = grounding_state(complete=complete)
    criticism = object_document(
        "crit",
        "structured_criticism",
        {
            "status": ADAPTER.STATUS,
            "structured_witness": {"grounding_state": state},
        },
        ["der", "target", "env"],
    )
    target = object_document(
        "target",
        "schema",
        {
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
    relation = object_document(
        "rel",
        "relation_set",
        {"relations": state["relations"]},
    )
    evidence = object_document(
        "env",
        "environment_evidence",
        {"prospective": {"judgments": [{"status": "supports"}]}},
        ["pred", "proposal"],
    )
    objects = [criticism, target, relation, evidence]
    return QC.CognitionTurn(
        request_id="request",
        workspace_id="workspace",
        basis_revision=9,
        basis_hash="head",
        mode="ordered-deltas",
        document={
            "revision_task": {
                "chain_ref": "chain",
                "derivation_id": "der",
                "semantic_target_id": "target",
                "criticism_id": "crit",
                "criticism_status": ADAPTER.STATUS,
                "target_alpha_signature": QC.alpha_schema_signature(target["payload"]),
                "candidate_refs": [],
                "causing_evidence_ids": ["env"],
                "grounding_state_digest": QC.stable_hash(state),
            },
            "sparse_cut": {"objects": objects, "edges": []},
            "object_index": [
                {"id": item["id"], "kind": item["kind"], "dependencies": item["dependencies"]}
                for item in objects
            ],
            "ordered_lossless_deltas": [],
            "full_materialization": None,
        },
        validation_context={
            "schema_alpha_signatures": [["target", QC.alpha_schema_signature(target["payload"])]],
            "visible_post_criticism_prospective_evidence_ids": ["env"],
            "exact_grounding_state_digest": QC.stable_hash(state),
        },
    )


def refined_conditions() -> list[dict[str, Any]]:
    return [
        {"predicate": "SameOutline", "arguments": ["?a", "?b"]},
        {"predicate": "AlignedHorizontal", "arguments": ["?a", "?b"]},
    ]


def test_complete_grounding_accepts_one_pair_and_rejects_ambiguous_or_incomplete() -> None:
    ADAPTER.validate_complete_grounding(QC, refined_conditions(), validator_turn())
    with pytest.raises(QC.CognitionError, match="grounding-not-unique"):
        ADAPTER.validate_complete_grounding(
            QC,
            [{"predicate": "SameOutline", "arguments": ["?a", "?b"]}],
            validator_turn(),
        )
    with pytest.raises(QC.CognitionError, match="grounding-state-incomplete"):
        ADAPTER.validate_complete_grounding(QC, refined_conditions(), validator_turn(complete=False))


def test_grounding_state_rejects_operation_fields() -> None:
    turn = validator_turn()
    criticism = turn.document["sparse_cut"]["objects"][0]
    criticism["payload"]["structured_witness"]["grounding_state"]["action_id"] = 7
    turn.validation_context["exact_grounding_state_digest"] = QC.stable_hash(
        criticism["payload"]["structured_witness"]["grounding_state"]
    )
    with pytest.raises(QC.CognitionError, match="grounding-state-not-action-free"):
        ADAPTER.validate_complete_grounding(QC, refined_conditions(), turn)


@dataclass(frozen=True)
class FakeTurn:
    request_id: str
    workspace_id: str
    basis_revision: int
    basis_hash: str | None
    mode: str
    document: dict[str, Any]
    id_aliases: tuple[tuple[str, str], ...] = ()
    validation_context: dict[str, Any] = field(default_factory=dict)


class FakeError(ValueError):
    pass


def fake_qc() -> Any:
    def stable_hash(value: Any) -> str:
        return hashlib.sha256(
            json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()

    def replace(value: Any, aliases: dict[str, str]) -> Any:
        if isinstance(value, dict):
            return {key: replace(item, aliases) for key, item in value.items()}
        if isinstance(value, list):
            return [replace(item, aliases) for item in value]
        return aliases.get(value, value) if isinstance(value, str) else value

    return SimpleNamespace(
        CognitionError=FakeError,
        CognitionTurn=FakeTurn,
        PROMPT="base prompt\n",
        PREDICATES=QC.PREDICATES,
        VARIABLES=QC.VARIABLES,
        stable_hash=stable_hash,
        _replace_ids=replace,
        _criticism_witness=lambda payload: payload["structured_witness"],
        exact_causal_chains=lambda state: tuple(state.units),
        _validate_unique_revision=lambda conditions, turn: None,
    )


def test_builder_promotes_explicit_evidence_return_and_makes_prior_cause_citable() -> None:
    qc = fake_qc()
    state_value = grounding_state()
    target = SimpleNamespace(
        object_id="target",
        kind="schema",
        created_by="qwen",
        created_revision=1,
        payload={},
        dependency_ids=(),
    )
    derivation = SimpleNamespace(
        object_id="der",
        kind="qwen_derivation",
        created_by="qwen",
        created_revision=2,
        payload={},
        dependency_ids=("target",),
    )
    evidence = SimpleNamespace(
        object_id="env",
        kind="environment_evidence",
        created_by="environment",
        created_revision=3,
        payload={"prospective": {"judgments": []}},
        dependency_ids=("pred", "proposal"),
    )
    criticism = SimpleNamespace(
        object_id="crit",
        kind="structured_criticism",
        created_by="r2",
        created_revision=4,
        payload={
            "status": ADAPTER.STATUS,
            "structured_witness": {"grounding_state": state_value},
        },
        dependency_ids=("target", "der", "env"),
    )
    state = SimpleNamespace(
        objects=(target, derivation, evidence, criticism),
        units=(
            {
                "chain_ref": "chain",
                "derivation_id": "der",
                "semantic_target_id": "target",
                "criticism_id": "crit",
                "criticism_status": ADAPTER.STATUS,
                "target_alpha_signature": "alpha",
                "candidate_refs": [],
            },
        ),
    )

    def base(*args: Any, **kwargs: Any) -> FakeTurn:
        return FakeTurn(
            "request",
            "workspace",
            4,
            "head",
            "ordered-deltas",
            {"sparse_cut": {"objects": [{"id": "E"}]}, "revision_task": None},
            (("E", "env"), ("C", "crit"), ("D", "der"), ("T", "target")),
            {},
        )

    turn = ADAPTER.wrap_build_turn(qc, base)(
        state,
        (),
        object(),
        request_id="request",
        token_budget=100,
        compact_ids=True,
    )
    assert turn.document["revision_task"]["criticism_status"] == ADAPTER.STATUS
    assert turn.document["revision_task"]["causing_evidence_ids"] == ["E"]
    assert turn.validation_context["visible_post_criticism_prospective_evidence_ids"] == ["E"]
    assert evidence.created_revision < criticism.created_revision


def test_builder_rejects_unlinked_evidence_and_install_is_idempotent() -> None:
    qc = fake_qc()
    qc.build_turn = lambda *args, **kwargs: None
    ADAPTER.install(qc)
    first = qc.build_turn
    ADAPTER.install(qc)
    assert qc.build_turn is first
    assert qc.PROMPT.count(ADAPTER.PROMPT_RULE.strip()) == 1


def test_installed_compiler_requires_prior_environment_citation_and_uses_exact_state() -> None:
    ADAPTER.install(QC)
    turn = validator_turn()
    response = {
        "protocol": QC.RESPONSE_PROTOCOL,
        "request_id": turn.request_id,
        "basis_revision": turn.basis_revision,
        "schema_revision": {
            "local_ref": "s0",
            "chain_ref": "chain",
            "revises_schema_id": "target",
            "conditions": refined_conditions(),
            "preferred_consequence": {
                "operator": "Decrease",
                "measure": "TranslationAlignmentResidual",
                "arguments": ["?a", "?b"],
            },
            "evidence_ids": ["rel"],
        },
        "explanation_set": None,
        "attention_contributions": [],
        "expansion_requests": [],
    }
    missing = QC.compile_response(response, turn)
    assert missing["rejected"][0]["reason"] == "missing-prospective-evidence-citation"
    response["schema_revision"]["evidence_ids"] = ["env", "rel"]
    accepted = QC.compile_response(response, turn)
    assert accepted["schema_revision_accepted"] is True
    assert accepted["accepted"][0]["dependency_ids"] == ["crit", "der", "env", "rel", "target"]
