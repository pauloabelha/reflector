"""Explanation-guided, exactly-one-action policy adapter."""

from __future__ import annotations

from dataclasses import asdict
import sys
from typing import Any, Sequence


def _components(grid: Any) -> list[tuple[int, int, int, int, int, int]]:
    """Color components as (color, area, min_y, min_x, cy2, cx2)."""
    rows = [list(row) for row in grid]
    if not rows:
        return []
    counts: dict[int, int] = {}
    for row in rows:
        for value in row: counts[int(value)] = counts.get(int(value), 0) + 1
    background = max(counts, key=counts.get)
    seen: set[tuple[int, int]] = set(); output = []
    for y, row in enumerate(rows):
        for x, value in enumerate(row):
            if int(value) == background or (y, x) in seen: continue
            stack = [(y, x)]; seen.add((y, x)); cells = []
            while stack:
                cy, cx = stack.pop(); cells.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < len(rows) and 0 <= nx < len(rows[ny]) and (ny, nx) not in seen and int(rows[ny][nx]) == int(value):
                        seen.add((ny, nx)); stack.append((ny, nx))
            output.append((int(value), len(cells), min(p[0] for p in cells), min(p[1] for p in cells), sum(p[0] for p in cells) * 2 // len(cells), sum(p[1] for p in cells) * 2 // len(cells)))
    return sorted(output, key=lambda item: (item[2], item[3], item[0]))


def action_trace(action: int, before: Any, after: Any) -> str:
    if before == after:
        return f"Action {action} → no visible change."
    before_items, after_items, messages = _components(before), _components(after), []
    used: set[int] = set()
    for index, item in enumerate(before_items):
        candidates = [(abs(item[4] - other[4]) + abs(item[5] - other[5]), pos, other) for pos, other in enumerate(after_items) if pos not in used and other[:2] == item[:2]]
        if not candidates: continue
        _distance, pos, other = min(candidates); used.add(pos)
        dy, dx = (other[4] - item[4]) // 2, (other[5] - item[5]) // 2
        parts = []
        if dy: parts.append(f"{'down' if dy > 0 else 'up'} {abs(dy)}")
        if dx: parts.append(f"{'right' if dx > 0 else 'left'} {abs(dx)}")
        if parts: messages.append(f"f{index:02d} moved {' and '.join(parts)}")
    return f"Action {action} → " + ("; ".join(messages) if messages else "visible configuration changed; object correspondence unresolved.")


def controller_class(live_controller: Any, runtime: Any | None = None) -> type:
    base = live_controller.ProspectiveWorkspaceController

    class OneActionController(base):
        """Choose one intervention for progress, information, or both."""

        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            self.no_change_attempts: dict[tuple[str, int], int] = {}
            self.current_observation_digest = ""
            self.last_contract: dict[str, Any] | None = None
            self.settlements: list[dict[str, Any]] = []

        def plan(self, legal_actions: Sequence[int], *, observation_digest: str, basis_revision: int) -> tuple[Any, Any]:
            self.current_observation_digest = str(observation_digest)
            decision, plan = super().plan(
                legal_actions,
                observation_digest=observation_digest,
                basis_revision=basis_revision,
            )
            legal = tuple(sorted(set(int(item) for item in legal_actions)))
            repeated_no_change = self.no_change_attempts.get((str(observation_digest), int(decision.action_id)), 0)
            if repeated_no_change:
                alternatives = [
                    action for action in legal
                    if self.no_change_attempts.get((str(observation_digest), action), 0) == 0
                ]
                if alternatives:
                    replacement = min(alternatives, key=lambda action: (self.action_uses.get(action, 0), action))
                    decision = type(decision)(
                        action_id=replacement,
                        fallback_action_id=decision.fallback_action_id,
                        reason="information-after-no-change",
                        template_hash=None,
                        residual_before=None,
                        predicted_residual_after=None,
                        prior_used=False,
                    )
                    plan = live_controller.PC.fallback_plan(plan, action_id=replacement, reason="same-state-no-change-excluded")
                    self.last_plan = plan

            selected = [
                prediction for prediction in plan.predictions
                if prediction.prediction_id in plan.selected_prediction_ids
            ]
            improvements = [
                prediction.current_residual - prediction.predicted_residual
                for prediction in selected if prediction.predicted_residual is not None
            ]
            if plan.mode == "control":
                role = "goal-progress"
            elif plan.probe_basis == "single-binding-confirmation" and any(value > 0 for value in improvements):
                role = "progress-and-information"
            else:
                role = "information"
            active = self._active_records()
            situated_explanations = [
                {
                    "kind": "situated-control-explanation",
                    "schema_object_id": item.schema_object_id,
                    "binding_object_id": item.graph_binding_id,
                    "operator": item.operator,
                    "effect_pair": list(item.effect_pair),
                    "control_eligible": item.control_eligible,
                    "confirmations": item.prospective_confirmations,
                    "refutations": item.prospective_refutations,
                }
                for item in active
            ]
            winning_family = {
                "kind": "winning-explanation-family",
                "status": "exists-unidentified",
                "nonempty": True,
                "candidate_first_interventions": len(legal),
                "completeness_assumption": (
                    "the environment is solvable and the open transition-model family "
                    "contains its true dynamics"
                ),
                "grounded_from": "current-frame",
            }
            ranked_actions = [int(decision.action_id), *(
                action for action in sorted(
                    (item for item in legal if item != int(decision.action_id)),
                    key=lambda action: (
                        self.no_change_attempts.get((str(observation_digest), action), 0),
                        self.action_uses.get(action, 0),
                        action,
                    ),
                )
            )]
            top_actions = [
                {
                    "rank": rank,
                    "action": action,
                    "selected": rank == 1,
                    "role": role if rank == 1 else "next-alternative",
                    "prior_uses": self.action_uses.get(action, 0),
                    "same-frame_no_change": self.no_change_attempts.get((str(observation_digest), action), 0),
                }
                for rank, action in enumerate(ranked_actions[:3], start=1)
            ]
            salient_schemas = [
                {
                    "schema_object_id": item.schema_object_id,
                    "operator": item.operator,
                    "effect_pair": list(item.effect_pair),
                    "control_eligible": item.control_eligible,
                    "confirmations": item.prospective_confirmations,
                    "refutations": item.prospective_refutations,
                }
                for item in active[:5]
            ]
            self.last_contract = {
                "protocol": "one-action-decision-v0",
                "basis_revision": int(basis_revision),
                "observation_digest": str(observation_digest),
                "objective": {
                    "kind": "relational-residual-objective",
                    "direction": "decrease",
                    "terminal_condition": "environment level increment",
                },
                "winning_explanation_set": winning_family,
                "explanations": [winning_family, *situated_explanations],
                "current_explanation": situated_explanations[0] if situated_explanations else winning_family,
                "top_actions": top_actions,
                "salient_schemas": salient_schemas,
                "candidate_count": len(legal),
                "selected_action": int(decision.action_id),
                "selection_role": role,
                "selection_rule": "lexicographic(progress, decision-relevant-information, support, novelty, stable-id)",
                "predictions": [asdict(item) for item in selected],
                "repeated_identical_no_change_excluded": bool(repeated_no_change),
                "one_external_action_only": True,
            }
            return decision, plan

        def observe(self, action: int, before_grid: Any, after_grid: Any) -> dict[str, Any]:
            learning = super().observe(action, before_grid, after_grid)
            changed = before_grid != after_grid
            if not changed:
                key = (self.current_observation_digest, int(action))
                self.no_change_attempts[key] = self.no_change_attempts.get(key, 0) + 1
            settlement = {
                "action": int(action),
                "predecessor_digest": self.current_observation_digest,
                "observation_changed": bool(changed),
                "outcome": "changed" if changed else "no-visible-change",
                "prospective_adjudication": learning.get("prospective_adjudication"),
            }
            self.settlements.append(settlement)
            if runtime is not None:
                trace = action_trace(int(action), before_grid, after_grid)
                runtime.record_r2_action_trace(trace)
                scratchpad = sys.modules.get("one_action_scratchpad")
                record = getattr(scratchpad, "record_r2_action_trace", None)
                if callable(record):
                    record(trace)
                runtime.update(settlement=settlement)
            return {**learning, "one_action_settlement": settlement}

        def report(self) -> dict[str, Any]:
            return {
                **super().report(),
                "decision_contract": self.last_contract,
                "no_change_attempt_count": sum(self.no_change_attempts.values()),
                "latest_settlement": self.settlements[-1] if self.settlements else None,
            }

    OneActionController.__name__ = "OneActionController"
    return OneActionController
