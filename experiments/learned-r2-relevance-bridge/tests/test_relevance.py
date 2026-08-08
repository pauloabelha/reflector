from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import sys


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))

from relevance import (  # noqa: E402
    EvidenceRecord,
    RelevanceBridge,
    RelevanceConfig,
    RelevanceTrainer,
    TRANSFER_NAMES,
    evaluate_snapshot,
    match_snapshot,
    permute_consequence_pairing,
    permute_reward_labels,
    relevance_atoms,
    run_offline_controls,
    stable_hash,
    train_snapshot,
)


CHANGE = (("Change", ("Count",)),)
PRESERVE = (("Preserve", ("Count",)),)
COMPOSED = (("Change", ("Count",)), ("Preserve", ("Form",)))


def record(
    sequence: int,
    consequence,
    delta: float,
    *,
    context: str | None = None,
    trajectory: str = "trajectory-a",
    stratum: str = "matched-context",
    binding: str | None = None,
) -> EvidenceRecord:
    return EvidenceRecord(
        sequence=sequence,
        event_id=f"event-{sequence}",
        context_id=context or f"context-{sequence}",
        trajectory_id=trajectory,
        pairing_stratum=stratum,
        binding_key=binding or f"binding-{sequence}",
        consequence=consequence,
        progress_delta=delta,
        opaque_action_id=sequence % 3,
        source="test:already-observed",
    )


def promoted_snapshot():
    return train_snapshot(
        (
            record(1, CHANGE, 1, binding="seen-binding"),
            record(2, CHANGE, 1),
            record(3, PRESERVE, 0),
            record(4, PRESERVE, 0),
        )
    )


def test_relevance_schema_requires_observed_pair_and_distinct_contexts() -> None:
    trainer = RelevanceTrainer()
    trainer.observe(record(1, CHANGE, 1, context="same"))
    assert trainer.freeze().schemas == ()
    trainer.observe(record(2, CHANGE, 1, context="same"))
    assert trainer.freeze().schemas == ()
    trainer.observe(record(3, CHANGE, 1, context="different"))
    snapshot = trainer.freeze()
    assert len(snapshot.schemas) == 1
    assert snapshot.schemas[0].support == 3
    atoms = relevance_atoms(CHANGE, "positive")
    serialized = repr(atoms)
    assert "arc-action" not in serialized
    assert "game" not in serialized.lower()
    assert "level" not in serialized.lower()


def test_transfer_classes_are_exact_binding_same_schema_and_structural_subset() -> None:
    snapshot = promoted_snapshot()
    exact = match_snapshot(snapshot, CHANGE, "seen-binding")
    rebound = match_snapshot(snapshot, CHANGE, "new-binding")
    composed = match_snapshot(snapshot, COMPOSED, "new-binding")
    assert {item.transfer_class for item in exact if item.outcome == "positive"} == {1}
    assert {item.transfer_class for item in rebound if item.outcome == "positive"} == {2}
    assert {item.transfer_class for item in composed if item.outcome == "positive"} == {3}


def test_null_permutations_preserve_required_marginals_and_fields() -> None:
    records = (
        record(1, CHANGE, 1),
        record(2, PRESERVE, 0),
        record(3, CHANGE, 1),
        record(4, PRESERVE, 0),
    )
    reward, reward_report = permute_reward_labels(records, seed=11)
    pairing, pairing_report = permute_consequence_pairing(records, seed=11)
    assert sorted(item.progress_delta for item in reward) == sorted(
        item.progress_delta for item in records
    )
    assert [item.consequence for item in reward] == [item.consequence for item in records]
    assert [item.opaque_action_id for item in reward] == [
        item.opaque_action_id for item in records
    ]
    assert [item.progress_delta for item in pairing] == [
        item.progress_delta for item in records
    ]
    assert reward_report["labels_moved"] > 0
    assert pairing_report["consequences_moved"] > 0


def test_offline_real_bridge_beats_both_permutation_controls() -> None:
    learning = (
        record(1, CHANGE, 1),
        record(2, PRESERVE, 0),
        record(3, CHANGE, 1),
        record(4, PRESERVE, 0),
    )
    held_out = (
        record(10, CHANGE, 1, binding="held-a"),
        record(11, PRESERVE, 0, binding="held-b"),
        record(12, COMPOSED, 1, binding="held-c"),
    )
    result = run_offline_controls(learning, held_out, RelevanceConfig())
    real = result["evaluations"]["real"]
    null_a = result["evaluations"]["null_a"]
    null_b = result["evaluations"]["null_b"]
    assert real["prospective_positive_precision"] == 1.0
    assert real["categorical_accuracy"] == 1.0
    assert real["prospective_positive_precision"] > null_a["prospective_positive_precision"]
    assert real["prospective_positive_precision"] > null_b["prospective_positive_precision"]
    assert real["successful_transfer_classes"][TRANSFER_NAMES[3]] == 1


