"""Bounded Qwen working memory for the one-action experiment."""

from __future__ import annotations

from dataclasses import replace
import copy
import hashlib
import json
import re
from typing import Any, Mapping


MAX_SCRATCHPAD_TOKENS = 1024
MAX_R2_SEMANTIC_PROJECTION_BYTES = 12000
EXPLANATION_CONSOLIDATION_PROTOCOL = "explanation-consolidation-v1"
FRESH_BINDING_AUTHORITY = "fresh-binding-probe-only"
MANDATORY_NUISANCE_DIMENSIONS = (
    "absolute_coordinates",
    "palette_values",
    "situated_object_identity",
    "prior_role_bindings",
    "prior_empirical_support",
    "prior_intervention_identity",
)
_R2_ACTION_TRACES: list[str] = []
_R2_SEMANTIC_PROJECTION: dict[str, Any] | None = None
_R2_TRANSITION_OBSERVATION: dict[str, Any] | None = None
CONTROL_PAYLOAD_KINDS = frozenset({"action_proposal", "action_settlement", "action_trace", "transition"})
ACTION_PROPOSAL = re.compile(
    r"\b(?:action\s*(?:#?\d+|id\b)|button|press|click|execute\s+(?:an?\s+)?action|"
    r"choose\s+(?:an?\s+)?action|select\s+(?:an?\s+)?action|"
    r"move\s+(?:up|down|left|right))\b",
    re.IGNORECASE,
)
OBSERVED_ACTION_OUTCOME = re.compile(
    r"\b(?:no\s+visible\s+change|visible\s+(?:change|configuration\s+changed)|"
    r"observation\s+(?:changed|remained)|adjusted|altered|changed|confirmed|decreased|"
    r"failed|increased|left|moved|occurred|produced|reduced|remained|remains|resolved|"
    r"resulted|shifted)\b",
    re.IGNORECASE,
)
FUTURE_OR_MODAL_CONTROL = re.compile(
    r"\b(?:could|future|may|might|must|next|plan|propose|recommend|should|try|will|would)\b",
    re.IGNORECASE,
)
RETROSPECTIVE_ACTION_WINDOW = 140
CONSOLIDATION_SITUATED_DETAIL = re.compile(
    r"(?:\b(?:black|blue|red|green|yellow|gr[ae]y|magenta|orange|cyan|"
    r"maroon|white|purple|brown)\b|\bf[0-9]{2,}\b|\b(?:eo|binding):|"
    r"\blevel\s*[0-9]+\b|\b(?:row|column|col|x|y)\s*[=:]\s*-?[0-9]+|"
    r"[\[(]\s*-?[0-9]+\s*,\s*-?[0-9]+\s*[\])])",
    re.IGNORECASE,
)


def _is_coordinated_historical_action_list(
    text: str,
    action_match: re.Match[str],
    outcome_match: re.Match[str],
) -> bool:
    """Recognize a parenthesized action list sharing one observed outcome."""

    if outcome_match.start() < action_match.end():
        return False
    open_paren = text.rfind("(", 0, action_match.start())
    close_paren = text.find(")", action_match.end(), outcome_match.start())
    if open_paren < 0 or close_paren < 0:
        return False
    governor = text[max(0, open_paren - 48):open_paren]
    return bool(re.search(r"\bactions\s*$", governor, re.IGNORECASE))


def _outcome_is_causally_adjacent(
    text: str,
    action_match: re.Match[str],
    outcome_match: re.Match[str],
) -> bool:
    """Require a short, unambiguous link from one opaque action to an outcome."""

    if outcome_match.end() <= action_match.start():
        gap = text[outcome_match.end():action_match.start()]
        if len(gap) > RETROSPECTIVE_ACTION_WINDOW or any(
            boundary in gap for boundary in (".", "!", "?", ";", "\n")
        ):
            return False
    elif outcome_match.start() >= action_match.end():
        gap = text[action_match.end():outcome_match.start()]
        if len(gap) > RETROSPECTIVE_ACTION_WINDOW:
            return False
        # An outcome may begin the immediately following sentence, but it may
        # not inherit across multiple claims or a semicolon/new paragraph.
        if sum(gap.count(boundary) for boundary in (".", "!", "?")) > 1 or any(
            boundary in gap for boundary in (";", "\n")
        ):
            return False
    else:
        return False
    if FUTURE_OR_MODAL_CONTROL.search(gap):
        return False
    return bool(
        not ACTION_PROPOSAL.search(gap)
        or _is_coordinated_historical_action_list(
            text,
            action_match,
            outcome_match,
        )
    )


def _is_bounded_retrospective_action(text: str, match: re.Match[str]) -> bool:
    """Accept an opaque action mention only as bounded observed history.

    Directive/control matches are never eligible.  A bare Action-N or move
    direction is historical only when a nearby observed outcome is connected
    without another action, modal/future control language, or claim boundary.
    """

    token = match.group(0)
    if not re.fullmatch(
        r"(?:action\s*#?\d+|move\s+(?:up|down|left|right))",
        token,
        re.IGNORECASE,
    ):
        return False
    window_start = max(0, match.start() - RETROSPECTIVE_ACTION_WINDOW)
    window_end = min(len(text), match.end() + RETROSPECTIVE_ACTION_WINDOW)
    return any(
        _outcome_is_causally_adjacent(text, match, outcome)
        for outcome in OBSERVED_ACTION_OUTCOME.finditer(
            text,
            window_start,
            window_end,
        )
    )


def _text_has_action_proposal(text: str) -> bool:
    return any(
        not _is_bounded_retrospective_action(text, match)
        for match in ACTION_PROPOSAL.finditer(text)
    )


def _has_action_proposal(value: Any) -> bool:
    if isinstance(value, str):
        return _text_has_action_proposal(value)
    if isinstance(value, Mapping):
        return any(_has_action_proposal(item) for item in value.values())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_has_action_proposal(item) for item in value)
    return _text_has_action_proposal(json.dumps(value, ensure_ascii=True))


def _has_consolidation_situated_detail(value: Any) -> bool:
    if isinstance(value, str):
        return bool(CONSOLIDATION_SITUATED_DETAIL.search(value))
    if isinstance(value, Mapping):
        return any(_has_consolidation_situated_detail(item) for item in value.values())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(_has_consolidation_situated_detail(item) for item in value)
    return False


def _canonical_action_id(value: Any) -> str | None:
    """Render an observed opaque action without assigning it semantics."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and value >= 0:
        return f"ACTION_{value}"
    if isinstance(value, str) and re.fullmatch(r"ACTION_[0-9]+", value):
        return value
    return None


def _canonical_goal_proposal_key(value: Any) -> str:
    """Canonicalize Qwen's proposal without interpreting or repairing it."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _transition_evidence_ref(document: Mapping[str, Any]) -> str | None:
    transition = document.get("scratchpad_context", {}).get("r2_transition_observation") or {}
    evidence_ref = transition.get("evidence_ref")
    return str(evidence_ref) if isinstance(evidence_ref, str) and evidence_ref else None


def _latest_level_boundary(state: Any) -> Any | None:
    """Return the latest completed-context boundary in the canonical graph."""

    boundaries = [
        item for item in getattr(state, "objects", ())
        if item.kind == "transition"
        and item.created_by == "environment"
        and item.payload.get("level_transition") is True
        and item.payload.get("boundary_kind") == "level-advance"
    ]
    return max(
        boundaries,
        key=lambda item: (item.created_revision, item.object_id),
        default=None,
    )


