"""Consumed-development run: learn opaque controls, infer flow roles, execute one plan."""
from __future__ import annotations
import importlib.util, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); return module

BASE = load("flow_routing_base", ROOT / "experiments/prior-accelerated-relational-transfer-v0/experiment.py")
FLOW = load("flow_routing_core", HERE / "flow_routing.py")

def main() -> int:
    out = HERE / "artifacts" / "sp80-development"
    out.mkdir(parents=True, exist_ok=True)
    arcade, env = BASE.open_environment(ROOT / "environment_files", out / "recordings", "sp80")
    try:
        initial = env.observation_space or env.reset()
        initial_grid = BASE.observation_grid(initial)
        initial_scene = FLOW.infer_scene(initial_grid)
        legal = BASE.simple_legal_actions(env, initial)
        movement, calibration, trigger = {}, [], None
        for action in legal:
            before = env.reset(); before_scene = FLOW.infer_scene(BASE.observation_grid(before))
            after = BASE.execute_action(env, "sp80", action, {}, "flow-control-calibration")
            record = BASE.observation_record(after)
            try:
                after_scene = FLOW.infer_scene(BASE.observation_grid(after))
                delta = (after_scene.reflector.x - before_scene.reflector.x, after_scene.reflector.y - before_scene.reflector.y)
            except FLOW.FlowRoutingError:
                delta = (0, 0)
            calibration.append({"opaque_action": action, "reflector_delta": delta, "state": record["state"]})
            if delta != (0, 0): movement[delta] = action
            elif record["digest"] != BASE.observation_record(before)["digest"]: trigger = action
        if trigger is None:
            remaining = [action for action in legal if action not in movement.values()]
            if len(remaining) != 1: raise RuntimeError("trigger intervention is not identified")
            trigger = remaining[0]
        plan = FLOW.plan_flow(initial_scene, movement, trigger)
        observation = env.reset(); history = []
        for action in plan.action_ids:
            before = BASE.observation_record(observation)
            observation = BASE.execute_action(env, "sp80", action, {}, "flow-routing-control")
            after = BASE.observation_record(observation)
            history.append({"opaque_action": action, "before_digest": before["digest"], "after_digest": after["digest"]})
            if after["levels_completed"] >= 1: break
        final = BASE.observation_record(observation)
        replay_arcade, replay_env = BASE.open_environment(ROOT / "environment_files", out / "replay-recordings", "sp80")
        try:
            # Match the factual episode boundary: calibration used resets and
            # the controlled trajectory began at the following reset state.
            _ = replay_env.observation_space or replay_env.reset()
            _ = BASE.execute_action(replay_env, "sp80", calibration[0]["opaque_action"], {}, "replay-boundary-warmup")
            replay = replay_env.reset(); replay_rows = []
            for expected in history:
                replay_before = BASE.observation_record(replay)
                replay = BASE.execute_action(replay_env, "sp80", expected["opaque_action"], {}, "flow-routing-exact-replay")
                replay_after = BASE.observation_record(replay)
                replay_rows.append({"before": replay_before["digest"], "after": replay_after["digest"]})
            replay_level = BASE.observation_record(replay)["levels_completed"]
        finally:
            replay_arcade.close_scorecard()
        exact_replay = all(
            actual["before"] == expected["before_digest"] and actual["after"] == expected["after_digest"]
            for actual, expected in zip(replay_rows, history)
        ) and replay_level >= 1
        document = {
            "protocol": "generic-flow-routing-development-v0",
            "calibration": calibration,
            "calibration_interactions": len(calibration),
            "factual_actions": len(history),
            "total_interactions": len(calibration) + len(history),
            "goal_potential": {"name": "UnservedTerminalCount", "before": plan.progress_before, "after_predicted": plan.progress_after},
            "grounding": {"source_column": initial_scene.source_column, "reflector_span": [initial_scene.reflector.x, initial_scene.reflector.x + initial_scene.reflector.width - 1], "terminal_ports": list(initial_scene.receptacle_ports)},
            "predicted_exit_columns": list(plan.predicted_exit_columns),
            "actions": history,
            "levels_completed": final["levels_completed"],
            "final_digest": final["digest"],
            "exact_replay": exact_replay,
        }
        (out / "RESULT.json").write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
        print(json.dumps(document, indent=2, sort_keys=True))
        return 0 if final["levels_completed"] >= 1 and exact_replay else 1
    finally:
        arcade.close_scorecard()

if __name__ == "__main__": raise SystemExit(main())
