from reflector import STARTER_OBJECT_CONCEPTS, MindConfig
from reflector.exploration import EpistemicExplorer
from reflector.perception import SceneTracker
from reflector.symbolic import Observation


def _observation(frame: tuple[tuple[int, ...], ...]) -> Observation:
    return Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=frame,
    )


def test_disabled_visual_primitives_are_an_exact_scene_ablation() -> None:
    observation = _observation(
        (
            (0, 0, 0, 0),
            (0, 2, 3, 0),
            (0, 0, 0, 0),
        )
    )

    scene, _events = SceneTracker().perceive(observation)

    assert scene.primitives == ()
    assert all(fact.predicate != "visual_primitive" for fact in scene.facts)


def test_multicolor_sprite_is_one_composite_and_keeps_mono_fragments() -> None:
    observation = _observation(
        (
            (0, 0, 0, 0, 0),
            (0, 2, 3, 0, 0),
            (0, 2, 3, 0, 0),
            (0, 0, 0, 0, 0),
        )
    )

    scene, _events = SceneTracker(enable_visual_primitives=True).perceive(
        observation
    )
    composites = tuple(
        item for item in scene.primitives if item.kind == "multicolor_region"
    )

    assert len(scene.objects) == 2
    assert len(composites) == 1
    assert composites[0].area == 4
    assert composites[0].colors == (2, 3)
    assert len(composites[0].members) == 2
    assert {
        fact.arguments[1]
        for fact in scene.facts
        if fact.predicate == "object_concept"
    } >= {"persistent-component", "composite-region"}


def test_closed_ring_has_an_enclosure_and_open_ring_does_not() -> None:
    closed = _observation(
        (
            (0, 0, 0, 0, 0),
            (0, 1, 1, 1, 0),
            (0, 1, 0, 1, 0),
            (0, 1, 1, 1, 0),
            (0, 0, 0, 0, 0),
        )
    )
    opened = _observation(
        (
            (0, 0, 0, 0, 0),
            (0, 1, 0, 1, 0),
            (0, 1, 0, 1, 0),
            (0, 1, 1, 1, 0),
            (0, 0, 0, 0, 0),
        )
    )
    tracker = SceneTracker(enable_visual_primitives=True)

    closed_scene, _events = tracker.perceive(closed)
    opened_scene, _events = SceneTracker(
        enable_visual_primitives=True
    ).perceive(opened)

    closed_holes = tuple(
        item
        for item in closed_scene.primitives
        if item.kind == "enclosed_region"
    )
    opened_holes = tuple(
        item
        for item in opened_scene.primitives
        if item.kind == "enclosed_region"
    )
    assert len(closed_holes) == 1
    assert closed_holes[0].centroid == (2, 2)
    assert opened_holes == ()


def test_primitive_click_keeps_composite_provenance_and_scheme_credit() -> None:
    observation = _observation(
        (
            (0, 0, 0, 0, 0),
            (0, 2, 3, 0, 0),
            (0, 2, 3, 0, 0),
            (0, 0, 0, 0, 0),
        )
    )
    scene, _events = SceneTracker(enable_visual_primitives=True).perceive(
        observation
    )
    explorer = EpistemicExplorer(
        visual_primitives=True,
        starter_schemas=True,
        level_failures=1,
    )
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))
    grounding = explorer.pending_grounding

    assert choice.token.action_id == 6
    assert grounding is not None
    assert grounding.primitive_id is not None
    assert grounding.role.primitive_kind == "multicolor_region"
    assert grounding.role.color is None
    assert "scheme:starter:intervene-on-region" in (
        explorer.last_scheme_components
    )


def test_pragmatic_disequilibrium_activates_primitive_accommodation() -> None:
    observation = _observation(
        (
            (0, 0, 0, 0, 0),
            (0, 2, 2, 2, 0),
            (0, 2, 0, 2, 0),
            (0, 2, 2, 2, 0),
            (0, 0, 0, 0, 0),
        )
    )
    scene, _events = SceneTracker(enable_visual_primitives=True).perceive(
        observation
    )
    explorer = EpistemicExplorer(visual_primitives=True)
    plain = explorer._tokens(observation, scene, (6,))

    explorer.observe(observation, scene)
    explorer.select(
        observation,
        scene,
        (6,),
        pragmatic_disequilibrium=True,
    )
    accommodated = explorer._tokens(observation, scene, (6,))

    assert explorer.primitive_accommodation_active
    assert accommodated != plain
    assert explorer.pending_grounding is not None
    assert explorer.pending_grounding.primitive_id is not None