def _consolidation_task(state: Any, workspace_id: str, qc: Any) -> dict[str, Any] | None:
    """Build one bounded, action-free abstraction task over a settled context.

    Only graph objects created before the level boundary are eligible semantic
    sources.  The boundary and its environment evidence are included solely to
    prove that the source context completed; the successor board is never
    projected into the abstraction packet.
    """

    boundary = _latest_level_boundary(state)
    if boundary is None:
        return None
    workspace_ref = _workspace_ref(qc, workspace_id)
    if any(
        item.kind == "explanation_consolidation"
        and item.created_by == "qwen"
        and item.payload.get("workspace_ref") == workspace_ref
        and item.payload.get("source_boundary_ref") == boundary.object_id
        for item in getattr(state, "objects", ())
    ):
        return None

    objects = tuple(getattr(state, "objects", ()))
    evidence = [
        item for item in objects
        if item.kind == "environment_evidence"
        and item.created_by == "environment"
        and boundary.object_id in item.dependency_ids
        and int(item.payload.get("level_delta") or 0) > 0
    ]
    evidence.sort(key=lambda item: (item.created_revision, item.object_id))
    prior_notes = [
        item for item in objects
        if item.kind == "working_note"
        and item.created_by == "qwen"
        and item.created_revision < boundary.created_revision
        and item.payload.get("workspace_ref") == workspace_ref
    ]
    prior_note = max(
        prior_notes,
        key=lambda item: (item.created_revision, item.object_id),
        default=None,
    )
    explanations = [
        item for item in objects
        if item.created_revision < boundary.created_revision
        and item.kind in {"control_explanation", "explanation"}
    ]
    explanations.sort(key=lambda item: (item.created_revision, item.object_id))
    explanations = explanations[-6:]
    explanation_projection = []
    for item in explanations:
        payload = item.payload
        explanation_projection.append({
            "source_ref": item.object_id,
            "kind": item.kind,
            "epistemic_status": payload.get("epistemic_status") or payload.get("status"),
            "claim": payload.get("claim"),
            "goal": copy.deepcopy(payload.get("goal")),
            "goal_proposals": copy.deepcopy(payload.get("goal_proposals", ())),
            "epistemic_evaluation": copy.deepcopy(payload.get("epistemic_evaluation")),
        })

    eligible_edges = [
        edge for edge in getattr(state, "edges", ())
        if edge.kind in {"supports", "refutes"}
        and edge.created_revision < boundary.created_revision
    ]
    eligible_edges.sort(
        key=lambda edge: (
            edge.created_revision, edge.kind, edge.source_id, edge.target_id,
        )
    )
    eligible_edges = eligible_edges[-8:]
    settlements = [{
        "kind": edge.kind,
        "evidence_ref": edge.source_id,
        "target_ref": edge.target_id,
    } for edge in eligible_edges]
    source_refs = {
        boundary.object_id,
        *(item.object_id for item in evidence),
        *(item.object_id for item in explanations),
        *((prior_note.object_id,) if prior_note is not None else ()),
        *(edge.source_id for edge in eligible_edges),
        *(edge.target_id for edge in eligible_edges),
    }
    existing_ids = {item.object_id for item in objects}
    source_refs = sorted(source_refs & existing_ids)
    context_index = sum(
        item.kind == "transition"
        and item.created_by == "environment"
        and item.payload.get("level_transition") is True
        for item in objects
    )
    return {
        "protocol": EXPLANATION_CONSOLIDATION_PROTOCOL,
        "operation": "reflective-abstraction",
        "projection_mode": "abstract-explanation-projection",
        "source_context_index": context_index,
        "source_boundary_ref": boundary.object_id,
        "source_evidence_refs": source_refs,
        "prior_semantic_note": None if prior_note is None else {
            "source_ref": prior_note.object_id,
            "goal_proposals": copy.deepcopy(prior_note.payload.get("goal_proposals", ())),
            "abductive_compositions": copy.deepcopy(prior_note.payload.get("abductive_compositions", ())),
        },
        "settled_explanations": explanation_projection,
        "settled_judgments": settlements,
        "abstraction_question": (
            "What is the smallest useful R2 schema fragment that could generate "
            "the settled structure after nuisance details are quotiented out?"
        ),
        "response_instruction": (
            "Return decision=propose with exactly one abstraction and exactly "
            "one referenced goal_proposal, or decision=abstain with both "
            "abstractions=[] and goal_proposals=[]; never repeat an array item. "
            "Project the abstract explanation into a future context: preserve "
            "its relational goal, typed roles, potential, terminal condition, "
            "and applicability conditions when supported, while leaving ports "
            "open for fresh binding and mechanism accommodation. This is not a "
            "game lesson, route, or next-action request. Reuse only an "
            "action-free goal proposal from this response."
        ),
        "mandatory_nuisance_quotient": list(MANDATORY_NUISANCE_DIMENSIONS),
        "authority": {
            "qwen": "propose-ungrounded-reusable-schema-or-abstain",
            "r2": "fresh-bind-specialize-test-or-discard",
            "environment": "sole-empirical-settlement-authority",
        },
        "transfer_contract": {
            "schema_definition": "project-and-fresh-bind",
            "empirical_support": "reset",
            "bindings": "reset",
            "role_identities": "reset",
            "potentials": "reset",
            "intervention_applicability": "reset",
            "progress_authority": "reset",
        },
    }


def explanation_consolidation_due(state: Any, workspace_id: str, qc: Any) -> bool:
    """Demand exactly one accepted consolidation per completed context."""

    return _consolidation_task(state, workspace_id, qc) is not None


