from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("schema_engine_test", HERE / "schema_engine.py")
E = importlib.util.module_from_spec(spec); sys.modules[spec.name] = E; spec.loader.exec_module(E)


def fact(predicate, arguments, types, evidence, context):
    return E.GroundFact(predicate, tuple(arguments), tuple(types), evidence, context)


def paired_schema():
    return E.Schema.create(
        (E.Port("a", "figure"), E.Port("b", "figure")),
        (E.Relation("SameOutline", ("a", "b")), E.Relation("DifferentFill", ("a", "b"))),
    )


def test_parallel_overlapping_bindings_and_partial_shadow():
    store = E.SchemaStore(); schema = store.add(paired_schema())
    fitter = E.ParallelSchemaFitter(store)
    bindings = fitter.update((
        fact("SameOutline", ("f1", "f2"), ("figure", "figure"), "ev:1", "frame:1"),
        fact("SameOutline", ("f3", "f4"), ("figure", "figure"), "ev:2", "frame:1"),
    ))
    assert len(bindings) == 2
    assert {binding.state for binding in bindings} == {E.BindingState.PARTIAL}
    shadows = tuple(fitter.shadows.values())
    assert len(shadows) == 2 and all(item.relation.predicate == "DifferentFill" for item in shadows)
    assert all(item.state == E.ShadowState.OPEN for item in shadows)
    fitter.settle((fact("DifferentFill", ("f1", "f2"), ("figure", "figure"), "ev:3", "frame:2"),))
    assert any(item.state == E.ShadowState.REIFIED for item in fitter.shadows.values())
    assert any(item.state == E.ShadowState.OPEN for item in fitter.shadows.values())


def test_schema_invention_promotes_repeated_relational_dag_and_binds_novel_case():
    inventor = E.SchemaInventor(minimum_contexts=2)
    first = (fact("SameOutline", ("u1", "u2"), ("figure", "figure"), "e1", "c1"), fact("DifferentFill", ("u1", "u2"), ("figure", "figure"), "e2", "c1"))
    second = (fact("SameOutline", ("v8", "v9"), ("figure", "figure"), "e3", "c2"), fact("DifferentFill", ("v8", "v9"), ("figure", "figure"), "e4", "c2"))
    assert inventor.observe(first).schema_id == inventor.observe(second).schema_id
    promoted, = inventor.promotable()
    store = E.SchemaStore(); store.add(promoted, promoted=True)
    novel = E.fit_schema(promoted, (fact("SameOutline", ("w3", "w4"), ("figure", "figure"), "e5", "c3"),), budget=8)
    assert novel[0].state == E.BindingState.PARTIAL
    shadow, = E.project_shadows(promoted, novel[0], limit=2)
    assert shadow.relation.predicate == "DifferentFill"


def test_temporal_schema_is_multi_directional_partial_binding_and_environment_settlement():
    transition = E.Schema.create(
        (E.Port("before", "figure"), E.Port("intervention", "token"), E.Port("after", "figure"), E.Port("delta", "delta")),
        (
            E.Relation("Corresponds", ("before", "after")),
            E.Relation("Applied", ("intervention", "before")),
            E.Relation("Translation", ("before", "after", "delta")),
        ), kind="transformation",
    )
    facts = (fact("Corresponds", ("x0", "x1"), ("figure", "figure"), "t1", "episode:1"), fact("Applied", ("k7", "x0"), ("token", "figure"), "t2", "episode:1"))
    binding, = E.fit_schema(transition, facts, budget=8)
    assert binding.assignment_map == {"after": "x1", "before": "x0", "intervention": "k7"}
    shadow, = E.project_shadows(transition, binding, limit=2)
    assert shadow.missing_ports == ("delta",)
    settled = E.settle_shadow(shadow, (fact("Translation", ("x0", "x1", "d:right"), ("figure", "figure", "delta"), "t3", "episode:2"),))
    assert settled.state == E.ShadowState.REIFIED


def test_dormant_irrelevant_store_does_not_perturb_indexed_frontier():
    store = E.SchemaStore(); target = store.add(paired_schema())
    for index in range(1000):
        store.add(E.Schema.create((E.Port("x", "other"),), (E.Relation(f"Dormant{index}", ("x",)),)))
    facts = (fact("SameOutline", ("f1", "f2"), ("figure", "figure"), "e1", "c1"),)
    retrieved = store.retrieve(facts, limit=8)
    assert retrieved == (target,)
    assert len(E.ParallelSchemaFitter(store).update(facts)) == 1


def test_partial_binding_extension_and_local_composition_preserve_decomposition():
    store = E.SchemaStore()
    outline = store.add(E.Schema.create((E.Port("a", "figure"), E.Port("b", "figure")), (E.Relation("SameOutline", ("a", "b")),)))
    fill = store.add(E.Schema.create((E.Port("x", "figure"), E.Port("y", "figure")), (E.Relation("DifferentFill", ("x", "y")),)))
    partial, = E.fit_schema(outline, (fact("SameOutline", ("f1", "f2"), ("figure", "figure"), "e1", "c1"),), budget=8)
    extension, = E.extend_binding(outline, partial, (fact("SameOutline", ("f1", "f2"), ("figure", "figure"), "e2", "c2"),), budget=8)
    other, = E.fit_schema(fill, (fact("DifferentFill", ("f1", "f3"), ("figure", "figure"), "e3", "c2"),), budget=8)
    composed = E.compose_compatible_bindings(store, extension, other)
    assert composed is not None and composed.components == tuple(sorted((outline.schema_id, fill.schema_id)))
    assert len(composed.constraints) == 2


