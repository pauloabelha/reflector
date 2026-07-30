from __future__ import annotations

import json

import pytest

from reflector.core import kline_memory
from reflector.core.kline_memory import (
    ActivationGrade,
    CueAtom,
    CueNamespace,
    KLineBounds,
    KLineDefinition,
    KLineEvidence,
    KLineMemory,
    KLineQuery,
    KLineSnapshot,
    StructuralCompatibility,
)


def _cue(
    namespace: CueNamespace,
    feature: str,
    value: str,
) -> CueAtom:
    return CueAtom(namespace, feature, value)


TRACK = _cue(CueNamespace.TOPOLOGY, "track-structure", "cyclic")
JUNCTION = _cue(CueNamespace.TOPOLOGY, "junction-count", "multiple")
TOKEN = _cue(CueNamespace.FORM, "token-role", "conserved")
SHIFT = _cue(CueNamespace.DYNAMICS, "relative-effect", "cyclic-shift")
ALIGN = _cue(CueNamespace.GOAL, "target-relation", "marker-aligned")
CONTROLLABLE = _cue(
    CueNamespace.CONTEXT,
    "controller-status",
    "evidenced",
)
BROKEN = _cue(CueNamespace.CONTEXT, "track-status", "disconnected")
TRANSPORT_GENERATOR = "segmented-cycle-transport"


def _memory(
    definitions: tuple[KLineDefinition, ...],
    *,
    bounds: KLineBounds = KLineBounds(),
    extra_registered_generators: tuple[str, ...] = (),
) -> KLineMemory:
    registered = tuple(
        sorted(
            {
                generator_id
                for definition in definitions
                for generator_id in definition.recalled_generator_ids
            }
            | set(extra_registered_generators)
        )
    )
    return KLineMemory.create(
        definitions,
        registered_generator_ids=registered,
        bounds=bounds,
    )


def _transport_definition(
    prior: str = "segmented-cycle-transport",
) -> KLineDefinition:
    return KLineDefinition.create(
        prior=prior,
        cues=(TRACK, JUNCTION, TOKEN, SHIFT, ALIGN),
        recalled_generator_ids=(TRANSPORT_GENERATOR,),
        preconditions=(CONTROLLABLE,),
        contradictions=(BROKEN,),
        minimum_cue_matches=2,
        minimum_namespace_matches=2,
    )


def test_default_retrieval_envelope_matches_the_documented_safety_contract() -> None:
    bounds = KLineBounds()

    assert bounds.max_candidate_pool == 64
    assert bounds.max_exact_candidates == 16
    assert bounds.max_results == 4
    assert bounds.max_structural_expansions == 2_048


def test_definition_snapshot_and_retrieval_are_byte_stable() -> None:
    transport = _transport_definition()
    lattice = KLineDefinition.create(
        prior="relative-lattice-effect",
        cues=(
            _cue(CueNamespace.TOPOLOGY, "node-layout", "regular-lattice"),
            _cue(CueNamespace.DYNAMICS, "relative-effect", "local-cycle"),
        ),
        recalled_generator_ids=("relative-effect-recall",),
    )
    forward = _memory((transport, lattice))
    reverse = _memory((lattice, transport))
    query = KLineQuery.create((CONTROLLABLE, TRACK, SHIFT, TOKEN))

    first = forward.retrieve(query)
    second = reverse.retrieve(KLineQuery.create(reversed(query.cues)))

    assert forward.snapshot.root == reverse.snapshot.root
    assert forward.snapshot.to_json() == reverse.snapshot.to_json()
    assert first.to_json().encode("ascii") == second.to_json().encode("ascii")
    assert json.loads(first.to_json())["snapshot_root"] == forward.snapshot.root


def test_definition_identity_excludes_external_evidence() -> None:
    definition = _transport_definition()
    before = definition.kline_id
    supported = KLineEvidence(
        kline_id=definition.kline_id,
        episode_digest="1" * 64,
        observation_digest="2" * 64,
        outcome="supported",
    )
    falsified = KLineEvidence(
        kline_id=definition.kline_id,
        episode_digest="3" * 64,
        observation_digest="4" * 64,
        outcome="falsified",
    )

    assert supported.evidence_id != falsified.evidence_id
    assert definition.kline_id == before
    assert _memory((definition,)).snapshot.root == (
        _memory((definition,)).snapshot.root
    )


