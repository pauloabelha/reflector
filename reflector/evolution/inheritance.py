"""Development-only evidence, accommodation, and selection for schemes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable, Literal, Mapping, Protocol

from ..core.inheritance import (
    SchemeDefinition,
    SchemeLibrary,
    common_sense_root,
)
from ..core.mind import MindConfig
from ..research.event_audit import (
    STABLE_REPEATED_FORM_ACTION_EFFECT,
    RecordingEventAudit,
)
from .population import Candidate

EvidenceOutcome = Literal[
    "prediction-confirmed",
    "prediction-falsified",
    "level-progress",
    "regression",
]


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class SchemeEvidence:
    """One append-only assessment of a preregistered scheme prediction."""

    scheme_id: str
    candidate_id: str
    partition: str
    episode_digest: str
    prediction_digest: str
    outcome: EvidenceOutcome
    interventions_saved: int = 0

    def __post_init__(self) -> None:
        for name in (
            "scheme_id",
            "candidate_id",
            "partition",
            "episode_digest",
            "prediction_digest",
        ):
            if not getattr(self, name):
                raise ValueError(f"{name} must be non-empty")
        if self.outcome not in (
            "prediction-confirmed",
            "prediction-falsified",
            "level-progress",
            "regression",
        ):
            raise ValueError(f"unknown evidence outcome: {self.outcome}")
        if type(self.interventions_saved) is not int:
            raise ValueError("interventions_saved must be an integer")

    @property
    def evidence_id(self) -> str:
        return _stable_digest(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SchemeEvidenceSummary:
    confirmations: int
    falsifications: int
    progress_events: int
    regressions: int
    heldout_confirmations: int
    interventions_saved: int


@dataclass(frozen=True, slots=True)
class SchemeEvidenceLedger:
    """Immutable unionable ledger; definitions never contain these values."""

    events: tuple[SchemeEvidence, ...] = ()

    def __post_init__(self) -> None:
        identifiers = tuple(item.evidence_id for item in self.events)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError("evidence must be sorted by hash and duplicate-free")

    @classmethod
    def create(
        cls, events: Iterable[SchemeEvidence] = ()
    ) -> "SchemeEvidenceLedger":
        by_id = {item.evidence_id: item for item in events}
        return cls(tuple(by_id[key] for key in sorted(by_id)))

    def append(self, event: SchemeEvidence) -> "SchemeEvidenceLedger":
        return self.create((*self.events, event))

    def merge(self, *others: "SchemeEvidenceLedger") -> "SchemeEvidenceLedger":
        return self.create(
            event for ledger in (self, *others) for event in ledger.events
        )

    @property
    def root(self) -> str:
        """Content hash of the complete immutable evidence history."""

        return _stable_digest([event.evidence_id for event in self.events])

    def summary(self, scheme_id: str) -> SchemeEvidenceSummary:
        relevant = tuple(
            event for event in self.events if event.scheme_id == scheme_id
        )
        return SchemeEvidenceSummary(
            confirmations=sum(
                item.outcome == "prediction-confirmed" for item in relevant
            ),
            falsifications=sum(
                item.outcome == "prediction-falsified" for item in relevant
            ),
            progress_events=sum(
                item.outcome == "level-progress" for item in relevant
            ),
            regressions=sum(item.outcome == "regression" for item in relevant),
            heldout_confirmations=sum(
                item.outcome == "prediction-confirmed"
                and item.partition.startswith("heldout:")
                for item in relevant
            ),
            interventions_saved=sum(
                item.interventions_saved for item in relevant
            ),
        )


@dataclass(frozen=True, slots=True)
class SchemePromotionRule:
    """Conservative cultural-inheritance gate."""

    minimum_confirmations: int = 2
    minimum_heldout_confirmations: int = 1
    minimum_progress_events: int = 1
    minimum_interventions_saved: int = 0

    def accepts(
        self, scheme_id: str, ledger: SchemeEvidenceLedger
    ) -> bool:
        evidence = ledger.summary(scheme_id)
        return (
            evidence.confirmations >= self.minimum_confirmations
            and evidence.heldout_confirmations
            >= self.minimum_heldout_confirmations
            and evidence.progress_events >= self.minimum_progress_events
            and evidence.interventions_saved
            >= self.minimum_interventions_saved
            and evidence.falsifications == 0
            and evidence.regressions == 0
        )


class SchemeAcceptanceRule(Protocol):
    """Structural interface shared by pragmatic and predictive gates."""

    def accepts(
        self,
        scheme_id: str,
        ledger: SchemeEvidenceLedger,
    ) -> bool: ...


@dataclass(frozen=True, slots=True)
class PredictivePromotionRule:
    """Admit calibrated knowledge without pretending it caused progress."""

    minimum_confirmations: int = 100
    minimum_heldout_confirmations: int = 100
    minimum_heldout_partitions: int = 2
    minimum_contributing_candidates: int = 2
    maximum_falsification_rate: float = 0.1

    def __post_init__(self) -> None:
        for name in (
            "minimum_confirmations",
            "minimum_heldout_confirmations",
            "minimum_heldout_partitions",
            "minimum_contributing_candidates",
        ):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        if not 0.0 <= self.maximum_falsification_rate < 1.0:
            raise ValueError(
                "maximum_falsification_rate must be in [0.0, 1.0)"
            )

    def accepts(
        self,
        scheme_id: str,
        ledger: SchemeEvidenceLedger,
    ) -> bool:
        relevant = tuple(
            event for event in ledger.events if event.scheme_id == scheme_id
        )
        confirmations = tuple(
            event
            for event in relevant
            if event.outcome == "prediction-confirmed"
        )
        falsifications = sum(
            event.outcome == "prediction-falsified" for event in relevant
        )
        heldout = tuple(
            event
            for event in confirmations
            if event.partition.startswith("heldout:")
        )
        predictions = len(confirmations) + falsifications
        return (
            len(confirmations) >= self.minimum_confirmations
            and len(heldout) >= self.minimum_heldout_confirmations
            and len({event.partition for event in heldout})
            >= self.minimum_heldout_partitions
            and len({event.candidate_id for event in confirmations})
            >= self.minimum_contributing_candidates
            and predictions > 0
            and falsifications / predictions
            <= self.maximum_falsification_rate
            and not any(event.outcome == "regression" for event in relevant)
        )


@dataclass(frozen=True, slots=True)
class CommonSenseSnapshot:
    """Versioned predictive knowledge plus the evidence that admitted it."""

    library: SchemeLibrary
    ledger: SchemeEvidenceLedger

    def __post_init__(self) -> None:
        if not self.library.definitions:
            raise ValueError("common-sense snapshot requires a definition")

    @property
    def root(self) -> str:
        return common_sense_root(self.library.root, self.ledger.root)


def promoted_library(
    proposals: SchemeLibrary,
    ledger: SchemeEvidenceLedger,
    rule: SchemeAcceptanceRule | None = None,
) -> SchemeLibrary:
    """Select definitions with evidence while retaining dependency closure."""

    promotion_rule: SchemeAcceptanceRule = rule or SchemePromotionRule()
    by_id = {item.scheme_id: item for item in proposals.definitions}
    retained = {
        item.scheme_id
        for item in proposals.definitions
        if promotion_rule.accepts(item.scheme_id, ledger)
    }
    frontier = list(retained)
    while frontier:
        definition = by_id[frontier.pop()]
        for dependency in definition.dependencies:
            if dependency not in retained:
                retained.add(dependency)
                frontier.append(dependency)
    return SchemeLibrary.create(by_id[item] for item in retained)


def predictive_common_sense_snapshot(
    proposals: SchemeLibrary,
    ledger: SchemeEvidenceLedger,
    rule: PredictivePromotionRule | None = None,
) -> CommonSenseSnapshot:
    """Freeze cross-agent calibrated definitions into one cultural root."""

    accepted = promoted_library(
        proposals,
        ledger,
        rule or PredictivePromotionRule(),
    )
    if not accepted.definitions:
        raise ValueError("no predictive definition cleared the cultural gate")
    return CommonSenseSnapshot(accepted, ledger)


def evidence_from_recording_audits(
    audits: Iterable[
        tuple[RecordingEventAudit, str, str]
    ],
    *,
    definition: SchemeDefinition = STABLE_REPEATED_FORM_ACTION_EFFECT,
) -> SchemeEvidenceLedger:
    """Compile recording predictions into an append-only cultural ledger.

    Each tuple contains ``(audit, candidate_id, partition)``. Confirmations and
    deviations remain separate evidence; a predictive gate, rather than this
    adapter, decides whether the calibrated error rate is acceptable.
    """

    events: list[SchemeEvidence] = []
    for audit, candidate_id, partition in audits:
        for index in range(audit.confirmations):
            events.append(
                SchemeEvidence(
                    scheme_id=definition.scheme_id,
                    candidate_id=candidate_id,
                    partition=partition,
                    episode_digest=audit.recording_sha256,
                    prediction_digest=_stable_digest(
                        {
                            "recording": audit.recording_sha256,
                            "outcome": "prediction-confirmed",
                            "index": index,
                        }
                    ),
                    outcome="prediction-confirmed",
                )
            )
        for occurrence in audit.occurrences:
            events.append(
                SchemeEvidence(
                    scheme_id=definition.scheme_id,
                    candidate_id=candidate_id,
                    partition=partition,
                    episode_digest=audit.recording_sha256,
                    prediction_digest=_stable_digest(occurrence.to_dict()),
                    outcome="prediction-falsified",
                )
            )
    return SchemeEvidenceLedger.create(events)


def accommodate_scheme(
    parent: SchemeDefinition,
    **changes: Any,
) -> SchemeDefinition:
    """Produce a new definition while preserving the parent as a dependency."""

    requested_dependencies = tuple(changes.pop("dependencies", ()))
    dependencies = tuple(
        sorted(set(requested_dependencies) | {parent.scheme_id})
    )
    return replace(parent, dependencies=dependencies, **changes)


def config_with_scheme_library(
    config: MindConfig,
    library: SchemeLibrary,
    *,
    enabled: bool = True,
) -> MindConfig:
    """Embed the exact validated snapshot in the deployable genome."""

    if enabled and not library.definitions:
        raise ValueError("cannot enable an empty inherited scheme library")
    return replace(
        config,
        enable_inherited_scheme_library=enabled,
        enable_preregistered_structural_credit=(
            True if enabled else config.enable_preregistered_structural_credit
        ),
        inherited_scheme_definitions=library.json_definitions(),
        inherited_scheme_root=library.root,
    )


def config_with_common_sense_snapshot(
    config: MindConfig,
    snapshot: CommonSenseSnapshot,
) -> MindConfig:
    """Embed exact definitions and both cultural evidence roots in a genome."""

    configured = config_with_scheme_library(config, snapshot.library)
    return replace(
        configured,
        inherited_evidence_root=snapshot.ledger.root,
        inherited_common_sense_root=snapshot.root,
    )


def _predicate_names(values: Iterable[str]) -> frozenset[str]:
    return frozenset(value.split("(", 1)[0] for value in values)


def evidence_from_cognitive_events(
    library: SchemeLibrary,
    events: Iterable[Mapping[str, Any]],
    *,
    candidate_id: str,
    partition: str,
) -> SchemeEvidenceLedger:
    """Compile only definition-specific preregistered predictions.

    A definition with no effect or externally observable goal contract cannot
    earn evidence merely by being active during an unrelated successful
    transition.
    """

    by_id = {item.scheme_id: item for item in library.definitions}
    output: list[SchemeEvidence] = []
    for event in events:
        deployment = event.get("deployment", {})
        if (
            isinstance(deployment, Mapping)
            and deployment.get("candidate_id") not in (None, candidate_id)
        ):
            raise ValueError("cognitive event belongs to another candidate")
        sequence = event.get("sequence")
        observation = event.get("observation", {})
        frame_digest = (
            observation.get("frame_digest")
            if isinstance(observation, Mapping)
            else None
        )
        construction = event.get("construction_delta", {})
        assessments = (
            construction.get("assessments", ())
            if isinstance(construction, Mapping)
            else ()
        )
        if not isinstance(assessments, (list, tuple)):
            continue
        for assessment in assessments:
            if not isinstance(assessment, Mapping):
                continue
            hypothesis_id = assessment.get("hypothesis_id")
            if not isinstance(hypothesis_id, str) or not hypothesis_id:
                continue
            components = assessment.get("scheme_components", ())
            if not isinstance(components, (list, tuple)):
                continue
            predicted = _predicate_names(
                item
                for item in assessment.get("predicted", ())
                if isinstance(item, str)
            )
            confirmed = _predicate_names(
                item
                for item in assessment.get("confirmed", ())
                if isinstance(item, str)
            )
            contradicted = _predicate_names(
                item
                for item in assessment.get("contradicted", ())
                if isinstance(item, str)
            )
            pragmatic = _predicate_names(
                item
                for item in assessment.get("pragmatic", ())
                if isinstance(item, str)
            )
            for component in components:
                if (
                    not isinstance(component, str)
                    or not component.startswith("scheme:inherited:")
                ):
                    continue
                scheme_id = component.rsplit(":", 1)[-1]
                definition = by_id.get(scheme_id)
                if definition is None:
                    raise ValueError(
                        f"assessment references unknown scheme {scheme_id}"
                    )
                effect_contract = _predicate_names(definition.effects)
                goal_contract = _predicate_names(definition.goal_contract)
                predicted_effects = effect_contract & predicted
                level_progress_contract = (
                    "level_advanced" in goal_contract
                    and "level_advanced" in pragmatic
                )
                outcome: EvidenceOutcome | None = None
                if level_progress_contract:
                    outcome = "level-progress"
                elif predicted_effects & contradicted:
                    outcome = "prediction-falsified"
                elif effect_contract and effect_contract <= confirmed:
                    outcome = "prediction-confirmed"
                if outcome is None:
                    continue
                output.append(
                    SchemeEvidence(
                        scheme_id=scheme_id,
                        candidate_id=candidate_id,
                        partition=partition,
                        episode_digest=_stable_digest(
                            {
                                "candidate_id": candidate_id,
                                "partition": partition,
                                "sequence": sequence,
                                "frame_digest": frame_digest,
                            }
                        ),
                        prediction_digest=_stable_digest(
                            {
                                "hypothesis_id": hypothesis_id,
                                "scheme_id": scheme_id,
                                "predicted": sorted(predicted),
                            }
                        ),
                        outcome=outcome,
                    )
                )
    return SchemeEvidenceLedger.create(output)


@dataclass(frozen=True, slots=True)
class InheritedBreedingResult:
    candidate: Candidate
    library: SchemeLibrary
    ledger: SchemeEvidenceLedger
    newly_promoted: tuple[str, ...]


def breed_inherited_candidate(
    parent: Candidate,
    *,
    proposal_libraries: Iterable[SchemeLibrary],
    evidence_ledgers: Iterable[SchemeEvidenceLedger],
    contributor_ids: Iterable[str] = (),
    source_fingerprint: str,
    rationale: str,
    rule: SchemeAcceptanceRule | None = None,
) -> InheritedBreedingResult:
    """Breed one exact offspring from evidence-clearing cultural artifacts."""

    parent_library = SchemeLibrary.from_json_definitions(
        parent.config.inherited_scheme_definitions
    )
    proposed = SchemeLibrary().merge(*tuple(proposal_libraries))
    ledger = SchemeEvidenceLedger().merge(*tuple(evidence_ledgers))
    additions = promoted_library(proposed, ledger, rule)
    inherited = parent_library.merge(additions)
    if not inherited.definitions:
        raise ValueError("no inherited schemes cleared the promotion gate")
    child = Candidate.create(
        config_with_scheme_library(parent.config, inherited),
        parent_id=parent.candidate_id,
        contributor_ids=tuple(contributor_ids),
        generation=parent.generation + 1,
        rationale=rationale,
        mutation_source="evidence-gated-scheme-breeding-v1",
        inference_fingerprint=source_fingerprint,
    )
    parent_ids = {item.scheme_id for item in parent_library.definitions}
    return InheritedBreedingResult(
        candidate=child,
        library=inherited,
        ledger=ledger,
        newly_promoted=tuple(
            item.scheme_id
            for item in additions.definitions
            if item.scheme_id not in parent_ids
        ),
    )
