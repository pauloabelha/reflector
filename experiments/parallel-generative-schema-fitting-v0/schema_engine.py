"""Generic, bounded parallel fitting for grounded generative schemas.

This module is intentionally domain neutral.  Symbols such as ``SameOutline``
and ``Delta`` are opaque predicates supplied by an observation adapter; the
engine neither knows nor infers semantic game roles.  It provides the common
machinery for static and temporal schemas: definitions, partial bindings,
shadows, causal/transformational composition, invention, and sparse retrieval.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field, replace
from enum import StrEnum
from hashlib import sha256
import json
from itertools import permutations, product
from typing import Iterable, Mapping, Sequence


def stable_id(prefix: str, value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return f"{prefix}:{sha256(canonical.encode()).hexdigest()[:16]}"


def _alpha_canonical_definition(ports: tuple[Port, ...], constraints: tuple[Relation, ...]) -> dict[str, object]:
    """Canonicalize small definition DAGs modulo port alpha-renaming.

    Schema invention operates over deliberately small active motifs. For up to
    eight ports we can exactly minimize all type-preserving permutations. The
    fallback remains deterministic for larger definitions, which should be
    decomposed rather than invented as one monolith.
    """
    by_type: dict[str, list[str]] = defaultdict(list)
    for port in ports:
        by_type[port.type].append(port.name)
    ordered_types = sorted(by_type)
    canonical_slots: dict[str, tuple[str, ...]] = {}
    offset = 0
    for type_name in ordered_types:
        canonical_slots[type_name] = tuple(f"p{number}" for number in range(offset, offset + len(by_type[type_name])))
        offset += len(by_type[type_name])
    if len(ports) > 8:
        mappings = [tuple(tuple(sorted(by_type[type_name])) for type_name in ordered_types)]
    else:
        mappings = product(*(permutations(by_type[type_name]) for type_name in ordered_types))
    best: str | None = None
    best_value: dict[str, object] | None = None
    for grouped_names in mappings:
        rename = {
            old: new
            for type_name, names in zip(ordered_types, grouped_names, strict=True)
            for old, new in zip(names, canonical_slots[type_name], strict=True)
        }
        value = {
            "ports": sorted((rename[port.name], port.type) for port in ports),
            "constraints": sorted((relation.predicate, tuple(rename[name] for name in relation.ports)) for relation in constraints),
        }
        rendered = json.dumps(value, sort_keys=True, separators=(",", ":"))
        if best is None or rendered < best:
            best, best_value = rendered, value
    assert best_value is not None
    return best_value


class BindingState(StrEnum):
    PARTIAL = "partial"
    REIFIED = "reified"
    REFUTED = "refuted"


class ShadowState(StrEnum):
    OPEN = "open"
    REIFIED = "reified"
    REFUTED = "refuted"


@dataclass(frozen=True, order=True)
class Port:
    name: str
    type: str


@dataclass(frozen=True, order=True)
class Relation:
    predicate: str
    ports: tuple[str, ...]


@dataclass(frozen=True)
class Schema:
    """Reusable intensional definition; its components form a definition DAG."""

    schema_id: str
    ports: tuple[Port, ...]
    constraints: tuple[Relation, ...]
    components: tuple[str, ...] = ()
    kind: str = "relational"
    derivation: tuple[str, ...] = ()
    output_type: str = "structure"

    @staticmethod
    def create(
        ports: Iterable[Port], constraints: Iterable[Relation], *,
        components: Iterable[str] = (), kind: str = "relational",
        derivation: Iterable[str] = (), output_type: str = "structure",
    ) -> "Schema":
        canonical_ports = tuple(sorted(ports))
        canonical_constraints = tuple(sorted(constraints))
        names = tuple(port.name for port in canonical_ports)
        if not names or len(names) != len(set(names)):
            raise ValueError("schema ports must be nonempty and unique")
        unknown = {name for relation in canonical_constraints for name in relation.ports} - set(names)
        if unknown:
            raise ValueError(f"schema constraints use unknown ports: {sorted(unknown)}")
        value = {
            "definition": _alpha_canonical_definition(canonical_ports, canonical_constraints),
            "components": sorted(components), "kind": kind, "output_type": output_type,
        }
        return Schema(
            stable_id("schema", value), canonical_ports, canonical_constraints,
            tuple(sorted(components)), kind, tuple(sorted(derivation)), output_type,
        )


@dataclass(frozen=True)
class GroundFact:
    """Relation over opaque support/binding IDs with explicit authority."""

    predicate: str
    arguments: tuple[str, ...]
    argument_types: tuple[str, ...]
    evidence_id: str
    context_id: str
    authority: str = "environment"

    def __post_init__(self) -> None:
        if len(self.arguments) != len(self.argument_types):
            raise ValueError("fact argument types must align with arguments")


@dataclass(frozen=True)
class Binding:
    binding_id: str
    schema_id: str
    assignments: tuple[tuple[str, str], ...]
    satisfied: tuple[int, ...]
    open_constraints: tuple[int, ...]
    open_ports: tuple[str, ...]
    evidence_ids: tuple[str, ...]
    contexts: tuple[str, ...]
    support: int
    salience: float
    state: BindingState

    @property
    def assignment_map(self) -> dict[str, str]:
        return dict(self.assignments)


@dataclass(frozen=True)
class Shadow:
    shadow_id: str
    binding_id: str
    schema_id: str
    relation: Relation
    grounded_arguments: tuple[str | None, ...]
    missing_ports: tuple[str, ...]
    state: ShadowState = ShadowState.OPEN
    resolution_evidence_id: str | None = None


@dataclass(frozen=True)
class Transformation:
    """A schema with oriented ports; no separate metaphysics is required."""

    schema_id: str
    before_port: str
    intervention_port: str
    after_port: str


@dataclass(frozen=True)
class FrontierBudget:
    retrieval: int = 32
    binding_expansion: int = 128
    shadow_generation: int = 64
    invention: int = 16
    active_bindings: int = 64
    relation_joins: int = 4096
    new_bindings: int = 128
    max_depth_increment: int = 4


@dataclass
class SchemaRecord:
    schema: Schema
    support_evidence: set[str] = field(default_factory=set)
    salience: float = 0.0
    promoted: bool = False


class SchemaStore:
    """Durable definition store with sparse inverted indexes and a DAG check."""

    def __init__(self) -> None:
        self.records: dict[str, SchemaRecord] = {}
        self.by_predicate: dict[str, set[str]] = defaultdict(set)
        self.by_port_type: dict[str, set[str]] = defaultdict(set)

    def add(self, schema: Schema, *, promoted: bool = False) -> Schema:
        if schema.schema_id in self.records:
            return self.records[schema.schema_id].schema
        candidate = {**{key: record.schema for key, record in self.records.items()}, schema.schema_id: schema}

        def visit(schema_id: str, path: tuple[str, ...]) -> None:
            if schema_id in path:
                raise ValueError("schema definition graph must be acyclic")
            current = candidate.get(schema_id)
            if current is None:
                raise ValueError(f"unknown component schema: {schema_id}")
            for component in current.components:
                visit(component, (*path, schema_id))

        visit(schema.schema_id, ())
        self.records[schema.schema_id] = SchemaRecord(schema=schema, promoted=promoted)
        for relation in schema.constraints:
            self.by_predicate[relation.predicate].add(schema.schema_id)
        for port in schema.ports:
            self.by_port_type[port.type].add(schema.schema_id)
        return schema

    def retrieve(self, facts: Sequence[GroundFact], *, limit: int) -> tuple[Schema, ...]:
        """Bounded indexed retrieval; dormant unrelated schemas are not scanned."""
        available_predicates = {fact.predicate for fact in facts}
        available_types = {kind for fact in facts for kind in fact.argument_types}
        candidates: set[str] = set()
        for predicate in available_predicates:
            candidates.update(self.by_predicate.get(predicate, ()))
        scored = []
        for schema_id in candidates:
            schema = self.records[schema_id].schema
            predicate_overlap = len({item.predicate for item in schema.constraints} & available_predicates)
            type_overlap = len({item.type for item in schema.ports} & available_types)
            record = self.records[schema_id]
            scored.append((-predicate_overlap, -type_overlap, -record.salience, schema_id))
        return tuple(self.records[item[-1]].schema for item in sorted(scored)[:limit])

    def support(self, schema_id: str, evidence_ids: Iterable[str]) -> None:
        self.records[schema_id].support_evidence.update(evidence_ids)

    def set_salience(self, schema_id: str, value: float) -> None:
        self.records[schema_id].salience = value


def workspace_object(value: Schema | Binding | Shadow) -> dict[str, object]:
    """Lossless first-class workspace projection with stable provenance.

    The generic workspace only needs `kind`, identity, payload and dependency
    IDs.  This adapter keeps schema definitions, situated bindings and
    predicted shadows distinct when the R2.1 core is embedded in the shared
    R2/Qwen graph.
    """
    if isinstance(value, Schema):
        return {
            "kind": "schema_definition", "created_by": "r2",
            "identity": {"schema_id": value.schema_id},
            "payload": {"ports": [asdict(port) for port in value.ports], "constraints": [asdict(item) for item in value.constraints], "kind": value.kind, "output_type": value.output_type},
            "dependency_ids": list(value.components), "derivation_ids": list(value.derivation),
        }
    if isinstance(value, Binding):
        return {
            "kind": "schema_binding", "created_by": "r2",
            "identity": {"binding_id": value.binding_id, "schema_id": value.schema_id},
            "payload": {"assignments": list(value.assignments), "satisfied": list(value.satisfied), "open_constraints": list(value.open_constraints), "open_ports": list(value.open_ports), "state": value.state.value, "salience": value.salience, "support": value.support},
            "dependency_ids": [value.schema_id, *value.evidence_ids], "derivation_ids": list(value.contexts),
        }
    return {
        "kind": "schema_shadow", "created_by": "r2",
        "identity": {"shadow_id": value.shadow_id, "binding_id": value.binding_id},
        "payload": {"relation": asdict(value.relation), "grounded_arguments": list(value.grounded_arguments), "missing_ports": list(value.missing_ports), "state": value.state.value},
        "dependency_ids": [value.schema_id, value.binding_id],
        "derivation_ids": [] if value.resolution_evidence_id is None else [value.resolution_evidence_id],
    }


def _unify(
    assignments: Mapping[str, str], relation: Relation, fact: GroundFact,
    ports: Mapping[str, Port],
) -> dict[str, str] | None:
    if relation.predicate != fact.predicate or len(relation.ports) != len(fact.arguments):
        return None
    merged = dict(assignments)
    for port_name, entity, type_name in zip(relation.ports, fact.arguments, fact.argument_types, strict=True):
        if ports[port_name].type != type_name:
            return None
        old = merged.get(port_name)
        if old is not None and old != entity:
            return None
        merged[port_name] = entity
    return merged


def fit_schema(
    schema: Schema, facts: Sequence[GroundFact], *, budget: int,
    initial_assignments: Mapping[str, str] | None = None,
) -> tuple[Binding, ...]:
    """Batch-like bounded join: preserve all compatible partial branches."""
    facts_by_predicate: dict[str, list[GroundFact]] = defaultdict(list)
    for fact in facts:
        facts_by_predicate[fact.predicate].append(fact)
    ports = {item.name: item for item in schema.ports}
    # assignment, satisfied, open, evidence, contexts
    branches: list[tuple[dict[str, str], tuple[int, ...], tuple[int, ...], tuple[str, ...], tuple[str, ...]]] = [(dict(initial_assignments or {}), (), (), (), ())]
    # Selective relations constrain the join first; relations with no evidence
    # remain open and are handled after the candidate assignments are narrow.
    ordered_constraints = sorted(
        enumerate(schema.constraints),
        key=lambda item: (len(facts_by_predicate.get(item[1].predicate, ())) == 0, len(facts_by_predicate.get(item[1].predicate, ())), item[0]),
    )
    for index, relation in ordered_constraints:
        next_branches = []
        for assignments, satisfied, open_items, evidence, contexts in branches:
            matches = []
            for fact in facts_by_predicate.get(relation.predicate, ()):
                merged = _unify(assignments, relation, fact, ports)
                if merged is not None:
                    matches.append((merged, fact))
            if matches:
                next_branches.extend((merged, (*satisfied, index), open_items, (*evidence, fact.evidence_id), (*contexts, fact.context_id)) for merged, fact in matches)
            else:
                next_branches.append((assignments, satisfied, (*open_items, index), evidence, contexts))
        branches = next_branches[:budget]
    unique: dict[tuple[tuple[tuple[str, str], ...], tuple[int, ...], tuple[int, ...]], Binding] = {}
    for assignments, satisfied, open_items, evidence, contexts in branches:
        packed = tuple(sorted(assignments.items()))
        key = packed, satisfied, open_items
        open_ports = tuple(sorted(set(ports) - set(assignments)))
        state = BindingState.REIFIED if not open_items and not open_ports else BindingState.PARTIAL
        environmental_evidence = {
            fact.evidence_id for fact in facts
            if fact.evidence_id in evidence and fact.authority == "environment"
        }
        support = len(environmental_evidence)
        value = {
            "schema": schema.schema_id, "assignments": packed,
            "satisfied": satisfied, "open": open_items, "open_ports": open_ports,
        }
        unique[key] = Binding(
            stable_id("binding", value), schema.schema_id, packed, satisfied, open_items, open_ports,
            tuple(sorted(set(evidence))), tuple(sorted(set(contexts))), support,
            float(len(satisfied) * 10 + support), state,
        )
    return tuple(sorted(unique.values(), key=lambda item: (-item.salience, item.binding_id)))


def extend_binding(schema: Schema, binding: Binding, facts: Sequence[GroundFact], *, budget: int) -> tuple[Binding, ...]:
    """Bounded completion of an existing partial binding.

    Re-running the same join with its current assignments as a seed is the
    generic operation behind recognition, prediction, diagnosis and temporal
    continuation.  It deliberately returns alternatives rather than selecting
    one completion.
    """
    if binding.schema_id != schema.schema_id or binding.state == BindingState.REFUTED:
        return ()
    return fit_schema(schema, facts, budget=budget, initial_assignments=binding.assignment_map)


def project_shadows(schema: Schema, binding: Binding, *, limit: int) -> tuple[Shadow, ...]:
    assignments = binding.assignment_map
    shadows = []
    for index in binding.open_constraints[:limit]:
        relation = schema.constraints[index]
        arguments = tuple(assignments.get(port) for port in relation.ports)
        missing = tuple(port for port, value in zip(relation.ports, arguments, strict=True) if value is None)
        value = {"binding": binding.binding_id, "relation": asdict(relation), "arguments": arguments}
        shadows.append(Shadow(stable_id("shadow", value), binding.binding_id, schema.schema_id, relation, arguments, missing))
    return tuple(shadows)


def settle_shadow(shadow: Shadow, facts: Iterable[GroundFact], *, contradictory_predicates: Iterable[str] = ()) -> Shadow:
    """Only matching environment facts reify/refute; lack of a fact stays open."""
    negatives = set(contradictory_predicates)
    for fact in facts:
        if len(fact.arguments) != len(shadow.grounded_arguments):
            continue
        compatible = all(expected is None or expected == actual for expected, actual in zip(shadow.grounded_arguments, fact.arguments, strict=True))
        if compatible and fact.predicate == shadow.relation.predicate:
            return replace(shadow, state=ShadowState.REIFIED, resolution_evidence_id=fact.evidence_id)
        if compatible and fact.predicate in negatives:
            return replace(shadow, state=ShadowState.REFUTED, resolution_evidence_id=fact.evidence_id)
    return shadow


def canonical_motif(facts: Sequence[GroundFact]) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Erase entity identities while preserving relational incidence and types."""
    aliases: dict[tuple[str, str], str] = {}
    next_index = 0
    rows = []
    for fact in sorted(facts, key=lambda item: (item.predicate, item.arguments, item.argument_types)):
        ports = []
        for entity, type_name in zip(fact.arguments, fact.argument_types, strict=True):
            key = entity, type_name
            if key not in aliases:
                aliases[key] = f"p{next_index}:{type_name}"; next_index += 1
            ports.append(aliases[key])
        rows.append((fact.predicate, tuple(ports)))
    return tuple(rows)


