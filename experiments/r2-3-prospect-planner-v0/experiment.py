"""Non-executing R2.3 prospect scans over frozen evidence prefixes."""

from __future__ import annotations

import argparse
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

from reflector2.planner import (
    BoundedBestFirstPlanner,
    NoPlanPlanner,
    ProspectPlanner,
)
from reflector2.r2.observation_envelope import from_observation, settled_frame
from reflector2.r2.r2_1_adapter import FrameSchemaObserver


ROOT = Path(__file__).resolve().parents[2]
ENVIRONMENTS = ROOT / "environment_files"
DEFAULT_PREFIX = (1, *(2 for _ in range(11)), *(3 for _ in range(5)))
PLANNER_LIMITS = {
    "enabled": True,
    "max_depth": 8,
    "max_frontier": 64,
    "max_expansions": 256,
    "max_milestones": 4,
    "max_goal_factorizations": 8,
    "minimum_effect_support": 1,
    "minimum_effect_confidence": 0.6,
}
SEMANTIC_GOAL = {
    "verb": "fit",
    "schema_name": "Relational fit",
    "goal_family": "alignment",
    "roles": ["actor", "target"],
    "potential_roles": ["actor", "target"],
    "observable": "fit_residual",
    "direction": "decrease",
    "terminal_class": "minimum",
    "terminal_condition": "fit_residual=0",
    "role_constraints": [
        {
            "predicate": "same_outline",
            "arguments": ["actor", "target"],
            "modality": "suggested",
        },
        {
            "predicate": "different_value",
            "arguments": ["actor", "target"],
            "modality": "suggested",
        },
    ],
    "goal_contract": {
        "environment_terminal": "level_completion",
        "contributor_relation": "reached",
        "contributor_target": 0.0,
        "countercondition": "verb-terminal-without-environment-terminal",
    },
}


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _frame(observation: Any) -> list[list[int]]:
    return settled_frame(from_observation(observation))


def _legal(observation: Any) -> tuple[int, ...]:
    return tuple(sorted(
        int(getattr(item, "value", item))
        for item in observation.available_actions
    ))


def _execute_recorded(environment: Any, action_id: int) -> Any:
    result = environment.step(
        GameAction.from_id(int(action_id)),
        data={"game_id": "ar25"},
        reasoning={
            "experiment": "r2-3-prospect-planner-v0",
            "phase": "reconstruct-recorded-prefix-only",
        },
    )
    return result if result is not None else environment.observation_space


def _effects_digest(observer: FrameSchemaObserver) -> str:
    return _digest({
        repr(key): sorted((list(delta), count) for delta, count in values.items())
        for key, values in observer.action_effects.items()
    })


def _rank(
    observer: FrameSchemaObserver,
    observation: Any,
    backend: Any,
) -> tuple[dict[str, Any], float]:
    observer.planner_backend = backend
    started = time.perf_counter()
    ranking = observer.rank_actions(
        _legal(observation),
        fallback_action=min(_legal(observation)),
        semantic_goal=SEMANTIC_GOAL,
    )
    return ranking, (time.perf_counter() - started) * 1000.0


def _decision_summary(ranking: Mapping[str, Any], elapsed_ms: float) -> dict[str, Any]:
    explanation = ranking.get("current_explanation") or {}
    prediction = explanation.get("prediction") or {}
    certificate = ranking.get("plan_certificate") or {}
    planner = ranking.get("planner") or {}
    return {
        "action": int(ranking["selected_action"]),
        "command_id": (ranking.get("selected_command") or {}).get("command_id"),
        "control_status": explanation.get("control_status"),
        "potential_before": prediction.get("residual_before"),
        "predicted_potential_after": prediction.get("residual_after"),
        "predicted_local_progress": prediction.get("expected_progress"),
        "planner_status": planner.get("status"),
        "plan_depth": certificate.get("planned_depth"),
        "immediate_orientation": certificate.get("immediate_orientation"),
        "prospect_improvement_kind": certificate.get("justification"),
        "goal_prospect": certificate.get("successor_goal_prospect"),
        "expansions": planner.get("expansions"),
        "frontier_peak": planner.get("frontier_peak"),
        "elapsed_ms": round(elapsed_ms, 3),
    }


def scan_ar25_prefixes(*, max_boundary: int = 17) -> dict[str, Any]:
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(ENVIRONMENTS),
        recordings_dir=str(
            ROOT / "experiments/r2-3-prospect-planner-v0/artifacts/recordings"
        ),
    )
    environment = arcade.make("ar25", include_frame_data=True)
    if environment is None:
        raise RuntimeError("could not open AR25")
    observer = FrameSchemaObserver(PLANNER_LIMITS, planner_backend=NoPlanPlanner())
    observation = environment.observation_space
    records = []
    for boundary in range(min(max_boundary, len(DEFAULT_PREFIX)) + 1):
        before = _frame(observation)
        observer.fit_frame(before, turn=boundary)
        support_before = _effects_digest(observer)
        one_step, one_step_ms = _rank(observer, observation, NoPlanPlanner())
        bounded, bounded_ms = _rank(
            observer, observation, BoundedBestFirstPlanner(),
        )
        prospect, prospect_ms = _rank(observer, observation, ProspectPlanner())
        support_after = _effects_digest(observer)
        if support_before != support_after:
            raise AssertionError("non-executing planner scan changed empirical effect support")
        arms = {
            "one_step": _decision_summary(one_step, one_step_ms),
            "bounded_best_first": _decision_summary(bounded, bounded_ms),
            "prospect": _decision_summary(prospect, prospect_ms),
        }
        original_action = arms["one_step"]["action"]
        prospect_action = arms["prospect"]["action"]
        if prospect_action == original_action:
            classification = "no divergence"
        elif arms["prospect"]["immediate_orientation"] == "adverse":
            classification = "locally adverse but prospect-improving divergence"
        elif arms["prospect"]["control_status"] == "PROBE_ELIGIBLE":
            classification = "probe divergence"
        else:
            classification = "locally preferred divergence"
        records.append({
            "boundary": boundary,
            "state_digest": from_observation(observation)["settled_support_digest"],
            "effect_digest": support_before,
            "goal_contract_status": next(
                (item.status for item in observer.goal_contracts.values()),
                None,
            ),
            "arms": arms,
            "classification": classification,
            "candidate_action_executed": False,
        })
        if boundary >= min(max_boundary, len(DEFAULT_PREFIX)):
            break
        forced_action = int(DEFAULT_PREFIX[boundary])
        # Restore fallback ranking so the recorded intervention is settled
        # against its own exact explanation, never a scan candidate.
        observer.planner_backend = NoPlanPlanner()
        forced_ranking = observer.rank_actions(
            _legal(observation),
            fallback_action=forced_action,
            semantic_goal=SEMANTIC_GOAL,
        )
        forced_explanation = next((
            item for item in forced_ranking.get("explanations", ())
            if int(item.get("prediction", {}).get("action", -1)) == forced_action
        ), None)
        if forced_explanation is not None:
            observer.commit_prediction(forced_action, forced_explanation)
        successor = _execute_recorded(environment, forced_action)
        if int(successor.levels_completed) > int(observation.levels_completed):
            observation = successor
            break
        observer.settle_action(forced_action, before, _frame(successor))
        observation = successor

    divergences = [item for item in records if item["classification"] != "no divergence"]
    return {
        "protocol": "r2-3-ar25-non-executing-prefix-scan-v0",
        "prefix_reference": "R2_1.md replicated action-17 clear",
        "planner_limits": PLANNER_LIMITS,
        "boundaries_scanned": len(records),
        "records": records,
        "divergences": divergences,
        "locally_adverse_prospect_divergences": sum(
            item["classification"]
            == "locally adverse but prospect-improving divergence"
            for item in records
        ),
        "environment_actions_executed_from_candidates": 0,
    }


def _git_json(path: str) -> Mapping[str, Any] | None:
    completed = subprocess.run(
        ("git", "show", f"HEAD:{path}"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, Mapping) else None


def scan_multi_game_archive() -> dict[str, Any]:
    completed = subprocess.run(
        ("git", "ls-tree", "-r", "--name-only", "HEAD"),
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    checkpoint_paths = sorted(
        path for path in completed.stdout.splitlines()
        if path.startswith(
            "experiments/r2-25-game-context-spinoff-diagnostic/parallel-run/checkpoints/"
        ) and path.endswith(".json")
    )
    records = []
    for path in checkpoint_paths:
        artifact = _git_json(path) or {}
        result = artifact.get("result") or {}
        deterministic = result.get("deterministic") or {}
        opportunities = list(deterministic.get("opportunity_records") or ())
        game = str(deterministic.get("game") or Path(path).stem)
        # These artifacts predate GoalContract and do not serialize the R2.2
        # grounded explanation/effect snapshots needed to construct a frozen
        # ControlProblem. Opportunity counts cannot substitute for either.
        records.append({
            "game": game,
            "artifact": path,
            "archived_opportunities": len(opportunities),
            "has_two_supported_causal_alternatives": False,
            "has_active_grounded_verb_or_explanation": False,
            "has_goal_contract": False,
            "eligible": False,
            "reason": (
                "archived diagnostic lacks frozen R2.2 grounded explanation, "
                "command-scoped effect table, and GoalContract"
            ),
        })
    return {
        "protocol": "r2-3-multi-game-candidate-inventory-v0",
        "archive_scope": "available tracked context-spinoff checkpoints",
        "games_in_inventory": len(records),
        "records": records,
        "eligible_candidates": [],
        "frozen_candidates": [],
        "environment_interventions_authorized": 0,
        "negative_result": (
            "No archived multi-game state satisfies the preregistered evidence "
            "requirements; no candidate was fabricated or executed."
        ),
    }


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    ar25 = scan_ar25_prefixes()
    multi = scan_multi_game_archive()
    (output_dir / "ar25-prefix-scan.json").write_text(
        json.dumps(ar25, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    (output_dir / "multi-game-candidate-scan.json").write_text(
        json.dumps(multi, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    summary = {
        "protocol": "r2-3-prospect-planner-v0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "ar25_boundaries_scanned": ar25["boundaries_scanned"],
        "ar25_divergences": len(ar25["divergences"]),
        "ar25_locally_adverse_prospect_divergences": ar25[
            "locally_adverse_prospect_divergences"
        ],
        "multi_game_inventory": multi["games_in_inventory"],
        "multi_game_eligible_candidates": len(multi["eligible_candidates"]),
        "matched_forks_executed": 0,
        "reason_no_matched_fork": (
            "non-executing scan must freeze an eligible divergence first"
            if not ar25["divergences"] else
            "divergences require manual scientific review before environment execution"
        ),
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8",
    )
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "artifacts",
    )
    args = parser.parse_args(argv)
    print(json.dumps(run(args.output_dir), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
