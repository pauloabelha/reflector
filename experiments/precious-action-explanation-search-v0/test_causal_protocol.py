from __future__ import annotations

from dataclasses import replace
from concurrent.futures import Future
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import causal_protocol as cp
import experiment
import live_controls
import matched_executor
import snapshot_view


def _proposal(action: int = 2) -> dict:
    return {
        "candidate_actions": [{
            "action_id": action,
            "computation_dependencies": ["comp:1"],
            "finding_refs": ["finding:0"],
        }],
        "decision": {"kind": "select", "action_id": action},
    }


def _treatment() -> cp.TreatmentResult:
    return cp.TreatmentResult(True, "PYTHON_EXECUTOR", ())


def test_battlefield_selection_is_mechanical_and_history_bearing() -> None:
    documents = [
        {"qwen_changed_action": False, "decision": {}, "prospective_plan": {}}
        for _ in range(26)
    ]
    documents[25] = {
        "qwen_changed_action": True,
        "decision": {"action_id": 2, "fallback_action_id": 5, "prior_used": True},
        "prospective_plan": {"mode": "control"},
    }
    events = [{"event_id": f"decision:{i}", "seq": i * 10} for i in range(26)]
    branches = [{
        "decision_index": 25,
        "actual_exact_replay": True,
        "actual": {"action_id": 2, "before_digest": "same"},
        "fallback": {"action_id": 5, "before_digest": "same"},
    }]
    selected = cp.select_battlefield(
        decision_documents=documents,
        decision_events=events,
        counterfactual_branches=branches,
        minimum_predecessors=24,
    )
    assert selected.decision_index == 25
    assert selected.baseline_action == 2
    assert selected.before_digest == "same"


def test_identity_requires_every_frozen_field_to_match() -> None:
    identity = cp.IdentityEnvelope(
        protocol=cp.PROTOCOL,
        source_commit="commit",
        source_manifest_hash="manifest",
        config_hash="config",
        primitive_version="v0.1",
        primitive_source_hash="primitive",
        game="ar25",
        seed=1,
        prefix_transition_count=25,
        prefix_hash="prefix",
        observation_hash="observation",
        snapshot_hash="snapshot",
    )
    cp.assert_same_identity([identity, identity])
    with pytest.raises(cp.CausalProtocolError, match="ARM_IDENTITY_MISMATCH"):
        cp.assert_same_identity([identity, replace(identity, snapshot_hash="other")])


def test_incoherent_no_legal_action_is_rejected() -> None:
    proposal = {
        "candidate_actions": [{"action_id": 2}],
        "decision": {"kind": "abstain", "reason": "NO_LEGAL_ACTION"},
    }
    with pytest.raises(cp.CausalProtocolError, match="INCOHERENT_NO_LEGAL_ACTION"):
        cp.validate_decision_coherence(proposal, legal_actions=[1, 2])


def test_tooling_abstention_requires_a_named_gap() -> None:
    proposal = {
        "candidate_actions": [{"action_id": 2}],
        "decision": {"kind": "abstain", "reason": "SNAPSHOT_OR_TOOLING_INSUFFICIENT"},
    }
    with pytest.raises(cp.CausalProtocolError, match="TOOLING_ABSTENTION_REQUIRES_GAP"):
        cp.validate_decision_coherence(proposal, legal_actions=[1, 2])
    proposal["missing_operation"] = "generic history grouping"
    assert cp.validate_decision_coherence(proposal, legal_actions=[1, 2]) is None


def test_c_treatment_requires_success_and_selected_provenance() -> None:
    computation = {
        "mode": "python",
        "generated_code": "result = {'x': 1}",
        "python_status": "ok",
        "code_hash": "hash",
        "structured_return_value": {"x": 1},
        "computation_id": "comp:1",
    }
    assert cp.assess_treatment(
        arm="arm-c", computation=computation, proposal=_proposal()
    ).engaged
    failed = dict(computation, python_status="runtime-error")
    result = cp.assess_treatment(arm="arm-c", computation=failed, proposal=_proposal())
    assert not result.engaged
    assert "PYTHON_NOT_SUCCESSFUL" in result.reasons


def test_checkpoint_is_executable_and_calibrated() -> None:
    before = [[0, 0], [0, 0]]
    after = [[0, 1], [0, 0]]
    observed = cp.successor_observables(
        before_grid=before,
        after_grid=after,
        before_record={"levels_completed": 0},
        after_record={"levels_completed": 0, "digest": "after"},
    )
    checkpoint = {
        "confidence": 0.8,
        "predicates": [
            {"observable": "grid_changed", "operator": "eq", "value": True},
            {"observable": "changed_cell_count", "operator": "eq", "value": 1},
            {"observable": "changed_bbox", "operator": "eq", "value": [0, 1, 0, 1]},
            {"observable": "level_delta", "operator": "eq", "value": 0},
        ],
    }
    result = cp.compare_checkpoint(checkpoint, observed=observed)
    assert result.passed
    assert result.predicate_accuracy == 1.0
    assert result.brier_loss == pytest.approx(0.04)


