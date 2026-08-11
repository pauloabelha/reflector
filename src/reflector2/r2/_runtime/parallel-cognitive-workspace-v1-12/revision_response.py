"""Strict, minimal response adapter for exact Qwen revision turns.

The authoritative v1.4 compiler remains the only semantic compiler.  This
module merely removes response branches that are irrelevant once an exact
``revision_task`` exists, then expands the bounded response back into the
legacy compiler contract.  Consequently alpha novelty, evidence visibility,
causal lineage, situated grounding, and unique-grounding checks are neither
duplicated nor weakened here.
"""

from __future__ import annotations

import json
from copy import deepcopy
from typing import Any, Mapping, Sequence


REVISION_PROMPT = """You are revising one grounded schema after structured criticism.
Return exactly one JSON branch allowed by the response schema:
- revision: a single evidence-citing schema revision; or
- abstain: true when the visible closed vocabulary cannot uniquely ground one effect pair.
Do not emit explanations, alternatives, attention writes, expansion requests, prose, or actions.
The revision must cite the exact chain and visible evidence, be alpha-novel, and uniquely retain one grounded effect pair. Enumerate the complete grounding before writing: every condition must hold and the conjunction must retain exactly one unordered pair. If no old candidate can be isolated, you may replace the old conditions and select a different uniquely grounded pair; never emit a predicate shared by multiple retained pairs. Evidence fields are addresses, not support. Reality and the compiler decide acceptance.
EPISTEMIC_INPUT=
"""


def is_revision_turn(turn: Any) -> bool:
    return isinstance(turn.document.get("revision_task"), Mapping)


def is_prospective_revision_turn(turn: Any) -> bool:
    return is_revision_turn(turn) and isinstance(
        turn.document.get("causal_revision_packet"), Mapping
    )


def _relation_evidence_id(qc: Any, turn: Any) -> str:
    if is_prospective_revision_turn(turn):
        return str(
            turn.document["causal_revision_packet"]["current_relation_set"]["id"]
        )
    candidates = [
        item
        for item in qc._visible_object_documents(turn).values()
        if item.get("kind") == "relation_set"
    ]
    if not candidates:
        raise RuntimeError("revision turn exposes no relation-set evidence address")
    selected = max(
        candidates,
        key=lambda item: (int(item.get("revision", item.get("created_revision", -1))), str(item["id"])),
    )
    return str(selected["id"])


def _revision_object_schema(qc: Any, turn: Any) -> dict[str, Any]:
    """Reuse the authoritative revision write grammar without its side branches."""

    legacy = qc._revision_response_base_schema(turn)
    nullable = legacy["properties"]["schema_revision"]
    for branch in nullable.get("oneOf", ()):
        if branch.get("type") == "object":
            value = deepcopy(branch)
            break
    else:
        if nullable.get("type") == "object":
            value = deepcopy(nullable)
        else:
            raise RuntimeError("authoritative compiler exposed no revision object schema")
    relation_id = _relation_evidence_id(qc, turn)
    value["required"] = [
        key for key in value["required"] if key != "evidence_ids"
    ] + ["relation_evidence_id"]
    value["properties"].pop("evidence_ids", None)
    value["properties"]["relation_evidence_id"] = {"const": relation_id}
    if is_prospective_revision_turn(turn):
        causing_ids = [
            str(item) for item in turn.document["revision_task"]["causing_evidence_ids"]
        ]
        if not causing_ids:
            raise RuntimeError("revision turn exposes no prospective evidence address")
        value["required"].append("prospective_evidence_id")
        value["properties"]["prospective_evidence_id"] = {"enum": causing_ids}
    return value


def revision_response_schema(qc: Any, turn: Any) -> dict[str, Any]:
    """Exactly one small write or an explicit abstention."""

    if not is_revision_turn(turn):
        return qc._revision_response_base_schema(turn)
    return {
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["revision"],
                "properties": {"revision": _revision_object_schema(qc, turn)},
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["abstain"],
                "properties": {"abstain": {"const": True}},
            },
        ]
    }


def _adapter_rejection(reason: str, raw: Any) -> dict[str, Any]:
    return {
        "valid_json_contract": False,
        "accepted": [],
        "rejected": [{"kind": "revision_adapter", "reason": reason, "raw": raw}],
        "expansion_requests": [],
        "support_assigned": 0,
        "schema_revision_accepted": False,
        "schema_write_mode": None,
        "explanation_alternative_count": 0,
        "revision_decision": None,
    }


