from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("prospective_control_under_test", HERE / "prospective_control.py")
assert SPEC is not None and SPEC.loader is not None
CONTROL = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CONTROL
SPEC.loader.exec_module(CONTROL)


def ambiguous_state() -> dict[str, Any]:
    return {
        "relations": [
            {"predicate": "SameArea", "arguments": ["a", "b"]},
            {"predicate": "SameArea", "arguments": ["a", "c"]},
        ]
    }


TEMPLATE = {
    "canonical_hash": "generic-template",
    "conditions": [{"predicate": "SameArea", "arguments": ["?x", "?y"]}],
    "effect_variables": ["?x", "?y"],
}


def alternatives() -> Any:
    return CONTROL.grounding_alternatives(TEMPLATE, ambiguous_state())


def binding(
    alternative: Any,
    *,
    relative2: tuple[int, int] = (-6, 0),
    models: tuple[Any, ...] = (),
    operator: str = "Decrease",
    confirmations: int = 0,
) -> Any:
    return CONTROL.LiveBinding.build(
        schema_object_id="schema:generic",
        alternative=alternative,
        operator=operator,
        relative2=relative2,
        action_models=models,
        confirmations=confirmations,
    )


def test_complete_grounding_alternatives_are_all_preserved_with_stable_ids() -> None:
    first = alternatives()
    second = alternatives()

    assert first.complete is True
    assert len(first.alternatives) == first.observed_grounding_count == 4
    assert first == second
    assert len({item.candidate_id for item in first.alternatives}) == 4
    assert {(item.effect_pair) for item in first.alternatives} == {
        ("a", "b"), ("b", "a"), ("a", "c"), ("c", "a")
    }
    live = [binding(item) for item in first.alternatives]
    assert len({item.binding_id for item in live}) == len(live)
    assert [item.binding_id for item in live] == [binding(item).binding_id for item in first.alternatives]

    truncated = CONTROL.grounding_alternatives(
        TEMPLATE, ambiguous_state(), enumeration_limit=2
    )
    assert truncated.complete is False
    assert len(truncated.alternatives) == 2


def test_prediction_matrix_contains_every_binding_action_and_marks_unknowns() -> None:
    candidates = alternatives().alternatives[:2]
    controller = CONTROL.ProspectiveController(
        (
            binding(candidates[0], models=(CONTROL.ActionModel(2, (2, 0), 3),)),
            binding(candidates[1], models=(CONTROL.ActionModel(1, (-2, 0), 2),)),
        )
    )

    predictions = controller.prediction_matrix(
        (2, 1), observation_digest="frame-x", basis_revision=17
    )

    assert len(predictions) == 4
    assert {(item.binding_id, item.action_id) for item in predictions} == {
        (binding_item.binding_id, action)
        for binding_item in controller.bindings
        for action in (1, 2)
    }
    assert sum(item.modeled for item in predictions) == 2
    assert all(item.basis_revision == 17 for item in predictions)
    assert all(item.predicted_delta is None and item.model_support == 0 for item in predictions if not item.modeled)


def test_plan_selects_deterministic_genuine_disagreement_probe() -> None:
    candidates = alternatives().alternatives[:2]
    # Each modeled outcome is non-improving under its binding's own operator,
    # leaving selection to their genuine disagreement.
    controller = CONTROL.ProspectiveController(
        (
            binding(
                candidates[0],
                operator="Increase",
                models=(CONTROL.ActionModel(1, (2, 0), 3),),
            ),
            binding(
                candidates[1],
                operator="Decrease",
                models=(CONTROL.ActionModel(1, (-2, 0), 3),),
            ),
        )
    )

    plan = controller.plan(
        (2, 1), observation_digest="frame-probe", basis_revision=8
    )

    assert plan.mode == "probe"
    assert plan.probe_basis == "alternative-disagreement"
    assert plan.action_id == 1
    assert plan.discrimination_pairs == 1
    assert len(plan.selected_prediction_ids) == 2
    assert plan == controller.plan((1, 2), observation_digest="frame-probe", basis_revision=8)


