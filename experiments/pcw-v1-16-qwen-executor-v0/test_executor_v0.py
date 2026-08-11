from __future__ import annotations

import ast
from concurrent.futures import Future
import importlib.util
import inspect
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import analysis_sandbox
import experiment
import executor_primitives
import policy
import protocol
import runner
import source_guard


def _snapshot() -> dict:
    packet = {
        "legal_opaque_actions": [{"action_id": 1}, {"action_id": 2}],
        "epistemic_graph": {
            "objects": [{"id": "eo:fact"}],
            "binding_catalog": {"columns": [], "rows": []},
        },
        "full_relevant_transition_history": [{"transition_id": "transition:0"}],
        "current_observation": {"reference": "observation:abc"},
        "dependency_aliases": {
            "eo:fact": "eo:fact", "transition:0": "transition:0",
            "observation:abc": "observation:abc",
        },
        "snapshot_hash": "snapshot",
    }
    return packet


def test_frozen_source_guard_and_arm_a_admission() -> None:
    assert len(source_guard.verify_frozen_sources()) >= 30
    _v116, base = experiment.load_frozen()
    result = experiment.frozen_arm_a_result(base, experiment.load_config())
    assert result["experiment_arm"] == "arm-a"
    assert result["actions"] == 38
    assert result["levels_completed"] == 1
    assert result["replay_verified"] is True


