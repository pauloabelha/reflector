"""Online symbolic world model, schema learner, and experiment selector."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from .causal import Experiment, HypothesisStore
from .graph import DependencyGraph
from .perception import SceneTracker
from .planning import Goal, Plan, SymbolicPlanner
from .schemas import ConceptStore, SchemaStore, SyntheticConcept
from .symbolic import Decision, Observation, Scene, Transition


@dataclass(frozen=True, slots=True)
class MindUpdate:
    scene: Scene
    transition: Transition | None
    new_concepts: tuple[SyntheticConcept, ...]
    new_hypotheses: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MindConfig:
    enable_concepts: bool = True
    enable_counterfactual_pressure: bool = True
    enable_schema_complexity_pressure: bool = True
    enable_experiments: bool = True
    enable_planning: bool = True


class SymbolicMind:
    """Drescher-inspired learner that updates entirely during inference."""

    def __init__(self, config: MindConfig | None = None) -> None:
        self.config = config or MindConfig()
        self.tracker = SceneTracker()
        self.schemas = SchemaStore()
        self.concepts = ConceptStore(
            complexity_pressure=(
                1.0 if self.config.enable_schema_complexity_pressure else 0.0
            ),
            require_counterfactual_utility=(
                self.config.enable_counterfactual_pressure
            ),
        )
        self.hypotheses = HypothesisStore()
        self.planner = SymbolicPlanner()
        self.last_experiment: Experiment | None = None
        self.last_plan: Plan | None = None
        self._last_scene: Scene | None = None

    def ingest(
        self, observation: Observation, previous_decision: Decision | None
    ) -> MindUpdate:
        scene, events = self.tracker.perceive(observation)
        transition = None
        new_concepts: tuple[SyntheticConcept, ...] = ()
        new_hypotheses: tuple[str, ...] = ()
        if self._last_scene is not None and previous_decision is not None:
            transition = self.tracker.transition(
                self._last_scene,
                scene,
                previous_decision.action_id,
                previous_decision.data,
                events,
            )
            self.schemas.observe(transition)
            new_hypotheses = self.hypotheses.observe(transition, self.schemas)
            if self.config.enable_concepts:
                before = set(self.concepts.concepts)
                self.concepts.reflect(self.schemas)
                new_concepts = tuple(
                    concept
                    for concept_id, concept in sorted(self.concepts.concepts.items())
                    if concept_id not in before
                )
        self._last_scene = scene
        return MindUpdate(scene, transition, new_concepts, new_hypotheses)

    def select_action(self, legal_actions: tuple[int, ...]) -> tuple[int, str]:
        """Balance predicted effects with information gain.

        A tiny canonical-order prior preserves deterministic tie-breaking. An
        untried action receives an information bonus, while repeated useful
        effects earn exploitation value.
        """

        experiments = (
            self.hypotheses.experiments(legal_actions, self.schemas)
            if self.config.enable_experiments
            else ()
        )
        experiment_by_action = {item.action_id: item for item in experiments}
        self.last_experiment = experiments[0] if experiments else None
        self.last_plan = (
            self.planner.plan(
                Goal("level_advanced", priority=1.0),
                legal_actions,
                self.schemas,
                self.hypotheses,
            )
            if self.config.enable_planning
            else None
        )

        scored: list[tuple[float, int, float, float, float, float]] = []
        for action in legal_actions:
            trials = self.schemas.action_trials.get(action, 0)
            predicted = self.schemas.action_value(action)
            information = 1.0 / math.sqrt(trials + 1)
            experiment = experiment_by_action.get(action)
            experiment_bonus = experiment.score * 0.25 if experiment else 0.0
            plan_bonus = (
                10.0 * self.last_plan.confidence
                if self.last_plan is not None
                and self.last_plan.actions
                and self.last_plan.actions[0] == action
                else 0.0
            )
            score = (
                predicted
                + information
                + experiment_bonus
                + plan_bonus
                - action / 1000.0
            )
            scored.append(
                (
                    score,
                    -action,
                    predicted,
                    information,
                    experiment_bonus,
                    plan_bonus,
                )
            )
        (
            score,
            negative_action,
            predicted,
            information,
            experiment_bonus,
            plan_bonus,
        ) = max(scored)
        action = -negative_action
        reason = (
            f"schema-selection:value={predicted:.3f},"
            f"information={information:.3f},"
            f"experiment={experiment_bonus:.3f},plan={plan_bonus:.3f},"
            f"score={score:.3f}"
        )
        return action, reason

    def snapshot(self) -> dict[str, Any]:
        graph = DependencyGraph.build(
            self.schemas, self.concepts, self.hypotheses
        )
        return {
            "schemas": self.schemas.to_dict(),
            "concepts": self.concepts.to_dict(),
            "hypotheses": self.hypotheses.to_dict(),
            "last_experiment": (
                self.last_experiment.to_dict()
                if self.last_experiment is not None
                else None
            ),
            "last_plan": (
                self.last_plan.to_dict() if self.last_plan is not None else None
            ),
            "planner_expansions": self.planner.last_expansions,
            "dependency_graph": graph.to_dict(),
        }
