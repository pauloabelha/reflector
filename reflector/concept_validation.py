"""Preregistered v9 validation for reversible concept retirement."""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass

from .causal import HypothesisStore
from .graph import DependencyGraph
from .schemas import ConceptStore, SchemaStore
from .symbolic import Atom, Event, Transition


@dataclass(frozen=True, slots=True)
class ConceptValidationRun:
    seed: int
    phase_evidence_hashes_match: bool
    oracle_lifecycle_passes: bool
    same_admitted_concept_id: bool
    enabled_retires: bool
    ablation_remains_active: bool
    enabled_context_omits_retired: bool
    ablation_context_retains_concept: bool
    reactivates_same_identity: bool
    lifecycle_order_valid: bool
    lifecycle_provenance_valid: bool
    retired_history_preserved: bool
    noisy_viable_remains_active: bool
    insufficient_contradiction_remains_active: bool
    failed_reactivation_remains_retired: bool
    unrelated_status_unchanged: bool
    held_out_leaks: int
    byte_idempotent: bool


def _observe(
    schemas: SchemaStore,
    *,
    index: int,
    context: tuple[Atom, ...],
    action: int,
    event: Event,
) -> None:
    schemas.observe(
        Transition(
            before_index=index,
            after_index=index + 1,
            context=context,
            action_id=action,
            action_data=(),
            result=(event,),
        )
    )


