from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent


def load_analyzer():
    spec = importlib.util.spec_from_file_location("r21_campaign_analyzer_test", HERE / "analyze.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_runner():
    spec = importlib.util.spec_from_file_location("r21_campaign_runner_test", HERE / "run.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_event(root: Path, seq: int, event_type: str, payload: dict | None = None):
    path = root / "workspaces" / "w" / "events" / f"{seq:08d}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({
        "event_type": event_type,
        "payload": payload or {},
    }), encoding="utf-8")


def traced_turn(
    turn: int, *, action: int = 2, selected: int = 2,
    changed: bool = False, identity: str = "UNIQUE",
    mechanism: str = "SUPPORTED",
):
    explanation = {
        "claim": "one unchanged situated proposal",
        "verb": "align",
        "control_status": "PROGRESS_ELIGIBLE" if mechanism == "SUPPORTED" else "PROBE_ELIGIBLE",
        "desired_delta": {"measure": "centroid_distance", "direction": "decrease"},
        "identity": {"actor": {"status": identity}, "target": {"status": "UNIQUE"}},
        "mechanism": {
            "actor": {"status": mechanism}, "target": {"status": "SUPPORTED"},
        },
    }
    return {
        "turn": turn,
        "frame": [[0, 2, 0]],
        "decision": {
            "selected_action": selected,
            "r2_1_explanation_control": {"current_explanation": explanation},
        },
        "settlement": {
            "action": action, "observation_changed": changed, "levels_completed": 0,
        },
    }


def test_classifier_reports_each_observable_layer_without_claiming_game_rules():
    analyzer = load_analyzer()
    timeline = [
        traced_turn(1),
        traced_turn(2, identity="BROKEN", mechanism="CONTESTED"),
        traced_turn(3, selected=1),
    ]
    result = analyzer.classify_trace(timeline, outcome={
        "status": "error", "error_type": "RuntimeError", "error": "recorded failure",
        "actions": 3, "levels_completed": 0,
    })

    assert tuple(result["layers"]) == analyzer.FAILURE_LAYERS
    assert result["observable_outcome"] == "failure-observed"
    assert result["layers"]["execution_coverage"]["assessment"] == "support-observed"
    assert result["layers"]["perception_animation_evidence"]["assessment"] == "partial-evidence"
    assert result["layers"]["identity"]["assessment"] == "limitation-observed"
    assert result["layers"]["mechanics"]["assessment"] == "limitation-observed"
    assert result["layers"]["telos_semantic_stagnation"]["assessment"] == "grounded-hypothesis-observed"
    assert result["layers"]["exploration_no_change"]["assessment"] == "limitation-observed"
    assert result["layers"]["planning"]["assessment"] == "failure-observed"
    assert result["layers"]["runtime_deadline"]["assessment"] == "failure-observed"
    assert result["layers"]["success"]["assessment"] == "not-observed"
    assert "does not identify hidden game rules" in result["epistemic_note"]


def test_missing_animation_identity_mechanics_and_runtime_are_explicit_unknowns():
    analyzer = load_analyzer()
    result = analyzer.classify_trace(())

    assert result["observable_outcome"] == "unknown"
    for layer in (
        "execution_coverage", "perception_animation_evidence", "identity",
        "mechanics", "exploration_no_change", "planning", "runtime_deadline", "success",
    ):
        assert result["layers"][layer]["assessment"] == "unknown"
        assert result["layers"][layer]["unknowns"]


def test_semantic_repetition_counts_qwen_note_writes_not_every_action_turn():
    analyzer = load_analyzer()
    timeline = []
    for basis in (10, 20, 30):
        turn = traced_turn(basis)
        turn["scratchpad"] = {
            "basis_revision": basis,
            "goal_proposals": [{
                "verb": "align", "observable": "centroid_distance",
                "direction": "decrease",
            }],
        }
        timeline.append(turn)
    result = analyzer.classify_trace(timeline, outcome={"actions": 3, "levels_completed": 0})
    telos = result["layers"]["telos_semantic_stagnation"]
    assert telos["assessment"] == "repetition-observed"
    assert {"semantic_note_writes": 3} in telos["evidence"]
    assert "does not establish that the proposal is false" in telos["unknowns"][0]


