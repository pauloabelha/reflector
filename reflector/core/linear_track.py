"""Ground compact markers moving along a one-dimensional colored track."""

from __future__ import annotations

from dataclasses import dataclass

type Frame = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class TrackState:
    target: tuple[int, int]
    marker: tuple[int, int]

    @property
    def distance(self) -> int:
        return abs(self.target[0] - self.marker[0]) + abs(
            self.target[1] - self.marker[1]
        )


@dataclass(frozen=True, slots=True)
class _Component:
    color: int
    points: frozenset[tuple[int, int]]

    @property
    def bounds(self) -> tuple[int, int, int, int]:
        xs = tuple(point[0] for point in self.points)
        ys = tuple(point[1] for point in self.points)
        return min(xs), min(ys), max(xs), max(ys)

    @property
    def center(self) -> tuple[int, int]:
        left, top, right, bottom = self.bounds
        return (left + right) // 2, (top + bottom) // 2


def _components(frame: Frame) -> tuple[_Component, ...]:
    if not frame or not frame[0]:
        return ()
    height = len(frame)
    width = len(frame[0])
    seen: set[tuple[int, int]] = set()
    output: list[_Component] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen:
                continue
            color = frame[y][x]
            frontier = [(x, y)]
            seen.add((x, y))
            points: set[tuple[int, int]] = set()
            while frontier:
                point = frontier.pop()
                points.add(point)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    neighbor = point[0] + dx, point[1] + dy
                    if (
                        0 <= neighbor[0] < width
                        and 0 <= neighbor[1] < height
                        and neighbor not in seen
                        and frame[neighbor[1]][neighbor[0]] == color
                    ):
                        seen.add(neighbor)
                        frontier.append(neighbor)
            if 4 <= len(points) <= 256:
                output.append(_Component(color, frozenset(points)))
    return tuple(output)


def infer_linear_track(frame: Frame) -> TrackState | None:
    """Return a unique marker/endpoint pair supported by an elongated track."""

    components = _components(frame)
    candidates: set[TrackState] = set()
    for target in components:
        tx1, ty1, tx2, ty2 = target.bounds
        for marker in components:
            if (
                marker is target
                or marker.color != target.color
                or len(marker.points) >= len(target.points)
            ):
                continue
            mx1, my1, mx2, my2 = marker.bounds
            horizontal = max(ty1, my1) <= min(ty2, my2)
            vertical = max(tx1, mx1) <= min(tx2, mx2)
            if horizontal == vertical:
                continue
            for track in components:
                if track.color == target.color:
                    continue
                x1, y1, x2, y2 = track.bounds
                if horizontal:
                    if x2 - x1 < 3 * max(1, y2 - y1):
                        continue
                    if not (
                        y1 <= target.center[1] <= y2
                        and y1 <= marker.center[1] <= y2
                        and min(target.center[0], marker.center[0]) <= x2
                        and max(target.center[0], marker.center[0]) >= x1
                    ):
                        continue
                else:
                    if y2 - y1 < 3 * max(1, x2 - x1):
                        continue
                    if not (
                        x1 <= target.center[0] <= x2
                        and x1 <= marker.center[0] <= x2
                        and min(target.center[1], marker.center[1]) <= y2
                        and max(target.center[1], marker.center[1]) >= y1
                    ):
                        continue
                candidates.add(TrackState(target.center, marker.center))
    if len(candidates) == 1:
        return next(iter(candidates))
    targets = {candidate.target for candidate in candidates}
    marker_xs = {candidate.marker[0] for candidate in candidates}
    marker_ys = {candidate.marker[1] for candidate in candidates}
    if (
        len(targets) == 1
        and max(marker_xs) - min(marker_xs) <= 4
        and max(marker_ys) - min(marker_ys) <= 4
    ):
        return TrackState(
            next(iter(targets)),
            (
                sum(marker_xs) // len(marker_xs),
                sum(marker_ys) // len(marker_ys),
            ),
        )
    return None
