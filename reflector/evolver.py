"""Population evaluation over the exact symbolic policy shipped to Kaggle."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .experiments import ExperimentManifest, ExperimentStore
from .mind import MindConfig
from .mutations import MutationProvider
from .population import Candidate, Fitness, pareto_archive
from .sandbox import ValidationReport, validate_candidate
from .trace import EpisodeTrace
from .transforms import transformed_holdouts


@dataclass(frozen=True, slots=True)
class EvolutionResult:
    manifest: ExperimentManifest
    evaluated: tuple[tuple[Candidate, Fitness], ...]
    archive: tuple[tuple[Candidate, Fitness], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest.to_dict(),
            "evaluated": [
                {"candidate": candidate.to_dict(), "fitness": fitness.to_dict()}
                for candidate, fitness in self.evaluated
            ],
            "pareto_archive": [
                {"candidate": candidate.to_dict(), "fitness": fitness.to_dict()}
                for candidate, fitness in self.archive
            ],
        }


def descendants(
    parent: Candidate,
    providers: Iterable[MutationProvider],
    feedback: dict[str, Any],
) -> tuple[Candidate, ...]:
    output = []
    for provider in providers:
        proposal = provider.propose(parent.config, feedback)
        output.append(
            Candidate.create(
                proposal.apply(parent.config),
                parent_id=parent.candidate_id,
                generation=parent.generation + 1,
                rationale=proposal.rationale,
            )
        )
    return tuple(output)


def run_experiment(
    *,
    name: str,
    seed: int,
    traces: dict[str, EpisodeTrace],
    candidates: Iterable[Candidate],
    store: ExperimentStore,
    holdout_seeds: tuple[int, ...] = (101, 211),
    network_disabled: bool = True,
) -> EvolutionResult:
    manifest = ExperimentManifest.create(
        name, seed, traces, holdout_seeds=holdout_seeds
    )
    store.save_manifest(manifest)
    evaluation_traces = {
        **dict(sorted(traces.items())),
        **transformed_holdouts(traces, holdout_seeds),
    }
    evaluated: list[tuple[Candidate, Fitness]] = []
    for candidate in candidates:
        report: ValidationReport = validate_candidate(
            candidate.config,
            evaluation_traces,
            network_disabled=network_disabled,
        )
        store.save_candidate(manifest.experiment_id, candidate)
        store.save_evaluation(
            manifest.experiment_id,
            candidate.candidate_id,
            report.fitness,
            {
                "traces": report.details,
                "deterministic": report.deterministic,
                "network_isolated": report.network_isolated,
            },
        )
        evaluated.append((candidate, report.fitness))
    result = tuple(evaluated)
    return EvolutionResult(manifest, result, pareto_archive(result))


def root_candidate(config: MindConfig | None = None) -> Candidate:
    return Candidate.create(config or MindConfig())
