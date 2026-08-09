"""Evidence-consistent port validation and structured Qwen revision."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Mapping


HERE = Path(__file__).resolve().parent
PATH = HERE.parent / "progress-goal-live-qwen-v3" / "goal_protocol.py"
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v4_base", PATH)
assert SPEC is not None and SPEC.loader is not None
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

PROTOCOL = BASE.PROTOCOL
PROMPT = BASE.PROMPT
GoalProtocolError = BASE.GoalProtocolError
build_workspace = BASE.build_workspace
response_schema = BASE.response_schema
request_payload = BASE.request_payload


def compile_response(response: Mapping[str, Any], workspace: Mapping[str, Any]) -> dict[str, Any]:
    compiled = BASE.compile_response(response, workspace)
    if not compiled.get("accepted") or not compiled.get("goal"):
        return compiled
    goal = compiled["goal"]
    if goal["family"] != "collection_containment":
        return compiled
    transitions = list(workspace["calibrated_transitions"])
    moving = sorted({
        str(item["controlled_id"])
        for item in transitions
        if tuple(item["observed_delta"]) != (0, 0)
    })
    zero = sorted(
        str(item["intervention_ref"])
        for item in transitions
        if tuple(item["observed_delta"]) == (0, 0)
    )
    by_ref = {str(item["intervention_ref"]): item for item in transitions}
    rows = []
    if len(moving) != 1 or goal["controlled_id"] != moving[0]:
        rows.append({
            "kind": "controlled-role-contradicted",
            "proposed": goal["controlled_id"],
            "observed_action_correlated_entities": moving,
        })
    proposed_intervention = by_ref.get(goal["interaction_candidate"])
    if (
        proposed_intervention is None
        or tuple(proposed_intervention["observed_delta"]) != (0, 0)
        or not zero
    ):
        rows.append({
            "kind": "interaction-port-explained-as-translation",
            "proposed": goal["interaction_candidate"],
            "proposed_observed_delta": None if proposed_intervention is None else list(proposed_intervention["observed_delta"]),
            "unexplained_zero_effect_candidates": zero,
        })
    if rows:
        return {
            "accepted": False,
            "reason": "r2-grounding-criticism",
            "goal": None,
            "proposed_goal": goal,
            "criticism": rows,
            "empirical_support": 0,
        }
    return compiled


REVISION_RULE = """
R2 rejected your prior support-zero proposal because some role ports contradict direct calibration evidence. Revise the complete hypothesis yourself. Treat observed nonzero deltas as established translation effects. A zero-effect intervention is only an unexplained candidate deserving a situated interaction probe, not a known interaction. Preserve or change the semantic family according to the evidence. Do not emit null, an action meaning, or an action sequence.
"""


def revise_response(
    *, workspace: Mapping[str, Any], config: Mapping[str, Any], image_url: str,
    prior_response: Mapping[str, Any], criticism: Mapping[str, Any],
    completion_poster: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    revision_workspace = dict(workspace)
    revision_workspace["r2_grounding_criticism"] = {
        "prior_goal": criticism.get("proposed_goal"),
        "witnesses": criticism.get("criticism", []),
        "support_delta": 0,
    }
    original = BASE.PROMPT
    BASE.PROMPT = original + REVISION_RULE
    try:
        payload = BASE.request_payload(revision_workspace, config, image_url)
    finally:
        BASE.PROMPT = original
    response = completion_poster(config["endpoint"], payload)
    compiled = compile_response(response, workspace)
    compiled["revision_attempted"] = True
    compiled["prior_criticism"] = criticism
    return response, compiled


__all__ = ["GoalProtocolError", "PROTOCOL", "PROMPT", "build_workspace", "compile_response", "request_payload", "response_schema", "revise_response"]
