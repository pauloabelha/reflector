"""Online symbolic world model, schema learner, and experiment selector."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields
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
    """Serializable, constrained genome for every deployable agent descendant."""

    enable_concepts: bool = True
    enable_counterfactual_pressure: bool = True
    enable_schema_complexity_pressure: bool = True
    enable_experiments: bool = True
    enable_planning: bool = True
    planner_max_depth: int = 3
    planner_max_expansions: int = 64
    information_weight: float = 1.0
    experiment_weight: float = 0.25
    plan_weight: float = 10.0

    def __post_init__(self) -> None:
        for name in (
            "enable_concepts",
            "enable_counterfactual_pressure",
            "enable_schema_complexity_pressure",
            "enable_experiments",
            "enable_planning",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean")
        if type(self.planner_max_depth) is not int:
            raise ValueError("planner_max_depth must be an integer")
        if type(self.planner_max_expansions) is not int:
            raise ValueError("planner_max_expansions must be an integer")
        if not 1 <= self.planner_max_depth <= 8:
            raise ValueError("planner_max_depth must be between 1 and 8")
        if not 1 <= self.planner_max_expansions <= 512:
            raise ValueError("planner_max_expansions must be between 1 and 512")
        for name in (
            "information_weight",
            "experiment_weight",
            "plan_weight",
        ):
            value = getattr(self, name)
            if type(value) not in (int, float):
                raise ValueError(f"{name} must be numeric")
            if not math.isfinite(value) or not 0.0 <= value <= 100.0:
                raise ValueError(f"{name} must be finite and between 0 and 100")

    def to_dict(self) -> dict[str, bool | int | float]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MindConfig":
        expected = {item.name for item in fields(cls)}
        unknown = set(value) - expected
        if unknown:
            raise ValueError(f"unknown MindConfig fields: {sorted(unknown)}")
        return cls(**value)


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
        self.planner = SymbolicPlanner(
            max_depth=self.config.planner_max_depth,
            max_expansions=self.config.planner_max_expansions,
        )
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
            experiment_bonus = (
                experiment.score * self.config.experiment_weight
                if experiment
                else 0.0
            )
            plan_bonus = (
                self.config.plan_weight * self.last_plan.confidence
                if self.last_plan is not None
                and self.last_plan.actions
                and self.last_plan.actions[0] == action
                else 0.0
            )
            score = (
                predicted
                + information * self.config.information_weight
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