def test_generator_dispositions_are_canonical_and_retrievable() -> None:
    cues = (TRACK, SHIFT)
    forward = KLineDefinition.create(
        prior="cycle-solving-disposition",
        cues=cues,
        recalled_generator_ids=(
            "relative-effect-learner",
            "bounded-symbolic-search",
        ),
    )
    reverse = KLineDefinition.create(
        prior="cycle-solving-disposition",
        cues=reversed(cues),
        recalled_generator_ids=(
            "bounded-symbolic-search",
            "relative-effect-learner",
        ),
    )

    assert forward.kline_id == reverse.kline_id
    result = _memory((forward,)).retrieve(
        KLineQuery.create(cues)
    )
    assert result.matches[0].recalled_generator_ids == (
        "bounded-symbolic-search",
        "relative-effect-learner",
    )


def test_generator_references_are_explicit_and_bounded() -> None:
    with pytest.raises(TypeError, match="recalled_generator_ids"):
        KLineDefinition.create(  # type: ignore[call-arg]
            prior="missing-generator-disposition",
            cues=(TRACK,),
        )

    two_generators = KLineDefinition.create(
        prior="two-generator-disposition",
        cues=(TRACK,),
        recalled_generator_ids=("first-recall", "second-recall"),
    )
    with pytest.raises(ValueError, match="per-definition generator"):
        KLineSnapshot.create(
            (two_generators,),
            bounds=KLineBounds(max_generator_ids_per_definition=1),
        )

    first = KLineDefinition.create(
        prior="first-generator-reference",
        cues=(TRACK,),
        recalled_generator_ids=("shared-recall",),
    )
    second = KLineDefinition.create(
        prior="second-generator-reference",
        cues=(TOKEN,),
        recalled_generator_ids=("shared-recall",),
    )
    with pytest.raises(ValueError, match="total generator-reference"):
        KLineSnapshot.create(
            (first, second),
            bounds=KLineBounds(max_total_generator_refs=1),
        )


def test_memory_requires_a_frozen_registered_generator_vocabulary() -> None:
    definition = _transport_definition()

    with pytest.raises(TypeError, match="registered_generator_ids"):
        KLineMemory.create((definition,))  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="unregistered"):
        KLineMemory.create(
            (definition,),
            registered_generator_ids=("different-symbolic-recall",),
        )

    memory = KLineMemory.create(
        (definition,),
        registered_generator_ids=(TRANSPORT_GENERATOR,),
    )
    assert memory.registered_generator_ids == (TRANSPORT_GENERATOR,)
    with pytest.raises(AttributeError):
        memory.registered_generator_ids = ("replacement-recall",)  # type: ignore[misc]


def test_partial_subset_beats_a_common_cue_distractor() -> None:
    target = _transport_definition()
    distractor = KLineDefinition.create(
        prior="generic-cycle-shape",
        cues=(
            TRACK,
            _cue(CueNamespace.FORM, "boundary-kind", "closed"),
            _cue(CueNamespace.FORM, "component-count", "multiple"),
        ),
        recalled_generator_ids=("shape-recall",),
    )
    memory = _memory((distractor, target))

    result = memory.retrieve(
        KLineQuery.create((CONTROLLABLE, TRACK, TOKEN, SHIFT))
    )

    assert result.matches
    assert result.matches[0].kline_id == target.kline_id
    assert result.matches[0].activation is ActivationGrade.RECALLED
    assert result.matches[0].matched_cues == tuple(
        sorted((TOKEN.key, TRACK.key, SHIFT.key))
    )
    assert result.matches[0].score > result.matches[1].score


