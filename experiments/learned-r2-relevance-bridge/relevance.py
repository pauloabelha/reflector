"""R2-native learned relevance bridge for the preregistered experiment.

This module is deliberately experiment-local.  It consumes structural effects
already predicted by the frozen explanation mechanism and never sees action,
game, level, or coordinate identities while binding or ranking.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from reflector2.perception import PerceptionBatch
from reflector2.runtime import REFUTED, REIFIED, Runtime
from reflector2.store import SCHEMA_PROMOTED, SourceAtom


EffectAtom = tuple[str, tuple[str | int | float, ...]]
OUTCOMES = ("negative", "neutral", "positive")
TRANSFER_NAMES = {
    1: "exact-previous-consequence-binding",
    2: "different-binding-same-consequence-schema",
    3: "structurally-related-or-composed-consequence",
}


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def outcome_of(delta: float) -> str:
    if delta > 0:
        return "positive"
    if delta < 0:
        return "negative"
    return "neutral"


def normalize_effects(atoms: Iterable[EffectAtom]) -> tuple[EffectAtom, ...]:
    """Canonical, duplicate-free effect content with no carrier identity."""

    normalized: set[EffectAtom] = set()
    for head, arguments in atoms:
        if head not in {"Change", "Preserve"}:
            raise ValueError(f"unsupported consequence atom: {head}")
        values = tuple(arguments)
        if not values:
            raise ValueError("a consequence atom must have structural content")
        if any(isinstance(item, bool) for item in values):
            raise TypeError("boolean consequence arguments are not accepted")
        normalized.add((str(head), values))
    if not normalized:
        raise ValueError("a relevance observation requires at least one effect atom")
    return tuple(sorted(normalized, key=repr))


def effect_token(atom: EffectAtom) -> str:
    return _stable_json([atom[0], list(atom[1])])


def consequence_hash(effects: Sequence[EffectAtom]) -> str:
    return stable_hash([[head, list(arguments)] for head, arguments in effects])


def structural_binding_key(
    effects: Sequence[EffectAtom],
    observed_before_binding: Sequence[tuple[str, object]],
) -> str:
    """One shared class-1/2 fingerprint for collection and live prediction."""

    return stable_hash(
        {
            "effect": [[head, list(arguments)] for head, arguments in effects],
            "observed_before_binding": sorted(observed_before_binding, key=repr),
        }
    )


def relevance_atoms(effects: Sequence[EffectAtom], outcome: str) -> tuple[SourceAtom, ...]:
    if outcome not in OUTCOMES:
        raise ValueError(f"unknown progress outcome: {outcome}")
    return (
        ("Consequence", ("?c",)),
        *(("Effect", ("?c", effect_token(atom))) for atom in effects),
        ("ProgressOutcome", ("?c", outcome)),
    )


@dataclass(frozen=True, slots=True)
class RelevanceConfig:
    minimum_support: int = 2
    minimum_distinct_contexts: int = 2
    minimum_confidence: float = 2.0 / 3.0
    relevance_weight: float = 1.0
    max_commitments: int = 8
    permutation_seed: int = 1729

    def __post_init__(self) -> None:
        if self.minimum_support < 2:
            raise ValueError("promotion support must be at least two")
        if self.minimum_distinct_contexts < 2:
            raise ValueError("promotion requires at least two distinct contexts")
        if not 0.5 < self.minimum_confidence <= 1.0:
            raise ValueError("minimum confidence must be in (0.5, 1]")
        if self.relevance_weight <= 0.0:
            raise ValueError("relevance weight must be positive")
        if self.max_commitments < 1:
            raise ValueError("max commitments must be positive")


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """One consequence/progress pair, admitted only after its successor exists."""

    sequence: int
    event_id: str
    context_id: str
    trajectory_id: str
    pairing_stratum: str
    binding_key: str
    consequence: tuple[EffectAtom, ...]
    progress_delta: float
    opaque_action_id: int | None = None
    source: str = "observed-trajectory"

    @property
    def outcome(self) -> str:
        return outcome_of(self.progress_delta)

    @property
    def consequence_hash(self) -> str:
        return consequence_hash(self.consequence)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "EvidenceRecord":
        raw_consequence = value.get("consequence")
        if not isinstance(raw_consequence, list):
            raise ValueError("evidence consequence must be a list")
        atoms: list[EffectAtom] = []
        for raw in raw_consequence:
            if not isinstance(raw, list) or len(raw) != 2 or not isinstance(raw[1], list):
                raise ValueError("consequence atoms must be [head, [arguments...]]")
            atoms.append((str(raw[0]), tuple(raw[1])))
        action = value.get("opaque_action_id")
        if action is not None and type(action) is not int:
            raise TypeError("opaque_action_id must be an integer or null")
        record = cls(
            sequence=int(value["sequence"]),
            event_id=str(value["event_id"]),
            context_id=str(value["context_id"]),
            trajectory_id=str(value["trajectory_id"]),
            pairing_stratum=str(value["pairing_stratum"]),
            binding_key=str(value["binding_key"]),
            consequence=normalize_effects(atoms),
            progress_delta=float(value["progress_delta"]),
            opaque_action_id=action,
            source=str(value.get("source", "observed-trajectory")),
        )
        if not all(
            (
                record.event_id,
                record.context_id,
                record.trajectory_id,
                record.pairing_stratum,
                record.binding_key,
            )
        ):
            raise ValueError("evidence identifiers must be non-empty")
        return record

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_id": self.event_id,
            "context_id": self.context_id,
            "trajectory_id": self.trajectory_id,
            "pairing_stratum": self.pairing_stratum,
            "binding_key": self.binding_key,
            "consequence": [
                [head, list(arguments)] for head, arguments in self.consequence
            ],
            "progress_delta": self.progress_delta,
            "opaque_action_id": self.opaque_action_id,
            "source": self.source,
        }


def read_evidence(path: Path) -> tuple[EvidenceRecord, ...]:
    records: list[EvidenceRecord] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            records.append(EvidenceRecord.from_dict(json.loads(line)))
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise ValueError(f"{path}:{line_number}: {error}") from error
    validate_stream(records, name=str(path))
    return tuple(records)


def validate_stream(records: Sequence[EvidenceRecord], *, name: str) -> None:
    if not records:
        raise ValueError(f"{name} is empty")
    sequences = [item.sequence for item in records]
    if sequences != sorted(sequences) or len(sequences) != len(set(sequences)):
        raise ValueError(f"{name} sequence values must be unique and increasing")
    event_ids = [item.event_id for item in records]
    if len(event_ids) != len(set(event_ids)):
        raise ValueError(f"{name} event IDs must be unique")


@dataclass(frozen=True, slots=True)
class FrozenRelevanceSchema:
    schema_hash: str
    consequence: tuple[EffectAtom, ...]
    consequence_hash: str
    outcome: str
    support: int
    contradictions: int
    distinct_contexts: int
    confidence: float
    support_event_ids: tuple[str, ...]
    contradiction_event_ids: tuple[str, ...]
    observed_binding_keys: tuple[str, ...]
    source: str = "learned-relevance"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "FrozenRelevanceSchema":
        effects = normalize_effects(
            (str(head), tuple(arguments))
            for head, arguments in value["consequence"]
        )
        return cls(
            schema_hash=str(value["schema_hash"]),
            consequence=effects,
            consequence_hash=str(value["consequence_hash"]),
            outcome=str(value["outcome"]),
            support=int(value["support"]),
            contradictions=int(value["contradictions"]),
            distinct_contexts=int(value["distinct_contexts"]),
            confidence=float(value["confidence"]),
            support_event_ids=tuple(map(str, value["support_event_ids"])),
            contradiction_event_ids=tuple(
                map(str, value["contradiction_event_ids"])
            ),
            observed_binding_keys=tuple(map(str, value["observed_binding_keys"])),
            source=str(value.get("source", "learned-relevance")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "consequence": [
                [head, list(arguments)] for head, arguments in self.consequence
            ],
            "support_event_ids": list(self.support_event_ids),
            "contradiction_event_ids": list(self.contradiction_event_ids),
            "observed_binding_keys": list(self.observed_binding_keys),
        }


@dataclass(frozen=True, slots=True)
class RelevanceSnapshot:
    version: str
    config: RelevanceConfig
    schemas: tuple[FrozenRelevanceSchema, ...]
    training_event_digest: str
    training_events: int
    training_outcomes: tuple[tuple[str, int], ...]
    positive_training_events: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "config": asdict(self.config),
            "schemas": [schema.to_dict() for schema in self.schemas],
            "training_event_digest": self.training_event_digest,
            "training_events": self.training_events,
            "training_outcomes": dict(self.training_outcomes),
            "positive_training_events": self.positive_training_events,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RelevanceSnapshot":
        return cls(
            version=str(value["version"]),
            config=RelevanceConfig(**value["config"]),
            schemas=tuple(
                FrozenRelevanceSchema.from_dict(item) for item in value["schemas"]
            ),
            training_event_digest=str(value["training_event_digest"]),
            training_events=int(value["training_events"]),
            training_outcomes=tuple(
                sorted((str(key), int(count)) for key, count in value["training_outcomes"].items())
            ),
            positive_training_events=int(value["positive_training_events"]),
        )

    @classmethod
    def read(cls, path: Path) -> "RelevanceSnapshot":
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


class RelevanceTrainer:
    """Chronological construction and promotion of consequence/progress schemas."""

    def __init__(self, config: RelevanceConfig | None = None) -> None:
        self.config = config or RelevanceConfig()
        self.runtime = Runtime()
        self._schema_by_key: dict[tuple[str, str], int] = {}
        self._records_by_consequence: dict[str, list[EvidenceRecord]] = defaultdict(list)
        self._support_events: dict[int, list[str]] = defaultdict(list)
        self._contradiction_events: dict[int, list[str]] = defaultdict(list)
        self._bindings: dict[int, set[str]] = defaultdict(set)
        self._records: list[EvidenceRecord] = []

    @staticmethod
    def _context_token(record: EvidenceRecord) -> str:
        # Context identity is used only to enforce independent support.  Its
        # content never enters a schema, match, or ranking feature.
        return f"observed-context:{stable_hash(record.context_id)}"

    def _ensure_schema(self, record: EvidenceRecord) -> int:
        key = (record.consequence_hash, record.outcome)
        found = self._schema_by_key.get(key)
        if found is not None:
            return found
        schema_id, _created = self.runtime.graph.add_schema(
            "LearnedRelevance",
            relevance_atoms(record.consequence, record.outcome),
            provenance="experience:observed-consequence-progress",
        )
        self._schema_by_key[key] = schema_id
        # Evidence that preceded the first occurrence of this outcome is still
        # valid contradiction evidence for the newly constructed schema.
        for prior in self._records_by_consequence[record.consequence_hash]:
            if prior.outcome != record.outcome:
                self.runtime.graph.add_evidence(
                    schema_id,
                    "contradiction",
                    1,
                    self._context_token(prior),
                    prior.sequence,
                    source="experience:observed-alternative-progress",
                )
                self._contradiction_events[schema_id].append(prior.event_id)
        return schema_id

    def observe(self, record: EvidenceRecord) -> None:
        if self._records and record.sequence <= self._records[-1].sequence:
            raise ValueError("training evidence must be observed in strict sequence order")
        if any(item.event_id == record.event_id for item in self._records):
            raise ValueError(f"duplicate training event: {record.event_id}")
        schema_id = self._ensure_schema(record)
        context = self._context_token(record)
        self.runtime.graph.add_evidence(
            schema_id,
            "support",
            1,
            context,
            record.sequence,
            source=record.source,
        )
        self._support_events[schema_id].append(record.event_id)
        self._bindings[schema_id].add(record.binding_key)
        for (candidate_hash, candidate_outcome), other_id in sorted(
            self._schema_by_key.items()
        ):
            if candidate_hash == record.consequence_hash and candidate_outcome != record.outcome:
                self.runtime.graph.add_evidence(
                    other_id,
                    "contradiction",
                    1,
                    context,
                    record.sequence,
                    source="experience:observed-alternative-progress",
                )
                self._contradiction_events[other_id].append(record.event_id)
        self._records_by_consequence[record.consequence_hash].append(record)
        self._records.append(record)

    def freeze(self) -> RelevanceSnapshot:
        if not self._records:
            raise ValueError("cannot freeze an empty relevance stream")
        promoted: list[FrozenRelevanceSchema] = []
        for (effect_hash, outcome), schema_id in sorted(self._schema_by_key.items()):
            graph = self.runtime.graph
            support = graph.support[schema_id]
            contexts = len(graph.support_contexts[schema_id])
            if (
                graph.schema_state[schema_id] != SCHEMA_PROMOTED
                or support < self.config.minimum_support
                or contexts < self.config.minimum_distinct_contexts
            ):
                continue
            contradictions = graph.contradiction[schema_id]
            confidence = (support + 1.0) / (support + contradictions + 2.0)
            effects = self._records_by_consequence[effect_hash][0].consequence
            promoted.append(
                FrozenRelevanceSchema(
                    schema_hash=graph.canonical_hash[schema_id],
                    consequence=effects,
                    consequence_hash=effect_hash,
                    outcome=outcome,
                    support=support,
                    contradictions=contradictions,
                    distinct_contexts=contexts,
                    confidence=confidence,
                    support_event_ids=tuple(self._support_events[schema_id]),
                    contradiction_event_ids=tuple(
                        self._contradiction_events[schema_id]
                    ),
                    observed_binding_keys=tuple(sorted(self._bindings[schema_id])),
                )
            )
        counts = Counter(record.outcome for record in self._records)
        return RelevanceSnapshot(
            version="r2-native-relevance/v1",
            config=self.config,
            schemas=tuple(sorted(promoted, key=lambda item: item.schema_hash)),
            training_event_digest=stable_hash(
                [record.to_dict() for record in self._records]
            ),
            training_events=len(self._records),
            training_outcomes=tuple((name, counts[name]) for name in OUTCOMES),
            positive_training_events=counts["positive"],
        )


def train_snapshot(
    records: Sequence[EvidenceRecord], config: RelevanceConfig | None = None
) -> RelevanceSnapshot:
    validate_stream(records, name="learning stream")
    if not any(record.progress_delta > 0 for record in records):
        raise ValueError("learning stream has no genuine positive progress")
    trainer = RelevanceTrainer(config)
    for record in records:
        trainer.observe(record)
    return trainer.freeze()


@dataclass(frozen=True, slots=True)
class ValueMatch:
    relevance_schema_hash: str
    consequence_hash: str
    outcome: str
    confidence: float
    support: int
    contradictions: int
    distinct_contexts: int
    transfer_class: int
    transfer_name: str
    support_event_ids: tuple[str, ...]
    contradiction_event_ids: tuple[str, ...]
    candidate_consequence_hash: str
    candidate_binding_key: str

    @property
    def signed_value(self) -> float:
        if self.outcome == "positive":
            return self.confidence
        if self.outcome == "negative":
            return -self.confidence
        return 0.0


def value_match_receipt(match: ValueMatch) -> dict[str, Any]:
    """Serialize a match without repeating the frozen schema's evidence lists.

    ``relevance_schema_hash`` is the exact join key into the immutable snapshot,
    where the complete event IDs remain available. Counts and ordered digests
    make that provenance linkage independently checkable in compact traces.
    """

    receipt = asdict(match)
    support_event_ids = receipt.pop("support_event_ids")
    contradiction_event_ids = receipt.pop("contradiction_event_ids")
    receipt["provenance"] = {
        "frozen_relevance_schema_hash": match.relevance_schema_hash,
        "support_event_count": len(support_event_ids),
        "support_event_digest": stable_hash(support_event_ids),
        "contradiction_event_count": len(contradiction_event_ids),
        "contradiction_event_digest": stable_hash(contradiction_event_ids),
    }
    return receipt


def match_snapshot(
    snapshot: RelevanceSnapshot,
    effects: Sequence[EffectAtom],
    binding_key: str,
    *,
    eligible_only: bool = True,
) -> tuple[ValueMatch, ...]:
    candidate = normalize_effects(effects)
    candidate_set = set(candidate)
    candidate_hash = consequence_hash(candidate)
    matches: list[ValueMatch] = []
    for schema in snapshot.schemas:
        if not set(schema.consequence) <= candidate_set:
            continue
        if eligible_only and schema.confidence < snapshot.config.minimum_confidence:
            continue
        if candidate_hash == schema.consequence_hash:
            transfer = 1 if binding_key in schema.observed_binding_keys else 2
        else:
            transfer = 3
        matches.append(
            ValueMatch(
                relevance_schema_hash=schema.schema_hash,
                consequence_hash=schema.consequence_hash,
                outcome=schema.outcome,
                confidence=schema.confidence,
                support=schema.support,
                contradictions=schema.contradictions,
                distinct_contexts=schema.distinct_contexts,
                transfer_class=transfer,
                transfer_name=TRANSFER_NAMES[transfer],
                support_event_ids=schema.support_event_ids,
                contradiction_event_ids=schema.contradiction_event_ids,
                candidate_consequence_hash=candidate_hash,
                candidate_binding_key=binding_key,
            )
        )
    return tuple(
        sorted(
            matches,
            key=lambda item: (
                -item.confidence,
                -item.support,
                item.relevance_schema_hash,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class OfflineForecast:
    event_id: str
    predicted_outcome: str | None
    positive_probability: float | None
    matches: tuple[ValueMatch, ...]


def forecast_effect(
    snapshot: RelevanceSnapshot,
    *,
    event_id: str,
    effects: Sequence[EffectAtom],
    binding_key: str,
) -> OfflineForecast:
    """Make a forecast from C alone; the outcome is intentionally absent."""

    matches = match_snapshot(snapshot, effects, binding_key)
    if not matches:
        return OfflineForecast(event_id, None, None, ())
    by_outcome: dict[str, list[ValueMatch]] = defaultdict(list)
    for match in matches:
        by_outcome[match.outcome].append(match)
    scores = {
        outcome: sum(item.confidence for item in values) / len(values)
        for outcome, values in by_outcome.items()
    }
    predicted = sorted(scores, key=lambda item: (-scores[item], item))[0]
    signed = sum(item.signed_value for item in matches) / len(matches)
    positive_probability = max(0.0, min(1.0, 0.5 + signed / 2.0))
    return OfflineForecast(event_id, predicted, positive_probability, matches)


def evaluate_snapshot(
    snapshot: RelevanceSnapshot, records: Sequence[EvidenceRecord]
) -> dict[str, Any]:
    validate_stream(records, name="held-out stream")
    forecasts: list[tuple[OfflineForecast, EvidenceRecord]] = []
    for record in records:
        # This call boundary is the leakage audit: no field derived from the
        # successor progress is passed into forecast_effect.
        forecast = forecast_effect(
            snapshot,
            event_id=record.event_id,
            effects=record.consequence,
            binding_key=record.binding_key,
        )
        forecasts.append((forecast, record))
    covered = [(forecast, record) for forecast, record in forecasts if forecast.predicted_outcome]
    positive = [
        (forecast, record)
        for forecast, record in covered
        if forecast.predicted_outcome == "positive"
    ]
    positive_correct = sum(record.progress_delta > 0 for _forecast, record in positive)
    categorical_correct = sum(
        forecast.predicted_outcome == record.outcome for forecast, record in covered
    )
    calibration = [
        (forecast.positive_probability, int(record.progress_delta > 0))
        for forecast, record in covered
        if forecast.positive_probability is not None
    ]
    successful_transfer = Counter()
    for forecast, record in covered:
        for match in forecast.matches:
            if match.outcome == record.outcome:
                successful_transfer[str(match.transfer_class)] += 1
    return {
        "events": len(records),
        "covered_events": len(covered),
        "bridge_coverage": len(covered) / len(records),
        "positive_commitments": len(positive),
        "positive_commitments_correct": positive_correct,
        "prospective_positive_precision": (
            positive_correct / len(positive) if positive else None
        ),
        "categorical_accuracy": (
            categorical_correct / len(covered) if covered else None
        ),
        "brier_score": (
            sum((float(probability) - actual) ** 2 for probability, actual in calibration)
            / len(calibration)
            if calibration
            else None
        ),
        "successful_transfer_classes": {
            name: successful_transfer[str(index)]
            for index, name in TRANSFER_NAMES.items()
        },
        "forecasts": [
            {
                "event_id": forecast.event_id,
                "predicted_outcome": forecast.predicted_outcome,
                "true_outcome": record.outcome,
                "positive_probability": forecast.positive_probability,
                "matches": [value_match_receipt(match) for match in forecast.matches],
            }
            for forecast, record in forecasts
        ],
    }


def _rotate_group(
    items: list[EvidenceRecord],
    seed: int,
    key: str,
    *,
    signature: Any,
) -> list[EvidenceRecord]:
    if len(items) < 2:
        return list(items)
    local = random.Random(int(stable_hash([seed, key])[:16], 16))
    scores = {
        offset: sum(
            signature(item) != signature(items[(index + offset) % len(items)])
            for index, item in enumerate(items)
        )
        for offset in range(1, len(items))
    }
    best = max(scores.values())
    offsets = [offset for offset, score in scores.items() if score == best]
    offset = local.choice(offsets)
    return items[offset:] + items[:offset]


def permute_reward_labels(
    records: Sequence[EvidenceRecord], *, seed: int
) -> tuple[tuple[EvidenceRecord, ...], dict[str, int]]:
    """Null A: permute labels within trajectories, preserving every C/action."""

    by_trajectory: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in records:
        by_trajectory[record.trajectory_id].append(record)
    replacement: dict[str, float] = {}
    for trajectory, group in sorted(by_trajectory.items()):
        donors = _rotate_group(
            group,
            seed,
            f"reward:{trajectory}",
            signature=lambda item: item.progress_delta,
        )
        replacement.update(
            (recipient.event_id, donor.progress_delta)
            for recipient, donor in zip(group, donors, strict=True)
        )
    permuted = tuple(
        replace(record, progress_delta=replacement[record.event_id])
        for record in records
    )
    return permuted, {
        "events": len(records),
        "labels_moved": sum(
            left.progress_delta != right.progress_delta
            for left, right in zip(records, permuted, strict=True)
        ),
        "trajectory_groups": len(by_trajectory),
    }


def permute_consequence_pairing(
    records: Sequence[EvidenceRecord], *, seed: int
) -> tuple[tuple[EvidenceRecord, ...], dict[str, int]]:
    """Null B: permute C within matched context strata, preserving outcomes."""

    by_stratum: dict[str, list[EvidenceRecord]] = defaultdict(list)
    for record in records:
        by_stratum[record.pairing_stratum].append(record)
    replacement: dict[str, EvidenceRecord] = {}
    for stratum, group in sorted(by_stratum.items()):
        donors = _rotate_group(
            group,
            seed,
            f"pairing:{stratum}",
            signature=lambda item: item.consequence_hash,
        )
        replacement.update(
            (recipient.event_id, donor)
            for recipient, donor in zip(group, donors, strict=True)
        )
    permuted = tuple(
        replace(
            record,
            consequence=replacement[record.event_id].consequence,
            binding_key=replacement[record.event_id].binding_key,
        )
        for record in records
    )
    return permuted, {
        "events": len(records),
        "consequences_moved": sum(
            left.consequence_hash != right.consequence_hash
            for left, right in zip(records, permuted, strict=True)
        ),
        "matched_strata": len(by_stratum),
    }


def run_offline_controls(
    learning: Sequence[EvidenceRecord],
    held_out: Sequence[EvidenceRecord],
    config: RelevanceConfig,
) -> dict[str, Any]:
    true_snapshot = train_snapshot(learning, config)
    null_a_records, null_a_permutation = permute_reward_labels(
        learning, seed=config.permutation_seed
    )
    null_b_records, null_b_permutation = permute_consequence_pairing(
        learning, seed=config.permutation_seed
    )
    snapshots: dict[str, RelevanceSnapshot | None] = {"real": true_snapshot}
    failures: dict[str, str] = {}
    for name, records in (("null_a", null_a_records), ("null_b", null_b_records)):
        try:
            snapshots[name] = train_snapshot(records, config)
        except ValueError as error:
            snapshots[name] = None
            failures[name] = str(error)
    evaluations = {
        name: (
            evaluate_snapshot(snapshot, held_out)
            if snapshot is not None
            else {
                "events": len(held_out),
                "covered_events": 0,
                "bridge_coverage": 0.0,
                "positive_commitments": 0,
                "positive_commitments_correct": 0,
                "prospective_positive_precision": None,
                "categorical_accuracy": None,
                "brier_score": None,
                "successful_transfer_classes": dict.fromkeys(
                    TRANSFER_NAMES.values(), 0
                ),
                "forecasts": [],
            }
        )
        for name, snapshot in snapshots.items()
    }
    return {
        "snapshot": true_snapshot,
        "evaluations": evaluations,
        "permutations": {
            "null_a_reward_label": null_a_permutation,
            "null_b_consequence_pairing": null_b_permutation,
        },
        "null_training_failures": failures,
        "null_schema_counts": {
            name: 0 if snapshot is None else len(snapshot.schemas)
            for name, snapshot in snapshots.items()
            if name != "real"
        },
    }


@dataclass(frozen=True, slots=True)
class BridgePrediction:
    action_id: int
    transition_schema_hash: str
    effects: tuple[EffectAtom, ...]
    binding_key: str
    matches: tuple[ValueMatch, ...]
    value: float


@dataclass(frozen=True, slots=True)
class BridgeActionRank:
    action_id: int
    explanation_score: float
    relevance_value: float
    combined_score: float
    eligible_matches: int


@dataclass(frozen=True, slots=True)
class ProgressCommitment:
    shadow_id: int
    action_id: int
    carrier: str
    match: ValueMatch


@dataclass(slots=True)
class BridgeDecision:
    decision_id: int
    explanation_action_id: int
    selected_action_id: int
    rankings: tuple[BridgeActionRank, ...]
    predictions: tuple[BridgePrediction, ...]
    commitments: tuple[ProgressCommitment, ...]
    changed_from_explanation: bool
    gate_passed: bool
    gate_reason: str


@dataclass(slots=True)
class BridgeMetrics:
    decisions: int = 0
    covered_decisions: int = 0
    promoted_schema_matches: int = 0
    prospective_progress_commitments: int = 0
    reifications: int = 0
    refutations: int = 0
    arm4_action_changes: int = 0
    positive_progress_after_changes: int = 0
    regressions_after_changes: int = 0
    level_completions_after_changes: int = 0
    calibration: list[tuple[float, int]] = field(default_factory=list)
    successful_transfer_classes: dict[str, int] = field(
        default_factory=lambda: dict.fromkeys(TRANSFER_NAMES.values(), 0)
    )
    action_changes_by_group: dict[str, int] = field(default_factory=dict)


class RelevanceBridge:
    """Frozen schema matcher, final action gate, and R2 shadow reconciler."""

    def __init__(self, snapshot: RelevanceSnapshot) -> None:
        self.snapshot = snapshot
        self.runtime = Runtime()
        self.metrics = BridgeMetrics()
        self._decision = 0
        self._schema_ids: dict[str, int] = {}
        for schema in snapshot.schemas:
            schema_id, _created = self.runtime.graph.add_schema(
                "FrozenLearnedRelevance",
                relevance_atoms(schema.consequence, schema.outcome),
                provenance=f"frozen:{snapshot.training_event_digest}",
            )
            if self.runtime.graph.canonical_hash[schema_id] != schema.schema_hash:
                raise ValueError("frozen relevance schema hash changed during import")
            self.runtime.graph.schema_state[schema_id] = SCHEMA_PROMOTED
            self.runtime.graph.support[schema_id] = schema.support
            self.runtime.graph.contradiction[schema_id] = schema.contradictions
            self._schema_ids[schema.schema_hash] = schema_id

    def _project(self, match: ValueMatch, action_id: int) -> ProgressCommitment:
        schema_id = self._schema_ids[match.relevance_schema_hash]
        carrier = f"relevance-decision:{self._decision}:action:{action_id}:schema:{match.relevance_schema_hash[:12]}"
        carrier_term = self.runtime.graph.terms.intern_symbol(carrier)
        constraints = self.runtime.graph.definition_constraint_atoms(schema_id)
        verified = {
            index
            for index, (head, _arguments) in enumerate(constraints)
            if head == "Consequence"
        }
        shadow = self.runtime.project_shadow(
            schema_id,
            {0: carrier_term},
            verified_constraints=verified,
            carrier=carrier,
            provenance=f"promoted-relevance:{match.relevance_schema_hash}",
            prospective_action=True,
        )
        return ProgressCommitment(shadow.shadow_id, action_id, carrier, match)

    def decide(
        self,
        explanation_decision: Any,
        *,
        transition_hashes: Mapping[int, str],
        binding_keys: Mapping[int, str],
    ) -> BridgeDecision:
        """Apply relevance only after the frozen explanation decision exists."""

        self._decision += 1
        # The relevance runtime is intentionally isolated from sensory
        # observation, so advance its bounded-work cycle explicitly once per
        # prospective decision.
        self.runtime.cycle += 1
        self.runtime.trace.append(
            {
                "event": "relevance-decision-cycle",
                "cycle": self.runtime.cycle,
                "decision": self._decision,
            }
        )
        self.metrics.decisions += 1
        predictions: list[BridgePrediction] = []
        matches_by_action: dict[int, list[ValueMatch]] = defaultdict(list)
        for prediction_index, prediction in enumerate(explanation_decision.predictions):
            key = binding_keys[prediction_index]
            matches = match_snapshot(self.snapshot, prediction.signature, key)
            if matches:
                matches_by_action[prediction.action_id].extend(matches)
                predictions.append(
                    BridgePrediction(
                        action_id=prediction.action_id,
                        transition_schema_hash=transition_hashes[prediction_index],
                        effects=normalize_effects(prediction.signature),
                        binding_key=key,
                        matches=matches,
                        value=sum(item.signed_value for item in matches) / len(matches),
                    )
                )
        if matches_by_action:
            self.metrics.covered_decisions += 1
        self.metrics.promoted_schema_matches += sum(
            len(items) for items in matches_by_action.values()
        )
        base_ranks = {item.action_id: item for item in explanation_decision.rankings}
        rankings: list[BridgeActionRank] = []
        for action_id, base in sorted(base_ranks.items()):
            matches = matches_by_action.get(action_id, [])
            relevance = (
                sum(item.signed_value for item in matches) / len(matches)
                if matches
                else 0.0
            )
            rankings.append(
                BridgeActionRank(
                    action_id=action_id,
                    explanation_score=float(base.score),
                    relevance_value=relevance,
                    combined_score=float(base.score)
                    + self.snapshot.config.relevance_weight * relevance,
                    eligible_matches=len(matches),
                )
            )
        rankings.sort(
            key=lambda item: (
                -item.combined_score,
                item.action_id != explanation_decision.selected_action_id,
                item.action_id,
            )
        )
        proposed = rankings[0].action_id
        changed = proposed != explanation_decision.selected_action_id
        selected_matches = matches_by_action.get(proposed, [])
        if not changed:
            selected = explanation_decision.selected_action_id
            gate_reason = "no-relevance-divergence"
            gate_passed = False
        elif not selected_matches:
            selected = explanation_decision.selected_action_id
            gate_reason = "divergent-action-has-no-promoted-match"
            gate_passed = False
        elif max(item.confidence for item in selected_matches) < self.snapshot.config.minimum_confidence:
            selected = explanation_decision.selected_action_id
            gate_reason = "below-frozen-confidence-threshold"
            gate_passed = False
        else:
            selected = proposed
            gate_reason = "promoted-schema-falsifiable-divergence"
            gate_passed = True
        commitments: list[ProgressCommitment] = []
        if gate_passed:
            unique: set[tuple[str, str, str]] = set()
            for match in selected_matches:
                identity = (
                    match.relevance_schema_hash,
                    match.candidate_consequence_hash,
                    match.candidate_binding_key,
                )
                if identity in unique:
                    continue
                unique.add(identity)
                if len(commitments) >= self.snapshot.config.max_commitments:
                    break
                try:
                    commitments.append(self._project(match, selected))
                except (RuntimeError, ValueError):
                    continue
            if not commitments:
                selected = explanation_decision.selected_action_id
                gate_reason = "progress-commitment-could-not-be-projected"
                gate_passed = False
        changed = selected != explanation_decision.selected_action_id
        if changed:
            self.metrics.arm4_action_changes += 1
        self.metrics.prospective_progress_commitments += len(commitments)
        return BridgeDecision(
            decision_id=self._decision,
            explanation_action_id=explanation_decision.selected_action_id,
            selected_action_id=selected,
            rankings=tuple(rankings),
            predictions=tuple(predictions),
            commitments=tuple(commitments),
            changed_from_explanation=changed,
            gate_passed=gate_passed,
            gate_reason=gate_reason,
        )

    def decision_trace(self, decision: BridgeDecision) -> dict[str, Any]:
        return {
            "event": "learned-relevance-decision",
            "decision": decision.decision_id,
            "frozen_explanation_selected": decision.explanation_action_id,
            "selected": decision.selected_action_id,
            "changed_from_explanation": decision.changed_from_explanation,
            "diagnostic_gate": {
                "passed": decision.gate_passed,
                "reason": decision.gate_reason,
                "minimum_confidence": self.snapshot.config.minimum_confidence,
            },
            "action_ranking": [asdict(item) for item in decision.rankings],
            "predictions": [
                {
                    **{key: value for key, value in asdict(item).items() if key != "matches"},
                    "effects": [[head, list(args)] for head, args in item.effects],
                    "matches": [value_match_receipt(match) for match in item.matches],
                }
                for item in decision.predictions
            ],
            "prospective_progress_commitments": [
                {
                    "shadow": item.shadow_id,
                    "action": item.action_id,
                    "predicted_outcome": item.match.outcome,
                    "relevance_schema": item.match.relevance_schema_hash,
                    "confidence": item.match.confidence,
                    "transfer_class": item.match.transfer_class,
                    "provenance": {
                        "support_events": list(item.match.support_event_ids),
                        "contradiction_events": list(
                            item.match.contradiction_event_ids
                        ),
                    },
                }
                for item in decision.commitments
            ],
        }

    def observe_outcome(
        self,
        decision: BridgeDecision,
        *,
        observed_effects: Sequence[EffectAtom],
        progress_delta: float,
        report_group: str,
    ) -> dict[str, Any]:
        observed_effects = (
            normalize_effects(observed_effects) if observed_effects else ()
        )
        actual_outcome = outcome_of(progress_delta)
        resolutions = []
        for commitment in decision.commitments:
            terms = self.runtime.graph.terms
            facts = [terms.ground_atom("Consequence", (commitment.carrier,))]
            facts.extend(
                terms.ground_atom("Effect", (commitment.carrier, effect_token(atom)))
                for atom in observed_effects
            )
            facts.append(
                terms.ground_atom(
                    "ProgressOutcome", (commitment.carrier, actual_outcome)
                )
            )
            observed = PerceptionBatch(
                context=f"relevance-outcome:{decision.decision_id}:{commitment.shadow_id}",
                facts=tuple(facts),
                form_terms=(),
                region_terms=(),
                outline_terms=(),
                source="experience:observed-consequence-progress",
            )
            if self.runtime.reconcile_shadow(commitment.shadow_id, observed):
                status = REIFIED
                self.metrics.reifications += 1
                self.metrics.successful_transfer_classes[
                    commitment.match.transfer_name
                ] += 1
            else:
                shadow = self.runtime.shadows[commitment.shadow_id]
                constraints = self.runtime.graph.definition_constraint_atoms(
                    shadow.schema_id
                )
                actual_effect_tokens = {
                    effect_token(atom) for atom in observed_effects
                }
                incompatible = set()
                for index in shadow.open_constraints:
                    head, arguments = constraints[index]
                    if (
                        head == "Effect"
                        and len(arguments) == 2
                        and str(arguments[1]) not in actual_effect_tokens
                    ):
                        incompatible.add(index)
                    elif (
                        head == "ProgressOutcome"
                        and len(arguments) == 2
                        and str(arguments[1]) != actual_outcome
                    ):
                        incompatible.add(index)
                if not incompatible:
                    raise RuntimeError(
                        "relevance shadow failed without positive structural contradiction"
                    )
                self.runtime.refute_shadow(
                    commitment.shadow_id,
                    incompatible_constraints=incompatible,
                    contradictory_evidence=observed.facts,
                    context=observed.context,
                    provenance="experience:observed-progress-refutation",
                )
                status = REFUTED
                self.metrics.refutations += 1
            resolutions.append(
                {
                    "shadow": commitment.shadow_id,
                    "status": status,
                    "predicted_outcome": commitment.match.outcome,
                    "observed_outcome": actual_outcome,
                    "relevance_schema": commitment.match.relevance_schema_hash,
                    "transfer_class": commitment.match.transfer_class,
                }
            )
        if decision.changed_from_explanation:
            self.metrics.action_changes_by_group[report_group] = (
                self.metrics.action_changes_by_group.get(report_group, 0) + 1
            )
            if progress_delta > 0:
                self.metrics.positive_progress_after_changes += 1
                self.metrics.level_completions_after_changes += int(progress_delta)
            elif progress_delta < 0:
                self.metrics.regressions_after_changes += 1
            selected_predictions = [
                item
                for item in decision.predictions
                if item.action_id == decision.selected_action_id
            ]
            if selected_predictions:
                value = sum(item.value for item in selected_predictions) / len(
                    selected_predictions
                )
                probability = max(0.0, min(1.0, 0.5 + value / 2.0))
                self.metrics.calibration.append(
                    (probability, int(progress_delta > 0))
                )
        return {
            "event": "learned-relevance-resolution",
            "decision": decision.decision_id,
            "selected": decision.selected_action_id,
            "changed_from_explanation": decision.changed_from_explanation,
            "progress_delta": progress_delta,
            "observed_effects": [
                [head, list(arguments)] for head, arguments in observed_effects
            ],
            "resolutions": resolutions,
        }

    def report(self) -> dict[str, Any]:
        changes = self.metrics.arm4_action_changes
        calibration = self.metrics.calibration
        group_counts = self.metrics.action_changes_by_group
        return {
            **asdict(self.metrics),
            "promoted_relevance_schemas": len(self.snapshot.schemas),
            "bridge_coverage": (
                self.metrics.covered_decisions / self.metrics.decisions
                if self.metrics.decisions
                else 0.0
            ),
            "bridge_precision": (
                self.metrics.positive_progress_after_changes / changes
                if changes
                else None
            ),
            "regression_rate": (
                self.metrics.regressions_after_changes / changes
                if changes
                else None
            ),
            "brier_score": (
                sum((probability - actual) ** 2 for probability, actual in calibration)
                / len(calibration)
                if calibration
                else None
            ),
            "macro_groups_with_action_change": sum(
                count > 0 for count in group_counts.values()
            ),
            "max_group_action_change_share": (
                max(group_counts.values(), default=0) / changes if changes else None
            ),
        }
