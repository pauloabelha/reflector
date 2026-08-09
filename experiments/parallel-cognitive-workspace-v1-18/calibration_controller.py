"""Generic action-effect calibration for unique, unmodelled grounded bindings.

Calibration selects an unknown prediction before acting and records the direct
outcome as control competence only.  It never creates epistemic support or a
prospective confirmation.  A later modeled prediction must still be committed
and matched by reality before ordinary control is eligible.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


CALIBRATION_PROBE_BASIS = "unique-binding-action-calibration"
MAX_CALIBRATION_PROBES = 8


def install(base: Any, live_owner: Any) -> type:
    """Install the calibration planner/controller into the active runner."""

    pc = live_owner.PC
    inherited_planner = pc.ProspectiveController
    inherited_controller = live_owner.ProspectiveWorkspaceController
    core_controller = live_owner.BASE.ProspectiveWorkspaceController

    class CalibrationPlanner(inherited_planner):
        def plan(
            self,
            legal_actions: Sequence[int],
            *,
            observation_digest: str,
            basis_revision: int,
            action_uses: Mapping[int, int] | None = None,
        ) -> Any:
            plan = super().plan(
                legal_actions,
                observation_digest=observation_digest,
                basis_revision=basis_revision,
                action_uses=action_uses,
            )
            if len(self.bindings) != 1 or self.bindings[0].confirmations != 0:
                return plan
            unknown = [item for item in plan.predictions if not item.modeled]
            selected = next(
                (
                    item
                    for item in plan.predictions
                    if item.prediction_id in plan.selected_prediction_ids
                ),
                None,
            )
            binding = self.bindings[0]
            preferred_gain = None
            if selected is not None and selected.predicted_residual is not None:
                preferred_gain = (
                    selected.current_residual - selected.predicted_residual
                    if binding.operator == "Decrease"
                    else selected.predicted_residual - selected.current_residual
                )
            # Preserve an already modeled, operator-improving confirmation.
            if plan.mode == "probe" and preferred_gain is not None and preferred_gain > 0:
                return plan
            # Direct zero effects are useful invariant calibration models, but
            # matching them would not test the schema's preferred consequence.
            # Once every action is calibrated and none improves the potential,
            # abstain instead of laundering invariance into support.
            if not unknown:
                if plan.mode == "probe" and (preferred_gain is None or preferred_gain <= 0):
                    return pc.fallback_plan(
                        plan,
                        action_id=plan.fallback_action_id,
                        reason="calibrated-no-operator-improving-action",
                    )
                return plan
            uses = {int(key): int(value) for key, value in (action_uses or {}).items()}
            chosen = min(unknown, key=lambda item: (uses.get(item.action_id, 0), item.action_id))
            identity = {
                "source_plan_id": plan.plan_id,
                "binding_id": chosen.binding_id,
                "prediction_id": chosen.prediction_id,
                "probe_basis": CALIBRATION_PROBE_BASIS,
            }
            return pc.ControlPlan(
                plan_id=pc.stable_id("cp", identity),
                basis_revision=plan.basis_revision,
                observation_digest=plan.observation_digest,
                mode="probe",
                action_id=chosen.action_id,
                fallback_action_id=plan.fallback_action_id,
                predictions=plan.predictions,
                selected_prediction_ids=(chosen.prediction_id,),
                discrimination_pairs=0,
                probe_basis=CALIBRATION_PROBE_BASIS,
            )

    pc.ProspectiveController = CalibrationPlanner

    class CalibrationWorkspaceController(inherited_controller):
        def __init__(self, *, max_probes: int = 5, max_control_decisions: int = 24) -> None:
            super().__init__(
                max_probes=max_probes,
                max_control_decisions=max_control_decisions,
            )
            self.max_probes = int(self.max_probes) + MAX_CALIBRATION_PROBES
            self.calibration_probe_decisions = 0
            self.calibration_samples: list[dict[str, Any]] = []

        def _probe_type(self, plan: Any) -> str:
            if plan.probe_basis == CALIBRATION_PROBE_BASIS:
                return "calibration"
            return super()._probe_type(plan)

        def _admit_or_demote(self, plan: Any) -> tuple[Any, bool]:
            if self._probe_type(plan) != "calibration":
                return super()._admit_or_demote(plan)
            if self.calibration_probe_decisions < MAX_CALIBRATION_PROBES:
                self.calibration_probe_decisions += 1
                return plan, True
            demoted = pc.fallback_plan(
                plan,
                action_id=int(plan.fallback_action_id),
                reason="calibration-probe-budget-exhausted",
            )
            self.probe_decisions -= 1
            self.last_plan = demoted
            return demoted, False

        def observe(self, action: int, before_grid: Any, after_grid: Any) -> dict[str, Any]:
            learning = super().observe(action, before_grid, after_grid)
            plan = self.last_plan
            if plan is None or plan.probe_basis != CALIBRATION_PROBE_BASIS:
                return learning
            selected = set(str(item) for item in plan.selected_prediction_ids)
            judgment = next(
                (
                    item
                    for item in learning.get("prospective_adjudication", {}).get("judgments", ())
                    if str(item.get("prediction_id")) in selected
                ),
                None,
            )
            if judgment is None or judgment.get("observed_delta") is None:
                sample = {
                    "plan_id": plan.plan_id,
                    "action_id": int(action),
                    "direct": False,
                    "model_created": False,
                }
                self.calibration_samples.append(sample)
                return {**learning, "calibration_sample": sample}
            prediction = next(
                item for item in plan.predictions if item.prediction_id in selected
            )
            record = self.last_plan_records[prediction.binding_id]
            delta = tuple(int(item) for item in judgment["observed_delta"])
            values = record.pair_binding.action_deltas.setdefault(int(action), [])
            # The inherited learner already stores nonzero direct effects.  It
            # intentionally drops zeros, which are meaningful invariant models
            # for calibration and must be retained here.
            if not values:
                values.append(delta)
            sample = {
                "plan_id": plan.plan_id,
                "prediction_id": prediction.prediction_id,
                "binding_id": prediction.binding_id,
                "candidate_id": prediction.candidate_id,
                "action_id": int(action),
                "direct": True,
                "observed_delta": list(delta),
                "observed_residual": judgment.get("observed_residual"),
                "model_created": True,
                "epistemic_support_delta": 0,
            }
            self.calibration_samples.append(sample)
            return {**learning, "calibration_sample": sample}

        def restore_plan(self, value: Mapping[str, Any]) -> None:
            probe_basis = value.get("probe_basis")
            if probe_basis != CALIBRATION_PROBE_BASIS:
                super().restore_plan(value)
                return
            core_controller.restore_plan(self, value)
            self.calibration_probe_decisions += 1
            if self.calibration_probe_decisions > MAX_CALIBRATION_PROBES:
                raise RuntimeError("replayed calibration probe exceeds typed budget")

        def report(self) -> dict[str, Any]:
            report = core_controller.report(self)
            typed_total = (
                int(self.ambiguous_probe_decisions)
                + int(self.revision_probe_decisions)
                + int(self.calibration_probe_decisions)
            )
            if int(report["probe_decisions"]) != typed_total:
                raise RuntimeError("calibration and inherited probe counters diverged")
            return {
                **report,
                "calibration_samples": list(self.calibration_samples),
                "typed_probe_budget": {
                    "ambiguous_limit": int(live_owner.AMBIGUOUS_PROBE_LIMIT),
                    "revision_reserved": int(live_owner.REVISION_PROBE_LIMIT),
                    "calibration_limit": MAX_CALIBRATION_PROBES,
                    "ambiguous_used": int(self.ambiguous_probe_decisions),
                    "revision_used": int(self.revision_probe_decisions),
                    "calibration_used": int(self.calibration_probe_decisions),
                    "total_used": typed_total,
                },
            }

    base.LC.ProspectiveWorkspaceController = CalibrationWorkspaceController
    return CalibrationWorkspaceController
