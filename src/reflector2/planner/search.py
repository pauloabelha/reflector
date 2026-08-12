"""Deterministic bounded best-first composition over supported causal effects."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any

from .factorization import (
    ControlFactorization,
    ControlProblem,
    MilestoneShadow,
    PlannerConfig,
    ProspectiveStep,
    SearchResult,
)
from .milestones import milestone_satisfied


@dataclass(frozen=True, slots=True)
class _Node:
    state: Any
    steps: tuple[ProspectiveStep, ...]
    reached: tuple[MilestoneShadow, ...]
    minimum_confidence: float
    risk: int


def _preferred_progress(direction: str, before: float, after: float | None) -> float:
    if after is None:
        return float("-inf")
    if direction == "decrease":
        return before - after
    if direction == "increase":
        return after - before
    return -abs(after - before)


def _node_rank(problem: ControlProblem, node: _Node) -> tuple[Any, ...]:
    terminal = any(item.terminal for item in node.reached)
    useful = bool(node.reached)
    current = problem.measure(node.state, problem.active_observable)
    progress = _preferred_progress(
        problem.preferred_direction, problem.initial_value, current,
    )
    commands = tuple(step.command_id for step in node.steps)
    return (
        1 if terminal else 0,
        1 if useful else 0,
        progress,
        node.minimum_confidence,
        -node.risk,
        -len(node.steps),
        tuple(reversed(commands)),
    )


def _select_milestone(node: _Node) -> MilestoneShadow:
    return sorted(
        node.reached,
        key=lambda item: (not item.terminal, item.kind, item.shadow_id),
    )[0]


def search(problem: ControlProblem, config: PlannerConfig | None = None) -> SearchResult:
    """Search hypothetical successors without mutating any empirical object."""

    cfg = config or PlannerConfig()
    started = time.perf_counter()
    if not cfg.enabled:
        return SearchResult(
            "DISABLED", None, 0, 0, 0, 0, 0.0, cfg, "planner-disabled",
        )
    effects = tuple(sorted(
        (
            effect for effect in problem.effects
            if effect.support >= cfg.minimum_effect_support
            and effect.confidence >= cfg.minimum_effect_confidence
        ),
        key=lambda item: (
            item.command_id,
            json.dumps(item.command, sort_keys=True, separators=(",", ":")),
        ),
    ))
    if not effects:
        return SearchResult(
            "NO_PLAN", None, 0, 0, 0, 0,
            round((time.perf_counter() - started) * 1000, 3), cfg,
            "no-explicitly-supported-causal-effects",
        )
    initial_values = {
        item.shadow_id: problem.measure(problem.initial_state, item.observable)
        for item in problem.milestones
    }
    frontier = [_Node(problem.initial_state, (), (), 1.0, 0)]
    visited = {problem.state_key(problem.initial_state): 0}
    best: _Node | None = None
    expansions = generated = maximum_depth = 0
    frontier_peak = 1
    while frontier and expansions < cfg.max_expansions:
        frontier.sort(key=lambda node: _node_rank(problem, node), reverse=True)
        node = frontier.pop(0)
        if len(node.steps) >= cfg.max_depth:
            continue
        expansions += 1
        for effect in effects:
            successor = problem.transition(node.state, effect)
            if successor is None or not problem.invariants_hold(successor):
                continue
            depth = len(node.steps) + 1
            state_key = problem.state_key(successor)
            if visited.get(state_key, cfg.max_depth + 1) <= depth:
                continue
            visited[state_key] = depth
            generated += 1
            before = problem.measure(node.state, problem.active_observable)
            after = problem.measure(successor, problem.active_observable)
            reached = tuple(
                milestone for milestone in problem.milestones
                if milestone_satisfied(
                    milestone,
                    problem.measure(successor, milestone.observable),
                    initial_values[milestone.shadow_id],
                )
            )
            step = ProspectiveStep(
                depth=depth,
                command_id=effect.command_id,
                command=dict(effect.command),
                causal_support=effect.support,
                causal_confidence=effect.confidence,
                potential_before=before,
                potential_after=after,
                state_key=state_key,
            )
            child = _Node(
                successor, (*node.steps, step), reached,
                min(node.minimum_confidence, effect.confidence),
                node.risk + effect.risk,
            )
            maximum_depth = max(maximum_depth, depth)
            if reached and (best is None or _node_rank(problem, child) > _node_rank(problem, best)):
                best = child
            if depth < cfg.max_depth and not any(item.terminal for item in reached):
                frontier.append(child)
        if len(frontier) > cfg.max_frontier:
            frontier.sort(key=lambda node: _node_rank(problem, node), reverse=True)
            del frontier[cfg.max_frontier:]
        frontier_peak = max(frontier_peak, len(frontier))
    elapsed = round((time.perf_counter() - started) * 1000, 3)
    if best is None:
        return SearchResult(
            "NO_PLAN", None, expansions, generated, frontier_peak,
            maximum_depth, elapsed, cfg, "no-supported-composition-reached-a-milestone",
        )
    milestone = _select_milestone(best)
    factorization = ControlFactorization(
        explanation_id=problem.explanation_id,
        verb=problem.verb,
        milestone=milestone,
        steps=best.steps,
        protected_invariants=problem.protected_invariants,
        terminal_reached=any(item.terminal for item in best.reached),
        useful_milestone_reached=bool(best.reached),
    )
    return SearchResult(
        "PLAN_FOUND", factorization, expansions, generated, frontier_peak,
        maximum_depth, elapsed, cfg,
    )