def test_plan_uses_fallback_when_no_action_genuinely_disagrees() -> None:
    candidates = alternatives().alternatives[:2]
    controller = CONTROL.ProspectiveController(
        tuple(binding(item) for item in candidates)
    )

    plan = controller.plan(
        (3, 1),
        observation_digest="frame-fallback",
        basis_revision=4,
        action_uses={1: 2, 3: 0},
    )

    assert plan.mode == "fallback"
    assert plan.action_id == plan.fallback_action_id == 3
    assert plan.discrimination_pairs == 0
    assert plan.selected_prediction_ids == ()


def test_unconfirmed_improvement_probes_once_but_confirmed_revision_can_control() -> None:
    candidate = alternatives().alternatives[0]
    model = (CONTROL.ActionModel(1, (2, 0), 4),)
    unknown = binding(candidate, models=(), confirmations=0)
    unconfirmed = binding(candidate, models=model, confirmations=0)

    unknown_plan = CONTROL.ProspectiveController((unknown,)).plan(
        (1, 2), observation_digest="frame-unknown", basis_revision=20
    )
    unconfirmed_plan = CONTROL.ProspectiveController((unconfirmed,)).plan(
        (1, 2), observation_digest="frame-unconfirmed", basis_revision=21
    )
    assert unknown_plan.mode == "fallback"
    assert unknown_plan.probe_basis is None
    assert unconfirmed_plan.mode == "probe"
    assert unconfirmed_plan.probe_basis == "single-binding-confirmation"
    assert unconfirmed_plan.action_id == 1
    prediction = next(
        item
        for item in unconfirmed_plan.predictions
        if item.prediction_id in unconfirmed_plan.selected_prediction_ids
    )
    judgment = CONTROL.adjudicate(
        unconfirmed_plan,
        action_id=1,
        observed={
            unconfirmed.binding_id: CONTROL.ObservedConsequence(
                direct=True,
                delta=prediction.predicted_delta,
                residual=prediction.predicted_residual,
            )
        },
    )
    assert judgment.counts == {"supports": 1, "refutes": 0, "unresolved": 0}

    (confirmed,) = CONTROL.revise_bindings((unconfirmed,), judgment)
    assert unconfirmed.binding_id == confirmed.binding_id
    assert confirmed.confirmations == 1
    confirmed_plan = CONTROL.ProspectiveController((confirmed,)).plan(
        (1, 2), observation_digest="frame-confirmed", basis_revision=22
    )
    assert confirmed_plan.mode == "control"
    assert confirmed_plan.probe_basis is None
    assert confirmed_plan.action_id == 1
    assert len(confirmed_plan.selected_prediction_ids) == 1


def test_direct_adjudication_supports_refutes_and_leaves_occlusion_unresolved() -> None:
    candidates = alternatives().alternatives[:3]
    controller = CONTROL.ProspectiveController(
        tuple(
            binding(item, models=(CONTROL.ActionModel(1, (2, 0), 2),))
            for item in candidates
        )
    )
    plan = controller.plan((1,), observation_digest="frame-evidence", basis_revision=11)
    by_binding = {item.binding_id: item for item in plan.predictions}
    binding_ids = sorted(by_binding)
    observed = {
        binding_ids[0]: CONTROL.ObservedConsequence(
            direct=True,
            delta=by_binding[binding_ids[0]].predicted_delta,
            residual=by_binding[binding_ids[0]].predicted_residual,
        ),
        binding_ids[1]: CONTROL.ObservedConsequence(direct=True, delta=(0, 0), residual=6),
        binding_ids[2]: CONTROL.ObservedConsequence(direct=False),
    }

    result = CONTROL.adjudicate(plan, action_id=1, observed=observed)

    assert result.counts == {"supports": 1, "refutes": 1, "unresolved": 1}
    assert {item.reason for item in result.judgments} == {
        "direct-outcome-matched",
        "direct-outcome-contradicted",
        "outcome-not-directly-observable",
    }
    assert all(item.prediction_id == by_binding[item.binding_id].prediction_id for item in result.judgments)
