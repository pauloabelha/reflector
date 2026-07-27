"""Practical recoverable epistemic redundancy and counterfactual replay."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from .mind import MindConfig
from .policy import SymbolicPolicy
from .schemas import SyntheticConcept
from .symbolic import Transition
from .trace import EpisodeTrace


@dataclass(frozen=True, slots=True)
class RedundancyReport:
    repeated_rediscoveries: int
    repeated_planning_work: int
    equivalent_schema_groups: int
    equivalent_schemas: int
    forgotten_inferences: int
    abstraction_description_savings: int
    language_description_savings: int
    raw_symbolic_description_length: int
    recoverable_redundancy: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class CounterfactualReplayResult:
    concept_id: str
    injection_index: int
    matching_occurrences: int
    raw_description_cost: int
    compiled_description_cost: int
    description_savings: int
    rediscoveries_avoided: int
    planner_expansions_saved: int
    action_savings: int
    net_utility: int
    accepted: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def replay_policy(
    trace: EpisodeTrace, config: MindConfig | None = None
) -> SymbolicPolicy:
    deployed = (
        config
        if config is not None
        else (
            MindConfig.from_dict(trace.mind_config)
            if trace.mind_config
            else MindConfig()
        )
    )
    policy = SymbolicPolicy(deployed)
    for step in trace.steps:
        policy.choose_action(step.observation)
    if trace.terminal_observation is not None:
        policy.observe(trace.terminal_observation)
    return policy


def transitions(trace: EpisodeTrace) -> tuple[Transition, ...]:
    items = [
        step.incoming_transition
        for step in trace.steps
        if step.incoming_transition is not None
    ]
    if trace.terminal_transition is not None:
        items.append(trace.terminal_transition)
    return tuple(items)


def analyze_redundancy(
    trace: EpisodeTrace, policy: SymbolicPolicy | None = None
) -> RedundancyReport:
    observed = transitions(trace)
    signatures = Counter(
        (item.action_id, event.kind)
        for item in observed
        for event in item.result
    )
    repeated_rediscoveries = sum(max(0, count - 1) for count in signatures.values())

    plan_signatures = Counter(
        step.plan_actions for step in trace.steps if step.plan_actions
    )
    repeated_planning = sum(
        max(0, count - 1) for count in plan_signatures.values()
    )

    policy = policy or replay_policy(trace)
    equivalent: dict[tuple[int, tuple[str, ...]], list[str]] = defaultdict(list)
    for schema in policy.mind.schemas.schemas.values():
        equivalent[(schema.action_id, schema.result)].append(schema.schema_id)
    equivalent_groups = tuple(
        group for group in equivalent.values() if len(group) > 1
    )

    birth = {
        concept_id: step.index
        for step in trace.steps
        for concept_id in step.new_concepts
    }
    forgotten = 0
    for concept in policy.mind.concepts.concepts.values():
        event = concept.definition[-1]
        born_at = birth.get(concept.concept_id, len(trace.steps))
        earlier = sum(
            event in item.result_signature()
            and item.after_index <= born_at
            for item in observed
        )
        forgotten += max(0, earlier - 1)

    raw_length = sum(
        len(atom.text()) for item in observed for atom in item.context
    ) + sum(
        len(result) for item in observed for result in item.result_signature()
    )
    equivalent_count = sum(len(group) - 1 for group in equivalent_groups)
    abstraction_savings = round(
        sum(
            item.utility
            for item in policy.mind.abstractions.schema_families.values()
        )
        + sum(
            item.utility
            for item in policy.mind.abstractions.concept_types.values()
        )
    )
    language_savings = round(
        sum(
            item.utility
            for item in policy.mind.abstractions.language_operators.values()
        )
    )
    recoverable = (
        repeated_rediscoveries
        + repeated_planning
        + equivalent_count
        + forgotten
    )
    return RedundancyReport(
        repeated_rediscoveries=repeated_rediscoveries,
        repeated_planning_work=repeated_planning,
        equivalent_schema_groups=len(equivalent_groups),
        equivalent_schemas=equivalent_count,
        forgotten_inferences=forgotten,
        abstraction_description_savings=abstraction_savings,
        language_description_savings=language_savings,
        raw_symbolic_description_length=raw_length,
        recoverable_redundancy=recoverable,
    )


def counterfactual_replay(
    trace: EpisodeTrace,
    policy: SymbolicPolicy | None = None,
) -> tuple[CounterfactualReplayResult, ...]:
    """Inject final concepts at first evidence and replay representational cost.

    This initial counterfactual deliberately claims no action savings because a
    trace cannot reveal unobserved environment outcomes. It measures only
    quantities recoverable without fabricating transitions: description length,
    repeated compilation, and equivalent planner work.
    """

    policy = policy or replay_policy(trace)
    observed = transitions(trace)
    return tuple(
        _replay_concept(trace, observed, concept)
        for concept in sorted(
            policy.mind.concepts.concepts.values(),
            key=lambda item: item.concept_id,
        )
    )


def _replay_concept(
    trace: EpisodeTrace,
    observed: tuple[Transition, ...],
    concept: SyntheticConcept,
) -> CounterfactualReplayResult:
    event = concept.definition[-1]
    matches = [
        item for item in observed if event in item.result_signature()
    ]
    injection = matches[0].after_index if matches else 0
    raw_cost = len(event) * len(matches)
    compiled_cost = concept.complexity + 4 * len(matches)
    description_savings = raw_cost - compiled_cost
    rediscoveries = max(0, len(matches) - 1)
    plan_counts = Counter(
        step.plan_actions
        for step in trace.steps
        if step.index >= injection and step.plan_actions
    )
    planner_savings = sum(max(0, count - 1) for count in plan_counts.values())
    net_utility = description_savings + rediscoveries * 10 + planner_savings
    return CounterfactualReplayResult(
        concept_id=concept.concept_id,
        injection_index=injection,
        matching_occurrences=len(matches),
        raw_description_cost=raw_cost,
        compiled_description_cost=compiled_cost,
        description_savings=description_savings,
        rediscoveries_avoided=rediscoveries,
        planner_expansions_saved=planner_savings,
        action_savings=0,
        net_utility=net_utility,
        accepted=net_utility > 0,
    )
