"""Compact evidence-return turn for a failed support-zero progress proxy."""
from __future__ import annotations

from copy import deepcopy
import json
from typing import Any, Callable, Mapping


class GoalRevisionError(ValueError):
    pass


FAMILY_CONTRACTS = {
    "matching": ("MismatchCount", "AllMatched"),
    "alignment": ("AlignmentResidual", "Aligned"),
    "collection_containment": ("OutsideCount", "AllInside"),
    "connectivity": ("ComponentDeficit", "Connected"),
    "avoidance": ("CollisionRisk", "NoCollision"),
    "transformation": ("TransformationResidual", "TransformationComplete"),
}


def semantic_signature(goal: Mapping[str, Any]) -> str:
    body = {
        "family": goal.get("family"), "controlled_id": goal.get("controlled_id"),
        "members": sorted(map(str, goal.get("members", ()))),
        "container_id": goal.get("container_id"), "potential": goal.get("potential"),
        "terminal": goal.get("terminal"),
    }
    return json.dumps(body, sort_keys=True, separators=(",", ":"))


def build_revision_payload(prior_request: Mapping[str, Any], prior_goal: Mapping[str, Any], attention_record: Mapping[str, Any]) -> dict[str, Any]:
    """Return a request with environment feedback, preserving image/schema."""
    request = deepcopy(dict(prior_request))
    try:
        content = request["messages"][0]["content"]
        text_part = content[0]
    except (KeyError, IndexError, TypeError) as error:
        raise GoalRevisionError("prior multimodal request is malformed") from error
    if text_part.get("type") != "text" or not isinstance(text_part.get("text"), str):
        raise GoalRevisionError("prior request lacks a text workspace projection")
    allowed_status = {"attention-suppressed-plateau", "refuted-terminal-proxy"}
    status = str(attention_record.get("status"))
    if status not in allowed_status:
        raise GoalRevisionError("revision requires direct proxy failure feedback")
    feedback = {
        "prior_semantics": json.loads(semantic_signature(prior_goal)),
        "status": status,
        "known_evaluations": int(attention_record.get("known_evaluations", 0)),
        "best_value": attention_record.get("best_value"),
        "environment_refutations": int(attention_record.get("environment_refutations", 0)),
        "last_reason": str(attention_record.get("last_reason", "")),
    }
    rule = (
        "\nENVIRONMENT_FEEDBACK\n" + json.dumps(feedback, sort_keys=True, separators=(",", ":")) +
        "\nThe prior goal improved as a visual proxy but did not establish environmental completion. "
        "Its attention is no longer active. Emit one semantically different, presently grounded support-zero goal "
        "from the same closed families and visible IDs, or return null. Changing only rationale, member order, or "
        "an opaque intervention is a repeat. Evidence against the prior proxy is not support for its replacement.\n"
    )
    text_part["text"] += rule
    _tighten_family_union(request)
    return request


def _tighten_family_union(request: dict[str, Any]) -> None:
    """Make the serving grammar express the compiler's tagged union."""
    try:
        root = request["response_format"]["json_schema"]["schema"]
        goal_union = root["properties"]["goal"]["oneOf"]
        object_schema = next(item for item in goal_union if item.get("type") == "object")
    except (KeyError, StopIteration, TypeError) as error:
        raise GoalRevisionError("response schema lacks the live goal union") from error
    branches = []
    for family, (potential, terminal) in FAMILY_CONTRACTS.items():
        branch = deepcopy(object_schema)
        branch["properties"]["family"] = {"const": family}
        branch["properties"]["potential"] = {"const": potential}
        branch["properties"]["terminal"] = {"const": terminal}
        branches.append(branch)
    root["properties"]["goal"]["oneOf"] = [{"type": "null"}] + branches


def compile_revision(response: Mapping[str, Any], workspace: Mapping[str, Any], prior_goal: Mapping[str, Any], compiler: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]]) -> dict[str, Any]:
    compiled = dict(compiler(response, workspace))
    if not compiled.get("accepted") or compiled.get("goal") is None:
        return compiled
    if semantic_signature(compiled["goal"]) == semantic_signature(prior_goal):
        return {"accepted": False, "reason": "semantic-repeat-after-environment-feedback", "goal": None}
    compiled["revision_of"] = semantic_signature(prior_goal)
    compiled["empirical_support"] = 0
    return compiled


__all__ = ["FAMILY_CONTRACTS", "GoalRevisionError", "build_revision_payload", "compile_revision", "semantic_signature"]
