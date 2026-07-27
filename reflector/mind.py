"""Online symbolic world model, schema learner, and experiment selector."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields
from typing import Any

from .abstraction import AbstractionStore
from .causal import Experiment, HypothesisStore
from .graph import DependencyGraph
from .perception import SceneTracker
from .planning import Goal, Plan, SymbolicPlanner
from .reinforcement import StructuralCreditLedger
from .schemas import ConceptStore, SchemaStore, SyntheticConcept
from .symbolic import (
    Decision,
    Event,
    Observation,
    Scene,
    Transition,
    canonical_atoms,
)


@dataclass(frozen=True, slots=True)
class MindUpdate:
    scene: Scene
    transition: Transition | None
    new_concepts: tuple[SyntheticConcept, ...]
    new_hypotheses: tuple[str, ...]
    new_abstractions: tuple[str, ...]
    new_assessments: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class MindConfig:
    """Serializable, constrained genome for every deployable agent descendant."""

    enable_concepts: bool = True
    enable_counterfactual_pressure: bool = True
    enable_schema_complexity_pressure: bool = True
    enable_experiments: bool = True
    enable_planning: bool = True
    enable_reflecting_abstraction: bool = True
    enable_accommodation: bool = True
    planner_max_depth: int = 3
    planner_max_expansions: int = 64
    information_weight: float = 1.0
    experiment_weight: float = 0.25
    plan_weight: float = 10.0
    hierarchy_complexity_pressure: float = 1.0

    def __post_init__(self) -> None:
        for name in (
            "enable_concepts",
            "enable_counterfactual_pressure",
            "enable_schema_complexity_pressure",
            "enable_experiments",
            "enable_planning",
            "enable_reflecting_abstraction",
            "enable_accommodation",
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
            "hierarchy_complexity_pressure",
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
        self.reinforcement = StructuralCreditLedger()
        self.abstractions = AbstractionStore(
            complexity_pressure=self.config.hierarchy_complexity_pressure
        )
        self.planner = SymbolicPlanner(
            max_depth=self.config.planner_max_depth,
            max_expansions=self.config.planner_max_expansions,
        )
        self.last_experiment: Experiment | None = None
        self.last_plan: Plan | None = None
        self._last_scene: Scene | None = None
        self._seen_frame_digests: set[str] = set()

    def ingest(
        self, observation: Observation, previous_decision: Decision | None
    ) -> MindUpdate:
        scene, events = self.tracker.perceive(observation)
        if (
            self._last_scene is not None
            and scene.frame_digest not in self._seen_frame_digests
        ):
            events = (*events, Event("novel_state_reached"))
        self._seen_frame_digests.add(scene.frame_digest)
        transition = None
        new_concepts: tuple[SyntheticConcept, ...] = ()
        new_hypotheses: tuple[str, ...] = ()
        new_abstractions: tuple[str, ...] = ()
        new_assessments: tuple[str, ...] = ()
        if self._last_scene is not None and previous_decision is not None:
            transition = self.tracker.transition(
                self._last_scene,
                scene,
                previous_decision.action_id,
                previous_decision.data,
                events,
            )
            transition = self.abstractions.normalize_transition(transition)
            transition = Transition(
                before_index=transition.before_index,
                after_index=transition.after_index,
                context=canonical_atoms(
                    (
                        *transition.context,
                        *self.concepts.context_atoms(
                            transition.action_id
                        ),
                    )
                ),
                action_id=transition.action_id,
                action_data=transition.action_data,
                result=transition.result,
            )
            # Freeze the forecast before the observed transition updates any
            # schema.  This prevents hindsight from masquerading as
            # prediction and gives contradiction a structural target.
            prediction = self.schemas.predict(
                transition.action_id,
                transition.context,
            )
            if self.config.enable_accommodation:
                prediction = self.reinforcement.accommodate_prediction(
                    action_id=transition.action_id,
                    context=transition.context,
                    prediction=prediction,
                )
            assessment_id = self.reinforcement.assess(
                transition,
                prediction,
            )
            new_assessments = (assessment_id,)
            if self.config.enable_accommodation:
                new_abstractions = self.reinforcement.last_constructed
            schema = self.schemas.observe(transition)
            new_hypotheses = self.hypotheses.observe(transition, self.schemas)
            if self.config.enable_reflecting_abstraction:
                new_abstractions = self.abstractions.observe_procedure(
                    transition,
                    schema.schema_id,
                    max_steps=self.config.planner_max_depth,
                )
            if self.config.enable_concepts:
                before = set(self.concepts.concepts)
                self.concepts.reflect(self.schemas)
                new_concepts = tuple(
                    concept
                    for concept_id, concept in sorted(self.concepts.concepts.items())
                    if concept_id not in before
                )
            if self.config.enable_reflecting_abstraction:
                new_abstractions = tuple(
                    sorted(
                        set(new_abstractions)
                        | set(
                            self.abstractions.reflect(
                                self.schemas, self.concepts
                            )
                        )
                    )
                )
                integrated = self.reinforcement.integrate(
                    (
                        family.action_id,
                        family.result_predicates,
                        family.shared_context,
                        family.support,
                    )
                    for family in self.abstractions.schema_families.values()
                )
                new_assessments = tuple(
                    sorted(set(new_assessments) | set(integrated))
                )
        self._last_scene = scene
        return MindUpdate(
            scene,
            transition,
            new_concepts,
            new_hypotheses,
            new_abstractions,
            new_assessments,
        )

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
        context = (
            self._last_scene.context() if self._last_scene is not None else ()
        )
        procedure = (
            self.abstractions.procedure_match(context, legal_actions)
            if self.config.enable_planning
            and self.config.enable_reflecting_abstraction
            else None
        )
        self.last_plan = (
            Plan(
                goal=Goal("level_advanced", priority=1.0),
                actions=procedure[0],
                predicted_events=("level_advanced",),
                confidence=procedure[1],
                expansions=0,
            )
            if procedure is not None
            else self.planner.plan(
                Goal("level_advanced", priority=1.0),
                legal_actions,
                self.schemas,
                self.hypotheses,
                self.abstractions,
            )
            if self.config.enable_planning
            else None
        )

        scored: list[
            tuple[float, int, float, float, float, float, float]
        ] = []
        for action in legal_actions:
            trials = self.schemas.contextual_trials(action, context)
            transfer_value = (
                self.abstractions.action_transfer_value(
                    action, self.schemas, context
                )
                if self.config.enable_reflecting_abstraction
                else 0.0
            )
            predicted = self.schemas.contextual_action_value(
                action,
                context,
                transfer_value=transfer_value,
            )
            if self.config.enable_accommodation:
                accommodated = self.reinforcement.accommodate_prediction(
                    action_id=action,
                    context=context,
                    prediction=self.schemas.predict(action, context),
                )
                if accommodated is not None and any(
                    evidence in self.reinforcement.accommodations
                    and self.reinforcement.accommodations[
                        evidence
                    ].proposition
                    in {"level_advanced", "WIN", "GAME_OVER"}
                    for evidence in accommodated.evidence
                ):
                    predicted = self.schemas.result_value(
                        accommodated.result
                    )
            information = 1.0 / math.sqrt(trials + 1)
            experiment = experiment_by_action.get(action)
            experiment_bonus = (
                experiment.score * self.config.experiment_weight
                if experiment
                else 0.0
            )
            epistemic_progress = self.schemas.event_probability(
                action, "novel_state_reached"
            )
            plan_bonus = (
                self.config.plan_weight * self.last_plan.confidence
                if self.last_plan is not None
                and self.last_plan.actions
                and self.last_plan.actions[0] == action
                and (
                    procedure is not None
                    or trials == 0
                    or predicted > 0.0
                )
                else 0.0
            )
            score = (
                predicted
                + information * self.config.information_weight
                + epistemic_progress * self.config.information_weight
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
                    epistemic_progress,
                    experiment_bonus,
                    plan_bonus,
                )
            )
        (
            score,
            negative_action,
            predicted,
            information,
            epistemic_progress,
            experiment_bonus,
            plan_bonus,
        ) = max(scored)
        action = -negative_action
        reason = (
            f"schema-selection:value={predicted:.3f},"
            f"information={information:.3f},"
            f"epistemic_progress={epistemic_progress:.3f},"
            f"experiment={experiment_bonus:.3f},plan={plan_bonus:.3f},"
            f"score={score:.3f}"
        )
        return action, reason

    def snapshot(self) -> dict[str, Any]:
        graph = DependencyGraph.build(
            self.schemas,
            self.concepts,
            self.hypotheses,
            self.abstractions,
        )
        return {
            "schemas": self.schemas.to_dict(),
            "concepts": self.concepts.to_dict(),
            "hypotheses": self.hypotheses.to_dict(),
            "abstractions": self.abstractions.to_dict(),
            "structural_credit": self.reinforcement.to_dict(),
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
