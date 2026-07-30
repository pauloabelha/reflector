"""Bounded symbolic inference and planning for projected token permutations.

The runtime-facing types in this module contain only episode-grounded perceptual
roles.  They do not name games, colors, actions, or absolute solution paths.
An effect is admitted only when a before/after observation exactly supports a
successor permutation over the declared conserved token-centroid domain.
"""

from __future__ import annotations

import hashlib
import itertools
import math
from collections import Counter, deque
from dataclasses import dataclass, replace
from typing import Literal, Self

type Point = tuple[int, int]
type Frame = tuple[tuple[int, ...], ...]
type ProjectedState = tuple[tuple[int, ...], ...]
type Axis = Literal["horizontal", "vertical", "path"]


@dataclass(frozen=True, slots=True)
class PermutationBounds:
    """Deterministic inference and search limits."""

    min_segment_length: int = 3
    min_segment_count: int = 2
    max_segments: int = 6
    max_slots: int = 64
    max_cycle_orderings: int = 256
    max_generators: int = 8
    max_projected_states: int = 4096
    max_plan_depth: int = 32


@dataclass(frozen=True, slots=True)
class MarkerTarget:
    """A percept-relative request to place one token color at one marker."""

    point: Point
    color: int


@dataclass(frozen=True, slots=True)
class PermutationGenerator:
    """One evidenced permutation effect and its grounded controller roles.

    ``successor[index]`` is the destination slot index for the token currently
    at ``slots[index]``.  Controllers are evidence groundings, not constants in
    the symbolic operator.
    """

    effect_id: str
    slots: tuple[Point, ...]
    successor: tuple[int, ...]
    controllers: tuple[Point, ...]
    support: int
    axis: Axis
    pitch: int
    segment_count: int

    @classmethod
    def create(
        cls,
        *,
        slots: tuple[Point, ...],
        successor: tuple[int, ...],
        controller: Point,
        axis: Axis,
        pitch: int,
        segment_count: int,
    ) -> Self:
        """Construct a canonical, content-free generator."""

        if (
            not slots
            or len(slots) != len(successor)
            or len(set(slots)) != len(slots)
            or sorted(successor) != list(range(len(slots)))
        ):
            raise ValueError("successor must be a permutation of unique slots")
        if pitch < 1 or segment_count < 1:
            raise ValueError("pitch and segment_count must be positive")
        digest = hashlib.sha256(
            repr(("permutation-transport-v1", slots, successor)).encode()
        ).hexdigest()[:16]
        return cls(
            effect_id=f"permutation-{digest}",
            slots=slots,
            successor=successor,
            controllers=(controller,),
            support=1,
            axis=axis,
            pitch=pitch,
            segment_count=segment_count,
        )

    def destination(self, point: Point) -> Point:
        """Apply this generator to one percept-relative token position."""

        try:
            source_index = self.slots.index(point)
        except ValueError:
            return point
        return self.slots[self.successor[source_index]]

    def apply_points(self, points: tuple[Point, ...]) -> tuple[Point, ...]:
        """Apply the generator to indistinguishable projected token positions."""

        return tuple(sorted(self.destination(point) for point in points))


@dataclass(frozen=True, slots=True)
class PermutationSystem:
    """A deterministic collection of multiple observed generator families."""

    generators: tuple[PermutationGenerator, ...]

    @classmethod
    def create(
        cls,
        generators: tuple[PermutationGenerator, ...],
        *,
        bounds: PermutationBounds = PermutationBounds(),
    ) -> Self:
        """Validate and deterministically order an episode's generators."""

        if len(generators) > bounds.max_generators:
            raise ValueError("generator bound exceeded")
        ordered = tuple(
            sorted(
                generators,
                key=lambda item: (
                    item.effect_id,
                    item.controllers,
                    item.slots,
                ),
            )
        )
        if len({item.effect_id for item in ordered}) != len(ordered):
            raise ValueError("effect identifiers must be unique")
        all_slots = {point for item in ordered for point in item.slots}
        if len(all_slots) > bounds.max_slots:
            raise ValueError("slot bound exceeded")
        return cls(generators=ordered)

    @property
    def all_slots(self) -> tuple[Point, ...]:
        """Return the union lattice used by projected planning."""

        return tuple(
            sorted({point for item in self.generators for point in item.slots})
        )

    @property
    def shared_slots(self) -> tuple[Point, ...]:
        """Return slots shared by distinct permutation domains.

        Inverse directions over the same domain count once, so this reports
        junctions between transport families rather than every bidirectional
        slot.
        """

        domains = tuple({frozenset(item.slots) for item in self.generators})
        counts: Counter[Point] = Counter()
        for domain in domains:
            counts.update(domain)
        return tuple(sorted(point for point, count in counts.items() if count > 1))

    def generator(self, effect_id: str) -> PermutationGenerator:
        """Resolve a typed plan step to its evidenced generator."""

        for item in self.generators:
            if item.effect_id == effect_id:
                return item
        raise KeyError(effect_id)

    def apply_state(
        self,
        state: ProjectedState,
        effect_id: str,
    ) -> ProjectedState:
        """Apply one generator to marker-color position groups."""

        generator = self.generator(effect_id)
        slots = self.all_slots
        point_state = tuple(tuple(slots[index] for index in group) for group in state)
        updated = tuple(generator.apply_points(group) for group in point_state)
        indexes = {point: index for index, point in enumerate(slots)}
        return tuple(tuple(indexes[point] for point in group) for group in updated)


