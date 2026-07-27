"""Bounded symbolic planning over learned event models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .causal import HypothesisStore
from .schemas import SchemaStore

if TYPE_CHECKING:
    from .abstraction import AbstractionStore


@dataclass(frozen=True, slots=True)
class Goal:
    event: str
    priority: float = 1.0


@dataclass(frozen=True, slots=True)
class Plan:
    goal: Goal
    actions: tuple[int, ...]
    predicted_events: tuple[str, ...]
    confidence: float
    expansions: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "goal": self.goal.event,
            "priority": self.goal.priority,
            "actions": list(self.actions),
            "predicted_events": list(self.predicted_events),
            "confidence": self.confidence,
            "expansions": self.expansions,
        }


class SymbolicPlanner:
    """Search direct and temporally mediated action-effect paths."""

    def __init__(self, max_depth: int = 3, max_expansions: int = 64) -> None:
        self.max_depth = max_depth
        self.max_expansions = max_expansions
        self.last_expansions = 0

    def plan(
        self,
        goal: Goal,
        legal_actions: tuple[int, ...],
        schemas: SchemaStore,
        hypotheses: HypothesisStore,
        abstractions: AbstractionStore | None = None,
    ) -> Plan | None:
        self.last_expansions = 0
        frontier: list[tuple[tuple[int, ...], frozenset[str], float]] = [
            ((), frozenset(), 1.0)
        ]
        best: Plan | None = None
        for _depth in range(self.max_depth):
            candidates: list[tuple[tuple[int, ...], frozenset[str], float]] = []
            for actions, achieved, confidence in frontier:
                for action in legal_actions:
                    if self.last_expansions >= self.max_expansions:
                        return best
                    self.last_expansions += 1
                    effects = {
                        hypothesis.effect
                        for hypothesis in hypotheses.causal.values()
                        if hypothesis.action_id == action
                        and hypothesis.strength > 0
                        and hypothesis.confidence > 0
                    }
                    if not effects:
                        effects = set(schemas.event_kinds(action))
                    if abstractions is not None:
                        effects.update(
                            predicate
                            for family in abstractions.schema_families.values()
                            if family.action_id == action
                            and family.reliability >= 0.5
                            for predicate in family.result_predicates
                        )
                    action_confidence = max(
                        (
                            hypothesis.confidence
                            for hypothesis in hypotheses.causal.values()
                            if hypothesis.action_id == action
                            and hypothesis.effect in effects
                            and hypothesis.strength > 0
                        ),
                        default=0.25 if effects else 0.0,
                    )
                    if abstractions is not None:
                        action_confidence = max(
                            action_confidence,
                            max(
                                (
                                    family.reliability
                                    for family in abstractions.schema_families.values()
                                    if family.action_id == action
                                    and set(family.result_predicates) & effects
                                ),
                                default=0.0,
                            ),
                        )
                    expanded = set(achieved) | effects
                    # Apply learned temporal implications as abstract operators.
                    changed = True
                    while changed:
                        changed = False
                        for temporal in hypotheses.temporal.values():
                            if (
                                temporal.antecedent in expanded
                                and temporal.consequent not in expanded
                                and temporal.confidence >= 0.5
                            ):
                                expanded.add(temporal.consequent)
                                changed = True
                    sequence = (*actions, action)
                    sequence_confidence = confidence * action_confidence
                    if goal.event in expanded:
                        proposal = Plan(
                            goal=goal,
                            actions=sequence,
                            predicted_events=tuple(sorted(expanded)),
                            confidence=sequence_confidence,
                            expansions=self.last_expansions,
                        )
                        if best is None or (
                            proposal.confidence,
                            -len(proposal.actions),
                            tuple(-item for item in proposal.actions),
                        ) > (
                            best.confidence,
                            -len(best.actions),
                            tuple(-item for item in best.actions),
                        ):
                            best = proposal
                    candidates.append(
                        (sequence, frozenset(expanded), sequence_confidence)
                    )
            if best is not None:
                return best
            frontier = sorted(
                candidates,
                key=lambda item: (-item[2], len(item[0]), item[0]),
            )[: self.max_expansions]
        return best