def schema_from_motif(facts: Sequence[GroundFact], *, derivation: Iterable[str]) -> Schema:
    motif = canonical_motif(facts)
    typed_ports = {token: Port(token.split(":", 1)[0], token.split(":", 1)[1]) for _predicate, tokens in motif for token in tokens}
    relations = tuple(Relation(predicate, tuple(token.split(":", 1)[0] for token in tokens)) for predicate, tokens in motif)
    return Schema.create(typed_ports.values(), relations, kind="composed", derivation=derivation)


def compose_compatible_bindings(store: SchemaStore, left: Binding, right: Binding) -> Schema | None:
    """Propose, but do not promote, a local composition sharing a support.

    The composed schema retains the component IDs and both internal relation
    DAGs.  Port names are namespaced, except for ports grounded to the same
    support; those become one shared compositional port.  This prevents an
    arbitrary conjunction from becoming a schema merely because two bindings
    happened to be active nearby.
    """
    if left.schema_id == right.schema_id or not set(left.assignment_map.values()) & set(right.assignment_map.values()):
        return None
    left_schema, right_schema = store.records[left.schema_id].schema, store.records[right.schema_id].schema
    left_values, right_values = left.assignment_map, right.assignment_map
    shared_values = set(left_values.values()) & set(right_values.values())
    ports: list[Port] = []
    relations: list[Relation] = []
    names: dict[tuple[str, str], str] = {}

    def add(schema: Schema, assignments: Mapping[str, str], side: str) -> None:
        for port in schema.ports:
            entity = assignments.get(port.name)
            identity = ("shared", entity) if entity in shared_values else (side, port.name)
            names[(side, port.name)] = names.setdefault(identity, f"p{len({value for value in names.values()})}")
            name = names[(side, port.name)]
            if not any(item.name == name for item in ports):
                ports.append(Port(name, port.type))
        for relation in schema.constraints:
            relations.append(Relation(relation.predicate, tuple(names[(side, port)] for port in relation.ports)))

    add(left_schema, left_values, "left"); add(right_schema, right_values, "right")
    return Schema.create(ports, relations, components=(left.schema_id, right.schema_id), kind="composition", derivation=(left.binding_id, right.binding_id))