def test_matches_across_multiple_relevance_namespaces() -> None:
    memory = _memory((_transport_definition(),))
    query = KLineQuery.create(
        (CONTROLLABLE, TRACK, JUNCTION, TOKEN, SHIFT, ALIGN)
    )

    recalled = memory.retrieve(query)

    def ground_current_structure(
        definition: KLineDefinition,
        current: KLineQuery,
        expansion_budget: int,
    ) -> StructuralCompatibility:
        assert definition.kline_id == _transport_definition().kline_id
        assert current == query
        assert expansion_budget == memory.bounds.max_structural_expansions
        return StructuralCompatibility(
            compatible=True,
            grounded=True,
            score=1_000_000,
            reason="exact-current-structure-grounded",
            expansions=7,
            grounding_proof_digest="a" * 64,
        )

    result = memory.retrieve(
        query,
        structural_matcher=ground_current_structure,
    )

    assert recalled.matches[0].activation is ActivationGrade.RECALLED
    assert len(result.matches) == 1
    match = result.matches[0]
    assert match.activation is ActivationGrade.GROUNDED
    assert match.recalled_generator_ids == (TRANSPORT_GENERATOR,)
    assert match.structural_reason == "exact-current-structure-grounded"
    assert match.structural_expansions == 7
    assert match.grounding_proof_digest == "a" * 64
    assert match.matched_namespaces == (
        "dynamics",
        "form",
        "goal",
        "topology",
    )
    assert "dynamics:relative-effect" in match.matched_features
    assert "goal:target-relation" in match.matched_features
    assert match.containment_score == 1_000_000
    assert match.namespace_score == 1_000_000


def test_missing_preconditions_and_contradictions_force_abstention() -> None:
    memory = _memory((_transport_definition(),))

    missing = memory.retrieve(KLineQuery.create((TRACK, TOKEN, SHIFT)))
    contradicted = memory.retrieve(
        KLineQuery.create((CONTROLLABLE, BROKEN, TRACK, TOKEN, SHIFT))
    )

    assert missing.matches == ()
    assert missing.diagnostics.missing_preconditions == 1
    assert missing.diagnostics.unknown_cues == ()
    assert contradicted.matches == ()
    assert contradicted.diagnostics.contradictions == 1
    assert contradicted.diagnostics.unknown_cues == ()

    constraint_only = memory.retrieve(KLineQuery.create((CONTROLLABLE,)))
    assert constraint_only.matches == ()
    assert constraint_only.diagnostics.known_query_atoms == 1
    assert constraint_only.diagnostics.unknown_cues == ()


def test_index_root_binds_bounds_schema_and_generator_registry() -> None:
    definition = _transport_definition()
    ordinary = _memory((definition,))
    tighter = _memory(
        (definition,),
        bounds=KLineBounds(max_posting_visits=32),
    )
    extended_registry = _memory(
        (definition,),
        extra_registered_generators=("unused-symbolic-recall",),
    )

    assert ordinary.snapshot.root == tighter.snapshot.root
    assert ordinary.snapshot.root == extended_registry.snapshot.root
    assert ordinary.index_root != tighter.index_root
    assert ordinary.index_root != extended_registry.index_root
    assert len(ordinary.index_root) == 64
    retrieval = ordinary.retrieve(KLineQuery.create((TRACK, TOKEN)))
    assert retrieval.index_root == ordinary.index_root
    assert json.loads(retrieval.to_json())["index_root"] == ordinary.index_root


def test_cross_postings_are_sampled_round_robin_under_a_tight_visit_cap() -> None:
    left = _cue(CueNamespace.FORM, "left-band", "present")
    right = _cue(CueNamespace.TOPOLOGY, "right-band", "present")
    left_definitions = tuple(
        KLineDefinition.create(
            prior=f"left-prior-{index}",
            cues=(left,),
            recalled_generator_ids=("cross-band-recall",),
        )
        for index in range(3)
    )
    right_definitions = tuple(
        KLineDefinition.create(
            prior=f"right-prior-{index}",
            cues=(right,),
            recalled_generator_ids=("cross-band-recall",),
        )
        for index in range(3)
    )
    bounds = KLineBounds(
        max_posting_visits=2,
        max_candidate_pool=4,
        max_exact_candidates=4,
        max_results=4,
    )
    memory = _memory(
        (*left_definitions, *right_definitions),
        bounds=bounds,
    )

    result = memory.retrieve(KLineQuery.create((left, right)))

    assert set(result.kline_ids) == {
        memory.posting(left)[0],
        memory.posting(right)[0],
    }
    assert result.diagnostics.posting_visits == 2
    assert result.diagnostics.posting_visit_cap_reached


