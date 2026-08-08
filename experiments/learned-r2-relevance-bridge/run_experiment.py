#!/usr/bin/env python3
"""Preregistered offline screen and optional four-arm public intervention."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Callable, Sequence, cast

from reflector2.arc_harness import (
    ArcGameSession,
    ArcadeTransport,
    JsonlTrace,
    _derived_seed,
    _official_arcade,
    _score_by_game,
    run_suite,
)
from reflector2.explanation_experiment import ordered_process_map
from reflector2.explanations import (
    ExplanationConfig,
    ExplanationDecision,
    ExplanationEngine,
)
from reflector2.perception import PerceptionBatch
from reflector2.runtime import Runtime, Workspace

from relevance import (
    EffectAtom,
    EvidenceRecord,
    RelevanceBridge,
    RelevanceConfig,
    RelevanceSnapshot,
    read_evidence,
    run_offline_controls,
    stable_hash,
    structural_binding_key,
)


FROZEN_POLICIES = ("random", "local-schema", "explanation")
ARM4 = "explanation+learned-relevance"
POLICIES = (*FROZEN_POLICIES, ARM4)


def verify_frozen_arms() -> dict[str, Any]:
    experiment_dir = Path(__file__).resolve().parent
    repository = experiment_dir.parents[1]
    manifest = json.loads(
        (experiment_dir / "frozen-arms.json").read_text(encoding="utf-8")
    )
    mismatches = []
    for relative, expected in sorted(manifest["files"].items()):
        path = repository / relative
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            mismatches.append(
                {"path": relative, "expected": expected, "actual": actual}
            )
    if mismatches:
        raise RuntimeError(
            "frozen arm source changed: "
            + ", ".join(item["path"] for item in mismatches)
        )
    return {
        "branch": manifest["branch"],
        "commit": manifest["commit"],
        "verified_files": len(manifest["files"]),
        "source_hashes_match": True,
    }


@dataclass(frozen=True, slots=True)
class LiveJob:
    game_id: str
    environments_dir: Path
    output_dir: Path
    seed: int
    max_transitions: int
    max_explanations: int
    include_grids: bool
    snapshot: RelevanceSnapshot


class DelayedCommitExplanationEngine(ExplanationEngine):
    """Identical frozen ranking with commitment delayed until arm 4 selects."""

    def _commit_selected(
        self, decision: ExplanationDecision, observed: PerceptionBatch
    ) -> None:
        return None

    def commit_executed(
        self, decision: ExplanationDecision, observed: PerceptionBatch
    ) -> None:
        super()._commit_selected(decision, observed)


@dataclass(slots=True)
class Arm4Decision:
    selected_action_id: int
    frozen_explanation: ExplanationDecision
    executed_explanation: ExplanationDecision
    relevance: Any


def _binding_key(
    engine: ExplanationEngine,
    prediction: Any,
    observed: PerceptionBatch,
    decision_id: int,
) -> str:
    assignments = engine._projection_assignments(  # noqa: SLF001 - audit wrapper
        prediction.schema_id, observed, decision_id
    )
    decoded: list[tuple[str, object]] = []
    for head, arguments in engine.runtime.graph.source_atoms(prediction.schema_id):
        if head != "Before" or len(arguments) != 3:
            continue
        _carrier, relation, value = arguments
        if not isinstance(value, str) or not value.startswith("?v"):
            continue
        term_id = (assignments or {}).get(int(value[2:]))
        if term_id is not None:
            decoded.append(
                (str(relation), engine.runtime.graph.terms.value(term_id))
            )
    return structural_binding_key(prediction.signature, decoded)


class Arm4Controller:
    """Compose frozen explanations with an isolated frozen relevance bridge."""

    def __init__(
        self,
        runtime: Runtime,
        snapshot: RelevanceSnapshot,
        explanation_config: ExplanationConfig,
        report_group: str,
    ) -> None:
        self.explanation = DelayedCommitExplanationEngine(
            runtime, explanation_config
        )
        self.bridge = RelevanceBridge(snapshot)
        self.report_group = report_group

    def decide(
        self,
        *,
        mode: str,
        workspace: Workspace,
        observed: PerceptionBatch,
        legal_action_ids: Sequence[int],
        baseline_action_id: int,
    ) -> Arm4Decision:
        if mode != "explanation":
            raise ValueError("arm 4 must wrap the frozen explanation mode")
        frozen = self.explanation.decide(
            mode="explanation",
            workspace=workspace,
            observed=observed,
            legal_action_ids=legal_action_ids,
            baseline_action_id=baseline_action_id,
        )
        transition_hashes = {
            index: self.explanation.runtime.graph.canonical_hash[prediction.schema_id]
            for index, prediction in enumerate(frozen.predictions)
        }
        binding_keys = {
            index: _binding_key(
                self.explanation, prediction, observed, frozen.decision_id
            )
            for index, prediction in enumerate(frozen.predictions)
        }
        relevance = self.bridge.decide(
            frozen,
            transition_hashes=transition_hashes,
            binding_keys=binding_keys,
        )
        selected_rank = next(
            item
            for item in frozen.rankings
            if item.action_id == relevance.selected_action_id
        )
        executed = replace(
            frozen,
            selected_action_id=relevance.selected_action_id,
            shadow_by_explanation={},
            changed_top_action=relevance.selected_action_id != baseline_action_id,
            selected_for_discrimination=selected_rank.discrimination > 0.0,
        )
        self.explanation.commit_executed(executed, observed)
        return Arm4Decision(
            relevance.selected_action_id, frozen, executed, relevance
        )

    def decision_trace(self, decision: Arm4Decision) -> dict[str, Any]:
        return {
            "event": "explanation-plus-learned-relevance-decision",
            "frozen_explanation": self.explanation.decision_trace(
                decision.frozen_explanation
            ),
            "learned_relevance": self.bridge.decision_trace(decision.relevance),
            "selected": decision.selected_action_id,
        }

    def observe_outcome(
        self,
        decision: Arm4Decision | None,
        *,
        before: PerceptionBatch,
        after: PerceptionBatch,
        observed_schema_id: int,
        progress_delta: float,
        reward: float | None,
    ) -> dict[str, Any] | None:
        if decision is None:
            return None
        explanation_resolution = self.explanation.observe_outcome(
            decision.executed_explanation,
            before=before,
            after=after,
            observed_schema_id=observed_schema_id,
            progress_delta=progress_delta,
            reward=reward,
        )
        observed_effects: tuple[EffectAtom, ...] = tuple(
            self.explanation._effect_signature(observed_schema_id)  # noqa: SLF001
        )
        relevance_resolution = None
        if decision.relevance.commitments:
            relevance_resolution = self.bridge.observe_outcome(
                decision.relevance,
                observed_effects=observed_effects,
                progress_delta=progress_delta,
                report_group=self.report_group,
            )
        return {
            "event": "explanation-plus-learned-relevance-resolution",
            "explanation": explanation_resolution,
            "learned_relevance": relevance_resolution,
        }

    def reset_episode(self) -> None:
        self.explanation.reset_episode()

    def report(self) -> dict[str, Any]:
        return {
            "frozen_explanation_mechanism": self.explanation.report(),
            "learned_relevance": self.bridge.report(),
            "relevance_runtime": self.bridge.runtime.report(),
        }


def _run_arm4(job: LiveJob) -> dict[str, Any]:
    root = job.output_dir / "runs" / job.game_id / ARM4
    arcade, action_from_id = _official_arcade(
        job.environments_dir, root / "recordings"
    )
    card_id = arcade.open_scorecard(
        tags=["reflector2", ARM4, f"seed-{job.seed}"]
    )
    runtime = Runtime()
    trace = JsonlTrace(root / "traces" / f"{job.game_id}.trace.jsonl")
    environment_seed = _derived_seed(job.seed, job.game_id, "environment")
    random_seed = _derived_seed(job.seed, job.game_id, "actions")
    try:
        environment = arcade.make(
            job.game_id,
            seed=environment_seed,
            scorecard_id=card_id,
            include_frame_data=True,
        )
        if environment is None:
            raise RuntimeError(f"{job.game_id}: environment did not load")
        session = ArcGameSession(
            cast(Any, environment),
            requested_game_id=job.game_id,
            runtime=runtime,
            random_seed=random_seed,
            environment_seed=environment_seed,
            max_transitions=job.max_transitions,
            trace=trace,
            action_from_id=action_from_id,
            include_grids=job.include_grids,
            policy="explanation",
            explanation_config=ExplanationConfig(
                max_explanations=job.max_explanations
            ),
        )
        controller = Arm4Controller(
            runtime,
            job.snapshot,
            ExplanationConfig(max_explanations=job.max_explanations),
            job.game_id,
        )
        session.explanations = cast(Any, controller)
        result = session.run().to_dict()
    finally:
        scorecard = arcade.close_scorecard(card_id)
    result["score"] = _score_by_game(scorecard).get(result["game_id"])
    result["runtime"]["policy"] = ARM4
    r2_path = root / "traces" / f"{job.game_id}.r2.jsonl"
    r2_path.parent.mkdir(parents=True, exist_ok=True)
    with r2_path.open("w", encoding="utf-8") as stream:
        for event in runtime.trace:
            stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
            stream.write("\n")
    relevance_path = root / "traces" / f"{job.game_id}.relevance.r2.jsonl"
    with relevance_path.open("w", encoding="utf-8") as stream:
        for event in controller.bridge.runtime.trace:
            stream.write(json.dumps(event, sort_keys=True, separators=(",", ":")))
            stream.write("\n")
    return result


def _run_live_game(job: LiveJob) -> dict[str, Any]:
    policies: dict[str, Any] = {}
    for policy in FROZEN_POLICIES:
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
        policies[policy] = summary["games"][0]
    policies[ARM4] = _run_arm4(job)
    return {"game_id": job.game_id, "policies": policies}


def _policy_metrics(games: Sequence[dict[str, Any]], policy: str) -> dict[str, Any]:
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
    }


def _aggregate_relevance(games: Sequence[dict[str, Any]]) -> dict[str, Any]:
    reports = [
        game["policies"][ARM4]["runtime"]["explanations"]["learned_relevance"]
        for game in games
    ]
    sums = {
        key: sum(int(report[key]) for report in reports)
        for key in (
            "decisions",
            "covered_decisions",
            "promoted_schema_matches",
            "prospective_progress_commitments",
            "reifications",
            "refutations",
            "arm4_action_changes",
            "positive_progress_after_changes",
            "regressions_after_changes",
            "level_completions_after_changes",
        )
    }
    changes = sums["arm4_action_changes"]
    changes_by_game = [int(report["arm4_action_changes"]) for report in reports]
    transfer = {
        name: sum(
            int(report["successful_transfer_classes"][name]) for report in reports
        )
        for name in (
            "exact-previous-consequence-binding",
            "different-binding-same-consequence-schema",
            "structurally-related-or-composed-consequence",
        )
    }
    calibration = [
        pair for report in reports for pair in report.get("calibration", [])
    ]
    return {
        **sums,
        "promoted_relevance_schemas": max(
            (int(report["promoted_relevance_schemas"]) for report in reports),
            default=0,
        ),
        "bridge_coverage": (
            sums["covered_decisions"] / sums["decisions"]
            if sums["decisions"]
            else 0.0
        ),
        "bridge_precision": (
            sums["positive_progress_after_changes"] / changes if changes else None
        ),
        "regression_rate": (
            sums["regressions_after_changes"] / changes if changes else None
        ),
        "brier_score": (
            sum((float(probability) - int(actual)) ** 2 for probability, actual in calibration)
            / len(calibration)
            if calibration
            else None
        ),
        "successful_transfer_classes": transfer,
        "games_with_action_change": sum(value > 0 for value in changes_by_game),
        "max_game_action_change_share": (
            max(changes_by_game, default=0) / changes if changes else None
        ),
    }


def aggregate_live(games: Sequence[dict[str, Any]]) -> dict[str, Any]:
    controls = {policy: _policy_metrics(games, policy) for policy in POLICIES}
    return {
        "controls": controls,
        "learned_relevance": _aggregate_relevance(games),
        "arm4_vs_frozen_explanation": {
            key: controls[ARM4][key] - controls["explanation"][key]
            for key in ("score", "total_progress", "completed_levels")
        },
    }


def _null_advantage(real: Any, null: Any) -> bool:
    real_value = real["prospective_positive_precision"]
    null_value = null["prospective_positive_precision"]
    precision_better = real_value is not None and (
        null_value is None or float(real_value) >= float(null_value) + 0.10
    )
    real_brier = real["brier_score"]
    null_brier = null["brier_score"]
    calibration_better = real_brier is not None and (
        null_brier is None or float(real_brier) + 0.01 <= float(null_brier)
    )
    return precision_better and calibration_better


def experimental_verdict(
    *,
    snapshot: RelevanceSnapshot,
    offline: dict[str, Any],
    live: dict[str, Any] | None,
    deterministic_replay: bool,
) -> tuple[str, dict[str, bool]]:
    evaluations = offline["evaluations"]
    relevance = None if live is None else live["aggregate"]["learned_relevance"]
    gates = {
        "formed_from_past_observed_pairs": bool(snapshot.schemas),
        "prospective_held_out_predictions": bool(
            evaluations["real"]["covered_events"]
        ),
        "changed_actions_vs_frozen_explanation": bool(
            relevance and relevance["arm4_action_changes"]
        ),
        "positive_behavioral_advantage": bool(
            relevance
            and relevance["bridge_precision"] is not None
            and relevance["bridge_precision"] > 0.0
        ),
        "beats_reward_label_permutation": _null_advantage(
            evaluations["real"], evaluations["null_a"]
        ),
        "beats_consequence_pairing_permutation": _null_advantage(
            evaluations["real"], evaluations["null_b"]
        ),
        "not_one_game_concentrated": bool(
            relevance
            and relevance["games_with_action_change"] > 1
            and relevance["max_game_action_change_share"] < 1.0
        ),
        "deterministic_replay": deterministic_replay,
    }
    if all(gates.values()):
        verdict = "PROMOTE"
    elif relevance and relevance["arm4_action_changes"] >= 10 and not relevance["positive_progress_after_changes"]:
        verdict = "REJECT"
    else:
        verdict = "CONTINUE-DIAGNOSTIC"
    return verdict, gates


def _jsonable_offline(result: dict[str, Any]) -> dict[str, Any]:
    return {
        **{key: value for key, value in result.items() if key != "snapshot"},
        "snapshot": result["snapshot"].to_dict(),
    }


def _parse_games(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(
        item.strip() for value in values for item in value.split(",") if item.strip()
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--learning-stream", type=Path, required=True)
    parser.add_argument("--held-out-stream", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/learned-r2-relevance-bridge/run"),
    )
    parser.add_argument("--run-live", action="store_true")
    parser.add_argument("--verify-live-replay", action="store_true")
    parser.add_argument("--environments-dir", type=Path, default=Path("environment_files"))
    parser.add_argument("--game", action="append", default=[])
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-transitions", type=int, default=80)
    parser.add_argument("--max-explanations", type=int, default=8)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--omit-grids", action="store_true")
    parser.add_argument("--minimum-confidence", type=float, default=2.0 / 3.0)
    parser.add_argument("--relevance-weight", type=float, default=1.0)
    parser.add_argument("--permutation-seed", type=int, default=1729)
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    if args.max_transitions < 0:
        raise SystemExit("--max-transitions must be non-negative")
    if args.verify_live_replay and not args.run_live:
        raise SystemExit("--verify-live-replay requires --run-live")
    frozen_arms = verify_frozen_arms()
    learning = read_evidence(args.learning_stream)
    held_out = read_evidence(args.held_out_stream)
    overlap = {item.event_id for item in learning} & {
        item.event_id for item in held_out
    }
    if overlap:
        raise SystemExit(
            f"learning/held-out leakage: {len(overlap)} event IDs overlap"
        )
    config = RelevanceConfig(
        minimum_confidence=args.minimum_confidence,
        relevance_weight=args.relevance_weight,
        permutation_seed=args.permutation_seed,
    )
    offline_raw = run_offline_controls(learning, held_out, config)
    snapshot = offline_raw["snapshot"]
    offline = _jsonable_offline(offline_raw)
    # The offline evaluation is executed twice from immutable inputs.  This is
    # cheap and is always required; live replay remains explicit because every
    # public action is expensive.
    offline_replay = _jsonable_offline(
        run_offline_controls(learning, held_out, config)
    )
    if offline_replay != offline:
        raise RuntimeError("offline deterministic replay diverged")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    snapshot_output_path = args.output_dir / "frozen-relevance-schemas.json"
    snapshot.write(snapshot_output_path)
    live: dict[str, Any] | None = None
    live_replay_identical = False
    if args.run_live:
        games = _parse_games(args.game)
        if not games:
            raise SystemExit("--run-live requires at least one --game")
        jobs = tuple(
            LiveJob(
                game_id,
                args.environments_dir,
                args.output_dir / "live",
                args.seed,
                args.max_transitions,
                args.max_explanations,
                not args.omit_grids,
                snapshot,
            )
            for game_id in games
        )
        game_results = ordered_process_map(_run_live_game, jobs, args.workers)
        live = {
            "config": {
                "games": list(games),
                "seed": args.seed,
                "max_transitions": args.max_transitions,
                "max_explanations": args.max_explanations,
                "workers": args.workers,
                "policies": list(POLICIES),
            },
            "aggregate": aggregate_live(game_results),
            "games": game_results,
        }
        if args.verify_live_replay:
            replay_jobs = tuple(
                replace(job, output_dir=args.output_dir / "live-replay")
                for job in jobs
            )
            replay_games = ordered_process_map(_run_live_game, replay_jobs, 1)
            live_replay_identical = replay_games == game_results
            if not live_replay_identical:
                raise RuntimeError("live deterministic replay diverged")

    deterministic_replay = True if live is None else live_replay_identical
    verdict, gates = experimental_verdict(
        snapshot=snapshot,
        offline=offline,
        live=live,
        deterministic_replay=deterministic_replay,
    )
    result = {
        "experiment": "learned-r2-relevance-bridge",
        "frozen_arms": frozen_arms,
        "preregistered_policies": list(POLICIES),
        "learning_cutoff": {
            "event_count": snapshot.training_events,
            "event_digest": snapshot.training_event_digest,
            "held_out_event_count": len(held_out),
            "overlapping_event_ids": 0,
        },
        "offline": offline,
        "offline_deterministic_replay": True,
        "live": live,
        "live_deterministic_replay": (
            live_replay_identical if args.run_live else None
        ),
        "promotion_gates": gates,
        "verdict": verdict,
    }
    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "experiment": result["experiment"],
                "summary_path": str(summary_path),
                "frozen_snapshot_path": str(snapshot_output_path),
                "learning_cutoff": result["learning_cutoff"],
                "offline_metrics": {
                    name: {
                        key: value
                        for key, value in evaluation.items()
                        if key != "forecasts"
                    }
                    for name, evaluation in result["offline"]["evaluations"].items()
                },
                "offline_deterministic_replay": result[
                    "offline_deterministic_replay"
                ],
                "promotion_gates": result["promotion_gates"],
                "verdict": result["verdict"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