@dataclass(frozen=True, slots=True)
class PermutationPlan:
    """A bounded typed plan over generator identities."""

    generator_ids: tuple[str, ...]
    explored_states: int
    initial_state: ProjectedState
    goal_state: ProjectedState


def merge_generator_evidence(
    generators: tuple[PermutationGenerator, ...],
    evidence: PermutationGenerator,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> tuple[PermutationGenerator, ...]:
    """Merge a repeated controller/effect observation without conflating effects."""

    output = list(generators)
    for index, item in enumerate(output):
        if item.slots != evidence.slots or item.successor != evidence.successor:
            continue
        output[index] = replace(
            item,
            controllers=tuple(sorted(set((*item.controllers, *evidence.controllers)))),
            support=item.support + evidence.support,
        )
        return PermutationSystem.create(
            tuple(output),
            bounds=bounds,
        ).generators
    output.append(evidence)
    return PermutationSystem.create(tuple(output), bounds=bounds).generators


def infer_segmented_permutations(
    before: Frame,
    after: Frame,
    token_positions: tuple[Point, ...],
    controller: Point,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> tuple[PermutationGenerator, ...]:
    """Infer exact successor maps over disconnected equal-pitch segments.

    Multiple results mean that the observation is underdetermined.  A caller
    should promote only a unique result, or retain the candidates until another
    observation eliminates the ambiguity.
    """

    dimensions = _shared_dimensions(before, after)
    if dimensions is None:
        return ()
    width, height = dimensions
    points = tuple(sorted(set(token_positions)))
    if (
        len(points) != len(token_positions)
        or len(points) > bounds.max_slots
        or any(not (0 <= x < width and 0 <= y < height) for x, y in points)
    ):
        return ()
    changed = {
        point for point in points if _value(before, point) != _value(after, point)
    }
    if not changed:
        return ()

    candidates: dict[
        tuple[tuple[Point, ...], tuple[int, ...]],
        PermutationGenerator,
    ] = {}
    for axis in ("horizontal", "vertical"):
        segmented = _equal_pitch_segments(
            points,
            changed,
            axis=axis,
            bounds=bounds,
        )
        if segmented is None:
            continue
        pitch, raw_segments = segmented
        for direction in (1, -1):
            oriented: list[tuple[Point, ...]] = []
            valid = True
            for segment in raw_segments:
                ordered = segment if direction > 0 else tuple(reversed(segment))
                if not all(
                    _value(after, destination) == _value(before, source)
                    for source, destination in zip(ordered, ordered[1:])
                ):
                    valid = False
                    break
                oriented.append(ordered)
            if not valid:
                continue
            if math.factorial(len(oriented) - 1) > bounds.max_cycle_orderings:
                continue
            first = min(oriented)
            remaining = tuple(item for item in oriented if item != first)
            for tail in itertools.permutations(remaining):
                ordered_segments = (first, *tail)
                track = tuple(
                    point for segment in ordered_segments for point in segment
                )
                if not _predicts_cycle(before, after, track):
                    continue
                generator = _generator_from_track(
                    track,
                    controller=controller,
                    axis=axis,
                    pitch=pitch,
                    segment_count=len(ordered_segments),
                )
                candidates[(generator.slots, generator.successor)] = generator
                if len(candidates) > bounds.max_cycle_orderings:
                    return ()
    return tuple(
        sorted(
            candidates.values(),
            key=lambda item: (
                item.effect_id,
                item.axis,
                item.controllers,
            ),
        )
    )


def infer_path_cycle_permutations(
    before: Frame,
    after: Frame,
    token_positions: tuple[Point, ...],
    controller: Point,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> tuple[PermutationGenerator, ...]:
    """Infer rotations over intervals of one uniform simple rectilinear path.

    The exact boundary is the declared token-centroid domain: every changed
    token must belong to the inferred interval and every value on that interval
    must match one cyclic successor step.  Unrelated rendered UI is outside this
    projected operator.
    """

    dimensions = _shared_dimensions(before, after)
    if dimensions is None:
        return ()
    width, height = dimensions
    points = tuple(sorted(set(token_positions)))
    if (
        len(points) != len(token_positions)
        or len(points) < bounds.min_segment_length
        or len(points) > bounds.max_slots
        or any(not (0 <= x < width and 0 <= y < height) for x, y in points)
    ):
        return ()
    changed = {
        point for point in points if _value(before, point) != _value(after, point)
    }
    if not changed:
        return ()
    ordered = _rectilinear_path(points)
    if ordered is None:
        return ()

    candidates: dict[
        tuple[tuple[Point, ...], tuple[int, ...]],
        PermutationGenerator,
    ] = {}
    for start in range(len(ordered)):
        for stop in range(start + bounds.min_segment_length, len(ordered) + 1):
            segment = ordered[start:stop]
            segment_set = set(segment)
            if not changed.issubset(segment_set):
                continue
            if any(
                _value(before, point) != _value(after, point)
                for point in points
                if point not in segment_set
            ):
                continue
            for track in (segment, tuple(reversed(segment))):
                if not _predicts_cycle(before, after, track):
                    continue
                generator = _generator_from_track(
                    track,
                    controller=controller,
                    axis="path",
                    pitch=_path_pitch(track),
                    segment_count=1,
                )
                candidates[(generator.slots, generator.successor)] = generator
                if len(candidates) > bounds.max_cycle_orderings:
                    return ()
    return tuple(
        sorted(
            candidates.values(),
            key=lambda item: (item.effect_id, item.controllers),
        )
    )


def plan_marker_transport(
    frame: Frame,
    token_positions: tuple[Point, ...],
    targets: tuple[MarkerTarget, ...],
    system: PermutationSystem,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> PermutationPlan | None:
    """BFS over only the positions of marker-matched token colors."""

    dimensions = _shared_dimensions(frame, frame)
    if dimensions is None or not targets or not system.generators:
        return None
    width, height = dimensions
    points = tuple(sorted(set(token_positions)))
    if (
        len(points) != len(token_positions)
        or len(points) > bounds.max_slots
        or any(not (0 <= x < width and 0 <= y < height) for x, y in points)
    ):
        return None
    slots = system.all_slots
    slot_set = set(slots)
    if not slot_set.issubset(points):
        return None
    indexes = {point: index for index, point in enumerate(slots)}
    targets_by_color: dict[int, list[Point]] = {}
    for target in targets:
        if target.point not in indexes:
            return None
        targets_by_color.setdefault(target.color, []).append(target.point)

    initial_groups: list[tuple[int, ...]] = []
    goal_groups: list[tuple[int, ...]] = []
    for color in sorted(targets_by_color):
        current = tuple(
            indexes[point] for point in slots if _value(frame, point) == color
        )
        color_goal = tuple(sorted(indexes[point] for point in targets_by_color[color]))
        if len(current) != len(color_goal):
            return None
        initial_groups.append(tuple(sorted(current)))
        goal_groups.append(color_goal)
    initial = tuple(initial_groups)
    goal_state = tuple(goal_groups)
    if initial == goal_state:
        return PermutationPlan(
            generator_ids=(),
            explored_states=0,
            initial_state=initial,
            goal_state=goal_state,
        )

    queue: deque[tuple[ProjectedState, tuple[str, ...]]] = deque([(initial, ())])
    seen = {initial}
    explored = 0
    ordered_generators = system.generators
    while queue and explored < bounds.max_projected_states:
        state, plan = queue.popleft()
        explored += 1
        if len(plan) >= bounds.max_plan_depth:
            continue
        for generator in ordered_generators:
            successor = system.apply_state(state, generator.effect_id)
            if successor == state or successor in seen:
                continue
            successor_plan = (*plan, generator.effect_id)
            if successor == goal_state:
                return PermutationPlan(
                    generator_ids=successor_plan,
                    explored_states=explored,
                    initial_state=initial,
                    goal_state=goal_state,
                )
            if len(seen) >= bounds.max_projected_states:
                return None
            seen.add(successor)
            queue.append((successor, successor_plan))
    return None


def _shared_dimensions(before: Frame, after: Frame) -> tuple[int, int] | None:
    if not before or not after or len(before) != len(after):
        return None
    width = len(before[0])
    if (
        width == 0
        or width != len(after[0])
        or any(len(row) != width for row in before)
        or any(len(row) != width for row in after)
    ):
        return None
    return width, len(before)


def _value(frame: Frame, point: Point) -> int:
    return frame[point[1]][point[0]]


def _equal_pitch_segments(
    points: tuple[Point, ...],
    changed: set[Point],
    *,
    axis: Axis,
    bounds: PermutationBounds,
) -> tuple[int, tuple[tuple[Point, ...], ...]] | None:
    groups: dict[int, list[Point]] = {}
    for point in points:
        key = point[1] if axis == "horizontal" else point[0]
        groups.setdefault(key, []).append(point)
    active = {
        key: sorted(
            group,
            key=lambda point: point[0] if axis == "horizontal" else point[1],
        )
        for key, group in groups.items()
        if any(point in changed for point in group)
    }
    differences: Counter[int] = Counter()
    for group in active.values():
        coordinates = [
            point[0] if axis == "horizontal" else point[1] for point in group
        ]
        differences.update(
            right - left
            for left, right in zip(coordinates, coordinates[1:])
            if right > left
        )
    if not differences:
        return None
    pitch = max(
        differences.items(),
        key=lambda item: (item[1], -item[0]),
    )[0]
    segments: list[tuple[Point, ...]] = []
    for group in active.values():
        run: list[Point] = []
        previous_coordinate: int | None = None
        for point in group:
            coordinate = point[0] if axis == "horizontal" else point[1]
            if (
                previous_coordinate is not None
                and coordinate - previous_coordinate != pitch
            ):
                if len(run) >= bounds.min_segment_length and any(
                    item in changed for item in run
                ):
                    segments.append(tuple(run))
                run = []
            run.append(point)
            previous_coordinate = coordinate
        if len(run) >= bounds.min_segment_length and any(
            item in changed for item in run
        ):
            segments.append(tuple(run))
    segments.sort()
    covered = {point for segment in segments for point in segment}
    if (
        not changed.issubset(covered)
        or not bounds.min_segment_count <= len(segments) <= bounds.max_segments
    ):
        return None
    return pitch, tuple(segments)


def _predicts_cycle(before: Frame, after: Frame, track: tuple[Point, ...]) -> bool:
    return all(
        _value(after, track[(index + 1) % len(track)]) == _value(before, source)
        for index, source in enumerate(track)
    )


def _rectilinear_path(points: tuple[Point, ...]) -> tuple[Point, ...] | None:
    """Return the canonical ordering of one uniform rectilinear path."""

    pitch = _path_pitch(points)
    if pitch < 1:
        return None
    point_set = set(points)
    neighbors = {
        point: tuple(
            sorted(
                candidate
                for candidate in (
                    (point[0] - pitch, point[1]),
                    (point[0] + pitch, point[1]),
                    (point[0], point[1] - pitch),
                    (point[0], point[1] + pitch),
                )
                if candidate in point_set
            )
        )
        for point in points
    }
    if any(len(items) > 2 for items in neighbors.values()):
        return None
    endpoints = tuple(
        sorted(point for point, items in neighbors.items() if len(items) == 1)
    )
    if len(endpoints) != 2:
        return None
    ordered = [endpoints[0]]
    previous: Point | None = None
    while len(ordered) < len(points):
        candidates = tuple(
            item for item in neighbors[ordered[-1]] if item != previous
        )
        if len(candidates) != 1 or candidates[0] in ordered:
            return None
        previous, current = ordered[-1], candidates[0]
        ordered.append(current)
    if set(ordered) != point_set:
        return None
    return tuple(ordered)


def _path_pitch(points: tuple[Point, ...]) -> int:
    """Return the greatest shared axial spacing of a rectilinear slot set."""

    differences = [
        difference
        for index, left in enumerate(points)
        for right in points[index + 1 :]
        for difference in (
            abs(right[0] - left[0]) if right[1] == left[1] else 0,
            abs(right[1] - left[1]) if right[0] == left[0] else 0,
        )
        if difference > 0
    ]
    if not differences:
        return 0
    pitch = differences[0]
    for difference in differences[1:]:
        pitch = math.gcd(pitch, difference)
    return pitch


def _generator_from_track(
    track: tuple[Point, ...],
    *,
    controller: Point,
    axis: Axis,
    pitch: int,
    segment_count: int,
) -> PermutationGenerator:
    slots = tuple(sorted(track))
    indexes = {point: index for index, point in enumerate(slots)}
    destinations = {
        source: track[(index + 1) % len(track)] for index, source in enumerate(track)
    }
    successor = tuple(indexes[destinations[point]] for point in slots)
    return PermutationGenerator.create(
        slots=slots,
        successor=successor,
        controller=controller,
        axis=axis,
        pitch=pitch,
        segment_count=segment_count,
    )