def _semantic_failure_signals(document: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Return only explicit R2 failures that can justify semantic revision.

    A scheduler tick, a new observation, an open mechanism, and an open shadow
    are not failures.  Nor does a refutation retire a proposal that R2 still
    reports as confirmed or progress-eligible.  This function only routes
    R2/environment judgments; it never interprets a goal proposal itself.
    """
    context = document.get("scratchpad_context", {})
    feedback = context.get("r2_semantic_projection") or {}
    signals: list[dict[str, Any]] = []
    explanations = [
        feedback.get("active_explanation"),
        *feedback.get("competing_explanations", ()),
    ]
    supported = any(
        isinstance(item, Mapping)
        and (
            item.get("control_status") == "PROGRESS_ELIGIBLE"
            or int(item.get("confirmations") or 0) > 0
            or int((item.get("epistemic_evaluation") or {}).get("confirmations") or 0) > 0
        )
        for item in explanations
    )
    rejected = [
        item for item in feedback.get("rejected_semantic_proposals", ())
        if isinstance(item, Mapping)
    ]
    if rejected and not supported:
        reasons = sorted({
            str(item.get("reason") or item.get("r2_grounding_status") or "r2-rejected")
            for item in rejected
        })
        signals.append({
            "kind": "r2-semantic-proposal-rejected",
            "count": len(rejected),
            "reason_digests": [
                hashlib.sha256(item.encode("utf-8")).hexdigest()[:20]
                for item in reasons
            ],
        })

    transition = context.get("r2_transition_observation") or {}
    settlement = feedback.get("latest_settlement") or transition.get("prediction_settlement") or {}
    if settlement.get("adjudication") == "refuted" and not supported:
        signals.append({"kind": "environment-prediction-refuted"})
    return tuple(signals)


def _minimal_support_fields(explanation: Mapping[str, Any]) -> dict[str, Any]:
    """Retain only the fields that prevent false semantic-failure routing."""

    retained = {
        key: explanation[key]
        for key in ("control_status", "confirmations")
        if key in explanation
    }
    evaluation = explanation.get("epistemic_evaluation")
    if isinstance(evaluation, Mapping) and "confirmations" in evaluation:
        retained["epistemic_evaluation"] = {
            "confirmations": evaluation["confirmations"],
        }
    return retained


def _action_evidence_refs(document: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """Index action-specific R2 evidence exposed in this semantic turn.

    Prior aliases contribute only their already-validated citations, which
    permits defeasible preservation or revision without turning the alias into
    evidence. New actions still require current-episode R2 transition or
    causal-effect evidence.
    """
    context = document.get("scratchpad_context", {})
    refs: dict[str, set[str]] = {}

    def add(action: Any, *values: Any) -> None:
        action_id = _canonical_action_id(action)
        if action_id is None:
            return
        bucket = refs.setdefault(action_id, set())
        bucket.update(str(value) for value in values if isinstance(value, str) and value)

    transition = context.get("r2_transition_observation") or {}
    settlement = transition.get("prediction_settlement") or {}
    add(
        transition.get("action"), transition.get("evidence_ref"),
        settlement.get("explanation_binding_id"),
    )
    for effect in settlement.get("learned_effects", ()):
        if isinstance(effect, Mapping):
            add(transition.get("action"), effect.get("trajectory_id"), effect.get("region_type"))

    feedback = context.get("r2_semantic_projection") or {}
    explanations = [feedback.get("active_explanation"), *feedback.get("competing_explanations", ())]
    for explanation in explanations:
        if not isinstance(explanation, Mapping):
            continue
        mechanism = explanation.get("mechanism") or {}
        add(mechanism.get("action"), mechanism.get("causal_effect_binding_id"))

    prior = context.get("qwen_note") or {}
    for alias in prior.get("action_aliases", ()):
        if isinstance(alias, Mapping):
            add(alias.get("action_id"), *alias.get("evidence_refs", ()))
    return {action_id: tuple(sorted(values)) for action_id, values in sorted(refs.items()) if values}


def record_r2_action_trace(trace: str) -> None:
    """Keep observations in the ephemeral scratchpad channel, not the graph.

    The semantic graph has a deliberate action-token quarantine.  This helper
    is called after an external action settles and its data is appended only
    after ``build_turn`` has constructed and validated the canonical graph
    projection.
    """
    _R2_ACTION_TRACES.append(str(trace))
    del _R2_ACTION_TRACES[:-12]


def record_r2_semantic_projection(projection: Mapping[str, Any]) -> dict[str, Any]:
    """Publish a bounded read-only attention cut for Semantic Qwen."""
    global _R2_SEMANTIC_PROJECTION
    candidate = copy.deepcopy(dict(projection))
    if len(json.dumps(candidate, sort_keys=True, separators=(",", ":"))) > MAX_R2_SEMANTIC_PROJECTION_BYTES:
        candidate["competing_explanations"] = candidate.get("competing_explanations", [])[:2]
        candidate["salient_structural_bindings"] = candidate.get("salient_structural_bindings", [])[:8]
        candidate["open_shadows"] = candidate.get("open_shadows", [])[:6]
        candidate["rejected_semantic_proposals"] = candidate.get("rejected_semantic_proposals", [])[:2]
        candidate["categorical_comparisons"] = candidate.get("categorical_comparisons", [])[:8]
        candidate["temporal_comparisons"] = candidate.get("temporal_comparisons", [])[:6]
        candidate["grounded_abductions"] = candidate.get("grounded_abductions", [])[:4]
        candidate["rejected_abductions"] = candidate.get("rejected_abductions", [])[:4]
    if len(json.dumps(candidate, sort_keys=True, separators=(",", ":"))) > MAX_R2_SEMANTIC_PROJECTION_BYTES:
        active = candidate.get("active_explanation") or {}
        settlement = candidate.get("latest_settlement") or {}
        candidate = {
            "protocol": candidate.get("protocol"),
            "authority": candidate.get("authority"),
            "frame_digest": candidate.get("frame_digest"),
            "active_explanation": {
                **{
                    key: active.get(key)
                    for key in ("binding_id", "verb", "epistemic_status", "verb_status", "potential", "mechanism")
                    if key in active
                },
                **_minimal_support_fields(active),
            },
            "latest_settlement": {
                key: settlement.get(key)
                for key in ("explanation_binding_id", "adjudication", "actual_progress")
                if key in settlement
            } or None,
            "schema_summary": candidate.get("schema_summary"),
            "categorical_comparisons": [
                {key: item.get(key) for key in ("binding_id", "schema_id", "type")}
                for item in candidate.get("categorical_comparisons", [])[:8]
            ],
            "grounded_abductions": [
                {key: item.get(key) for key in ("local_ref", "binding_id", "schema_id", "component_schema_ids", "epistemic_status")}
                for item in candidate.get("grounded_abductions", [])[:4]
            ],
            "projection_truncated": True,
        }
    if len(json.dumps(candidate, sort_keys=True, separators=(",", ":"))) > MAX_R2_SEMANTIC_PROJECTION_BYTES:
        active = candidate.get("active_explanation", {})
        candidate["active_explanation"] = {
            **{
                key: active.get(key)
                for key in ("binding_id", "verb", "epistemic_status")
                if key in active
            },
            **_minimal_support_fields(active),
        }
    _R2_SEMANTIC_PROJECTION = candidate
    return copy.deepcopy(candidate)


def record_r2_transition_observation(
    *, action: int, observation_changed: bool, outcome: str, trace: str,
    settlement: Mapping[str, Any] | None,
) -> None:
    """Bind the observed intervention to its structured successor evidence."""
    global _R2_TRANSITION_OBSERVATION
    adjudication = dict(settlement or {})
    observation = {
        "role": "observed-history-not-action-proposal",
        "action": int(action),
        "observation_changed": bool(observation_changed),
        "outcome": str(outcome),
        "r2_observation_trace": str(trace)[:1000],
        "prediction_settlement": {
            key: adjudication.get(key)
            for key in (
                "explanation_binding_id", "adjudication", "actual_progress",
                "learned_effects",
            )
            if key in adjudication
        },
    }
    digest = hashlib.sha256(
        json.dumps(observation, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:20]
    _R2_TRANSITION_OBSERVATION = {
        **observation,
        "evidence_ref": f"r2-transition:{digest}",
    }


def causal_visual_evidence(items: list[dict[str, str]]) -> list[dict[str, str]]:
    """Make visual temporal order an explicit, checked protocol invariant."""
    if len(items) == 1:
        current = dict(items[0])
        if not current.get("label", "").startswith("CURRENT_FRAME"):
            raise ValueError("frame-zero visual evidence must contain only CURRENT_FRAME")
        current["label"] = current["label"].replace(
            "CURRENT_FRAME", "CAUSAL_UNIT_CURRENT_FRAME order=1/1 predecessor=none", 1,
        )
        return [current]
    if len(items) < 2:
        raise ValueError("visual evidence must contain a current frame")
    previous, current = dict(items[0]), dict(items[1])
    if not previous.get("label", "").startswith("IMMEDIATELY_PRECEDING_FRAME"):
        raise ValueError("post-action visual evidence must begin with the predecessor")
    if not current.get("label", "").startswith("CURRENT_FRAME"):
        raise ValueError("post-action visual evidence must place current frame second")
    previous["label"] = previous["label"].replace(
        "IMMEDIATELY_PRECEDING_FRAME", "CAUSAL_UNIT_PREVIOUS_FRAME order=1/2", 1,
    )
    current["label"] = current["label"].replace(
        "CURRENT_FRAME", "CAUSAL_UNIT_CURRENT_FRAME order=2/2", 1,
    )
    # The base retriever already selects at most one older structural frame;
    # enforce that bound here so no visual transcript can accumulate.
    return [previous, current, *[dict(item) for item in items[2:3]]]


def reset_episode_context() -> None:
    """Prevent action traces and semantic conclusions crossing episodes."""
    global _R2_SEMANTIC_PROJECTION, _R2_TRANSITION_OBSERVATION
    _R2_ACTION_TRACES.clear()
    _R2_SEMANTIC_PROJECTION = None
    _R2_TRANSITION_OBSERVATION = None


def advance_level_context() -> None:
    """Discard frame-local semantic projections, retaining the game note."""
    global _R2_SEMANTIC_PROJECTION, _R2_TRANSITION_OBSERVATION
    _R2_ACTION_TRACES.clear()
    _R2_SEMANTIC_PROJECTION = None
    _R2_TRANSITION_OBSERVATION = None


def retry_level_context() -> None:
    """Discard failed-attempt situated evidence, retaining the game note."""
    advance_level_context()


def alias_revision_due(state: Any, workspace_id: str, qc: Any) -> bool:
    """Request one semantic revision when a newly observed action lacks a gloss."""
    transition = _R2_TRANSITION_OBSERVATION or {}
    action_id = _canonical_action_id(transition.get("action"))
    if action_id is None or not transition.get("evidence_ref"):
        return False
    prior = _latest_note(state, workspace_id, qc)
    named = {
        _canonical_action_id(item.get("action_id"))
        for item in (() if prior is None else prior.payload.get("action_aliases", ()))
        if isinstance(item, Mapping)
    }
    return action_id not in named


def initial_semantics_due(state: Any, workspace_id: str, qc: Any) -> bool:
    """Keep initial Qwen semantics due until one valid note is canonical."""

    workspace_ref = _workspace_ref(qc, workspace_id)
    invalidated: set[str] = set()
    graph = getattr(qc, "GRAPH", None)
    invalidated_ids = getattr(graph, "invalidated_ids", None)
    if callable(invalidated_ids):
        invalidated = {str(value) for value in invalidated_ids(state)}
    return not any(
        item.kind == "working_note"
        and item.created_by == "qwen"
        and item.object_id not in invalidated
        and item.payload.get("workspace_ref") == workspace_ref
        for item in state.objects
    )


def semantic_failure_revision_due() -> bool:
    """Request Qwen only for explicit, unsupported R2 semantic failure.

    The same failure classifier enforces the compile-time stagnation contract,
    so scheduling cannot reinterpret open, mechanism-observed, confirmed, or
    progress-eligible evidence as a semantic rejection.
    """

    document = {
        "scratchpad_context": {
            "r2_semantic_projection": _R2_SEMANTIC_PROJECTION,
            "r2_transition_observation": _R2_TRANSITION_OBSERVATION,
        }
    }
    return bool(_semantic_failure_signals(document))


def semantic_control_projection(kind: str, payload: Mapping[str, Any], digest: str) -> tuple[dict[str, Any], list[str]] | None:
    """Project control artifacts without exposing intervention tokens to Qwen.

    The canonical object remains untouched in the authoritative ledger. Qwen
    receives only outcome fields that can bear on semantic goal relevance.
    """
    if kind not in CONTROL_PAYLOAD_KINDS:
        return None
    retained = {
        key: payload[key]
        for key in ("status", "observation_changed", "level_delta", "levels_completed")
        if key in payload
    }
    retained["canonical_payload_digest"] = digest
    retained["control_details"] = "quarantined-from-semantic-projection"
    return retained, [key for key in payload if key not in retained]


def _workspace_ref(qc: Any, workspace_id: str) -> str:
    return f"ws:{qc.stable_hash({'workspace': str(workspace_id)})[:16]}"


def _latest_note(state: Any, workspace_id: str, qc: Any) -> Any | None:
    workspace_ref = _workspace_ref(qc, workspace_id)
    notes = [
        item
        for item in state.objects
        if item.kind == "working_note"
        and item.created_by == "qwen"
        and item.payload.get("workspace_ref") == workspace_ref
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
    original_payload_projection = getattr(qc, "_payload_projection", None)

    if callable(original_payload_projection):
        def payload_projection(kind: str, payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
            quarantined = semantic_control_projection(
                kind, payload, qc.stable_hash(dict(payload))[:16]
            )
            if quarantined is not None:
                return quarantined
            projected, omitted = original_payload_projection(kind, payload)
            if kind == "working_note" and "action_aliases" in projected:
                # Aliases are reintroduced below through prior_working_note and
                # scratchpad_context.  They must not enter the canonical graph
                # projection, whose action-token quarantine remains absolute.
                projected = dict(projected)
                projected.pop("action_aliases", None)
                omitted = [*omitted, "action_aliases"]
            return projected, omitted

        qc._payload_projection = payload_projection

    qc.PROMPT = qc.PROMPT.replace(
        "11. A schema can enter the control gate only with Decrease or Increase of TranslationAlignmentResidual. Explanation claims may use the broader semantic vocabulary but do not directly control.",
        "11. No measure is privileged as a goal. Propose an action-free goal schema; R2 alone decides whether its observable can be grounded, measured, and used for control.",
    )

    qc.PROMPT += """

TWO SEPARATE OUTPUT CHANNELS:
1. natural_language_scratchpad is bounded, unverified prose for your next
semantic turn. Rewrite it rather than appending a transcript. It is not
evidence and is never compiled as a workspace claim.
On every post-action turn, begin from the latest causal visual unit and R2
feedback. State what the latest observation established, contradicted, or left
open. Do not repeat the frame-0 description or copy the prior prose. The prior
prose is intentionally unavailable; its digest only detects failed rewrites.
2. workspace_write is a compact structured, cited, defeasible explanation.
R2 alone owns formal schema binding and action selection. Propose one to three
action-free prospective verb schemas through goal_proposals. Each proposal
names a reusable verb such as fit, touch, collect, avoid, reveal, or another
verb justified by visible structure. Give it two to four abstract roles and a
typed relation graph over those roles using only the allowed role predicates;
never bind a role to a visible object yourself. Also give it a measurable
potential, preferred direction, typed terminal class, and terminal condition. R2 decides whether
and how each proposal binds. Outside the optional action_aliases field, never
put an environment action, direction, button, policy, or game identifier in
either channel. Do not serialize a situated binding, attention table, or
action policy.

ACTION ALIASES:
For an opaque ACTION_i with exposed R2 transition or causal-effect evidence,
action_aliases may add a short cited phrase: move left, rotate, interact, or
no-op. Use move?/interact? or abstain when ambiguous. Never infer aliases from
button position, action index, convention, or expectation. Never infer control
authority from the name. Aliases are defeasible unverified glosses—not
evidence, semantics, grounding, or control. ACTION_i stays canonical.
Return exactly one alias for every action exposed by the action_aliases schema.
Use a cautious question-mark gloss rather than omitting an evidenced but still
ambiguous action.

SEMANTIC COHERENCE:
- Express telic quantities as residuals whenever possible: progress decreases
  a residual toward minimum/zero. FIT should use fit_residual, which composes
  boundary_gap + overlap_deficit and therefore has a gradient before contact.
  Never use raw overlap_area.
- The preferred direction must move the named observable toward the terminal.
- direction=decrease requires terminal_class=minimum; increase requires
  maximum; maintain requires invariant. Use open only with direction=unknown.
- Fit normally decreases fit_residual. Touch decreases boundary gap. Avoid decreases a hazard
  violation residual rather than maximizing an unbounded distance.
- Collect approaches a candidate item before any disappearance or merger can
  be observed. Reveal increases stable visible structure.
- If evidence supports several verbs, retain up to three competing proposals
  rather than forcing one premature interpretation.
- Never repeat an identical proposal. Every role_constraint argument must be
  a member of that proposal's roles array, and a binary constraint must use
  two different roles. Prefer actor/target unless a third role is necessary.
- A verb's universal definition must stay weak. FIT requires only two spatial
  roles and a measurable fit_residual; sameness, difference, area, value,
  interior, and outline relations are evidence about a situated binding, not
  universal FIT requirements.

ROLE-GRAPH FORM (use abstract role names in every constraint, never f00,
object IDs, colors, or current entities):
roles: [actor, target]
potential_roles: [actor, target]
role_constraints:
- suggested same_outline(actor, target)
- suggested same_interior(actor, target)
- suggested different_value(actor, target)
observable: fit_residual
direction: decrease
terminal_class: minimum
Every role constraint has a modality: required, suggested, anti-clue, or
unknown. Use required only when violating it makes the verb semantically
ill-typed; ordinary visual guesses must be suggested. Role constraints
describe stable categorical compatibility only. Put distance, alignment,
overlap, contact, and separation in the potential and terminal, never in
role_constraints.
Keep the scratchpad and summary terse so the strict JSON always completes.

R2.1 FEEDBACK:
- r2_semantic_projection is a read-only, bounded report from R2's recursive
  workspace. Treat its grounded roles, causal status, prediction settlements,
  and open shadows as inputs to semantic revision.
- Preserve a useful grounded verb when only its mechanism failed. Revise or
  replace proposals when their grounding repeatedly fails or their predictions
  are refuted. Open shadows are explicit unresolved questions.
- Never declare your own revision grounded, verified, or action-authoritative.
  Return revised abstract verb schemas through goal_proposals; R2 must bind and
  adjudicate them again.

- When r2_semantic_projection exposes at least two stable schema IDs, use
  abductive_compositions to propose a small typed diagram over those existing
  definitions. Compose; do not duplicate their content. State directed
  morphisms, residual-orientation predictions, and open questions. Situated
  binding IDs are evidence references, never reusable component definitions.

CAUSAL VISUAL UNIT:
- At frame 0, causal_unit contains only the current frame and explicitly has
  predecessor=none.
- After an intervention, read CAUSAL_UNIT_PREVIOUS_FRAME first and
  CAUSAL_UNIT_CURRENT_FRAME second. They are the exact predecessor/successor
  pair for r2_transition_observation.action.
- r2_transition_observation is observed history, not permission to choose the
  next action. Compare the two frames yourself, then use R2's trace and
  prediction settlement as structured but defeasible interpretation.
- At most one separately labeled historically salient frame may follow the
  causal pair. It is context, never the successor of the latest action.
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
        prior = _latest_note(state, turn.workspace_id, qc)
        projection = None
        if prior is not None:
            projection = {
                "object_id": prior.object_id,
                "basis_revision": prior.payload.get("basis_revision"),
                "summary": prior.payload.get("summary", ""),
                "prior_natural_language_digest": hashlib.sha256(
                    str(prior.payload.get("natural_language", "")).encode("utf-8")
                ).hexdigest(),
                "objective_hypothesis": prior.payload.get("objective_hypothesis", ""),
                "goal_proposals": list(prior.payload.get("goal_proposals", ())),
                "action_aliases": list(prior.payload.get("action_aliases", ())),
                "open_questions": list(prior.payload.get("open_questions", ())),
                "cited_ids": list(prior.payload.get("cited_ids", ())),
                "transition_evidence_ref": prior.payload.get("transition_evidence_ref"),
                "explanation_consolidation": copy.deepcopy(
                    prior.payload.get("explanation_consolidation")
                ),
                "verified": False,
            }
        scratchpad_context = {
            "qwen_note": projection,
            "r2_action_traces": list(_R2_ACTION_TRACES),
            "r2_semantic_projection": copy.deepcopy(_R2_SEMANTIC_PROJECTION),
            "r2_transition_observation": copy.deepcopy(_R2_TRANSITION_OBSERVATION),
        }
        consolidation_task = _consolidation_task(state, turn.workspace_id, qc)
        current_evidence_ref = (_R2_TRANSITION_OBSERVATION or {}).get("evidence_ref")
        prior_evidence_ref = None if prior is None else prior.payload.get("transition_evidence_ref")
        if (
            prior is not None
            and isinstance(current_evidence_ref, str)
            and current_evidence_ref
            and current_evidence_ref != prior_evidence_ref
        ):
            failure_signals = _semantic_failure_signals({
                "scratchpad_context": scratchpad_context,
            })
        else:
            failure_signals = ()
        if failure_signals:
            prior_keys = sorted({
                _canonical_goal_proposal_key(item)
                for item in prior.payload.get("goal_proposals", ())
            })
            scratchpad_context["semantic_stagnation"] = {
                "protocol": "evidence-stale-exact-proposal-guard-v1",
                "new_transition_evidence_ref": current_evidence_ref,
                "prior_transition_evidence_ref": prior_evidence_ref,
                "prior_goal_proposal_digests": [
                    hashlib.sha256(item.encode("utf-8")).hexdigest()[:20]
                    for item in prior_keys
                ],
                "explicit_failure_signals": [dict(item) for item in failure_signals],
                "instruction": (
                    "R2 or environment failure evidence is available; do not return "
                    "the exact same canonical goal_proposal set"
                ),
                "authority": "qwen-must-revise-or-replace; r2-still-grounds-and-controls",
            }
        document = {**turn.document, "prior_working_note": projection, "scratchpad_context": scratchpad_context}
        if consolidation_task is not None:
            document["explanation_consolidation_task"] = consolidation_task
        vocabulary = dict(document.get("allowed_vocabulary", {}))
        if vocabulary:
            vocabulary["control_gate"] = {
                "authority": "semantic-goal-proposal-requires-r2-grounding",
                "measures": list(vocabulary.get("measures", ())),
                "operators": list(vocabulary.get("operators", ())),
            }
            document["allowed_vocabulary"] = vocabulary
        return replace(turn, document=document)

    def note_schema(turn: Any) -> dict[str, Any]:
        _index, visible = qc._v14_visible(turn)
        consolidation_task = turn.document.get("explanation_consolidation_task")
        consolidation_sources = (
            set(consolidation_task.get("source_evidence_refs", ()))
            if isinstance(consolidation_task, Mapping) else set()
        )
        visible_ids = sorted(set(visible) | consolidation_sources)
        cited_item = {"enum": visible_ids} if visible_ids else {"type": "string", "maxLength": 0}
        abstract_roles = ["actor", "target", "reference", "item", "container", "hazard", "occluder", "hidden", "source", "destination"]
        feedback = turn.document.get("scratchpad_context", {}).get("r2_semantic_projection") or {}
        action_evidence = dict(list(_action_evidence_refs(turn.document).items())[:8])
        stable_schema_ids = set()
        active = feedback.get("active_explanation") or {}
        if active.get("schema_id"): stable_schema_ids.add(str(active["schema_id"]))
        for field in ("categorical_comparisons", "grounded_abductions"):
            for item in feedback.get(field, ()):
                if item.get("schema_id"): stable_schema_ids.add(str(item["schema_id"]))
        stable_schema_ids = sorted(stable_schema_ids)[:24]
        schema_ref = {"enum": stable_schema_ids} if stable_schema_ids else {"type": "string", "maxLength": 0}
        abduction_schema = {
            "type": "object", "additionalProperties": False,
            "required": ["local_ref", "component_schema_ids", "morphisms", "preferred_residual_changes", "open_questions"],
            "properties": {
                # Avoid the two-letters-plus-two-digits shape reserved by the
                # cognition boundary for opaque game identifiers.
                "local_ref": {"type": "string", "pattern": "^composition_[0-9]{1,2}$"},
                "component_schema_ids": {
                    "type": "array", "uniqueItems": True,
                    "minItems": 2 if len(stable_schema_ids) >= 2 else 0,
                    "maxItems": min(3, len(stable_schema_ids)), "items": schema_ref,
                },
                "morphisms": {"type": "array", "minItems": 1, "maxItems": 3, "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["source_schema_id", "target_schema_id", "kind"],
                    "properties": {
                        "source_schema_id": schema_ref, "target_schema_id": schema_ref,
                        "kind": {"enum": ["preserves", "factors_through", "constrains", "predicts", "realizes", "co_describes"]},
                    },
                }},
                "preferred_residual_changes": {"type": "array", "maxItems": 2, "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["comparison_schema_id", "dimension", "direction"],
                    "properties": {
                        "comparison_schema_id": schema_ref,
                        "dimension": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,63}$"},
                        "direction": {"enum": ["decrease", "increase", "maintain"]},
                    },
                }},
                "open_questions": {"type": "array", "maxItems": 1, "items": {"type": "string", "maxLength": 160}},
            },
        }
        verb_schema = {
            "type": "object", "additionalProperties": False,
            "required": ["verb", "schema_name", "goal_family", "roles", "role_constraints", "potential_roles", "observable", "direction", "terminal_class", "terminal_condition"],
            "properties": {
                "verb": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,39}$"},
                "schema_name": {"type": "string", "maxLength": 80},
                "goal_family": {"enum": ["alignment", "containment", "contact", "separation", "ordering", "symmetry", "multiplicity", "transformation", "unknown"]},
                "roles": {"type": "array", "minItems": 2, "maxItems": 4, "uniqueItems": True, "items": {"enum": abstract_roles}},
                "potential_roles": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"enum": abstract_roles}},
                "observable": {"enum": ["fit_residual", "centroid_distance", "boundary_gap", "overlap_deficit", "containment_violation", "component_count", "symmetry_residual", "unknown"]},
                "direction": {"enum": ["decrease", "increase", "maintain", "unknown"]},
                "terminal_class": {"enum": ["minimum", "maximum", "invariant", "open"]},
                "terminal_condition": {"type": "string", "maxLength": 120},
                "role_constraints": {"type": "array", "maxItems": 6, "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["predicate", "arguments", "modality"],
                    "properties": {
                        "predicate": {"enum": ["same_outline", "different_outline", "same_interior", "different_interior", "same_area", "different_area", "same_value", "different_value"]},
                        "arguments": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"enum": abstract_roles}},
                        "modality": {"enum": ["required", "suggested", "anti-clue", "unknown"]},
                    },
                }},
            },
        }
        alias_branches = []
        for action_id, evidence_refs in action_evidence.items():
            alias_branches.append({
                "type": "object", "additionalProperties": False,
                "required": ["action_id", "alias", "status", "evidence_refs"],
                "properties": {
                    "action_id": {"const": action_id},
                    "alias": {
                        "type": "string", "minLength": 1, "maxLength": 64,
                        "pattern": "^[a-z][a-z0-9 ?-]{0,63}$",
                    },
                    "status": {"enum": ["tentative", "stable"]},
                    "evidence_refs": {
                        "type": "array", "minItems": 1,
                        "maxItems": min(4, len(evidence_refs)), "uniqueItems": True,
                        "items": {"enum": list(evidence_refs)},
                    },
                },
            })
        action_aliases = {
            "type": "array", "minItems": len(action_evidence),
            "maxItems": min(8, len(action_evidence)), "uniqueItems": True,
            "items": (
                {"oneOf": alias_branches}
                if alias_branches else
                {"type": "object", "additionalProperties": False, "maxProperties": 0}
            ),
        }
        required = ["summary", "objective_hypothesis", "goal_proposals", "abductive_compositions", "action_aliases", "open_questions", "cited_ids"]
        properties = {
                "summary": {"type": "string", "maxLength": 360},
                "objective_hypothesis": {"type": "string", "maxLength": 240},
                "goal_proposals": {
                    "type": "array", "minItems": 1,
                    "maxItems": 2 if len(stable_schema_ids) >= 2 else 3,
                    "items": verb_schema,
                },
                "abductive_compositions": {
                    "type": "array", "minItems": 1 if len(stable_schema_ids) >= 2 else 0,
                    "maxItems": 1 if len(stable_schema_ids) >= 2 else 0,
                    "items": abduction_schema,
                },
                "action_aliases": action_aliases,
                "open_questions": {
                    "type": "array", "maxItems": 2,
                    "items": {"type": "string", "maxLength": 160},
                },
                "cited_ids": {
                    "type": "array", "minItems": 1 if visible_ids else 0,
                    "maxItems": 4, "uniqueItems": True,
                    "items": cited_item,
                },
        }
        if isinstance(consolidation_task, Mapping):
            source_refs = list(consolidation_task.get("source_evidence_refs", ()))
            role_relation = {
                "type": "object", "additionalProperties": False,
                "required": ["predicate", "arguments", "modality"],
                "properties": {
                    "predicate": {"enum": ["same_outline", "different_outline", "same_interior", "different_interior", "same_area", "different_area", "same_value", "different_value"]},
                    "arguments": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"enum": abstract_roles}},
                    "modality": {"enum": ["required", "suggested", "anti-clue", "unknown"]},
                },
            }
            consolidation_properties = {
                    "protocol": {"const": EXPLANATION_CONSOLIDATION_PROTOCOL},
                    "source_boundary_ref": {"const": consolidation_task["source_boundary_ref"]},
                    "source_refs": {
                        "type": "array", "minItems": 1, "maxItems": min(8, len(source_refs)),
                        "uniqueItems": True, "items": {"enum": source_refs},
                    },
                    "abstractions": {
                        "type": "array", "uniqueItems": True, "maxItems": 1,
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["local_ref", "goal_proposal_index", "applicability_relations", "preserved_structure", "nuisance_dimensions", "causal_structure", "unresolved_ports", "predicted_reuse", "counterconditions"],
                            "properties": {
                                "local_ref": {"type": "string", "pattern": "^abstraction_[0-9]{1,2}$"},
                                "goal_proposal_index": {"type": "integer", "minimum": 0, "maximum": 2},
                                "applicability_relations": {"type": "array", "maxItems": 6, "items": role_relation},
                                "preserved_structure": {"type": "array", "uniqueItems": True, "maxItems": 5, "items": {"enum": ["topology", "intrinsic_geometry", "component_count", "relative_order", "contact_state", "containment_state"]}},
                                "nuisance_dimensions": {"type": "array", "uniqueItems": True, "maxItems": 8, "items": {"enum": list(MANDATORY_NUISANCE_DIMENSIONS)}},
                                "causal_structure": {"type": "array", "uniqueItems": True, "maxItems": 4, "items": {"enum": ["preserves_intrinsic_structure", "changes_relative_position", "changes_contact", "changes_containment", "changes_component_count", "unknown"]}},
                                "unresolved_ports": {"type": "array", "uniqueItems": True, "maxItems": 4, "items": {"enum": abstract_roles}},
                                "predicted_reuse": {"type": "array", "minItems": 1, "maxItems": 4, "uniqueItems": True, "items": {"enum": ["faster_role_binding", "constrained_shadow_generation", "potential_prediction", "mechanism_discrimination", "milestone_detection"]}},
                                "counterconditions": {"type": "array", "maxItems": 5, "uniqueItems": True, "items": {"enum": ["applicability_relation_absent", "role_identity_ambiguous", "mechanism_conflict", "potential_not_measurable", "predicted_reuse_refuted"]}},
                            },
                        },
                    },
            }
            consolidation_required = [
                "protocol", "decision", "source_boundary_ref", "source_refs",
                "abstractions",
            ]
            properties["explanation_consolidation"] = {
                "oneOf": [
                    {
                        "type": "object", "additionalProperties": False,
                        "required": consolidation_required,
                        "properties": {
                            **copy.deepcopy(consolidation_properties),
                            "decision": {"const": "propose"},
                            "abstractions": {
                                **copy.deepcopy(consolidation_properties["abstractions"]),
                                "minItems": 1,
                            },
                        },
                    },
                    {
                        "type": "object", "additionalProperties": False,
                        "required": consolidation_required,
                        "properties": {
                            **copy.deepcopy(consolidation_properties),
                            "decision": {"const": "abstain"},
                            "abstractions": {
                                **copy.deepcopy(consolidation_properties["abstractions"]),
                                "maxItems": 0,
                            },
                        },
                    },
                ],
            }
            # Consolidation is a semantic projection operation, not an
            # ordinary scratchpad refresh.  Do not make Qwen re-emit action
            # aliases, abductive compositions, or open questions that are
            # unrelated to the reusable schema and substantially enlarge the
            # constrained response.  The compiler materializes those absent
            # working-note fields as empty, never as inferred content.
            required = [
                "summary", "objective_hypothesis", "goal_proposals",
                "cited_ids", "explanation_consolidation",
            ]
            properties = {
                key: value for key, value in properties.items()
                if key in required
            }
            properties["goal_proposals"] = {
                **properties["goal_proposals"], "minItems": 0, "maxItems": 1,
            }
        return {
            "type": "object",
            "additionalProperties": False,
            "required": required,
            "properties": properties,
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

        # The canonical turn retains the full catalog and mixed lossy delta
        # frontier for compilation and audit. Sending those attention-routing
        # structures is redundant once the current dependency-closed sparse
        # cut and R2 scratchpad projection are present. Required causal and
        # evidence packets are separate fields and are never projected away;
        # response validation still uses the untouched full turn.
        compact_document = dict(turn.document)
        consolidation_task = compact_document.get("explanation_consolidation_task")
        if isinstance(consolidation_task, Mapping):
            # The successor level is a future test context, not evidence for
            # the abstraction.  Transport only the completed-context packet;
            # keep the full canonical turn locally for response validation.
            compact_document = {
                key: compact_document[key]
                for key in (
                    "protocol", "request_id", "workspace_ref",
                    "allowed_vocabulary", "explanation_consolidation_task",
                )
                if key in compact_document
            }
            compact_document["transport_projection"] = {
                "omitted_successor_context": True,
                "authority": "canonical-turn-retained-for-response-validation",
                "semantic_view": "completed-context-only",
            }
        omitted = []
        for field in (
            "full_materialization", "object_index", "ordered_lossless_deltas",
        ):
            if field in compact_document:
                compact_document.pop(field)
                omitted.append(field)
        if omitted:
            compact_document["transport_projection"] = {
                "omitted_redundant_fields": omitted,
                "authority": "canonical-turn-retained-for-response-validation",
                "semantic_view": "bounded-sparse-cut",
            }
        compact_text = qc.PROMPT + json.dumps(
            compact_document, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        )
        messages = request.get("messages", ())
        if messages:
            content = messages[0].get("content")
            if isinstance(content, str):
                messages[0]["content"] = compact_text
            elif isinstance(content, list) and content and content[0].get("type") == "text":
                content[0]["text"] = compact_text
                if isinstance(consolidation_task, Mapping):
                    messages[0]["content"] = [content[0]]
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
        prior_projection = turn.document.get("prior_working_note") or {}
        prior_prose_digest = prior_projection.get("prior_natural_language_digest")
        if (
            isinstance(prior_prose_digest, str)
            and hashlib.sha256(prose.strip().encode("utf-8")).hexdigest() == prior_prose_digest
        ):
            return {
                **compilation,
                "rejected": [
                    *compilation.get("rejected", ()),
                    {"reason": "natural-language-scratchpad-not-revised"},
                ],
            }
        if note is None:
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "workspace-write-missing"}]}
        consolidation_task = turn.document.get("explanation_consolidation_task")
        ordinary_required = {
            "summary", "objective_hypothesis", "goal_proposals",
            "abductive_compositions", "action_aliases", "open_questions",
            "cited_ids",
        }
        consolidation_required = {
            "summary", "objective_hypothesis", "goal_proposals",
            "cited_ids", "explanation_consolidation",
        }
        required = (
            consolidation_required
            if isinstance(consolidation_task, Mapping)
            else ordinary_required
        )
        if not isinstance(note, Mapping) or set(note) != required:
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "working-note-contract"}]}
        if isinstance(consolidation_task, Mapping):
            note = {
                **dict(note),
                "abductive_compositions": [],
                "action_aliases": [],
                "open_questions": [],
            }
        scratch_tokens = qc.GRAPH.estimate_tokens(prose)
        action_free_note = {key: value for key, value in note.items() if key != "action_aliases"}
        if _has_action_proposal(prose) or _has_action_proposal(action_free_note) or scratch_tokens > MAX_SCRATCHPAD_TOKENS:
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "working-note-safety-or-budget"}]}
        _index, visible = qc._v14_visible(turn)
        aliases = dict(turn.id_aliases)
        cited = list(note["cited_ids"])
        source_citations = (
            set(consolidation_task.get("source_evidence_refs", ()))
            if isinstance(consolidation_task, Mapping) else set()
        )
        if any(
            not isinstance(item, str)
            or item not in set(visible) | source_citations
            for item in cited
        ):
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "working-note-citation"}]}
        if not compilation.get("valid_json_contract"):
            return compilation
        real_citations = [aliases.get(item, item) for item in cited]
        available_action_evidence = _action_evidence_refs(turn.document)
        action_aliases = []
        seen_actions = set()
        for alias in note["action_aliases"]:
            if not isinstance(alias, Mapping) or set(alias) != {"action_id", "alias", "status", "evidence_refs"}:
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "action-alias-contract"}]}
            action_id = _canonical_action_id(alias.get("action_id"))
            phrase = alias.get("alias")
            status = alias.get("status")
            evidence_refs = alias.get("evidence_refs")
            allowed_refs = set(available_action_evidence.get(str(action_id), ()))
            if (
                action_id is None or action_id in seen_actions
                or not isinstance(phrase, str)
                or re.fullmatch(r"[a-z][a-z0-9 ?-]{0,63}", phrase) is None
                or status not in {"tentative", "stable"}
                or not isinstance(evidence_refs, list) or not evidence_refs
                or len(evidence_refs) > 4
                or any(not isinstance(ref, str) for ref in evidence_refs)
                or len(set(evidence_refs)) != len(evidence_refs)
                or any(ref not in allowed_refs for ref in evidence_refs)
            ):
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "action-alias-evidence"}]}
            seen_actions.add(action_id)
            action_aliases.append({
                "action_id": action_id, "alias": phrase,
                "status": status, "evidence_refs": list(evidence_refs),
            })
        unique_proposals = []
        seen_proposals = set()
        for proposal in note["goal_proposals"]:
            key = _canonical_goal_proposal_key(proposal)
            if key not in seen_proposals:
                seen_proposals.add(key); unique_proposals.append(dict(proposal))
        consolidation = None
        consolidation_write = None
        if isinstance(consolidation_task, Mapping):
            raw = note.get("explanation_consolidation")
            exact_fields = {
                "protocol", "decision", "source_boundary_ref", "source_refs", "abstractions",
            }
            if not isinstance(raw, Mapping) or set(raw) != exact_fields:
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-contract"}]}
            decision = raw.get("decision")
            source_boundary_ref = raw.get("source_boundary_ref")
            source_refs = raw.get("source_refs")
            abstractions = raw.get("abstractions")
            allowed_source_refs = set(consolidation_task.get("source_evidence_refs", ()))
            if (
                raw.get("protocol") != EXPLANATION_CONSOLIDATION_PROTOCOL
                or decision not in {"propose", "abstain"}
                or source_boundary_ref != consolidation_task.get("source_boundary_ref")
                or not isinstance(source_refs, list) or not source_refs
                or len(source_refs) > 8 or len(set(source_refs)) != len(source_refs)
                or source_boundary_ref not in source_refs
                or not set(source_refs).issubset(allowed_source_refs)
                or not isinstance(abstractions, list) or len(abstractions) > 1
                or (decision == "propose" and not abstractions)
                or (decision == "abstain" and abstractions)
                or (decision == "abstain" and unique_proposals)
                or len(unique_proposals) != len(note["goal_proposals"])
            ):
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-authority"}]}
            normalized_abstractions = []
            used_indices = set()
            allowed_predicates = {
                "same_outline", "different_outline", "same_interior",
                "different_interior", "same_area", "different_area",
                "same_value", "different_value",
            }
            allowed_modalities = {"required", "suggested", "anti-clue", "unknown"}
            allowed_preserved = {
                "topology", "intrinsic_geometry", "component_count",
                "relative_order", "contact_state", "containment_state",
            }
            allowed_causal = {
                "preserves_intrinsic_structure", "changes_relative_position",
                "changes_contact", "changes_containment",
                "changes_component_count", "unknown",
            }
            allowed_reuse = {
                "faster_role_binding", "constrained_shadow_generation",
                "potential_prediction", "mechanism_discrimination",
                "milestone_detection",
            }
            allowed_counterconditions = {
                "applicability_relation_absent", "role_identity_ambiguous",
                "mechanism_conflict", "potential_not_measurable",
                "predicted_reuse_refuted",
            }
            abstraction_fields = {
                "local_ref", "goal_proposal_index", "applicability_relations",
                "preserved_structure", "nuisance_dimensions", "causal_structure",
                "unresolved_ports", "predicted_reuse", "counterconditions",
            }
            for abstraction in abstractions:
                if not isinstance(abstraction, Mapping) or set(abstraction) != abstraction_fields:
                    return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-abstraction"}]}
                index = abstraction.get("goal_proposal_index")
                if (
                    not isinstance(index, int) or isinstance(index, bool)
                    or index < 0 or index >= len(unique_proposals)
                    or index in used_indices
                ):
                    return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-schema-reference"}]}
                used_indices.add(index)
                roles = set(unique_proposals[index].get("roles", ()))
                relations = abstraction.get("applicability_relations")
                preserved = abstraction.get("preserved_structure")
                nuisances = abstraction.get("nuisance_dimensions")
                causal = abstraction.get("causal_structure")
                unresolved = abstraction.get("unresolved_ports")
                predicted_reuse = abstraction.get("predicted_reuse")
                counterconditions = abstraction.get("counterconditions")
                if not isinstance(relations, list) or any(
                    not isinstance(item, Mapping)
                    or set(item) != {"predicate", "arguments", "modality"}
                    or item.get("predicate") not in allowed_predicates
                    or item.get("modality") not in allowed_modalities
                    or len(item.get("arguments", ())) != 2
                    or len(set(item.get("arguments", ()))) != 2
                    or not set(item.get("arguments", ())).issubset(roles)
                    for item in relations
                ) or any(
                    not isinstance(value, list)
                    or len(value) != len(set(value))
                    for value in (
                        preserved, nuisances, causal, unresolved,
                        predicted_reuse, counterconditions,
                    )
                ) or (
                    not set(preserved).issubset(allowed_preserved)
                    or not set(nuisances).issubset(MANDATORY_NUISANCE_DIMENSIONS)
                    or not set(causal).issubset(allowed_causal)
                    or not set(unresolved).issubset(roles)
                    or not predicted_reuse
                    or not set(predicted_reuse).issubset(allowed_reuse)
                    or not set(counterconditions).issubset(allowed_counterconditions)
                    or re.fullmatch(r"abstraction_[0-9]{1,2}", str(abstraction.get("local_ref"))) is None
                ):
                    return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-port-typing"}]}
                if _has_consolidation_situated_detail(unique_proposals[index]):
                    return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-situated-detail"}]}
                schema_definition = {
                    **unique_proposals[index],
                    "authority_scope": FRESH_BINDING_AUTHORITY,
                    "projection_mode": "abstract-explanation-projection",
                    "consolidation_source_boundary_ref": source_boundary_ref,
                }
                unique_proposals[index] = schema_definition
                normalized_abstractions.append({
                    **dict(abstraction),
                    "schema_definition": schema_definition,
                    "nuisance_dimensions": sorted(set((
                        *MANDATORY_NUISANCE_DIMENSIONS,
                        *abstraction.get("nuisance_dimensions", ()),
                    ))),
                    "empirical_support": 0,
                    "epistemic_status": "ungrounded-reusable-hypothesis",
                })
            if decision == "propose" and used_indices != set(range(len(unique_proposals))):
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-schema-reference"}]}
            consolidation = {
                "protocol": EXPLANATION_CONSOLIDATION_PROTOCOL,
                "operation": "reflective-abstraction",
                "projection_mode": "abstract-explanation-projection",
                "decision": decision,
                "source_context_index": int(consolidation_task["source_context_index"]),
                "source_boundary_ref": source_boundary_ref,
                "source_refs": list(source_refs),
                "abstractions": normalized_abstractions,
                "authority_reset": dict(consolidation_task["transfer_contract"]),
                "workspace_ref": _workspace_ref(qc, turn.workspace_id),
                "basis_revision": turn.basis_revision,
            }
            consolidation_write = {
                "kind": "explanation_consolidation",
                "local_ref": "explanation_consolidation",
                "identity": {
                    "workspace_ref": _workspace_ref(qc, turn.workspace_id),
                    "source_boundary_ref": source_boundary_ref,
                    "content_hash": qc.stable_hash(consolidation),
                },
                "payload": consolidation,
                "dependency_ids": list(source_refs),
            }
        current_evidence_ref = _transition_evidence_ref(turn.document)
        prior_evidence_ref = prior_projection.get("transition_evidence_ref")
        prior_proposal_keys = {
            _canonical_goal_proposal_key(item)
            for item in prior_projection.get("goal_proposals", ())
        }
        evidence_stale_exact_repetition = (
            bool(current_evidence_ref)
            and current_evidence_ref != prior_evidence_ref
            and bool(prior_proposal_keys)
            and bool(_semantic_failure_signals(turn.document))
            and seen_proposals == prior_proposal_keys
        )
        if evidence_stale_exact_repetition:
            return {
                **compilation,
                "rejected": [
                    *compilation.get("rejected", ()),
                    {
                        "reason": "evidence-stale-goal-proposal-repetition",
                        "new_transition_evidence_ref": current_evidence_ref,
                        "prior_transition_evidence_ref": prior_evidence_ref,
                        "proposal_digests": [
                            hashlib.sha256(item.encode("utf-8")).hexdigest()[:20]
                            for item in sorted(seen_proposals)
                        ],
                    },
                ],
            }
        feedback = turn.document.get("scratchpad_context", {}).get("r2_semantic_projection") or {}
        available_schema_ids = {
            str(item.get("schema_id"))
            for field in ("categorical_comparisons", "grounded_abductions")
            for item in feedback.get(field, ()) if item.get("schema_id")
        }
        active = feedback.get("active_explanation") or {}
        if active.get("schema_id"): available_schema_ids.add(str(active["schema_id"]))
        abductions = []
        for proposal in note["abductive_compositions"]:
            components = tuple(str(item) for item in proposal.get("component_schema_ids", ()))
            morphisms = tuple(proposal.get("morphisms", ()))
            if len(components) < 2 or not set(components).issubset(available_schema_ids):
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "abduction-component-authority"}]}
            if any(
                str(item.get("source_schema_id")) not in components
                or str(item.get("target_schema_id")) not in components
                for item in morphisms
            ):
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "abduction-morphism-type-boundary"}]}
            abductions.append(dict(proposal))
        payload = {
            **dict(note),
            "goal_proposals": unique_proposals,
            "abductive_compositions": abductions,
            "action_aliases": action_aliases,
            "natural_language": prose.strip(),
            "cited_ids": real_citations,
            "workspace_ref": _workspace_ref(qc, turn.workspace_id),
            "basis_revision": turn.basis_revision,
            "verified": False,
            "token_count": scratch_tokens,
            "token_budget": MAX_SCRATCHPAD_TOKENS,
            "transition_evidence_ref": current_evidence_ref,
        }
        if consolidation is not None:
            payload["explanation_consolidation"] = consolidation
        write = {
            "kind": "working_note",
            "local_ref": "working_note",
            "identity": {
                "workspace_ref": _workspace_ref(qc, turn.workspace_id),
                "basis_revision": turn.basis_revision,
                "content_hash": qc.stable_hash({"natural_language": prose, "workspace_write": note}),
            },
            "payload": payload,
            "dependency_ids": sorted(set((
                *real_citations,
                *((consolidation or {}).get("source_refs", ())),
            ))),
        }
        explanation = {
            "kind": "explanation",
            "local_ref": "working_hypothesis",
            "identity": {
                "workspace_ref": _workspace_ref(qc, turn.workspace_id),
                "basis_revision": turn.basis_revision,
                "content_hash": qc.stable_hash({"objective_hypothesis": note["objective_hypothesis"]}),
                "mode": "defeasible-working-hypothesis",
            },
            "payload": {
                "claim": note["objective_hypothesis"],
                "summary": note["summary"],
                "goal_proposals": unique_proposals,
                "abductive_compositions": abductions,
                "open_questions": list(note["open_questions"]),
                "status": "unverified",
                "epistemic_role": "candidate-model-for-goal-progress-or-information",
                "basis_revision": turn.basis_revision,
            },
            "dependency_ids": sorted(set((
                *real_citations,
                *((consolidation or {}).get("source_refs", ())),
            ))),
            "evidence": [],
            "support": 0,
        }
        accepted = [*compilation.get("accepted", ())]
        accepted.append(explanation)
        if consolidation_write is not None:
            accepted.append(consolidation_write)
        accepted.append(write)
        return {**compilation, "accepted": accepted, "working_note": payload}

    qc.build_turn = build_turn
    qc.response_schema = response_schema
    qc.request_payload = request_payload
    qc.compile_response = compile_response
    qc.alias_revision_due = lambda state, workspace_id: alias_revision_due(
        state, workspace_id, qc
    )
    qc.initial_semantics_due = lambda state, workspace_id: initial_semantics_due(
        state, workspace_id, qc
    )
    qc.semantic_failure_revision_due = (
        lambda state, workspace_id: semantic_failure_revision_due()
    )
    qc.explanation_consolidation_due = (
        lambda state, workspace_id: explanation_consolidation_due(
            state, workspace_id, qc
        )
    )
