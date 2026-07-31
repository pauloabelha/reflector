from reflector.core.reference_constellation import (
    _unbounded_central_completion,
    compile_composite_reference_plan,
)
from reflector.core.scheme_category import TranslationMorphism


def test_unbounded_completion_recovers_boundary_clipped_arm() -> None:
    anchor = (54, 36)
    visible = frozenset(
        {(x, 36) for x in range(41, 64)}
        | {(54, y) for y in range(23, 50)}
    )

    completed = _unbounded_central_completion(visible, anchor)

    assert (67, 36) in completed
    assert (54, 23) in completed
    assert (54, 49) in completed


def _level_five_composite_frame() -> tuple[tuple[int, ...], ...]:
    frame = [[5 for _x in range(64)] for _y in range(64)]
    frame[63] = [15 for _x in range(64)]
    for left, top, color in (
        (3, 3, 11),
        (54, 3, 10),
        (3, 27, 14),
        (3, 52, 9),
        (54, 52, 8),
    ):
        for y in range(top, top + 6):
            for x in range(left, left + 6):
                frame[y][x] = 2
        for y in range(top + 1, top + 5):
            for x in range(left + 1, left + 5):
                frame[y][x] = color
    color_nine = {
        (21, 6),
        (39, 6),
        (33, 45),
        (24, 51),
        (45, 51),
        (33, 60),
    }
    color_eight = {(42, 36), (51, 27), (54, 42), (57, 33)}
    for (x, y), color in (
        *((point, 9) for point in color_nine),
        *((point, 8) for point in color_eight),
    ):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                frame[y + dy][x + dx] = 4
        frame[y][x] = color
    for offset in range(-11, 12):
        if offset:
            frame[42 + abs(offset)][24 + offset] = 11
            frame[42 - abs(offset)][24 + offset] = 11
    for offset in range(-9, 10):
        vertical = 9 - abs(offset)
        frame[18 + vertical][30 + offset] = 14
        frame[18 - vertical][30 + offset] = 14
    for x in range(40, 64):
        frame[33][x] = 12
    for y in range(19, 48):
        frame[y][54] = 12
    frame[42][24] = 0
    return tuple(tuple(row) for row in frame)


def test_composite_reference_jointly_solves_paint_cover_and_occlusion() -> None:
    plan = compile_composite_reference_plan(
        _level_five_composite_frame(),
        (
            TranslationMorphism(1, (0, -3)),
            TranslationMorphism(2, (0, 3)),
            TranslationMorphism(3, (-3, 0)),
            TranslationMorphism(4, (3, 0)),
        ),
    )

    assert plan.status == "solved"
    assert plan.selector_color == 0
    assert {
        (
            option.source_color,
            option.target_anchor,
            option.target_color,
            len(option.actions),
        )
        for option in plan.options
    } == {
        (11, (30, 15), 9, 17),
        (12, (33, 51), 9, 23),
        (14, (51, 36), 8, 21),
    }
