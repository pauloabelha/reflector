"""Bounded, action-free Qwen working memory for the one-action experiment."""

from __future__ import annotations

from dataclasses import replace
import copy
import json
import re
from typing import Any, Mapping


MAX_SCRATCHPAD_TOKENS = 1024
_R2_ACTION_TRACES: list[str] = []
ACTION_PROPOSAL = re.compile(
    r"\b(?:action|button|press|click|execute|choose\s+(?:an?\s+)?action|"
    r"select\s+(?:an?\s+)?action|move\s+(?:up|down|left|right))\b",
    re.IGNORECASE,
)


def _has_action_proposal(value: Any) -> bool:
    return bool(ACTION_PROPOSAL.search(json.dumps(value, ensure_ascii=True)))


def record_r2_action_trace(trace: str) -> None:
    """Keep observations in the ephemeral scratchpad channel, not the graph.

    The semantic graph has a deliberate action-token quarantine.  This helper
    is called after an external action settles and its data is appended only
    after ``build_turn`` has constructed and validated the canonical graph
    projection.
    """
    _R2_ACTION_TRACES.append(str(trace))
    del _R2_ACTION_TRACES[:-12]


def _latest_note(state: Any, workspace_id: str) -> Any | None:
    notes = [
        item
        for item in state.objects
        if item.kind == "working_note"
        and item.created_by == "qwen"
        and item.payload.get("workspace_id") == workspace_id
    ]
    return max(notes, key=lambda item: (item.created_revision, item.object_id), default=None)


