"""Bounded Qwen working memory for the one-action experiment."""

from __future__ import annotations

from dataclasses import replace
from collections import Counter
import copy
import hashlib
import json
import re
from typing import Any, Mapping


MAX_SCRATCHPAD_TOKENS = 1024
MAX_R2_SEMANTIC_PROJECTION_BYTES = 12000
EXPLANATION_CONSOLIDATION_PROTOCOL = "explanation-consolidation-v1"
FRESH_BINDING_AUTHORITY = "fresh-binding-probe-only"
DEEP_CONSOLIDATION_MAX_TOKENS = 5120
DEEP_CONSOLIDATION_THINKING_TOKENS = 1024
MAX_CONSOLIDATION_PROPOSALS = 3
MODEL_SCRATCHPAD_FIELDS = (
    "game_objective", "explanation", "goal", "expectation", "notes",
)
CONSOLIDATION_PROMPT = """You are the configured semantic model performing R2 explanation consolidation.
Read model_scratchpad as the exact current shared workspace scratchpad used by
ordinary semantic turns and Agent Arcade. Rewrite the same five-field object in
your response; do not rename, omit, or add fields. During consolidation set:
- game_objective to the current inferred condition for winning or completing
  the game, explicitly marked open when the evidence does not determine it;
- explanation to the smallest reusable explanation that survived settlement;
- goal to the current action-free subgoal that advances the game objective;
- expectation to a falsifiable prediction for a fresh future binding;
- notes to what was preserved, discarded, refuted, or left open by consolidation.
At least one field must change from the input object; prefer revising all five
when the completed context changes their meaning.
The packet is a deterministic digest of a completed context. Compare
its explanation families, potential summaries, change points, confirmations,
refutations, and terminal evidence. Propose the smallest reusable action-free R2
schemas whose failure in a future context would be informative, or explicitly
abstain. Do not prescribe an action, route, coordinate, palette value, situated
identity, prior binding, or intervention meaning. A proposal receives zero
empirical authority: R2 alone may freshly bind, test, specialize, or discard it,
and the environment alone settles it. Prefer exactly one minimal abstraction.
Return a second or third only for causally independent structures with distinct
reuse predictions; never repeat a schema or an array item. Keep every prose
field terse. Return only the required JSON contract.

CONSOLIDATION DIGEST:
"""
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
TRANSPORT_METADATA_LEAK = re.compile(
    r"\b(?:contiguous\s+)?dormant\s+run(?:s)?\b|"
    r"\bdelta\s+codec\b|\bordered\s+(?:lossless\s+)?projection(?:s)?\b|"
    r"\blossy\s+(?:event\s+)?summar(?:y|ies)\b|"
    r"\btransport\s+projection\b|\bevent\s+compression\b",
    re.IGNORECASE,
)


def canonical_model_scratchpad(value: Any) -> dict[str, str]:
    """Validate and copy the exact model/UI/workspace scratchpad contract."""

    if not isinstance(value, Mapping) or set(value) != set(MODEL_SCRATCHPAD_FIELDS):
        raise ValueError("model scratchpad must contain exactly five canonical fields")
    output: dict[str, str] = {}
    for field in MODEL_SCRATCHPAD_FIELDS:
        item = value.get(field)
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"model scratchpad {field} must be a nonempty string")
        output[field] = item.strip()
    return output