def test_bridge_gate_changes_action_and_reifies_or_retains_refutation() -> None:
    snapshot = train_snapshot(
        (
            record(1, CHANGE, 1, binding="train-a"),
            record(2, CHANGE, 1, binding="train-b"),
        )
    )
    explanation = SimpleNamespace(
        selected_action_id=1,
        rankings=(
            SimpleNamespace(action_id=1, score=0.2),
            SimpleNamespace(action_id=2, score=0.0),
        ),
        predictions=(
            SimpleNamespace(action_id=1, signature=PRESERVE),
            SimpleNamespace(action_id=2, signature=CHANGE),
        ),
    )
    bridge = RelevanceBridge(snapshot)
    decision = bridge.decide(
        explanation,
        transition_hashes={0: "transition-preserve", 1: "transition-change"},
        binding_keys={0: "held-preserve", 1: "held-change"},
    )
    assert decision.gate_passed
    assert decision.selected_action_id == 2
    assert decision.changed_from_explanation
    assert decision.commitments
    prospective = bridge.decision_trace(decision)
    assert prospective["prospective_progress_commitments"]

    resolution = bridge.observe_outcome(
        decision,
        observed_effects=CHANGE,
        progress_delta=1,
        report_group="held-out-group-a",
    )
    assert {item["status"] for item in resolution["resolutions"]} == {"REIFIED"}
    report = bridge.report()
    assert report["bridge_precision"] == 1.0
    assert report["reifications"] == len(decision.commitments)

    second = bridge.decide(
        explanation,
        transition_hashes={0: "transition-preserve", 1: "transition-change"},
        binding_keys={0: "held-preserve-2", 1: "held-change-2"},
    )
    bridge.observe_outcome(
        second,
        observed_effects=PRESERVE,
        # Progress alone cannot confirm the bridge when the prospectively
        # predicted consequence failed to occur.
        progress_delta=1,
        report_group="held-out-group-b",
    )
    assert bridge.report()["refutations"] == len(second.commitments)
    assert all(
        bridge.runtime.shadows[item.shadow_id].status == "REFUTED"
        for item in second.commitments
    )


def test_held_out_outcomes_do_not_change_frozen_snapshot() -> None:
    snapshot = promoted_snapshot()
    before = snapshot.to_dict()
    evaluation = evaluate_snapshot(snapshot, (record(10, CHANGE, -1),))
    assert snapshot.to_dict() == before
    match = evaluation["forecasts"][0]["matches"][0]
    schema = next(
        item
        for item in snapshot.schemas
        if item.schema_hash == match["relevance_schema_hash"]
    )
    assert "support_event_ids" not in match
    assert match["provenance"]["support_event_count"] == len(
        schema.support_event_ids
    )
    assert match["provenance"]["support_event_digest"] == stable_hash(
        list(schema.support_event_ids)
    )


def test_projection_budget_resets_for_each_relevance_decision() -> None:
    snapshot = train_snapshot(
        (
            record(1, CHANGE, 1, binding="train-a"),
            record(2, CHANGE, 1, binding="train-b"),
        )
    )
    explanation = SimpleNamespace(
        selected_action_id=1,
        rankings=(
            SimpleNamespace(action_id=1, score=0.2),
            SimpleNamespace(action_id=2, score=0.0),
        ),
        predictions=(
            SimpleNamespace(action_id=1, signature=PRESERVE),
            SimpleNamespace(action_id=2, signature=CHANGE),
        ),
    )
    bridge = RelevanceBridge(snapshot)
    for index in range(12):
        decision = bridge.decide(
            explanation,
            transition_hashes={0: "preserve", 1: "change"},
            binding_keys={0: f"preserve-{index}", 1: f"change-{index}"},
        )
        assert decision.gate_passed
        assert decision.commitments
        bridge.observe_outcome(
            decision,
            observed_effects=CHANGE,
            progress_delta=1,
            report_group=f"group-{index % 2}",
        )
