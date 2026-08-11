"""Exact one-step branches and generic successor measurements."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import causal_protocol as cp
import matched_executor


@dataclass(frozen=True, slots=True)
class BranchResult:
    arm: str
    action_id: int
    prefix_exact: bool
    before_digest: str
    after_digest: str
    before_record: Mapping[str, Any]
    after_record: Mapping[str, Any]
    before_grid: Sequence[Sequence[int]]
    after_grid: Sequence[Sequence[int]]
    observables: Mapping[str, Any]
    effect_signature: Mapping[str, Any]
    information_novelty: int
    progress_delta: int
    residual_after: int | None
    hard_risk: bool


def generic_effect_signature(
    *, before_grid: Sequence[Sequence[int]], after_grid: Sequence[Sequence[int]],
    observables: Mapping[str, Any],
) -> dict[str, Any]:
    transitions: Counter[tuple[int, int]] = Counter()
    for left_row, right_row in zip(before_grid, after_grid):
        for left, right in zip(left_row, right_row):
            if int(left) != int(right):
                transitions[(int(left), int(right))] += 1
    bbox = observables.get("changed_bbox")
    extent = None if bbox is None else [
        int(bbox[2]) - int(bbox[0]) + 1,
        int(bbox[3]) - int(bbox[1]) + 1,
    ]
    return {
        "grid_changed": bool(observables["grid_changed"]),
        "changed_cell_count": int(observables["changed_cell_count"]),
        "changed_extent": extent,
        "color_transition_multiset": [
            [left, right, count]
            for (left, right), count in sorted(transitions.items())
        ],
        "level_delta": int(observables["level_delta"]),
        "terminal": bool(observables["terminal"]),
    }

def history_signatures(
    history: Sequence[Mapping[str, Any]], *, action_id: int,
) -> set[str]:
    signatures: set[str] = set()
    for item in history:
        if int(item["action_id"]) != int(action_id):
            continue
        observed = cp.successor_observables(
            before_grid=item["before_grid"], after_grid=item["after_grid"],
            before_record=item["before"], after_record=item["after"],
        )
        signatures.add(cp.stable_hash(generic_effect_signature(
            before_grid=item["before_grid"], after_grid=item["after_grid"],
            observables=observed,
        )))
    return signatures


def run_exact_branch(
    *, base: Any, game: str, environments: Path, recordings: Path,
    prefix: Sequence[Mapping[str, Any]], action_id: int, arm: str,
    expected_before_digest: str, effect_pair: Sequence[str],
) -> BranchResult:
    arcade, environment, observation = base._open_at_prefix(
        game, environments, recordings / arm, prefix
    )
    try:
        before_record = base.BASE.observation_record(observation)
        before_grid = base.BASE.observation_grid(observation)
        prefix_exact = str(before_record["digest"]) == str(expected_before_digest)
        if not prefix_exact:
            raise cp.CausalProtocolError("EXACT_PREFIX_REPLAY_FAILED")
        successor = base.execute_action(
            environment, game, int(action_id), {}, f"precious-action-branch-{arm}"
        )
        after_record = base.BASE.observation_record(successor)
        after_grid = base.BASE.observation_grid(successor)
        observed = cp.successor_observables(
            before_grid=before_grid, after_grid=after_grid,
            before_record=before_record, after_record=after_record,
        )
        signature = generic_effect_signature(
            before_grid=before_grid, after_grid=after_grid, observables=observed,
        )
        prior = history_signatures(prefix, action_id=int(action_id))
        novelty = int(cp.stable_hash(signature) not in prior)
        residual = base._pair_after_residual(before_grid, after_grid, effect_pair)
        progress = int(observed["level_delta"])
        hard_risk = bool(observed["terminal"] and progress <= 0)
        return BranchResult(
            arm=arm, action_id=int(action_id), prefix_exact=True,
            before_digest=str(before_record["digest"]),
            after_digest=str(after_record["digest"]),
            before_record=dict(before_record), after_record=dict(after_record),
            before_grid=[list(row) for row in before_grid],
            after_grid=[list(row) for row in after_grid],
            observables=observed, effect_signature=signature,
            information_novelty=novelty, progress_delta=progress,
            residual_after=residual, hard_risk=hard_risk,
        )
    finally:
        arcade.close_scorecard()


def evaluate_executor_branch(
    *, result: BranchResult, proposal: Mapping[str, Any],
) -> dict[str, Any]:
    selected = cp.validate_decision_coherence(
        proposal,
        legal_actions=[int(item["action_id"]) for item in proposal["candidate_actions"]],
    )
    if selected != result.action_id:
        raise cp.CausalProtocolError("BRANCH_ACTION_DOES_NOT_MATCH_PROPOSAL")
    candidate = next(
        item for item in proposal["candidate_actions"]
        if int(item["action_id"]) == int(selected)
    )
    executable = matched_executor.checkpoint_document(candidate["expected_checkpoint"])
    comparison = cp.compare_checkpoint(executable, observed=result.observables)
    return {
        "branch": asdict(result),
        "checkpoint": executable,
        "checkpoint_result": asdict(comparison),
    }
