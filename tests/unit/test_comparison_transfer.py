from reflector import (
    Atom,
    ComparisonTransferSystem,
    Event,
    ObjectState,
    Scene,
    Transition,
)


def _scene(
    *,
    index: int,
    marker_color: int,
    mover: tuple[int, int] = (4, 4),
    target: tuple[int, int] | None = None,
) -> Scene:
    objects = [
        ObjectState(
            object_id="piece",
            color=2,
            area=1,
            bbox=(*mover, *mover),
            centroid=mover,
        ),
        ObjectState(
            object_id=f"marker-{marker_color}",
            color=marker_color,
            area=2,
            bbox=(0, 0, 1, 0),
            centroid=(0, 0),
            shape=((0, 0), (1, 0)),
        ),
    ]
    if target is not None:
        objects.append(
            ObjectState(
                object_id="target",
                color=8,
                area=1,
                bbox=(*target, *target),
                centroid=target,
            )
        )
    return Scene(
        index=index,
        state="NOT_FINISHED",
        levels_completed=0,
        available_actions=(1, 2, 3, 4),
        objects=tuple(objects),
        facts=(Atom("frame_bounds", ("0", "0", "8", "8")),),
        frame_digest=f"scene-{index}",
    )


def _observe(
    system: ComparisonTransferSystem,
    scene: Scene,
    action: int,
    vector: tuple[int, int],
    *,
    allow_transfer: bool = True,
) -> None:
    system.observe(
        Transition(
            before_index=scene.index,
            after_index=scene.index + 1,
            context=(),
            action_id=action,
            action_data=(),
            result=(
                Event(
                    "object_moved",
                    "piece",
                    (str(vector[0]), str(vector[1])),
                ),
            ),
        ),
        scene,
        allow_transfer=allow_transfer,
    )


def test_two_correspondences_infer_typed_held_out_operators_and_plan() -> None:
    system = ComparisonTransferSystem()
    canonical = _scene(index=0, marker_color=9)
    rotated = _scene(index=10, marker_color=10)
    for action, vector in enumerate(
        ((1, 0), (0, 1), (-1, 0), (0, -1)),
        start=1,
    ):
        _observe(system, canonical, action, vector)
    _observe(system, rotated, 1, (0, 1))
    _observe(system, rotated, 2, (-1, 0))

    rotated_domain = system.domain(rotated)
    canonical_domain = system.domain(canonical)
    assert rotated_domain is not None
    assert canonical_domain is not None
    comparison = system.comparisons[(canonical_domain, rotated_domain)]
    assert comparison.correspondences == (1, 2)

    inferred = system.operator(rotated_domain, 3)
    assert inferred is not None
    assert not inferred.observed
    assert inferred.parameters == (0, -1)
    assert inferred.source_operator_id is not None
    assert inferred.comparison_id == comparison.comparison_id
    assert len(inferred.evidence) >= 4

    system.touching_goal_evidence.add("known-adjacency")
    plan = system.plan_touching(
        _scene(
            index=12,
            marker_color=10,
            mover=(4, 4),
            target=(4, 2),
        ),
        (1, 2, 3, 4),
        max_depth=3,
        max_expansions=64,
    )
    assert plan is not None
    assert plan.actions == (3,)
    assert plan.inferred_operators == (inferred.operator_id,)


def test_transfer_ablation_retains_observations_but_no_inferred_operator() -> None:
    system = ComparisonTransferSystem()
    canonical = _scene(index=0, marker_color=9)
    transformed = _scene(index=10, marker_color=10)
    for action, vector in enumerate(
        ((1, 0), (0, 1), (-1, 0), (0, -1)),
        start=1,
    ):
        _observe(system, canonical, action, vector, allow_transfer=False)
    _observe(system, transformed, 1, (0, 1), allow_transfer=False)
    _observe(system, transformed, 2, (-1, 0), allow_transfer=False)

    assert len(system.observed_operators) == 6
    assert system.comparisons
    assert not system.inferred_operators


def test_inconsistent_calibrations_are_rejected_without_augmentation() -> None:
    system = ComparisonTransferSystem()
    canonical = _scene(index=0, marker_color=9)
    negative = _scene(index=10, marker_color=11)
    _observe(system, canonical, 1, (1, 0))
    _observe(system, canonical, 2, (0, 1))
    _observe(system, negative, 1, (0, 1))
    _observe(system, negative, 2, (-2, 0))

    canonical_domain = system.domain(canonical)
    negative_domain = system.domain(negative)
    assert canonical_domain is not None
    assert negative_domain is not None
    assert (canonical_domain, negative_domain) in system.rejected_comparisons
    assert (negative_domain, 3) not in system.inferred_operators
