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
from itertools import product
from statistics import mean
from typing import Protocol

from .comparisons import SQUARE_SYMMETRIES, apply_matrix
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


class ModalGame:
    """Equal-history reachability test over a learned finite operator set."""

    family = "modal_reachability"
    _VECTORS = {1: (1, 0), 3: (0, 1)}

    def __init__(self, seed: int) -> None:
        rng = random.Random(seed)
        self._training = (1, 3, 1, 3)
        possible_displacements = [(5, 0), (0, 5), (4, 1), (1, 4)]
        impossible_displacements = [
            (-5, 0),
            (0, -5),
            (-4, -1),
            (-1, -4),
        ]
        layouts: list[
            tuple[tuple[int, int], tuple[int, int], bool]
        ] = []
        for dx, dy in possible_displacements + impossible_displacements:
            valid_starts = [
                (x, y)
                for y in range(1, 8)
                for x in range(1, 8)
                if 1 <= x + dx <= 7
                and 1 <= y + dy <= 7
                and (
                    (dx >= 0 and dy >= 0)
                    or (x >= 5 and y >= 5)
                )
            ]
            mover = rng.choice(valid_starts)
            layouts.append(
                (
                    mover,
                    (mover[0] + dx, mover[1] + dy),
                    dx >= 0 and dy >= 0,
                )
            )
        rng.shuffle(layouts)
        self._held_out = tuple(layouts)
        self._phase = 0
        self._mover = (1, 1)
        self._target: tuple[int, int] | None = None
        self._levels = 0
        self._won = False
        self.training_actions = (*self._training, 1, 5)
        self.training_progress: list[int] = []
        self.test_first_attempts = 0
        self.test_correct_first = 0
        self._last_attempted_phase = -1
        self.total_levels = 2 + len(self._held_out)
        self.oracle_actions = len(self.training_actions) + 20

    @property
    def _primitive_phase(self) -> bool:
        return self._phase < len(self._training)

    @property
    def _possible_demo_phase(self) -> bool:
        return self._phase == len(self._training)

    @property
    def _impossible_demo_phase(self) -> bool:
        return self._phase == len(self._training) + 1

    @property
    def _test_index(self) -> int:
        return self._phase - len(self._training) - 2

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
        elif self._possible_demo_phase:
            actions = (1,)
        elif self._impossible_demo_phase:
            actions = (5,)
        else:
            actions = (1, 3, 5)
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=actions,
            frame=self._frame(),
            levels_completed=self._levels,
        )

    def _move(self, action: int) -> None:
        dx, dy = self._VECTORS[action]
        self._mover = (
            min(8, max(0, self._mover[0] + dx)),
            min(8, max(0, self._mover[1] + dy)),
        )

    def _advance(self) -> None:
        self._levels += 1
        self._phase += 1
        if self._test_index == len(self._held_out):
            self._won = True
            return
        mover, target, _possible = self._held_out[self._test_index]
        self._mover, self._target = mover, target

    def step(self, decision: Decision) -> None:
        if self._primitive_phase:
            forced = self._training[self._phase]
            if decision.action_id != forced:
                return
            self._move(forced)
            self.training_progress.append(self._levels)
            self._phase += 1
            if self._possible_demo_phase:
                self._target = (5, 3)
            return
        if self._possible_demo_phase:
            if decision.action_id != 1:
                return
            self._move(1)
            self._levels += 1
            self.training_progress.append(self._levels)
            self._phase += 1
            self._mover, self._target = (4, 4), (1, 1)
            return
        if self._impossible_demo_phase:
            if decision.action_id != 5:
                return
            self._levels += 1
            self.training_progress.append(self._levels)
            self._phase += 1
            mover, demo_target, _possible = self._held_out[0]
            self._mover, self._target = mover, demo_target
            return

        target = self._target
        if target is None:
            return
        possible = self._held_out[self._test_index][2]
        before_distance = abs(self._mover[0] - target[0]) + abs(
            self._mover[1] - target[1]
        )
        after_distance = before_distance
        if decision.action_id in self._VECTORS:
            self._move(decision.action_id)
            after_distance = abs(self._mover[0] - target[0]) + abs(
                self._mover[1] - target[1]
            )
        if self._last_attempted_phase != self._phase:
            self.test_first_attempts += 1
            correct = (
                decision.action_id == 5
                if not possible
                else after_distance < before_distance
            )
            self.test_correct_first += int(correct)
            self._last_attempted_phase = self._phase
        if (not possible and decision.action_id == 5) or (
            possible and after_distance == 1
        ):
            self._advance()