def test_passive_object_concepts_do_not_change_click_token_order() -> None:
    observation = _observation(
        (
            (0, 0, 0, 0, 0),
            (0, 2, 3, 0, 0),
            (0, 2, 3, 0, 0),
            (0, 0, 0, 0, 0),
        )
    )
    plain_scene, _events = SceneTracker().perceive(observation)
    rich_scene, _events = SceneTracker(
        enable_visual_primitives=True
    ).perceive(observation)
    explorer = EpistemicExplorer(visual_primitives=False)

    assert explorer._tokens(observation, plain_scene, (6,)) == explorer._tokens(
        observation,
        rich_scene,
        (6,),
    )


def test_starter_object_concepts_are_bounded_and_content_free() -> None:
    serialized = repr(STARTER_OBJECT_CONCEPTS).lower()

    assert len(STARTER_OBJECT_CONCEPTS) == 6
    assert all(item.complexity_cost > 0 for item in STARTER_OBJECT_CONCEPTS)
    assert all(
        forbidden not in serialized
        for forbidden in ("player", "goal", "key", "door", "game_id")
    )


def test_frame_difference_and_discrete_flow_are_typed_primitives() -> None:
    before = _observation(
        (
            (0, 0, 0, 0),
            (0, 2, 0, 0),
            (0, 0, 0, 0),
        )
    )
    after = _observation(
        (
            (0, 0, 0, 0),
            (0, 0, 2, 0),
            (0, 0, 0, 0),
        )
    )
    tracker = SceneTracker(enable_temporal_primitives=True)
    first_scene, _events = tracker.perceive(before)
    second_scene, _events = tracker.perceive(after)

    assert first_scene.primitives == ()
    assert {
        primitive.kind for primitive in second_scene.primitives
    } == {"frame_delta_region", "discrete_flow"}
    delta = next(
        item
        for item in second_scene.primitives
        if item.kind == "frame_delta_region"
    )
    flow = next(
        item
        for item in second_scene.primitives
        if item.kind == "discrete_flow"
    )
    assert delta.area == 2
    assert set(delta.properties) == {
        "contains_appearance",
        "contains_disappearance",
    }
    assert set(flow.properties) == {"dx_1", "dy_0", "shape_preserved"}
    event_kinds = {event.kind for event in _events}
    assert "frame_difference" in event_kinds
    assert "object_flow" in event_kinds


def test_shape_forms_assimilate_translation_and_recoloring() -> None:
    first = _observation(
        (
            (0, 0, 0, 0, 0),
            (0, 2, 2, 0, 0),
            (0, 2, 0, 0, 0),
            (0, 0, 0, 0, 0),
        )
    )
    second = _observation(
        (
            (0, 0, 0, 0, 0),
            (0, 0, 0, 3, 3),
            (0, 0, 0, 3, 0),
            (0, 0, 0, 0, 0),
        )
    )
    first_scene, _events = SceneTracker().perceive(first)
    second_scene, _events = SceneTracker().perceive(second)
    first_forms = {
        fact.arguments[1]
        for fact in first_scene.facts
        if fact.predicate == "shape_form"
    }
    second_forms = {
        fact.arguments[1]
        for fact in second_scene.facts
        if fact.predicate == "shape_form"
    }

    assert first_forms == second_forms
    first_context_forms = {
        fact
        for fact in first_scene.context()
        if fact.predicate == "shape_form_present"
    }
    second_context_forms = {
        fact
        for fact in second_scene.context()
        if fact.predicate == "shape_form_present"
    }
    assert first_context_forms == second_context_forms


def test_disequilibrium_reuses_a_causally_responsive_action_role() -> None:
    before = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0, 0), (0, 0, 0), (0, 0, 0)),
    )
    after = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((2, 2, 2), (2, 2, 2), (2, 2, 2)),
    )
    tracker = SceneTracker()
    before_scene, _events = tracker.perceive(before)
    after_scene, _events = tracker.perceive(after)
    explorer = EpistemicExplorer(productive_role_reuse=True)
    explorer.observe(before, before_scene)
    first = explorer.select(before, before_scene, (1, 2))
    assert first.token.action_id == 1
    explorer.observe(after, after_scene)

    reused = explorer.select(
        after,
        after_scene,
        (1, 2),
        pragmatic_disequilibrium=True,
    )

    assert reused.token.action_id == 1
    assert "reuse-productive-action-role" in reused.reason

    explorer.productive_reuse_level_trials = (
        explorer.max_productive_reuse_trials_per_level
    )
    released = explorer.select(
        after,
        after_scene,
        (1, 2),
        pragmatic_disequilibrium=True,
    )
    assert released.token.action_id == 2
    assert "untried-current-state" in released.reason


def test_primitive_actions_require_primitive_perception() -> None:
    try:
        MindConfig(enable_visual_primitive_actions=True)
    except ValueError as error:
        assert "require visual primitive perception" in str(error)
    else:
        raise AssertionError("invalid primitive-action genome was accepted")
