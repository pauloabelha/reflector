"""Content-free cyclic lattice effect induction and bounded planning.

The structures in this module deliberately operate on already-grounded lattice
roles.  Perception decides which visible items are lattice nodes and which
nodes are legal action anchors; this module only learns a relative action
effect and inverts it against symbolic equality or inequality constraints.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Sequence

LatticePoint = tuple[int, int]


@dataclass(frozen=True, slots=True)
class ColorCycle:
    """A finite, ordered domain whose actions advance values cyclically."""

    values: tuple[int, ...]

    def __post_init__(self) -> None:
        if len(self.values) < 2:
            raise ValueError("a color cycle requires at least two values")
        if len(set(self.values)) != len(self.values):
            raise ValueError("color cycle values must be unique")

    @classmethod
    def create(cls, values: Sequence[int]) -> ColorCycle:
        return cls(tuple(values))

    def index(self, value: int) -> int:
        try:
            return self.values.index(value)
        except ValueError as error:
            raise ValueError(f"value {value} is outside the color cycle") from error

    def advance(self, value: int, steps: int = 1) -> int:
        return self.values[(self.index(value) + steps) % len(self.values)]

    def delta(self, before: int, after: int) -> int:
        return (self.index(after) - self.index(before)) % len(self.values)

    def to_dict(self) -> dict[str, object]:
        return {"values": list(self.values)}


@dataclass(frozen=True, slots=True)
class LatticeState:
    """Canonical color values keyed by integer lattice coordinates."""

    values: tuple[tuple[LatticePoint, int], ...]

    def __post_init__(self) -> None:
        points = tuple(point for point, _value in self.values)
        if not points:
            raise ValueError("a lattice state cannot be empty")
        if len(set(points)) != len(points):
            raise ValueError("lattice points must be unique")
        if self.values != tuple(sorted(self.values)):
            raise ValueError("lattice state values must be canonically sorted")

    @classmethod
    def create(cls, values: Mapping[LatticePoint, int]) -> LatticeState:
        return cls(
            tuple(
                sorted(
                    (
                        (int(point[0]), int(point[1])),
                        int(value),
                    )
                    for point, value in values.items()
                )
            )
        )

    @property
    def points(self) -> tuple[LatticePoint, ...]:
        return tuple(point for point, _value in self.values)

    def value_at(self, point: LatticePoint) -> int:
        for candidate, value in self.values:
            if candidate == point:
                return value
        raise KeyError(point)

    def as_dict(self) -> dict[LatticePoint, int]:
        return dict(self.values)

    def to_dict(self) -> dict[str, object]:
        return {
            "values": [
                {"point": list(point), "value": value}
                for point, value in self.values
            ]
        }


@dataclass(frozen=True, slots=True)
class ClickTransition:
    """One grounded click and its before/after lattice observations."""

    anchor: LatticePoint
    before: LatticeState
    after: LatticeState

    def __post_init__(self) -> None:
        if self.before.points != self.after.points:
            raise ValueError("effect induction requires stable lattice membership")
        if self.anchor not in self.before.points:
            raise ValueError("the click anchor must be a grounded lattice point")


@dataclass(frozen=True, slots=True)
class OffsetEffect:
    """A confirmed cyclic change at an offset relative to a click anchor."""

    offset: LatticePoint
    delta: int
    confirmations: int
    opportunities: int

    def __post_init__(self) -> None:
        if self.delta <= 0:
            raise ValueError("an offset effect must have a non-zero cyclic delta")
        if self.confirmations <= 0:
            raise ValueError("an offset effect requires positive confirmation")
        if self.opportunities < self.confirmations:
            raise ValueError("effect opportunities cannot trail confirmations")

    def to_dict(self) -> dict[str, object]:
        return {
            "offset": list(self.offset),
            "delta": self.delta,
            "confirmations": self.confirmations,
            "opportunities": self.opportunities,
        }


@dataclass(frozen=True, slots=True)
class ClickEffectModel:
    """A translation-invariant set of effects learned from grounded clicks."""

    cycle: ColorCycle
    effects: tuple[OffsetEffect, ...]
    transition_count: int

    def __post_init__(self) -> None:
        if not self.effects:
            raise ValueError("a click effect model requires at least one effect")
        offsets = tuple(effect.offset for effect in self.effects)
        if len(set(offsets)) != len(offsets):
            raise ValueError("click effect offsets must be unique")
        if self.effects != tuple(sorted(self.effects, key=lambda item: item.offset)):
            raise ValueError("click effects must be canonically sorted")
        if self.transition_count <= 0:
            raise ValueError("effect evidence count must be positive")
        domain_size = len(self.cycle.values)
        if any(effect.delta >= domain_size for effect in self.effects):
            raise ValueError("effect delta must be inside the cyclic domain")

    def affected(
        self,
        anchor: LatticePoint,
        available_points: Sequence[LatticePoint],
    ) -> tuple[tuple[LatticePoint, int], ...]:
        represented = set(available_points)
        grounded = []
        for effect in self.effects:
            target = (
                anchor[0] + effect.offset[0],
                anchor[1] + effect.offset[1],
            )
            if target in represented:
                grounded.append((target, effect.delta))
        return tuple(grounded)

    def apply(
        self,
        state: LatticeState,
        anchor: LatticePoint,
        *,
        times: int = 1,
    ) -> LatticeState:
        if times < 0:
            raise ValueError("click repetitions cannot be negative")
        values = state.as_dict()
        for target, delta in self.affected(anchor, state.points):
            values[target] = self.cycle.advance(values[target], delta * times)
        return LatticeState.create(values)

    def to_dict(self) -> dict[str, object]:
        return {
            "cycle": self.cycle.to_dict(),
            "effects": [effect.to_dict() for effect in self.effects],
            "transition_count": self.transition_count,
        }


def learn_click_effect_model(
    cycle: ColorCycle,
    transitions: Sequence[ClickTransition],
    *,
    min_transitions: int = 2,
    min_confirmations: int = 1,
) -> ClickEffectModel | None:
    """Induce one strict relative effect model from counterfactual changes.

    Boundary observations are supported: an offset is only an opportunity when
    the corresponding target exists in that transition.  Any observed conflict
    or cyclic change not explained by the resulting model rejects promotion.
    """

    if min_transitions <= 0:
        raise ValueError("minimum transition evidence must be positive")
    if min_confirmations <= 0:
        raise ValueError("minimum effect confirmation must be positive")
    if len(transitions) < min_transitions:
        return None

    changed_deltas: dict[LatticePoint, set[int]] = {}
    for transition in transitions:
        before = transition.before.as_dict()
        after = transition.after.as_dict()
        for point in transition.before.points:
            delta = cycle.delta(before[point], after[point])
            if delta == 0:
                continue
            offset = (
                point[0] - transition.anchor[0],
                point[1] - transition.anchor[1],
            )
            changed_deltas.setdefault(offset, set()).add(delta)

    if not changed_deltas:
        return None

    effects = []
    for offset in sorted(changed_deltas):
        deltas = changed_deltas[offset]
        if len(deltas) != 1:
            return None
        delta = next(iter(deltas))
        confirmations = 0
        opportunities = 0
        for transition in transitions:
            target = (
                transition.anchor[0] + offset[0],
                transition.anchor[1] + offset[1],
            )
            if target not in transition.before.points:
                continue
            opportunities += 1
            observed = cycle.delta(
                transition.before.value_at(target),
                transition.after.value_at(target),
            )
            if observed == delta:
                confirmations += 1
            else:
                return None
        if confirmations < min_confirmations:
            continue
        effects.append(
            OffsetEffect(
                offset=offset,
                delta=delta,
                confirmations=confirmations,
                opportunities=opportunities,
            )
        )

    if not effects:
        return None
    promoted = {effect.offset: effect.delta for effect in effects}
    for transition in transitions:
        for point in transition.before.points:
            observed = cycle.delta(
                transition.before.value_at(point),
                transition.after.value_at(point),
            )
            if observed == 0:
                continue
            offset = (
                point[0] - transition.anchor[0],
                point[1] - transition.anchor[1],
            )
            if promoted.get(offset) != observed:
                return None
    return ClickEffectModel(
        cycle=cycle,
        effects=tuple(effects),
        transition_count=len(transitions),
    )


class Relation(str, Enum):
    EQUAL = "equal"
    NOT_EQUAL = "not-equal"


@dataclass(frozen=True, slots=True)
class RelationConstraint:
    """Equality or inequality between a lattice node and a node or color."""

    left: LatticePoint
    relation: Relation
    right_point: LatticePoint | None = None
    right_color: int | None = None

    def __post_init__(self) -> None:
        if (self.right_point is None) == (self.right_color is None):
            raise ValueError(
                "a relation constraint requires exactly one right-hand term"
            )

    @classmethod
    def equal_color(
        cls,
        point: LatticePoint,
        color: int,
    ) -> RelationConstraint:
        return cls(point, Relation.EQUAL, right_color=color)

    @classmethod
    def different_color(
        cls,
        point: LatticePoint,
        color: int,
    ) -> RelationConstraint:
        return cls(point, Relation.NOT_EQUAL, right_color=color)

    @classmethod
    def equal_points(
        cls,
        left: LatticePoint,
        right: LatticePoint,
    ) -> RelationConstraint:
        return cls(left, Relation.EQUAL, right_point=right)

    @classmethod
    def different_points(
        cls,
        left: LatticePoint,
        right: LatticePoint,
    ) -> RelationConstraint:
        return cls(left, Relation.NOT_EQUAL, right_point=right)

    @property
    def points(self) -> tuple[LatticePoint, ...]:
        if self.right_point is None:
            return (self.left,)
        return (self.left, self.right_point)

    def holds(self, state: LatticeState) -> bool:
        left = state.value_at(self.left)
        right = (
            state.value_at(self.right_point)
            if self.right_point is not None
            else self.right_color
        )
        satisfied = left == right
        return satisfied if self.relation is Relation.EQUAL else not satisfied

    def to_dict(self) -> dict[str, object]:
        return {
            "left": list(self.left),
            "relation": self.relation.value,
            "right_point": (
                list(self.right_point) if self.right_point is not None else None
            ),
            "right_color": self.right_color,
        }


class SolveStatus(str, Enum):
    SOLVED = "solved"
    NO_PLAN_WITHIN_ACTION_BOUND = "no-plan-within-action-bound"
    SEARCH_BOUND_EXHAUSTED = "search-bound-exhausted"


@dataclass(frozen=True, slots=True)
class ClickPlan:
    """A deterministic click program and its predicted final lattice state."""

    actions: tuple[LatticePoint, ...]
    click_counts: tuple[tuple[LatticePoint, int], ...]
    final_state: LatticeState
    search_nodes: int
    minimal_within_model: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "actions": [list(point) for point in self.actions],
            "click_counts": [
                {"point": list(point), "count": count}
                for point, count in self.click_counts
            ],
            "final_state": self.final_state.to_dict(),
            "search_nodes": self.search_nodes,
            "minimal_within_model": self.minimal_within_model,
        }


@dataclass(frozen=True, slots=True)
class ClickSolveResult:
    status: SolveStatus
    plan: ClickPlan | None
    search_nodes: int
    max_clicks: int


@dataclass(frozen=True, slots=True)
class _CompiledConstraint:
    relation: Relation
    base: int
    coefficients: tuple[int, ...]


def solve_click_csp(
    current: LatticeState,
    model: ClickEffectModel,
    constraints: Sequence[RelationConstraint],
    *,
    anchors: Sequence[LatticePoint] | None = None,
    max_clicks: int = 32,
    max_search_nodes: int = 100_000,
) -> ClickSolveResult:
    """Invert a cyclic relative effect model under a deterministic bound.

    Each anchor is assigned a click count in ``0..domain_size - 1`` because a
    full domain cycle is observationally redundant.  Iterative action bounds
    make the first returned plan minimal under the learned commutative model.
    """

    if max_clicks < 0:
        raise ValueError("maximum clicks cannot be negative")
    if max_search_nodes <= 0:
        raise ValueError("maximum search nodes must be positive")
    if not constraints:
        plan = ClickPlan(
            actions=(),
            click_counts=(),
            final_state=current,
            search_nodes=0,
            minimal_within_model=True,
        )
        return ClickSolveResult(SolveStatus.SOLVED, plan, 0, max_clicks)

    represented = set(current.points)
    for _point, value in current.values:
        model.cycle.index(value)
    for constraint in constraints:
        if any(point not in represented for point in constraint.points):
            raise ValueError("constraint point is absent from the lattice")
        if constraint.right_color is not None:
            model.cycle.index(constraint.right_color)

    requested_anchors = current.points if anchors is None else tuple(anchors)
    if len(set(requested_anchors)) != len(requested_anchors):
        raise ValueError("action anchors must be unique")
    if any(anchor not in represented for anchor in requested_anchors):
        raise ValueError("action anchors must be grounded lattice points")
    requested_anchors = tuple(sorted(requested_anchors))

    involved = {
        point for constraint in constraints for point in constraint.points
    }
    contributions = {
        anchor: dict(model.affected(anchor, current.points))
        for anchor in requested_anchors
    }
    active_anchors = tuple(
        anchor
        for anchor in requested_anchors
        if set(contributions[anchor]) & involved
    )
    modulus = len(model.cycle.values)

    compiled = []
    for constraint in constraints:
        left_index = model.cycle.index(current.value_at(constraint.left))
        if constraint.right_point is not None:
            right_index = model.cycle.index(
                current.value_at(constraint.right_point)
            )
        else:
            assert constraint.right_color is not None
            right_index = model.cycle.index(constraint.right_color)
        coefficients = []
        for anchor in active_anchors:
            effect = contributions[anchor]
            coefficient = effect.get(constraint.left, 0)
            if constraint.right_point is not None:
                coefficient -= effect.get(constraint.right_point, 0)
            coefficients.append(coefficient % modulus)
        compiled.append(
            _CompiledConstraint(
                relation=constraint.relation,
                base=(left_index - right_index) % modulus,
                coefficients=tuple(coefficients),
            )
        )

    if not active_anchors:
        if all(constraint.holds(current) for constraint in constraints):
            plan = ClickPlan(
                actions=(),
                click_counts=(),
                final_state=current,
                search_nodes=0,
                minimal_within_model=True,
            )
            return ClickSolveResult(SolveStatus.SOLVED, plan, 0, max_clicks)
        return ClickSolveResult(
            SolveStatus.NO_PLAN_WITHIN_ACTION_BOUND,
            None,
            0,
            max_clicks,
        )

    assignments = [-1] * len(active_anchors)
    partial = [constraint.base for constraint in compiled]
    search_nodes = 0
    search_exhausted = False

    def reachable(
        constraint_index: int,
        remaining_clicks: int,
    ) -> bool:
        constraint = compiled[constraint_index]
        residues: dict[int, int] = {partial[constraint_index]: 0}
        for action_index, coefficient in enumerate(constraint.coefficients):
            if assignments[action_index] >= 0 or coefficient == 0:
                continue
            updated = dict(residues)
            for residue, cost in residues.items():
                for count in range(1, modulus):
                    next_cost = cost + count
                    if next_cost > remaining_clicks:
                        continue
                    next_residue = (residue + coefficient * count) % modulus
                    previous = updated.get(next_residue)
                    if previous is None or next_cost < previous:
                        updated[next_residue] = next_cost
            residues = updated
        if constraint.relation is Relation.EQUAL:
            return 0 in residues
        return any(residue != 0 for residue in residues)

    def choose_action() -> int | None:
        unassigned = {index for index, value in enumerate(assignments) if value < 0}
        if not unassigned:
            return None
        candidates = []
        for constraint_index, constraint in enumerate(compiled):
            relevant = tuple(
                index
                for index in unassigned
                if constraint.coefficients[index] != 0
            )
            if not relevant:
                continue
            for index in relevant:
                degree = sum(
                    other.coefficients[index] != 0 for other in compiled
                )
                candidates.append(
                    (
                        len(relevant),
                        -degree,
                        active_anchors[index],
                        constraint_index,
                        index,
                    )
                )
        if not candidates:
            return min(unassigned, key=lambda index: active_anchors[index])
        return min(candidates)[-1]

    def search(action_bound: int, used_clicks: int) -> tuple[int, ...] | None:
        nonlocal search_nodes, search_exhausted
        search_nodes += 1
        if search_nodes > max_search_nodes:
            search_exhausted = True
            return None
        remaining = action_bound - used_clicks
        if remaining < 0:
            return None
        if any(
            not reachable(constraint_index, remaining)
            for constraint_index in range(len(compiled))
        ):
            return None
        action_index = choose_action()
        if action_index is None:
            if all(
                (
                    partial[index] == 0
                    if constraint.relation is Relation.EQUAL
                    else partial[index] != 0
                )
                for index, constraint in enumerate(compiled)
            ):
                return tuple(assignments)
            return None

        max_count = min(modulus - 1, remaining)
        for count in range(max_count + 1):
            assignments[action_index] = count
            for constraint_index, constraint in enumerate(compiled):
                partial[constraint_index] = (
                    partial[constraint_index]
                    + constraint.coefficients[action_index] * count
                ) % modulus
            result = search(action_bound, used_clicks + count)
            for constraint_index, constraint in enumerate(compiled):
                partial[constraint_index] = (
                    partial[constraint_index]
                    - constraint.coefficients[action_index] * count
                ) % modulus
            assignments[action_index] = -1
            if result is not None:
                return result
            if search_exhausted:
                return None
        return None

    solution = None
    for action_bound in range(max_clicks + 1):
        solution = search(action_bound, 0)
        if solution is not None or search_exhausted:
            break

    if solution is None:
        status = (
            SolveStatus.SEARCH_BOUND_EXHAUSTED
            if search_exhausted
            else SolveStatus.NO_PLAN_WITHIN_ACTION_BOUND
        )
        return ClickSolveResult(status, None, search_nodes, max_clicks)

    click_counts = tuple(
        (anchor, count)
        for anchor, count in zip(active_anchors, solution)
        if count > 0
    )
    actions = tuple(
        anchor for anchor, count in click_counts for _index in range(count)
    )
    final_state = current
    for anchor in actions:
        final_state = model.apply(final_state, anchor)
    if not all(constraint.holds(final_state) for constraint in constraints):
        raise AssertionError("compiled click solution failed concrete validation")
    plan = ClickPlan(
        actions=actions,
        click_counts=click_counts,
        final_state=final_state,
        search_nodes=search_nodes,
        minimal_within_model=True,
    )
    return ClickSolveResult(SolveStatus.SOLVED, plan, search_nodes, max_clicks)
