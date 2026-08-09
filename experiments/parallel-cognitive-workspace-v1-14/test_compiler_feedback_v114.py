from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
V111 = HERE.parent / "parallel-cognitive-workspace-v1-11"
V112 = HERE.parent / "parallel-cognitive-workspace-v1-12"
FIXTURE_ROOT = V111 / "artifacts/workspaces/generic_prospective--ar25--shared_live_qwen"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V112_EXPERIMENT = load("compiler_feedback_v114_base", V112 / "experiment.py")
FEEDBACK = load("compiler_feedback_v114_test", HERE / "compiler_feedback.py")
BASE = V112_EXPERIMENT.BASE
QC = BASE.QC
EG = BASE.EG


def state_and_turn():
    state = BASE.graph_state(FIXTURE_ROOT)[0]
    orientation = QC.Orientation(
        workspace_id="compiler-feedback-fixture",
        initialized=True,
        cursor_revision=state.revision,
        cursor_hash=state.head_hash,
    )
    turn = V112_EXPERIMENT.PACKET.build_revision_turn(
        QC,
        state,
        orientation,
        request_id="compiler-feedback-fixture",
        token_budget=6400,
        compact_ids=True,
    )
    assert turn is not None
    return state, turn


def rejected_response(turn):
    task = turn.document["revision_task"]
    target = QC._visible_object_documents(turn)[task["semantic_target_id"]]["payload"]
    return {
        "parsed": {
            "revision": {
                "local_ref": "s0",
                "chain_ref": task["chain_ref"],
                "revises_schema_id": task["semantic_target_id"],
                # Exact alpha-repeat: a semantic attempt that the compiler can
                # criticize without any environment/control vocabulary.
                "conditions": target["conditions"],
                "preferred_consequence": target["preferred_consequence"],
                "relation_evidence_id": turn.document["causal_revision_packet"][
                    "current_relation_set"
                ]["id"],
                "prospective_evidence_id": turn.document["revision_task"][
                    "causing_evidence_ids"
                ][0],
            }
        }
    }


def test_compile_wrapper_retains_exact_attempt_and_exact_rejection() -> None:
    _state, turn = state_and_turn()
    response = rejected_response(turn)
    fallback = QC.compile_response
    wrapped = FEEDBACK.wrap_compile_response(QC, fallback)
    base = fallback(response, turn)
    compiled = wrapped(response, turn)
    assert compiled["schema_revision_accepted"] is False
    assert compiled["rejected"][0]["reason"] == "alpha-repeat"
    feedback = compiled["compiler_feedback"]
    assert feedback["raw_revision"] == response["parsed"]["revision"]
    assert feedback["compiler_rejections"] == base["rejected"]
    assert feedback["lineage"]["semantic_target_id"] == turn.document[
        "revision_task"
    ]["semantic_target_id"]
    assert FEEDBACK.is_action_blind(feedback)


