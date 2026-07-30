"""Bounded synthesis of content-free connector traversal programs.

The synthesizer consumes an already perceived, ordered container description.
It assigns a finite multiset of payloads and connectors to variable slots and
checks the assignment by executing depth-first container semantics.  Cyclic
graphs are safe because execution is bounded by the finite reference horizon
and explicit structural limits.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Iterator

type Color = int


@dataclass(frozen=True, slots=True)
class FixedColorSlot:
    """A container slot whose emitted color is already visible."""

    color: Color


@dataclass(frozen=True, slots=True)
class VariableSlot:
    """A slot whose item and grounded connector-placement cost are unknown."""

    connector_cost: int = 0


type SlotSpec = FixedColorSlot | VariableSlot


@dataclass(frozen=True, slots=True)
class ContainerSpec:
    """One visually ordered container and its visually ordered slots."""

    container_id: str
    slots: tuple[SlotSpec, ...]


@dataclass(frozen=True, slots=True)
class Connector:
    """One inventory item that invokes its target container."""

    target: str


@dataclass(frozen=True, slots=True)
class Payload:
    """One inventory item that emits a color."""

    color: Color


type AssignedItem = Connector | Payload
type ResolvedSlot = FixedColorSlot | Connector | Payload


@dataclass(frozen=True, slots=True)
class ConnectorSynthesisProblem:
    """Abstract input to connector-graph program synthesis."""

    reference: tuple[Color, ...]
    containers: tuple[ContainerSpec, ...]
    root: str
    payloads: tuple[Color, ...]
    connectors: tuple[Connector, ...]


@dataclass(frozen=True, slots=True)
class ConnectorSynthesisBounds:
    """Strict deterministic structure, enumeration, and execution limits."""

    max_reference_length: int = 32
    max_containers: int = 8
    max_slots_per_container: int = 8
    max_variable_slots: int = 12
    max_payload_inventory: int = 16
    max_assignments: int = 100_000
    max_traversal_steps: int = 256
    max_call_depth: int = 40


class ConnectorSynthesisStatus(str, Enum):
    """Complete status of a bounded synthesis request."""

    UNIQUE = "unique"
    NO_SOLUTION = "no-solution"
    AMBIGUOUS = "ambiguous"
    INVALID = "invalid"
    BOUNDS_EXCEEDED = "bounds-exceeded"


@dataclass(frozen=True, slots=True)
class VariableBinding:
    """One synthesized semantic item at one ordered variable slot."""

    container_id: str
    slot_index: int
    item: AssignedItem


@dataclass(frozen=True, slots=True)
class ResolvedContainer:
    """One container after every variable slot has an assignment."""

    container_id: str
    slots: tuple[ResolvedSlot, ...]


@dataclass(frozen=True, slots=True)
class ConnectorUse:
    """One executed connector invocation in the finite traversal."""

    container_id: str
    slot_index: int
    target: str


@dataclass(frozen=True, slots=True)
class ConnectorGraphProgram:
    """The selected grounded assignment and its finite semantic execution."""

    root: str
    reference: tuple[Color, ...]
    containers: tuple[ResolvedContainer, ...]
    bindings: tuple[VariableBinding, ...]
    unused_payloads: tuple[Color, ...]
    emissions: tuple[Color, ...]
    connector_trace: tuple[ConnectorUse, ...]
    visited_containers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConnectorSynthesisResult:
    """A synthesis result that never hides ambiguity or exhausted bounds."""

    status: ConnectorSynthesisStatus
    plan: ConnectorGraphProgram | None
    explored_assignments: int
    semantic_solutions: int
    diagnostic: str


@dataclass(frozen=True, slots=True)
class _VariablePosition:
    container_id: str
    slot_index: int


@dataclass(frozen=True, slots=True)
class _Traversal:
    matched: bool
    bounded: bool
    emissions: tuple[Color, ...]
    connector_trace: tuple[ConnectorUse, ...]
    visited_containers: tuple[str, ...]


def synthesize_connector_program(
    problem: ConnectorSynthesisProblem,
    *,
    bounds: ConnectorSynthesisBounds = ConnectorSynthesisBounds(),
) -> ConnectorSynthesisResult:
    """Return only one minimum-cost, visually grounded complete assignment."""

    validation = _validate(problem, bounds)
    if validation is not None:
        return validation
    positions = _variable_positions(problem.containers)
    payload_count = len(positions) - len(problem.connectors)
    payload_subsets = tuple(_canonical_payload_subsets(problem.payloads, payload_count))
    assignment_count = sum(
        _multiset_permutation_count((*payload_subset, *problem.connectors))
        for payload_subset in payload_subsets
    )
    if assignment_count > bounds.max_assignments:
        return ConnectorSynthesisResult(
            status=ConnectorSynthesisStatus.BOUNDS_EXCEEDED,
            plan=None,
            explored_assignments=0,
            semantic_solutions=0,
            diagnostic="assignment-enumeration-bound",
        )

    explored = 0
    bounded_traversal = False
    solution: ConnectorGraphProgram | None = None
    best_connector_cost: int | None = None
    best_solution_count = 0
    semantic_solutions = 0
    for payload_subset in payload_subsets:
        inventory: tuple[AssignedItem, ...] = (
            *payload_subset,
            *problem.connectors,
        )
        for assignment in _canonical_assignments(inventory, len(positions)):
            explored += 1
            bindings = tuple(
                VariableBinding(
                    container_id=position.container_id,
                    slot_index=position.slot_index,
                    item=item,
                )
                for position, item in zip(positions, assignment)
            )
            resolved = _resolve_containers(problem.containers, bindings)
            traversal = _execute(
                problem,
                resolved,
                bindings,
                bounds=bounds,
            )
            if traversal.bounded:
                bounded_traversal = True
                continue
            if not traversal.matched:
                continue
            semantic_solutions += 1
            candidate = ConnectorGraphProgram(
                root=problem.root,
                reference=problem.reference,
                containers=resolved,
                bindings=bindings,
                unused_payloads=_unused_payloads(problem.payloads, bindings),
                emissions=traversal.emissions,
                connector_trace=traversal.connector_trace,
                visited_containers=traversal.visited_containers,
            )
            connector_cost = _connector_assignment_cost(
                problem.containers,
                bindings,
            )
            if (
                best_connector_cost is None
                or connector_cost < best_connector_cost
            ):
                solution = candidate
                best_connector_cost = connector_cost
                best_solution_count = 1
                continue
            if connector_cost == best_connector_cost:
                best_solution_count += 1

    if bounded_traversal:
        return ConnectorSynthesisResult(
            status=ConnectorSynthesisStatus.BOUNDS_EXCEEDED,
            plan=None,
            explored_assignments=explored,
            semantic_solutions=semantic_solutions,
            diagnostic="traversal-bound-prevents-uniqueness",
        )
    if best_solution_count > 1:
        return ConnectorSynthesisResult(
            status=ConnectorSynthesisStatus.AMBIGUOUS,
            plan=None,
            explored_assignments=explored,
            semantic_solutions=semantic_solutions,
            diagnostic="multiple-minimum-cost-semantic-assignments",
        )
    if solution is None:
        return ConnectorSynthesisResult(
            status=ConnectorSynthesisStatus.NO_SOLUTION,
            plan=None,
            explored_assignments=explored,
            semantic_solutions=0,
            diagnostic="no-semantic-assignment",
        )
    return ConnectorSynthesisResult(
        status=ConnectorSynthesisStatus.UNIQUE,
        plan=solution,
        explored_assignments=explored,
        semantic_solutions=semantic_solutions,
        diagnostic=(
            "unique-minimum-cost-semantic-assignment"
            if semantic_solutions > 1
            else "unique-semantic-assignment"
        ),
    )


def _validate(
    problem: ConnectorSynthesisProblem,
    bounds: ConnectorSynthesisBounds,
) -> ConnectorSynthesisResult | None:
    if not problem.reference:
        return _invalid("empty-reference")
    if not problem.containers:
        return _invalid("empty-container-set")
    identifiers = tuple(item.container_id for item in problem.containers)
    if any(not identifier for identifier in identifiers) or len(
        set(identifiers)
    ) != len(identifiers):
        return _invalid("invalid-container-identifiers")
    if problem.root not in set(identifiers):
        return _invalid("root-not-observed")
    if any(
        not item.slots
        or any(
            not isinstance(slot, (FixedColorSlot, VariableSlot)) for slot in item.slots
        )
        for item in problem.containers
    ):
        return _invalid("invalid-container-slots")
    if any(
        isinstance(slot, VariableSlot)
        and (
            isinstance(slot.connector_cost, bool)
            or not isinstance(slot.connector_cost, int)
            or slot.connector_cost < 0
        )
        for item in problem.containers
        for slot in item.slots
    ):
        return _invalid("invalid-connector-cost")
    known = set(identifiers)
    if any(item.target not in known for item in problem.connectors):
        return _invalid("connector-target-not-observed")
    variable_count = len(_variable_positions(problem.containers))
    if not (
        len(problem.connectors)
        <= variable_count
        <= len(problem.payloads) + len(problem.connectors)
    ):
        return _invalid("inventory-slot-cardinality-mismatch")
    if (
        len(problem.reference) > bounds.max_reference_length
        or len(problem.containers) > bounds.max_containers
        or any(
            len(item.slots) > bounds.max_slots_per_container
            for item in problem.containers
        )
        or variable_count > bounds.max_variable_slots
        or len(problem.payloads) > bounds.max_payload_inventory
    ):
        return ConnectorSynthesisResult(
            status=ConnectorSynthesisStatus.BOUNDS_EXCEEDED,
            plan=None,
            explored_assignments=0,
            semantic_solutions=0,
            diagnostic="structural-bound",
        )
    if (
        bounds.max_reference_length < 1
        or bounds.max_containers < 1
        or bounds.max_slots_per_container < 1
        or bounds.max_variable_slots < 0
        or bounds.max_payload_inventory < 0
        or bounds.max_assignments < 1
        or bounds.max_traversal_steps < 1
        or bounds.max_call_depth < 1
    ):
        return _invalid("invalid-bounds")
    return None


def _invalid(diagnostic: str) -> ConnectorSynthesisResult:
    return ConnectorSynthesisResult(
        status=ConnectorSynthesisStatus.INVALID,
        plan=None,
        explored_assignments=0,
        semantic_solutions=0,
        diagnostic=diagnostic,
    )


def _variable_positions(
    containers: tuple[ContainerSpec, ...],
) -> tuple[_VariablePosition, ...]:
    return tuple(
        _VariablePosition(item.container_id, index)
        for item in containers
        for index, slot in enumerate(item.slots)
        if isinstance(slot, VariableSlot)
    )


def _item_key(item: AssignedItem) -> tuple[int, int | str]:
    if isinstance(item, Payload):
        return 0, item.color
    return 1, item.target


def _multiset_permutation_count(inventory: tuple[AssignedItem, ...]) -> int:
    counts = Counter(inventory)
    output = math.factorial(len(inventory))
    for count in counts.values():
        output //= math.factorial(count)
    return output


def _canonical_payload_subsets(
    payloads: tuple[Color, ...],
    length: int,
) -> Iterator[tuple[Payload, ...]]:
    counts = Counter(Payload(color) for color in payloads)
    ordered = tuple(sorted(counts, key=_item_key))
    selected: list[Payload] = []

    def choose(index: int, remaining: int) -> Iterator[tuple[Payload, ...]]:
        if index == len(ordered):
            if remaining == 0:
                yield tuple(selected)
            return
        item = ordered[index]
        for amount in range(min(counts[item], remaining) + 1):
            selected.extend(item for _index in range(amount))
            yield from choose(index + 1, remaining - amount)
            if amount:
                del selected[-amount:]

    yield from choose(0, length)


def _canonical_assignments(
    inventory: tuple[AssignedItem, ...],
    length: int,
) -> Iterator[tuple[AssignedItem, ...]]:
    counts = Counter(inventory)
    ordered = tuple(sorted(counts, key=_item_key))
    prefix: list[AssignedItem] = []

    def expand() -> Iterator[tuple[AssignedItem, ...]]:
        if len(prefix) == length:
            yield tuple(prefix)
            return
        for item in ordered:
            if counts[item] == 0:
                continue
            counts[item] -= 1
            prefix.append(item)
            yield from expand()
            prefix.pop()
            counts[item] += 1

    yield from expand()


def _unused_payloads(
    payloads: tuple[Color, ...],
    bindings: tuple[VariableBinding, ...],
) -> tuple[Color, ...]:
    unused = Counter(payloads)
    for binding in bindings:
        if isinstance(binding.item, Payload):
            unused[binding.item.color] -= 1
    return tuple(color for color in sorted(unused) for _index in range(unused[color]))


def _connector_assignment_cost(
    containers: tuple[ContainerSpec, ...],
    bindings: tuple[VariableBinding, ...],
) -> int:
    costs = {
        (container.container_id, index): slot.connector_cost
        for container in containers
        for index, slot in enumerate(container.slots)
        if isinstance(slot, VariableSlot)
    }
    return sum(
        costs[(binding.container_id, binding.slot_index)]
        for binding in bindings
        if isinstance(binding.item, Connector)
    )


def _resolve_containers(
    containers: tuple[ContainerSpec, ...],
    bindings: tuple[VariableBinding, ...],
) -> tuple[ResolvedContainer, ...]:
    assigned = {(item.container_id, item.slot_index): item.item for item in bindings}
    return tuple(
        ResolvedContainer(
            container_id=container.container_id,
            slots=tuple(
                slot
                if isinstance(slot, FixedColorSlot)
                else assigned[(container.container_id, index)]
                for index, slot in enumerate(container.slots)
            ),
        )
        for container in containers
    )


def _execute(
    problem: ConnectorSynthesisProblem,
    containers: tuple[ResolvedContainer, ...],
    bindings: tuple[VariableBinding, ...],
    *,
    bounds: ConnectorSynthesisBounds,
) -> _Traversal:
    by_id = {item.container_id: item for item in containers}
    connector_positions = {
        (item.container_id, item.slot_index)
        for item in bindings
        if isinstance(item.item, Connector)
    }
    used_connector_positions: set[tuple[str, int]] = set()
    visited = {problem.root}
    emissions: list[Color] = []
    connector_trace: list[ConnectorUse] = []
    stack: list[tuple[str, int, int]] = [(problem.root, 0, 0)]
    productive_cycle_observed = False
    steps = 0
    while True:
        reference_complete = len(emissions) == len(problem.reference)
        if reference_complete and (productive_cycle_observed or not stack):
            matched = (
                used_connector_positions == connector_positions
                and visited == set(by_id)
            )
            return _Traversal(
                matched=matched,
                bounded=False,
                emissions=tuple(emissions),
                connector_trace=tuple(connector_trace),
                visited_containers=tuple(
                    item.container_id
                    for item in containers
                    if item.container_id in visited
                ),
            )
        if not stack:
            return _failed_traversal(emissions, connector_trace, visited, containers)
        if steps >= bounds.max_traversal_steps:
            return _bounded_traversal(emissions, connector_trace, visited, containers)
        container_id, slot_index, entry_emissions = stack[-1]
        container = by_id[container_id]
        if slot_index >= len(container.slots):
            stack.pop()
            continue
        stack[-1] = (container_id, slot_index + 1, entry_emissions)
        slot = container.slots[slot_index]
        steps += 1
        if isinstance(slot, Connector):
            location = (container_id, slot_index)
            used_connector_positions.add(location)
            connector_trace.append(
                ConnectorUse(
                    container_id=container_id,
                    slot_index=slot_index,
                    target=slot.target,
                )
            )
            if any(
                active_container == slot.target
                and active_entry_emissions == len(emissions)
                for (
                    active_container,
                    _active_slot,
                    active_entry_emissions,
                ) in stack
            ):
                return _failed_traversal(
                    emissions,
                    connector_trace,
                    visited,
                    containers,
                )
            active_target = next(
                (
                    active_entry_emissions
                    for (
                        active_container,
                        _active_slot,
                        active_entry_emissions,
                    ) in stack
                    if active_container == slot.target
                ),
                None,
            )
            if active_target is not None:
                if reference_complete:
                    return _failed_traversal(
                        emissions,
                        connector_trace,
                        visited,
                        containers,
                    )
                productive_cycle_observed = True
            if len(stack) >= bounds.max_call_depth:
                return _bounded_traversal(
                    emissions,
                    connector_trace,
                    visited,
                    containers,
                )
            visited.add(slot.target)
            stack.append((slot.target, 0, len(emissions)))
            continue
        color = slot.color
        if reference_complete:
            return _failed_traversal(
                emissions,
                connector_trace,
                visited,
                containers,
            )
        if color != problem.reference[len(emissions)]:
            return _failed_traversal(emissions, connector_trace, visited, containers)
        emissions.append(color)


def _failed_traversal(
    emissions: list[Color],
    connector_trace: list[ConnectorUse],
    visited: set[str],
    containers: tuple[ResolvedContainer, ...],
) -> _Traversal:
    return _Traversal(
        matched=False,
        bounded=False,
        emissions=tuple(emissions),
        connector_trace=tuple(connector_trace),
        visited_containers=tuple(
            item.container_id for item in containers if item.container_id in visited
        ),
    )


def _bounded_traversal(
    emissions: list[Color],
    connector_trace: list[ConnectorUse],
    visited: set[str],
    containers: tuple[ResolvedContainer, ...],
) -> _Traversal:
    return _Traversal(
        matched=False,
        bounded=True,
        emissions=tuple(emissions),
        connector_trace=tuple(connector_trace),
        visited_containers=tuple(
            item.container_id for item in containers if item.container_id in visited
        ),
    )