def compose_transformations(first: Transformation, second: Transformation, *, bridge_port: str) -> tuple[str, str, str, str]:
    """Return an oriented compositional signature when ``first.after`` feeds ``second.before``.

    The signature is intentionally small: definition construction remains a
    normal schema-composition operation, while this function states the
    category-inspired orientation check without pretending to implement a
    mathematical category.
    """
    if first.after_port != bridge_port or second.before_port != bridge_port:
        raise ValueError("transformations do not compose at the supplied bridge port")
    return first.schema_id, second.schema_id, first.before_port, second.after_port


@dataclass
class InventionCandidate:
    schema: Schema
    contexts: set[str] = field(default_factory=set)
    reified_shadows: int = 0


class SchemaInventor:
    """Promotes repeated relational constructions, retaining their derivation."""

    def __init__(self, *, minimum_contexts: int = 2) -> None:
        self.minimum_contexts = minimum_contexts
        self.candidates: dict[str, InventionCandidate] = {}

    def observe(self, facts: Sequence[GroundFact]) -> Schema:
        schema = schema_from_motif(facts, derivation=tuple(sorted({fact.evidence_id for fact in facts})))
        candidate = self.candidates.setdefault(schema.schema_id, InventionCandidate(schema))
        candidate.contexts.update(fact.context_id for fact in facts)
        return schema

    def note_reified_shadow(self, schema_id: str) -> None:
        if schema_id in self.candidates:
            self.candidates[schema_id].reified_shadows += 1

    def promotable(self) -> tuple[Schema, ...]:
        return tuple(
            candidate.schema for candidate in self.candidates.values()
            if len(candidate.contexts) >= self.minimum_contexts
        )