def test_failed_cheap_preconditions_cannot_consume_the_exact_cap() -> None:
    common = _cue(CueNamespace.FORM, "shared-form", "present")
    rare = _cue(CueNamespace.DYNAMICS, "rare-dynamic", "present")
    absent_requirement = _cue(
        CueNamespace.CONTEXT,
        "required-context",
        "absent",
    )
    invalid_high_rank = KLineDefinition.create(
        prior="invalid-high-rank-prior",
        cues=(common, rare),
        recalled_generator_ids=("invalid-recall",),
        preconditions=(absent_requirement,),
    )
    valid_lower_rank = KLineDefinition.create(
        prior="valid-lower-rank-prior",
        cues=(common,),
        recalled_generator_ids=("valid-recall",),
    )
    bounds = KLineBounds(
        max_candidate_pool=2,
        max_exact_candidates=1,
        max_results=1,
    )
    memory = _memory(
        (invalid_high_rank, valid_lower_rank),
        bounds=bounds,
    )

    result = memory.retrieve(KLineQuery.create((common, rare)))

    assert result.kline_ids == (valid_lower_rank.kline_id,)
    assert result.diagnostics.missing_preconditions == 1
    assert result.diagnostics.exact_evaluated == 1
    assert not result.diagnostics.exact_cap_reached


def test_custom_exact_matcher_is_called_only_within_the_exact_cap() -> None:
    common = _cue(CueNamespace.FORM, "object-role", "repeated")
    definitions = tuple(
        KLineDefinition.create(
            prior=f"abstract-prior-{index}",
            cues=(
                common,
                _cue(
                    CueNamespace.TOPOLOGY,
                    "structure-family",
                    f"family-{index}",
                ),
            ),
            recalled_generator_ids=("generic-structure-recall",),
        )
        for index in range(12)
    )
    bounds = KLineBounds(
        max_posting_visits=12,
        max_candidate_pool=8,
        max_exact_candidates=3,
        max_results=2,
    )
    memory = _memory(definitions, bounds=bounds)
    calls: list[str] = []

    def reject_everything(
        definition: KLineDefinition,
        query: KLineQuery,
        expansion_budget: int,
    ) -> StructuralCompatibility:
        assert query.cues == (common,)
        assert expansion_budget >= 0
        calls.append(definition.kline_id)
        return StructuralCompatibility(
            compatible=False,
            grounded=False,
            score=0,
            reason="exact-structure-conflicted",
            expansions=1,
            grounding_proof_digest=None,
        )

    result = memory.retrieve(
        KLineQuery.create((common,)),
        structural_matcher=reject_everything,
    )

    assert len(memory.posting(common)) == len(definitions)
    assert result.matches == ()
    assert len(calls) == bounds.max_exact_candidates
    assert result.diagnostics.candidate_cap_reached
    assert result.diagnostics.exact_cap_reached
    assert result.diagnostics.structural_rejections == 3
    assert result.diagnostics.structural_expansions == 3
    assert result.diagnostics.posting_visits <= bounds.max_posting_visits


def test_structural_budget_and_grounding_proof_are_hard_gates() -> None:
    definition = _transport_definition()
    bounds = KLineBounds(max_structural_expansions=2)
    memory = _memory((definition,), bounds=bounds)
    query = KLineQuery.create((CONTROLLABLE, TRACK, TOKEN, SHIFT))
    observed_budgets: list[int] = []

    def over_budget(
        current_definition: KLineDefinition,
        current_query: KLineQuery,
        expansion_budget: int,
    ) -> StructuralCompatibility:
        assert current_definition == definition
        assert current_query == query
        observed_budgets.append(expansion_budget)
        return StructuralCompatibility(
            compatible=True,
            grounded=True,
            score=1_000_000,
            reason="reported-expansion-over-budget",
            expansions=expansion_budget + 1,
            grounding_proof_digest="b" * 64,
        )

    over_budget_result = memory.retrieve(
        query,
        structural_matcher=over_budget,
    )

    assert observed_budgets == [2]
    assert over_budget_result.matches == ()
    assert (
        over_budget_result.diagnostics.structural_budget_rejections == 1
    )
    assert over_budget_result.diagnostics.structural_expansions == 0

    def no_grounding_proof(
        _definition: KLineDefinition,
        _query: KLineQuery,
        expansion_budget: int,
    ) -> StructuralCompatibility:
        assert expansion_budget == 2
        return StructuralCompatibility(
            compatible=True,
            grounded=True,
            score=1_000_000,
            reason="missing-grounding-proof",
            expansions=2,
            grounding_proof_digest=None,
        )

    no_proof_result = memory.retrieve(
        query,
        structural_matcher=no_grounding_proof,
    )

    assert no_proof_result.matches == ()
    assert no_proof_result.diagnostics.structural_proof_rejections == 1
    assert no_proof_result.diagnostics.structural_expansions == 2


