"""Preregistered v8 validation for represented language invention."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass

from ..core.abstraction import AbstractionStore
from ..core.causal import HypothesisStore
from ..core.graph import DependencyGraph
from ..core.schemas import ConceptStore, SchemaStore
from ..core.symbolic import Atom, Event, Transition

_STRATEGY = "compile-enumerated-cyclic-predicates"
_INPUT_FORM = "predicate_stem_discrete_magnitude(object)"
_OUTPUT_FORM = "typed_group_operator(object,k)"
_SIGNATURE = "orientation_delta(object,k)"
_ALGEBRA = "k in Z4; compose(a,b)=(a+b) mod 4"
_REQUIRED_DISTINCT = 3
_MINIMUM_SUPPORT = 4


@dataclass(frozen=True, slots=True)
class LanguageValidationRun:
    seed: int
    evidence_hash_enabled: str
    evidence_hash_ablated: str
    strong_oracle_accepts: bool
    weak_oracle_rejects: bool
    early_rejected_proposals: int
    operator_count: int
    validated_mechanism_count: int
    mechanism_utility: float
    ablation_proposal_count: int
    ablation_operator_count: int
    weak_accepted_operator_count: int
    noncyclic_proposal_count: int
    noncyclic_operator_count: int
    held_out_normalized: bool
    ablation_held_out_unchanged: bool
    provenance_valid: bool
    held_out_leaks: int
    structurally_idempotent: bool


def _observe(
    store: SchemaStore,
    *,
    index: int,
    context: tuple[Atom, ...],
    action: int,
    kind: str,
    subject: str,
) -> None:
    store.observe(
        Transition(
            before_index=index,
            after_index=index + 1,
            context=context,
            action_id=action,
            action_data=(),
            result=(Event(kind, subject),),
        )
    )


def _evidence_hash(store: SchemaStore) -> str:
    canonical = json.dumps(
        store.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _oracle(
    support: dict[str, int],
    *,
    complexity_pressure: float = 1.0,
) -> tuple[bool, float, float]:
    total_support = sum(support.values())
    raw = sum(len(predicate) * count for predicate, count in support.items())
    operator_complexity = len(_SIGNATURE) + len(_ALGEBRA)
    compiled = round(complexity_pressure * operator_complexity) + (
        3 * total_support
    )
    operator_utility = raw - compiled
    mechanism_complexity = (
        len(_STRATEGY.split("-"))
        + len(_INPUT_FORM.split("_"))
        + len(_OUTPUT_FORM.split("_"))
        + _REQUIRED_DISTINCT
        + _MINIMUM_SUPPORT
        + 8
    )
    mechanism_utility = operator_utility - round(
        complexity_pressure * mechanism_complexity
    )
    accepts = (
        len(support) >= _REQUIRED_DISTINCT
        and total_support >= _MINIMUM_SUPPORT
        and operator_utility > 0
        and mechanism_utility > 0
    )
    return accepts, operator_utility, mechanism_utility


def _provenance_valid(
    schemas: SchemaStore,
    store: AbstractionStore,
) -> bool:
    if len(store.language_operators) != 1:
        return False
    operator = next(iter(store.language_operators.values()))
    mechanism = store.language_mechanism_history[-1]
    proposal_ids = set(store.language_proposals)
    schema_ids = set(schemas.schemas)
    evidence_resolves = all(
        item in proposal_ids or item in schema_ids
        for item in mechanism.evidence
    )
    graph = DependencyGraph.build(
        schemas,
        ConceptStore(),
        HypothesisStore(),
        store,
    )
    edges = {
        (edge.source, edge.relation, edge.target)
        for edge in graph.edges
    }
    required_edges = {
        (operator.operator_id, "invented_by", operator.invented_by),
        (mechanism.revision_id, "descends_from", operator.invented_by),
        (mechanism.revision_id, "retains", operator.operator_id),
        (
            store.language_history[-1].version_id,
            "licensed_by",
            mechanism.revision_id,
        ),
    }
    return (
        mechanism.status == "validated"
        and mechanism.parent_id == operator.invented_by
        and bool(mechanism.rejected_proposals)
        and operator.operator_id in mechanism.accepted_operators
        and set(mechanism.proposals) == proposal_ids
        and store.language_history[
            -1
        ].invention_mechanism_revision
        == mechanism.revision_id
        and evidence_resolves
        and required_edges.issubset(edges)
        and all(
            proposal.mechanism_revision_id == operator.invented_by
            for proposal in store.language_proposals.values()
        )
    )


def run_language_validation_seed(seed: int) -> LanguageValidationRun:
    rng = random.Random(seed)
    action = rng.choice((1, 2, 3, 4, 5))
    subject = f"piece_{rng.randrange(10_000_000):07d}"
    held_out = f"heldout_{rng.randrange(10_000_000):07d}"
    context = (
        Atom("state", ("NOT_FINISHED",)),
        Atom("layout", (f"layout_{rng.randrange(10_000_000):07d}",)),
    )
    angles = [90, 180, 270]
    rng.shuffle(angles)
    repetitions = {angle: rng.randint(10, 14) for angle in angles}

    schemas = SchemaStore()
    enabled = AbstractionStore()
    ablated = AbstractionStore(enable_language_meta_reflection=False)
    index = 0
    first = angles[0]
    _observe(
        schemas,
        index=index,
        context=context,
        action=action,
        kind=f"rotated_{first}",
        subject=subject,
    )
    index += 1
    enabled.reflect(schemas, ConceptStore())
    ablated.reflect(schemas, ConceptStore())

    for angle in angles:
        for _ in range(repetitions[angle]):
            _observe(
                schemas,
                index=index,
                context=context,
                action=action,
                kind=f"rotated_{angle}",
                subject=subject,
            )
            index += 1
    enabled.reflect(schemas, ConceptStore())
    ablated.reflect(schemas, ConceptStore())

    support = {
        f"rotated_{angle}": repetitions[angle] + int(angle == first)
        for angle in angles
    }
    strong_accepts, _operator_utility, mechanism_utility = _oracle(
        support
    )
    evidence_hash = _evidence_hash(schemas)
    early_rejected = sum(
        not proposal.accepted
        and proposal.reason == "insufficient-distinct-predicates"
        for proposal in enabled.language_proposals.values()
    )

    weak = SchemaStore()
    weak_angles = angles[:2]
    weak_support: dict[str, int] = {}
    for angle in weak_angles:
        count = repetitions[angle]
        weak_support[f"rotated_{angle}"] = count
        for _ in range(count):
            _observe(
                weak,
                index=index,
                context=context,
                action=action,
                kind=f"rotated_{angle}",
                subject=subject,
            )
            index += 1
    weak_store = AbstractionStore()
    weak_store.reflect(weak, ConceptStore())
    weak_accepts, _weak_operator_utility, _weak_mechanism_utility = (
        _oracle(weak_support)
    )

    noncyclic = SchemaStore()
    for angle in angles:
        for _ in range(repetitions[angle]):
            _observe(
                noncyclic,
                index=index,
                context=context,
                action=action,
                kind=f"translated_{angle}",
                subject=subject,
            )
            index += 1
    noncyclic_store = AbstractionStore()
    noncyclic_store.reflect(noncyclic, ConceptStore())

    future = Transition(
        before_index=index,
        after_index=index + 1,
        context=context,
        action_id=action,
        action_data=(),
        result=(Event("rotated_90", held_out),),
    )
    normalized = enabled.normalize_transition(future)
    before_repeat = enabled.to_dict()
    enabled.reflect(schemas, ConceptStore())
    after_repeat = enabled.to_dict()
    serialized_induction = json.dumps(
        {
            "schemas": schemas.to_dict(),
            "abstractions": before_repeat,
        },
        sort_keys=True,
    )

    return LanguageValidationRun(
        seed=seed,
        evidence_hash_enabled=evidence_hash,
        evidence_hash_ablated=evidence_hash,
        strong_oracle_accepts=strong_accepts,
        weak_oracle_rejects=not weak_accepts,
        early_rejected_proposals=early_rejected,
        operator_count=len(enabled.language_operators),
        validated_mechanism_count=sum(
            item.status == "validated"
            for item in enabled.language_mechanism_history
        ),
        mechanism_utility=mechanism_utility,
        ablation_proposal_count=len(ablated.language_proposals),
        ablation_operator_count=len(ablated.language_operators),
        weak_accepted_operator_count=len(weak_store.language_operators),
        noncyclic_proposal_count=len(noncyclic_store.language_proposals),
        noncyclic_operator_count=len(noncyclic_store.language_operators),
        held_out_normalized=(
            normalized.result
            == (Event("orientation_delta", held_out, ("1",)),)
        ),
        ablation_held_out_unchanged=(
            ablated.normalize_transition(future) == future
        ),
        provenance_valid=_provenance_valid(schemas, enabled),
        held_out_leaks=int(held_out in serialized_induction),
        structurally_idempotent=before_repeat == after_repeat,
    )


def run_language_meta_validation(
    seed_count: int,
    seed_start: int,
) -> dict[str, object]:
    if seed_count < 2:
        raise ValueError("seed_count must be at least 2")
    if seed_start < 0:
        raise ValueError("seed_start must be non-negative")
    runs = tuple(
        run_language_validation_seed(seed)
        for seed in range(seed_start, seed_start + seed_count)
    )
    criteria = {
        "independent_oracle_accepts_every_strong_history": all(
            item.strong_oracle_accepts for item in runs
        ),
        "independent_oracle_rejects_every_weak_history": all(
            item.weak_oracle_rejects for item in runs
        ),
        "paired_histories_have_identical_evidence_hashes": all(
            item.evidence_hash_enabled == item.evidence_hash_ablated
            for item in runs
        ),
        "early_rejected_trial_recorded": all(
            item.early_rejected_proposals >= 1 for item in runs
        ),
        "exactly_one_orientation_operator_constructed": all(
            item.operator_count == 1 for item in runs
        ),
        "validated_mechanism_has_positive_utility": all(
            item.validated_mechanism_count >= 1
            and item.mechanism_utility > 0
            for item in runs
        ),
        "ablation_has_no_language_structures": all(
            item.ablation_proposal_count == 0
            and item.ablation_operator_count == 0
            for item in runs
        ),
        "weak_history_has_no_accepted_operator": all(
            item.weak_accepted_operator_count == 0 for item in runs
        ),
        "noncyclic_control_abstains": all(
            item.noncyclic_proposal_count == 0
            and item.noncyclic_operator_count == 0
            for item in runs
        ),
        "held_out_transition_is_normalized": all(
            item.held_out_normalized for item in runs
        ),
        "ablation_preserves_held_out_transition": all(
            item.ablation_held_out_unchanged for item in runs
        ),
        "all_provenance_endpoints_are_valid": all(
            item.provenance_valid for item in runs
        ),
        "held_out_identity_never_leaks": all(
            item.held_out_leaks == 0 for item in runs
        ),
        "repeated_reflection_is_structurally_idempotent": all(
            item.structurally_idempotent for item in runs
        ),
    }
    payload: dict[str, object] = {
        "benchmark": "reflector_symbolic_diagnostics_v8",
        "claim_scope": (
            "bounded causal meta-reflection over one hand-authored cyclic "
            "language-invention strategy; not an ARC score"
        ),
        "seed_start": seed_start,
        "seed_count": seed_count,
        "policies": [
            "language_meta_reflection",
            "no_language_meta_reflection",
        ],
        "controls": ["weak_evidence", "noncyclic_vocabulary"],
        "criteria": criteria,
        "causal_thesis_supported": all(criteria.values()),
        "verdict": "supported" if all(criteria.values()) else "not_supported",
        "runs": [asdict(item) for item in runs],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["result_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload
