"""Causal factor discovery and exact-cover goals for overlapping movers."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from itertools import product

from .constellation_alignment import _landmark_groups

type Frame = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]


@dataclass(frozen=True, slots=True)
class FactorScene:
    """One same-colored product scene and its currently focused anchor."""

    color: int
    landmarks: frozenset[Point]
    selector_color: int
    selector: Point


@dataclass(frozen=True, slots=True)
class FactorMask:
    """One causally separated mover mask relative to its focus anchor."""

    home_anchor: Point
    offsets: frozenset[Point]


@dataclass(frozen=True, slots=True)
class FactorGoal:
    """One factor placement selected by the global exact-cover CSP."""

    factor_index: int
    target_anchor: Point
    covered_landmarks: frozenset[Point]
    action_cost: int


def infer_factor_scene(frame: Frame) -> FactorScene | None:
    """Parse a one-color, multi-factor landmark scene conservatively."""

    if not frame or not frame[0] or any(len(row) != len(frame[0]) for row in frame):
        return None
    counts = Counter(cell for row in frame for cell in row)
    background = counts.most_common(1)[0][0]
    groups = _landmark_groups(frame, background)
    if len(groups) != 1:
        return None
    color, landmarks = next(iter(groups.items()))
    if len(landmarks) < 4:
        return None
    candidates = [
        (value, (x, y))
        for y, row in enumerate(frame)
        for x, value in enumerate(row)
        if counts[value] == 1
        and value not in {background, color}
    ]
    if len(candidates) != 1:
        return None
    selector_color, selector = candidates[0]
    return FactorScene(
        color,
        frozenset(landmarks),
        selector_color,
        selector,
    )


def find_selector(frame: Frame, selector_color: int) -> Point | None:
    """Return the unique focus marker of a known factor scene."""

    points = [
        (x, y)
        for y, row in enumerate(frame)
        for x, value in enumerate(row)
        if value == selector_color
    ]
    return points[0] if len(points) == 1 else None


def learn_factor_mask(
    before: Frame,
    after: Frame,
    scene: FactorScene,
    displacement: Point,
) -> FactorMask | None:
    """Separate a translated factor from same-colored overlapping factors."""

    dx, dy = displacement
    expected_selector = scene.selector[0] + dx, scene.selector[1] + dy
    if not (
        0 <= expected_selector[0] < len(before[0])
        and 0 <= expected_selector[1] < len(before)
        and after[expected_selector[1]][expected_selector[0]]
        == scene.selector_color
    ):
        return None
    removed = {
        (x, y)
        for y, row in enumerate(before)
        for x, value in enumerate(row)
        if value == scene.color and after[y][x] != scene.color
    }
    added = {
        (x, y)
        for y, row in enumerate(after)
        for x, value in enumerate(row)
        if value == scene.color and before[y][x] != scene.color
    }
    points = removed | {(x - dx, y - dy) for x, y in added}
    if len(points) < 3:
        return None
    offsets = {
        (x - scene.selector[0], y - scene.selector[1])
        for x, y in points
    }
    offsets |= {(-x, -y) for x, y in offsets}
    x, y = scene.selector
    horizontal = (
        0 < x < len(before[0]) - 1
        and before[y][x - 1] == scene.color
        and before[y][x + 1] == scene.color
    )
    vertical = (
        0 < y < len(before) - 1
        and before[y - 1][x] == scene.color
        and before[y + 1][x] == scene.color
    )
    if horizontal or vertical:
        offsets.add((0, 0))
    return FactorMask(scene.selector, frozenset(offsets))


def solve_factor_exact_cover(
    factors: tuple[FactorMask, ...],
    landmarks: frozenset[Point],
    *,
    width: int,
    height: int,
    step: int,
) -> tuple[FactorGoal, ...] | None:
    """Select a unique minimum-cost reachable placement for every factor."""

    if not factors or not landmarks or step < 1:
        return None
    domains: list[tuple[FactorGoal, ...]] = []
    for index, factor in enumerate(factors):
        candidates: list[FactorGoal] = []
        for x in range(factor.home_anchor[0] % step, width, step):
            for y in range(factor.home_anchor[1] % step, height, step):
                if not all(
                    0 <= x + dx < width and 0 <= y + dy < height
                    for dx, dy in factor.offsets
                ):
                    continue
                covered = frozenset(
                    landmark
                    for landmark in landmarks
                    if (
                        landmark[0] - x,
                        landmark[1] - y,
                    )
                    in factor.offsets
                )
                if len(covered) < 2:
                    continue
                cost = (
                    abs(x - factor.home_anchor[0])
                    + abs(y - factor.home_anchor[1])
                ) // step
                candidates.append(
                    FactorGoal(index, (x, y), covered, cost)
                )
        if not candidates:
            return None
        domains.append(tuple(candidates))
    solutions: list[tuple[int, tuple[FactorGoal, ...]]] = []
    for assignment in product(*domains):
        union: set[Point] = set()
        valid = True
        for goal in assignment:
            if union & goal.covered_landmarks:
                valid = False
                break
            union.update(goal.covered_landmarks)
        if valid and union == landmarks:
            solutions.append(
                (sum(goal.action_cost for goal in assignment), assignment)
            )
    if not solutions:
        return None
    minimum = min(cost for cost, _assignment in solutions)
    best = {
        tuple(
            (goal.factor_index, goal.target_anchor)
            for goal in assignment
        ): assignment
        for cost, assignment in solutions
        if cost == minimum
    }
    if len(best) != 1:
        return None
    return next(iter(best.values()))
