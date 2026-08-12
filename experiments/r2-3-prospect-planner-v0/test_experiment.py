from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


PATH = Path(__file__).with_name("experiment.py")
SPEC = importlib.util.spec_from_file_location("r2_3_prospect_experiment", PATH)
assert SPEC and SPEC.loader
EXPERIMENT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPERIMENT
SPEC.loader.exec_module(EXPERIMENT)


def test_multi_game_scan_fails_closed_without_required_frozen_r2_state():
    result = EXPERIMENT.scan_multi_game_archive()
    assert result["games_in_inventory"] > 0
    assert result["eligible_candidates"] == []
    assert result["environment_interventions_authorized"] == 0
    assert all(not item["eligible"] for item in result["records"])


def test_limits_match_preregistered_hard_budgets():
    assert EXPERIMENT.PLANNER_LIMITS == {
        "enabled": True,
        "max_depth": 8,
        "max_frontier": 64,
        "max_expansions": 256,
        "max_milestones": 4,
        "max_goal_factorizations": 8,
        "minimum_effect_support": 1,
        "minimum_effect_confidence": 0.6,
    }
