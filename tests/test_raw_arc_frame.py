from __future__ import annotations

from pathlib import Path

import pytest

from reflector2.raw_frame import load_first_grid, run_raw_frame
from reflector2.perception import perceive_grid
from reflector2.runtime import Runtime
from reflector2.store import TermStore


LOCAL_AR25_RECORDING = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/recordings/reflector-v14-graph-400/"
    "ar25.reflectoragent.3b673829-b481-46fb-9c8e-3af7bf0bb444.recording.jsonl"
)


def test_first_grid_uses_final_layer_of_boundary_packet(tmp_path: Path) -> None:
    recording = tmp_path / "layered.recording.jsonl"
    recording.write_text(
        '{"data":{"frame":[[[0,1],[1,0]],[[2,2],[2,0]]]}}\n',
        encoding="utf-8",
    )

    assert load_first_grid(recording) == ((2, 2), (2, 0))


@pytest.mark.skipif(not LOCAL_AR25_RECORDING.exists(), reason="local public ARC recording is optional")
def test_first_raw_public_arc_frame_stays_bounded() -> None:
    report = run_raw_frame(LOCAL_AR25_RECORDING)
    assert report["shape"] == [64, 64]
    assert report["facts"] > 0
    assert report["regions"] > 1
    assert report["candidates_retrieved"] == report["candidates_verified"]
    assert report["candidates_retrieved"] < report["total_schemas"]
    assert report["active_schemas"] <= 256
    assert report["active_edges"] <= 1024
    assert report["compositions_proposed"] <= report["limits"]["composition_proposals"]
    assert report["truncation_events"] == report["truncations"]
    assert sum(report["truncation_reasons"].values()) == report["truncations"]
    assert report["reusable_composite_candidates"] >= 1
    assert report["reusable_composites"]
    assert all(
        candidate["depth"] > 0
        and candidate["uses"] >= 2
        and candidate["decompositions"] >= 1
        and len(candidate["body"]) >= 2
        for candidate in report["reusable_composites"]
    )


@pytest.mark.skipif(not LOCAL_AR25_RECORDING.exists(), reason="local public ARC recording is optional")
def test_ar25_color_agnostic_figures_preserve_all_three_l_pairs() -> None:
    terms = TermStore()
    batch = perceive_grid(terms, load_first_grid(LOCAL_AR25_RECORDING), "ar25", background=9)
    same_outline = terms.intern_symbol("SameOutline")
    different_interior = terms.intern_symbol("DifferentInteriorContrast")
    same_interior = terms.intern_symbol("SameInteriorContrast")

    # The three L figures form all C(3, 2) pairs: one solid/solid pair and
    # two solid/internally-contrasting pairs.
    assert len([args for head, args in batch.facts if head == same_outline]) >= 3
    assert len([args for head, args in batch.facts if head == different_interior]) >= 2
    assert len([args for head, args in batch.facts if head == same_interior]) >= 1


@pytest.mark.skipif(not LOCAL_AR25_RECORDING.exists(), reason="local public ARC recording is optional")
def test_ar25_oracle_discovers_pair_schemas_above_two_l_subschemas() -> None:
    runtime = Runtime()
    batch = perceive_grid(
        runtime.graph.terms, load_first_grid(LOCAL_AR25_RECORDING), "ar25-oracle", background=9
    )
    workspace = runtime.observe(batch)
    pair_heads = {"SameOutline", "SameInteriorContrast", "DifferentInteriorContrast"}
    pair_schemas = [
        schema_id
        for schema_id in workspace.activation
        if runtime.graph.depth[schema_id] >= 2
        and pair_heads & {head for head, _arguments in runtime.graph.source_atoms(schema_id)}
    ]

    # The native visual vocabulary now relates every bounded figure pair,
    # rather than emitting interior comparisons only inside an outline class.
    assert len(pair_schemas) >= 2
    uses = sorted(runtime.graph.use_count[schema_id] for schema_id in pair_schemas)
    assert uses[:2] == [1, 2]
    assert all(
        sum(
            runtime.graph.depth[child] == 1
            for decomposition_id in runtime.graph.decomposition_out_index[schema_id]
            for child, _interface in runtime.graph.decomposition_occurrences(decomposition_id)
        ) == 2
        for schema_id in pair_schemas
    )