def test_frozen_verdict_fixtures_cover_positive_negative_inconclusive() -> None:
    common = dict(
        identity_ok=True,
        replay_ok=True,
        b_valid=True,
        c_valid=True,
        c_treatment=_treatment(),
        computation_changed_action=True,
        c_checkpoint_brier=0.05,
        b_checkpoint_brier=0.30,
        c_progress=0,
        b_progress=0,
        c_information=2,
        b_information=1,
        c_hard_risk_regression=False,
    )
    assert cp.adjudicate_verdict(**common).status == cp.POSITIVE
    negative = dict(common, c_checkpoint_brier=0.30, b_checkpoint_brier=0.05, c_information=0, b_information=1)
    assert cp.adjudicate_verdict(**negative).status == cp.NEGATIVE
    absent = cp.TreatmentResult(False, "PYTHON_EXECUTOR", ("PYTHON_MODE_NOT_SELECTED",))
    inconclusive = dict(common, c_treatment=absent)
    assert cp.adjudicate_verdict(**inconclusive).status == cp.INCONCLUSIVE


def test_executor_vs_baseline_has_separate_frozen_verdicts() -> None:
    common = dict(
        label="ARM_B_VS_A", identity_ok=True, replay_ok=True,
        executor_valid=True, action_changed=True, executor_progress=0,
        baseline_progress=0, executor_information=2, baseline_information=1,
        hard_risk_regression=False,
    )
    assert cp.adjudicate_executor_vs_baseline(**common).status == cp.POSITIVE
    assert cp.adjudicate_executor_vs_baseline(
        **dict(common, executor_information=1)
    ).status == cp.NEGATIVE
    assert cp.adjudicate_executor_vs_baseline(
        **dict(common, replay_ok=False)
    ).status == cp.INCONCLUSIVE


def test_action_label_permutation_is_equivariant() -> None:
    proposal = _proposal(2)
    assert cp.validate_decision_coherence(proposal, legal_actions=[1, 2, 5]) == 2
    permutation = {1: 5, 2: 1, 5: 2}
    permuted = {
        **proposal,
        "candidate_actions": [
            {**item, "action_id": permutation[int(item["action_id"])]}
            for item in proposal["candidate_actions"]
        ],
        "decision": {"kind": "select", "action_id": permutation[2]},
    }
    assert cp.validate_decision_coherence(permuted, legal_actions=permutation.values()) == permutation[2]


def test_no_trigger_still_routes_to_sole_executor_policy() -> None:
    assert cp.executor_route([], legal_actions=[1, 2]) == ("SOLE_POLICY_DECISION_BOUNDARY",)
    assert cp.executor_route([], legal_actions=[]) == ()
    assert cp.executor_route(["ambiguity"], legal_actions=[1, 2]) == ("ambiguity",)


def test_empty_history_cannot_support_invented_transition_dependencies() -> None:
    cp.validate_history_dependencies([], transition_ids=[])
    with pytest.raises(cp.CausalProtocolError, match="HISTORY_DEPENDENCY_NOT_AVAILABLE"):
        cp.validate_history_dependencies(["t000"], transition_ids=[])


def test_prompt_compaction_preserves_full_hash_and_python_availability() -> None:
    objects = [
        {
            "id": f"p{i}", "kind": "partial_binding", "invalidated": False,
            "support": i, "contradiction": 0, "created_revision": i,
        }
        for i in range(20)
    ]
    snapshot = {
        "snapshot_hash": "full",
        "dependency_aliases": {"p0": "real:p0"},
        "full_relevant_transition_history": [],
        "epistemic_graph": {
            "objects": objects,
            "binding_catalog": {"rows": [], "columns": []},
            "edges": [],
        },
    }
    view = snapshot_view.compact_model_view(snapshot)
    assert view["full_snapshot_hash"] == "full"
    assert "dependency_aliases" not in view
    assert len(view["epistemic_graph"]["objects"]) == snapshot_view.MAX_BY_KIND["partial_binding"]
    compaction = view["epistemic_graph"]["compaction"]
    assert compaction["omitted_by_kind"]["partial_binding"]["count"] == (
        20 - snapshot_view.MAX_BY_KIND["partial_binding"]
    )
    assert compaction["full_data_available_to_python"] is True


def test_model_grammar_is_bounded_without_dependency_enum_bloat() -> None:
    dependencies = [f"o{i:05d}" for i in range(10_000)]
    analysis = matched_executor.analysis_schema(arm="arm-c", dependencies=dependencies)
    proposal = matched_executor.proposal_schema(
        legal_actions=[1, 2], dependencies=dependencies, computation_id="computation:x",
        finding_count=2,
    )
    encoded = json.dumps({"analysis": analysis, "proposal": proposal})
    assert len(encoded) < 10_000
    assert "o09999" not in encoded
    assert analysis["properties"]["code"]["maxLength"] == 800
    candidate = proposal["properties"]["candidate_actions"]["items"]
    assert candidate["properties"]["computed_reason"]["maxLength"] == 240


