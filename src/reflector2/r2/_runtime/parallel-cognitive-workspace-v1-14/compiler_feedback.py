"""Persist rejected semantic revisions and compiler criticism in one workspace.

This adapter is intentionally split at the durable compilation boundary:

* ``wrap_compile_response`` attaches the *exact Qwen revision branch* and the
  compiler's exact structured rejection rows to the compilation blob.
* ``ingest_compiler_feedback`` writes an immutable Qwen attempt plus a
  kernel-provenance criticism into the epistemic graph and raises attention on
  the criticism for Qwen's next turn.

Neither object is environment evidence and this module creates no support,
refute, or invalidation edge.  The feedback says only "this executable write
failed this compiler check", never "this hypothesis is empirically false".
"""

from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Sequence


PROTOCOL = "compiler-revision-feedback-v1.14"
ATTEMPT_KIND = "qwen_revision_attempt"
CRITICISM_KIND = "compiler_criticism"
CRITICISM_STATUS = "compiler-rejected-revision"

_FORBIDDEN_KEY = re.compile(
    r"(?:^|_)(?:actions?|action_id|action_token|button|command|policy|games?|game_id)(?:$|_)",
    re.IGNORECASE,
)
_FORBIDDEN_TEXT = re.compile(
    r"(?:arc-action|\baction\b|\bbutton\b|\bcommand\b|\bpolicy\b|\bgame\b|\b(?:up|down|left|right)\b)",
    re.IGNORECASE,
)


class CompilerFeedbackError(RuntimeError):
    """Feedback cannot be represented without weakening its invariants."""