def test_animation_and_success_require_direct_recorded_evidence():
    analyzer = load_analyzer()
    turn = traced_turn(1, changed=True)
    turn["ordered_frames"] = [[[0]], [[1]]]
    turn["levels_completed"] = 1
    result = analyzer.classify_trace([turn], outcome={
        "status": "complete", "actions": 1, "levels_completed": 1,
    })

    assert result["observable_outcome"] == "success-observed"
    assert result["layers"]["perception_animation_evidence"]["assessment"] == "support-observed"
    assert result["layers"]["success"] == {
        "assessment": "success-observed",
        "evidence": [{"levels_completed": 1}],
        "unknowns": [],
    }


def test_complex_only_abstention_is_execution_coverage_not_a_rule_inference():
    analyzer = load_analyzer()
    result = analyzer.classify_trace((), outcome={
        "status": "complete", "actions": 0, "levels_completed": 0,
        "stop_reason": "complex-only-epistemic-abstention",
    })

    execution = result["layers"]["execution_coverage"]
    assert execution["assessment"] == "limitation-observed"
    assert {"stop_reason": "complex-only-epistemic-abstention"} in execution["evidence"]
    assert "which unexecuted action would be useful" in execution["unknowns"][0]
    assert result["layers"]["runtime_deadline"]["assessment"] == "support-observed"


def test_analyze_classifies_outcomes_that_have_no_replay(tmp_path):
    analyzer = load_analyzer()
    (tmp_path / "episodes").mkdir()
    outcomes = tmp_path / "outcomes"
    outcomes.mkdir()
    (outcomes / "pass-01--x--level-01.json").write_text(json.dumps({
        "game": "x", "start_level": 1, "status": "timeout", "actions": None,
    }), encoding="utf-8")

    report = analyzer.analyze(tmp_path)

    assert report["episodes"] == []
    assert len(report["outcomes_without_replay"]) == 1
    classified = report["outcomes_without_replay"][0]["observable_failure_layers"]
    assert classified["layers"]["runtime_deadline"]["assessment"] == "failure-observed"
    assert report["observable_failure_layer_counts"]["runtime_deadline"] == {
        "failure-observed": 1,
    }


def test_timeout_partial_outcome_counts_only_committed_successors(tmp_path):
    runner = load_runner()
    write_event(tmp_path, 1, "ActionPending", {"action_id": 1})
    write_event(tmp_path, 2, "TransitionCommitted", {"levels_completed": 0})
    write_event(tmp_path, 3, "ActionPending", {"action_id": 2})
    write_event(tmp_path, 4, "TransitionCommitted", {"levels_completed": 1})
    write_event(tmp_path, 5, "ActionPending", {"action_id": 3})
    # A malformed or half-written artifact must not manufacture an action.
    broken = tmp_path / "workspaces" / "w" / "events" / "00000006.json"
    broken.write_text("{", encoding="utf-8")

    assert runner.partial_ledger_outcome(tmp_path) == {
        "actions": 2,
        "levels_completed": 1,
        "uncommitted_pending_actions": 1,
        "partial_ledger_recovered": True,
    }


def test_aggregate_counts_recovered_commits_but_scores_only_completed_runs():
    runner = load_runner()
    rows = [
        {
            "game": "complete-game", "status": "complete",
            "actions": 2, "levels_completed": 1,
        },
        {
            "game": "error-game", "status": "error",
            "actions": 1, "levels_completed": 2,
            "uncommitted_pending_actions": 1,
            "partial_ledger_recovered": True,
        },
        {
            "game": "timeout-game", "status": "timeout",
            "actions": 0, "levels_completed": 3,
            "uncommitted_pending_actions": 2,
            "partial_ledger_recovered": True,
        },
    ]

    summary = runner.aggregate(
        rows, run_id="test", started_at="2026-01-01T00:00:00+00:00",
        deadline_s=60,
    )

    # All three externally committed transitions count, including the one
    # recovered after error. Pending actions do not.
    assert summary["total_actions"] == 3
    # Campaign score remains based on completed outcomes, not partial recovery.
    assert summary["total_levels_completed"] == 1
    assert summary["games_clearing_a_level"] == ["complete-game"]
    assert summary["runs_completed"] == 1
    assert summary["runs_errored"] == 1
    assert summary["runs_timed_out"] == 1


