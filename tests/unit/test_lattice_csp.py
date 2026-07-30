import pytest

from reflector.core.lattice_csp import (
    ClickEffectModel,
    ClickTransition,
    ColorCycle,
    LatticeState,
    OffsetEffect,
    RelationConstraint,
    SolveStatus,
    learn_click_effect_model,
    solve_click_csp,
)


def test_color_cycle_wraps_and_rejects_values_outside_domain() -> None:
    cycle = ColorCycle.create((3, 8, 13))

    assert cycle.advance(13) == 3
    assert cycle.advance(3, 2) == 13
    assert cycle.delta(13, 8) == 2
    with pytest.raises(ValueError, match="outside"):
        cycle.advance(99)


def test_click_effect_learning_uses_relative_offsets_at_boundaries() -> None:
    cycle = ColorCycle.create((3, 8, 13))
    initial = LatticeState.create({(4, 1): 3, (4, 4): 3, (4, 7): 3})
    top_after = LatticeState.create({(4, 1): 8, (4, 4): 3, (4, 7): 3})
    middle_after = LatticeState.create({(4, 1): 8, (4, 4): 8, (4, 7): 3})

    model = learn_click_effect_model(
        cycle,
        (
            ClickTransition((4, 1), initial, top_after),
            ClickTransition((4, 4), initial, middle_after),
        ),
    )

    assert model is not None
    assert tuple(
        (
            effect.offset,
            effect.delta,
            effect.confirmations,
            effect.opportunities,
        )
        for effect in model.effects
    ) == (
        ((0, -3), 1, 1, 1),
        ((0, 0), 1, 2, 2),
    )
    assert model.apply(initial, (4, 4)) == middle_after


def test_click_effect_learning_rejects_contextual_effect_conflicts() -> None:
    cycle = ColorCycle.create((2, 7))
    initial = LatticeState.create({(1, 1): 2, (1, 3): 2})
    changed = LatticeState.create({(1, 1): 7, (1, 3): 7})
    conflicting = LatticeState.create({(1, 1): 2, (1, 3): 7})

    assert (
        learn_click_effect_model(
            cycle,
            (
                ClickTransition((1, 3), initial, changed),
                ClickTransition((1, 3), initial, conflicting),
            ),
        )
        is None
    )


def test_solver_inverts_offset_effects_and_mixed_relations() -> None:
    cycle = ColorCycle.create((4, 9))
    model = ClickEffectModel(
        cycle=cycle,
        effects=(
            OffsetEffect((0, -3), 1, 2, 2),
            OffsetEffect((0, 0), 1, 3, 3),
        ),
        transition_count=3,
    )
    state = LatticeState.create(
        {
            (2, 1): 4,
            (2, 4): 4,
            (2, 7): 4,
            (8, 1): 4,
            (8, 4): 4,
        }
    )
    constraints = (
        RelationConstraint.equal_color((2, 1), 4),
        RelationConstraint.different_points((2, 4), (2, 1)),
        RelationConstraint.equal_color((2, 7), 9),
        RelationConstraint.different_color((8, 1), 9),
        RelationConstraint.equal_color((8, 4), 9),
    )

    result = solve_click_csp(
        state,
        model,
        constraints,
        max_clicks=5,
    )

    assert result.status is SolveStatus.SOLVED
    assert result.plan is not None
    assert result.plan.actions == ((2, 7), (8, 1), (8, 4))
    assert all(
        constraint.holds(result.plan.final_state) for constraint in constraints
    )
    assert result.plan.minimal_within_model


def test_solver_supports_multiple_steps_in_nonbinary_cycle() -> None:
    cycle = ColorCycle.create((2, 5, 8))
    model = ClickEffectModel(
        cycle=cycle,
        effects=(OffsetEffect((0, 0), 1, 1, 1),),
        transition_count=1,
    )
    state = LatticeState.create({(7, 11): 2})
    constraint = RelationConstraint.equal_color((7, 11), 8)

    solved = solve_click_csp(
        state,
        model,
        (constraint,),
        max_clicks=2,
    )
    bounded = solve_click_csp(
        state,
        model,
        (constraint,),
        max_clicks=1,
    )

    assert solved.status is SolveStatus.SOLVED
    assert solved.plan is not None
    assert solved.plan.actions == ((7, 11), (7, 11))
    assert bounded.status is SolveStatus.NO_PLAN_WITHIN_ACTION_BOUND
    assert bounded.plan is None


def test_solver_reports_search_bound_exhaustion_deterministically() -> None:
    cycle = ColorCycle.create((0, 1))
    model = ClickEffectModel(
        cycle=cycle,
        effects=(OffsetEffect((0, 0), 1, 1, 1),),
        transition_count=1,
    )
    state = LatticeState.create({(0, 0): 0, (1, 0): 0})
    constraints = (
        RelationConstraint.equal_color((0, 0), 1),
        RelationConstraint.equal_color((1, 0), 1),
    )

    result = solve_click_csp(
        state,
        model,
        constraints,
        max_clicks=2,
        max_search_nodes=1,
    )

    assert result.status is SolveStatus.SEARCH_BOUND_EXHAUSTED
    assert result.plan is None
