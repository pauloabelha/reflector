"""Smallest deterministic symbolic ARC-AGI-3 policy.

The policy deliberately speaks in protocol primitives (integer action ids and
immutable observations), so it has no dependency on Kaggle, the ARC toolkit,
the web UI, a database, or development-time services.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class Observation:
    """Serializable subset of an ARC observation needed by the baseline."""

    state: str
    available_actions: tuple[int, ...]
    frame: tuple[tuple[int, ...], ...] = ()
    levels_completed: int = 0

    @classmethod
    def create(
        cls,
        *,
        state: str,
        available_actions: Iterable[int],
        frame: Sequence[Sequence[int]] | None = None,
        levels_completed: int = 0,
    ) -> "Observation":
        return cls(
            state=state,
            available_actions=tuple(sorted(set(available_actions))),
            frame=tuple(tuple(int(cell) for cell in row) for row in (frame or ())),
            levels_completed=levels_completed,
        )


@dataclass(frozen=True, slots=True)
class Decision:
    """A legal ARC action plus optional data and a symbolic explanation."""

    action_id: int
    data: tuple[tuple[str, int], ...] = ()
    reason: str = ""

    def data_dict(self) -> dict[str, int]:
        return dict(self.data)


class SymbolicPolicy:
    """Deterministic, dependency-free baseline that only emits legal actions."""

    RESET = 0
    COMPLEX = 6
    TERMINAL = "WIN"
    NEEDS_RESET = frozenset({"NOT_PLAYED", "GAME_OVER", "NOT_STARTED"})

    def __init__(self) -> None:
        self.observations_seen = 0
        self.action_counts: dict[int, int] = {}

    def is_done(self, observation: Observation) -> bool:
        return observation.state == self.TERMINAL

    def choose_action(self, observation: Observation) -> Decision:
        self.observations_seen += 1
        if observation.state in self.NEEDS_RESET:
            return self._record(Decision(self.RESET, reason="reset-required"))

        legal = tuple(
            action
            for action in observation.available_actions
            if action != self.RESET
        )
        if not legal:
            raise ValueError("active observation exposes no legal non-reset action")

        # Canonical action order is the minimal symbolic baseline. It is stable,
        # reproducible, and cannot accidentally emit an unavailable enum member.
        action_id = min(legal)
        if action_id == self.COMPLEX:
            x, y = self._symbolic_click(observation.frame)
            return self._record(
                Decision(
                    action_id,
                    data=(("x", x), ("y", y)),
                    reason="canonical-action:rare-color-centroid",
                )
            )
        return self._record(
            Decision(action_id, reason="canonical-lowest-legal-action")
        )

    def _record(self, decision: Decision) -> Decision:
        self.action_counts[decision.action_id] = (
            self.action_counts.get(decision.action_id, 0) + 1
        )
        return decision

    @staticmethod
    def _symbolic_click(frame: tuple[tuple[int, ...], ...]) -> tuple[int, int]:
        if not frame or not frame[0]:
            return (32, 32)

        positions: dict[int, list[tuple[int, int]]] = {}
        for y, row in enumerate(frame):
            for x, color in enumerate(row):
                positions.setdefault(color, []).append((x, y))

        # Background is usually the most frequent color. Select the centroid of
        # the rarest non-background color as a deterministic object hypothesis.
        background = max(positions, key=lambda color: len(positions[color]))
        candidates = [
            (len(points), color, points)
            for color, points in positions.items()
            if color != background
        ]
        if not candidates:
            return (len(frame[0]) // 2, len(frame) // 2)
        _, _, points = min(candidates, key=lambda item: (item[0], item[1]))
        x = sum(point[0] for point in points) // len(points)
        y = sum(point[1] for point in points) // len(points)
        return (max(0, min(63, x)), max(0, min(63, y)))
