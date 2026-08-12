"""Goal-respecting deterministic search over supported causal factorizations.

All states, paths, and prospects in this module are hypothetical.  The module
has no evidence or environment interface and returns first-command-only
control structure through the ordinary planner contract.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any

from .factorization import (
    ControlFactorization,
    ControlProblem,
    GoalProspect,
    MilestoneShadow,
    PlannerConfig,
    ProspectiveStep,
    SearchResult,
    SupportedCausalEffect,
)
from .search import search as local_milestone_search


TOLERANCE = 0.01


@dataclass(frozen=True, slots=True)
class _Path:
    state: Any
    steps: tuple[ProspectiveStep, ...]
    minimum_support: int
    minimum_confidence: float
    risk: int

    @property
    def first_command_id(self) -> str:
        return self.steps[0].command_id


def _orientation(direction: str, before: float | None, after: float | None) -> str:
    if before is None or after is None:
        return "open"
    delta = after - before
    if abs(delta) <= TOLERANCE:
        return "stable"
    preferred = delta < 0 if direction == "decrease" else delta > 0
    if direction == "maintain":
        preferred = False
    return "preferred" if preferred else "adverse"


def _terminal_reached(problem: ControlProblem, state: Any) -> bool:
    contract = problem.goal_contract
    if contract is None:
        return False
    value = problem.measure(state, contract.contributor_observable)
    target = contract.contributor_target
    if value is None:
        return False
    if contract.contributor_relation == "reached":
        return target is not None and abs(value - target) <= TOLERANCE
    if contract.contributor_relation == "minimum":
        return target is not None and value <= target + TOLERANCE
    if contract.contributor_relation == "maximum":
        return target is not None and value >= target - TOLERANCE
    return False


def _terminal_milestone(problem: ControlProblem) -> MilestoneShadow:
    contract = problem.goal_contract
    assert contract is not None
    matching = [
        item for item in problem.milestones
        if item.observable == contract.contributor_observable and item.terminal
    ]
    if matching:
        return sorted(matching, key=lambda item: (item.kind, item.shadow_id))[0]
    return MilestoneShadow(
        shadow_id=f"goal-contract-terminal:{contract.contract_id}",
        kind="GoalContractVerbTerminal",
        observable=contract.contributor_observable,
        relation="reached",
        target=contract.contributor_target,
        terminal=True,
        preserves=problem.protected_invariants,
        open_ports=(),
    )


def _prospect(
    problem: ControlProblem,
    config: PlannerConfig,
    paths: tuple[_Path, ...],
    *,
    depth_offset: int = 0,
    orientation: str = "open",
    reached: bool = False,
) -> GoalProspect:
    retained = paths[: config.max_goal_factorizations]
    best_depth = (
        min(len(path.steps) - depth_offset for path in retained)
        if retained else (0 if reached else None)
    )
    best = retained[0] if retained else None
    return GoalProspect(
        terminal_status=(
            "reached" if reached else "reachable" if retained
            else "unreachable-with-current-model"
        ),
        best_supported_depth=best_depth,
        terminal_reaching_factorizations=len(retained),
        minimum_edge_support=best.minimum_support if best else None,
        minimum_edge_confidence=(
            round(best.minimum_confidence, 6) if best else None
        ),
        unresolved_preconditions=problem.unresolved_requirements,
        protected_invariants=problem.protected_invariants,
        identity_risk=problem.identity_risk,
        expected_local_verb_orientation=orientation,
        search_budget_basis=config.document(),
        option_preserving_first_commands=len({path.first_command_id for path in retained}),
    )


def _path_rank(
    problem: ControlProblem,
    path: _Path,
    first_command_path_count: int,
) -> tuple[Any, ...]:
    first = path.steps[0]
    local_orientation = _orientation(
        problem.preferred_direction,
        first.potential_before,
        first.potential_after,
    )
    # This is a transparent dominance order rather than a weighted reward.
    # Once a supported terminal factorization exists, weakest-link model
    # quality and unresolved risk precede path length; local verb orientation
    # is only a later tie-break.
    return (
        1 if problem.goal_contract and problem.goal_contract.status == "SUPPORTED" else 0,
        path.minimum_support,
        path.minimum_confidence,
        -path.risk,
        -len(path.steps),
        first_command_path_count,
        1 if local_orientation == "preferred" else 0,
        1 if local_orientation == "stable" else 0,
        tuple(reversed(tuple(step.command_id for step in path.steps))),
    )


def _no_plan(
    config: PlannerConfig,
    started: float,
    reason: str,
    *,
    expansions: int,
    generated: int,
    frontier_peak: int,
    maximum_depth: int,
    prospect: GoalProspect,
) -> SearchResult:
    return SearchResult(
        status="NO_PLAN",
        factorization=None,
        expansions=expansions,
        generated=generated,
        frontier_peak=frontier_peak,
        maximum_depth_reached=maximum_depth,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
        config=config,
        reason=reason,
        current_goal_prospect=prospect,
    )


def search(problem: ControlProblem, config: PlannerConfig | None = None) -> SearchResult:
    """Find bounded supported paths to the active contract's verb terminal."""

    cfg = config or PlannerConfig()
    started = time.perf_counter()
    contract = problem.goal_contract
    if contract is None or contract.status not in {"OPEN", "SUPPORTED"}:
        # With GoalProspect disabled, preserve existing bounded-search behavior.
        return local_milestone_search(problem, cfg)
    if contract.contributor_verb != problem.verb:
        empty = _prospect(problem, cfg, ())
        return _no_plan(
            cfg, started, "goal-contract-does-not-match-active-verb",
            expansions=0, generated=0, frontier_peak=0, maximum_depth=0,
            prospect=empty,
        )
    if not cfg.enabled:
        empty = _prospect(problem, cfg, ())
        return SearchResult(
            "DISABLED", None, 0, 0, 0, 0, 0.0, cfg, "planner-disabled",
            current_goal_prospect=empty,
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
        empty = _prospect(problem, cfg, ())
        return _no_plan(
            cfg, started, "no-explicitly-supported-causal-effects",
            expansions=0, generated=0, frontier_peak=0, maximum_depth=0,
            prospect=empty,
        )

    initial_reached = _terminal_reached(problem, problem.initial_state)
    if initial_reached:
        current = _prospect(problem, cfg, (), reached=True)
        return _no_plan(
            cfg, started, "goal-contract-verb-terminal-already-reached",
            expansions=0, generated=0, frontier_peak=0, maximum_depth=0,
            prospect=current,
        )

    frontier = [_Path(problem.initial_state, (), 2**31 - 1, 1.0, 0)]
    visited: dict[tuple[str, str], int] = {}
    terminals: list[_Path] = []
    expansions = generated = maximum_depth = 0
    frontier_peak = 1
    while frontier and expansions < cfg.max_expansions:
        frontier.sort(key=lambda path: (
            -len(path.steps),
            path.minimum_support,
            path.minimum_confidence,
            -path.risk,
            tuple(reversed(tuple(step.command_id for step in path.steps))),
        ), reverse=True)
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
            first_command = node.first_command_id if node.steps else effect.command_id
            visit_key = (state_key, first_command)
            if visited.get(visit_key, cfg.max_depth + 1) <= depth:
                continue
            visited[visit_key] = depth
            generated += 1
            before = problem.measure(node.state, problem.active_observable)
            after = problem.measure(successor, problem.active_observable)
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
            child = _Path(
                successor,
                (*node.steps, step),
                min(node.minimum_support, effect.support),
                min(node.minimum_confidence, effect.confidence),
                node.risk + effect.risk,
            )
            maximum_depth = max(maximum_depth, depth)
            if _terminal_reached(problem, successor):
                terminals.append(child)
                continue
            if depth < cfg.max_depth:
                frontier.append(child)
        if len(frontier) > cfg.max_frontier:
            # Apply the same deterministic dominance order before enforcing
            # the hard frontier cap; insertion order must not decide which
            # hypothetical routes survive the budget.
            frontier.sort(key=lambda path: (
                -len(path.steps),
                path.minimum_support,
                path.minimum_confidence,
                -path.risk,
                tuple(reversed(tuple(step.command_id for step in path.steps))),
            ), reverse=True)
            frontier = frontier[: cfg.max_frontier]
        frontier_peak = max(frontier_peak, len(frontier))

    counts: dict[str, int] = {}
    for path in terminals:
        counts[path.first_command_id] = counts.get(path.first_command_id, 0) + 1
    terminals.sort(
        key=lambda path: _path_rank(problem, path, counts[path.first_command_id]),
        reverse=True,
    )
    retained = tuple(terminals[: cfg.max_goal_factorizations])
    current = _prospect(problem, cfg, retained)
    if not retained:
        return _no_plan(
            cfg, started, "no-supported-factorization-reached-goal-contract-verb-terminal",
            expansions=expansions, generated=generated, frontier_peak=frontier_peak,
            maximum_depth=maximum_depth, prospect=current,
        )

    selected = retained[0]
    first = selected.steps[0]
    orientation = _orientation(
        problem.preferred_direction,
        first.potential_before,
        first.potential_after,
    )
    same_first = tuple(
        path for path in retained if path.first_command_id == selected.first_command_id
    )
    successor = _prospect(
        problem,
        cfg,
        same_first,
        depth_offset=1,
        orientation=orientation,
        reached=len(selected.steps) == 1,
    )
    improvement = (
        "enables-terminal-factorization" if orientation == "adverse"
        else "terminal-reached" if len(selected.steps) == 1
        else "terminal-depth-decreased"
    )
    factorization = ControlFactorization(
        explanation_id=problem.explanation_id,
        verb=problem.verb,
        milestone=_terminal_milestone(problem),
        steps=selected.steps,
        protected_invariants=problem.protected_invariants,
        terminal_reached=True,
        useful_milestone_reached=True,
    )
    return SearchResult(
        status="PLAN_FOUND",
        factorization=factorization,
        expansions=expansions,
        generated=generated,
        frontier_peak=frontier_peak,
        maximum_depth_reached=maximum_depth,
        elapsed_ms=round((time.perf_counter() - started) * 1000, 3),
        config=cfg,
        current_goal_prospect=current,
        successor_goal_prospect=successor,
        prospect_improvement_kind=improvement,
    )


@dataclass(frozen=True, slots=True)
class ProspectPlanner:
    """Goal-respecting causal-factorization backend."""

    name: str = "prospect-planner-v0"

    def search(self, problem: ControlProblem, config: PlannerConfig) -> SearchResult:
        return search(problem, config)
