"""Frozen causal gates for the Precious Action experiment.

This module has no ARC environment or model dependency.  It validates causal
identity, action authority, code-treatment engagement, executable one-step
checkpoints, and preregistered verdicts.  Language-model output is computation;
only an observed successor can settle a checkpoint.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence


PROTOCOL = "precious-action-causal-v0"
INCONCLUSIVE = "INCONCLUSIVE"
POSITIVE = "POSITIVE"
NEGATIVE = "NEGATIVE"


class CausalProtocolError(ValueError):
    """A hard causal or authority invariant failed."""


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Battlefield:
    decision_index: int
    predecessor_transition_count: int
    before_digest: str
    action_decision_event_id: str
    action_decision_seq: int
    baseline_action: int
    fallback_action: int
    exact_branch_recorded: bool


@dataclass(frozen=True, slots=True)
class IdentityEnvelope:
    protocol: str
    source_commit: str
    source_manifest_hash: str
    config_hash: str
    primitive_version: str
    primitive_source_hash: str
    game: str
    seed: int
    prefix_transition_count: int
    prefix_hash: str
    observation_hash: str
    snapshot_hash: str


@dataclass(frozen=True, slots=True)
class CheckpointResult:
    passed: bool
    predicate_results: tuple[bool, ...]
    predicate_accuracy: float
    confidence: float
    brier_loss: float
    observed: Mapping[str, Any]


@dataclass(frozen=True, slots=True)
class TreatmentResult:
    engaged: bool
    code: str
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Verdict:
    status: str
    code: str
    reasons: tuple[str, ...]
    mechanism_engaged: bool


def select_battlefield(
    *,
    decision_documents: Sequence[Mapping[str, Any]],
    decision_events: Sequence[Mapping[str, Any]],
    counterfactual_branches: Sequence[Mapping[str, Any]],
    minimum_predecessors: int,
) -> Battlefield:
    """Apply the preregistered rule without consulting new B/C outputs."""

    if len(decision_documents) != len(decision_events):
        raise CausalProtocolError("decision documents/events are misaligned")
    exact_by_index = {
        int(item["decision_index"]): item
        for item in counterfactual_branches
        if bool(item.get("actual_exact_replay"))
    }
    for index, (document, event) in enumerate(zip(decision_documents, decision_events)):
        decision = document.get("decision", {})
        plan = document.get("prospective_plan", {})
        branch = exact_by_index.get(index)
        if (
            index < int(minimum_predecessors)
            or not bool(document.get("qwen_changed_action"))
            or not bool(decision.get("prior_used"))
            or str(plan.get("mode")) != "control"
            or branch is None
        ):
            continue
        actual = branch.get("actual", {})
        fallback = branch.get("fallback", {})
        before_digest = str(actual.get("before_digest", ""))
        if not before_digest or before_digest != str(fallback.get("before_digest", "")):
            raise CausalProtocolError("recorded branch does not share an exact predecessor")
        if int(actual.get("action_id")) != int(decision.get("action_id")):
            raise CausalProtocolError("recorded branch disagrees with baseline decision")
        return Battlefield(
            decision_index=index,
            predecessor_transition_count=index,
            before_digest=before_digest,
            action_decision_event_id=str(event["event_id"]),
            action_decision_seq=int(event["seq"]),
            baseline_action=int(decision["action_id"]),
            fallback_action=int(decision["fallback_action_id"]),
            exact_branch_recorded=True,
        )
    raise CausalProtocolError("NO_PREREGISTERED_BATTLEFIELD")


def assert_same_identity(envelopes: Sequence[IdentityEnvelope]) -> None:
    if len(envelopes) < 2:
        raise CausalProtocolError("identity comparison needs at least two arms")
    first = asdict(envelopes[0])
    for envelope in envelopes[1:]:
        if asdict(envelope) != first:
            raise CausalProtocolError("ARM_IDENTITY_MISMATCH")


def executor_route(trigger_reasons: Sequence[str], *, legal_actions: Sequence[int]) -> tuple[str, ...]:
    """B/C always reach their sole policy head when a primitive is legal.

    The ambiguity trigger is diagnostic, not permission for R2 to regain action
    authority.  This closes the prior experiment's no-trigger termination hole.
    """

    if not tuple(legal_actions):
        return ()
    reasons = tuple(str(item) for item in trigger_reasons if str(item).strip())
    return reasons or ("SOLE_POLICY_DECISION_BOUNDARY",)


def validate_history_dependencies(
    dependency_ids: Sequence[str], *, transition_ids: Sequence[str]
) -> None:
    """Prevent an empty or truncated history from supporting invented queries."""

    available = {str(item) for item in transition_ids}
    claimed = {str(item) for item in dependency_ids if str(item).startswith("t")}
    if not claimed <= available:
        raise CausalProtocolError("HISTORY_DEPENDENCY_NOT_AVAILABLE")


def validate_decision_coherence(
    proposal: Mapping[str, Any], *, legal_actions: Sequence[int]
) -> int | None:
    """Validate decision semantics independently of JSON-schema conformance."""

    legal = {int(item) for item in legal_actions}
    raw_candidates = proposal.get("candidate_actions", proposal.get("candidates"))
    if not isinstance(raw_candidates, list) or not raw_candidates:
        raise CausalProtocolError("RANKED_CANDIDATES_REQUIRED")
    ranked = [int(item["action_id"]) for item in raw_candidates]
    if len(ranked) != len(set(ranked)) or any(item not in legal for item in ranked):
        raise CausalProtocolError("ILLEGAL_OR_DUPLICATE_CANDIDATE")
    decision = proposal.get("decision")
    if not isinstance(decision, Mapping):
        raise CausalProtocolError("DECISION_REQUIRED")
    kind = str(decision.get("kind", "")).lower()
    if kind == "select":
        selected = int(decision["action_id"])
        if selected not in ranked:
            raise CausalProtocolError("SELECTED_ACTION_NOT_RANKED")
        return selected
    if kind != "abstain":
        raise CausalProtocolError("DECISION_MUST_SELECT_OR_ABSTAIN")
    reason = str(decision.get("reason", "")).upper()
    allowed = {
        "NO_LEGAL_ACTION",
        "SNAPSHOT_OR_TOOLING_INSUFFICIENT",
        "HARD_RISK_BLOCKED",
        "NO_DISCRIMINATING_ACTION",
    }
    if reason not in allowed:
        raise CausalProtocolError("UNTYPED_ABSTENTION")
    if reason == "NO_LEGAL_ACTION" and legal:
        raise CausalProtocolError("INCOHERENT_NO_LEGAL_ACTION")
    if reason == "SNAPSHOT_OR_TOOLING_INSUFFICIENT" and not proposal.get("missing_operation"):
        raise CausalProtocolError("TOOLING_ABSTENTION_REQUIRES_GAP")
    if reason in {"HARD_RISK_BLOCKED", "NO_DISCRIMINATING_ACTION"} and not proposal.get("abstention_dependencies"):
        raise CausalProtocolError("ABSTENTION_REQUIRES_DEPENDENCIES")
    return None


def assess_treatment(
    *, arm: str, computation: Mapping[str, Any], proposal: Mapping[str, Any]
) -> TreatmentResult:
    """Determine whether the intended B/C intervention actually occurred."""

    if arm == "arm-b":
        reasons = []
        if str(computation.get("mode")) != "verbal":
            reasons.append("B_NOT_VERBAL")
        if computation.get("python_status") is not None:
            reasons.append("B_PYTHON_LEAKAGE")
        return TreatmentResult(not reasons, "VERBAL_EXECUTOR", tuple(reasons))
    if arm != "arm-c":
        raise CausalProtocolError("treatment is defined only for B/C")

    reasons: list[str] = []
    if str(computation.get("mode")) != "python":
        reasons.append("PYTHON_MODE_NOT_SELECTED")
    if not str(computation.get("generated_code") or "").strip():
        reasons.append("EMPTY_CODE")
    if str(computation.get("python_status")) != "ok":
        reasons.append("PYTHON_NOT_SUCCESSFUL")
    if not computation.get("code_hash"):
        reasons.append("CODE_HASH_MISSING")
    if "structured_return_value" not in computation:
        reasons.append("STRUCTURED_RETURN_MISSING")
    computation_id = str(computation.get("computation_id", ""))
    selected = validate_decision_coherence(
        proposal, legal_actions=[int(item["action_id"]) for item in proposal.get("candidate_actions", ())]
    )
    selected_candidate = next(
        (item for item in proposal.get("candidate_actions", ()) if int(item["action_id"]) == selected),
        None,
    )
    cited = () if selected_candidate is None else selected_candidate.get("computation_dependencies", ())
    if not computation_id or computation_id not in {str(item) for item in cited}:
        reasons.append("SELECTED_PROPOSAL_DOES_NOT_CITE_COMPUTATION")
    finding_refs = () if selected_candidate is None else selected_candidate.get("finding_refs", ())
    if not finding_refs:
        reasons.append("SELECTED_PROPOSAL_DOES_NOT_CITE_FINDING")
    return TreatmentResult(not reasons, "PYTHON_EXECUTOR", tuple(reasons))


def _bbox(changed: Sequence[Sequence[int]]) -> list[int] | None:
    if not changed:
        return None
    return [
        min(int(item[0]) for item in changed),
        min(int(item[1]) for item in changed),
        max(int(item[0]) for item in changed),
        max(int(item[1]) for item in changed),
    ]


def successor_observables(
    *,
    before_grid: Sequence[Sequence[int]],
    after_grid: Sequence[Sequence[int]],
    before_record: Mapping[str, Any],
    after_record: Mapping[str, Any],
) -> dict[str, Any]:
    changed: list[list[int]] = []
    if len(before_grid) != len(after_grid) or any(
        len(left) != len(right) for left, right in zip(before_grid, after_grid)
    ):
        raise CausalProtocolError("GRID_SHAPE_MISMATCH")
    for row, (left, right) in enumerate(zip(before_grid, after_grid)):
        for column, (before, after) in enumerate(zip(left, right)):
            if int(before) != int(after):
                changed.append([row, column, int(before), int(after)])
    before_levels = int(before_record.get("levels_completed", 0))
    after_levels = int(after_record.get("levels_completed", 0))
    terminal = after_record.get("state") or after_record.get("terminal_state")
    terminal_normalized = None if terminal is None else str(terminal).upper()
    return {
        "grid_changed": bool(changed),
        "changed_cell_count": len(changed),
        "changed_bbox": _bbox(changed),
        "level_delta": after_levels - before_levels,
        "terminal_status": terminal,
        "terminal": terminal_normalized not in {None, "", "NOT_FINISHED", "RUNNING"},
        "after_digest": str(after_record.get("digest", "")),
    }


def _predicate_result(predicate: Mapping[str, Any], observed: Mapping[str, Any]) -> bool:
    observable = str(predicate.get("observable"))
    if observable not in {
        "grid_changed", "changed_cell_count", "changed_bbox", "level_delta",
        "terminal_status", "terminal",
    }:
        raise CausalProtocolError(f"UNSUPPORTED_CHECKPOINT_OBSERVABLE:{observable}")
    actual = observed[observable]
    operator = str(predicate.get("operator"))
    expected = predicate.get("value")
    operations = {
        "eq": lambda: actual == expected,
        "ne": lambda: actual != expected,
        "gt": lambda: actual > expected,
        "ge": lambda: actual >= expected,
        "lt": lambda: actual < expected,
        "le": lambda: actual <= expected,
        "in": lambda: actual in expected,
    }
    if operator not in operations:
        raise CausalProtocolError(f"UNSUPPORTED_CHECKPOINT_OPERATOR:{operator}")
    try:
        return bool(operations[operator]())
    except TypeError as error:
        raise CausalProtocolError("INVALID_CHECKPOINT_VALUE") from error


def compare_checkpoint(
    checkpoint: Mapping[str, Any], *, observed: Mapping[str, Any]
) -> CheckpointResult:
    predicates = checkpoint.get("predicates")
    if not isinstance(predicates, list) or not 1 <= len(predicates) <= 6:
        raise CausalProtocolError("CHECKPOINT_REQUIRES_1_TO_6_PREDICATES")
    confidence = float(checkpoint.get("confidence", -1.0))
    if not 0.0 <= confidence <= 1.0:
        raise CausalProtocolError("CHECKPOINT_CONFIDENCE_OUT_OF_RANGE")
    results = tuple(_predicate_result(item, observed) for item in predicates)
    passed = all(results)
    accuracy = sum(results) / len(results)
    brier = (confidence - float(passed)) ** 2
    return CheckpointResult(
        passed=passed,
        predicate_results=results,
        predicate_accuracy=accuracy,
        confidence=confidence,
        brier_loss=brier,
        observed=dict(observed),
    )


def adjudicate_verdict(
    *,
    identity_ok: bool,
    replay_ok: bool,
    b_valid: bool,
    c_valid: bool,
    c_treatment: TreatmentResult,
    computation_changed_action: bool,
    c_checkpoint_brier: float | None,
    b_checkpoint_brier: float | None,
    c_progress: int | None,
    b_progress: int | None,
    c_information: int | None,
    b_information: int | None,
    c_hard_risk_regression: bool,
) -> Verdict:
    broken: list[str] = []
    if not identity_ok:
        broken.append("ARM_IDENTITY_MISMATCH")
    if not replay_ok:
        broken.append("EXACT_REPLAY_FAILED")
    if not b_valid:
        broken.append("B_PROPOSAL_INVALID")
    if not c_valid:
        broken.append("C_PROPOSAL_INVALID")
    if not c_treatment.engaged:
        broken.extend(c_treatment.reasons or ("TREATMENT_NOT_ENGAGED",))
    metrics = (c_checkpoint_brier, b_checkpoint_brier, c_progress, b_progress, c_information, b_information)
    if any(item is None for item in metrics):
        broken.append("COMPARISON_METRIC_MISSING")
    if broken:
        return Verdict(INCONCLUSIVE, "CAUSAL_PRECONDITION_FAILED", tuple(broken), c_treatment.engaged)

    assert c_checkpoint_brier is not None and b_checkpoint_brier is not None
    assert c_progress is not None and b_progress is not None
    assert c_information is not None and b_information is not None
    improved = (
        c_checkpoint_brier < b_checkpoint_brier
        or c_progress > b_progress
        or c_information > b_information
    )
    if computation_changed_action and improved and not c_hard_risk_regression:
        return Verdict(POSITIVE, "CODE_MEDIATED_CAUSAL_SPECIMEN", (), True)
    reasons = []
    if not computation_changed_action:
        reasons.append("NO_CODE_MEDIATED_ACTION_CHANGE")
    if not improved:
        reasons.append("NO_TARGET_OUTCOME_IMPROVEMENT")
    if c_hard_risk_regression:
        reasons.append("HARD_RISK_REGRESSION")
    return Verdict(NEGATIVE, "TREATMENT_ENGAGED_WITHOUT_QUALIFYING_GAIN", tuple(reasons), True)


def adjudicate_executor_vs_baseline(
    *, label: str, identity_ok: bool, replay_ok: bool, executor_valid: bool,
    action_changed: bool, executor_progress: int | None,
    baseline_progress: int | None, executor_information: int | None,
    baseline_information: int | None, hard_risk_regression: bool,
) -> Verdict:
    """Frozen one-step system comparison for B>A and C>A.

    A has no matched Executor checkpoint, so this deliberately uses only
    environment-authored progress, generic information novelty, and hard risk.
    Calibration remains exclusive to the matched B/C mechanism comparison.
    """

    broken: list[str] = []
    if not identity_ok:
        broken.append("ARM_IDENTITY_MISMATCH")
    if not replay_ok:
        broken.append("EXACT_REPLAY_FAILED")
    if not executor_valid:
        broken.append("EXECUTOR_PROPOSAL_INVALID")
    if executor_progress is None or baseline_progress is None:
        broken.append("PROGRESS_METRIC_MISSING")
    if executor_information is None or baseline_information is None:
        broken.append("INFORMATION_METRIC_MISSING")
    if broken:
        return Verdict(
            INCONCLUSIVE, f"{label}_CAUSAL_PRECONDITION_FAILED",
            tuple(broken), False,
        )
    improved = (
        int(executor_progress) > int(baseline_progress)
        or int(executor_information) > int(baseline_information)
    )
    if action_changed and improved and not hard_risk_regression:
        return Verdict(
            POSITIVE, f"{label}_FAVORABLE_ACTION_CHANGE",
            ("TARGET_OUTCOME_IMPROVED",), True,
        )
    reasons: list[str] = []
    if not action_changed:
        reasons.append("NO_ACTION_CHANGE")
    if not improved:
        reasons.append("NO_TARGET_OUTCOME_IMPROVEMENT")
    if hard_risk_regression:
        reasons.append("HARD_RISK_REGRESSION")
    return Verdict(NEGATIVE, f"{label}_NO_QUALIFYING_GAIN", tuple(reasons), True)
