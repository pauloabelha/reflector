from __future__ import annotations
import importlib.util, json, pathlib, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ART = HERE / "artifacts" / "fresh-1"

def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); assert spec and spec.loader
    module = importlib.util.module_from_spec(spec); sys.modules[name] = module; spec.loader.exec_module(module); return module

V3 = load("ontology_v4_v3", HERE.parent / "progress-ontology-cross-v3" / "run.py")
FLOW = load("ontology_v4_flow", HERE.parent / "progress-drive-flow-routing-v0" / "flow_routing.py")
SEL = load("ontology_v4_selector", HERE / "selector.py")
V3.ART = ART; V3.V2.ART = ART; V3.V2.V1.ART = ART
B = V3.B

def changed_cells(before, after):
    return sum(a != b for row_a, row_b in zip(before, after) for a, b in zip(row_a, row_b))

def flow_arm(config, game):
    root = ART / "shared_progress_ontology"
    arcade, env = B.LAB.BASE.BASE.open_environment(ROOT / "environment_files", root / "recordings-flow", game)
    history = []
    try:
        initial_obs = env.observation_space or env.reset()
        initial = B.LAB.BASE.BASE.observation_record(initial_obs)
        initial_grid = B.LAB.BASE.BASE.observation_grid(initial_obs)
        scene = FLOW.infer_scene(initial_grid)
        legal = B.LAB.BASE.BASE.simple_legal_actions(env, initial_obs)
        movement = {}; nonmovement = []; calibration = []
        for action in legal:
            before = env.reset(); before_grid = B.LAB.BASE.BASE.observation_grid(before)
            before_scene = FLOW.infer_scene(before_grid)
            after = B.LAB.BASE.execute_action(env, game, action, {}, "flow-calibration")
            after_grid = B.LAB.BASE.BASE.observation_grid(after)
            try:
                after_scene = FLOW.infer_scene(after_grid)
                delta = (after_scene.reflector.x - before_scene.reflector.x, after_scene.reflector.y - before_scene.reflector.y)
            except FLOW.FlowRoutingError:
                delta = (0, 0)
            change = changed_cells(before_grid, after_grid)
            calibration.append({"opaque_action": action, "reflector_delta": delta, "changed_cells": change})
            if delta in {(-1, 0), (1, 0), (0, -1), (0, 1)}:
                movement[delta] = action
            else:
                nonmovement.append((change, action))
        if not nonmovement:
            raise FLOW.FlowRoutingError("no release-like intervention candidate")
        trigger = max(nonmovement, key=lambda row: (row[0], -row[1]))[1]
        plan = FLOW.plan_flow(scene, movement, trigger)
        obs = env.reset()
        for action in plan.action_ids:
            obs = V3.execute(env, game, obs, action, {}, history, "flow-routing")
            if V3.terminal(B.LAB.BASE.BASE.observation_record(obs)):
                break
        final = B.LAB.BASE.BASE.observation_record(obs)
    finally:
        arcade.close_scorecard()
    result = {
        "arm": "shared_progress_ontology", "mechanism": "flow_routing",
        "initial_digest": initial["digest"], "planning_interactions": len(calibration),
        "actions": len(history), "levels_completed": final["levels_completed"],
        "final_digest": final["digest"],
        "exact_replay": V3.replay(history, game, ART / "replay-flow"),
        "goal_potential": {"name": "UnservedTerminalCount", "before": plan.progress_before, "after_predicted": plan.progress_after},
        "calibration": calibration,
    }
    B.atomic_json(root / "RESULT.json", result); return result

def shared(config, game):
    failures = []
    try:
        return V3.placement(config, game)
    except Exception as error:
        failures.append(f"placement:{type(error).__name__}:{error}")
    try:
        return flow_arm(config, game)
    except Exception as error:
        failures.append(f"flow:{type(error).__name__}:{error}")
    try:
        return V3.V2.V1.run_arm("shared_progress_ontology", config, game)
    except Exception as error:
        failures.append(f"symbolic:{type(error).__name__}:{error}")
    return {"arm": "shared_progress_ontology", "status": "ontology_abstention", "diagnostics": failures}

def main():
    config = json.loads((HERE / "config.json").read_text())
    receipt = SEL.select(ROOT / "environment_files")
    B.atomic_json(ART / "SELECTION.json", receipt)
    game = receipt["selected"]["game"]
    results = []
    for function in (V3.baseline, shared):
        try: results.append(function(config, game))
        except Exception as error: results.append({"arm": "r2_cycle" if function is V3.baseline else "shared_progress_ontology", "error": f"{type(error).__name__}: {error}"})
    same = len(results) == 2 and all("initial_digest" in row for row in results) and results[0]["initial_digest"] == results[1]["initial_digest"]
    valid = same and all(row.get("exact_replay") for row in results)
    baseline, treatment = results
    gain = valid and (treatment["levels_completed"] > baseline["levels_completed"] or (treatment["levels_completed"] >= 1 and baseline["levels_completed"] >= 1 and treatment["actions"] * 4 <= baseline["actions"] * 3))
    verdict = "PASS" if gain else "FAIL" if valid else "ABSTAIN" if treatment.get("status") == "ontology_abstention" else "INVALID"
    summary = {"protocol": "progress-ontology-cross-v4", "verdict": verdict, "same_start": same, "results": results}
    B.atomic_json(ART / "RESULT.json", summary); print(json.dumps(summary, indent=2)); return 0 if gain else 1

if __name__ == "__main__": raise SystemExit(main())