class ComparisonTransferGame:
    """Infer withheld context operators from calibrated system comparisons."""

    family = "comparison_transfer"

    def __init__(self, seed: int) -> None:
        rng = random.Random(seed)
        vectors = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        rng.shuffle(vectors)
        self._canonical = {
            action: vector for action, vector in zip(range(1, 5), vectors)
        }
        self._calibration = next(
            (left, right)
            for left in range(1, 5)
            for right in range(left + 1, 5)
            if (
                self._canonical[left][0] * self._canonical[right][1]
                - self._canonical[left][1] * self._canonical[right][0]
            )
            != 0
        )
        withheld = tuple(
            action for action in range(1, 5) if action not in self._calibration
        )
        marker_colors = [1, 3, 4, 5, 6, 7, 11, 12, 13, 14, 15]
        rng.shuffle(marker_colors)
        self._canonical_marker = marker_colors.pop()
        self._negative_marker = marker_colors.pop()
        layouts: list[tuple[int, tuple[int, int, int, int], int]] = []
        for index in range(8):
            layouts.append(
                (
                    marker_colors[index],
                    rng.choice(SQUARE_SYMMETRIES),
                    rng.choice(withheld),
                )
            )
        rng.shuffle(layouts)
        self._held_out = tuple(layouts)
        self._negative_matrix = rng.choice(SQUARE_SYMMETRIES)
        self._phase = 0
        self._mover = (4, 4)
        self._target: tuple[int, int] | None = None
        self._marker_color = self._canonical_marker
        self._levels = 0
        self._won = False
        self.training_actions: list[int] = []
        self.training_progress: list[int] = []
        self.test_first_attempts = 0
        self.test_correct_first = 0
        self._last_attempted_phase = -1
        self.total_levels = 10
        self.oracle_actions = 32

    @property
    def _canonical_phase(self) -> bool:
        return self._phase < 4

    @property
    def _canonical_demo_phase(self) -> bool:
        return self._phase == 4

    @property
    def _negative_calibration_phase(self) -> bool:
        return self._phase in {5, 6}

    @property
    def _negative_exit_phase(self) -> bool:
        return self._phase == 7

    @property
    def _test_index(self) -> int:
        return (self._phase - 8) // 3

    @property
    def _test_subphase(self) -> int:
        return (self._phase - 8) % 3

    @property
    def decisive_withheld_action(self) -> int | None:
        if self._phase < 8 or self._test_subphase != 2:
            return None
        return self._held_out[self._test_index][2]

    @property
    def decisive_query_id(self) -> int | None:
        return (
            self._test_index
            if self.decisive_withheld_action is not None
            else None
        )

    def _effects(self) -> dict[int, tuple[int, int]]:
        if self._phase <= 4:
            return self._canonical
        if self._negative_calibration_phase or self._negative_exit_phase:
            output = {
                action: apply_matrix(self._negative_matrix, vector)
                for action, vector in self._canonical.items()
            }
            second = self._calibration[1]
            output[second] = (
                output[second][0] * 2,
                output[second][1] * 2,
            )
            return output
        matrix = self._held_out[self._test_index][1]
        return {
            action: apply_matrix(matrix, vector)
            for action, vector in self._canonical.items()
        }

    def oracle_audit(self) -> bool:
        """Prove the withheld action is required by every generated query."""

        left, right = self._calibration
        canonical_non_collinear = (
            self._canonical[left][0] * self._canonical[right][1]
            - self._canonical[left][1] * self._canonical[right][0]
        ) != 0
        if not canonical_non_collinear:
            return False
        for _marker, matrix, withheld in self._held_out:
            effects = {
                action: apply_matrix(matrix, vector)
                for action, vector in self._canonical.items()
            }
            start = (
                4 + effects[left][0] + effects[right][0],
                4 + effects[left][1] + effects[right][1],
            )
            target = (
                start[0] + 2 * effects[withheld][0],
                start[1] + 2 * effects[withheld][1],
            )
            reached = (
                start[0] + effects[withheld][0],
                start[1] + effects[withheld][1],
            )
            if abs(reached[0] - target[0]) + abs(
                reached[1] - target[1]
            ) != 1:
                return False
            for depth in range(1, 4):
                for sequence in product(self._calibration, repeat=depth):
                    position = start
                    for action in sequence:
                        position = (
                            position[0] + effects[action][0],
                            position[1] + effects[action][1],
                        )
                    if abs(position[0] - target[0]) + abs(
                        position[1] - target[1]
                    ) == 1:
                        return False
        negative = {
            action: apply_matrix(self._negative_matrix, vector)
            for action, vector in self._canonical.items()
        }
        negative[right] = (
            negative[right][0] * 2,
            negative[right][1] * 2,
        )
        negative_matches = [
            matrix
            for matrix in SQUARE_SYMMETRIES
            if all(
                apply_matrix(matrix, self._canonical[action])
                == negative[action]
                for action in self._calibration
            )
        ]
        return not negative_matches

    def _frame(self) -> tuple[tuple[int, ...], ...]:
        grid = [[0] * 9 for _ in range(9)]
        grid[0][0] = self._marker_color
        grid[0][1] = self._marker_color
        grid[self._mover[1]][self._mover[0]] = 2
        if self._target is not None:
            grid[self._target[1]][self._target[0]] = 8
        return tuple(tuple(row) for row in grid)

    def observation(self) -> Observation:
        if self._won:
            actions: tuple[int, ...] = ()
        elif self._canonical_phase:
            actions = (self._phase + 1,)
        elif self._canonical_demo_phase:
            actions = (1,)
        elif self._negative_calibration_phase:
            actions = (self._calibration[self._phase - 5],)
        elif self._negative_exit_phase:
            actions = (7,)
        elif self._test_subphase < 2:
            actions = (self._calibration[self._test_subphase],)
        else:
            actions = (1, 2, 3, 4)
        return Observation.create(
            state="WIN" if self._won else "NOT_FINISHED",
            available_actions=actions,
            frame=self._frame(),
            levels_completed=self._levels,
        )

    def _move(self, action: int) -> None:
        vector = self._effects()[action]
        self._mover = (
            min(8, max(0, self._mover[0] + vector[0])),
            min(8, max(0, self._mover[1] + vector[1])),
        )

    def _record_forced(self, action: int) -> None:
        self.training_actions.append(action)
        self.training_progress.append(self._levels)

    def _setup_negative(self) -> None:
        self._mover = (4, 4)
        self._target = None
        self._marker_color = self._negative_marker

    def _setup_held_out(self, index: int) -> None:
        if index == len(self._held_out):
            self._won = True
            return
        self._mover = (4, 4)
        self._target = None
        self._marker_color = self._held_out[index][0]

    def step(self, decision: Decision) -> None:
        if self._canonical_phase:
            forced = self._phase + 1
            if decision.action_id != forced:
                return
            self._move(forced)
            self._phase += 1
            self._record_forced(forced)
            if self._canonical_demo_phase:
                vector = self._canonical[1]
                self._target = (
                    self._mover[0] + 2 * vector[0],
                    self._mover[1] + 2 * vector[1],
                )
            return
        if self._canonical_demo_phase:
            if decision.action_id != 1:
                return
            self._move(1)
            self._levels += 1
            self._phase += 1
            self._record_forced(1)
            self._setup_negative()
            return
        if self._negative_calibration_phase:
            forced = self._calibration[self._phase - 5]
            if decision.action_id != forced:
                return
            self._move(forced)
            self._phase += 1
            self._record_forced(forced)
            return
        if self._negative_exit_phase:
            if decision.action_id != 7:
                return
            self._levels += 1
            self._phase += 1
            self._record_forced(7)
            self._setup_held_out(0)
            return
        if self._test_subphase < 2:
            forced = self._calibration[self._test_subphase]
            if decision.action_id != forced:
                return
            self._move(forced)
            self._phase += 1
            if self._test_subphase == 2:
                withheld = self._held_out[self._test_index][2]
                vector = self._effects()[withheld]
                self._target = (
                    self._mover[0] + 2 * vector[0],
                    self._mover[1] + 2 * vector[1],
                )
            return

        withheld = self._held_out[self._test_index][2]
        if self._last_attempted_phase != self._phase:
            self.test_first_attempts += 1
            self.test_correct_first += int(decision.action_id == withheld)
            self._last_attempted_phase = self._phase
        self._move(decision.action_id)
        target = self._target
        if target is None:
            return
        distance = abs(self._mover[0] - target[0]) + abs(
            self._mover[1] - target[1]
        )
        if distance != 1:
            return
        self._levels += 1
        self._phase += 1
        self._setup_held_out(self._test_index)


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
    modal_response_evidence: int = 0
    modal_actions_used: int = 0
    context_operators_observed: int = 0
    system_comparisons_constructed: int = 0
    inferred_context_operators: int = 0
    inferred_comparison_plans: int = 0
    comparison_rejection_abstained: bool = False
    observed_withheld_leaks: int = 0
    inferred_ready_before_intervention: int = 0
    environment_oracle_passed: bool = False

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

