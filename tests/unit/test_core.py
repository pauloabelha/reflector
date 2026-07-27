from unittest.mock import MagicMock

import pytest
from arcengine import FrameData, GameAction, GameState

from agents.templates.reflector_agent import ReflectorAgent


@pytest.mark.unit
def test_official_action_protocol_mapping() -> None:
    assert GameAction.from_id(0) is GameAction.RESET
    assert GameAction.from_id(6) is GameAction.ACTION6
    assert GameAction.from_name("ACTION7") is GameAction.ACTION7


@pytest.mark.unit
def test_official_adapter_selects_available_action() -> None:
    agent = ReflectorAgent(
        card_id="test-card",
        game_id="test-game",
        agent_name="reflector",
        ROOT_URL="http://localhost",
        record=False,
        arc_env=MagicMock(),
    )
    frame = FrameData(
        game_id="test-game",
        state=GameState.NOT_FINISHED,
        available_actions=[4, 3],
        frame=[[[0, 0], [0, 0]]],
    )
    assert agent.choose_action([frame], frame) is GameAction.ACTION3
    assert not agent.is_done([frame], frame)
    frame.state = GameState.WIN
    assert agent.is_done([frame], frame)
