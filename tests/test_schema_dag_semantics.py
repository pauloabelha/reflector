from __future__ import annotations

from reflector2.dsl import Compiler
from reflector2.perception import PerceptionBatch
from reflector2.runtime import PROJECTED, REFUTED, REIFIED, SHADOW, Binding, Runtime
from reflector2.store import SchemaGraph


def _fact_batch(graph: SchemaGraph, context: str, atoms: list[tuple[str, tuple[str, ...]]]) -> PerceptionBatch:
    return PerceptionBatch(
        context,
        tuple(graph.terms.ground_atom(head, arguments) for head, arguments in atoms),
        (),
        (),
    )


def _dag_fixture() -> tuple[SchemaGraph, int, int, int]:
    graph = SchemaGraph()
    segment, _ = graph.add_schema("Segment", [("Segment", ("?s",))], provenance="kernel", candidate=False)
    corner, _ = graph.add_schema("Corner", [("Corner", ("?c",))], provenance="kernel", candidate=False)
    hole, _ = graph.add_schema("Hole", [("Hole", ("?h",))], provenance="kernel", candidate=False)
    l_shape, created = graph.add_dag_schema(
        "LShape",
        ("?left", "?right", "?corner"),
        ((segment, {0: "?left"}), (segment, {0: "?right"}), (corner, {0: "?corner"})),
        (
            ("EndpointOf", ("?corner", "?left")),
            ("EndpointOf", ("?corner", "?right")),
            ("Orthogonal", ("?left", "?right")),
        ),
        provenance="test",
    )
    assert created
    perforated, created = graph.add_dag_schema(
        "PerforatedL",
        ("?left", "?right", "?corner", "?hole"),
        (
            (l_shape, {0: "?left", 1: "?right", 2: "?corner"}),
            (hole, {0: "?hole"}),
        ),
        (("Inside", ("?hole", "?corner")),),
        provenance="test",
    )
    assert created
    return graph, l_shape, perforated, hole


def test_one_reusable_schema_has_two_bindings_not_two_definitions() -> None:
    graph, l_shape, _perforated, _hole = _dag_fixture()
    runtime = Runtime(graph)
    workspace = runtime.observe(
        _fact_batch(
            graph,
            "two-locations",
            [
                ("Segment", ("a1",)), ("Segment", ("b1",)), ("Corner", ("c1",)),
                ("EndpointOf", ("c1", "a1")), ("EndpointOf", ("c1", "b1")), ("Orthogonal", ("a1", "b1")),
                ("Segment", ("a2",)), ("Segment", ("b2",)), ("Corner", ("c2",)),
                ("EndpointOf", ("c2", "a2")), ("EndpointOf", ("c2", "b2")), ("Orthogonal", ("a2", "b2")),
            ],
        ),
        compose=False,
    )
    bindings = [binding for binding in workspace.bindings if binding.schema_id == l_shape]
    assert len(bindings) == 2
    assert len({binding.schema_id for binding in bindings}) == 1
    assert all(binding.carrier == "two-locations" for binding in bindings)


def test_recursive_schema_dag_references_shared_child_identity() -> None:
    graph, l_shape, perforated, hole = _dag_fixture()
    same, created = graph.add_dag_schema(
        "AnotherNameForPerforatedL",
        ("?a", "?b", "?c", "?h"),
        ((l_shape, {0: "?a", 1: "?b", 2: "?c"}), (hole, {0: "?h"})),
        (("Inside", ("?h", "?c")),),
        provenance="same-structure",
    )
    assert same == perforated
    assert not created
    occurrences = graph.decomposition_occurrences(graph.decomposition_out_index[perforated][0])
    assert {child for child, _interface in occurrences} == {l_shape, hole}
    constraints = graph.definition_constraint_atoms(perforated)
    assert len(constraints) == 1 and constraints[0][0] == "Inside"
    assert graph.depth[perforated] == graph.depth[l_shape] + 1


