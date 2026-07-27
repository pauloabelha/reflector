"""Development-time evaluation over traces produced by the deployed package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Callable

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
    mean_schema_reliability: float
    schema_description_length: int
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
    return TraceMetrics(
        actions=len(trace.steps),
        resets=resets,
        transitions=transitions,
        levels_advanced=levels_advanced,
        failed_experiments=failed_experiments,
        schema_count=len(schemas),
        concept_count=len(policy.mind.concepts.concepts),
        mean_schema_reliability=reliability,
        schema_description_length=description_length,
        deterministic_replay_rate=matches / len(trace.steps) if trace.steps else 1.0,
    )


def compare_traces(
    traces: dict[str, EpisodeTrace],
) -> dict[str, dict[str, Any]]:
    return {
        name: evaluate_trace(trace).to_dict()
        for name, trace in sorted(traces.items())
    }
