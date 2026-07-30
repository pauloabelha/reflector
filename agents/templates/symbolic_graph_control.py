"""Official-toolkit adapter for the research-only symbolic graph control."""

from __future__ import annotations

import os
from typing import Any

from arcengine import FrameData, GameAction, GameState

from reflector.research.symbolic_controls import ObjectGraphControl

from ..agent import Agent


class SymbolicGraphControlAgent(Agent):
    """Pure symbolic control; deliberately excluded from deployed inference."""

    MAX_ACTIONS = 399

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        budget = int(os.environ.get("REFLECTOR_CONTROL_ACTION_BUDGET", "400"))
        if budget < 1:
            raise ValueError("control action budget must be positive")
        self.MAX_ACTIONS = budget - 1
        self.policy = ObjectGraphControl()

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            if latest_frame.state is GameState.GAME_OVER:
                self.policy.abandon_transition()
            return GameAction.RESET
        grid = latest_frame.frame[-1] if latest_frame.frame else []
        selected = self.policy.choose(
            frame=tuple(tuple(int(value) for value in row) for row in grid),
            available_actions=latest_frame.available_actions,
            levels_completed=int(latest_frame.levels_completed),
        )
        action = GameAction.from_id(selected.action_id)
        if selected.data:
            action.set_data(selected.data)
        action.reasoning = {
            "policy": "research-symbolic-object-graph-control-v1",
            "why": "shortest-known-path-to-untested-symbolic-frontier",
        }
        return action