def test_attempt_namespaces_are_immutable(tmp_path: Path) -> None:
    first_id, first = experiment.allocate_attempt_root(tmp_path, manifest_hash="a" * 64)
    second_id, second = experiment.allocate_attempt_root(tmp_path, manifest_hash="a" * 64)
    assert first_id == "run-001-aaaaaaaaaaaa"
    assert second_id == "run-002-aaaaaaaaaaaa"
    assert first != second
    with pytest.raises(FileExistsError):
        first.mkdir(exist_ok=False)


def test_live_control_fixtures_are_coherent_and_do_not_touch_environment() -> None:
    snapshot = {
        "snapshot_hash": "original",
        "legal_opaque_actions": [
            {"action_id": 1, "token": "A1"},
            {"action_id": 2, "token": "A2"},
        ],
        "full_relevant_transition_history": [
            {"transition_id": "t000", "opaque_action": {"action_id": 1, "token": "A1"}},
            {"transition_id": "t001", "opaque_action": {"action_id": 2, "token": "A2"}},
        ],
    }
    permuted = live_controls.permuted_fixture(snapshot, {1: 2, 2: 1})
    assert [
        item["opaque_action"]["action_id"]
        for item in permuted["full_relevant_transition_history"]
    ] == [2, 1]
    assert [
        item["opaque_action"]["token"]
        for item in permuted["full_relevant_transition_history"]
    ] == ["A2", "A1"]
    deleted = live_controls.dependency_deleted_fixture(
        snapshot, transition_ids={"t000"},
    )
    assert [
        item["transition_id"] for item in deleted["full_relevant_transition_history"]
    ] == ["t001"]
    assert snapshot["full_relevant_transition_history"][0]["transition_id"] == "t000"


def test_matched_executor_engages_python_and_passes_full_snapshot() -> None:
    class Fifo:
        def submit(self, _context: str, payload: dict) -> Future:
            name = payload["response_format"]["json_schema"]["name"]
            user = json.loads(payload["messages"][1]["content"])
            snapshot = user["snapshot"]
            if "analysis" in name:
                assert snapshot["current_observation"]["reference"] in user["valid_dependency_ids"]
                parsed = {
                    "mode": "python",
                    "dependencies": [snapshot["current_observation"]["reference"]],
                    "findings": ["history counts computed"],
                    "code": "rows=query_transitions()\nresult={'n':len(rows)}",
                    "missing_operation": None,
                }
            else:
                computation = user["intermediate_computation"]
                assert user["valid_finding_refs"] == ["finding:0"]
                action = snapshot["legal_opaque_actions"][0]["action_id"]
                parsed = {
                    "candidate_actions": [{
                        "action_id": action,
                        "dependencies": [snapshot["current_observation"]["reference"]],
                        "computation_dependencies": [computation["computation_id"]],
                        "finding_refs": ["finding:0"],
                        "computed_reason": "exact history count",
                        "value_case": {
                            "progress": "unknown", "discrimination": "high",
                            "option_value": "preserves", "risk": "low", "redundancy": "low",
                        },
                        "expected_checkpoint": {
                            "grid_changed": True, "changed_cell_count_min": 1,
                            "changed_cell_count_max": 10, "level_delta": 0,
                            "terminal_expected": False, "confidence_milli": 700,
                        },
                        "invalidate_on": ["CHECKPOINT_MISMATCH"],
                    }],
                    "decision": {"kind": "select", "action_id": action},
                    "missing_operation": None,
                    "abstention_dependencies": [],
                }
            future: Future = Future()
            future.set_result(SimpleNamespace(response={
                "parsed": parsed, "raw_body": '{"usage":{}}', "latency_s": 0.0,
                "transport_error": None,
            }))
            return future

    class Sandbox:
        seen_full = False

        def run_analysis(self, _code: str, snapshot: dict, _limits: dict) -> dict:
            self.seen_full = snapshot.get("full_only") is True
            return {
                "status": "ok", "stdout": "", "stderr": "",
                "return_value": {"n": 2}, "execution_time_s": 0.01,
            }

    model_snapshot = {
        "legal_opaque_actions": [{"action_id": 1}, {"action_id": 2}],
        "current_observation": {"reference": "obs-current"},
        "full_relevant_transition_history": [{"transition_id": "t000"}],
        "epistemic_graph": {
            "objects": [], "binding_catalog": {"rows": []}, "edges": [],
        },
    }
    full_snapshot = {**model_snapshot, "snapshot_hash": "full", "full_only": True}
    sandbox = Sandbox()
    artifacts: dict[str, object] = {}
    worker = matched_executor.MatchedExecutor(
        fifo=Fifo(), sandbox=sandbox,
        model_config={
            "model": "fixture", "max_tokens_stage_1": 100,
            "max_tokens_stage_2": 100, "request_timeout_seconds": 1,
        },
        python_config={}, artifact_writer=lambda name, value: artifacts.__setitem__(name, value),
    )
    result = worker.deliberate(
        arm="arm-c", full_snapshot=full_snapshot, model_snapshot=model_snapshot,
    )
    assert result.treatment.engaged
    assert result.python_calls == 1
    assert sandbox.seen_full
    assert result.proposal["decision"]["action_id"] == 1
    assert result.computation["findings"] == ['python_result={"n":2}']
    assert "computation.json" in artifacts
