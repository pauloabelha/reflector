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