def test_dsl_constructs_a_schema_dag_with_explicit_child_roles_and_relations() -> None:
    graph = SchemaGraph()
    left, _ = graph.add_schema("Left", [("Left", ("?x",))], provenance="kernel")
    right, _ = graph.add_schema("Right", [("Right", ("?x",))], provenance="kernel")
    compiler = Compiler(graph)
    [(kind, (whole, created))] = compiler.compile(
        """
        (schema Joined (?a ?b)
          (child Left ?a)
          (child Right ?b)
          (relation (Touches ?a ?b))
          :source native)
        """
    )
    assert kind == "schema" and created
    assert {child for child, _interface in graph.decomposition_occurrences(graph.decomposition_out_index[whole][0])} == {left, right}
    assert graph.definition_constraint_atoms(whole) == (("Touches", ("?v0", "?v1")),)


def test_partial_binding_projects_shadow_then_reifies_or_refutes_without_facts() -> None:
    graph = SchemaGraph()
    a_schema, _ = graph.add_schema("A", [("A", ("?x",))], provenance="kernel")
    b_schema, _ = graph.add_schema("B", [("B", ("?x",))], provenance="kernel")
    parent, _ = graph.add_dag_schema(
        "AB",
        ("?a", "?b"),
        ((a_schema, {0: "?a"}), (b_schema, {0: "?b"})),
        (("R", ("?a", "?b")),),
        provenance="test",
    )
    runtime = Runtime(graph)
    a_term = graph.terms.intern_symbol("a")
    occurrences = graph.decomposition_occurrences(graph.decomposition_out_index[parent][0])
    a_role = next(index for index, (child, _interface) in enumerate(occurrences) if child == a_schema)
    b_role = next(index for index, (child, _interface) in enumerate(occurrences) if child == b_schema)
    shadow = runtime.project_shadow(
        parent,
        {},
        child_bindings={a_role: Binding(a_schema, ((0, a_term),), "ctx-partial")},
        carrier="ctx-partial",
    )
    assert shadow.status == SHADOW
    assert shadow.open_roles and shadow.open_constraints
    assert shadow.child_roles[a_role].status == REIFIED
    assert shadow.child_roles[b_role].status == SHADOW
    assert shadow.constraints[0].status == PROJECTED
    assert runtime.metrics.shadow_projections == 1
    assert runtime.project_shadow(
        parent,
        {},
        child_bindings={a_role: Binding(a_schema, ((0, a_term),), "ctx-partial")},
        carrier="ctx-partial",
    ) is shadow
    assert runtime.metrics.parent_binding_memo_hits == 1
    assert runtime.reconcile_shadow(
        shadow.shadow_id,
        _fact_batch(graph, "ctx-reified", [("A", ("a",)), ("B", ("b",)), ("R", ("a", "b"))]),
    )
    assert shadow.status == REIFIED
    assert shadow.completed_roles == (b_role,)
    assert shadow.completed_constraints == (0,)
    assert graph.projection_support[parent] == 1
    pathway = (parent, shadow.decomposition_id, tuple(range(len(occurrences))), (0,))
    assert graph.projection_pathway_support[pathway] == 1
    assert graph.evidence_log[-1]["kind"] == "projection-success"

    refuted = runtime.project_shadow(
        parent,
        {},
        child_bindings={a_role: Binding(a_schema, ((0, a_term),), "ctx-refuted")},
        carrier="ctx-refuted",
    )
    runtime.refute_shadow(refuted.shadow_id)
    assert refuted.status == REFUTED
    assert graph.projection_failure[parent] == 1
    assert graph.evidence_log[-1]["kind"] == "projection-failure"


def test_shadow_projection_is_local_not_a_dormant_schema_scan() -> None:
    graph = SchemaGraph()
    active, _ = graph.add_schema("Active", [("A", ("?x",))], provenance="kernel")
    for index in range(200):
        graph.add_schema(f"Dormant:{index}", [(f"D{index}", ("?x",))], provenance="test")
    runtime = Runtime(graph)
    shadow = runtime.project_shadow(active, {0: graph.terms.intern_symbol("a")}, carrier="bounded")
    assert shadow.schema_id == active
    assert runtime.metrics.shadow_projections == 1
    assert runtime.metrics.candidates_retrieved == 0
    assert len(runtime.shadows) == 1
