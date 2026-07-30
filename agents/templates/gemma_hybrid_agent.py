"""Official-toolkit adapter for the research-only Gemma hybrid."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import IO, Any

from arcengine import FrameData, GameAction, GameState

from reflector.research.gemma_hybrid import GemmaHybridBrain

from ..agent import Agent


class GemmaHybridAgent(Agent):
    """Symbolic visual compression with inference-time local Gemma control."""

    MAX_ACTIONS = 39

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        budget = int(os.environ.get("REFLECTOR_GEMMA_ACTION_BUDGET", "40"))
        self.MAX_ACTIONS = budget - 1
        self.brain = GemmaHybridBrain(
            os.environ.get(
                "REFLECTOR_GEMMA_ENDPOINT", "http://127.0.0.1:18092"
            ),
            model=os.environ.get(
                "REFLECTOR_GEMMA_MODEL",
                "google_gemma-4-E2B-it-Q4_K_M.gguf",
            ),
        )
        self._stream: IO[str] | None = None
        stream_root = os.environ.get("REFLECTOR_GEMMA_STREAM_DIR")
        if stream_root:
            directory = Path(stream_root)
            directory.mkdir(parents=True, exist_ok=True)
            self._stream = (
                directory / f"{self.game_id}.gemma-hybrid.jsonl"
            ).open("w", encoding="utf-8")

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        grid = tuple(
            tuple(int(value) for value in row)
            for row in (latest_frame.frame[-1] if latest_frame.frame else [])
        )
        if latest_frame.state in (GameState.NOT_PLAYED, GameState.GAME_OVER):
            if latest_frame.state is GameState.GAME_OVER:
                self.brain.observe_terminal(
                    frame=grid,
                    state=latest_frame.state.value,
                    levels_completed=int(latest_frame.levels_completed),
                )
            return GameAction.RESET
        selected = self.brain.choose(
            frame=grid,
            available_actions=latest_frame.available_actions,
            state=latest_frame.state.value,
            levels_completed=int(latest_frame.levels_completed),
        )
        action = GameAction.from_id(selected.action_id)
        if selected.data:
            action.set_data(selected.data)
        action.reasoning = {
            "policy": "research-gemma-hybrid-v1",
            "why": self.brain.last_event.get("hypothesis", ""),
        }
        if self._stream is not None:
            event = dict(self.brain.last_event)
            event["game_id"] = self.game_id
            self._stream.write(
                json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n"
            )
            self._stream.flush()
        return action

    def cleanup(self, scorecard: Any | None = None) -> None:
        if self._stream is not None:
            self._stream.close()
            self._stream = None
        super().cleanup(scorecard)
