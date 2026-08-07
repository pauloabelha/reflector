from __future__ import annotations

from pathlib import Path

from reflector2.benchmark import run_benchmark
from reflector2.store import SchemaGraph


def test_hot_source_has_no_named_fixture_solver_or_old_runtime_dependency() -> None:
    source_root = Path(__file__).resolve().parents[1] / "src" / "reflector2"
    source = "\n".join(path.read_text(encoding="utf-8") for path in source_root.glob("*.py"))
    forbidden = (
        "def is_" + "L",
        "def is_" + "Z",
        "is_" + "perforated",
        "infer_" + "perforation",
        "import reflector_" + "old",
        "from reflector_" + "old",
        "import torch",
        "import tensorflow",
    )
    assert not any(token in source for token in forbidden)


def test_schema_graph_soa_columns_and_provenance_stay_aligned() -> None:
    run = run_benchmark()
    graph = run.runtime.graph
    schema_columns = (
        graph.body_offset,
        graph.body_count,
        graph.canonical_hash,
        graph.display_name,
        graph.patterns,
        graph.provenance,
        graph.depth,
        graph.schema_state,
        graph.support,
        graph.contradiction,
        graph.prediction_success,
        graph.prediction_failure,
        graph.projection_support,
        graph.projection_failure,
        graph.use_count,
        graph.last_used,
        graph.distinct_contexts,
        graph.support_contexts,
        graph.projection_contexts,
    )
    edge_columns = (
        graph.src,
        graph.relation,
        graph.dst,
        graph.weight,
        graph.edge_flags,
        graph.edge_provenance,
    )
    decomposition_columns = (
        graph.decomposition_owner,
        graph.decomposition_occurrence_offset,
        graph.decomposition_occurrence_count,
        graph.decomposition_provenance,
    )
    occurrence_columns = (
        graph.occurrence_schema,
        graph.occurrence_map_offset,
        graph.occurrence_map_count,
    )

    assert {len(column) for column in schema_columns} == {graph.schema_count}
    assert {len(column) for column in edge_columns} == {graph.edge_count}
    assert len({len(column) for column in decomposition_columns}) == 1
    assert len({len(column) for column in occurrence_columns}) == 1
    assert len(graph.occurrence_child_variable) == len(graph.occurrence_owner_variable)
    assert all(graph.provenance)
    assert all(graph.edge_provenance)
    assert all(graph.decomposition_provenance)


def test_alpha_canonicalization_survives_renaming_and_atom_order() -> None:
    graph = SchemaGraph()
    variants = (
        [("R", ("?a", "?b")), ("R", ("?b", "?c")), ("Q", ("?c", "?a"))],
        [("Q", ("?z", "?x")), ("R", ("?y", "?z")), ("R", ("?x", "?y"))],
        [("R", ("?n", "?p")), ("Q", ("?q", "?n")), ("R", ("?p", "?q"))],
    )
    ids = []
    for index, body in enumerate(variants):
        schema_id, created = graph.add_schema(
            f"Variant:{index}", body, provenance=f"source:{index}"
        )
        ids.append(schema_id)
        assert created is (index == 0)
    assert len(set(ids)) == 1
    assert graph.provenance[ids[0]] == {"source:0", "source:1", "source:2"}

    different, created = graph.add_schema(
        "Different",
        [("R", ("?a", "?b")), ("R", ("?a", "?c")), ("Q", ("?c", "?b"))],
        provenance="different",
    )
    assert created
    assert different != ids[0]
