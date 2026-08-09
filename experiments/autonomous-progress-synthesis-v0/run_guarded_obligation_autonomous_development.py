"""Source-blind runtime test of the guarded-obligation capability on consumed ls20.

The mechanism was designed after this development game's source was inspected,
so this can validate autonomous grounding and control, not generalization.
Runtime induction uses only reset observations and environment transitions.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = HERE / "artifacts" / "guarded-obligation-autonomous-development"
GAME = "ls20"
sys.path.insert(0, str(HERE))

import guarded_obligation_capability as guarded
import guarded_visual_induction as visual
import region_object_projection as projection
import run_broad_nonregression as runner


def _load_tracker():
    path = ROOT / "experiments/progress-goal-generic-calibration-v1/tracker.py"
    spec = importlib.util.spec_from_file_location("guarded_development_tracker", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TRACKER = _load_tracker()


def _record(observation):
    return runner.BASE.observation_record(observation)


def _grid(observation):
    return runner.BASE.observation_grid(observation)


def main() -> int:
    arcade, environment = runner.BASE.open_environment(
        ROOT / "environment_files", ARTIFACTS / "factual", GAME
    )
    history = []
    calibration_rows = []
    try:
        initial_observation = environment.observation_space or environment.reset()
        initial_record = _record(initial_observation)
        initial_grid = _grid(initial_observation)
        legal = runner.BASE.simple_legal_actions(environment, initial_observation)
        for index, action in enumerate(legal):
            environment.reset()
            after = runner.BASE.execute_action(
                environment, GAME, action, {}, "guarded-role-calibration"
            )
            after_grid = _grid(after)
            motions = TRACKER.pixel_motion_hypotheses(initial_grid, after_grid)
            if motions:
                motion = motions[0]
                calibration_rows.append(visual.MotionCalibration(
                    int(action), motion.before_anchor, motion.after_anchor,
                    motion.size, after_grid, f"transition:calibration:{index}",
                ))

        hypotheses = visual.enumerate_hypotheses(initial_grid, calibration_rows)
        if len(hypotheses) != 1:
            raise RuntimeError(f"expected one grounded hypothesis, got {len(hypotheses)}")
        hypothesis = hypotheses[0]
        initial_objects = projection.project_objects(
            initial_grid,
            controlled_bboxes=((
                hypothesis.actor_anchor[0], hypothesis.actor_anchor[1],
                hypothesis.actor_anchor[0] + calibration_rows[0].actor_size[0],
                hypothesis.actor_anchor[1] + calibration_rows[0].actor_size[1],
            ),),
        )
        register_object = next(
            row for row in initial_objects if row.object_id == hypothesis.register_id
        )

        observation = environment.reset()
        probe = guarded.plan_capability(visual.probe_capability(hypothesis))
        if probe.mode != "probe-transformer" or not probe.actions:
            raise RuntimeError("induction did not produce a transformer probe")
        for action in probe.actions:
            before = _record(observation)
            observation = runner.BASE.execute_action(
                environment, GAME, action, {}, "guarded-transformer-probe"
            )
            after = _record(observation)
            history.append({"action": int(action), "phase": "probe", "before": before, "after": after})

        observed_register = visual.observe_register(_grid(observation), register_object.bbox)
        if observed_register is None or observed_register == hypothesis.current_register:
            raise RuntimeError("probe did not directly change grounded register")
        transition_id = "transition:" + history[-1]["after"]["digest"][:24]
        effect = guarded.ArrivalEffect(
            f"node:{hypothesis.transformer_anchor[0]}:{hypothesis.transformer_anchor[1]}",
            hypothesis.current_register, observed_register, (transition_id,),
        )
        world = guarded.GuardedWorld(
            effect.node, observed_register, hypothesis.transitions,
            (guarded.GuardedObligation(
                "obligation:" + hypothesis.obligation_id,
                f"node:{hypothesis.obligation_anchor[0]}:{hypothesis.obligation_anchor[1]}",
                hypothesis.required_register,
            ),),
            (effect,), (), tuple(sorted(set(hypothesis.basis_ids + (transition_id,)))),
        )
        capability = guarded.compile_capability(world, attention=hypothesis.attention)
        control = guarded.plan_capability(capability)
        if not control.complete:
            raise RuntimeError("confirmed transformer did not yield a complete control plan")
        for action in control.actions:
            before = _record(observation)
            observation = runner.BASE.execute_action(
                environment, GAME, action, {}, "guarded-obligation-control"
            )
            after = _record(observation)
            history.append({"action": int(action), "phase": "control", "before": before, "after": after})
            if int(after["levels_completed"]) >= 1:
                break
        final = _record(observation)
    finally:
        arcade.close_scorecard()

    replay_arcade, replay_environment = runner.BASE.open_environment(
        ROOT / "environment_files", ARTIFACTS / "replay", GAME
    )
    try:
        replay_observation = replay_environment.observation_space or replay_environment.reset()
        exact_replay = True
        for row in history:
            replay_observation = runner.BASE.execute_action(
                replay_environment, GAME, row["action"], {}, "guarded-exact-replay"
            )
            exact_replay = exact_replay and _record(replay_observation)["digest"] == row["after"]["digest"]
    finally:
        replay_arcade.close_scorecard()

    observed_remaining = 0 if int(final["levels_completed"]) >= 1 else 1
    supported = guarded.adjudicate(capability, guarded.GuardedEvidence(
        capability.candidate_id, capability.binding_id,
        "transition:" + final["digest"][:24], 0, observed_remaining, True,
    ))
    document = {
        "protocol": "guarded-obligation-autonomous-development-v0",
        "development_only": True,
        "consumed_game": GAME,
        "mechanism_designed_after_source_inspection": True,
        "runtime_source_or_oracle_binding_used": False,
        "transferable_evidence": False,
        "initial_digest": initial_record["digest"],
        "legal_intervention_count": len(legal),
        "reset_calibration_actions": len(legal),
        "direct_motion_calibrations": len(calibration_rows),
        "hypothesis_count": len(hypotheses),
        "grounded_roles": {
            "actor": hypothesis.actor_id,
            "register": hypothesis.register_id,
            "obligation": hypothesis.obligation_id,
            "transformer": hypothesis.transformer_id,
        },
        "probe_actions": list(probe.actions),
        "control_actions": list(control.actions),
        "factual_actions": len(history),
        "total_environment_actions_including_reset_calibration": len(legal) + len(history),
        "levels_completed": int(final["levels_completed"]),
        "exact_replay": exact_replay,
        "environment_support": supported.empirical_support,
        "environment_confirmations": supported.confirmations,
        "action_sequence": [row["action"] for row in history],
        "scientific_conclusion": (
            "Autonomous visual grounding, a direct transformer probe, environment evidence, "
            "and guarded control completed one consumed development level. A frozen cross-game "
            "test is still required before claiming transfer."
        ),
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "RESULT.json").write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(document, indent=2, sort_keys=True))
    return 0 if int(final["levels_completed"]) >= 1 and exact_replay else 1


if __name__ == "__main__":
    raise SystemExit(main())
