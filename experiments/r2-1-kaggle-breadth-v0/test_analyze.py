from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent


def load_analyzer():
    spec = importlib.util.spec_from_file_location("r21_campaign_analyzer_test", HERE / "analyze.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
