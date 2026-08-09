"""Strict, action-blind live-Qwen protocol for executable progress goals."""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from typing import Any, Mapping, Sequence


PROTOCOL = "live-progress-goal-v1"
FAMILIES = (
    "matching", "alignment", "collection_containment",
    "connectivity", "avoidance", "transformation",
)
POTENTIALS = (
    "MismatchCount", "AlignmentResidual", "OutsideCount",
    "ComponentDeficit", "CollisionRisk", "TransformationResidual",
)
TERMINALS = (
    "AllMatched", "Aligned", "AllInside", "Connected",
    "NoCollision", "TransformationComplete",
)


class GoalProtocolError(ValueError):
    pass


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def build_workspace(
    *,
    entities: Sequence[Mapping[str, Any]],
    transitions: Sequence[Mapping[str, Any]],
    frame: Mapping[str, int],
) -> dict[str, Any]:
    """Build a compact world-facing field without interpreting the goal."""

    rows = [dict(item) for item in entities]
    ids = [str(item["id"]) for item in rows]
    if len(ids) != len(set(ids)):
        raise GoalProtocolError("entity IDs must be unique")
    exact_classes: dict[tuple[Any, ...], list[str]] = defaultdict(list)
    outline_classes: dict[str, list[str]] = defaultdict(list)
    for item in rows:
        exact_classes[(item["outline_class"], item["interior_class"], item["area"])].append(str(item["id"]))
        outline_classes[str(item["outline_class"])].append(str(item["id"]))
    classes = [
        {"kind": "exact_visual", "members": sorted(members)}
        for _, members in sorted(exact_classes.items(), key=lambda pair: repr(pair[0]))
        if len(members) >= 2
    ] + [
        {"kind": "same_outline", "members": sorted(members)}
        for _, members in sorted(outline_classes.items())
        if len(members) >= 2
    ]
    capacities: list[dict[str, Any]] = []
    for group in classes:
        member_rows = [next(item for item in rows if item["id"] == ref) for ref in group["members"]]
        if len({item["area"] for item in member_rows}) != 1:
            continue
        member_area = int(member_rows[0]["area"])
        for container in rows:
            if container["id"] in group["members"] or member_area <= 0:
                continue
            if int(container["area"]) == member_area * len(group["members"]):
                capacities.append({
                    "members": list(group["members"]),
                    "container": str(container["id"]),
                    "member_count": len(group["members"]),
                    "area_ratio_exact": True,
                    "placement_capacity": len(group["members"]),
                })
    return {
        "protocol": PROTOCOL,
        "frame": {"height": int(frame["height"]), "width": int(frame["width"])},
        "entities": rows,
        "equivalence_classes": classes,
        "capacity_hypotheses": capacities,
        "calibrated_transitions": [dict(item) for item in transitions],
        "epistemic_rules": {
            "attention_is_not_support": True,
            "only_environment_changes_support": True,
            "all_roles_require_visible_ids": True,
        },
    }


def response_schema(workspace: Mapping[str, Any]) -> dict[str, Any]:
    entity_ids = [str(item["id"]) for item in workspace["entities"]]
    interventions = [str(item["intervention_ref"]) for item in workspace["calibrated_transitions"]]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["protocol", "goal"],
        "properties": {
            "protocol": {"const": PROTOCOL},
            "goal": {
                "oneOf": [
                    {"type": "null"},
                    {
                        "type": "object", "additionalProperties": False,
                        "required": ["family", "controlled_id", "members", "container_id", "potential", "terminal", "interaction_candidate", "rationale"],
                        "properties": {
                            "family": {"enum": list(FAMILIES)},
                            "controlled_id": {"enum": entity_ids},
                            "members": {"type": "array", "minItems": 1, "maxItems": 16, "uniqueItems": True, "items": {"enum": entity_ids}},
                            "container_id": {"oneOf": [{"type": "null"}, {"enum": entity_ids}]},
                            "potential": {"enum": list(POTENTIALS)},
                            "terminal": {"enum": list(TERMINALS)},
                            "interaction_candidate": {"oneOf": [{"type": "null"}, {"enum": interventions}]},
                            "rationale": {"type": "string", "minLength": 1, "maxLength": 320},
                        },
                    },
                ]
            },
        },
    }


