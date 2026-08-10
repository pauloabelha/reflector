"""Content-addressed term arrays and a uniform schema/link graph."""

from __future__ import annotations

import hashlib
import itertools
import json
from collections import defaultdict
from collections.abc import Iterable, Sequence
from typing import TypeAlias

SYMBOL = 0
VARIABLE = 1
APPLICATION = 2

SCHEMA_CANDIDATE = 0
SCHEMA_ESTABLISHED = 1
SCHEMA_PROMOTED = 2

# A source-level argument is either a variable spelling or a scalar symbol.
SourceArg: TypeAlias = str | int | float
SourceAtom: TypeAlias = tuple[str, tuple[SourceArg, ...]]
DecompositionOccurrence: TypeAlias = tuple[int, dict[int, str]]
# Canonical arguments use variable ordinals or term IDs.
CanonicalArg: TypeAlias = tuple[str, int]
CanonicalAtom: TypeAlias = tuple[int, tuple[CanonicalArg, ...]]
GroundAtom: TypeAlias = tuple[int, tuple[int, ...]]


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


class TermStore:
    """A growable SoA term store; integer lists are the Phase-1 delta buffers."""

    def __init__(self) -> None:
        self.term_kind: list[int] = []
        self.term_symbol: list[int] = []
        self.child_offset: list[int] = []
        self.child_count: list[int] = []
        self.children: list[int] = []

        self.symbol_values: list[str | int | float] = []
        self._symbol_ids: dict[tuple[str, str], int] = {}
        self._term_ids: dict[tuple[object, ...], int] = {}

    def intern_symbol(self, value: str | int | float) -> int:
        if isinstance(value, bool):
            raise TypeError("boolean symbols are not accepted")
        tag = type(value).__name__
        key = (tag, repr(value))
        found = self._symbol_ids.get(key)
        if found is not None:
            return found
        symbol_id = len(self.symbol_values)
        self.symbol_values.append(value)
        term_id = self._append(SYMBOL, symbol_id, ())
        self._symbol_ids[key] = term_id
        return term_id

    def intern_variable(self, ordinal: int) -> int:
        key = (VARIABLE, ordinal)
        found = self._term_ids.get(key)
        if found is not None:
            return found
        term_id = self._append(VARIABLE, ordinal, ())
        self._term_ids[key] = term_id
        return term_id

    def intern_application(self, head: str | int, arguments: Sequence[int]) -> int:
        head_id = self.intern_symbol(head)
        key = (APPLICATION, head_id, *arguments)
        found = self._term_ids.get(key)
        if found is not None:
            return found
        term_id = self._append(APPLICATION, head_id, arguments)
        self._term_ids[key] = term_id
        return term_id

    def _append(self, kind: int, symbol: int, children: Sequence[int]) -> int:
        term_id = len(self.term_kind)
        self.term_kind.append(kind)
        self.term_symbol.append(symbol)
        self.child_offset.append(len(self.children))
        self.child_count.append(len(children))
        self.children.extend(children)
        return term_id

    def value(self, term_id: int) -> str | int | float:
        if self.term_kind[term_id] != SYMBOL:
            raise TypeError("term is not a symbol")
        return self.symbol_values[self.term_symbol[term_id]]

    def head_value(self, application_id: int) -> str | int | float:
        if self.term_kind[application_id] != APPLICATION:
            raise TypeError("term is not an application")
        return self.value(self.term_symbol[application_id])

    def application_children(self, application_id: int) -> tuple[int, ...]:
        start = self.child_offset[application_id]
        return tuple(self.children[start : start + self.child_count[application_id]])

    def ground_atom(self, head: str, arguments: Sequence[SourceArg]) -> GroundAtom:
        return (self.intern_symbol(head), tuple(self.intern_symbol(arg) for arg in arguments))

    def estimate_bytes(self) -> int:
        # Numeric target-layout estimate, deliberately excluding Python container overhead.
        return (
            len(self.term_kind)
            + 4 * len(self.term_symbol)
            + 8 * len(self.child_offset)
            + len(self.child_count)
            + 4 * len(self.children)
            + sum(len(str(value).encode("utf-8")) for value in self.symbol_values)
        )