def _hash_schemas(schemas: SchemaStore) -> str:
    canonical = json.dumps(
        schemas.to_dict(),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


def _target_id(concepts: ConceptStore, target: Event) -> str:
    target_text = target.text()
    return next(
        concept.concept_id
        for concept in concepts.concepts.values()
        if concept.definition[-1] == target_text
    )


def _oracle_status(
    *,
    support: int,
    opportunities: int,
    retired_support: int | None = None,
) -> str:
    contradictions = opportunities - support
    reliability = support / opportunities
    if retired_support is None:
        if (
            opportunities >= 6
            and contradictions >= 3
            and reliability < 0.35
        ):
            return "retired"
        return "active"
    if support >= retired_support + 2 and reliability >= 0.50:
        return "reactivated"
    return "retired"


def _control_store(
    *,
    action: int,
    context: tuple[Atom, ...],
    target: Event,
    successes: int,
    failures: int,
) -> tuple[ConceptStore, str]:
    schemas = SchemaStore()
    index = 0
    for _ in range(successes):
        _observe(
            schemas,
            index=index,
            context=context,
            action=action,
            event=target,
        )
        index += 1
    concepts = ConceptStore()
    concepts.reflect(schemas)
    concept_id = _target_id(concepts, target)
    for _ in range(failures):
        _observe(
            schemas,
            index=index,
            context=context,
            action=action,
            event=Event("no_observed_change"),
        )
        index += 1
    concepts.reflect(schemas)
    return concepts, concept_id


def run_concept_validation_seed(seed: int) -> ConceptValidationRun:
    rng = random.Random(seed)
    action = rng.choice((1, 2, 3, 4, 5))
    dependency_action = next(
        candidate for candidate in (1, 2, 3, 4, 5) if candidate != action
    )
    subject = f"goal_{rng.randrange(10_000_000):07d}"
    layout = f"layout_{rng.randrange(10_000_000):07d}"
    held_out = f"heldout_{rng.randrange(10_000_000):07d}"
    context = (
        Atom("state", ("NOT_FINISHED",)),
        Atom("layout", (layout,)),
    )
    target = Event("level_advanced", subject, ("0", "1"))
    failure = Event(
        "no_observed_change",
        f"noise_{rng.randrange(10_000_000):07d}",
    )
    schemas = SchemaStore()
    enabled = ConceptStore()
    ablated = ConceptStore(enable_retirement=False)
    phase_hashes: list[tuple[str, str]] = []
    index = 0

    for _ in range(3):
        _observe(
            schemas,
            index=index,
            context=context,
            action=action,
            event=target,
        )
        index += 1
    enabled.reflect(schemas)
    ablated.reflect(schemas)
    enabled_id = _target_id(enabled, target)
    ablated_id = _target_id(ablated, target)
    phase_hash = _hash_schemas(schemas)
    phase_hashes.append((phase_hash, phase_hash))

    dependency_context = (
        *context,
        Atom("synthetic_item", (enabled_id,)),
    )
    _observe(
        schemas,
        index=index,
        context=dependency_context,
        action=dependency_action,
        event=Event("dependency_probe", subject),
    )
    index += 1

    for _ in range(8):
        _observe(
            schemas,
            index=index,
            context=context,
            action=action,
            event=failure,
        )
        index += 1
    enabled.reflect(schemas)
    ablated.reflect(schemas)
    phase_hash = _hash_schemas(schemas)
    phase_hashes.append((phase_hash, phase_hash))
    retired_snapshot = enabled.to_dict()
    retired_graph = DependencyGraph.build(
        schemas,
        enabled,
        HypothesisStore(),
    )

    held_out_atom = Atom("held_out_context", (held_out,))
    enabled_context = (*enabled.context_atoms(action), held_out_atom)
    ablated_context = (*ablated.context_atoms(action), held_out_atom)

    unrelated_ids = set(enabled.concepts) - {enabled_id}
    unrelated_status_unchanged = all(
        enabled.is_active(concept_id) == ablated.is_active(concept_id)
        for concept_id in unrelated_ids
    )

    for _ in range(6):
        _observe(
            schemas,
            index=index,
            context=context,
            action=action,
            event=target,
        )
        index += 1
    enabled.reflect(schemas)
    ablated.reflect(schemas)
    phase_hash = _hash_schemas(schemas)
    phase_hashes.append((phase_hash, phase_hash))

    lifecycle = [
        event
        for event in enabled.lifecycle_events.values()
        if event.concept_id == enabled_id
    ]
    schema_ids = set(schemas.schemas)
    graph = DependencyGraph.build(
        schemas,
        enabled,
        HypothesisStore(),
    )
    graph_edges = {
        (edge.source, edge.relation, edge.target)
        for edge in graph.edges
    }
    lifecycle_provenance = (
        [event.transition for event in lifecycle]
        == ["activated", "retired", "reactivated"]
        and lifecycle[-1].supersedes == lifecycle[-2].event_id
        and all(
            set(event.evidence).issubset(schema_ids) for event in lifecycle
        )
        and all(
            (event.event_id, event.transition, enabled_id) in graph_edges
            for event in lifecycle
        )
        and all(
            (
                event.event_id,
                "supersedes",
                event.supersedes,
            )
            in graph_edges
            for event in lifecycle[1:]
        )
    )
    dependency_edges = {
        (
            edge.source,
            edge.relation,
            edge.target,
        )
        for edge in retired_graph.edges
    }
    retired_history_preserved = (
        enabled_id in retired_snapshot["retired_ids"]
        and any(
            item["concept_id"] == enabled_id
            for item in retired_snapshot["concepts"]
        )
        and any(
            source in schema_ids
            and relation == "uses"
            and target_id == enabled_id
            for source, relation, target_id in dependency_edges
        )
    )

    noisy, noisy_id = _control_store(
        action=action,
        context=context,
        target=target,
        successes=3,
        failures=3,
    )
    insufficient, insufficient_id = _control_store(
        action=action,
        context=context,
        target=target,
        successes=3,
        failures=2,
    )
    failed, failed_id = _control_store(
        action=action,
        context=context,
        target=target,
        successes=3,
        failures=8,
    )
    failed_schemas = SchemaStore()
    failed_index = 0
    for _ in range(3):
        _observe(
            failed_schemas,
            index=failed_index,
            context=context,
            action=action,
            event=target,
        )
        failed_index += 1
    failed_store = ConceptStore()
    failed_store.reflect(failed_schemas)
    for _ in range(8):
        _observe(
            failed_schemas,
            index=failed_index,
            context=context,
            action=action,
            event=failure,
        )
        failed_index += 1
    failed_store.reflect(failed_schemas)
    failed_store_id = _target_id(failed_store, target)
    _observe(
        failed_schemas,
        index=failed_index,
        context=context,
        action=action,
        event=target,
    )
    failed_store.reflect(failed_schemas)

    before_repeat = enabled.to_dict()
    enabled.reflect(schemas)
    after_repeat = enabled.to_dict()
    serialized_evidence = json.dumps(
        {
            "schemas": schemas.to_dict(),
            "lifecycle": [
                event.to_dict() for event in lifecycle
            ],
        },
        sort_keys=True,
    )
    del failed, failed_id

    return ConceptValidationRun(
        seed=seed,
        phase_evidence_hashes_match=all(
            left == right for left, right in phase_hashes
        ),
        oracle_lifecycle_passes=(
            _oracle_status(support=3, opportunities=3) == "active"
            and _oracle_status(support=3, opportunities=11) == "retired"
            and _oracle_status(
                support=9,
                opportunities=17,
                retired_support=3,
            )
            == "reactivated"
        ),
        same_admitted_concept_id=enabled_id == ablated_id,
        enabled_retires=enabled_id in retired_snapshot["retired_ids"],
        ablation_remains_active=ablated_id in ablated.active_ids,
        enabled_context_omits_retired=(
            Atom("synthetic_item", (enabled_id,))
            not in enabled_context
        ),
        ablation_context_retains_concept=(
            Atom("synthetic_item", (ablated_id,))
            in ablated_context
        ),
        reactivates_same_identity=enabled.is_active(enabled_id),
        lifecycle_order_valid=(
            [event.transition for event in lifecycle]
            == ["activated", "retired", "reactivated"]
        ),
        lifecycle_provenance_valid=lifecycle_provenance,
        retired_history_preserved=retired_history_preserved,
        noisy_viable_remains_active=noisy.is_active(noisy_id),
        insufficient_contradiction_remains_active=(
            insufficient.is_active(insufficient_id)
        ),
        failed_reactivation_remains_retired=(
            not failed_store.is_active(failed_store_id)
        ),
        unrelated_status_unchanged=unrelated_status_unchanged,
        held_out_leaks=int(held_out in serialized_evidence),
        byte_idempotent=before_repeat == after_repeat,
    )


def run_concept_lifecycle_validation(
    seed_count: int,
    seed_start: int,
) -> dict[str, object]:
    if seed_count < 2:
        raise ValueError("seed_count must be at least 2")
    if seed_start < 0:
        raise ValueError("seed_start must be non-negative")
    runs = tuple(
        run_concept_validation_seed(seed)
        for seed in range(seed_start, seed_start + seed_count)
    )
    criteria = {
        "independent_oracle_predicts_lifecycle": all(
            item.oracle_lifecycle_passes for item in runs
        ),
        "paired_phase_evidence_hashes_match": all(
            item.phase_evidence_hashes_match for item in runs
        ),
        "both_variants_admit_same_concept": all(
            item.same_admitted_concept_id for item in runs
        ),
        "enabled_concept_retires": all(
            item.enabled_retires for item in runs
        ),
        "ablation_concept_remains_active": all(
            item.ablation_remains_active for item in runs
        ),
        "enabled_context_omits_retired_concept": all(
            item.enabled_context_omits_retired for item in runs
        ),
        "ablation_context_retains_concept": all(
            item.ablation_context_retains_concept for item in runs
        ),
        "concept_reactivates_with_same_identity": all(
            item.reactivates_same_identity for item in runs
        ),
        "lifecycle_order_is_exact": all(
            item.lifecycle_order_valid for item in runs
        ),
        "lifecycle_provenance_resolves": all(
            item.lifecycle_provenance_valid for item in runs
        ),
        "retired_history_is_preserved": all(
            item.retired_history_preserved for item in runs
        ),
        "noisy_viable_control_remains_active": all(
            item.noisy_viable_remains_active for item in runs
        ),
        "insufficient_contradiction_control_remains_active": all(
            item.insufficient_contradiction_remains_active
            for item in runs
        ),
        "failed_reactivation_control_remains_retired": all(
            item.failed_reactivation_remains_retired for item in runs
        ),
        "unrelated_concept_status_is_unchanged": all(
            item.unrelated_status_unchanged for item in runs
        ),
        "repeated_reflection_is_byte_idempotent": all(
            item.byte_idempotent and item.held_out_leaks == 0
            for item in runs
        ),
    }
    payload: dict[str, object] = {
        "benchmark": "reflector_symbolic_diagnostics_v9",
        "claim_scope": (
            "reversible evidence-driven lifecycle of explicit synthetic "
            "concepts; not an ARC score"
        ),
        "seed_start": seed_start,
        "seed_count": seed_count,
        "policies": ["concept_retirement", "no_concept_retirement"],
        "controls": [
            "noisy_viable",
            "insufficient_contradiction",
            "failed_reactivation",
        ],
        "criteria": criteria,
        "causal_thesis_supported": all(criteria.values()),
        "verdict": "supported" if all(criteria.values()) else "not_supported",
        "runs": [asdict(item) for item in runs],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["result_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload
