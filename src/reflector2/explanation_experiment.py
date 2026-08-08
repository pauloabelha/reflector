"""Matched random/local/explanation experiment over public ARC-AGI-3 games."""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence, TypeVar

from .arc_harness import _official_arcade, run_suite
from .explanations import ExplanationConfig


POLICIES = ("random", "local-schema", "explanation")
T = TypeVar("T")
R = TypeVar("R")


@dataclass(frozen=True, slots=True)
class MatchedJob:
    game_id: str
    environments_dir: Path
    output_dir: Path
    seed: int
    max_transitions: int
    max_explanations: int
    include_grids: bool


def discover_public_games(environments_dir: Path) -> tuple[str, ...]:
    return tuple(
        sorted(
            path.name
            for path in environments_dir.iterdir()
            if path.is_dir() and any(path.glob("*/metadata.json"))
        )
    )


def _run_game(job: MatchedJob) -> dict[str, Any]:
    policies: dict[str, Any] = {}
    for policy in POLICIES:
        root = job.output_dir / "runs" / job.game_id / policy
        arcade, action_from_id = _official_arcade(
            job.environments_dir, root / "recordings"
        )
        summary = run_suite(
            arcade,
            games=(job.game_id,),
            seed=job.seed,
            max_transitions=job.max_transitions,
            trace_dir=root / "traces",
            action_from_id=action_from_id,
            expected_games=1,
            include_grids=job.include_grids,
            policy=policy,
            explanation_config=ExplanationConfig(
                max_explanations=job.max_explanations
            ),
        )
        if summary["errors"]:
            raise RuntimeError(f"{job.game_id}/{policy}: {summary['errors']}")
        games = summary["games"]
        if not isinstance(games, list) or len(games) != 1:
            raise RuntimeError(f"{job.game_id}/{policy}: missing game result")
        policies[policy] = games[0]
    return {"game_id": job.game_id, "policies": policies}


def ordered_process_map(
    worker: Callable[[T], R], jobs: Sequence[T], workers: int
) -> list[R]:
    if workers < 1:
        raise ValueError("workers must be positive")
    if workers == 1:
        return [worker(job) for job in jobs]
    context = mp.get_context("fork")
    output: list[R | None] = [None] * len(jobs)
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        pending = {
            executor.submit(worker, job): index for index, job in enumerate(jobs)
        }
        for future in as_completed(pending):
            output[pending[future]] = future.result()
    if any(item is None for item in output):
        raise RuntimeError("parallel game worker returned no result")
    return [item for item in output if item is not None]


def _control_metrics(games: list[dict[str, Any]], policy: str) -> dict[str, Any]:
    results = [game["policies"][policy] for game in games]
    actions = sum(int(item["random_actions"]) for item in results)
    progress = sum(float(item["progress"]) for item in results)
    return {
        "score": sum(float(item["score"] or 0.0) for item in results),
        "total_progress": progress,
        "completed_levels": sum(int(item["peak_levels_completed"]) for item in results),
        "completed_games": sum(bool(item["completed"]) for item in results),
        "games_with_any_progress": sum(float(item["progress"]) > 0.0 for item in results),
        "actions_used": actions,
        "progress_per_action": progress / actions if actions else None,
        "macro_progress": progress / len(results) if results else 0.0,
    }


def _sum_explanation_metric(
    games: list[dict[str, Any]], key: str
) -> int | float:
    return sum(
        game["policies"]["explanation"]["runtime"]["explanations"][key]
        for game in games
    )


