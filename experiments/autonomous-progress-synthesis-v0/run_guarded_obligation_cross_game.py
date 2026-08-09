"""Frozen, mechanically selected cross-game test for guarded obligations."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = HERE / "artifacts" / "guarded-obligation-cross-game-v0"
RECEIPT = ARTIFACTS / "SELECTION.json"
sys.path.insert(0, str(HERE))

import guarded_obligation_capability as guarded
import guarded_visual_induction as visual
import region_object_projection as projection
import run_broad_nonregression as runner


def _tracker():
    path = ROOT / "experiments/progress-goal-generic-calibration-v1/tracker.py"
    spec = importlib.util.spec_from_file_location("guarded_cross_tracker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec); sys.modules[spec.name] = module
    spec.loader.exec_module(module); return module


TRACKER = _tracker()


def run() -> dict:
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    game = str(receipt["selected_game"])
    arcade, environment = runner.BASE.open_environment(
        ROOT / "environment_files", ARTIFACTS / "factual", game
    )
    history = []; stop_reason = "not-started"; hypothesis = None
    probe = None; control = None; initial_record = None; final = None
    try:
        initial_observation = environment.observation_space or environment.reset()
        initial_record = runner.BASE.observation_record(initial_observation)
        initial_grid = runner.BASE.observation_grid(initial_observation)
        legal = runner.BASE.simple_legal_actions(environment, initial_observation)
        calibrations = []
        for index, action in enumerate(legal):
            environment.reset()
            after = runner.BASE.execute_action(environment, game, action, {}, "guarded-cross-calibration")
            motions = TRACKER.pixel_motion_hypotheses(initial_grid, runner.BASE.observation_grid(after))
            if motions:
                motion = motions[0]
                calibrations.append(visual.MotionCalibration(
                    int(action), motion.before_anchor, motion.after_anchor, motion.size,
                    runner.BASE.observation_grid(after), f"transition:calibration:{index}",
                ))
        try:
            hypotheses = visual.enumerate_hypotheses(initial_grid, calibrations)
        except Exception as error:
            hypotheses = (); stop_reason = f"induction-abstention:{type(error).__name__}:{error}"
        if len(hypotheses) != 1:
            if stop_reason == "not-started": stop_reason = f"hypothesis-count:{len(hypotheses)}"
            observation = environment.reset(); final = runner.BASE.observation_record(observation)
        else:
            hypothesis = hypotheses[0]
            actor_box = (
                hypothesis.actor_anchor[0], hypothesis.actor_anchor[1],
                hypothesis.actor_anchor[0] + calibrations[0].actor_size[0],
                hypothesis.actor_anchor[1] + calibrations[0].actor_size[1],
            )
            initial_objects = projection.project_objects(initial_grid, controlled_bboxes=(actor_box,))
            register = next(row for row in initial_objects if row.object_id == hypothesis.register_id)
            observation = environment.reset()
            probe = guarded.plan_capability(visual.probe_capability(hypothesis))
            if probe.mode != "probe-transformer" or not probe.actions:
                stop_reason = "no-transformer-probe"
            else:
                for action in probe.actions:
                    before = runner.BASE.observation_record(observation)
                    observation = runner.BASE.execute_action(environment, game, action, {}, "guarded-cross-probe")
                    after = runner.BASE.observation_record(observation)
                    history.append({"action":int(action),"phase":"probe","before":before,"after":after})
                observed = visual.observe_register(runner.BASE.observation_grid(observation), register.bbox)
                if observed is None or observed == hypothesis.current_register:
                    stop_reason = "probe-did-not-change-register"
                else:
                    evidence_id = "transition:" + history[-1]["after"]["digest"][:24]
                    transformer_node = f"node:{hypothesis.transformer_anchor[0]}:{hypothesis.transformer_anchor[1]}"
                    world = guarded.GuardedWorld(
                        transformer_node, observed, hypothesis.transitions,
                        (guarded.GuardedObligation(
                            "obligation:" + hypothesis.obligation_id,
                            f"node:{hypothesis.obligation_anchor[0]}:{hypothesis.obligation_anchor[1]}",
                            hypothesis.required_register,
                        ),),
                        (guarded.ArrivalEffect(
                            transformer_node, hypothesis.current_register, observed, (evidence_id,)
                        ),), (), tuple(sorted(set(hypothesis.basis_ids + (evidence_id,)))),
                    )
                    control = guarded.plan_capability(guarded.compile_capability(world))
                    if not control.complete:
                        stop_reason = "confirmed-model-has-no-control-plan"
                    else:
                        for action in control.actions:
                            before = runner.BASE.observation_record(observation)
                            observation = runner.BASE.execute_action(environment, game, action, {}, "guarded-cross-control")
                            after = runner.BASE.observation_record(observation)
                            history.append({"action":int(action),"phase":"control","before":before,"after":after})
                            if int(after["levels_completed"]) >= 1: break
                        stop_reason = "level-completed" if int(runner.BASE.observation_record(observation)["levels_completed"]) >= 1 else "control-ended-without-completion"
            final = runner.BASE.observation_record(observation)
    finally:
        arcade.close_scorecard()

    replay_arcade, replay_environment = runner.BASE.open_environment(
        ROOT / "environment_files", ARTIFACTS / "replay", game
    )
    try:
        replay = replay_environment.observation_space or replay_environment.reset(); exact = True
        for row in history:
            replay = runner.BASE.execute_action(replay_environment, game, row["action"], {}, "guarded-cross-replay")
            exact = exact and runner.BASE.observation_record(replay)["digest"] == row["after"]["digest"]
    finally:
        replay_arcade.close_scorecard()
    return {
        "protocol": receipt["protocol"], "selected_game": game,
        "selection_receipt": "SELECTION.json", "mechanism_commit": receipt["mechanism_commit"],
        "no_post_selection_tuning": True, "source_or_oracle_used": False,
        "initial_digest": initial_record["digest"], "legal_interventions": len(legal),
        "direct_motion_calibrations": len(calibrations), "hypothesis_count": len(hypotheses),
        "factual_actions": len(history), "levels_completed": int(final["levels_completed"]),
        "exact_replay": exact, "stop_reason": stop_reason,
        "action_sequence": [row["action"] for row in history],
        "probe_actions": [] if probe is None else list(probe.actions),
        "control_actions": [] if control is None else list(control.actions),
    }


def main() -> int:
    result = run()
    (ARTIFACTS / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True)); return 0


if __name__ == "__main__": raise SystemExit(main())
