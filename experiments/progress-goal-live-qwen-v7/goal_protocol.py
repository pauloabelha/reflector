"""Treat any grounded controllable process as a live progress opportunity."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

HERE = Path(__file__).resolve().parent
PATH = HERE.parent / "progress-goal-live-qwen-v5" / "goal_protocol.py"
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v7_base", PATH)
assert SPEC is not None and SPEC.loader is not None
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

PROTOCOL = BASE.PROTOCOL
GoalProtocolError = BASE.GoalProtocolError
compile_response = BASE.compile_response

CONTROL_RULE = """
A unique action-correlated visual process is itself a grounded progress opportunity even when no capacity hypothesis exists. Use the current frame to identify possible terminal exemplars, destinations, hazards, transformations, or connectivity changes. Choose the cheapest falsifiable family/potential/terminal hypothesis and keep unsupported roles OPEN through null container or minimal visible members. Do not default to collection and do not narrate a route.
"""
PROMPT = BASE.PROMPT + CONTROL_RULE


def build_workspace(*, entities: Sequence[Mapping[str, Any]], transitions: Sequence[Mapping[str, Any]], frame: Mapping[str, int]) -> dict[str, Any]:
    value = BASE.build_workspace(entities=entities, transitions=transitions, frame=frame)
    controlled = sorted({
        str(item["controlled_id"]) for item in transitions
        if item.get("controlled_id") is not None
        and tuple(item.get("observed_delta", (0, 0))) != (0, 0)
    })
    value["control_opportunity"] = {
        "controlled_candidates": controlled,
        "unique": len(controlled) == 1,
        "effects": [
            {"intervention_ref": item["intervention_ref"], "delta": item["observed_delta"]}
            for item in transitions if item.get("controlled_id") in controlled
        ],
    }
    if len(controlled) == 1:
        value["progress_opportunity_present"] = True
        value["cognitive_drive"] = "propose cheapest grounded falsifiable progress hypothesis for controlled process"
    return value


def response_schema(workspace: Mapping[str, Any]) -> dict[str, Any]:
    return BASE.response_schema(workspace)


def request_payload(workspace: Mapping[str, Any], config: Mapping[str, Any], image_url: str) -> dict[str, Any]:
    original = BASE.BASE.PROMPT
    BASE.BASE.PROMPT = PROMPT
    try:
        return BASE.request_payload(workspace, config, image_url)
    finally:
        BASE.BASE.PROMPT = original


__all__ = ["GoalProtocolError", "PROTOCOL", "PROMPT", "build_workspace", "compile_response", "request_payload", "response_schema"]
