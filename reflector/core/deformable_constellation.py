"""Compile obstacle-mediated options for conserved segment and loop factors."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .constellation_alignment import _landmark_groups
from .reference_constellation import _components
from .scheme_category import TranslationMorphism

type Frame = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]


@dataclass(frozen=True, slots=True)
class DeformableConstellationPlan:
    """One bounded factor/obstacle option, or a conservative abstention."""

    actions: tuple[int, ...]
    cross_color: int | None
    loop_color: int | None
    status: str


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
    magnitudes = {
        abs(dx) + abs(dy) for dx, dy in by_displacement
    }
    if len(magnitudes) != 1:
        return None
    step = next(iter(magnitudes))
    required = {(0, -step), (0, step), (-step, 0), (step, 0)}
    if set(by_displacement) != required:
        return None
    return by_displacement, step


def _repeat(
    actions: list[int],
    action_id: int,
    count: int,
) -> bool:
    if not 0 <= count <= 32:
        return False
    actions.extend([action_id] * count)
    return True


def compile_deformable_constellation_plan(
    frame: Frame,
    morphisms: tuple[TranslationMorphism, ...],
    *,
    switch_action: int,
) -> DeformableConstellationPlan:
    """Compile a coordinate-free obstacle differential and loop deformation.

    The admitted scene contains exactly two same-color mover/landmark pairs:
    one orthogonal product of equal conserved segments and one rectangular
    conserved-perimeter loop. A third compact component is a fixed obstacle.
    """

    failure = DeformableConstellationPlan((), None, None, "not-grounded")
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
    height = len(frame)
    width = len(frame[0])
    counts = Counter(value for row in frame for value in row)
    background = counts.most_common(1)[0][0]
    groups = _landmark_groups(frame, background)
    if len(groups) != 2 or any(len(points) != 4 for points in groups.values()):
        return failure
    selector_candidates = [
        (value, (x, y))
        for y, row in enumerate(frame)
        for x, value in enumerate(row)
        if counts[value] == 1 and value not in {background, *groups}
    ]
    if len(selector_candidates) != 1:
        return failure
    _selector_color, selector = selector_candidates[0]
    movers: dict[int, frozenset[Point]] = {}
    for color in groups:
        components = _components(frame, color)
        if not components or len(components[0]) < 16:
            return failure
        movers[color] = components[0]

    cross_color: int | None = None
    loop_color: int | None = None
    cross_center: Point | None = None
    cross_radius = 0
    loop_box: tuple[int, int, int, int] | None = None
    for color, points in movers.items():
        box = _bbox(points)
        mover_width = box[2] - box[0] + 1
        mover_height = box[3] - box[1] + 1
        rows = Counter(y for _x, y in points)
        columns = Counter(x for x, _y in points)
        row, row_support = rows.most_common(1)[0]
        column, column_support = columns.most_common(1)[0]
        if (
            mover_width == mover_height
            and row_support == mover_width
            and column_support == mover_height
            and len(points) == mover_width + mover_height - 1
        ):
            cross_color = color
            cross_center = column, row
            cross_radius = (mover_width - 1) // 2
        elif len(points) == 2 * mover_width + 2 * mover_height - 4:
            loop_color = color
            loop_box = box
    if (
        cross_color is None
        or loop_color is None
        or cross_center is None
        or loop_box is None
    ):
        return failure

    excluded = {background, *groups, _selector_color}
    obstacle_candidates: list[frozenset[Point]] = []
    for color in sorted(counts):
        if color in excluded:
            continue
        for component in _components(frame, color):
            box = _bbox(component)
            if (
                len(component) >= 8
                and box[2] - box[0] + 1 < width
                and box[3] - box[1] + 1 < height
            ):
                obstacle_candidates.append(component)
    if not obstacle_candidates:
        return failure
    obstacle = max(obstacle_candidates, key=lambda item: (len(item), _bbox(item)))
    obstacle_box = _bbox(obstacle)
    ox0, oy0, ox1, oy1 = obstacle_box

    cross_landmarks = groups[cross_color]
    horizontal_rows = Counter(y for _x, y in cross_landmarks)
    vertical_columns = Counter(x for x, _y in cross_landmarks)
    horizontal_y = next(
        (value for value, support in horizontal_rows.items() if support == 2),
        None,
    )
    vertical_x = next(
        (value for value, support in vertical_columns.items() if support == 2),
        None,
    )
    if horizontal_y is None or vertical_x is None:
        return failure
    horizontal_xs = sorted(
        x for x, y in cross_landmarks if y == horizontal_y
    )
    vertical_ys = sorted(
        y for x, y in cross_landmarks if x == vertical_x
    )
    if len(horizontal_xs) != 2 or len(vertical_ys) != 2:
        return failure
    cross_target_h = horizontal_xs[0] + cross_radius, horizontal_y
    cross_target_v = vertical_x, vertical_ys[0] + cross_radius
    relative = (
        cross_target_v[0] - cross_target_h[0],
        cross_target_v[1] - cross_target_h[1],
    )
    if (
        relative[0] >= 0
        or relative[1] <= 0
        or -relative[0] != relative[1]
        or relative[1] % step
    ):
        return failure
    differential_steps = relative[1] // step
    if differential_steps != (ox1 - ox0 + step) // step:
        return failure

    loop_landmarks = groups[loop_color]
    target_loop_box = (
        min(x for x, _y in loop_landmarks),
        min(y for _x, y in loop_landmarks),
        max(x for x, _y in loop_landmarks),
        max(y for _x, y in loop_landmarks),
    )
    if loop_landmarks != {
        (target_loop_box[0], target_loop_box[1]),
        (target_loop_box[2], target_loop_box[1]),
        (target_loop_box[0], target_loop_box[3]),
        (target_loop_box[2], target_loop_box[3]),
    }:
        return failure
    loop_width = loop_box[2] - loop_box[0] + 1
    loop_height = loop_box[3] - loop_box[1] + 1
    target_width = target_loop_box[2] - target_loop_box[0] + 1
    target_height = target_loop_box[3] - target_loop_box[1] + 1
    if (
        2 * loop_width + 2 * loop_height
        != 2 * target_width + 2 * target_height
        or (loop_width - target_width) % step
        or target_height <= loop_height
    ):
        return failure

    cross_actions: list[int] = []
    contact_y = oy0 + (-oy0 % step)
    if cross_center[0] - cross_radius != ox1 + 1:
        return failure
    if not _repeat(
        cross_actions,
        down,
        (contact_y - cross_center[1]) // step,
    ):
        return failure
    if not _repeat(cross_actions, left, differential_steps):
        return failure
    if not _repeat(
        cross_actions,
        up,
        (contact_y - cross_center[1]) // step,
    ):
        return failure
    vertical_after_shear = cross_center[0] - relative[1]
    staging_vertical_x = ox0 - 1
    staging_shift = (vertical_after_shear - staging_vertical_x) // step
    if (
        vertical_after_shear - staging_vertical_x < 0
        or (vertical_after_shear - staging_vertical_x) % step
        or not _repeat(cross_actions, left, staging_shift)
    ):
        return failure
    staging_h_x = cross_center[0] - staging_shift * step
    staging_h_y = oy0 - 1
    if (
        staging_h_y - cross_center[1] < 0
        or (staging_h_y - cross_center[1]) % step
        or not _repeat(
            cross_actions,
            down,
            (staging_h_y - cross_center[1]) // step,
        )
        or not _repeat(cross_actions, down, differential_steps)
    ):
        return failure
    if (
        staging_h_y - cross_target_h[1] < 0
        or (staging_h_y - cross_target_h[1]) % step
        or not _repeat(
            cross_actions,
            up,
            (staging_h_y - cross_target_h[1]) // step,
        )
        or staging_h_x - cross_target_h[0] < 0
        or (staging_h_x - cross_target_h[0]) % step
        or not _repeat(
            cross_actions,
            left,
            (staging_h_x - cross_target_h[0]) // step,
        )
    ):
        return failure

    loop_actions: list[int] = []
    approach_top = oy1 - step + 1
    if (
        loop_box[1] - approach_top < 0
        or (loop_box[1] - approach_top) % step
        or not _repeat(
            loop_actions,
            up,
            (loop_box[1] - approach_top) // step,
        )
    ):
        return failure
    approach_right = ox0 - 1
    if (
        approach_right - loop_box[2] < 0
        or (approach_right - loop_box[2]) % step
        or not _repeat(
            loop_actions,
            right,
            (approach_right - loop_box[2]) // step,
        )
    ):
        return failure
    deform_steps = (loop_width - target_width) // step
    if not _repeat(loop_actions, right, deform_steps):
        return failure
    deformed_left = (
        loop_box[0]
        + (approach_right - loop_box[2])
        + deform_steps * step
    )
    deformed_top = approach_top - ((deform_steps + 1) // 2) * step
    clear_steps = (oy1 + 1 - deformed_top + step - 1) // step
    cleared_top = deformed_top + clear_steps * step
    if (
        not _repeat(loop_actions, down, clear_steps)
        or target_loop_box[0] - deformed_left < 0
        or (target_loop_box[0] - deformed_left) % step
        or not _repeat(
            loop_actions,
            right,
            (target_loop_box[0] - deformed_left) // step,
        )
        or cleared_top - target_loop_box[1] < 0
        or (cleared_top - target_loop_box[1]) % step
        or not _repeat(
            loop_actions,
            up,
            (cleared_top - target_loop_box[1]) // step,
        )
    ):
        return failure

    loop_selected = (
        loop_box[0] <= selector[0] <= loop_box[2]
        and loop_box[1] <= selector[1] <= loop_box[3]
    )
    cross_box = _bbox(movers[cross_color])
    cross_selected = (
        cross_box[0] <= selector[0] <= cross_box[2]
        and cross_box[1] <= selector[1] <= cross_box[3]
    )
    if loop_selected == cross_selected:
        return failure
    actions = (
        (switch_action, *cross_actions, switch_action, *loop_actions)
        if loop_selected
        else (*cross_actions, switch_action, *loop_actions)
    )
    return DeformableConstellationPlan(
        tuple(actions),
        cross_color,
        loop_color,
        "solved",
    )
