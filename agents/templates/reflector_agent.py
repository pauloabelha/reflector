"""Official ARC-AGI-3 Agents adapter for Reflector's shared symbolic policy."""

import json
import os
import time
from pathlib import Path
from typing import IO, Any

from arcengine import FrameData, FrameDataRaw, GameAction, GameState

from reflector import Observation, SymbolicPolicy
from reflector.runtime.deployment import (
    CANDIDATE_ID_ENV,
    COGNITIVE_STREAM_DIR_ENV,
    INFERENCE_FINGERPRINT_ENV,
    deployed_config,
)
from reflector.runtime.trace import AGENT_VERSION

from ..agent import Agent


class ReflectorAgent(Agent):
    """Kaggle-valid adapter; all decisions come from ``reflector``."""

    MAX_ACTIONS = 80

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.policy = SymbolicPolicy(deployed_config())
        # The upstream loop is inclusive (``<= MAX_ACTIONS``), so subtract
        # one to make the serialized genome's budget exact.
        self.MAX_ACTIONS = self.policy.mind.config.action_budget - 1
        self._finished_at: float | None = None
        self._cognitive_stream: IO[str] | None = None
        stream_root = os.environ.get(COGNITIVE_STREAM_DIR_ENV)
        if stream_root:
            directory = Path(stream_root)
            directory.mkdir(parents=True, exist_ok=True)
            safe_game_id = "".join(
                character if character.isalnum() or character in "-_" else "_"
                for character in self.game_id
            )
            self._cognitive_stream = (
                directory / f"{safe_game_id}.cognitive.jsonl"
            ).open("w", encoding="utf-8")

    def is_done(self, frames: list[FrameData], latest_frame: FrameData) -> bool:
        return latest_frame.state is GameState.WIN

    def append_frame(self, frame: FrameData) -> None:
        """Preserve the official lifecycle while learning terminal results."""

        super().append_frame(frame)
        self.policy.observe(self._observation(frame))

    def _convert_raw_frame_data(
        self, raw: FrameDataRaw | None
    ) -> FrameData:
        """Retain the action that produced a frame for replay and diagnosis."""

        converted = super()._convert_raw_frame_data(raw)
        if raw is not None:
            converted.action_input = raw.action_input.model_copy(deep=True)
        return converted

    @property
    def seconds(self) -> float:
        """Freeze gameplay duration before post-run trace analysis begins."""

        end = self._finished_at if self._finished_at is not None else time.time()
        return (end - self.timer) * 100 // 1 / 100

    def cleanup(self, scorecard: Any | None = None) -> None:
        if self._finished_at is None:
            self._finished_at = time.time()
        if self._cognitive_stream is not None:
            self._cognitive_stream.close()
            self._cognitive_stream = None
        super().cleanup(scorecard)

    def choose_action(
        self, frames: list[FrameData], latest_frame: FrameData
    ) -> GameAction:
        observation = self._observation(latest_frame)
        decision = self.policy.choose_action(observation)
        action = GameAction.from_id(decision.action_id)
        if decision.data:
            action.set_data(decision.data_dict())
        action.reasoning = {"policy": AGENT_VERSION, "why": decision.reason}
        if self._cognitive_stream is not None:
            event = self.policy.cognitive_event(observation, decision)
            event["deployment"] = {
                "game_id": self.game_id,
                "candidate_id": os.environ.get(CANDIDATE_ID_ENV),
                "inference_fingerprint": os.environ.get(
                    INFERENCE_FINGERPRINT_ENV
                ),
                "agent_version": AGENT_VERSION,
            }
            self._cognitive_stream.write(
                json.dumps(
                    event,
                    sort_keys=True,
                    separators=(",", ":"),
                    ensure_ascii=True,
                )
                + "\n"
            )
            self._cognitive_stream.flush()
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
