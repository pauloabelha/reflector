"""Goal-blind exploration by bounded coherent intervention sweeps.

Ordinary breadth-first reset/replay search spends most of its budget replaying
one-step siblings.  Interactive visual worlds often expose their controllable
geometry only after a sustained run of one opaque intervention.  This search
executes each run once, retains every intermediate state as a possible turn
point, and then explores a different intervention from those turn points.

No action meaning, goal predicate, coordinate, palette, or game identity is
used.  Environment completion is the only success authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Any, Callable, Protocol, Sequence


class SweepError(RuntimeError):
    pass


class World(Protocol):
    def reset(self) -> Any: ...
    def step(self, opaque_action: int) -> Any: ...
    def key(self, observation: Any) -> str: ...
    def legal_actions(self, observation: Any) -> Sequence[int]: ...
    def completed(self, observation: Any) -> bool: ...
    def terminal(self, observation: Any) -> bool: ...


@dataclass(frozen=True, slots=True)
class SweepNode:
    path: tuple[int, ...]
    segments: tuple[tuple[int, int], ...]
    observation_key: str


@dataclass(frozen=True, slots=True)
class SweepEdge:
    source_key: str
    opaque_action: int
    repetition: int
    target_key: str
    changed: bool
    completed: bool
    terminal: bool


@dataclass(frozen=True, slots=True)
class SweepResult:
    solved: bool
    solution: tuple[int, ...]
    environment_actions: int
    reset_count: int
    discovered_states: int
    maximum_actions: int
    maximum_segments: int
    edges: tuple[SweepEdge, ...]
    stop_reason: str


def search(
    world: World,
    *,
    action_budget: int = 1_200,
    max_actions: int = 64,
    max_segments: int = 8,
    max_run: int = 16,
    max_states: int = 512,
    history_order: int = 2,
    priority: Callable[[Any, Any, tuple[int, ...], tuple[tuple[int, int], ...]], tuple] | None = None,
) -> SweepResult:
    if min(action_budget, max_actions, max_segments, max_run) < 1 or max_states < 2:
        raise SweepError("invalid sweep bound")
    if history_order < 0:
        raise SweepError("history order must be nonnegative")
    root = world.reset(); resets = 1; spent = 0; edges: list[SweepEdge] = []
    root_key = str(world.key(root))
    if world.completed(root):
        return SweepResult(True, (), 0, resets, 1, 0, 0, (), "root-complete")

    def epistemic(key: str, segments: tuple[tuple[int, int], ...]):
        return key, (() if not history_order else segments[-history_order:])

    root_node = SweepNode((), (), root_key)
    serial = 0
    queue = [((0, 0, 0, ()), serial, root_node)]
    known = {epistemic(root_key, ()): root_node}
    deepest_actions = 0; deepest_segments = 0; expanded = 0
    while queue and spent < action_budget and expanded < max_states:
        _rank, _serial, node = heapq.heappop(queue)
        expanded += 1
        if len(node.path) >= max_actions or len(node.segments) >= max_segments:
            continue
        observation = world.reset(); resets += 1
        replay_ok = True
        for action in node.path:
            if spent >= action_budget:
                replay_ok = False; break
            observation = world.step(action); spent += 1
            if world.terminal(observation) and not world.completed(observation):
                replay_ok = False; break
        if not replay_ok:
            continue
        legal = tuple(sorted(set(map(int, world.legal_actions(observation)))))
        previous_action = node.segments[-1][0] if node.segments else None
        for action in legal:
            # The parent sweep already enumerated every longer continuation of
            # its final intervention.  Only a turn can add information here.
            if action == previous_action:
                continue
            if spent >= action_budget:
                break
            branch = world.reset(); resets += 1
            valid = True
            for replay_action in node.path:
                if spent >= action_budget:
                    valid = False; break
                branch = world.step(replay_action); spent += 1
                if world.terminal(branch) and not world.completed(branch):
                    valid = False; break
            if not valid:
                continue
            source_key = str(world.key(branch)); prior_key = source_key; prior_observation = branch
            for repetition in range(1, min(max_run, max_actions - len(node.path)) + 1):
                if spent >= action_budget:
                    break
                branch = world.step(action); spent += 1
                target_key = str(world.key(branch)); done = bool(world.completed(branch)); dead = bool(world.terminal(branch))
                path = node.path + (action,) * repetition
                segments = node.segments + ((action, repetition),)
                changed = target_key != prior_key
                edges.append(SweepEdge(source_key, action, repetition, target_key, changed, done, dead))
                deepest_actions = max(deepest_actions, len(path)); deepest_segments = max(deepest_segments, len(segments))
                key = epistemic(target_key, segments)
                if done:
                    return SweepResult(True, path, spent, resets, len(known) + int(key not in known), deepest_actions, deepest_segments, tuple(edges), "environment-completion")
                if not dead and key not in known and len(known) < max_states * max_run:
                    child = SweepNode(path, segments, target_key); known[key] = child; serial += 1
                    # Prefer direct visual novelty, then fewer turns, then
                    # shorter trajectories.  No visual direction is preferred.
                    leading = priority(prior_observation, branch, path, segments) if priority is not None else (0 if changed else 1,)
                    if not isinstance(leading, tuple):
                        raise SweepError("priority must return a tuple")
                    rank = leading + (len(segments), len(path), segments)
                    heapq.heappush(queue, (rank, serial, child))
                if dead:
                    break
                prior_key = target_key; prior_observation = branch
    reason = "action-budget" if spent >= action_budget else "state-budget" if expanded >= max_states else "frontier-exhausted"
    return SweepResult(False, (), spent, resets, len(known), deepest_actions, deepest_segments, tuple(edges), reason)


__all__ = ["SweepEdge", "SweepError", "SweepNode", "SweepResult", "World", "search"]