def install(qc: Any) -> None:
    """Install an idempotent adapter around the frozen semantic-Qwen protocol."""

    if getattr(qc, "_one_action_scratchpad_installed", False):
        return
    qc._one_action_scratchpad_installed = True
    original_build_turn = qc.build_turn
    original_response_schema = qc.response_schema
    original_compile_response = qc.compile_response
    original_request_payload = qc.request_payload

    qc.PROMPT += """

TWO SEPARATE OUTPUT CHANNELS:
1. natural_language_scratchpad is bounded, unverified prose for your next
semantic turn. Rewrite it rather than appending a transcript. It is not
evidence and is never compiled as a workspace claim.
2. workspace_write is a compact structured, cited, defeasible explanation.
R2 alone owns formal schema binding and action selection. Never put an
environment action, direction, button, policy, or game identifier in either
channel. Do not serialize a schema, binding, attention table, or action policy.
"""

    def build_turn(state: Any, events: Any, orientation: Any, **kwargs: Any) -> Any:
        try:
            turn = original_build_turn(state, events, orientation, **kwargs)
        except Exception as error:
            # v1.12's optional revision-packet adapter assumes that every
            # evidence-return target began ambiguous. A uniquely grounded
            # target can legitimately violate that premise. Reject that
            # packet, preserve its reason, and build an ordinary bounded turn.
            fallback = getattr(qc, "_CAUSAL_PACKET_V112_BASE_BUILD_TURN", None)
            if fallback is None or "original ambiguity diagnosis is unavailable" not in str(error):
                raise
            turn = fallback(state, events, orientation, **kwargs)
            turn = replace(
                turn,
                document={
                    **turn.document,
                    "rejected_causal_packet": {
                        "reason": "unique-target-has-no-prior-ambiguity-diagnosis",
                        "empirical_claim": False,
                    },
                },
            )
        prior = _latest_note(state, turn.workspace_id)
        projection = None
        if prior is not None:
            projection = {
                "object_id": prior.object_id,
                "basis_revision": prior.payload.get("basis_revision"),
                "summary": prior.payload.get("summary", ""),
                "natural_language": prior.payload.get("natural_language", ""),
                "objective_hypothesis": prior.payload.get("objective_hypothesis", ""),
                "open_questions": list(prior.payload.get("open_questions", ())),
                "cited_ids": list(prior.payload.get("cited_ids", ())),
                "verified": False,
            }
        scratchpad_context = {
            "qwen_note": projection,
            "r2_action_traces": list(_R2_ACTION_TRACES),
        }
        return replace(turn, document={**turn.document, "prior_working_note": projection, "scratchpad_context": scratchpad_context})

    def note_schema(turn: Any) -> dict[str, Any]:
        _index, visible = qc._v14_visible(turn)
        visible_ids = sorted(visible)
        cited_item = {"enum": visible_ids} if visible_ids else {"type": "string", "maxLength": 0}
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["summary", "objective_hypothesis", "open_questions", "cited_ids"],
            "properties": {
                "summary": {"type": "string", "maxLength": 360},
                "objective_hypothesis": {"type": "string", "maxLength": 240},
                "open_questions": {
                    "type": "array", "maxItems": 2,
                    "items": {"type": "string", "maxLength": 160},
                },
                "cited_ids": {
                    "type": "array", "minItems": 1 if visible_ids else 0,
                    "maxItems": 4, "uniqueItems": True,
                    "items": cited_item,
                },
            },
        }

    def add_note_to_schema(schema: dict[str, Any], turn: Any) -> dict[str, Any]:
        output = copy.deepcopy(schema)
        if "oneOf" in output:
            output["oneOf"] = [add_note_to_schema(branch, turn) for branch in output["oneOf"]]
            return output
        if output.get("type") == "object" and isinstance(output.get("properties"), dict):
            output["properties"]["working_note"] = note_schema(turn)
            output["required"] = list(output.get("required", ()))
            if "working_note" not in output["required"]:
                output["required"].append("working_note")
        return output

    def response_schema(turn: Any) -> dict[str, Any]:
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["protocol", "request_id", "natural_language_scratchpad", "workspace_write"],
            "properties": {
                "protocol": {"const": turn.document["protocol"]},
                "request_id": {"const": turn.request_id},
                "natural_language_scratchpad": {"type": "string", "maxLength": 900},
                "workspace_write": note_schema(turn),
            },
        }

    def request_payload(turn: Any, qwen: Mapping[str, Any], **kwargs: Any) -> dict[str, Any]:
        request = original_request_payload(turn, qwen, **kwargs)
        request = copy.deepcopy(request)
        container = request["response_format"]["json_schema"]
        container["schema"] = response_schema(turn)
        return request

    def compile_response(response: Mapping[str, Any], turn: Any) -> dict[str, Any]:
        parsed = response.get("parsed", response)
        if not isinstance(parsed, Mapping):
            return original_compile_response(response, turn)
        prose = parsed.get("natural_language_scratchpad")
        note = parsed.get("workspace_write")
        stripped = dict(parsed)
        stripped.pop("natural_language_scratchpad", None)
        stripped.pop("workspace_write", None)
        envelope = dict(response)
        envelope["parsed"] = stripped
        expected = {"protocol", "request_id"}
        compact = set(str(key) for key in stripped) == expected
        compact = compact and stripped.get("protocol") == turn.document["protocol"]
        compact = compact and stripped.get("request_id") == turn.request_id
        compilation = {
            "valid_json_contract": bool(compact),
            "accepted": [],
            "rejected": [] if compact else [{"reason": "compact-hypothesis-contract"}],
            "explanation_alternative_count": 0,
            "schema_write_mode": "compact-working-hypothesis",
        }
        if not isinstance(prose, str) or not prose.strip():
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "natural-language-scratchpad-missing"}]}
        if note is None:
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "workspace-write-missing"}]}
        required = {"summary", "objective_hypothesis", "open_questions", "cited_ids"}
        if not isinstance(note, Mapping) or set(note) != required:
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "working-note-contract"}]}
        scratch_tokens = qc.GRAPH.estimate_tokens(prose)
        if _has_action_proposal(prose) or _has_action_proposal(note) or scratch_tokens > MAX_SCRATCHPAD_TOKENS:
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "working-note-safety-or-budget"}]}
        _index, visible = qc._v14_visible(turn)
        aliases = dict(turn.id_aliases)
        cited = list(note["cited_ids"])
        if any(not isinstance(item, str) or item not in visible for item in cited):
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "working-note-citation"}]}
        if not compilation.get("valid_json_contract"):
            return compilation
        real_citations = [aliases.get(item, item) for item in cited]
        payload = {
            **dict(note),
            "natural_language": prose.strip(),
            "cited_ids": real_citations,
            "workspace_id": turn.workspace_id,
            "basis_revision": turn.basis_revision,
            "verified": False,
            "token_count": scratch_tokens,
            "token_budget": MAX_SCRATCHPAD_TOKENS,
        }
        write = {
            "kind": "working_note",
            "local_ref": "working_note",
            "identity": {
                "workspace_id": turn.workspace_id,
                "basis_revision": turn.basis_revision,
                "content_hash": qc.stable_hash({"natural_language": prose, "workspace_write": note}),
            },
            "payload": payload,
            "dependency_ids": real_citations,
        }
        explanation = {
            "kind": "explanation",
            "local_ref": "working_hypothesis",
            "identity": {
                "workspace_id": turn.workspace_id,
                "basis_revision": turn.basis_revision,
                "content_hash": qc.stable_hash({"objective_hypothesis": note["objective_hypothesis"]}),
                "mode": "defeasible-working-hypothesis",
            },
            "payload": {
                "claim": note["objective_hypothesis"],
                "summary": note["summary"],
                "open_questions": list(note["open_questions"]),
                "status": "unverified",
                "epistemic_role": "candidate-model-for-goal-progress-or-information",
                "basis_revision": turn.basis_revision,
            },
            "dependency_ids": real_citations,
            "evidence": [],
            "support": 0,
        }
        accepted = [*compilation.get("accepted", ())]
        accepted.append(explanation)
        accepted.append(write)
        return {**compilation, "accepted": accepted, "working_note": payload}

    qc.build_turn = build_turn
    qc.response_schema = response_schema
    qc.request_payload = request_payload
    qc.compile_response = compile_response
