"""Generic planning over visually grounded, topology-editing interventions.

The environment remains the transition oracle.  The planner knows neither action
semantics nor a game-specific route: it searches canonical observed states using
opaque interventions grounded in visible component addresses.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Callable, Hashable, Iterable, Mapping, Sequence

Grid = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class Intervention:
    token: str
    action_id: int
    data: tuple[tuple[str, int], ...] = ()

    def payload(self) -> dict[str, int]:
        return dict(self.data)


@dataclass(frozen=True)
class SearchResult:
    plan: tuple[Intervention, ...]
    expanded: int
    observed_state_count: int


class EditableTopologyError(ValueError):
    pass


class NoEditableTopologyPlan(RuntimeError):
    pass


def _components(points: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    output: list[set[tuple[int, int]]] = []
    while points:
        seed = points.pop()
        component = {seed}
        frontier = [seed]
        while frontier:
            x, y = frontier.pop()
            for neighbour in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbour in points:
                    points.remove(neighbour)
                    component.add(neighbour)
                    frontier.append(neighbour)
        output.append(component)
    return output


def grounded_interaction_points(
    grid: Grid,
    *,
    background_values: frozenset[int] = frozenset({0}),
    min_component_mass: int = 2,
) -> tuple[tuple[int, int], ...]:
    """Infer display-space component centres in a visually separated side pane.

    The pane boundary is the strongest vertical transition boundary.  This is an
    address proposal, not evidence that a component is interactive; interventions
    remain support-zero until an observed successor changes.
    """
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise EditableTopologyError("grid must be a nonempty rectangle")
    height, width = len(grid), len(grid[0])
    if width < 3:
        return ()
    boundary_scores = [
        sum(grid[y][x] != grid[y][x - 1] for y in range(height))
        for x in range(1, width)
    ]
    split = max(range(1, width), key=lambda x: (boundary_scores[x - 1], x))
    points = {
        (x, y)
        for y in range(height)
        for x in range(split + 1, width)
        if grid[y][x] not in background_values
    }
    padding_y = (64 - height) // 2
    centres = []
    for component in _components(points):
        if len(component) < min_component_mass:
            continue
        xs = [point[0] for point in component]
        ys = [point[1] for point in component]
        centres.append(((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2 + padding_y))
    return tuple(sorted(set(centres)))


def intervention_vocabulary(
    simple_action_ids: Iterable[int],
    *,
    parameterized_action_id: int | None,
    interaction_points: Iterable[tuple[int, int]],
) -> tuple[Intervention, ...]:
    output = [Intervention(f"simple:{int(action_id)}", int(action_id)) for action_id in sorted(set(simple_action_ids))]
    if parameterized_action_id is not None:
        for index, (x, y) in enumerate(sorted(set(interaction_points))):
            output.append(
                Intervention(
                    f"grounded-component:{index}",
                    int(parameterized_action_id),
                    (("x", int(x)), ("y", int(y))),
                )
            )
    return tuple(output)


def search_observed_state_space(
    interventions: Sequence[Intervention],
    *,
    observe_prefix: Callable[[tuple[Intervention, ...]], Mapping[str, object]],
    state_key: Callable[[Mapping[str, object]], Hashable],
    completed: Callable[[Mapping[str, object]], bool],
    viable: Callable[[Mapping[str, object]], bool] = lambda _state: True,
    max_depth: int = 32,
    max_expansions: int = 100_000,
) -> SearchResult:
    """Breadth-first search with exact observed-state transposition pruning."""
    if not interventions:
        raise EditableTopologyError("at least one intervention is required")
    initial = observe_prefix(())
    if completed(initial):
        return SearchResult((), 0, 1)
    queue = deque([()])
    seen = {state_key(initial)}
    expanded = 0
    while queue:
        prefix = queue.popleft()
        if len(prefix) >= max_depth:
            continue
        for intervention in interventions:
            candidate = prefix + (intervention,)
            state = observe_prefix(candidate)
            expanded += 1
            if completed(state):
                return SearchResult(candidate, expanded, len(seen) + 1)
            key = state_key(state)
            if viable(state) and key not in seen:
                seen.add(key)
                queue.append(candidate)
            if expanded >= max_expansions:
                raise NoEditableTopologyPlan(
                    f"expansion budget exhausted after {expanded} transitions"
                )
    raise NoEditableTopologyPlan(
        f"no plan within depth {max_depth}; observed {len(seen)} states"
    )