def test_structural_metadata_is_canonical_and_budget_decreases() -> None:
    first = KLineDefinition.create(
        prior="first-structural-prior",
        cues=(TRACK,),
        recalled_generator_ids=("structural-recall",),
    )
    second = KLineDefinition.create(
        prior="second-structural-prior",
        cues=(TRACK,),
        recalled_generator_ids=("structural-recall",),
    )
    memory = _memory(
        (first, second),
        bounds=KLineBounds(
            max_exact_candidates=2,
            max_results=2,
            max_structural_expansions=3,
        ),
    )
    budgets: list[int] = []

    def bounded_recall(
        _definition: KLineDefinition,
        _query: KLineQuery,
        expansion_budget: int,
    ) -> StructuralCompatibility:
        budgets.append(expansion_budget)
        return StructuralCompatibility(
            compatible=True,
            grounded=False,
            score=500_000,
            reason="bounded-structural-recall",
            expansions=1,
            grounding_proof_digest=None,
        )

    result = memory.retrieve(
        KLineQuery.create((TRACK,)),
        structural_matcher=bounded_recall,
    )

    assert budgets == [3, 2]
    assert result.diagnostics.structural_expansions == 2
    assert all(
        match.structural_reason == "bounded-structural-recall"
        and match.structural_expansions == 1
        and match.grounding_proof_digest is None
        for match in result.matches
    )
    with pytest.raises(ValueError, match="abstract symbol"):
        StructuralCompatibility(
            compatible=True,
            grounded=False,
            score=0,
            reason="not canonical",
            expansions=0,
            grounding_proof_digest=None,
        )


def test_inverse_frequency_component_is_bounded() -> None:
    query_cues = tuple(
        _cue(
            CueNamespace.DYNAMICS,
            f"rare-feature-{index}",
            "present",
        )
        for index in range(20)
    )
    target = KLineDefinition.create(
        prior="many-rare-cues",
        cues=query_cues,
        recalled_generator_ids=("rare-cue-recall",),
    )
    common = _cue(CueNamespace.FORM, "common-feature", "present")
    distractors = tuple(
        KLineDefinition.create(
            prior=f"common-distractor-{index}",
            cues=(common,),
            recalled_generator_ids=("common-recall",),
        )
        for index in range(20)
    )
    memory = _memory((target, *distractors))

    result = memory.retrieve(KLineQuery.create(query_cues))

    assert result.matches[0].kline_id == target.kline_id
    assert 0 <= result.matches[0].idf_score <= 1_000_000
    assert result.matches[0].idf_score <= (
        result.matches[0].containment_score
        + result.matches[0].namespace_score
        + result.matches[0].query_coverage_score
    )


def test_result_and_visit_caps_hold_under_one_common_posting() -> None:
    common = _cue(CueNamespace.FORM, "component-role", "salient")
    definitions = tuple(
        KLineDefinition.create(
            prior=f"shape-prior-{index}",
            cues=(common,),
            recalled_generator_ids=("shape-recall",),
        )
        for index in range(40)
    )
    bounds = KLineBounds(
        max_posting_visits=7,
        max_candidate_pool=7,
        max_exact_candidates=5,
        max_results=2,
    )
    memory = _memory(definitions, bounds=bounds)

    result = memory.retrieve(KLineQuery.create((common,)))

    assert len(result.matches) == 2
    assert result.diagnostics.posting_visits == 7
    assert not result.diagnostics.candidate_cap_reached
    assert result.diagnostics.posting_visit_cap_reached
    assert result.diagnostics.exact_cap_reached
    assert result.diagnostics.result_cap_reached
    assert result.kline_ids == tuple(sorted(result.kline_ids))


