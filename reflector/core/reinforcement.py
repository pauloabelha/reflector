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
    hypothesis_id: str | None
    before_index: int
    after_index: int
    context: tuple[str, ...]
    action_id: int
    predicted: tuple[str, ...]
    observed: tuple[str, ...]
    licensing_structures: tuple[str, ...]
    scheme_components: tuple[str, ...]
    confirmed: tuple[str, ...]
    contradicted: tuple[str, ...]
    predicted_absent: tuple[str, ...]
    confirmed_absent: tuple[str, ...]
    contradicted_absent: tuple[str, ...]
    unpredicted: tuple[str, ...]
    pragmatic: tuple[str, ...]
    epistemic: tuple[str, ...]
    perturbation: tuple[str, ...]
    response: str
    support: int

    @property
    def is_disequilibrium(self) -> bool:
        return bool(self.contradicted or self.contradicted_absent)

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
class PrimedCausalHypothesis:
    """A pre-intervention forecast naming every structure put at risk."""

    hypothesis_id: str
    before_index: int
    action_id: int
    context: tuple[str, ...]
    predicted: tuple[str, ...]
    predicted_absent: tuple[str, ...]
    licensing_structures: tuple[str, ...]
    scheme_components: tuple[str, ...]
    support: int
    confidence: float

    def prediction(self) -> SchemaPrediction | None:
        if not self.predicted and not self.predicted_absent:
            return None
        return SchemaPrediction(
            action_id=self.action_id,
            result=self.predicted,
            evidence=self.licensing_structures,
            evidence_contexts=(self.context,),
            support=self.support,
            confidence=self.confidence,
            transferred=False,
            negated_predicates=self.predicted_absent,
        )

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
    typed_credit: dict[str, dict[str, int]] = field(default_factory=dict)
    hypothesis_history: dict[str, PrimedCausalHypothesis] = field(
        default_factory=dict
    )
    pending_hypothesis: PrimedCausalHypothesis | None = None
    consecutive_without_progress: int = 0
    pragmatic_disequilibrium_threshold: int = 8
    accommodations: dict[str, ConditionalAccommodation] = field(
        default_factory=dict
    )
    accommodation_history: dict[str, ConditionalAccommodation] = field(
        default_factory=dict
    )
    last_constructed: tuple[str, ...] = ()

    @property
    def pragmatic_disequilibrium(self) -> bool:
        return (
            self.consecutive_without_progress
            >= self.pragmatic_disequilibrium_threshold
        )

    def prime(
        self,
        *,
        before_index: int,
        action_id: int,
        context: tuple[Atom, ...],
        prediction: SchemaPrediction | None,
        scheme_components: tuple[str, ...] = (),
    ) -> str:
        """Preregister a causal forecast before its intervention is executed."""

        context_terms = tuple(sorted(atom.text() for atom in context))
        predicted = prediction.result if prediction is not None else ()
        absent = (
            prediction.negated_predicates if prediction is not None else ()
        )
        licensing = prediction.evidence if prediction is not None else ()
        hypothesis_id = (
            "primed-"
            + hashlib.sha256(
                "|".join(
                    (
                        str(before_index),
                        str(action_id),
                        *context_terms,
                        "predict",
                        *predicted,
                        "absent",
                        *absent,
                        "structures",
                        *licensing,
                        "schemes",
                        *scheme_components,
                    )
                ).encode()
            ).hexdigest()[:12]
        )
        hypothesis = PrimedCausalHypothesis(
            hypothesis_id=hypothesis_id,
            before_index=before_index,
            action_id=action_id,
            context=context_terms,
            predicted=predicted,
            predicted_absent=absent,
            licensing_structures=tuple(sorted(set(licensing))),
            scheme_components=tuple(sorted(set(scheme_components))),
            support=prediction.support if prediction is not None else 0,
            confidence=prediction.confidence if prediction is not None else 0.0,
        )
        self.pending_hypothesis = hypothesis
        self.hypothesis_history[hypothesis_id] = hypothesis
        return hypothesis_id

    def consume_primed(
        self,
        action_id: int,
    ) -> PrimedCausalHypothesis | None:
        hypothesis = self.pending_hypothesis
        self.pending_hypothesis = None
        if hypothesis is None or hypothesis.action_id != action_id:
            return None
        return hypothesis

    def assess(
        self,
        transition: Transition,
        prediction: SchemaPrediction | None,
        primed: PrimedCausalHypothesis | None = None,
    ) -> str:
        """Assess a transition against a prediction frozen before learning."""

        observed = transition.result_signature()
        predicted = prediction.result if prediction is not None else ()
        observed_set = set(observed)
        observed_kinds = {_kind(term) for term in observed}
        confirmed = tuple(
            sorted(
                term
                for term in predicted
                if (
                    term in observed_set
                    if "(" in term
                    else term in observed_kinds
                )
            )
        )
        contradicted = tuple(sorted(set(predicted) - set(confirmed)))
        matched_observed = {
            term
            for term in observed
            if any(
                forecast == term
                if "(" in forecast
                else forecast == _kind(term)
                for forecast in predicted
            )
        }
        predicted_absent = (
            prediction.negated_predicates if prediction is not None else ()
        )
        confirmed_absent = tuple(
            sorted(
                proposition
                for proposition in predicted_absent
                if proposition not in observed_kinds
            )
        )
        contradicted_absent = tuple(
            sorted(
                proposition
                for proposition in predicted_absent
                if proposition in observed_kinds
            )
        )
        unpredicted = tuple(sorted(observed_set - matched_observed))
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
            if (contradicted or contradicted_absent or unpredicted)
            and prediction is not None
            else ()
        )
        response = (
            "differentiate"
            if (contradicted or contradicted_absent) and perturbation
            else "specialize"
            if contradicted or contradicted_absent
            else "retain"
        )
        licensing = (
            primed.licensing_structures
            if primed is not None
            else prediction.evidence
            if prediction is not None
            else ()
        )
        scheme_components = (
            primed.scheme_components if primed is not None else ()
        )
        assessment_id = _identifier(
            primed.hypothesis_id if primed is not None else "unprimed",
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
            hypothesis_id=(
                primed.hypothesis_id if primed is not None else None
            ),
            before_index=transition.before_index,
            after_index=transition.after_index,
            context=context,
            action_id=transition.action_id,
            predicted=predicted,
            observed=observed,
            licensing_structures=licensing,
            scheme_components=scheme_components,
            confirmed=confirmed,
            contradicted=contradicted,
            predicted_absent=predicted_absent,
            confirmed_absent=confirmed_absent,
            contradicted_absent=contradicted_absent,
            unpredicted=unpredicted,
            pragmatic=pragmatic,
            epistemic=epistemic,
            perturbation=perturbation,
            response=response,
            support=1 if previous is None else previous.support + 1,
        )
        self._assign_typed_credit(
            (*licensing, *scheme_components),
            confirmed=confirmed,
            contradicted=(*contradicted, *contradicted_absent),
            observed=observed,
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

    def _assign_typed_credit(
        self,
        structures: tuple[str, ...],
        *,
        confirmed: tuple[str, ...],
        contradicted: tuple[str, ...],
        observed: tuple[str, ...],
    ) -> None:
        observed_kinds = {_kind(term) for term in observed}
        progress = bool(observed_kinds & {"level_advanced", "WIN"})
        terminal_failure = any("GAME_OVER" in term for term in observed)
        no_effect = observed_kinds == {"no_observed_change"}
        self.consecutive_without_progress = (
            0 if progress else self.consecutive_without_progress + 1
        )
        for structure_id in sorted(set(structures)):
            channels = self.typed_credit.setdefault(structure_id, {})
            if confirmed:
                channels["predictive_support"] = (
                    channels.get("predictive_support", 0) + len(confirmed)
                )
            if contradicted:
                channels["predictive_refutation"] = (
                    channels.get("predictive_refutation", 0)
                    + len(contradicted)
                )
            if progress:
                channels["pragmatic_progress"] = (
                    channels.get("pragmatic_progress", 0) + 1
                )
            elif terminal_failure:
                channels["pragmatic_failure"] = (
                    channels.get("pragmatic_failure", 0) + 1
                )
            elif no_effect:
                channels["pragmatic_stagnation"] = (
                    channels.get("pragmatic_stagnation", 0) + 1
                )

    def pragmatic_structure_scores(self) -> dict[str, int]:
        """Return only pragmatic credit; never collapse prediction into reward."""

        return {
            structure_id: (
                channels.get("pragmatic_progress", 0) * 4
                - channels.get("pragmatic_stagnation", 0)
                - channels.get("pragmatic_failure", 0) * 4
            )
            for structure_id, channels in self.typed_credit.items()
        }

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
        negated = set(
            prediction.negated_predicates if prediction is not None else ()
        )
        for proposition, item in sorted(chosen.items()):
            result = [term for term in result if _kind(term) != proposition]
            if item.operation == "remove":
                negated.add(proposition)
            else:
                negated.discard(proposition)
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
            negated_predicates=tuple(sorted(negated)),
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
            for proposition in assessment.contradicted_absent:
                grouped.setdefault(
                    (assessment.action_id, "add", proposition), []
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
            "typed_credit": {
                structure: dict(sorted(channels.items()))
                for structure, channels in sorted(self.typed_credit.items())
            },
            "hypothesis_history": [
                item.to_dict()
                for item in sorted(
                    self.hypothesis_history.values(),
                    key=lambda value: value.hypothesis_id,
                )
            ],
            "pending_hypothesis": (
                self.pending_hypothesis.to_dict()
                if self.pending_hypothesis is not None
                else None
            ),
            "consecutive_without_progress": self.consecutive_without_progress,
            "pragmatic_disequilibrium": self.pragmatic_disequilibrium,
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