class ParallelSchemaFitter:
    """A sparse active frontier over a potentially large durable store."""

    def __init__(self, store: SchemaStore, *, budget: FrontierBudget = FrontierBudget()) -> None:
        self.store, self.budget = store, budget
        self.active: dict[str, Binding] = {}
        self.shadows: dict[str, Shadow] = {}

    def update(self, facts: Sequence[GroundFact]) -> tuple[Binding, ...]:
        schemas = self.store.retrieve(facts, limit=self.budget.retrieval)
        proposed = [binding for schema in schemas for binding in fit_schema(schema, facts, budget=self.budget.binding_expansion)]
        # Extend, rather than discard, compatible partial interpretations.
        for binding in self.active.values():
            if binding.schema_id in self.store.records:
                schema = self.store.records[binding.schema_id].schema
                proposed.extend(extend_binding(schema, binding, facts, budget=self.budget.binding_expansion))
        # Multiple schemas/bindings remain active.  The frontier only bounds
        # attention; definitions and historical evidence remain durable.
        proposed.sort(key=lambda item: (-item.salience, item.binding_id))
        self.active = {item.binding_id: item for item in proposed[:self.budget.active_bindings]}
        for binding in self.active.values():
            self.store.support(binding.schema_id, binding.evidence_ids)
            self.store.set_salience(binding.schema_id, binding.salience)
            schema = self.store.records[binding.schema_id].schema
            for shadow in project_shadows(schema, binding, limit=self.budget.shadow_generation):
                self.shadows[shadow.shadow_id] = shadow
        return tuple(self.active.values())

    def settle(self, facts: Sequence[GroundFact], *, contradictions: Mapping[str, Sequence[str]] = {}) -> tuple[Shadow, ...]:
        settled = []
        for shadow_id, shadow in tuple(self.shadows.items()):
            next_shadow = settle_shadow(shadow, facts, contradictory_predicates=contradictions.get(shadow.relation.predicate, ()))
            self.shadows[shadow_id] = next_shadow
            settled.append(next_shadow)
        return tuple(settled)


