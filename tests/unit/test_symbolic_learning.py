from reflector import (
    Atom,
    ConceptStore,
    Event,
    MindConfig,
    Observation,
    SchemaStore,
    SymbolicPolicy,
    Transition,
)
from reflector.perception import SceneTracker


def test_object_identity_and_motion_event() -> None:
    tracker = SceneTracker()
    first, _ = tracker.perceive(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(1,),
            frame=((0, 0, 0), (0, 2, 0), (0, 0, 0)),
        )
    )
    second, events = tracker.perceive(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(1,),
            frame=((0, 0, 0), (0, 0, 2), (0, 0, 0)),
        )
    )
    assert first.objects[0].object_id == second.objects[0].object_id
    assert Event("object_moved", first.objects[0].object_id, ("1", "0")) in events


def test_repeated_effect_earns_synthetic_concept() -> None:
    schemas = SchemaStore()
    context = (Atom("state", ("NOT_FINISHED",)),)
    for index in range(2):
        schemas.observe(
            Transition(
                before_index=index,
                after_index=index + 1,
                context=context,
                action_id=3,
                action_data=(),
                result=(Event("level_advanced", "game", ("0", "1")),),
            )
        )
    concepts = ConceptStore().reflect(schemas)
    assert len(schemas.schemas) == 1
    schema = next(iter(schemas.schemas.values()))
    assert schema.support == 2
    assert schema.reliability == 0.75
    assert any(concept.name == "Activator[action=3]" for concept in concepts)
    assert all(concept.evidence for concept in concepts)
    assert all(concept.utility > 0 for concept in concepts)


def test_policy_learns_transition_and_records_trace() -> None:
    policy = SymbolicPolicy()
    first = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0), (0, 0)),
    )
    second = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0), (0, 9)),
    )
    policy.choose_action(first)
    policy.choose_action(second)
    assert len(policy.trace.steps) == 2
    assert policy.trace.steps[1].incoming_transition is not None
    assert policy.mind.schemas.action_trials == {1: 1}


def test_terminal_observation_is_learned_without_an_outgoing_action() -> None:
    policy = SymbolicPolicy()
    policy.choose_action(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(1,),
            frame=((0, 0), (0, 0)),
        )
    )
    terminal = Observation.create(
        state="WIN",
        available_actions=(),
        frame=((0, 0), (0, 9)),
        levels_completed=1,
    )
    policy.observe(terminal)
    policy.observe(terminal)
    assert policy.mind.schemas.action_trials == {1: 1}
    assert policy.trace.terminal_observation == terminal
    assert policy.trace.terminal_transition is not None
    assert any(
        event.kind == "level_advanced"
        for event in policy.trace.terminal_transition.result
    )


def test_identical_observation_after_a_new_action_is_learned_once() -> None:
    policy = SymbolicPolicy()
    unchanged = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1,),
        frame=((0, 0), (0, 0)),
    )

    policy.choose_action(unchanged)
    policy.observe(unchanged)
    assert policy.mind.schemas.action_trials == {1: 1}

    # The adapter presents the same received frame to choose_action after
    # append_frame. That delivery is not a second environment transition.
    policy.choose_action(unchanged)
    assert policy.mind.schemas.action_trials == {1: 1}

    # A new environment response after the second action is a real transition,
    # even when its pixels and metadata are byte-for-byte identical.
    policy.observe(unchanged)
    policy.observe(unchanged)
    assert policy.mind.schemas.action_trials == {1: 2}


def test_policy_uses_context_to_reject_a_globally_successful_action() -> None:
    policy = SymbolicPolicy(config=MindConfig(enable_experiments=False))
    left = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((2, 0, 0), (0, 0, 0), (0, 0, 0)),
    )
    advanced_right = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0, 0), (0, 0, 0), (0, 0, 2)),
        levels_completed=1,
    )

    assert policy.choose_action(left).action_id == 1
    assert policy.choose_action(advanced_right).action_id == 1
    # Action 1 now has strong global success evidence, but the unchanged
    # right-hand context is evidence that it is locally wrong.
    assert policy.choose_action(advanced_right).action_id == 2
