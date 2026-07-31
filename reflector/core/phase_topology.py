"""Bounded planning over rigid-body anchors and symbolic display phases."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from math import gcd
from typing import Iterable

type Frame = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]
type Pattern = tuple[int, int, tuple[Point, ...]]


@dataclass(frozen=True, slots=True)
class Component:
    color: int
    cells: tuple[Point, ...]
    origin: Point
    shape: tuple[Point, ...]
    bbox: tuple[int, int, int, int]

    @property
    def area(self) -> int:
        return len(self.cells)


@dataclass(frozen=True, slots=True)
class RigidTranslation:
    before_anchor: Point
    after_anchor: Point
    displacement: Point
    colored_mask: tuple[tuple[int, int, int], ...]

    @property
    def mask(self) -> tuple[Point, ...]:
        return tuple((x, y) for x, y, _color in self.colored_mask)

    @property
    def colors(self) -> frozenset[int]:
        return frozenset(color for _x, _y, color in self.colored_mask)


@dataclass(frozen=True, slots=True)
class EmbeddedPattern:
    host_color: int
    glyph_color: int
    host_bbox: tuple[int, int, int, int]
    scale: int
    pattern: Pattern
    glyph_cells: tuple[Point, ...]


def components(frame: Frame) -> tuple[Component, ...]:
    if not frame or not frame[0]:
        return ()
    height = len(frame)
    width = len(frame[0])
    seen: set[Point] = set()
    output = []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen:
                continue
            color = frame[y][x]
            queue = [(x, y)]
            seen.add((x, y))
            cells = []
            while queue:
                point = queue.pop()
                cells.append(point)
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    neighbor = point[0] + dx, point[1] + dy
                    if (
                        0 <= neighbor[0] < width
                        and 0 <= neighbor[1] < height
                        and neighbor not in seen
                        and frame[neighbor[1]][neighbor[0]] == color
                    ):
                        seen.add(neighbor)
                        queue.append(neighbor)
            min_x = min(point[0] for point in cells)
            min_y = min(point[1] for point in cells)
            max_x = max(point[0] for point in cells)
            max_y = max(point[1] for point in cells)
            output.append(
                Component(
                    color=color,
                    cells=tuple(sorted(cells)),
                    origin=(min_x, min_y),
                    shape=tuple(
                        sorted((px - min_x, py - min_y) for px, py in cells)
                    ),
                    bbox=(min_x, min_y, max_x, max_y),
                )
            )
    return tuple(output)


def infer_rigid_translation(before: Frame, after: Frame) -> RigidTranslation | None:
    """Find adjacent differently colored components with one shared translation."""

    after_by_key: dict[
        tuple[int, int, tuple[Point, ...]],
        list[Component],
    ] = defaultdict(list)
    for item in components(after):
        after_by_key[(item.color, item.area, item.shape)].append(item)
    moved: dict[Point, list[Component]] = defaultdict(list)
    for item in components(before):
        matches = after_by_key.get((item.color, item.area, item.shape), ())
        if len(matches) != 1:
            continue
        successor = matches[0]
        displacement = (
            successor.origin[0] - item.origin[0],
            successor.origin[1] - item.origin[1],
        )
        if displacement != (0, 0):
            moved[displacement].append(item)
    candidates = []
    for displacement, items in moved.items():
        if len({item.color for item in items}) < 2:
            continue
        cells = tuple(cell for item in items for cell in item.cells)
        if not 8 <= len(cells) <= 512:
            continue
        min_x = min(x for x, _y in cells)
        min_y = min(y for _x, y in cells)
        max_x = max(x for x, _y in cells)
        max_y = max(y for _x, y in cells)
        bbox_area = (max_x - min_x + 1) * (max_y - min_y + 1)
        if bbox_area > len(cells) * 2:
            continue
        colored_mask = tuple(
            sorted(
                (
                    x - min_x,
                    y - min_y,
                    before[y][x],
                )
                for x, y in cells
            )
        )
        candidates.append(
            RigidTranslation(
                before_anchor=(min_x, min_y),
                after_anchor=(
                    min_x + displacement[0],
                    min_y + displacement[1],
                ),
                displacement=displacement,
                colored_mask=colored_mask,
            )
        )
    if not candidates:
        return None
    candidates.sort(key=lambda item: (-len(item.colored_mask), item.colored_mask))
    if (
        len(candidates) > 1
        and len(candidates[0].colored_mask) == len(candidates[1].colored_mask)
    ):
        return None
    return candidates[0]


def _coarse_pattern(cells: tuple[Point, ...]) -> tuple[int, Pattern] | None:
    if not cells:
        return None
    min_x = min(x for x, _y in cells)
    min_y = min(y for _x, y in cells)
    width = max(x for x, _y in cells) - min_x + 1
    height = max(y for _x, y in cells) - min_y + 1
    occupied = {(x - min_x, y - min_y) for x, y in cells}
    common = gcd(width, height)
    for scale in range(min(8, common), 0, -1):
        if width % scale or height % scale:
            continue
        logical = set()
        valid = True
        for block_y in range(height // scale):
            for block_x in range(width // scale):
                values = {
                    (
                        block_x * scale + local_x,
                        block_y * scale + local_y,
                    )
                    in occupied
                    for local_y in range(scale)
                    for local_x in range(scale)
                }
                if len(values) != 1:
                    valid = False
                    break
                if True in values:
                    logical.add((block_x, block_y))
            if not valid:
                break
        if valid:
            logical_width = width // scale
            logical_height = height // scale
            if 2 <= logical_width <= 8 and 2 <= logical_height <= 8:
                return (
                    scale,
                    (logical_width, logical_height, tuple(sorted(logical))),
                )
    return None


def embedded_patterns(frame: Frame) -> tuple[EmbeddedPattern, ...]:
    """Extract scale-normalized glyphs embedded in bounded host components."""

    if not frame or not frame[0]:
        return ()
    background = Counter(cell for row in frame for cell in row).most_common(1)[0][0]
    output = []
    for host in components(frame):
        min_x, min_y, max_x, max_y = host.bbox
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        if (
            host.color == background
            or not 3 <= width <= 24
            or not 3 <= height <= 24
            or not 16 <= host.area <= 1024
        ):
            continue
        interior: dict[int, list[Point]] = defaultdict(list)
        for y in range(min_y, max_y + 1):
            for x in range(min_x, max_x + 1):
                color = frame[y][x]
                if color not in {host.color, background}:
                    interior[color].append((x, y))
        for glyph_color, raw_cells in interior.items():
            cells = tuple(sorted(raw_cells))
            if not 2 <= len(cells) < host.area:
                continue
            coarse = _coarse_pattern(cells)
            if coarse is None:
                continue
            scale, pattern = coarse
            output.append(
                EmbeddedPattern(
                    host_color=host.color,
                    glyph_color=glyph_color,
                    host_bbox=host.bbox,
                    scale=scale,
                    pattern=pattern,
                    glyph_cells=cells,
                )
            )
    return tuple(
        sorted(
            output,
            key=lambda item: (
                item.pattern,
                item.scale,
                item.host_bbox,
                item.host_color,
                item.glyph_color,
            ),
        )
    )


def _covers(anchor: Point, mask: tuple[Point, ...], cells: Iterable[Point]) -> bool:
    occupied = {(anchor[0] + x, anchor[1] + y) for x, y in mask}
    return set(cells) <= occupied


def _overlaps_bbox(
    anchor: Point,
    mask: tuple[Point, ...],
    bbox: tuple[int, int, int, int],
) -> bool:
    min_x, min_y, max_x, max_y = bbox
    return any(
        min_x <= anchor[0] + local_x <= max_x
        and min_y <= anchor[1] + local_y <= max_y
        for local_x, local_y in mask
    )


@dataclass(slots=True)
class PhaseTopologyPlanner:
    """Learn and execute a bounded anchor × display-phase option."""

    max_anchors: int = 512
    max_operator_applications: int = 8
    max_plan_selections: int = 96
    action_effects: dict[int, Point] = field(default_factory=dict)
    action_evidence: Counter[int] = field(default_factory=Counter)
    invalid_actions: set[int] = field(default_factory=set)
    colored_mask: tuple[tuple[int, int, int], ...] = ()
    current_anchor: Point | None = None
    traversable_colors: set[int] = field(default_factory=set)
    current_host: tuple[int, int, int, int] | None = None
    current_pattern: Pattern | None = None
    goal_host: tuple[int, int, int, int] | None = None
    goal_pattern: Pattern | None = None
    goal_cells: tuple[Point, ...] = ()
    operator_cells: tuple[Point, ...] = ()
    pattern_candidates: tuple[EmbeddedPattern, ...] = ()
    blocked_edges: set[tuple[Point, int]] = field(default_factory=set)
    pending_anchor: Point | None = None
    pending_source: Point | None = None
    pending_action: int | None = None
    operator_applications: int = 0
    selections: int = 0
    compilations: int = 0
    confirmations: int = 0
    conflicts: int = 0
    search_expansions: int = 0
    last_plan_length: int = 0
    diagnostic: str = "exact-off"
    cap_failure: str | None = None

    @property
    def mask(self) -> tuple[Point, ...]:
        return tuple((x, y) for x, y, _color in self.colored_mask)

    @property
    def body_colors(self) -> frozenset[int]:
        return frozenset(color for _x, _y, color in self.colored_mask)

    def reset_level(self) -> None:
        self.action_effects.clear()
        self.action_evidence.clear()
        self.invalid_actions.clear()
        self.colored_mask = ()
        self.current_anchor = None
        self.traversable_colors.clear()
        self.current_host = None
        self.current_pattern = None
        self.goal_host = None
        self.goal_pattern = None
        self.goal_cells = ()
        self.operator_cells = ()
        self.pattern_candidates = ()
        self.blocked_edges.clear()
        self.pending_anchor = None
        self.pending_source = None
        self.pending_action = None
        self.operator_applications = 0
        self.selections = 0
        self.last_plan_length = 0
        self.diagnostic = "level-reset"
        self.cap_failure = None

    def observe(
        self,
        before: Frame,
        after: Frame,
        *,
        action_id: int,
        progressed: bool,
    ) -> None:
        motion = infer_rigid_translation(before, after)
        if progressed:
            self.confirmations += int(self.pending_action is not None)
            self.pending_anchor = None
            self.pending_source = None
            self.pending_action = None
            self.diagnostic = "terminal-predicate-confirmed"
            return
        if self.pending_action is not None:
            if (
                motion is None
                or motion.after_anchor != self.pending_anchor
                or action_id != self.pending_action
            ):
                if self.pending_source is not None:
                    self.blocked_edges.add((self.pending_source, action_id))
                self.conflicts += 1
                self.diagnostic = "predicted-anchor-transition-blocked"
            else:
                self.confirmations += 1
        self.pending_anchor = None
        self.pending_source = None
        self.pending_action = None
        if motion is not None:
            if (
                self.colored_mask
                and motion.colored_mask != self.colored_mask
            ):
                self.cap_failure = "inconsistent-rigid-body-mask"
                self.diagnostic = "fail-closed:inconsistent-rigid-body-mask"
                return
            self.colored_mask = motion.colored_mask
            self.current_anchor = motion.after_anchor
            previous = self.action_effects.get(action_id)
            if previous not in {None, motion.displacement}:
                self.invalid_actions.add(action_id)
                self.action_effects.pop(action_id, None)
                self.diagnostic = "inconsistent-action-displacement"
            elif action_id not in self.invalid_actions:
                self.action_effects[action_id] = motion.displacement
                self.action_evidence[action_id] += 1
            for local_x, local_y in motion.mask:
                x = motion.before_anchor[0] + local_x
                y = motion.before_anchor[1] + local_y
                if (
                    0 <= y < len(after)
                    and 0 <= x < len(after[y])
                    and after[y][x] not in motion.colors
                ):
                    self.traversable_colors.add(after[y][x])
        before_patterns = {
            item.host_bbox: item for item in embedded_patterns(before)
        }
        after_patterns = {
            item.host_bbox: item for item in embedded_patterns(after)
        }
        self.pattern_candidates = tuple(after_patterns.values())
        changed = tuple(
            (before_patterns[host], after_patterns[host])
            for host in set(before_patterns) & set(after_patterns)
            if before_patterns[host].pattern != after_patterns[host].pattern
        )
        qualified_changes = tuple(
            (previous_phase, next_phase, stationary[0])
            for previous_phase, next_phase in changed
            if len(
                stationary := tuple(
                    item
                    for host, item in after_patterns.items()
                    if host != next_phase.host_bbox
                    and item.pattern[:2] == next_phase.pattern[:2]
                )
            )
            == 1
        )
        if len(qualified_changes) == 1:
            _previous_phase, next_phase, goal = qualified_changes[0]
            self.current_host = next_phase.host_bbox
            self.current_pattern = next_phase.pattern
            self.goal_host = goal.host_bbox
            self.goal_pattern = goal.pattern
            self.goal_cells = goal.glyph_cells
            self.operator_applications += 1
            self.diagnostic = "operator-induced-phase-transition"
        elif self.current_host in after_patterns:
            current = after_patterns[self.current_host]
            self.current_pattern = current.pattern
            if self.goal_host in after_patterns:
                goal = after_patterns[self.goal_host]
                self.goal_pattern = goal.pattern
                self.goal_cells = goal.glyph_cells
        self._refresh_operator(before)

    def _refresh_operator(self, frame: Frame) -> None:
        if not self.colored_mask or not self.traversable_colors:
            return
        excluded = set(self.body_colors) | self.traversable_colors
        for item in self.pattern_candidates:
            excluded.update((item.host_color, item.glyph_color))
        body_cells = (
            {
                (
                    self.current_anchor[0] + x,
                    self.current_anchor[1] + y,
                )
                for x, y in self.mask
            }
            if self.current_anchor is not None
            else set()
        )
        small = [
            item
            for item in components(frame)
            if item.color not in excluded
            and 1 <= item.area <= 16
            and item.bbox[2] - item.bbox[0] + 1 <= 8
            and item.bbox[3] - item.bbox[1] + 1 <= 8
            and not set(item.cells) & body_cells
            and not any(
                host.host_bbox[0] <= item.origin[0] <= host.host_bbox[2]
                and host.host_bbox[1] <= item.origin[1] <= host.host_bbox[3]
                for host in self.pattern_candidates
            )
        ]
        groups = []
        remaining = set(range(len(small)))
        while remaining:
            seed = remaining.pop()
            group = {seed}
            queue = [seed]
            while queue:
                index = queue.pop()
                left = small[index].bbox
                neighbors = tuple(remaining)
                for other in neighbors:
                    right = small[other].bbox
                    if (
                        left[0] <= right[2] + 1
                        and right[0] <= left[2] + 1
                        and left[1] <= right[3] + 1
                        and right[1] <= left[3] + 1
                    ):
                        remaining.remove(other)
                        group.add(other)
                        queue.append(other)
            cells = tuple(
                sorted(cell for index in group for cell in small[index].cells)
            )
            colors = {small[index].color for index in group}
            if 2 <= len(cells) <= len(self.mask) and len(colors) >= 2:
                groups.append(cells)
        if len(groups) == 1:
            self.operator_cells = groups[0]

    def _target_anchors(self, cells: tuple[Point, ...]) -> tuple[Point, ...]:
        if not cells or not self.mask or self.current_anchor is None:
            return ()
        min_x = min(x for x, _y in cells)
        max_x = max(x for x, _y in cells)
        min_y = min(y for _x, y in cells)
        max_y = max(y for _x, y in cells)
        mask_max_x = max(x for x, _y in self.mask)
        mask_max_y = max(y for _x, y in self.mask)
        step_x = gcd(*(abs(dx) for dx, _dy in self.action_effects.values()))
        step_y = gcd(*(abs(dy) for _dx, dy in self.action_effects.values()))
        step_x = max(1, step_x)
        step_y = max(1, step_y)
        anchors = []
        for y in range(min_y - mask_max_y, max_y + 1):
            for x in range(min_x - mask_max_x, max_x + 1):
                if (
                    (x - self.current_anchor[0]) % step_x == 0
                    and (y - self.current_anchor[1]) % step_y == 0
                    and _covers((x, y), self.mask, cells)
                ):
                    anchors.append((x, y))
        return tuple(sorted(anchors))

    def _valid_anchor(
        self,
        frame: Frame,
        anchor: Point,
        *,
        special_colors: frozenset[int] = frozenset(),
    ) -> bool:
        allowed = self.traversable_colors | set(self.body_colors) | set(
            special_colors
        )
        return all(
            0 <= anchor[1] + local_y < len(frame)
            and 0 <= anchor[0] + local_x < len(frame[anchor[1] + local_y])
            and frame[anchor[1] + local_y][anchor[0] + local_x] in allowed
            for local_x, local_y in self.mask
        )

    def _path(
        self,
        frame: Frame,
        target_cells: tuple[Point, ...],
    ) -> tuple[int, ...]:
        if self.current_anchor is None:
            return ()
        targets = set(self._target_anchors(target_cells))
        if not targets:
            return ()
        special_colors = frozenset(
            frame[y][x]
            for x, y in target_cells
            if 0 <= y < len(frame) and 0 <= x < len(frame[y])
        )
        if target_cells == self.goal_cells and self.goal_host is not None:
            min_x, min_y, max_x, max_y = self.goal_host
            special_colors = frozenset(
                {
                    *special_colors,
                    *(
                        frame[y][x]
                        for y in range(max(0, min_y), min(len(frame), max_y + 1))
                        for x in range(
                            max(0, min_x),
                            min(len(frame[y]), max_x + 1),
                        )
                    ),
                }
            )
        queue: deque[tuple[Point, tuple[int, ...]]] = deque(
            [(self.current_anchor, ())]
        )
        seen = {self.current_anchor}
        expansions = 0
        while queue and expansions < self.max_anchors:
            anchor, path = queue.popleft()
            expansions += 1
            if anchor in targets:
                self.search_expansions += expansions
                return path
            for action_id, (dx, dy) in sorted(self.action_effects.items()):
                if (anchor, action_id) in self.blocked_edges:
                    continue
                neighbor = anchor[0] + dx, anchor[1] + dy
                if neighbor in seen:
                    continue
                if not self._valid_anchor(
                    frame,
                    neighbor,
                    special_colors=(
                        special_colors
                        if neighbor in targets
                        or (
                            target_cells == self.goal_cells
                            and self.goal_host is not None
                            and _overlaps_bbox(
                                neighbor,
                                self.mask,
                                self.goal_host,
                            )
                        )
                        else frozenset()
                    ),
                ):
                    continue
                seen.add(neighbor)
                queue.append((neighbor, (*path, action_id)))
        self.search_expansions += expansions
        if expansions >= self.max_anchors:
            self.cap_failure = "anchor-search-cap"
        return ()

    def select(
        self,
        frame: Frame,
        legal_action_ids: tuple[int, ...],
    ) -> int | None:
        if self.cap_failure is not None:
            self.diagnostic = f"fail-closed:{self.cap_failure}"
            return None
        if self.selections >= self.max_plan_selections:
            self.diagnostic = "plan-selection-cap"
            return None
        if (
            not self.colored_mask
            or self.current_anchor is None
            or len(self.action_effects) < 4
            or not self.traversable_colors
        ):
            self.diagnostic = "awaiting-rigid-translation-algebra"
            return None
        self._refresh_operator(frame)
        phase_equal = (
            self.current_pattern is not None
            and self.current_pattern == self.goal_pattern
        )
        if phase_equal and self.goal_cells:
            target_cells = self.goal_cells
            mode = "terminal"
        elif (
            self.operator_cells
            and self.operator_applications < self.max_operator_applications
        ):
            target_cells = self.operator_cells
            mode = "operator"
        else:
            self.diagnostic = "missing-phase-goal-or-operator"
            return None
        path = self._path(frame, target_cells)
        if not path:
            self.diagnostic = f"no-{mode}-path"
            return None
        action_id = path[0]
        if action_id not in legal_action_ids:
            self.diagnostic = "planned-action-not-legal"
            return None
        displacement = self.action_effects[action_id]
        self.pending_source = self.current_anchor
        self.pending_anchor = (
            self.current_anchor[0] + displacement[0],
            self.current_anchor[1] + displacement[1],
        )
        self.pending_action = action_id
        self.selections += 1
        self.compilations += 1
        self.last_plan_length = len(path)
        self.diagnostic = f"executing-{mode}-option"
        return action_id
