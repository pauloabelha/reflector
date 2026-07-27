"""Empirical Drescher-style schemas and evidence-backed synthetic concepts."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from .symbolic import Atom, Transition


@dataclass(slots=True)
class Schema:
    """Empirical context + action -> result prediction."""

    schema_id: str
    context: tuple[Atom, ...]
    action_id: int
    result: tuple[str, ...]
    support: int = 0
    opportunities: int = 0
    confirmations: int = 0

    @property
    def reliability(self) -> float:
        # Beta(1, 1) posterior mean prevents unjustified certainty.
        return (self.confirmations + 1) / (self.opportunities + 2)

    @property
    def attribution(self) -> float:
        return self.support / max(1, self.opportunities)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "context": [atom.text() for atom in self.context],
            "action_id": self.action_id,
            "result": list(self.result),
            "support": self.support,
            "opportunities": self.opportunities,
            "confirmations": self.confirmations,
            "reliability": self.reliability,
            "attribution": self.attribution,
        }


@dataclass(frozen=True, slots=True)
class SyntheticConcept:
    """A concept retained only with explicit evidence and positive utility."""

    concept_id: str
    name: str
    kind: str
    definition: tuple[str, ...]
    evidence: tuple[str, ...]
    support: int
    utility: float
    complexity: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "name": self.name,
            "kind": self.kind,
            "definition": list(self.definition),
            "evidence": list(self.evidence),
            "support": self.support,
            "utility": self.utility,
            "complexity": self.complexity,
        }


@dataclass(slots=True)
class SchemaStore:
    """Online schema induction with global action-effect attribution."""

    schemas: dict[str, Schema] = field(default_factory=dict)
    action_trials: dict[int, int] = field(default_factory=dict)
    action_events: dict[int, dict[str, int]] = field(default_factory=dict)

    def observe(self, transition: Transition) -> Schema:
        self.action_trials[transition.action_id] = (
            self.action_trials.get(transition.action_id, 0) + 1
        )
        signature = transition.result_signature()
        for event in signature:
            counts = self.action_events.setdefault(transition.action_id, {})
            counts[event] = counts.get(event, 0) + 1

        schema_id = self._id(transition.context, transition.action_id, signature)
        schema = self.schemas.get(schema_id)
        if schema is None:
            schema = Schema(
                schema_id=schema_id,
                context=transition.context,
                action_id=transition.action_id,
                result=signature,
            )
            self.schemas[schema_id] = schema

        # Every schema with the same context/action had an opportunity; only
        # the observed result receives a confirmation.
        for candidate in self.schemas.values():
            if (
                candidate.context == transition.context
                and candidate.action_id == transition.action_id
            ):
                candidate.opportunities += 1
                if candidate.result == signature:
                    candidate.confirmations += 1
        schema.support += 1
        return schema

    def action_value(self, action_id: int) -> float:
        trials = self.action_trials.get(action_id, 0)
        if not trials:
            return 0.0
        weights = {
            "level_advanced": 100.0,
            "state_changed": 5.0,
            "object_appeared": 2.0,
            "object_disappeared": 2.0,
            "object_moved": 1.0,
            "area_changed": 1.0,
            "frame_changed": 0.25,
            "no_observed_change": -0.5,
        }
        total = 0.0
        for event, count in self.action_events.get(action_id, {}).items():
            kind = event.split("(", 1)[0]
            total += weights.get(kind, 0.0) * count
            if "GAME_OVER" in event:
                total -= 100.0 * count
            if "WIN" in event:
                total += 200.0 * count
        return total / trials

    @staticmethod
    def _id(
        context: tuple[Atom, ...], action_id: int, result: tuple[str, ...]
    ) -> str:
        raw = "|".join(
            [*(atom.text() for atom in context), f"action:{action_id}", *result]
        )
        return f"s-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemas": [
                schema.to_dict()
                for schema in sorted(self.schemas.values(), key=lambda item: item.schema_id)
            ],
            "action_trials": dict(sorted(self.action_trials.items())),
            "action_events": {
                str(action): dict(sorted(events.items()))
                for action, events in sorted(self.action_events.items())
            },
        }


@dataclass(slots=True)
class ConceptStore:
    """Propose functional concepts from repeated, reliable schema evidence."""

    concepts: dict[str, SyntheticConcept] = field(default_factory=dict)
    minimum_support: int = 2
    minimum_utility: float = 0.0

    def reflect(self, schemas: SchemaStore) -> tuple[SyntheticConcept, ...]:
        proposals: list[SyntheticConcept] = []
        for action_id, events in sorted(schemas.action_events.items()):
            trials = schemas.action_trials[action_id]
            for event, support in sorted(events.items()):
                if support < self.minimum_support:
                    continue
                reliability = support / trials
                kind = event.split("(", 1)[0]
                if kind == "level_advanced":
                    name, concept_kind = f"Activator[action={action_id}]", "functional_role"
                else:
                    name, concept_kind = (
                        f"ReliableEffect[action={action_id},{kind}]",
                        "causal_regularization",
                    )
                definition = (f"action({action_id})", event)
                complexity = sum(len(term) for term in definition)
                utility = support * reliability - complexity / 100.0
                evidence = tuple(
                    sorted(
                        schema.schema_id
                        for schema in schemas.schemas.values()
                        if schema.action_id == action_id and event in schema.result
                    )
                )
                concept_id = (
                    "c-"
                    + hashlib.sha256(
                        f"{name}|{'|'.join(definition)}".encode()
                    ).hexdigest()[:12]
                )
                if utility > self.minimum_utility:
                    concept = SyntheticConcept(
                        concept_id=concept_id,
                        name=name,
                        kind=concept_kind,
                        definition=definition,
                        evidence=evidence,
                        support=support,
                        utility=utility,
                        complexity=complexity,
                    )
                    self.concepts[concept_id] = concept
                    proposals.append(concept)
        return tuple(proposals)

    def to_dict(self) -> dict[str, Any]:
        return {
            "concepts": [
                concept.to_dict()
                for concept in sorted(
                    self.concepts.values(), key=lambda item: item.concept_id
                )
            ]
        }
