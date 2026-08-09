"""Progress-seeking goal protocol layered over geometrically valid v2."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
PATH = HERE.parent / "progress-goal-live-qwen-v2" / "goal_protocol.py"
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v3_base", PATH)
assert SPEC is not None and SPEC.loader is not None
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

PROTOCOL = BASE.PROTOCOL
GoalProtocolError = BASE.GoalProtocolError

DRIVE_RULE = """
PROGRESS-SEEKING RULE: capacity_hypothesis.members is a candidate role population, never a claim that those regions are already inside. current_inside_count and outside_count are direct present-state measurements. When any exact grounded opportunity has outside_count > 0, you MUST write the single cheapest falsifiable goal hypothesis; uncertainty calls for testing, not abstention. Null is legal only when the workspace says progress_opportunity_present=false. Prefer hypotheses whose potential exactly measures the exposed deficit. Do not narrate an action sequence.
"""
PROMPT = BASE.PROMPT + DRIVE_RULE


def _inside(member: Mapping[str, Any], container: Mapping[str, Any]) -> bool:
    mx, my = (int(x) for x in member["origin"])
    mw, mh = (int(x) for x in member["size"])
    cx, cy = (int(x) for x in container["origin"])
    cw, ch = (int(x) for x in container["size"])
    return cx <= mx and cy <= my and mx + mw <= cx + cw and my + mh <= cy + ch


def build_workspace(
    *, entities: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]], frame: Mapping[str, int],
) -> dict[str, Any]:
    value = BASE.build_workspace(entities=entities, transitions=transitions, frame=frame)
    by_id = {str(item["id"]): item for item in value["entities"]}
    opportunities = []
    for item in value["capacity_hypotheses"]:
        container = by_id[item["container"]]
        inside = sum(_inside(by_id[member], container) for member in item["members"])
        enriched = {
            **item,
            "members_semantics": "candidate role population, not current contents",
            "current_inside_count": inside,
            "outside_count": len(item["members"]) - inside,
        }
        opportunities.append(enriched)
    value["capacity_hypotheses"] = opportunities
    value["progress_opportunity_present"] = any(item["outside_count"] > 0 for item in opportunities)
    value["cognitive_drive"] = "propose cheapest grounded falsifiable progress hypothesis when opportunity is present"
    return value


def response_schema(workspace: Mapping[str, Any]) -> dict[str, Any]:
    schema = BASE.response_schema(workspace)
    if workspace.get("progress_opportunity_present"):
        goal_schema = schema["properties"]["goal"]
        goal_schema["oneOf"] = [branch for branch in goal_schema["oneOf"] if branch.get("type") != "null"]
    return schema


def request_payload(workspace: Mapping[str, Any], config: Mapping[str, Any], image_url: str) -> dict[str, Any]:
    original = BASE.BASE.PROMPT
    BASE.BASE.PROMPT = PROMPT
    try:
        payload = BASE.request_payload(workspace, config, image_url)
    finally:
        BASE.BASE.PROMPT = original
    payload["response_format"]["json_schema"]["schema"] = response_schema(workspace)
    return payload


def compile_response(response: Mapping[str, Any], workspace: Mapping[str, Any]) -> dict[str, Any]:
    if workspace.get("progress_opportunity_present"):
        parsed = response.get("parsed", response)
        if isinstance(parsed, Mapping) and parsed.get("goal") is None:
            return {"accepted": False, "reason": "progress-opportunity-requires-proposal", "goal": None}
    return BASE.compile_response(response, workspace)


__all__ = ["GoalProtocolError", "PROTOCOL", "PROMPT", "build_workspace", "compile_response", "request_payload", "response_schema"]
