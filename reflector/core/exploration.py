"""Bounded epistemic exploration over observed symbolic states."""

from __future__ import annotations

import hashlib
import heapq
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

from .symbolic import ObjectState, Observation, Scene

StateKey = tuple[int, str, str]


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
    successful_role_replay: bool = False
    multicolor_click_objects: bool = False
    click_object_accommodation: bool = False
    productive_role_reuse: bool = False
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

    @property
    def uses_action_family_schema(self) -> bool:
        return self.hierarchical_action_fairness or self.starter_schemas

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
        self.pending_role = None
        grounding = self.pending_grounding
        self.pending_grounding = None
        relational_scheme = self.pending_relational_scheme
        self.pending_relational_scheme = None
        self.role_trials[role] += 1
        if len(before) != len(after) or not before or not after:
            return
        if any(len(left) != len(right) for left, right in zip(before, after)):
            return
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
            return ()
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
            ]
        ] = []
        for reference in rows:
            size = len(reference)
            reference_colors = tuple(item.color for item in reference)
            color_set = set(reference_colors)
            if len(color_set) != size:
                continue
            for selectors in rows:
                if len(selectors) != size:
                    continue
                if selectors[0].centroid[1] <= reference[0].centroid[1]:
                    continue
                if {item.color for item in selectors} != color_set:
                    continue
                selector_by_color = {item.color: item for item in selectors}
                for targets in rows:
                    if len(targets) != size or len({item.color for item in targets}) != 1:
                        continue
                    target_y = targets[0].centroid[1]
                    if not (
                        reference[0].centroid[1]
                        < target_y
                        < selectors[0].centroid[1]
                    ):
                        continue
                    actions: list[ActionToken] = []
                    for source, target in zip(reference, targets):
                        selector = selector_by_color[source.color]
                        actions.extend(
                            (
                                ActionToken(
                                    self.complex_action,
                                    (
                                        ("x", selector.centroid[0]),
                                        ("y", selector.centroid[1]),
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
                    commit_actions = sorted(
                        action
                        for action in observation.available_actions
                        if action not in {self.reset_action, self.complex_action}
                    )
                    if not commit_actions or any(token not in represented for token in actions):
                        continue
                    actions.append(ActionToken(commit_actions[0]))
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
                            tuple(actions),
                        )
                    )
        if not candidates:
            return ()
        return min(candidates, key=lambda item: item[0])[1]

    def _issue(
        self,
        state: StateKey,
        token: ActionToken,
        reason: str,
        scene: Scene,
    ) -> ExplorationChoice:
        self.level_interventions += 1
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
        if not self.productive_role_reuse or (
            self.level_failures < 2 and not self.pragmatic_disequilibrium_active
        ):
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
