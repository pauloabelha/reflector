"""Bounded epistemic exploration over observed symbolic states."""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

from .symbolic import Observation, Scene

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
    successful_program: tuple[ActionRole, ...] = ()
    program_cursor: int = 0
    level_failures: int = 0

    def observe(self, observation: Observation, scene: Scene) -> StateKey:
        """Record the outcome of the last issued intervention exactly once."""

        state = self._state_key(observation, scene)
        if self.current_level is None:
            self.current_level = observation.levels_completed
        elif observation.levels_completed > self.current_level:
            if self.successful_role_replay and self.episode_roles:
                self.successful_program = tuple(self.episode_roles)
                self.program_cursor = 0
            self.episode_roles.clear()
            self.current_level = observation.levels_completed
            self.level_failures = 0
        elif observation.state == "GAME_OVER":
            self.episode_roles.clear()
            self.program_cursor = 0
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
        self.current_state = None
        self.pending = None

    def select(
        self,
        observation: Observation,
        scene: Scene,
        legal_actions: tuple[int, ...],
    ) -> ExplorationChoice:
        """Choose an untried intervention or navigate to a known frontier."""

        state = self._state_key(observation, scene)
        if self.current_state != state:
            self.observe(observation, scene)
        tokens = self._tokens(observation, scene, legal_actions)
        if not tokens:
            raise ValueError("epistemic explorer has no represented legal action")
        self.tokens_by_state[state] = tokens

        replay = self._select_program_role(tokens, scene)
        if replay is not None:
            return self._issue(
                state,
                replay,
                "epistemic-frontier:replay-successful-action-role",
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
        if self.successful_role_replay:
            self.episode_roles.append(self._role(token, scene))
        self.pending = (state, token)
        return ExplorationChoice(token, reason)

    def _select_program_role(
        self,
        tokens: tuple[ActionToken, ...],
        scene: Scene,
    ) -> ActionToken | None:
        if not self.successful_role_replay or not self.successful_program:
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

    def _role(self, token: ActionToken, scene: Scene) -> ActionRole:
        if token.action_id != self.complex_action:
            return ActionRole(token.action_id)
        data = dict(token.data)
        x = data.get("x")
        y = data.get("y")
        if x is None or y is None:
            return ActionRole(token.action_id)
        point = (x, y)
        for item in scene.objects:
            min_x, min_y, _max_x, _max_y = item.bbox
            absolute_shape = {
                (min_x + local_x, min_y + local_y) for local_x, local_y in item.shape
            }
            if point in absolute_shape:
                return ActionRole(
                    token.action_id,
                    color=item.color,
                    area=item.area,
                    shape=item.shape,
                )
        return ActionRole(token.action_id)

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
            "frontier_states": sum(
                self._has_frontier(state) for state in self.tokens_by_state
            ),
        }
