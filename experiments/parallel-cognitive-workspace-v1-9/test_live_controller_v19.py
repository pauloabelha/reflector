from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "prospective_workspace_v19_live_test", HERE / "live_controller.py"
)
assert SPEC is not None and SPEC.loader is not None
LIVE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LIVE
SPEC.loader.exec_module(LIVE)


def prediction(candidate_id: str, ordinal: int = 0) -> Any:
    return LIVE.PC.ProspectivePrediction(
        prediction_id=f"pp:{candidate_id}:{ordinal}",
        binding_id=f"lb:{candidate_id}",
        candidate_id=candidate_id,
        action_id=1,
        basis_revision=ordinal,
        current_residual=4,
        predicted_residual=2,
        predicted_delta=(2, 0),
        model_support=1,
        modeled=True,
    )


def probe_plan(candidate_id: str, ordinal: int = 0) -> Any:
    item = prediction(candidate_id, ordinal)
    return LIVE.PC.ControlPlan(
        plan_id=f"cp:{candidate_id}:{ordinal}",
        basis_revision=ordinal,
        observation_digest=f"frame:{ordinal}",
        mode="probe",
        action_id=1,
        fallback_action_id=2,
        predictions=(item,),
        selected_prediction_ids=(item.prediction_id,),
        discrimination_pairs=1,
        probe_basis="test",
    )


def fallback_plan(ordinal: int = 0) -> Any:
    source = probe_plan("fallback", ordinal)
    return LIVE.PC.fallback_plan(
        source, action_id=2, reason="ambiguous-probe-budget-exhausted"
    )


def candidate_record(candidate_id: str, *, revision: bool, activated: int) -> Any:
    return LIVE.CandidateRecord(
        schema_object_id=f"schema:{candidate_id}",
        template_hash=f"template:{candidate_id}",
        candidate_id=candidate_id,
        operator="Decrease",
        effect_pair=("left", "right"),
        pair_binding=SimpleNamespace(action_deltas={}),
        activated_at_action=activated,
        revision_of="schema:prior" if revision else None,
        population_complete=True,
        unique_population=revision,
    )


def install_fake_parent(monkeypatch: Any, plans: list[tuple[Any, bool]]) -> None:
    def fake_parent_plan(self: Any, *_args: Any, **_kwargs: Any) -> tuple[Any, Any]:
        plan, revision = plans.pop(0)
        record = SimpleNamespace(control_eligible=revision, candidate_id=plan.predictions[0].candidate_id)
        self.last_plan_records = {plan.predictions[0].binding_id: record}
        self.last_plan = plan
        if plan.mode == "probe":
            self.probe_decisions += 1
        return (
            LIVE.Q0.Decision(
                action_id=plan.action_id,
                fallback_action_id=plan.fallback_action_id,
                reason="prospective-probe",
                template_hash="template",
                residual_before=4,
                predicted_residual_after=2,
                prior_used=False,
            ),
            plan,
        )

    monkeypatch.setattr(LIVE.BASE.ProspectiveWorkspaceController, "plan", fake_parent_plan)


def test_four_ambiguous_probes_leave_reserved_revision_probe(monkeypatch: Any) -> None:
    plans = [(probe_plan("ambiguous", index), False) for index in range(5)]
    plans.append((probe_plan("revision", 5), True))
    plans.append((probe_plan("revision", 6), True))
    install_fake_parent(monkeypatch, plans)
    controller = LIVE.ProspectiveWorkspaceController(max_probes=5)

    results = [
        controller.plan((1, 2), observation_digest=f"f:{index}", basis_revision=index)
        for index in range(7)
    ]

    assert [plan.mode for _decision, plan in results] == [
        "probe", "probe", "probe", "probe", "fallback", "probe", "fallback"
    ]
    assert results[4][1].probe_basis == "ambiguous-probe-budget-exhausted"
    assert results[6][1].probe_basis == "revision-probe-budget-exhausted"
    assert results[4][0].prior_used is False
    assert results[4][0].action_id == results[4][0].fallback_action_id == 2
    report = controller.report()
    assert report["probe_decisions"] == 5
    assert report["typed_probe_budget"] == {
        "ambiguous_limit": 4,
        "revision_reserved": 1,
        "total_limit": 5,
        "ambiguous_used": 4,
        "revision_used": 1,
        "total_used": 5,
        "ambiguous_remaining": 0,
        "revision_remaining": 0,
    }


def test_demoted_and_replayed_fallbacks_do_not_count() -> None:
    controller = LIVE.ProspectiveWorkspaceController(max_probes=5)
    controller.restore_plan(LIVE.PC.document(fallback_plan()))

    assert controller.probe_decisions == 0
    assert controller.ambiguous_probe_decisions == 0
    assert controller.revision_probe_decisions == 0
    assert controller.report()["typed_probe_budget"]["total_used"] == 0


def test_replay_reconstructs_typed_counts_deterministically() -> None:
    controller = LIVE.ProspectiveWorkspaceController(max_probes=5)
    ambiguous_record = candidate_record("ambiguous", revision=False, activated=0)
    controller.records.append(ambiguous_record)
    for index in range(4):
        controller.restore_plan(LIVE.PC.document(probe_plan("ambiguous", index)))

    revision_record = candidate_record("revision", revision=True, activated=1)
    controller.records.append(revision_record)
    controller.restore_plan(LIVE.PC.document(probe_plan("revision", 4)))
    first = controller.report()["typed_probe_budget"]

    replayed = LIVE.ProspectiveWorkspaceController(max_probes=5)
    replayed.records.append(ambiguous_record)
    for index in range(4):
        replayed.restore_plan(LIVE.PC.document(probe_plan("ambiguous", index)))
    replayed.records.append(revision_record)
    replayed.restore_plan(LIVE.PC.document(probe_plan("revision", 4)))

    assert replayed.report()["typed_probe_budget"] == first
    assert replayed.probe_decisions == controller.probe_decisions == 5


def test_constructor_rejects_any_untyped_budget() -> None:
    with pytest.raises(ValueError, match="exactly 5"):
        LIVE.ProspectiveWorkspaceController(max_probes=4)
