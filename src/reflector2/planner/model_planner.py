"""Model-guided planner whose proposals receive deterministic validation."""

from __future__ import annotations

from dataclasses import dataclass
import json
import time
from typing import Any

from .factorization import (
    ControlFactorization,
    ControlProblem,
    PlannerConfig,
    ProspectiveStep,
    SearchResult,
)
from .milestones import milestone_satisfied
from .model import MODEL_PROPOSAL_PROTOCOL, PlanningModel, PlanningModelError


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, sort_keys=True, default=str))


def _progress(direction: str, initial: float, current: float | None) -> float:
    if current is None:
        return float("-inf")
    if direction == "decrease":
        return initial - current
    if direction == "increase":
        return current - initial
    return -abs(current - initial)


def _no_plan(
    config: PlannerConfig, started: float, reason: str, *, expansions: int = 0,
) -> SearchResult:
    return SearchResult(
        "NO_PLAN", None, expansions, expansions, min(expansions, 1), expansions,
        round((time.perf_counter() - started) * 1000, 3), config, reason,
    )


@dataclass(frozen=True, slots=True)
class ModelPlanner:
    """Interchangeable backend: model proposes, generic simulator disposes."""

    model: PlanningModel
    max_problems_per_decision: int = 1

    @property
    def name(self) -> str:
        return f"model-validated-v0:{self.model.name}"

    def search(self, problem: ControlProblem, config: PlannerConfig) -> SearchResult:
        started = time.perf_counter()
        if not config.enabled:
            return SearchResult(
                "DISABLED", None, 0, 0, 0, 0, 0.0, config, "planner-disabled",
            )
        effects = {
            effect.command_id: effect
            for effect in problem.effects
            if effect.support >= config.minimum_effect_support
            and effect.confidence >= config.minimum_effect_confidence
        }
        if not effects:
            return _no_plan(config, started, "no-explicitly-supported-causal-effects")
        model_problem = {
            "protocol": MODEL_PROPOSAL_PROTOCOL,
            "explanation_id": problem.explanation_id,
            "verb": problem.verb,
            "active_observable": problem.active_observable,
            "preferred_direction": problem.preferred_direction,
            "initial_value": problem.initial_value,
            "initial_state": _json_safe(
                problem.model_view if problem.model_view is not None else problem.initial_state
            ),
            "supported_effects": [
                {
                    "command_id": effect.command_id,
                    "command": _json_safe(effect.command),
                    "actor_delta": list(effect.actor_delta),
                    "target_delta": list(effect.target_delta),
                    "support": effect.support,
                    "confidence": effect.confidence,
                    "risk": effect.risk,
                }
                for effect in sorted(effects.values(), key=lambda item: item.command_id)
            ],
            "milestone_shadows": [item.document() for item in problem.milestones],
            "protected_invariants": list(problem.protected_invariants),
            "hard_limits": config.document(),
        }
        try:
            proposal = self.model.propose(model_problem)
        except PlanningModelError as error:
            return _no_plan(config, started, str(error))
        if not proposal.command_ids:
            return _no_plan(config, started, "model-returned-empty-composition")
        if len(proposal.command_ids) > config.max_depth:
            return _no_plan(config, started, "model-composition-exceeds-depth-budget")
        if len(proposal.command_ids) > config.max_expansions:
            return _no_plan(config, started, "model-composition-exceeds-expansion-budget")
        if proposal.milestone_shadow_id is not None and proposal.milestone_shadow_id not in {
            item.shadow_id for item in problem.milestones
        }:
            return _no_plan(config, started, "model-selected-unknown-milestone")

        initial_values = {
            item.shadow_id: problem.measure(problem.initial_state, item.observable)
            for item in problem.milestones
        }
        state = problem.initial_state
        steps: list[ProspectiveStep] = []
        best: tuple[tuple[Any, ...], tuple[ProspectiveStep, ...], tuple[Any, ...]] | None = None
        minimum_confidence = 1.0
        total_risk = 0
        for depth, command_id in enumerate(proposal.command_ids, start=1):
            effect = effects.get(command_id)
            if effect is None:
                return _no_plan(
                    config, started, "model-proposed-unsupported-command",
                    expansions=depth - 1,
                )
            successor = problem.transition(state, effect)
            if successor is None:
                return _no_plan(
                    config, started, "model-proposed-inapplicable-transition",
                    expansions=depth,
                )
            if not problem.invariants_hold(successor):
                return _no_plan(
                    config, started, "model-proposed-invariant-violating-transition",
                    expansions=depth,
                )
            before = problem.measure(state, problem.active_observable)
            after = problem.measure(successor, problem.active_observable)
            steps.append(ProspectiveStep(
                depth=depth,
                command_id=effect.command_id,
                command=dict(effect.command),
                causal_support=effect.support,
                causal_confidence=effect.confidence,
                potential_before=before,
                potential_after=after,
                state_key=problem.state_key(successor),
            ))
            minimum_confidence = min(minimum_confidence, effect.confidence)
            total_risk += effect.risk
            reached = tuple(
                item for item in problem.milestones
                if milestone_satisfied(
                    item,
                    problem.measure(successor, item.observable),
                    initial_values[item.shadow_id],
                )
            )
            if proposal.milestone_shadow_id is not None:
                reached = tuple(
                    item for item in reached
                    if item.shadow_id == proposal.milestone_shadow_id
                )
            if reached:
                rank = (
                    1 if any(item.terminal for item in reached) else 0,
                    _progress(problem.preferred_direction, problem.initial_value, after),
                    minimum_confidence,
                    -total_risk,
                    -depth,
                )
                candidate = (rank, tuple(steps), reached)
                if best is None or candidate[0] > best[0]:
                    best = candidate
            state = successor
        if best is None:
            return _no_plan(
                config, started, "validated-composition-reached-no-milestone",
                expansions=len(steps),
            )
        _rank, best_steps, reached = best
        milestone = sorted(
            reached, key=lambda item: (not item.terminal, item.kind, item.shadow_id),
        )[0]
        factorization = ControlFactorization(
            explanation_id=problem.explanation_id,
            verb=problem.verb,
            milestone=milestone,
            steps=best_steps,
            protected_invariants=problem.protected_invariants,
            terminal_reached=any(item.terminal for item in reached),
            useful_milestone_reached=True,
        )
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        return SearchResult(
            "PLAN_FOUND", factorization, len(best_steps), len(best_steps), 1,
            len(best_steps), elapsed, config,
        )