def test_snapshot_verifies_equal_digests_have_equal_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = KLineDefinition.create(
        prior="first-abstract-prior",
        cues=(TRACK,),
        recalled_generator_ids=("first-recall",),
    )
    second = KLineDefinition.create(
        prior="second-abstract-prior",
        cues=(TOKEN,),
        recalled_generator_ids=("second-recall",),
    )
    monkeypatch.setattr(kline_memory, "_content_digest", lambda _value: "0" * 64)

    with pytest.raises(ValueError, match="collision"):
        KLineSnapshot.create((first, second))


def test_snapshot_rejects_a_root_that_does_not_match_its_definitions() -> None:
    definition = _transport_definition()

    with pytest.raises(ValueError, match="does not match"):
        KLineSnapshot(
            definitions=(definition,),
            root="0" * 64,
        )


def test_retrieval_has_no_direct_action_or_executable_output() -> None:
    result = _memory((_transport_definition(),)).retrieve(
        KLineQuery.create(
            (CONTROLLABLE, TRACK, JUNCTION, TOKEN, SHIFT, ALIGN)
        )
    )
    encoded = result.to_dict()

    assert set(encoded) == {
        "diagnostics",
        "index_root",
        "matches",
        "snapshot_root",
        "version",
    }
    assert result.matches[0].activation in {
        ActivationGrade.RECALLED,
        ActivationGrade.GROUNDED,
    }
    assert not hasattr(result.matches[0], "action")
    assert not hasattr(result.matches[0], "code")
    assert result.matches[0].recalled_generator_ids == (
        TRANSPORT_GENERATOR,
    )
    assert "action_id" not in result.to_json()
    assert "executable" not in result.to_json()


def test_abstract_cues_are_equivariant_and_reject_concrete_identifiers() -> None:
    original = KLineDefinition.create(
        prior="relative-neighbor-effect",
        cues=(
            _cue(CueNamespace.RELATION, "neighbor-role", "preceding"),
            _cue(CueNamespace.DYNAMICS, "effect-frame", "anchor-relative"),
        ),
        recalled_generator_ids=("relative-neighbor-recall",),
    )
    translated_and_recolored = KLineDefinition.create(
        prior="relative-neighbor-effect",
        cues=(
            _cue(CueNamespace.RELATION, "neighbor-role", "preceding"),
            _cue(CueNamespace.DYNAMICS, "effect-frame", "anchor-relative"),
        ),
        recalled_generator_ids=("relative-neighbor-recall",),
    )

    assert translated_and_recolored.kline_id == original.kline_id
    assert _cue(
        CueNamespace.FORM,
        "palette-cardinality",
        "binary-color-cycle",
    ).key == "form:palette-cardinality:binary-color-cycle"
    assert _cue(
        CueNamespace.CONTEXT,
        "legal-action-role",
        "coordinate-bearing",
    ).key == "context:legal-action-role:coordinate-bearing"
    with pytest.raises(ValueError, match="concrete"):
        _cue(CueNamespace.FORM, "color-id", "seven")
    with pytest.raises(ValueError, match="concrete"):
        _cue(CueNamespace.CONTEXT, "action-id", "five")
    with pytest.raises(ValueError, match="concrete"):
        _cue(CueNamespace.RELATION, "absolute-position", "(3,4)")


def test_empty_and_entirely_unknown_queries_abstain_cleanly() -> None:
    memory = _memory((_transport_definition(),))
    unknown = _cue(CueNamespace.GOAL, "completion-form", "novel")

    empty = memory.retrieve(KLineQuery.create())
    absent = memory.retrieve(KLineQuery.create((unknown,)))

    assert empty.matches == ()
    assert empty.diagnostics.query_atoms == 0
    assert empty.diagnostics.unknown_cues == ()
    assert absent.matches == ()
    assert absent.diagnostics.query_atoms == 1
    assert absent.diagnostics.known_query_atoms == 0
    assert absent.diagnostics.unknown_cues == (unknown.key,)
