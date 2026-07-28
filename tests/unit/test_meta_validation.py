from reflector.meta_validation import (
    run_language_meta_validation,
    run_language_validation_seed,
)


def test_v8_language_validation_is_deterministic_and_causal() -> None:
    first = run_language_validation_seed(17)
    second = run_language_validation_seed(17)

    assert first == second
    assert first.evidence_hash_enabled == first.evidence_hash_ablated
    assert first.strong_oracle_accepts
    assert first.weak_oracle_rejects
    assert first.early_rejected_proposals >= 1
    assert first.operator_count == 1
    assert first.validated_mechanism_count >= 1
    assert first.mechanism_utility > 0
    assert first.ablation_proposal_count == 0
    assert first.ablation_operator_count == 0
    assert first.held_out_normalized
    assert first.ablation_held_out_unchanged
    assert first.provenance_valid
    assert first.held_out_leaks == 0
    assert first.structurally_idempotent


def test_v8_development_smoke_passes_every_frozen_criterion() -> None:
    report = run_language_meta_validation(3, 0)

    assert report["verdict"] == "supported"
    assert report["causal_thesis_supported"]
    assert all(report["criteria"].values())
    assert len(report["result_sha256"]) == 64
