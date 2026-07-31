"""Infer movable crosses and latent targets encoded by landmark constellations."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

type Frame = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class ConstellationObject:
    """One colored mover and the intersection encoded by its four landmarks."""

    color: int
    center: tuple[int, int]
    target: tuple[int, int]

    @property
    def distance(self) -> int:
        return abs(self.target[0] - self.center[0]) + abs(
            self.target[1] - self.center[1]
        )


@dataclass(frozen=True, slots=True)
class ConstellationAlignment:
    """A uniquely parsed multi-object constellation-alignment problem."""

    objects: tuple[ConstellationObject, ...]
    selected_color: int


def _landmark_groups(frame: Frame, background: int) -> dict[int, set[tuple[int, int]]]:
    height = len(frame)
    width = len(frame[0])
    groups: dict[int, set[tuple[int, int]]] = {}
    for top in range(height - 2):
        for left in range(width - 2):
            perimeter = (
                frame[top][left],
                frame[top][left + 1],
                frame[top][left + 2],
                frame[top + 1][left],
                frame[top + 1][left + 2],
                frame[top + 2][left],
                frame[top + 2][left + 1],
                frame[top + 2][left + 2],
            )
            center_color = frame[top + 1][left + 1]
            counts = Counter(perimeter)
            ring_color, support = counts.most_common(1)[0]
            if (
                ring_color == background
                or center_color in {background, ring_color}
                or support < 6
                or set(counts) - {ring_color, center_color}
            ):
                continue
            groups.setdefault(center_color, set()).add((left + 1, top + 1))
    return groups


def _intersection(points: set[tuple[int, int]]) -> tuple[int, int] | None:
    if len(points) != 4:
        return None
    candidates: set[tuple[int, int]] = set()
    ordered = tuple(points)
    for first_index, first in enumerate(ordered):
        for second in ordered[first_index + 1 :]:
            if first[0] != second[0]:
                continue
            vertical = {first, second}
            horizontal = tuple(point for point in points if point not in vertical)
            if len(horizontal) != 2 or horizontal[0][1] != horizontal[1][1]:
                continue
            target = first[0], horizontal[0][1]
            if target in points:
                continue
            candidates.add(target)
    return next(iter(candidates)) if len(candidates) == 1 else None


def _run_length(
    frame: Frame,
    center: tuple[int, int],
    color: int,
    delta: tuple[int, int],
) -> int:
    width = len(frame[0])
    height = len(frame)
    x, y = center
    dx, dy = delta
    length = 0
    x += dx
    y += dy
    while 0 <= x < width and 0 <= y < height and frame[y][x] == color:
        length += 1
        x += dx
        y += dy
    return length


def _plus_centers(frame: Frame, color: int) -> tuple[tuple[int, int], ...]:
    height = len(frame)
    width = len(frame[0])
    centers: list[tuple[int, int]] = []
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            center = x, y
            runs = tuple(
                _run_length(frame, center, color, delta)
                for delta in ((-1, 0), (1, 0), (0, -1), (0, 1))
            )
            if min(runs) < 3:
                continue
            horizontal = runs[0] + runs[1]
            vertical = runs[2] + runs[3]
            if abs(horizontal - vertical) <= 2:
                centers.append(center)
    return tuple(centers)


def infer_constellation_alignment(frame: Frame) -> ConstellationAlignment | None:
    """Return a unique colored-plus/landmark alignment, otherwise abstain."""

    if not frame or not frame[0] or any(len(row) != len(frame[0]) for row in frame):
        return None
    background = Counter(cell for row in frame for cell in row).most_common(1)[0][0]
    groups = _landmark_groups(frame, background)
    objects: list[ConstellationObject] = []
    selected: list[int] = []
    for color, points in groups.items():
        target = _intersection(points)
        centers = _plus_centers(frame, color)
        if target is None or len(centers) != 1:
            continue
        center = centers[0]
        objects.append(ConstellationObject(color, center, target))
        if frame[center[1]][center[0]] != color:
            selected.append(color)
    if len(objects) < 2 or len(objects) != len(groups) or len(selected) != 1:
        return None
    return ConstellationAlignment(
        tuple(sorted(objects, key=lambda item: item.color)),
        selected[0],
    )
