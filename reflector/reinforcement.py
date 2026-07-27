"""Typed structural credit and disequilibrium, without scalarizing cognition."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Iterable

from .schemas import SchemaPrediction
from .symbolic import Atom, Transition


def _identifier(*parts: str) -> str:
    raw = "|".join(parts)
    return f"assessment-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _kind(term: str) -> str:
    return term.split("(", 1)[0]


@dataclass(frozen=True, slots=True)
class StructuralAssessment:
    """Separate evidence channels for one pre-outcome symbolic prediction."""

    assessment_id: str
    before_index: int
    after_index: int
    context: tuple[str, ...]
    action_id: int
    predicted: tuple[str, ...]
    observed: tuple[str, ...]
    licensing_structures: tuple[str, ...]
    confirmed: tuple[str, ...]
    contradicted: tuple[str, ...]
    unpredicted: tuple[str, ...]
    pragmatic: tuple[str, ...]
    epistemic: tuple[str, ...]
    perturbation: tuple[str, ...]
    response: str
    support: int

    @property
    def is_disequilibrium(self) -> bool:
        return bool(self.contradicted)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "is_disequilibrium": self.is_disequilibrium}


@dataclass(frozen=True, slots=True)
class StructuralEligibility:
    """Bounded, proposition-naming responsibility across later transitions."""

    structure_id: str
    proposition: str
    source_assessment: str
    age: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ConditionalAccommodation:
    """A learned context condition that adds or suppresses a proposition."""

    accommodation_id: str
    action_id: int
    condition: tuple[str, ...]
    operation: str
    proposition: str
    evidence: tuple[str, ...]
    support: int
    confidence: float
    raw_description_length: int
    compiled_description_length: int
    complexity: int
    utility: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class StructuralCreditLedger:
    """Route prediction error to evidence-backed structural responses."""

    max_trace_age: int = 4
    assessments: dict[str, StructuralAssessment] = field(default_factory=dict)
    eligibility: list[StructuralEligibility] = field(default_factory=list)
    credited_structures: dict[str, dict[str, int]] = field(default_factory=dict)
    accommodations: dict[str, ConditionalAccommodation] = field(
        default_factory=dict
    )
    accommodation_history: dict[str, ConditionalAccommodation] = field(
        default_factory=dict
    )
    last_constructed: tuple[str, ...] = ()

    def assess(
        self,
        transition: Transition,
        prediction: SchemaPrediction | None,
    ) -> str:
        """Assess a transition against a prediction frozen before learning."""

        observed = transition.result_signature()
        predicted = prediction.result if prediction is not None else ()
        predicted_set = set(predicted)
        observed_set = set(observed)
        confirmed = tuple(sorted(predicted_set & observed_set))
        contradicted = tuple(sorted(predicted_set - observed_set))
        unpredicted = tuple(sorted(observed_set - predicted_set))
        pragmatic = tuple(
            sorted(
                term
                for term in observed
                if _kind(term) in {"level_advanced", "WIN"}
                or "GAME_OVER" in term
            )
        )
        epistemic = tuple(
            sorted(
                term
                for term in observed
                if _kind(term)
                in {
                    "novel_state_reached",
                    "object_appeared",
                    "object_disappeared",
                    "object_moved",
                    "orientation_delta",
                }
            )
        )
        context = tuple(sorted(atom.text() for atom in transition.context))
        shared = self._shared_context(
            prediction.evidence_contexts if prediction is not None else ()
        )
        perturbation = (
            tuple(sorted(set(context) - shared))
            if (contradicted or unpredicted) and prediction is not None
            else ()
        )
        response = (
            "differentiate"
            if contradicted and perturbation
            else "specialize"
            if contradicted
            else "retain"
        )
        licensing = prediction.evidence if prediction is not None else ()
        assessment_id = _identifier(
            str(transition.before_index),
            str(transition.after_index),
            str(transition.action_id),
            *predicted,
            "=>",
            *observed,
        )
        previous = self.assessments.get(assessment_id)
        self.assessments[assessment_id] = StructuralAssessment(
            assessment_id=assessment_id,
            before_index=transition.before_index,
            after_index=transition.after_index,
            context=context,
            action_id=transition.action_id,
            predicted=predicted,
            observed=observed,
            licensing_structures=licensing,
            confirmed=confirmed,
            contradicted=contradicted,
            unpredicted=unpredicted,
            pragmatic=pragmatic,
            epistemic=epistemic,
            perturbation=perturbation,
            response=response,
            support=1 if previous is None else previous.support + 1,
        )
        self._advance_eligibility(observed)
        for structure_id in licensing:
            for proposition in predicted:
                self.eligibility.append(
                    StructuralEligibility(
                        structure_id=structure_id,
                        proposition=proposition,
                        source_assessment=assessment_id,
                    )
                )
        self.eligibility = self.eligibility[-256:]
        self.last_constructed = self._rebuild_accommodations()
        return assessment_id

    def accommodate_prediction(
        self,
        *,
        action_id: int,
        context: tuple[Atom, ...],
        prediction: SchemaPrediction | None,
    ) -> SchemaPrediction | None:
        """Apply the most specific evidenced proposition amendments."""

        current = {atom.text() for atom in context}
        applicable = [
            item
            for item in self.accommodations.values()
            if item.action_id == action_id
            and set(item.condition).issubset(current)
        ]
        if not applicable:
            return prediction
        chosen: dict[str, ConditionalAccommodation] = {}
        for item in applicable:
            previous = chosen.get(item.proposition)
            if previous is None or (
                len(item.condition),
                item.support,
                item.confidence,
                item.accommodation_id,
            ) > (
                len(previous.condition),
                previous.support,
                previous.confidence,
                previous.accommodation_id,
            ):
                chosen[item.proposition] = item
        result = list(prediction.result if prediction is not None else ())
        for proposition, item in sorted(chosen.items()):
            result = [term for term in result if _kind(term) != proposition]
            if item.operation == "add":
                result.append(proposition)
        evidence = set(prediction.evidence if prediction is not None else ())
        evidence.update(item.accommodation_id for item in chosen.values())
        contexts = (
            prediction.evidence_contexts if prediction is not None else ()
        )
        support = min(item.support for item in chosen.values())
        confidence = min(item.confidence for item in chosen.values())
        return SchemaPrediction(
            action_id=action_id,
            result=tuple(sorted(set(result))),
            evidence=tuple(sorted(evidence)),
            evidence_contexts=contexts,
            support=support,
            confidence=confidence,
            transferred=True,
        )

    def _rebuild_accommodations(self) -> tuple[str, ...]:
        before = set(self.accommodations)
        grouped: dict[
            tuple[int, str, str], list[StructuralAssessment]
        ] = {}
        for assessment in self.assessments.values():
            if not assessment.perturbation:
                continue
            for term in assessment.contradicted:
                grouped.setdefault(
                    (assessment.action_id, "remove", _kind(term)), []
                ).append(assessment)
            for term in assessment.unpredicted:
                grouped.setdefault(
                    (assessment.action_id, "add", _kind(term)), []
                ).append(assessment)

        rebuilt: dict[str, ConditionalAccommodation] = {}
        for (action_id, operation, proposition), evidence in sorted(
            grouped.items()
        ):
            if len(evidence) < 2:
                continue
            condition = tuple(
                sorted(
                    set.intersection(
                        *(set(item.perturbation) for item in evidence)
                    )
                )
            )
            if not condition:
                continue
            evidence_ids = tuple(
                sorted(item.assessment_id for item in evidence)
            )
            raw = sum(
                sum(len(term) for term in item.context)
                + sum(len(term) for term in item.predicted)
                + sum(len(term) for term in item.observed)
                for item in evidence
            )
            complexity = (
                len(str(action_id))
                + len(operation)
                + len(proposition)
                + sum(len(term) for term in condition)
                + 12
            )
            compiled = complexity + len(evidence) * 4
            utility = raw - compiled
            if utility <= 0:
                continue
            accommodation_id = (
                "accommodation-"
                + hashlib.sha256(
                    "|".join(
                        (
                            str(action_id),
                            operation,
                            proposition,
                            *condition,
                        )
                    ).encode()
                ).hexdigest()[:12]
            )
            rebuilt[accommodation_id] = ConditionalAccommodation(
                accommodation_id=accommodation_id,
                action_id=action_id,
                condition=condition,
                operation=operation,
                proposition=proposition,
                evidence=evidence_ids,
                support=len(evidence),
                confidence=(len(evidence) + 1) / (len(evidence) + 2),
                raw_description_length=raw,
                compiled_description_length=compiled,
                complexity=complexity,
                utility=utility,
            )
        self.accommodations = rebuilt
        self.accommodation_history.update(rebuilt)
        return tuple(sorted(set(rebuilt) - before))

    def integrate(
        self,
        family_rows: Iterable[
            tuple[int, tuple[str, ...], tuple[str, ...], int]
        ],
    ) -> tuple[str, ...]:
        """Mark differentiated cases integrated by an evidenced conditional."""

        integrated: list[str] = []
        families = tuple(family_rows)
        for assessment_id, assessment in tuple(self.assessments.items()):
            if assessment.response not in {"differentiate", "specialize"}:
                continue
            context = set(assessment.context)
            for action_id, results, shared_context, support in families:
                if (
                    action_id == assessment.action_id
                    and {_kind(term) for term in assessment.observed}.issubset(
                        results
                    )
                    and set(shared_context).issubset(context)
                    and support >= 2
                ):
                    self.assessments[assessment_id] = replace(
                        assessment,
                        response="integrate",
                    )
                    integrated.append(assessment_id)
                    break
        return tuple(sorted(integrated))

    @staticmethod
    def _shared_context(contexts: tuple[tuple[str, ...], ...]) -> set[str]:
        if not contexts:
            return set()
        return set.intersection(*(set(context) for context in contexts))

    def _advance_eligibility(self, observed: tuple[str, ...]) -> None:
        retained: list[StructuralEligibility] = []
        observed_set = set(observed)
        for item in self.eligibility:
            if item.proposition in observed_set:
                counts = self.credited_structures.setdefault(
                    item.structure_id, {}
                )
                counts[item.proposition] = counts.get(item.proposition, 0) + 1
            aged = replace(item, age=item.age + 1)
            if aged.age <= self.max_trace_age:
                retained.append(aged)
        self.eligibility = retained

    def to_dict(self) -> dict[str, Any]:
        return {
            "assessments": [
                item.to_dict()
                for item in sorted(
                    self.assessments.values(),
                    key=lambda value: value.assessment_id,
                )
            ],
            "eligibility": [item.to_dict() for item in self.eligibility],
            "credited_structures": {
                structure: dict(sorted(propositions.items()))
                for structure, propositions in sorted(
                    self.credited_structures.items()
                )
            },
            "accommodations": [
                item.to_dict()
                for item in sorted(
                    self.accommodations.values(),
                    key=lambda value: value.accommodation_id,
                )
            ],
            "accommodation_history": [
                item.to_dict()
                for item in sorted(
                    self.accommodation_history.values(),
                    key=lambda value: value.accommodation_id,
                )
            ],
        }
