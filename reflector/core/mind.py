"""Online symbolic world model, schema learner, and experiment selector."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, fields
from typing import Any

from .abstraction import AbstractionStore
from .causal import Experiment, HypothesisStore
from .comparisons import ComparisonTransferSystem
from .graph import DependencyGraph
from .inheritance import (
    EMPTY_COMMON_SENSE_ROOT,
    EMPTY_EVIDENCE_LEDGER_ROOT,
    EMPTY_SCHEME_LIBRARY_ROOT,
    SchemeLibrary,
    common_sense_root,
)
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
from .transformations import TransformationSystem


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
    enable_transformations: bool = True
    enable_modal_reasoning: bool = True
    enable_comparison_transfer: bool = True
    enable_comparison_composition: bool = True
    enable_language_meta_reflection: bool = True
    enable_concept_retirement: bool = True
    enable_epistemic_state_graph: bool = False
    enable_hierarchical_action_fairness: bool = False
    enable_failure_conditioned_fairness: bool = False
    enable_successful_role_replay: bool = False
    enable_multicolor_click_objects: bool = False
    enable_click_object_accommodation: bool = False
    enable_productive_role_reuse: bool = False
    enable_cross_retry_maturity: bool = False
    enable_boundary_nuisance_state_key: bool = False
    enable_boundary_nuisance_fairness: bool = False
    enable_paired_object_contact_planning: bool = False
    enable_paired_contextual_transitions: bool = False
    enable_paired_transport_family: bool = False
    enable_paired_post_accommodation_plan: bool = False
    paired_terminal_relation_mode: str = "contact-only"
    paired_occlusion_procedure_mode: str = "off"
    repeated_form_event_mode: str = "off"
    enable_local_relation_solver: bool = False
    enable_constraint_first_role_replay: bool = False
    enable_global_relation_constraint_solver: bool = False
    enable_preregistered_structural_credit: bool = False
    enable_parameterized_scheme_variation: bool = False
    enable_starter_schemas: bool = False
    enable_inherited_scheme_library: bool = False
    enable_general_reasoning_prior_library: bool = False
    enable_relational_scheme_binding: bool = False
    enable_visual_primitives: bool = False
    enable_visual_primitive_actions: bool = False
    enable_temporal_primitives: bool = False
    enable_cyclic_sequence_alignment: bool = False
    enable_graph_cycle_transport: bool = False
    enable_parameterized_select_apply_commit: bool = False
    enable_multiline_target_binding: bool = False
    enable_spatial_order_variation: bool = False
    enable_nested_target_traversal: bool = False
    enable_nested_source_traversal: bool = False
    enable_enclosure_target_traversal: bool = False
    enable_connector_relocation: bool = False
    enable_constructive_connector_placement: bool = False
    enable_connector_graph_synthesis: bool = False
    enable_lattice_effect_planning: bool = False
    enable_segmented_permutation_transport: bool = False
    enable_path_cycle_transport: bool = False
    enable_factored_orbit_transport: bool = False
    enable_shape_goal_translation: bool = False
    enable_relational_phase_translation: bool = False
    enable_committed_trajectory_planning: bool = False
    enable_colored_stencil_primary_planning: bool = False
    enable_colored_stencil_secondary_planning: bool = False
    enable_first_contact_center_probe: bool = False
    enable_deep_failure_productive_reuse: bool = False
    enable_compact_component_frontier: bool = False
    enable_compact_component_nuisance_filter: bool = False
    enable_action_translation_algebra: bool = False
    enable_action_translation_orbit_probe: bool = False
    enable_action_translation_contact_probe: bool = False
    enable_action_effect_typing: bool = False
    enable_positive_effect_family_fairness: bool = False
    action_budget: int = 80
    planner_max_depth: int = 3
    planner_max_expansions: int = 64
    information_weight: float = 1.0
    experiment_weight: float = 0.25
    plan_weight: float = 10.0
    hierarchy_complexity_pressure: float = 1.0
    inherited_scheme_definitions: tuple[str, ...] = ()
    inherited_scheme_root: str = EMPTY_SCHEME_LIBRARY_ROOT
    inherited_evidence_root: str = EMPTY_EVIDENCE_LEDGER_ROOT
    inherited_common_sense_root: str = EMPTY_COMMON_SENSE_ROOT

    def __post_init__(self) -> None:
        for name in (
            "enable_concepts",
            "enable_counterfactual_pressure",
            "enable_schema_complexity_pressure",
            "enable_experiments",
            "enable_planning",
            "enable_reflecting_abstraction",
            "enable_accommodation",
            "enable_transformations",
            "enable_modal_reasoning",
            "enable_comparison_transfer",
            "enable_comparison_composition",
            "enable_language_meta_reflection",
            "enable_concept_retirement",
            "enable_epistemic_state_graph",
            "enable_hierarchical_action_fairness",
            "enable_failure_conditioned_fairness",
            "enable_successful_role_replay",
            "enable_multicolor_click_objects",
            "enable_click_object_accommodation",
            "enable_productive_role_reuse",
            "enable_cross_retry_maturity",
            "enable_boundary_nuisance_state_key",
            "enable_boundary_nuisance_fairness",
            "enable_paired_object_contact_planning",
            "enable_paired_contextual_transitions",
            "enable_paired_transport_family",
            "enable_paired_post_accommodation_plan",
            "enable_local_relation_solver",
            "enable_constraint_first_role_replay",
            "enable_global_relation_constraint_solver",
            "enable_preregistered_structural_credit",
            "enable_parameterized_scheme_variation",
            "enable_starter_schemas",
            "enable_inherited_scheme_library",
            "enable_general_reasoning_prior_library",
            "enable_relational_scheme_binding",
            "enable_visual_primitives",
            "enable_visual_primitive_actions",
            "enable_temporal_primitives",
            "enable_cyclic_sequence_alignment",
            "enable_graph_cycle_transport",
            "enable_parameterized_select_apply_commit",
            "enable_multiline_target_binding",
            "enable_spatial_order_variation",
            "enable_nested_target_traversal",
            "enable_nested_source_traversal",
            "enable_enclosure_target_traversal",
            "enable_connector_relocation",
            "enable_constructive_connector_placement",
            "enable_connector_graph_synthesis",
            "enable_lattice_effect_planning",
            "enable_segmented_permutation_transport",
            "enable_path_cycle_transport",
            "enable_factored_orbit_transport",
            "enable_shape_goal_translation",
            "enable_relational_phase_translation",
            "enable_committed_trajectory_planning",
            "enable_colored_stencil_primary_planning",
            "enable_colored_stencil_secondary_planning",
            "enable_first_contact_center_probe",
            "enable_deep_failure_productive_reuse",
            "enable_compact_component_frontier",
            "enable_compact_component_nuisance_filter",
            "enable_action_translation_algebra",
            "enable_action_translation_orbit_probe",
            "enable_action_translation_contact_probe",
            "enable_action_effect_typing",
            "enable_positive_effect_family_fairness",
        ):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name} must be a boolean")
        if (
            self.enable_compact_component_nuisance_filter
            and not self.enable_compact_component_frontier
        ):
            raise ValueError(
                "compact component nuisance filtering requires the compact "
                "component frontier"
            )
        if (
            self.enable_action_translation_orbit_probe
            and not self.enable_action_translation_algebra
        ):
            raise ValueError(
                "action translation orbit probing requires the action "
                "translation algebra"
            )
        if (
            self.enable_action_translation_contact_probe
            and not self.enable_action_translation_orbit_probe
        ):
            raise ValueError(
                "action translation contact probing requires orbit probing"
            )
        if (
            self.enable_positive_effect_family_fairness
            and not self.enable_action_effect_typing
        ):
            raise ValueError(
                "positive effect family fairness requires action effect typing"
            )
        if (
            self.enable_colored_stencil_secondary_planning
            and not self.enable_colored_stencil_primary_planning
        ):
            raise ValueError(
                "secondary stencil planning requires primary stencil planning"
            )
        if self.enable_visual_primitive_actions and not self.enable_visual_primitives:
            raise ValueError(
                "visual primitive actions require visual primitive perception"
            )
        if (
            self.enable_failure_conditioned_fairness
            and not self.enable_hierarchical_action_fairness
        ):
            raise ValueError(
                "failure-conditioned fairness requires hierarchical fairness"
            )
        if (
            self.enable_cross_retry_maturity
            and not self.enable_productive_role_reuse
        ):
            raise ValueError(
                "cross-retry maturity requires productive role reuse"
            )
        if self.enable_boundary_nuisance_fairness and not (
            self.enable_boundary_nuisance_state_key
            and self.enable_hierarchical_action_fairness
        ):
            raise ValueError(
                "boundary-nuisance fairness requires boundary state keys "
                "and hierarchical fairness"
            )
        if (
            self.enable_paired_contextual_transitions
            and not self.enable_paired_object_contact_planning
        ):
            raise ValueError(
                "paired contextual transitions require paired object "
                "contact planning"
            )
        if (
            self.enable_paired_transport_family
            and not self.enable_paired_contextual_transitions
        ):
            raise ValueError(
                "paired transport family requires paired contextual "
                "transitions"
            )
        if (
            self.enable_paired_post_accommodation_plan
            and not self.enable_paired_transport_family
        ):
            raise ValueError(
                "paired post-accommodation plan requires paired transport "
                "family"
            )
        if self.paired_terminal_relation_mode not in {
            "contact-only",
            "shortest-grounded",
            "marker-first",
        }:
            raise ValueError(
                "paired_terminal_relation_mode must be contact-only, "
                "shortest-grounded, or marker-first"
            )
        if (
            self.paired_terminal_relation_mode != "contact-only"
            and not self.enable_paired_object_contact_planning
        ):
            raise ValueError(
                "paired terminal relation hypotheses require paired object "
                "planning"
            )
        if self.paired_occlusion_procedure_mode not in {
            "off",
            "repeat-entry",
            "reuse-progress",
            "canonical-probe",
        }:
            raise ValueError(
                "paired_occlusion_procedure_mode must be off, repeat-entry, "
                "reuse-progress, or canonical-probe"
            )
        if (
            self.paired_occlusion_procedure_mode != "off"
            and not self.enable_paired_object_contact_planning
        ):
            raise ValueError(
                "paired occlusion procedures require paired object planning"
            )
        if self.repeated_form_event_mode not in {
            "off",
            "confirm-affordance",
            "confirm-discontinuity",
            "phase-segment",
            "propagate-affordance",
        }:
            raise ValueError(
                "repeated_form_event_mode must be off, confirm-affordance, "
                "confirm-discontinuity, phase-segment, or "
                "propagate-affordance"
            )
        if (
            self.enable_graph_cycle_transport
            and not self.enable_cyclic_sequence_alignment
        ):
            raise ValueError("graph cycle transport requires cyclic sequence alignment")
        if (
            self.enable_segmented_permutation_transport
            and not self.enable_cyclic_sequence_alignment
        ):
            raise ValueError(
                "segmented permutation transport requires cyclic sequence alignment"
            )
        if (
            self.enable_path_cycle_transport
            and not self.enable_segmented_permutation_transport
        ):
            raise ValueError(
                "path cycle transport requires segmented permutation transport"
            )
        if (
            self.enable_factored_orbit_transport
            and not self.enable_segmented_permutation_transport
        ):
            raise ValueError(
                "factored orbit transport requires segmented permutation transport"
            )
        if (
            self.enable_multiline_target_binding
            and not self.enable_parameterized_select_apply_commit
        ):
            raise ValueError(
                "multiline target binding requires parameterized select/apply/commit"
            )
        if (
            self.enable_spatial_order_variation
            and not self.enable_multiline_target_binding
        ):
            raise ValueError(
                "spatial order variation requires multiline target binding"
            )
        if (
            self.enable_nested_target_traversal
            and not self.enable_multiline_target_binding
        ):
            raise ValueError(
                "nested target traversal requires multiline target binding"
            )
        if (
            self.enable_nested_source_traversal
            and not self.enable_nested_target_traversal
        ):
            raise ValueError(
                "nested source traversal requires nested target traversal"
            )
        if (
            self.enable_enclosure_target_traversal
            and not self.enable_nested_target_traversal
        ):
            raise ValueError(
                "enclosure target traversal requires nested target traversal"
            )
        if (
            self.enable_connector_relocation
            and not self.enable_enclosure_target_traversal
        ):
            raise ValueError(
                "connector relocation requires enclosure target traversal"
            )
        if (
            self.enable_constructive_connector_placement
            and not self.enable_enclosure_target_traversal
        ):
            raise ValueError(
                "constructive connector placement requires enclosure target "
                "traversal"
            )
        if (
            self.enable_connector_graph_synthesis
            and not self.enable_enclosure_target_traversal
        ):
            raise ValueError(
                "connector graph synthesis requires enclosure target traversal"
            )
        if (
            self.enable_relational_phase_translation
            and not self.enable_shape_goal_translation
        ):
            raise ValueError(
                "relational phase translation requires shape-goal translation"
            )
        if type(self.planner_max_depth) is not int:
            raise ValueError("planner_max_depth must be an integer")
        if type(self.planner_max_expansions) is not int:
            raise ValueError("planner_max_expansions must be an integer")
        if type(self.action_budget) is not int:
            raise ValueError("action_budget must be an integer")
        if not 1 <= self.action_budget <= 5000:
            raise ValueError("action_budget must be between 1 and 5000")
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
        if type(self.inherited_scheme_definitions) is not tuple or any(
            not isinstance(item, str)
            for item in self.inherited_scheme_definitions
        ):
            raise ValueError(
                "inherited_scheme_definitions must be a tuple of strings"
            )
        if type(self.inherited_scheme_root) is not str:
            raise ValueError("inherited_scheme_root must be a string")
        for name in (
            "inherited_evidence_root",
            "inherited_common_sense_root",
        ):
            value = getattr(self, name)
            if (
                type(value) is not str
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ValueError(f"{name} must be a SHA-256 hash")
        library = SchemeLibrary.from_json_definitions(
            self.inherited_scheme_definitions
        )
        if library.json_definitions() != self.inherited_scheme_definitions:
            raise ValueError(
                "inherited scheme definitions must be sorted by content hash"
            )
        if library.root != self.inherited_scheme_root:
            raise ValueError(
                "inherited_scheme_root does not match inherited definitions"
            )
        if self.enable_inherited_scheme_library and not library.definitions:
            raise ValueError(
                "enabled inherited scheme library must not be empty"
            )
        if (
            self.enable_inherited_scheme_library
            and not self.enable_preregistered_structural_credit
        ):
            raise ValueError(
                "inherited scheme library requires preregistered "
                "structural credit"
            )
        if (
            self.enable_general_reasoning_prior_library
            and not self.enable_preregistered_structural_credit
        ):
            raise ValueError(
                "general reasoning prior library requires preregistered "
                "structural credit"
            )
        if self.inherited_evidence_root != EMPTY_EVIDENCE_LEDGER_ROOT:
            if not self.enable_inherited_scheme_library:
                raise ValueError(
                    "inherited evidence requires an enabled scheme library"
                )
            expected_common_sense_root = common_sense_root(
                self.inherited_scheme_root,
                self.inherited_evidence_root,
            )
            if (
                self.inherited_common_sense_root
                != expected_common_sense_root
            ):
                raise ValueError(
                    "inherited_common_sense_root does not bind library and "
                    "evidence roots"
                )

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        # The genome's authoritative wire form is JSON, where arrays are
        # lists. Returning that form here keeps process-isolation cross-talk
        # checks and candidate identities identical before and after encoding.
        value["inherited_scheme_definitions"] = list(
            self.inherited_scheme_definitions
        )
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MindConfig":
        expected = {item.name for item in fields(cls)}
        unknown = set(value) - expected
        if unknown:
            raise ValueError(f"unknown MindConfig fields: {sorted(unknown)}")
        normalized = dict(value)
        definitions = normalized.get("inherited_scheme_definitions", ())
        if isinstance(definitions, list):
            normalized["inherited_scheme_definitions"] = tuple(definitions)
        return cls(**normalized)


class SymbolicMind:
    """Drescher-inspired learner that updates entirely during inference."""

    def __init__(self, config: MindConfig | None = None) -> None:
        self.config = config or MindConfig()
        self.tracker = SceneTracker(
            enable_visual_primitives=self.config.enable_visual_primitives,
            enable_temporal_primitives=self.config.enable_temporal_primitives,
        )
        self.schemas = SchemaStore()
        self.concepts = ConceptStore(
            complexity_pressure=(
                1.0 if self.config.enable_schema_complexity_pressure else 0.0
            ),
            require_counterfactual_utility=(self.config.enable_counterfactual_pressure),
            enable_retirement=self.config.enable_concept_retirement,
        )
        self.hypotheses = HypothesisStore()
        self.reinforcement = StructuralCreditLedger()
        self.transformations = TransformationSystem(
            complexity_pressure=self.config.hierarchy_complexity_pressure
        )
        self.comparisons = ComparisonTransferSystem()
        self.abstractions = AbstractionStore(
            complexity_pressure=self.config.hierarchy_complexity_pressure,
            enable_language_meta_reflection=(
                self.config.enable_language_meta_reflection
            ),
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
                        *self.concepts.context_atoms(transition.action_id),
                    )
                ),
                action_id=transition.action_id,
                action_data=transition.action_data,
                result=transition.result,
            )
            # Freeze the forecast before the observed transition updates any
            # schema.  This prevents hindsight from masquerading as
            # prediction and gives contradiction a structural target.
            primed = (
                self.reinforcement.consume_primed(
                    transition.action_id,
                    transition.action_data,
                )
                if self.config.enable_preregistered_structural_credit
                else None
            )
            prediction = (
                primed.prediction()
                if primed is not None
                else self.schemas.predict(
                    transition.action_id,
                    transition.context,
                )
            )
            if self.config.enable_accommodation and primed is None:
                prediction = self.reinforcement.accommodate_prediction(
                    action_id=transition.action_id,
                    context=transition.context,
                    prediction=prediction,
                )
            assessment_id = self.reinforcement.assess(
                transition,
                prediction,
                primed,
            )
            new_assessments = (assessment_id,)
            if self.config.enable_accommodation:
                new_abstractions = self.reinforcement.last_constructed
            schema = self.schemas.observe(transition)
            comparison_updates = self.comparisons.observe(
                transition,
                self._last_scene,
                allow_transfer=self.config.enable_comparison_transfer,
                allow_composition=self.config.enable_comparison_composition,
            )
            comparison_goals = self.comparisons.observe_goal(
                transition,
                self._last_scene,
            )
            new_abstractions = tuple(
                sorted(
                    set(new_abstractions)
                    | set(comparison_updates)
                    | set(comparison_goals)
                )
            )
            if self.config.enable_transformations:
                new_abstractions = tuple(
                    sorted(
                        set(new_abstractions)
                        | set(self.transformations.reflect(self.schemas))
                        | set(
                            self.transformations.observe_goal(
                                transition,
                                self._last_scene,
                            )
                        )
                    )
                )
                if self.config.enable_modal_reasoning:
                    new_abstractions = tuple(
                        sorted(
                            set(new_abstractions)
                            | set(
                                self.transformations.observe_impossible_touching(
                                    transition,
                                    self._last_scene,
                                    max_expansions=(self.config.planner_max_expansions),
                                )
                            )
                        )
                    )
            new_hypotheses = self.hypotheses.observe(transition, self.schemas)
            if self.config.enable_reflecting_abstraction:
                new_abstractions = self.abstractions.observe_procedure(
                    transition,
                    schema.schema_id,
                    max_steps=self.config.planner_max_depth,
                )
            if self.config.enable_concepts:
                new_concepts = self.concepts.reflect(self.schemas)
            if self.config.enable_reflecting_abstraction:
                new_abstractions = tuple(
                    sorted(
                        set(new_abstractions)
                        | set(self.abstractions.reflect(self.schemas, self.concepts))
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
                new_assessments = tuple(sorted(set(new_assessments) | set(integrated)))
        self._last_scene = scene
        return MindUpdate(
            scene,
            transition,
            new_concepts,
            new_hypotheses,
            new_abstractions,
            new_assessments,
        )

    def prime_hypothesis(
        self,
        decision: Decision,
        *,
        scheme_components: tuple[str, ...] = (),
    ) -> str | None:
        """Put exact symbolic dependencies at risk before an intervention."""

        if (
            not self.config.enable_preregistered_structural_credit
            or self._last_scene is None
        ):
            return None
        context = canonical_atoms(
            (
                *self._last_scene.context(),
                *self.concepts.context_atoms(decision.action_id),
            )
        )
        prediction = self.schemas.predict(decision.action_id, context)
        if self.config.enable_accommodation:
            prediction = self.reinforcement.accommodate_prediction(
                action_id=decision.action_id,
                context=context,
                prediction=prediction,
            )
        return self.reinforcement.prime(
            before_index=self._last_scene.index,
            action_id=decision.action_id,
            action_data=decision.data,
            context=context,
            prediction=prediction,
            scheme_components=scheme_components,
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
        context = self._last_scene.context() if self._last_scene is not None else ()
        procedure = (
            self.abstractions.procedure_match(context, legal_actions)
            if self.config.enable_planning and self.config.enable_reflecting_abstraction
            else None
        )
        transformation_plan = (
            self.transformations.plan_touching(
                self._last_scene,
                legal_actions,
                max_depth=self.config.planner_max_depth,
                max_expansions=self.config.planner_max_expansions,
            )
            if self._last_scene is not None
            and self.config.enable_planning
            and self.config.enable_transformations
            else None
        )
        comparison_plan = (
            self.comparisons.plan_touching(
                self._last_scene,
                legal_actions,
                max_depth=self.config.planner_max_depth,
                max_expansions=self.config.planner_max_expansions,
            )
            if self._last_scene is not None and self.config.enable_planning
            else None
        )
        modal_action = (
            self.transformations.modal_touching_decision(
                self._last_scene,
                legal_actions,
                max_expansions=self.config.planner_max_expansions,
            )
            if self._last_scene is not None
            and self.config.enable_planning
            and self.config.enable_transformations
            and self.config.enable_modal_reasoning
            and transformation_plan is None
            else None
        )
        self.last_plan = (
            Plan(
                goal=Goal("touching", priority=1.0),
                actions=comparison_plan.actions,
                predicted_events=("touching",),
                confidence=comparison_plan.confidence,
                expansions=comparison_plan.expansions,
            )
            if comparison_plan is not None
            else Plan(
                goal=Goal("touching", priority=1.0),
                actions=transformation_plan[0],
                predicted_events=("touching",),
                confidence=transformation_plan[1],
                expansions=transformation_plan[2],
            )
            if transformation_plan is not None
            else Plan(
                goal=Goal("impossible_touching", priority=1.0),
                actions=(modal_action[0],),
                predicted_events=("level_advanced",),
                confidence=1.0,
                expansions=modal_action[1].expansions,
            )
            if modal_action is not None
            else Plan(
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
        if comparison_plan is not None:
            action = comparison_plan.actions[0]
            return (
                action,
                "comparison-transfer-plan:"
                f"actions={comparison_plan.actions},"
                f"inferred={comparison_plan.inferred_operators},"
                f"expansions={comparison_plan.expansions}",
            )
        if transformation_plan is not None:
            action = transformation_plan[0][0]
            return (
                action,
                "transformation-plan:"
                f"actions={transformation_plan[0]},"
                f"confidence={transformation_plan[1]:.3f},"
                f"expansions={transformation_plan[2]}",
            )
        if modal_action is not None:
            modal_kind = (
                "modal-possible:" if modal_action[1].possible else "modal-impossible:"
            )
            return (
                modal_action[0],
                f"{modal_kind}"
                f"reachable_states={modal_action[1].reachable_states},"
                f"expansions={modal_action[1].expansions}",
            )

        scored: list[tuple[float, int, float, float, float, float, float]] = []
        for action in legal_actions:
            trials = self.schemas.contextual_trials(action, context)
            transfer_value = (
                self.abstractions.action_transfer_value(action, self.schemas, context)
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
                    and self.reinforcement.accommodations[evidence].proposition
                    in {"level_advanced", "WIN", "GAME_OVER"}
                    for evidence in accommodated.evidence
                ):
                    predicted = self.schemas.result_value(accommodated.result)
            information = 1.0 / math.sqrt(trials + 1)
            experiment = experiment_by_action.get(action)
            experiment_bonus = (
                experiment.score * self.config.experiment_weight if experiment else 0.0
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
                    transformation_plan is not None
                    or procedure is not None
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
            "transformations": self.transformations.to_dict(),
            "comparisons": self.comparisons.to_dict(),
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
