from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SERVER_PATH = Path(__file__).resolve().parents[1] / "inspect" / "server.py"
SPEC = importlib.util.spec_from_file_location("reflector2_inspector_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
inspector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inspector)


def test_inspector_static_files_are_mounted_under_inspect() -> None:
    assert inspector._static_relative("/inspect") == "index.html"
    assert inspector._static_relative("/inspect/") == "index.html"
    assert inspector._static_relative("/inspect/app.js") == "app.js"
    assert inspector._static_relative("/app.js") is None


def test_inspector_projects_real_runtime_without_global_retrieval() -> None:
    grid = inspector._validate_grid([[0, 1, 0], [0, 1, 0], [0, 1, 0]])
    report = inspector.analyze_grid(grid, background=0)

    assert report["shape"] == [3, 3]
    assert report["grid"] == grid
    assert report["background"] == 0
    assert report["regions"]
    assert report["forms"]
    assert report["nodes"]
    assert report["metrics"]["active_schemas"] == len(report["nodes"])
    assert report["metrics"]["candidates_retrieved"] < report["metrics"]["total_schemas"]
    assert report["metrics"]["active_schemas"] <= report["limits"]["active_nodes"]
    assert report["metrics"]["active_edges"] <= report["limits"]["active_edges"]
    assert report["metrics"]["compositions_proposed"] <= report["limits"]["composition_proposals"]
    assert all(node["provenance"] and node["body"] for node in report["nodes"])
    assert all(
        {"interface", "definition_constraints", "binding_records", "shadows"} <= set(node)
        for node in report["nodes"]
    )
    assert all(
        {"projection_support", "projection_failure", "projection_context_count"} <= set(node)
        for node in report["nodes"]
    )
    assert {"partial_bindings", "active_shadows", "shadow_projections"} <= set(report["metrics"])
    assert all(
        set(node["region_ids"]) <= {region["id"] for region in report["regions"]}
        for node in report["nodes"]
    )
    pair_nodes = [node for node in report["nodes"] if node["name"] == "SameOutlinePair"]
    assert all(node["region_ids"] for node in pair_nodes)
    assert {node["name"] for node in report["nodes"]} >= {
        "RegionDescriptor", "ConnectedDescriptor", "ColorDescriptor", "FormDescriptor"
    }
    reusable = [node for node in report["nodes"] if node["reusable_candidate"]]
    assert len(reusable) == report["metrics"]["reusable_composite_candidates"]
    assert all(node["uses"] >= 2 and node["decompositions"] for node in reusable)
    assert all(link["provenance"] for link in report["links"])
    assert sum(report["truncation_reasons"].values()) == report["metrics"]["truncations"]


@pytest.mark.skipif(not inspector.RAW_RECORDING.exists(), reason="local public ARC recording is optional")
def test_inspector_exposes_reusable_dag_schemas_from_raw_arc_frame() -> None:
    fixture = inspector._load_fixture("raw-ar25")
    report = inspector.analyze_grid(fixture["grid"], background=fixture["background"])
    reusable = [node for node in report["nodes"] if node["reusable_candidate"]]

    assert reusable
    assert len(reusable) == report["metrics"]["reusable_composite_candidates"]
    assert all(node["uses"] >= 2 and node["decompositions"] for node in reusable)
    assert all(
        occurrence["interface"]
        for node in reusable
        for decomposition in node["decompositions"]
        for occurrence in decomposition["occurrences"]
    )


@pytest.mark.parametrize(
    "value, message",
    [
        ([], "non-empty"),
        ([[0], [0, 1]], "rectangular"),
        ([[True]], "integers"),
        ([[-1]], "0..65535"),
        ([[65536]], "0..65535"),
    ],
)
def test_inspector_rejects_invalid_grids(value: object, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        inspector._validate_grid(value)


def test_fixture_catalog_is_arc_only() -> None:
    catalog = inspector._fixture_catalog()
    fixture_ids = {entry["id"] for entry in catalog}
    assert not fixture_ids or all(fixture_id.startswith("raw-") for fixture_id in fixture_ids)


def test_ar25_label_assignments_are_external_to_runtime() -> None:
    assignment = inspector._load_assignment("ar25")
    assert assignment is not None
    assert assignment["kind"] == "schema-label-assignment"
    assert "not stored in" in assignment["scope"]


def test_llm_predicate_names_are_external_and_cover_runtime_heads() -> None:
    assignment = inspector._load_predicate_assignment()

    assert assignment["kind"] == "predicate-label-assignment"
    assert "not stored in" in assignment["scope"]
    assert "not" in assignment["scope"] and "supplied to Reflector-II" in assignment["scope"]
    assert {
        "Kind",
        "Connected",
        "Color",
        "Form",
        "Enclosed",
        "Inside",
        "EnclosureCount",
        "Value",
        "At",
        "PartOf",
        "OutlineForm",
        "Contains",
    } <= set(assignment["labels"])
    assert all(
        {"label", "reading", "rationale"} <= set(label)
        for label in assignment["labels"].values()
    )


@pytest.mark.skipif(
    not inspector.RAW_RECORDING_DIRECTORY.exists(), reason="local public ARC recordings are optional"
)
def test_fixture_catalog_includes_all_25_evaluated_games() -> None:
    raw_ids = {entry["id"] for entry in inspector._fixture_catalog() if entry["id"].startswith("raw-")}
    assert len(raw_ids) == 25
    assert {"raw-ar25", "raw-m0r0", "raw-vc33"} <= raw_ids
