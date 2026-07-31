"""Bind clipped mover shapes to differently colored landmark constraints."""

from __future__ import annotations

import heapq
from collections import Counter
from dataclasses import dataclass
from itertools import permutations

from .constellation_alignment import _embedding_targets, _landmark_groups
from .scheme_category import (
    TranslationMorphism,
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


@dataclass(frozen=True, slots=True)
class CompositeReferenceOption:
    """One mover's contribution to a jointly painted exact cover."""

    source_color: int
    home_anchor: Point
    target_anchor: Point
    target_color: int
    actions: tuple[int, ...]
    selected: bool


@dataclass(frozen=True, slots=True)
class CompositeReferencePlan:
    """A unique multi-mover cover with causally latent landmark colors."""

    options: tuple[CompositeReferenceOption, ...]
    selector_color: int | None
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


def _paint_regions(
    frame: Frame,
) -> dict[int, frozenset[Point]]:
    output: dict[int, frozenset[Point]] = {}
    for color in sorted({value for row in frame for value in row}):
        for component in _components(frame, color):
            if len(component) != 16:
                continue
            component_width = (
                max(x for x, _y in component)
                - min(x for x, _y in component)
                + 1
            )
            component_height = (
                max(y for _x, y in component)
                - min(y for _x, y in component)
                + 1
            )
            if component_width == component_height == 4:
                output[color] = component
                break
    return output


def _shape_anchor(points: frozenset[Point]) -> Point:
    """Infer a symmetry center, including a one-sided clipped thick cross."""

    row_counts = Counter(y for _x, y in points)
    column_counts = Counter(x for x, _y in points)
    row, row_support = row_counts.most_common(1)[0]
    column, column_support = column_counts.most_common(1)[0]
    if row_support >= 5 and column_support >= 5:
        return column, row
    return (
        (min(x for x, _y in points) + max(x for x, _y in points)) // 2,
        (min(y for _x, y in points) + max(y for _x, y in points)) // 2,
    )


def _landmark_ring_color(
    frame: Frame,
    landmarks: dict[int, set[Point]],
) -> int | None:
    perimeter: Counter[int] = Counter()
    height = len(frame)
    width = len(frame[0])
    for points in landmarks.values():
        for x, y in points:
            for dx, dy in (
                (-1, -1),
                (0, -1),
                (1, -1),
                (-1, 0),
                (1, 0),
                (-1, 1),
                (0, 1),
                (1, 1),
            ):
                if 0 <= x + dx < width and 0 <= y + dy < height:
                    perimeter[frame[y + dy][x + dx]] += 1
    return perimeter.most_common(1)[0][0] if perimeter else None


def _composite_movers(
    frame: Frame,
    landmarks: dict[int, set[Point]],
    paint_regions: dict[int, frozenset[Point]],
    selector: Point,
    selector_color: int,
) -> tuple[ReferenceMover, ...]:
    counts = Counter(value for row in frame for value in row)
    background = counts.most_common(1)[0][0]
    ring_color = _landmark_ring_color(frame, landmarks)
    paint_border_colors = {
        frame[min(y for _x, y in region) - 1][
            min(x for x, _y in region) - 1
        ]
        for region in paint_regions.values()
        if min(x for x, _y in region) > 0
        and min(y for _x, y in region) > 0
    }
    height = len(frame)
    width = len(frame[0])
    movers: list[ReferenceMover] = []
    for color in sorted(counts):
        if color in {
            background,
            ring_color,
            selector_color,
            *paint_border_colors,
        }:
            continue
        excluded = paint_regions.get(color, frozenset())
        points = frozenset(
            (x, y)
            for y, row in enumerate(frame)
            for x, value in enumerate(row)
            if value == color and (x, y) not in excluded
        )
        if len(points) < 24:
            continue
        if (
            max(x for x, _y in points) - min(x for x, _y in points) + 1
            == width
            or max(y for _x, y in points) - min(y for _x, y in points) + 1
            == height
        ):
            continue
        anchor = _shape_anchor(points)
        selected = anchor == selector
        movers.append(
            ReferenceMover(
                color,
                anchor,
                _unbounded_central_completion(points, anchor),
                selected,
            )
        )
    return tuple(movers)


def _compile_paint_route(
    mover: ReferenceMover,
    target: Point,
    target_color: int,
    morphisms: tuple[TranslationMorphism, ...],
    paint_regions: dict[int, frozenset[Point]],
    *,
    width: int,
    height: int,
    max_expansions: int,
) -> tuple[int, ...] | None:
    offsets = frozenset(
        (x - mover.anchor[0], y - mover.anchor[1])
        for x, y in mover.points
    )
    maximum_step = max(
        abs(item.displacement[0]) + abs(item.displacement[1])
        for item in morphisms
    )

    def heuristic(point: Point) -> int:
        distance = abs(point[0] - target[0]) + abs(point[1] - target[1])
        return (distance + maximum_step - 1) // maximum_step

    start = mover.anchor, mover.color
    frontier: list[
        tuple[int, int, Point, int, tuple[int, ...]]
    ] = [(heuristic(mover.anchor), 0, mover.anchor, mover.color, ())]
    best: dict[tuple[Point, int], int] = {start: 0}
    expansions = 0
    while frontier and expansions < max_expansions:
        _priority, cost, point, color, actions = heapq.heappop(frontier)
        if cost != best.get((point, color)):
            continue
        if point == target and color == target_color:
            return actions
        expansions += 1
        for morphism in sorted(morphisms):
            successor = (
                point[0] + morphism.displacement[0],
                point[1] + morphism.displacement[1],
            )
            if not (
                0 <= successor[0] < width
                and 0 <= successor[1] < height
            ):
                continue
            contacts = {
                paint_color
                for paint_color, region in paint_regions.items()
                if any(
                    (
                        pixel[0] - successor[0],
                        pixel[1] - successor[1],
                    )
                    in offsets
                    for pixel in region
                )
            }
            if len(contacts) > 1:
                continue
            next_color = next(iter(contacts), color)
            state = successor, next_color
            next_cost = cost + 1
            if next_cost >= best.get(state, max_expansions + 1):
                continue
            best[state] = next_cost
            heapq.heappush(
                frontier,
                (
                    next_cost + heuristic(successor),
                    next_cost,
                    successor,
                    next_color,
                    (*actions, morphism.action_id),
                ),
            )
    return None


def compile_reference_constellation_plan(
    frame: Frame,
    morphisms: tuple[TranslationMorphism, ...],
    *,
    switch_action: int,
    max_expansions: int = 4096,
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
    paint_regions = _paint_regions(frame)
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
                route = _compile_paint_route(
                    mover,
                    target,
                    landmark_color,
                    morphisms,
                    paint_regions,
                    width=width,
                    height=height,
                    max_expansions=max_expansions,
                )
                if route:
                    options.append((len(route), target, route))
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


def compile_composite_reference_plan(
    frame: Frame,
    morphisms: tuple[TranslationMorphism, ...],
    *,
    max_expansions: int = 20_000,
    max_assignments: int = 4096,
) -> CompositeReferencePlan:
    """Jointly solve mover placement, paint state, and occluded landmark color.

    A landmark center is allowed to be latent only when a currently rendered
    mover pixel of that same color lies over it. All other center colors remain
    hard constraints. Multiple movers may inhabit the same paint-color fiber.
    """

    failure = CompositeReferencePlan((), None, "not-grounded")
    if not frame or not frame[0] or len(morphisms) < 2:
        return failure
    width, height = len(frame[0]), len(frame)
    counts = Counter(value for row in frame for value in row)
    background = counts.most_common(1)[0][0]
    groups = _landmark_groups(frame, background)
    landmarks = {
        point: color
        for color, points in groups.items()
        for point in points
    }
    if len(landmarks) < 6:
        return failure
    paint_regions = _paint_regions(frame)
    ring_color = _landmark_ring_color(frame, groups)
    selector_candidates = [
        (value, (x, y))
        for y, row in enumerate(frame)
        for x, value in enumerate(row)
        if counts[value] == 1
        and value not in {background, ring_color}
        and value not in paint_regions
    ]
    if len(selector_candidates) != 1:
        return failure
    selector_color, selector = selector_candidates[0]
    movers = _composite_movers(
        frame,
        groups,
        paint_regions,
        selector,
        selector_color,
    )
    if len(movers) < 3 or sum(mover.selected for mover in movers) != 1:
        return failure
    mover_colors = {mover.color for mover in movers}
    visible_by_color = {
        mover.color: frozenset(
            point
            for point in mover.points
            if 0 <= point[0] < width and 0 <= point[1] < height
        )
        for mover in movers
    }
    latent = {
        point
        for point, color in landmarks.items()
        if color in mover_colors and point in visible_by_color[color]
    }
    fixed_colors = {
        color
        for point, color in landmarks.items()
        if point not in latent
    }
    if not fixed_colors or not fixed_colors <= set(paint_regions):
        return failure
    step = min(
        abs(item.displacement[0]) + abs(item.displacement[1])
        for item in morphisms
        if item.displacement != (0, 0)
    )
    domains: list[
        tuple[
            tuple[
                frozenset[Point],
                CompositeReferenceOption,
            ],
            ...,
        ]
    ] = []
    all_landmarks = frozenset(landmarks)
    for mover in movers:
        offsets = frozenset(
            (x - mover.anchor[0], y - mover.anchor[1])
            for x, y in mover.points
        )
        candidates: dict[
            tuple[Point, int, frozenset[Point]],
            CompositeReferenceOption,
        ] = {}
        for x in range(mover.anchor[0] % step, width, step):
            for y in range(mover.anchor[1] % step, height, step):
                covered = frozenset(
                    point
                    for point in all_landmarks
                    if (point[0] - x, point[1] - y) in offsets
                )
                if len(covered) < 2:
                    continue
                required = {
                    landmarks[point]
                    for point in covered
                    if point not in latent
                }
                if len(required) != 1:
                    continue
                target_color = next(iter(required))
                route = _compile_paint_route(
                    mover,
                    (x, y),
                    target_color,
                    morphisms,
                    paint_regions,
                    width=width,
                    height=height,
                    max_expansions=max_expansions,
                )
                if route is None:
                    continue
                option = CompositeReferenceOption(
                    mover.color,
                    mover.anchor,
                    (x, y),
                    target_color,
                    route,
                    mover.selected,
                )
                candidates[(option.target_anchor, target_color, covered)] = option
        if not candidates:
            return failure
        domains.append(
            tuple(
                (covered, option)
                for (_target, _color, covered), option in sorted(
                    candidates.items()
                )
            )
        )

    solutions: list[tuple[int, tuple[CompositeReferenceOption, ...]]] = []
    assignments = 0

    def search(
        index: int,
        covered: frozenset[Point],
        chosen: tuple[CompositeReferenceOption, ...],
    ) -> None:
        nonlocal assignments
        if assignments >= max_assignments:
            return
        if index == len(domains):
            assignments += 1
            if covered == all_landmarks:
                solutions.append(
                    (
                        sum(len(option.actions) for option in chosen),
                        chosen,
                    )
                )
            return
        for contribution, option in domains[index]:
            if contribution & covered:
                continue
            search(index + 1, covered | contribution, (*chosen, option))

    search(0, frozenset(), ())
    if not solutions:
        status = (
            "search-bound-exhausted"
            if assignments >= max_assignments
            else "no-exact-cover"
        )
        return CompositeReferencePlan((), selector_color, status)
    minimum = min(cost for cost, _options in solutions)
    best = {
        tuple(
            (
                option.source_color,
                option.target_anchor,
                option.target_color,
            )
            for option in options
        ): options
        for cost, options in solutions
        if cost == minimum
    }
    if len(best) != 1:
        return CompositeReferencePlan((), selector_color, "ambiguous")
    options = next(iter(best.values()))
    return CompositeReferencePlan(
        tuple(sorted(options, key=lambda option: option.source_color)),
        selector_color,
        "solved",
    )
