"""Paired diagnostic for an already-consumed live Qwen goal on ls20.

The archived proposal is not a claimed discovery or held-out result.  This run
asks only whether the generic support-zero potential/search seam can use a
previously discarded, non-collection proposal without changing its semantics.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = HERE / "artifacts" / "workspace-goal-search-development"
GAME = "ls20"
ACTION_BUDGET = 400
CALIBRATION_BUDGET = 4
SEARCH_BUDGET = ACTION_BUDGET - CALIBRATION_BUDGET
MAX_DEPTH = 16
MAX_STATES = 256
HISTORY_ORDER = 4

sys.path.insert(0, str(HERE))
import reset_replay_explorer as SEARCH
import run_broad_nonregression as R
import workspace_potential_search as POTENTIAL


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module)
    return module


LIVE = load("workspace_goal_search_live_v7", ROOT / "experiments/progress-goal-live-qwen-v7/live.py").RUNNER
ARCHIVED_RESULT = ROOT / "experiments/progress-goal-live-qwen-v7/artifacts/fresh-1/RESULT.json"


class ArcadeWorld:
    def __init__(self, environment): self.environment = environment; self.observation = None
    def reset(self): self.observation = self.environment.reset(); return self.observation
    def step(self, opaque_action):
        self.observation = R.BASE.execute_action(self.environment, GAME, opaque_action, {}, "workspace-potential-search")
        return self.observation
    def key(self, observation): return R.BASE.observation_record(observation)["digest"]
    def legal_actions(self, observation): return R.BASE.simple_legal_actions(self.environment, observation)
    def completed(self, observation): return int(observation.levels_completed) >= 1
    def terminal(self, observation): return str(observation.state).upper().rsplit(".", 1)[-1] in {"WIN", "GAME_OVER"}


def run(arm: str) -> dict:
    arcade, environment = R.BASE.open_environment(ROOT / "environment_files", ARTIFACTS / arm / "search", GAME)
    LIVE.ARTIFACTS = ARTIFACTS / arm / "calibration"
    try:
        observation = environment.observation_space or environment.reset()
        legal = R.BASE.simple_legal_actions(environment, observation)
        if len(legal) != CALIBRATION_BUDGET:
            raise RuntimeError("frozen calibration budget does not cover the legal intervention set")
        calibrated = LIVE.generic_calibration(environment, observation, GAME, legal)
        goal = None
        priority = None
        if arm == "shared_goal_attention":
            grid = R.BASE.observation_grid(calibrated["observation"])
            workspace = LIVE.GP.build_workspace(
                entities=calibrated["entities"], transitions=calibrated["transition_rows"],
                frame={"height": len(grid), "width": len(grid[0])},
            )
            proposal = json.loads(ARCHIVED_RESULT.read_text(encoding="utf-8"))["compilation"]["goal"]
            goal = POTENTIAL.compile_rendered_goal(proposal, workspace, grid, proposal_id="archived-live-qwen-v7")
            priority = POTENTIAL.search_priority((goal,), projection=R.BASE.observation_grid)
        result = SEARCH.search(
            ArcadeWorld(environment), action_budget=SEARCH_BUDGET, max_depth=MAX_DEPTH,
            max_states=MAX_STATES, history_order=HISTORY_ORDER, priority=priority,
        )
    finally:
        arcade.close_scorecard()
    return {
        "arm": arm, "solved": result.solved, "solution": list(result.solution),
        "calibration_actions": CALIBRATION_BUDGET, "search_actions": result.environment_actions,
        "total_environment_actions": CALIBRATION_BUDGET + result.environment_actions,
        "resets": result.reset_count, "states": result.discovered_states,
        "maximum_depth": result.maximum_depth_reached, "stop_reason": result.stop_reason,
        "goal_support": None if goal is None else goal.empirical_support,
    }


def main() -> int:
    rows = [run("causal_search_only"), run("shared_goal_attention")]
    document = {
        "protocol": "workspace-potential-search-development-v0", "development_only": True,
        "consumed_game": GAME, "archived_proposal": str(ARCHIVED_RESULT.relative_to(ROOT)),
        "frozen_bounds": {"total_action_budget": ACTION_BUDGET, "calibration": CALIBRATION_BUDGET, "max_depth": MAX_DEPTH, "max_states": MAX_STATES, "history_order": HISTORY_ORDER},
        "results": rows,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "RESULT.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(document, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
