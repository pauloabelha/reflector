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
    VisualPrimitive,
    canonical_atoms,
)


class SceneTracker:
    """Convert grids into symbolic scenes while preserving object identity."""

    MAX_RELATION_PAIRS = 2048

    def __init__(
        self,
        *,
        enable_visual_primitives: bool = False,
        enable_temporal_primitives: bool = False,
        max_visual_primitives: int = 128,
    ) -> None:
        self._index = 0
        self._next_object = 1
        self._previous: Scene | None = None
        self._previous_frame: tuple[tuple[int, ...], ...] = ()
        self.enable_visual_primitives = enable_visual_primitives
        self.enable_temporal_primitives = enable_temporal_primitives
        if not 1 <= max_visual_primitives <= 1024:
            raise ValueError("max_visual_primitives must be between 1 and 1024")
        self.max_visual_primitives = max_visual_primitives

    @property
    def previous(self) -> Scene | None:
        return self._previous

    def perceive(self, observation: Observation) -> tuple[Scene, tuple[Event, ...]]:
        components = self._components(observation.frame)
        objects = self._assign_identities(components)
        spatial_primitives = (
            self._visual_primitives(observation.frame, objects)
            if self.enable_visual_primitives
            else ()
        )
        temporal_primitives = (
            self._temporal_primitives(
                self._previous_frame,
                observation.frame,
                self._previous,
                objects,
            )
            if self.enable_temporal_primitives
            else ()
        )
        primitives = tuple(
            sorted(
                (*spatial_primitives, *temporal_primitives),
                key=lambda item: (
                    item.kind,
                    item.bbox,
                    item.area,
                    item.primitive_id,
                ),
            )[: self.max_visual_primitives]
        )
        facts = self._facts(observation, objects, primitives)
        scene = Scene(
            index=self._index,
            state=observation.state,
            levels_completed=observation.levels_completed,
            available_actions=observation.available_actions,
            objects=objects,
            facts=facts,
            frame_digest=self._digest(observation.frame),
            primitives=primitives,
        )
        events = self._events(self._previous, scene)
        self._previous = scene
        self._previous_frame = observation.frame
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
        observation: Observation,
        objects: tuple[ObjectState, ...],
        primitives: tuple[VisualPrimitive, ...] = (),
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
                    Atom(
                        "object_concept",
                        (obj.object_id, "persistent-component"),
                    ),
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
                    Atom(
                        "shape_form",
                        (
                            obj.object_id,
                            "sf-"
                            + hashlib.sha256(repr(obj.shape).encode()).hexdigest()[
                                :12
                            ],
                        ),
                    ),
                )
            )
        for primitive in primitives:
            concept_id = {
                "multicolor_region": "composite-region",
                "enclosed_region": "enclosed-region",
                "frame_delta_region": "frame-difference",
                "discrete_flow": "object-flow",
            }.get(primitive.kind, "visual-form")
            facts.extend(
                (
                    Atom(
                        "visual_primitive",
                        (primitive.primitive_id, primitive.kind),
                    ),
                    Atom(
                        "object_concept",
                        (primitive.primitive_id, concept_id),
                    ),
                    Atom(
                        "primitive_area",
                        (primitive.primitive_id, str(primitive.area)),
                    ),
                    Atom(
                        "primitive_bbox",
                        (
                            primitive.primitive_id,
                            *(str(value) for value in primitive.bbox),
                        ),
                    ),
                    Atom(
                        "primitive_color_count",
                        (
                            primitive.primitive_id,
                            str(len(primitive.colors)),
                        ),
                    ),
                )
            )
            facts.extend(
                Atom(
                    "primitive_property",
                    (primitive.primitive_id, property_name),
                )
                for property_name in primitive.properties
            )
            facts.extend(
                Atom(
                    "primitive_member",
                    (primitive.primitive_id, member),
                )
                for member in primitive.members
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

    def _visual_primitives(
        self,
        frame: tuple[tuple[int, ...], ...],
        objects: tuple[ObjectState, ...],
    ) -> tuple[VisualPrimitive, ...]:
        """Construct bounded regions and structural groups without semantics."""

        if not frame or not frame[0]:
            return ()
        counts = Counter(cell for row in frame for cell in row)
        background = max(counts, key=lambda color: (counts[color], -color))
        primitives = [
            *self._multicolor_regions(frame, background, objects),
            *self._enclosed_regions(frame, background),
        ]
        return tuple(
            sorted(
                primitives,
                key=lambda item: (
                    item.kind,
                    item.bbox,
                    item.area,
                    item.primitive_id,
                ),
            )[: self.max_visual_primitives]
        )

    @staticmethod
    def _primitive(
        *,
        kind: str,
        points: tuple[tuple[int, int], ...],
        colors: tuple[int, ...],
        members: tuple[str, ...] = (),
        properties: tuple[str, ...] = (),
        evidence: tuple[str, ...] = (),
        complexity_cost: int,
    ) -> VisualPrimitive:
        xs = tuple(point[0] for point in points)
        ys = tuple(point[1] for point in points)
        min_x, min_y = min(xs), min(ys)
        max_x, max_y = max(xs), max(ys)
        shape = tuple(
            sorted((x - min_x, y - min_y) for x, y in points)
        )
        normalized_properties = tuple(sorted(set(properties)))
        payload = repr(
            (
                kind,
                shape,
                colors,
                members,
                normalized_properties,
            )
        ).encode()
        primitive_id = (
            "vp-" + hashlib.sha256(payload).hexdigest()[:12]
        )
        return VisualPrimitive(
            primitive_id=primitive_id,
            kind=kind,
            area=len(points),
            bbox=(min_x, min_y, max_x, max_y),
            centroid=(sum(xs) // len(xs), sum(ys) // len(ys)),
            colors=colors,
            shape=shape,
            members=members,
            properties=normalized_properties,
            evidence=evidence,
            complexity_cost=complexity_cost,
        )

    @staticmethod
    def _shape_properties(
        points: tuple[tuple[int, int], ...],
    ) -> tuple[str, ...]:
        min_x = min(x for x, _y in points)
        min_y = min(y for _x, y in points)
        normalized = {
            (x - min_x, y - min_y) for x, y in points
        }
        width = max(x for x, _y in normalized) + 1
        height = max(y for _x, y in normalized) + 1
        properties = []
        if {(width - 1 - x, y) for x, y in normalized} == normalized:
            properties.append("symmetric_horizontal")
        if {(x, height - 1 - y) for x, y in normalized} == normalized:
            properties.append("symmetric_vertical")
        return tuple(properties)

    def _multicolor_regions(
        self,
        frame: tuple[tuple[int, ...], ...],
        background: int,
        objects: tuple[ObjectState, ...],
    ) -> tuple[VisualPrimitive, ...]:
        height, width = len(frame), len(frame[0])
        substrate: set[tuple[int, int]] = set()
        frame_area = width * height
        for item in objects:
            min_x, min_y, max_x, max_y = item.bbox
            if (
                item.area * 4 >= frame_area
                and (
                    min_x == 0
                    or min_y == 0
                    or max_x == width - 1
                    or max_y == height - 1
                )
            ):
                substrate.update(
                    (min_x + local_x, min_y + local_y)
                    for local_x, local_y in item.shape
                )
        seen: set[tuple[int, int]] = set()
        output = []
        for y in range(height):
            for x in range(width):
                if (
                    frame[y][x] == background
                    or (x, y) in substrate
                    or (x, y) in seen
                ):
                    continue
                queue = deque([(x, y)])
                seen.add((x, y))
                points = []
                while queue:
                    px, py = queue.popleft()
                    points.append((px, py))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == dy == 0:
                                continue
                            nx, ny = px + dx, py + dy
                            if (
                                0 <= nx < width
                                and 0 <= ny < height
                                and (nx, ny) not in seen
                                and (nx, ny) not in substrate
                                and frame[ny][nx] != background
                            ):
                                seen.add((nx, ny))
                                queue.append((nx, ny))
                colors = tuple(
                    sorted({frame[py][px] for px, py in points})
                )
                bounded = tuple(points)
                if not 2 <= len(colors) or not 2 <= len(bounded) <= 512:
                    continue
                bounded_set = set(bounded)
                members = []
                for item in objects:
                    min_x, min_y, _max_x, _max_y = item.bbox
                    absolute_shape = {
                        (min_x + local_x, min_y + local_y)
                        for local_x, local_y in item.shape
                    }
                    if absolute_shape & bounded_set:
                        members.append(item.object_id)
                touches_border = any(
                    px in {0, width - 1} or py in {0, height - 1}
                    for px, py in bounded
                )
                output.append(
                    self._primitive(
                        kind="multicolor_region",
                        points=bounded,
                        colors=colors,
                        members=tuple(sorted(members)),
                        properties=(
                            *self._shape_properties(bounded),
                            *(("touches_border",) if touches_border else ()),
                        ),
                        evidence=("8_connected_non_background",),
                        complexity_cost=3,
                    )
                )
        return tuple(output)

    def _temporal_primitives(
        self,
        before: tuple[tuple[int, ...], ...],
        after: tuple[tuple[int, ...], ...],
        before_scene: Scene | None,
        after_objects: tuple[ObjectState, ...],
    ) -> tuple[VisualPrimitive, ...]:
        if (
            not before
            or not after
            or len(before) != len(after)
            or any(len(left) != len(right) for left, right in zip(before, after))
        ):
            return ()
        height = len(after)
        width = len(after[0]) if after else 0
        changed = {
            (x, y)
            for y in range(height)
            for x in range(width)
            if before[y][x] != after[y][x]
        }
        output: list[VisualPrimitive] = []
        before_counts = Counter(cell for row in before for cell in row)
        after_counts = Counter(cell for row in after for cell in row)
        before_background = max(
            before_counts,
            key=lambda color: (before_counts[color], -color),
        )
        after_background = max(
            after_counts,
            key=lambda color: (after_counts[color], -color),
        )
        unseen = set(changed)
        while unseen:
            start = min(unseen, key=lambda point: (point[1], point[0]))
            queue = deque((start,))
            unseen.remove(start)
            points = []
            while queue:
                px, py = queue.popleft()
                points.append((px, py))
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dx == dy == 0:
                            continue
                        neighbor = (px + dx, py + dy)
                        if neighbor in unseen:
                            unseen.remove(neighbor)
                            queue.append(neighbor)
            bounded = tuple(points)
            if not 1 <= len(bounded) <= 512:
                continue
            appearances = sum(
                before[y][x] == before_background
                and after[y][x] != after_background
                for x, y in bounded
            )
            disappearances = sum(
                before[y][x] != before_background
                and after[y][x] == after_background
                for x, y in bounded
            )
            properties = []
            if appearances:
                properties.append("contains_appearance")
            if disappearances:
                properties.append("contains_disappearance")
            if len(bounded) > appearances + disappearances:
                properties.append("contains_substitution")
            output.append(
                self._primitive(
                    kind="frame_delta_region",
                    points=bounded,
                    colors=tuple(
                        sorted(
                            {
                                before[y][x]
                                for x, y in bounded
                            }
                            | {
                                after[y][x]
                                for x, y in bounded
                            }
                        )
                    ),
                    properties=tuple(properties),
                    evidence=("connected_frame_difference",),
                    complexity_cost=2,
                )
            )
        if before_scene is None:
            return tuple(output)
        old = {item.object_id: item for item in before_scene.objects}
        for item in after_objects:
            previous = old.get(item.object_id)
            if previous is None or previous.centroid == item.centroid:
                continue
            dx = item.centroid[0] - previous.centroid[0]
            dy = item.centroid[1] - previous.centroid[1]
            old_points = tuple(
                (
                    previous.bbox[0] + local_x,
                    previous.bbox[1] + local_y,
                )
                for local_x, local_y in previous.shape
            )
            new_points = tuple(
                (item.bbox[0] + local_x, item.bbox[1] + local_y)
                for local_x, local_y in item.shape
            )
            output.append(
                self._primitive(
                    kind="discrete_flow",
                    points=tuple(sorted(set((*old_points, *new_points)))),
                    colors=tuple(sorted({previous.color, item.color})),
                    members=(item.object_id,),
                    properties=(
                        f"dx_{dx}",
                        f"dy_{dy}",
                        "shape_preserved"
                        if previous.shape == item.shape
                        else "shape_changed",
                    ),
                    evidence=("persistent_object_displacement",),
                    complexity_cost=2,
                )
            )
        return tuple(output)

    def _enclosed_regions(
        self,
        frame: tuple[tuple[int, ...], ...],
        background: int,
    ) -> tuple[VisualPrimitive, ...]:
        height, width = len(frame), len(frame[0])
        seen: set[tuple[int, int]] = set()
        output = []
        for y in range(height):
            for x in range(width):
                if frame[y][x] != background or (x, y) in seen:
                    continue
                queue = deque([(x, y)])
                seen.add((x, y))
                points = []
                touches_edge = False
                while queue:
                    px, py = queue.popleft()
                    points.append((px, py))
                    touches_edge = touches_edge or (
                        px in {0, width - 1} or py in {0, height - 1}
                    )
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
                            and frame[ny][nx] == background
                        ):
                            seen.add((nx, ny))
                            queue.append((nx, ny))
                bounded = tuple(points)
                if touches_edge or not 1 <= len(bounded) <= 512:
                    continue
                output.append(
                    self._primitive(
                        kind="enclosed_region",
                        points=bounded,
                        colors=(background,),
                        properties=self._shape_properties(bounded),
                        evidence=("4_connected_background_not_on_frame",),
                        complexity_cost=3,
                    )
                )
        return tuple(output)

    def _repeated_shape_groups(
        self,
        objects: tuple[ObjectState, ...],
    ) -> tuple[VisualPrimitive, ...]:
        groups: dict[
            tuple[int, tuple[tuple[int, int], ...]],
            list[ObjectState],
        ] = {}
        for item in objects:
            groups.setdefault((item.area, item.shape), []).append(item)
        output = []
        for members in groups.values():
            if len(members) < 2:
                continue
            points = tuple(item.centroid for item in members)
            x_values = sorted({point[0] for point in points})
            y_values = sorted({point[1] for point in points})
            properties = []
            for axis, values in (("x", x_values), ("y", y_values)):
                deltas = [
                    right - left
                    for left, right in zip(values, values[1:])
                ]
                if len(deltas) >= 2 and len(set(deltas)) == 1:
                    properties.append(f"regular_{axis}")
            output.append(
                self._primitive(
                    kind="repeated_shape_group",
                    points=points,
                    colors=tuple(sorted({item.color for item in members})),
                    members=tuple(
                        sorted(item.object_id for item in members)
                    ),
                    properties=tuple(properties),
                    evidence=("equal_area", "equal_normalized_shape"),
                    complexity_cost=3,
                )
            )
        return tuple(output)

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
        for primitive in after.primitives:
            if primitive.kind == "frame_delta_region":
                area_band = (
                    "small"
                    if primitive.area <= 4
                    else "medium"
                    if primitive.area <= 32
                    else "large"
                )
                events.append(
                    Event(
                        "frame_difference",
                        "scene",
                        (area_band, *primitive.properties),
                    )
                )
            elif primitive.kind == "discrete_flow":
                events.append(
                    Event(
                        "object_flow",
                        "object",
                        primitive.properties,
                    )
                )
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