def test_shadow_refutation_requires_explicit_contradictory_environment_fact():
    schema = paired_schema()
    binding, = E.fit_schema(schema, (fact("SameOutline", ("f1", "f2"), ("figure", "figure"), "e1", "c1"),), budget=8)
    shadow, = E.project_shadows(schema, binding, limit=1)
    assert E.settle_shadow(shadow, ()).state == E.ShadowState.OPEN
    refuted = E.settle_shadow(shadow, (fact("SameFill", ("f1", "f2"), ("figure", "figure"), "e2", "c2"),), contradictory_predicates=("SameFill",))
    assert refuted.state == E.ShadowState.REFUTED


def test_oriented_transformations_only_compose_at_the_shared_boundary():
    first = E.Transformation("t1", "before", "token", "middle")
    second = E.Transformation("t2", "middle", "token", "after")
    assert E.compose_transformations(first, second, bridge_port="middle") == ("t1", "t2", "before", "after")
    import pytest
    with pytest.raises(ValueError):
        E.compose_transformations(first, second, bridge_port="wrong")


def test_schema_binding_and_shadow_have_distinct_workspace_projections():
    schema = paired_schema()
    binding, = E.fit_schema(schema, (fact("SameOutline", ("f1", "f2"), ("figure", "figure"), "env:1", "frame:1"),), budget=8)
    shadow, = E.project_shadows(schema, binding, limit=1)
    schema_doc, binding_doc, shadow_doc = E.workspace_object(schema), E.workspace_object(binding), E.workspace_object(shadow)
    assert schema_doc["kind"] == "schema_definition"
    assert binding_doc["kind"] == "schema_binding" and "env:1" in binding_doc["dependency_ids"]
    assert shadow_doc["kind"] == "schema_shadow" and shadow_doc["payload"]["state"] == "open"


def test_schema0_bindings_recursively_become_inputs_to_higher_schemas():
    store, workspace = E.SchemaStore(), E.BindingWorkspace()
    schema0 = store.add(E.Schema.create((E.Port("support", "region-support"),), (), kind="schema0", output_type="region-structure"))
    pair = store.add(E.Schema.create(
        (E.Port("a", "region-structure"), E.Port("b", "region-structure")),
        (E.Relation("SameInvariant", ("a", "b")), E.Relation("Arranged", ("a", "b"))),
        output_type="pair-structure",
    ))
    higher = store.add(E.Schema.create((E.Port("pair", "pair-structure"),), (), output_type="configuration"))
    left = workspace.bind_schema0(schema0, E.GroundSupport("region:r1", "region-support", "env:r1", "frame:0"), port_name="support")
    right = workspace.bind_schema0(schema0, E.GroundSupport("region:r2", "region-support", "env:r2", "frame:0"), port_name="support")
    workspace.add_fact(fact("SameInvariant", (left.atom_id, right.atom_id), ("region-structure", "region-structure"), "env:same", "frame:0"))
    workspace.add_fact(fact("Arranged", (left.atom_id, right.atom_id), ("region-structure", "region-structure"), "env:arranged", "frame:0"))
    stats = E.RecursiveSchemaFitter(store, workspace, budget=E.FrontierBudget(max_depth_increment=3)).close((left.atom_id, right.atom_id))
    pair_atoms = [atom for atom in workspace.atoms.values() if atom.type == "pair-structure"]
    configuration_atoms = [atom for atom in workspace.atoms.values() if atom.type == "configuration"]
    assert stats.new_bindings >= 2
    assert len(pair_atoms) == 1 and len(configuration_atoms) == 1
    assert workspace.grounded(configuration_atoms[0].atom_id)
    assert set(configuration_atoms[0].grounding_evidence_ids) >= {"env:r1", "env:r2", "env:same", "env:arranged"}
    assert workspace.bindings[pair_atoms[0].source_id].schema_id == pair.schema_id
    assert workspace.bindings[configuration_atoms[0].source_id].schema_id == higher.schema_id


def test_recursive_fitting_preserves_parallel_ontologies_and_is_depth_bounded():
    store, workspace = E.SchemaStore(), E.BindingWorkspace()
    schema0 = store.add(E.Schema.create((E.Port("x", "raw"),), (), kind="schema0", output_type="seed"))
    store.add(E.Schema.create((E.Port("x", "seed"),), (), output_type="view-a"))
    store.add(E.Schema.create((E.Port("x", "seed"),), (), output_type="view-b"))
    # A recursive schema could otherwise build an unbounded tower.
    store.add(E.Schema.create((E.Port("x", "view-a"),), (), output_type="view-a"))
    seed = workspace.bind_schema0(schema0, E.GroundSupport("raw:1", "raw", "env:raw", "frame:0"), port_name="x")
    stats = E.RecursiveSchemaFitter(store, workspace, budget=E.FrontierBudget(max_depth_increment=3, new_bindings=20)).close((seed.atom_id,))
    assert {atom.type for atom in workspace.atoms.values()} >= {"seed", "view-a", "view-b"}
    assert stats.maximum_depth == 3
    assert len(workspace.bindings) <= 1 + 20


