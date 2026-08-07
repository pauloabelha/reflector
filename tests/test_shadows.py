from __future__ import annotations

import pytest

from reflector2.perception import PerceptionBatch
from reflector2.runtime import REFUTED, REIFIED, SHADOW, Runtime
from reflector2.store import SchemaGraph


def _batch(
    graph: SchemaGraph, context: str, atoms: list[tuple[str, tuple[str, ...]]]
) -> PerceptionBatch:
    return PerceptionBatch(
        context,
        tuple(graph.terms.ground_atom(head, arguments) for head, arguments in atoms),
        (),
        (),
    )


def _ab_fixture() -> tuple[SchemaGraph, int, int, int]:
    graph = SchemaGraph()
    a_schema, _ = graph.add_schema(
        "A", [("A", ("?x",))], provenance="test", candidate=False
    )
    b_schema, _ = graph.add_schema(
        "B", [("B", ("?x",))], provenance="test", candidate=False
    )
    parent, _ = graph.add_dag_schema(
        "AB",
        ("?a", "?b"),
        ((a_schema, {0: "?a"}), (b_schema, {0: "?b"})),
        (("R", ("?a", "?b")),),
        provenance="test",
        candidate=False,
    )
    return graph, a_schema, b_schema, parent


def test_a_observation_creates_partial_binding_and_bounded_shadow_not_fact() -> None:
    graph, _a, _b, parent = _ab_fixture()
    runtime = Runtime(graph)
    observed = _batch(graph, "partial", [("A", ("a",))])

    workspace = runtime.observe(observed, compose=False)

    shadows = [shadow for shadow in runtime.shadows.values() if shadow.schema_id == parent]
    assert len(shadows) == 1
    shadow = shadows[0]
    partial = runtime.partial_bindings[shadow.partial_binding_id]
    assert shadow.status == SHADOW
    assert partial.schema_id == parent
    assert len(partial.bound_roles) == 1
    assert len(partial.unresolved_roles) == 1
    assert partial.unresolved_constraints == (0,)
    assert shadow.open_roles == partial.unresolved_roles
    assert all(binding.schema_id != parent for binding in workspace.bindings)
    assert observed.facts == (graph.terms.ground_atom("A", ("a",)),)


def test_b_later_compatible_evidence_reifies_once_and_keeps_canonical_binding() -> None:
    graph, _a, _b, parent = _ab_fixture()
    runtime = Runtime(graph)
    runtime.observe(_batch(graph, "partial", [("A", ("a",))]), compose=False)
    shadow = next(shadow for shadow in runtime.shadows.values() if shadow.schema_id == parent)

    workspace = runtime.observe(
        _batch(
            graph,
            "complete",
            [("A", ("a",)), ("B", ("b",)), ("R", ("a", "b"))],
        ),
        compose=False,
    )

    assert shadow.status == REIFIED
    assert any(binding.schema_id == parent for binding in workspace.bindings)
    assert graph.projection_support[parent] == 1
    assert len(graph.projection_contexts[parent]) == 1
    assert len(graph.projection_binding_signatures[parent]) == 1
    confirmation = next(event for event in runtime.trace if event["event"] == "ProjectionConfirmed")
    assert confirmation["generating_schema"] == graph.canonical_hash[parent]
    assert confirmation["grounded_binding"]
    assert runtime.reconcile_shadow(
        shadow.shadow_id,
        _batch(
            graph,
            "complete-again",
            [("A", ("a",)), ("B", ("b",)), ("R", ("a", "b"))],
        ),
    )
    assert graph.projection_support[parent] == 1


def test_c_refutation_requires_positive_applicable_contradiction_and_no_binding() -> None:
    graph, _a, _b, parent = _ab_fixture()
    runtime = Runtime(graph)
    workspace = runtime.observe(
        _batch(graph, "partial", [("A", ("a",))]), compose=False
    )
    shadow = next(shadow for shadow in runtime.shadows.values() if shadow.schema_id == parent)

    with pytest.raises(ValueError, match="positive contradictory evidence"):
        runtime.refute_shadow(
            shadow.shadow_id,
            incompatible_constraints={0},
            contradictory_evidence=(),
        )
    conflict = graph.terms.ground_atom("R", ("a", "incompatible"))
    runtime.refute_shadow(
        shadow.shadow_id,
        incompatible_constraints={0},
        contradictory_evidence=(conflict,),
        context="closed-applicable-carrier",
    )

    assert shadow.status == REFUTED
    assert shadow.contradictory_evidence == (conflict,)
    assert shadow.constraints[0].status == REFUTED
    assert runtime.partial_bindings[shadow.partial_binding_id].incompatible_constraints == (0,)
    assert graph.projection_failure[parent] == 1
    assert all(binding.schema_id != parent for binding in workspace.bindings)
    refutation = runtime.trace[-1]
    assert refutation["event"] == "ProjectionRefuted"
    assert refutation["contradictory_evidence"] == [conflict]


