"""Bind clipped mover shapes to differently colored landmark constraints."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import permutations

from .constellation_alignment import _embedding_targets, _landmark_groups
from .scheme_category import (
    FocusedRewriteObject,
    FocusedVariable,
    TranslationMorphism,
    compile_focused_option,
)

type Frame = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]


@dataclass(frozen=True, slots=True)
class ReferenceMover:
    color: int
    anchor: Point
    points: frozenset[Point]
    selected: bool


@dataclass(frozen=True, slots=True)
class ReferenceConstellationPlan:
    actions: tuple[int, ...]
    bindings: tuple[tuple[int, int, Point], ...]
    status: str


def _components(frame: Frame, color: int) -> tuple[frozenset[Point], ...]:
    points = {
        (x, y)
        for y, row in enumerate(frame)
        for x, value in enumerate(row)
        if value == color
    }
    seen: set[Point] = set()
    output: list[frozenset[Point]] = []
    for point in points:
        if point in seen:
            continue
        frontier = [point]
        seen.add(point)
        component: set[Point] = set()
        while frontier:
            current = frontier.pop()
            component.add(current)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbor = current[0] + dx, current[1] + dy
                    if neighbor in points and neighbor not in seen:
                        seen.add(neighbor)
                        frontier.append(neighbor)
        output.append(frozenset(component))
    return tuple(sorted(output, key=lambda item: (-len(item), min(item))))


def _rounded_mean(points: frozenset[Point]) -> Point:
    return (
        (2 * sum(x for x, _y in points) + len(points))
        // (2 * len(points)),
        (2 * sum(y for _x, y in points) + len(points))
        // (2 * len(points)),
    )


def _unbounded_central_completion(
    points: frozenset[Point],
    anchor: Point,
) -> frozenset[Point]:
    return points | frozenset(
        (2 * anchor[0] - x, 2 * anchor[1] - y)
        for x, y in points
    )


def compile_reference_constellation_plan(
    frame: Frame,
    morphisms: tuple[TranslationMorphism, ...],
    *,
    switch_action: int,
    max_expansions: int = 512,
) -> ReferenceConstellationPlan:
    """Compile a unique two-mover, cross-color landmark assignment."""

    if not frame or not frame[0] or len(morphisms) < 2:
        return ReferenceConstellationPlan((), (), "not-grounded")
    width, height = len(frame[0]), len(frame)
    counts = Counter(cell for row in frame for cell in row)
    background = counts.most_common(1)[0][0]
    groups = _landmark_groups(frame, background)
    if len(groups) != 2:
        return ReferenceConstellationPlan((), (), "not-grounded")
    selector_candidates = [
        (value, (x, y))
        for y, row in enumerate(frame)
        for x, value in enumerate(row)
        if counts[value] == 1
        and value not in {background, *groups}
    ]
    if len(selector_candidates) != 1:
        return ReferenceConstellationPlan((), (), "not-grounded")
    _selector_color, selector = selector_candidates[0]
    movers: list[ReferenceMover] = []
    for color in sorted(counts):
        if color in {background, *groups}:
            continue
        components = _components(frame, color)
        if not components or len(components[0]) < 32:
            continue
        component = components[0]
        min_x = min(x for x, _y in component)
        max_x = max(x for x, _y in component)
        min_y = min(y for _x, y in component)
        max_y = max(y for _x, y in component)
        if (max_x - min_x + 1 == width) or (max_y - min_y + 1 == height):
            continue
        selected = min_x <= selector[0] <= max_x and min_y <= selector[1] <= max_y
        anchor = selector if selected else _rounded_mean(component)
        movers.append(
            ReferenceMover(
                color,
                anchor,
                _unbounded_central_completion(component, anchor),
                selected,
            )
        )
    if len(movers) != 2 or sum(mover.selected for mover in movers) != 1:
        return ReferenceConstellationPlan((), (), "not-grounded")
    movers.sort(key=lambda mover: (not mover.selected, mover.color))
    step = min(
        abs(item.displacement[0]) + abs(item.displacement[1])
        for item in morphisms
        if item.displacement != (0, 0)
    )
    domains: dict[tuple[int, int], tuple[Point, ...]] = {}
    for mover_index, mover in enumerate(movers):
        for landmark_color, landmarks in groups.items():
            embedded_targets = _embedding_targets(
                mover.points,
                landmarks,
                mover.anchor,
                width,
                height,
            )
            reachable = tuple(
                sorted(
                    target
                    for target in embedded_targets
                    if (
                        target[0] - mover.anchor[0]
                    ) % step == 0
                    and (
                        target[1] - mover.anchor[1]
                    ) % step == 0
                )
            )
            if reachable:
                domains[mover_index, landmark_color] = reachable
    assignments: list[
        tuple[int, tuple[tuple[int, int, Point], ...], tuple[int, ...]]
    ] = []
    landmark_colors = tuple(sorted(groups))
    for assigned_colors in permutations(landmark_colors):
        bindings: list[tuple[int, int, Point]] = []
        actions: list[int] = []
        cost = 0
        valid = True
        for index, (mover, landmark_color) in enumerate(
            zip(movers, assigned_colors, strict=True)
        ):
            candidate_targets = domains.get((index, landmark_color), ())
            options: list[tuple[int, Point, tuple[int, ...]]] = []
            for target in candidate_targets:
                option = compile_focused_option(
                    FocusedRewriteObject(
                        (
                            FocusedVariable(
                                index,
                                mover.anchor,
                                frozenset({target}),
                            ),
                        ),
                        index,
                    ),
                    morphisms,
                    width=width,
                    height=height,
                    max_expansions=max_expansions,
                )
                if option.actions:
                    options.append((len(option.actions), target, option.actions))
            if not options:
                valid = False
                break
            length, target, route = min(options)
            if sum(item[0] == length for item in options) != 1:
                valid = False
                break
            if index:
                actions.append(switch_action)
                cost += 1
            actions.extend(route)
            cost += length
            bindings.append((mover.color, landmark_color, target))
        if valid:
            assignments.append((cost, tuple(bindings), tuple(actions)))
    if not assignments:
        return ReferenceConstellationPlan((), (), "not-grounded")
    minimum = min(cost for cost, _bindings, _actions in assignments)
    best = [
        (bindings, actions)
        for cost, bindings, actions in assignments
        if cost == minimum
    ]
    if len(best) != 1:
        return ReferenceConstellationPlan((), (), "ambiguous")
    selected_bindings, selected_actions = best[0]
    return ReferenceConstellationPlan(
        selected_actions,
        selected_bindings,
        "solved",
    )
