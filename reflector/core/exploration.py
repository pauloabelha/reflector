"""Bounded epistemic exploration over observed symbolic states."""

from __future__ import annotations

import hashlib
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
    learned_local_relation: dict[int, bool] = field(default_factory=dict)
    successful_schemes: dict[str, tuple[ActionRole, ...]] = field(
        default_factory=dict
    )
    parameterized_schemes: dict[str, ParameterizedScheme] = field(
        default_factory=dict
    )
    variation_cursors: dict[str, int] = field(default_factory=dict)
    variation_trials: Counter[str] = field(default_factory=Counter)
    successful_relational_schemes: dict[
        str, tuple[GroundedRole, ...]
    ] = field(default_factory=dict)
    relational_schemes: dict[str, RelationalScheme] = field(
        default_factory=dict
    )
    relational_cursors: dict[str, int] = field(default_factory=dict)
    relational_last: dict[str, GroundedRole] = field(default_factory=dict)
    relational_trials: Counter[str] = field(default_factory=Counter)
    last_relational_binding: dict[str, Any] = field(default_factory=dict)
    last_scheme_components: tuple[str, ...] = ()

    def arbitration_snapshot(self, selected_reason: str) -> tuple[dict[str, str], ...]:
        """Explain deterministic advisor priority without inventing prose."""

        order = []
        if self.constraint_first_role_replay:
            order.append("constraint-first-relation-repair")
        if self.successful_role_replay:
            order.append("successful-role-replay")
        if self.relational_scheme_binding:
            order.append("relational-scheme-binding")
        if self.productive_role_reuse:
            order.append("productive-role-reuse")
        if self.local_relation_solver and not self.constraint_first_role_replay:
            order.append("local-relation-repair")
        if self.parameterized_scheme_variation:
            order.append("parameterized-scheme-variation")
        if self.hierarchical_action_fairness:
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
                {"advisor": advisor, "status": "not_evaluated"}
                for advisor in order
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
                    self._learn_parameterized_variations(
                        self.successful_program
                    )
                if self.relational_scheme_binding:
                    self._learn_relational_variations(
                        tuple(
                            self.productive_groundings
                            or self.episode_groundings
                        )
                    )
            self.episode_roles.clear()
            self.episode_groundings.clear()
            self.productive_groundings.clear()
            self.relational_cursors = {
                scheme_id: 0 for scheme_id in self.relational_schemes
            }
            self.relational_last.clear()
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
            return
        before = self.pending_frame
        after = observation.frame
        self.pending_frame = ()
        role = self.pending_role
        self.pending_role = None
        grounding = self.pending_grounding
        self.pending_grounding = None
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
        if changed >= 4:
            self.role_responses[role] += 1
            if grounding is not None:
                self.productive_groundings.append(grounding)

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
            return self._issue(
                state,
                token,
                "epistemic-frontier:relational-scheme-binding:"
                f"{relational_scheme.operator}:"
                f"{relational_scheme.scheme_id}",
                scene,
            )

        productive = self._select_productive_role(tokens, scene, state)
        if productive is not None:
            return self._issue(
                state,
                productive,
                "epistemic-frontier:reuse-productive-action-role",
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

        if self.hierarchical_action_fairness:
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
                    if self.hierarchical_action_fairness
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

    def _issue(
        self,
        state: StateKey,
        token: ActionToken,
        reason: str,
        scene: Scene,
    ) -> ExplorationChoice:
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
            self.last_scheme_components = (
                self._starter_component(reason, grounding),
            )
        self.pending_frame = self.selection_frame
        self.pending_role = grounding.role
        self.pending_grounding = grounding
        self.pending = (state, token)
        return ExplorationChoice(token, reason)

    @staticmethod
    def _starter_component(
        reason: str,
        grounding: GroundedRole,
    ) -> str:
        if "repair-local-relation" in reason:
            schema_id = "repair-relation"
        elif "hierarchical-action-family" in reason:
            schema_id = "probe-action-family"
        elif grounding.centroid is not None:
            schema_id = "intervene-on-object"
        else:
            schema_id = "bounded-novelty"
        return f"scheme:starter:{schema_id}"

    def _select_productive_role(
        self,
        tokens: tuple[ActionToken, ...],
        scene: Scene,
        state: StateKey,
    ) -> ActionToken | None:
        if not self.productive_role_reuse or self.level_failures < 2:
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
        return repr((role.action_id, role.color, role.area, role.shape))

    @classmethod
    def _scheme_id(
        cls,
        prefix: str,
        roles: tuple[ActionRole, ...],
        *parts: str,
    ) -> str:
        raw = "|".join(
            (prefix, *parts, *(cls._role_key(role) for role in roles))
        )
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
            interleaved = tuple(
                role
                for pair in zip(base, program)
                for role in pair
            )
            shared_actions = {
                role.action_id for role in base
            } & {role.action_id for role in program}
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
            retained = dict(
                sorted(self.parameterized_schemes.items())[-64:]
            )
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
                action_slots = tuple(
                    item.role.action_id for item in base[:32]
                )
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
                key: self.relational_cursors.get(key, 0)
                for key in retained
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
        ):
            return None
        represented = tuple(
            (token, self._grounding(token, scene)) for token in tokens
        )
        schemes = sorted(
            self.relational_schemes.values(),
            key=lambda scheme: (
                -structure_scores.get(f"scheme:{scheme.scheme_id}", 0),
                self.relational_trials[scheme.scheme_id],
                scheme.scheme_id,
            ),
        )
        for scheme in schemes:
            if structure_scores.get(f"scheme:{scheme.scheme_id}", 0) < 0:
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
                    if represented_role == role
                    and self.attempts[(state, token)] == 0
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
        if self.hierarchical_action_fairness:
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
            == (item.bbox[2] - item.bbox[0] + 1)
            * (item.bbox[3] - item.bbox[1] + 1)
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
            == (item.bbox[2] - item.bbox[0] + 1)
            * (item.bbox[3] - item.bbox[1] + 1)
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
                    neighbor = origins.get(
                        (origin_x + dx * step, origin_y + dy * step)
                    )
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
            "learned_local_relations": len(self.learned_local_relation),
            "successful_schemes": len(self.successful_schemes),
            "parameterized_schemes": len(self.parameterized_schemes),
            "parameterized_scheme_trials": sum(self.variation_trials.values()),
            "starter_schemas": (
                len(STARTER_SCHEMA_SET) if self.starter_schemas else 0
            ),
            "starter_schema_ids": (
                [item.schema_id for item in STARTER_SCHEMA_SET]
                if self.starter_schemas
                else []
            ),
            "successful_relational_schemes": len(
                self.successful_relational_schemes
            ),
            "relational_schemes": len(self.relational_schemes),
            "relational_scheme_trials": sum(
                self.relational_trials.values()
            ),
            "last_relational_binding": dict(self.last_relational_binding),
            "frontier_states": sum(
                self._has_frontier(state) for state in self.tokens_by_state
            ),
        }
