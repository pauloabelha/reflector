from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


EXPERIMENT = Path(__file__).with_name("experiment.py")
ROOT = EXPERIMENT.parents[2]


def _module():
    spec = importlib.util.spec_from_file_location("r2_2_planner_ar25_v0", EXPERIMENT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _arm(*, state: str = "state", effects: str = "effects", explanation: str = "explanation",
         action: int = 1,
         progress: int = 0, completed: bool = False, completion_at: int | None = None):
    return {
        "fork_digest": state,
        "fork_effect_digest": effects,
        "fork_explanation_digest": explanation,
        "suffix": [{
            "predecessor_digest": state,
            "selected_action": action,
            "actual_progress": progress,
        }],
        "metrics": {
            "level_completion": completed,
            "actions_to_level_completion": completion_at,
        },
    }


def test_compare_rejects_nonmatched_state_or_knowledge() -> None:
    compare = _module().compare
    with pytest.raises(AssertionError, match="same environment state"):
        compare(_arm(state="a"), _arm(state="b"))
    with pytest.raises(AssertionError, match="same causal knowledge"):
        compare(_arm(effects="a"), _arm(effects="b"))
    with pytest.raises(AssertionError, match="same explanation basis"):
        compare(_arm(explanation="a"), _arm(explanation="b"))


def test_compare_records_only_state_matched_action_divergence() -> None:
    comparison = _module().compare(
        _arm(action=1, progress=-1, completed=False),
        _arm(action=2, progress=2, completed=True, completion_at=1),
    )
    assert comparison["same_observed_state"] is True
    assert comparison["same_causal_knowledge"] is True
    assert comparison["same_active_explanation_basis"] is True
    assert comparison["useful_divergence"] is True
    assert comparison["counterfactual_control_divergence"] == [{
        "predecessor_digest": "state",
        "one_step_action": 1,
        "planner_action": 2,
        "one_step_actual_progress": -1,
        "planner_actual_progress": 2,
    }]


def test_compare_records_action_versus_abstention_and_score_regression() -> None:
    baseline = _arm(action=3, progress=2, completed=True, completion_at=1)
    planner = _arm(completed=False)
    planner["suffix"] = []
    planner["stopped_at"] = {
        "predecessor_digest": "state", "reason": "no-r2-execution-authority",
    }
    comparison = _module().compare(baseline, planner)
    assert comparison["useful_divergence"] is False
    assert comparison["environment_score_changed"] is True
    assert comparison["counterfactual_control_divergence"][0]["kind"] == "action-vs-abstention"


def test_production_planner_has_no_experiment_fixture_literals() -> None:
    sources = [ROOT / "src/reflector2/r2/r2_1_adapter.py"]
    sources.extend((ROOT / "src/reflector2/planner").glob("*.py"))
    joined = "\n".join(path.read_text(encoding="utf-8").lower() for path in sources)
    for forbidden in ("ar25", "action_2", "blue_l", "yellow_l"):
        assert forbidden not in joined
