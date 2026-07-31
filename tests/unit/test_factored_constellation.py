from reflector.core.factored_constellation import (
    FactorMask,
    FactorScene,
    learn_factor_mask,
    solve_factor_exact_cover,
)


def test_learns_factor_when_selector_is_occluded_by_same_color() -> None:
    before = [[5 for _x in range(7)] for _y in range(7)]
    after = [[5 for _x in range(7)] for _y in range(7)]
    for x in range(1, 6):
        before[4][x] = 8
        after[3][x] = 8
    before[4][3] = 0
    scene = FactorScene(8, frozenset({(1, 1), (5, 1)}), 0, (3, 4))

    mask = learn_factor_mask(
        tuple(tuple(row) for row in before),
        tuple(tuple(row) for row in after),
        scene,
        (0, -1),
    )

    assert mask is not None
    assert mask.home_anchor == (3, 4)
    assert mask.offsets == frozenset(
        {(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0)}
    )


def test_solves_unique_minimum_cost_product_exact_cover() -> None:
    landmarks = frozenset(
        {
            (6, 6),
            (45, 6),
            (9, 27),
            (21, 21),
            (21, 39),
            (33, 33),
            (48, 30),
            (51, 15),
        }
    )
    line = FactorMask(
        (30, 45),
        frozenset((x, 0) for x in range(-21, 22)),
    )
    x_11 = FactorMask(
        (18, 48),
        frozenset(
            (x, y)
            for x in range(-11, 12)
            for y in range(-11, 12)
            if abs(x) == abs(y) and (x, y) != (0, 0)
        ),
    )
    diamond_12 = FactorMask(
        (45, 48),
        frozenset(
            (x, y)
            for x in range(-12, 13)
            for y in range(-12, 13)
            if abs(x) + abs(y) == 12
        ),
    )

    goals = solve_factor_exact_cover(
        (line, x_11, diamond_12),
        landmarks,
        width=64,
        height=64,
        step=3,
    )

    assert goals is not None
    assert tuple(goal.target_anchor for goal in goals) == (
        (27, 6),
        (42, 24),
        (18, 30),
    )
    assert set().union(
        *(goal.covered_landmarks for goal in goals)
    ) == landmarks
