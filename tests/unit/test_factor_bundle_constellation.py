from reflector.core.factor_bundle_constellation import compile_factor_bundle_plan
from reflector.core.scheme_category import TranslationMorphism


def _frame() -> tuple[tuple[int, ...], ...]:
    grid = [[5 for _x in range(64)] for _y in range(64)]
    grid[63] = [15 for _x in range(64)]
    for index, color in enumerate((9, 11, 8, 14, 6)):
        x0 = 15 + index * 10
        for y in range(2, 7):
            for x in range(x0, x0 + 5):
                if x in {x0, x0 + 4} or y in {2, 6}:
                    grid[y][x] = 2
                else:
                    grid[y][x] = color
    groups = {
        8: {(3, 15), (9, 9), (9, 27), (36, 15)},
        9: {(39, 24), (57, 18)},
        11: {(39, 48), (45, 30), (51, 48)},
    }
    for color, points in groups.items():
        for x, y in points:
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    grid[y + dy][x + dx] = 4
            grid[y][x] = color
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
            grid[y][x] = 1
    for x in range(6, 43):
        grid[54][x] = 7
    for y in range(45, 64):
        grid[y][24] = 7
    for x in range(15, 28):
        grid[45][x] = 12
        grid[57][x] = 12
    for y in range(46, 57):
        grid[y][15] = 12
        grid[y][27] = 12
    for x in range(3, 22):
        grid[48][x] = 10
    for y in range(39, 58):
        grid[y][12] = 10
    grid[48][12] = 0
    return tuple(tuple(row) for row in grid)


def test_compiles_three_factor_bundles_from_observed_invariants() -> None:
    plan = compile_factor_bundle_plan(
        _frame(),
        (
            TranslationMorphism(1, (0, -3)),
            TranslationMorphism(2, (0, 3)),
            TranslationMorphism(3, (-3, 0)),
            TranslationMorphism(4, (3, 0)),
        ),
        switch_action=5,
    )

    assert plan.status == "solved"
    assert plan.bindings == ((10, 11), (12, 9), (7, 8))
    assert len(plan.actions) == 120
    assert plan.actions[:4] == (1, 1, 1, 1)
    assert plan.actions.count(5) == 2


def test_abstains_without_three_landmark_fibers() -> None:
    mutable = [list(row) for row in _frame()]
    mutable[24][39] = 5

    plan = compile_factor_bundle_plan(
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
