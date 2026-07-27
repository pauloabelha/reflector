"""Development-time evaluation over traces produced by the deployed package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import partial
from typing import Any, Callable

from .compression import analyze_redundancy, counterfactual_replay
from .mind import MindConfig
from .policy import SymbolicPolicy
from .trace import EpisodeTrace


@dataclass(frozen=True, slots=True)
class TraceMetrics:
    actions: int
    resets: int
    transitions: int
    levels_advanced: int
    failed_experiments: int
    schema_count: int
    concept_count: int
    causal_hypotheses: int
    temporal_hypotheses: int
    mean_schema_reliability: float
    schema_description_length: int
    planner_expansions: int
    recoverable_redundancy: int
    counterfactual_replay_savings: int
    deterministic_replay_rate: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_trace(
    trace: EpisodeTrace,
    policy_factory: Callable[[], SymbolicPolicy] = SymbolicPolicy,
) -> TraceMetrics:
    policy = policy_factory()
    matches = 0
    resets = 0
    transitions = 0
    levels_advanced = 0
    failed_experiments = 0
    for step in trace.steps:
        decision = policy.choose_action(step.observation)
        matches += int(decision == step.decision)
        resets += int(step.decision.action_id == 0)
        if step.incoming_transition is not None:
            transitions += 1
            kinds = {event.kind for event in step.incoming_transition.result}
            levels_advanced += int("level_advanced" in kinds)
            failed_experiments += int(kinds == {"no_observed_change"})

    if trace.terminal_observation is not None:
        policy.observe(trace.terminal_observation)
    if trace.terminal_transition is not None:
        transitions += 1
        terminal_kinds = {event.kind for event in trace.terminal_transition.result}
        levels_advanced += int("level_advanced" in terminal_kinds)
        failed_experiments += int(terminal_kinds == {"no_observed_change"})

    schemas = tuple(policy.mind.schemas.schemas.values())
    reliability = (
        sum(schema.reliability for schema in schemas) / len(schemas)
        if schemas
        else 0.0
    )
    description_length = sum(
        len(atom.text())
        for schema in schemas
        for atom in schema.context
    ) + sum(len(result) for schema in schemas for result in schema.result)
    redundancy = analyze_redundancy(trace, policy)
    counterfactual_savings = sum(
        max(0, item.net_utility)
        for item in counterfactual_replay(trace, policy)
    )
    return TraceMetrics(
        actions=len(trace.steps),
        resets=resets,
        transitions=transitions,
        levels_advanced=levels_advanced,
        failed_experiments=failed_experiments,
        schema_count=len(schemas),
        concept_count=len(policy.mind.concepts.concepts),
        causal_hypotheses=len(policy.mind.hypotheses.causal),
        temporal_hypotheses=len(policy.mind.hypotheses.temporal),
        mean_schema_reliability=reliability,
        schema_description_length=description_length,
        planner_expansions=sum(
            step.planner_expansions for step in policy.trace.steps
        ),
        recoverable_redundancy=redundancy.recoverable_redundancy,
        counterfactual_replay_savings=counterfactual_savings,
        deterministic_replay_rate=matches / len(trace.steps) if trace.steps else 1.0,
    )


def compare_traces(
    traces: dict[str, EpisodeTrace],
) -> dict[str, dict[str, Any]]:
    return {
        name: evaluate_trace(trace).to_dict()
        for name, trace in sorted(traces.items())
    }


ABLATIONS: dict[str, MindConfig] = {
    "full": MindConfig(),
    "no_synthetic_concepts": MindConfig(enable_concepts=False),
    "no_counterfactual_replay": MindConfig(
        enable_counterfactual_pressure=False
    ),
    "no_schema_complexity_pressure": MindConfig(
        enable_schema_complexity_pressure=False
    ),
    "no_experiments": MindConfig(enable_experiments=False),
    "no_planning": MindConfig(enable_planning=False),
}


def evaluate_ablations(trace: EpisodeTrace) -> dict[str, dict[str, Any]]:
    return {
        name: evaluate_trace(
            trace, policy_factory=partial(SymbolicPolicy, config)
        ).to_dict()
        for name, config in ABLATIONS.items()
    }
