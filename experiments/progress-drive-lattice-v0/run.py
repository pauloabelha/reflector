from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = HERE / "artifacts" / "fresh-1"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = load("progress_drive_live_base", HERE.parent / "progress-goal-live-qwen-v1" / "live.py")
PROTOCOL = load("progress_drive_protocol", HERE.parent / "progress-goal-live-qwen-v7" / "goal_protocol.py")
TRACKER = load("progress_drive_tracker", HERE.parent / "progress-goal-generic-calibration-v1" / "tracker.py")
FIELD = load("progress_drive_field", HERE / "lattice_progress.py")
RUNNER.ARTIFACTS = ARTIFACTS
RUNNER.GP = PROTOCOL
RUNNER.TRACKER = TRACKER


def main() -> int:
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    game = str(config["development_game"])
    arcade, environment = RUNNER.LAB.BASE.BASE.open_environment(
        ROOT / "environment_files", ARTIFACTS / "recordings", game
    )
    history = []
    durable_checkpoint = None
    if (ARTIFACTS / "checkpoint.json").exists():
        durable_checkpoint = json.loads((ARTIFACTS / "checkpoint.json").read_text(encoding="utf-8"))
    try:
        observation = environment.observation_space or environment.reset()
        initial = RUNNER.LAB.BASE.BASE.observation_record(observation)
        legal = RUNNER.LAB.BASE.BASE.simple_legal_actions(environment, observation)
        calibrated = RUNNER.generic_calibration(environment, observation, game, legal)
        observation = calibrated["observation"]
        history = calibrated["history"]
        if durable_checkpoint is not None:
            durable_history = durable_checkpoint.get("history", [])
            replayed_prefix = history[:len(durable_history)]
            if replayed_prefix != durable_history:
                raise RuntimeError("checkpoint calibration prefix did not replay exactly")
        current_grid = RUNNER.LAB.BASE.BASE.observation_grid(observation)
        workspace = PROTOCOL.build_workspace(
            entities=calibrated["entities"],
            transitions=calibrated["transition_rows"],
            frame={"height": len(current_grid), "width": len(current_grid[0])},
        )
        request = PROTOCOL.request_payload(workspace, config, RUNNER.LAB.BASE.grid_data_url(current_grid))
        request_path = ARTIFACTS / "request.json"
        if request_path.exists():
            durable_request = json.loads(request_path.read_text(encoding="utf-8"))
            if request != durable_request:
                raise RuntimeError("recovered request differs from the durable request")
        else:
            RUNNER.atomic_json(request_path, request)
        response_path = ARTIFACTS / "response.json"
        if response_path.exists():
            response = json.loads(response_path.read_text(encoding="utf-8"))
        else:
            response = RUNNER.post_completion(config["endpoint"], request)
            RUNNER.atomic_json(response_path, response)
        compilation = PROTOCOL.compile_response(response, workspace)
        RUNNER.atomic_json(ARTIFACTS / "compilation.json", compilation)

        pixel_rows = calibrated["pixel_controller"]
        if pixel_rows is None:
            raise RuntimeError("a unique pixel-grounded controlled process was not recovered")
        grids = (calibrated["initial_grid"],) + tuple(calibrated["grid_successors"])
        samples = tuple(
            FIELD.motion_sample(
                grids[index], grids[index + 1],
                before_anchor=row.before_anchor,
                after_anchor=row.after_anchor,
                size=row.size,
            )
            for index, row in enumerate(pixel_rows)
        )
        field = FIELD.infer_progress_field(samples)
        plan = FIELD.plan_progress(field, calibrated["movement"])
        RUNNER.atomic_json(ARTIFACTS / "progress_field.json", {
            "step": field.step,
            "lattice_offset": field.lattice_offset,
            "substrate": field.substrate,
            "background": field.background,
            "controlled_anchor": field.controlled_anchor,
            "passable": sorted(field.passable),
            "overlay_affordances": field.overlay_affordances,
            "terminal_candidates": field.terminal_candidates,
            "waypoints": plan.waypoints,
            "actions": plan.actions,
            "waypoint_action_ends": plan.waypoint_action_ends,
        })
        ends = set(plan.waypoint_action_ends)
        for index, action in enumerate(plan.actions, start=1):
            if len(history) >= int(config["action_budget"]):
                break
            before = RUNNER.LAB.BASE.BASE.observation_record(observation)
            observation = RUNNER.LAB.BASE.execute_action(environment, game, action, {}, "visual-progress-field")
            after = RUNNER.LAB.BASE.BASE.observation_record(observation)
            history.append({
                "action": action, "before": before, "after": after,
                "phase": "progress-field", "waypoint_reached": index in ends,
            })
            RUNNER.atomic_json(ARTIFACTS / "checkpoint.json", {"history": history, "compilation": compilation})
            if int(after["levels_completed"]) >= 1:
                break
        final = RUNNER.LAB.BASE.BASE.observation_record(observation)
    finally:
        arcade.close_scorecard()

    replay = RUNNER.exact_replay(history, game)
    passed = int(final["levels_completed"]) >= 1 and len(history) <= int(config["completion_action_gate"]) and replay
    result = {
        "verdict": "PASS" if passed else "FAIL",
        "development_only": True,
        "initial_digest": initial["digest"],
        "actions": len(history),
        "action_sequence": [row["action"] for row in history],
        "levels_completed": int(final["levels_completed"]),
        "final_digest": final["digest"],
        "exact_replay": replay,
        "qwen_compilation": compilation,
        "qwen_causally_used_for_control": False,
        "qwen_usage": response.get("usage", {}),
        "qwen_latency_seconds": response.get("latency_seconds"),
    }
    RUNNER.atomic_json(ARTIFACTS / "RESULT.json", result)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
