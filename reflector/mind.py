"""Online symbolic world model, schema learner, and experiment selector."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .perception import SceneTracker
from .schemas import ConceptStore, SchemaStore, SyntheticConcept
from .symbolic import Decision, Observation, Scene, Transition


@dataclass(frozen=True, slots=True)
class MindUpdate:
    scene: Scene
    transition: Transition | None
    new_concepts: tuple[SyntheticConcept, ...]


class SymbolicMind:
    """Drescher-inspired learner that updates entirely during inference."""

    def __init__(self) -> None:
        self.tracker = SceneTracker()
        self.schemas = SchemaStore()
        self.concepts = ConceptStore()
        self._last_scene: Scene | None = None

    def ingest(
        self, observation: Observation, previous_decision: Decision | None
    ) -> MindUpdate:
        scene, events = self.tracker.perceive(observation)
        transition = None
        new_concepts: tuple[SyntheticConcept, ...] = ()
        if self._last_scene is not None and previous_decision is not None:
            transition = self.tracker.transition(
                self._last_scene,
                scene,
                previous_decision.action_id,
                previous_decision.data,
                events,
            )
            self.schemas.observe(transition)
            before = set(self.concepts.concepts)
            self.concepts.reflect(self.schemas)
            new_concepts = tuple(
                concept
                for concept_id, concept in sorted(self.concepts.concepts.items())
                if concept_id not in before
            )
        self._last_scene = scene
        return MindUpdate(scene, transition, new_concepts)

    def select_action(self, legal_actions: tuple[int, ...]) -> tuple[int, str]:
        """Balance predicted effects with information gain.

        A tiny canonical-order prior preserves deterministic tie-breaking. An
        untried action receives an information bonus, while repeated useful
        effects earn exploitation value.
        """

        scored: list[tuple[float, int, float, float]] = []
        for action in legal_actions:
            trials = self.schemas.action_trials.get(action, 0)
            predicted = self.schemas.action_value(action)
            information = 1.0 / math.sqrt(trials + 1)
            score = predicted + information - action / 1000.0
            scored.append((score, -action, predicted, information))
        score, negative_action, predicted, information = max(scored)
        action = -negative_action
        reason = (
            f"schema-selection:value={predicted:.3f},"
            f"information={information:.3f},score={score:.3f}"
        )
        return action, reason

    def snapshot(self) -> dict[str, Any]:
        return {
            "schemas": self.schemas.to_dict(),
            "concepts": self.concepts.to_dict(),
        }