def test_equivalence_index_materializes_membership_not_quadratic_pairs():
    index = E.EquivalenceIndex()
    for number in range(100):
        index.add("outline", "sig:17", f"binding:{number}")
    assert len(index.members("outline", "sig:17")) == 100
    assert index.membership_count == 100


def test_recursive_partial_binding_survives_and_new_fact_delta_completes_it():
    store, workspace = E.SchemaStore(), E.BindingWorkspace()
    schema0 = store.add(E.Schema.create((E.Port("x", "raw"),), (), kind="schema0", output_type="item"))
    candidate = store.add(E.Schema.create(
        (E.Port("a", "item"), E.Port("b", "item")),
        (E.Relation("Related", ("a", "b")), E.Relation("Ordered", ("a", "b"))),
        output_type="arrangement",
    ))
    a = workspace.bind_schema0(schema0, E.GroundSupport("raw:a", "raw", "env:a", "f0"), port_name="x")
    b = workspace.bind_schema0(schema0, E.GroundSupport("raw:b", "raw", "env:b", "f0"), port_name="x")
    first_fact = fact("Related", (a.atom_id, b.atom_id), ("item", "item"), "env:related", "f0")
    workspace.add_fact(first_fact)
    first = E.RecursiveSchemaFitter(store, workspace).close((a.atom_id, b.atom_id))
    partials = [item for item in workspace.bindings.values() if item.schema_id == candidate.schema_id and item.state == E.BindingState.PARTIAL]
    assert first.new_partial_bindings >= 1 and partials and workspace.shadows
    second_fact = fact("Ordered", (a.atom_id, b.atom_id), ("item", "item"), "env:ordered", "f1")
    second = E.RecursiveSchemaFitter(store, workspace).close((), (second_fact,))
    assert second.new_bindings >= 1
    arrangements = [atom for atom in workspace.atoms.values() if atom.type == "arrangement"]
    assert len(arrangements) == 1 and set(arrangements[0].grounding_evidence_ids) >= {"env:a", "env:b", "env:related", "env:ordered"}


def test_alpha_equivalent_definitions_hash_cons_to_one_schema_id():
    left = E.Schema.create(
        (E.Port("a", "item"), E.Port("b", "item")),
        (E.Relation("R", ("a", "b")), E.Relation("S", ("b", "a"))),
        output_type="pair",
    )
    right = E.Schema.create(
        (E.Port("x", "item"), E.Port("y", "item")),
        (E.Relation("R", ("x", "y")), E.Relation("S", ("y", "x"))),
        output_type="pair",
    )
    assert left.schema_id == right.schema_id
    store = E.SchemaStore()
    assert store.add(left).schema_id == store.add(right).schema_id
    assert len(store.records) == 1


def test_depth_budget_is_per_cycle_not_an_architectural_level_ceiling():
    store, workspace = E.SchemaStore(), E.BindingWorkspace()
    schema0 = store.add(E.Schema.create((E.Port("x", "raw"),), (), kind="schema0", output_type="recursive"))
    store.add(E.Schema.create((E.Port("x", "recursive"),), (), output_type="recursive"))
    seed = workspace.bind_schema0(schema0, E.GroundSupport("raw:0", "raw", "env:0", "f0"), port_name="x")
    fitter = E.RecursiveSchemaFitter(store, workspace, budget=E.FrontierBudget(max_depth_increment=2, new_bindings=20))
    first = fitter.close((seed.atom_id,))
    assert first.maximum_depth == 2
    deepest = max(workspace.atoms.values(), key=lambda atom: atom.depth)
    second = fitter.close((deepest.atom_id,))
    assert second.maximum_depth == 4


def test_recursive_delta_retrieval_ignores_large_dormant_unrelated_store():
    store, workspace = E.SchemaStore(), E.BindingWorkspace()
    schema0 = store.add(E.Schema.create((E.Port("x", "raw"),), (), kind="schema0", output_type="active-type"))
    store.add(E.Schema.create((E.Port("x", "active-type"),), (), output_type="result"))
    for index in range(1000):
        store.add(E.Schema.create((E.Port("x", f"dormant-type-{index}"),), (), output_type="dormant-result"))
    seed = workspace.bind_schema0(schema0, E.GroundSupport("raw:1", "raw", "env:1", "f0"), port_name="x")
    stats = E.RecursiveSchemaFitter(store, workspace).close((seed.atom_id,))
    assert stats.schemas_considered == 1
    assert any(atom.type == "result" for atom in workspace.atoms.values())
