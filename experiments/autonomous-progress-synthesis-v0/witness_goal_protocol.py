"""Evidence-bearing goal selection over R2-grounded executable witnesses.

Qwen chooses attention among candidates that R2 has already grounded all the
way to pixels and evaluated.  Selection never raises empirical support and
never conveys an action policy.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence

import progress_synthesis as PS
import workspace_potential_search as WPS
import workspace_goal_revision as REVISION


PROTOCOL = "executable-progress-witness-selection-v0"
MAX_WITNESSES = 64


class WitnessProtocolError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ExecutableGoalWitness:
    witness_id: str
    goal: Mapping[str, Any]
    current_value: int
    correspondence_count: int
    compiled: WPS.WorkspacePotential
    empirical_support: int = 0


def _goal(family: str, controlled_id: str, members: Sequence[str], container_id: str | None = None) -> dict[str, Any]:
    potential, terminal = WPS.FAMILY_CONTRACTS[family]
    return {
        "family": family, "controlled_id": str(controlled_id), "members": list(map(str, members)),
        "container_id": None if container_id is None else str(container_id),
        "potential": potential, "terminal": terminal, "interaction_candidate": None,
        "rationale": "selected from an exact executable R2 witness",
    }


def _candidate(goal: Mapping[str, Any], workspace: Mapping[str, Any], grid: Sequence[Sequence[int]]) -> ExecutableGoalWitness | None:
    signature = REVISION.semantic_signature(goal)
    witness_id = "gw:" + PS.stable_hash({"protocol": PROTOCOL, "semantics": json.loads(signature)})[:24]
    try:
        compiled = WPS.compile_rendered_goal(goal, workspace, grid, proposal_id=witness_id)
        reading = WPS.evaluate(compiled, grid)
    except (WPS.WorkspacePotentialError, PS.SynthesisError):
        return None
    # A goal at its claimed terminal value while the environment is known not
    # complete is already refuted. Unknown/ambiguous values are not executable.
    if reading.value is None or reading.value <= 0:
        return None
    return ExecutableGoalWitness(witness_id, dict(goal), reading.value, reading.correspondence_count, compiled, 0)


def enumerate_witnesses(workspace: Mapping[str, Any], grid: Sequence[Sequence[int]], *, limit: int = MAX_WITNESSES) -> tuple[ExecutableGoalWitness, ...]:
    if not 1 <= int(limit) <= MAX_WITNESSES:
        raise WitnessProtocolError("witness limit is out of bounds")
    rows = tuple(workspace.get("entities", ())); entity_ids = tuple(str(row["id"]) for row in rows)
    controlled = tuple(map(str, workspace.get("control_opportunity", {}).get("controlled_candidates", ())))
    if len(controlled) != 1 or controlled[0] not in entity_ids:
        return ()
    actor = controlled[0]; ordinary = tuple(item for item in entity_ids if item != actor)
    member_sets = {(item,) for item in ordinary}
    for group in workspace.get("equivalence_classes", ()):
        members = tuple(sorted(map(str, group.get("members", ()))))
        if members and actor not in members and all(item in ordinary for item in members):
            member_sets.add(members)
    proposed = []
    for members in sorted(member_sets):
        for family in ("alignment", "matching", "connectivity", "avoidance", "transformation"):
            proposed.append(_goal(family, actor, members))
    for capacity in workspace.get("capacity_hypotheses", ()):
        members = tuple(map(str, capacity.get("members", ())))
        container = capacity.get("container")
        if members and container in ordinary and all(item in ordinary for item in members):
            proposed.append(_goal("collection_containment", actor, members, str(container)))
    unique = {}
    for goal in proposed:
        item = _candidate(goal, workspace, grid)
        if item is not None:
            unique[item.witness_id] = item
    return tuple(sorted(unique.values(), key=lambda item: (item.current_value, item.goal["family"], item.witness_id))[:limit])


def witness_projection(witnesses: Sequence[ExecutableGoalWitness], *, retired_ids: Sequence[str] = ()) -> list[dict[str, Any]]:
    retired = set(map(str, retired_ids)); rows = []
    for item in witnesses:
        if item.witness_id in retired:
            continue
        goal = item.goal
        rows.append({
            "witness_id": item.witness_id, "family": goal["family"],
            "controlled_id": goal["controlled_id"], "members": list(goal["members"]),
            "container_id": goal["container_id"], "potential": goal["potential"],
            "terminal": goal["terminal"], "current_value": item.current_value,
            "correspondence_count": item.correspondence_count,
            "grounding": "pixel-executable-agreement", "empirical_support": 0,
        })
    return rows


PROMPT = """You are the semantic attention worker in a shared executable epistemic workspace.
R2 has enumerated goal witnesses whose roles terminate in current pixels, whose potential is mechanically evaluable, and whose current value is above the claimed terminal lower bound. Select at most one witness that deserves causal testing, or abstain.

