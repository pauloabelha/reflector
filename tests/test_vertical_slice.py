from __future__ import annotations

from reflector2.benchmark import deterministic_projection, run_benchmark, run_stress
from reflector2.perception import PerceptionBatch
from reflector2.runtime import Limits, Runtime
from reflector2.store import SCHEMA_CANDIDATE, SCHEMA_ESTABLISHED, SCHEMA_PROMOTED


def _body_heads_and_arguments(artifacts, schema_id):
    return artifacts.runtime.graph.source_atoms(schema_id)


def test_parallel_activation_composition_and_analogy() -> None:
    run = run_benchmark()
    graph = run.runtime.graph
    terms = graph.terms

    assert graph.support[run.transformation_id] == 2
    assert graph.schema_state[run.transformation_id] == SCHEMA_PROMOTED
    assert len(graph.distinct_contexts[run.transformation_id]) == 2
    body = _body_heads_and_arguments(run, run.transformation_id)
    assert ("Preserve", ("Form",)) in body
    assert ("Change", ("Color",)) in body
    assert ("Change", ("EnclosureCount",)) in body
    assert any(head == "Less" for head, _args in body)

    frame_b = run.workspaces[1]
    active_b = set(frame_b["active_ids"])
    assert run.runtime.kernel_schema_ids["ConnectedDescriptor"] in active_b
    hole_schemas = [
        schema_id
        for schema_id in active_b
        if graph.depth[schema_id] > 0
        and any(head == "Enclosed" for head, _args in graph.source_atoms(schema_id))
        and any(head == "Inside" for head, _args in graph.source_atoms(schema_id))
    ]
    assert hole_schemas
    form_b = terms.value(run.batches[1].form_terms[0])
    composites = [
        schema_id
        for schema_id in active_b
        if graph.depth[schema_id] > 0
        and any(head == "Form" and form_b in args for head, args in graph.source_atoms(schema_id))
        and any(head == "Enclosed" for head, _args in graph.source_atoms(schema_id))
        and any(head == "Inside" for head, _args in graph.source_atoms(schema_id))
    ]
    assert composites
    for composite in composites:
        assert graph.schema_state[composite] == SCHEMA_CANDIDATE
        relation_part = terms.intern_symbol("part")
        parts = [graph.dst[edge] for edge in graph.out_index[composite] if graph.relation[edge] == relation_part]
        assert len(parts) >= 2
        assert set(parts) <= active_b
    assert len(active_b) <= run.runtime.limits.max_active_nodes
    assert all(
        graph.schema_state[schema_id] == SCHEMA_ESTABLISHED
        for schema_id in run.runtime.kernel_schema_ids.values()
    )


def test_form_reuse_across_value_change_and_independent_enclosure() -> None:
    run = run_benchmark()
    graph = run.runtime.graph
    form_a = graph.terms.value(run.batches[0].form_terms[0])
    form_b = graph.terms.value(run.batches[1].form_terms[0])
    form_c = graph.terms.value(run.batches[2].form_terms[0])
    form_d = graph.terms.value(run.batches[3].form_terms[0])
    assert form_a == form_b
    assert form_c == form_d
    assert form_a != form_c
    assert run.runtime.kernel_schema_ids["EnclosedDescriptor"] in run.workspaces[1]["active_ids"]
    assert run.runtime.kernel_schema_ids["EnclosedDescriptor"] in run.workspaces[3]["active_ids"]


def test_replay_is_structurally_deterministic() -> None:
    first = run_benchmark()
    second = run_benchmark()
    assert deterministic_projection(first) == deterministic_projection(second)


def test_prediction_is_prospective_and_falsification_is_retained() -> None:
    run = run_benchmark()
    runtime = run.runtime
    graph = runtime.graph
    color = graph.terms.intern_symbol("Color")
    impossible = (color, (run.batches[3].region_terms[0], graph.terms.intern_symbol(99)))
    prediction = runtime.predict(run.transformation_id, impossible, "counterexample")
    prediction_event_index = len(runtime.trace) - 1
    assert not runtime.resolve_prediction(prediction, run.batches[3])
    resolution_event_index = len(runtime.trace) - 1
    assert prediction_event_index < resolution_event_index
    assert graph.support[run.transformation_id] == 2
    assert graph.prediction_failure[run.transformation_id] == 1
    assert graph.contradiction[run.transformation_id] == 1


