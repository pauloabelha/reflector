from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = HERE / "artifacts" / "fresh-1"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = load("progress_cross_base", HERE.parent / "progress-goal-live-qwen-v1" / "live.py")
GP = load("progress_cross_protocol", HERE.parent / "progress-goal-live-qwen-v7" / "goal_protocol.py")
TRACKER = load("progress_cross_tracker", HERE.parent / "progress-goal-generic-calibration-v1" / "tracker.py")
FIELD = load("progress_cross_field", HERE.parent / "progress-drive-lattice-v0" / "lattice_progress.py")
SELECTOR = load("progress_cross_selector_runtime", HERE / "selector.py")
BASE.GP = GP
BASE.TRACKER = TRACKER


def terminal(record):
    return int(record["levels_completed"]) >= 1 or str(record.get("state", "")).upper() in {"WIN", "GAME_OVER"}


def run_arm(arm, config, game):
    root = ARTIFACTS / arm
    BASE.ARTIFACTS = root
    arcade, environment = BASE.LAB.BASE.BASE.open_environment(ROOT / "environment_files", root / "recordings", game)
    history = []
    field_doc = None
    try:
        observation = environment.observation_space or environment.reset()
        initial = BASE.LAB.BASE.BASE.observation_record(observation)
        legal = BASE.LAB.BASE.BASE.simple_legal_actions(environment, observation)
        calibrated = BASE.generic_calibration(environment, observation, game, legal)
        observation, history = calibrated["observation"], calibrated["history"]
        grid = BASE.LAB.BASE.BASE.observation_grid(observation)
        workspace = GP.build_workspace(entities=calibrated["entities"], transitions=calibrated["transition_rows"], frame={"height": len(grid), "width": len(grid[0])})
        request = GP.request_payload(workspace, config, BASE.LAB.BASE.grid_data_url(grid))
        BASE.atomic_json(root / "request.json", request)
        response = BASE.post_completion(config["endpoint"], request)
        BASE.atomic_json(root / "response.json", response)
        compilation = GP.compile_response(response, workspace)
        BASE.atomic_json(root / "compilation.json", compilation)
        if arm == "shared_progress":
            rows = calibrated["pixel_controller"]
            if rows is None:
                raise FIELD.ProgressFieldError("no unique pixel-controlled process")
            grids = (calibrated["initial_grid"],) + tuple(calibrated["grid_successors"])
            samples = tuple(FIELD.motion_sample(grids[i], grids[i + 1], before_anchor=row.before_anchor, after_anchor=row.after_anchor, size=row.size) for i, row in enumerate(rows))
            field = FIELD.infer_progress_field(samples)
            plan = FIELD.plan_progress(field, calibrated["movement"])
            actions = list(plan.actions)
            field_doc = {"step": field.step, "passable_count": len(field.passable), "overlays": field.overlay_affordances, "terminals": field.terminal_candidates, "waypoints": plan.waypoints, "actions": plan.actions}
            BASE.atomic_json(root / "progress_field.json", field_doc)
        else:
            remaining = max(0, int(config["action_budget"]) - len(history))
            actions = [int(legal[index % len(legal)]) for index in range(remaining)]
        for action in actions:
            if len(history) >= int(config["action_budget"]) or terminal(BASE.LAB.BASE.BASE.observation_record(observation)):
                break
            before = BASE.LAB.BASE.BASE.observation_record(observation)
            observation = BASE.LAB.BASE.execute_action(environment, game, action, {}, arm)
            after = BASE.LAB.BASE.BASE.observation_record(observation)
            history.append({"action": action, "before": before, "after": after, "phase": arm})
            BASE.atomic_json(root / "checkpoint.json", {"history": history})
        final = BASE.LAB.BASE.BASE.observation_record(observation)
    finally:
        arcade.close_scorecard()
    BASE.ARTIFACTS = root
    replay = BASE.exact_replay(history, game)
    result = {"arm": arm, "initial_digest": initial["digest"], "actions": len(history), "action_sequence": [row["action"] for row in history], "levels_completed": int(final["levels_completed"]), "final_digest": final["digest"], "exact_replay": replay, "qwen_compilation": compilation, "progress_field": field_doc}
    BASE.atomic_json(root / "RESULT.json", result)
    return result


def main():
    config = json.loads((HERE / "config.json").read_text())
    receipt = SELECTOR.select(ROOT / "environment_files")
    BASE.atomic_json(ARTIFACTS / "SELECTION.json", receipt)
    game = receipt["selected"]["game"]
    if game != config["development_game"]:
        raise RuntimeError("selector/config disagreement")
    results = [run_arm(arm, config, game) for arm in ("shared_cycle", "shared_progress")]
    cycle, progress = results
    same_start = cycle["initial_digest"] == progress["initial_digest"]
    valid = same_start and all(row["exact_replay"] for row in results)
    gain = progress["levels_completed"] > cycle["levels_completed"] or (progress["levels_completed"] >= 1 and cycle["levels_completed"] >= 1 and progress["actions"] * 4 <= cycle["actions"] * 3)
    summary = {"verdict": "PASS" if valid and gain else "FAIL" if valid else "INVALID", "same_start": same_start, "results": results}
    BASE.atomic_json(ARTIFACTS / "RESULT.json", summary)
    return 0 if summary["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