def _canonicalize_source_atoms(
    atoms: Sequence[SourceAtom],
) -> tuple[tuple[tuple[str, tuple[tuple[str, object], ...]], ...], dict[str, int]]:
    """Return an alpha-invariant representation using structural refinement.

    Variables that have distinct relational roles are separated before search.
    Only variables that remain structurally symmetric are permuted.  The hard
    eight-variable cap still bounds the residual worst case.
    """

    variables = sorted(
        {
            arg
            for _head, args in atoms
            for arg in args
            if isinstance(arg, str) and arg.startswith("?")
        }
    )
    if len(variables) > 8:
        raise ValueError("a schema may contain at most 8 variables")
    if not 1 <= len(atoms) <= 16:
        raise ValueError("a schema body must contain 1..16 applications")
    if any(len(args) > 8 for _head, args in atoms):
        raise ValueError("application arity may not exceed 8")

    colors = {variable: 0 for variable in variables}
    while variables:
        signatures: dict[str, tuple[object, ...]] = {}
        for variable in variables:
            occurrences: list[object] = []
            for head, args in atoms:
                for position, argument in enumerate(args):
                    if argument != variable:
                        continue
                    context = []
                    for neighbor in args:
                        if isinstance(neighbor, str) and neighbor.startswith("?"):
                            context.append(("self",) if neighbor == variable else ("var", colors[neighbor]))
                        else:
                            context.append((type(neighbor).__name__, neighbor))
                    occurrences.append((head, len(args), position, tuple(context)))
            signatures[variable] = tuple(sorted(occurrences))
        ordered_signatures = {signature: index for index, signature in enumerate(sorted(set(signatures.values())))}
        refined = {variable: ordered_signatures[signatures[variable]] for variable in variables}
        if refined == colors:
            break
        colors = refined

    classes: dict[int, list[str]] = defaultdict(list)
    for variable in variables:
        classes[colors[variable]].append(variable)
    class_permutations: list[Iterable[tuple[int, ...]]] = []
    ordinal = 0
    for color in sorted(classes):
        width = len(classes[color])
        class_permutations.append(itertools.permutations(range(ordinal, ordinal + width)))
        ordinal += width
    renamings: Iterable[dict[str, int]]
    if not variables:
        renamings = [{}]
    else:
        renamings = (
            {
                variable: value
                for color, values in zip(sorted(classes), choices, strict=True)
                for variable, value in zip(classes[color], values, strict=True)
            }
            for choices in itertools.product(*class_permutations)
        )
    best: tuple[tuple[str, tuple[tuple[str, object], ...]], ...] | None = None
    best_renaming: dict[str, int] | None = None
    for renaming in renamings:
        encoded = []
        for head, args in atoms:
            if not isinstance(head, str) or not head:
                raise ValueError("application heads must be non-empty strings")
            encoded_args: list[tuple[str, object]] = []
            for arg in args:
                if isinstance(arg, str) and arg.startswith("?"):
                    encoded_args.append(("v", renaming[arg]))
                else:
                    encoded_args.append((type(arg).__name__, arg))
            encoded.append((head, tuple(encoded_args)))
        candidate = tuple(sorted(set(encoded)))
        if best is None or candidate < best:
            best = candidate
            best_renaming = dict(renaming)
    assert best is not None
    assert best_renaming is not None
    return best, best_renaming


def _canonical_source_atoms(
    atoms: Sequence[SourceAtom],
) -> tuple[tuple[str, tuple[tuple[str, object], ...]], ...]:
    return _canonicalize_source_atoms(atoms)[0]


def canonical_variable_ordinals(atoms: Sequence[SourceAtom]) -> dict[str, int]:
    """Return native alpha-normalized ordinals for source variable names."""

    _canonical, mapping = _canonicalize_source_atoms(atoms)
    return dict(mapping)


