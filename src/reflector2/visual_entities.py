"""Generic situated figures, relations, and cross-frame correspondence.

This module contains no game, role, color, or action semantics.  It is the
ground visual substrate shared by native R2 perception and prospective
control: stable component descriptions, pair relations, and conservative
structural correspondence across consecutive frames.
"""

from __future__ import annotations

import hashlib
from collections import Counter, deque
from dataclasses import dataclass
from typing import Iterable, Sequence

Point = tuple[int, int]
Grid = tuple[tuple[int, ...], ...]


def _components(points: set[Point]) -> list[set[Point]]:
    output: list[set[Point]] = []
    unseen = set(points)
    while unseen:
        start = min(unseen, key=lambda point: (point[1], point[0]))
        unseen.remove(start)
        queue = deque((start,))
        component = {start}
        while queue:
            x, y = queue.popleft()
            for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    queue.append(neighbor)
        output.append(component)
    return output


def _normalized(points: Iterable[Point]) -> tuple[Point, ...]:
    values = tuple(points)
    min_x = min(x for x, _y in values)
    min_y = min(y for _x, y in values)
    return tuple(sorted((x - min_x, y - min_y) for x, y in values))


def _outline(points: set[Point]) -> str:
    transformed = []
    for transform in (
        lambda x, y: (x, y),
        lambda x, y: (x, -y),
        lambda x, y: (-x, y),
        lambda x, y: (-x, -y),
        lambda x, y: (y, x),
        lambda x, y: (y, -x),
        lambda x, y: (-y, x),
        lambda x, y: (-y, -x),
    ):
        transformed.append(_normalized(transform(x, y) for x, y in points))
    digest = hashlib.sha256(repr(min(transformed)).encode()).hexdigest()[:20]
    return f"outline:{digest}"


@dataclass(frozen=True, slots=True)
class VisualFigure:
    local_ref: str
    outline: str
    area: int
    anchor: Point
    centroid2: Point
    normalized_cells: tuple[Point, ...]
    absolute_cells: tuple[Point, ...]
    interior_pattern: tuple[Point, ...]
    primary_value: int

    @property
    def structural_key(self) -> tuple[object, ...]:
        return (
            self.outline,
            self.area,
            self.normalized_cells,
            self.interior_pattern,
        )

    @property
    def relative_identity(self) -> tuple[object, ...]:
        return self.structural_key, self.anchor


def extract_visual_figures(
    grid: Grid, *, background: int | None = None, maximum: int = 32
) -> tuple[VisualFigure, ...]:
    if not grid or not grid[0]:
        raise ValueError("visual grid must be non-empty")
    counts = Counter(value for row in grid for value in row)
    background_value = (
        max(counts, key=lambda value: (counts[value], -value))
        if background is None
        else int(background)
    )
    foreground = {
        (x, y)
        for y, row in enumerate(grid)
        for x, value in enumerate(row)
        if value != background_value
    }
    output: list[VisualFigure] = []
    for index, cells in enumerate(_components(foreground)[:maximum]):
        min_x = min(x for x, _y in cells)
        min_y = min(y for _x, y in cells)
        normalized = _normalized(cells)
        colors = Counter(grid[y][x] for x, y in cells)
        primary = max(colors, key=lambda value: (colors[value], -value))
        interior = tuple(
            sorted(
                (x - min_x, y - min_y)
                for x, y in cells
                if grid[y][x] != primary
            )
        )
        area = len(cells)
        output.append(
            VisualFigure(
                local_ref=f"f{index:02d}",
                outline=_outline(cells),
                area=area,
                anchor=(min_x, min_y),
                centroid2=(
                    round(2 * sum(x for x, _y in cells) / area),
                    round(2 * sum(y for _x, y in cells) / area),
                ),
                normalized_cells=normalized,
                absolute_cells=tuple(sorted(cells)),
                interior_pattern=interior,
                primary_value=primary,
            )
        )
    return tuple(output)


def pair_relations(
    figures: Sequence[VisualFigure], *, maximum_pairs: int = 128
) -> tuple[tuple[str, str, str], ...]:
    facts: set[tuple[str, str, str]] = set()
    pair_count = 0
    for index, left in enumerate(figures):
        for right in figures[index + 1 :]:
            if pair_count >= maximum_pairs:
                break
            facts.add(
                (
                    "SameOutline" if left.outline == right.outline else "DifferentOutline",
                    left.local_ref,
                    right.local_ref,
                )
            )
            same_interior = left.interior_pattern == right.interior_pattern
            facts.add(
                (
                    "SameInteriorLayout" if same_interior else "DifferentInteriorLayout",
                    left.local_ref,
                    right.local_ref,
                )
            )
            # Backward-compatible native name; both denote the same exact
            # color-layout comparison in the current sensory vocabulary.
            facts.add(
                (
                    "SameInteriorContrast" if same_interior else "DifferentInteriorContrast",
                    left.local_ref,
                    right.local_ref,
                )
            )
            facts.add(
                (
                    "SameArea" if left.area == right.area else "DifferentArea",
                    left.local_ref,
                    right.local_ref,
                )
            )
            if left.centroid2[1] == right.centroid2[1]:
                facts.add(("AlignedHorizontal", left.local_ref, right.local_ref))
            if left.centroid2[0] == right.centroid2[0]:
                facts.add(("AlignedVertical", left.local_ref, right.local_ref))
            distance = min(
                abs(lx - rx) + abs(ly - ry)
                for lx, ly in left.absolute_cells
                for rx, ry in right.absolute_cells
            )
            facts.add(
                ("Touches" if distance == 1 else "Disjoint", left.local_ref, right.local_ref)
            )
            pair_count += 1
        if pair_count >= maximum_pairs:
            break
    return tuple(sorted(facts))


def correspond_figures(
    before: Sequence[VisualFigure], after: Sequence[VisualFigure]
) -> dict[VisualFigure, VisualFigure]:
    """Conservatively match structural peers by minimum displacement."""

    available = list(after)
    output: dict[VisualFigure, VisualFigure] = {}
    for source in sorted(before, key=lambda item: (repr(item.structural_key), item.anchor)):
        compatible = [
            item for item in available if item.structural_key == source.structural_key
        ]
        if not compatible:
            continue
        selected = min(
            compatible,
            key=lambda item: (
                abs(item.anchor[0] - source.anchor[0])
                + abs(item.anchor[1] - source.anchor[1]),
                item.anchor,
            ),
        )
        output[source] = selected
        available.remove(selected)
    return output


def translation_residual(left: VisualFigure, right: VisualFigure) -> int:
    return abs(left.centroid2[0] - right.centroid2[0]) + abs(
        left.centroid2[1] - right.centroid2[1]
    )
