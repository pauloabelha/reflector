"""Deterministic object extraction, identity tracking, and event detection."""

from __future__ import annotations

import hashlib
from collections import Counter, deque
from typing import Iterable

from .symbolic import (
    Atom,
    Event,
    ObjectState,
    Observation,
    Scene,
    Transition,
    canonical_atoms,
)


class SceneTracker:
    """Convert grids into symbolic scenes while preserving object identity."""

    MAX_RELATION_PAIRS = 2048

    def __init__(self) -> None:
        self._index = 0
        self._next_object = 1
        self._previous: Scene | None = None

    @property
    def previous(self) -> Scene | None:
        return self._previous

    def perceive(self, observation: Observation) -> tuple[Scene, tuple[Event, ...]]:
        components = self._components(observation.frame)
        objects = self._assign_identities(components)
        facts = self._facts(observation, objects)
        scene = Scene(
            index=self._index,
            state=observation.state,
            levels_completed=observation.levels_completed,
            available_actions=observation.available_actions,
            objects=objects,
            facts=facts,
            frame_digest=self._digest(observation.frame),
        )
        events = self._events(self._previous, scene)
        self._previous = scene
        self._index += 1
        return scene, events

    def transition(
        self,
        before: Scene,
        after: Scene,
        action_id: int,
        action_data: tuple[tuple[str, int], ...],
        events: tuple[Event, ...],
    ) -> Transition:
        return Transition(
            before_index=before.index,
            after_index=after.index,
            context=before.context(),
            action_id=action_id,
            action_data=action_data,
            result=events or (Event("no_observed_change"),),
        )

    def _components(
        self, frame: tuple[tuple[int, ...], ...]
    ) -> tuple[ObjectState, ...]:
        if not frame or not frame[0]:
            return ()
        counts = Counter(cell for row in frame for cell in row)
        background = max(counts, key=lambda color: (counts[color], -color))
        height, width = len(frame), len(frame[0])
        seen: set[tuple[int, int]] = set()
        output: list[ObjectState] = []
        for y in range(height):
            for x in range(width):
                color = frame[y][x]
                if color == background or (x, y) in seen:
                    continue
                queue = deque([(x, y)])
                seen.add((x, y))
                points: list[tuple[int, int]] = []
                while queue:
                    px, py = queue.popleft()
                    points.append((px, py))
                    for nx, ny in (
                        (px - 1, py),
                        (px + 1, py),
                        (px, py - 1),
                        (px, py + 1),
                    ):
                        if (
                            0 <= nx < width
                            and 0 <= ny < height
                            and (nx, ny) not in seen
                            and frame[ny][nx] == color
                        ):
                            seen.add((nx, ny))
                            queue.append((nx, ny))
                xs, ys = zip(*points)
                output.append(
                    ObjectState(
                        object_id="",
                        color=color,
                        area=len(points),
                        bbox=(min(xs), min(ys), max(xs), max(ys)),
                        centroid=(
                            sum(xs) // len(points),
                            sum(ys) // len(points),
                        ),
                        shape=tuple(
                            sorted(
                                (px - min(xs), py - min(ys))
                                for px, py in points
                            )
                        ),
                    )
                )
        return tuple(
            sorted(output, key=lambda obj: (obj.color, obj.centroid, obj.area))
        )

    def _assign_identities(
        self, components: tuple[ObjectState, ...]
    ) -> tuple[ObjectState, ...]:
        previous = list(self._previous.objects if self._previous else ())
        unused = set(range(len(previous)))
        assigned: list[ObjectState] = []
        for component in components:
            matches = [
                (
                    self._distance(component, previous[index]),
                    abs(component.area - previous[index].area),
                    index,
                )
                for index in unused
                if component.color == previous[index].color
            ]
            if matches:
                _, _, match = min(matches)
                unused.remove(match)
                object_id = previous[match].object_id
            else:
                object_id = f"o{self._next_object}"
                self._next_object += 1
            assigned.append(
                ObjectState(
                    object_id=object_id,
                    color=component.color,
                    area=component.area,
                    bbox=component.bbox,
                    centroid=component.centroid,
                    shape=component.shape,
                )
            )
        return tuple(sorted(assigned, key=lambda obj: obj.object_id))

    @staticmethod
    def _distance(left: ObjectState, right: ObjectState) -> int:
        return abs(left.centroid[0] - right.centroid[0]) + abs(
            left.centroid[1] - right.centroid[1]
        )

    @staticmethod
    def _facts(
        observation: Observation, objects: tuple[ObjectState, ...]
    ) -> tuple[Atom, ...]:
        facts: list[Atom] = [
            Atom("state", (observation.state,)),
            Atom("object_count", (str(len(objects)),)),
            Atom(
                "frame_bounds",
                (
                    "0",
                    "0",
                    str(len(observation.frame[0]) - 1)
                    if observation.frame and observation.frame[0]
                    else "-1",
                    str(len(observation.frame) - 1),
                ),
            ),
        ]
        facts.extend(
            Atom("action_available", (str(action),))
            for action in observation.available_actions
        )
        facts.extend(
            Atom("color_present", (str(color),))
            for color in sorted({obj.color for obj in objects})
        )
        for obj in objects:
            facts.extend(
                (
                    Atom("object", (obj.object_id,)),
                    Atom("color", (obj.object_id, str(obj.color))),
                    Atom("area", (obj.object_id, str(obj.area))),
                    Atom(
                        "centroid",
                        (obj.object_id, str(obj.centroid[0]), str(obj.centroid[1])),
                    ),
                    Atom(
                        "shape_size",
                        (
                            obj.object_id,
                            str(obj.bbox[2] - obj.bbox[0] + 1),
                            str(obj.bbox[3] - obj.bbox[1] + 1),
                        ),
                    ),
                )
            )
        relation_pairs = 0
        for index, left in enumerate(objects):
            for right in objects[index + 1 :]:
                if relation_pairs >= SceneTracker.MAX_RELATION_PAIRS:
                    break
                relation_pairs += 1
                left_id, right_id = left.object_id, right.object_id
                if left.bbox[2] < right.bbox[0]:
                    facts.append(Atom("left_of", (left_id, right_id)))
                elif right.bbox[2] < left.bbox[0]:
                    facts.append(Atom("left_of", (right_id, left_id)))
                if left.bbox[3] < right.bbox[1]:
                    facts.append(Atom("above", (left_id, right_id)))
                elif right.bbox[3] < left.bbox[1]:
                    facts.append(Atom("above", (right_id, left_id)))
                if left.centroid[0] == right.centroid[0]:
                    facts.append(Atom("aligned_x", (left_id, right_id)))
                if left.centroid[1] == right.centroid[1]:
                    facts.append(Atom("aligned_y", (left_id, right_id)))
                horizontal_gap = max(
                    0,
                    max(left.bbox[0], right.bbox[0])
                    - min(left.bbox[2], right.bbox[2])
                    - 1,
                )
                vertical_gap = max(
                    0,
                    max(left.bbox[1], right.bbox[1])
                    - min(left.bbox[3], right.bbox[3])
                    - 1,
                )
                if horizontal_gap + vertical_gap == 0:
                    facts.append(Atom("touching", tuple(sorted((left_id, right_id)))))
        return canonical_atoms(facts)

    @staticmethod
    def _events(before: Scene | None, after: Scene) -> tuple[Event, ...]:
        if before is None:
            return ()
        events: list[Event] = []
        old = {obj.object_id: obj for obj in before.objects}
        new = {obj.object_id: obj for obj in after.objects}
        for object_id in sorted(old.keys() - new.keys()):
            events.append(Event("object_disappeared", object_id))
        for object_id in sorted(new.keys() - old.keys()):
            events.append(Event("object_appeared", object_id))
        for object_id in sorted(old.keys() & new.keys()):
            left, right = old[object_id], new[object_id]
            dx = right.centroid[0] - left.centroid[0]
            dy = right.centroid[1] - left.centroid[1]
            if dx or dy:
                events.append(Event("object_moved", object_id, (str(dx), str(dy))))
            if left.area != right.area:
                events.append(
                    Event(
                        "area_changed",
                        object_id,
                        (str(left.area), str(right.area)),
                    )
                )
            rotation = SceneTracker._rotation(left.shape, right.shape)
            if rotation is not None:
                events.append(Event(f"rotated_{rotation}", object_id))
        if after.levels_completed > before.levels_completed:
            events.append(
                Event(
                    "level_advanced",
                    "game",
                    (str(before.levels_completed), str(after.levels_completed)),
                )
            )
        if after.state != before.state:
            events.append(Event("state_changed", "game", (before.state, after.state)))
        if after.frame_digest != before.frame_digest:
            events.append(Event("frame_changed"))
        return tuple(sorted(set(events)))

    @staticmethod
    def _rotation(
        before: tuple[tuple[int, int], ...],
        after: tuple[tuple[int, int], ...],
    ) -> int | None:
        if not before or before == after or len(before) != len(after):
            return None
        transformed = before
        for quarter_turn in range(1, 4):
            height = max(y for _x, y in transformed) + 1
            transformed = tuple(
                sorted((height - 1 - y, x) for x, y in transformed)
            )
            min_x = min(x for x, _y in transformed)
            min_y = min(y for _x, y in transformed)
            transformed = tuple(
                sorted((x - min_x, y - min_y) for x, y in transformed)
            )
            if transformed == after:
                return quarter_turn * 90
        return None

    @staticmethod
    def _digest(frame: Iterable[Iterable[int]]) -> str:
        payload = bytes(cell for row in frame for cell in row)
        return hashlib.sha256(payload).hexdigest()[:16]
