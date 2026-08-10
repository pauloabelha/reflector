from __future__ import annotations

import pytest

from reflector2.perception import PerceptionBatch
from reflector2.runtime import Runtime
from reflector2.shared_cognition import (
    NativeSharedCognition,
    SemanticSchemaProposal,
    SharedCognitionError,
)


def _batch(runtime: Runtime) -> PerceptionBatch:
    terms = runtime.graph.terms
    a = terms.intern_symbol("entity:a")
    b = terms.intern_symbol("entity:b")
    c = terms.intern_symbol("entity:c")
    related = terms.intern_symbol("Related")
    distinguishes = terms.intern_symbol("Distinguishes")
    return PerceptionBatch(
        context="synthetic:0",
        facts=(
            (related, (a, b)),
            (related, (a, c)),
            (distinguishes, (a, b)),
        ),
        form_terms=(),
        region_terms=(a, b, c),
        source="synthetic:test",
    )


def test_native_true_r2_causal_loop_revises_and_changes_control() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    batch = _batch(runtime)
    observation_id = cognition.observe(batch)

    initial = cognition.propose(
        SemanticSchemaProposal(
            name="InitialSemanticProposal",
            conditions=(("Related", ("?a", "?b")),),
            operator="Decrease",
            measure="RelationalResidual",
            effect_variables=(0, 1),
            basis_ids=(observation_id,),
        ),
        response_id="qwen:0",
    )
    assert initial.status == "ambiguous"
    assert len(initial.effect_pairs) == 2
    assert initial.criticism_id is not None
    criticism = cognition.epistemic.object(initial.criticism_id)
    diagnostics = criticism.payload["grounding_diagnostics"]
    rows = {
        row["predicate"]: row
        for row in diagnostics["predicate_rows"]
    }
    assert rows["Related"]["classification"] == "ambiguous"
    assert rows["Distinguishes"]["classification"] == "unique"
    assert rows["Distinguishes"]["unique_pair"] == ["entity:a", "entity:b"]

    probe = cognition.predict(
        binding_id=initial.binding_ids[0],
        intervention_ref="intervention:opaque-7",
        current_residual=10,
        predicted_delta=-2,
        basis_revision=cognition.epistemic.revision,
    )
    returned = cognition.adjudicate(
        probe,
        transition_id="transition:0",
        observed_delta=-2,
        direct=True,
    )
    assert returned.verdict == "supports"
    assert cognition.epistemic.support(probe.prediction_id) == 1
    evidence_criticism = cognition.epistemic.object(returned.criticism_id)
    assert evidence_criticism.payload["target"] == initial.hypothesis_id
    assert evidence_criticism.payload["derivation"] == initial.derivation_id
    assert returned.evidence_object_id in evidence_criticism.dependency_ids
    assert initial.hypothesis_id in evidence_criticism.dependency_ids

    revision = cognition.propose(
        SemanticSchemaProposal(
            name="EvidenceDrivenRevision",
            conditions=(
                ("Related", ("?a", "?b")),
                ("Distinguishes", ("?a", "?b")),
            ),
            operator="Decrease",
            measure="RelationalResidual",
            effect_variables=(0, 1),
            basis_ids=(returned.evidence_object_id,),
        ),
        response_id="qwen:1",
        revises_id=initial.hypothesis_id,
        criticism_id=initial.criticism_id,
    )
    assert revision.status == "bound"
    assert revision.effect_pairs == (("entity:a", "entity:b"),)
    assert revision.hypothesis_id != initial.hypothesis_id

    confirmation = cognition.predict(
        binding_id=revision.binding_ids[0],
        intervention_ref="intervention:opaque-7",
        current_residual=8,
        predicted_delta=-2,
        basis_revision=cognition.epistemic.revision,
    )
    confirmation_return = cognition.adjudicate(
        confirmation,
        transition_id="transition:1",
        observed_delta=-2,
        direct=True,
    )
    assert confirmation_return.verdict == "supports"

    decision = cognition.choose_confirmed_control(
        binding_id=revision.binding_ids[0],
        legal_interventions=("intervention:opaque-3", "intervention:opaque-7"),
        fallback_intervention="intervention:opaque-3",
        decision_basis="state:digest:1",
    )
    assert decision.changed
    assert decision.selected_intervention == "intervention:opaque-7"
    lineage = cognition.epistemic.dependency_closure((decision.decision_id,))
    assert revision.hypothesis_id in lineage
    assert confirmation.prediction_id in lineage

    qwen_frontier = cognition.epistemic.frontier(worker="qwen", budget=100_000)
    assert returned.criticism_id in qwen_frontier.object_ids
    assert returned.evidence_object_id in qwen_frontier.object_ids


def test_control_refuses_unrevised_or_unconfirmed_hypothesis() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    observation_id = cognition.observe(_batch(runtime))
    proposal = cognition.propose(
        SemanticSchemaProposal(
            name="UniqueButInitial",
            conditions=(("Distinguishes", ("?a", "?b")),),
            operator="Decrease",
            measure="RelationalResidual",
            effect_variables=(0, 1),
            basis_ids=(observation_id,),
        ),
        response_id="qwen:initial",
    )
    assert proposal.status == "bound"
    with pytest.raises(SharedCognitionError, match="initial semantic proposals"):
        cognition.choose_confirmed_control(
            binding_id=proposal.binding_ids[0],
            legal_interventions=("intervention:opaque-1",),
            fallback_intervention="intervention:opaque-1",
            decision_basis="state:0",
        )


def test_alpha_identical_revision_is_rejected_before_stable_identity_write() -> None:
    runtime = Runtime()
    cognition = NativeSharedCognition(runtime)
    observation_id = cognition.observe(_batch(runtime))
    proposal = SemanticSchemaProposal(
        name="Repeated",
        conditions=(("Related", ("?a", "?b")),),
        operator="Decrease",
        measure="RelationalResidual",
        effect_variables=(0, 1),
        basis_ids=(observation_id,),
    )
    initial = cognition.propose(proposal, response_id="qwen:first")
    assert initial.criticism_id is not None

    with pytest.raises(SharedCognitionError, match="alpha-identical revision"):
        cognition.propose(
            proposal,
            response_id="qwen:repeat",
            revises_id=initial.hypothesis_id,
            criticism_id=initial.criticism_id,
        )
