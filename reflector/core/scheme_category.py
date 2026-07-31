"""Finite relational objects, causal morphisms, and compressed symbolic options."""

from __future__ import annotations

import heapq
from dataclasses import dataclass

type Point = tuple[int, int]


@dataclass(frozen=True, order=True, slots=True)
class FocusedVariable:
    """One finite-domain state variable and its admissible goal values."""

    name: int
    value: Point
    goals: frozenset[Point]


@dataclass(frozen=True, slots=True)
class FocusedRewriteObject:
    """An abstract state object with exactly one causally focused variable."""

    variables: tuple[FocusedVariable, ...]
    focus: int

    def __post_init__(self) -> None:
        names = tuple(variable.name for variable in self.variables)
        if names != tuple(sorted(set(names))):
            raise ValueError("focused variables must be sorted and unique")
        if self.focus not in names:
            raise ValueError("focus must name one represented variable")
        if any(not variable.goals for variable in self.variables):
            raise ValueError("every focused variable requires a nonempty goal domain")

    @property
    def focused(self) -> FocusedVariable:
        return next(
            variable
            for variable in self.variables
            if variable.name == self.focus
        )

    @property
    def satisfied(self) -> bool:
        return all(variable.value in variable.goals for variable in self.variables)


@dataclass(frozen=True, order=True, slots=True)
class TranslationMorphism:
    """A grounded endomorphism on the currently focused variable."""

    action_id: int
    displacement: Point


@dataclass(frozen=True, order=True, slots=True)
class FocusMorphism:
    """A grounded arrow that transfers causal focus without changing content."""

    action_id: int
    source_focus: int
    destination_focus: int


@dataclass(frozen=True, slots=True)
class CommutingSquare:
    """Evidence that perception and an abstract action model commute."""

    action_id: int
    predicted: FocusedRewriteObject
    observed: FocusedRewriteObject
    commutes: bool


@dataclass(frozen=True, slots=True)
class SymbolicOption:
    """A bounded plan with an initiation object and a goal-domain termination."""

    actions: tuple[int, ...]
    target: Point | None
    expansions: int
    raw_description_length: int
    compiled_description_length: int
    compression_utility: int
    retained: bool
    status: str


def apply_translation(
    state: FocusedRewriteObject,
    morphism: TranslationMorphism,
) -> FocusedRewriteObject:
    """Apply one endomorphism without changing goals or non-focused variables."""

    variables = tuple(
        (
            FocusedVariable(
                variable.name,
                (
                    variable.value[0] + morphism.displacement[0],
                    variable.value[1] + morphism.displacement[1],
                ),
                variable.goals,
            )
            if variable.name == state.focus
            else variable
        )
        for variable in state.variables
    )
    return FocusedRewriteObject(variables, state.focus)


def translation_square(
    before: FocusedRewriteObject,
    after: FocusedRewriteObject,
    morphism: TranslationMorphism,
) -> CommutingSquare:
    """Construct the concrete-abstraction commuting-square test."""

    predicted = apply_translation(before, morphism)
    return CommutingSquare(
        morphism.action_id,
        predicted,
        after,
        predicted == after,
    )


def apply_focus(
    state: FocusedRewriteObject,
    morphism: FocusMorphism,
) -> FocusedRewriteObject:
    """Apply a grounded focus transfer while preserving every variable."""

    if state.focus != morphism.source_focus:
        raise ValueError("focus morphism source does not match state focus")
    if morphism.destination_focus not in {
        variable.name for variable in state.variables
    }:
        raise ValueError("focus morphism destination is not represented")
    return FocusedRewriteObject(state.variables, morphism.destination_focus)


def focus_square(
    before: FocusedRewriteObject,
    after: FocusedRewriteObject,
    morphism: FocusMorphism,
) -> CommutingSquare:
    """Test whether an observed control is exactly a pure focus morphism."""

    predicted = apply_focus(before, morphism)
    return CommutingSquare(
        morphism.action_id,
        predicted,
        after,
        predicted == after,
    )


def compile_focused_option(
    state: FocusedRewriteObject,
    morphisms: tuple[TranslationMorphism, ...],
    *,
    width: int,
    height: int,
    max_expansions: int = 512,
) -> SymbolicOption:
    """Solve one focused goal-domain CSP and report its MDL compression value."""

    if not 1 <= max_expansions <= 8192:
        raise ValueError("max_expansions must be between 1 and 8192")
    focused = state.focused
    if focused.value in focused.goals:
        return SymbolicOption((), focused.value, 0, 0, 0, 0, False, "satisfied")
    generators = tuple(
        sorted(
            (
                morphism
                for morphism in morphisms
                if morphism.displacement != (0, 0)
            ),
            key=lambda item: (item.action_id, item.displacement),
        )
    )
    if not generators:
        return SymbolicOption((), None, 0, 0, 0, 0, False, "unknown")

    def heuristic(point: Point) -> int:
        maximum_step = max(
            abs(item.displacement[0]) + abs(item.displacement[1])
            for item in generators
        )
        distance = min(
            abs(goal[0] - point[0]) + abs(goal[1] - point[1])
            for goal in focused.goals
        )
        return (distance + maximum_step - 1) // maximum_step

    frontier: list[tuple[int, int, Point, tuple[int, ...]]] = [
        (heuristic(focused.value), 0, focused.value, ())
    ]
    best_cost: dict[Point, int] = {focused.value: 0}
    expansions = 0
    while frontier and expansions < max_expansions:
        _priority, cost, point, actions = heapq.heappop(frontier)
        if cost != best_cost.get(point):
            continue
        if point in focused.goals:
            raw = 2 * len(actions) + 3 * len(generators)
            compiled = 4 + 3 * len(generators) + 2 * len(focused.goals)
            utility = raw - compiled
            return SymbolicOption(
                actions,
                point,
                expansions,
                raw,
                compiled,
                utility,
                utility > 0,
                "solved",
            )
        expansions += 1
        for morphism in generators:
            successor = (
                point[0] + morphism.displacement[0],
                point[1] + morphism.displacement[1],
            )
            if not (0 <= successor[0] < width and 0 <= successor[1] < height):
                continue
            next_cost = cost + 1
            if next_cost >= best_cost.get(successor, max_expansions + 1):
                continue
            best_cost[successor] = next_cost
            heapq.heappush(
                frontier,
                (
                    next_cost + heuristic(successor),
                    next_cost,
                    successor,
                    (*actions, morphism.action_id),
                ),
            )
    return SymbolicOption(
        (),
        None,
        expansions,
        0,
        0,
        0,
        False,
        "unknown",
    )
