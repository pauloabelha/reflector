from reflector.core.factored_constellation import (
    FactorMask,
    solve_factor_exact_cover,
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
