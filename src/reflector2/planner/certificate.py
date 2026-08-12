"""Auditable prospective certificate serialization."""

from __future__ import annotations

from typing import Any, Mapping

from .factorization import ControlProblem, SearchResult


def plan_certificate(
    problem: ControlProblem,
    result: SearchResult,
    *,
    first_successor_prediction: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    factorization = result.factorization
    if factorization is None:
        return None
    if problem.goal_contract is not None and result.current_goal_prospect is not None:
        current = result.current_goal_prospect
        successor = result.successor_goal_prospect
        supports = [step.causal_support for step in factorization.steps]
        confidences = [step.causal_confidence for step in factorization.steps]
        return {
            "protocol": "r2-goal-prospect-certificate-v2",
            "epistemic_status": "prospective-control-justification-not-evidence",
            "explanation_basis": problem.explanation_id,
            "goal_contract_basis": problem.goal_contract.document(),
            "current_verb": problem.verb,
            "current_potential": {
                "measure": problem.active_observable,
                "value": problem.initial_value,
                "preferred_direction": problem.preferred_direction,
            },
            "current_goal_prospect": current.document(),
            "chosen_first_command": dict(factorization.first_command),
            "first_successor_shadow": dict(first_successor_prediction or {}),
            "immediate_orientation": (
                successor.expected_local_verb_orientation if successor else "open"
            ),
            "successor_goal_prospect": successor.document() if successor else None,
            "justification": result.prospect_improvement_kind,
            "factorization": [step.document() for step in factorization.steps],
            "terminal_or_intermediate_completion": factorization.milestone.document(),
            "minimum_edge_support": min(supports) if supports else None,
            "minimum_edge_confidence": min(confidences) if confidences else None,
            "protected_invariants": list(factorization.protected_invariants),
            "unresolved_requirements": list(problem.unresolved_requirements),
            "search_budgets": result.config.document(),
            "search_telemetry": {
                "status": result.status,
                "expansions": result.expansions,
                "generated": result.generated,
                "frontier_peak": result.frontier_peak,
                "maximum_depth_reached": result.maximum_depth_reached,
            },
            "planned_depth": len(factorization.steps),
            "first_command": dict(factorization.first_command),
            "predicted_causal_composition": [
                step.document() for step in factorization.steps
            ],
            "invalidation_conditions": [
                "prediction-mismatch",
                "identity-ambiguity-or-break",
                "mechanism-applicability-failure",
                "goal-contract-status-changed",
                "unexpected-successor-structure",
                "terminal-or-intermediate-completion-settled",
            ],
            "authority": "FIRST_COMMAND_ONLY",
            "external_action_authority": "first-command-only",
            "continuation_authority": "none-replan-after-environment-settlement",
        }
    return {
        "protocol": "r2-control-factorization-v0",
        "epistemic_status": "prospective-control-justification-not-evidence",
        "explanation": problem.explanation_id,
        "verb": problem.verb,
        "current_potential": {
            "measure": problem.active_observable,
            "value": problem.initial_value,
            "preferred_direction": problem.preferred_direction,
        },
        "selected_milestone": factorization.milestone.document(),
        "predicted_causal_composition": [step.document() for step in factorization.steps],
        "planned_depth": len(factorization.steps),
        "first_command": dict(factorization.first_command),
        "first_successor_prediction": dict(first_successor_prediction or {}),
        "protected_invariants": list(factorization.protected_invariants),
        "replan_unlock_conditions": [
            "prediction-mismatch",
            "identity-ambiguity-or-break",
            "mechanism-applicability-failure",
            "unexpected-successor-structure",
            "milestone-achieved-or-refuted",
        ],
        "search": {
            "status": result.status,
            "expansions": result.expansions,
            "generated": result.generated,
            "frontier_peak": result.frontier_peak,
            "maximum_depth_reached": result.maximum_depth_reached,
            "elapsed_ms": result.elapsed_ms,
            "limits": result.config.document(),
        },
        "external_action_authority": "first-command-only",
        "continuation_authority": "none-replan-after-environment-settlement",
    }


def settle_plan_certificate(
    certificate: Mapping[str, Any],
    *,
    adjudication: str,
    identity_status: str,
    mechanism_status: str,
    unexpected_event: bool = False,
    milestone_observed: bool | None = None,
) -> dict[str, Any]:
    """Invalidate every continuation and classify its environment settlement."""

    reasons = []
    if adjudication != "confirmed":
        reasons.append("prediction-mismatch")
    if identity_status != "UNIQUE":
        reasons.append("identity-ambiguity-or-break")
    if mechanism_status == "REFUTED":
        reasons.append("mechanism-applicability-failure")
    if unexpected_event:
        reasons.append("unexpected-successor-structure")
    confirmed = not reasons
    planned_depth = int(certificate.get("planned_depth", 0))
    milestone = (
        "CONFIRMED" if milestone_observed is True else
        "REFUTED" if milestone_observed is False else
        "CONFIRMED" if confirmed and planned_depth == 1 else
        "PENDING_REPLAN" if confirmed else "REFUTED"
    )
    return {
        "certificate_protocol": certificate.get("protocol"),
        "first_step": "CONFIRMED" if confirmed else "INVALIDATED",
        "milestone": milestone,
        "invalidation_reasons": reasons,
        "continuation": "INVALIDATED_AFTER_OBSERVATION",
        "replan_required": True,
        "evidence_source": "environment-successor-settlement",
    }
