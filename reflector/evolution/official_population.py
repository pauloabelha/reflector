"""Parallel official-game rounds for reproducible symbolic strategy genomes."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from ..core.mind import MindConfig
from ..kaggle import OVERLAY_FILES
from .population import Candidate


@dataclass(frozen=True, slots=True)
class SymbolicStrategy:
    """One operative, one-factor strategy variation and its falsifier."""

    name: str
    field: str | None
    value: bool | int | float | None
    rationale: str
    falsifier: str
    candidate: Candidate

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "field": self.field,
            "value": self.value,
            "rationale": self.rationale,
            "falsifier": self.falsifier,
            "candidate": self.candidate.to_dict(),
        }


@dataclass(frozen=True, slots=True)
class OfficialRunOutcome:
    strategy: SymbolicStrategy
    rerun: int
    report: dict[str, Any]
    report_sha256: str

    def to_dict(self) -> dict[str, Any]:
        scorecard = self.report["scorecard"]
        return {
            "strategy": self.strategy.name,
            "candidate_id": self.strategy.candidate.candidate_id,
            "rerun": self.rerun,
            "report_sha256": self.report_sha256,
            "source_commit": self.report["source_commit"],
            "score": scorecard["score"],
            "total_levels_completed": scorecard["total_levels_completed"],
            "total_actions": scorecard["total_actions"],
            "games": {
                environment["id"].split("-", 1)[0]: {
                    "levels_completed": environment["levels_completed"],
                    "actions": environment["actions"],
                    "score": environment["score"],
                    "completed": environment["completed"],
                    "level_actions": environment["runs"][0]["level_actions"],
                }
                for environment in scorecard["environments"]
            },
        }


@dataclass(frozen=True, slots=True)
class InheritedTrait:
    field: str
    value: bool | int | float
    donor_id: str
    control_id: str
    evidence_scope: tuple[str, ...]
    evidence_sha256: str
    score_delta: float
    levels_delta: int
    deterministic_reruns: int

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["evidence_scope"] = list(self.evidence_scope)
        return value


@dataclass(frozen=True, slots=True)
class OfficialPopulationRound:
    strategies: tuple[SymbolicStrategy, ...]
    outcomes: tuple[OfficialRunOutcome, ...]
    inherited_traits: tuple[InheritedTrait, ...]
    offspring: Candidate | None
    max_workers: int
    reruns: int
    cognitive_stream_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": "local-official-population-experiment",
            "claim_boundary": (
                "Parallel local development evidence; not a full-suite accepted "
                "score and not a Kaggle leaderboard score."
            ),
            "max_workers": self.max_workers,
            "reruns": self.reruns,
            "cognitive_stream_dir": self.cognitive_stream_dir,
            "strategies": [item.to_dict() for item in self.strategies],
            "outcomes": [item.to_dict() for item in self.outcomes],
            "inherited_traits": [
                item.to_dict() for item in self.inherited_traits
            ],
            "offspring": (
                self.offspring.to_dict() if self.offspring is not None else None
            ),
            "offspring_status": (
                "created from deterministic positive non-regressive traits"
                if self.offspring is not None
                else "not created; no variation passed the inheritance gate"
            ),
        }


def inference_fingerprint(project_root: Path) -> str:
    """Hash the exact inference overlay source independently of Git state."""

    digest = hashlib.sha256()
    for relative in sorted(OVERLAY_FILES):
        path = project_root / relative
        digest.update(relative.encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def operative_strategy_population(
    parent: Candidate,
    *,
    source_fingerprint: str,
) -> tuple[SymbolicStrategy, ...]:
    """Create a control plus three coordinate-free operative variations."""

    definitions = (
        (
            "action-family-fairness",
            "enable_hierarchical_action_fairness",
            True,
            "Balance trials across legal action families before repeating them.",
            "Reject if it regresses any control completion or fails to improve "
            "levels or equal-budget official score.",
        ),
        (
            "successful-structural-replay",
            "enable_successful_role_replay",
            True,
            "Replay a completed level's coordinate-free action-role program.",
            "Reject if replay fails to improve a later level or regresses any "
            "control completion.",
        ),
        (
            "productive-role-reuse",
            "enable_productive_role_reuse",
            True,
            "Prefer object-role interventions with observed productive effects.",
            "Reject if role reuse fails to improve levels or equal-budget score "
            "without a control regression.",
        ),
        (
            "constraint-first-structural-replay",
            "enable_constraint_first_role_replay",
            True,
            "Repair active evidenced relations before replaying a completed "
            "level's coordinate-free action-role program.",
            "Reject if constraint-first replay fails to improve levels or "
            "equal-budget score without a control regression.",
        ),
    )
    control = Candidate.create(
        parent.config,
        parent_id=parent.candidate_id,
        generation=parent.generation + 1,
        rationale="Frozen control for the parallel symbolic strategy round.",
        mutation_source="collective-control-v1",
        inference_fingerprint=source_fingerprint,
    )
    output = [
        SymbolicStrategy(
            "relation-repair-control",
            None,
            None,
            "Retain the parent's evidenced relation-repair arbitration.",
            "The control is falsified as a baseline if deterministic reruns differ.",
            control,
        )
    ]
    for name, field, value, rationale, falsifier in definitions:
        config = parent.config.to_dict()
        if config[field] == value:
            raise ValueError(
                f"strategy field {field} already has the proposed value"
            )
        config[field] = value
        candidate = Candidate.create(
            MindConfig.from_dict(config),
            parent_id=parent.candidate_id,
            generation=parent.generation + 1,
            rationale=rationale,
            mutation_source=f"symbolic-strategy:{name}",
            inference_fingerprint=source_fingerprint,
        )
        output.append(
            SymbolicStrategy(
                name,
                field,
                value,
                rationale,
                falsifier,
                candidate,
            )
        )
    return tuple(output)


def _canonical_report_hash(report: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            report, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    ).hexdigest()


def _outcome_signature(outcome: OfficialRunOutcome) -> tuple[Any, ...]:
    scorecard = outcome.report["scorecard"]
    return (
        scorecard["score"],
        scorecard["total_levels_completed"],
        scorecard["total_actions"],
        tuple(
            (
                environment["id"].split("-", 1)[0],
                environment["levels_completed"],
                environment["actions"],
                environment["score"],
                tuple(environment["runs"][0]["level_actions"]),
            )
            for environment in scorecard["environments"]
        ),
    )


def _run_one(
    *,
    strategy: SymbolicStrategy,
    rerun: int,
    games: tuple[str, ...],
    environments_dir: Path,
    recordings_root: Path,
    project_root: Path,
    timeout: float,
    cognitive_stream_root: Path | None,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> OfficialRunOutcome:
    candidate_dir = recordings_root / strategy.candidate.candidate_id
    candidate_dir.mkdir(parents=True, exist_ok=True)
    config_path = candidate_dir / f"candidate-rerun-{rerun}.json"
    config_path.write_text(
        json.dumps(strategy.candidate.to_dict(), sort_keys=True),
        encoding="utf-8",
    )
    command = [
        sys.executable,
        "-m",
        "reflector.cli",
        "official-isolated-run",
        *games,
        "--environments-dir",
        str(environments_dir),
        "--recordings-dir",
        str(candidate_dir / f"rerun-{rerun}"),
        "--config",
        str(config_path),
        "--no-recordings",
        "--lightweight",
    ]
    if cognitive_stream_root is not None:
        command.extend(
            (
                "--cognitive-stream-dir",
                str(
                    cognitive_stream_root
                    / strategy.candidate.candidate_id
                    / f"rerun-{rerun}"
                ),
            )
        )
    completed = command_runner(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"official strategy run failed for {strategy.name} rerun {rerun}: "
            f"{completed.stderr.strip() or completed.stdout.strip()}"
        )
    report = json.loads(completed.stdout)
    expected_config = strategy.candidate.config.to_dict()
    if any(agent["mind_config"] != expected_config for agent in report["agents"]):
        raise RuntimeError(
            f"configuration cross-talk detected for {strategy.name}"
        )
    reported_games = tuple(sorted(agent["game_id"] for agent in report["agents"]))
    if reported_games != tuple(sorted(games)):
        raise RuntimeError(
            f"incomplete official outcome for {strategy.name}: {reported_games}"
        )
    return OfficialRunOutcome(
        strategy,
        rerun,
        report,
        _canonical_report_hash(report),
    )


def _qualifying_traits(
    strategies: tuple[SymbolicStrategy, ...],
    outcomes: tuple[OfficialRunOutcome, ...],
    reruns: int,
) -> tuple[InheritedTrait, ...]:
    grouped = {
        strategy.name: tuple(
            outcome
            for outcome in outcomes
            if outcome.strategy.name == strategy.name
        )
        for strategy in strategies
    }
    for name, runs in grouped.items():
        if len(runs) != reruns or len({_outcome_signature(run) for run in runs}) != 1:
            raise RuntimeError(f"nondeterministic official reruns for {name}")
    control_strategy = strategies[0]
    control_runs = grouped[control_strategy.name]
    control = control_runs[0].to_dict()
    control_games = control["games"]
    traits: list[InheritedTrait] = []
    for strategy in strategies[1:]:
        if strategy.field is None or strategy.value is None:
            continue
        candidate_runs = grouped[strategy.name]
        candidate = candidate_runs[0].to_dict()
        candidate_games = candidate["games"]
        nonregressive = all(
            candidate_games[game]["levels_completed"]
            >= control_games[game]["levels_completed"]
            for game in control_games
        )
        levels_delta = (
            candidate["total_levels_completed"] - control["total_levels_completed"]
        )
        score_delta = candidate["score"] - control["score"]
        if not nonregressive or not (
            levels_delta > 0 or (levels_delta == 0 and score_delta > 0)
        ):
            continue
        evidence_hash = hashlib.sha256(
            "".join(run.report_sha256 for run in candidate_runs).encode()
        ).hexdigest()
        traits.append(
            InheritedTrait(
                field=strategy.field,
                value=strategy.value,
                donor_id=strategy.candidate.candidate_id,
                control_id=control_strategy.candidate.candidate_id,
                evidence_scope=tuple(sorted(control_games)),
                evidence_sha256=evidence_hash,
                score_delta=score_delta,
                levels_delta=levels_delta,
                deterministic_reruns=reruns,
            )
        )
    return tuple(sorted(traits, key=lambda item: item.field))


def _breed_one(
    strategies: tuple[SymbolicStrategy, ...],
    traits: tuple[InheritedTrait, ...],
    source_fingerprint: str,
) -> Candidate | None:
    if not traits:
        return None
    control = strategies[0].candidate
    config = control.config.to_dict()
    donors = {trait.donor_id for trait in traits}
    for trait in traits:
        config[trait.field] = trait.value
    contributor_ids = tuple(sorted({control.candidate_id, *donors}))
    return Candidate.create(
        MindConfig.from_dict(config),
        parent_id=control.candidate_id,
        contributor_ids=contributor_ids,
        generation=max(strategy.candidate.generation for strategy in strategies)
        + 1,
        rationale=(
            "Combine only deterministic, positive, non-regressive operative "
            "strategy traits from the completed official round."
        ),
        mutation_source="deterministic-symbolic-breeding-v1",
        inference_fingerprint=source_fingerprint,
    )


def run_official_population_round(
    *,
    parent: Candidate,
    games: Iterable[str],
    environments_dir: Path,
    project_root: Path,
    max_workers: int = 4,
    reruns: int = 2,
    timeout: float = 1800.0,
    cognitive_stream_dir: Path | None = None,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> OfficialPopulationRound:
    """Run isolated candidate swarms concurrently, then breed one gated child."""

    selected_games = tuple(sorted(set(games)))
    if not selected_games:
        raise ValueError("official population round requires at least one game")
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    if reruns < 2:
        raise ValueError("inheritance requires at least two deterministic reruns")
    source_fingerprint = inference_fingerprint(project_root)
    strategies = operative_strategy_population(
        parent,
        source_fingerprint=source_fingerprint,
    )
    tasks = tuple(
        (strategy, rerun)
        for strategy in strategies
        for rerun in range(1, reruns + 1)
    )
    with tempfile.TemporaryDirectory(
        prefix="reflector-official-population-"
    ) as temporary:
        recordings_root = Path(temporary)
        with ThreadPoolExecutor(max_workers=min(max_workers, len(tasks))) as pool:
            futures = [
                pool.submit(
                    _run_one,
                    strategy=strategy,
                    rerun=rerun,
                    games=selected_games,
                    environments_dir=environments_dir.resolve(),
                    recordings_root=recordings_root,
                    project_root=project_root.resolve(),
                    timeout=timeout,
                    cognitive_stream_root=(
                        cognitive_stream_dir.resolve()
                        if cognitive_stream_dir is not None
                        else None
                    ),
                    command_runner=command_runner,
                )
                for strategy, rerun in tasks
            ]
            outcomes = tuple(future.result() for future in futures)
    outcomes = tuple(
        sorted(
            outcomes,
            key=lambda item: (item.strategy.name, item.rerun),
        )
    )
    traits = _qualifying_traits(strategies, outcomes, reruns)
    offspring = _breed_one(strategies, traits, source_fingerprint)
    return OfficialPopulationRound(
        strategies,
        outcomes,
        traits,
        offspring,
        min(max_workers, len(tasks)),
        reruns,
        (
            str(cognitive_stream_dir.resolve())
            if cognitive_stream_dir is not None
            else None
        ),
    )