def test_controller_source_inventory_covers_loaded_chain_and_excludes_tests():
    runner = load_runner()
    hashes = runner.r21_source_hashes()

    assert "R2_1.md" in hashes
    for required in (
        "experiments/explanation-guided-one-action-control-v0/experiment.py",
        "experiments/explanation-guided-one-action-control-v0/observation_envelope.py",
        "experiments/explanation-guided-one-action-control-v0/config.json",
        "experiments/parallel-cognitive-workspace-v0/workspace.py",
        "experiments/parallel-cognitive-workspace-v1-4/ledger.py",
        "experiments/parallel-cognitive-workspace-v1-9/evidence_revision.py",
        "experiments/parallel-cognitive-workspace-v1-12/causal_packet.py",
        "experiments/parallel-cognitive-workspace-v1-14/compiler_feedback.py",
        "experiments/parallel-cognitive-workspace-v1-16/experiment.py",
        "experiments/parallel-cognitive-workspace-v1-16/config.json",
        "experiments/qwen-generic-explanation-priors-v0/experiment.py",
        "experiments/prior-accelerated-relational-transfer-v0/experiment.py",
        "src/reflector2/explanations.py",
        "src/reflector2/perception.py",
        "src/reflector2/runtime.py",
    ):
        assert required in hashes
    assert not any(Path(path).name.startswith("test_") for path in hashes)


def test_source_hash_diff_reports_added_deleted_and_modified_paths():
    runner = load_runner()

    assert runner.source_hash_diff(
        {"deleted.py": "a", "modified.py": "b", "same.py": "c"},
        {"added.py": "d", "modified.py": "e", "same.py": "c"},
    ) == {
        "added.py": {
            "change": "added", "frozen_sha256": None, "current_sha256": "d",
        },
        "deleted.py": {
            "change": "deleted", "frozen_sha256": "a", "current_sha256": None,
        },
        "modified.py": {
            "change": "modified", "frozen_sha256": "b", "current_sha256": "e",
        },
    }


def test_batch_stops_before_first_worker_and_finalizes_source_drift(tmp_path, monkeypatch):
    runner = load_runner()
    runner.HERE = tmp_path
    frozen = {"R2_1.md": "a", "experiments/controller.py": "b"}
    changed = {"R2_1.md": "a", "experiments/controller.py": "changed"}
    snapshots = iter((frozen, changed))
    monkeypatch.setattr(runner, "r21_source_hashes", lambda: next(snapshots))
    monkeypatch.setattr(runner, "discover_games", lambda: ["aa00"])
    monkeypatch.setattr(runner, "breadth_order", lambda games: list(games))
    real_popen = runner.subprocess.Popen

    def guarded_popen(command, *popen_args, **popen_kwargs):
        if command[:2] == ["git", "rev-parse"]:
            return real_popen(command, *popen_args, **popen_kwargs)
        raise AssertionError("worker launched")

    monkeypatch.setattr(runner.subprocess, "Popen", guarded_popen)
    args = SimpleNamespace(
        run_id="source-drift-test", global_seconds=120,
        reserve_seconds=30, per_run_seconds=60,
    )

    assert runner.run_batch(args) == 2
    root = tmp_path / "artifacts" / args.run_id
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    summary = json.loads((root / "summary.json").read_text(encoding="utf-8"))

    assert manifest["frozen_controller_source_hashes"] == frozen
    assert manifest["frozen_controller_source_digest"] == runner.source_inventory_digest(frozen)
    assert summary["stop_reason"] == "controller-source-drift"
    assert summary["before_worker"] == "pass-01--aa00--level-01"
    assert summary["source_drift_paths"] == ["experiments/controller.py"]
    assert summary["source_drift"]["experiments/controller.py"] == {
        "change": "modified", "frozen_sha256": "b", "current_sha256": "changed",
    }
    assert summary["runs_started"] == 0


def test_click_repetition_uses_exact_command_not_bare_action_id():
    analyzer = load_analyzer()
    first = traced_turn(1, action=6, selected=6, changed=False)
    second = traced_turn(2, action=6, selected=6, changed=False)
    third = traced_turn(3, action=6, selected=6, changed=False)
    first["decision"]["selected_command"] = {"command_id": "click:a"}
    second["decision"]["selected_command"] = {"command_id": "click:b"}
    third["decision"]["selected_command"] = {"command_id": "click:b"}

    classified = analyzer.classify_trace([first, second, third])
    # Distinct coordinates are distinct interventions; only the exact repeated
    # click command is evidence of repeated non-informative probing.
    assert classified["layers"]["exploration_no_change"]["evidence"] == [
        {"changed_observations": 0},
        {"no_change_observations": 3},
        {"consecutive_identical_no_change": 1},
    ]