def test_feedback_enters_one_workspace_without_epistemic_authority() -> None:
    state, turn = state_and_turn()
    response = rejected_response(turn)
    compiled = FEEDBACK.wrap_compile_response(QC, QC.compile_response)(response, turn)
    result = FEEDBACK.ingest_compiler_feedback(
        EG,
        QC,
        state,
        turn,
        compiled,
        response_id="fixture-response",
    )
    attempt_id, criticism_id = result.object_ids
    objects = {item.object_id: item for item in result.state.objects}
    attempt = objects[attempt_id]
    criticism = objects[criticism_id]
    assert attempt.kind == FEEDBACK.ATTEMPT_KIND and attempt.created_by == "qwen"
    assert criticism.kind == FEEDBACK.CRITICISM_KIND
    assert criticism.created_by == "kernel"
    assert criticism.payload["compiler_rejections"] == compiled["rejected"]
    assert criticism.payload["status"] == FEEDBACK.CRITICISM_STATUS
    assert criticism.payload["world_model_only"] is True
    assert FEEDBACK.is_action_blind(attempt.identity)
    assert FEEDBACK.is_action_blind(attempt.payload)
    assert FEEDBACK.is_action_blind(criticism.identity)
    assert FEEDBACK.is_action_blind(criticism.payload)
    assert not QC._forbidden_input(
        {
            "attempt_identity": attempt.identity,
            "attempt_payload": attempt.payload,
            "criticism_identity": criticism.identity,
            "criticism_payload": criticism.payload,
        }
    )
    assert attempt_id in criticism.dependency_ids
    assert set(attempt.dependency_ids) <= set(criticism.dependency_ids)
    assert EG.support(result.state, attempt_id) == 0
    assert EG.support(result.state, criticism_id) == 0
    assert not any(
        edge.kind in EG.EVIDENCE_EDGE_KINDS
        and (edge.source_id in result.object_ids or edge.target_id in result.object_ids)
        for edge in result.state.edges
    )
    attention = EG.attention_for(result.state, criticism_id)
    assert len(attention) == 1
    assert attention[0].worker == "qwen"
    assert attention[0].weight == 100
    assert attention[0].basis_ids == (attempt_id,)
    assert EG.salience(result.state, "qwen", criticism_id) > 700
    assert EG.replay((*BASE.graph_state(FIXTURE_ROOT)[1], *result.events)) == result.state

    repeated = FEEDBACK.ingest_compiler_feedback(
        EG,
        QC,
        result.state,
        turn,
        compiled,
        response_id="fixture-response",
    )
    assert repeated.state == result.state
    assert repeated.events == ()
    assert repeated.object_ids == result.object_ids


def test_abstention_and_accepted_revision_do_not_become_criticisms() -> None:
    _state, turn = state_and_turn()
    abstain = {"parsed": {"abstain": True}}
    compiled = FEEDBACK.wrap_compile_response(QC, QC.compile_response)(abstain, turn)
    assert "compiler_feedback" not in compiled

    response = rejected_response(turn)
    response["parsed"]["revision"]["conditions"] = [
        {"predicate": "SameInteriorLayout", "arguments": ["?a", "?b"]}
    ]
    accepted = FEEDBACK.wrap_compile_response(QC, QC.compile_response)(response, turn)
    assert accepted["schema_revision_accepted"] is True
    assert "compiler_feedback" not in accepted


def test_control_bearing_or_tampered_feedback_never_enters_workspace() -> None:
    state, turn = state_and_turn()
    response = rejected_response(turn)
    response["parsed"]["revision"]["action_id"] = 3
    compiled = FEEDBACK.wrap_compile_response(QC, QC.compile_response)(response, turn)
    assert "compiler_feedback" not in compiled

    clean = FEEDBACK.wrap_compile_response(QC, QC.compile_response)(
        rejected_response(turn), turn
    )
    clean["compiler_feedback"]["compiler_rejections"][0]["reason"] = "tampered"
    with pytest.raises(FEEDBACK.CompilerFeedbackError, match="contract mismatch"):
        FEEDBACK.ingest_compiler_feedback(
            EG,
            QC,
            state,
            turn,
            clean,
            response_id="tampered-response",
        )


def test_runner_wrapper_persists_feedback_before_normal_integration() -> None:
    state, turn = state_and_turn()
    compiled = FEEDBACK.wrap_compile_response(QC, QC.compile_response)(
        rejected_response(turn), turn
    )
    order = []

    def persist(_root, _workspace_id, result):
        order.append(("persist", len(result.events)))
        return result.state

    def fallback(
        _root,
        _workspace_id,
        integrated_state,
        _task_id,
        _turn,
        _compilation,
        _profile,
        *,
        action_count,
    ):
        order.append(("fallback", action_count))
        assert any(
            item.kind == FEEDBACK.CRITICISM_KIND
            for item in integrated_state.objects
        )
        return integrated_state

    wrapped = FEEDBACK.wrap_apply_qwen_compilation(EG, QC, fallback, persist)
    result = wrapped(
        None,
        "fixture",
        state,
        "fixture-task",
        turn,
        compiled,
        {},
        action_count=16,
    )
    assert order == [("persist", 3), ("fallback", 16)]

    order.clear()
    repeated = wrapped(
        None,
        "fixture",
        result,
        "fixture-task",
        turn,
        compiled,
        {},
        action_count=16,
    )
    assert repeated == result
    assert order == [("fallback", 16)]