PROMPT = """You are the slow semantic worker in a shared executable epistemic workspace.
You see the world directly and also see R2's exact grounded component and intervention deltas.
Construct at most one live goal hypothesis. It starts with empirical support zero: you may say what deserves testing, never that it is true.

Do not assume every goal is pairwise. Consider these generic families equally: matching, alignment, collection/containment, connectivity, avoidance, transformation. A useful goal identifies a controlled entity, any set-valued roles, a measurable nonnegative potential, a terminal predicate, and—only if warranted—an opaque interaction candidate. Repeated visual classes may denote a set role. A differently patterned member of the same outline class may have a distinct controlled role. A region whose placement capacity matches a repeated class may deserve attention as a receptacle, but this is only a hypothesis.

Available potential/terminal pairs are semantic contracts:
- MismatchCount / AllMatched
- AlignmentResidual / Aligned
- OutsideCount / AllInside
- ComponentDeficit / Connected
- CollisionRisk / NoCollision
- TransformationResidual / TransformationComplete

Use only visible IDs and opaque intervention refs. Never emit action meanings, colors, coordinates, a policy, or an action sequence. Return null if no hypothesis is sufficiently grounded for a cheap empirical test.
"""


def request_payload(workspace: Mapping[str, Any], config: Mapping[str, Any], image_url: str) -> dict[str, Any]:
    text = PROMPT + "\nEPISTEMIC_WORKSPACE\n" + stable_json(workspace)
    return {
        "model": config["model"],
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": text},
            {"type": "text", "text": "current visual frame"},
            {"type": "image_url", "image_url": {"url": image_url}},
        ]}],
        "temperature": config.get("temperature", 0),
        "seed": config.get("seed", 0),
        "max_tokens": config.get("max_tokens", 3072),
        "thinking_budget_tokens": config.get("thinking_budget_tokens", 1536),
        "stream": False,
        "response_format": {"type": "json_schema", "json_schema": {
            "name": "live_progress_goal_v1", "strict": True,
            "schema": response_schema(workspace),
        }},
    }


def compile_response(response: Mapping[str, Any], workspace: Mapping[str, Any]) -> dict[str, Any]:
    parsed = response.get("parsed", response)
    if not isinstance(parsed, Mapping) or set(parsed) != {"protocol", "goal"} or parsed.get("protocol") != PROTOCOL:
        return {"accepted": False, "reason": "top-level-contract", "goal": None}
    goal = parsed.get("goal")
    if goal is None:
        return {"accepted": True, "reason": "abstain", "goal": None}
    if not isinstance(goal, Mapping):
        return {"accepted": False, "reason": "goal-contract", "goal": None}
    required = {"family", "controlled_id", "members", "container_id", "potential", "terminal", "interaction_candidate", "rationale"}
    if set(goal) != required:
        return {"accepted": False, "reason": "goal-fields", "goal": None}
    ids = {str(item["id"]) for item in workspace["entities"]}
    members = tuple(str(item) for item in goal["members"])
    if goal["controlled_id"] not in ids or not members or len(set(members)) != len(members) or any(item not in ids for item in members):
        return {"accepted": False, "reason": "grounding-address", "goal": None}
    if goal["controlled_id"] in members or (goal["container_id"] is not None and goal["container_id"] not in ids):
        return {"accepted": False, "reason": "role-separation", "goal": None}
    interventions = {str(item["intervention_ref"]) for item in workspace["calibrated_transitions"]}
    if goal["interaction_candidate"] is not None and goal["interaction_candidate"] not in interventions:
        return {"accepted": False, "reason": "intervention-address", "goal": None}
    expected = {
        "matching": ("MismatchCount", "AllMatched"),
        "alignment": ("AlignmentResidual", "Aligned"),
        "collection_containment": ("OutsideCount", "AllInside"),
        "connectivity": ("ComponentDeficit", "Connected"),
        "avoidance": ("CollisionRisk", "NoCollision"),
        "transformation": ("TransformationResidual", "TransformationComplete"),
    }
    if goal["family"] not in expected or (goal["potential"], goal["terminal"]) != expected[goal["family"]]:
        return {"accepted": False, "reason": "family-semantics", "goal": None}
    if goal["family"] == "collection_containment":
        match = any(
            set(item["members"]) == set(members)
            and item["container"] == goal["container_id"]
            and item["placement_capacity"] == len(members)
            for item in workspace["capacity_hypotheses"]
        )
        if not match or goal["interaction_candidate"] is None:
            return {"accepted": False, "reason": "collection-grounding", "goal": None}
    return {"accepted": True, "reason": "support-zero-proposal", "goal": dict(goal), "empirical_support": 0}


__all__ = ["GoalProtocolError", "PROTOCOL", "PROMPT", "build_workspace", "compile_response", "request_payload", "response_schema"]