def test_dormant_schema_stress_preserves_active_operation_counts() -> None:
    rows = run_stress([1_000, 10_000, 100_000], 1)
    totals = [row["total_schemas"] for row in rows]
    assert totals[1] - totals[0] == 9_000
    assert totals[2] - totals[1] == 90_000
    assert len({row["structural_digest"] for row in rows}) == 1
    assert len({repr(row["operation_counts"]) for row in rows}) == 1
    assert rows[0]["graph_bytes_estimate"] < rows[1]["graph_bytes_estimate"] < rows[2]["graph_bytes_estimate"]


def test_fact_postings_and_transition_correspondences_have_hard_caps() -> None:
    runtime = Runtime(limits=Limits(max_facts_per_atom=2, max_transition_correspondences=1))
    terms = runtime.graph.terms
    color = terms.intern_symbol("Color")
    pattern = runtime.graph.patterns[runtime.kernel_schema_ids["ColorDescriptor"]]
    facts = [(terms.intern_symbol(f"region:{index}"), terms.intern_symbol(index)) for index in range(4)]
    bindings, truncated = runtime._verify(pattern, {(color, 2): facts})
    assert truncated
    assert len(bindings) == 2

    form = terms.intern_symbol("Form")
    before_facts = tuple(
        (form, (terms.intern_symbol(f"before:{index}"), terms.intern_symbol(f"form:{index}")))
        for index in range(3)
    )
    after_facts = tuple(
        (form, (terms.intern_symbol(f"after:{index}"), terms.intern_symbol(f"form:{index}")))
        for index in range(3)
    )
    before = PerceptionBatch("before", before_facts, (), ())
    after = PerceptionBatch("after", after_facts, (), ())
    assert len(runtime._correspond_regions(before, after)) == 1
    assert runtime.metrics.truncations == 1


def test_schema_decompositions_are_acyclic_occurrence_dags() -> None:
    run = run_benchmark()
    graph = run.runtime.graph
    adjacency: dict[int, set[int]] = {}
    assert graph.decomposition_owner
    assert any(len(ids) > 1 for ids in graph.decomposition_out_index.values())

    for decomposition_id, owner in enumerate(graph.decomposition_owner):
        assert graph.decomposition_provenance[decomposition_id]
        occurrences = graph.decomposition_occurrences(decomposition_id)
        assert occurrences
        for child, interface in occurrences:
            assert child != owner
            assert graph.depth[child] < graph.depth[owner]
            adjacency.setdefault(owner, set()).add(child)
            child_variables = {
                value
                for _head, args in graph.patterns[child]
                for tag, value in args
                if tag == "v"
            }
            owner_variables = {
                value
                for _head, args in graph.patterns[owner]
                for tag, value in args
                if tag == "v"
            }
            assert all(
                child_variable in child_variables and owner_variable in owner_variables
                for child_variable, owner_variable in interface
            )
        expanded = set()
        for child, interface in occurrences:
            variable_map = dict(interface)
            for head, args in graph.patterns[child]:
                expanded.add(
                    (
                        head,
                        tuple(
                            (tag, value if tag == "c" else variable_map[value])
                            for tag, value in args
                        ),
                    )
                )
        assert expanded == set(graph.patterns[owner])

    # Strictly decreasing depth is a topological certificate, checked again by
    # an explicit traversal so the test guards both data and interpretation.
    visiting: set[int] = set()
    visited: set[int] = set()

    def visit(schema_id: int) -> None:
        assert schema_id not in visiting
        if schema_id in visited:
            return
        visiting.add(schema_id)
        for child in adjacency.get(schema_id, ()):
            visit(child)
        visiting.remove(schema_id)
        visited.add(schema_id)

    for schema_id in adjacency:
        visit(schema_id)

    assert all(graph.edge_provenance)
