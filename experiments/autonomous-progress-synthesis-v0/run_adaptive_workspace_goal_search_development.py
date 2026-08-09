"""v1 repair: environment-refute or attention-suppress a misleading proxy."""
from __future__ import annotations

import json
from pathlib import Path

import run_workspace_goal_search_development as BASE


ARTIFACTS = BASE.HERE / "artifacts" / "adaptive-workspace-goal-search-development"
POLICIES = []


def adaptive_priority(goals, *, projection=lambda observation: observation):
    policy = BASE.POTENTIAL.AdaptivePotentialPolicy(goals, projection=projection, plateau_patience=12)
    POLICIES.append(policy)
    return policy


def main() -> int:
    BASE.ARTIFACTS = ARTIFACTS
    BASE.POTENTIAL.search_priority = adaptive_priority
    baseline = BASE.run("causal_search_only")
    treatment = BASE.run("shared_goal_attention")
    treatment["arm"] = "adaptive_shared_goal_attention"
    treatment["goal_attention_records"] = [record.__dict__ if hasattr(record, "__dict__") else {
        name: getattr(record, name) for name in record.__slots__
    } for record in POLICIES[-1].records()]
    document = {
        "protocol": "adaptive-workspace-potential-search-development-v1", "development_only": True,
        "consumed_game": BASE.GAME, "archived_proposal": str(BASE.ARCHIVED_RESULT.relative_to(BASE.ROOT)),
        "repair_after_v0_failure": "environment terminal refutation plus bounded plateau attention suppression",
        "frozen_bounds": {"total_action_budget": BASE.ACTION_BUDGET, "calibration": BASE.CALIBRATION_BUDGET, "max_depth": BASE.MAX_DEPTH, "max_states": BASE.MAX_STATES, "history_order": BASE.HISTORY_ORDER, "plateau_patience": 12},
        "results": [baseline, treatment],
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "RESULT.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(document, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
