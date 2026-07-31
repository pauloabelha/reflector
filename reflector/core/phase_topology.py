"""Bounded planning over rigid-body anchors and symbolic display phases."""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from heapq import heappop, heappush
from math import gcd
from typing import Iterable, Literal

type Frame = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]
type Pattern = tuple[int, int, tuple[Point, ...]]
type BBox = tuple[int, int, int, int]
type ResourceKey = tuple[int, tuple[int, int, int, int], tuple[Point, ...]]
type MaskSignature = tuple[tuple[int, int, int], ...]
type RetentionScope = Literal["cross-level", "same-level-retry"]


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
                    shape=tuple(sorted((px - min_x, py - min_y) for px, py in cells)),
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
    if len(candidates) > 1 and len(candidates[0].colored_mask) == len(
        candidates[1].colored_mask
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


def _bbox_contains(outer: BBox, inner: BBox) -> bool:
    return (
        outer[0] <= inner[0]
        and outer[1] <= inner[1]
        and outer[2] >= inner[2]
        and outer[3] >= inner[3]
    )


def _bboxes_overlap(left: BBox, right: BBox) -> bool:
    return (
        left[0] <= right[2]
        and right[0] <= left[2]
        and left[1] <= right[3]
        and right[1] <= left[3]
    )


def _complementary_display_pairs(
    patterns: Iterable[EmbeddedPattern],
) -> tuple[tuple[EmbeddedPattern, EmbeddedPattern], ...]:
    """Find exact color-dual presentations of one bounded binary partition."""

    items = tuple(patterns)
    pairs = []
    for index, left in enumerate(items):
        for right in items[index + 1 :]:
            width, height = left.pattern[:2]
            if (
                left.scale != right.scale
                or right.pattern[:2] != (width, height)
                or left.host_color != right.glyph_color
                or left.glyph_color != right.host_color
                or not (
                    _bbox_contains(left.host_bbox, right.host_bbox)
                    or _bbox_contains(right.host_bbox, left.host_bbox)
                )
            ):
                continue
            left_cells = set(left.pattern[2])
            right_cells = set(right.pattern[2])
            logical_grid = {
                (x, y) for y in range(height) for x in range(width)
            }
            if left_cells.isdisjoint(right_cells) and (
                left_cells | right_cells
            ) == logical_grid:
                pairs.append((left, right))
    return tuple(pairs)


def _select_partition_view(
    patterns: dict[BBox, EmbeddedPattern],
    hosts: tuple[BBox, ...],
    goal: EmbeddedPattern,
) -> EmbeddedPattern | None:
    """Choose one presentation by a unique structural CSP optimum."""

    candidates = tuple(
        patterns[host]
        for host in hosts
        if (
            host in patterns
            and patterns[host].pattern[:2] == goal.pattern[:2]
            and patterns[host].host_color == goal.host_color
        )
    )
    if len(candidates) != 1:
        return None
    return candidates[0]


def _ground_complementary_display(
    patterns: Iterable[EmbeddedPattern],
) -> tuple[tuple[BBox, ...], EmbeddedPattern, EmbeddedPattern] | None:
    """Ground a unique current binary partition against one external target."""

    items = tuple(patterns)
    pairs = _complementary_display_pairs(items)
    if len(pairs) != 1:
        return None
    pair = pairs[0]
    pair_hosts = tuple(sorted(item.host_bbox for item in pair))
    arity = pair[0].pattern[:2]
    external = tuple(
        item
        for item in items
        if item.host_bbox not in pair_hosts
        and item.pattern[:2] == arity
        and all(
            not _bboxes_overlap(item.host_bbox, host) for host in pair_hosts
        )
    )
    if len(external) != 1:
        return None
    goal = external[0]
    current = _select_partition_view(
        {item.host_bbox: item for item in pair},
        pair_hosts,
        goal,
    )
    if current is None:
        return None
    return pair_hosts, current, goal


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
        min_x <= anchor[0] + local_x <= max_x and min_y <= anchor[1] + local_y <= max_y
        for local_x, local_y in mask
    )


def _resource_key(component: Component) -> ResourceKey:
    return component.color, component.bbox, component.shape


def _partition_signature(
    colored_mask: tuple[tuple[int, int, int], ...],
) -> MaskSignature:
    """Canonicalize a colored mask up to a bijective color renaming."""

    classes: dict[int, int] = {}
    signature = []
    for x, y, color in sorted(colored_mask):
        if color not in classes:
            classes[color] = len(classes)
        signature.append((x, y, classes[color]))
    return tuple(signature)


def _bbox_union(
    left: tuple[int, int, int, int] | None,
    right: tuple[int, int, int, int],
) -> tuple[int, int, int, int]:
    if left is None:
        return right
    return (
        min(left[0], right[0]),
        min(left[1], right[1]),
        max(left[2], right[2]),
        max(left[3], right[3]),
    )


def _overlap_classes(
    candidates: Iterable[tuple[Point, ...]],
) -> tuple[tuple[tuple[Point, ...], tuple[tuple[Point, ...], ...]], ...]:
    """Quotient partially occluded cell sets by transitive spatial overlap."""

    remaining = set(candidates)
    classes = []
    while remaining:
        seed = remaining.pop()
        members = {seed}
        occupied = set(seed)
        changed = True
        while changed:
            changed = False
            for candidate in tuple(remaining):
                if occupied.isdisjoint(candidate):
                    continue
                remaining.remove(candidate)
                members.add(candidate)
                occupied.update(candidate)
                changed = True
        representative = min(
            members,
            key=lambda cells: (-len(cells), cells),
        )
        classes.append((representative, tuple(sorted(members))))
    return tuple(
        sorted(
            classes,
            key=lambda item: (
                min(y for _x, y in item[0]),
                min(x for x, _y in item[0]),
                item[0],
            ),
        )
    )


