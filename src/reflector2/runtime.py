"""Bounded indexed matching, sparse activation, composition, and morphism learning."""

from __future__ import annotations

import resource
import time
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any

from .perception import PerceptionBatch
from .store import (
    CanonicalAtom,
    DecompositionOccurrence,
    GroundAtom,
    SchemaGraph,
    SourceArg,
    SourceAtom,
    SCHEMA_CANDIDATE,
    SCHEMA_ESTABLISHED,
    SCHEMA_PROMOTED,
)

FactIndex = dict[tuple[int, int], list[tuple[int, ...]]]
FactSlotIndex = dict[tuple[int, int, int, int], list[tuple[int, ...]]]


@dataclass(frozen=True, slots=True)
class Limits:
    max_active_nodes: int = 256
    max_active_edges: int = 1024
    max_binding_candidates: int = 512
    max_facts_per_atom: int = 2048
    max_partial_bindings: int = 1024
    max_bindings_per_schema: int = 64
    max_composition_proposals: int = 256
    max_new_compositions: int = 128
    max_composition_rounds: int = 4
    max_relational_closures: int = 64
    max_composition_body: int = 16
    max_expansion_rounds: int = 2
    max_transition_correspondences: int = 128
    max_analogy_candidates: int = 128
    max_queue_items: int = 4096


@dataclass(slots=True)
class Metrics:
    candidates_retrieved: int = 0
    candidates_verified: int = 0
    compositions_proposed: int = 0
    compositions_retained: int = 0
    work_items_processed: int = 0
    work_items_by_kind: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    frontier_sizes: list[int] = field(default_factory=list)
    peak_workspace: int = 0
    active_edge_visits: int = 0
    truncations: int = 0
    matching_time_s: float = 0.0
    activation_time_s: float = 0.0
    composition_time_s: float = 0.0
    transition_learning_time_s: float = 0.0
    shadow_projections: int = 0
    shadow_reifications: int = 0
    shadow_refutations: int = 0
    parent_binding_memo_hits: int = 0
    parent_match_memo_hits: int = 0

    def work(self, kind: str, amount: int = 1) -> None:
        self.work_items_processed += amount
        self.work_items_by_kind[kind] += amount

    def deterministic(self) -> dict[str, Any]:
        value = asdict(self)
        for key in tuple(value):
            if key.endswith("_time_s"):
                value.pop(key)
        value["work_items_by_kind"] = dict(sorted(self.work_items_by_kind.items()))
        return value


@dataclass(slots=True)
class Workspace:
    context: str
    activation: dict[int, float] = field(default_factory=dict)
    bindings: list["Binding"] = field(default_factory=list)
    active_edge_ids: set[int] = field(default_factory=set)
    shadow_ids: list[int] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Binding:
    """A compact realization of one reusable schema in one carrier/context."""

    schema_id: int
    assignments: tuple[tuple[int, int], ...]
    carrier: str
    activation: float = 1.0
    provenance: str = "observation"

    def as_dict(self) -> dict[int, int]:
        return dict(self.assignments)

    def __iter__(self):
        # Keeps internal consumers concise while the record remains explicitly
        # separate from the schema definition.
        yield self.schema_id
        yield self.as_dict()


SHADOW = "SHADOW"
REIFIED = "REIFIED"
REFUTED = "REFUTED"
PROJECTED = "PROJECTED"


@dataclass(frozen=True, slots=True)
class ChildRoleState:
    """One child-schema occurrence inside a partial parent DAG binding."""

    role_index: int
    occurrence_id: int
    child_schema_id: int
    assignments: tuple[tuple[int, int], ...]
    status: str


@dataclass(frozen=True, slots=True)
class ConstraintState:
    """One parent-level constraint: observed/reified or projected only."""

    constraint_index: int
    status: str


@dataclass(slots=True)
class Shadow:
    """A demand-driven, partially bound projection of one schema DAG."""

    shadow_id: int
    schema_id: int
    assignments: tuple[tuple[int, int], ...]
    carrier: str
    open_roles: tuple[int, ...]
    open_constraints: tuple[int, ...]
    activation: float
    provenance: str
    decomposition_id: int | None = None
    child_roles: tuple[ChildRoleState, ...] = ()
    constraints: tuple[ConstraintState, ...] = ()
    status: str = SHADOW
    reified_assignments: tuple[tuple[int, int], ...] | None = None
    completed_roles: tuple[int, ...] = ()
    completed_constraints: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class PendingPrediction:
    prediction_id: int
    schema_id: int
    expected: GroundAtom
    context: str


