"""Preregistered interactive diagnostics for the symbolic research thesis.

These environments are deliberately small and synthetic. They test mechanisms,
not ARC-AGI-3 accuracy, and their results must never be reported as an ARC
score. The deployed SymbolicPolicy is used without a benchmark-only adapter.
"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import asdict, dataclass
from statistics import mean
from typing import Protocol

from .mind import MindConfig
from .policy import SymbolicPolicy
from .symbolic import Decision, Observation


class BenchmarkPolicy(Protocol):
    def choose_action(self, observation: Observation) -> Decision: ...

    def observe(self, observation: Observation) -> object: ...


class DiagnosticGame(Protocol):
    family: str
    total_levels: int
    oracle_actions: int

    def observation(self) -> Observation: ...

    def step(self, decision: Decision) -> None: ...


def _marker_frame(marker: int, progress: int = 0) -> tuple[tuple[int, ...], ...]:
    positions = ((1, 1), (5, 1), (1, 5), (5, 5))
    grid = [[0] * 7 for _ in range(7)]
    x, y = positions[marker % len(positions)]
    grid[y][x] = 2
    for offset in range(progress):
        grid[3][2 + offset] = 4
    return tuple(tuple(row) for row in grid)


class ActionGame:
    """Repeated levels with either invariant or context-dependent controls."""

    def __init__(self, seed: int, contextual: bool) -> None:
        rng = random.Random(seed)
        self.family = "contextual_control" if contextual else "invariant_control"
        self.total_levels = 12
        self.oracle_actions = self.total_levels
        self._contexts = [index % 4 for index in range(self.total_levels)]
        rng.shuffle(self._contexts)
        actions = [1, 2, 3, 4]
        rng.shuffle(actions)
        self._mapping = tuple(actions)
        self._invariant = actions[0]
        self._contextual = contextual
        self._level = 0
        self._won = False

    def observation(self) -> Observation:
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=() if self._won else (1, 2, 3, 4),
            frame=(
                _marker_frame(self._contexts[-1])
                if self._won
                else _marker_frame(self._contexts[self._level])
            ),
            levels_completed=self._level,
        )

    def step(self, decision: Decision) -> None:
        context = self._contexts[self._level]
        target = self._mapping[context] if self._contextual else self._invariant
        if decision.action_id == target:
            self._level += 1
            self._won = self._level == self.total_levels


class ClickGame:
    """Levels solved by clicking the single rare-colored object."""

    family = "rare_object_click"

    def __init__(self, seed: int) -> None:
        rng = random.Random(seed)
        self.total_levels = 12
        self.oracle_actions = self.total_levels
        positions = [(x, y) for y in range(7) for x in range(7)]
        rng.shuffle(positions)
        self._targets = positions[: self.total_levels]
        self._level = 0
        self._won = False

    def _frame(self) -> tuple[tuple[int, ...], ...]:
        x, y = self._targets[min(self._level, self.total_levels - 1)]
        grid = [[0] * 7 for _ in range(7)]
        grid[y][x] = 7
        return tuple(tuple(row) for row in grid)

    def observation(self) -> Observation:
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=() if self._won else (6,),
            frame=self._frame(),
            levels_completed=self._level,
        )

    def step(self, decision: Decision) -> None:
        target = self._targets[self._level]
        data = decision.data_dict()
        if (
            decision.action_id == 6
            and data.get("x") == target[0]
            and data.get("y") == target[1]
        ):
            self._level += 1
            self._won = self._level == self.total_levels


class SequenceGame:
    """Levels require discovery and reuse of a three-action sequence."""

    family = "temporal_sequence"

    def __init__(self, seed: int) -> None:
        rng = random.Random(seed)
        sequence = [1, 2, 3]
        rng.shuffle(sequence)
        self._sequence = tuple(sequence)
        self.total_levels = 8
        self.oracle_actions = self.total_levels * len(self._sequence)
        self._level = 0
        self._progress = 0
        self._won = False

    def observation(self) -> Observation:
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=() if self._won else (1, 2, 3),
            frame=_marker_frame(self._level, self._progress),
            levels_completed=self._level,
        )

    def step(self, decision: Decision) -> None:
        if decision.action_id == self._sequence[self._progress]:
            self._progress += 1
            if self._progress == len(self._sequence):
                self._progress = 0
                self._level += 1
                self._won = self._level == self.total_levels
        else:
            self._progress = 0


def _novel_frame(
    position: tuple[int, int], color: int
) -> tuple[tuple[int, ...], ...]:
    grid = [[0] * 9 for _ in range(9)]
    grid[position[1]][position[0]] = color
    return tuple(tuple(row) for row in grid)


class NovelContextGame:
    """Invariant control over contexts not revisited within the game."""

    family = "novel_context_transfer"

    def __init__(self, seed: int) -> None:
        rng = random.Random(seed)
        positions = [(x, y) for y in range(1, 8) for x in range(1, 8)]
        rng.shuffle(positions)
        self._positions = positions[:16]
        actions = [1, 2, 3, 4]
        rng.shuffle(actions)
        self._targets = {2: actions[0], 3: actions[1]}
        self._colors = tuple(2 + index % 2 for index in range(16))
        self.total_levels = len(self._positions)
        self.oracle_actions = self.total_levels
        self._level = 0
        self._won = False

    def observation(self) -> Observation:
        position = self._positions[min(self._level, self.total_levels - 1)]
        color = self._colors[min(self._level, self.total_levels - 1)]
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=() if self._won else (1, 2, 3, 4),
            frame=_novel_frame(position, color),
            levels_completed=self._level,
        )

    def step(self, decision: Decision) -> None:
        if decision.action_id == self._targets[self._colors[self._level]]:
            self._level += 1
            self._won = self._level == self.total_levels


class TransferSequenceGame:
    """A recurring abstract procedure amid novel absolute layouts."""

    family = "procedure_transfer"

    def __init__(self, seed: int) -> None:
        rng = random.Random(seed)
        actions = [1, 2, 3, 4]
        rng.shuffle(actions)
        self._sequence = tuple(actions[:3])
        positions = [
            (1, 1),
            (4, 1),
            (7, 1),
            (1, 4),
            (7, 4),
            (1, 7),
            (4, 7),
            (7, 7),
        ]
        rng.shuffle(positions)
        self._markers = positions
        self.total_levels = len(positions)
        self.oracle_actions = self.total_levels * len(self._sequence)
        self._level = 0
        self._progress = 0
        self._won = False

    def _frame(self) -> tuple[tuple[int, ...], ...]:
        grid = [[0] * 9 for _ in range(9)]
        marker = self._markers[min(self._level, self.total_levels - 1)]
        grid[marker[1]][marker[0]] = 2
        for offset in range(self._progress):
            grid[4][3 + offset] = 4
        return tuple(tuple(row) for row in grid)

    def observation(self) -> Observation:
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=() if self._won else (1, 2, 3, 4),
            frame=self._frame(),
            levels_completed=self._level,
        )

    def step(self, decision: Decision) -> None:
        if decision.action_id == self._sequence[self._progress]:
            self._progress += 1
            if self._progress == len(self._sequence):
                self._progress = 0
                self._level += 1
                self._won = self._level == self.total_levels
        else:
            self._progress = 0


class AccommodationGame:
    """Equal-history construction followed by novel-context interventions.

    Training actions are forced, so every policy receives the same actions and
    level-progress sequence.  Barrier contexts share only a color predicate;
    layouts and incidental effects vary.  Test layouts never appeared during
    training.
    """

    family = "constructive_accommodation"

    def __init__(self, seed: int) -> None:
        rng = random.Random(seed)
        self._training = (
            (False, 1, True),
            (False, 2, False),
            (False, 1, True),
            (False, 2, False),
            (True, 1, False),
            (True, 2, True),
            (True, 1, False),
            (True, 2, True),
        )
        held_out = [False, True] * 4
        rng.shuffle(held_out)
        self._held_out = tuple(held_out)
        positions = [
            (x, y)
            for y in range(1, 8)
            for x in range(1, 8)
            if (x, y) not in {(4, 4), (7, 7)}
        ]
        rng.shuffle(positions)
        self._positions = tuple(
            positions[: len(self._training) + len(self._held_out)]
        )
        barrier_candidates = [
            (x, y) for y in range(1, 8) for x in range(1, 8)
        ]
        rng.shuffle(barrier_candidates)
        barrier_positions: list[tuple[int, int]] = []
        for mover in self._positions:
            reflected = (8 - mover[0], 8 - mover[1])
            barrier = next(
                candidate
                for candidate in barrier_candidates
                if candidate not in {mover, reflected}
                and candidate not in barrier_positions[-3:]
            )
            barrier_positions.append(barrier)
        self._barrier_positions = tuple(barrier_positions)
        self.training_actions = tuple(item[1] for item in self._training)
        self.training_progress: list[int] = []
        self.test_first_attempts = 0
        self.test_correct_first = 0
        self._last_attempted_phase = -1
        self.total_levels = sum(
            int(item[2]) for item in self._training
        ) + len(self._held_out)
        self.oracle_actions = len(self._training) + len(self._held_out)
        self._phase = 0
        self._levels = 0
        self._won = False

    @property
    def _training_phase(self) -> bool:
        return self._phase < len(self._training)

    def _barrier(self) -> bool:
        if self._training_phase:
            return self._training[self._phase][0]
        index = min(
            self._phase - len(self._training),
            len(self._held_out) - 1,
        )
        return self._held_out[index]

    def _frame(self) -> tuple[tuple[int, ...], ...]:
        index = min(self._phase, len(self._positions) - 1)
        x, y = self._positions[index]
        grid = [[0] * 9 for _ in range(9)]
        grid[y][x] = 2
        # A second moving object makes incidental transition signatures differ.
        grid[8 - y][8 - x] = 3
        if self._barrier():
            barrier_x, barrier_y = self._barrier_positions[index]
            grid[barrier_y][barrier_x] = 5
        return tuple(tuple(row) for row in grid)

    def observation(self) -> Observation:
        if self._won:
            actions: tuple[int, ...] = ()
        elif self._training_phase:
            actions = (self._training[self._phase][1],)
        else:
            actions = (1, 2)
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=actions,
            frame=self._frame(),
            levels_completed=self._levels,
        )

    def step(self, decision: Decision) -> None:
        if self._training_phase:
            _barrier, forced, succeeds = self._training[self._phase]
            if decision.action_id != forced:
                return
            if succeeds:
                self._levels += 1
            self.training_progress.append(self._levels)
            self._phase += 1
            return

        target = 2 if self._barrier() else 1
        if self._last_attempted_phase != self._phase:
            self.test_first_attempts += 1
            self.test_correct_first += int(decision.action_id == target)
            self._last_attempted_phase = self._phase
        if decision.action_id == target:
            self._levels += 1
            self._phase += 1
            self._won = self._phase == (
                len(self._training) + len(self._held_out)
            )


class TransformationGame:
    """Forced operator learning, one goal demonstration, then composition."""

    family = "transformation_composition"
    _VECTORS = {
        1: (1, 0),
        2: (-1, 0),
        3: (0, 1),
        4: (0, -1),
    }

    def __init__(self, seed: int) -> None:
        rng = random.Random(seed)
        self._training = (1, 2, 3, 4, 1, 2, 3, 4, 1)
        pairs: list[tuple[tuple[int, int], tuple[int, int]]] = []
        displacements = [
            (3, 0),
            (-3, 0),
            (0, 3),
            (0, -3),
            (2, 1),
            (-2, 1),
            (1, -2),
            (-1, -2),
        ]
        rng.shuffle(displacements)
        for dx, dy in displacements:
            valid_starts = [
                (x, y)
                for y in range(1, 8)
                for x in range(1, 8)
                if 1 <= x + dx <= 7 and 1 <= y + dy <= 7
            ]
            mover = rng.choice(valid_starts)
            pairs.append((mover, (mover[0] + dx, mover[1] + dy)))
        self._held_out = tuple(pairs)
        self._phase = 0
        self._mover = (4, 4)
        self._target: tuple[int, int] | None = None
        self._levels = 0
        self._won = False
        self.training_actions = (*self._training, 1)
        self.training_progress: list[int] = []
        self.test_first_attempts = 0
        self.test_correct_first = 0
        self._last_attempted_phase = -1
        self.total_levels = 1 + len(self._held_out)
        self.oracle_actions = len(self.training_actions) + sum(
            abs(mover[0] - target[0]) + abs(mover[1] - target[1]) - 1
            for mover, target in self._held_out
        )

    @property
    def _primitive_phase(self) -> bool:
        return self._phase < len(self._training)

    @property
    def _demo_phase(self) -> bool:
        return self._phase == len(self._training)

    @property
    def _test_index(self) -> int:
        return self._phase - len(self._training) - 1

    def _frame(self) -> tuple[tuple[int, ...], ...]:
        grid = [[0] * 9 for _ in range(9)]
        grid[self._mover[1]][self._mover[0]] = 2
        if self._target is not None:
            grid[self._target[1]][self._target[0]] = 8
        return tuple(tuple(row) for row in grid)

    def observation(self) -> Observation:
        if self._won:
            actions: tuple[int, ...] = ()
        elif self._primitive_phase:
            actions = (self._training[self._phase],)
        elif self._demo_phase:
            actions = (1,)
        else:
            actions = (1, 2, 3, 4)
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=actions,
            frame=self._frame(),
            levels_completed=self._levels,
        )

    def _move(self, action: int) -> None:
        dx, dy = self._VECTORS[action]
        self._mover = (
            min(7, max(1, self._mover[0] + dx)),
            min(7, max(1, self._mover[1] + dy)),
        )

    def step(self, decision: Decision) -> None:
        if self._primitive_phase:
            forced = self._training[self._phase]
            if decision.action_id != forced:
                return
            self._move(forced)
            self.training_progress.append(self._levels)
            self._phase += 1
            if self._demo_phase:
                # The primitive sequence ends at (5, 4).
                self._target = (7, 4)
            return

        if self._demo_phase:
            if decision.action_id != 1:
                return
            self._levels += 1
            self.training_progress.append(self._levels)
            self._phase += 1
            self._mover, self._target = self._held_out[0]
            return

        target = self._target
        if target is None:
            return
        before_distance = abs(self._mover[0] - target[0]) + abs(
            self._mover[1] - target[1]
        )
        dx, dy = self._VECTORS[decision.action_id]
        proposed = (
            min(7, max(1, self._mover[0] + dx)),
            min(7, max(1, self._mover[1] + dy)),
        )
        after_distance = abs(proposed[0] - target[0]) + abs(
            proposed[1] - target[1]
        )
        if self._last_attempted_phase != self._phase:
            self.test_first_attempts += 1
            self.test_correct_first += int(after_distance < before_distance)
            self._last_attempted_phase = self._phase
        self._mover = proposed
        if after_distance != 1:
            return
        self._levels += 1
        self._phase += 1
        if self._test_index == len(self._held_out):
            self._won = True
            return
        self._mover, self._target = self._held_out[self._test_index]


class SeededRandomPolicy:
    def __init__(self, seed: int) -> None:
        self._rng = random.Random(seed)

    def choose_action(self, observation: Observation) -> Decision:
        action = self._rng.choice(observation.available_actions)
        if action == 6:
            return Decision(
                6,
                (("x", self._rng.randrange(7)), ("y", self._rng.randrange(7))),
                "seeded-random",
            )
        return Decision(action, reason="seeded-random")

    def observe(self, observation: Observation) -> None:
        del observation


class ScoreOnlyPolicy:
    """Context-free empirical controller using only level advancement."""

    def __init__(self) -> None:
        self._trials: dict[int, int] = {}
        self._successes: dict[int, int] = {}
        self._previous: Decision | None = None
        self._level = 0

    def choose_action(self, observation: Observation) -> Decision:
        if self._previous is not None:
            action = self._previous.action_id
            self._trials[action] = self._trials.get(action, 0) + 1
            if observation.levels_completed > self._level:
                self._successes[action] = self._successes.get(action, 0) + 1
        self._level = observation.levels_completed
        action = max(
            observation.available_actions,
            key=lambda item: (
                (self._successes.get(item, 0) + 1)
                / (self._trials.get(item, 0) + 2),
                -self._trials.get(item, 0),
                -item,
            ),
        )
        self._previous = Decision(action, reason="score-only-bandit")
        return self._previous

    def observe(self, observation: Observation) -> None:
        del observation


class ContextTablePolicy:
    """Minimal recurrence baseline keyed by the complete visible frame."""

    def __init__(self) -> None:
        self._trials: dict[tuple[tuple[tuple[int, ...], ...], int], int] = {}
        self._successes: dict[tuple[tuple[tuple[int, ...], ...], int], int] = {}
        self._previous: tuple[tuple[tuple[int, ...], ...], int, int] | None = None

    def choose_action(self, observation: Observation) -> Decision:
        if self._previous is not None:
            frame, action, level = self._previous
            key = (frame, action)
            self._trials[key] = self._trials.get(key, 0) + 1
            if observation.levels_completed > level:
                self._successes[key] = self._successes.get(key, 0) + 1
        action = max(
            observation.available_actions,
            key=lambda item: (
                (
                    self._successes.get((observation.frame, item), 0) + 1
                )
                / (self._trials.get((observation.frame, item), 0) + 2),
                -self._trials.get((observation.frame, item), 0),
                -item,
            ),
        )
        self._previous = (
            observation.frame,
            action,
            observation.levels_completed,
        )
        return Decision(action, reason="context-table")

    def observe(self, observation: Observation) -> None:
        del observation


class RareColorPolicy:
    def choose_action(self, observation: Observation) -> Decision:
        action = min(observation.available_actions)
        if action == 6:
            x, y = SymbolicPolicy._symbolic_click(observation.frame)
            return Decision(6, (("x", x), ("y", y)), "rare-color")
        return Decision(action, reason="rare-color-fallback")

    def observe(self, observation: Observation) -> None:
        del observation


@dataclass(frozen=True, slots=True)
class RunResult:
    policy: str
    family: str
    seed: int
    actions: int
    levels_completed: int
    total_levels: int
    won: bool
    legal: bool
    oracle_actions: int
    training_actions: tuple[int, ...] = ()
    training_progress: tuple[int, ...] = ()
    held_out_first_attempt_accuracy: float = 0.0
    structures_constructed: int = 0
    target_condition_constructed: bool = False
    transformations_constructed: int = 0
    inverse_transformations: int = 0
    comparison_laws_passed: bool = False
    multi_step_plans: int = 0

    @property
    def completion(self) -> float:
        return self.levels_completed / self.total_levels

    @property
    def efficiency(self) -> float:
        return self.oracle_actions / self.actions if self.won else 0.0


POLICY_NAMES = (
    "full",
    "no_abstraction",
    "no_planning",
    "minimal_symbolic",
    "score_only",
    "context_table",
    "rare_color",
    "seeded_random",
)

FAMILIES = (
    "invariant_control",
    "contextual_control",
    "rare_object_click",
    "temporal_sequence",
)

FAMILIES_V2 = (
    "novel_context_transfer",
    "contextual_control",
    "rare_object_click",
    "procedure_transfer",
)

POLICY_NAMES_V3 = (
    "full",
    "constructive",
    "fixed_ontology",
    "score_only",
    "context_table",
    "seeded_random",
)

FAMILIES_V3 = ("constructive_accommodation",)

POLICY_NAMES_V4 = (
    "full",
    "transformation",
    "no_transformations",
    "score_only",
    "context_table",
    "seeded_random",
)

FAMILIES_V4 = ("transformation_composition",)


def _policy(name: str, seed: int) -> BenchmarkPolicy:
    if name == "full":
        return SymbolicPolicy()
    if name == "no_abstraction":
        return SymbolicPolicy(MindConfig(enable_reflecting_abstraction=False))
    if name == "no_planning":
        return SymbolicPolicy(MindConfig(enable_planning=False))
    if name == "minimal_symbolic":
        return SymbolicPolicy(
            MindConfig(
                enable_concepts=False,
                enable_counterfactual_pressure=False,
                enable_schema_complexity_pressure=False,
                enable_experiments=False,
                enable_planning=False,
                enable_reflecting_abstraction=False,
            )
        )
    if name == "score_only":
        return ScoreOnlyPolicy()
    if name in {"constructive", "fixed_ontology"}:
        return SymbolicPolicy(
            MindConfig(
                enable_concepts=False,
                enable_experiments=False,
                enable_planning=False,
                enable_reflecting_abstraction=False,
                enable_accommodation=name == "constructive",
            )
        )
    if name in {"transformation", "no_transformations"}:
        return SymbolicPolicy(
            MindConfig(
                enable_concepts=False,
                enable_experiments=False,
                enable_reflecting_abstraction=False,
                enable_accommodation=False,
                enable_transformations=name == "transformation",
            )
        )
    if name == "context_table":
        return ContextTablePolicy()
    if name == "rare_color":
        return RareColorPolicy()
    if name == "seeded_random":
        return SeededRandomPolicy(seed + 100_000)
    raise ValueError(f"unknown policy: {name}")


def _game(family: str, seed: int) -> DiagnosticGame:
    if family == "invariant_control":
        return ActionGame(seed, contextual=False)
    if family == "contextual_control":
        return ActionGame(seed, contextual=True)
    if family == "rare_object_click":
        return ClickGame(seed)
    if family == "temporal_sequence":
        return SequenceGame(seed)
    if family == "novel_context_transfer":
        return NovelContextGame(seed)
    if family == "procedure_transfer":
        return TransferSequenceGame(seed)
    if family == "constructive_accommodation":
        return AccommodationGame(seed)
    if family == "transformation_composition":
        return TransformationGame(seed)
    raise ValueError(f"unknown family: {family}")


def _budget(family: str) -> int:
    return {
        "invariant_control": 36,
        "contextual_control": 36,
        "rare_object_click": 24,
        "temporal_sequence": 128,
        "novel_context_transfer": 56,
        "procedure_transfer": 160,
        "constructive_accommodation": 40,
        "transformation_composition": 96,
    }[family]


def run_one(policy_name: str, family: str, seed: int) -> RunResult:
    policy = _policy(policy_name, seed)
    game = _game(family, seed)
    legal = True
    actions = 0
    observation = game.observation()
    while observation.state != "WIN" and actions < _budget(family):
        decision = policy.choose_action(observation)
        legal = legal and decision.action_id in observation.available_actions
        game.step(decision)
        actions += 1
        observation = game.observation()
    policy.observe(observation)
    training_actions = tuple(getattr(game, "training_actions", ()))
    training_progress = tuple(getattr(game, "training_progress", ()))
    test_attempts = int(getattr(game, "test_first_attempts", 0))
    test_correct = int(getattr(game, "test_correct_first", 0))
    structures = (
        len(policy.mind.reinforcement.accommodations)
        if isinstance(policy, SymbolicPolicy)
        and policy.mind.config.enable_accommodation
        else 0
    )
    target_condition = (
        any(
            item.action_id == 2
            and item.operation == "add"
            and item.proposition == "level_advanced"
            and "color_present(5)" in item.condition
            for item in (
                policy.mind.reinforcement.accommodation_history.values()
            )
        )
        if isinstance(policy, SymbolicPolicy)
        and policy.mind.config.enable_accommodation
        else False
    )
    transformations = (
        len(policy.mind.transformations.transformations)
        if isinstance(policy, SymbolicPolicy)
        and policy.mind.config.enable_transformations
        else 0
    )
    inverse_count = (
        sum(
            int(policy.mind.transformations.inverse(item) is not None)
            for item in policy.mind.transformations.transformations.values()
        )
        if isinstance(policy, SymbolicPolicy)
        and policy.mind.config.enable_transformations
        else 0
    )
    laws_passed = (
        policy.mind.transformations.law_report().passed
        if isinstance(policy, SymbolicPolicy)
        and policy.mind.config.enable_transformations
        else False
    )
    multi_step_plans = (
        sum(int(len(step.plan_actions) >= 2) for step in policy.trace.steps)
        if isinstance(policy, SymbolicPolicy)
        else 0
    )
    return RunResult(
        policy_name,
        family,
        seed,
        actions,
        observation.levels_completed,
        game.total_levels,
        observation.state == "WIN",
        legal,
        game.oracle_actions,
        training_actions,
        training_progress,
        test_correct / test_attempts if test_attempts else 0.0,
        structures,
        target_condition,
        transformations,
        inverse_count,
        laws_passed,
        multi_step_plans,
    )


def _bootstrap_difference(
    left: list[float], right: list[float], seed: int = 20260727
) -> tuple[float, float, float]:
    differences = [a - b for a, b in zip(left, right, strict=True)]
    rng = random.Random(seed)
    samples = sorted(
        mean(rng.choice(differences) for _ in differences) for _ in range(2000)
    )
    return (
        mean(differences),
        samples[int(len(samples) * 0.025)],
        samples[int(len(samples) * 0.975)],
    )


def run_validation(
    seed_count: int = 30,
    seed_start: int = 0,
    *,
    suite: str = "v1",
) -> dict[str, object]:
    if seed_count < 2:
        raise ValueError("seed_count must be at least 2")
    if seed_start < 0:
        raise ValueError("seed_start must be non-negative")
    if suite not in {"v1", "v2", "v3", "v4"}:
        raise ValueError("suite must be v1, v2, v3, or v4")
    families = (
        FAMILIES
        if suite == "v1"
        else FAMILIES_V2
        if suite == "v2"
        else FAMILIES_V3
        if suite == "v3"
        else FAMILIES_V4
    )
    policies = (
        POLICY_NAMES
        if suite in {"v1", "v2"}
        else POLICY_NAMES_V3
        if suite == "v3"
        else POLICY_NAMES_V4
    )
    results = [
        run_one(policy, family, seed)
        for policy in policies
        for family in families
        for seed in range(seed_start, seed_start + seed_count)
    ]
    grouped: dict[tuple[str, str], list[RunResult]] = {}
    for item in results:
        grouped.setdefault((item.policy, item.family), []).append(item)
    aggregates = {
        f"{policy}/{family}": {
            "completion": mean(item.completion for item in items),
            "win_rate": mean(float(item.won) for item in items),
            "mean_actions": mean(item.actions for item in items),
            "efficiency": mean(item.efficiency for item in items),
            "legal_rate": mean(float(item.legal) for item in items),
        }
        for (policy, family), items in sorted(grouped.items())
    }

    def values(policy: str, metric: str, family: str | None = None) -> list[float]:
        selected = [
            item
            for item in results
            if item.policy == policy and (family is None or item.family == family)
        ]
        selected.sort(key=lambda item: (item.family, item.seed))
        return [float(getattr(item, metric)) for item in selected]

    full_random = _bootstrap_difference(
        values("full", "completion"), values("seeded_random", "completion")
    )
    full_score = _bootstrap_difference(
        values("full", "completion"), values("score_only", "completion")
    )
    if suite == "v3":
        constructive = _bootstrap_difference(
            values("constructive", "efficiency"),
            values("fixed_ontology", "efficiency"),
        )
        intervention_accuracy = _bootstrap_difference(
            values("constructive", "held_out_first_attempt_accuracy"),
            values("fixed_ontology", "held_out_first_attempt_accuracy"),
        )
        histories = {
            (item.seed, item.training_actions, item.training_progress)
            for item in results
        }
        histories_by_seed = {
            seed: {
                (item.training_actions, item.training_progress)
                for item in results
                if item.seed == seed
            }
            for seed in range(seed_start, seed_start + seed_count)
        }
        criteria = {
            "all_actions_legal": all(item.legal for item in results),
            "identical_training_histories": (
                bool(histories)
                and all(len(items) == 1 for items in histories_by_seed.values())
            ),
            "constructive_completion_is_one": mean(
                values(
                    "constructive",
                    "completion",
                    "constructive_accommodation",
                )
            )
            == 1.0,
            "full_completion_at_least_0_95": mean(
                values("full", "completion", "constructive_accommodation")
            )
            >= 0.95,
            "accommodation_improves_efficiency_ci": constructive[1] > 0.0,
            "accommodation_improves_intervention_accuracy_ci": (
                intervention_accuracy[1] > 0.0
            ),
            "constructive_builds_evidenced_conditions": mean(
                values("constructive", "structures_constructed")
            )
            >= 2.0,
            "constructive_builds_target_condition": mean(
                values("constructive", "target_condition_constructed")
            )
            == 1.0,
            "fixed_ontology_builds_no_conditions": mean(
                values("fixed_ontology", "structures_constructed")
            )
            == 0.0,
        }
        v3_payload: dict[str, object] = {
            "benchmark": "reflector_symbolic_diagnostics_v3",
            "claim_scope": (
                "equal-history constructive accommodation mechanism test; "
                "not an ARC score"
            ),
            "seed_start": seed_start,
            "seed_count": seed_count,
            "policies": list(policies),
            "families": list(families),
            "aggregates": aggregates,
            "paired_differences": {
                "constructive_minus_fixed_ontology_efficiency": {
                    "mean": constructive[0],
                    "ci95": [constructive[1], constructive[2]],
                },
                "constructive_minus_fixed_ontology_intervention_accuracy": {
                    "mean": intervention_accuracy[0],
                    "ci95": [
                        intervention_accuracy[1],
                        intervention_accuracy[2],
                    ],
                },
            },
            "training_history_variants": len(histories),
            "criteria": criteria,
            "causal_thesis_supported": all(criteria.values()),
            "verdict": "supported" if all(criteria.values()) else "not_supported",
            "runs": [asdict(item) for item in results],
        }
        canonical = json.dumps(
            v3_payload, sort_keys=True, separators=(",", ":")
        )
        v3_payload["result_sha256"] = hashlib.sha256(
            canonical.encode()
        ).hexdigest()
        return v3_payload

    if suite == "v4":
        transformation_effect = _bootstrap_difference(
            values("transformation", "efficiency"),
            values("no_transformations", "efficiency"),
        )
        intervention_accuracy = _bootstrap_difference(
            values("transformation", "held_out_first_attempt_accuracy"),
            values("no_transformations", "held_out_first_attempt_accuracy"),
        )
        histories_by_seed = {
            seed: {
                (item.training_actions, item.training_progress)
                for item in results
                if item.seed == seed
            }
            for seed in range(seed_start, seed_start + seed_count)
        }
        criteria = {
            "all_actions_legal": all(item.legal for item in results),
            "identical_training_histories": all(
                len(items) == 1 for items in histories_by_seed.values()
            ),
            "transformation_completion_at_least_0_95": mean(
                values("transformation", "completion")
            )
            >= 0.95,
            "full_completion_at_least_0_95": mean(
                values("full", "completion")
            )
            >= 0.95,
            "transformations_improve_efficiency_ci": (
                transformation_effect[1] > 0.0
            ),
            "transformations_improve_intervention_accuracy_ci": (
                intervention_accuracy[1] > 0.0
            ),
            "four_primitive_transformations_constructed": mean(
                values("transformation", "transformations_constructed")
            )
            == 4.0,
            "all_primitives_have_inverses": mean(
                values("transformation", "inverse_transformations")
            )
            == 4.0,
            "typed_comparison_laws_pass": mean(
                values("transformation", "comparison_laws_passed")
            )
            == 1.0,
            "multi_step_compositions_are_operative": mean(
                values("transformation", "multi_step_plans")
            )
            >= 1.0,
        }
        v4_payload: dict[str, object] = {
            "benchmark": "reflector_symbolic_diagnostics_v4",
            "claim_scope": (
                "transformation composition, reversal, and finite comparison "
                "laws on synthetic interactions; not an ARC score"
            ),
            "seed_start": seed_start,
            "seed_count": seed_count,
            "policies": list(policies),
            "families": list(families),
            "aggregates": aggregates,
            "paired_differences": {
                "transformation_minus_no_transformations_efficiency": {
                    "mean": transformation_effect[0],
                    "ci95": [
                        transformation_effect[1],
                        transformation_effect[2],
                    ],
                },
                "transformation_minus_no_transformations_intervention_accuracy": {
                    "mean": intervention_accuracy[0],
                    "ci95": [
                        intervention_accuracy[1],
                        intervention_accuracy[2],
                    ],
                },
            },
            "criteria": criteria,
            "causal_thesis_supported": all(criteria.values()),
            "verdict": "supported" if all(criteria.values()) else "not_supported",
            "runs": [asdict(item) for item in results],
        }
        canonical = json.dumps(
            v4_payload, sort_keys=True, separators=(",", ":")
        )
        v4_payload["result_sha256"] = hashlib.sha256(
            canonical.encode()
        ).hexdigest()
        return v4_payload

    abstraction = _bootstrap_difference(
        values("full", "efficiency"), values("no_abstraction", "efficiency")
    )
    contextual = mean(values("full", "completion", "contextual_control"))
    click = mean(values("full", "completion", "rare_object_click"))
    procedure_family = (
        "temporal_sequence" if suite == "v1" else "procedure_transfer"
    )
    temporal = mean(values("full", "completion", procedure_family))
    planning = _bootstrap_difference(
        values("full", "efficiency", procedure_family),
        values("no_planning", "efficiency", procedure_family),
    )
    transfer = (
        _bootstrap_difference(
            values("full", "efficiency", "novel_context_transfer"),
            values("no_abstraction", "efficiency", "novel_context_transfer"),
        )
        if suite == "v2"
        else (0.0, 0.0, 0.0)
    )
    all_legal = all(item.legal for item in results)
    criteria = {
        "all_actions_legal": all_legal,
        "full_beats_random_completion_ci": full_random[1] > 0.0,
        "full_beats_score_only_completion_ci": full_score[1] > 0.0,
        "abstraction_improves_efficiency_ci": abstraction[1] > 0.0,
        "contextual_completion_at_least_0_75": contextual >= 0.75,
        "rare_click_completion_at_least_0_95": click >= 0.95,
    }
    if suite == "v2":
        criteria.update(
            {
                "procedure_completion_at_least_0_90": temporal >= 0.90,
                "planning_improves_procedure_efficiency_ci": planning[1] > 0.0,
                "abstraction_improves_novel_transfer_efficiency_ci": (
                    transfer[1] > 0.0
                ),
            }
        )
    causal_supported = all(
        criteria[name]
        for name in (
            "full_beats_random_completion_ci",
            "full_beats_score_only_completion_ci",
            "abstraction_improves_efficiency_ci",
            "contextual_completion_at_least_0_75",
        )
    )
    verdict = (
        "supported"
        if all(criteria.values())
        else "mixed"
        if all_legal
        and criteria["full_beats_random_completion_ci"]
        and criteria["rare_click_completion_at_least_0_95"]
        else "not_supported"
    )
    payload: dict[str, object] = {
        "benchmark": f"reflector_symbolic_diagnostics_{suite}",
        "claim_scope": "synthetic interactive mechanism tests; not an ARC score",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "policies": list(policies),
        "families": list(families),
        "aggregates": aggregates,
        "paired_differences": {
            "full_minus_seeded_random_completion": {
                "mean": full_random[0],
                "ci95": [full_random[1], full_random[2]],
            },
            "full_minus_score_only_completion": {
                "mean": full_score[0],
                "ci95": [full_score[1], full_score[2]],
            },
            "full_minus_no_abstraction_efficiency": {
                "mean": abstraction[0],
                "ci95": [abstraction[1], abstraction[2]],
            },
            "full_minus_no_planning_procedure_efficiency": {
                "mean": planning[0],
                "ci95": [planning[1], planning[2]],
            },
            "full_minus_no_abstraction_novel_transfer_efficiency": {
                "mean": transfer[0],
                "ci95": [transfer[1], transfer[2]],
            },
        },
        "criteria": criteria,
        "causal_thesis_supported": causal_supported,
        "verdict": verdict,
        "runs": [asdict(item) for item in results],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["result_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload
