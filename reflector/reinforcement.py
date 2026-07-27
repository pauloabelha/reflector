"""Typed structural credit and disequilibrium, without scalarizing cognition."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Iterable

from .schemas import SchemaPrediction
from .symbolic import Transition


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


@dataclass(slots=True)
class StructuralCreditLedger:
    """Route prediction error to evidence-backed structural responses."""

    max_trace_age: int = 4
    assessments: dict[str, StructuralAssessment] = field(default_factory=dict)
    eligibility: list[StructuralEligibility] = field(default_factory=list)
    credited_structures: dict[str, dict[str, int]] = field(default_factory=dict)

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
            if contradicted and prediction is not None
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
        return assessment_id

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
        }
