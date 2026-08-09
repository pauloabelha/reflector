"""Strict semantic nomination of guarded-obligation roles from live vision."""
from __future__ import annotations

import json
from typing import Any, Mapping


PROTOCOL = "guarded-obligation-role-nomination-v0"


class GuardedGoalProtocolError(ValueError):
    pass


PROMPT = """You are a semantic attention worker sharing one executable workspace with a grounded visual reasoner.
You see a current frame and recent opaque transition effects. Hypotheses start with empirical support zero.

Look for tasks whose progress may require satisfying locations while a separate visible state or mode has a required appearance. Generic examples include locks and keys, configure-then-visit tasks, deliveries with types, switches, and stateful navigation. Do not assume this family when a simpler spatial goal explains the frame.

If warranted, nominate: (1) the action-correlated controlled object's bounding box; (2) a persistent visible state-register panel; (3) one or more obligation sites and the visible exemplar that may specify each required state; and (4) visible sites that may transform the register. Bounding boxes are situated addresses only. R2 must test every role through transitions before control.

Never name an action meaning, route, game, color name, or policy. Do not claim support. Return null if these roles are not visibly distinguishable.
"""


def _bbox_schema(width: int, height: int) -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["x1", "y1", "x2", "y2"],
        "properties": {
            "x1": {"type": "integer", "minimum": 0, "maximum": width - 1},
            "y1": {"type": "integer", "minimum": 0, "maximum": height - 1},
            "x2": {"type": "integer", "minimum": 1, "maximum": width},
            "y2": {"type": "integer", "minimum": 1, "maximum": height},
        },
    }


def response_schema(width: int, height: int) -> dict[str, Any]:
    bbox = _bbox_schema(width, height)
    site = {
        "type": "object", "additionalProperties": False,
        "required": ["site_bbox", "required_state_bbox"],
        "properties": {"site_bbox": bbox, "required_state_bbox": bbox},
    }
    proposal = {
        "type": "object", "additionalProperties": False,
        "required": ["controlled_bbox", "register_bbox", "obligations", "transformer_bboxes", "rationale"],
        "properties": {
            "controlled_bbox": bbox,
            "register_bbox": bbox,
            "obligations": {"type": "array", "minItems": 1, "maxItems": 8, "items": site},
            "transformer_bboxes": {"type": "array", "minItems": 1, "maxItems": 8, "items": bbox},
            "rationale": {"type": "string", "minLength": 1, "maxLength": 320},
        },
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": ["protocol", "proposal"],
        "properties": {"protocol": {"const": PROTOCOL}, "proposal": {"oneOf": [{"type": "null"}, proposal]}},
    }


def request_payload(workspace: Mapping[str, Any], config: Mapping[str, Any], image_url: str) -> dict[str, Any]:
    frame = workspace.get("frame", {})
    width, height = int(frame.get("width", 0)), int(frame.get("height", 0))
    if width < 1 or height < 1:
        raise GuardedGoalProtocolError("workspace needs frame dimensions")
    text = PROMPT + "\nEPISTEMIC_WORKSPACE\n" + json.dumps(workspace, sort_keys=True, separators=(",", ":"))
    return {
        "model": config["model"],
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": text},
            {"type": "text", "text": "current visual frame"},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]}],
        "temperature": config.get("temperature", 0), "seed": config.get("seed", 0),
        "max_tokens": config.get("max_tokens", 2048),
        "thinking_budget_tokens": config.get("thinking_budget_tokens", 1024),
        "stream": False,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "guarded_obligation_role_nomination_v0", "strict": True,
            "schema": response_schema(width, height),
        }},
    }


def _bbox(value: Any, width: int, height: int) -> tuple[int, int, int, int]:
    if not isinstance(value, Mapping) or set(value) != {"x1", "y1", "x2", "y2"}:
        raise GuardedGoalProtocolError("invalid bounding box")
    box = tuple(int(value[key]) for key in ("x1", "y1", "x2", "y2"))
    if not (0 <= box[0] < box[2] <= width and 0 <= box[1] < box[3] <= height):
        raise GuardedGoalProtocolError("bounding box is outside the frame")
    return box


def compile_response(response: Mapping[str, Any], workspace: Mapping[str, Any]) -> dict[str, Any]:
    parsed = response.get("parsed", response)
    if not isinstance(parsed, Mapping) or set(parsed) != {"protocol", "proposal"} or parsed.get("protocol") != PROTOCOL:
        return {"accepted": False, "reason": "top-level-contract", "proposal": None}
    proposal = parsed.get("proposal")
    if proposal is None:
        return {"accepted": True, "reason": "abstain", "proposal": None, "empirical_support": 0}
    required = {"controlled_bbox", "register_bbox", "obligations", "transformer_bboxes", "rationale"}
    if not isinstance(proposal, Mapping) or set(proposal) != required:
        return {"accepted": False, "reason": "proposal-contract", "proposal": None}
    width, height = int(workspace["frame"]["width"]), int(workspace["frame"]["height"])
    try:
        controlled = _bbox(proposal["controlled_bbox"], width, height)
        register = _bbox(proposal["register_bbox"], width, height)
        obligations = tuple((
            _bbox(row["site_bbox"], width, height),
            _bbox(row["required_state_bbox"], width, height),
        ) for row in proposal["obligations"])
        transformers = tuple(_bbox(row, width, height) for row in proposal["transformer_bboxes"])
    except (GuardedGoalProtocolError, KeyError, TypeError) as error:
        return {"accepted": False, "reason": "grounding-address", "proposal": None, "detail": str(error)}
    if not obligations or not transformers:
        return {"accepted": False, "reason": "empty-role-population", "proposal": None}
    if controlled == register or any(site == register for site, _required in obligations):
        return {"accepted": False, "reason": "role-collapse", "proposal": None}
    situated = {
        "controlled_bbox": controlled, "register_bbox": register,
        "obligations": obligations, "transformer_bboxes": transformers,
        "rationale": str(proposal["rationale"]),
    }
    return {
        "accepted": True, "reason": "support-zero-role-nomination",
        "proposal": situated, "empirical_support": 0,
        "required_r2_tests": ["action-correlated-pose", "persistent-register", "arrival-state-change", "state-qualified-discharge"],
    }


__all__ = ["GuardedGoalProtocolError", "PROMPT", "PROTOCOL", "compile_response", "request_payload", "response_schema"]
