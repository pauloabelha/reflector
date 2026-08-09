"""Infer and traverse a visual progress field from calibrated pixel motion.

The module knows no game IDs, colors, action meanings, or routes.  It treats
the substrate exposed behind a translated controlled process as traversable,
then distinguishes small overlays on that substrate from terminal-like visual
regions adjoining it.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from math import gcd
from typing import Mapping, Sequence


class ProgressFieldError(ValueError):
    pass


Point = tuple[int, int]
Delta = tuple[int, int]


@dataclass(frozen=True)
class MotionSample:
    before_anchor: Point
    after_anchor: Point
    size: Point
    before_grid: tuple[tuple[int, ...], ...]
    after_grid: tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class ProgressField:
    step: int
    lattice_offset: Point
    substrate: int
    background: int
    controlled_anchor: Point
    passable: frozenset[Point]
    overlay_affordances: tuple[Point, ...]
    terminal_candidates: tuple[Point, ...]


@dataclass(frozen=True)
class ProgressItinerary:
    waypoints: tuple[Point, ...]
    actions: tuple[int, ...]
    waypoint_action_ends: tuple[int, ...]


def _grid(value: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    rows = tuple(tuple(int(cell) for cell in row) for row in value)
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise ProgressFieldError("grid must be a nonempty rectangle")
    return rows


def motion_sample(before_grid: Sequence[Sequence[int]], after_grid: Sequence[Sequence[int]], *, before_anchor: Point, after_anchor: Point, size: Point) -> MotionSample:
    before, after = _grid(before_grid), _grid(after_grid)
    if (len(before), len(before[0])) != (len(after), len(after[0])):
        raise ProgressFieldError("motion grids differ in shape")
    if before_anchor == after_anchor:
        raise ProgressFieldError("motion sample has zero displacement")
    if min(size) <= 0:
        raise ProgressFieldError("controlled size must be positive")
    return MotionSample(tuple(before_anchor), tuple(after_anchor), tuple(size), before, after)


def _step(samples: Sequence[MotionSample]) -> int:
    value = 0
    for sample in samples:
        dx = abs(sample.after_anchor[0] - sample.before_anchor[0])
        dy = abs(sample.after_anchor[1] - sample.before_anchor[1])
        value = gcd(value, gcd(dx, dy))
    if value <= 0:
        raise ProgressFieldError("motion does not establish a lattice step")
    return value


def _restoration_color(samples: Sequence[MotionSample]) -> int:
    counts: Counter[int] = Counter()
    for sample in samples:
        x0, y0 = sample.before_anchor
        width, height = sample.size
        for y in range(y0, min(y0 + height, len(sample.after_grid))):
            for x in range(x0, min(x0 + width, len(sample.after_grid[0]))):
                if sample.before_grid[y][x] != sample.after_grid[y][x]:
                    counts[sample.after_grid[y][x]] += 1
    if not counts:
        raise ProgressFieldError("motion exposed no stable substrate")
    return min(counts, key=lambda color: (-counts[color], color))


def infer_progress_field(samples: Sequence[MotionSample]) -> ProgressField:
    if not samples:
        raise ProgressFieldError("at least one motion sample is required")
    step = _step(samples)
    substrate = _restoration_color(samples)
    current = samples[-1].after_anchor
    latest = samples[-1].after_grid
    global_counts = Counter(cell for row in latest for cell in row)
    alternatives = [color for color in global_counts if color != substrate]
    if not alternatives:
        raise ProgressFieldError("frame has no substrate contrast")
    background = min(alternatives, key=lambda color: (-global_counts[color], color))
    offset = current[0] % step, current[1] % step
    height, width = len(latest), len(latest[0])
    tile_area = step * step
    tiles: dict[Point, Counter[int]] = {}
    for y in range(offset[1], height - step + 1, step):
        for x in range(offset[0], width - step + 1, step):
            tiles[(x, y)] = Counter(
                latest[yy][xx]
                for yy in range(y, y + step)
                for xx in range(x, x + step)
            )
    passable = {
        point for point, counts in tiles.items()
        if counts[substrate] * 2 >= tile_area
    }
    passable.add(current)
    novelty = {
        point: sum(count for color, count in counts.items() if color not in {substrate, background})
        for point, counts in tiles.items()
    }
    overlays = tuple(sorted(
        point for point in passable
        if point != current and novelty[point] > 0
    ))
    directions = ((0, -step), (0, step), (-step, 0), (step, 0))
    terminals = tuple(sorted(
        point for point in tiles
        if point not in passable
        and novelty[point] * 5 >= tile_area
        and any((point[0] + dx, point[1] + dy) in passable for dx, dy in directions)
    ))
    if not passable:
        raise ProgressFieldError("no traversable field was inferred")
    return ProgressField(step, offset, substrate, background, current, frozenset(passable), overlays, terminals)


def shortest_actions(start: Point, target: Point, allowed: frozenset[Point] | set[Point], delta_actions: Mapping[Delta, int]) -> tuple[int, ...] | None:
    queue = deque([start])
    parent: dict[Point, tuple[Point, int] | None] = {start: None}
    ordered = sorted(((tuple(delta), int(action)) for delta, action in delta_actions.items()), key=lambda row: row[1])
    while queue:
        point = queue.popleft()
        if point == target:
            break
        for (dx, dy), action in ordered:
            successor = point[0] + dx, point[1] + dy
            if successor not in allowed or successor in parent:
                continue
            parent[successor] = point, action
            queue.append(successor)
    if target not in parent:
        return None
    actions: list[int] = []
    point = target
    while parent[point] is not None:
        point, action = parent[point]
        actions.append(action)
    return tuple(reversed(actions))


def plan_progress(field: ProgressField, delta_actions: Mapping[Delta, int]) -> ProgressItinerary:
    expected = {(0, -field.step), (0, field.step), (-field.step, 0), (field.step, 0)}
    if not expected.issubset({tuple(delta) for delta in delta_actions}):
        raise ProgressFieldError("the lattice is not controllable in four directions")
    current = field.controlled_anchor
    remaining = set(field.overlay_affordances)
    waypoints: list[Point] = []
    actions: list[int] = []
    ends: list[int] = []
    while remaining:
        options = []
        for target in remaining:
            route = shortest_actions(current, target, field.passable, delta_actions)
            if route is not None:
                options.append((len(route), target, route))
        if not options:
            break
        _length, target, route = min(options)
        actions.extend(route)
        current = target
        remaining.remove(target)
        waypoints.append(target)
        ends.append(len(actions))
    for target in field.terminal_candidates:
        route = shortest_actions(current, target, set(field.passable) | {target}, delta_actions)
        if route is None:
            continue
        actions.extend(route)
        current = target
        waypoints.append(target)
        ends.append(len(actions))
        break
    if not actions:
        raise ProgressFieldError("no reachable progress itinerary")
    return ProgressItinerary(tuple(waypoints), tuple(actions), tuple(ends))


__all__ = ["MotionSample", "ProgressField", "ProgressFieldError", "ProgressItinerary", "infer_progress_field", "motion_sample", "plan_progress", "shortest_actions"]
