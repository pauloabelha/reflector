"""Geometrically valid capacity projection layered over frozen v1."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V1_PATH = HERE.parent / "progress-goal-live-qwen-v1" / "goal_protocol.py"
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v2_base", V1_PATH)
assert SPEC is not None and SPEC.loader is not None
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

PROTOCOL = BASE.PROTOCOL
PROMPT = BASE.PROMPT
GoalProtocolError = BASE.GoalProtocolError
response_schema = BASE.response_schema
compile_response = BASE.compile_response


def build_workspace(
    *, entities: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]], frame: Mapping[str, int],
) -> dict[str, Any]:
    value = BASE.build_workspace(entities=entities, transitions=transitions, frame=frame)
    by_id = {str(item["id"]): item for item in value["entities"]}
    valid = []
    for hypothesis in value["capacity_hypotheses"]:
        members = [by_id[item] for item in hypothesis["members"]]
        container = by_id[hypothesis["container"]]
        sizes = {tuple(int(x) for x in item["size"]) for item in members}
        if len(sizes) != 1:
            continue
        member_width, member_height = next(iter(sizes))
        container_width, container_height = (int(x) for x in container["size"])
        if (
            member_width <= 0 or member_height <= 0
            or container_width % member_width
            or container_height % member_height
        ):
            continue
        slots = (container_width // member_width) * (container_height // member_height)
        if slots != len(members):
            continue
        valid.append({**hypothesis, "placement_capacity": slots, "integer_tiling": True})
    value["capacity_hypotheses"] = valid
    value["capacity_semantics"] = "integer shape tiling, not area equality alone"
    return value


def request_payload(workspace: Mapping[str, Any], config: Mapping[str, Any], image_url: str) -> dict[str, Any]:
    return BASE.request_payload(workspace, config, image_url)


__all__ = ["GoalProtocolError", "PROTOCOL", "PROMPT", "build_workspace", "compile_response", "request_payload", "response_schema"]