def test_executor_policy_never_calls_an_r2_action_selector() -> None:
    source = inspect.getsource(policy.ExecutorPolicy)
    tree = ast.parse(source)
    called_attributes = {
        node.func.attr for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "prediction_matrix" in called_attributes
    assert "plan" not in called_attributes


def test_ranked_proposal_requires_visible_dependencies_and_checkpoint() -> None:
    value = {
        "candidate_actions": [
            {
                "action_id": 2,
                "dependencies": ["transition:0"],
                "subgoal": "discriminate_hypotheses",
                "desired_delta": {"kind": "differentiate", "target_dependency": "transition:0"},
                "computed_reason": {"basis": "history_rule", "finding_indices": [0]},
                "value_case": {
                    "goal_progress": "unknown",
                    "epistemic_discrimination": "high",
                    "option_value": "preserves",
                    "known_risk": "low",
                    "redundancy": "low",
                },
                "expected_checkpoint": {
                    "observable_type": "grid_delta",
                    "direction": "change",
                    "target_dependency": "transition:0",
                    "horizon_steps": 1,
                },
                "invalidate_on": ["checkpoint_mismatch"],
            },
            {
                "action_id": 1,
                "dependencies": ["eo:fact"],
                "subgoal": "preserve_option_value",
                "desired_delta": {"kind": "differentiate", "target_dependency": "eo:fact"},
                "computed_reason": {"basis": "information_gain", "finding_indices": [0]},
                "value_case": {
                    "goal_progress": "positive",
                    "epistemic_discrimination": "medium",
                    "option_value": "unknown",
                    "known_risk": "medium",
                    "redundancy": "low",
                },
                "expected_checkpoint": {
                    "observable_type": "relation_change",
                    "direction": "differentiate",
                    "target_dependency": "eo:fact",
                    "horizon_steps": 1,
                },
                "invalidate_on": ["checkpoint_mismatch", "hard_contradiction"],
            },
        ],
        "decision": {"kind": "select", "action_id": 2},
        "computation_summary": [0],
        "open_questions": [],
    }
    proposal = protocol.validate_proposal(value, request_id="request", snapshot=_snapshot())
    assert proposal.selected_action == 2
    assert [item.action_id for item in proposal.candidates] == [2, 1]
    value["candidate_actions"][0]["dependencies"] = ["not-visible"]
    with pytest.raises(protocol.ProtocolError):
        protocol.validate_proposal(value, request_id="request", snapshot=_snapshot())


def test_trigger_is_mechanical_and_generic() -> None:
    reasons = protocol.trigger_reasons(
        legal_actions=[1, 2], controller_report={"records": []}, prediction_matrix=[]
    )
    assert reasons == ("no-settled-unique-policy",)
    assert protocol.trigger_reasons(
        legal_actions=[1], controller_report={"records": []}, prediction_matrix=[]
    ) == ()


def test_python_sandbox_is_fresh_bounded_and_read_only() -> None:
    limits = experiment.load_config()["python"]
    result = analysis_sandbox.run_analysis(
        "result = {'n': len(snapshot['items']), 'total': sum(snapshot['items'])}",
        {"items": [1, 2, 3]}, limits,
    )
    assert result["status"] == "ok"
    assert result["return_value"] == {"n": 3, "total": 6}
    for source in ("open('/tmp/x')", "import os", "().__class__"):
        with pytest.raises(analysis_sandbox.SandboxError):
            analysis_sandbox.run_analysis(source, {}, limits)


def test_worker_prompts_are_logically_isolated() -> None:
    _v116, base = experiment.load_frozen()
    assert protocol.WORKER_ID == "qwen-executor"
    assert protocol.EXECUTOR_PROMPT != base.QC.PROMPT
    request = protocol.request_payload(
        model_config={
            "model": "fixture", "max_tokens_stage_1": 10,
            "max_tokens_stage_2": 10,
        },
        snapshot={"legal_opaque_actions": [{"action_id": 1}]},
        stage="analysis", tool_available=False,
    )
    assert request["messages"][0] == {"role": "system", "content": protocol.EXECUTOR_PROMPT}
    assert len(request["messages"]) == 2
    assert not any("orientation" in str(message).lower() for message in request["messages"])


def test_support_authority_is_not_modified_by_executor_ledger_events(tmp_path: Path) -> None:
    _v116, base = experiment.load_frozen()
    ledger = base.LEDGER
    workspace = "authority-fixture"
    ledger.append_event(
        tmp_path, workspace_id=workspace, event_type="WorkspaceStarted",
        actor="coordinator", payload={"fixture": True},
    )
    for event_type, actor in (
        ("ExecutorRequest", "coordinator"),
        ("ExecutorComputation", "qwen_executor"),
        ("ExecutorProposal", "qwen_executor"),
        ("ExecutorResult", "coordinator"),
    ):
        ledger.append_event(
            tmp_path, workspace_id=workspace, event_type=event_type,
            actor=actor, payload={"fixture": True},
        )
    assert all(event["event_type"] != "EpistemicGraphEvent" for event in ledger.list_events(tmp_path))


def test_one_action_executor_chain_is_replayable_and_returns_result_to_workspace(tmp_path: Path) -> None:
    class FixtureFifo:
        def __init__(self) -> None:
            self.sequence = 0
            self.snapshot_bytes = 0

        def submit(self, _context: str, payload: dict) -> Future:
            self.sequence += 1
            content = json.loads(payload["messages"][1]["content"])
            snapshot = content["snapshot"]
            self.snapshot_bytes = max(self.snapshot_bytes, int(snapshot["encoded_bytes"]))
            schema_name = payload["response_format"]["json_schema"]["name"]
            if schema_name.endswith("analysis_v0"):
                parsed = {
                    "mode": "verbal", "dependencies": [],
                        "findings": ["fixture comparison"], "code": None,
                        "missing_operation": None,
                }
            else:
                action = int(snapshot["legal_opaque_actions"][0]["action_id"])
                parsed = {
                    "candidate_actions": [{
                        "action_id": action,
                        "dependencies": [snapshot["current_observation"]["reference"]],
                        "subgoal": "discriminate_hypotheses",
                        "desired_delta": {"kind": "differentiate", "target_dependency": snapshot["current_observation"]["reference"]},
                        "computed_reason": {"basis": "information_gain", "finding_indices": [0]},
                        "value_case": {
                            "goal_progress": "unknown",
                            "epistemic_discrimination": "high",
                            "option_value": "preserves",
                            "known_risk": "low",
                            "redundancy": "low",
                        },
                        "expected_checkpoint": {
                            "observable_type": "grid_delta",
                            "direction": "change",
                            "target_dependency": snapshot["current_observation"]["reference"],
                            "horizon_steps": 1,
                        },
                        "invalidate_on": ["checkpoint_mismatch"],
                    }],
                    "decision": {"kind": "select", "action_id": action},
                    "computation_summary": [0], "open_questions": [],
                }
            future: Future = Future()
            future.set_result(SimpleNamespace(
                sequence=self.sequence,
                response={
                    "parsed": parsed, "raw_body": "{\"usage\":{}}",
                    "latency_s": 0.0, "transport_error": None,
                },
            ))
            return future

    v116, base = experiment.load_frozen()
    frozen_config = v116.load_config()
    frozen_config["qwen"]["max_calls_per_episode"] = 0
    config = experiment.load_config()
    config["action_budget"] = 1
    fifo = FixtureFifo()
    episode = runner.ExecutorEpisodeRunner(
        base=base, frozen_config=frozen_config, experiment_config=config,
        arm="arm-b", fifo=fifo, artifact_root=tmp_path,
        environments=base.CENSUS.DEFAULT_ENVIRONMENTS,
    )
    result = episode.run()
    assert result["actions"] == 1
    assert result["replay_verified"] is True
    assert result["support_authority_violations"] == 0
    assert result["first_executor_chain"]["settlement_workspace_object_id"].startswith("eo:")
    assert fifo.snapshot_bytes < config["executor"]["snapshot_max_bytes"]


def test_frozen_primitive_surface_is_small_generic_and_game_free() -> None:
    primitive_manifest = executor_primitives.manifest()
    assert primitive_manifest["version"] == "executor-generic-primitives-v0.1"
    assert len(primitive_manifest["functions"]) == 8
    forbidden = {"find_player", "find_target", "find_collectible", "solve_lock", "move_to_goal", "solve_ar25", "palette role", "action meaning"}
    assert not any(token in str(primitive_manifest).lower() for token in forbidden)
    snapshot = {
        "epistemic_graph": {
            "objects": [{"id": "eo:a", "kind": "entity", "created_by": "r2", "invalidated": False}],
            "binding_catalog": {
                "columns": [], "rows": [], "schema_registry": {},
            },
        },
        "full_relevant_transition_history": [],
    }
    assert executor_primitives.get_object(snapshot, "eo:a")["kind"] == "entity"
    assert executor_primitives.manhattan([0, 1], [2, 4]) == 5
    assert executor_primitives.bfs({"a": ["b"], "b": ["c"]}, "a", ["c"]) == ["a", "b", "c"]