@dataclass(frozen=True)
class GroundSupport:
    """A leaf at the Schema_0 boundary."""

    support_id: str
    type: str
    evidence_id: str
    context_id: str


@dataclass(frozen=True)
class WorkspaceAtom:
    """A typed object which may fill a port of a higher schema."""

    atom_id: str
    type: str
    grounding_evidence_ids: tuple[str, ...]
    depth: int
    source_kind: str
    source_id: str


@dataclass(frozen=True)
class ClosureStats:
    delta_atoms: int
    schemas_considered: int
    joins_attempted: int
    new_bindings: int
    new_partial_bindings: int
    maximum_depth: int
    budget_exhausted: bool


class BindingWorkspace:
    """Episode-local recursively growing graph of grounded bindings."""

    def __init__(self) -> None:
        self.atoms: dict[str, WorkspaceAtom] = {}
        self.bindings: dict[str, Binding] = {}
        self.shadows: dict[str, Shadow] = {}
        self.facts: dict[tuple[str, tuple[str, ...], str], GroundFact] = {}

    def add_fact(self, fact: GroundFact) -> None:
        self.facts[(fact.predicate, fact.arguments, fact.evidence_id)] = fact

    def bind_schema0(self, schema: Schema, support: GroundSupport, *, port_name: str) -> WorkspaceAtom:
        """Bind one weak Schema_0 definition directly to observation support."""
        if schema.kind != "schema0":
            raise ValueError("only Schema_0 definitions may bind raw supports")
        ports = {port.name: port for port in schema.ports}
        if port_name not in ports or ports[port_name].type != support.type:
            raise ValueError("Schema_0 port is incompatible with the support")
        assignments = ((port_name, support.support_id),)
        open_ports = tuple(sorted(set(ports) - {port_name}))
        value = {"schema": schema.schema_id, "assignments": assignments, "support": support.support_id}
        binding = Binding(
            stable_id("binding", value), schema.schema_id, assignments, (), (), open_ports,
            (support.evidence_id,), (support.context_id,), 1, 11.0,
            BindingState.REIFIED if not open_ports else BindingState.PARTIAL,
        )
        self.bindings[binding.binding_id] = binding
        atom = WorkspaceAtom(
            binding.binding_id, schema.output_type, (support.evidence_id,), 0,
            "schema0_binding", binding.binding_id,
        )
        if binding.state == BindingState.REIFIED:
            self.atoms[atom.atom_id] = atom
        return atom

    def add_binding_atom(self, schema: Schema, binding: Binding) -> WorkspaceAtom:
        if binding.state != BindingState.REIFIED:
            raise ValueError("only complete bindings become recursive workspace atoms")
        assigned_atoms = [self.atoms[value] for _port, value in binding.assignments if value in self.atoms]
        grounding = {
            evidence for atom in assigned_atoms for evidence in atom.grounding_evidence_ids
        }
        environmental = {
            fact.evidence_id for fact in self.facts.values()
            if fact.evidence_id in binding.evidence_ids and fact.authority == "environment"
        }
        grounding.update(environmental)
        depth = 1 + max((atom.depth for atom in assigned_atoms), default=0)
        grounded = replace(binding, support=len(grounding))
        self.bindings[binding.binding_id] = grounded
        atom = WorkspaceAtom(
            binding.binding_id, schema.output_type, tuple(sorted(grounding)), depth,
            "schema_binding", binding.binding_id,
        )
        self.atoms[atom.atom_id] = atom
        return atom

    def grounded(self, atom_id: str) -> bool:
        return bool(self.atoms[atom_id].grounding_evidence_ids)


