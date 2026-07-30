"""Grounded primary-stencil composition over visible relational roles.

The planner represents a scene as two same-sized dense grids, a congruent
palette, and one outlined movable template.  It never stores a game name,
absolute coordinate, color identity, or action identifier.  Cardinal and
diagonal primary masks are normalized half-plane predicates; controls are
bound from rendered pose changes.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Literal

type Frame = tuple[tuple[int, ...], ...]
type Grid = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]
type Pose = Literal["n", "ne", "e", "se", "s", "sw", "w", "nw"]

POSE_COORDINATES: dict[Pose, Point] = {
    "n": (0, -1),
    "ne": (1, -1),
    "e": (1, 0),
    "se": (1, 1),
    "s": (0, 1),
    "sw": (-1, 1),
    "w": (-1, 0),
    "nw": (-1, -1),
}
COORDINATE_POSES = {value: key for key, value in POSE_COORDINATES.items()}


@dataclass(frozen=True, order=True, slots=True)
class StencilToken:
    action_id: int
    data: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class _Component:
    color: int
    points: tuple[Point, ...]
    bbox: tuple[int, int, int, int]
    centroid: Point

    @property
    def area(self) -> int:
        return len(self.points)


@dataclass(frozen=True, slots=True)
class StencilScene:
    reference: Grid
    construction: Grid
    reference_bbox: tuple[int, int, int, int]
    construction_bbox: tuple[int, int, int, int]
    palette: tuple[tuple[int, StencilToken], ...]
    selected_color: int
    pose: Pose


@dataclass(slots=True)
class PrimaryStencilPlanner:
    """Learn controller bindings and search exact primary-stencil programs."""

    enabled: bool = False
    complex_action: int = 6
    reset_action: int = 0
    max_levels: int = 2
    max_search_states: int = 50_000
    max_plan_depth: int = 16
    current_level: int | None = None
    pending_token: StencilToken | None = None
    pending_scene: StencilScene | None = None
    action_directions: dict[int, Point] = field(default_factory=dict)
    no_effect_poses: dict[int, set[Pose]] = field(default_factory=dict)
    movement_confirmations: Counter[int] = field(default_factory=Counter)
    palette_predictions: int = 0
    palette_confirmations: int = 0
    palette_conflicts: int = 0
    plan_steps: int = 0
    search_states: int = 0
    submit_action: int | None = None
    quarantined: bool = False
    diagnostic: str = "exact-off"
    last_scene: StencilScene | None = None
    last_plan_length: int = 0
    last_target_pose: Pose | None = None
    last_reference_mismatches: int = 0

    def observe(self, frame: Frame, levels_completed: int) -> StencilScene | None:
        """Ground the current scene and validate the previously issued action."""

        scene = infer_stencil_scene(frame, complex_action=self.complex_action)
        if not self.enabled:
            self.diagnostic = "exact-off"
            self.last_scene = scene
            return scene
        if self.current_level is None:
            self.current_level = levels_completed
        elif levels_completed > self.current_level:
            self.current_level = levels_completed
            self.pending_token = None
            self.pending_scene = None
            self.no_effect_poses.clear()
            self.submit_action = None
            self.quarantined = False
            self.diagnostic = "level-advanced"
        if (
            self.pending_token is not None
            and self.pending_scene is not None
            and scene is not None
            and levels_completed == self.current_level
        ):
            self._validate_pending(self.pending_scene, scene, self.pending_token)
        self.pending_token = None
        self.pending_scene = None
        self.last_scene = scene
        if scene is None and not self.quarantined:
            self.diagnostic = "no-unique-stencil-scene"
        return scene

    def select(
        self,
        frame: Frame,
        levels_completed: int,
        legal_actions: tuple[int, ...],
    ) -> StencilToken | None:
        """Return one grounded probe or exact plan step, otherwise abstain."""

        if not self.enabled:
            self.diagnostic = "exact-off"
            return None
        if levels_completed >= self.max_levels:
            self.diagnostic = "stage-complete"
            return None
        if self.quarantined:
            self.diagnostic = "quarantined"
            return None
        scene = self.last_scene or infer_stencil_scene(
            frame,
            complex_action=self.complex_action,
        )
        if scene is None:
            self.diagnostic = "no-unique-stencil-scene"
            return None
        plain_actions = tuple(
            action
            for action in legal_actions
            if action not in {self.reset_action, self.complex_action}
        )
        if len(plain_actions) < 5:
            self.diagnostic = "insufficient-plain-controls"
            return None

        if len(self.action_directions) < 4:
            token = self._movement_probe(scene.pose, plain_actions)
            if token is None:
                self.diagnostic = "movement-binding-stalled"
                return None
            self.diagnostic = "probing-pose-controller"
            return self._register(token, scene)

        remaining = tuple(
            action for action in plain_actions if action not in self.action_directions
        )
        if len(remaining) != 1:
            self.diagnostic = "ambiguous-submit-control"
            return None
        self.submit_action = remaining[0]
        plan = self._plan(scene)
        if not plan:
            self.last_plan_length = 0
            self.diagnostic = "no-primary-stencil-plan"
            return None
        self.last_plan_length = len(plan)
        self.plan_steps += 1
        self.diagnostic = "executing-primary-stencil-plan"
        return self._register(plan[0], scene)

    def _movement_probe(
        self,
        pose: Pose,
        plain_actions: tuple[int, ...],
    ) -> StencilToken | None:
        unresolved = tuple(
            action for action in plain_actions if action not in self.action_directions
        )
        for action in unresolved:
            if pose not in self.no_effect_poses.get(action, set()):
                return StencilToken(action)

        targets = {
            candidate_pose
            for candidate_pose in POSE_COORDINATES
            if any(
                candidate_pose not in self.no_effect_poses.get(action, set())
                for action in unresolved
            )
        }
        return self._first_navigation_step(pose, targets)

    def _plan(self, scene: StencilScene) -> tuple[StencilToken, ...]:
        assert self.submit_action is not None
        start = (scene.construction, scene.selected_color, scene.pose)
        queue: deque[
            tuple[tuple[Grid, int, Pose], tuple[StencilToken, ...]]
        ] = deque(((start, ()),))
        visited = {start}
        self.search_states = 0
        while queue and self.search_states < self.max_search_states:
            (construction, color, pose), path = queue.popleft()
            self.search_states += 1
            prospective = apply_primary_stencil(construction, pose, color)
            mismatches = _grid_mismatches(prospective, scene.reference)
            if not path:
                self.last_reference_mismatches = mismatches
            if mismatches == 0:
                self.last_target_pose = pose
                return path + (StencilToken(self.submit_action),)
            if len(path) >= self.max_plan_depth:
                continue
            for action, direction in sorted(self.action_directions.items()):
                next_pose = move_pose(pose, direction)
                if next_pose == pose:
                    continue
                next_state = (construction, color, next_pose)
                if next_state in visited:
                    continue
                visited.add(next_state)
                queue.append((next_state, path + (StencilToken(action),)))
            committed = apply_primary_stencil(construction, pose, color)
            for next_color, token in scene.palette:
                if next_color == color:
                    continue
                next_state = (committed, next_color, pose)
                if next_state in visited:
                    continue
                visited.add(next_state)
                queue.append((next_state, path + (token,)))
        return ()

    def _first_navigation_step(
        self,
        start: Pose,
        targets: set[Pose],
    ) -> StencilToken | None:
        queue: deque[tuple[Pose, int | None]] = deque(((start, None),))
        visited = {start}
        while queue:
            pose, first = queue.popleft()
            if pose in targets and first is not None:
                return StencilToken(first)
            for action, direction in sorted(self.action_directions.items()):
                next_pose = move_pose(pose, direction)
                if next_pose == pose or next_pose in visited:
                    continue
                visited.add(next_pose)
                queue.append((next_pose, action if first is None else first))
        return None

    def _validate_pending(
        self,
        before: StencilScene,
        after: StencilScene,
        token: StencilToken,
    ) -> None:
        if before.reference != after.reference:
            self.no_effect_poses.clear()
            self.diagnostic = "level-scene-refreshed"
            return
        if token.action_id == self.complex_action and token.data:
            selected = next(
                (
                    color
                    for color, palette_token in before.palette
                    if palette_token == token
                ),
                None,
            )
            if selected is None:
                self.quarantined = True
                self.palette_conflicts += 1
                self.diagnostic = "unrepresented-palette-token"
                return
            self.palette_predictions += 1
            expected = apply_primary_stencil(
                before.construction,
                before.pose,
                before.selected_color,
            )
            if after.construction == expected and after.selected_color == selected:
                self.palette_confirmations += 1
                self.diagnostic = "palette-commit-confirmed"
            else:
                self.quarantined = True
                self.palette_conflicts += 1
                self.diagnostic = "palette-commit-mismatch"
            return
        if token.data:
            return
        before_coord = POSE_COORDINATES[before.pose]
        after_coord = POSE_COORDINATES[after.pose]
        delta = (
            after_coord[0] - before_coord[0],
            after_coord[1] - before_coord[1],
        )
        if before.construction != after.construction:
            self.quarantined = True
            self.diagnostic = "movement-changed-grounded-grids"
            return
        if delta in {(1, 0), (-1, 0), (0, 1), (0, -1)}:
            known = self.action_directions.get(token.action_id)
            if known is not None and known != delta:
                self.quarantined = True
                self.diagnostic = "controller-direction-conflict"
                return
            self.action_directions[token.action_id] = delta
            self.movement_confirmations[token.action_id] += 1
            self.diagnostic = "pose-controller-bound"
        elif delta == (0, 0):
            self.no_effect_poses.setdefault(token.action_id, set()).add(before.pose)
            self.diagnostic = "pose-boundary-no-effect"
        else:
            self.quarantined = True
            self.diagnostic = "noncardinal-pose-transition"

    def _register(self, token: StencilToken, scene: StencilScene) -> StencilToken:
        self.pending_token = token
        self.pending_scene = scene
        return token

    def to_dict(self) -> dict[str, object]:
        return {
            "active": int(self.enabled and not self.quarantined),
            "diagnostic": self.diagnostic,
            "scene_grounded": int(self.last_scene is not None),
            "current_pose": self.last_scene.pose if self.last_scene else None,
            "palette_roles": len(self.last_scene.palette) if self.last_scene else 0,
            "movement_bindings": len(self.action_directions),
            "movement_confirmations": sum(self.movement_confirmations.values()),
            "submit_action_grounded": int(self.submit_action is not None),
            "palette_predictions": self.palette_predictions,
            "palette_confirmations": self.palette_confirmations,
            "palette_conflicts": self.palette_conflicts,
            "search_states": self.search_states,
            "last_plan_length": self.last_plan_length,
            "plan_steps": self.plan_steps,
            "last_target_pose": self.last_target_pose,
            "last_reference_mismatches": self.last_reference_mismatches,
            "quarantined": int(self.quarantined),
        }


def infer_stencil_scene(
    frame: Frame,
    *,
    complex_action: int = 6,
) -> StencilScene | None:
    """Uniquely ground reference, construction, palette, template, and pose."""

    if not frame or not frame[0] or any(len(row) != len(frame[0]) for row in frame):
        return None
    background = Counter(value for row in frame for value in row).most_common(1)[0][0]
    components = _components(frame)
    palette = _palette_roles(frame, components, complex_action=complex_action)
    if len(palette) < 2:
        return None
    patches = _dense_square_patches(frame, background)
    paired = tuple(
        (left, right)
        for index, left in enumerate(patches)
        for right in patches[index + 1 :]
        if len(left[1]) == len(right[1])
    )
    if len(paired) != 1:
        return None
    first, second = paired[0]
    size = len(first[1])
    palette_colors = {color for color, _token in palette}
    palette_centers = tuple(
        (
            dict(token.data)["x"],
            dict(token.data)["y"],
        )
        for _color, token in palette
    )
    template_candidates = tuple(
        item
        for item in components
        if item.color in palette_colors
        and size <= item.area <= 2 * size * size
        and not any(_bbox_contains(patch[0], item.bbox) for patch in (first, second))
        and not any(
            item.bbox[0] <= center[0] <= item.bbox[2]
            and item.bbox[1] <= center[1] <= item.bbox[3]
            for center in palette_centers
        )
    )
    if not template_candidates:
        return None
    ranked: list[
        tuple[int, int, tuple[tuple[int, int, int, int], Grid], _Component]
    ] = []
    for patch in (first, second):
        center = _bbox_center(patch[0])
        for component in template_candidates:
            distance = _chebyshev(center, component.centroid)
            ranked.append((distance, -component.area, patch, component))
    ranked.sort(key=lambda item: (item[0], item[1], item[2][0], item[3].bbox))
    if len(ranked) > 1 and ranked[0][:2] == ranked[1][:2]:
        return None
    _distance, _neg_area, construction, template = ranked[0]
    reference = second if construction == first else first
    pose = _relative_pose(
        _bbox_center(construction[0]),
        template.centroid,
        size=size,
    )
    if pose is None:
        return None
    return StencilScene(
        reference=reference[1],
        construction=construction[1],
        reference_bbox=reference[0],
        construction_bbox=construction[0],
        palette=palette,
        selected_color=template.color,
        pose=pose,
    )


def primary_mask(size: int, pose: Pose) -> tuple[tuple[bool, ...], ...]:
    """Return one normalized cardinal or inclusive diagonal half-plane."""

    if size < 2:
        raise ValueError("primary stencil requires a grid of size at least two")
    middle = size // 2
    return tuple(
        tuple(
            (
                y < middle
                if pose == "n"
                else y >= size - middle
                if pose == "s"
                else x < middle
                if pose == "w"
                else x >= size - middle
                if pose == "e"
                else x + y <= size - 1
                if pose == "nw"
                else x + y >= size - 1
                if pose == "se"
                else x >= y
                if pose == "ne"
                else y >= x
            )
            for x in range(size)
        )
        for y in range(size)
    )


def apply_primary_stencil(grid: Grid, pose: Pose, color: int) -> Grid:
    if not grid or any(len(row) != len(grid) for row in grid):
        raise ValueError("primary stencil grid must be non-empty and square")
    mask = primary_mask(len(grid), pose)
    return tuple(
        tuple(color if mask[y][x] else value for x, value in enumerate(row))
        for y, row in enumerate(grid)
    )


def move_pose(pose: Pose, direction: Point) -> Pose:
    x, y = POSE_COORDINATES[pose]
    candidate = (x + direction[0], y + direction[1])
    return COORDINATE_POSES.get(candidate, pose)


def _components(frame: Frame) -> tuple[_Component, ...]:
    height = len(frame)
    width = len(frame[0])
    visited: set[Point] = set()
    output: list[_Component] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in visited:
                continue
            color = frame[y][x]
            queue = [(x, y)]
            visited.add((x, y))
            points: list[Point] = []
            while queue:
                current = queue.pop()
                points.append(current)
                cx, cy = current
                for candidate in (
                    (cx - 1, cy),
                    (cx + 1, cy),
                    (cx, cy - 1),
                    (cx, cy + 1),
                ):
                    nx, ny = candidate
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and candidate not in visited
                        and frame[ny][nx] == color
                    ):
                        visited.add(candidate)
                        queue.append(candidate)
            min_x = min(point[0] for point in points)
            max_x = max(point[0] for point in points)
            min_y = min(point[1] for point in points)
            max_y = max(point[1] for point in points)
            output.append(
                _Component(
                    color=color,
                    points=tuple(sorted(points)),
                    bbox=(min_x, min_y, max_x, max_y),
                    centroid=(
                        sum(point[0] for point in points) // len(points),
                        sum(point[1] for point in points) // len(points),
                    ),
                )
            )
    return tuple(output)


def _palette_roles(
    frame: Frame,
    components: tuple[_Component, ...],
    *,
    complex_action: int,
) -> tuple[tuple[int, StencilToken], ...]:
    enclosures = tuple(
        item
        for item in components
        if item.area == 16
        and item.bbox[2] - item.bbox[0] == 4
        and item.bbox[3] - item.bbox[1] == 4
    )
    groups: dict[tuple[int, int], list[_Component]] = {}
    for item in enclosures:
        groups.setdefault((item.color, item.centroid[1]), []).append(item)
    candidates: list[tuple[tuple[int, StencilToken], ...]] = []
    for items in groups.values():
        ordered = tuple(sorted(items, key=lambda item: item.centroid[0]))
        if len(ordered) < 2:
            continue
        spacings = {
            right.centroid[0] - left.centroid[0]
            for left, right in zip(ordered, ordered[1:], strict=False)
        }
        if len(spacings) != 1:
            continue
        roles: list[tuple[int, StencilToken]] = []
        for enclosure in ordered:
            center_x, center_y = enclosure.centroid
            payload = {
                frame[y][x]
                for y in range(center_y - 1, center_y + 2)
                for x in range(center_x - 1, center_x + 2)
            }
            if len(payload) != 1:
                break
            roles.append(
                (
                    next(iter(payload)),
                    StencilToken(
                        complex_action,
                        (("x", center_x), ("y", center_y)),
                    ),
                )
            )
        if len(roles) == len(ordered) and len({item[0] for item in roles}) == len(
            roles
        ):
            candidates.append(tuple(roles))
    if len(candidates) != 1:
        return ()
    return candidates[0]


def _dense_square_patches(
    frame: Frame,
    background: int,
) -> tuple[tuple[tuple[int, int, int, int], Grid], ...]:
    height = len(frame)
    width = len(frame[0])
    output: list[tuple[tuple[int, int, int, int], Grid]] = []
    for size in range(6, min(16, height - 2, width - 2) + 1):
        for y in range(1, height - size):
            for x in range(1, width - size):
                if any(
                    frame[row][column] == background
                    for row in range(y, y + size)
                    for column in range(x, x + size)
                ):
                    continue
                ring = (
                    tuple((column, y - 1) for column in range(x - 1, x + size + 1))
                    + tuple(
                        (column, y + size)
                        for column in range(x - 1, x + size + 1)
                    )
                    + tuple((x - 1, row) for row in range(y, y + size))
                    + tuple((x + size, row) for row in range(y, y + size))
                )
                if all(frame[row][column] == background for column, row in ring):
                    bbox = (x, y, x + size - 1, y + size - 1)
                    grid = tuple(
                        tuple(frame[row][x : x + size])
                        for row in range(y, y + size)
                    )
                    output.append((bbox, grid))
    maximal = tuple(
        item
        for item in output
        if not any(
            item != other and _bbox_contains(other[0], item[0])
            for other in output
        )
    )
    return tuple(sorted(maximal, key=lambda item: item[0]))


def _relative_pose(center: Point, template: Point, *, size: int) -> Pose | None:
    dx = template[0] - center[0]
    dy = template[1] - center[1]
    threshold = max(2, size // 3)
    sx = 0 if abs(dx) < threshold else 1 if dx > 0 else -1
    sy = 0 if abs(dy) < threshold else 1 if dy > 0 else -1
    if (sx, sy) == (0, 0):
        return None
    return COORDINATE_POSES.get((sx, sy))


def _bbox_center(bbox: tuple[int, int, int, int]) -> Point:
    return ((bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2)


def _bbox_contains(
    outer: tuple[int, int, int, int],
    inner: tuple[int, int, int, int],
) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def _chebyshev(left: Point, right: Point) -> int:
    return max(abs(left[0] - right[0]), abs(left[1] - right[1]))


def _grid_mismatches(left: Grid, right: Grid) -> int:
    if len(left) != len(right) or any(
        len(left_row) != len(right_row)
        for left_row, right_row in zip(left, right, strict=False)
    ):
        return max(len(left), len(right))
    return sum(
        left_value != right_value
        for left_row, right_row in zip(left, right, strict=True)
        for left_value, right_value in zip(left_row, right_row, strict=True)
    )
