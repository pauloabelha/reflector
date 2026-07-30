"""Smallest deterministic symbolic ARC-AGI-3 policy.

The policy deliberately speaks in protocol primitives (integer action ids and
immutable observations), so it has no dependency on Kaggle, the ARC toolkit,
the web UI, a database, or development-time services.
"""

from __future__ import annotations

from typing import Any

from ..core.exploration import EpistemicExplorer
from ..core.inheritance import SchemeLibrary
from ..core.mind import MindConfig, MindUpdate, SymbolicMind
from ..core.symbolic import Decision, Observation
from .trace import EpisodeTrace, TraceStep


class SymbolicPolicy:
    """Deterministic, dependency-free baseline that only emits legal actions."""

    RESET = 0
    COMPLEX = 6
    TERMINAL = "WIN"
    NEEDS_RESET = frozenset({"NOT_PLAYED", "GAME_OVER", "NOT_STARTED"})

    def __init__(self, config: MindConfig | None = None) -> None:
        self.observations_seen = 0
        self.action_counts: dict[int, int] = {}
        self.mind = SymbolicMind(config)
        self.trace = EpisodeTrace(mind_config=self.mind.config.to_dict())
        self.explorer = EpistemicExplorer(
            hierarchical_action_fairness=(
                self.mind.config.enable_hierarchical_action_fairness
            ),
            failure_conditioned_fairness=(
                self.mind.config.enable_failure_conditioned_fairness
            ),
            successful_role_replay=(
                self.mind.config.enable_successful_role_replay
                or self.mind.config.enable_constraint_first_role_replay
            ),
            multicolor_click_objects=self.mind.config.enable_multicolor_click_objects,
            click_object_accommodation=(
                self.mind.config.enable_click_object_accommodation
            ),
            productive_role_reuse=self.mind.config.enable_productive_role_reuse,
            cross_retry_maturity=(
                self.mind.config.enable_cross_retry_maturity
            ),
            deep_failure_productive_reuse=(
                self.mind.config.enable_deep_failure_productive_reuse
            ),
            compact_component_frontier=(
                self.mind.config.enable_compact_component_frontier
            ),
            boundary_nuisance_state_key=(
                self.mind.config.enable_boundary_nuisance_state_key
            ),
            boundary_nuisance_fairness=(
                self.mind.config.enable_boundary_nuisance_fairness
            ),
            paired_object_contact_planning=(
                self.mind.config.enable_paired_object_contact_planning
            ),
            paired_contextual_transitions=(
                self.mind.config.enable_paired_contextual_transitions
            ),
            paired_transport_family=(
                self.mind.config.enable_paired_transport_family
            ),
            paired_post_accommodation_plan=(
                self.mind.config.enable_paired_post_accommodation_plan
            ),
            paired_terminal_relation_mode=(
                self.mind.config.paired_terminal_relation_mode
            ),
            paired_occlusion_procedure_mode=(
                self.mind.config.paired_occlusion_procedure_mode
            ),
            repeated_form_event_mode=(
                self.mind.config.repeated_form_event_mode
            ),
            local_relation_solver=self.mind.config.enable_local_relation_solver,
            constraint_first_role_replay=(
                self.mind.config.enable_constraint_first_role_replay
            ),
            global_relation_constraint_solver=(
                self.mind.config.enable_global_relation_constraint_solver
            ),
            parameterized_scheme_variation=(
                self.mind.config.enable_parameterized_scheme_variation
            ),
            starter_schemas=self.mind.config.enable_starter_schemas,
            inherited_scheme_library=(
                SchemeLibrary.from_json_definitions(
                    self.mind.config.inherited_scheme_definitions
                )
                if self.mind.config.enable_inherited_scheme_library
                else SchemeLibrary()
            ),
            relational_scheme_binding=(
                self.mind.config.enable_relational_scheme_binding
            ),
            visual_primitives=(self.mind.config.enable_visual_primitive_actions),
            cyclic_sequence_alignment=(
                self.mind.config.enable_cyclic_sequence_alignment
            ),
            graph_cycle_transport=(self.mind.config.enable_graph_cycle_transport),
            parameterized_select_apply_commit=(
                self.mind.config.enable_parameterized_select_apply_commit
            ),
            multiline_target_binding=(
                self.mind.config.enable_multiline_target_binding
            ),
            spatial_order_variation=(
                self.mind.config.enable_spatial_order_variation
            ),
            nested_target_traversal=(
                self.mind.config.enable_nested_target_traversal
            ),
            nested_source_traversal=(
                self.mind.config.enable_nested_source_traversal
            ),
            enclosure_target_traversal=(
                self.mind.config.enable_enclosure_target_traversal
            ),
            connector_relocation=(
                self.mind.config.enable_connector_relocation
            ),
            constructive_connector_placement=(
                self.mind.config.enable_constructive_connector_placement
            ),
            connector_graph_synthesis=(
                self.mind.config.enable_connector_graph_synthesis
            ),
            lattice_effect_planning=(
                self.mind.config.enable_lattice_effect_planning
            ),
            segmented_permutation_transport=(
                self.mind.config.enable_segmented_permutation_transport
            ),
            path_cycle_transport=(
                self.mind.config.enable_path_cycle_transport
            ),
            shape_goal_translation=(
                self.mind.config.enable_shape_goal_translation
            ),
            relational_phase_translation=(
                self.mind.config.enable_relational_phase_translation
            ),
            committed_trajectory_planning=(
                self.mind.config.enable_committed_trajectory_planning
            ),
        )
        self._previous_decision: Decision | None = None
        self._last_observation: Observation | None = None
        self._last_update: MindUpdate | None = None
        self._decision_epoch = 0
        self._last_ingested_epoch = -1
        self._first_contact_center_probe_issued = False

    def is_done(self, observation: Observation) -> bool:
        return observation.state == self.TERMINAL

    def observe(self, observation: Observation) -> MindUpdate:
        """Ingest each environment observation exactly once.

        The official agent adapter calls this from ``append_frame`` so terminal
        results are learned even though the official loop never chooses another
        action after WIN.
        """

        if (
            observation == self._last_observation
            and self._last_update is not None
            and self._last_ingested_epoch == self._decision_epoch
        ):
            return self._last_update
        self.observations_seen += 1
        update = self.mind.ingest(observation, self._previous_decision)
        self.explorer.observe(observation, update.scene)
        self._last_observation = observation
        self._last_update = update
        self._last_ingested_epoch = self._decision_epoch
        if self.is_done(observation):
            self.trace.finish(observation, update.scene, update.transition)
        return update

    def choose_action(self, observation: Observation) -> Decision:
        update = self.observe(observation)
        if observation.state in self.NEEDS_RESET:
            self.mind.last_experiment = None
            self.mind.last_plan = None
            decision = self._record(Decision(self.RESET, reason="reset-required"))
            self._append_trace(observation, decision, update)
            self._previous_decision = decision
            self._decision_epoch += 1
            return decision

        legal = tuple(
            action for action in observation.available_actions if action != self.RESET
        )
        if not legal:
            raise ValueError("active observation exposes no legal non-reset action")

        data: tuple[tuple[str, int], ...]
        if (
            self.mind.config.enable_first_contact_center_probe
            and not self._first_contact_center_probe_issued
            and self.COMPLEX in legal
        ):
            action_id = self.COMPLEX
            reason = "first-contact-center-probe"
            x, y = self._frame_center(observation.frame)
            data = (("x", x), ("y", y))
            self._first_contact_center_probe_issued = True
        elif self.mind.config.enable_epistemic_state_graph:
            exploration = self.explorer.select(
                observation,
                update.scene,
                legal,
                pragmatic_disequilibrium=(
                    self.mind.reinforcement.pragmatic_disequilibrium
                ),
                structure_scores=(self.mind.reinforcement.pragmatic_structure_scores()),
            )
            action_id = exploration.token.action_id
            reason = exploration.reason
            data = exploration.token.data
        else:
            action_id, reason = self.mind.select_action(legal)
            data = ()
        if action_id == self.COMPLEX and data:
            decision = self._record(
                Decision(
                    action_id,
                    data=data,
                    reason=reason,
                )
            )
        elif action_id == self.COMPLEX:
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
        self.mind.prime_hypothesis(
            decision,
            scheme_components=self.explorer.last_scheme_components,
        )
        self._append_trace(observation, decision, update)
        self._previous_decision = decision
        self._decision_epoch += 1
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
                    concept.concept_id for concept in update.new_concepts
                ),
                new_hypotheses=update.new_hypotheses,
                new_abstractions=update.new_abstractions,
                new_assessments=update.new_assessments,
                experiment=(
                    self.mind.last_experiment.question
                    if self.mind.last_experiment is not None
                    else None
                ),
                plan_actions=(
                    self.mind.last_plan.actions
                    if self.mind.last_plan is not None
                    else ()
                ),
                planner_expansions=self.mind.planner.last_expansions,
            )
        )

    def cognitive_event(
        self,
        observation: Observation,
        decision: Decision,
    ) -> dict[str, Any]:
        """Return bounded inspectable symbolic state for development streaming."""

        update = self._last_update
        assessments = []
        if update is not None:
            for assessment_id in update.new_assessments:
                assessment = self.mind.reinforcement.assessments.get(assessment_id)
                if assessment is None:
                    continue
                assessments.append(
                    {
                        "assessment_id": assessment.assessment_id,
                        "hypothesis_id": assessment.hypothesis_id,
                        "action_id": assessment.action_id,
                        "predicted": list(assessment.predicted),
                        "observed": list(assessment.observed),
                        "confirmed": list(assessment.confirmed),
                        "contradicted": list(assessment.contradicted),
                        "confirmed_absent": list(assessment.confirmed_absent),
                        "contradicted_absent": list(assessment.contradicted_absent),
                        "unpredicted": list(assessment.unpredicted),
                        "pragmatic": list(assessment.pragmatic),
                        "epistemic": list(assessment.epistemic),
                        "response": assessment.response,
                        "support": assessment.support,
                        "licensing_structures": list(assessment.licensing_structures),
                        "scheme_components": list(assessment.scheme_components),
                        "context_count": len(assessment.context),
                        "context_sample": [
                            term
                            for term in assessment.context
                            if not term.startswith("object_signature(")
                        ][:16],
                        "object_signature_count": sum(
                            term.startswith("object_signature(")
                            for term in assessment.context
                        ),
                        "perturbation_count": len(assessment.perturbation),
                    }
                )
        abstractions = self.mind.abstractions
        primitive_counts: dict[str, int] = {}
        if update is not None:
            for primitive in update.scene.primitives:
                primitive_counts[primitive.kind] = (
                    primitive_counts.get(primitive.kind, 0) + 1
                )
        return {
            "format": "reflector-cognitive-event-v1",
            "sequence": max(0, self._decision_epoch - 1),
            "observation": {
                "state": observation.state,
                "levels_completed": observation.levels_completed,
                "available_actions": list(observation.available_actions),
                "frame_digest": (
                    update.scene.frame_digest if update is not None else None
                ),
                "object_count": (
                    len(update.scene.objects) if update is not None else 0
                ),
                "primitive_counts": primitive_counts,
            },
            "decision": decision.to_dict(),
            "advisor_arbitration": self.explorer.arbitration_snapshot(decision.reason),
            "transition": (
                update.transition.to_dict()
                if update is not None and update.transition is not None
                else None
            ),
            "construction_delta": {
                "concepts": (
                    [item.concept_id for item in update.new_concepts]
                    if update is not None
                    else []
                ),
                "hypotheses": (
                    list(update.new_hypotheses) if update is not None else []
                ),
                "abstractions": (
                    list(update.new_abstractions) if update is not None else []
                ),
                "assessments": assessments,
            },
            "operative_state": {
                "schema_count": len(self.mind.schemas.schemas),
                "active_concept_count": len(self.mind.concepts.active_concepts()),
                "schema_family_count": len(abstractions.schema_families),
                "concept_type_count": len(abstractions.concept_types),
                "language_operator_count": len(abstractions.language_operators),
                "procedure_count": len(abstractions.procedures),
                "accommodation_count": len(self.mind.reinforcement.accommodations),
                "primed_hypothesis_count": len(
                    self.mind.reinforcement.hypothesis_history
                ),
                "typed_credit_structure_count": len(
                    self.mind.reinforcement.typed_credit
                ),
                "consecutive_without_progress": (
                    self.mind.reinforcement.consecutive_without_progress
                ),
                "pragmatic_disequilibrium": (
                    self.mind.reinforcement.pragmatic_disequilibrium
                ),
                "learned_local_relation": dict(
                    sorted(self.explorer.learned_local_relation.items())
                ),
                "exploration": self.explorer.to_dict(),
            },
        }

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

    @staticmethod
    def _frame_center(frame: tuple[tuple[int, ...], ...]) -> tuple[int, int]:
        if not frame or not frame[0]:
            return (32, 32)
        return (
            max(0, min(63, len(frame[0]) // 2)),
            max(0, min(63, len(frame) // 2)),
        )
