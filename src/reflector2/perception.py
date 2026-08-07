"""Audited generic grid kernels that emit ground relational terms."""

from __future__ import annotations

import hashlib
from collections import Counter, deque
from collections.abc import Sequence
from dataclasses import dataclass

from .store import GroundAtom, TermStore

Grid = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class PerceptionBatch:
    context: str
    facts: tuple[GroundAtom, ...]
    form_terms: tuple[int, ...]
    region_terms: tuple[int, ...]
    outline_terms: tuple[int, ...] = ()
    source: str = "sensor:grid"


def _components(points: set[tuple[int, int]]) -> list[set[tuple[int, int]]]:
    output: list[set[tuple[int, int]]] = []
    unseen = set(points)
    while unseen:
        start = min(unseen, key=lambda point: (point[1], point[0]))
        unseen.remove(start)
        queue = deque([start])
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


def _normalized(points: set[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    min_x = min(x for x, _y in points)
    min_y = min(y for _x, y in points)
    return tuple(sorted((x - min_x, y - min_y) for x, y in points))


def _fingerprint(points: set[tuple[int, int]]) -> str:
    encoded = repr(_normalized(points)).encode("utf-8")
    return "form:" + hashlib.sha256(encoded).hexdigest()[:20]


def _outline_fingerprint(points: set[tuple[int, int]]) -> str:
    # Shape correspondence is invariant to the dihedral symmetries of the
    # grid: translation, quarter-turn rotation, and reflection. The exact
    # colored regions remain separately represented above.
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
        transformed.append(_normalized({transform(x, y) for x, y in points}))
    encoded = repr(min(transformed)).encode("utf-8")
    return "outline:" + hashlib.sha256(encoded).hexdigest()[:20]


MAX_SAME_OUTLINE_PAIRS = 128


def perceive_grid(
    store: TermStore,
    frame: Sequence[Sequence[int]],
    context: str,
    *,
    background: int | None = None,
) -> PerceptionBatch:
    """Emit generic facts; no branch recognizes a named form or task object."""

    grid: Grid = tuple(tuple(int(value) for value in row) for row in frame)
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise ValueError("frame must be a non-empty rectangle")
    height, width = len(grid), len(grid[0])
    counts = Counter(value for row in grid for value in row)
    # Background identity is sensory-channel configuration, not inferred object
    # semantics. Modal inference is a convenience fallback and is traceable by
    # the caller; the benchmark supplies its declared value explicitly.
    background_value = (
        max(counts, key=lambda value: (counts[value], -value))
        if background is None
        else int(background)
    )

    foreground_by_value: dict[int, set[tuple[int, int]]] = {}
    background_points: set[tuple[int, int]] = set()
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            if value == background_value:
                background_points.add((x, y))
            else:
                foreground_by_value.setdefault(value, set()).add((x, y))

    enclosed: list[set[tuple[int, int]]] = []
    for component in _components(background_points):
        if not any(x in (0, width - 1) or y in (0, height - 1) for x, y in component):
            enclosed.append(component)

    facts: list[GroundAtom] = []
    form_terms: list[int] = []
    region_terms: list[int] = []
    outline_terms: list[int] = []
    region_index = 0
    all_regions: list[tuple[int, int, int, set[tuple[int, int]]]] = []
    for value, points in sorted(foreground_by_value.items()):
        for component in _components(points):
            region = store.intern_symbol(f"region:{context}:{region_index}")
            ordinal = region_index
            region_index += 1
            all_regions.append((ordinal, region, value, component))

    hole_ordinals = {frozenset(hole): index for index, hole in enumerate(enclosed)}

    for region_ordinal, region, value, component in all_regions:
        owned_holes = []
        for hole in enclosed:
            boundary_neighbors = {
                neighbor
                for x, y in hole
                for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1))
                if neighbor not in hole
            }
            if boundary_neighbors and boundary_neighbors <= component:
                owned_holes.append(hole)
        outer = set(component)
        for hole in owned_holes:
            outer.update(hole)
        form = store.intern_symbol(_fingerprint(outer))
        form_terms.append(form)
        region_terms.append(region)
        facts.extend(
            [
                (store.intern_symbol("Kind"), (region, store.intern_symbol("Region"))),
                (store.intern_symbol("Connected"), (region,)),
                (store.intern_symbol("Color"), (region, store.intern_symbol(value))),
                (store.intern_symbol("Form"), (region, form)),
                (store.intern_symbol("EnclosureCount"), (region, store.intern_symbol(len(owned_holes)))),
            ]
        )
        for hole in owned_holes:
            hole_index = hole_ordinals[frozenset(hole)]
            hole_term = store.intern_symbol(f"enclosed:{context}:{hole_index}")
            facts.extend(
                [
                    (store.intern_symbol("Kind"), (hole_term, store.intern_symbol("EnclosedRegion"))),
                    (store.intern_symbol("Enclosed"), (hole_term,)),
                    (store.intern_symbol("Inside"), (hole_term, region)),
                    (store.intern_symbol("Count"), (hole_term, store.intern_symbol(len(hole)))),
                ]
            )

        min_x = min(x for x, _y in component)
        min_y = min(y for _x, y in component)
        for ordinal, (x, y) in enumerate(sorted(component, key=lambda point: (point[1], point[0]))):
            cell = store.intern_symbol(f"cell:{context}:{region_ordinal}:{ordinal}")
            facts.extend(
                [
                    (store.intern_symbol("Kind"), (cell, store.intern_symbol("Cell"))),
                    (store.intern_symbol("Value"), (cell, store.intern_symbol(value))),
                    (store.intern_symbol("At"), (cell, store.intern_symbol(x - min_x), store.intern_symbol(y - min_y))),
                    (store.intern_symbol("PartOf"), (cell, region)),
                ]
            )

    # A figure is a color-agnostic connected foreground component. It preserves
    # a common outline across recoloring or internally contrasting cells, while
    # color-specific regions above remain available as a finer description.
    figure_by_outline: dict[int, list[tuple[int, int]]] = {}
    all_foreground = {
        (x, y)
        for y, row in enumerate(grid)
        for x, value in enumerate(row)
        if value != background_value
    }
    for figure_index, component in enumerate(_components(all_foreground)):
        figure = store.intern_symbol(f"figure:{context}:{figure_index}")
        outline = store.intern_symbol(_outline_fingerprint(component))
        outline_terms.append(outline)
        values = Counter(grid[y][x] for x, y in component)
        primary_value = max(values, key=lambda value: (values[value], -value))
        contrast_count = len(component) - values[primary_value]
        facts.extend(
            [
                (store.intern_symbol("Kind"), (figure, store.intern_symbol("Figure"))),
                (store.intern_symbol("OutlineForm"), (figure, outline)),
                (
                    store.intern_symbol("InteriorContrastCount"),
                    (figure, store.intern_symbol(contrast_count)),
                ),
            ]
        )
        for _ordinal, region, _value, region_component in all_regions:
            if region_component <= component:
                facts.append((store.intern_symbol("Contains"), (figure, region)))
        figure_by_outline.setdefault(outline, []).append((figure, contrast_count))

    pair_count = 0
    for outline in sorted(figure_by_outline):
        figures = sorted(figure_by_outline[outline])
        for left_index, (left, left_contrast) in enumerate(figures):
            for right, right_contrast in figures[left_index + 1 :]:
                if pair_count >= MAX_SAME_OUTLINE_PAIRS:
                    break
                facts.append((store.intern_symbol("SameOutline"), (left, right)))
                relation = (
                    "SameInteriorContrast"
                    if left_contrast == right_contrast
                    else "DifferentInteriorContrast"
                )
                facts.append((store.intern_symbol(relation), (left, right)))
                pair_count += 1
            if pair_count >= MAX_SAME_OUTLINE_PAIRS:
                break
        if pair_count >= MAX_SAME_OUTLINE_PAIRS:
            break

    return PerceptionBatch(
        context, tuple(facts), tuple(form_terms), tuple(region_terms), tuple(outline_terms)
    )
