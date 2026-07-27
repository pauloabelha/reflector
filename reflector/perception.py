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
                )
            )
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
    def _digest(frame: Iterable[Iterable[int]]) -> str:
        payload = bytes(cell for row in frame for cell in row)
        return hashlib.sha256(payload).hexdigest()[:16]