def _explanation_metrics(games: list[dict[str, Any]]) -> dict[str, Any]:
    reports = [
        game["policies"]["explanation"]["runtime"]["explanations"]
        for game in games
    ]
    active_counts = [value for report in reports for value in report["active_counts"]]
    constituents = [value for report in reports for value in report["constituent_counts"]]
    lifetimes = [value for report in reports for value in report["explanation_lifetimes"]]
    calibration = [value for report in reports for value in report["calibration"]]
    action_changes_by_game = [int(report["action_changes"]) for report in reports]
    total_changes = sum(action_changes_by_game)
    return {
        "constructed": _sum_explanation_metric(games, "explanations_constructed"),
        "mean_active": sum(active_counts) / len(active_counts) if active_counts else 0.0,
        "max_active": max(active_counts, default=0),
        "mean_constituents": sum(constituents) / len(constituents) if constituents else 0.0,
        "mean_lifetime": sum(lifetimes) / len(lifetimes) if lifetimes else 0.0,
        "changes": _sum_explanation_metric(games, "explanation_changes"),
        "retirements": _sum_explanation_metric(games, "explanations_retired"),
        "commitments": _sum_explanation_metric(games, "prediction_commitments"),
        "reified": _sum_explanation_metric(games, "shadows_reified"),
        "refuted": _sum_explanation_metric(games, "shadows_refuted"),
        "abstained": _sum_explanation_metric(games, "shadows_abstained"),
        "calibration_mean_support": (
            sum(float(item[0]) for item in calibration) / len(calibration)
            if calibration
            else None
        ),
        "calibration_confirmation_rate": (
            sum(int(item[1]) for item in calibration) / len(calibration)
            if calibration
            else None
        ),
        "decisions_changed": total_changes,
        "progress_after_changed": _sum_explanation_metric(
            games, "progress_after_changed_actions"
        ),
        "regressions_after_changed": _sum_explanation_metric(
            games, "regressions_after_changed_actions"
        ),
        "level_completions_after_changed": _sum_explanation_metric(
            games, "completions_after_changed_actions"
        ),
        "action_changing_precision": (
            _sum_explanation_metric(games, "progress_after_changed_actions")
            / total_changes
            if total_changes
            else None
        ),
        "discrimination_selections": _sum_explanation_metric(
            games, "discrimination_selections"
        ),
        "discrimination_settlements": _sum_explanation_metric(
            games, "discrimination_settlements"
        ),
        "games_without_usable_explanation": sum(
            int(report["explanations_constructed"]) == 0 for report in reports
        ),
        "decisions_without_action_prediction": _sum_explanation_metric(
            games, "no_action_prediction"
        ),
        "single_trivial_explanation_decisions": _sum_explanation_metric(
            games, "single_trivial_explanation"
        ),
        "micro_decisions": _sum_explanation_metric(games, "decisions"),
        "macro_games_with_action_change": sum(value > 0 for value in action_changes_by_game),
        "max_game_action_change_share": (
            max(action_changes_by_game, default=0) / total_changes
            if total_changes
            else None
        ),
    }


def aggregate(games: list[dict[str, Any]]) -> dict[str, Any]:
    controls = {policy: _control_metrics(games, policy) for policy in POLICIES}
    explanations = _explanation_metrics(games)
    deltas = {
        baseline: {
            "progress": controls["explanation"]["total_progress"]
            - controls[baseline]["total_progress"],
            "completed_levels": controls["explanation"]["completed_levels"]
            - controls[baseline]["completed_levels"],
            "score": controls["explanation"]["score"] - controls[baseline]["score"],
        }
        for baseline in ("random", "local-schema")
    }
    action_changes = int(explanations["decisions_changed"])
    progress_after = int(explanations["progress_after_changed"])
    regressions_after = int(explanations["regressions_after_changed"])
    completion_gain = deltas["random"]["completed_levels"]
    if (
        action_changes > 0
        and progress_after > regressions_after
        and completion_gain > 0
        and deltas["local-schema"]["completed_levels"] >= 0
    ):
        verdict = "PROMOTE"
    elif action_changes >= 10 and progress_after == 0 and regressions_after > 0:
        verdict = "REJECT"
    else:
        verdict = "CONTINUE-DIAGNOSTIC"
    return {
        "controls": controls,
        "explanations": explanations,
        "deltas": deltas,
        "verdict": verdict,
    }


def run_matched(jobs: Sequence[MatchedJob], workers: int) -> dict[str, Any]:
    games = ordered_process_map(_run_game, jobs, workers)
    return {
        "experiment": "minimal-explanation-driven-control",
        "config": {
            "workers": workers,
            "games": [job.game_id for job in jobs],
            "seed": jobs[0].seed if jobs else None,
            "max_transitions": jobs[0].max_transitions if jobs else None,
            "max_explanations": jobs[0].max_explanations if jobs else None,
            "policies": list(POLICIES),
        },
        "aggregate": aggregate(games),
        "games": games,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environments-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "environment_files",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/minimal-explanation-driven-control"),
    )
    parser.add_argument("--game", action="append", default=[])
    parser.add_argument("--expected-games", type=int)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-transitions", type=int, default=80)
    parser.add_argument("--max-explanations", type=int, default=8)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--verify-workers", action="store_true")
    parser.add_argument("--omit-grids", action="store_true")
    return parser


def main() -> None:
    parser = _parser()
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be positive")
    if args.max_transitions < 0:
        parser.error("--max-transitions must be non-negative")
    games = tuple(args.game) or discover_public_games(args.environments_dir)
    if args.expected_games is not None and len(games) != args.expected_games:
        parser.error(f"expected {args.expected_games} games, found {len(games)}")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    jobs = [
        MatchedJob(
            game,
            args.environments_dir,
            args.output_dir,
            args.seed,
            args.max_transitions,
            args.max_explanations,
            not args.omit_grids,
        )
        for game in games
    ]
    result = run_matched(jobs, args.workers)
    if args.verify_workers and args.workers > 1:
        serial = run_matched(jobs, 1)
        parallel_games = result["games"]
        if serial["games"] != parallel_games:
            raise RuntimeError("workers=1 and parallel game results differ")
        result["worker_equivalence"] = {
            "serial_workers": 1,
            "parallel_workers": args.workers,
            "identical": True,
        }
    else:
        result["worker_equivalence"] = None
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
