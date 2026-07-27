import pytest

from reflector import (
    Atom,
    Event,
    ObjectState,
    Scene,
    SchemaStore,
    TransformationSystem,
    Transition,
)


def _learn_movement(
    store: SchemaStore,
    *,
    action: int,
    dx: int,
    dy: int,
    offset: int,
) -> None:
    for repetition in range(2):
        store.observe(
            Transition(
                before_index=offset + repetition,
                after_index=offset + repetition + 1,
                context=(Atom("layout", (str(offset + repetition),)),),
                action_id=action,
                action_data=(),
                result=(Event("object_moved", "piece", (str(dx), str(dy))),),
            )
        )


def _system() -> TransformationSystem:
    schemas = SchemaStore()
    for offset, (action, dx, dy) in enumerate(
        ((1, 1, 0), (2, -1, 0), (3, 0, 1), (4, 0, -1))
    ):
        _learn_movement(
            schemas,
            action=action,
            dx=dx,
            dy=dy,
            offset=offset * 10,
        )
    system = TransformationSystem()
    system.reflect(schemas)
    return system


def test_transformations_compose_reverse_and_pass_finite_laws() -> None:
    system = _system()
    assert len(system.transformations) == 4
    right = next(
        item
        for item in system.transformations.values()
        if item.parameters == (1, 0)
    )
    up = next(
        item
        for item in system.transformations.values()
        if item.parameters == (0, -1)
    )
    left = system.inverse(right)
    assert left is not None
    assert left.parameters == (-1, 0)

    composite = system.compose(right, up)
    assert composite.parameters == (1, -1)
    assert composite.components == (
        right.transformation_id,
        up.transformation_id,
    )

    laws = system.law_report()
    assert laws.passed
    assert laws.transformations_checked == 4
    assert laws.composable_pairs_checked > 0
    assert laws.composable_triples_checked > 0

    first = next(
        item
        for item in system.morphisms.values()
        if item.domain == right.transformation_id
        and item.codomain == up.transformation_id
    )
    with pytest.raises(ValueError, match="endpoints"):
        system.compose_morphisms(first, first)


def test_modal_reachability_is_checked_against_a_finite_state_graph() -> None:
    system = _system()
    possible = system.modal_reachability(
        start=(0, 0),
        target=(2, 1),
        bounds=(0, 0, 2, 2),
        max_depth=8,
    )
    assert possible.possible
    assert len(possible.shortest_actions) == 3
    assert possible.reachable_states > 1

    schemas = SchemaStore()
    _learn_movement(schemas, action=1, dx=1, dy=0, offset=0)
    _learn_movement(schemas, action=2, dx=-1, dy=0, offset=10)
    horizontal = TransformationSystem()
    horizontal.reflect(schemas)
    impossible = horizontal.modal_reachability(
        start=(0, 0),
        target=(0, 1),
        bounds=(0, 0, 2, 1),
        max_depth=8,
    )
    assert not impossible.possible
    assert impossible.impossible_within_bounds


def test_touching_goal_requires_level_evidence_and_projects_known_effect() -> None:
    system = _system()
    mover = ObjectState(
        object_id="piece",
        color=2,
        area=1,
        bbox=(1, 1, 1, 1),
        centroid=(1, 1),
    )
    target = ObjectState(
        object_id="target",
        color=8,
        area=1,
        bbox=(3, 1, 3, 1),
        centroid=(3, 1),
    )
    scene = Scene(
        index=0,
        state="NOT_FINISHED",
        levels_completed=0,
        available_actions=(1,),
        objects=(mover, target),
        facts=(),
        frame_digest="before",
    )
    transition = Transition(
        before_index=0,
        after_index=1,
        context=(),
        action_id=1,
        action_data=(),
        result=(Event("level_advanced", "game", ("0", "1")),),
    )
    created = system.observe_goal(transition, scene)
    assert created

    plan = system.plan_touching(
        Scene(
            index=1,
            state="NOT_FINISHED",
            levels_completed=1,
            available_actions=(1, 2, 3, 4),
            objects=(
                ObjectState(
                    object_id="piece",
                    color=2,
                    area=1,
                    bbox=(1, 1, 1, 1),
                    centroid=(1, 1),
                ),
                ObjectState(
                    object_id="target",
                    color=8,
                    area=1,
                    bbox=(4, 3, 4, 3),
                    centroid=(4, 3),
                ),
            ),
            facts=(),
            frame_digest="held-out",
        ),
        (1, 2, 3, 4),
        max_depth=6,
        max_expansions=64,
    )
    assert plan is not None
    assert len(plan[0]) == 4
