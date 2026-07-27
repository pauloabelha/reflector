import pytest

from reflector import Observation, SymbolicPolicy


def test_reset_and_legal_action() -> None:
    policy = SymbolicPolicy()
    reset = policy.choose_action(
        Observation.create(state="NOT_PLAYED", available_actions=(3, 4))
    )
    assert reset.action_id == 0
    action = policy.choose_action(
        Observation.create(state="NOT_FINISHED", available_actions=(4, 3))
    )
    assert action.action_id == 3


def test_complex_action_targets_rare_color() -> None:
    policy = SymbolicPolicy()
    decision = policy.choose_action(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(6,),
            frame=((0, 0, 0), (0, 9, 0), (0, 0, 0)),
        )
    )
    assert decision.action_id == 6
    assert decision.data_dict() == {"x": 1, "y": 1}


def test_active_observation_requires_legal_action() -> None:
    with pytest.raises(ValueError):
        SymbolicPolicy().choose_action(
            Observation.create(state="NOT_FINISHED", available_actions=())
        )