def compile_revision_response(qc: Any, response: Mapping[str, Any], turn: Any) -> dict[str, Any]:
    """Expand the tiny contract and delegate every epistemic check unchanged."""

    if not is_revision_turn(turn):
        return qc._revision_response_base_compile(response, turn)
    parsed = response.get("parsed", response)
    if not isinstance(parsed, Mapping):
        return _adapter_rejection("revision-top-level-contract", parsed)
    if set(parsed) == {"abstain"} and parsed["abstain"] is True:
        revision = None
        decision = "abstain"
    elif set(parsed) == {"revision"} and isinstance(parsed["revision"], Mapping):
        revision = dict(parsed["revision"])
        relation_id = revision.pop("relation_evidence_id", None)
        prospective_id = revision.pop("prospective_evidence_id", None)
        if not isinstance(relation_id, str):
            return _adapter_rejection("revision-evidence-address-contract", parsed)
        evidence_ids = [relation_id]
        if is_prospective_revision_turn(turn):
            if not isinstance(prospective_id, str):
                return _adapter_rejection("revision-evidence-address-contract", parsed)
            evidence_ids.append(prospective_id)
        elif prospective_id is not None:
            return _adapter_rejection("premature-prospective-evidence-address", parsed)
        revision["evidence_ids"] = evidence_ids
        decision = "revision"
    else:
        return _adapter_rejection("revision-exclusive-branch", parsed)
    legacy = {
        "protocol": qc.RESPONSE_PROTOCOL,
        "request_id": turn.request_id,
        "basis_revision": turn.basis_revision,
        "schema_revision": revision,
        "explanation_set": None,
        "attention_contributions": [],
        "expansion_requests": [],
    }
    compiled = dict(qc._revision_response_base_compile(legacy, turn))
    compiled["revision_decision"] = decision
    return compiled


def revision_request_payload(
    qc: Any,
    turn: Any,
    qwen: Mapping[str, Any],
    *,
    visual_evidence: Sequence[Mapping[str, str]] = (),
) -> dict[str, Any]:
    """Use a short cognitive contract on revision turns; retain exact input."""

    if not is_revision_turn(turn):
        return qc._revision_response_base_request(
            turn, qwen, visual_evidence=visual_evidence
        )
    phase_rule = (
        "Set relation_evidence_id and prospective_evidence_id to the grammar-required addresses."
        if is_prospective_revision_turn(turn)
        else "This is a pre-probe grounding repair. Set relation_evidence_id to the grammar-required current relation-set address; no prospective evidence exists yet."
    )
    text = REVISION_PROMPT + phase_rule + "\n" + qc.stable_json(turn.document)
    content: str | list[dict[str, Any]]
    if visual_evidence:
        parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
        for item in visual_evidence:
            parts.append({"type": "text", "text": str(item["label"])})
            parts.append(
                {"type": "image_url", "image_url": {"url": str(item["data_url"])}}
            )
        content = parts
    else:
        content = text
    return {
        "model": qwen["model"],
        "messages": [{"role": "user", "content": content}],
        "temperature": qwen.get("temperature", 0),
        "top_p": qwen.get("top_p", 1),
        "seed": qwen.get("seed", 0),
        "max_tokens": qwen.get("revision_max_tokens", qwen.get("max_tokens", 900)),
        "thinking_budget_tokens": qwen.get(
            "revision_thinking_budget_tokens",
            qwen.get("thinking_budget_tokens", qwen.get("thinking_budget", 256)),
        ),
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "shared_attention_qwen_revision_v1_12",
                "strict": True,
                "schema": revision_response_schema(qc, turn),
            },
        },
    }


def schema_size_report(qc: Any, turn: Any) -> dict[str, Any]:
    """Deterministic byte and conservative chars/4 measurements."""

    legacy = json.dumps(
        qc._revision_response_base_schema(turn), sort_keys=True, separators=(",", ":")
    )
    compact = json.dumps(
        revision_response_schema(qc, turn), sort_keys=True, separators=(",", ":")
    )
    return {
        "legacy_schema_bytes": len(legacy.encode("utf-8")),
        "revision_schema_bytes": len(compact.encode("utf-8")),
        "legacy_schema_token_estimate_chars_div_4": (len(legacy) + 3) // 4,
        "revision_schema_token_estimate_chars_div_4": (len(compact) + 3) // 4,
        "byte_reduction_fraction": 1.0 - (len(compact) / len(legacy)),
    }


def install(qc: Any) -> None:
    """Install once onto the inherited cognition module."""

    if hasattr(qc, "_revision_response_base_schema"):
        return
    qc._revision_response_base_schema = qc.response_schema
    qc._revision_response_base_compile = qc.compile_response
    qc._revision_response_base_request = qc.request_payload
    qc.response_schema = lambda turn: revision_response_schema(qc, turn)
    qc.compile_response = lambda response, turn: compile_revision_response(
        qc, response, turn
    )
    qc.request_payload = lambda turn, qwen, visual_evidence=(): revision_request_payload(
        qc, turn, qwen, visual_evidence=visual_evidence
    )
