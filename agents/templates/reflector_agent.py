"""Official ARC-AGI-3 Agents adapter for Reflector's shared symbolic policy."""

from typing import Any

from arcengine import FrameData, GameAction, GameState

from reflector import Observation, SymbolicPolicy
from reflector.deployment import deployed_config
from reflector.trace import AGENT_VERSION

from ..agent import Agent


class ReflectorAgent(Agent):
    """Kaggle-valid adapter; all decisions come from ``reflector``."""

    MAX_ACTIONS = 80

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.policy = SymbolicPolicy(deployed_config())

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def append_frame(self, frame: FrameData) -> None:
        """Preserve the official lifecycle while learning terminal results."""

        super().append_frame(frame)
        self.policy.observe(self._observation(frame))

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        observation = self._observation(latest_frame)
        decision = self.policy.choose_action(observation)
        action = GameAction.from_id(decision.action_id)
        if decision.data:
            action.set_data(decision.data_dict())
        action.reasoning = {"policy": AGENT_VERSION, "why": decision.reason}
        return action

    @staticmethod
    def _observation(frame: FrameData) -> Observation:
        latest_grid = frame.frame[-1] if frame.frame else ()
        return Observation.create(
            state=frame.state.value,
            available_actions=frame.available_actions,
            frame=latest_grid,
            levels_completed=frame.levels_completed,
        )
