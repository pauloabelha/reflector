"""Typed prospective-probe budgets for the v1.9 experiment.

Four probes may be spent on incomplete/non-revision ambiguity.  One distinct
probe is reserved for confirming a unique control-eligible revision.  A plan
demoted at either boundary remains a fallback and never increments any probe
counter, including during deterministic ledger replay.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"
SPEC = importlib.util.spec_from_file_location(
    "prospective_workspace_v19_live_base", V14 / "live_controller.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load v1.4 live controller")
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

AMBIGUOUS_PROBE_LIMIT = 4
REVISION_PROBE_LIMIT = 1
TOTAL_PROBE_LIMIT = AMBIGUOUS_PROBE_LIMIT + REVISION_PROBE_LIMIT


class ProspectiveWorkspaceController(BASE.ProspectiveWorkspaceController):
    """The v1.4 controller with separate ambiguity and revision budgets."""

    def __init__(
        self, *, max_probes: int = TOTAL_PROBE_LIMIT, max_control_decisions: int = 24
    ) -> None:
        if int(max_probes) != TOTAL_PROBE_LIMIT:
            raise ValueError("v1.9 requires a total prospective probe budget of exactly 5")
        # The inherited method performs its own untyped pre-check.  Six keeps
        # that check out of the way while this class admits at most five and
        # rolls back every typed demotion immediately.
        super().__init__(
            max_probes=TOTAL_PROBE_LIMIT + 1,
            max_control_decisions=max_control_decisions,
        )
        self.ambiguous_probe_decisions = 0
        self.revision_probe_decisions = 0

    def _probe_type(self, plan: Any) -> str:
        selected = set(str(item) for item in plan.selected_prediction_ids)
        records = {
            id(record): record
            for prediction in plan.predictions
            if prediction.prediction_id in selected
            for record in (self.last_plan_records.get(prediction.binding_id),)
            if record is not None
        }
        if not records:
            candidate_ids = {
                str(prediction.candidate_id)
                for prediction in plan.predictions
                if prediction.prediction_id in selected
            }
            records = {
                id(record): record
                for record in self.records
                if str(record.candidate_id) in candidate_ids
            }
        values = tuple(records.values())
        return (
            "revision"
            if len(values) == 1 and bool(values[0].control_eligible)
            else "ambiguous"
        )

    @staticmethod
    def _fallback_decision(plan: Any) -> Any:
        return BASE.Q0.Decision(
            action_id=int(plan.action_id),
            fallback_action_id=int(plan.fallback_action_id),
            reason="prospective-fallback",
            template_hash=None,
            residual_before=None,
            predicted_residual_after=None,
            prior_used=False,
        )

    def _admit_or_demote(self, plan: Any) -> tuple[Any, bool]:
        probe_type = self._probe_type(plan)
        used = (
            self.revision_probe_decisions
            if probe_type == "revision"
            else self.ambiguous_probe_decisions
        )
        limit = REVISION_PROBE_LIMIT if probe_type == "revision" else AMBIGUOUS_PROBE_LIMIT
        if used < limit:
            if probe_type == "revision":
                self.revision_probe_decisions += 1
            else:
                self.ambiguous_probe_decisions += 1
            return plan, True
        demoted = BASE.PC.fallback_plan(
            plan,
            action_id=int(plan.fallback_action_id),
            reason=f"{probe_type}-probe-budget-exhausted",
        )
        # super.plan already counted the proposed probe.  A demotion is not a
        # probe, so restore the exact state that existed before that proposal.
        self.probe_decisions -= 1
        self.last_plan = demoted
        return demoted, False

    def plan(
        self,
        legal_actions: Sequence[int],
        *,
        observation_digest: str,
        basis_revision: int,
    ) -> tuple[Any, Any]:
        decision, plan = super().plan(
            legal_actions,
            observation_digest=observation_digest,
            basis_revision=basis_revision,
        )
        if plan.mode != "probe":
            return decision, plan
        plan, admitted = self._admit_or_demote(plan)
        if admitted:
            return decision, plan
        return self._fallback_decision(plan), plan

    def restore_plan(self, value: Mapping[str, Any]) -> None:
        before = self.probe_decisions
        super().restore_plan(value)
        if self.last_plan is None or self.last_plan.mode != "probe":
            return
        probe_type = self._probe_type(self.last_plan)
        if probe_type == "revision":
            self.revision_probe_decisions += 1
            if self.revision_probe_decisions > REVISION_PROBE_LIMIT:
                raise RuntimeError("replayed revision probe exceeds typed budget")
        else:
            self.ambiguous_probe_decisions += 1
            if self.ambiguous_probe_decisions > AMBIGUOUS_PROBE_LIMIT:
                raise RuntimeError("replayed ambiguous probe exceeds typed budget")
        if self.probe_decisions != before + 1:
            raise RuntimeError("replayed probe counter is not deterministic")

    def report(self) -> dict[str, Any]:
        report = super().report()
        typed_total = self.ambiguous_probe_decisions + self.revision_probe_decisions
        if int(report["probe_decisions"]) != typed_total:
            raise RuntimeError("typed and inherited probe counters diverged")
        return {
            **report,
            "typed_probe_budget": {
                "ambiguous_limit": AMBIGUOUS_PROBE_LIMIT,
                "revision_reserved": REVISION_PROBE_LIMIT,
                "total_limit": TOTAL_PROBE_LIMIT,
                "ambiguous_used": self.ambiguous_probe_decisions,
                "revision_used": self.revision_probe_decisions,
                "total_used": typed_total,
                "ambiguous_remaining": AMBIGUOUS_PROBE_LIMIT
                - self.ambiguous_probe_decisions,
                "revision_remaining": REVISION_PROBE_LIMIT
                - self.revision_probe_decisions,
            },
        }


CandidateRecord = BASE.CandidateRecord
PC = BASE.PC
Q0 = BASE.Q0