def is_action_blind(value: Any) -> bool:
    """Reject concrete control/game vocabulary anywhere in durable feedback."""

    if isinstance(value, Mapping):
        return all(
            not _FORBIDDEN_KEY.search(str(key)) and is_action_blind(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return all(is_action_blind(item) for item in value)
    return not (isinstance(value, str) and _FORBIDDEN_TEXT.search(value))


def _raw_revision(response: Mapping[str, Any]) -> Mapping[str, Any] | None:
    parsed = response.get("parsed", response)
    if not isinstance(parsed, Mapping):
        return None
    revision = parsed.get("revision")
    return revision if isinstance(revision, Mapping) else None


def attach_compiler_feedback(
    qc: Any,
    response: Mapping[str, Any],
    turn: Any,
    compilation: Mapping[str, Any],
) -> dict[str, Any]:
    """Attach exact rejected-revision material to a durable compilation.

    Malformed transport and explicit abstention are not semantic attempts.
    Inputs that contain forbidden control vocabulary are deliberately not
    reflected into the cognitive graph; the original response/compilation
    blobs remain authoritative for operational audit.
    """

    output = dict(compilation)
    task = turn.document.get("revision_task")
    raw = _raw_revision(response)
    rejected = compilation.get("rejected")
    accepted_schema = any(
        isinstance(item, Mapping) and item.get("kind") == "schema"
        for item in compilation.get("accepted", ())
    )
    if (
        not isinstance(task, Mapping)
        or raw is None
        or accepted_schema
        or not isinstance(rejected, list)
        or not rejected
    ):
        return output
    exact_rejections = [dict(item) for item in rejected if isinstance(item, Mapping)]
    if len(exact_rejections) != len(rejected):
        return output
    candidate = {
        "protocol": PROTOCOL,
        "request_id": turn.request_id,
        "basis_revision": turn.basis_revision,
        "basis_hash": turn.basis_hash,
        "raw_revision": dict(raw),
        "compiler_rejections": exact_rejections,
        "compilation_digest": qc.stable_hash(compilation),
        "lineage": {
            key: task.get(key)
            for key in (
                "chain_ref",
                "derivation_id",
                "semantic_target_id",
                "criticism_id",
                "criticism_status",
                "target_alpha_signature",
            )
        },
    }
    if not is_action_blind(candidate):
        return output
    candidate["feedback_digest"] = qc.stable_hash(candidate)
    output["compiler_feedback"] = candidate
    return output


def wrap_compile_response(qc: Any, fallback: Callable[..., Any]) -> Callable[..., Any]:
    """Return a compiler that durably retains eligible rejected revisions."""

    def compile_response(response: Mapping[str, Any], turn: Any) -> dict[str, Any]:
        compiled = fallback(response, turn)
        return attach_compiler_feedback(qc, response, turn, compiled)

    return compile_response


def _replace_ids(value: Any, aliases: Mapping[str, str]) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _replace_ids(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_ids(item, aliases) for item in value]
    if isinstance(value, tuple):
        return [_replace_ids(item, aliases) for item in value]
    return aliases.get(value, value) if isinstance(value, str) else value


def _ingest_object_once(
    eg: Any,
    state: Any,
    *,
    kind: str,
    created_by: str,
    identity: Mapping[str, Any],
    payload: Mapping[str, Any],
    dependency_ids: Sequence[str],
    event_key: str,
) -> tuple[Any, list[Any], str]:
    candidate = eg.make_object(
        kind=kind,
        created_by=created_by,
        created_revision=state.revision + 1,
        identity=identity,
        payload=payload,
        dependency_ids=dependency_ids,
    )
    existing = next(
        (item for item in state.objects if item.object_id == candidate.object_id), None
    )
    if existing is not None:
        if (
            existing.kind != kind
            or existing.created_by != created_by
            or existing.identity != dict(identity)
            or existing.payload != dict(payload)
            or existing.dependency_ids != tuple(sorted(set(dependency_ids)))
        ):
            raise CompilerFeedbackError("stable feedback object collision")
        return state, [], existing.object_id
    event = eg.object_event(
        state,
        kind=kind,
        created_by=created_by,
        identity=identity,
        payload=payload,
        dependency_ids=dependency_ids,
        event_key=event_key,
    )
    return eg.apply_event(state, event), [event], candidate.object_id


def _existing_dependencies(
    state: Any, values: Sequence[Any]
) -> tuple[str, ...]:
    known = {item.object_id for item in state.objects}
    return tuple(sorted({str(value) for value in values if str(value) in known}))


def ingest_compiler_feedback(
    eg: Any,
    qc: Any,
    state: Any,
    turn: Any,
    compilation: Mapping[str, Any],
    *,
    response_id: str,
    attention_weight: int = 100,
) -> Any:
    """Ingest one attached feedback unit and return ``eg.IngestResult``.

    The returned events are suitable for the runner's ordinary atomic graph
    persistence path.  Calling this function again is idempotent.
    """

    feedback = compilation.get("compiler_feedback")
    if not isinstance(feedback, Mapping):
        return eg.IngestResult(state, ())
    without_digest = {key: value for key, value in feedback.items() if key != "feedback_digest"}
    if (
        feedback.get("protocol") != PROTOCOL
        or feedback.get("feedback_digest") != qc.stable_hash(without_digest)
        or not is_action_blind(feedback)
    ):
        raise CompilerFeedbackError("compiler feedback contract mismatch")
    if not 1 <= int(attention_weight) <= 100:
        raise CompilerFeedbackError("attention weight must be in [1,100]")

    alias_to_real = dict(turn.id_aliases)
    canonical_lineage = _replace_ids(feedback["lineage"], alias_to_real)
    target_id = str(canonical_lineage.get("semantic_target_id"))
    lineage_dependencies = _existing_dependencies(
        state,
        (
            target_id,
            canonical_lineage.get("derivation_id"),
            canonical_lineage.get("criticism_id"),
        ),
    )
    if target_id not in lineage_dependencies:
        raise CompilerFeedbackError("revision target is absent from graph")

    canonical_revision = _replace_ids(feedback["raw_revision"], alias_to_real)
    cited = []
    for key in ("relation_evidence_id", "prospective_evidence_id"):
        if isinstance(canonical_revision.get(key), str):
            cited.append(canonical_revision[key])
    if isinstance(canonical_revision.get("evidence_ids"), list):
        cited.extend(canonical_revision["evidence_ids"])
    attempt_dependencies = _existing_dependencies(
        state, (*lineage_dependencies, *cited)
    )

    events: list[Any] = []
    attempt_identity = {
        "response_id": str(response_id),
        "request_id": str(feedback["request_id"]),
        "target_id": target_id,
        "attempt_digest": qc.stable_hash(feedback["raw_revision"]),
    }
    attempt_payload = {
        "protocol": PROTOCOL,
        "rendered_revision": dict(feedback["raw_revision"]),
        "canonical_revision": canonical_revision,
        "lineage": canonical_lineage,
        "basis_revision": feedback["basis_revision"],
        "basis_hash": feedback["basis_hash"],
    }
    state, added, attempt_id = _ingest_object_once(
        eg,
        state,
        kind=ATTEMPT_KIND,
        created_by="qwen",
        identity=attempt_identity,
        payload=attempt_payload,
        dependency_ids=attempt_dependencies,
        event_key=f"qwen-revision-attempt:{response_id}:{feedback['feedback_digest']}",
    )
    events.extend(added)

    criticism_identity = {
        "attempt_id": attempt_id,
        "target_id": target_id,
        "compilation_digest": feedback["compilation_digest"],
        "status": CRITICISM_STATUS,
    }
    criticism_payload = {
        "protocol": PROTOCOL,
        "status": CRITICISM_STATUS,
        "compiler_rejections": list(feedback["compiler_rejections"]),
        "attempt_digest": attempt_identity["attempt_digest"],
        "lineage": canonical_lineage,
        "world_model_only": True,
    }
    criticism_dependencies = tuple(
        sorted(set((attempt_id, *attempt_dependencies)))
    )
    state, added, criticism_id = _ingest_object_once(
        eg,
        state,
        kind=CRITICISM_KIND,
        created_by="kernel",
        identity=criticism_identity,
        payload=criticism_payload,
        dependency_ids=criticism_dependencies,
        event_key=f"compiler-criticism:{response_id}:{feedback['compilation_digest']}",
    )
    events.extend(added)

    candidate = eg.make_attention(
        worker="qwen",
        object_id=criticism_id,
        weight=int(attention_weight),
        channel="inspect",
        basis_ids=(attempt_id,),
        created_revision=state.revision + 1,
        contribution_key=f"compiler-feedback:{response_id}:{criticism_id}",
    )
    if not eg.has_attention(state, candidate.attention_id):
        event = eg.attention_event(
            state,
            worker="qwen",
            object_id=criticism_id,
            weight=int(attention_weight),
            channel="inspect",
            basis_ids=(attempt_id,),
            contribution_key=f"compiler-feedback:{response_id}:{criticism_id}",
        )
        state = eg.apply_event(state, event)
        events.append(event)
    return eg.IngestResult(
        state,
        tuple(events),
        object_ids=(attempt_id, criticism_id),
    )


def wrap_apply_qwen_compilation(
    eg: Any,
    qc: Any,
    fallback: Callable[..., Any],
    persist_ingest: Callable[[Any, str, Any], Any],
) -> Callable[..., Any]:
    """Persist feedback before the runner appends its integrated-task marker.

    This ordering makes crash recovery safe: a crash before the marker replays
    this idempotent prelude; a crash after the marker necessarily follows a
    durable feedback batch.
    """

    def apply_qwen_compilation(
        root: Any,
        workspace_id: str,
        state: Any,
        task_id: str,
        turn: Any,
        compilation: Mapping[str, Any],
        profile: Mapping[str, Any],
        *,
        action_count: int,
    ) -> Any:
        feedback = ingest_compiler_feedback(
            eg,
            qc,
            state,
            turn,
            compilation,
            response_id=task_id,
        )
        if feedback.events:
            state = persist_ingest(root, workspace_id, feedback)
        return fallback(
            root,
            workspace_id,
            state,
            task_id,
            turn,
            compilation,
            profile,
            action_count=action_count,
        )

    return apply_qwen_compilation


def install(qc: Any) -> Any:
    """Idempotently retain rejected-revision data in compilation blobs."""

    if getattr(qc, "_COMPILER_FEEDBACK_V114_INSTALLED", False):
        return qc
    qc._COMPILER_FEEDBACK_V114_BASE_COMPILE = qc.compile_response
    qc.compile_response = wrap_compile_response(qc, qc.compile_response)
    qc._COMPILER_FEEDBACK_V114_INSTALLED = True
    return qc


__all__ = [
    "ATTEMPT_KIND",
    "CRITICISM_KIND",
    "CRITICISM_STATUS",
    "CompilerFeedbackError",
    "PROTOCOL",
    "attach_compiler_feedback",
    "ingest_compiler_feedback",
    "install",
    "is_action_blind",
    "wrap_apply_qwen_compilation",
    "wrap_compile_response",
]
