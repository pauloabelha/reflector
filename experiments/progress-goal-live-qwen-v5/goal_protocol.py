"""Keep Qwen semantics; ground contradicted exact ports in R2."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
PATH = HERE.parent / "progress-goal-live-qwen-v3" / "goal_protocol.py"
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v5_base", PATH)
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
    qwen_goal = dict(compiled["goal"])
    if qwen_goal["family"] != "collection_containment":
        return compiled
    transitions = list(workspace["calibrated_transitions"])
    moving = sorted({
        str(item["controlled_id"])
        for item in transitions if tuple(item["observed_delta"]) != (0, 0)
    })
    zero = sorted(
        str(item["intervention_ref"])
        for item in transitions if tuple(item["observed_delta"]) == (0, 0)
    )
    if len(moving) != 1 or len(zero) != 1:
        return {
            "accepted": False, "reason": "r2-open-port-ambiguous", "goal": None,
            "qwen_goal": qwen_goal, "controlled_candidates": moving,
            "interaction_candidates": zero, "empirical_support": 0,
        }
    witnesses = []
    if qwen_goal["controlled_id"] != moving[0]:
        witnesses.append({
            "port": "controlled_id", "qwen_value": qwen_goal["controlled_id"],
            "status": "contradicted-open", "r2_binding": moving[0],
            "basis": "unique nonzero action-correlated pose change",
        })
    if qwen_goal["interaction_candidate"] != zero[0]:
        proposed = next(
            (item for item in transitions if item["intervention_ref"] == qwen_goal["interaction_candidate"]),
            None,
        )
        witnesses.append({
            "port": "interaction_candidate", "qwen_value": qwen_goal["interaction_candidate"],
            "status": "contradicted-open", "r2_binding": zero[0],
            "qwen_value_observed_delta": None if proposed is None else list(proposed["observed_delta"]),
            "basis": "unique intervention without a grounded translation effect",
        })
    grounded = {**qwen_goal, "controlled_id": moving[0], "interaction_candidate": zero[0]}
    return {
        "accepted": True,
        "reason": "support-zero-semantic-proposal-r2-grounded-ports",
        "goal": grounded,
        "qwen_goal": qwen_goal,
        "r2_grounding": {
            "controlled_id": moving[0], "interaction_candidate": zero[0],
            "port_witnesses": witnesses, "population_complete": True,
        },
        "empirical_support": 0,
    }


__all__ = ["GoalProtocolError", "PROTOCOL", "PROMPT", "build_workspace", "compile_response", "request_payload", "response_schema"]
