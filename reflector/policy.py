"""Smallest deterministic symbolic ARC-AGI-3 policy.

The policy deliberately speaks in protocol primitives (integer action ids and
immutable observations), so it has no dependency on Kaggle, the ARC toolkit,
the web UI, a database, or development-time services.
"""

from __future__ import annotations

from .mind import MindUpdate, SymbolicMind
from .symbolic import Decision, Observation
from .trace import EpisodeTrace, TraceStep


class SymbolicPolicy:
    """Deterministic, dependency-free baseline that only emits legal actions."""

    RESET = 0
    COMPLEX = 6
    TERMINAL = "WIN"
    NEEDS_RESET = frozenset({"NOT_PLAYED", "GAME_OVER", "NOT_STARTED"})

    def __init__(self) -> None:
        self.observations_seen = 0
        self.action_counts: dict[int, int] = {}
        self.mind = SymbolicMind()
        self.trace = EpisodeTrace()
        self._previous_decision: Decision | None = None
        self._last_observation: Observation | None = None
        self._last_update: MindUpdate | None = None

    def is_done(self, observation: Observation) -> bool:
        return observation.state == self.TERMINAL

    def observe(self, observation: Observation) -> MindUpdate:
        """Ingest each environment observation exactly once.

        The official agent adapter calls this from ``append_frame`` so terminal
        results are learned even though the official loop never chooses another
        action after WIN.
        """

        if observation == self._last_observation and self._last_update is not None:
            return self._last_update
        self.observations_seen += 1
        update = self.mind.ingest(observation, self._previous_decision)
        self._last_observation = observation
        self._last_update = update
        if self.is_done(observation):
            self.trace.finish(observation, update.scene, update.transition)
        return update

    def choose_action(self, observation: Observation) -> Decision:
        update = self.observe(observation)
        if observation.state in self.NEEDS_RESET:
            decision = self._record(Decision(self.RESET, reason="reset-required"))
            self._append_trace(observation, decision, update)
            self._previous_decision = decision
            return decision

        legal = tuple(
            action
            for action in observation.available_actions
            if action != self.RESET
        )
        if not legal:
            raise ValueError("active observation exposes no legal non-reset action")

        action_id, reason = self.mind.select_action(legal)
        if action_id == self.COMPLEX:
            x, y = self._symbolic_click(observation.frame)
            decision = self._record(
                Decision(
                    action_id,
                    data=(("x", x), ("y", y)),
                    reason=f"{reason}:rare-color-centroid",
                )
            )
        else:
            decision = self._record(Decision(action_id, reason=reason))
        self._append_trace(observation, decision, update)
        self._previous_decision = decision
        return decision

    def _append_trace(
        self: "SymbolicPolicy",
        observation: Observation,
        decision: Decision,
        update: MindUpdate,
    ) -> None:
        # The concrete type is deliberately accessed structurally to keep the
        # public policy surface compact.
        self.trace.append(
            TraceStep(
                index=len(self.trace.steps),
                observation=observation,
                decision=decision,
                scene=update.scene,
                incoming_transition=update.transition,
                new_concepts=tuple(
                    concept.concept_id
                    for concept in update.new_concepts
                ),
            )
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
