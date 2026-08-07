from __future__ import annotations

import pytest

from reflector2.dsl import Compiler
from reflector2.perception import MAX_SAME_OUTLINE_PAIRS, perceive_grid
from reflector2.runtime import Runtime
from reflector2.store import (
    SCHEMA_CANDIDATE,
    SCHEMA_PROMOTED,
    SchemaGraph,
    TermStore,
    _canonicalize_source_atoms,
)


def test_alpha_equivalence_hash_conses_and_merges_teacher_provenance() -> None:
    graph = SchemaGraph()
    endogenous, created = graph.add_schema(
        "Native", [("Form", ("?object", "?shape")), ("Inside", ("?hole", "?object"))], provenance="endogenous"
    )
    assert created
    teacher, created = graph.add_schema(
        "TeacherName", [("Inside", ("?h", "?x")), ("Form", ("?x", "?f"))], provenance="teacher:qwen"
    )
    assert not created
    assert teacher == endogenous
    assert graph.provenance[endogenous] == {"endogenous", "teacher:qwen"}


def test_teacher_compiler_uses_same_graph_and_rejects_partial_mutation() -> None:
    graph = SchemaGraph()
    compiler = Compiler(graph)
    with pytest.raises(ValueError):
        compiler.compile(
            """
            (schema PerforatedCandidate (?x ?h)
              (Form ?x ?f)
              (Enclosed ?h)
              (Inside ?h ?x)
              :source teacher:qwen)
            """
        )
    # ?f must be declared: the whole submission is rejected before mutation.
    assert graph.schema_count == 0


def test_teacher_compiler_valid_submission_and_transactional_rejection() -> None:
    graph = SchemaGraph()
    compiler = Compiler(graph)
    result = compiler.compile(
        """
        (schema PerforatedCandidate (?x ?h ?f)
          (Form ?x ?f) (Enclosed ?h) (Inside ?h ?x)
          :source teacher:qwen)
        """
    )
    schema_id, created = result[0][1]
    assert created
    assert graph.provenance[schema_id] == {"teacher:qwen"}
    assert graph.schema_state[schema_id] == SCHEMA_CANDIDATE
    before = graph.schema_count
    with pytest.raises(ValueError):
        compiler.compile(
            """
            (schema Valid (?x) (Connected ?x) :source native)
            (schema Invalid (?x) (Inside ?x ?undeclared) :source native)
            """
        )
    assert graph.schema_count == before


def test_native_evidence_form_is_logged_and_teacher_cannot_install_evidence() -> None:
    graph = SchemaGraph()
    compiler = Compiler(graph)
    [(kind, payload)] = compiler.compile(
        "(schema Candidate (?x) (Connected ?x) :source teacher:qwen)"
    )
    assert kind == "schema"
    schema_id, _created = payload
    compiler.compile("(evidence Candidate support 1 :source environment :context trial-1)")
    assert graph.support[schema_id] == 1
    assert graph.evidence_log[-1]["source"] == "environment"
    with pytest.raises(ValueError):
        compiler.compile("(evidence Candidate support 1 :source teacher:qwen :context trial-2)")
    assert graph.support[schema_id] == 1


def test_perception_ids_do_not_alias_across_disconnected_regions() -> None:
    graph = SchemaGraph()
    batch = perceive_grid(graph.terms, ((1, 0, 2),), "multi", background=0)
    part_of = graph.terms.intern_symbol("PartOf")
    memberships = [args for head, args in batch.facts if head == part_of]

    assert len(batch.region_terms) == 2
    assert len(memberships) == 2
    assert len({cell for cell, _region in memberships}) == 2
    assert {region for _cell, region in memberships} == set(batch.region_terms)


def test_outline_pairs_are_generic_across_reflection_and_internal_contrast() -> None:
    # Three separated, color-agnostic foreground figures share one L outline:
    # two are uniform and one contains a contrasting internal cell. No ARC game
    # ID, palette value, or named shape enters the perception code.
    grid = (
        (0, 0, 0, 0, 0, 0, 0, 0),
        (0, 1, 1, 0, 0, 2, 2, 0),
        (0, 1, 0, 0, 0, 0, 2, 0),
        (0, 0, 0, 0, 0, 0, 0, 0),
        (0, 3, 3, 0, 0, 0, 0, 0),
        (0, 4, 0, 0, 0, 0, 0, 0),
    )
    terms = TermStore()
    batch = perceive_grid(terms, grid, "generic-symmetry", background=0)
    same_outline = terms.intern_symbol("SameOutline")
    same_interior = terms.intern_symbol("SameInteriorContrast")
    different_interior = terms.intern_symbol("DifferentInteriorContrast")

    assert len([args for head, args in batch.facts if head == same_outline]) == 3
    assert len([args for head, args in batch.facts if head == same_interior]) == 1
    assert len([args for head, args in batch.facts if head == different_interior]) == 2

    runtime = Runtime()
    workspace = runtime.observe(
        perceive_grid(runtime.graph.terms, grid, "generic-relational-closure", background=0)
    )
    pair_heads = {"SameOutline", "SameInteriorContrast", "DifferentInteriorContrast"}
    relational = [
        schema_id
        for schema_id in workspace.activation
        if runtime.graph.depth[schema_id] >= 2
        and pair_heads & {head for head, _arguments in runtime.graph.source_atoms(schema_id)}
    ]
    for contrast_relation, expected_uses in (("DifferentInteriorContrast", 2), ("SameInteriorContrast", 1)):
        matches = [
            schema_id
            for schema_id in relational
            if {"SameOutline", contrast_relation, "Kind"}
            <= {head for head, _arguments in runtime.graph.source_atoms(schema_id)}
            and runtime.graph.use_count[schema_id] == expected_uses
        ]
        assert matches
        assert any(
            sum(
                runtime.graph.depth[child] >= 1
                for decomposition_id in runtime.graph.decomposition_out_index[schema_id]
                for child, _interface in runtime.graph.decomposition_occurrences(decomposition_id)
            ) >= 2
            for schema_id in matches
        )