class Runtime:
    """Deterministic coordinator over a sparse schema-graph delta generation."""

    def __init__(self, graph: SchemaGraph | None = None, limits: Limits | None = None) -> None:
        self.graph = graph or SchemaGraph()
        self.limits = limits or Limits()
        self.metrics = Metrics()
        self.cycle = 0
        self.trace: list[dict[str, Any]] = []
        self.workspace: Workspace | None = None
        self._next_prediction = 0
        self._next_shadow = 0
        self._pending: dict[int, PendingPrediction] = {}
        self.shadows: dict[int, Shadow] = {}
        self._parent_binding_memo: dict[tuple[object, ...], int] = {}
        self._parent_match_memo: dict[tuple[object, ...], tuple[tuple[int, int], ...] | None] = {}
        # Audited quantitative sensory relations. Numeric palette/value IDs are
        # nominal and must never acquire order semantics from their encoding.
        self.ordered_relations = frozenset({"Count", "EnclosureCount"})
        self.kernel_schema_ids: dict[str, int] = {}
        self._install_kernel_schemas()

    def _truncation(self, reason: str) -> None:
        self.metrics.truncations += 1
        self.trace.append(
            {"event": "truncation", "cycle": self.cycle, "reason": reason}
        )

    def _install_kernel_schemas(self) -> None:
        schemas: list[tuple[str, list[SourceAtom]]] = [
            ("RegionDescriptor", [("Kind", ("?x", "Region"))]),
            ("CellDescriptor", [("Kind", ("?x", "Cell"))]),
            ("ConnectedDescriptor", [("Connected", ("?x",))]),
            ("ColorDescriptor", [("Color", ("?x", "?value"))]),
            ("FormDescriptor", [("Form", ("?x", "?form"))]),
            ("EnclosedDescriptor", [("Enclosed", ("?h",))]),
            ("InsideDescriptor", [("Inside", ("?h", "?x"))]),
            ("EnclosureCountDescriptor", [("EnclosureCount", ("?x", "?n"))]),
            ("CellValueDescriptor", [("Kind", ("?x", "Cell")), ("Value", ("?x", "?v"))]),
        ]
        for name, atoms in schemas:
            schema_id, _ = self.graph.add_schema(
                name, atoms, provenance="kernel", candidate=False
            )
            self.kernel_schema_ids[name] = schema_id

    def _ensure_form_schemas(self, batch: PerceptionBatch) -> None:
        for form_term in batch.form_terms:
            form_value = self.graph.terms.value(form_term)
            digest_fragment = str(form_value).split(":")[-1][:10]
            self.graph.add_schema(
                f"FormPattern:{digest_fragment}",
                [("Form", ("?x", form_value))],
                provenance="endogenous:form-index",
            )

    def _ensure_figure_schemas(self, batch: PerceptionBatch) -> None:
        relation_names = {
            str(self.graph.terms.value(head))
            for head, _arguments in batch.facts
        }
        if not {"SameOutline", "SameInteriorContrast", "DifferentInteriorContrast"} & relation_names:
            return
        for name, atoms in (
            ("FigureDescriptor", [("Kind", ("?x", "Figure"))]),
            ("OutlineDescriptor", [("OutlineForm", ("?x", "?outline"))]),
            ("InteriorContrastDescriptor", [("InteriorContrastCount", ("?x", "?n"))]),
            ("SameOutlinePair", [("SameOutline", ("?left", "?right"))]),
            (
                "DifferentInteriorContrastPair",
                [("DifferentInteriorContrast", ("?left", "?right"))],
            ),
            ("SameInteriorContrastPair", [("SameInteriorContrast", ("?left", "?right"))]),
        ):
            self.graph.add_schema(name, atoms, provenance="kernel", candidate=False)
        for outline_term in batch.outline_terms:
            outline_value = self.graph.terms.value(outline_term)
            digest_fragment = str(outline_value).split(":")[-1][:10]
            self.graph.add_schema(
                f"OutlinePattern:{digest_fragment}",
                [("OutlineForm", ("?x", outline_value))],
                provenance="endogenous:outline-index",
            )

    def observe(self, batch: PerceptionBatch, *, compose: bool = True) -> Workspace:
        self.cycle += 1
        self._ensure_form_schemas(batch)
        self._ensure_figure_schemas(batch)
        workspace = Workspace(batch.context)
        self.trace.append(
            {
                "event": "observation",
                "cycle": self.cycle,
                "context": batch.context,
                "source": batch.source,
                "fact_count": len(batch.facts),
            }
        )

        start = time.perf_counter()
        candidates, truncated = self.graph.candidates(batch.facts, self.limits.max_binding_candidates)
        self.metrics.candidates_retrieved += len(candidates)
        if truncated:
            self._truncation("binding-candidate-budget")
        fact_index: FactIndex = defaultdict(list)
        fact_slot_index: FactSlotIndex = defaultdict(list)
        for head, args in batch.facts:
            fact_index[(head, len(args))].append(args)
            for position, value in enumerate(args):
                fact_slot_index[(head, len(args), position, value)].append(args)
        for values in (*fact_index.values(), *fact_slot_index.values()):
            values.sort()
        joinable_values = {args[0] for _head, args in batch.facts if args}

        for schema_id in candidates:
            self.metrics.candidates_verified += 1
            self.metrics.work("TRY_BIND")
            bindings, was_truncated = self._verify(
                self.graph.patterns[schema_id], fact_index, fact_slot_index
            )
            if was_truncated:
                self._truncation("binding-verification-budget")
            if not bindings:
                continue
            self.graph.use_count[schema_id] += len(bindings)
            workspace.bindings.extend(
                Binding(schema_id, tuple(sorted(binding.items())), batch.context)
                for binding in bindings
            )
            workspace.activation[schema_id] = min(1.0, workspace.activation.get(schema_id, 0.0) + 0.5)
            self.trace.append(
                {"event": "binding", "cycle": self.cycle, "context": batch.context, "schema": self.graph.canonical_hash[schema_id]}
            )
        self.metrics.matching_time_s += time.perf_counter() - start

        self._prune(workspace)
        self._expand(workspace)
        if compose:
            # Bounded breadth-first closure: each round preserves a share of
            # the total work budget while preferentially extending schemas
            # created in the prior round. This lets relation + endpoint
            # descriptors become higher-level schemas without privileging any
            # named visual form or task.
            remaining_proposals = (
                self.limits.max_composition_proposals - self.limits.max_relational_closures
            )
            remaining_new = self.limits.max_new_compositions
            preferred: set[int] = set()
            for round_index in range(self.limits.max_composition_rounds):
                rounds_left = self.limits.max_composition_rounds - round_index
                proposal_budget = remaining_proposals // rounds_left
                if proposal_budget <= 0 or remaining_new <= 0:
                    break
                _used, created = self._compose(
                    workspace,
                    fact_index,
                    fact_slot_index,
                    joinable_values,
                    proposal_budget=proposal_budget,
                    retention_budget=remaining_new,
                    preferred_schema_ids=preferred,
                )
                remaining_proposals -= proposal_budget
                remaining_new -= len(created)
                preferred = created
                self._prune(workspace)
                self._expand(workspace)
            if remaining_new > 0:
                self._compose_relational_closures(
                    workspace,
                    fact_index,
                    fact_slot_index,
                    entity_terms={
                        arguments[0]
                        for head, arguments in batch.facts
                        if str(self.graph.terms.value(head)) == "Kind" and arguments
                    },
                    proposal_budget=self.limits.max_relational_closures,
                    retention_budget=remaining_new,
                )
                self._prune(workspace)
                self._expand(workspace)
        self._prune(workspace)
        self.metrics.peak_workspace = max(self.metrics.peak_workspace, len(workspace.activation))
        self.workspace = workspace
        return workspace

    def _verify(
        self,
        pattern: tuple[CanonicalAtom, ...],
        fact_index: FactIndex,
        fact_slot_index: FactSlotIndex | None = None,
    ) -> tuple[list[dict[int, int]], bool]:
        def posting_size(atom: CanonicalAtom) -> int:
            head, arguments = atom
            sizes = [len(fact_index.get((head, len(arguments)), ()))]
            if fact_slot_index is not None:
                sizes.extend(
                    len(fact_slot_index.get((head, len(arguments), position, value), ()))
                    for position, (tag, value) in enumerate(arguments)
                    if tag == "c"
                )
            return min(sizes)

        ordered = sorted(pattern, key=lambda atom: (posting_size(atom), atom))
        partials: list[dict[int, int]] = [{}]
        truncated = False
        for head, pattern_args in ordered:
            next_partials: list[dict[int, int]] = []
            for partial in partials:
                facts = fact_index.get((head, len(pattern_args)), ())
                if fact_slot_index is not None:
                    constrained = []
                    for position, (tag, value) in enumerate(pattern_args):
                        required = value if tag == "c" else partial.get(value)
                        if required is not None:
                            constrained.append(
                                fact_slot_index.get(
                                    (head, len(pattern_args), position, required), ()
                                )
                            )
                    if constrained:
                        facts = min(constrained, key=len)
                if len(facts) > self.limits.max_facts_per_atom:
                    facts = facts[: self.limits.max_facts_per_atom]
                    truncated = True
                for fact_args in facts:
                    candidate = dict(partial)
                    valid = True
                    for (tag, value), fact_value in zip(pattern_args, fact_args, strict=True):
                        if tag == "c":
                            valid = value == fact_value
                        else:
                            prior = candidate.get(value)
                            valid = prior is None or prior == fact_value
                            if valid:
                                candidate[value] = fact_value
                        if not valid:
                            break
                    if valid:
                        next_partials.append(candidate)
                        if len(next_partials) >= self.limits.max_partial_bindings:
                            truncated = True
                            break
                if truncated:
                    break
            partials = next_partials
            if not partials:
                break
        if len(partials) > self.limits.max_bindings_per_schema:
            truncated = True
            partials = partials[: self.limits.max_bindings_per_schema]
        return partials, truncated

    @staticmethod
    def _fact_indices(batch: PerceptionBatch) -> tuple[FactIndex, FactSlotIndex]:
        fact_index: FactIndex = defaultdict(list)
        fact_slot_index: FactSlotIndex = defaultdict(list)
        for head, args in batch.facts:
            fact_index[(head, len(args))].append(args)
            for position, value in enumerate(args):
                fact_slot_index[(head, len(args), position, value)].append(args)
        for values in (*fact_index.values(), *fact_slot_index.values()):
            values.sort()
        return fact_index, fact_slot_index

    def project_shadow(
        self,
        schema_id: int,
        partial_binding: dict[int, int],
        *,
        child_bindings: dict[int, Binding] | None = None,
        verified_constraints: set[int] | None = None,
        carrier: str | None = None,
        activation: float | None = None,
        provenance: str = "schema-completion",
    ) -> Shadow:
        """Project one requested schema DAG from explicit child-role state.

        This intentionally performs neither global schema retrieval nor
        consequence enumeration.  It records an epistemic expectation; it
        does not add a fact or a normal binding.
        """

        if not 0 <= schema_id < self.graph.schema_count:
            raise ValueError("shadow references an unknown schema")
        variables = {
            value
            for _head, args in self.graph.patterns[schema_id]
            for tag, value in args
            if tag == "v"
        }
        if not set(partial_binding) <= variables:
            raise ValueError("partial binding contains a variable outside the schema interface")
        assignments_by_variable = dict(partial_binding)
        carrier_id = carrier or (self.workspace.context if self.workspace else "projection")
        decomposition_ids = self.graph.decomposition_out_index.get(schema_id, ())
        decomposition_id = decomposition_ids[0] if decomposition_ids else None
        role_states: list[ChildRoleState] = []
        for role_index, (child_schema_id, interface) in enumerate(
            () if decomposition_id is None else self.graph.decomposition_occurrences(decomposition_id)
        ):
            supplied = (child_bindings or {}).get(role_index)
            if supplied is not None:
                if supplied.schema_id != child_schema_id:
                    raise ValueError("child binding does not realize the referenced role schema")
                child_assignment = supplied.as_dict()
                for child_variable, parent_variable in interface:
                    if child_variable not in child_assignment:
                        raise ValueError("child binding is incomplete for its role interface")
                    prior = assignments_by_variable.get(parent_variable)
                    if prior is not None and prior != child_assignment[child_variable]:
                        raise ValueError("child bindings disagree on a parent interface variable")
                    assignments_by_variable[parent_variable] = child_assignment[child_variable]
            child_assignments = tuple(
                (child_variable, assignments_by_variable[parent_variable])
                for child_variable, parent_variable in interface
                if parent_variable in assignments_by_variable
            )
            role_states.append(
                ChildRoleState(
                    role_index,
                    self.graph.decomposition_occurrence_offset[decomposition_id] + role_index,
                    child_schema_id,
                    child_assignments,
                    # Assigned parent variables alone are not evidence that a
                    # child schema matched.  Only an explicit child Binding
                    # realizes a child-role occurrence.
                    REIFIED if supplied is not None else SHADOW,
                )
            )
        verified = verified_constraints or set()
        constraint_states = tuple(
            ConstraintState(index, REIFIED if index in verified else PROJECTED)
            for index, _constraint in enumerate(self.graph.definition_constraint_atoms(schema_id))
        )
        assignments = tuple(sorted(assignments_by_variable.items()))
        open_roles = tuple(sorted(variables - set(assignments_by_variable)))
        open_constraints = (
            tuple(state.constraint_index for state in constraint_states if state.status != REIFIED)
            if constraint_states
            else tuple(
                index
                for index, (_head, args) in enumerate(self.graph.patterns[schema_id])
                if any(tag == "v" and value not in assignments_by_variable for tag, value in args)
            )
        )
        completed = sum(state.status == REIFIED for state in role_states) + sum(
            state.status == REIFIED for state in constraint_states
        )
        total = len(role_states) + len(constraint_states)
        incremental_activation = 0.0 if total == 0 else completed / total
        shadow_activation = incremental_activation if activation is None else max(
            incremental_activation, max(0.0, min(1.0, activation))
        )
        memo_key = (
            schema_id,
            carrier_id,
            decomposition_id,
            assignments,
            tuple((role.role_index, role.child_schema_id, role.assignments, role.status) for role in role_states),
            tuple((constraint.constraint_index, constraint.status) for constraint in constraint_states),
        )
        memoized_id = self._parent_binding_memo.get(memo_key)
        if memoized_id is not None and self.shadows[memoized_id].status == SHADOW:
            self.metrics.parent_binding_memo_hits += 1
            self.metrics.work("MEMO_PARENT_BINDING")
            return self.shadows[memoized_id]
        shadow = Shadow(
            self._next_shadow,
            schema_id,
            assignments,
            carrier_id,
            open_roles,
            open_constraints,
            shadow_activation,
            provenance,
            decomposition_id,
            tuple(role_states),
            constraint_states,
        )
        self._next_shadow += 1
        self.shadows[shadow.shadow_id] = shadow
        self._parent_binding_memo[memo_key] = shadow.shadow_id
        if self.workspace is not None and self.workspace.context == shadow.carrier:
            self.workspace.shadow_ids.append(shadow.shadow_id)
            self.workspace.activation[schema_id] = max(
                self.workspace.activation.get(schema_id, 0.0), shadow_activation
            )
        self.metrics.shadow_projections += 1
        self.metrics.work("PROJECT_SHADOW")
        self.trace.append(
            {
                "event": "shadow-projection",
                "cycle": self.cycle,
                "shadow": shadow.shadow_id,
                "schema": self.graph.canonical_hash[schema_id],
                "carrier": shadow.carrier,
                "open_roles": list(open_roles),
                "role_states": [state.status for state in role_states],
                "constraint_states": [state.status for state in constraint_states],
            }
        )
        return shadow

    def reconcile_shadow(self, shadow_id: int, observed: PerceptionBatch) -> bool:
        """Reify a projected frontier if later evidence supplies a full match."""

        shadow = self.shadows[shadow_id]
        if shadow.status != SHADOW:
            return shadow.status == REIFIED
        expected = dict(shadow.assignments)
        match_key = (shadow.schema_id, shadow.assignments, observed.context, tuple(observed.facts))
        cached = self._parent_match_memo.get(match_key, ...)
        if cached is ...:
            fact_index, fact_slot_index = self._fact_indices(observed)
            matches, truncated = self._verify(
                self.graph.patterns[shadow.schema_id], fact_index, fact_slot_index
            )
            if truncated:
                self._truncation("shadow-reconciliation-budget")
            match = next(
                (candidate for candidate in matches if all(candidate.get(key) == value for key, value in expected.items())),
                None,
            )
            cached = None if match is None else tuple(sorted(match.items()))
            self._parent_match_memo[match_key] = cached
        else:
            self.metrics.parent_match_memo_hits += 1
            self.metrics.work("MEMO_PARENT_MATCH")
        if cached is None:
            return False
        match = dict(cached)
        shadow.status = REIFIED
        shadow.reified_assignments = cached
        old_role_states = shadow.child_roles
        new_role_states: list[ChildRoleState] = []
        for state in old_role_states:
            interface = self.graph.decomposition_occurrences(shadow.decomposition_id)[state.role_index][1] if shadow.decomposition_id is not None else ()
            new_role_states.append(
                ChildRoleState(
                    state.role_index,
                    state.occurrence_id,
                    state.child_schema_id,
                    tuple((child_variable, match[parent_variable]) for child_variable, parent_variable in interface),
                    REIFIED,
                )
            )
        shadow.completed_roles = tuple(state.role_index for state in old_role_states if state.status != REIFIED)
        shadow.completed_constraints = tuple(
            state.constraint_index for state in shadow.constraints if state.status != REIFIED
        )
        shadow.child_roles = tuple(new_role_states)
        shadow.constraints = tuple(ConstraintState(state.constraint_index, REIFIED) for state in shadow.constraints)
        self.graph.add_projection_pathway_evidence(
            shadow.schema_id,
            shadow.decomposition_id,
            tuple(state.role_index for state in shadow.child_roles),
            tuple(state.constraint_index for state in shadow.constraints),
            "projection-success",
            observed.context,
            self.cycle,
            source="shadow:reified",
        )
        self.metrics.shadow_reifications += 1
        self.metrics.work("REIFY_SHADOW")
        self.trace.append(
            {
                "event": "shadow-reified",
                "cycle": self.cycle,
                "shadow": shadow_id,
                "schema": self.graph.canonical_hash[shadow.schema_id],
                "carrier": observed.context,
                "completed_roles": list(shadow.completed_roles),
                "completed_constraints": list(shadow.completed_constraints),
            }
        )
        return True

    def refute_shadow(self, shadow_id: int, *, context: str | None = None, provenance: str = "environment") -> None:
        """Record an applicable contradiction without turning the projection into a fact."""

        shadow = self.shadows[shadow_id]
        if shadow.status != SHADOW:
            raise ValueError("only unresolved shadows may be refuted")
        shadow.status = REFUTED
        failure_context = context or shadow.carrier
        self.graph.add_projection_pathway_evidence(
            shadow.schema_id,
            shadow.decomposition_id,
            tuple(state.role_index for state in shadow.child_roles),
            tuple(state.constraint_index for state in shadow.constraints),
            "projection-failure",
            failure_context,
            self.cycle,
            source=provenance,
        )
        self.metrics.shadow_refutations += 1
        self.metrics.work("REFUTE_SHADOW")
        self.trace.append(
            {
                "event": "shadow-refuted",
                "cycle": self.cycle,
                "shadow": shadow_id,
                "schema": self.graph.canonical_hash[shadow.schema_id],
                "carrier": failure_context,
            }
        )

    def _expand(self, workspace: Workspace) -> None:
        start = time.perf_counter()
        frontier = sorted(workspace.activation)
        for _round in range(self.limits.max_expansion_rounds):
            if not frontier:
                break
            self.metrics.frontier_sizes.append(len(frontier))
            deltas: dict[int, float] = defaultdict(float)
            for source in frontier:
                for edge_id in self.graph.out_index.get(source, ()):
                    if len(workspace.active_edge_ids) >= self.limits.max_active_edges:
                        self._truncation("active-edge-budget")
                        break
                    workspace.active_edge_ids.add(edge_id)
                    self.metrics.active_edge_visits += 1
                    self.metrics.work("EXPAND")
                    deltas[self.graph.dst[edge_id]] += self.graph.weight[edge_id] * workspace.activation[source]
            next_frontier = []
            for destination, delta in sorted(deltas.items()):
                previous = workspace.activation.get(destination, 0.0)
                updated = min(1.0, previous + delta)
                workspace.activation[destination] = updated
                if previous == 0.0 and updated > 0.05:
                    next_frontier.append(destination)
            frontier = next_frontier
        self.metrics.activation_time_s += time.perf_counter() - start

    def _compose(
        self,
        workspace: Workspace,
        fact_index: FactIndex,
        fact_slot_index: FactSlotIndex,
        joinable_values: set[int],
        *,
        proposal_budget: int,
        retention_budget: int,
        preferred_schema_ids: set[int] | None = None,
    ) -> tuple[int, set[int]]:
        start = time.perf_counter()
        preferred_schema_ids = preferred_schema_ids or set()
        by_value: dict[int, list[tuple[int, dict[int, int]]]] = defaultdict(list)
        for schema_id, binding in workspace.bindings:
            for value in set(binding.values()) & joinable_values:
                by_value[value].append((schema_id, binding))

        proposed_keys: set[tuple[int, int, int]] = set()
        generation_truncated = False
        proposal_groups: list[
            tuple[int, list[tuple[tuple[int, int, int, int, int, str], int, int, dict[int, int], dict[int, int]]]]
        ] = []
        for shared_value, entries in sorted(by_value.items()):
            unique = sorted(entries, key=lambda item: (self.graph.canonical_hash[item[0]], sorted(item[1].items())))
            if len(unique) > self.limits.max_bindings_per_schema:
                generation_truncated = True
                unique = unique[: self.limits.max_bindings_per_schema]
            binding_degree = len({schema_id for schema_id, _binding in unique})
            group: list[tuple[tuple[int, int, int, int, int, str], int, int, dict[int, int], dict[int, int]]] = []
            for left_index, (left, left_binding) in enumerate(unique):
                for right, right_binding in unique[left_index + 1 :]:
                    if left == right:
                        continue
                    key = (min(left, right), max(left, right), shared_value)
                    if key in proposed_keys:
                        continue
                    proposed_keys.add(key)
                    constant_count = sum(
                        tag == "c"
                        for schema_id in (left, right)
                        for _head, args in self.graph.patterns[schema_id]
                        for tag, _value in args
                    )
                    # Prefer already useful chunks and discriminative constants,
                    # without allowing one high-degree join value to monopolize
                    # the whole work queue.
                    priority = (
                        0 if left in preferred_schema_ids or right in preferred_schema_ids else 1,
                        self.graph.body_count[left] + self.graph.body_count[right],
                        -constant_count,
                        -max(self.graph.depth[left], self.graph.depth[right]),
                        -(self.graph.depth[left] + self.graph.depth[right]),
                        self.graph.canonical_hash[left] + self.graph.canonical_hash[right],
                    )
                    group.append((priority, left, right, left_binding, right_binding))
                    if len(proposed_keys) >= self.limits.max_queue_items:
                        generation_truncated = True
                        break
                if generation_truncated and len(proposed_keys) >= self.limits.max_queue_items:
                    break
            if group:
                group.sort(key=lambda item: item[0])
                proposal_groups.append((binding_degree, group))
            if generation_truncated and len(proposed_keys) >= self.limits.max_queue_items:
                break
        if generation_truncated:
            self._truncation("composition-generation-budget")

        # Fair first pass: every shared binding value may contribute its best
        # proposal. Remaining slots are filled globally by the same value/cost
        # priority. This avoids both attribute-value explosions and starvation.
        proposal_groups.sort(key=lambda item: (item[1][0][0][0], -item[0], item[1][0][0][1:]))
        proposals = [group[0] for _degree, group in proposal_groups]
        remaining = [
            (proposal[0], -degree, *proposal[1:])
            for degree, group in proposal_groups
            for proposal in group[1:]
        ]
        remaining.sort(key=lambda item: (item[0], item[1]))
        proposals.extend((item[0], *item[2:]) for item in remaining)
        if len(proposals) > proposal_budget:
            self._truncation("composition-proposal-budget")
            proposals = proposals[:proposal_budget]

        created_ids: set[int] = set()
        processed = 0
        binding_keys = {
            (schema_id, tuple(sorted(binding.items())))
            for schema_id, binding in workspace.bindings
        }
        for _priority, left, right, left_binding, right_binding in proposals:
            if len(created_ids) >= retention_budget:
                self._truncation("composition-retention-budget")
                break
            processed += 1
            self.metrics.compositions_proposed += 1
            self.metrics.work("TRY_COMPOSE")
            atoms, decomposition = self._merge_bound_patterns(
                left, left_binding, right, right_binding
            )
            if len(atoms) > self.limits.max_composition_body:
                self._truncation("composition-body-budget")
                continue
            schema_id, created = self.graph.add_schema(
                "Composite",
                atoms,
                provenance="endogenous:compose",
                decomposition=decomposition,
            )
            if created:
                created_ids.add(schema_id)
                self.metrics.compositions_retained += 1
            workspace.activation[schema_id] = max(workspace.activation.get(schema_id, 0.0), 0.2)
            bindings, was_truncated = self._verify(
                self.graph.patterns[schema_id], fact_index, fact_slot_index
            )
            if was_truncated:
                self._truncation("composite-verification-budget")
            new_binding_count = 0
            for binding in bindings:
                key = (schema_id, tuple(sorted(binding.items())))
                if key not in binding_keys:
                    binding_keys.add(key)
                    workspace.bindings.append(
                        Binding(schema_id, tuple(sorted(binding.items())), workspace.context, provenance="composition")
                    )
                    new_binding_count += 1
            self.graph.use_count[schema_id] += new_binding_count
            self.trace.append(
                {"event": "composition", "cycle": self.cycle, "context": workspace.context, "schema": self.graph.canonical_hash[schema_id], "created": created}
            )
        self.metrics.composition_time_s += time.perf_counter() - start
        return processed, created_ids

    def _merge_bound_patterns(
        self,
        left: int,
        left_binding: dict[int, int],
        right: int,
        right_binding: dict[int, int],
    ) -> tuple[list[SourceAtom], list[DecompositionOccurrence]]:
        bound_name: dict[int, str] = {}
        next_var = 0
        output: list[SourceAtom] = []
        occurrences: list[DecompositionOccurrence] = []
        for schema_id, binding in ((left, left_binding), (right, right_binding)):
            local_unbound: dict[int, str] = {}
            interface: dict[int, str] = {}
            for head_id, args in self.graph.patterns[schema_id]:
                converted: list[SourceArg] = []
                for tag, value in args:
                    if tag == "c":
                        converted.append(self.graph.terms.value(value))
                        continue
                    grounded = binding.get(value)
                    if grounded is not None:
                        if grounded not in bound_name:
                            bound_name[grounded] = f"?b{next_var}"
                            next_var += 1
                        source_variable = bound_name[grounded]
                    else:
                        if value not in local_unbound:
                            local_unbound[value] = f"?b{next_var}"
                            next_var += 1
                        source_variable = local_unbound[value]
                    interface[value] = source_variable
                    converted.append(source_variable)
                output.append((str(self.graph.terms.value(head_id)), tuple(converted)))
            occurrences.append((schema_id, interface))
        return output, occurrences

    def _compose_relational_closures(
        self,
        workspace: Workspace,
        fact_index: FactIndex,
        fact_slot_index: FactSlotIndex,
        *,
        entity_terms: set[int],
        proposal_budget: int,
        retention_budget: int,
    ) -> set[int]:
        """Complete generic binary relations with one discovered child per endpoint.

        This is a bounded hypergraph closure, not a named-predicate rule. A
        depth-zero relation binding with two typed entities is grouped with all
        other relation atoms over the same grounded pair, then attached to one
        non-relational composite descriptor for each endpoint. The resulting
        schema retains all child occurrences in its decomposition DAG.
        """
        relation_groups: dict[
            tuple[int, int], list[tuple[int, dict[int, int]]]
        ] = defaultdict(list)
        descriptors: dict[int, list[tuple[int, dict[int, int]]]] = defaultdict(list)
        for schema_id, binding in workspace.bindings:
            entities = sorted(set(binding.values()) & entity_terms)
            if graph_depth := self.graph.depth[schema_id]:
                if len(entities) == 1:
                    descriptors[entities[0]].append((schema_id, binding))
                continue
            if len(entities) == 2:
                relation_groups[(entities[0], entities[1])].append((schema_id, binding))

        proposals: list[
            tuple[
                tuple[int, int, str],
                tuple[tuple[int, dict[int, int]], ...],
            ]
        ] = []
        for endpoints, relations in sorted(relation_groups.items()):
            left_options = sorted(
                descriptors.get(endpoints[0], ()),
                key=lambda item: (
                    -self.graph.depth[item[0]],
                    -self.graph.body_count[item[0]],
                    self.graph.canonical_hash[item[0]],
                ),
            )[:2]
            right_options = sorted(
                descriptors.get(endpoints[1], ()),
                key=lambda item: (
                    -self.graph.depth[item[0]],
                    -self.graph.body_count[item[0]],
                    self.graph.canonical_hash[item[0]],
                ),
            )[:2]
            if not left_options or not right_options:
                continue
            relation_entries = tuple(
                sorted(relations, key=lambda item: self.graph.canonical_hash[item[0]])
            )
            for left in left_options:
                for right in right_options:
                    entries = relation_entries + (left, right)
                    priority = (
                        -max(self.graph.depth[left[0]], self.graph.depth[right[0]]),
                        -sum(self.graph.body_count[schema_id] for schema_id, _binding in entries),
                        "".join(self.graph.canonical_hash[schema_id] for schema_id, _binding in entries),
                    )
                    proposals.append((priority, entries))
        proposals.sort(key=lambda item: item[0])
        if len(proposals) > proposal_budget:
            self._truncation("relational-closure-budget")
            proposals = proposals[:proposal_budget]

        created_ids: set[int] = set()
        binding_keys = {
            (schema_id, tuple(sorted(binding.items())))
            for schema_id, binding in workspace.bindings
        }
        for _priority, entries in proposals:
            if len(created_ids) >= retention_budget:
                self._truncation("relational-closure-retention-budget")
                break
            self.metrics.compositions_proposed += 1
            self.metrics.work("TRY_RELATIONAL_CLOSURE")
            atoms, decomposition = self._merge_many_bound_patterns(entries)
            if len(atoms) > self.limits.max_composition_body:
                self._truncation("composition-body-budget")
                continue
            schema_id, created = self.graph.add_schema(
                "RelationalComposite",
                atoms,
                provenance="endogenous:relational-closure",
                decomposition=decomposition,
            )
            if created:
                created_ids.add(schema_id)
                self.metrics.compositions_retained += 1
            workspace.activation[schema_id] = max(workspace.activation.get(schema_id, 0.0), 0.3)
            bindings, was_truncated = self._verify(
                self.graph.patterns[schema_id], fact_index, fact_slot_index
            )
            if was_truncated:
                self._truncation("composite-verification-budget")
            for binding in bindings:
                key = (schema_id, tuple(sorted(binding.items())))
                if key not in binding_keys:
                    binding_keys.add(key)
                    workspace.bindings.append(
                        Binding(schema_id, tuple(sorted(binding.items())), workspace.context, provenance="composition")
                    )
                    self.graph.use_count[schema_id] += 1
        return created_ids

    def _merge_many_bound_patterns(
        self, entries: tuple[tuple[int, dict[int, int]], ...]
    ) -> tuple[list[SourceAtom], list[DecompositionOccurrence]]:
        bound_name: dict[int, str] = {}
        next_var = 0
        output: list[SourceAtom] = []
        occurrences: list[DecompositionOccurrence] = []
        for schema_id, binding in entries:
            local_unbound: dict[int, str] = {}
            interface: dict[int, str] = {}
            for head_id, args in self.graph.patterns[schema_id]:
                converted: list[SourceArg] = []
                for tag, value in args:
                    if tag == "c":
                        converted.append(self.graph.terms.value(value))
                        continue
                    grounded = binding.get(value)
                    if grounded is not None:
                        if grounded not in bound_name:
                            bound_name[grounded] = f"?b{next_var}"
                            next_var += 1
                        source_variable = bound_name[grounded]
                    else:
                        if value not in local_unbound:
                            local_unbound[value] = f"?b{next_var}"
                            next_var += 1
                        source_variable = local_unbound[value]
                    interface[value] = source_variable
                    converted.append(source_variable)
                output.append((str(self.graph.terms.value(head_id)), tuple(converted)))
            occurrences.append((schema_id, interface))
        return output, occurrences

    def _prune(self, workspace: Workspace) -> None:
        self.metrics.peak_workspace = max(self.metrics.peak_workspace, len(workspace.activation))
        if len(workspace.activation) <= self.limits.max_active_nodes:
            return
        ranked = sorted(
            workspace.activation,
            key=lambda schema_id: (-workspace.activation[schema_id], self.graph.canonical_hash[schema_id]),
        )
        keep = set(ranked[: self.limits.max_active_nodes])
        workspace.activation = {schema_id: workspace.activation[schema_id] for schema_id in sorted(keep)}
        workspace.bindings = [binding for binding in workspace.bindings if binding.schema_id in keep]
        self._truncation("active-node-budget")

    def learn_transition(
        self,
        before: PerceptionBatch,
        after: PerceptionBatch,
        action: str,
    ) -> int:
        start = time.perf_counter()
        self.metrics.work("SCORE_MAPPING")
        pairs = self._correspond_regions(before, after)
        if not pairs:
            raise ValueError("no bounded form correspondence found")
        # The benchmark has one unambiguous region. Ambiguity remains a bounded version space.
        before_region, after_region, form_term = pairs[0]
        before_relations = self._entity_relations(before.facts, before_region)
        after_relations = self._entity_relations(after.facts, after_region)

        atoms: list[SourceAtom] = [
            ("Domain", ("?s0",)),
            ("Codomain", ("?s1",)),
            ("Intervention", (action,)),
        ]
        relation_index = 0
        for head in sorted(set(before_relations) & set(after_relations), key=lambda item: str(self.graph.terms.value(item))):
            before_value = before_relations[head]
            after_value = after_relations[head]
            head_value = str(self.graph.terms.value(head))
            if before_value == after_value:
                variable = f"?r{relation_index}"
                atoms.extend(
                    [
                        ("Before", ("?s0", head_value, variable)),
                        ("After", ("?s1", head_value, variable)),
                        ("Preserve", (head_value,)),
                    ]
                )
            else:
                before_variable = f"?r{relation_index}a"
                after_variable = f"?r{relation_index}b"
                atoms.extend(
                    [
                        ("Before", ("?s0", head_value, before_variable)),
                        ("After", ("?s1", head_value, after_variable)),
                        ("Change", (head_value,)),
                    ]
                )
                left_value = self.graph.terms.value(before_value)
                right_value = self.graph.terms.value(after_value)
                if (
                    head_value in self.ordered_relations
                    and isinstance(left_value, (int, float))
                    and isinstance(right_value, (int, float))
                    and left_value < right_value
                ):
                    atoms.append(("Less", (before_variable, after_variable)))
            relation_index += 1
        schema_id, created = self.graph.add_schema(
            "TransitionCandidate", atoms, provenance="endogenous:map"
        )
        context = str(self.graph.terms.value(form_term))
        self.graph.add_evidence(
            schema_id, "support", 1, context, self.cycle, source="experience:transition"
        )
        self.trace.append(
            {"event": "mapping-evidence", "cycle": self.cycle, "schema": self.graph.canonical_hash[schema_id], "context": context, "created": created, "kind": "support"}
        )
        self.metrics.transition_learning_time_s += time.perf_counter() - start
        return schema_id

    def _correspond_regions(
        self, before: PerceptionBatch, after: PerceptionBatch
    ) -> list[tuple[int, int, int]]:
        form_head = self.graph.terms.intern_symbol("Form")
        before_forms = {args[1]: args[0] for head, args in before.facts if head == form_head and len(args) == 2}
        after_forms = {args[1]: args[0] for head, args in after.facts if head == form_head and len(args) == 2}
        common = sorted(set(before_forms) & set(after_forms))
        limit = min(
            self.limits.max_transition_correspondences,
            self.limits.max_analogy_candidates,
        )
        if len(common) > limit:
            common = common[:limit]
            self._truncation("transition-correspondence-budget")
        return [(before_forms[form], after_forms[form], form) for form in common]

    @staticmethod
    def _entity_relations(facts: tuple[GroundAtom, ...], entity: int) -> dict[int, int]:
        return {head: args[1] for head, args in facts if len(args) == 2 and args[0] == entity}

    def predict(self, schema_id: int, expected: GroundAtom, context: str) -> int:
        prediction_id = self._next_prediction
        self._next_prediction += 1
        pending = PendingPrediction(prediction_id, schema_id, expected, context)
        self._pending[prediction_id] = pending
        self.trace.append({"event": "prediction", "cycle": self.cycle, "prediction": prediction_id, "schema": self.graph.canonical_hash[schema_id], "context": context})
        return prediction_id

    def resolve_prediction(self, prediction_id: int, observed: PerceptionBatch) -> bool:
        pending = self._pending.pop(prediction_id)
        success = pending.expected in set(observed.facts)
        kind = "prediction-success" if success else "prediction-failure"
        self.graph.add_evidence(
            pending.schema_id, kind, 1, pending.context, self.cycle, source="environment"
        )
        if not success:
            self.graph.add_evidence(
                pending.schema_id,
                "contradiction",
                1,
                pending.context,
                self.cycle,
                source="environment",
            )
        self.metrics.work("CHECK_PREDICTION")
        self.trace.append({"event": "prediction-resolution", "cycle": self.cycle, "prediction": prediction_id, "schema": self.graph.canonical_hash[pending.schema_id], "context": pending.context, "success": success})
        return success

    def reusable_composite_candidates(self, minimum_uses: int = 2) -> list[int]:
        """Return active, genuinely decomposed schemas reused by distinct bindings.

        This is a one-frame structural-utility criterion, not a prediction or
        truth claim. Evidence over later contexts may strengthen or falsify it.
        """

        if self.workspace is None:
            return []
        return sorted(
            (
                schema_id
                for schema_id in self.workspace.activation
                if self.graph.decomposition_out_index.get(schema_id)
                and self.graph.use_count[schema_id] >= minimum_uses
                and self.graph.contradiction[schema_id] == 0
            ),
            key=lambda schema_id: (
                -self.graph.use_count[schema_id],
                self.graph.canonical_hash[schema_id],
            ),
        )

    def report(self) -> dict[str, Any]:
        workspace = self.workspace
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # Linux reports KiB; this project currently targets Linux/Kaggle.
        return {
            "total_schemas": self.graph.schema_count,
            "active_schemas": 0 if workspace is None else len(workspace.activation),
            "active_edges": 0 if workspace is None else len(workspace.active_edge_ids),
            **asdict(self.metrics),
            "term_bytes_estimate": self.graph.terms.estimate_bytes(),
            "graph_bytes_estimate": self.graph.estimate_bytes(),
            "process_peak_rss_bytes": int(rss * 1024),
            "candidate_schemas": self.graph.schema_state.count(SCHEMA_CANDIDATE),
            "established_schemas": self.graph.schema_state.count(SCHEMA_ESTABLISHED),
            "promoted_schemas": self.graph.schema_state.count(SCHEMA_PROMOTED),
            "reusable_composite_candidates": len(self.reusable_composite_candidates()),
            "canonical_active_ids": [] if workspace is None else [self.graph.canonical_hash[item] for item in sorted(workspace.activation)],
        }
