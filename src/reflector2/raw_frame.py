"""Read one recorded raw ARC frame and run the generic observation cycle."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from typing import Any

from .perception import perceive_grid
from .runtime import Runtime


def load_first_grid(recording: Path) -> tuple[tuple[int, ...], ...]:
    with recording.open(encoding="utf-8") as stream:
        first = json.loads(stream.readline())
    frame: Any = first["data"]["frame"]
    # ARC observations are layer packets. The final layer is the state opened
    # for the next action; single-layer packets use the same representation.
    if frame and frame[0] and isinstance(frame[0][0], list):
        frame = frame[-1]
    if not frame or not frame[0] or not isinstance(frame[0][0], int):
        raise ValueError("recording does not contain one rectangular scalar grid")
    width = len(frame[0])
    if any(not isinstance(row, list) or len(row) != width for row in frame):
        raise ValueError("recording does not contain one rectangular scalar grid")
    return tuple(tuple(int(value) for value in row) for row in frame)


def run_raw_frame(recording: Path) -> dict[str, Any]:
    grid = load_first_grid(recording)
    counts = Counter(value for row in grid for value in row)
    inferred_background = max(counts, key=lambda value: (counts[value], -value))
    runtime = Runtime()
    start = time.perf_counter()
    batch = perceive_grid(runtime.graph.terms, grid, "raw-frame:0")
    perception_time = time.perf_counter() - start
    start = time.perf_counter()
    workspace = runtime.observe(batch)
    runtime_time = time.perf_counter() - start
    reusable = runtime.reusable_composite_candidates()
    truncation_events = [event for event in runtime.trace if event["event"] == "truncation"]
    return {
        "recording": str(recording),
        "shape": [len(grid), len(grid[0])],
        "values": sorted(counts),
        "inferred_background": inferred_background,
        "facts": len(batch.facts),
        "regions": len(batch.region_terms),
        "distinct_forms": len(set(batch.form_terms)),
        "active_schemas": len(workspace.activation),
        "active_edges": len(workspace.active_edge_ids),
        "total_schemas": runtime.graph.schema_count,
        "candidates_retrieved": runtime.metrics.candidates_retrieved,
        "candidates_verified": runtime.metrics.candidates_verified,
        "compositions_proposed": runtime.metrics.compositions_proposed,
        "compositions_retained": runtime.metrics.compositions_retained,
        "limits": {
            "active_nodes": runtime.limits.max_active_nodes,
            "active_edges": runtime.limits.max_active_edges,
            "composition_proposals": runtime.limits.max_composition_proposals,
            "composition_rounds": runtime.limits.max_composition_rounds,
        },
        "reusable_composite_candidates": len(reusable),
        "reusable_composites": [
            {
                "hash": runtime.graph.canonical_hash[schema_id],
                "depth": runtime.graph.depth[schema_id],
                "uses": runtime.graph.use_count[schema_id],
                "body": runtime.graph.source_atoms(schema_id),
                "decompositions": len(runtime.graph.decomposition_out_index[schema_id]),
            }
            for schema_id in reusable
        ],
        "work_items_processed": runtime.metrics.work_items_processed,
        "frontier_sizes": runtime.metrics.frontier_sizes,
        "peak_workspace": runtime.metrics.peak_workspace,
        "truncations": runtime.metrics.truncations,
        "truncation_events": len(truncation_events),
        "truncation_reasons": dict(
            sorted(Counter(str(event["reason"]) for event in truncation_events).items())
        ),
        "perception_time_s": perception_time,
        "runtime_time_s": runtime_time,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording", type=Path)
    args = parser.parse_args()
    print(json.dumps(run_raw_frame(args.recording), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