POLICY_NAMES_V5 = (
    "full",
    "modal",
    "no_modal",
    "score_only",
    "context_table",
    "seeded_random",
)

FAMILIES_V5 = ("modal_reachability",)

POLICY_NAMES_V6 = (
    "full",
    "comparison_transfer",
    "no_comparison_transfer",
    "score_only",
    "context_table",
    "seeded_random",
)

FAMILIES_V6 = ("comparison_transfer",)


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
    if name in {"modal", "no_modal"}:
        return SymbolicPolicy(
            MindConfig(
                enable_concepts=False,
                enable_experiments=False,
                enable_reflecting_abstraction=False,
                enable_accommodation=False,
                enable_modal_reasoning=name == "modal",
            )
        )
    if name in {"comparison_transfer", "no_comparison_transfer"}:
        return SymbolicPolicy(
            MindConfig(
                enable_concepts=False,
                enable_experiments=False,
                enable_reflecting_abstraction=False,
                enable_accommodation=False,
                enable_transformations=False,
                enable_modal_reasoning=False,
                enable_comparison_transfer=name == "comparison_transfer",
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
    if family == "modal_reachability":
        return ModalGame(seed)
    if family == "comparison_transfer":
        return ComparisonTransferGame(seed)
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
        "modal_reachability": 72,
        "comparison_transfer": 96,
    }[family]


def run_one(policy_name: str, family: str, seed: int) -> RunResult:
    policy = _policy(policy_name, seed)
    game = _game(family, seed)
    legal = True
    actions = 0
    observed_withheld_leaks = 0
    inferred_ready = 0
    seen_decisive_queries: set[int] = set()
    observation = game.observation()
    while observation.state != "WIN" and actions < _budget(family):
        decision = policy.choose_action(observation)
        query_id = getattr(game, "decisive_query_id", None)
        withheld = getattr(game, "decisive_withheld_action", None)
        if (
            isinstance(query_id, int)
            and isinstance(withheld, int)
            and query_id not in seen_decisive_queries
            and isinstance(policy, SymbolicPolicy)
        ):
            seen_decisive_queries.add(query_id)
            scene = policy.trace.steps[-1].scene
            domain_id = policy.mind.comparisons.domain(scene)
            if domain_id is not None:
                key = (domain_id, withheld)
                observed_withheld_leaks += int(
                    key in policy.mind.comparisons.observed_operators
                )
                inferred_ready += int(
                    key in policy.mind.comparisons.inferred_operators
                )
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
    modal_evidence = (
        sum(
            len(evidence)
            for evidence in (
                policy.mind.transformations.impossible_touching_actions.values()
            )
        )
        if isinstance(policy, SymbolicPolicy)
        and policy.mind.config.enable_modal_reasoning
        else 0
    )
    modal_actions = (
        sum(
            int(step.decision.reason.startswith("modal-"))
            for step in policy.trace.steps
        )
        if isinstance(policy, SymbolicPolicy)
        else 0
    )
    context_operators = (
        len(policy.mind.comparisons.observed_operators)
        if isinstance(policy, SymbolicPolicy)
        else 0
    )
    system_comparisons = (
        len(policy.mind.comparisons.comparisons)
        if isinstance(policy, SymbolicPolicy)
        else 0
    )
    inferred_operators = (
        len(policy.mind.comparisons.inferred_operators)
        if isinstance(policy, SymbolicPolicy)
        else 0
    )
    inferred_plans = (
        sum(
            int(
                step.decision.reason.startswith("comparison-transfer-plan:")
                and "inferred=()" not in step.decision.reason
            )
            for step in policy.trace.steps
        )
        if isinstance(policy, SymbolicPolicy)
        else 0
    )
    rejection_abstained = False
    if isinstance(policy, SymbolicPolicy):
        accepted_targets = {
            comparison.codomain
            for comparison in policy.mind.comparisons.comparisons.values()
        }
        rejected_only = {
            codomain
            for _domain, codomain in (
                policy.mind.comparisons.rejected_comparisons
            )
            if codomain not in accepted_targets
        }
        rejection_abstained = bool(rejected_only) and not any(
            item.domain_id in rejected_only
            for item in policy.mind.comparisons.inferred_operators.values()
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
        modal_evidence,
        modal_actions,
        context_operators,
        system_comparisons,
        inferred_operators,
        inferred_plans,
        rejection_abstained,
        observed_withheld_leaks,
        inferred_ready,
        bool(getattr(game, "oracle_audit", lambda: True)()),
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
    if suite not in {"v1", "v2", "v3", "v4", "v5", "v6"}:
        raise ValueError("suite must be v1, v2, v3, v4, v5, or v6")
    families = (
        FAMILIES
        if suite == "v1"
        else FAMILIES_V2
        if suite == "v2"
        else FAMILIES_V3
        if suite == "v3"
        else FAMILIES_V4
        if suite == "v4"
        else FAMILIES_V5
        if suite == "v5"
        else FAMILIES_V6
    )
    policies = (
        POLICY_NAMES
        if suite in {"v1", "v2"}
        else POLICY_NAMES_V3
        if suite == "v3"
        else POLICY_NAMES_V4
        if suite == "v4"
        else POLICY_NAMES_V5
        if suite == "v5"
        else POLICY_NAMES_V6
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
                "transformation composition, represented inverse partners, "
                "and finite comparison laws on synthetic interactions; not "
                "an ARC score"
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

    if suite == "v5":
        modal_effect = _bootstrap_difference(
            values("modal", "efficiency"),
            values("no_modal", "efficiency"),
        )
        intervention_accuracy = _bootstrap_difference(
            values("modal", "held_out_first_attempt_accuracy"),
            values("no_modal", "held_out_first_attempt_accuracy"),
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
            "modal_completion_at_least_0_95": mean(
                values("modal", "completion")
            )
            >= 0.95,
            "full_completion_at_least_0_95": mean(
                values("full", "completion")
            )
            >= 0.95,
            "modal_reasoning_improves_efficiency_ci": modal_effect[1] > 0.0,
            "modal_reasoning_improves_intervention_accuracy_ci": (
                intervention_accuracy[1] > 0.0
            ),
            "impossibility_response_is_evidence_grounded": mean(
                values("modal", "modal_response_evidence")
            )
            >= 1.0,
            "modal_response_is_operative": mean(
                values("modal", "modal_actions_used")
            )
            >= 4.0,
            "ablation_has_no_modal_side_channel": mean(
                values("no_modal", "modal_actions_used")
            )
            == 0.0,
        }
        v5_payload: dict[str, object] = {
            "benchmark": "reflector_symbolic_diagnostics_v5",
            "claim_scope": (
                "finite modal reachability used in synthetic control after "
                "equal training histories; not an ARC score"
            ),
            "seed_start": seed_start,
            "seed_count": seed_count,
            "policies": list(policies),
            "families": list(families),
            "aggregates": aggregates,
            "paired_differences": {
                "modal_minus_no_modal_efficiency": {
                    "mean": modal_effect[0],
                    "ci95": [modal_effect[1], modal_effect[2]],
                },
                "modal_minus_no_modal_intervention_accuracy": {
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
            v5_payload, sort_keys=True, separators=(",", ":")
        )
        v5_payload["result_sha256"] = hashlib.sha256(
            canonical.encode()
        ).hexdigest()
        return v5_payload

    if suite == "v6":
        comparison_effect = _bootstrap_difference(
            values("comparison_transfer", "efficiency"),
            values("no_comparison_transfer", "efficiency"),
        )
        intervention_accuracy = _bootstrap_difference(
            values(
                "comparison_transfer",
                "held_out_first_attempt_accuracy",
            ),
            values(
                "no_comparison_transfer",
                "held_out_first_attempt_accuracy",
            ),
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
            "independent_environment_oracle_passes": all(
                item.environment_oracle_passed for item in results
            ),
            "all_actions_legal": all(item.legal for item in results),
            "identical_forced_histories": all(
                len(items) == 1 for items in histories_by_seed.values()
            ),
            "comparison_completion_at_least_0_95": mean(
                values("comparison_transfer", "completion")
            )
            >= 0.95,
            "full_completion_at_least_0_90": mean(
                values("full", "completion")
            )
            >= 0.90,
            "comparison_improves_efficiency_ci": comparison_effect[1] > 0.0,
            "comparison_improves_intervention_accuracy_ci": (
                intervention_accuracy[1] > 0.0
            ),
            "withheld_effect_never_observed_before_intervention": (
                mean(
                    values(
                        "comparison_transfer",
                        "observed_withheld_leaks",
                    )
                )
                == 0.0
                and mean(
                    values(
                        "no_comparison_transfer",
                        "observed_withheld_leaks",
                    )
                )
                == 0.0
            ),
            "all_withheld_effects_inferred_before_intervention": mean(
                values(
                    "comparison_transfer",
                    "inferred_ready_before_intervention",
                )
            )
            == 8.0,
            "ablation_infers_no_withheld_effects": mean(
                values(
                    "no_comparison_transfer",
                    "inferred_ready_before_intervention",
                )
            )
            == 0.0,
            "inferred_comparison_plans_are_operative": mean(
                values("comparison_transfer", "inferred_comparison_plans")
            )
            >= 8.0,
            "negative_control_is_rejected": mean(
                values(
                    "comparison_transfer",
                    "comparison_rejection_abstained",
                )
            )
            == 1.0,
        }
        v6_payload: dict[str, object] = {
            "benchmark": "reflector_symbolic_diagnostics_v6",
            "claim_scope": (
                "causal transfer of withheld context-typed operator effects "
                "through evidenced finite comparisons; not an ARC score"
            ),
            "seed_start": seed_start,
            "seed_count": seed_count,
            "policies": list(policies),
            "families": list(families),
            "aggregates": aggregates,
            "paired_differences": {
                "comparison_minus_no_comparison_efficiency": {
                    "mean": comparison_effect[0],
                    "ci95": [
                        comparison_effect[1],
                        comparison_effect[2],
                    ],
                },
                "comparison_minus_no_comparison_intervention_accuracy": {
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
            v6_payload, sort_keys=True, separators=(",", ":")
        )
        v6_payload["result_sha256"] = hashlib.sha256(
            canonical.encode()
        ).hexdigest()
        return v6_payload

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