Selection changes attention only. Every witness has empirical support zero. Do not infer truth from visual plausibility, do not emit an action meaning or route, and do not alter the witness's family, roles, potential, or terminal predicate. Prefer a witness whose measured potential could discriminate environmental progress rather than merely describe motion. Retired witnesses may not be selected.
"""


def response_schema(witnesses: Sequence[ExecutableGoalWitness], *, retired_ids: Sequence[str] = ()) -> dict[str, Any]:
    ids = [row["witness_id"] for row in witness_projection(witnesses, retired_ids=retired_ids)]
    selection = {"type": "object", "additionalProperties": False, "required": ["witness_id", "rationale"], "properties": {"witness_id": {"enum": ids}, "rationale": {"type": "string", "minLength": 1, "maxLength": 240}}}
    return {"type": "object", "additionalProperties": False, "required": ["protocol", "selection"], "properties": {"protocol": {"const": PROTOCOL}, "selection": {"oneOf": [{"type": "null"}, selection]}}}


def request_payload(workspace: Mapping[str, Any], witnesses: Sequence[ExecutableGoalWitness], config: Mapping[str, Any], image_url: str, *, retired_ids: Sequence[str] = (), feedback: Mapping[str, Any] | None = None) -> dict[str, Any]:
    visible = witness_projection(witnesses, retired_ids=retired_ids)
    text = PROMPT + "\nEPISTEMIC_WORKSPACE\n" + json.dumps(workspace, sort_keys=True, separators=(",", ":")) + "\nEXECUTABLE_WITNESSES\n" + json.dumps(visible, sort_keys=True, separators=(",", ":"))
    if feedback is not None:
        text += "\nENVIRONMENT_FEEDBACK\n" + json.dumps(dict(feedback), sort_keys=True, separators=(",", ":"))
    return {
        "model": config["model"], "messages": [{"role": "user", "content": [{"type": "text", "text": text}, {"type": "text", "text": "current visual frame"}, {"type": "image_url", "image_url": {"url": image_url}}]}],
        "temperature": config.get("temperature", 0), "seed": config.get("seed", 0), "max_tokens": config.get("max_tokens", 2048), "thinking_budget_tokens": config.get("thinking_budget_tokens", 1024), "stream": False,
        "response_format": {"type": "json_schema", "json_schema": {"name": "executable_progress_witness_selection_v0", "strict": True, "schema": response_schema(witnesses, retired_ids=retired_ids)}},
    }


def compile_selection(response: Mapping[str, Any], witnesses: Sequence[ExecutableGoalWitness], *, retired_ids: Sequence[str] = ()) -> dict[str, Any]:
    parsed = response.get("parsed", response); retired = set(map(str, retired_ids)); by_id = {item.witness_id: item for item in witnesses}
    if not isinstance(parsed, Mapping) or set(parsed) != {"protocol", "selection"} or parsed.get("protocol") != PROTOCOL:
        return {"accepted": False, "reason": "top-level-contract", "goal": None}
    selection = parsed.get("selection")
    if selection is None:
        return {"accepted": True, "reason": "abstain", "goal": None}
    if not isinstance(selection, Mapping) or set(selection) != {"witness_id", "rationale"}:
        return {"accepted": False, "reason": "selection-contract", "goal": None}
    witness_id = str(selection["witness_id"]); item = by_id.get(witness_id)
    if item is None or witness_id in retired:
        return {"accepted": False, "reason": "witness-not-live", "goal": None}
    goal = dict(item.goal); goal["rationale"] = str(selection["rationale"])
    return {"accepted": True, "reason": "support-zero-witness-selection", "witness_id": witness_id, "goal": goal, "compiled": item.compiled, "empirical_support": 0}


__all__ = ["ExecutableGoalWitness", "MAX_WITNESSES", "PROMPT", "PROTOCOL", "WitnessProtocolError", "compile_selection", "enumerate_witnesses", "request_payload", "response_schema", "witness_projection"]
