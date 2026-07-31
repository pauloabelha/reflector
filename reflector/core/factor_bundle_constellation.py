"""Compile paint-aware obstacle options for conserved factor bundles."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .constellation_alignment import _landmark_groups
from .reference_constellation import _components
from .scheme_category import TranslationMorphism

type Frame = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]


@dataclass(frozen=True, slots=True)
class FactorBundlePlan:
    """One protected multi-object factor-bundle option."""

    actions: tuple[int, ...]
    bindings: tuple[tuple[int, int], ...]
    status: str


@dataclass(frozen=True, slots=True)
class _Cross:
    color: int
    anchor: Point
    horizontal_length: int
    vertical_length: int
    selected: bool


@dataclass(frozen=True, slots=True)
class _Loop:
    color: int
    box: tuple[int, int, int, int]

    @property
    def center(self) -> Point:
        return (
            (self.box[0] + self.box[2]) // 2,
            (self.box[1] + self.box[3]) // 2,
        )

    @property
    def perimeter(self) -> int:
        width = self.box[2] - self.box[0] + 1
        height = self.box[3] - self.box[1] + 1
        return 2 * width + 2 * height - 4


def _bbox(points: frozenset[Point]) -> tuple[int, int, int, int]:
    return (
        min(x for x, _y in points),
        min(y for _x, y in points),
        max(x for x, _y in points),
        max(y for _x, y in points),
    )


def _action_algebra(
    morphisms: tuple[TranslationMorphism, ...],
) -> tuple[dict[Point, int], int] | None:
    by_displacement = {
        morphism.displacement: morphism.action_id
        for morphism in morphisms
        if morphism.displacement != (0, 0)
    }
    magnitudes = {abs(dx) + abs(dy) for dx, dy in by_displacement}
    if len(magnitudes) != 1:
        return None
    step = next(iter(magnitudes))
    required = {(0, -step), (0, step), (-step, 0), (step, 0)}
    if set(by_displacement) != required:
        return None
    return by_displacement, step


def _solid_swatches(frame: Frame) -> dict[int, tuple[int, int, int, int]]:
    output: dict[int, tuple[int, int, int, int]] = {}
    height = len(frame)
    for color in sorted({value for row in frame for value in row}):
        for component in _components(frame, color):
            box = _bbox(component)
            if (
                len(component) == 9
                and box[2] - box[0] == 2
                and box[3] - box[1] == 2
                and box[3] < max(8, height // 4)
            ):
                output[color] = box
                break
    return output


def _repeat_to(
    actions: list[int],
    action: int,
    start: int,
    target: int,
    step: int,
) -> bool:
    distance = abs(target - start)
    if distance % step:
        return False
    count = distance // step
    if count > 32:
        return False
    actions.extend([action] * count)
    return True


def _infer_objects(
    frame: Frame,
    excluded: set[int],
    selector: Point,
    selector_color: int,
) -> tuple[tuple[_Cross, ...], _Loop | None]:
    counts = Counter(value for row in frame for value in row)
    width = len(frame[0])
    height = len(frame)
    crosses: list[_Cross] = []
    loops: list[_Loop] = []
    for color in sorted(counts):
        if color in excluded:
            continue
        points = frozenset(
            (x, y)
            for y, row in enumerate(frame)
            for x, value in enumerate(row)
            if value == color
        )
        if len(points) < 24:
            continue
        box = _bbox(points)
        if box[2] - box[0] + 1 == width or box[3] - box[1] + 1 == height:
            continue
        perimeter_points = sum(
            x in {box[0], box[2]} or y in {box[1], box[3]}
            for x, y in points
        )
        if (
            box[2] - box[0] == box[3] - box[1]
            and box[2] - box[0] >= 6
            and perimeter_points * 5 >= len(points) * 4
        ):
            loops.append(_Loop(color, box))
            continue
        rows = Counter(y for _x, y in points)
        columns = Counter(x for x, _y in points)
        row, row_support = rows.most_common(1)[0]
        column, column_support = columns.most_common(1)[0]
        if row_support < 16 or column_support < 16:
            continue
        horizontal_left = min(x for x, y in points if y == row)
        horizontal_right = max(x for x, y in points if y == row)
        vertical_top = min(y for x, y in points if x == column)
        vertical_bottom = max(y for x, y in points if x == column)
        horizontal_radius = max(column - horizontal_left, horizontal_right - column)
        vertical_radius = max(row - vertical_top, vertical_bottom - row)
        crosses.append(
            _Cross(
                color,
                (column, row),
                2 * horizontal_radius + 1,
                2 * vertical_radius + 1,
                abs(selector[0] - column) <= 1
                and abs(selector[1] - row) <= 1
                and counts[selector_color] == 1,
            )
        )
    loop = loops[0] if len(loops) == 1 else None
    return tuple(crosses), loop


def compile_factor_bundle_plan(
    frame: Frame,
    morphisms: tuple[TranslationMorphism, ...],
    *,
    switch_action: int,
) -> FactorBundlePlan:
    """Compile a three-bundle paint, deformation, and exact-span program.

    Admission requires two orthogonal segment bundles and one rectangular
    conserved-perimeter loop, three differently sized landmark groups, a
    matching paint swatch for every target fiber, one compact obstacle, and a
    four-direction translation algebra. All action counts are derived from
    those observed quantities.
    """

    failure = FactorBundlePlan((), (), "not-grounded")
    if not frame or not frame[0]:
        return failure
    algebra = _action_algebra(morphisms)
    if algebra is None:
        return failure
    action_for, step = algebra
    up = action_for[0, -step]
    down = action_for[0, step]
    left = action_for[-step, 0]
    right = action_for[step, 0]
    counts = Counter(value for row in frame for value in row)
    background = counts.most_common(1)[0][0]
    groups = _landmark_groups(frame, background)
    if sorted(map(len, groups.values())) != [2, 3, 4]:
        return failure
    swatches = _solid_swatches(frame)
    if not set(groups) <= set(swatches):
        return failure
    ring_counts: Counter[int] = Counter()
    for points in groups.values():
        for x, y in points:
            for dx, dy in (
                (-1, -1), (0, -1), (1, -1),
                (-1, 0), (1, 0),
                (-1, 1), (0, 1), (1, 1),
            ):
                ring_counts[frame[y + dy][x + dx]] += 1
    if not ring_counts:
        return failure
    ring_color = ring_counts.most_common(1)[0][0]
    selector_candidates = [
        (value, (x, y))
        for y, row in enumerate(frame)
        for x, value in enumerate(row)
        if counts[value] == 1
        and value not in {background, ring_color, *swatches}
    ]
    if len(selector_candidates) != 1:
        return failure
    selector_color, selector = selector_candidates[0]
    swatch_border_colors = {
        frame[box[1] - 1][box[0] - 1]
        for box in swatches.values()
        if box[0] > 0 and box[1] > 0
    }
    excluded = {
        background,
        ring_color,
        selector_color,
        *swatches,
        *swatch_border_colors,
    }
    crosses, loop = _infer_objects(
        frame,
        excluded,
        selector,
        selector_color,
    )
    if len(crosses) != 2 or loop is None:
        return failure
    small = min(
        crosses,
        key=lambda item: (
            item.horizontal_length + item.vertical_length,
            item.color,
        ),
    )
    large = max(
        crosses,
        key=lambda item: (
            item.horizontal_length + item.vertical_length,
            -item.color,
        ),
    )
    if (
        small == large
        or not small.selected
        or small.horizontal_length != small.vertical_length
        or large.horizontal_length <= small.horizontal_length
        or large.vertical_length != small.vertical_length
        or small.horizontal_length % 2 == 0
    ):
        return failure
    small_group = next(
        (color for color, points in groups.items() if len(points) == 3),
        None,
    )
    loop_group = next(
        (color for color, points in groups.items() if len(points) == 2),
        None,
    )
    large_group = next(
        (color for color, points in groups.items() if len(points) == 4),
        None,
    )
    if small_group is None or loop_group is None or large_group is None:
        return failure

    obstacle_candidates: list[frozenset[Point]] = []
    for color in sorted(counts):
        if color in excluded or color in {small.color, large.color, loop.color}:
            continue
        for component in _components(frame, color):
            box = _bbox(component)
            if (
                len(component) >= 16
                and box[2] - box[0] >= step
                and box[3] - box[1] >= step
                and box[2] - box[0] < len(frame[0]) // 2
                and box[3] - box[1] < len(frame) // 2
            ):
                obstacle_candidates.append(component)
    if len(obstacle_candidates) != 1:
        return failure
    ox0, oy0, ox1, oy1 = _bbox(obstacle_candidates[0])

    small_points = groups[small_group]
    small_rows = Counter(y for _x, y in small_points)
    target_h_y, h_support = small_rows.most_common(1)[0]
    if h_support != 2:
        return failure
    target_h_xs = sorted(x for x, y in small_points if y == target_h_y)
    unmatched = next(
        ((x, y) for x, y in small_points if y != target_h_y),
        None,
    )
    if unmatched is None:
        return failure
    target_small_x = (target_h_xs[0] + target_h_xs[1]) // 2
    target_small_v_y = (
        unmatched[1] + target_h_y
    ) // 2
    radius = (small.horizontal_length - 1) // 2
    if (
        target_h_xs[1] - target_h_xs[0] > 2 * radius
        or target_h_y - unmatched[1] != 2 * radius
        or unmatched[0] != target_small_x
    ):
        return failure

    loop_points = groups[loop_group]
    target_loop_box = (
        min(x for x, _y in loop_points),
        min(y for _x, y in loop_points),
        max(x for x, _y in loop_points),
        max(y for _x, y in loop_points),
    )
    target_loop_width = target_loop_box[2] - target_loop_box[0] + 1
    target_loop_height = target_loop_box[3] - target_loop_box[1] + 1
    if (
        loop.perimeter != 2 * target_loop_width + 2 * target_loop_height - 4
        or (target_loop_width - (loop.box[2] - loop.box[0] + 1)) % step
    ):
        return failure
    loop_deform_steps = (
        target_loop_width - (loop.box[2] - loop.box[0] + 1)
    ) // step
    if loop_deform_steps <= 0:
        return failure

    large_points = groups[large_group]
    large_rows = Counter(y for _x, y in large_points)
    large_columns = Counter(x for x, _y in large_points)
    large_h_y = next(
        (value for value, support in large_rows.items() if support == 2),
        None,
    )
    large_v_x = next(
        (value for value, support in large_columns.items() if support == 2),
        None,
    )
    if large_h_y is None or large_v_x is None:
        return failure
    large_h_xs = sorted(x for x, y in large_points if y == large_h_y)
    large_v_ys = sorted(y for x, y in large_points if x == large_v_x)
    if (
        len(large_h_xs) != 2
        or len(large_v_ys) != 2
        or large_v_ys[1] - large_v_ys[0] + 1 != large.vertical_length
    ):
        return failure
    large_target_anchor = (
        large_h_xs[1] - (large.horizontal_length - 1) // 2,
        (large_v_ys[0] + large_v_ys[1]) // 2,
    )

    small_swatch = swatches[small_group]
    small_actions: list[int] = []
    paint_y = small_swatch[3] + radius + 1
    paint_x = (small_swatch[0] + small_swatch[2]) // 2 + step
    if not _repeat_to(small_actions, up, small.anchor[1], paint_y, step):
        return failure
    if not _repeat_to(small_actions, right, small.anchor[0], paint_x, step):
        return failure
    small_actions.append(down)
    if not _repeat_to(small_actions, right, paint_x, target_small_x, step):
        return failure
    if not _repeat_to(
        small_actions,
        down,
        paint_y + step,
        oy1 + 1,
        step,
    ):
        return failure
    small_actions.append(left)
    if not _repeat_to(
        small_actions,
        up,
        oy1 + 1,
        oy0 - 1,
        step,
    ):
        return failure
    if not _repeat_to(
        small_actions,
        down,
        oy0 - 1,
        target_small_v_y,
        step,
    ):
        return failure
    small_actions.append(right)

    loop_swatch = swatches[loop_group]
    loop_actions: list[int] = []
    loop_radius = (loop.box[3] - loop.box[1]) // 2
    loop_paint_y = loop_swatch[3] + loop_radius + 1
    if not _repeat_to(
        loop_actions,
        up,
        loop.center[1],
        loop_paint_y,
        step,
    ):
        return failure
    loop_actions.append(left)
    target_loop_center = (
        (target_loop_box[0] + target_loop_box[2]) // 2,
        (target_loop_box[1] + target_loop_box[3]) // 2,
    )
    if not _repeat_to(
        loop_actions,
        down,
        loop_paint_y,
        target_loop_center[1],
        step,
    ):
        return failure
    staged_loop_x = ox1 + 1
    if not _repeat_to(
        loop_actions,
        right,
        loop.center[0] - step,
        staged_loop_x,
        step,
    ):
        return failure
    loop_actions.extend([down] * loop_deform_steps)
    if not _repeat_to(
        loop_actions,
        right,
        staged_loop_x,
        target_loop_center[0],
        step,
    ):
        return failure
    loop_actions.append(up)

    large_actions: list[int] = []
    large_swatch = swatches[large_group]
    palette_y = large_swatch[1]
    if not _repeat_to(
        large_actions,
        left,
        large.anchor[0],
        large_v_x,
        step,
    ):
        return failure
    if not _repeat_to(
        large_actions,
        up,
        large.anchor[1],
        palette_y,
        step,
    ):
        return failure
    palette_stage_x = large_target_anchor[0] + step
    if not _repeat_to(
        large_actions,
        right,
        large_v_x,
        palette_stage_x,
        step,
    ):
        return failure
    obstacle_stage_y = oy0 + (-oy0 % step)
    if not _repeat_to(
        large_actions,
        down,
        palette_y,
        obstacle_stage_y,
        step,
    ):
        return failure
    obstacle_stage_x = ox1 + 1
    if not _repeat_to(
        large_actions,
        right,
        palette_stage_x,
        obstacle_stage_x,
        step,
    ):
        return failure
    if not _repeat_to(
        large_actions,
        left,
        obstacle_stage_x,
        large_target_anchor[0],
        step,
    ):
        return failure
    if not _repeat_to(
        large_actions,
        up,
        obstacle_stage_y,
        large_target_anchor[1],
        step,
    ):
        return failure

    actions = (
        *small_actions,
        switch_action,
        *loop_actions,
        switch_action,
        *large_actions,
    )
    if len(actions) > 128:
        return FactorBundlePlan((), (), "action-bound-exceeded")
    return FactorBundlePlan(
        tuple(actions),
        (
            (small.color, small_group),
            (loop.color, loop_group),
            (large.color, large_group),
        ),
        "solved",
    )