@dataclass(slots=True)
class PhaseTopologyPlanner:
    """Learn bounded options over anchor × phase × temporal-resource state."""

    max_anchors: int = 512
    max_operator_applications: int = 16
    max_contextual_edges: int = 16
    max_operator_candidates: int = 8
    max_plan_selections: int = 96
    max_resources: int = 8
    min_budget_evidence: int = 2
    action_effects: dict[int, Point] = field(default_factory=dict)
    action_evidence: Counter[int] = field(default_factory=Counter)
    inherited_action_effects: dict[int, Point] = field(default_factory=dict)
    inherited_action_evidence: Counter[int] = field(default_factory=Counter)
    inherited_mask_signature: MaskSignature = ()
    inherited_traversable_colors: frozenset[int] = frozenset()
    inherited_probe_actions: set[int] = field(default_factory=set)
    inherited_action_algebra_scope: RetentionScope | None = None
    transferred_action_algebra_active: bool = False
    active_action_algebra_scope: RetentionScope | None = None
    transfer_probe_selections: int = 0
    cross_level_transfer_confirmations: int = 0
    cross_level_transfer_rejections: int = 0
    retry_transfer_confirmations: int = 0
    retry_transfer_rejections: int = 0
    invalid_actions: set[int] = field(default_factory=set)
    colored_mask: tuple[tuple[int, int, int], ...] = ()
    current_anchor: Point | None = None
    traversable_colors: set[int] = field(default_factory=set)
    current_host: tuple[int, int, int, int] | None = None
    current_view_hosts: tuple[BBox, ...] = ()
    current_pattern: Pattern | None = None
    current_glyph_color: int | None = None
    goal_host: tuple[int, int, int, int] | None = None
    goal_pattern: Pattern | None = None
    goal_glyph_color: int | None = None
    goal_cells: tuple[Point, ...] = ()
    # Equality remains valid under later visual occlusion until a causal reset.
    goal_latched: bool = False
    operator_cells: tuple[Point, ...] = ()
    operator_candidates: tuple[tuple[Point, ...], ...] = ()
    operator_effects: dict[tuple[Point, ...], frozenset[str]] = field(
        default_factory=dict
    )
    active_operator: tuple[Point, ...] | None = None
    pattern_candidates: tuple[EmbeddedPattern, ...] = ()
    blocked_edges: set[tuple[Point, int]] = field(default_factory=set)
    contextual_edges: dict[tuple[Point, int], Point] = field(default_factory=dict)
    pending_anchor: Point | None = None
    pending_source: Point | None = None
    pending_action: int | None = None
    pending_resource_back_edge: tuple[Point, int] | None = None
    resource_exit_edges: set[tuple[Point, int]] = field(default_factory=set)
    operator_applications: int = 0
    contextual_transitions: int = 0
    budget_color: int | None = None
    budget_bbox: tuple[int, int, int, int] | None = None
    budget_area: int | None = None
    budget_capacity: int = 0
    budget_unit: int | None = None
    budget_evidence: Counter[int] = field(default_factory=Counter)
    resource_candidates: tuple[Component, ...] = ()
    consumed_resources: set[ResourceKey] = field(default_factory=set)
    active_resource: ResourceKey | None = None
    pending_resource: ResourceKey | None = None
    resource_rearm_cells: tuple[Point, ...] = ()
    resource_resets: int = 0
    horizon_resets: int = 0
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

    def reset_level(
        self,
        *,
        retain_action_algebra: bool = False,
        retention_scope: RetentionScope = "cross-level",
    ) -> None:
        self.transferred_action_algebra_active = False
        self.active_action_algebra_scope = None
        retain_supported = (
            retain_action_algebra
            and 4 <= len(self.action_effects) <= 8
            and bool(self.colored_mask)
        )
        if retain_supported:
            self.inherited_action_effects = dict(self.action_effects)
            self.inherited_action_evidence = Counter(self.action_evidence)
            self.inherited_mask_signature = _partition_signature(self.colored_mask)
            self.inherited_traversable_colors = frozenset(
                self.traversable_colors
            )
            self.inherited_action_algebra_scope = retention_scope
        else:
            self.inherited_action_effects.clear()
            self.inherited_action_evidence.clear()
            self.inherited_mask_signature = ()
            self.inherited_traversable_colors = frozenset()
            self.inherited_action_algebra_scope = None
        self.inherited_probe_actions.clear()
        self.action_effects.clear()
        self.action_evidence.clear()
        self.invalid_actions.clear()
        self.colored_mask = ()
        self.current_anchor = None
        self.traversable_colors.clear()
        self.current_host = None
        self.current_view_hosts = ()
        self.current_pattern = None
        self.current_glyph_color = None
        self.goal_host = None
        self.goal_pattern = None
        self.goal_glyph_color = None
        self.goal_cells = ()
        self.goal_latched = False
        self.operator_cells = ()
        self.operator_candidates = ()
        self.operator_effects.clear()
        self.active_operator = None
        self.pattern_candidates = ()
        self.blocked_edges.clear()
        self.contextual_edges.clear()
        self.pending_anchor = None
        self.pending_source = None
        self.pending_action = None
        self.pending_resource_back_edge = None
        self.resource_exit_edges.clear()
        self.operator_applications = 0
        self.contextual_transitions = 0
        self.budget_color = None
        self.budget_bbox = None
        self.budget_area = None
        self.budget_capacity = 0
        self.budget_unit = None
        self.budget_evidence.clear()
        self.resource_candidates = ()
        self.consumed_resources.clear()
        self.active_resource = None
        self.pending_resource = None
        self.resource_rearm_cells = ()
        self.resource_resets = 0
        self.horizon_resets = 0
        self.selections = 0
        self.last_plan_length = 0
        self.diagnostic = "level-reset"
        self.cap_failure = None

    def _clear_inherited_action_algebra(self) -> None:
        self.inherited_action_effects.clear()
        self.inherited_action_evidence.clear()
        self.inherited_mask_signature = ()
        self.inherited_traversable_colors = frozenset()
        self.inherited_probe_actions.clear()
        self.inherited_action_algebra_scope = None

    def _locate_inherited_body(
        self,
        frame: Frame,
    ) -> tuple[Point, tuple[tuple[int, int, int], ...]] | None:
        """Relocate one retained color partition from exact components."""

        if not self.inherited_mask_signature:
            return None
        partition: dict[int, list[Point]] = defaultdict(list)
        for x, y, color_class in self.inherited_mask_signature:
            partition[color_class].append((x, y))
        base_class = min(partition)
        base = partition[base_class]
        base_min_x = min(x for x, _y in base)
        base_min_y = min(y for _x, y in base)
        base_shape = tuple(
            sorted((x - base_min_x, y - base_min_y) for x, y in base)
        )
        frame_components = components(frame)
        component_by_cell = {
            cell: component
            for component in frame_components
            for cell in component.cells
        }
        matches: list[tuple[Point, tuple[tuple[int, int, int], ...]]] = []
        for component in frame_components:
            if component.shape != base_shape:
                continue
            anchor = (
                component.origin[0] - base_min_x,
                component.origin[1] - base_min_y,
            )
            class_colors: dict[int, int] = {}
            valid = True
            for color_class, local_cells in sorted(partition.items()):
                absolute_cells = {
                    (anchor[0] + x, anchor[1] + y)
                    for x, y in local_cells
                }
                witness = component_by_cell.get(next(iter(absolute_cells)))
                if witness is None or set(witness.cells) != absolute_cells:
                    valid = False
                    break
                class_colors[color_class] = witness.color
            if not valid or len(class_colors) != len(set(class_colors.values())):
                continue
            colored_mask = tuple(
                (x, y, class_colors[color_class])
                for x, y, color_class in self.inherited_mask_signature
            )
            matches.append((anchor, colored_mask))
        return matches[0] if len(matches) == 1 else None

    def _select_inherited_probe(
        self,
        frame: Frame,
        legal_action_ids: tuple[int, ...],
    ) -> int | None:
        """Prospectively test one inherited morphism on known substrate."""

        if (
            self.action_effects
            or not self.inherited_action_effects
            or not self.inherited_traversable_colors
        ):
            return None
        located = self._locate_inherited_body(frame)
        if located is None:
            return None
        anchor, colored_mask = located
        mask = tuple((x, y) for x, y, _color in colored_mask)
        occupied = {(anchor[0] + x, anchor[1] + y) for x, y in mask}
        candidates = []
        for action_id, (dx, dy) in sorted(self.inherited_action_effects.items()):
            if (
                action_id not in legal_action_ids
                or action_id in self.inherited_probe_actions
            ):
                continue
            destination = anchor[0] + dx, anchor[1] + dy
            entering = tuple(
                (destination[0] + x, destination[1] + y)
                for x, y in mask
                if (destination[0] + x, destination[1] + y) not in occupied
            )
            if not entering or any(
                not (0 <= y < len(frame) and 0 <= x < len(frame[y]))
                for x, y in entering
            ):
                continue
            if all(
                frame[y][x] in self.inherited_traversable_colors
                for x, y in entering
            ):
                candidates.append(action_id)
        if not candidates:
            return None
        selected = min(candidates)
        self.inherited_probe_actions.add(selected)
        self.transfer_probe_selections += 1
        self.selections += 1
        self.compilations += 1
        self.last_plan_length = 1
        self.diagnostic = "executing-inherited-naturality-probe"
        return selected

    def _consider_inherited_action_algebra(
        self,
        motion: RigidTranslation,
        *,
        action_id: int,
    ) -> None:
        """Prospectively confirm or reject a compressed cross-level scheme."""

        if (
            not self.inherited_action_effects
            or action_id not in self.inherited_action_effects
        ):
            return
        commutes = (
            _partition_signature(motion.colored_mask) == self.inherited_mask_signature
            and motion.displacement == self.inherited_action_effects[action_id]
        )
        scope = self.inherited_action_algebra_scope
        if commutes:
            self.action_effects = dict(self.inherited_action_effects)
            self.action_evidence = Counter(
                {
                    inherited_action: max(
                        1,
                        self.inherited_action_evidence[inherited_action],
                    )
                    for inherited_action in self.inherited_action_effects
                }
            )
            self.transferred_action_algebra_active = True
            self.active_action_algebra_scope = scope
            if scope == "same-level-retry":
                self.retry_transfer_confirmations += 1
                self.diagnostic = "retry-action-algebra-confirmed"
            else:
                self.cross_level_transfer_confirmations += 1
                self.diagnostic = "cross-level-action-algebra-confirmed"
        else:
            self.transferred_action_algebra_active = False
            self.active_action_algebra_scope = None
            if scope == "same-level-retry":
                self.retry_transfer_rejections += 1
                self.diagnostic = "retry-action-algebra-rejected"
            else:
                self.cross_level_transfer_rejections += 1
                self.diagnostic = "cross-level-action-algebra-rejected"
        self._clear_inherited_action_algebra()

    @property
    def remaining_budget(self) -> int | None:
        if self.budget_area is None or self.budget_unit is None:
            return None
        return self.budget_area // self.budget_unit

    @property
    def budget_horizon(self) -> int | None:
        if not self.budget_capacity or self.budget_unit is None:
            return None
        return self.budget_capacity // self.budget_unit

    def _temporal_components(
        self,
        frame: Frame,
    ) -> tuple[Component | None, tuple[Component, ...]]:
        """Find one boundary meter and its bounded same-role spatial tokens."""

        if not frame or not frame[0]:
            return None, ()
        height = len(frame)
        width = len(frame[0])
        items = components(frame)

        def boundary_distance(item: Component) -> int:
            min_x, min_y, max_x, max_y = item.bbox
            return min(min_x, min_y, width - 1 - max_x, height - 1 - max_y)

        def thin(item: Component) -> bool:
            min_x, min_y, max_x, max_y = item.bbox
            box_width = max_x - min_x + 1
            box_height = max_y - min_y + 1
            return min(box_width, box_height) <= 2

        def aligned_with_meter(item: Component) -> bool:
            if self.budget_bbox is None:
                return True
            min_x, min_y, max_x, max_y = item.bbox
            old_min_x, old_min_y, old_max_x, old_max_y = self.budget_bbox
            horizontal = old_max_x - old_min_x >= old_max_y - old_min_y
            if horizontal:
                return min_y <= old_max_y and max_y >= old_min_y
            return min_x <= old_max_x and max_x >= old_min_x

        meter_options = [
            item
            for item in items
            if (self.budget_color is None or item.color == self.budget_color)
            and thin(item)
            and boundary_distance(item) <= 2
            and aligned_with_meter(item)
            and (
                self.budget_color is not None
                or (
                    item.area >= 16
                    and max(
                        item.bbox[2] - item.bbox[0] + 1,
                        item.bbox[3] - item.bbox[1] + 1,
                    )
                    >= 4
                    * min(
                        item.bbox[2] - item.bbox[0] + 1,
                        item.bbox[3] - item.bbox[1] + 1,
                    )
                )
            )
        ]
        meter_options.sort(key=lambda item: (-item.area, item.bbox, item.color))

        if self.budget_color is None:
            paired = []
            for meter in meter_options:
                tokens = tuple(
                    item
                    for item in items
                    if item.color == meter.color
                    and item is not meter
                    and 4 <= item.area <= 64
                    and boundary_distance(item) > 2
                    and item.bbox[2] - item.bbox[0] + 1 >= 2
                    and item.bbox[3] - item.bbox[1] + 1 >= 2
                    and (
                        (item.bbox[2] - item.bbox[0] + 1)
                        * (item.bbox[3] - item.bbox[1] + 1)
                        > item.area
                    )
                )
                if 1 <= len(tokens) <= self.max_resources:
                    paired.append((meter, tokens))
            if len(paired) != 1:
                return None, ()
            meter, tokens = paired[0]
        else:
            if not meter_options:
                return None, ()
            meter = meter_options[0]
            tokens = tuple(
                item
                for item in items
                if item.color == self.budget_color
                and item is not meter
                and 4 <= item.area <= 64
                and boundary_distance(item) > 2
                and item.bbox[2] - item.bbox[0] + 1 >= 2
                and item.bbox[3] - item.bbox[1] + 1 >= 2
                and (
                    (item.bbox[2] - item.bbox[0] + 1)
                    * (item.bbox[3] - item.bbox[1] + 1)
                    > item.area
                )
            )
        return meter, tuple(
            sorted(tokens, key=lambda item: (item.bbox, item.shape))[
                : self.max_resources
            ]
        )

    def _observe_temporal_resources(
        self,
        before: Frame,
        after: Frame,
        motion: RigidTranslation | None,
    ) -> bool:
        """Update the learned reset algebra; return whether the horizon reset."""

        before_meter, before_resources = self._temporal_components(before)
        if before_meter is not None and self.budget_color is None:
            self.budget_color = before_meter.color
            self.budget_bbox = before_meter.bbox
        if before_meter is not None:
            self.budget_bbox = _bbox_union(self.budget_bbox, before_meter.bbox)
            self.budget_capacity = max(self.budget_capacity, before_meter.area)
        after_meter, after_resources = self._temporal_components(after)
        if after_meter is not None and self.budget_color is None:
            self.budget_color = after_meter.color

        horizon_reset = False
        if after_meter is not None:
            self.budget_bbox = _bbox_union(self.budget_bbox, after_meter.bbox)
            self.budget_area = after_meter.area
            self.budget_capacity = max(self.budget_capacity, after_meter.area)
        if before_meter is not None and after_meter is not None:
            difference = before_meter.area - after_meter.area
            if 0 < difference <= 64:
                self.budget_evidence[difference] += 1
                best, count = self.budget_evidence.most_common(1)[0]
                if count >= self.min_budget_evidence:
                    self.budget_unit = best
            elif (
                difference < 0
                and self.budget_unit is not None
                and -difference >= 2 * self.budget_unit
            ):
                contacted = tuple(
                    item
                    for item in before_resources
                    if motion is not None
                    and _covers(motion.after_anchor, motion.mask, item.cells)
                )
                if (
                    not contacted
                    and self.pending_resource is not None
                    and all(
                        _resource_key(item) != self.pending_resource
                        for item in after_resources
                    )
                ):
                    contacted = tuple(
                        item
                        for item in before_resources
                        if _resource_key(item) == self.pending_resource
                    )
                if len(contacted) == 1:
                    contacted_key = _resource_key(contacted[0])
                    self.consumed_resources.add(contacted_key)
                    self.resource_rearm_cells = contacted[0].cells
                    if self.active_resource == contacted_key:
                        self.active_resource = None
                    self.resource_resets += 1
                else:
                    horizon_reset = True
                    self.horizon_resets += 1
                    self.consumed_resources.clear()
                    self.active_resource = None
                    self.resource_rearm_cells = ()
        after_resource_keys = {
            _resource_key(item) for item in after_resources
        }
        if (
            not horizon_reset
            and self.consumed_resources
            and self.consumed_resources <= after_resource_keys
        ):
            horizon_reset = True
            self.horizon_resets += 1
            self.consumed_resources.clear()
            self.active_resource = None
            self.resource_rearm_cells = ()
            self.resource_exit_edges.clear()
            self.pending_resource_back_edge = None
        self.resource_candidates = tuple(
            item
            for item in after_resources
            if _resource_key(item) not in self.consumed_resources
        )
        self.pending_resource = None
        return horizon_reset

    def observe(
        self,
        before: Frame,
        after: Frame,
        *,
        action_id: int,
        progressed: bool,
    ) -> None:
        motion = infer_rigid_translation(before, after)
        had_pending = self.pending_action is not None
        changed_cells = sum(
            before_cell != after_cell
            for before_row, after_row in zip(before, after, strict=False)
            for before_cell, after_cell in zip(
                before_row,
                after_row,
                strict=False,
            )
        )
        frame_area = sum(len(row) for row in after)
        scene_discontinuity = changed_cells > max(
            4 * len(motion.colored_mask) if motion is not None else 0,
            frame_area // 5,
        )
        horizon_reset = self._observe_temporal_resources(before, after, motion)
        if horizon_reset:
            self.goal_latched = False
            self.active_operator = None
            self.operator_applications = 0
            self.selections = 0
            self.resource_exit_edges.clear()
            self.pending_resource_back_edge = None
        if progressed:
            self.confirmations += int(self.pending_action is not None)
            self.pending_anchor = None
            self.pending_source = None
            self.pending_action = None
            self.pending_resource_back_edge = None
            self.diagnostic = "terminal-predicate-confirmed"
            return
        predicted_transition = (
            self.pending_action is not None
            and motion is not None
            and motion.after_anchor == self.pending_anchor
            and action_id == self.pending_action
        )
        ordinary_effect = self.action_effects.get(action_id)
        contextual_transition = (
            motion is not None
            and ordinary_effect is not None
            and motion.displacement != ordinary_effect
            and not horizon_reset
            and not scene_discontinuity
            and (
                not self.colored_mask
                or motion.colored_mask == self.colored_mask
            )
        )
        if self.pending_action is not None:
            if horizon_reset or scene_discontinuity:
                self.confirmations += 1
                self.diagnostic = (
                    "temporal-horizon-reset"
                    if horizon_reset
                    else "scene-transition-bootstrap"
                )
            elif contextual_transition and motion is not None:
                if self.pending_source is not None:
                    self.blocked_edges.add((self.pending_source, action_id))
                if (
                    self.pending_source is not None
                    and len(self.contextual_edges) < self.max_contextual_edges
                ):
                    key = self.pending_source, action_id
                    previous_destination = self.contextual_edges.get(key)
                    if previous_destination in {None, motion.after_anchor}:
                        self.contextual_edges[key] = motion.after_anchor
                        self.contextual_transitions += int(
                            previous_destination is None
                        )
                        self.confirmations += 1
                        self.diagnostic = "contextual-anchor-edge-observed"
                    else:
                        self.conflicts += 1
                        self.contextual_edges.pop(key, None)
                        self.diagnostic = "contextual-anchor-edge-conflict"
                else:
                    self.conflicts += 1
                    self.diagnostic = "contextual-anchor-edge-cap"
            elif not predicted_transition:
                if self.pending_source is not None:
                    self.blocked_edges.add((self.pending_source, action_id))
                self.conflicts += 1
                self.diagnostic = "predicted-anchor-transition-blocked"
            else:
                self.confirmations += 1
        if self.pending_resource_back_edge is not None:
            if (
                predicted_transition
                and len(self.resource_exit_edges) < self.max_resources
            ):
                self.resource_exit_edges.add(self.pending_resource_back_edge)
            self.pending_resource_back_edge = None
        self.pending_anchor = None
        self.pending_source = None
        self.pending_action = None
        if motion is not None:
            if self.colored_mask and motion.colored_mask != self.colored_mask:
                self.cap_failure = "inconsistent-rigid-body-mask"
                self.diagnostic = "fail-closed:inconsistent-rigid-body-mask"
                return
            self.colored_mask = motion.colored_mask
            self.current_anchor = motion.after_anchor
            if (
                not horizon_reset
                and not scene_discontinuity
                and not contextual_transition
                and (not had_pending or predicted_transition)
            ):
                self._consider_inherited_action_algebra(
                    motion,
                    action_id=action_id,
                )
                previous = self.action_effects.get(action_id)
                if previous not in {None, motion.displacement}:
                    self.invalid_actions.add(action_id)
                    self.action_effects.pop(action_id, None)
                    self.diagnostic = "inconsistent-action-displacement"
                elif action_id not in self.invalid_actions:
                    self.action_effects[action_id] = motion.displacement
                    self.action_evidence[action_id] += 1
            elif contextual_transition and not had_pending:
                key = motion.before_anchor, action_id
                previous_destination = self.contextual_edges.get(key)
                if (
                    previous_destination in {None, motion.after_anchor}
                    and (
                        previous_destination is not None
                        or len(self.contextual_edges) < self.max_contextual_edges
                    )
                ):
                    self.contextual_edges[key] = motion.after_anchor
                    self.blocked_edges.add(key)
                    self.contextual_transitions += int(previous_destination is None)
                    self.diagnostic = "contextual-anchor-edge-observed"
            protected_cells = set(self.operator_cells)
            for resource in self.resource_candidates:
                protected_cells.update(resource.cells)
            for local_x, local_y in motion.mask:
                x = motion.before_anchor[0] + local_x
                y = motion.before_anchor[1] + local_y
                if (
                    0 <= y < len(after)
                    and 0 <= x < len(after[y])
                    and (x, y) not in protected_cells
                    and after[y][x] not in motion.colors
                ):
                    self.traversable_colors.add(after[y][x])
        before_patterns = {item.host_bbox: item for item in embedded_patterns(before)}
        after_patterns = {item.host_bbox: item for item in embedded_patterns(after)}
        self.pattern_candidates = tuple(after_patterns.values())
        if self.current_host is None or self.goal_host is None:
            grounding = _ground_complementary_display(after_patterns.values())
            if grounding is not None:
                view_hosts, current, goal = grounding
                self.current_view_hosts = view_hosts
                self.current_host = current.host_bbox
                self.current_pattern = current.pattern
                self.current_glyph_color = current.glyph_color
                self.goal_host = goal.host_bbox
                self.goal_pattern = goal.pattern
                self.goal_glyph_color = goal.glyph_color
                self.goal_cells = goal.glyph_cells
                self.diagnostic = "complementary-display-bundle-grounded"
        changed = tuple(
            (before_patterns[host], after_patterns[host])
            for host in set(before_patterns) & set(after_patterns)
            if (
                before_patterns[host].pattern != after_patterns[host].pattern
                or before_patterns[host].glyph_color
                != after_patterns[host].glyph_color
                or before_patterns[host].host_color
                != after_patterns[host].host_color
            )
        )
        stable_factor_bundle = (
            self.current_host is not None and self.goal_host is not None
        )
        qualified_changes: tuple[
            tuple[EmbeddedPattern, EmbeddedPattern, EmbeddedPattern],
            ...,
        ]
        if (
            self.current_view_hosts
            and self.goal_host in after_patterns
            and (
                previous_view := _select_partition_view(
                    before_patterns,
                    self.current_view_hosts,
                    after_patterns[self.goal_host],
                )
            )
            is not None
            and (
                next_view := _select_partition_view(
                    after_patterns,
                    self.current_view_hosts,
                    after_patterns[self.goal_host],
                )
            )
            is not None
            and (
                previous_view.pattern != next_view.pattern
                or previous_view.glyph_color != next_view.glyph_color
                or previous_view.host_color != next_view.host_color
            )
        ):
            qualified_changes = (
                (
                    previous_view,
                    next_view,
                    after_patterns[self.goal_host],
                ),
            )
        elif (
            stable_factor_bundle
            and self.current_host in before_patterns
            and self.current_host in after_patterns
            and self.goal_host in after_patterns
            and any(
                next_phase.host_bbox == self.current_host
                for _previous_phase, next_phase in changed
            )
        ):
            qualified_changes = (
                (
                    before_patterns[self.current_host],
                    after_patterns[self.current_host],
                    after_patterns[self.goal_host],
                ),
            )
        elif stable_factor_bundle:
            # A learned current→goal factor bundle is an object identity, not
            # whichever same-arity glyph happens to change next.  In
            # particular, moving-body occlusion can transiently manufacture
            # unrelated embedded patterns while the terminal option executes.
            qualified_changes = ()
        else:
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
        if (
            len(qualified_changes) == 1
            and not horizon_reset
            and not scene_discontinuity
        ):
            previous_phase, next_phase, goal = qualified_changes[0]
            self.current_host = next_phase.host_bbox
            self.current_pattern = next_phase.pattern
            self.current_glyph_color = next_phase.glyph_color
            self.goal_host = goal.host_bbox
            self.goal_pattern = goal.pattern
            self.goal_glyph_color = goal.glyph_color
            self.goal_cells = goal.glyph_cells
            self.goal_latched = self.goal_latched or (
                next_phase.pattern == goal.pattern
                and next_phase.glyph_color == goal.glyph_color
            )
            effects = set(self.operator_effects.get(self.operator_cells, ()))
            if previous_phase.pattern != next_phase.pattern:
                effects.add("shape")
            if (
                previous_phase.glyph_color != next_phase.glyph_color
                or previous_phase.host_color != next_phase.host_color
            ):
                effects.add("palette")
            if self.operator_cells and effects:
                self.operator_effects[self.operator_cells] = frozenset(effects)
                if self.active_operator == self.operator_cells:
                    self.active_operator = None
            self.operator_applications += 1
            self.diagnostic = "operator-induced-factor-transition"
        elif self.current_view_hosts and self.goal_host in after_patterns:
            goal = after_patterns[self.goal_host]
            current_view = _select_partition_view(
                after_patterns,
                self.current_view_hosts,
                goal,
            )
            if current_view is not None:
                self.current_host = current_view.host_bbox
                self.current_pattern = current_view.pattern
                self.current_glyph_color = current_view.glyph_color
                self.goal_pattern = goal.pattern
                self.goal_glyph_color = goal.glyph_color
                self.goal_cells = goal.glyph_cells
                self.goal_latched = self.goal_latched or (
                    current_view.pattern == goal.pattern
                    and current_view.glyph_color == goal.glyph_color
                )
        elif self.current_host in after_patterns:
            current = after_patterns[self.current_host]
            self.current_pattern = current.pattern
            self.current_glyph_color = current.glyph_color
            if self.goal_host in after_patterns:
                goal = after_patterns[self.goal_host]
                self.goal_pattern = goal.pattern
                self.goal_glyph_color = goal.glyph_color
                self.goal_cells = goal.glyph_cells
                self.goal_latched = self.goal_latched or (
                    current.pattern == goal.pattern
                    and current.glyph_color == goal.glyph_color
                )
        self._refresh_operator(before)

    def _refresh_operator(self, frame: Frame) -> None:
        if not self.colored_mask or not self.traversable_colors:
            return
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
        visible_displays = tuple(
            item
            for item in self.pattern_candidates
            if not any(
                min_x <= x <= max_x and min_y <= y <= max_y
                for x, y in body_cells
                for min_x, min_y, max_x, max_y in (item.host_bbox,)
            )
        )
        nested_display = any(
            outer.host_bbox[0] <= inner.host_bbox[0]
            and outer.host_bbox[1] <= inner.host_bbox[1]
            and outer.host_bbox[2] >= inner.host_bbox[2]
            and outer.host_bbox[3] >= inner.host_bbox[3]
            and outer.host_bbox != inner.host_bbox
            for outer in visible_displays
            for inner in visible_displays
        )
        comparable_display = any(
            left.host_bbox != right.host_bbox
            and left.pattern[:2] == right.pattern[:2]
            for left in visible_displays
            for right in visible_displays
        )
        factored_scene = nested_display and comparable_display
        excluded = set(self.traversable_colors)
        if not factored_scene:
            excluded.update(self.body_colors)
            for item in self.pattern_candidates:
                excluded.update((item.host_color, item.glyph_color))
        if self.budget_color is not None:
            excluded.add(self.budget_color)
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
            logical_arity = (
                self.goal_pattern[:2] if self.goal_pattern is not None else None
            )
            sparse_factor_morphism = False
            if (
                factored_scene
                and len(colors) == 1
                and logical_arity is not None
            ):
                width = max(x for x, _y in cells) - min(x for x, _y in cells) + 1
                height = max(y for _x, y in cells) - min(
                    y for _x, y in cells
                ) + 1
                sparse_factor_morphism = (
                    (width, height) == logical_arity
                    and len(cells) < width * height
                )
            if (
                2 <= len(cells) < len(self.mask)
                and (len(colors) >= 2 or sparse_factor_morphism)
            ):
                groups.append(cells)
        discovered = tuple(sorted(set(groups)))
        if factored_scene and discovered:
            classes = _overlap_classes(
                set((*self.operator_candidates, *discovered))
            )
            canonical: dict[tuple[Point, ...], tuple[Point, ...]] = {}
            for representative, members in classes:
                effects: set[str] = set()
                for member in members:
                    canonical[member] = representative
                    effects.update(self.operator_effects.pop(member, ()))
                if effects:
                    self.operator_effects[representative] = frozenset(effects)
            self.operator_cells = canonical.get(
                self.operator_cells,
                self.operator_cells,
            )
            if self.active_operator is not None:
                self.active_operator = canonical.get(
                    self.active_operator,
                    self.active_operator,
                )
            self.operator_candidates = tuple(
                representative for representative, _members in classes
            )[: self.max_operator_candidates]
        elif not factored_scene:
            self.operator_candidates = discovered if len(discovered) == 1 else ()
        if len(self.operator_candidates) == 1:
            self.operator_cells = self.operator_candidates[0]

    def _display_factors_equal(self) -> bool:
        if self.current_pattern is None or self.goal_pattern is None:
            return False
        palette_equal = (
            self.current_glyph_color is None
            or self.goal_glyph_color is None
            or self.current_glyph_color == self.goal_glyph_color
        )
        return self.current_pattern == self.goal_pattern and palette_equal

    def _is_sparse_arity_candidate(
        self,
        frame: Frame,
        candidate: tuple[Point, ...],
    ) -> bool:
        if not candidate or self.goal_pattern is None:
            return False
        width = max(x for x, _y in candidate) - min(
            x for x, _y in candidate
        ) + 1
        height = max(y for _x, y in candidate) - min(
            y for _x, y in candidate
        ) + 1
        visible_colors = {
            frame[y][x]
            for x, y in candidate
            if 0 <= y < len(frame) and 0 <= x < len(frame[y])
        }
        return (
            (width, height) == self.goal_pattern[:2]
            and len(candidate) < width * height
            and len(visible_colors) == 1
        )

    def _select_operator_candidate(self, frame: Frame) -> None:
        if not self.operator_candidates:
            return
        palette_equal = (
            self.current_glyph_color is not None
            and self.goal_glyph_color is not None
            and self.current_glyph_color == self.goal_glyph_color
        )
        shape_equal = (
            self.current_pattern is not None
            and self.goal_pattern is not None
            and self.current_pattern == self.goal_pattern
        )
        needed_role = (
            None
            if self.current_pattern is None or self.goal_pattern is None
            else "palette"
            if not palette_equal
            else "shape"
            if not shape_equal
            else "complete"
        )
        if needed_role == "complete":
            return
        both_factors_differ = not palette_equal and not shape_equal
        eligible = []
        for candidate in self.operator_candidates:
            effects = self.operator_effects.get(candidate, frozenset())
            if needed_role is None:
                if effects:
                    continue
            elif effects and needed_role not in effects:
                continue
            path = (
                ()
                if (
                    self.current_anchor is not None
                    and _covers(self.current_anchor, self.mask, candidate)
                )
                else self._path(frame, candidate)
            )
            if path or (
                self.current_anchor is not None
                and _covers(self.current_anchor, self.mask, candidate)
            ):
                sparse_arity_hypothesis = (
                    bool(self.current_view_hosts)
                    and both_factors_differ
                    and not effects
                    and self._is_sparse_arity_candidate(frame, candidate)
                )
                eligible.append(
                    (
                        int(not sparse_arity_hypothesis),
                        len(path),
                        candidate,
                    )
                )
        if eligible:
            self.operator_cells = min(
                eligible,
                key=lambda item: (item[0], item[1], item[2]),
            )[2]

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

    def _goal_anchors(self) -> tuple[Point, ...]:
        if self.goal_host is None or not self.mask:
            return ()
        min_x, min_y, max_x, max_y = self.goal_host
        mask_width = max(x for x, _y in self.mask) + 1
        mask_height = max(y for _x, y in self.mask) + 1
        host_width = max_x - min_x + 1
        host_height = max_y - min_y + 1
        if host_width < mask_width or host_height < mask_height:
            return ()
        return (
            (
                min_x + (host_width - mask_width) // 2,
                min_y + (host_height - mask_height) // 2,
            ),
        )

    def _valid_anchor(
        self,
        frame: Frame,
        anchor: Point,
        *,
        special_cells: frozenset[Point] = frozenset(),
    ) -> bool:
        allowed = self.traversable_colors | set(self.body_colors)
        return all(
            0 <= anchor[1] + local_y < len(frame)
            and 0 <= anchor[0] + local_x < len(frame[anchor[1] + local_y])
            and (
                frame[anchor[1] + local_y][anchor[0] + local_x] in allowed
                or (
                    anchor[0] + local_x,
                    anchor[1] + local_y,
                )
                in special_cells
            )
            for local_x, local_y in self.mask
        )

    def _search_path(
        self,
        frame: Frame,
        *,
        start: Point,
        targets: set[Point],
        special_cells: frozenset[Point] = frozenset(),
        prefer_fewer_contextual: bool = False,
    ) -> tuple[int, ...]:
        if not targets:
            return ()
        if prefer_fewer_contextual:
            risk_queue: list[tuple[int, int, tuple[int, ...], Point]] = [
                (0, 0, (), start)
            ]
            best = {start: (0, 0)}
            expansions = 0
            while risk_queue and expansions < self.max_anchors:
                contextual_cost, length, path, anchor = heappop(risk_queue)
                if best.get(anchor) != (contextual_cost, length):
                    continue
                expansions += 1
                if anchor in targets:
                    self.search_expansions += expansions
                    return path
                for action_id, (dx, dy) in sorted(self.action_effects.items()):
                    key = anchor, action_id
                    contextual = self.contextual_edges.get(key)
                    if key in self.resource_exit_edges or (
                        contextual is None and key in self.blocked_edges
                    ):
                        continue
                    neighbor = (
                        contextual
                        if contextual is not None
                        else (anchor[0] + dx, anchor[1] + dy)
                    )
                    if not self._valid_anchor(
                        frame,
                        neighbor,
                        special_cells=special_cells,
                    ):
                        continue
                    cost = (
                        contextual_cost + int(contextual is not None),
                        length + 1,
                    )
                    if cost >= best.get(neighbor, (1_000_000, 1_000_000)):
                        continue
                    best[neighbor] = cost
                    heappush(
                        risk_queue,
                        (*cost, (*path, action_id), neighbor),
                    )
            self.search_expansions += expansions
            if expansions >= self.max_anchors:
                self.cap_failure = "anchor-search-cap"
            return ()
        queue: deque[tuple[Point, tuple[int, ...]]] = deque([(start, ())])
        seen = {start}
        expansions = 0
        while queue and expansions < self.max_anchors:
            anchor, path = queue.popleft()
            expansions += 1
            if anchor in targets:
                self.search_expansions += expansions
                return path
            for action_id, (dx, dy) in sorted(self.action_effects.items()):
                contextual = self.contextual_edges.get((anchor, action_id))
                if (anchor, action_id) in self.resource_exit_edges or (
                    contextual is None
                    and (anchor, action_id) in self.blocked_edges
                ):
                    continue
                neighbor = (
                    contextual
                    if contextual is not None
                    else (anchor[0] + dx, anchor[1] + dy)
                )
                if neighbor in seen:
                    continue
                if not self._valid_anchor(
                    frame,
                    neighbor,
                    special_cells=special_cells,
                ):
                    continue
                seen.add(neighbor)
                queue.append((neighbor, (*path, action_id)))
        self.search_expansions += expansions
        if expansions >= self.max_anchors:
            self.cap_failure = "anchor-search-cap"
        return ()

    def _path(
        self,
        frame: Frame,
        target_cells: tuple[Point, ...],
        *,
        start: Point | None = None,
        transit_cells: tuple[Point, ...] = (),
    ) -> tuple[int, ...]:
        source = self.current_anchor if start is None else start
        if source is None:
            return ()
        targets = set(
            self._goal_anchors()
            if target_cells == self.goal_cells
            else self._target_anchors(target_cells)
        )
        special_cells = set(target_cells) | set(transit_cells)
        if target_cells == self.goal_cells and self.goal_host is not None:
            min_x, min_y, max_x, max_y = self.goal_host
            special_cells.update(
                (x, y)
                for y in range(max(0, min_y), min(len(frame), max_y + 1))
                for x in range(
                    max(0, min_x),
                    min(len(frame[y]), max_x + 1),
                )
            )
        return self._search_path(
            frame,
            start=source,
            targets=targets,
            special_cells=frozenset(special_cells),
            prefer_fewer_contextual=(
                bool(self.current_view_hosts)
                and bool(self.resource_exit_edges)
                and not self.resource_candidates
            ),
        )

    def _endpoint(self, start: Point, path: tuple[int, ...]) -> Point:
        x, y = start
        for action_id in path:
            contextual = self.contextual_edges.get(((x, y), action_id))
            if contextual is not None:
                x, y = contextual
            else:
                dx, dy = self.action_effects[action_id]
                x += dx
                y += dy
        return x, y

    def _operator_rearm_path(
        self,
        frame: Frame,
        legal_action_ids: tuple[int, ...],
    ) -> tuple[int, ...]:
        if self.current_anchor is None or not self.operator_cells:
            return ()
        candidates = []
        for action_id, (dx, dy) in sorted(self.action_effects.items()):
            neighbor = (
                self.current_anchor[0] + dx,
                self.current_anchor[1] + dy,
            )
            if (
                action_id not in legal_action_ids
                or (self.current_anchor, action_id) in self.blocked_edges
                or (self.current_anchor, action_id) in self.resource_exit_edges
                or not self._valid_anchor(frame, neighbor)
                or _covers(neighbor, self.mask, self.operator_cells)
            ):
                continue
            return_path = self._path(
                frame,
                self.operator_cells,
                start=neighbor,
            )
            if return_path:
                candidates.append((action_id, *return_path))
        if not candidates:
            return ()
        return min(candidates, key=lambda path: (len(path), path))

    def _leave_contact_path(
        self,
        frame: Frame,
        cells: tuple[Point, ...],
        legal_action_ids: tuple[int, ...],
    ) -> tuple[int, ...]:
        if self.current_anchor is None:
            return ()
        candidates = []
        for action_id, (dx, dy) in sorted(self.action_effects.items()):
            contextual = self.contextual_edges.get(
                (self.current_anchor, action_id)
            )
            neighbor = (
                contextual
                if contextual is not None
                else (
                    self.current_anchor[0] + dx,
                    self.current_anchor[1] + dy,
                )
            )
            if (
                action_id not in legal_action_ids
                or (self.current_anchor, action_id) in self.blocked_edges
                or (self.current_anchor, action_id) in self.resource_exit_edges
                or not self._valid_anchor(frame, neighbor)
                or _covers(neighbor, self.mask, cells)
            ):
                continue
            candidates.append((action_id,))
        return min(candidates) if candidates else ()

    def _resource_option(
        self,
        frame: Frame,
        destination: tuple[Point, ...],
        *,
        remaining: int,
        horizon: int,
        prefer_nearest: bool = False,
    ) -> tuple[Component, tuple[int, ...]] | None:
        """Choose the latest reachable reset whose post-reset suffix is feasible."""

        if self.current_anchor is None:
            return None
        feasible = []
        for resource in self.resource_candidates:
            path = self._path(frame, resource.cells)
            if not path or len(path) > remaining:
                continue
            resource_anchor = self._endpoint(self.current_anchor, path)
            suffix = self._path(
                frame,
                destination,
                start=resource_anchor,
                transit_cells=resource.cells,
            )
            if not suffix or len(suffix) > horizon:
                continue
            feasible.append((resource, path, suffix))
        if not feasible:
            return None
        resource, path, _suffix = min(
            feasible,
            key=lambda item: (
                len(item[1]) if prefer_nearest else -len(item[1]),
                len(item[2]),
                item[0].bbox,
            ),
        )
        return resource, path

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
        inherited_probe = self._select_inherited_probe(
            frame,
            legal_action_ids,
        )
        if inherited_probe is not None:
            return inherited_probe
        if (
            not self.colored_mask
            or self.current_anchor is None
            or len(self.action_effects) < 4
            or not self.traversable_colors
        ):
            self.diagnostic = "awaiting-rigid-translation-algebra"
            return None
        self._refresh_operator(frame)
        if self.active_operator is not None:
            self.operator_cells = self.active_operator
        else:
            self._select_operator_candidate(frame)
        on_operator = (
            self.current_anchor is not None
            and bool(self.operator_cells)
            and _covers(
                self.current_anchor,
                self.mask,
                self.operator_cells,
            )
        )
        phase_equal = self.goal_latched or self._display_factors_equal()
        remaining = self.remaining_budget
        horizon = self.budget_horizon
        bounded_remaining = remaining if remaining is not None else 0
        bounded_horizon = horizon if horizon is not None else 0
        temporal_grounded = (
            remaining is not None
            and horizon is not None
            and bool(self.resource_candidates)
        )
        resource_scheduling_grounded = (
            not self.transferred_action_algebra_active
            or self.operator_applications > 0
            or self.contextual_transitions > 0
        )
        target_cells: tuple[Point, ...]
        path: tuple[int, ...]
        selected_resource: Component | None = None

        resource_rearm_active = (
            bool(self.resource_rearm_cells)
            and bool(self.current_view_hosts)
            and bool(self.operator_effects)
            and self.contextual_transitions > 0
            and self.current_anchor is not None
            and _covers(
                self.current_anchor,
                self.mask,
                self.resource_rearm_cells,
            )
        )
        if self.resource_rearm_cells and not resource_rearm_active:
            self.resource_rearm_cells = ()
        active = next(
            (
                resource
                for resource in self.resource_candidates
                if _resource_key(resource) == self.active_resource
            ),
            None,
        )
        if resource_rearm_active:
            target_cells = self.resource_rearm_cells
            path = self._leave_contact_path(
                frame,
                target_cells,
                legal_action_ids,
            )
            mode = "resource-rearm"
        elif self.active_resource is not None and active is None:
            self.active_resource = None
            self.diagnostic = "active-resource-role-disappeared"
            return None
        elif active is not None:
            selected_resource = active
            target_cells = active.cells
            path = self._path(frame, target_cells)
            mode = "resource-reset"
            if not path:
                self.active_resource = None
                self.diagnostic = "active-resource-path-falsified"
                return None
        elif phase_equal and self.goal_cells:
            target_cells = self.goal_cells
            mode = "terminal"
            path = self._path(frame, target_cells)
            if (
                temporal_grounded
                and resource_scheduling_grounded
                and path
                and len(path) > bounded_remaining
                and (
                    option := self._resource_option(
                        frame,
                        self.goal_cells,
                        remaining=bounded_remaining,
                        horizon=bounded_horizon,
                    )
                )
                is not None
            ):
                selected_resource, path = option
                target_cells = selected_resource.cells
                mode = "resource-reset"
        elif (
            self.operator_cells
            and self.operator_applications < self.max_operator_applications
        ):
            target_cells = self.operator_cells
            if on_operator:
                path = self._operator_rearm_path(frame, legal_action_ids)
                mode = "operator-rearm"
                if temporal_grounded and resource_scheduling_grounded and path:
                    resource_paths = tuple(
                        candidate
                        for resource in self.resource_candidates
                        if (candidate := self._path(frame, resource.cells))
                    )
                    nearest_resource = min(
                        (len(candidate) for candidate in resource_paths),
                        default=None,
                    )
                    if (
                        nearest_resource is not None
                        and len(path) + nearest_resource > bounded_remaining
                        and (
                            option := self._resource_option(
                                frame,
                                self.operator_cells,
                                remaining=bounded_remaining,
                                horizon=bounded_horizon,
                            )
                        )
                        is not None
                    ):
                        selected_resource, path = option
                        target_cells = selected_resource.cells
                        mode = "resource-reset"
            else:
                path = self._path(frame, target_cells)
                mode = "operator"
                sparse_information_probe = (
                    bool(self.current_view_hosts)
                    and self.current_pattern is not None
                    and self.goal_pattern is not None
                    and self.current_pattern != self.goal_pattern
                    and self.current_glyph_color is not None
                    and self.goal_glyph_color is not None
                    and self.current_glyph_color != self.goal_glyph_color
                    and target_cells not in self.operator_effects
                    and self._is_sparse_arity_candidate(frame, target_cells)
                )
                contextual_resource_chain = (
                    bool(self.current_view_hosts)
                    and bool(self.operator_effects)
                    and target_cells not in self.operator_effects
                    and self.contextual_transitions > 0
                )
                unknown_factor_target = (
                    target_cells not in self.operator_effects
                    and self.active_operator is None
                    and not sparse_information_probe
                    and (
                        (
                            len(self.operator_candidates) > 1
                            and bounded_remaining < bounded_horizon
                        )
                        or contextual_resource_chain
                    )
                )
                if (
                    temporal_grounded
                    and resource_scheduling_grounded
                    and path
                    and (
                        len(path) >= bounded_remaining
                        or unknown_factor_target
                    )
                    and (
                        option := self._resource_option(
                            frame,
                            self.operator_cells,
                            remaining=bounded_remaining,
                            horizon=bounded_horizon,
                            prefer_nearest=contextual_resource_chain,
                        )
                    )
                    is not None
                ):
                    selected_resource, path = option
                    target_cells = selected_resource.cells
                    mode = "resource-reset"
                elif (
                    len(self.operator_candidates) > 1
                    and target_cells not in self.operator_effects
                    and resource_scheduling_grounded
                ):
                    self.active_operator = target_cells
        else:
            self.diagnostic = "missing-phase-goal-or-operator"
            return None
        if not path:
            if mode == "operator" and self.active_operator == target_cells:
                self.active_operator = None
            self.diagnostic = f"no-{mode}-path"
            return None
        action_id = path[0]
        if action_id not in legal_action_ids:
            self.diagnostic = "planned-action-not-legal"
            return None
        displacement = self.action_effects[action_id]
        self.pending_source = self.current_anchor
        self.pending_anchor = self.contextual_edges.get(
            (self.current_anchor, action_id),
            (
                self.current_anchor[0] + displacement[0],
                self.current_anchor[1] + displacement[1],
            ),
        )
        self.pending_action = action_id
        self.pending_resource_back_edge = None
        if mode == "resource-rearm":
            inverse_actions = tuple(
                candidate
                for candidate, effect in self.action_effects.items()
                if effect == (-displacement[0], -displacement[1])
            )
            if len(inverse_actions) == 1:
                self.pending_resource_back_edge = (
                    self.pending_anchor,
                    inverse_actions[0],
                )
        self.pending_resource = (
            _resource_key(selected_resource) if selected_resource is not None else None
        )
        if selected_resource is not None:
            self.active_resource = _resource_key(selected_resource)
        self.selections += 1
        self.compilations += 1
        self.last_plan_length = len(path)
        self.diagnostic = f"executing-{mode}-option"
        return action_id
