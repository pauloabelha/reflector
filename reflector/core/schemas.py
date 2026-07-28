"""Empirical Drescher-style schemas and evidence-backed synthetic concepts."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
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
    counterfactual_savings: float

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
            "counterfactual_savings": self.counterfactual_savings,
        }


@dataclass(frozen=True, slots=True)
class ConceptLifecycleEvent:
    """Append-only evidence for a concept's operative lifecycle."""

    event_id: str
    concept_id: str
    transition: str
    supersedes: str | None
    reason: str
    support: int
    opportunities: int
    contradictions: int
    reliability: float
    utility: float
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SchemaPrediction:
    """A proposition-level forecast frozen before an outcome is observed."""

    action_id: int
    result: tuple[str, ...]
    evidence: tuple[str, ...]
    evidence_contexts: tuple[tuple[str, ...], ...]
    support: int
    confidence: float
    transferred: bool
    negated_predicates: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "result": list(self.result),
            "evidence": list(self.evidence),
            "evidence_contexts": [list(item) for item in self.evidence_contexts],
            "support": self.support,
            "confidence": self.confidence,
            "transferred": self.transferred,
            "negated_predicates": list(self.negated_predicates),
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

    @staticmethod
    def result_value(result: tuple[str, ...]) -> float:
        """Return external-goal utility, not mere sensory novelty.

        Object and frame changes remain predicted effects for planning, but
        they are not rewards by themselves. Treating any pixel change as
        utility creates repeatable novelty traps in interactive environments.
        """

        weights = {
            "level_advanced": 100.0,
            "state_changed": 0.0,
            "object_appeared": 0.0,
            "object_disappeared": 0.0,
            "object_moved": 0.0,
            "area_changed": 0.0,
            "frame_changed": 0.0,
            "no_observed_change": -0.5,
        }
        total = 0.0
        for event in result:
            kind = event.split("(", 1)[0]
            total += weights.get(kind, 0.0)
            if "GAME_OVER" in event:
                total -= 100.0
            if "WIN" in event:
                total += 200.0
        return total

    def action_value(self, action_id: int) -> float:
        trials = self.action_trials.get(action_id, 0)
        if not trials:
            return 0.0
        return sum(
            self.result_value((event,)) * count
            for event, count in self.action_events.get(action_id, {}).items()
        ) / trials

    @staticmethod
    def _environment_context(
        context: tuple[Atom, ...],
    ) -> tuple[Atom, ...]:
        return tuple(
            atom for atom in context if atom.predicate != "synthetic_item"
        )

    def contextual_trials(
        self, action_id: int, context: tuple[Atom, ...]
    ) -> int:
        environment = self._environment_context(context)
        return sum(
            schema.support
            for schema in self.schemas.values()
            if schema.action_id == action_id
            and self._environment_context(schema.context) == environment
        )

    def contextual_action_value(
        self,
        action_id: int,
        context: tuple[Atom, ...],
        *,
        transfer_value: float = 0.0,
    ) -> float:
        """Prefer empirical effects in the current symbolic scene.

        Cross-context transfer is supplied explicitly by a retained
        abstraction. Raw global action averages are not silently treated as an
        abstraction because doing so makes the abstraction ablation invalid.
        """

        environment = self._environment_context(context)
        matching = [
            schema
            for schema in self.schemas.values()
            if schema.action_id == action_id
            and self._environment_context(schema.context) == environment
        ]
        support = sum(schema.support for schema in matching)
        if not support:
            return transfer_value
        return sum(
            self.result_value(schema.result) * schema.support
            for schema in matching
        ) / support

    def predict(
        self,
        action_id: int,
        context: tuple[Atom, ...],
        *,
        minimum_confidence: float = 0.5,
    ) -> SchemaPrediction | None:
        """Freeze the best supported result forecast before observing it.

        Exact-context evidence is preferred.  If none exists, repeated
        action/result evidence may transfer as a deliberately marked
        hypothesis so a perturbation can expose a missing validity condition.
        """

        environment = self._environment_context(context)
        candidates = [
            schema
            for schema in self.schemas.values()
            if schema.action_id == action_id
            and schema.reliability >= minimum_confidence
        ]
        exact = [
            schema
            for schema in candidates
            if self._environment_context(schema.context) == environment
        ]
        selected = exact or candidates
        if not selected:
            return None

        grouped: dict[tuple[str, ...], list[Schema]] = {}
        for schema in selected:
            predicate_signature = tuple(
                sorted(term.split("(", 1)[0] for term in schema.result)
            )
            grouped.setdefault(predicate_signature, []).append(schema)
        _signature, members = max(
            grouped.items(),
            key=lambda item: (
                sum(schema.support for schema in item[1]),
                sum(schema.confirmations for schema in item[1]),
                item[0],
            ),
        )
        representative = max(
            members,
            key=lambda schema: (
                schema.support,
                schema.confirmations,
                schema.result,
            ),
        )
        result = representative.result
        support = sum(schema.support for schema in members)
        opportunities = sum(schema.opportunities for schema in members)
        confirmations = sum(schema.confirmations for schema in members)
        return SchemaPrediction(
            action_id=action_id,
            result=result,
            evidence=tuple(sorted(schema.schema_id for schema in members)),
            evidence_contexts=tuple(
                sorted(
                    tuple(atom.text() for atom in schema.context)
                    for schema in members
                )
            ),
            support=support,
            confidence=(confirmations + 1) / (opportunities + 2),
            transferred=not bool(exact),
            negated_predicates=(),
        )

    def event_probability(self, action_id: int, event_kind: str) -> float:
        trials = self.action_trials.get(action_id, 0)
        if not trials:
            return 0.0
        support = sum(
            count
            for event, count in self.action_events.get(action_id, {}).items()
            if event.split("(", 1)[0] == event_kind
        )
        return support / trials

    def event_kinds(self, action_id: int) -> tuple[str, ...]:
        return tuple(
            sorted(
                {
                    event.split("(", 1)[0]
                    for event in self.action_events.get(action_id, {})
                }
            )
        )

    def event_text_probability(self, action_id: int, token: str) -> float:
        trials = self.action_trials.get(action_id, 0)
        if not trials:
            return 0.0
        support = sum(
            count
            for event, count in self.action_events.get(action_id, {}).items()
            if token in event
        )
        return support / trials

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
    active_ids: set[str] = field(default_factory=set)
    lifecycle_events: dict[str, ConceptLifecycleEvent] = field(
        default_factory=dict
    )
    latest_lifecycle_event: dict[str, str] = field(default_factory=dict)
    minimum_support: int = 2
    minimum_utility: float = 0.0
    complexity_pressure: float = 1.0
    require_counterfactual_utility: bool = True
    enable_retirement: bool = True
    retirement_min_opportunities: int = 6
    retirement_min_contradictions: int = 3
    retirement_reliability: float = 0.35
    reactivation_support_gain: int = 2
    reactivation_reliability: float = 0.50

    def context_atoms(self, action_id: int) -> tuple[Atom, ...]:
        """Compile retained functional concepts into later schema contexts."""

        action_term = f"action({action_id})"
        return tuple(
            Atom("synthetic_item", (concept.concept_id,))
            for concept in sorted(
                self.concepts.values(), key=lambda item: item.concept_id
            )
            if concept.concept_id in self.active_ids
            and action_term in concept.definition
        )

    def is_active(self, concept_id: str) -> bool:
        return concept_id in self.active_ids

    def active_concepts(self) -> tuple[SyntheticConcept, ...]:
        return tuple(
            concept
            for concept in sorted(
                self.concepts.values(), key=lambda item: item.concept_id
            )
            if concept.concept_id in self.active_ids
        )

    def reflect(self, schemas: SchemaStore) -> tuple[SyntheticConcept, ...]:
        transitions: list[SyntheticConcept] = []
        for action_id, events in sorted(schemas.action_events.items()):
            trials = schemas.action_trials[action_id]
            for event, support in sorted(events.items()):
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
                raw_description = support * len(event)
                compiled_description = (
                    self.complexity_pressure * complexity + support * 4
                )
                rediscovery_savings = max(0, support - 1) * 10
                counterfactual_savings = (
                    raw_description
                    + rediscovery_savings
                    - compiled_description
                )
                utility = (
                    counterfactual_savings * reliability
                    if self.require_counterfactual_utility
                    else support * reliability
                )
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
                concept = SyntheticConcept(
                    concept_id=concept_id,
                    name=name,
                    kind=concept_kind,
                    definition=definition,
                    evidence=evidence,
                    support=support,
                    utility=utility,
                    complexity=complexity,
                    counterfactual_savings=counterfactual_savings,
                )
                eligible = (
                    support >= self.minimum_support
                    and utility > self.minimum_utility
                )
                existing = self.concepts.get(concept_id)
                if existing is None:
                    if not eligible:
                        continue
                    self.concepts[concept_id] = concept
                    self.active_ids.add(concept_id)
                    self._record_lifecycle(
                        concept,
                        transition="activated",
                        reason="positive-counterfactual-utility",
                        opportunities=trials,
                    )
                    transitions.append(concept)
                else:
                    self.concepts[concept_id] = concept

                contradictions = trials - support
                if (
                    self.enable_retirement
                    and concept_id in self.active_ids
                    and trials >= self.retirement_min_opportunities
                    and contradictions
                    >= self.retirement_min_contradictions
                    and reliability < self.retirement_reliability
                ):
                    self.active_ids.remove(concept_id)
                    self._record_lifecycle(
                        concept,
                        transition="retired",
                        reason="repeated-contradiction-below-reliability",
                        opportunities=trials,
                    )
                elif (
                    self.enable_retirement
                    and concept_id not in self.active_ids
                    and eligible
                    and reliability >= self.reactivation_reliability
                    and self._support_gain_since_retirement(concept_id, support)
                    >= self.reactivation_support_gain
                ):
                    self.active_ids.add(concept_id)
                    self._record_lifecycle(
                        concept,
                        transition="reactivated",
                        reason="restored-reliability-and-utility",
                        opportunities=trials,
                    )
                    transitions.append(concept)
        return tuple(transitions)

    def _support_gain_since_retirement(
        self,
        concept_id: str,
        support: int,
    ) -> int:
        event_id = self.latest_lifecycle_event.get(concept_id)
        if event_id is None:
            return 0
        event = self.lifecycle_events[event_id]
        if event.transition != "retired":
            return 0
        return support - event.support

    def _record_lifecycle(
        self,
        concept: SyntheticConcept,
        *,
        transition: str,
        reason: str,
        opportunities: int,
    ) -> None:
        supersedes = self.latest_lifecycle_event.get(concept.concept_id)
        raw = "|".join(
            (
                concept.concept_id,
                transition,
                str(concept.support),
                str(opportunities),
                supersedes or "",
            )
        )
        event_id = (
            "concept-lifecycle-"
            + hashlib.sha256(raw.encode()).hexdigest()[:12]
        )
        if event_id in self.lifecycle_events:
            return
        event = ConceptLifecycleEvent(
            event_id=event_id,
            concept_id=concept.concept_id,
            transition=transition,
            supersedes=supersedes,
            reason=reason,
            support=concept.support,
            opportunities=opportunities,
            contradictions=opportunities - concept.support,
            reliability=concept.support / opportunities,
            utility=concept.utility,
            evidence=concept.evidence,
        )
        self.lifecycle_events[event_id] = event
        self.latest_lifecycle_event[concept.concept_id] = event_id

    def to_dict(self) -> dict[str, Any]:
        return {
            "concepts": [
                concept.to_dict()
                for concept in sorted(
                    self.concepts.values(), key=lambda item: item.concept_id
                )
            ],
            "active_ids": sorted(self.active_ids),
            "retired_ids": sorted(set(self.concepts) - self.active_ids),
            "lifecycle_events": [
                event.to_dict()
                for event in self.lifecycle_events.values()
            ],
        }
