"""Bounded epistemic exploration over observed symbolic states."""

from __future__ import annotations

import hashlib
import heapq
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

from .symbolic import ObjectState, Observation, Scene

StateKey = tuple[int, str, str]
PhaseSignature = tuple[
    tuple[
        int,
        int,
        tuple[tuple[int, int], ...],
        tuple[tuple[int, int, int], ...],
    ],
    ...,
]


@dataclass(frozen=True, order=True, slots=True)
class ActionToken:
    """A concrete legal intervention, including complex-action arguments."""

    action_id: int
    data: tuple[tuple[str, int], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {"action_id": self.action_id, "data": dict(self.data)}


@dataclass(frozen=True, slots=True)
class ExplorationChoice:
    token: ActionToken
    reason: str


@dataclass(frozen=True, order=True, slots=True)
class ActionRole:
    """Coordinate-free structural role of an observed intervention."""

    action_id: int
    color: int | None = None
    area: int | None = None
    shape: tuple[tuple[int, int], ...] = ()
    primitive_kind: str | None = None
    primitive_properties: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StarterSchema:
    """A content-free sensorimotor form available before experience."""

    schema_id: str
    operator: str
    slots: tuple[str, ...]
    complexity_cost: int

    def component(self) -> str:
        return f"scheme:starter:{self.schema_id}"


STARTER_SCHEMA_SET = (
    StarterSchema(
        "probe-action-family",
        "intervene",
        ("action-family",),
        1,
    ),
    StarterSchema(
        "intervene-on-object",
        "intervene",
        ("action", "object"),
        2,
    ),
    StarterSchema(
        "intervene-on-region",
        "intervene",
        ("action", "visual-region"),
        3,
    ),
    StarterSchema(
        "repair-relation",
        "intervene",
        ("action", "source", "relation", "target"),
        3,
    ),
    StarterSchema(
        "bind-manner-to-action",
        "compose",
        ("base-scheme", "modifier-scheme", "role-relation"),
        4,
    ),
    StarterSchema(
        "bounded-novelty",
        "intervene",
        ("action", "untried-state"),
        2,
    ),
)


@dataclass(frozen=True, slots=True)
class GroundedRole:
    """An action role temporarily grounded in one perceived object."""

    role: ActionRole
    centroid: tuple[int, int] | None = None
    primitive_id: str | None = None


@dataclass(frozen=True, slots=True)
class CyclicAlignmentScheme:
    """An evidenced, appearance-relative goal over cyclic transports."""

    scheme_id: str
    target_relation: str
    controller_side: str
    shift_direction: int
    evidence: tuple[str, ...]

    def components(self) -> tuple[str, ...]:
        return (
            f"scheme:{self.scheme_id}",
            "relation:anchor-token-matches-markers",
            "operator:cyclic-shift",
        )


@dataclass(frozen=True, slots=True)
class _FrameObject:
    color: int
    area: int
    bbox: tuple[int, int, int, int]
    centroid: tuple[int, int]
    shape: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class _MarkedAnchor:
    point: tuple[int, int]
    marker_color: int
    token_area: int
    token_shape: tuple[tuple[int, int], ...]


@dataclass(frozen=True, slots=True)
class _CyclicTrack:
    points: tuple[tuple[int, int], ...]
    left_controller: tuple[int, int] | None = None
    right_controller: tuple[int, int] | None = None


@dataclass(frozen=True, slots=True)
class _TrajectoryGrounding:
    mover_signature: tuple[int, int, int, tuple[tuple[int, int], ...]]
    mover_anchor: tuple[int, int]
    mover_color: int
    target_anchor: tuple[int, int]
    target_color: int
    receptacle_signature: tuple[int, int, int, tuple[tuple[int, int], ...]]


@dataclass(frozen=True, slots=True)
class RoleRelation:
    """Content-free relation supplied by one scheme to another."""

    color: str = "any"
    area: str = "any"
    shape: str = "any"
    horizontal: str = "any"
    vertical: str = "any"


@dataclass(frozen=True, slots=True)
class RelationalScheme:
    """A base action scheme parameterized by another scheme's manner."""

    scheme_id: str
    base_id: str
    modifier_id: str
    operator: str
    action_slots: tuple[int, ...]
    constraints: tuple[RoleRelation, ...]
    evidence: tuple[str, ...]

    def components(self) -> tuple[str, ...]:
        return (
            f"scheme:{self.scheme_id}",
            f"base:{self.base_id}",
            f"modifier:{self.modifier_id}",
            f"operator:{self.operator}",
            "scheme:starter:bind-manner-to-action",
        )


@dataclass(frozen=True, slots=True)
class ParameterizedScheme:
    """One learned scheme supplied as a typed modifier to another."""

    scheme_id: str
    base_id: str
    argument_id: str
    operator: str
    roles: tuple[ActionRole, ...]
    evidence: tuple[str, ...]

    def components(self) -> tuple[str, ...]:
        return (
            f"scheme:{self.scheme_id}",
            f"base:{self.base_id}",
            f"argument:{self.argument_id}",
            f"operator:{self.operator}",
        )


@dataclass(slots=True)
class EpistemicExplorer:
    """Construct and traverse a finite graph of tried interventions.

    Nodes are actually observed frame digests, separated by level and game
    state. Edges are concrete interventions. The controller first tries every
    represented intervention in the current state, then uses known edges to
    reach another state with an untried intervention. It never peeks into an
    environment or assumes action semantics.
    """

    complex_action: int = 6
    reset_action: int = 0
    max_states: int = 4096
    max_click_candidates: int = 256
    max_relational_trials_per_level: int = 8
    max_relational_application_steps: int = 4
    max_productive_reuse_trials_per_level: int = 8
    min_productive_reuse_interventions: int = 32
    max_cyclic_alignment_trials_per_level: int = 24
    max_cyclic_plan_expansions: int = 8192
    hierarchical_action_fairness: bool = False
    failure_conditioned_fairness: bool = False
    successful_role_replay: bool = False
    multicolor_click_objects: bool = False
    click_object_accommodation: bool = False
    productive_role_reuse: bool = False
    cross_retry_maturity: bool = False
    local_relation_solver: bool = False
    constraint_first_role_replay: bool = False
    global_relation_constraint_solver: bool = False
    parameterized_scheme_variation: bool = False
    starter_schemas: bool = False
    relational_scheme_binding: bool = False
    visual_primitives: bool = False
    cyclic_sequence_alignment: bool = False
    graph_cycle_transport: bool = False
    parameterized_select_apply_commit: bool = False
    multiline_target_binding: bool = False
    spatial_order_variation: bool = False
    nested_target_traversal: bool = False
    nested_source_traversal: bool = False
    enclosure_target_traversal: bool = False
    connector_relocation: bool = False
    shape_goal_translation: bool = False
    relational_phase_translation: bool = False
    committed_trajectory_planning: bool = False
    attempts: Counter[tuple[StateKey, ActionToken]] = field(default_factory=Counter)
    global_attempts: Counter[ActionToken] = field(default_factory=Counter)
    family_attempts: Counter[tuple[StateKey, int]] = field(default_factory=Counter)
    global_family_attempts: Counter[int] = field(default_factory=Counter)
    edges: dict[tuple[StateKey, ActionToken], StateKey] = field(default_factory=dict)
    tokens_by_state: dict[StateKey, tuple[ActionToken, ...]] = field(
        default_factory=dict
    )
    state_status: dict[StateKey, str] = field(default_factory=dict)
    visit_order: list[StateKey] = field(default_factory=list)
    current_state: StateKey | None = None
    pending: tuple[StateKey, ActionToken] | None = None
    current_level: int | None = None
    episode_roles: list[ActionRole] = field(default_factory=list)
    episode_groundings: list[GroundedRole] = field(default_factory=list)
    productive_groundings: list[GroundedRole] = field(default_factory=list)
    successful_program: tuple[ActionRole, ...] = ()
    program_cursor: int = 0
    level_failures: int = 0
    selection_frame: tuple[tuple[int, ...], ...] = ()
    pending_frame: tuple[tuple[int, ...], ...] = ()
    pending_role: ActionRole | None = None
    pending_grounding: GroundedRole | None = None
    role_trials: Counter[ActionRole] = field(default_factory=Counter)
    role_responses: Counter[ActionRole] = field(default_factory=Counter)
    productive_reuse_level_trials: int = 0
    level_interventions: int = 0
    learned_local_relation: dict[int, bool] = field(default_factory=dict)
    successful_schemes: dict[str, tuple[ActionRole, ...]] = field(default_factory=dict)
    parameterized_schemes: dict[str, ParameterizedScheme] = field(default_factory=dict)
    variation_cursors: dict[str, int] = field(default_factory=dict)
    variation_trials: Counter[str] = field(default_factory=Counter)
    successful_relational_schemes: dict[str, tuple[GroundedRole, ...]] = field(
        default_factory=dict
    )
    relational_schemes: dict[str, RelationalScheme] = field(default_factory=dict)
    relational_cursors: dict[str, int] = field(default_factory=dict)
    relational_last: dict[str, GroundedRole] = field(default_factory=dict)
    relational_trials: Counter[str] = field(default_factory=Counter)
    relational_responses: Counter[str] = field(default_factory=Counter)
    relational_progress: Counter[str] = field(default_factory=Counter)
    relational_stagnations: Counter[str] = field(default_factory=Counter)
    relational_application_steps: Counter[str] = field(default_factory=Counter)
    relational_level_trials: int = 0
    pending_relational_scheme: str | None = None
    last_relational_binding: dict[str, Any] = field(default_factory=dict)
    last_scheme_components: tuple[str, ...] = ()
    primitive_accommodation_active: bool = False
    pragmatic_disequilibrium_active: bool = False
    cyclic_alignment_scheme: CyclicAlignmentScheme | None = None
    cyclic_alignment_level_trials: int = 0
    cyclic_transport_evidence: Counter[tuple[str, int]] = field(default_factory=Counter)
    cyclic_last_plan_length: int = 0
    grounded_cyclic_transports: dict[
        tuple[tuple[tuple[int, int], ...], tuple[int, int]], int
    ] = field(default_factory=dict)
    select_apply_program: tuple[ActionToken, ...] = ()
    select_apply_cursor: int = 0
    select_apply_attempted: bool = False
    select_apply_level_trials: int = 0
    nested_target_plan_active: bool = False
    nested_source_plan_active: bool = False
    connector_relocation_plan_active: bool = False
    select_apply_diagnostic: str = "not-attempted"
    shape_translation_probes: set[int] = field(default_factory=set)
    shape_translation_effects: dict[int, tuple[int, int]] = field(
        default_factory=dict
    )
    shape_translation_effect_evidence: Counter[int] = field(
        default_factory=Counter
    )
    shape_translation_invalid_actions: set[int] = field(default_factory=set)
    shape_goal_mover_signature: (
        tuple[int, int, tuple[tuple[int, int], ...]] | None
    ) = None
    shape_goal_target_signature: (
        tuple[int, int, tuple[tuple[int, int], ...]] | None
    ) = None
    shape_translation_level_trials: int = 0
    shape_translation_application_trials: int = 0
    shape_translation_diagnostic: str = "not-attempted"
    shape_goal_latent_mover_origin: tuple[int, int] | None = None
    shape_goal_latent_target_origin: tuple[int, int] | None = None
    shape_translation_occluded_action: int | None = None
    shape_translation_occluded_steps: int = 0
    shape_translation_pending_prediction: (
        tuple[
            int,
            tuple[int, int, tuple[tuple[int, int], ...]],
            tuple[int, int, tuple[tuple[int, int], ...]],
            tuple[int, int],
            tuple[int, int],
            tuple[int, int],
        ]
        | None
    ) = None
    shape_translation_phase: PhaseSignature | None = None
    shape_translation_phase_models: dict[
        PhaseSignature,
        tuple[
            set[int],
            dict[int, tuple[int, int]],
            Counter[int],
            set[int],
        ],
    ] = field(default_factory=dict)
    shape_translation_phase_transitions: dict[
        tuple[PhaseSignature, int],
        PhaseSignature,
    ] = field(default_factory=dict)
    shape_translation_phase_transition_count: int = 0
    shape_translation_phase_blocked: bool = False
    trajectory_stage: str = "not-attempted"
    trajectory_mover_signature: (
        tuple[int, int, int, tuple[tuple[int, int], ...]] | None
    ) = None
    trajectory_receptacle_signature: (
        tuple[int, int, int, tuple[tuple[int, int], ...]] | None
    ) = None
    trajectory_mover_color: int | None = None
    trajectory_target_color: int | None = None
    trajectory_origin: tuple[int, int] | None = None
    trajectory_current_anchor: tuple[int, int] | None = None
    trajectory_latent_anchor: tuple[int, int] | None = None
    trajectory_target_anchor: tuple[int, int] | None = None
    trajectory_probes: set[int] = field(default_factory=set)
    trajectory_no_effect_actions: set[int] = field(default_factory=set)
    trajectory_effects: dict[int, tuple[int, int]] = field(default_factory=dict)
    trajectory_effect_evidence: Counter[int] = field(default_factory=Counter)
    trajectory_invalid_actions: set[int] = field(default_factory=set)
    trajectory_contextual_blocks: Counter[tuple[tuple[int, int], int]] = field(
        default_factory=Counter
    )
    trajectory_gate_failures: Counter[tuple[tuple[int, int], int]] = field(
        default_factory=Counter
    )
    trajectory_gate_cooldowns: dict[
        tuple[tuple[int, int], int],
        int,
    ] = field(default_factory=dict)
    trajectory_gate_refresh_actions: Counter[int] = field(
        default_factory=Counter
    )
    trajectory_topology_nodes: set[tuple[int, int]] = field(
        default_factory=set
    )
    trajectory_uncertain_nodes: set[tuple[int, int]] = field(
        default_factory=set
    )
    trajectory_topology_support_color: int | None = None
    trajectory_restore_tried: set[int] = field(default_factory=set)
    trajectory_macro_action: int | None = None
    trajectory_macro_effect: tuple[int, int] | None = None
    trajectory_previous_failed_macro_action: int | None = None
    trajectory_active_path: list[tuple[int, int]] = field(default_factory=list)
    trajectory_enacted_path: list[tuple[int, int]] = field(default_factory=list)
    trajectory_endpoint_macros: list[tuple[tuple[int, int], ...]] = field(
        default_factory=list
    )
    trajectory_commit_action: int | None = None
    trajectory_commit_trials: int = 0
    trajectory_committed_macro: tuple[tuple[int, int], ...] = ()
    trajectory_replay_started: bool = False
    trajectory_replay_anchor: tuple[int, int] | None = None
    trajectory_replay_cursor: int = 0
    trajectory_replay_validations: int = 0
    trajectory_replay_misses: int = 0
    trajectory_navigation_action: int | None = None
    trajectory_settle_steps: int = 0
    trajectory_plan_steps: int = 0
    trajectory_level_trials: int = 0
    trajectory_pending: (
        tuple[str, int, tuple[int, int], tuple[int, int] | None] | None
    ) = None
    trajectory_causal_states: set[
        tuple[
            tuple[int, int],
            tuple[int, int],
            tuple[int, tuple[int, int], int] | None,
            int,
        ]
    ] = field(default_factory=set)
    trajectory_causal_edges: set[
        tuple[
            tuple[
                tuple[int, int],
                tuple[int, int],
                tuple[int, tuple[int, int], int] | None,
                int,
            ],
            int,
            tuple[
                tuple[int, int],
                tuple[int, int],
                tuple[int, tuple[int, int], int] | None,
                int,
            ],
        ]
    ] = field(default_factory=set)
    trajectory_boundary_transitions: list[
        tuple[int, tuple[int, ...], tuple[int, ...]]
    ] = field(default_factory=list)
    trajectory_boundary_nuisance_evidenced: bool = False
    trajectory_diagnostic: str = "not-attempted"
    trajectory_disabled: bool = False

    @property
    def uses_action_family_schema(self) -> bool:
        fairness_active = self.hierarchical_action_fairness and (
            not self.failure_conditioned_fairness or self.level_failures >= 2
        )
        return fairness_active or self.starter_schemas

    def arbitration_snapshot(self, selected_reason: str) -> tuple[dict[str, str], ...]:
        """Explain deterministic advisor priority without inventing prose."""

        order = []
        if self.constraint_first_role_replay:
            order.append("constraint-first-relation-repair")
        if self.successful_role_replay:
            order.append("successful-role-replay")
        if self.local_relation_solver and not self.constraint_first_role_replay:
            order.append("local-relation-repair")
        if self.relational_scheme_binding:
            order.append("relational-scheme-binding")
        if self.parameterized_select_apply_commit:
            order.append("parameterized-select-apply-commit")
        if self.cyclic_sequence_alignment:
            order.append("cyclic-sequence-alignment")
        if self.committed_trajectory_planning:
            order.append("committed-trajectory-planning")
        if self.shape_goal_translation:
            order.append("shape-goal-translation")
        if self.productive_role_reuse:
            order.append("productive-role-reuse")
        if self.parameterized_scheme_variation:
            order.append("parameterized-scheme-variation")
        if self.uses_action_family_schema:
            order.append("hierarchical-action-fairness")
        order.extend(("untried-state-intervention", "known-frontier-navigation"))
        order.append("least-repeated-fallback")
        selected = (
            "constraint-first-relation-repair"
            if "constraint-first-repair-local-relation" in selected_reason
            else "successful-role-replay"
            if "replay-successful-action-role" in selected_reason
            else "relational-scheme-binding"
            if "relational-scheme-binding" in selected_reason
            else "productive-role-reuse"
            if "reuse-productive-action-role" in selected_reason
            else "cyclic-sequence-alignment"
            if "cyclic-sequence-alignment" in selected_reason
            else "committed-trajectory-planning"
            if "committed-trajectory-planning" in selected_reason
            else "shape-goal-translation"
            if "shape-goal-translation" in selected_reason
            else "parameterized-select-apply-commit"
            if "parameterized-select-apply-commit" in selected_reason
            else "local-relation-repair"
            if "repair-local-relation" in selected_reason
            else "parameterized-scheme-variation"
            if "parameterized-scheme-variation" in selected_reason
            else "hierarchical-action-fairness"
            if "hierarchical-action-family" in selected_reason
            else "untried-state-intervention"
            if "untried-current-state" in selected_reason
            else "known-frontier-navigation"
            if "navigate-known-state-graph" in selected_reason
            else "least-repeated-fallback"
            if "least-repeated-exhausted-state" in selected_reason
            else None
        )
        if selected is None or selected not in order:
            return tuple(
                {"advisor": advisor, "status": "not_evaluated"} for advisor in order
            )
        selected_index = order.index(selected)
        return tuple(
            {
                "advisor": advisor,
                "status": (
                    "selected"
                    if index == selected_index
                    else "no_applicable_action"
                    if index < selected_index
                    else "preempted_by_selected_advisor"
                ),
            }
            for index, advisor in enumerate(order)
        )

    def observe(self, observation: Observation, scene: Scene) -> StateKey:
        """Record the outcome of the last issued intervention exactly once."""

        state = self._state_key(observation, scene)
        self._record_response(observation)
        if self.current_level is None:
            self.current_level = observation.levels_completed
        elif observation.levels_completed > self.current_level:
            if (
                self.successful_role_replay
                or self.parameterized_scheme_variation
                or self.relational_scheme_binding
            ) and self.episode_roles:
                self.successful_program = tuple(self.episode_roles)
                self.program_cursor = 0
                if self.parameterized_scheme_variation:
                    self._learn_parameterized_variations(self.successful_program)
                if self.relational_scheme_binding:
                    self._learn_relational_variations(
                        tuple(self.productive_groundings or self.episode_groundings)
                    )
            self.episode_roles.clear()
            self.episode_groundings.clear()
            self.productive_groundings.clear()
            self.relational_cursors = {
                scheme_id: 0 for scheme_id in self.relational_schemes
            }
            self.relational_last.clear()
            self.relational_level_trials = 0
            self.productive_reuse_level_trials = 0
            self.cyclic_alignment_level_trials = 0
            self.grounded_cyclic_transports.clear()
            self.select_apply_program = ()
            self.select_apply_cursor = 0
            self.select_apply_attempted = False
            self.select_apply_level_trials = 0
            self.nested_target_plan_active = False
            self.nested_source_plan_active = False
            self.connector_relocation_plan_active = False
            self.select_apply_diagnostic = "not-attempted"
            self._reset_shape_translation_level()
            self._reset_committed_trajectory_level()
            self.level_interventions = 0
            self.current_level = observation.levels_completed
            self.level_failures = 0
        elif observation.state == "GAME_OVER":
            self.episode_roles.clear()
            self.episode_groundings.clear()
            self.productive_groundings.clear()
            self.program_cursor = 0
            self.variation_cursors = {
                scheme_id: 0 for scheme_id in self.parameterized_schemes
            }
            self.relational_cursors = {
                scheme_id: 0 for scheme_id in self.relational_schemes
            }
            self.relational_last.clear()
            self.relational_level_trials = 0
            self.productive_reuse_level_trials = 0
            self.cyclic_alignment_level_trials = 0
            self.grounded_cyclic_transports.clear()
            self.select_apply_program = ()
            self.select_apply_cursor = 0
            self._reset_shape_translation_level()
            self._reset_committed_trajectory_level(retain_accommodation=True)
            if not self.cross_retry_maturity:
                self.level_interventions = 0
            self.level_failures += 1
            if self.click_object_accommodation and self.level_failures == 1:
                self._reorganize_click_ontology()
        if state not in self.state_status:
            if len(self.visit_order) >= self.max_states:
                self._forget_oldest_state()
            self.visit_order.append(state)
        self.state_status[state] = observation.state
        if self.pending is not None:
            source, token = self.pending
            self.edges[(source, token)] = state
            self.pending = None
        self.current_state = state
        return state

    def _record_response(self, observation: Observation) -> None:
        if self.pending_role is None or not self.pending_frame:
            self.pending_grounding = None
            self.pending_relational_scheme = None
            return
        before = self.pending_frame
        after = observation.frame
        self.pending_frame = ()
        role = self.pending_role
        pending_token = self.pending[1] if self.pending is not None else None
        self.pending_role = None
        grounding = self.pending_grounding
        self.pending_grounding = None
        relational_scheme = self.pending_relational_scheme
        self.pending_relational_scheme = None
        self.role_trials[role] += 1
        progressed = (
            self.current_level is not None
            and observation.levels_completed > self.current_level
        )
        if (
            self.committed_trajectory_planning
            and pending_token is not None
            and not pending_token.data
            and pending_token.action_id
            not in {self.reset_action, self.complex_action}
        ):
            self._observe_committed_trajectory(
                before,
                after,
                pending_token.action_id,
                progressed=progressed,
            )
        phase_changed = (
            self.shape_goal_translation
            and pending_token is not None
            and not pending_token.data
            and pending_token.action_id
            not in {self.reset_action, self.complex_action}
            and not progressed
            and self._observe_shape_translation_phase(
                before,
                after,
                pending_token.action_id,
            )
        )
        if self.shape_goal_translation and not phase_changed:
            self._validate_shape_translation_prediction(
                before,
                after,
                progressed=progressed,
            )
        if len(before) != len(after) or not before or not after:
            return
        if any(len(left) != len(right) for left, right in zip(before, after)):
            return
        if (
            self.shape_goal_translation
            and pending_token is not None
            and not pending_token.data
            and pending_token.action_id
            not in {self.reset_action, self.complex_action}
            and not progressed
            and not phase_changed
        ):
            self._observe_shape_goal_translation(
                before,
                after,
                pending_token.action_id,
            )
        height = len(before)
        width = len(before[0]) if before else 0
        margin = 4 if height > 8 and width > 8 else 0
        changed = sum(
            before[y][x] != after[y][x]
            for y in range(margin, height - margin)
            for x in range(margin, width - margin)
        )
        changed_frame = changed >= 4
        if self.cyclic_sequence_alignment and grounding is not None:
            self._observe_cyclic_transition(
                before,
                after,
                grounding.centroid,
                progressed=(
                    self.current_level is not None
                    and observation.levels_completed > self.current_level
                ),
            )
        if changed_frame:
            self.role_responses[role] += 1
            if grounding is not None:
                self.productive_groundings.append(grounding)
            if relational_scheme is not None:
                self.relational_responses[relational_scheme] += 1
        if relational_scheme is not None:
            progressed = (
                self.current_level is not None
                and observation.levels_completed > self.current_level
            )
            scheme = self.relational_schemes.get(relational_scheme)
            application_limit = min(
                self.max_relational_application_steps,
                len(scheme.action_slots) if scheme is not None else 1,
            )
            application_complete = (
                self.relational_application_steps[relational_scheme]
                >= application_limit
            )
            if progressed:
                self.relational_progress[relational_scheme] += 1
                self.relational_application_steps[relational_scheme] = 0
            elif not changed_frame or application_complete:
                self.relational_stagnations[relational_scheme] += 1
                self.relational_application_steps[relational_scheme] = 0

    def _reorganize_click_ontology(self) -> None:
        """Invalidate graph evidence whose action tokens changed meaning."""

        self.attempts.clear()
        self.global_attempts.clear()
        self.family_attempts.clear()
        self.global_family_attempts.clear()
        self.edges.clear()
        self.tokens_by_state.clear()
        self.state_status.clear()
        self.visit_order.clear()
        self.role_trials.clear()
        self.role_responses.clear()
        self.current_state = None
        self.pending = None
        self.pending_frame = ()
        self.pending_role = None
        self.pending_grounding = None
        self.pending_relational_scheme = None

    def _reset_shape_translation_level(self) -> None:
        self.shape_translation_probes.clear()
        self.shape_translation_effects.clear()
        self.shape_translation_effect_evidence.clear()
        self.shape_translation_invalid_actions.clear()
        self.shape_goal_mover_signature = None
        self.shape_goal_target_signature = None
        self.shape_translation_level_trials = 0
        self.shape_translation_application_trials = 0
        self.shape_translation_diagnostic = "not-attempted"
        self.shape_goal_latent_mover_origin = None
        self.shape_goal_latent_target_origin = None
        self.shape_translation_occluded_action = None
        self.shape_translation_occluded_steps = 0
        self.shape_translation_pending_prediction = None
        self.shape_translation_phase = None
        self.shape_translation_phase_models.clear()
        self.shape_translation_phase_transitions.clear()
        self.shape_translation_phase_transition_count = 0
        self.shape_translation_phase_blocked = False

    def _reset_committed_trajectory_level(
        self,
        *,
        retain_accommodation: bool = False,
    ) -> None:
        """Reset episode state, optionally retaining same-level causal learning."""

        self.trajectory_stage = "not-attempted"
        self.trajectory_mover_signature = None
        self.trajectory_receptacle_signature = None
        self.trajectory_mover_color = None
        self.trajectory_target_color = None
        self.trajectory_origin = None
        self.trajectory_current_anchor = None
        self.trajectory_latent_anchor = None
        self.trajectory_target_anchor = None
        if not retain_accommodation:
            self.trajectory_probes.clear()
            self.trajectory_no_effect_actions.clear()
            self.trajectory_effects.clear()
            self.trajectory_effect_evidence.clear()
            self.trajectory_invalid_actions.clear()
        self.trajectory_contextual_blocks.clear()
        self.trajectory_gate_failures.clear()
        self.trajectory_gate_cooldowns.clear()
        self.trajectory_gate_refresh_actions.clear()
        self.trajectory_topology_nodes.clear()
        self.trajectory_uncertain_nodes.clear()
        self.trajectory_topology_support_color = None
        self.trajectory_restore_tried.clear()
        self.trajectory_macro_action = None
        self.trajectory_macro_effect = None
        if not retain_accommodation:
            self.trajectory_previous_failed_macro_action = None
        self.trajectory_active_path.clear()
        self.trajectory_enacted_path.clear()
        self.trajectory_endpoint_macros.clear()
        self.trajectory_commit_action = None
        self.trajectory_commit_trials = 0
        self.trajectory_committed_macro = ()
        self.trajectory_replay_started = False
        self.trajectory_replay_anchor = None
        self.trajectory_replay_cursor = 0
        self.trajectory_replay_validations = 0
        self.trajectory_replay_misses = 0
        self.trajectory_navigation_action = None
        self.trajectory_settle_steps = 0
        self.trajectory_plan_steps = 0
        self.trajectory_level_trials = 0
        self.trajectory_pending = None
        self.trajectory_causal_states.clear()
        self.trajectory_causal_edges.clear()
        self.trajectory_boundary_transitions.clear()
        self.trajectory_boundary_nuisance_evidenced = False
        self.trajectory_diagnostic = "not-attempted"
        self.trajectory_disabled = False

    @staticmethod
    def _trajectory_signature(
        item: _FrameObject,
    ) -> tuple[int, int, int, tuple[tuple[int, int], ...]]:
        return (
            item.area,
            item.bbox[2] - item.bbox[0] + 1,
            item.bbox[3] - item.bbox[1] + 1,
            item.shape,
        )

    @classmethod
    def _trajectory_grounding(
        cls,
        frame: tuple[tuple[int, ...], ...],
    ) -> _TrajectoryGrounding | None:
        """Ground a hosted near-filled square and one compatible receptacle."""

        if not frame or not frame[0]:
            return None
        height = len(frame)
        width = len(frame[0])
        objects = cls._frame_objects(frame)
        interior = tuple(
            item
            for item in objects
            if 0 < item.bbox[0]
            and 0 < item.bbox[1]
            and item.bbox[2] < width - 1
            and item.bbox[3] < height - 1
        )
        markers = tuple(item for item in interior if item.area <= 2)

        def hosted_markers(host: _FrameObject) -> tuple[_FrameObject, ...]:
            return tuple(
                marker
                for marker in markers
                if marker is not host
                and host.bbox[0] < marker.centroid[0] < host.bbox[2]
                and host.bbox[1] < marker.centroid[1] < host.bbox[3]
            )

        movers = []
        for item in interior:
            item_width = item.bbox[2] - item.bbox[0] + 1
            item_height = item.bbox[3] - item.bbox[1] + 1
            if (
                item_width == item_height
                and 3 <= item_width <= 9
                and item.area == item_width * item_height - 1
                and len(hosted_markers(item)) == 1
            ):
                movers.append(item)
        grounded = []
        for mover in movers:
            mover_width = mover.bbox[2] - mover.bbox[0] + 1
            mover_height = mover.bbox[3] - mover.bbox[1] + 1
            receptacles = []
            for item in interior:
                item_width = item.bbox[2] - item.bbox[0] + 1
                item_height = item.bbox[3] - item.bbox[1] + 1
                if (
                    item is not mover
                    and item_width == mover_width + 2
                    and item_height == mover_height + 2
                    and 2 * max(item_width, item_height) <= item.area
                    < item_width * item_height - 1
                    and hosted_markers(item)
                ):
                    receptacles.append(item)
            if len(receptacles) != 1:
                continue
            target = receptacles[0]
            grounded.append(
                _TrajectoryGrounding(
                    mover_signature=cls._trajectory_signature(mover),
                    mover_anchor=mover.bbox[:2],
                    mover_color=mover.color,
                    target_anchor=(
                        target.bbox[0] + (target.bbox[2] - target.bbox[0] + 1 - mover_width) // 2,
                        target.bbox[1] + (target.bbox[3] - target.bbox[1] + 1 - mover_height) // 2,
                    ),
                    target_color=target.color,
                    receptacle_signature=cls._trajectory_signature(target),
                )
            )
        return grounded[0] if len(grounded) == 1 else None

    @classmethod
    def _trajectory_mover_anchors(
        cls,
        frame: tuple[tuple[int, ...], ...],
        signature: tuple[int, int, int, tuple[tuple[int, int], ...]],
    ) -> tuple[tuple[int, int], ...]:
        return tuple(
            sorted(
                item.bbox[:2]
                for item in cls._frame_objects(frame)
                if cls._trajectory_signature(item) == signature
            )
        )

    @classmethod
    def _trajectory_phase_signature(
        cls,
        frame: tuple[tuple[int, ...], ...],
        mover_color: int,
        target_color: int,
    ) -> tuple[
        tuple[
            int,
            int,
            int,
            tuple[tuple[int, int], ...],
            bool,
            bool,
        ],
        ...,
    ]:
        if not frame or not frame[0]:
            return ()
        height = len(frame)
        width = len(frame[0])
        return tuple(
            sorted(
                (
                    item.area,
                    item.bbox[2] - item.bbox[0] + 1,
                    item.bbox[3] - item.bbox[1] + 1,
                    item.shape,
                    item.color == mover_color,
                    item.color == target_color,
                )
                for item in cls._frame_objects(frame)
                if item.area <= 16
                and 0 < item.bbox[0]
                and 0 < item.bbox[1]
                and item.bbox[2] < width - 1
                and item.bbox[3] < height - 1
            )
        )

    @staticmethod
    def _trajectory_boundary_signature(
        frame: tuple[tuple[int, ...], ...],
    ) -> tuple[int, ...]:
        if not frame or not frame[0]:
            return ()
        height = len(frame)
        width = len(frame[0])
        sides = (
            tuple(frame[0]),
            tuple(frame[height - 1]),
            tuple(frame[y][0] for y in range(height)),
            tuple(frame[y][width - 1] for y in range(height)),
        )
        return tuple(
            len(side) - max(Counter(side).values(), default=0) for side in sides
        )

    def _observe_trajectory_boundary(
        self,
        before: tuple[tuple[int, ...], ...],
        after: tuple[tuple[int, ...], ...],
        action_id: int,
    ) -> None:
        before_signature = self._trajectory_boundary_signature(before)
        after_signature = self._trajectory_boundary_signature(after)
        if before_signature == after_signature:
            return
        if len(self.trajectory_boundary_transitions) < 8:
            self.trajectory_boundary_transitions.append(
                (action_id, before_signature, after_signature)
            )
        transitions = self.trajectory_boundary_transitions
        if len(transitions) < 4 or len({item[0] for item in transitions}) < 3:
            return
        deltas = tuple(
            tuple(right - left for left, right in zip(before_item, after_item))
            for _action, before_item, after_item in transitions
        )
        monotone = all(
            all(value >= 0 for value in axis_values)
            or all(value <= 0 for value in axis_values)
            for axis_values in zip(*deltas)
        )
        if monotone and any(any(value != 0 for value in delta) for delta in deltas):
            self.trajectory_boundary_nuisance_evidenced = True

    def _trajectory_causal_key(
        self,
        anchor: tuple[int, int],
    ) -> tuple[
        tuple[int, int],
        tuple[int, int],
        tuple[int, tuple[int, int], int] | None,
        int,
    ]:
        assert self.trajectory_origin is not None
        assert self.trajectory_target_anchor is not None
        macro = (
            (
                self.trajectory_macro_action,
                self.trajectory_macro_effect,
                len(self.trajectory_committed_macro),
            )
            if self.trajectory_macro_action is not None
            and self.trajectory_macro_effect is not None
            and self.trajectory_committed_macro
            else None
        )
        return (
            (
                anchor[0] - self.trajectory_origin[0],
                anchor[1] - self.trajectory_origin[1],
            ),
            (
                self.trajectory_target_anchor[0] - anchor[0],
                self.trajectory_target_anchor[1] - anchor[1],
            ),
            macro,
            self.trajectory_replay_cursor,
        )

    def _record_trajectory_effect(
        self,
        action_id: int,
        displacement: tuple[int, int],
    ) -> bool:
        previous = self.trajectory_effects.get(action_id)
        if previous is not None and previous != displacement:
            self.trajectory_effects.pop(action_id, None)
            self.trajectory_invalid_actions.add(action_id)
            self.trajectory_disabled = True
            self.trajectory_diagnostic = "inconsistent-translation"
            return False
        self.trajectory_effects[action_id] = displacement
        self.trajectory_effect_evidence[action_id] += 1
        self.trajectory_no_effect_actions.discard(action_id)
        return True

    def _trajectory_axes_grounded(self) -> bool:
        effects = set(self.trajectory_effects.values())
        return (
            any(dx > 0 and dy == 0 for dx, dy in effects)
            and any(dx < 0 and dy == 0 for dx, dy in effects)
            and any(dy > 0 and dx == 0 for dx, dy in effects)
            and any(dy < 0 and dx == 0 for dx, dy in effects)
        )

    def _trajectory_structural_endpoint(
        self,
        frame: tuple[tuple[int, ...], ...],
        anchor: tuple[int, int],
        effect: tuple[int, int],
    ) -> bool:
        """Recognize that the next translated footprint leaves rendered slots."""

        signature = self.trajectory_mover_signature
        if signature is None or not frame or not frame[0]:
            return False
        predicted = (
            anchor[0] + effect[0],
            anchor[1] + effect[1],
        )
        height = len(frame)
        width = len(frame[0])
        background = Counter(
            value for row in frame for value in row
        ).most_common(1)[0][0]
        footprint = tuple(
            (predicted[0] + local_x, predicted[1] + local_y)
            for local_x, local_y in signature[3]
        )
        if any(not (0 <= x < width and 0 <= y < height) for x, y in footprint):
            return True
        return all(frame[y][x] == background for x, y in footprint)

    def _trajectory_topology(
        self,
        frame: tuple[tuple[int, ...], ...],
    ) -> tuple[
        frozenset[tuple[int, int]],
        frozenset[tuple[int, int]],
        int | None,
    ]:
        """Infer a bounded movement lattice over rendered substrate."""

        origin = self.trajectory_origin
        target = self.trajectory_target_anchor
        signature = self.trajectory_mover_signature
        if (
            origin is None
            or target is None
            or signature is None
            or not frame
            or not frame[0]
        ):
            return frozenset(), frozenset(), None
        x_steps = sorted(
            {
                abs(effect[0])
                for effect in self.trajectory_effects.values()
                if effect[0] and not effect[1]
            }
        )
        y_steps = sorted(
            {
                abs(effect[1])
                for effect in self.trajectory_effects.values()
                if effect[1] and not effect[0]
            }
        )
        if len(x_steps) != 1 or len(y_steps) != 1:
            return frozenset(), frozenset(), None
        background = Counter(
            value for row in frame for value in row
        ).most_common(1)[0][0]
        height = len(frame)
        width = len(frame[0])
        interior = tuple(
            item
            for item in self._frame_objects(frame)
            if item.color != background
            and 0 < item.bbox[0]
            and 0 < item.bbox[1]
            and item.bbox[2] < width - 1
            and item.bbox[3] < height - 1
        )
        if not interior:
            return frozenset(), frozenset(), None
        support = max(
            interior,
            key=lambda item: (item.area, -item.color),
        )
        mover_width = signature[1]
        mover_height = signature[2]
        center_dx = mover_width // 2
        center_dy = mover_height // 2
        x_step = x_steps[0]
        y_step = y_steps[0]
        xs = tuple(
            x
            for offset in range(-16, 17)
            for x in (origin[0] + offset * x_step,)
            if (
                0 <= x
                and x + mover_width <= width
                and support.bbox[0] <= x
                and x + mover_width - 1 <= support.bbox[2]
            )
        )
        ys = tuple(
            y
            for offset in range(-16, 17)
            for y in (origin[1] + offset * y_step,)
            if (
                0 <= y
                and y + mover_height <= height
                and support.bbox[1] <= y
                and y + mover_height - 1 <= support.bbox[3]
            )
        )
        candidates = sorted(
            ((x, y) for y in ys for x in xs),
            key=lambda anchor: (
                abs(anchor[0] - origin[0])
                + abs(anchor[1] - origin[1]),
                anchor,
            ),
        )[:128]
        admitted: set[tuple[int, int]] = set()
        uncertain: set[tuple[int, int]] = set()
        grounded_colors = {
            support.color,
            self.trajectory_mover_color,
            self.trajectory_target_color,
        }
        current = self.trajectory_current_anchor
        for anchor in candidates:
            center_color = frame[anchor[1] + center_dy][
                anchor[0] + center_dx
            ]
            if (
                center_color == background
                and anchor not in {origin, current, target}
            ):
                continue
            admitted.add(anchor)
            if (
                center_color not in grounded_colors
                and center_color != background
                and anchor not in {origin, current, target}
            ):
                uncertain.add(anchor)
        admitted.update(
            anchor
            for anchor in (origin, current, target)
            if anchor is not None
        )
        return frozenset(admitted), frozenset(uncertain), support.color

    def _disable_trajectory(self, diagnostic: str) -> None:
        if (
            diagnostic
            in {
                "no-causal-plan",
                "replay-diverged",
                "replay-never-started",
                "trajectory-plan-cap-reached",
            }
            and self.trajectory_macro_action is not None
        ):
            self.trajectory_previous_failed_macro_action = (
                self.trajectory_macro_action
            )
        self.trajectory_disabled = True
        self.trajectory_pending = None
        self.trajectory_diagnostic = diagnostic

    def _record_trajectory_enacted(
        self,
        anchor: tuple[int, int],
    ) -> bool:
        """Retain the full successful operation history, including inverses."""

        if len(self.trajectory_enacted_path) >= 32:
            self._disable_trajectory("enacted-trajectory-cap-reached")
            return False
        self.trajectory_enacted_path.append(anchor)
        return True

    def _advance_trajectory_gate_cooldowns(self) -> None:
        """Advance uncertain-gate experiments only after actual movement."""

        for edge, remaining in tuple(self.trajectory_gate_cooldowns.items()):
            if remaining <= 1:
                self.trajectory_gate_cooldowns.pop(edge, None)
                self.trajectory_contextual_blocks.pop(edge, None)
            else:
                self.trajectory_gate_cooldowns[edge] = remaining - 1

    def _trajectory_block_threshold(self) -> int:
        """Let a bounded committed replay clear before declaring a hard block."""

        return max(2, len(self.trajectory_committed_macro) - 1)

    def _trajectory_plan_cap(self) -> int:
        """Pay bounded joint-state detours from evidenced operation length."""

        return min(32, 20 + len(self.trajectory_committed_macro))

    def _observe_committed_trajectory(
        self,
        before: tuple[tuple[int, ...], ...],
        after: tuple[tuple[int, ...], ...],
        action_id: int,
        *,
        progressed: bool,
    ) -> None:
        pending = self.trajectory_pending
        self.trajectory_pending = None
        if pending is None or self.trajectory_disabled:
            return
        self._observe_trajectory_boundary(before, after, action_id)
        kind, expected_action, before_anchor, expected_anchor = pending
        if expected_action != action_id:
            self._disable_trajectory("pending-action-mismatch")
            return
        if progressed:
            self.trajectory_diagnostic = "level-advanced"
            return
        signature = self.trajectory_mover_signature
        if signature is None:
            self._disable_trajectory("missing-mover-signature")
            return
        anchors = self._trajectory_mover_anchors(after, signature)
        if expected_anchor is not None and expected_anchor in anchors:
            after_anchor = expected_anchor
        elif kind == "settle":
            after_anchor = before_anchor
        elif kind == "navigate" and before_anchor in anchors:
            after_anchor = before_anchor
        elif kind == "commit" and self.trajectory_origin in anchors:
            after_anchor = self.trajectory_origin
        elif len(anchors) == 1:
            after_anchor = anchors[0]
        else:
            self._disable_trajectory("ambiguous-mover-identity")
            return
        displacement = (
            after_anchor[0] - before_anchor[0],
            after_anchor[1] - before_anchor[1],
        )
        latent_before = (
            self.trajectory_latent_anchor
            if kind == "navigate" and self.trajectory_latent_anchor is not None
            else before_anchor
        )
        before_key = self._trajectory_causal_key(latent_before)

        if kind == "probe":
            if displacement == (0, 0):
                self.trajectory_no_effect_actions.add(action_id)
                self.trajectory_stage = "probe"
                self.trajectory_diagnostic = "probe-no-translation"
            elif self._record_trajectory_effect(action_id, displacement):
                if not self._record_trajectory_enacted(after_anchor):
                    return
                self.trajectory_current_anchor = after_anchor
                self.trajectory_restore_tried.clear()
                self.trajectory_stage = "restore"
                self.trajectory_diagnostic = "translation-probed"
        elif kind == "restore":
            if displacement != (0, 0):
                if not self._record_trajectory_effect(action_id, displacement):
                    return
                if not self._record_trajectory_enacted(after_anchor):
                    return
            if after_anchor == self.trajectory_origin:
                self.trajectory_current_anchor = after_anchor
                self.trajectory_restore_tried.clear()
                self.trajectory_stage = (
                    "macro" if self._trajectory_axes_grounded() else "probe"
                )
                self.trajectory_diagnostic = "origin-restored"
            else:
                self.trajectory_current_anchor = after_anchor
                self.trajectory_stage = "restore"
                self.trajectory_diagnostic = "restoring-origin"
        elif kind == "macro":
            if displacement == self.trajectory_macro_effect:
                if len(self.trajectory_active_path) >= 16:
                    self._disable_trajectory("trajectory-cap-reached")
                    return
                self._record_trajectory_effect(action_id, displacement)
                if not self._record_trajectory_enacted(after_anchor):
                    return
                self.trajectory_active_path.append(after_anchor)
                self.trajectory_current_anchor = after_anchor
                self.trajectory_stage = "macro"
                self.trajectory_diagnostic = "extending-endpoint-macro"
            elif displacement == (0, 0) and len(self.trajectory_active_path) >= 2:
                macro = tuple(self.trajectory_active_path)
                if len(self.trajectory_endpoint_macros) >= 4:
                    self._disable_trajectory("endpoint-cap-reached")
                    return
                self.trajectory_endpoint_macros.append(macro)
                self.trajectory_current_anchor = after_anchor
                self.trajectory_stage = "commit"
                self.trajectory_diagnostic = "blocked-endpoint"
            else:
                self._disable_trajectory("macro-effect-falsified")
                return
        elif kind == "commit":
            if (
                after_anchor != self.trajectory_origin
                or len(self.trajectory_active_path) < 2
                or self.trajectory_mover_color is None
                or self.trajectory_target_color is None
            ):
                self._disable_trajectory("commit-dependencies-failed")
                return
            before_phase = self._trajectory_phase_signature(
                before,
                self.trajectory_mover_color,
                self.trajectory_target_color,
            )
            after_phase = self._trajectory_phase_signature(
                after,
                self.trajectory_mover_color,
                self.trajectory_target_color,
            )
            if before_phase == after_phase:
                self.trajectory_stage = "commit"
                self.trajectory_diagnostic = "commit-no-phase-change"
                return
            self.trajectory_commit_action = action_id
            self.trajectory_committed_macro = tuple(
                self.trajectory_enacted_path
            )
            self.trajectory_current_anchor = after_anchor
            self.trajectory_latent_anchor = after_anchor
            self.trajectory_replay_started = False
            self.trajectory_replay_anchor = None
            self.trajectory_replay_cursor = 0
            self.trajectory_stage = "navigate"
            self.trajectory_diagnostic = "trajectory-committed"
        elif kind == "navigate":
            if displacement == (0, 0):
                blocked_edge = (latent_before, action_id)
                self.trajectory_contextual_blocks[blocked_edge] += 1
                if expected_anchor in self.trajectory_uncertain_nodes:
                    self.trajectory_gate_failures[blocked_edge] += 1
                    self.trajectory_gate_cooldowns[blocked_edge] = min(
                        4,
                        self.trajectory_gate_failures[blocked_edge],
                    )
                self.trajectory_current_anchor = after_anchor
                self.trajectory_stage = "navigate"
                self.trajectory_diagnostic = "planned-edge-blocked"
            elif displacement != self.trajectory_effects.get(action_id):
                self._disable_trajectory("planned-effect-falsified")
                return
            else:
                self._advance_trajectory_gate_cooldowns()
                self.trajectory_current_anchor = after_anchor
                effect = self.trajectory_effects[action_id]
                assert self.trajectory_latent_anchor is not None
                self.trajectory_latent_anchor = (
                    self.trajectory_latent_anchor[0] + effect[0],
                    self.trajectory_latent_anchor[1] + effect[1],
                )
            if displacement != (0, 0) and self.trajectory_replay_cursor < len(
                self.trajectory_committed_macro
            ):
                other_anchors = tuple(
                    anchor for anchor in anchors if anchor != after_anchor
                )
                if not self.trajectory_replay_started:
                    if self.trajectory_origin in other_anchors:
                        self.trajectory_replay_started = True
                        self.trajectory_replay_anchor = self.trajectory_origin
                        self.trajectory_replay_misses = 0
                    elif (
                        self.trajectory_committed_macro
                        and self.trajectory_committed_macro[0]
                        in other_anchors
                    ):
                        first_replay_anchor = (
                            self.trajectory_committed_macro[0]
                        )
                        self.trajectory_replay_started = True
                        self.trajectory_replay_anchor = first_replay_anchor
                        self.trajectory_replay_cursor = 1
                        self.trajectory_replay_validations += 1
                        self.trajectory_replay_misses = 0
                    else:
                        self.trajectory_replay_misses += 1
                        if self.trajectory_replay_misses >= 4:
                            self._disable_trajectory("replay-never-started")
                            return
                else:
                    replay_anchor = self.trajectory_committed_macro[
                        self.trajectory_replay_cursor
                    ]
                    if replay_anchor in other_anchors:
                        self.trajectory_replay_validations += 1
                        self.trajectory_replay_cursor += 1
                        self.trajectory_replay_anchor = replay_anchor
                        self.trajectory_replay_misses = 0
                    elif self.trajectory_replay_anchor in other_anchors:
                        self.trajectory_diagnostic = "replay-paused"
                    else:
                        self.trajectory_replay_misses += 1
                        if self.trajectory_replay_misses >= 2:
                            self._disable_trajectory("replay-diverged")
                            return
            self.trajectory_stage = "navigate"
            if displacement != (0, 0):
                self.trajectory_diagnostic = (
                    "replay-validated"
                    if self.trajectory_replay_validations >= 2
                    else "validating-replay"
                )
        elif kind == "settle":
            if displacement not in {
                (0, 0),
                self.trajectory_effects.get(action_id),
            }:
                self._disable_trajectory("settling-effect-falsified")
                return
            self.trajectory_current_anchor = after_anchor
            self.trajectory_stage = "navigate"
            self.trajectory_diagnostic = "equilibrating-committed-replay"

        if self.trajectory_current_anchor is None:
            return
        causal_anchor = (
            self.trajectory_latent_anchor
            if kind == "navigate" and self.trajectory_latent_anchor is not None
            else self.trajectory_current_anchor
        )
        after_key = self._trajectory_causal_key(causal_anchor)
        if len(self.trajectory_causal_states) < 64:
            self.trajectory_causal_states.update((before_key, after_key))
        if len(self.trajectory_causal_edges) < 64:
            self.trajectory_causal_edges.add((before_key, action_id, after_key))

    @classmethod
    def _relational_phase_signature(
        cls,
        frame: tuple[tuple[int, ...], ...],
    ) -> PhaseSignature | None:
        """Describe rare markers by their normalized relation to major hosts."""

        objects = cls._frame_objects(frame)
        major = tuple(item for item in objects if 16 <= item.area <= 512)
        markers = tuple(item for item in objects if item.area <= 2)
        hosted: dict[
            tuple[int, int, tuple[tuple[int, int], ...]],
            list[tuple[int, int, int]],
        ] = {}
        for marker in markers:
            hosts = tuple(
                host
                for host in major
                if host.bbox[0] < marker.centroid[0] < host.bbox[2]
                and host.bbox[1] < marker.centroid[1] < host.bbox[3]
            )
            if len(hosts) > 1:
                return None
            if not hosts:
                continue
            host = hosts[0]
            host_key = (host.color, host.area, host.shape)
            hosted.setdefault(host_key, []).append(
                (
                    marker.color,
                    marker.centroid[0] - host.bbox[0],
                    marker.centroid[1] - host.bbox[1],
                )
            )
        return tuple(
            sorted(
                (
                    color,
                    area,
                    shape,
                    tuple(sorted(marker_relations)),
                )
                for (color, area, shape), marker_relations in hosted.items()
            )
        )

    def _store_shape_translation_phase(self) -> None:
        if self.shape_translation_phase is None:
            return
        self.shape_translation_phase_models[self.shape_translation_phase] = (
            self.shape_translation_probes,
            self.shape_translation_effects,
            self.shape_translation_effect_evidence,
            self.shape_translation_invalid_actions,
        )

    def _load_shape_translation_phase(
        self,
        phase: PhaseSignature,
    ) -> None:
        self._store_shape_translation_phase()
        model = self.shape_translation_phase_models.get(phase)
        if model is None:
            model = (set(), {}, Counter(), set())
            self.shape_translation_phase_models[phase] = model
        (
            self.shape_translation_probes,
            self.shape_translation_effects,
            self.shape_translation_effect_evidence,
            self.shape_translation_invalid_actions,
        ) = model
        self.shape_translation_phase = phase

    def _ensure_shape_translation_phase(
        self,
        frame: tuple[tuple[int, ...], ...],
    ) -> None:
        if not self.relational_phase_translation or self.shape_translation_phase_blocked:
            return
        phase = self._relational_phase_signature(frame)
        if phase is None:
            if self.shape_translation_occluded_action is not None:
                self.shape_translation_diagnostic = (
                    "phase-unavailable-during-predicted-occlusion"
                )
                return
            self.shape_translation_phase_blocked = True
            self.shape_translation_diagnostic = "ambiguous-marker-host"
            return
        if self.shape_translation_phase is None:
            self._load_shape_translation_phase(phase)

    def _observe_shape_translation_phase(
        self,
        before: tuple[tuple[int, ...], ...],
        after: tuple[tuple[int, ...], ...],
        action_id: int,
    ) -> bool:
        """Quarantine action semantics after an evidenced marker-host change."""

        if not self.relational_phase_translation or self.shape_translation_phase_blocked:
            return False
        if self.shape_translation_occluded_action is not None:
            return False
        before_phase = self._relational_phase_signature(before)
        after_phase = self._relational_phase_signature(after)
        if (
            before_phase is None
            or after_phase is None
            or not before_phase
            or not after_phase
            or before_phase == after_phase
        ):
            return False
        if self.shape_translation_phase is None:
            self._load_shape_translation_phase(before_phase)
        if self.shape_translation_phase != before_phase:
            self.shape_translation_phase_blocked = True
            self.shape_translation_diagnostic = "untracked-phase-change"
            return False

        before_pair = self._unique_shape_pair(before)
        after_pair = self._unique_shape_pair(after)
        if before_pair is None or after_pair is None:
            return False
        before_by_signature = {
            self._shape_signature(item): item for item in before_pair
        }
        after_by_signature = {
            self._shape_signature(item): item for item in after_pair
        }
        if set(before_by_signature) != set(after_by_signature):
            return False
        if any(
            before_by_signature[signature].bbox
            != after_by_signature[signature].bbox
            for signature in before_by_signature
        ):
            return False
        transition = (before_phase, action_id)
        previous = self.shape_translation_phase_transitions.get(transition)
        if previous not in {None, after_phase}:
            self.shape_translation_phase_blocked = True
            self.shape_translation_diagnostic = "inconsistent-phase-transition"
            return False
        if (
            after_phase not in self.shape_translation_phase_models
            and len(self.shape_translation_phase_models) >= 3
        ):
            self.shape_translation_phase_blocked = True
            self.shape_translation_diagnostic = "phase-cap-reached"
            return False
        if self.shape_translation_phase_transition_count >= 4:
            self.shape_translation_phase_blocked = True
            self.shape_translation_diagnostic = "phase-transition-cap-reached"
            return False
        self.shape_translation_phase_transitions[transition] = after_phase
        self.shape_translation_phase_transition_count += 1
        self._load_shape_translation_phase(after_phase)
        self.shape_translation_pending_prediction = None
        self.shape_translation_occluded_action = None
        self.shape_translation_occluded_steps = 0
        self.shape_translation_diagnostic = "relational-phase-transition"
        return True

    @staticmethod
    def _shape_signature(
        item: _FrameObject,
    ) -> tuple[int, int, tuple[tuple[int, int], ...]]:
        return item.color, item.area, item.shape

    @classmethod
    def _interior_shape_objects(
        cls,
        frame: tuple[tuple[int, ...], ...],
    ) -> tuple[_FrameObject, ...]:
        if not frame or not frame[0]:
            return ()
        height = len(frame)
        width = len(frame[0])
        items = tuple(
            item
            for item in cls._frame_objects(frame)
            if 4 <= item.area <= 512
            and 0 < item.bbox[0]
            and 0 < item.bbox[1]
            and item.bbox[2] < width - 1
            and item.bbox[3] < height - 1
            and item.bbox[2] - item.bbox[0] + 1 <= width // 2
            and item.bbox[3] - item.bbox[1] + 1 <= height // 2
        )
        return items if len(items) <= 64 else ()

    @classmethod
    def _unique_shape_pair(
        cls,
        frame: tuple[tuple[int, ...], ...],
    ) -> tuple[_FrameObject, _FrameObject] | None:
        groups: dict[
            tuple[int, tuple[tuple[int, int], ...]],
            list[_FrameObject],
        ] = {}
        for item in cls._interior_shape_objects(frame):
            groups.setdefault((item.area, item.shape), []).append(item)
        pairs = tuple(
            tuple(items)
            for items in groups.values()
            if len(items) == 2 and len({item.color for item in items}) == 2
        )
        if len(pairs) != 1:
            return None
        return pairs[0][0], pairs[0][1]

    def _validate_shape_translation_prediction(
        self,
        before: tuple[tuple[int, ...], ...],
        after: tuple[tuple[int, ...], ...],
        *,
        progressed: bool,
    ) -> None:
        prediction = self.shape_translation_pending_prediction
        self.shape_translation_pending_prediction = None
        if prediction is None or progressed:
            return
        (
            action_id,
            mover_signature,
            target_signature,
            mover_centroid,
            target_centroid,
            effect,
        ) = prediction
        objects = self._interior_shape_objects(after)
        movers = tuple(
            item
            for item in objects
            if self._shape_signature(item) == mover_signature
        )
        targets = tuple(
            item
            for item in objects
            if self._shape_signature(item) == target_signature
        )
        expected = (
            mover_centroid[0] + effect[0],
            mover_centroid[1] + effect[1],
        )
        if (
            len(movers) == 1
            and len(targets) == 1
            and movers[0].bbox[:2] == expected
            and targets[0].bbox[:2] == target_centroid
        ):
            self.shape_goal_latent_mover_origin = expected
            self.shape_goal_latent_target_origin = target_centroid
            self.shape_translation_occluded_action = None
            self.shape_translation_occluded_steps = 0
            return

        mover_mask = {
            (expected[0] + local_x, expected[1] + local_y)
            for local_x, local_y in mover_signature[2]
        }
        target_mask = {
            (target_centroid[0] + local_x, target_centroid[1] + local_y)
            for local_x, local_y in target_signature[2]
        }
        prior_mover_mask = {
            (mover_centroid[0] + local_x, mover_centroid[1] + local_y)
            for local_x, local_y in mover_signature[2]
        }
        causal_support = prior_mover_mask | mover_mask | target_mask
        local_change = any(
            0 <= y < len(before)
            and 0 <= y < len(after)
            and 0 <= x < len(before[y])
            and 0 <= x < len(after[y])
            and before[y][x] != after[y][x]
            for x, y in causal_support
        )
        predicted_occlusion = bool(mover_mask & target_mask)
        if (
            predicted_occlusion
            and expected != target_centroid
            and local_change
            and self.shape_translation_effect_evidence[action_id] >= 2
            and self.shape_translation_occluded_steps < 4
            and self.shape_translation_occluded_action in {None, action_id}
        ):
            self.shape_goal_latent_mover_origin = expected
            self.shape_goal_latent_target_origin = target_centroid
            self.shape_translation_occluded_action = action_id
            self.shape_translation_occluded_steps += 1
            self.shape_translation_diagnostic = "predicted-occlusion"
            return

        self.shape_translation_effects.pop(action_id, None)
        self.shape_translation_invalid_actions.add(action_id)
        self.shape_translation_occluded_action = None
        self.shape_translation_diagnostic = "translation-prediction-falsified"

    def _observe_shape_goal_translation(
        self,
        before: tuple[tuple[int, ...], ...],
        after: tuple[tuple[int, ...], ...],
        action_id: int,
    ) -> None:
        """Ground one action displacement and one stationary exact-shape goal."""

        before_objects = self._interior_shape_objects(before)
        after_objects = self._interior_shape_objects(after)
        after_by_signature: dict[
            tuple[int, int, tuple[tuple[int, int], ...]],
            list[_FrameObject],
        ] = {}
        for item in after_objects:
            after_by_signature.setdefault(self._shape_signature(item), []).append(
                item
            )

        moved: list[tuple[_FrameObject, tuple[int, int]]] = []
        stationary: list[_FrameObject] = []
        for item in before_objects:
            matches = after_by_signature.get(self._shape_signature(item), [])
            if len(matches) != 1:
                continue
            successor = matches[0]
            displacement = (
                successor.centroid[0] - item.centroid[0],
                successor.centroid[1] - item.centroid[1],
            )
            if displacement == (0, 0):
                stationary.append(item)
            else:
                moved.append((item, displacement))

        grounded = tuple(
            (mover, target, displacement)
            for mover, displacement in moved
            for target in stationary
            if mover.color != target.color
            and mover.area == target.area
            and mover.shape == target.shape
        )
        if len(grounded) != 1:
            return
        mover, target, displacement = grounded[0]
        mover_signature = self._shape_signature(mover)
        target_signature = self._shape_signature(target)
        if self.shape_goal_mover_signature not in {None, mover_signature}:
            self.shape_translation_diagnostic = "inconsistent-mover"
            return
        if self.shape_goal_target_signature not in {None, target_signature}:
            self.shape_translation_diagnostic = "inconsistent-target"
            return
        previous = self.shape_translation_effects.get(action_id)
        if previous is not None and previous != displacement:
            self.shape_translation_effects.pop(action_id, None)
            self.shape_translation_invalid_actions.add(action_id)
            self.shape_translation_diagnostic = "inconsistent-translation"
            return
        if action_id in self.shape_translation_invalid_actions:
            return
        self.shape_goal_mover_signature = mover_signature
        self.shape_goal_target_signature = target_signature
        self.shape_translation_effects[action_id] = displacement
        self.shape_translation_effect_evidence[action_id] += 1
        self.shape_goal_latent_mover_origin = (
            mover.bbox[0] + displacement[0],
            mover.bbox[1] + displacement[1],
        )
        self.shape_goal_latent_target_origin = target.bbox[:2]
        self.shape_translation_occluded_action = None
        self.shape_translation_occluded_steps = 0
        self.shape_translation_diagnostic = "translation-grounded"

    def _select_shape_goal_translation(
        self,
        observation: Observation,
        tokens: tuple[ActionToken, ...],
    ) -> ActionToken | None:
        """Probe, then compose only translations that approach an exact shape."""

        if (
            not self.shape_goal_translation
        ):
            return None
        self._ensure_shape_translation_phase(observation.frame)
        if self.shape_translation_phase_blocked:
            return None
        if self.shape_translation_application_trials >= 32:
            self.shape_translation_diagnostic = "application-cap-reached"
            return None
        plain_tokens = tuple(
            token
            for token in tokens
            if not token.data
            and token.action_id not in {self.reset_action, self.complex_action}
        )
        if not plain_tokens:
            return None

        if (
            self.shape_goal_mover_signature is not None
            and self.shape_goal_target_signature is not None
        ):
            objects = self._interior_shape_objects(observation.frame)
            movers = tuple(
                item
                for item in objects
                if self._shape_signature(item)
                == self.shape_goal_mover_signature
            )
            targets = tuple(
                item
                for item in objects
                if self._shape_signature(item)
                == self.shape_goal_target_signature
            )
            if len(movers) == 1 and len(targets) == 1:
                mover_origin = movers[0].bbox[:2]
                target_origin = targets[0].bbox[:2]
                self.shape_goal_latent_mover_origin = mover_origin
                self.shape_goal_latent_target_origin = target_origin
            elif (
                self.shape_translation_occluded_action is not None
                and self.shape_goal_latent_mover_origin is not None
                and self.shape_goal_latent_target_origin is not None
            ):
                mover_origin = self.shape_goal_latent_mover_origin
                target_origin = self.shape_goal_latent_target_origin
            else:
                self.shape_translation_diagnostic = "grounding-not-visible"
                return None
            delta = (
                target_origin[0] - mover_origin[0],
                target_origin[1] - mover_origin[1],
            )
            distance = abs(delta[0]) + abs(delta[1])
            represented = set(plain_tokens)
            productive = []
            for action_id, effect in self.shape_translation_effects.items():
                token = ActionToken(action_id)
                if (
                    token not in represented
                    or action_id in self.shape_translation_invalid_actions
                    or (
                        self.shape_translation_occluded_action is not None
                        and action_id != self.shape_translation_occluded_action
                    )
                ):
                    continue
                remainder = (
                    delta[0] - effect[0],
                    delta[1] - effect[1],
                )
                if any(
                    effect_axis != 0
                    and (
                        delta_axis == 0
                        or (effect_axis > 0) != (delta_axis > 0)
                        or abs(effect_axis) > abs(delta_axis)
                    )
                    for delta_axis, effect_axis in zip(delta, effect)
                ):
                    continue
                next_distance = abs(remainder[0]) + abs(remainder[1])
                if next_distance < distance:
                    productive.append((next_distance, action_id, token))
            if productive:
                token = min(productive)[2]
                effect = self.shape_translation_effects[token.action_id]
                self.shape_translation_pending_prediction = (
                    token.action_id,
                    self.shape_goal_mover_signature,
                    self.shape_goal_target_signature,
                    mover_origin,
                    target_origin,
                    effect,
                )
                self.shape_translation_level_trials += 1
                self.shape_translation_application_trials += 1
                self.shape_translation_diagnostic = "applying-translation"
                return token
        elif self._unique_shape_pair(observation.frame) is None:
            self.shape_translation_diagnostic = "no-unique-shape-pair"
            return None

        unprobed = tuple(
            token
            for token in plain_tokens
            if token.action_id not in self.shape_translation_probes
            and token.action_id not in self.shape_translation_invalid_actions
        )
        if not unprobed:
            self.shape_translation_diagnostic = "plain-actions-exhausted"
            return None
        probe = min(unprobed)
        self.shape_translation_probes.add(probe.action_id)
        self.shape_translation_level_trials += 1
        self.shape_translation_diagnostic = "probing-action"
        return probe

    def _select_committed_trajectory(
        self,
        observation: Observation,
        tokens: tuple[ActionToken, ...],
    ) -> ActionToken | None:
        """Construct, commit, and reuse one evidenced trajectory macro."""

        if (
            not self.committed_trajectory_planning
            or self.trajectory_disabled
            or self.trajectory_level_trials >= 40
        ):
            return None
        plain_tokens = tuple(
            token
            for token in tokens
            if not token.data
            and token.action_id not in {self.reset_action, self.complex_action}
        )
        if not plain_tokens:
            return None
        represented = {token.action_id: token for token in plain_tokens}

        if self.trajectory_stage == "not-attempted":
            grounding = self._trajectory_grounding(observation.frame)
            if grounding is None:
                self.trajectory_diagnostic = "no-unique-trajectory-grounding"
                return None
            self.trajectory_mover_signature = grounding.mover_signature
            self.trajectory_receptacle_signature = grounding.receptacle_signature
            self.trajectory_mover_color = grounding.mover_color
            self.trajectory_target_color = grounding.target_color
            self.trajectory_origin = grounding.mover_anchor
            self.trajectory_current_anchor = grounding.mover_anchor
            self.trajectory_target_anchor = grounding.target_anchor
            self.trajectory_stage = "probe"
            self.trajectory_causal_states.add(
                self._trajectory_causal_key(grounding.mover_anchor)
            )
            self.trajectory_diagnostic = "trajectory-grounded"

        current = self.trajectory_current_anchor
        origin = self.trajectory_origin
        target = self.trajectory_target_anchor
        if current is None or origin is None or target is None:
            self._disable_trajectory("incomplete-trajectory-grounding")
            return None

        if self.trajectory_stage == "probe":
            if self._trajectory_axes_grounded():
                self.trajectory_stage = "macro"
            else:
                unprobed = tuple(
                    token
                    for token in plain_tokens
                    if token.action_id not in self.trajectory_probes
                    and token.action_id not in self.trajectory_invalid_actions
                )
                if not unprobed:
                    self._disable_trajectory("translation-probes-exhausted")
                    return None
                token = min(unprobed)
                self.trajectory_probes.add(token.action_id)
                self.trajectory_pending = (
                    "probe",
                    token.action_id,
                    current,
                    None,
                )
                self.trajectory_level_trials += 1
                self.trajectory_diagnostic = "probing-trajectory-action"
                return token

        if self.trajectory_stage == "restore":
            required = (origin[0] - current[0], origin[1] - current[1])
            evidenced = tuple(
                represented[action_id]
                for action_id, effect in self.trajectory_effects.items()
                if effect == required
                and action_id in represented
                and action_id not in self.trajectory_restore_tried
            )
            candidates = evidenced or tuple(
                token
                for token in plain_tokens
                if token.action_id not in self.trajectory_invalid_actions
                and token.action_id not in self.trajectory_restore_tried
                and (
                    token.action_id in self.trajectory_no_effect_actions
                    or token.action_id not in self.trajectory_probes
                )
            )
            if not candidates:
                self._disable_trajectory("origin-restore-exhausted")
                return None
            token = min(candidates)
            self.trajectory_restore_tried.add(token.action_id)
            effect = self.trajectory_effects.get(token.action_id)
            expected = (
                (current[0] + effect[0], current[1] + effect[1])
                if effect is not None
                else None
            )
            self.trajectory_pending = (
                "restore",
                token.action_id,
                current,
                expected,
            )
            self.trajectory_level_trials += 1
            self.trajectory_diagnostic = "probing-origin-restore"
            return token

        if self.trajectory_stage == "macro":
            if self.trajectory_macro_action is None:
                delta = (target[0] - current[0], target[1] - current[1])
                reducers = []
                for action_id, effect in self.trajectory_effects.items():
                    dx, dy = effect
                    if (
                        action_id not in represented
                        or action_id
                        == self.trajectory_previous_failed_macro_action
                        or (dx != 0) == (dy != 0)
                    ):
                        continue
                    axis = 0 if dx else 1
                    effect_axis = effect[axis]
                    delta_axis = delta[axis]
                    if (
                        delta_axis == 0
                        or (effect_axis > 0) != (delta_axis > 0)
                        or abs(effect_axis) > abs(delta_axis)
                    ):
                        continue
                    reducers.append(
                        (
                            abs(delta_axis),
                            action_id,
                            effect,
                        )
                    )
                if not reducers:
                    self._disable_trajectory("no-endpoint-macro")
                    return None
                _residual, action_id, effect = min(reducers)
                self.trajectory_macro_action = action_id
                self.trajectory_macro_effect = effect
            action_id = self.trajectory_macro_action
            effect = self.trajectory_macro_effect
            if action_id not in represented or effect is None:
                self._disable_trajectory("endpoint-action-unavailable")
                return None
            if (
                len(self.trajectory_active_path) >= 2
                and self._trajectory_structural_endpoint(
                    observation.frame,
                    current,
                    effect,
                )
            ):
                macro = tuple(self.trajectory_active_path)
                if len(self.trajectory_endpoint_macros) >= 4:
                    self._disable_trajectory("endpoint-cap-reached")
                    return None
                self.trajectory_endpoint_macros.append(macro)
                self.trajectory_stage = "commit"
                self.trajectory_diagnostic = "rendered-structural-endpoint"
            else:
                token = represented[action_id]
                expected = (current[0] + effect[0], current[1] + effect[1])
                self.trajectory_pending = (
                    "macro",
                    action_id,
                    current,
                    expected,
                )
                self.trajectory_level_trials += 1
                self.trajectory_diagnostic = "applying-endpoint-macro"
                return token

        if self.trajectory_stage == "commit":
            candidates = tuple(
                token
                for token in plain_tokens
                if token.action_id not in self.trajectory_effects
                and token.action_id not in self.trajectory_invalid_actions
                and token.action_id != self.trajectory_macro_action
                and token.action_id != self.trajectory_commit_action
            )
            if not candidates or self.trajectory_commit_trials >= 2:
                self._disable_trajectory("commit-candidates-exhausted")
                return None
            token = min(candidates)
            self.trajectory_commit_action = token.action_id
            self.trajectory_commit_trials += 1
            self.trajectory_pending = (
                "commit",
                token.action_id,
                current,
                origin,
            )
            self.trajectory_level_trials += 1
            self.trajectory_diagnostic = "probing-trajectory-commit"
            return token

        if self.trajectory_stage == "navigate":
            if self.trajectory_plan_steps >= self._trajectory_plan_cap():
                self._disable_trajectory("trajectory-plan-cap-reached")
                return None
            planning_anchor = self.trajectory_latent_anchor or current
            (
                topology_nodes,
                uncertain_nodes,
                support_color,
            ) = self._trajectory_topology(observation.frame)
            if not topology_nodes:
                self._disable_trajectory("no-substrate-topology")
                return None
            self.trajectory_topology_nodes = set(topology_nodes)
            self.trajectory_uncertain_nodes = set(uncertain_nodes)
            self.trajectory_topology_support_color = support_color
            delta = (
                target[0] - planning_anchor[0],
                target[1] - planning_anchor[1],
            )
            if delta == (0, 0):
                settle_action = self.trajectory_navigation_action
                if (
                    settle_action is None
                    or settle_action not in represented
                    or self.trajectory_settle_steps
                    >= len(self.trajectory_committed_macro)
                ):
                    self._disable_trajectory("latent-plan-not-validated")
                    return None
                effect = self.trajectory_effects[settle_action]
                expected = (current[0] + effect[0], current[1] + effect[1])
                self.trajectory_pending = (
                    "settle",
                    settle_action,
                    current,
                    expected,
                )
                self.trajectory_settle_steps += 1
                self.trajectory_plan_steps += 1
                self.trajectory_level_trials += 1
                self.trajectory_diagnostic = "equilibrating-committed-replay"
                return represented[settle_action]
            planned_action = self._trajectory_bfs_action(
                planning_anchor,
                target,
                represented=frozenset(represented),
                frame_width=len(observation.frame[0]),
                frame_height=len(observation.frame),
                allowed_nodes=topology_nodes,
                forbidden_first=self._trajectory_replay_forbidden_actions(
                    planning_anchor
                ),
            )
            if planned_action is None:
                planned_action = self._trajectory_gate_refresh_action(
                    planning_anchor,
                    represented=frozenset(represented),
                    allowed_nodes=topology_nodes,
                    uncertain_nodes=uncertain_nodes,
                )
                if planned_action is None:
                    self._disable_trajectory("no-causal-plan")
                    return None
                self.trajectory_gate_refresh_actions[planned_action] += 1
                self.trajectory_diagnostic = "refreshing-uncertain-gate"
            effect = self.trajectory_effects[planned_action]
            self.trajectory_navigation_action = planned_action
            token = represented[planned_action]
            expected = (current[0] + effect[0], current[1] + effect[1])
            self.trajectory_pending = (
                "navigate",
                planned_action,
                current,
                expected,
            )
            self.trajectory_plan_steps += 1
            self.trajectory_level_trials += 1
            if self.trajectory_diagnostic != "refreshing-uncertain-gate":
                self.trajectory_diagnostic = "executing-causal-plan"
            return token
        return None

    def _trajectory_replay_parallel_actions(self) -> frozenset[int]:
        """Keep the fresh mover distinct from the first enacted replay step."""

        if (
            self.trajectory_replay_started
            or not self.trajectory_committed_macro
            or self.trajectory_origin is None
        ):
            return frozenset()
        first_anchor = self.trajectory_committed_macro[0]
        first_effect = (
            first_anchor[0] - self.trajectory_origin[0],
            first_anchor[1] - self.trajectory_origin[1],
        )
        return frozenset(
            action_id
            for action_id, effect in self.trajectory_effects.items()
            if effect != (0, 0)
            and (effect[0] != 0) == (first_effect[0] != 0)
        )

    def _trajectory_replay_forbidden_actions(
        self,
        fresh_anchor: tuple[int, int],
    ) -> frozenset[int]:
        """Prevent the fresh mover from merging with predicted replay."""

        forbidden = set(self._trajectory_replay_parallel_actions())
        if (
            not self.trajectory_replay_started
            or self.trajectory_replay_cursor
            >= len(self.trajectory_committed_macro)
        ):
            return frozenset(forbidden)
        replay_next = self.trajectory_committed_macro[
            self.trajectory_replay_cursor
        ]
        forbidden.update(
            action_id
            for action_id, effect in self.trajectory_effects.items()
            if (
                fresh_anchor[0] + effect[0],
                fresh_anchor[1] + effect[1],
            )
            == replay_next
        )
        return frozenset(forbidden)

    def _trajectory_gate_refresh_action(
        self,
        start: tuple[int, int],
        *,
        represented: frozenset[int],
        allowed_nodes: frozenset[tuple[int, int]],
        uncertain_nodes: frozenset[tuple[int, int]],
    ) -> int | None:
        """Choose one safe world-tick only after an uncertain gate blocks."""

        if not self.trajectory_contextual_blocks or not uncertain_nodes:
            return None
        candidates: list[tuple[int, int, int, int]] = []
        for action_id, effect in self.trajectory_effects.items():
            if (
                action_id not in represented
                or action_id in self.trajectory_invalid_actions
                or effect == (0, 0)
                or self.trajectory_contextual_blocks.get(
                    (start, action_id), 0
                )
            ):
                continue
            next_anchor = (
                start[0] + effect[0],
                start[1] + effect[1],
            )
            if next_anchor not in allowed_nodes:
                continue
            candidates.append(
                (
                    self.trajectory_gate_refresh_actions[action_id],
                    int(next_anchor in uncertain_nodes),
                    self.trajectory_effect_evidence[action_id] * -1,
                    action_id,
                )
            )
        return min(candidates)[3] if candidates else None

    def _trajectory_bfs_action(
        self,
        start: tuple[int, int],
        target: tuple[int, int],
        *,
        represented: frozenset[int],
        frame_width: int,
        frame_height: int,
        allowed_nodes: frozenset[tuple[int, int]] | None = None,
        forbidden_first: frozenset[int] = frozenset(),
    ) -> int | None:
        """Return a bounded A* action around blocks and first-step constraints."""

        if start == target:
            return None
        x_steps = [
            abs(effect[0])
            for effect in self.trajectory_effects.values()
            if effect[0]
        ]
        y_steps = [
            abs(effect[1])
            for effect in self.trajectory_effects.values()
            if effect[1]
        ]

        def heuristic(anchor: tuple[int, int]) -> int:
            dx = abs(target[0] - anchor[0])
            dy = abs(target[1] - anchor[1])
            x_cost = (
                (dx + max(x_steps) - 1) // max(x_steps)
                if x_steps
                else (0 if dx == 0 else 10**6)
            )
            y_cost = (
                (dy + max(y_steps) - 1) // max(y_steps)
                if y_steps
                else (0 if dy == 0 else 10**6)
            )
            return x_cost + y_cost

        queue: list[
            tuple[int, int, tuple[int, int], int | None]
        ] = [(heuristic(start), 0, start, None)]
        visited = {start}
        expanded = 0
        while queue and expanded < 64:
            _priority, depth, anchor, first_action = heapq.heappop(queue)
            expanded += 1
            if depth >= 16:
                continue
            actions = sorted(
                (
                    action_id
                    for action_id, effect in self.trajectory_effects.items()
                    if action_id in represented
                    and (depth > 0 or action_id not in forbidden_first)
                    and action_id not in self.trajectory_invalid_actions
                    and effect != (0, 0)
                    and self.trajectory_contextual_blocks.get(
                        (anchor, action_id), 0
                    )
                    == 0
                ),
                key=lambda action_id: (
                    abs(
                        target[0]
                        - (
                            anchor[0]
                            + self.trajectory_effects[action_id][0]
                        )
                    )
                    + abs(
                        target[1]
                        - (
                            anchor[1]
                            + self.trajectory_effects[action_id][1]
                        )
                    ),
                    action_id,
                ),
            )
            for action_id in actions:
                effect = self.trajectory_effects[action_id]
                next_anchor = (
                    anchor[0] + effect[0],
                    anchor[1] + effect[1],
                )
                if (
                    not 0 <= next_anchor[0] < frame_width
                    or not 0 <= next_anchor[1] < frame_height
                    or (
                        allowed_nodes is not None
                        and next_anchor not in allowed_nodes
                    )
                    or next_anchor in visited
                ):
                    continue
                next_first = (
                    action_id if first_action is None else first_action
                )
                if next_anchor == target:
                    return next_first
                visited.add(next_anchor)
                heapq.heappush(
                    queue,
                    (
                        depth + 1 + heuristic(next_anchor),
                        depth + 1,
                        next_anchor,
                        next_first,
                    ),
                )
        return None

    def select(
        self,
        observation: Observation,
        scene: Scene,
        legal_actions: tuple[int, ...],
        *,
        pragmatic_disequilibrium: bool = False,
        structure_scores: dict[str, int] | None = None,
    ) -> ExplorationChoice:
        """Choose an untried intervention or navigate to a known frontier."""

        state = self._state_key(observation, scene)
        if self.current_state != state:
            self.observe(observation, scene)
        if pragmatic_disequilibrium:
            self.pragmatic_disequilibrium_active = True
        if self.visual_primitives and pragmatic_disequilibrium:
            self.primitive_accommodation_active = True
        tokens = self._tokens(observation, scene, legal_actions)
        if not tokens:
            raise ValueError("epistemic explorer has no represented legal action")
        self.tokens_by_state[state] = tokens
        self.selection_frame = observation.frame
        self.last_scheme_components = ()
        self.last_relational_binding = {}

        local_repair = None
        if self.constraint_first_role_replay:
            local_repair = self._select_local_relation_repair(
                observation,
                scene,
                state,
                tokens,
            )
            if local_repair is not None:
                return self._issue(
                    state,
                    local_repair,
                    "epistemic-frontier:constraint-first-repair-local-relation",
                    scene,
                )

        replay = self._select_program_role(
            tokens,
            scene,
            pragmatic_disequilibrium=pragmatic_disequilibrium,
        )
        if replay is not None:
            return self._issue(
                state,
                replay,
                "epistemic-frontier:replay-successful-action-role",
                scene,
            )

        if not self.constraint_first_role_replay:
            local_repair = self._select_local_relation_repair(
                observation,
                scene,
                state,
                tokens,
            )
            if local_repair is not None:
                return self._issue(
                    state,
                    local_repair,
                    "epistemic-frontier:repair-local-relation",
                    scene,
                )

        select_apply = self._select_parameterized_select_apply_commit(
            observation,
            tokens,
        )
        if select_apply is not None:
            self.select_apply_level_trials += 1
            self.last_scheme_components = (
                "scheme:parameterized-select-apply-commit",
                "operator:bind-attribute",
                "operator:select",
                "operator:apply",
                "operator:commit",
            ) + (
                ("operator:nested-container-traversal",)
                if self.nested_target_plan_active
                else ()
            ) + (
                ("operator:nested-source-flattening",)
                if self.nested_source_plan_active
                else ()
            ) + (
                ("operator:relocate-connector",)
                if self.connector_relocation_plan_active
                else ()
            )
            return self._issue(
                state,
                select_apply,
                "epistemic-frontier:parameterized-select-apply-commit",
                scene,
            )

        cyclic = self._select_cyclic_alignment(
            observation,
            scene,
            state,
            tokens,
        )
        if cyclic is not None:
            self.cyclic_alignment_level_trials += 1
            if self.cyclic_alignment_scheme is not None:
                self.last_scheme_components = self.cyclic_alignment_scheme.components()
            return self._issue(
                state,
                cyclic,
                "epistemic-frontier:cyclic-sequence-alignment",
                scene,
            )

        trajectory = self._select_committed_trajectory(
            observation,
            tokens,
        )
        if trajectory is not None:
            self.last_scheme_components = (
                "scheme:committed-trajectory",
                "relation:hosted-mover-receptacle",
                "operator:probe-translation-role",
                "operator:construct-endpoint-macro",
                "operator:commit-enacted-trajectory",
                "state:committed-macro-and-replay-cursor",
            )
            return self._issue(
                state,
                trajectory,
                "epistemic-frontier:committed-trajectory-planning",
                scene,
            )

        shape_translation = self._select_shape_goal_translation(
            observation,
            tokens,
        )
        if shape_translation is not None:
            self.last_scheme_components = (
                "scheme:evidenced-shape-goal-translation",
                "relation:exact-normalized-shape",
                (
                    "operator:probe-action"
                    if self.shape_translation_diagnostic == "probing-action"
                    else "operator:apply-evidenced-translation"
                ),
            )
            return self._issue(
                state,
                shape_translation,
                "epistemic-frontier:shape-goal-translation",
                scene,
            )

        productive = self._select_productive_role(tokens, scene, state)
        if productive is not None:
            self.productive_reuse_level_trials += 1
            return self._issue(
                state,
                productive,
                "epistemic-frontier:reuse-productive-action-role",
                scene,
            )

        relational = self._select_relational_binding(
            state,
            tokens,
            scene,
            pragmatic_disequilibrium=pragmatic_disequilibrium,
            structure_scores=structure_scores or {},
        )
        if relational is not None:
            token, relational_scheme = relational
            self.last_scheme_components = relational_scheme.components()
            self.pending_relational_scheme = relational_scheme.scheme_id
            return self._issue(
                state,
                token,
                "epistemic-frontier:relational-scheme-binding:"
                f"{relational_scheme.operator}:"
                f"{relational_scheme.scheme_id}",
                scene,
            )

        variation = self._select_scheme_variation(
            state,
            tokens,
            scene,
            pragmatic_disequilibrium=pragmatic_disequilibrium,
            structure_scores=structure_scores or {},
        )
        if variation is not None:
            token, parameterized_scheme = variation
            self.last_scheme_components = parameterized_scheme.components()
            return self._issue(
                state,
                token,
                "epistemic-frontier:parameterized-scheme-variation:"
                f"{parameterized_scheme.scheme_id}",
                scene,
            )

        if self.uses_action_family_schema:
            _index, balanced = min(
                enumerate(tokens),
                key=lambda item: (
                    self.global_family_attempts[item[1].action_id],
                    self.family_attempts[(state, item[1].action_id)],
                    item[1].action_id,
                    self.attempts[(state, item[1])],
                    self.global_attempts[item[1]],
                    item[0],
                ),
            )
            return self._issue(
                state,
                balanced,
                "epistemic-frontier:hierarchical-action-family",
                scene,
            )

        untried = tuple(token for token in tokens if self.attempts[(state, token)] == 0)
        if untried:
            _index, novel = min(
                enumerate(untried),
                key=lambda item: self._novelty_rank(
                    state,
                    item[1],
                    item[0],
                ),
            )
            return self._issue(
                state,
                novel,
                "epistemic-frontier:untried-current-state",
                scene,
            )

        navigation = self._path_to_frontier(state)
        if navigation:
            return self._issue(
                state,
                navigation[0],
                "epistemic-frontier:navigate-known-state-graph",
                scene,
            )

        fallback = min(
            tokens,
            key=lambda token: (
                (
                    self.family_attempts[(state, token.action_id)]
                    if self.uses_action_family_schema
                    else 0
                ),
                self.attempts[(state, token)],
                token,
            ),
        )
        return self._issue(
            state,
            fallback,
            "epistemic-frontier:least-repeated-exhausted-state",
            scene,
        )

    def _select_local_relation_repair(
        self,
        observation: Observation,
        scene: Scene,
        state: StateKey,
        tokens: tuple[ActionToken, ...],
    ) -> ActionToken | None:
        """Prefer an evidenced constraint repair over undirected novelty."""

        if not self.local_relation_solver:
            return None
        represented = set(tokens)
        for x, y in self._local_relation_candidates(observation, scene):
            token = ActionToken(self.complex_action, (("x", x), ("y", y)))
            if token in represented and self.attempts[(state, token)] == 0:
                return token
        return None

    def _select_parameterized_select_apply_commit(
        self,
        observation: Observation,
        tokens: tuple[ActionToken, ...],
    ) -> ActionToken | None:
        """Bind an ordered attribute template to selectors and neutral slots."""

        if not self.parameterized_select_apply_commit:
            return None
        represented = set(tokens)
        while self.select_apply_cursor < len(self.select_apply_program):
            token = self.select_apply_program[self.select_apply_cursor]
            self.select_apply_cursor += 1
            if token in represented:
                return token
            self.select_apply_program = ()
            return None
        if self.select_apply_attempted:
            return None
        self.select_apply_attempted = True
        program = self._infer_select_apply_program(observation, tokens)
        if not program:
            return None
        self.select_apply_program = program
        self.select_apply_cursor = 1
        return program[0]

    def _infer_select_apply_program(
        self,
        observation: Observation,
        tokens: tuple[ActionToken, ...],
    ) -> tuple[ActionToken, ...]:
        """Infer ``select(attribute) -> apply(slot) -> commit`` from layout."""

        if self.complex_action not in observation.available_actions:
            self.select_apply_diagnostic = "complex-action-unavailable"
            return ()
        self.select_apply_diagnostic = "no-structural-candidate"
        objects = tuple(
            item for item in self._frame_objects(observation.frame) if item.area >= 2
        )
        groups: dict[
            tuple[int, tuple[tuple[int, int], ...], int],
            list[_FrameObject],
        ] = {}
        for item in objects:
            groups.setdefault((item.area, item.shape, item.centroid[1]), []).append(
                item
            )
        rows = tuple(
            tuple(sorted(items, key=lambda item: item.centroid))
            for items in groups.values()
            if 2 <= len(items) <= 8
            and len({item.centroid[0] for item in items}) == len(items)
        )
        represented = set(tokens)
        candidates: list[
            tuple[
                tuple[int, int, int, tuple[int, ...]],
                tuple[ActionToken, ...],
                bool,
                bool,
                bool,
            ]
        ] = []
        for reference in rows:
            size = len(reference)
            reference_colors = tuple(item.color for item in reference)
            color_set = set(reference_colors)
            if len(color_set) != size:
                continue
            selector_layouts = list(rows)
            if self.connector_relocation:
                selector_layouts.extend(
                    self._rectangular_selector_variants(
                        objects,
                        colors=color_set,
                        below=reference[0].centroid[1],
                    )
                )
            for selectors in selector_layouts:
                if len(selectors) != size:
                    continue
                if selectors[0].centroid[1] <= reference[0].centroid[1]:
                    continue
                if {item.color for item in selectors} != color_set:
                    continue
                selector_by_color = {item.color: item for item in selectors}
                target_layouts = list(rows)
                if self.multiline_target_binding:
                    target_layouts.extend(
                        self._multiline_target_layouts(
                            objects,
                            size=size,
                            above=reference[0].centroid[1],
                            below=selectors[0].centroid[1],
                        )
                    )
                for targets in target_layouts:
                    if len(targets) != size or len({item.color for item in targets}) != 1:
                        continue
                    target_y = targets[0].centroid[1]
                    if not (
                        reference[0].centroid[1]
                        < target_y
                        < selectors[0].centroid[1]
                    ):
                        continue
                    commit_actions = sorted(
                        action
                        for action in observation.available_actions
                        if action not in {self.reset_action, self.complex_action}
                    )
                    if not commit_actions:
                        continue
                    target_orders: tuple[tuple[_FrameObject, ...], ...] = (targets,)
                    is_multiline = len(
                        {item.centroid[1] for item in targets}
                    ) > 1
                    nested_plan = False
                    connector_plan = False
                    relocation_prefix: tuple[ActionToken, ...] = ()
                    if self.nested_target_traversal and is_multiline:
                        nested_order = None
                        if self.enclosure_target_traversal:
                            nested_order = self._nested_enclosure_order(
                                observation.frame,
                                targets,
                                objects,
                            )
                        if nested_order is None:
                            nested_order = self._nested_target_order(
                                observation.frame,
                                targets,
                            )
                        if (
                            nested_order is None
                            and self.connector_relocation
                        ):
                            relocation = self._relocated_connector_order(
                                observation.frame,
                                targets,
                                objects,
                            )
                            if relocation is not None:
                                marker, destination, nested_order = relocation
                                relocation_prefix = (
                                    ActionToken(
                                        self.complex_action,
                                        (
                                            ("x", marker.centroid[0]),
                                            ("y", marker.centroid[1]),
                                        ),
                                    ),
                                    ActionToken(
                                        self.complex_action,
                                        (
                                            ("x", destination.centroid[0]),
                                            ("y", destination.centroid[1]),
                                        ),
                                    ),
                                )
                                connector_plan = True
                        if nested_order is None:
                            continue
                        target_orders = (nested_order,)
                        nested_plan = True
                    elif self.spatial_order_variation and is_multiline:
                        target_orders = self._spatial_target_orderings(targets)
                    programs = []
                    for target_order in target_orders:
                        actions = list(relocation_prefix)
                        for source, target in zip(reference, target_order):
                            selector = selector_by_color[source.color]
                            selector_x, selector_y = self._object_click_point(
                                selector
                            )
                            actions.extend(
                                (
                                    ActionToken(
                                        self.complex_action,
                                        (
                                            ("x", selector_x),
                                            ("y", selector_y),
                                        ),
                                    ),
                                    ActionToken(
                                        self.complex_action,
                                        (
                                            ("x", target.centroid[0]),
                                            ("y", target.centroid[1]),
                                        ),
                                    ),
                                )
                            )
                        if any(token not in represented for token in actions):
                            continue
                        actions.append(ActionToken(commit_actions[0]))
                        programs.append(tuple(actions))
                    if not programs:
                        continue
                    combined: list[ActionToken] = []
                    clear_action = (
                        ActionToken(commit_actions[1])
                        if len(commit_actions) > 1
                        else None
                    )
                    for index, program in enumerate(programs):
                        if index:
                            if clear_action is None or clear_action not in represented:
                                break
                            combined.append(clear_action)
                        combined.extend(program)
                    vertical_span = selectors[0].centroid[1] - reference[0].centroid[1]
                    midpoint_error = abs(
                        2 * target_y
                        - reference[0].centroid[1]
                        - selectors[0].centroid[1]
                    )
                    candidates.append(
                        (
                            (
                                -size,
                                midpoint_error,
                                vertical_span,
                                reference_colors,
                            ),
                            tuple(combined),
                            nested_plan,
                            False,
                            connector_plan,
                        )
                    )
            if self.nested_source_traversal:
                for outputs in rows:
                    if len(outputs) != size:
                        continue
                    output_y = outputs[0].centroid[1]
                    if output_y <= reference[0].centroid[1]:
                        continue
                    if len({item.color for item in outputs}) != 1:
                        continue
                    source_layouts = self._multiline_source_layouts(
                        objects,
                        size=size,
                        colors=color_set,
                        above=reference[0].centroid[1],
                        below=output_y,
                    )
                    if source_layouts:
                        self.select_apply_diagnostic = "nested-source-layout"
                    for sources in source_layouts:
                        source_order = self._nested_target_order(
                            observation.frame,
                            sources,
                            uniform_payload=False,
                        )
                        if source_order is None:
                            self.select_apply_diagnostic = (
                                "nested-source-topology-unresolved"
                            )
                            continue
                        if tuple(item.color for item in source_order) != reference_colors:
                            self.select_apply_diagnostic = (
                                "nested-source-reference-mismatch"
                            )
                            continue
                        commit_actions = sorted(
                            action
                            for action in observation.available_actions
                            if action not in {self.reset_action, self.complex_action}
                        )
                        if not commit_actions:
                            self.select_apply_diagnostic = (
                                "nested-source-commit-unavailable"
                            )
                            continue
                        actions = []
                        for source, output in zip(source_order, outputs):
                            actions.extend(
                                (
                                    ActionToken(
                                        self.complex_action,
                                        (
                                            ("x", source.centroid[0]),
                                            ("y", source.centroid[1]),
                                        ),
                                    ),
                                    ActionToken(
                                        self.complex_action,
                                        (
                                            ("x", output.centroid[0]),
                                            ("y", output.centroid[1]),
                                        ),
                                    ),
                                )
                            )
                        missing_actions = tuple(
                            token for token in actions if token not in represented
                        )
                        if missing_actions:
                            self.select_apply_diagnostic = (
                                "nested-source-unrepresented:"
                                f"{len(missing_actions)}"
                            )
                            continue
                        actions.append(ActionToken(commit_actions[0]))
                        source_y = sum(
                            item.centroid[1] for item in sources
                        ) // len(sources)
                        candidates.append(
                            (
                                (
                                    -size,
                                    abs(
                                        2 * source_y
                                        - reference[0].centroid[1]
                                        - output_y
                                    ),
                                    output_y - reference[0].centroid[1],
                                    reference_colors,
                                ),
                                tuple(actions),
                                False,
                                True,
                                False,
                            )
                        )
                        self.select_apply_diagnostic = "nested-source-program"
        if not candidates:
            return ()
        winner = min(candidates, key=lambda item: item[0])
        self.nested_target_plan_active = winner[2]
        self.nested_source_plan_active = winner[3]
        self.connector_relocation_plan_active = winner[4]
        self.select_apply_diagnostic = (
            "nested-source-selected"
            if winner[3]
            else "connector-relocation-selected"
            if winner[4]
            else "nested-target-selected"
            if winner[2]
            else "select-apply-selected"
        )
        return winner[1]

    @staticmethod
    def _nested_enclosure_order(
        frame: tuple[tuple[int, ...], ...],
        targets: tuple[_FrameObject, ...],
        objects: tuple[_FrameObject, ...],
    ) -> tuple[_FrameObject, ...] | None:
        """Traverse sibling containers grounded by exact rendered enclosures."""

        if not frame or not frame[0] or not 3 <= len(targets) <= 12:
            return None
        columns = tuple(sorted({item.centroid[0] for item in targets}))
        if not 3 <= len(columns) <= 8:
            return None
        pitches = {
            right - left for left, right in zip(columns, columns[1:])
        }
        if len(pitches) != 1:
            return None
        pitch = pitches.pop()
        if pitch <= 0:
            return None

        def is_rectangle(item: _FrameObject) -> bool:
            min_x, min_y, max_x, max_y = item.bbox
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            if width < 3 or height < 3:
                return False
            perimeter = {
                (x, y)
                for y in range(height)
                for x in range(width)
                if x in {0, width - 1} or y in {0, height - 1}
            }
            return item.area == len(perimeter) and set(item.shape) == perimeter

        def encloses(item: _FrameObject, target: _FrameObject) -> bool:
            min_x, min_y, max_x, max_y = item.bbox
            x, y = target.centroid
            return min_x < x < max_x and min_y < y < max_y

        containers = tuple(
            item
            for item in objects
            if is_rectangle(item)
            and sum(encloses(item, target) for target in targets) >= 2
        )
        if not 2 <= len(containers) <= 4:
            return None

        assigned: dict[_FrameObject, list[_FrameObject]] = {
            container: [] for container in containers
        }
        for target in targets:
            enclosing = tuple(
                container for container in containers if encloses(container, target)
            )
            if not enclosing:
                return None
            smallest_area = min(container.area for container in enclosing)
            smallest = tuple(
                container
                for container in enclosing
                if container.area == smallest_area
            )
            if len(smallest) != 1:
                return None
            assigned[smallest[0]].append(target)
        if any(len(items) < 2 for items in assigned.values()):
            return None

        counts = Counter(cell for row in frame for cell in row)
        background = max(counts, key=lambda color: (counts[color], -color))
        target_color = targets[0].color
        height = len(frame)
        width = len(frame[0])
        entries: dict[_FrameObject, dict[int, _FrameObject | None]] = {}
        links: dict[tuple[_FrameObject, int], _FrameObject] = {}
        in_degree = Counter[_FrameObject]()

        for container, items in assigned.items():
            by_x = {item.centroid[0]: item for item in items}
            if len(by_x) != len(items):
                return None
            left = min(by_x)
            right = max(by_x)
            if (right - left) % pitch:
                return None
            slots = tuple(range(left, right + 1, pitch))
            row_entries: dict[int, _FrameObject | None] = {}
            target_y_values = {item.centroid[1] for item in items}
            if len(target_y_values) != 1:
                return None
            target_y = target_y_values.pop()
            for x in slots:
                slot_target = by_x.get(x)
                row_entries[x] = slot_target
                if slot_target is not None:
                    continue
                radius = max(1, pitch // 2)
                sampled = {
                    frame[sample_y][sample_x]
                    for sample_y in range(
                        max(0, target_y - radius),
                        min(height, target_y + radius + 1),
                    )
                    for sample_x in range(
                        max(0, x - radius),
                        min(width, x + radius + 1),
                    )
                    if frame[sample_y][sample_x]
                    not in {background, target_color, container.color}
                }
                if len(sampled) != 1:
                    return None
                connector_color = sampled.pop()
                children = tuple(
                    candidate
                    for candidate in containers
                    if candidate != container
                    and candidate.color == connector_color
                )
                if len(children) != 1:
                    return None
                child = children[0]
                links[(container, x)] = child
                in_degree[child] += 1
                if in_degree[child] > 1:
                    return None
            entries[container] = row_entries

        roots = tuple(
            container for container in containers if in_degree[container] == 0
        )
        if len(roots) != 1:
            return None
        ordered: list[_FrameObject] = []
        visiting: set[_FrameObject] = set()
        visited: set[_FrameObject] = set()

        def expand(container: _FrameObject) -> bool:
            if container in visiting or container in visited:
                return False
            visiting.add(container)
            for x, target in sorted(entries[container].items()):
                if target is not None:
                    ordered.append(target)
                    continue
                child = links.get((container, x))
                if child is None or not expand(child):
                    return False
            visiting.remove(container)
            visited.add(container)
            return True

        if not expand(roots[0]):
            return None
        if visited != set(containers) or set(ordered) != set(targets):
            return None
        return tuple(ordered)

    @staticmethod
    def _object_click_point(item: _FrameObject) -> tuple[int, int]:
        """Choose a represented colored pixel nearest an object's centroid."""

        min_x, min_y, _max_x, _max_y = item.bbox
        points = tuple(
            (min_x + local_x, min_y + local_y)
            for local_x, local_y in item.shape
        )
        return min(
            points,
            key=lambda point: (
                abs(point[0] - item.centroid[0])
                + abs(point[1] - item.centroid[1]),
                point[1],
                point[0],
            ),
        )

    @staticmethod
    def _rectangular_selector_variants(
        objects: tuple[_FrameObject, ...],
        *,
        colors: set[int],
        below: int,
    ) -> tuple[tuple[_FrameObject, ...], ...]:
        """Normalize a selected outline among otherwise filled selectors."""

        size = len(colors)
        grouped: dict[tuple[int, int, int], list[_FrameObject]] = {}
        for item in objects:
            min_x, min_y, max_x, max_y = item.bbox
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            if (
                item.color in colors
                and item.centroid[1] > below
                and 3 <= width <= 6
                and width == height
            ):
                grouped.setdefault((item.centroid[1], width, height), []).append(
                    item
                )
        variants = []
        for items in grouped.values():
            if (
                len(items) != size
                or {item.color for item in items} != colors
                or len({item.centroid[0] for item in items}) != size
            ):
                continue
            width = items[0].bbox[2] - items[0].bbox[0] + 1
            full_area = width * width
            outline_area = 4 * width - 4
            if all(item.area in {full_area, outline_area} for item in items):
                variants.append(tuple(sorted(items, key=lambda item: item.centroid)))
        return tuple(variants)

    @staticmethod
    def _relocated_connector_order(
        frame: tuple[tuple[int, ...], ...],
        targets: tuple[_FrameObject, ...],
        objects: tuple[_FrameObject, ...],
    ) -> tuple[_FrameObject, _FrameObject, tuple[_FrameObject, ...]] | None:
        """Construct a unique two-enclosure link by relocating its marker."""

        if not frame or not frame[0] or not 3 <= len(targets) <= 12:
            return None

        def is_outline_rectangle(item: _FrameObject) -> bool:
            min_x, min_y, max_x, max_y = item.bbox
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            if width < 3 or height < 3:
                return False
            perimeter = {
                (x, y)
                for y in range(height)
                for x in range(width)
                if x in {0, width - 1} or y in {0, height - 1}
            }
            return item.area == len(perimeter) and set(item.shape) == perimeter

        def encloses(container: _FrameObject, item: _FrameObject) -> bool:
            min_x, min_y, max_x, max_y = container.bbox
            x, y = item.centroid
            return min_x < x < max_x and min_y < y < max_y

        containers = tuple(
            item
            for item in objects
            if is_outline_rectangle(item)
            and sum(encloses(item, target) for target in targets) >= 2
        )
        if len(containers) != 2:
            return None

        assigned: dict[_FrameObject, list[_FrameObject]] = {
            container: [] for container in containers
        }
        for target in targets:
            enclosing = tuple(
                container for container in containers if encloses(container, target)
            )
            if not enclosing:
                return None
            smallest_area = min(container.area for container in enclosing)
            smallest = tuple(
                container
                for container in enclosing
                if container.area == smallest_area
            )
            if len(smallest) != 1:
                return None
            assigned[smallest[0]].append(target)
        if any(len(items) < 2 for items in assigned.values()):
            return None

        columns = tuple(sorted({item.centroid[0] for item in targets}))
        pitches = {
            right - left for left, right in zip(columns, columns[1:])
        }
        if len(pitches) != 1:
            return None
        pitch = pitches.pop()
        if pitch <= 0:
            return None

        candidates: list[
            tuple[_FrameObject, _FrameObject, _FrameObject, _FrameObject]
        ] = []
        target_set = set(targets)
        container_set = set(containers)
        for child in containers:
            parent = next(item for item in containers if item != child)
            child_markers = tuple(
                item
                for item in objects
                if item not in target_set
                and item not in container_set
                and item.color == child.color
                and encloses(child, item)
                and item.area
                == (item.bbox[2] - item.bbox[0] + 1)
                * (item.bbox[3] - item.bbox[1] + 1)
            )
            for marker in child_markers:
                destinations = tuple(
                    target
                    for target in assigned[parent]
                    if target.centroid[0] == marker.centroid[0]
                )
                if len(destinations) == 1:
                    candidates.append((marker, child, destinations[0], parent))
        if len(candidates) != 1:
            return None
        marker, child, destination, parent = candidates[0]

        child_slots = tuple(
            sorted((*assigned[child], marker), key=lambda item: item.centroid)
        )
        if len({item.centroid[1] for item in child_slots}) != 1:
            return None
        child_x = tuple(item.centroid[0] for item in child_slots)
        if any(right - left != pitch for left, right in zip(child_x, child_x[1:])):
            return None

        parent_slots = tuple(
            sorted(assigned[parent], key=lambda item: item.centroid)
        )
        if len({item.centroid[1] for item in parent_slots}) != 1:
            return None
        parent_x = tuple(item.centroid[0] for item in parent_slots)
        if any(
            right - left != pitch for left, right in zip(parent_x, parent_x[1:])
        ):
            return None

        ordered: list[_FrameObject] = []
        for target in parent_slots:
            if target == destination:
                ordered.extend(child_slots)
            else:
                ordered.append(target)
        if len(ordered) != len(targets) or len(set(ordered)) != len(targets):
            return None
        return marker, destination, tuple(ordered)

    @staticmethod
    def _nested_target_order(
        frame: tuple[tuple[int, ...], ...],
        targets: tuple[_FrameObject, ...],
        *,
        uniform_payload: bool = True,
    ) -> tuple[_FrameObject, ...] | None:
        """Expand rendered container links into a bounded depth-first order."""

        if not frame or not frame[0] or not 3 <= len(targets) <= 12:
            return None
        target_rows: dict[int, dict[int, _FrameObject]] = {}
        for item in targets:
            target_rows.setdefault(item.centroid[1], {})[item.centroid[0]] = item
        if not 2 <= len(target_rows) <= 4:
            return None
        if any(len(row) < 2 for row in target_rows.values()):
            return None

        columns = tuple(
            sorted({x for row in target_rows.values() for x in row})
        )
        if not 3 <= len(columns) <= 8:
            return None
        pitches = {
            right - left for left, right in zip(columns, columns[1:])
        }
        if len(pitches) != 1:
            return None
        pitch = pitches.pop()
        if pitch <= 0:
            return None

        counts = Counter(cell for row in frame for cell in row)
        background = max(counts, key=lambda color: (counts[color], -color))
        payload_backgrounds = {background}
        if uniform_payload:
            payload_backgrounds.add(targets[0].color)
        height = len(frame)
        width = len(frame[0])

        def boundary_color(
            y: int,
            start_x: int,
            direction: int,
        ) -> int | None:
            for distance in range(1, pitch + 1):
                x = start_x + direction * distance
                if not (0 <= x < width and 0 <= y < height):
                    return None
                color = frame[y][x]
                if color not in payload_backgrounds:
                    return color
            return None

        container_colors: dict[int, int] = {}
        for y, row in target_rows.items():
            left_item = row[min(row)]
            right_item = row[max(row)]
            left_color = boundary_color(y, left_item.bbox[0], -1)
            right_color = boundary_color(y, right_item.bbox[2], 1)
            if left_color is None or left_color != right_color:
                return None
            container_colors[y] = left_color
        if len(set(container_colors.values())) != len(container_colors):
            return None

        links: dict[tuple[int, int], int] = {}
        in_degree = Counter[int]()
        for y, row in target_rows.items():
            for x in columns:
                if x in row:
                    continue
                radius = max(1, pitch // 2)
                sampled = {
                    frame[sample_y][sample_x]
                    for sample_y in range(
                        max(0, y - radius),
                        min(height, y + radius + 1),
                    )
                    for sample_x in range(
                        max(0, x - radius),
                        min(width, x + radius + 1),
                    )
                    if frame[sample_y][sample_x]
                    not in payload_backgrounds | {container_colors[y]}
                }
                if len(sampled) != 1:
                    return None
                connector_color = sampled.pop()
                children = tuple(
                    child_y
                    for child_y, color in container_colors.items()
                    if child_y != y and color == connector_color
                )
                if len(children) != 1:
                    return None
                child_y = children[0]
                links[(y, x)] = child_y
                in_degree[child_y] += 1
                if in_degree[child_y] > 1:
                    return None

        roots = tuple(y for y in target_rows if in_degree[y] == 0)
        if len(roots) != 1:
            return None
        root = roots[0]
        ordered: list[_FrameObject] = []
        visiting: set[int] = set()
        visited: set[int] = set()

        def expand(y: int) -> bool:
            if y in visiting or y in visited:
                return False
            visiting.add(y)
            row = target_rows[y]
            for x in columns:
                target = row.get(x)
                if target is not None:
                    ordered.append(target)
                    continue
                child_y = links.get((y, x))
                if child_y is None or not expand(child_y):
                    return False
            visiting.remove(y)
            visited.add(y)
            return True

        if not expand(root):
            return None
        if visited != set(target_rows) or set(ordered) != set(targets):
            return None
        return tuple(ordered)

    @staticmethod
    def _multiline_source_layouts(
        objects: tuple[_FrameObject, ...],
        *,
        size: int,
        colors: set[int],
        above: int,
        below: int,
    ) -> tuple[tuple[_FrameObject, ...], ...]:
        """Find exact heterogeneous payload sets distributed across rows."""

        groups: dict[
            tuple[int, tuple[tuple[int, int], ...]],
            list[_FrameObject],
        ] = {}
        for item in objects:
            if above < item.centroid[1] < below and item.color in colors:
                groups.setdefault((item.area, item.shape), []).append(item)
        layouts = []
        for items in groups.values():
            if len(items) != size or {item.color for item in items} != colors:
                continue
            row_counts = Counter(item.centroid[1] for item in items)
            if not 2 <= len(row_counts) <= 4:
                continue
            if any(count < 2 for count in row_counts.values()):
                continue
            if len({item.centroid for item in items}) != size:
                continue
            layouts.append(
                tuple(sorted(items, key=lambda item: (item.centroid[1], item.centroid[0])))
            )
        return tuple(sorted(layouts, key=lambda items: tuple(item.centroid for item in items)))

    @staticmethod
    def _spatial_target_orderings(
        targets: tuple[_FrameObject, ...],
    ) -> tuple[tuple[_FrameObject, ...], ...]:
        """Construct bounded coordinate-free row/column traversal variations."""

        rows: dict[int, list[_FrameObject]] = {}
        columns: dict[int, list[_FrameObject]] = {}
        for item in targets:
            rows.setdefault(item.centroid[1], []).append(item)
            columns.setdefault(item.centroid[0], []).append(item)
        row_groups = tuple(
            tuple(sorted(rows[key], key=lambda item: item.centroid[0]))
            for key in sorted(rows)
        )
        column_groups = tuple(
            tuple(sorted(columns[key], key=lambda item: item.centroid[1]))
            for key in sorted(columns)
        )
        variants = (
            tuple(item for group in row_groups for item in group),
            tuple(
                item
                for index, group in enumerate(row_groups)
                for item in (group if index % 2 == 0 else tuple(reversed(group)))
            ),
            tuple(item for group in column_groups for item in group),
            tuple(
                item
                for index, group in enumerate(column_groups)
                for item in (group if index % 2 == 0 else tuple(reversed(group)))
            ),
        )
        return tuple(dict.fromkeys(variants))

    @staticmethod
    def _multiline_target_layouts(
        objects: tuple[_FrameObject, ...],
        *,
        size: int,
        above: int,
        below: int,
    ) -> tuple[tuple[_FrameObject, ...], ...]:
        """Merge only exact neutral-object types across bounded visual rows."""

        groups: dict[
            tuple[int, int, tuple[tuple[int, int], ...]],
            list[_FrameObject],
        ] = {}
        for item in objects:
            if above < item.centroid[1] < below:
                groups.setdefault((item.color, item.area, item.shape), []).append(item)
        layouts = []
        for items in groups.values():
            if len(items) != size:
                continue
            row_counts = Counter(item.centroid[1] for item in items)
            if not 2 <= len(row_counts) <= 4:
                continue
            if any(count < 2 for count in row_counts.values()):
                continue
            layouts.append(
                tuple(sorted(items, key=lambda item: (item.centroid[1], item.centroid[0])))
            )
        return tuple(sorted(layouts, key=lambda items: tuple(item.centroid for item in items)))

    def _issue(
        self,
        state: StateKey,
        token: ActionToken,
        reason: str,
        scene: Scene,
    ) -> ExplorationChoice:
        self.level_interventions = min(
            self.min_productive_reuse_interventions,
            self.level_interventions + 1,
        )
        self.attempts[(state, token)] += 1
        self.global_attempts[token] += 1
        self.family_attempts[(state, token.action_id)] += 1
        self.global_family_attempts[token.action_id] += 1
        grounding = self._grounding(token, scene)
        if (
            self.successful_role_replay
            or self.parameterized_scheme_variation
            or self.relational_scheme_binding
        ):
            self.episode_roles.append(grounding.role)
            self.episode_groundings.append(grounding)
        if self.starter_schemas and not self.last_scheme_components:
            self.last_scheme_components = self._starter_components(
                reason,
                grounding,
            )
        self.pending_frame = self.selection_frame
        self.pending_role = grounding.role
        self.pending_grounding = grounding
        self.pending = (state, token)
        return ExplorationChoice(token, reason)

    @staticmethod
    def _starter_components(
        reason: str,
        grounding: GroundedRole,
    ) -> tuple[str, ...]:
        if "repair-local-relation" in reason:
            schema_id = "repair-relation"
        elif "hierarchical-action-family" in reason:
            schema_id = "probe-action-family"
        elif grounding.primitive_id is not None:
            schema_id = "intervene-on-region"
        elif grounding.centroid is not None:
            schema_id = "intervene-on-object"
        else:
            schema_id = "bounded-novelty"
        components = {f"scheme:starter:{schema_id}"}
        if grounding.centroid is not None:
            components.add(
                "scheme:starter:intervene-on-region"
                if grounding.primitive_id is not None
                else "scheme:starter:intervene-on-object"
            )
        return tuple(sorted(components))

    def _observe_cyclic_transition(
        self,
        before: tuple[tuple[int, ...], ...],
        after: tuple[tuple[int, ...], ...],
        action_point: tuple[int, int] | None,
        *,
        progressed: bool,
    ) -> None:
        """Construct transport evidence, then a goal relation on progress."""

        if action_point is None:
            return
        anchors = self._marked_anchors(before)
        tracks = self._cyclic_tracks(
            before,
            include_graph_cycles=self.graph_cycle_transport,
        )
        if not anchors or not tracks:
            return
        for track in tracks:
            before_values = tuple(before[y][x] for x, y in track.points)
            after_values = (
                tuple(after[y][x] for x, y in track.points)
                if self._frame_contains(after, track.points)
                else ()
            )
            direction = self._unit_rotation(before_values, after_values)
            if direction is None or progressed:
                continue
            if self.graph_cycle_transport:
                self.grounded_cyclic_transports[(track.points, action_point)] = (
                    direction
                )
            if action_point[0] < min(point[0] for point in track.points):
                self.cyclic_transport_evidence[("left", direction)] += 1
            elif action_point[0] > max(point[0] for point in track.points):
                self.cyclic_transport_evidence[("right", direction)] += 1

        if not progressed:
            return
        candidates = [
            track
            for track in tracks
            if action_point[0] < min(point[0] for point in track.points)
            or action_point[0] > max(point[0] for point in track.points)
        ]
        if not candidates:
            return
        candidates.sort(key=lambda item: (-len(item.points), item.points))
        for track in candidates:
            side = (
                "left"
                if action_point[0] < min(point[0] for point in track.points)
                else "right"
            )
            learned_direction = self._preferred_cyclic_direction(side)
            if learned_direction is None:
                continue
            predicted = self._rotate_frame_track(
                before,
                track.points,
                learned_direction,
            )
            if not self._anchors_satisfied(predicted, anchors):
                continue
            left_direction = learned_direction if side == "left" else -learned_direction
            digest = hashlib.sha256(
                repr(
                    (
                        "anchor-token-matches-markers",
                        "cyclic-shift",
                        left_direction,
                    )
                ).encode()
            ).hexdigest()[:12]
            self.cyclic_alignment_scheme = CyclicAlignmentScheme(
                scheme_id=f"cyclic-alignment-{digest}",
                target_relation="anchor-token-matches-markers",
                controller_side="left",
                shift_direction=left_direction,
                evidence=(
                    "level-progress",
                    "predicted-cyclic-transport",
                    "marker-relative-match",
                ),
            )
            return

    def _select_cyclic_alignment(
        self,
        observation: Observation,
        scene: Scene,
        state: StateKey,
        tokens: tuple[ActionToken, ...],
    ) -> ActionToken | None:
        if (
            not self.cyclic_sequence_alignment
            or self.cyclic_alignment_scheme is None
            or self.cyclic_alignment_level_trials
            >= self.max_cyclic_alignment_trials_per_level
        ):
            return None
        anchors = self._marked_anchors(observation.frame)
        tracks = self._cyclic_tracks(
            observation.frame,
            include_graph_cycles=self.graph_cycle_transport,
        )
        if not anchors or not tracks:
            return None
        represented = {
            (dict(token.data).get("x"), dict(token.data).get("y")): token
            for token in tokens
            if token.action_id == self.complex_action
        }
        actions: list[
            tuple[
                tuple[int, int],
                tuple[tuple[int, int], ...],
                int,
                ActionToken,
            ]
        ] = []
        for track in tracks:
            controller_directions: tuple[tuple[tuple[int, int] | None, int], ...]
            evidenced = tuple(
                (controller, direction)
                for (points, controller), direction in (
                    self.grounded_cyclic_transports.items()
                )
                if points == track.points
            )
            if evidenced:
                controller_directions = evidenced
            elif self._axis_aligned_track(track.points):
                controller_directions = (
                    (
                        track.left_controller,
                        self.cyclic_alignment_scheme.shift_direction,
                    ),
                    (
                        track.right_controller,
                        -self.cyclic_alignment_scheme.shift_direction,
                    ),
                )
            else:
                controller_directions = ()
            for controller, direction in controller_directions:
                if controller is None:
                    continue
                token = represented.get(controller)
                if token is None:
                    continue
                actions.append((controller, track.points, direction, token))
        if not actions:
            return None

        points = tuple(sorted({point for track in tracks for point in track.points}))
        point_indexes = {point: index for index, point in enumerate(points)}
        initial = tuple(observation.frame[y][x] for x, y in points)
        goals = {
            point_indexes[anchor.point]: anchor.marker_color
            for anchor in anchors
            if anchor.point in point_indexes
        }
        if not goals or all(initial[index] == color for index, color in goals.items()):
            self.cyclic_last_plan_length = 0
            return None

        ordered_actions = tuple(
            sorted(actions, key=lambda item: (item[0], item[2], item[1]))
        )

        def estimate(values: tuple[int, ...]) -> tuple[int, int]:
            mismatches = 0
            distance = 0
            for index, color in goals.items():
                if values[index] == color:
                    continue
                mismatches += 1
                candidates = []
                for _controller, track_points, _direction, _token in ordered_actions:
                    indexes = tuple(point_indexes[point] for point in track_points)
                    if index not in indexes:
                        continue
                    anchor_index = indexes.index(index)
                    for marker_index, track_index in enumerate(indexes):
                        if values[track_index] != color:
                            continue
                        length = len(indexes)
                        candidates.append(
                            min(
                                (marker_index - anchor_index) % length,
                                (anchor_index - marker_index) % length,
                            )
                        )
                distance += min(candidates, default=len(points))
            return mismatches, distance

        if len(ordered_actions) <= 2:
            beam: list[tuple[tuple[int, ...], tuple[int, ...]]] = [(initial, ())]
            seen = {initial}
            remaining_trials = (
                self.max_cyclic_alignment_trials_per_level
                - self.cyclic_alignment_level_trials
            )
            for _depth in range(1, remaining_trials + 1):
                successors: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
                for values, plan in beam:
                    for action_index, (
                        _controller,
                        track_points,
                        direction,
                        _token,
                    ) in enumerate(ordered_actions):
                        updated = list(values)
                        indexes = tuple(point_indexes[point] for point in track_points)
                        rotated = self._rotate_values(
                            tuple(values[index] for index in indexes),
                            direction,
                        )
                        for index, value in zip(indexes, rotated):
                            updated[index] = value
                        successor = tuple(updated)
                        if successor in seen:
                            continue
                        successor_plan = (*plan, action_index)
                        if all(
                            successor[index] == color for index, color in goals.items()
                        ):
                            self.cyclic_last_plan_length = len(successor_plan)
                            return ordered_actions[successor_plan[0]][3]
                        seen.add(successor)
                        successors.append((successor, successor_plan))
                successors.sort(key=lambda item: (estimate(item[0]), item[1]))
                beam = successors[:64]
                if not beam:
                    break
            self.cyclic_last_plan_length = 0
            return None

        initial_estimate = estimate(initial)
        queue: list[tuple[int, int, int, tuple[int, ...], tuple[int, ...]]] = [
            (
                initial_estimate[0],
                initial_estimate[1],
                0,
                initial,
                (),
            )
        ]
        best_depth = {initial: 0}
        expansions = 0
        while queue and expansions < self.max_cyclic_plan_expansions:
            _mismatches, _distance, _depth, values, plan = heapq.heappop(queue)
            expansions += 1
            for action_index, (
                _controller,
                track_points,
                direction,
                _token,
            ) in enumerate(ordered_actions):
                updated = list(values)
                indexes = tuple(point_indexes[point] for point in track_points)
                track_values = tuple(values[index] for index in indexes)
                rotated = self._rotate_values(track_values, direction)
                for index, value in zip(indexes, rotated):
                    updated[index] = value
                successor = tuple(updated)
                successor_plan = (*plan, action_index)
                successor_depth = len(successor_plan)
                if best_depth.get(successor, successor_depth + 1) <= successor_depth:
                    continue
                if all(successor[index] == color for index, color in goals.items()):
                    self.cyclic_last_plan_length = len(successor_plan)
                    return ordered_actions[successor_plan[0]][3]
                best_depth[successor] = successor_depth
                successor_estimate = estimate(successor)
                heapq.heappush(
                    queue,
                    (
                        successor_estimate[0],
                        successor_estimate[1],
                        successor_depth,
                        successor,
                        successor_plan,
                    ),
                )
        self.cyclic_last_plan_length = 0
        return None

    @staticmethod
    def _axis_aligned_track(
        points: tuple[tuple[int, int], ...],
    ) -> bool:
        return all(
            left[0] == right[0] or left[1] == right[1]
            for left, right in zip(points, (*points[1:], points[0]))
        )

    def _preferred_cyclic_direction(self, side: str) -> int | None:
        votes = {
            direction: self.cyclic_transport_evidence[(side, direction)]
            for direction in (-1, 1)
        }
        direction, support = max(
            votes.items(),
            key=lambda item: (item[1], -item[0]),
        )
        return direction if support > 0 else None

    @staticmethod
    def _unit_rotation(
        before: tuple[int, ...],
        after: tuple[int, ...],
    ) -> int | None:
        if len(before) < 4 or len(before) != len(after):
            return None
        for direction in (1, -1):
            if EpistemicExplorer._rotate_values(before, direction) == after:
                return direction
        return None

    @staticmethod
    def _rotate_values(values: tuple[int, ...], direction: int) -> tuple[int, ...]:
        if not values:
            return ()
        amount = direction % len(values)
        return values[amount:] + values[:amount]

    @staticmethod
    def _rotate_frame_track(
        frame: tuple[tuple[int, ...], ...],
        points: tuple[tuple[int, int], ...],
        direction: int,
    ) -> tuple[tuple[int, ...], ...]:
        output = [list(row) for row in frame]
        values = tuple(frame[y][x] for x, y in points)
        for (x, y), value in zip(
            points,
            EpistemicExplorer._rotate_values(values, direction),
        ):
            output[y][x] = value
        return tuple(tuple(row) for row in output)

    @staticmethod
    def _frame_contains(
        frame: tuple[tuple[int, ...], ...],
        points: tuple[tuple[int, int], ...],
    ) -> bool:
        return bool(frame) and all(
            0 <= y < len(frame) and 0 <= x < len(frame[y]) for x, y in points
        )

    @staticmethod
    def _anchors_satisfied(
        frame: tuple[tuple[int, ...], ...],
        anchors: tuple[_MarkedAnchor, ...],
    ) -> bool:
        return bool(anchors) and all(
            frame[anchor.point[1]][anchor.point[0]] == anchor.marker_color
            for anchor in anchors
        )

    @staticmethod
    def _frame_objects(
        frame: tuple[tuple[int, ...], ...],
    ) -> tuple[_FrameObject, ...]:
        if not frame or not frame[0]:
            return ()
        height = len(frame)
        width = len(frame[0])
        counts = Counter(cell for row in frame for cell in row)
        background = max(counts, key=lambda color: (counts[color], -color))
        seen: set[tuple[int, int]] = set()
        output: list[_FrameObject] = []
        for y in range(height):
            for x in range(width):
                color = frame[y][x]
                if color == background or (x, y) in seen:
                    continue
                queue = deque([(x, y)])
                seen.add((x, y))
                points: list[tuple[int, int]] = []
                while queue:
                    point_x, point_y = queue.popleft()
                    points.append((point_x, point_y))
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        neighbor = (point_x + dx, point_y + dy)
                        if (
                            0 <= neighbor[0] < width
                            and 0 <= neighbor[1] < height
                            and neighbor not in seen
                            and frame[neighbor[1]][neighbor[0]] == color
                        ):
                            seen.add(neighbor)
                            queue.append(neighbor)
                min_x = min(point[0] for point in points)
                min_y = min(point[1] for point in points)
                max_x = max(point[0] for point in points)
                max_y = max(point[1] for point in points)
                shape = tuple(
                    sorted(
                        (point_x - min_x, point_y - min_y)
                        for point_x, point_y in points
                    )
                )
                output.append(
                    _FrameObject(
                        color=color,
                        area=len(points),
                        bbox=(min_x, min_y, max_x, max_y),
                        centroid=(
                            sum(point[0] for point in points) // len(points),
                            sum(point[1] for point in points) // len(points),
                        ),
                        shape=shape,
                    )
                )
        return tuple(output)

    @classmethod
    def _marked_anchors(
        cls,
        frame: tuple[tuple[int, ...], ...],
    ) -> tuple[_MarkedAnchor, ...]:
        objects = cls._frame_objects(frame)
        groups: dict[
            tuple[int, int, tuple[tuple[int, int], ...]],
            list[_FrameObject],
        ] = {}
        for item in objects:
            groups.setdefault((item.color, item.area, item.shape), []).append(item)
        anchors: list[_MarkedAnchor] = []
        for token in objects:
            min_x, min_y, max_x, max_y = token.bbox
            width = max_x - min_x + 1
            height = max_y - min_y + 1
            if width != height or token.area != width * height:
                continue
            for (_color, marker_area, _shape), markers in groups.items():
                if marker_area >= token.area:
                    continue
                top_left = any(
                    item.bbox[2] == min_x - 1 and item.bbox[3] == min_y - 1
                    for item in markers
                )
                top_right = any(
                    item.bbox[0] == max_x + 1 and item.bbox[3] == min_y - 1
                    for item in markers
                )
                bottom_left = any(
                    item.bbox[2] == min_x - 1 and item.bbox[1] == max_y + 1
                    for item in markers
                )
                bottom_right = any(
                    item.bbox[0] == max_x + 1 and item.bbox[1] == max_y + 1
                    for item in markers
                )
                if top_left and top_right and bottom_left and bottom_right:
                    anchors.append(
                        _MarkedAnchor(
                            point=token.centroid,
                            marker_color=markers[0].color,
                            token_area=token.area,
                            token_shape=token.shape,
                        )
                    )
                    break
        return tuple(sorted(set(anchors), key=lambda item: item.point))

    @classmethod
    def _cyclic_tracks(
        cls,
        frame: tuple[tuple[int, ...], ...],
        *,
        include_graph_cycles: bool = False,
    ) -> tuple[_CyclicTrack, ...]:
        anchors = cls._marked_anchors(frame)
        if not anchors:
            return ()
        objects = cls._frame_objects(frame)
        token_area = anchors[0].token_area
        token_shape = anchors[0].token_shape
        tokens = tuple(
            item
            for item in objects
            if item.area == token_area and item.shape == token_shape
        )
        positions = {item.centroid for item in tokens}
        if len(positions) < 4:
            return ()
        deltas: Counter[int] = Counter()
        by_y: dict[int, list[int]] = {}
        by_x: dict[int, list[int]] = {}
        for x, y in positions:
            by_y.setdefault(y, []).append(x)
            by_x.setdefault(x, []).append(y)
        for values in (*by_y.values(), *by_x.values()):
            ordered = sorted(values)
            deltas.update(
                right - left
                for left, right in zip(ordered, ordered[1:])
                if right > left
            )
        if not deltas:
            return ()
        pitch = max(deltas.items(), key=lambda item: (item[1], -item[0]))[0]
        x_values = sorted({point[0] for point in positions})
        y_values = sorted({point[1] for point in positions})
        rectangles: list[tuple[tuple[int, int], ...]] = []
        for left_index, left in enumerate(x_values):
            for right in x_values[left_index + 2 :]:
                if (right - left) % pitch:
                    continue
                for top_index, top in enumerate(y_values):
                    for bottom in y_values[top_index + 2 :]:
                        if (bottom - top) % pitch:
                            continue
                        path = cls._rectangular_perimeter(
                            left,
                            top,
                            right,
                            bottom,
                            pitch,
                        )
                        if all(point in positions for point in path) and all(
                            anchor.point in path for anchor in anchors
                        ):
                            rectangles.append(path)
        raw_tracks: list[tuple[tuple[int, int], ...]] = []
        if rectangles:
            principal = max(
                rectangles,
                key=lambda path: (
                    (max(point[0] for point in path) - min(point[0] for point in path))
                    * (
                        max(point[1] for point in path)
                        - min(point[1] for point in path)
                    ),
                    len(path),
                    path,
                ),
            )
            raw_tracks.append(principal)
            for anchor in anchors:
                row = sorted(
                    point for point in positions if point[1] == anchor.point[1]
                )
                containing_index = row.index(anchor.point)
                start = containing_index
                end = containing_index
                while start > 0 and row[start][0] - row[start - 1][0] == pitch:
                    start -= 1
                while end + 1 < len(row) and row[end + 1][0] - row[end][0] == pitch:
                    end += 1
                contiguous = tuple(row[start : end + 1])
                if len(contiguous) >= 5 and not set(contiguous).issubset(principal):
                    raw_tracks.append(contiguous)
        if include_graph_cycles:
            raw_tracks.extend(
                cls._graph_cycles(
                    positions,
                    tuple(anchor.point for anchor in anchors),
                    pitch,
                )
            )
        if not raw_tracks:
            return ()
        tracks = []
        for points in dict.fromkeys(raw_tracks):
            left_controller, right_controller = cls._paired_controllers(
                objects, points, pitch
            )
            tracks.append(
                _CyclicTrack(
                    points=points,
                    left_controller=left_controller,
                    right_controller=right_controller,
                )
            )
        return tuple(tracks)

    @staticmethod
    def _graph_cycles(
        positions: set[tuple[int, int]],
        anchors: tuple[tuple[int, int], ...],
        pitch: int,
        *,
        max_cycles: int = 64,
        max_cycle_length: int = 32,
        max_expansions: int = 8192,
    ) -> tuple[tuple[tuple[int, int], ...], ...]:
        """Enumerate a bounded chordless cycle basis around marked anchors."""

        if not 4 <= len(positions) <= 64 or pitch < 2:
            return ()
        adjacency = {
            point: tuple(
                sorted(
                    neighbor
                    for neighbor in positions
                    if neighbor != point
                    and max(
                        abs(neighbor[0] - point[0]),
                        abs(neighbor[1] - point[1]),
                    )
                    == pitch
                    and abs(neighbor[0] - point[0]) in {0, pitch}
                    and abs(neighbor[1] - point[1]) in {0, pitch}
                )
            )
            for point in positions
        }
        if any(len(neighbors) > 4 for neighbors in adjacency.values()):
            return ()
        cycles: set[tuple[tuple[int, int], ...]] = set()
        expansions = 0

        def canonical(
            cycle: tuple[tuple[int, int], ...],
        ) -> tuple[tuple[int, int], ...]:
            variants: list[tuple[tuple[int, int], ...]] = []
            for sequence in (cycle, tuple(reversed(cycle))):
                variants.extend(
                    (*sequence[index:], *sequence[:index])
                    for index in range(len(sequence))
                )
            return min(variants)

        for anchor in anchors:
            if anchor not in adjacency:
                continue
            stack: list[tuple[tuple[int, int], tuple[tuple[int, int], ...]]] = [
                (anchor, (anchor,))
            ]
            while stack and len(cycles) < max_cycles and expansions < max_expansions:
                current, path = stack.pop()
                expansions += 1
                for neighbor in adjacency[current]:
                    if neighbor == anchor and len(path) >= 4:
                        members = set(path)
                        if all(
                            sum(adjacent in members for adjacent in adjacency[member])
                            == 2
                            for member in path
                        ):
                            cycles.add(canonical(path))
                        continue
                    if neighbor in path or len(path) >= max_cycle_length:
                        continue
                    if len(stack) + expansions >= max_expansions:
                        continue
                    stack.append((neighbor, (*path, neighbor)))
        return tuple(sorted(cycles, key=lambda item: (len(item), item)))

    @staticmethod
    def _rectangular_perimeter(
        left: int,
        top: int,
        right: int,
        bottom: int,
        pitch: int,
    ) -> tuple[tuple[int, int], ...]:
        return (
            *((x, top) for x in range(left, right + 1, pitch)),
            *((right, y) for y in range(top + pitch, bottom + 1, pitch)),
            *((x, bottom) for x in range(right - pitch, left - 1, -pitch)),
            *((left, y) for y in range(bottom - pitch, top, -pitch)),
        )

    @staticmethod
    def _paired_controllers(
        objects: tuple[_FrameObject, ...],
        points: tuple[tuple[int, int], ...],
        pitch: int,
    ) -> tuple[tuple[int, int] | None, tuple[int, int] | None]:
        min_x = min(point[0] for point in points)
        max_x = max(point[0] for point in points)
        axis_y = points[0][1]
        left = [
            item
            for item in objects
            if item.centroid[0] < min_x and abs(item.centroid[1] - axis_y) <= pitch
        ]
        right = [
            item
            for item in objects
            if item.centroid[0] > max_x and abs(item.centroid[1] - axis_y) <= pitch
        ]
        pairs = [
            (left_item, right_item)
            for left_item in left
            for right_item in right
            if left_item.area == right_item.area
            and (
                left_item.bbox[2] - left_item.bbox[0],
                left_item.bbox[3] - left_item.bbox[1],
            )
            == (
                right_item.bbox[2] - right_item.bbox[0],
                right_item.bbox[3] - right_item.bbox[1],
            )
        ]
        if not pairs:
            return None, None
        left_item, right_item = min(
            pairs,
            key=lambda pair: (
                min_x - pair[0].centroid[0] + pair[1].centroid[0] - max_x,
                abs(pair[0].centroid[1] - axis_y) + abs(pair[1].centroid[1] - axis_y),
                pair[0].centroid,
                pair[1].centroid,
            ),
        )
        return left_item.centroid, right_item.centroid

    def _select_productive_role(
        self,
        tokens: tuple[ActionToken, ...],
        scene: Scene,
        state: StateKey,
    ) -> ActionToken | None:
        if not self.productive_role_reuse:
            return None
        if self.cross_retry_maturity:
            if self.level_failures == 1:
                return None
            if (
                self.level_failures == 0
                and not self.pragmatic_disequilibrium_active
            ):
                return None
        elif self.level_failures < 2 and not self.pragmatic_disequilibrium_active:
            return None
        if self.level_interventions < self.min_productive_reuse_interventions:
            return None
        if self.learned_local_relation:
            return None
        if (
            self.productive_reuse_level_trials
            >= self.max_productive_reuse_trials_per_level
        ):
            return None
        candidates = tuple(
            token
            for token in tokens
            if self.role_responses[self._role(token, scene)] > 0
        )
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda token: (
                -(
                    self.role_responses[self._role(token, scene)]
                    / self.role_trials[self._role(token, scene)]
                ),
                -self.role_responses[self._role(token, scene)],
                self.attempts[(state, token)],
                self.global_attempts[token],
                token,
            ),
        )

    def _select_program_role(
        self,
        tokens: tuple[ActionToken, ...],
        scene: Scene,
        *,
        pragmatic_disequilibrium: bool = False,
    ) -> ActionToken | None:
        if (
            not self.successful_role_replay
            or not self.successful_program
            or pragmatic_disequilibrium
        ):
            return None
        while self.program_cursor < len(self.successful_program):
            role = self.successful_program[self.program_cursor]
            self.program_cursor += 1
            matches = tuple(
                token for token in tokens if self._role(token, scene) == role
            )
            if matches:
                return min(
                    matches,
                    key=lambda token: (
                        self.global_attempts[token],
                        token,
                    ),
                )
        return None

    @staticmethod
    def _role_key(role: ActionRole) -> str:
        return repr(
            (
                role.action_id,
                role.color,
                role.area,
                role.shape,
                role.primitive_kind,
                role.primitive_properties,
            )
        )

    @classmethod
    def _scheme_id(
        cls,
        prefix: str,
        roles: tuple[ActionRole, ...],
        *parts: str,
    ) -> str:
        raw = "|".join((prefix, *parts, *(cls._role_key(role) for role in roles)))
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def _learn_parameterized_variations(
        self,
        program: tuple[ActionRole, ...],
    ) -> None:
        """Construct bounded higher-order variations from successful schemes."""

        if not program:
            return
        argument_id = self._scheme_id("operative", program)
        previous = tuple(self.successful_schemes.items())
        self.successful_schemes[argument_id] = program
        for base_id, base in previous:
            if base_id == argument_id:
                continue
            interleaved = tuple(role for pair in zip(base, program) for role in pair)
            shared_actions = {role.action_id for role in base} & {
                role.action_id for role in program
            }
            rebound = tuple(
                next(
                    (
                        modifier
                        for modifier in program
                        if modifier.action_id == role.action_id
                    ),
                    role,
                )
                if role.action_id in shared_actions
                else role
                for role in base
            )
            variants = (
                ("prefix", (*program[:1], *base)),
                ("suffix", (*base, *program[-1:])),
                ("interleave", interleaved),
                ("role-bind", rebound),
            )
            for operator, roles in variants:
                bounded = tuple(roles[:32])
                if not bounded or bounded == base:
                    continue
                scheme_id = self._scheme_id(
                    "parameterized",
                    bounded,
                    base_id,
                    argument_id,
                    operator,
                )
                self.parameterized_schemes[scheme_id] = ParameterizedScheme(
                    scheme_id=scheme_id,
                    base_id=base_id,
                    argument_id=argument_id,
                    operator=operator,
                    roles=bounded,
                    evidence=(base_id, argument_id),
                )
                self.variation_cursors.setdefault(scheme_id, 0)
        if len(self.parameterized_schemes) > 64:
            retained = dict(sorted(self.parameterized_schemes.items())[-64:])
            self.parameterized_schemes = retained
            self.variation_cursors = {
                key: self.variation_cursors.get(key, 0) for key in retained
            }

    @staticmethod
    def _ordinal_relation(left: int, right: int) -> str:
        return "same" if left == right else "larger" if right > left else "smaller"

    @classmethod
    def _role_relation(
        cls,
        before: GroundedRole,
        after: GroundedRole,
    ) -> RoleRelation:
        left = before.role
        right = after.role
        color = (
            "any"
            if left.color is None or right.color is None
            else "same"
            if left.color == right.color
            else "different"
        )
        area = (
            "any"
            if left.area is None or right.area is None
            else cls._ordinal_relation(left.area, right.area)
        )
        shape = (
            "any"
            if not left.shape or not right.shape
            else "same"
            if left.shape == right.shape
            else "different"
        )
        if before.centroid is None or after.centroid is None:
            horizontal = vertical = "any"
        else:
            horizontal = (
                "aligned"
                if before.centroid[0] == after.centroid[0]
                else "right"
                if after.centroid[0] > before.centroid[0]
                else "left"
            )
            vertical = (
                "aligned"
                if before.centroid[1] == after.centroid[1]
                else "below"
                if after.centroid[1] > before.centroid[1]
                else "above"
            )
        return RoleRelation(color, area, shape, horizontal, vertical)

    @staticmethod
    def _project_relation(
        relation: RoleRelation,
        operator: str,
    ) -> RoleRelation:
        if operator == "feature-manner":
            return RoleRelation(
                color=relation.color,
                area=relation.area,
                shape=relation.shape,
            )
        if operator == "spatial-manner":
            return RoleRelation(
                horizontal=relation.horizontal,
                vertical=relation.vertical,
            )
        return relation

    @classmethod
    def _relational_program_id(
        cls,
        program: tuple[GroundedRole, ...],
    ) -> str:
        actions = ",".join(str(item.role.action_id) for item in program)
        relations = "|".join(
            repr(cls._role_relation(left, right))
            for left, right in zip(program, program[1:])
        )
        return hashlib.sha256(
            f"relational-program|{actions}|{relations}".encode()
        ).hexdigest()[:12]

    def _learn_relational_variations(
        self,
        program: tuple[GroundedRole, ...],
    ) -> None:
        """Use one productive scheme's relations as another's manner."""

        bounded = tuple(program[:32])
        if not bounded:
            return
        argument_id = self._relational_program_id(bounded)
        previous = tuple(self.successful_relational_schemes.items())
        self.successful_relational_schemes[argument_id] = bounded
        for previous_id, previous_program in previous:
            if previous_id == argument_id:
                continue
            for base_id, base, modifier_id, modifier in (
                (previous_id, previous_program, argument_id, bounded),
                (argument_id, bounded, previous_id, previous_program),
            ):
                raw_constraints = tuple(
                    self._role_relation(left, right)
                    for left, right in zip(modifier, modifier[1:])
                )
                if not raw_constraints:
                    continue
                action_slots = tuple(item.role.action_id for item in base[:32])
                if not action_slots:
                    continue
                for operator in (
                    "feature-manner",
                    "spatial-manner",
                    "full-manner",
                ):
                    constraints = tuple(
                        self._project_relation(item, operator)
                        for item in raw_constraints[:32]
                    )
                    scheme_id = hashlib.sha256(
                        repr(
                            (
                                "relational-binding",
                                base_id,
                                modifier_id,
                                operator,
                                action_slots,
                                constraints,
                            )
                        ).encode()
                    ).hexdigest()[:12]
                    self.relational_schemes[scheme_id] = RelationalScheme(
                        scheme_id=scheme_id,
                        base_id=base_id,
                        modifier_id=modifier_id,
                        operator=operator,
                        action_slots=action_slots,
                        constraints=constraints,
                        evidence=(base_id, modifier_id),
                    )
                    self.relational_cursors.setdefault(scheme_id, 0)
        if len(self.relational_schemes) > 64:
            retained = dict(sorted(self.relational_schemes.items())[-64:])
            self.relational_schemes = retained
            self.relational_cursors = {
                key: self.relational_cursors.get(key, 0) for key in retained
            }
            self.relational_last = {
                key: value
                for key, value in self.relational_last.items()
                if key in retained
            }

    @classmethod
    def _satisfies_relation(
        cls,
        before: GroundedRole,
        after: GroundedRole,
        relation: RoleRelation,
    ) -> bool:
        observed = cls._role_relation(before, after)
        return all(
            expected == "any" or actual == expected
            for expected, actual in (
                (relation.color, observed.color),
                (relation.area, observed.area),
                (relation.shape, observed.shape),
                (relation.horizontal, observed.horizontal),
                (relation.vertical, observed.vertical),
            )
        )

    def _select_relational_binding(
        self,
        state: StateKey,
        tokens: tuple[ActionToken, ...],
        scene: Scene,
        *,
        pragmatic_disequilibrium: bool,
        structure_scores: dict[str, int],
    ) -> tuple[ActionToken, RelationalScheme] | None:
        if (
            not self.relational_scheme_binding
            or not pragmatic_disequilibrium
            or not self.relational_schemes
            or self.relational_level_trials >= self.max_relational_trials_per_level
        ):
            return None
        represented = tuple((token, self._grounding(token, scene)) for token in tokens)
        schemes = sorted(
            self.relational_schemes.values(),
            key=lambda scheme: (
                -(
                    structure_scores.get(
                        f"scheme:{scheme.scheme_id}",
                        0,
                    )
                    + self.relational_progress[scheme.scheme_id] * 4
                    - self.relational_stagnations[scheme.scheme_id]
                ),
                self.relational_trials[scheme.scheme_id],
                scheme.scheme_id,
            ),
        )
        for scheme in schemes:
            pragmatic_score = (
                structure_scores.get(f"scheme:{scheme.scheme_id}", 0)
                + self.relational_progress[scheme.scheme_id] * 4
                - self.relational_stagnations[scheme.scheme_id]
            )
            if pragmatic_score < 0:
                continue
            cursor = self.relational_cursors.get(scheme.scheme_id, 0)
            action_id = scheme.action_slots[cursor % len(scheme.action_slots)]
            constraint = scheme.constraints[cursor % len(scheme.constraints)]
            previous = self.relational_last.get(scheme.scheme_id)
            matches = [
                (token, grounding)
                for token, grounding in represented
                if token.action_id == action_id
                and self.attempts[(state, token)] == 0
                and (
                    previous is None
                    or self._satisfies_relation(
                        previous,
                        grounding,
                        constraint,
                    )
                )
            ]
            if not matches:
                continue
            token, grounding = min(
                matches,
                key=lambda item: (
                    self.global_attempts[item[0]],
                    item[0],
                ),
            )
            self.relational_cursors[scheme.scheme_id] = cursor + 1
            self.relational_last[scheme.scheme_id] = grounding
            self.relational_trials[scheme.scheme_id] += 1
            self.relational_application_steps[scheme.scheme_id] += 1
            self.relational_level_trials += 1
            self.last_relational_binding = {
                "scheme_id": scheme.scheme_id,
                "base_id": scheme.base_id,
                "modifier_id": scheme.modifier_id,
                "operator": scheme.operator,
                "slot_index": cursor % len(scheme.action_slots),
                "action_id": action_id,
                "constraint": {
                    "color": constraint.color,
                    "area": constraint.area,
                    "shape": constraint.shape,
                    "horizontal": constraint.horizontal,
                    "vertical": constraint.vertical,
                },
                "had_previous_grounding": previous is not None,
            }
            return token, scheme
        return None

    def _select_scheme_variation(
        self,
        state: StateKey,
        tokens: tuple[ActionToken, ...],
        scene: Scene,
        *,
        pragmatic_disequilibrium: bool,
        structure_scores: dict[str, int],
    ) -> tuple[ActionToken, ParameterizedScheme] | None:
        if (
            not self.parameterized_scheme_variation
            or not pragmatic_disequilibrium
            or not self.parameterized_schemes
        ):
            return None
        represented = tuple((token, self._role(token, scene)) for token in tokens)
        schemes = sorted(
            self.parameterized_schemes.values(),
            key=lambda scheme: (
                -structure_scores.get(f"scheme:{scheme.scheme_id}", 0),
                self.variation_trials[scheme.scheme_id],
                scheme.scheme_id,
            ),
        )
        for scheme in schemes:
            if structure_scores.get(f"scheme:{scheme.scheme_id}", 0) < 0:
                continue
            cursor = self.variation_cursors.get(scheme.scheme_id, 0)
            while cursor < len(scheme.roles):
                role = scheme.roles[cursor]
                cursor += 1
                self.variation_cursors[scheme.scheme_id] = cursor
                matches = [
                    token
                    for token, represented_role in represented
                    if represented_role == role and self.attempts[(state, token)] == 0
                ]
                if matches:
                    self.variation_trials[scheme.scheme_id] += 1
                    return min(matches), scheme
        return None

    def _grounding(
        self,
        token: ActionToken,
        scene: Scene,
    ) -> GroundedRole:
        if token.action_id != self.complex_action:
            return GroundedRole(ActionRole(token.action_id))
        data = dict(token.data)
        x = data.get("x")
        y = data.get("y")
        if x is None or y is None:
            return GroundedRole(ActionRole(token.action_id))
        point = (x, y)
        if self.visual_primitives:
            containing_primitives = []
            for primitive in scene.primitives:
                if primitive.kind not in {
                    "multicolor_region",
                    "enclosed_region",
                }:
                    continue
                min_x, min_y, _max_x, _max_y = primitive.bbox
                absolute_shape = {
                    (min_x + local_x, min_y + local_y)
                    for local_x, local_y in primitive.shape
                }
                if point in absolute_shape:
                    containing_primitives.append(primitive)
            if containing_primitives:
                primitive = min(
                    containing_primitives,
                    key=lambda item: (
                        item.complexity_cost,
                        item.area,
                        item.kind,
                        item.primitive_id,
                    ),
                )
                return GroundedRole(
                    ActionRole(
                        token.action_id,
                        area=primitive.area,
                        shape=primitive.shape,
                        primitive_kind=primitive.kind,
                        primitive_properties=primitive.properties,
                    ),
                    centroid=primitive.centroid,
                    primitive_id=primitive.primitive_id,
                )
        for item in scene.objects:
            min_x, min_y, _max_x, _max_y = item.bbox
            absolute_shape = {
                (min_x + local_x, min_y + local_y) for local_x, local_y in item.shape
            }
            if point in absolute_shape:
                return GroundedRole(
                    ActionRole(
                        token.action_id,
                        color=item.color,
                        area=item.area,
                        shape=item.shape,
                    ),
                    centroid=item.centroid,
                )
        return GroundedRole(ActionRole(token.action_id))

    def _role(self, token: ActionToken, scene: Scene) -> ActionRole:
        return self._grounding(token, scene).role

    def _novelty_rank(
        self,
        state: StateKey,
        token: ActionToken,
        stable_index: int,
    ) -> tuple[int, ...]:
        if self.uses_action_family_schema:
            return (
                self.global_family_attempts[token.action_id],
                self.family_attempts[(state, token.action_id)],
                self.global_attempts[token],
                stable_index,
            )
        return (self.global_attempts[token], stable_index)

    def _path_to_frontier(
        self,
        start: StateKey,
    ) -> tuple[ActionToken, ...]:
        queue: deque[tuple[StateKey, tuple[ActionToken, ...]]] = deque([(start, ())])
        seen = {start}
        while queue:
            state, path = queue.popleft()
            if state != start and self._has_frontier(state):
                return path
            outgoing = sorted(
                (
                    token,
                    destination,
                )
                for (source, token), destination in self.edges.items()
                if source == state
                and self.state_status.get(destination) == "NOT_FINISHED"
            )
            for token, destination in outgoing:
                if destination in seen:
                    continue
                seen.add(destination)
                queue.append((destination, (*path, token)))
        return ()

    def _has_frontier(self, state: StateKey) -> bool:
        return any(
            self.attempts[(state, token)] == 0
            for token in self.tokens_by_state.get(state, ())
        )

    def _tokens(
        self,
        observation: Observation,
        scene: Scene,
        legal_actions: tuple[int, ...],
    ) -> tuple[ActionToken, ...]:
        tokens = [
            ActionToken(action)
            for action in sorted(legal_actions)
            if action not in {self.reset_action, self.complex_action}
        ]
        if self.complex_action in legal_actions:
            tokens.extend(
                ActionToken(
                    self.complex_action,
                    (("x", x), ("y", y)),
                )
                for x, y in self._click_candidates(observation, scene)
            )
        return tuple(tokens)

    def _click_candidates(
        self,
        observation: Observation,
        scene: Scene,
    ) -> tuple[tuple[int, int], ...]:
        """Represent object hypotheses first, then a bounded coarse scan."""

        candidates: list[tuple[int, int]] = []
        if self.local_relation_solver:
            candidates.extend(self._local_relation_candidates(observation, scene))
        if self.multicolor_click_objects or (
            self.click_object_accommodation and self.level_failures > 0
        ):
            candidates.extend(self._multicolor_candidates(observation))
        if self.visual_primitives and (
            self.level_failures > 0 or self.primitive_accommodation_active
        ):
            primitives = sorted(
                (
                    item
                    for item in scene.primitives
                    if item.kind in {"multicolor_region", "enclosed_region"}
                ),
                key=lambda item: (
                    item.complexity_cost,
                    item.area,
                    item.kind,
                    item.bbox,
                    item.primitive_id,
                ),
            )
            for primitive in primitives:
                min_x, min_y, _max_x, _max_y = primitive.bbox
                points = tuple(
                    (min_x + local_x, min_y + local_y)
                    for local_x, local_y in primitive.shape
                )
                if not points:
                    continue
                candidates.append(
                    min(
                        points,
                        key=lambda point: (
                            abs(point[0] - primitive.centroid[0])
                            + abs(point[1] - primitive.centroid[1]),
                            point[1],
                            point[0],
                        ),
                    )
                )
        objects = sorted(
            scene.objects,
            key=lambda item: (
                item.area,
                item.color,
                item.centroid[1],
                item.centroid[0],
                item.object_id,
            ),
        )
        for item in objects:
            min_x, min_y, _max_x, _max_y = item.bbox
            points = tuple(
                (min_x + local_x, min_y + local_y) for local_x, local_y in item.shape
            )
            if not points:
                continue
            representative = min(
                points,
                key=lambda point: (
                    abs(point[0] - item.centroid[0]) + abs(point[1] - item.centroid[1]),
                    point[1],
                    point[0],
                ),
            )
            candidates.append(representative)

        height = len(observation.frame)
        width = len(observation.frame[0]) if observation.frame else 0
        if width and height:
            step = max(4, min(width, height) // 8)
            candidates.extend(
                (min(width - 1, x), min(height - 1, y))
                for y in range(step // 2, height, step)
                for x in range(step // 2, width, step)
            )

        unique: list[tuple[int, int]] = []
        seen: set[tuple[int, int]] = set()
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            unique.append(candidate)
            if len(unique) >= self.max_click_candidates:
                break
        if not unique and width and height:
            unique.append((width // 2, height // 2))
        return tuple(unique)

    def _local_relation_candidates(
        self,
        observation: Observation,
        scene: Scene,
    ) -> tuple[tuple[int, int], ...]:
        """Induce equality constraints from repeated 3x3 visual panels."""

        if self.global_relation_constraint_solver:
            global_candidates = self._global_relation_candidates(
                observation,
                scene,
            )
            if global_candidates:
                return global_candidates

        blocks = tuple(
            item
            for item in scene.objects
            if 16 <= item.area <= 100
            and item.bbox[2] - item.bbox[0] == item.bbox[3] - item.bbox[1]
            and item.area
            == (item.bbox[2] - item.bbox[0] + 1) * (item.bbox[3] - item.bbox[1] + 1)
        )
        if len(blocks) < 8:
            return ()
        sizes = Counter(item.bbox[2] - item.bbox[0] + 1 for item in blocks)
        size, _support = max(sizes.items(), key=lambda item: (item[1], item[0]))
        blocks = tuple(
            item for item in blocks if item.bbox[2] - item.bbox[0] + 1 == size
        )
        if len(blocks) < 8 or size % 3:
            return ()
        origins = {(item.bbox[0], item.bbox[1]): item for item in blocks}
        x_values = sorted({point[0] for point in origins})
        y_values = sorted({point[1] for point in origins})
        deltas = [
            right - left
            for values in (x_values, y_values)
            for left, right in zip(values, values[1:])
            if size < right - left <= size * 2
        ]
        if not deltas:
            return ()
        step, _count = Counter(deltas).most_common(1)[0]
        directions = (
            (-1, -1),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        )
        panels: list[
            tuple[
                tuple[int, ...],
                int,
                tuple[tuple[ObjectState, int], ...],
            ]
        ] = []
        frame = observation.frame
        for origin_x, origin_y in sorted(origins):
            center_x = origin_x + step
            center_y = origin_y + step
            neighbors: list[tuple[ObjectState, int]] = []
            valid = True
            for dx, dy in directions:
                item = origins.get((center_x + dx * step, center_y + dy * step))
                if item is None:
                    valid = False
                    break
                neighbors.append((item, item.color))
            if not valid:
                continue
            if (
                center_y < 0
                or center_x < 0
                or center_y + size > len(frame)
                or not frame
                or center_x + size > len(frame[0])
            ):
                continue
            subcell = size // 3
            clue = tuple(
                frame[center_y + row * subcell + subcell // 2][
                    center_x + column * subcell + subcell // 2
                ]
                for row in range(3)
                for column in range(3)
            )
            center_color = clue[4]
            if len(set(clue)) < 2:
                continue
            panels.append((clue, center_color, tuple(neighbors)))
        clue_indexes = (0, 1, 2, 3, 5, 6, 7, 8)
        if len(panels) >= 3 and not self.learned_local_relation:
            relation_counts: dict[int, Counter[bool]] = {}
            for clue, center_color, panel_neighbors in panels:
                for clue_index, (_item, color) in zip(clue_indexes, panel_neighbors):
                    relation_counts.setdefault(clue[clue_index], Counter())[
                        color == center_color
                    ] += 1
            self.learned_local_relation = {
                symbol: max(counts, key=lambda value: (counts[value], value))
                for symbol, counts in relation_counts.items()
            }
        relation = self.learned_local_relation
        if not panels or not relation:
            return ()

        ranked: list[tuple[int, tuple[tuple[int, int], ...]]] = []
        for clue, center_color, panel_neighbors in panels:
            violations = []
            for clue_index, (item, color) in zip(clue_indexes, panel_neighbors):
                expected_same = relation.get(clue[clue_index])
                if expected_same is None:
                    continue
                if (color == center_color) != expected_same:
                    violations.append(item.centroid)
            if violations:
                ranked.append((len(violations), tuple(violations)))
        if not ranked:
            return ()
        _count, output = max(ranked, key=lambda item: (item[0], item[1]))
        return output

    def _global_relation_candidates(
        self,
        observation: Observation,
        scene: Scene,
    ) -> tuple[tuple[int, int], ...]:
        """Coordinate consistent clue constraints on one inferred tile lattice."""

        relation = self.learned_local_relation
        frame = observation.frame
        if not relation or not frame or not frame[0]:
            return ()
        blocks = tuple(
            item
            for item in scene.objects
            if 16 <= item.area <= 100
            and item.bbox[2] - item.bbox[0] == item.bbox[3] - item.bbox[1]
            and item.area
            == (item.bbox[2] - item.bbox[0] + 1) * (item.bbox[3] - item.bbox[1] + 1)
        )
        if len(blocks) < 8:
            return ()
        sizes = Counter(item.bbox[2] - item.bbox[0] + 1 for item in blocks)
        size, _support = max(sizes.items(), key=lambda item: (item[1], item[0]))
        if size % 3:
            return ()
        blocks = tuple(
            item for item in blocks if item.bbox[2] - item.bbox[0] + 1 == size
        )
        if len(blocks) < 8:
            return ()
        x_values = sorted({item.bbox[0] for item in blocks})
        y_values = sorted({item.bbox[1] for item in blocks})
        deltas = [
            right - left
            for values in (x_values, y_values)
            for left, right in zip(values, values[1:])
            if size < right - left <= size * 2
        ]
        if not deltas:
            return ()
        step, _count = Counter(deltas).most_common(1)[0]
        x_phase, _x_support = Counter(
            item.bbox[0] % step for item in blocks
        ).most_common(1)[0]
        y_phase, _y_support = Counter(
            item.bbox[1] % step for item in blocks
        ).most_common(1)[0]
        origins = {(item.bbox[0], item.bbox[1]): item for item in blocks}
        directions = (
            (-1, -1),
            (0, -1),
            (1, -1),
            (-1, 0),
            (1, 0),
            (-1, 1),
            (0, 1),
            (1, 1),
        )
        clue_indexes = (0, 1, 2, 3, 5, 6, 7, 8)
        subcell = size // 3
        height = len(frame)
        width = len(frame[0])
        constraints: dict[tuple[int, int], list[bool]] = {}
        support: Counter[tuple[int, int]] = Counter()
        for origin_y in range(y_phase, height - size + 1, step):
            for origin_x in range(x_phase, width - size + 1, step):
                if (origin_x, origin_y) in origins:
                    continue
                clue = []
                uniform = True
                for row in range(3):
                    for column in range(3):
                        start_x = origin_x + column * subcell
                        start_y = origin_y + row * subcell
                        values = {
                            frame[y][x]
                            for y in range(start_y, start_y + subcell)
                            for x in range(start_x, start_x + subcell)
                        }
                        if len(values) != 1:
                            uniform = False
                            break
                        clue.append(next(iter(values)))
                    if not uniform:
                        break
                if not uniform or len(clue) != 9 or len(set(clue)) < 2:
                    continue
                center_color = clue[4]
                for clue_index, (dx, dy) in zip(clue_indexes, directions):
                    expected_same = relation.get(clue[clue_index])
                    neighbor = origins.get((origin_x + dx * step, origin_y + dy * step))
                    if expected_same is None or neighbor is None:
                        continue
                    centroid = neighbor.centroid
                    constraints.setdefault(centroid, []).append(
                        (neighbor.color == center_color) != expected_same
                    )
                    support[centroid] += 1
        candidates = [
            centroid
            for centroid, violations in constraints.items()
            if violations and all(violations)
        ]
        return tuple(
            sorted(
                candidates,
                key=lambda centroid: (-support[centroid], centroid),
            )
        )

    def _multicolor_candidates(
        self,
        observation: Observation,
    ) -> tuple[tuple[int, int], ...]:
        """Group adjacent foreground colors into bounded visual affordances."""

        frame = observation.frame
        if not frame or not frame[0]:
            return ()
        height = len(frame)
        width = len(frame[0])
        counts = Counter(cell for row in frame for cell in row)
        background = max(counts, key=lambda color: (counts[color], -color))
        seen: set[tuple[int, int]] = set()
        regions: list[tuple[tuple[int, int], ...]] = []
        for y in range(height):
            for x in range(width):
                if frame[y][x] == background or (x, y) in seen:
                    continue
                queue = deque([(x, y)])
                seen.add((x, y))
                points: list[tuple[int, int]] = []
                while queue:
                    px, py = queue.popleft()
                    points.append((px, py))
                    for dy in (-1, 0, 1):
                        for dx in (-1, 0, 1):
                            if dx == dy == 0:
                                continue
                            nx, ny = px + dx, py + dy
                            if (
                                0 <= nx < width
                                and 0 <= ny < height
                                and (nx, ny) not in seen
                                and frame[ny][nx] != background
                            ):
                                seen.add((nx, ny))
                                queue.append((nx, ny))
                if 2 <= len(points) <= 512:
                    regions.append(tuple(points))

        output: list[tuple[int, int]] = []
        for region_points in sorted(
            regions,
            key=lambda region: (
                len(region),
                min(point[1] for point in region),
                min(point[0] for point in region),
            ),
        ):
            xs = tuple(point[0] for point in region_points)
            ys = tuple(point[1] for point in region_points)
            center = (
                (min(xs) + max(xs)) // 2,
                (min(ys) + max(ys)) // 2,
            )
            output.append(
                min(
                    region_points,
                    key=lambda point: (
                        abs(point[0] - center[0]) + abs(point[1] - center[1]),
                        point[1],
                        point[0],
                    ),
                )
            )
        return tuple(output)

    @staticmethod
    def _state_key(
        observation: Observation,
        scene: Scene,
    ) -> StateKey:
        return (
            observation.levels_completed,
            observation.state,
            scene.frame_digest,
        )

    def _forget_oldest_state(self) -> None:
        oldest = self.visit_order.pop(0)
        self.state_status.pop(oldest, None)
        self.tokens_by_state.pop(oldest, None)
        for key in tuple(self.attempts):
            if key[0] == oldest:
                del self.attempts[key]
        for family_key in tuple(self.family_attempts):
            if family_key[0] == oldest:
                del self.family_attempts[family_key]
        for edge, destination in tuple(self.edges.items()):
            if edge[0] == oldest or destination == oldest:
                del self.edges[edge]

    def to_dict(self) -> dict[str, Any]:
        return {
            "states": len(self.state_status),
            "edges": len(self.edges),
            "attempts": sum(self.attempts.values()),
            "global_interventions": len(self.global_attempts),
            "action_families": len(self.global_family_attempts),
            "successful_program_length": len(self.successful_program),
            "program_cursor": self.program_cursor,
            "perceptual_accommodations": self.level_failures,
            "productive_roles": sum(
                response > 0 for response in self.role_responses.values()
            ),
            "productive_reuse_level_trials": (self.productive_reuse_level_trials),
            "learned_cyclic_alignments": (
                1 if self.cyclic_alignment_scheme is not None else 0
            ),
            "cyclic_transport_evidence": sum(self.cyclic_transport_evidence.values()),
            "cyclic_alignment_level_trials": (self.cyclic_alignment_level_trials),
            "cyclic_last_plan_length": self.cyclic_last_plan_length,
            "grounded_cyclic_transports": len(self.grounded_cyclic_transports),
            "select_apply_program_length": len(self.select_apply_program),
            "select_apply_cursor": self.select_apply_cursor,
            "select_apply_level_trials": self.select_apply_level_trials,
            "select_apply_diagnostic": self.select_apply_diagnostic,
            "shape_translation_effects": len(self.shape_translation_effects),
            "shape_translation_effect_evidence": sum(
                self.shape_translation_effect_evidence.values()
            ),
            "shape_translation_probes": len(self.shape_translation_probes),
            "shape_translation_invalid_actions": len(
                self.shape_translation_invalid_actions
            ),
            "shape_goal_grounded": int(
                self.shape_goal_mover_signature is not None
                and self.shape_goal_target_signature is not None
            ),
            "shape_translation_level_trials": (
                self.shape_translation_level_trials
            ),
            "shape_translation_application_trials": (
                self.shape_translation_application_trials
            ),
            "shape_translation_occluded_steps": (
                self.shape_translation_occluded_steps
            ),
            "shape_translation_phases": len(
                self.shape_translation_phase_models
            ),
            "shape_translation_phase_transitions": (
                self.shape_translation_phase_transition_count
            ),
            "shape_translation_phase_blocked": int(
                self.shape_translation_phase_blocked
            ),
            "shape_translation_diagnostic": self.shape_translation_diagnostic,
            "trajectory_stage": self.trajectory_stage,
            "trajectory_current_anchor": self.trajectory_current_anchor,
            "trajectory_latent_anchor": self.trajectory_latent_anchor,
            "trajectory_target_anchor": self.trajectory_target_anchor,
            "trajectory_effects": len(self.trajectory_effects),
            "trajectory_effect_evidence": sum(
                self.trajectory_effect_evidence.values()
            ),
            "trajectory_probes": len(self.trajectory_probes),
            "trajectory_endpoint_macros": len(self.trajectory_endpoint_macros),
            "trajectory_contextual_blocks": len(
                self.trajectory_contextual_blocks
            ),
            "trajectory_gate_failures": sum(
                self.trajectory_gate_failures.values()
            ),
            "trajectory_gate_cooldowns": len(
                self.trajectory_gate_cooldowns
            ),
            "trajectory_gate_refresh_action_roles": len(
                self.trajectory_gate_refresh_actions
            ),
            "trajectory_topology_nodes": len(self.trajectory_topology_nodes),
            "trajectory_uncertain_nodes": len(
                self.trajectory_uncertain_nodes
            ),
            "trajectory_topology_support_grounded": int(
                self.trajectory_topology_support_color is not None
            ),
            "trajectory_committed_macro_length": len(
                self.trajectory_committed_macro
            ),
            "trajectory_enacted_path_length": len(
                self.trajectory_enacted_path
            ),
            "trajectory_replay_cursor": self.trajectory_replay_cursor,
            "trajectory_replay_started": int(self.trajectory_replay_started),
            "trajectory_replay_validations": (
                self.trajectory_replay_validations
            ),
            "trajectory_causal_states": len(self.trajectory_causal_states),
            "trajectory_causal_edges": len(self.trajectory_causal_edges),
            "trajectory_boundary_nuisance_evidenced": int(
                self.trajectory_boundary_nuisance_evidenced
            ),
            "trajectory_plan_steps": self.trajectory_plan_steps,
            "trajectory_plan_cap": self._trajectory_plan_cap(),
            "trajectory_settle_steps": self.trajectory_settle_steps,
            "trajectory_level_trials": self.trajectory_level_trials,
            "trajectory_disabled": int(self.trajectory_disabled),
            "trajectory_diagnostic": self.trajectory_diagnostic,
            "level_interventions": self.level_interventions,
            "learned_local_relations": len(self.learned_local_relation),
            "successful_schemes": len(self.successful_schemes),
            "parameterized_schemes": len(self.parameterized_schemes),
            "parameterized_scheme_trials": sum(self.variation_trials.values()),
            "starter_schemas": (len(STARTER_SCHEMA_SET) if self.starter_schemas else 0),
            "starter_schema_ids": (
                [item.schema_id for item in STARTER_SCHEMA_SET]
                if self.starter_schemas
                else []
            ),
            "successful_relational_schemes": len(self.successful_relational_schemes),
            "relational_schemes": len(self.relational_schemes),
            "relational_scheme_trials": sum(self.relational_trials.values()),
            "responsive_relational_schemes": sum(
                value > 0 for value in self.relational_responses.values()
            ),
            "progressing_relational_schemes": sum(
                value > 0 for value in self.relational_progress.values()
            ),
            "falsified_relational_schemes": sum(
                self.relational_progress[scheme_id] * 4 - stagnations < 0
                for scheme_id, stagnations in self.relational_stagnations.items()
            ),
            "relational_level_trials": self.relational_level_trials,
            "last_relational_binding": dict(self.last_relational_binding),
            "frontier_states": sum(
                self._has_frontier(state) for state in self.tokens_by_state
            ),
        }