class SchemaGraph:
    """Uniform schema rows, local evidence arrays, links, and retrieval indices."""

    def __init__(self, terms: TermStore | None = None) -> None:
        self.terms = terms or TermStore()

        self.body_offset: list[int] = []
        self.body_count: list[int] = []
        self.body_roots: list[int] = []
        # The matcher consumes ``body_*`` (the compiled expansion).  A
        # constructed schema's meaning, however, is its child references plus
        # only the constraints introduced at this level.  These slices retain
        # that distinction without allocating nested graph objects.
        self.constraint_offset: list[int] = []
        self.constraint_count: list[int] = []
        self.constraint_roots: list[int] = []
        self.interface_offset: list[int] = []
        self.interface_count: list[int] = []
        self.interface_variables: list[int] = []
        self.canonical_hash: list[str] = []
        self.display_name: list[str] = []
        self.patterns: list[tuple[CanonicalAtom, ...]] = []
        self.provenance: list[set[str]] = []
        self.depth: list[int] = []
        self.schema_state: list[int] = []
        self.support: list[int] = []
        self.contradiction: list[int] = []
        self.prediction_success: list[int] = []
        self.prediction_failure: list[int] = []
        self.projection_support: list[int] = []
        self.projection_failure: list[int] = []
        self.use_count: list[int] = []
        self.last_used: list[int] = []
        self.distinct_contexts: list[set[str]] = []
        self.support_contexts: list[set[str]] = []
        self.projection_contexts: list[set[str]] = []
        self.projection_binding_signatures: list[set[str]] = []
        # Cold, path-specific evidence.  The key names a parent definition and
        # the roles/constraints that constituted one projected pathway; atoms
        # are deliberately not evidence targets here.
        self.projection_pathway_support: dict[tuple[int, int | None, tuple[int, ...], tuple[int, ...]], int] = defaultdict(int)
        self.projection_pathway_failure: dict[tuple[int, int | None, tuple[int, ...], tuple[int, ...]], int] = defaultdict(int)
        self.projection_pathway_contexts: dict[tuple[int, int | None, tuple[int, ...], tuple[int, ...]], set[str]] = defaultdict(set)

        self.src: list[int] = []
        self.relation: list[int] = []
        self.dst: list[int] = []
        self.weight: list[float] = []
        self.edge_flags: list[int] = []
        self.edge_provenance: list[set[str]] = []
        self.out_index: dict[int, list[int]] = defaultdict(list)

        # A semantic schema may have several derivations. Each derivation is a
        # finite DAG layer of child schema occurrences with an explicit map
        # from child-variable ordinal to owner-variable ordinal.
        self.decomposition_owner: list[int] = []
        self.decomposition_occurrence_offset: list[int] = []
        self.decomposition_occurrence_count: list[int] = []
        self.decomposition_provenance: list[set[str]] = []
        self.occurrence_schema: list[int] = []
        self.occurrence_map_offset: list[int] = []
        self.occurrence_map_count: list[int] = []
        self.occurrence_child_variable: list[int] = []
        self.occurrence_owner_variable: list[int] = []
        self.decomposition_out_index: dict[int, list[int]] = defaultdict(list)
        self._decomposition_keys: dict[tuple[object, ...], int] = {}

        self._hash_to_schema: dict[str, int] = {}
        self._name_to_schemas: dict[str, set[int]] = defaultdict(set)
        self._generic_signature_index: dict[tuple[int, int], list[int]] = defaultdict(list)
        self._ground_index: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)
        self.evidence_log: list[dict[str, str | int]] = []

    @property
    def schema_count(self) -> int:
        return len(self.canonical_hash)

    @property
    def edge_count(self) -> int:
        return len(self.src)

    def add_schema(
        self,
        name: str,
        atoms: Sequence[SourceAtom],
        *,
        provenance: str,
        decomposition: Sequence[DecompositionOccurrence] = (),
        candidate: bool = True,
        dag_identity: bool = False,
    ) -> tuple[int, bool]:
        canonical_source, source_variable_ordinals = _canonicalize_source_atoms(atoms)
        normalized_decomposition, constraint_indices = self._normalize_decomposition(
            decomposition, source_variable_ordinals, canonical_source, allow_constraints=dag_identity
        )
        if normalized_decomposition and dag_identity:
            # Names and construction order do not participate.  Child hashes
            # are stable content identities, and owner-variable ordinals came
            # from alpha-normalizing the complete compiled pattern.
            encoded_for_hash = _stable_json(
                {
                    "kind": "schema-dag/v1",
                    "children": [
                        (self.canonical_hash[child], pairs)
                        for child, pairs in normalized_decomposition
                    ],
                    "constraints": [canonical_source[index] for index in constraint_indices],
                    "interface": tuple(range(len(source_variable_ordinals))),
                }
            )
        else:
            encoded_for_hash = _stable_json({"kind": "schema-atom/v1", "body": canonical_source})
        digest = hashlib.sha256(encoded_for_hash.encode("utf-8")).hexdigest()
        found = self._hash_to_schema.get(digest)
        if found is not None:
            self.provenance[found].add(provenance)
            if not candidate and self.schema_state[found] == SCHEMA_CANDIDATE:
                self.schema_state[found] = SCHEMA_ESTABLISHED
            self._name_to_schemas[name].add(found)
            self._add_decomposition(
                found, normalized_decomposition, provenance
            )
            return found, False

        canonical_atoms: list[CanonicalAtom] = []
        roots: list[int] = []
        for head, args in canonical_source:
            compiled_args: list[CanonicalArg] = []
            child_ids: list[int] = []
            for tag, value in args:
                if tag == "v":
                    ordinal = int(value)
                    compiled_args.append(("v", ordinal))
                    child_ids.append(self.terms.intern_variable(ordinal))
                else:
                    term_id = self.terms.intern_symbol(value)  # type: ignore[arg-type]
                    compiled_args.append(("c", term_id))
                    child_ids.append(term_id)
            head_id = self.terms.intern_symbol(head)
            root = self.terms.intern_application(head, child_ids)
            canonical_atoms.append((head_id, tuple(compiled_args)))
            roots.append(root)

        schema_id = self.schema_count
        self.body_offset.append(len(self.body_roots))
        self.body_count.append(len(roots))
        self.body_roots.extend(roots)
        self.constraint_offset.append(len(self.constraint_roots))
        self.constraint_count.append(len(constraint_indices))
        self.constraint_roots.extend(roots[index] for index in constraint_indices)
        self.interface_offset.append(len(self.interface_variables))
        self.interface_count.append(len(source_variable_ordinals))
        self.interface_variables.extend(range(len(source_variable_ordinals)))
        self.canonical_hash.append(digest)
        self.display_name.append(name)
        pattern = tuple(canonical_atoms)
        self.patterns.append(pattern)
        self.provenance.append({provenance})
        child_ids = [schema_id for schema_id, _mapping in normalized_decomposition]
        self.depth.append(0 if not child_ids else 1 + max(self.depth[item] for item in child_ids))
        self.schema_state.append(SCHEMA_CANDIDATE if candidate else SCHEMA_ESTABLISHED)
        self.support.append(0)
        self.contradiction.append(0)
        self.prediction_success.append(0)
        self.prediction_failure.append(0)
        self.projection_support.append(0)
        self.projection_failure.append(0)
        self.use_count.append(0)
        self.last_used.append(0)
        self.distinct_contexts.append(set())
        self.support_contexts.append(set())
        self.projection_contexts.append(set())
        self.projection_binding_signatures.append(set())
        self._hash_to_schema[digest] = schema_id
        self._name_to_schemas[name].add(schema_id)

        for head, args in pattern:
            constants = [(position, value) for position, (tag, value) in enumerate(args) if tag == "c"]
            if not constants:
                self._generic_signature_index[(head, len(args))].append(schema_id)
            else:
                for position, value in constants:
                    self._ground_index[(head, len(args), position, value)].append(schema_id)
        self._add_decomposition(
            schema_id, normalized_decomposition, provenance
        )
        return schema_id, True

    def _normalize_decomposition(
        self,
        occurrences: Sequence[DecompositionOccurrence],
        source_variable_ordinals: dict[str, int],
        canonical_source: tuple[tuple[str, tuple[tuple[str, object], ...]], ...],
        *,
        allow_constraints: bool = False,
    ) -> tuple[tuple[tuple[int, tuple[tuple[int, int], ...]], ...], tuple[int, ...]]:
        normalized = []
        for child, mapping in occurrences:
            if not 0 <= child < self.schema_count:
                raise ValueError("decomposition references an unknown child schema")
            child_variables = {
                value
                for _head, args in self.patterns[child]
                for tag, value in args
                if tag == "v"
            }
            if set(mapping) != child_variables:
                raise ValueError("decomposition interface must map every child variable exactly once")
            pairs = []
            for child_variable, source_variable in sorted(mapping.items()):
                if source_variable not in source_variable_ordinals:
                    raise ValueError("decomposition interface references an unknown owner variable")
                pairs.append((child_variable, source_variable_ordinals[source_variable]))
            normalized.append((child, tuple(pairs)))
        normalized.sort()

        constraint_indices: tuple[int, ...] = tuple(range(len(canonical_source)))
        if normalized:
            expanded = set()
            for child, pairs in normalized:
                interface = dict(pairs)
                for head, args in self.patterns[child]:
                    expanded.add(
                        (
                            str(self.terms.value(head)),
                            tuple(
                                (
                                    ("v", interface[value])
                                    if tag == "v"
                                    else (
                                        type(self.terms.value(value)).__name__,
                                        self.terms.value(value),
                                    )
                                )
                                for tag, value in args
                            ),
                        )
                    )
            if not expanded <= set(canonical_source):
                raise ValueError("decomposition child expansion does not flatten into the owner schema")
            if not allow_constraints and tuple(sorted(expanded)) != canonical_source:
                raise ValueError("decomposition occurrences do not flatten to the owner schema")
            constraint_indices = tuple(
                index for index, atom in enumerate(canonical_source) if atom not in expanded
            )
        return tuple(normalized), constraint_indices

    def add_dag_schema(
        self,
        name: str,
        interface: Sequence[str],
        children: Sequence[DecompositionOccurrence],
        constraints: Sequence[SourceAtom],
        *,
        provenance: str,
        candidate: bool = True,
    ) -> tuple[int, bool]:
        """Install one reusable schema DAG and compile it to matcher atoms.

        ``children`` are references, not copies.  Their variable maps bind a
        child schema's canonical variables to this schema's exposed interface;
        ``constraints`` are the directed typed relations introduced by the
        parent.  The compiled expansion remains an implementation detail used
        by the existing indexed matcher.
        """

        declared = set(interface)
        if len(declared) != len(interface) or any(not item.startswith("?") for item in interface):
            raise ValueError("schema DAG interface must contain unique variables")
        atoms: list[SourceAtom] = list(constraints)
        for child, mapping in children:
            if not 0 <= child < self.schema_count:
                raise ValueError("schema DAG references an unknown child schema")
            child_variables = {
                value
                for _head, args in self.patterns[child]
                for tag, value in args
                if tag == "v"
            }
            if set(mapping) != child_variables or not set(mapping.values()) <= declared:
                raise ValueError("schema DAG child interface is incomplete or outside the exposed interface")
            for head, args in self.source_atoms(child):
                expanded = tuple(mapping[int(arg[2:])] if isinstance(arg, str) and arg.startswith("?v") else arg for arg in args)
                atoms.append((head, expanded))
        used = {arg for _head, args in atoms for arg in args if isinstance(arg, str) and arg.startswith("?")}
        if used != declared:
            raise ValueError("schema DAG interface must equal the variables used by children and constraints")
        return self.add_schema(
            name,
            atoms,
            provenance=provenance,
            decomposition=children,
            candidate=candidate,
            dag_identity=True,
        )

    def _add_decomposition(
        self,
        owner: int,
        occurrences: Sequence[tuple[int, tuple[tuple[int, int], ...]]],
        provenance: str,
    ) -> int | None:
        if not occurrences:
            return None
        # A hash-consed union that resolves to one of its operands is not a new
        # construction. Recording it would create a self-cycle.
        if any(child == owner for child, _mapping in occurrences):
            return None
        # Strict depth descent is the topological certificate. Alternative
        # decompositions that would require raising an established node (and
        # potentially all its parents) are rejected rather than made cyclic.
        if any(self.depth[child] >= self.depth[owner] for child, _mapping in occurrences):
            return None

        key: tuple[object, ...] = (owner, tuple(occurrences))
        found = self._decomposition_keys.get(key)
        if found is not None:
            self.decomposition_provenance[found].add(provenance)
            return found

        decomposition_id = len(self.decomposition_owner)
        self.decomposition_owner.append(owner)
        self.decomposition_occurrence_offset.append(len(self.occurrence_schema))
        self.decomposition_occurrence_count.append(len(occurrences))
        self.decomposition_provenance.append({provenance})
        self.decomposition_out_index[owner].append(decomposition_id)
        self._decomposition_keys[key] = decomposition_id
        for child, pairs in occurrences:
            self.occurrence_schema.append(child)
            self.occurrence_map_offset.append(len(self.occurrence_child_variable))
            self.occurrence_map_count.append(len(pairs))
            for child_variable, owner_variable in pairs:
                self.occurrence_child_variable.append(child_variable)
                self.occurrence_owner_variable.append(owner_variable)
            self._ensure_part_links(owner, child, provenance)
        return decomposition_id

    def _ensure_part_links(self, whole: int, part: int, provenance: str) -> None:
        part_relation = self.terms.intern_symbol("part")
        support_relation = self.terms.intern_symbol("supports")
        part_edge = next(
            (e for e in self.out_index[whole] if self.relation[e] == part_relation and self.dst[e] == part),
            None,
        )
        if part_edge is None:
            self.add_link(whole, "part", part, 1.0, provenance=provenance)
        else:
            self.edge_provenance[part_edge].add(provenance)
        support_edge = next(
            (e for e in self.out_index[part] if self.relation[e] == support_relation and self.dst[e] == whole),
            None,
        )
        if support_edge is None:
            self.add_link(part, "supports", whole, 0.25, provenance=provenance)
        else:
            self.edge_provenance[support_edge].add(provenance)

    def add_link(
        self,
        source: int,
        relation: str,
        destination: int,
        weight: float,
        *,
        provenance: str,
    ) -> int:
        edge_id = self.edge_count
        self.src.append(source)
        self.relation.append(self.terms.intern_symbol(relation))
        self.dst.append(destination)
        self.weight.append(float(weight))
        self.edge_flags.append(0)
        self.edge_provenance.append({provenance})
        self.out_index[source].append(edge_id)
        return edge_id

    def candidates(self, facts: Iterable[GroundAtom], limit: int) -> tuple[list[int], bool]:
        selected: set[int] = set()
        truncated = False
        for head, args in sorted(set(facts)):
            postings: list[Iterable[int]] = [self._generic_signature_index.get((head, len(args)), ())]
            postings.extend(
                self._ground_index.get((head, len(args), position, value), ())
                for position, value in enumerate(args)
            )
            for schema_id in itertools.chain.from_iterable(postings):
                selected.add(schema_id)
                if len(selected) >= limit:
                    truncated = True
                    return sorted(selected), truncated
        return sorted(selected), truncated

    def schema_reference(self, reference: str) -> int:
        by_hash = self._hash_to_schema.get(reference)
        if by_hash is not None:
            return by_hash
        by_name = self._name_to_schemas.get(reference, set())
        if len(by_name) != 1:
            raise ValueError(f"schema reference is unknown or ambiguous: {reference}")
        return next(iter(by_name))

    def add_evidence(
        self,
        schema_id: int,
        kind: str,
        amount: int,
        context: str,
        cycle: int,
        *,
        source: str = "runtime",
    ) -> None:
        if amount < 0:
            raise ValueError("evidence amount must be non-negative")
        target = {
            "support": self.support,
            "contradiction": self.contradiction,
            "prediction-success": self.prediction_success,
            "prediction-failure": self.prediction_failure,
            "projection-success": self.projection_support,
            "projection-failure": self.projection_failure,
        }.get(kind)
        if target is None:
            raise ValueError(f"unknown evidence kind: {kind}")
        target[schema_id] += amount
        self.last_used[schema_id] = cycle
        self.distinct_contexts[schema_id].add(context)
        if kind == "support":
            self.support_contexts[schema_id].add(context)
        if kind == "projection-success":
            self.projection_contexts[schema_id].add(context)
        self.evidence_log.append(
            {
                "schema": self.canonical_hash[schema_id],
                "kind": kind,
                "amount": amount,
                "context": context,
                "cycle": cycle,
                "source": source,
            }
        )
        if self.schema_state[schema_id] == SCHEMA_CANDIDATE and (
            (
                self.support[schema_id] >= 2
                and len(self.support_contexts[schema_id]) >= 2
            )
            or self.prediction_success[schema_id] >= 2
        ):
            self.schema_state[schema_id] = SCHEMA_PROMOTED

    def add_projection_pathway_evidence(
        self,
        schema_id: int,
        decomposition_id: int | None,
        role_indices: Sequence[int],
        constraint_indices: Sequence[int],
        kind: str,
        context: str,
        cycle: int,
        *,
        source: str,
        binding_signature: str,
    ) -> None:
        """Attach projection evidence to a parent definition pathway, not atoms."""

        if kind not in {"projection-success", "projection-failure"}:
            raise ValueError("pathway evidence must be projection success or failure")
        key = (schema_id, decomposition_id, tuple(sorted(role_indices)), tuple(sorted(constraint_indices)))
        self.add_evidence(schema_id, kind, 1, context, cycle, source=source)
        target = self.projection_pathway_support if kind == "projection-success" else self.projection_pathway_failure
        target[key] += 1
        self.projection_pathway_contexts[key].add(context)
        if kind == "projection-success":
            self.projection_binding_signatures[schema_id].add(binding_signature)
        self.evidence_log[-1]["pathway"] = f"definition:{decomposition_id};roles:{key[2]};constraints:{key[3]}"
        self.evidence_log[-1]["binding_signature"] = binding_signature

    def source_atoms(self, schema_id: int) -> tuple[SourceAtom, ...]:
        output: list[SourceAtom] = []
        for head_id, args in self.patterns[schema_id]:
            head = str(self.terms.value(head_id))
            source_args: list[SourceArg] = []
            for tag, value in args:
                source_args.append(f"?v{value}" if tag == "v" else self.terms.value(value))
            output.append((head, tuple(source_args)))
        return tuple(output)

    def definition_constraint_atoms(self, schema_id: int) -> tuple[SourceAtom, ...]:
        """Return only relations imposed by this schema above its children."""

        start = self.constraint_offset[schema_id]
        stop = start + self.constraint_count[schema_id]
        output: list[SourceAtom] = []
        for root in self.constraint_roots[start:stop]:
            head = str(self.terms.head_value(root))
            args: list[SourceArg] = []
            for term in self.terms.application_children(root):
                if self.terms.term_kind[term] == VARIABLE:
                    args.append(f"?v{self.terms.term_symbol[term]}")
                else:
                    args.append(self.terms.value(term))
            output.append((head, tuple(args)))
        return tuple(output)

    def decomposition_occurrences(
        self, decomposition_id: int
    ) -> tuple[tuple[int, tuple[tuple[int, int], ...]], ...]:
        start = self.decomposition_occurrence_offset[decomposition_id]
        stop = start + self.decomposition_occurrence_count[decomposition_id]
        output = []
        for occurrence_id in range(start, stop):
            map_start = self.occurrence_map_offset[occurrence_id]
            map_stop = map_start + self.occurrence_map_count[occurrence_id]
            interface = tuple(
                zip(
                    self.occurrence_child_variable[map_start:map_stop],
                    self.occurrence_owner_variable[map_start:map_stop],
                    strict=True,
                )
            )
            output.append((self.occurrence_schema[occurrence_id], interface))
        return tuple(output)

    def estimate_bytes(self) -> int:
        return (
            8 * len(self.body_offset)
            + len(self.body_count)
            + 4 * len(self.body_roots)
            + 8 * len(self.constraint_offset)
            + len(self.constraint_count)
            + 4 * len(self.constraint_roots)
            + 8 * len(self.interface_offset)
            + len(self.interface_count)
            + 2 * len(self.interface_variables)
            + 32 * len(self.canonical_hash)
            + (4 * 7 + 1) * self.schema_count
            + (4 + 2 + 4 + 4 + 1) * self.edge_count
            + (8 + 8 + 1) * len(self.decomposition_owner)
            + (4 + 8 + 1) * len(self.occurrence_schema)
            + 2 * len(self.occurrence_child_variable)
        )
