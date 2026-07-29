import json

import pytest

from reflector import Observation, SymbolicPolicy
from reflector.mind import MindConfig


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


def test_cognitive_event_exposes_auditable_state_without_prose_reasoning() -> None:
    policy = SymbolicPolicy(MindConfig(enable_epistemic_state_graph=True))
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=((0, 0, 0), (0, 9, 0), (0, 0, 0)),
    )
    decision = policy.choose_action(observation)

    event = policy.cognitive_event(observation, decision)

    assert event["format"] == "reflector-cognitive-event-v1"
    assert event["decision"] == decision.to_dict()
    assert event["observation"]["frame_digest"]
    assert any(
        item["status"] == "selected"
        for item in event["advisor_arbitration"]
    )
    assert event["operative_state"]["exploration"]["states"] == 1
    assert "thought" not in json.dumps(event).lower()