def test_d_recursive_schema_projects_only_immediate_child_frontier() -> None:
    graph = SchemaGraph()
    a, _ = graph.add_schema("A", [("A", ("?x",))], provenance="test")
    b1, _ = graph.add_schema("B1", [("B1", ("?x",))], provenance="test")
    b2, _ = graph.add_schema("B2", [("B2", ("?x",))], provenance="test")
    child_b, _ = graph.add_dag_schema(
        "ChildB",
        ("?x", "?y"),
        ((b1, {0: "?x"}), (b2, {0: "?y"})),
        (("BR", ("?x", "?y")),),
        provenance="test",
    )
    parent, _ = graph.add_dag_schema(
        "Parent",
        ("?a", "?x", "?y"),
        ((a, {0: "?a"}), (child_b, {0: "?x", 1: "?y"})),
        (("PR", ("?a", "?x")),),
        provenance="test",
    )
    runtime = Runtime(graph)

    runtime.observe(_batch(graph, "recursive", [("A", ("a",))]), compose=False)

    shadows = list(runtime.shadows.values())
    assert len(shadows) == 1
    assert shadows[0].schema_id == parent
    open_role = shadows[0].open_roles[0]
    assert shadows[0].child_roles[open_role].child_schema_id == child_b
    assert all(shadow.schema_id != child_b for shadow in shadows)


def test_e_same_schema_two_partial_bindings_make_two_shadows_not_definitions() -> None:
    graph, _a, _b, parent = _ab_fixture()
    runtime = Runtime(graph)
    schema_count = graph.schema_count

    runtime.observe(
        _batch(graph, "two-places", [("A", ("a1",)), ("A", ("a2",))]),
        compose=False,
    )

    shadows = [shadow for shadow in runtime.shadows.values() if shadow.schema_id == parent]
    assert len(shadows) == 2
    assert len({shadow.partial_binding_id for shadow in shadows}) == 2
    assert len({shadow.schema_id for shadow in shadows}) == 1
    assert graph.schema_count == schema_count


def test_f_shadows_share_one_immutable_schema_dag() -> None:
    graph, _a, _b, parent = _ab_fixture()
    runtime = Runtime(graph)
    decomposition_id = graph.decomposition_out_index[parent][0]
    occurrence_count = len(graph.occurrence_schema)
    runtime.observe(
        _batch(graph, "sharing", [("A", ("a1",)), ("A", ("a2",)), ("A", ("a3",))]),
        compose=False,
    )
    shadows = [shadow for shadow in runtime.shadows.values() if shadow.schema_id == parent]

    assert len(shadows) == 3
    assert {shadow.decomposition_id for shadow in shadows} == {decomposition_id}
    assert len(graph.occurrence_schema) == occurrence_count
    assert not any(
        hasattr(shadow, name)
        for shadow in shadows
        for name in ("graph", "dag", "schema_copy")
    )


@pytest.mark.parametrize("dormant_count", [1_000, 10_000, 100_000])
def test_g_dormant_store_size_does_not_change_projection_work(dormant_count: int) -> None:
    graph, _a, _b, parent = _ab_fixture()
    for index in range(dormant_count):
        graph.add_schema(
            f"Dormant:{index}",
            [(f"DormantHead:{index}", ("?x",))],
            provenance="stress",
        )
    runtime = Runtime(graph)

    runtime.observe(_batch(graph, "stress", [("A", ("a",))]), compose=False)

    shadows = [shadow for shadow in runtime.shadows.values() if shadow.schema_id == parent]
    assert len(shadows) == 1
    assert runtime.metrics.candidates_retrieved == 2
    assert runtime.metrics.candidates_verified == 2
    assert runtime.metrics.work_items_by_kind["PROJECT_SHADOW"] == 1


def test_h_shadow_never_enters_ground_facts_before_reification() -> None:
    graph, _a, _b, parent = _ab_fixture()
    runtime = Runtime(graph)
    observed = _batch(graph, "firewall", [("A", ("a",))])
    workspace = runtime.observe(observed, compose=False)

    assert runtime.metrics.shadow_projections == 1
    assert all(binding.schema_id != parent for binding in workspace.bindings)
    fact_values = {
        (graph.terms.value(head), tuple(graph.terms.value(value) for value in arguments))
        for head, arguments in observed.facts
    }
    assert fact_values == {("A", ("a",))}
    assert not {"B", "R"} & {head for head, _arguments in fact_values}
