from reflector.core.deformable_constellation import (
    compile_deformable_constellation_plan,
)
from reflector.core.scheme_category import TranslationMorphism


def _deformable_frame() -> tuple[tuple[int, ...], ...]:
    frame = [[5 for _x in range(64)] for _y in range(64)]
    frame[63] = [15 for _x in range(64)]
    groups = {
        9: {(9, 9), (12, 6), (12, 27), (30, 9)},
        11: {(45, 30), (54, 30), (45, 57), (54, 57)},
    }
    for color, points in groups.items():
        for x, y in points:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    frame[y + dy][x + dx] = 4
            frame[y][x] = color
    obstacle_rows = {
        28: range(28, 36),
        29: (*range(28, 31), *range(33, 36)),
        30: (28, 29, 34, 35),
        31: (28, 35),
        32: (28, 35),
        33: (28, 29, 34, 35),
        34: (*range(28, 31), *range(33, 36)),
        35: range(28, 36),
    }
    for y, xs in obstacle_rows.items():
        for x in xs:
            frame[y][x] = 1
    for x in range(36, 61):
        frame[15][x] = 9
    for y in range(3, 28):
        frame[y][48] = 9
    for x in range(6, 25):
        frame[39][x] = 11
        frame[57][x] = 11
    for y in range(40, 57):
        frame[y][6] = 11
        frame[y][24] = 11
    frame[48][15] = 0
    return tuple(tuple(row) for row in frame)


def test_compiles_conserved_segment_and_loop_factor_options() -> None:
    plan = compile_deformable_constellation_plan(
        _deformable_frame(),
        (
            TranslationMorphism(1, (0, -3)),
            TranslationMorphism(2, (0, 3)),
            TranslationMorphism(3, (-3, 0)),
            TranslationMorphism(4, (3, 0)),
        ),
        switch_action=5,
    )

    assert plan.status == "solved"
    assert plan.cross_color == 9
    assert plan.loop_color == 11
    assert len(plan.actions) == 57
    assert plan.actions[:6] == (5, 2, 2, 2, 2, 2)
    assert plan.actions[-2:] == (1, 1)


def test_abstains_when_loop_perimeter_is_not_conserved() -> None:
    mutable = [list(row) for row in _deformable_frame()]
    mutable[57][54] = 5

    plan = compile_deformable_constellation_plan(
        tuple(tuple(row) for row in mutable),
        (
            TranslationMorphism(1, (0, -3)),
            TranslationMorphism(2, (0, 3)),
            TranslationMorphism(3, (-3, 0)),
            TranslationMorphism(4, (3, 0)),
        ),
        switch_action=5,
    )

    assert plan.actions == ()