def test_same_outline_pair_generation_is_explicitly_bounded() -> None:
    grid = tuple(
        tuple(1 if x % 2 == 0 and y % 2 == 0 else 0 for x in range(40))
        for y in range(40)
    )
    terms = TermStore()
    batch = perceive_grid(terms, grid, "many-singletons", background=0)
    same_outline = terms.intern_symbol("SameOutline")

    assert len([args for head, args in batch.facts if head == same_outline]) == MAX_SAME_OUTLINE_PAIRS


def test_figure_pair_schemas_are_not_installed_without_a_pair() -> None:
    runtime = Runtime()
    batch = perceive_grid(runtime.graph.terms, ((0, 1, 0),), "one-figure", background=0)
    runtime.observe(batch)

    assert "SameOutlinePair" not in runtime.kernel_schema_ids
    assert "FigureDescriptor" not in runtime.kernel_schema_ids


def test_dsl_resource_failures_are_preflighted_transactionally() -> None:
    graph = SchemaGraph()
    compiler = Compiler(graph)
    with pytest.raises(ValueError, match="at most 8 variables"):
        compiler.compile(
            """
            (schema First (?x) (Connected ?x) :source native)
            (schema TooMany (?a ?b ?c ?d ?e ?f ?g ?h ?i)
              (R ?a ?b ?c ?d ?e ?f ?g ?h) (S ?i)
              :source native)
            """
        )
    assert graph.schema_count == 0

    with pytest.raises(ValueError, match="unknown metadata"):
        compiler.compile("(schema Weighted (?x) (Connected ?x) :weight 0.5)")
    with pytest.raises(ValueError, match="finite"):
        compiler.compile("(fact (Measure sample NaN) :source sensor)")
    assert graph.schema_count == 0


def test_hash_hit_cannot_install_a_self_decomposition() -> None:
    graph = SchemaGraph()
    connected, _ = graph.add_schema(
        "Connected", [("Connected", ("?x",))], provenance="kernel"
    )
    colored, _ = graph.add_schema(
        "Colored", [("Color", ("?x", "?c"))], provenance="kernel"
    )
    body = [("Connected", ("?x",)), ("Color", ("?x", "?c"))]
    whole, created = graph.add_schema(
        "Whole",
        body,
        provenance="endogenous",
        decomposition=[
            (connected, {0: "?x"}),
            (colored, {0: "?x", 1: "?c"}),
        ],
    )
    assert created
    before = len(graph.decomposition_owner)
    _canonical, source_to_ordinal = _canonicalize_source_atoms(body)
    owner_interface = {ordinal: source for source, ordinal in source_to_ordinal.items()}
    reused, created = graph.add_schema(
        "Redundant",
        body,
        provenance="endogenous:redundant",
        decomposition=[(whole, owner_interface), (connected, {0: "?x"})],
    )
    assert reused == whole
    assert not created
    assert len(graph.decomposition_owner) == before


def test_invalid_decomposition_is_rejected_before_graph_mutation() -> None:
    graph = SchemaGraph()
    child, _ = graph.add_schema(
        "Connected", [("Connected", ("?x",))], provenance="kernel"
    )
    schema_count = graph.schema_count
    term_count = len(graph.terms.term_kind)
    with pytest.raises(ValueError, match="do not flatten"):
        graph.add_schema(
            "InvalidWhole",
            [("Connected", ("?x",)), ("Color", ("?x", "?c"))],
            provenance="teacher:qwen",
            decomposition=[(child, {0: "?x"})],
        )
    assert graph.schema_count == schema_count
    assert len(graph.terms.term_kind) == term_count
    assert not graph.decomposition_owner


def test_promotion_requires_support_from_distinct_contexts() -> None:
    graph = SchemaGraph()
    schema_id, _ = graph.add_schema(
        "Candidate", [("Connected", ("?x",))], provenance="endogenous"
    )
    graph.add_evidence(schema_id, "support", 2, "same", 1, source="experience")
    graph.add_evidence(schema_id, "contradiction", 1, "other", 2, source="experience")
    assert graph.schema_state[schema_id] == SCHEMA_CANDIDATE
    graph.add_evidence(schema_id, "support", 1, "third", 3, source="experience")
    assert graph.schema_state[schema_id] == SCHEMA_PROMOTED
