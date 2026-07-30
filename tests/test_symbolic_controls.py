from reflector.research.symbolic_controls import ObjectGraphControl


def test_graph_control_prefers_legal_simple_actions_deterministically() -> None:
    policy = ObjectGraphControl()
    frame = ((0, 0, 0), (0, 9, 0), (0, 0, 0))

    first = policy.choose(
        frame=frame,
        available_actions=(4, 2),
        levels_completed=0,
    )
    second = policy.choose(
        frame=frame,
        available_actions=(4, 2),
        levels_completed=0,
    )

    assert first.action_id == 2
    assert second.action_id == 4


def test_graph_control_grounds_clicks_in_components() -> None:
    policy = ObjectGraphControl()
    frame = (
        (0, 0, 0, 0),
        (0, 7, 7, 0),
        (0, 7, 7, 0),
        (0, 0, 0, 0),
    )

    selected = policy.choose(
        frame=frame,
        available_actions=(6,),
        levels_completed=0,
    )

    assert selected.action_id == 6
    assert (selected.y, selected.x) in {(1, 1), (1, 2), (2, 1), (2, 2)}


def test_new_level_clears_graph_but_retains_metrics() -> None:
    policy = ObjectGraphControl()
    frame = ((0, 0), (0, 1))
    policy.choose(frame=frame, available_actions=(1,), levels_completed=0)
    first_total = policy.unique_states

    policy.choose(frame=frame, available_actions=(1,), levels_completed=1)

    assert len(policy.nodes) == 1
    assert policy.unique_states == first_total + 1