class EquivalenceIndex:
    """Quotient-like membership index without quadratic pair materialization."""

    def __init__(self) -> None:
        self._members: dict[tuple[str, str], set[str]] = defaultdict(set)

    def add(self, invariant_id: str, signature: str, member_id: str) -> str:
        key = invariant_id, signature
        self._members[key].add(member_id)
        return stable_id("equivalence", {"invariant": invariant_id, "signature": signature})

    def members(self, invariant_id: str, signature: str) -> tuple[str, ...]:
        return tuple(sorted(self._members.get((invariant_id, signature), ())))

    @property
    def membership_count(self) -> int:
        return sum(len(members) for members in self._members.values())


class RecursiveSchemaFitter:
    """Semi-naive, delta-triggered approximation to recursive schema closure.

    A new atom activates only schemas indexed for a compatible port type. Each
    derived complete binding becomes another typed atom. Every derivation in a
    cycle contains at least one atom from the current delta queue, and explicit
    budgets bound depth, joins and new graph mutations.
    """

    def __init__(self, store: SchemaStore, workspace: BindingWorkspace, *, budget: FrontierBudget = FrontierBudget()) -> None:
        self.store, self.workspace, self.budget = store, workspace, budget

    def close(self, delta_atom_ids: Sequence[str], delta_facts: Sequence[GroundFact] = ()) -> ClosureStats:
        for fact in delta_facts:
            self.workspace.add_fact(fact)
        # Carry the origin depth with every delta lineage. The budget limits
        # growth in this cycle, not the lifetime depth of the ontology.
        queue = deque((atom_id, self.workspace.atoms[atom_id].depth) for atom_id in delta_atom_ids)
        schemas_considered = joins = created = partial_created = 0
        maximum_depth = max((depth for _atom, depth in queue), default=0)
        exhausted = False
        seen_delta: set[str] = set()
        facts = tuple(self.workspace.facts.values())

        # Semi-naively revisit only partials whose open predicate appears in
        # the new fact delta. This lets later evidence complete old questions
        # without globally refitting the workspace.
        delta_predicates = {fact.predicate for fact in delta_facts}
        for previous in tuple(self.workspace.bindings.values()):
            if previous.state != BindingState.PARTIAL:
                continue
            schema = self.store.records[previous.schema_id].schema
            if not delta_predicates.intersection(schema.constraints[index].predicate for index in previous.open_constraints):
                continue
            for candidate in extend_binding(schema, previous, facts, budget=self.budget.binding_expansion):
                joins += 1
                if candidate.binding_id in self.workspace.bindings:
                    continue
                if candidate.state == BindingState.REIFIED:
                    atom = self.workspace.add_binding_atom(schema, candidate)
                    self.store.support(schema.schema_id, atom.grounding_evidence_ids)
                    maximum_depth = max(maximum_depth, atom.depth)
                    queue.append((atom.atom_id, atom.depth)); created += 1
                else:
                    self.workspace.bindings[candidate.binding_id] = candidate
                    for shadow in project_shadows(schema, candidate, limit=self.budget.shadow_generation):
                        self.workspace.shadows[shadow.shadow_id] = shadow
                    partial_created += 1
        while queue:
            atom_id, origin_depth = queue.popleft()
            if atom_id in seen_delta:
                continue
            seen_delta.add(atom_id)
            atom = self.workspace.atoms[atom_id]
            if atom.depth - origin_depth >= self.budget.max_depth_increment:
                continue
            candidate_ids = sorted(
                self.store.by_port_type.get(atom.type, ()),
                key=lambda schema_id: (-self.store.records[schema_id].salience, schema_id),
            )[:self.budget.retrieval]
            schemas_considered += len(candidate_ids)
            for schema_id in candidate_ids:
                schema = self.store.records[schema_id].schema
                for port in (port for port in schema.ports if port.type == atom.type):
                    joins += 1
                    if joins > self.budget.relation_joins:
                        exhausted = True; queue.clear(); break
                    candidates = fit_schema(
                        schema, facts, budget=self.budget.binding_expansion,
                        initial_assignments={port.name: atom_id},
                    )
                    for binding in candidates:
                        if binding.binding_id in self.workspace.bindings:
                            continue
                        if binding.state == BindingState.PARTIAL:
                            self.workspace.bindings[binding.binding_id] = binding
                            for shadow in project_shadows(schema, binding, limit=self.budget.shadow_generation):
                                self.workspace.shadows[shadow.shadow_id] = shadow
                            partial_created += 1
                            continue
                        new_atom = self.workspace.add_binding_atom(schema, binding)
                        self.store.support(schema.schema_id, new_atom.grounding_evidence_ids)
                        created += 1
                        maximum_depth = max(maximum_depth, new_atom.depth)
                        queue.append((new_atom.atom_id, origin_depth))
                        if created + partial_created >= self.budget.new_bindings:
                            exhausted = True; queue.clear(); break
                    if exhausted:
                        break
                if exhausted:
                    break
        return ClosureStats(len(delta_atom_ids), schemas_considered, joins, created, partial_created, maximum_depth, exhausted)