def model_scratchpad_text(value: Any) -> str:
    return json.dumps(
        canonical_model_scratchpad(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def has_transport_metadata_leak(value: Any) -> bool:
    """Detect representation-layer jargon miscast as game-world semantics."""

    if isinstance(value, Mapping):
        return any(has_transport_metadata_leak(item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return any(has_transport_metadata_leak(item) for item in value)
    return isinstance(value, str) and bool(TRANSPORT_METADATA_LEAK.search(value))


def current_transition_evidence_ref() -> str | None:
    value = (_R2_TRANSITION_OBSERVATION or {}).get("evidence_ref")
    return value if isinstance(value, str) and value else None


def scratchpad_basis_is_current(turn_evidence_ref: Any) -> bool:
    return current_transition_evidence_ref() == turn_evidence_ref
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
    """Build one deep, bounded reflection task over one completed context.

    Only graph objects created before the level boundary are eligible semantic
    sources.  The boundary and its environment evidence are included solely to
    prove that the source context completed; the successor board is never
    projected into the abstraction packet.
    """

    boundary = _latest_level_boundary(state)
    if boundary is None:
        return None
    workspace_ref = _workspace_ref(qc, workspace_id)
    objects = tuple(getattr(state, "objects", ()))
    authority_reset = {
        "schema_definition": "project-and-fresh-bind",
        "empirical_support": "reset",
        "bindings": "reset",
        "role_identities": "reset",
        "potentials": "reset",
        "intervention_applicability": "reset",
        "progress_authority": "reset",
    }
    if any(
        item.kind == "explanation_consolidation"
        and item.created_by == "qwen"
        and item.payload.get("protocol") == EXPLANATION_CONSOLIDATION_PROTOCOL
        and item.payload.get("workspace_ref") == workspace_ref
        and item.payload.get("source_boundary_ref") == boundary.object_id
        and item.payload.get("source_boundary_ref") in item.payload.get("source_refs", ())
        and item.payload.get("decision") in {"propose", "abstain"}
        and item.payload.get("authority_reset") == authority_reset
        and isinstance(item.payload.get("abstractions"), list)
        and (
            (item.payload.get("decision") == "abstain" and not item.payload["abstractions"])
            or (
                item.payload.get("decision") == "propose"
                and 1 <= len(item.payload["abstractions"]) <= MAX_CONSOLIDATION_PROPOSALS
            )
        )
        for item in objects
    ):
        return None
    prior_boundaries = sorted(
        (
            item for item in objects
            if item.kind == "transition"
            and item.created_by == "environment"
            and item.payload.get("level_transition") is True
            and item.payload.get("boundary_kind") == "level-advance"
            and item.created_revision < boundary.created_revision
        ),
        key=lambda item: (item.created_revision, item.object_id),
    )
    prior_boundary = prior_boundaries[-1] if prior_boundaries else None
    source_start_revision = (
        prior_boundary.created_revision if prior_boundary is not None else 0
    )

    def within_completed_context(item: Any) -> bool:
        return source_start_revision < item.created_revision < boundary.created_revision

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
        and within_completed_context(item)
        and item.payload.get("workspace_ref") == workspace_ref
    ]
    prior_note = max(
        prior_notes,
        key=lambda item: (item.created_revision, item.object_id),
        default=None,
    )
    explanations = [
        item for item in objects
        if within_completed_context(item)
        and item.kind in {"control_explanation", "explanation"}
    ]
    explanations.sort(key=lambda item: (item.created_revision, item.object_id))
    explanation_count = len(explanations)

    # Consolidation receives epistemic structure, not a transcript dump.  A
    # completed level can contain dozens of byte-near-identical situated
    # explanations.  Quotient them by their action-free semantic definition,
    # then preserve multiplicity, status/evidence change points, potential
    # movement, and a digest back to every source object.
    family_members: dict[str, list[Any]] = {}
    family_cores: dict[str, dict[str, Any]] = {}
    unstructured_explanation_count = 0
    for item in explanations:
        payload = item.payload
        raw_goal = payload.get("goal")
        goal = dict(raw_goal) if isinstance(raw_goal, Mapping) else {}
        goal_template = {
            key: copy.deepcopy(goal[key])
            for key in (
                "family", "measure", "observable", "direction", "terminal",
                "terminal_class", "terminal_condition", "role_constraints",
                "roles", "potential_roles",
            )
            if key in goal
        }
        claim = payload.get("claim")
        claim_text = str(claim) if isinstance(claim, str) else ""
        semantic_label = (
            claim_text
            if re.fullmatch(r"[A-Za-z][A-Za-z _-]{0,47}", claim_text)
            and re.search(r"\bf[0-9]{2}\b|\bACTION_[0-9]+\b", claim_text) is None
            else None
        )
        core = {
            "kind": item.kind,
            "semantic_label": semantic_label,
            "claim_digest": hashlib.sha256(
                claim_text.encode("utf-8")
            ).hexdigest()[:20] if claim_text else None,
            "goal_template": goal_template or None,
            "goal_proposals": copy.deepcopy(payload.get("goal_proposals", ())),
        }
        if (
            core["semantic_label"] is None
            and core["goal_template"] is None
            and not core["goal_proposals"]
        ):
            unstructured_explanation_count += 1
            continue
        family_key = qc.stable_hash(core)
        family_cores[family_key] = core
        family_members.setdefault(family_key, []).append(item)

    explanation_projection = []
    representative_explanation_refs: set[str] = set()
    for family_key in sorted(family_members):
        members = family_members[family_key]
        statuses: Counter[str] = Counter()
        control_statuses: Counter[str] = Counter()
        confirmations: list[int] = []
        refutations: list[int] = []
        confidences: list[float] = []
        potential_values: list[float] = []
        point_reasons: dict[str, set[str]] = {
            members[0].object_id: {"initial"},
            members[-1].object_id: {"latest"},
        }
        seen_statuses: set[tuple[str, str]] = set()
        first_confirmation = first_repeated = first_refutation = False
        for member in members:
            payload = member.payload
            status = str(
                payload.get("epistemic_status") or payload.get("status") or "unknown"
            )
            control_status = str(payload.get("control_status") or "unknown")
            statuses[status] += 1
            control_statuses[control_status] += 1
            status_pair = (status, control_status)
            if status_pair not in seen_statuses:
                point_reasons.setdefault(member.object_id, set()).add("status-change")
                seen_statuses.add(status_pair)
            evaluation = payload.get("epistemic_evaluation")
            evaluation = evaluation if isinstance(evaluation, Mapping) else {}
            confirmation = int(
                evaluation.get("confirmations") or payload.get("confirmations") or 0
            )
            refutation = int(
                evaluation.get("refutations") or payload.get("refutations") or 0
            )
            confidence = evaluation.get("mechanism_confidence")
            confirmations.append(confirmation)
            refutations.append(refutation)
            if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
                confidences.append(float(confidence))
            if confirmation > 0 and not first_confirmation:
                point_reasons.setdefault(member.object_id, set()).add("first-confirmation")
                first_confirmation = True
            if confirmation > 1 and not first_repeated:
                point_reasons.setdefault(member.object_id, set()).add("repeated-confirmation")
                first_repeated = True
            if refutation > 0 and not first_refutation:
                point_reasons.setdefault(member.object_id, set()).add("first-refutation")
                first_refutation = True
            goal = payload.get("goal")
            current = goal.get("current") if isinstance(goal, Mapping) else None
            if isinstance(current, (int, float)) and not isinstance(current, bool):
                potential_values.append(float(current))
                if float(current) == 0.0:
                    point_reasons.setdefault(member.object_id, set()).add("terminal-potential")

        def numeric_range(values: Sequence[float | int]) -> dict[str, Any] | None:
            return None if not values else {"min": min(values), "max": max(values)}

        steps = Counter()
        for left, right in zip(potential_values, potential_values[1:]):
            steps["decrease" if right < left else "increase" if right > left else "equal"] += 1
        change_points = []
        by_id = {item.object_id: item for item in members}
        for source_ref in sorted(
            point_reasons,
            key=lambda ref: (by_id[ref].created_revision, ref),
        ):
            member = by_id[source_ref]
            payload = member.payload
            evaluation = payload.get("epistemic_evaluation")
            evaluation = evaluation if isinstance(evaluation, Mapping) else {}
            goal = payload.get("goal")
            current = goal.get("current") if isinstance(goal, Mapping) else None
            change_points.append({
                "source_ref": source_ref,
                "reasons": sorted(point_reasons[source_ref]),
            })
            representative_explanation_refs.add(source_ref)
        explanation_projection.append({
            "family_digest": family_key,
            "semantic_core": family_cores[family_key],
            "occurrence_count": len(members),
            "ordered_source_ref_digest": qc.stable_hash(
                [item.object_id for item in members]
            ),
            "epistemic_status_counts": dict(sorted(statuses.items())),
            "control_status_counts": dict(sorted(control_statuses.items())),
            "confirmation_range": numeric_range(confirmations),
            "refutation_range": numeric_range(refutations),
            "mechanism_confidence_range": numeric_range(confidences),
            "potential_summary": None if not potential_values else {
                "observed_count": len(potential_values),
                "first": potential_values[0],
                "last": potential_values[-1],
                "min": min(potential_values),
                "max": max(potential_values),
                "distinct_count": len(set(potential_values)),
                "step_counts": dict(sorted(steps.items())),
                "ordered_value_digest": qc.stable_hash(potential_values),
            },
            "change_points": change_points,
        })

    eligible_edges = [
        edge for edge in getattr(state, "edges", ())
        if edge.kind in {"supports", "refutes"}
        and source_start_revision < edge.created_revision < boundary.created_revision
    ]
    eligible_edges.sort(
        key=lambda edge: (
            edge.created_revision, edge.kind, edge.source_id, edge.target_id,
        )
    )
    judgment_count = len(eligible_edges)
    settlements = []
    representative_judgment_refs: set[str] = set()
    for kind in ("supports", "refutes"):
        members = [edge for edge in eligible_edges if edge.kind == kind]
        if not members:
            continue
        representatives = [members[0]]
        if members[-1] is not members[0]:
            representatives.append(members[-1])
        pairs = [[edge.source_id, edge.target_id] for edge in members]
        settlements.append({
            "kind": kind,
            "count": len(members),
            "distinct_evidence_count": len({edge.source_id for edge in members}),
            "distinct_target_count": len({edge.target_id for edge in members}),
            "ordered_pair_digest": qc.stable_hash(pairs),
            "representatives": [
                {"evidence_ref": edge.source_id, "target_ref": edge.target_id}
                for edge in representatives
            ],
        })
        representative_judgment_refs.update(
            ref for pair in pairs[:1] + pairs[-1:] for ref in pair
        )
    all_source_refs = {
        boundary.object_id,
        *(item.object_id for item in evidence),
        *(item.object_id for item in explanations),
        *((prior_note.object_id,) if prior_note is not None else ()),
        *(edge.source_id for edge in eligible_edges),
        *(edge.target_id for edge in eligible_edges),
    }
    existing_ids = {item.object_id for item in objects}
    all_source_refs = sorted(all_source_refs & existing_ids)
    citation_candidates = [
        boundary.object_id,
        *(item.object_id for item in evidence),
        *sorted(representative_explanation_refs),
        *sorted(representative_judgment_refs),
        *((prior_note.object_id,) if prior_note is not None else ()),
    ]
    source_refs = []
    for source_ref in citation_candidates:
        if source_ref in existing_ids and source_ref not in source_refs:
            source_refs.append(source_ref)
        if len(source_refs) == 12:
            break
    context_index = sum(
        item.kind == "transition"
        and item.created_by == "environment"
        and item.payload.get("level_transition") is True
        for item in objects
    )
    completed_context_objects = [
        item for item in objects if within_completed_context(item)
    ]
    complete_evidence_census = {
        kind: sum(item.kind == kind for item in completed_context_objects)
        for kind in sorted({item.kind for item in completed_context_objects})
    }
    evidence_census = {
        kind: complete_evidence_census.get(kind, 0)
        for kind in (
            "explanation", "control_explanation", "prediction", "transition",
            "environment_evidence", "schema", "working_note",
        )
        if complete_evidence_census.get(kind, 0)
    }
    return {
        "protocol": EXPLANATION_CONSOLIDATION_PROTOCOL,
        "operation": "reflective-abstraction",
        "reflection_mode": "deep-synchronous-level-boundary",
        "projection_mode": "abstract-explanation-projection",
        "reuse_scope": "game",
        "source_context_index": context_index,
        "source_boundary_ref": boundary.object_id,
        "source_evidence_refs": source_refs,
        "retrospective_scope": {
            "prior_boundary_ref": (
                prior_boundary.object_id if prior_boundary is not None else None
            ),
            "start_revision_exclusive": source_start_revision,
            "end_revision_exclusive": boundary.created_revision,
            "object_census": evidence_census,
            "complete_object_census_digest": qc.stable_hash(
                complete_evidence_census
            ),
            "explanations_total": explanation_count,
            "explanations_selected": explanation_count,
            "explanation_families": len(explanation_projection),
            "unstructured_explanations_digest_only": unstructured_explanation_count,
            "judgments_total": judgment_count,
            "judgments_selected": judgment_count,
            "judgment_classes": len(settlements),
            "selection": "complete-evidence-preserving-semantic-quotient",
            "all_source_ref_count": len(all_source_refs),
            "ordered_source_ref_digest": qc.stable_hash(all_source_refs),
            "qwen_citation_ref_count": len(source_refs),
        },
        "prior_semantic_note": None if prior_note is None else {
            "source_ref": prior_note.object_id,
            "goal_proposal_count": len(prior_note.payload.get("goal_proposals", ())),
            "goal_proposal_digest": qc.stable_hash(
                prior_note.payload.get("goal_proposals", ())
            ),
            "abductive_composition_count": len(
                prior_note.payload.get("abductive_compositions", ())
            ),
            "abductive_composition_digest": qc.stable_hash(
                prior_note.payload.get("abductive_compositions", ())
            ),
        },
        "settled_explanations": explanation_projection,
        "settled_judgments": settlements,
        "reflection_questions": [
            "What structures persisted across the completed context?",
            "What causal regularities survived intervention and settlement?",
            "What explanation fragments contributed to the preferred completion?",
            "What apparent regularities were refuted or remained context-dependent?",
            "Which details can be quotiented away without losing falsifiable predictions?",
        ],
        "abstraction_question": (
            "What are the smallest useful R2 schema fragments that could generate "
            "the settled structure after nuisance details are quotiented out? "
            "Prefer an abstraction whose future failure would teach R2 the most, "
            "not one that merely describes the completed context."
        ),
        "response_instruction": (
            "Reason broadly over the complete retrospective packet, compare and "
            "reject weak abstractions internally, then return a compact artifact. "
            "Return decision=propose with one minimal abstraction by default, "
            "and at most three only when they capture causally independent "
            "structures with distinct reuse predictions. Return exactly "
            "one referenced goal_proposal per abstraction, or decision=abstain with both "
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
        "transfer_contract": authority_reset,
    }


def explanation_consolidation_due(state: Any, workspace_id: str, qc: Any) -> bool:
    """Demand exactly one accepted consolidation per completed context."""

    return _consolidation_task(state, workspace_id, qc) is not None


def boundary_consolidation_accepted(
    compilation: Mapping[str, Any], turn: Any,
) -> bool:
    """Authorize crossing a context boundary only after proposal or abstention."""

    task = getattr(turn, "document", {}).get("explanation_consolidation_task")
    if not isinstance(task, Mapping):
        return True
    writes = [
        item for item in compilation.get("accepted", ())
        if item.get("kind") == "explanation_consolidation"
    ]
    return bool(
        len(writes) == 1
        and writes[0].get("payload", {}).get("source_boundary_ref")
        == task.get("source_boundary_ref")
        and writes[0].get("payload", {}).get("decision") in {"propose", "abstain"}
    )


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


def epistemic_scratchpad_revision_due(
    state: Any, workspace_id: str, qc: Any,
) -> bool:
    """Require the shared scratchpad to consume every latest settlement once."""

    latest_ref = (_R2_TRANSITION_OBSERVATION or {}).get("evidence_ref")
    if not isinstance(latest_ref, str) or not latest_ref:
        return False
    prior = _latest_note(state, workspace_id, qc)
    consumed_ref = None if prior is None else prior.payload.get("transition_evidence_ref")
    return consumed_ref != latest_ref


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
    qc.PROMPT = qc.PROMPT.replace(
        "while each G row is explicitly a small-lossy summary of a contiguous dormant run.",
        "while each G row is non-semantic bookkeeping for older ledger history.",
    )

    qc.PROMPT += """

TWO SEPARATE OUTPUT CHANNELS:
1. scratchpad is one bounded object with exactly five string fields:
game_objective, explanation, goal, expectation, and notes. game_objective is
the current inferred condition for winning or completing the game; goal is the
current action-free subgoal serving it. Keep uncertainty explicit. This exact object is stored, shown
in Agent Arcade, and passed back to your next semantic turn without renaming or
reformatting. Rewrite the four fields rather than appending a transcript. The
object is unverified, is not evidence, and is never compiled as a workspace
claim.
On every post-action turn, begin from the latest causal visual unit and R2
feedback. State what the latest observation established, contradicted, or left
open. Read model_scratchpad as the exact prior shared state, then revise it in
place. Do not repeat the frame-0 description or copy fields unchanged when new
evidence requires a revision.
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
- A contiguous dormant run, G row, delta codec, ordered projection, lossy
  summary, and transport projection are representation-layer bookkeeping only.
  They never denote a visible object, spatial relation, causal mechanism,
  explanation, goal, expectation, or game state. Never copy or paraphrase those
  terms into scratchpad or workspace_write. Reason only from the observations
  and epistemic content they carry.
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

R2.2 FEEDBACK:
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
            stored_scratchpad = prior.payload.get("model_scratchpad")
            try:
                stored_scratchpad = canonical_model_scratchpad(stored_scratchpad)
            except ValueError:
                proposal = next(iter(prior.payload.get("goal_proposals", ())), {})
                expectation_parts = [
                    str(value) for value in (
                        proposal.get("observable"), proposal.get("direction"),
                        proposal.get("terminal_condition") or proposal.get("terminal_class"),
                    ) if value
                ]
                stored_scratchpad = {
                    "game_objective": "Open; infer the completion condition from evidence.",
                    "explanation": str(prior.payload.get("summary") or "Open."),
                    "goal": str(prior.payload.get("objective_hypothesis") or "Open."),
                    "expectation": " · ".join(expectation_parts) or "Open.",
                    "notes": str(prior.payload.get("natural_language") or "Open."),
                }
                stored_scratchpad = canonical_model_scratchpad(stored_scratchpad)
            scratchpad_text = model_scratchpad_text(stored_scratchpad)
            projection = {
                "object_id": prior.object_id,
                "basis_revision": prior.payload.get("basis_revision"),
                "scratchpad": copy.deepcopy(stored_scratchpad),
                "summary": prior.payload.get("summary", ""),
                "prior_natural_language_digest": hashlib.sha256(
                    scratchpad_text.encode("utf-8")
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
        document = {
            **turn.document,
            "prior_working_note": projection,
            "scratchpad_context": scratchpad_context,
        }
        if projection is not None:
            # One canonical WYSIWYG object shared by ordinary semantic turns,
            # explanation consolidation, the durable workspace, and Arcade.
            document["model_scratchpad"] = copy.deepcopy(projection["scratchpad"])
        if consolidation_task is not None:
            document["explanation_consolidation_task"] = consolidation_task
        vocabulary = dict(document.get("allowed_vocabulary", {}))
        if vocabulary:
            # Codec documentation is coordinator bookkeeping, not semantic
            # vocabulary. The projected content remains available without the
            # representation jargon that previously leaked into hypotheses.
            vocabulary.pop("delta_codec", None)
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
                        "type": "array", "minItems": 1, "maxItems": min(6, len(source_refs)),
                        "uniqueItems": True, "items": {"enum": source_refs},
                    },
                    "abstractions": {
                        "type": "array", "uniqueItems": True,
                        "maxItems": MAX_CONSOLIDATION_PROPOSALS,
                        "items": {
                            "type": "object", "additionalProperties": False,
                            "required": ["local_ref", "goal_proposal_index", "applicability_relations", "preserved_structure", "causal_structure", "predicted_reuse", "counterconditions"],
                            "properties": {
                                "local_ref": {"type": "string", "pattern": "^abstraction_[0-9]{1,2}$"},
                                "goal_proposal_index": {"type": "integer", "minimum": 0, "maximum": 2},
                                "applicability_relations": {"type": "array", "maxItems": 6, "items": role_relation},
                                "preserved_structure": {"type": "array", "uniqueItems": True, "maxItems": 5, "items": {"enum": ["topology", "intrinsic_geometry", "component_count", "relative_order", "contact_state", "containment_state"]}},
                                "causal_structure": {"type": "array", "uniqueItems": True, "maxItems": 4, "items": {"enum": ["preserves_intrinsic_structure", "changes_relative_position", "changes_contact", "changes_containment", "changes_component_count", "unknown"]}},
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
            # Keep the transport schema compact.  The compiler below enforces
            # the dependent invariant: propose means 1..3 abstractions and
            # abstain means zero.  JSON validation alone never opens the gate.
            properties["explanation_consolidation"] = {
                "type": "object", "additionalProperties": False,
                "required": consolidation_required,
                "properties": {
                    **consolidation_properties,
                    "decision": {"enum": ["propose", "abstain"]},
                },
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
                **properties["goal_proposals"], "minItems": 0,
                "maxItems": MAX_CONSOLIDATION_PROPOSALS,
            }
            properties["summary"] = {
                **properties["summary"], "maxLength": 240,
            }
            properties["objective_hypothesis"] = {
                **properties["objective_hypothesis"], "maxLength": 160,
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
        is_consolidation = isinstance(
            turn.document.get("explanation_consolidation_task"), Mapping,
        )
        return {
            "type": "object",
            "additionalProperties": False,
            "required": ["protocol", "request_id", "scratchpad", "workspace_write"],
            "properties": {
                "protocol": {"const": turn.document["protocol"]},
                "request_id": {"const": turn.request_id},
                "scratchpad": {
                    "type": "object", "additionalProperties": False,
                    "required": list(MODEL_SCRATCHPAD_FIELDS),
                    "properties": {
                        "game_objective": {
                            "type": "string", "minLength": 1, "maxLength": 280,
                        },
                        "explanation": {"type": "string", "minLength": 1, "maxLength": 360},
                        "goal": {"type": "string", "minLength": 1, "maxLength": 240},
                        "expectation": {"type": "string", "minLength": 1, "maxLength": 240},
                        "notes": {
                            "type": "string", "minLength": 1,
                            "maxLength": 320 if is_consolidation else 900,
                        },
                    },
                },
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
                    "allowed_vocabulary", "model_scratchpad",
                    "explanation_consolidation_task",
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
        prompt = (
            CONSOLIDATION_PROMPT
            if isinstance(consolidation_task, Mapping)
            else qc.PROMPT
        )
        compact_text = prompt + json.dumps(
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
        if isinstance(consolidation_task, Mapping):
            request["max_tokens"] = int(qwen.get(
                "consolidation_max_tokens", DEEP_CONSOLIDATION_MAX_TOKENS,
            ))
            if qwen.get("consolidation_reasoning_effort"):
                request["reasoning_effort"] = str(
                    qwen["consolidation_reasoning_effort"]
                )
            request["thinking_budget_tokens"] = int(qwen.get(
                "consolidation_thinking_budget_tokens",
                DEEP_CONSOLIDATION_THINKING_TOKENS,
            ))
        return request

    def compile_response(response: Mapping[str, Any], turn: Any) -> dict[str, Any]:
        parsed = response.get("parsed", response)
        if not isinstance(parsed, Mapping):
            return original_compile_response(response, turn)
        scratchpad = parsed.get("scratchpad")
        note = parsed.get("workspace_write")
        stripped = dict(parsed)
        stripped.pop("scratchpad", None)
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
        try:
            scratchpad = canonical_model_scratchpad(scratchpad)
        except ValueError:
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "model-scratchpad-contract"}]}
        scratchpad_text = model_scratchpad_text(scratchpad)
        transition_basis = (
            turn.document.get("scratchpad_context", {})
            .get("r2_transition_observation")
            or {}
        )
        turn_evidence_ref = transition_basis.get("evidence_ref")
        latest_evidence_ref = current_transition_evidence_ref()
        if not scratchpad_basis_is_current(turn_evidence_ref):
            return {
                **compilation,
                "rejected": [
                    *compilation.get("rejected", ()),
                    {
                        "reason": "stale-epistemic-scratchpad-basis",
                        "turn_evidence_ref": turn_evidence_ref,
                        "latest_evidence_ref": latest_evidence_ref,
                    },
                ],
            }
        prior_projection = turn.document.get("prior_working_note") or {}
        prior_prose_digest = prior_projection.get("prior_natural_language_digest")
        if (
            isinstance(prior_prose_digest, str)
            and hashlib.sha256(scratchpad_text.encode("utf-8")).hexdigest() == prior_prose_digest
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
        scratch_tokens = qc.GRAPH.estimate_tokens(scratchpad_text)
        action_free_note = {key: value for key, value in note.items() if key != "action_aliases"}
        if has_transport_metadata_leak(scratchpad) or has_transport_metadata_leak(action_free_note):
            return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "transport-metadata-semantic-leak"}]}
        if _has_action_proposal(scratchpad) or _has_action_proposal(action_free_note) or scratch_tokens > MAX_SCRATCHPAD_TOKENS:
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
                or len(source_refs) > 6 or len(set(source_refs)) != len(source_refs)
                or source_boundary_ref not in source_refs
                or not set(source_refs).issubset(allowed_source_refs)
                or not isinstance(abstractions, list)
                or len(abstractions) > MAX_CONSOLIDATION_PROPOSALS
                or (decision == "propose" and not abstractions)
                or (decision == "abstain" and abstractions)
                or (decision == "abstain" and unique_proposals)
                or len(unique_proposals) != len(note["goal_proposals"])
            ):
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-authority"}]}
            normalized_abstractions = []
            used_indices = set()
            used_local_refs = set()
            used_abstraction_cores = set()
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
                "preserved_structure", "causal_structure", "predicted_reuse",
                "counterconditions",
            }
            for abstraction in abstractions:
                if not isinstance(abstraction, Mapping) or set(abstraction) != abstraction_fields:
                    return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-abstraction"}]}
                abstraction = dict(abstraction)
                for field in (
                    "applicability_relations", "preserved_structure",
                    "causal_structure", "predicted_reuse", "counterconditions",
                ):
                    values = abstraction.get(field)
                    if not isinstance(values, list):
                        return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-port-typing"}]}
                    seen_values = set()
                    unique_values = []
                    for value in values:
                        value_hash = qc.stable_hash(value)
                        if value_hash not in seen_values:
                            seen_values.add(value_hash)
                            unique_values.append(value)
                    abstraction[field] = unique_values
                index = abstraction.get("goal_proposal_index")
                if (
                    not isinstance(index, int) or isinstance(index, bool)
                    or index < 0 or index >= len(unique_proposals)
                    or index in used_indices
                    or abstraction.get("local_ref") in used_local_refs
                ):
                    return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-schema-reference"}]}
                used_indices.add(index)
                used_local_refs.add(abstraction.get("local_ref"))
                abstraction_core = {
                    key: value for key, value in abstraction.items()
                    if key not in {"local_ref", "goal_proposal_index"}
                }
                abstraction_core_hash = qc.stable_hash(abstraction_core)
                if abstraction_core_hash in used_abstraction_cores:
                    return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-duplicate"}]}
                used_abstraction_cores.add(abstraction_core_hash)
                roles = set(unique_proposals[index].get("roles", ()))
                relations = abstraction.get("applicability_relations")
                preserved = abstraction.get("preserved_structure")
                causal = abstraction.get("causal_structure")
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
                        preserved, causal, predicted_reuse, counterconditions,
                    )
                ) or (
                    not set(preserved).issubset(allowed_preserved)
                    or not set(causal).issubset(allowed_causal)
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
                    "reuse_scope": "game",
                    "consolidation_source_boundary_ref": source_boundary_ref,
                }
                unique_proposals[index] = schema_definition
                normalized_abstractions.append({
                    **dict(abstraction),
                    "schema_definition": schema_definition,
                    # These are R2 authority-reset facts, not Qwen choices.
                    "nuisance_dimensions": list(MANDATORY_NUISANCE_DIMENSIONS),
                    "unresolved_ports": sorted(roles),
                    "empirical_support": 0,
                    "epistemic_status": "ungrounded-reusable-hypothesis",
                })
            if decision == "propose" and used_indices != set(range(len(unique_proposals))):
                return {**compilation, "rejected": [*compilation.get("rejected", ()), {"reason": "explanation-consolidation-schema-reference"}]}
            consolidation = {
                "protocol": EXPLANATION_CONSOLIDATION_PROTOCOL,
                "operation": "reflective-abstraction",
                "projection_mode": "abstract-explanation-projection",
                "reflection_mode": "deep-synchronous-level-boundary",
                "reuse_scope": "game",
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
            "model_scratchpad": dict(scratchpad),
            "natural_language": scratchpad["notes"],
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
                "content_hash": qc.stable_hash({"scratchpad": scratchpad, "workspace_write": note}),
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
    qc.epistemic_scratchpad_revision_due = (
        lambda state, workspace_id: epistemic_scratchpad_revision_due(
            state, workspace_id, qc
        )
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
    qc.boundary_consolidation_accepted = boundary_consolidation_accepted
