"""Matched exact-state AR25 forks for R2.2 ControlFactorization."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import time
from typing import Any, Mapping, Sequence

from arc_agi import Arcade, OperationMode
from arcengine import GameAction

from reflector2.r2.observation_envelope import from_observation, settled_frame
from reflector2.r2.controller import FastPathAuthority
from reflector2.r2.planner_wiring import QwenCliInvoker
from reflector2.r2.r2_1_adapter import FrameSchemaObserver
from reflector2.planner import (
    BoundedBestFirstPlanner,
    ModelPlanner,
    NoPlanPlanner,
    PlannerBackend,
    QwenPlanningModel,
)


ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENTS = ROOT / "environment_files"
DEFAULT_PREFIX = (1, *(2 for _ in range(11)), *(3 for _ in range(5)))
SEMANTIC_GOAL = {
    "verb": "fit",
    "schema_name": "Relational fit",
    "goal_family": "alignment",
    "observable": "fit_residual",
    "direction": "decrease",
    "terminal_condition": "fit_residual=0",
    "role_constraints": [
        {"predicate": "same_outline", "arguments": ["actor", "target"], "modality": "suggested"},
        {"predicate": "different_value", "arguments": ["actor", "target"], "modality": "suggested"},
    ],
}
PLANNER_LIMITS = {
    "max_depth": 8,
    "max_frontier": 64,
    "max_expansions": 256,
    "max_milestones": 4,
    "minimum_effect_support": 1,
    "minimum_effect_confidence": 0.6,
}
DEFAULT_QWEN_CLI = Path(
    "/home/pauloabelha/alienware16-llm/llama.cpp/build-cpu-native/bin/llama-cli"
)
DEFAULT_QWEN_MODEL = Path(
    "/home/pauloabelha/alienware16-llm/qwen/models/Qwen3VL-4B-Thinking-Q4_K_M.gguf"
)


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _git(*args: str) -> str:
    result = subprocess.run(
        ("git", *args), cwd=ROOT, text=True, capture_output=True, check=False,
    )
    return result.stdout.strip()


def _frame(observation: Any) -> list[list[int]]:
    return settled_frame(from_observation(observation))


def _legal(observation: Any) -> tuple[int, ...]:
    return tuple(sorted(int(getattr(item, "value", item)) for item in observation.available_actions))


def _execute(environment: Any, action_id: int, *, phase: str) -> Any:
    result = environment.step(
        GameAction.from_id(int(action_id)),
        data={"game_id": "ar25"},
        reasoning={"experiment": "r2-2-planner-ar25-v0", "phase": phase},
    )
    return result if result is not None else environment.observation_space


def _matching_explanation(ranking: Mapping[str, Any], action_id: int) -> dict[str, Any] | None:
    return next((
        item for item in ranking.get("explanations", ())
        if int(item.get("prediction", {}).get("action", -1)) == int(action_id)
    ), None)


def _rank(
    observer: FrameSchemaObserver,
    fast_path: FastPathAuthority,
    observation: Any,
    *,
    fallback_action: int,
) -> dict[str, Any]:
    ranking = None
    if fast_path.active:
        ranking = observer.rank_authorized_policy(
            _legal(observation), authorization=fast_path.document(),
        )
        if ranking is None:
            fast_path.revoke("no-preferred-legal-successor")
    if ranking is None:
        ranking = observer.rank_actions(
            _legal(observation), fallback_action=fallback_action,
            semantic_goal=SEMANTIC_GOAL,
        )
    return ranking


def replay_prefix(
    environment: Any,
    observer: FrameSchemaObserver,
    fast_path: FastPathAuthority,
    prefix: Sequence[int],
) -> tuple[Any, list[dict[str, Any]]]:
    observation = environment.observation_space
    trace = []
    for turn, action_id in enumerate(prefix):
        before = _frame(observation)
        observer.fit_frame(before, turn=turn)
        ranking = _rank(
            observer, fast_path, observation, fallback_action=int(action_id),
        )
        explanation = _matching_explanation(ranking, int(action_id))
        if explanation is not None:
            observer.commit_prediction(int(action_id), explanation)
        successor = _execute(environment, int(action_id), phase="matched-prefix")
        after = _frame(successor)
        settlement = observer.settle_action(int(action_id), before, after)
        fast_path.consider(explanation, settlement)
        trace.append({
            "turn": turn,
            "forced_action": int(action_id),
            "controller_counterfactual_action": int(ranking["selected_action"]),
            "predecessor_digest": from_observation(observation)["settled_support_digest"],
            "successor_digest": from_observation(successor)["settled_support_digest"],
            "adjudication": settlement["adjudication"],
            "actual_progress": settlement["actual_progress"],
            "levels_completed": int(successor.levels_completed),
            "fast_path": (ranking.get("control_proposal") or {}).get("mode") == "FAST_PATH",
        })
        observation = successor
    return observation, trace


def run_arm(
    *, arm: str, planner_backend: PlannerBackend, boundary: int,
    suffix_budget: int, recording_root: Path,
) -> dict[str, Any]:
    planner_enabled = not isinstance(planner_backend, NoPlanPlanner)
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(ENVIRONMENTS),
        recordings_dir=str(recording_root / f"boundary-{boundary}" / arm),
    )
    environment = arcade.make("ar25", include_frame_data=True)
    if environment is None:
        raise RuntimeError("could not open AR25")
    # Prefix replay is identical fallback-only control in every arm. The
    # experimental backend is installed only after evidence acquisition.
    observer = FrameSchemaObserver(
        {**PLANNER_LIMITS, "enabled": True}, planner_backend=NoPlanPlanner(),
    )
    fast_path = FastPathAuthority()
    observation, prefix_trace = replay_prefix(
        environment, observer, fast_path, DEFAULT_PREFIX[:boundary],
    )
    observer.planner_backend = planner_backend
    fork_digest = from_observation(observation)["settled_support_digest"]
    fork_effect_digest = _digest({
        repr(key): sorted((list(delta), count) for delta, count in values.items())
        for key, values in observer.action_effects.items()
    })
    original_planner_config = observer.planner_config
    observer.planner_config = replace(original_planner_config, enabled=False)
    observer.fit_frame(_frame(observation), turn=boundary)
    fork_one_step = observer.rank_actions(
        _legal(observation), fallback_action=min(_legal(observation)),
        semantic_goal=SEMANTIC_GOAL,
    )
    observer.planner_config = original_planner_config
    fork_explanation_digest = _digest({
        "selected_action": fork_one_step["selected_action"],
        "explanations": fork_one_step["explanations"],
        "role_hypotheses": fork_one_step["role_hypotheses"],
    })
    prefix_levels = int(observation.levels_completed)
    suffix = []
    counters: Counter[str] = Counter()
    planning_ms = 0.0
    stopped_at: dict[str, Any] | None = None
    for offset in range(max(0, int(suffix_budget))):
        if int(observation.levels_completed) > prefix_levels:
            break
        before = _frame(observation)
        observer.fit_frame(before, turn=boundary + offset)
        started = time.perf_counter()
        ranking = _rank(
            observer, fast_path, observation, fallback_action=min(_legal(observation)),
        )
        planning_ms += (time.perf_counter() - started) * 1000.0
        explanation = ranking.get("current_explanation") or {}
        fast_mode = (ranking.get("control_proposal") or {}).get("mode") == "FAST_PATH"
        counters["fast_path_interactions"] += fast_mode
        status = str(explanation.get("control_status", "INELIGIBLE"))
        if status == "PROBE_ELIGIBLE":
            counters["probe_actions"] += 1
        if status in {"PROGRESS_ELIGIBLE", "PLAN_ELIGIBLE"}:
            counters["predicted_progress_actions"] += 1
        planner = ranking.get("planner") or {}
        if planner_enabled and "planner" in ranking:
            counters["planner_invocations"] += 1
            counters["planner_success"] += planner.get("status") == "PLAN_FOUND"
            counters["planner_no_plan"] += planner.get("status") == "NO_PLAN"
        certificate = ranking.get("plan_certificate")
        if not bool(ranking.get("execution_authorized", ranking.get("control_override", False))):
            counters["stopped_without_r2_authority"] += 1
            stopped_at = {
                "predecessor_digest": from_observation(observation)["settled_support_digest"],
                "reason": "no-r2-execution-authority",
            }
            break
        action_id = int(ranking["selected_action"])
        successor = _execute(environment, action_id, phase=arm)
        completed = int(successor.levels_completed) > int(observation.levels_completed)
        if completed:
            settlement = {
                "adjudication": "level-completed",
                "actual_progress": None,
                "identity": {"status": "LEVEL_BOUNDARY"},
                "mechanism": {"status": "LEVEL_BOUNDARY"},
                "plan_settlement": None,
            }
        else:
            settlement = observer.settle_action(action_id, before, _frame(successor))
            fast_path.consider(explanation, settlement)
        identity_status = str(settlement.get("identity", {}).get("status", ""))
        mechanism_status = str(settlement.get("mechanism", {}).get("status", ""))
        counters["identity_failures"] += identity_status in {"BROKEN", "AMBIGUOUS"}
        counters["mechanism_failures"] += mechanism_status == "REFUTED"
        plan_settlement = settlement.get("plan_settlement") or {}
        counters["replans"] += bool(plan_settlement.get("replan_required"))
        counters["milestone_confirmations"] += plan_settlement.get("milestone") == "CONFIRMED"
        counters["milestone_refutations"] += plan_settlement.get("milestone") == "REFUTED"
        counters["first_step_confirmations"] += settlement.get("adjudication") == "confirmed"
        counters["first_step_refutations"] += settlement.get("adjudication") == "refuted"
        suffix.append({
            "offset": offset,
            "predecessor_digest": from_observation(observation)["settled_support_digest"],
            "selected_action": action_id,
            "control_status": status,
            "control_mode": "FAST_PATH" if fast_mode else "PLANNER" if certificate else "ONE_STEP",
            "potential_before": explanation.get("prediction", {}).get("residual_before"),
            "predicted_potential_after": explanation.get("prediction", {}).get("residual_after"),
            "actual_progress": settlement.get("actual_progress"),
            "adjudication": settlement.get("adjudication"),
            "identity": identity_status,
            "mechanism": mechanism_status,
            "plan_depth": certificate.get("planned_depth") if certificate else None,
            "expanded_nodes": planner.get("expansions"),
            "planner_attempts": planner.get("attempts"),
            "milestone": certificate.get("selected_milestone") if certificate else None,
            "plan_settlement": plan_settlement or None,
            "successor_digest": from_observation(successor)["settled_support_digest"],
            "levels_completed": int(successor.levels_completed),
        })
        observation = successor
        if completed:
            break
    levels = int(observation.levels_completed)
    return {
        "arm": arm,
        "planner_enabled": planner_enabled,
        "planner_backend": planner_backend.name,
        "boundary": boundary,
        "fork_digest": fork_digest,
        "fork_effect_digest": fork_effect_digest,
        "fork_explanation_digest": fork_explanation_digest,
        "prefix_actions": list(DEFAULT_PREFIX[:boundary]),
        "prefix_trace": prefix_trace,
        "suffix": suffix,
        "stopped_at": stopped_at,
        "metrics": {
            "level_completion": levels > prefix_levels,
            "levels_completed": levels,
            "actions_to_level_completion": boundary + len(suffix) if levels > prefix_levels else None,
            "suffix_actions": len(suffix),
            **dict(counters),
            "search_depths": [item["plan_depth"] for item in suffix if item["plan_depth"] is not None],
            "expanded_nodes": [item["expanded_nodes"] for item in suffix if item["expanded_nodes"] is not None],
            "wall_clock_planning_ms": round(planning_ms, 3),
        },
    }


def compare(arm_a: Mapping[str, Any], arm_b: Mapping[str, Any]) -> dict[str, Any]:
    if arm_a["fork_digest"] != arm_b["fork_digest"]:
        raise AssertionError("matched arms did not reach the same environment state")
    if arm_a["fork_effect_digest"] != arm_b["fork_effect_digest"]:
        raise AssertionError("matched arms did not acquire the same causal knowledge")
    if arm_a["fork_explanation_digest"] != arm_b["fork_explanation_digest"]:
        raise AssertionError("matched arms did not ground the same explanation basis")
    divergences = []
    for left, right in zip(arm_a["suffix"], arm_b["suffix"]):
        if left["predecessor_digest"] != right["predecessor_digest"]:
            break
        if left["selected_action"] != right["selected_action"]:
            divergences.append({
                "predecessor_digest": left["predecessor_digest"],
                "one_step_action": left["selected_action"],
                "planner_action": right["selected_action"],
                "one_step_actual_progress": left["actual_progress"],
                "planner_actual_progress": right["actual_progress"],
            })
    shared = min(len(arm_a["suffix"]), len(arm_b["suffix"]))
    if len(arm_a["suffix"]) != len(arm_b["suffix"]):
        longer, shorter, longer_label = (
            (arm_a, arm_b, "one_step")
            if len(arm_a["suffix"]) > len(arm_b["suffix"])
            else (arm_b, arm_a, "planner")
        )
        next_step = longer["suffix"][shared]
        stopped = shorter.get("stopped_at") or {}
        if stopped.get("predecessor_digest") == next_step.get("predecessor_digest"):
            divergences.append({
                "predecessor_digest": next_step["predecessor_digest"],
                "kind": "action-vs-abstention",
                "one_step_action": (
                    next_step["selected_action"] if longer_label == "one_step" else None
                ),
                "planner_action": (
                    next_step["selected_action"] if longer_label == "planner" else None
                ),
                "one_step_actual_progress": (
                    next_step["actual_progress"] if longer_label == "one_step" else None
                ),
                "planner_actual_progress": (
                    next_step["actual_progress"] if longer_label == "planner" else None
                ),
            })
    a_metrics, b_metrics = arm_a["metrics"], arm_b["metrics"]
    useful = bool(divergences) and (
        bool(b_metrics["level_completion"]) and not bool(a_metrics["level_completion"])
        or (
            b_metrics["actions_to_level_completion"] is not None
            and a_metrics["actions_to_level_completion"] is not None
            and b_metrics["actions_to_level_completion"] < a_metrics["actions_to_level_completion"]
        )
    )
    score_changed = bool(divergences) and (
        bool(a_metrics["level_completion"]) != bool(b_metrics["level_completion"])
        or (
            a_metrics["actions_to_level_completion"] is not None
            and b_metrics["actions_to_level_completion"] is not None
            and a_metrics["actions_to_level_completion"] != b_metrics["actions_to_level_completion"]
        )
    )
    return {
        "same_observed_state": True,
        "same_causal_knowledge": True,
        "same_active_explanation_basis": True,
        "counterfactual_control_divergence": divergences,
        "useful_divergence": useful,
        "environment_score_changed": score_changed,
    }


def run(
    boundaries: Sequence[int], suffix_budget: int, output: Path,
    *, qwen_cli: Path = DEFAULT_QWEN_CLI, qwen_model: Path = DEFAULT_QWEN_MODEL,
    include_model: bool = True,
) -> dict[str, Any]:
    recording_root = output.parent / "recordings"
    backends: list[tuple[str, PlannerBackend]] = [
        ("one_step", NoPlanPlanner()),
        ("planner", BoundedBestFirstPlanner()),
    ]
    if include_model:
        backends.append((
            "model_qwen",
            ModelPlanner(QwenPlanningModel(
                QwenCliInvoker(
                    qwen_cli, qwen_model, context_size=8192,
                    timeout_seconds=60,
                ),
                model_name=qwen_model.name,
                max_tokens=128,
            )),
        ))
    forks = []
    for boundary in boundaries:
        arms = {
            name: run_arm(
                arm=name, planner_backend=backend, boundary=boundary,
                suffix_budget=suffix_budget, recording_root=recording_root,
            )
            for name, backend in backends
        }
        fork = {
            "boundary": boundary,
            "arm_a": arms["one_step"],
            "arm_b": arms["planner"],
            "comparison": compare(arms["one_step"], arms["planner"]),
        }
        if "model_qwen" in arms:
            fork["arm_c"] = arms["model_qwen"]
            fork["comparison_model"] = compare(
                arms["one_step"], arms["model_qwen"],
            )
        forks.append(fork)
    source_paths = [
        ROOT / "src/reflector2/r2/config.json",
        ROOT / "src/reflector2/r2/controller.py",
        ROOT / "src/reflector2/r2/experiment.py",
        ROOT / "src/reflector2/r2/r2_1_adapter.py",
        *(ROOT / "src/reflector2/planner").glob("*.py"),
        Path(__file__),
    ]
    result = {
        "protocol": "r2-2-planner-ar25-matched-v0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_head": _git("rev-parse", "HEAD"),
        "git_branch": _git("branch", "--show-current"),
        "worktree_diff_sha256": hashlib.sha256(_git("diff", "--binary").encode()).hexdigest(),
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(source_paths)
        },
        "environment": "environment_files/ar25/0c556536",
        "prefix_trace_reference": "R2_1.md replicated action-17 clear",
        "semantic_goal_digest": _digest(SEMANTIC_GOAL),
        "planner_limits": PLANNER_LIMITS,
        "suffix_budget": suffix_budget,
        "model_arm": ({
            "adapter": "QwenPlanningModel",
            "transport": "QwenCliInvoker",
            "executable": str(qwen_cli),
            "model": str(qwen_model),
            "model_size_bytes": qwen_model.stat().st_size,
        } if include_model else None),
        "forks": forks,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--boundaries", type=int, nargs="+", default=[12])
    parser.add_argument("--suffix-budget", type=int, default=8)
    parser.add_argument("--qwen-cli", type=Path, default=DEFAULT_QWEN_CLI)
    parser.add_argument("--qwen-model", type=Path, default=DEFAULT_QWEN_MODEL)
    parser.add_argument("--without-model", action="store_true")
    parser.add_argument(
        "--output", type=Path,
        default=Path(__file__).resolve().parent / "artifacts" / "matched-result.json",
    )
    args = parser.parse_args(argv)
    result = run(
        args.boundaries, args.suffix_budget, args.output,
        qwen_cli=args.qwen_cli, qwen_model=args.qwen_model,
        include_model=not args.without_model,
    )
    print(json.dumps({
        "output": str(args.output),
        "forks": len(result["forks"]),
        "divergences": sum(len(item["comparison"]["counterfactual_control_divergence"]) for item in result["forks"]),
        "useful_divergences": sum(bool(item["comparison"]["useful_divergence"]) for item in result["forks"]),
        "model_divergences": sum(
            len(item.get("comparison_model", {}).get("counterfactual_control_divergence", ()))
            for item in result["forks"]
        ),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
