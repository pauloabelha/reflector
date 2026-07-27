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
    raise ValueError(f"unknown family: {family}")


def _budget(family: str) -> int:
    return {
        "invariant_control": 36,
        "contextual_control": 36,
        "rare_object_click": 24,
        "temporal_sequence": 128,
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


def run_validation(seed_count: int = 30, seed_start: int = 0) -> dict[str, object]:
    if seed_count < 2:
        raise ValueError("seed_count must be at least 2")
    if seed_start < 0:
        raise ValueError("seed_start must be non-negative")
    results = [
        run_one(policy, family, seed)
        for policy in POLICY_NAMES
        for family in FAMILIES
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
    abstraction = _bootstrap_difference(
        values("full", "efficiency"), values("no_abstraction", "efficiency")
    )
    contextual = mean(values("full", "completion", "contextual_control"))
    click = mean(values("full", "completion", "rare_object_click"))
    all_legal = all(item.legal for item in results)
    criteria = {
        "all_actions_legal": all_legal,
        "full_beats_random_completion_ci": full_random[1] > 0.0,
        "full_beats_score_only_completion_ci": full_score[1] > 0.0,
        "abstraction_improves_efficiency_ci": abstraction[1] > 0.0,
        "contextual_completion_at_least_0_75": contextual >= 0.75,
        "rare_click_completion_at_least_0_95": click >= 0.95,
    }
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
        "benchmark": "reflector_symbolic_diagnostics_v1",
        "claim_scope": "synthetic interactive mechanism tests; not an ARC score",
        "seed_start": seed_start,
        "seed_count": seed_count,
        "policies": list(POLICY_NAMES),
        "families": list(FAMILIES),
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
        },
        "criteria": criteria,
        "causal_thesis_supported": causal_supported,
        "verdict": verdict,
        "runs": [asdict(item) for item in results],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    payload["result_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return payload
