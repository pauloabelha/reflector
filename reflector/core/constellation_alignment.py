"""Infer movable crosses and latent targets encoded by landmark constellations."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

type Frame = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class ConstellationObject:
    """One colored mover and its uniquely reachable subset embeddings."""

    color: int
    center: tuple[int, int]
    targets: frozenset[tuple[int, int]]

    @property
    def distance(self) -> int:
        return min(
            abs(target[0] - self.center[0]) + abs(target[1] - self.center[1])
            for target in self.targets
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


def _shape_points(frame: Frame, color: int) -> frozenset[tuple[int, int]]:
    height = len(frame)
    width = len(frame[0])
    points = {
        (x, y)
        for y, row in enumerate(frame)
        for x, value in enumerate(row)
        if value == color
    }
    seen: set[tuple[int, int]] = set()
    components: list[set[tuple[int, int]]] = []
    for point in points:
        if point in seen:
            continue
        frontier = [point]
        seen.add(point)
        component: set[tuple[int, int]] = set()
        while frontier:
            current = frontier.pop()
            component.add(current)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    neighbor = current[0] + dx, current[1] + dy
                    if (
                        0 <= neighbor[0] < width
                        and 0 <= neighbor[1] < height
                        and neighbor in points
                        and neighbor not in seen
                    ):
                        seen.add(neighbor)
                        frontier.append(neighbor)
        components.append(component)
    return frozenset().union(
        *(component for component in components if len(component) >= 3)
    )


def _embedding_targets(
    shape: frozenset[tuple[int, int]],
    landmarks: set[tuple[int, int]],
    center: tuple[int, int],
    width: int,
    height: int,
) -> frozenset[tuple[int, int]]:
    translations: set[tuple[int, int]] | None = None
    for landmark in landmarks:
        candidates = {
            (landmark[0] - point[0], landmark[1] - point[1])
            for point in shape
        }
        translations = (
            candidates if translations is None else translations & candidates
        )
    bounded = {
        delta
        for delta in translations or set()
        if 0 <= center[0] + delta[0] < width
        and 0 <= center[1] + delta[1] < height
    }
    return frozenset(
        (center[0] + delta[0], center[1] + delta[1])
        for delta in bounded
    )


def infer_constellation_alignment(frame: Frame) -> ConstellationAlignment | None:
    """Return a unique colored-plus/landmark alignment, otherwise abstain."""

    if not frame or not frame[0] or any(len(row) != len(frame[0]) for row in frame):
        return None
    background = Counter(cell for row in frame for cell in row).most_common(1)[0][0]
    counts = Counter(cell for row in frame for cell in row)
    groups = _landmark_groups(frame, background)
    objects: list[ConstellationObject] = []
    selected: list[int] = []
    for color, points in groups.items():
        if len(points) < 2:
            continue
        shape = _shape_points(frame, color)
        if len(shape) < 8:
            continue
        center = (
            (2 * sum(point[0] for point in shape) + len(shape))
            // (2 * len(shape)),
            (2 * sum(point[1] for point in shape) + len(shape))
            // (2 * len(shape)),
        )
        targets = _embedding_targets(
            shape,
            points,
            center,
            len(frame[0]),
            len(frame),
        )
        if not targets:
            continue
        objects.append(ConstellationObject(color, center, targets))
        selector = frame[center[1]][center[0]]
        if (
            selector not in {background, color}
            and counts[selector] == 1
        ):
            selected.append(color)
    if len(objects) < 2 or len(objects) != len(groups) or len(selected) != 1:
        return None
    return ConstellationAlignment(
        tuple(sorted(objects, key=lambda item: item.color)),
        selected[0],
    )
