from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "prospective_workspace_v118_tested", HERE / "experiment.py"
)
assert SPEC is not None and SPEC.loader is not None
EXP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXP
SPEC.loader.exec_module(EXP)

PC = EXP.LIVE_OWNER.PC


def binding(*, models=(), confirmations: int = 0):
    alternative = PC.GroundingAlternative(
        candidate_id="ga:generic",
        template_hash="template:generic",
        substitution=(),
        effect_pair=("left", "right"),
    )
    return PC.LiveBinding.build(
        schema_object_id="schema:generic",
        alternative=alternative,
        operator="Decrease",
        relative2=(-10, 0),
        action_models=models,
        confirmations=confirmations,
    )


def result(arm: str) -> dict:
    return {
        "arm_id": arm,
        "initial_digest": "same",
        "replay_verified": True,
        "counterfactual_exact": True,
        "qwen_context_valid": True,
        "qwen_transport_successful": True,
        "qwen_valid_compilations": 0 if arm == "r2_only" else 5,
        "qwen_calls": 0 if arm == "r2_only" else 5,
        "support_authority_violations": 0,
        "actions": 64,
        "first_level_completed": False,
        "counterfactual_favorable_count": 0,
        "groundings": [],
        "prospective_chain": {},
        "graph_metrics": {"object_kinds": {}},
    }


def test_unique_unknown_binding_selects_unknown_calibration_without_claiming_outcome() -> None:
    plan = PC.ProspectiveController((binding(),)).plan(
        (2, 1),
        observation_digest="frame:unknown",
        basis_revision=7,
        action_uses={1: 3, 2: 0},
    )
    assert plan.mode == "probe"
    assert plan.probe_basis == EXP.CALIBRATION.CALIBRATION_PROBE_BASIS
    assert plan.action_id == plan.fallback_action_id == 2
    assert len(plan.selected_prediction_ids) == 1
    selected = next(
        item for item in plan.predictions if item.prediction_id in plan.selected_prediction_ids
    )
    assert selected.modeled is False
    assert selected.predicted_delta is None
    assert selected.predicted_residual is None


def test_unknown_calibration_adjudication_is_unresolved_not_support() -> None:
    live = binding()
    plan = PC.ProspectiveController((live,)).plan(
        (1,), observation_digest="frame:calibration", basis_revision=8
    )
    adjudication = PC.adjudicate(
        plan,
        action_id=1,
        observed={live.binding_id: PC.ObservedConsequence(direct=True, delta=(0, 0), residual=10)},
    )
    assert adjudication.counts == {"supports": 0, "refutes": 0, "unresolved": 1}
    assert adjudication.judgments[0].reason == "no-prospective-model"
    assert adjudication.judgments[0].observed_delta == (0, 0)


def test_invariant_models_exhaust_to_fallback_but_improving_model_gets_confirmation() -> None:
    invariant = tuple(PC.ActionModel(action, (0, 0), 1) for action in (1, 2))
    exhausted = PC.ProspectiveController((binding(models=invariant),)).plan(
        (1, 2), observation_digest="frame:invariant", basis_revision=9
    )
    assert exhausted.mode == "fallback"
    assert exhausted.probe_basis == "calibrated-no-operator-improving-action"
    assert exhausted.selected_prediction_ids == ()

    improving = PC.ProspectiveController(
        (binding(models=(PC.ActionModel(1, (2, 0), 1),)),)
    ).plan((1, 2), observation_digest="frame:improving", basis_revision=10)
    assert improving.mode == "probe"
    assert improving.probe_basis == "single-binding-confirmation"
    assert improving.action_id == 1


def test_direct_zero_calibration_creates_model_without_confirmation_or_support() -> None:
    live = binding()
    plan = PC.ProspectiveController((live,)).plan(
        (1,), observation_digest="frame:zero", basis_revision=11
    )
    controller = EXP.BASE.LC.ProspectiveWorkspaceController(max_probes=5)
    pair_binding = SimpleNamespace(action_deltas={})
    record = SimpleNamespace(
        pair_binding=pair_binding,
        control_eligible=False,
        prospective_confirmations=0,
        prospective_refutations=0,
    )
    controller.records = [record]
    controller.inner.bindings = [pair_binding]
    controller.inner.observe = lambda _action, _before, _after: {
        "bindings": [{"direct": True, "delta": [0, 0], "residual": 10}]
    }
    controller.last_plan = plan
    controller.last_plan_records = {live.binding_id: record}

    learned = controller.observe(1, (), ())

    assert pair_binding.action_deltas == {1: [(0, 0)]}
    assert record.prospective_confirmations == 0
    assert learned["prospective_adjudication"]["judgments"][0]["status"] == "unresolved"
    assert learned["calibration_sample"]["epistemic_support_delta"] == 0


def test_calibration_budget_is_typed_and_cannot_consume_ambiguity_or_revision() -> None:
    plan = PC.ProspectiveController((binding(),)).plan(
        (1,), observation_digest="frame:budget", basis_revision=12
    )
    controller = EXP.BASE.LC.ProspectiveWorkspaceController(max_probes=5)
    admitted = []
    for _index in range(EXP.CALIBRATION.MAX_CALIBRATION_PROBES + 1):
        controller.probe_decisions += 1
        selected, accepted = controller._admit_or_demote(plan)
        admitted.append((selected.mode, accepted))
    assert admitted[:-1] == [("probe", True)] * EXP.CALIBRATION.MAX_CALIBRATION_PROBES
    assert admitted[-1] == ("fallback", False)
    assert controller.ambiguous_probe_decisions == 0
    assert controller.revision_probe_decisions == 0
    report = controller.report()
    assert report["typed_probe_budget"]["calibration_used"] == 8
    assert report["probe_decisions"] == 8


def test_calibration_gate_requires_full_post_calibration_chain() -> None:
    control = result("r2_only")
    shared = result("shared_live_qwen")
    shared.update(
        {
            "groundings": [{"status": "bound", "effect_pair_count": 1}],
            "counterfactual_favorable_count": 1,
            "prospective_chain": {
                "evidence_citing_revision_derivations": 1,
                "confirmed_revision_bindings": 1,
                "changed_control_decisions": 1,
            },
            "graph_metrics": {
                "object_kinds": {"calibration_sample": 1, "structured_criticism": 1}
            },
        }
    )
    verdict = EXP.evaluate_calibration_gate((control, shared), {})
    assert verdict["verdict"] == "MECHANISM_PASS"
    assert all(verdict["gates"].values())

    shared["counterfactual_favorable_count"] = 0
    assert EXP.evaluate_calibration_gate((control, shared), {})["verdict"] == "FAIL"


def test_v118_changes_only_calibration_and_later_qwen_boundary() -> None:
    inherited = EXP.V117_MODULE.load_config()
    current = EXP.load_config()
    differing = {
        key for key in set(inherited) | set(current) if inherited.get(key) != current.get(key)
    }
    assert differing <= {
        "experiment",
        "protocol",
        "workspace_protocol",
        "qwen",
        "prospective_control",
        "binary_gate",
    }
    assert current["games"] == inherited["games"] == ["wa30"]
    assert current["action_budget"] == inherited["action_budget"] == 64
