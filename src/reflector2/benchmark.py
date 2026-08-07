"""Deterministic four-frame mechanism and dormant-schema scaling benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any

from .perception import PerceptionBatch, perceive_grid
from .runtime import Limits, Runtime
from .store import SchemaGraph

FRAME_A = (
    (1, 1, 1, 0, 0),
    (1, 1, 1, 0, 0),
    (1, 1, 1, 0, 0),
    (1, 1, 1, 1, 1),
    (1, 1, 1, 1, 1),
)
FRAME_B = (
    (5, 5, 5, 0, 0),
    (5, 0, 5, 0, 0),
    (5, 5, 5, 0, 0),
    (5, 5, 5, 5, 5),
    (5, 5, 5, 5, 5),
)
FRAME_C = (
    (1, 1, 1, 1, 1),
    (1, 1, 1, 1, 1),
    (0, 0, 1, 1, 1),
    (0, 0, 1, 1, 1),
    (0, 0, 1, 1, 1),
)
FRAME_D = (
    (5, 5, 5, 5, 5),
    (5, 5, 5, 5, 5),
    (0, 0, 5, 0, 5),
    (0, 0, 5, 5, 5),
    (0, 0, 5, 5, 5),
)


@dataclass(frozen=True, slots=True)
class RunArtifacts:
    runtime: Runtime
    batches: tuple[PerceptionBatch, ...]
    workspaces: tuple[dict[str, Any], ...]
    transformation_id: int
    report: dict[str, Any]


def add_dormant_schemas(graph: SchemaGraph, count: int) -> None:
    for index in range(count):
        graph.add_schema(
            f"Dormant:{index}",
            [(f"DormantHead:{index}", ("?x",))],
            provenance="stress",
            candidate=False,
        )


def _workspace_snapshot(runtime: Runtime) -> dict[str, Any]:
    workspace = runtime.workspace
    assert workspace is not None
    return {
        "context": workspace.context,
        "active_ids": tuple(sorted(workspace.activation)),
        "binding_schema_ids": tuple(sorted({schema_id for schema_id, _binding in workspace.bindings})),
        "active_edges": tuple(sorted(workspace.active_edge_ids)),
    }


def run_benchmark(*, dormant_schemas: int = 0, limits: Limits | None = None) -> RunArtifacts:
    total_start = time.perf_counter()
    graph = SchemaGraph()
    runtime = Runtime(graph, limits)
    if dormant_schemas:
        add_dormant_schemas(graph, dormant_schemas)
    store_construction_time = time.perf_counter() - total_start
    cognition_start = time.perf_counter()
    batches = tuple(
        perceive_grid(graph.terms, frame, context, background=0)
        for frame, context in zip((FRAME_A, FRAME_B, FRAME_C, FRAME_D), ("A", "B", "C", "D"), strict=True)
    )

    snapshots = []
    runtime.observe(batches[0])
    snapshots.append(_workspace_snapshot(runtime))
    runtime.observe(batches[1])
    snapshots.append(_workspace_snapshot(runtime))
    first_mapping = runtime.learn_transition(batches[0], batches[1], "ACTION_1")
    runtime.observe(batches[2])
    snapshots.append(_workspace_snapshot(runtime))
    runtime.observe(batches[3])
    snapshots.append(_workspace_snapshot(runtime))
    second_mapping = runtime.learn_transition(batches[2], batches[3], "ACTION_1")
    if first_mapping != second_mapping:
        raise AssertionError("analogous transitions did not canonicalize to one morphism")

    report = runtime.report()
    report["total_time_s"] = time.perf_counter() - total_start
    report["store_construction_time_s"] = store_construction_time
    report["cognition_time_s"] = time.perf_counter() - cognition_start
    report["dormant_schemas"] = dormant_schemas
    report["transformation_hash"] = graph.canonical_hash[first_mapping]
    report["transformation_support"] = graph.support[first_mapping]
    report["transformation_contexts"] = sorted(graph.distinct_contexts[first_mapping])
    report["transformation_body"] = graph.source_atoms(first_mapping)
    report["cycles"] = snapshots
    return RunArtifacts(runtime, batches, tuple(snapshots), first_mapping, report)


def deterministic_projection(artifacts: RunArtifacts) -> dict[str, Any]:
    graph = artifacts.runtime.graph
    relevant_schema_ids = {
        schema_id
        for snapshot in artifacts.workspaces
        for schema_id in snapshot["active_ids"]
    } | {artifacts.transformation_id}
    return {
        "active_hashes": [
            [graph.canonical_hash[schema_id] for schema_id in snapshot["active_ids"]]
            for snapshot in artifacts.workspaces
        ],
        "binding_hashes": [
            [graph.canonical_hash[schema_id] for schema_id in snapshot["binding_schema_ids"]]
            for snapshot in artifacts.workspaces
        ],
        "transformation_hash": graph.canonical_hash[artifacts.transformation_id],
        "transformation_support": graph.support[artifacts.transformation_id],
        "transformation_contexts": sorted(graph.distinct_contexts[artifacts.transformation_id]),
        "decompositions": [
            {
                "owner": graph.canonical_hash[owner],
                "provenance": sorted(graph.decomposition_provenance[decomposition_id]),
                "occurrences": [
                    {
                        "schema": graph.canonical_hash[child],
                        "interface": interface,
                    }
                    for child, interface in graph.decomposition_occurrences(decomposition_id)
                ],
            }
            for decomposition_id, owner in enumerate(graph.decomposition_owner)
        ],
        "reusable_composites": [
            graph.canonical_hash[schema_id]
            for schema_id in artifacts.runtime.reusable_composite_candidates()
        ],
        "schema_states": {
            graph.canonical_hash[schema_id]: graph.schema_state[schema_id]
            for schema_id in sorted(relevant_schema_ids)
        },
        "metrics": artifacts.runtime.metrics.deterministic(),
    }


def run_stress(sizes: list[int], repetitions: int) -> list[dict[str, Any]]:
    output = []
    for size in sizes:
        runs = [run_benchmark(dormant_schemas=size) for _ in range(repetitions)]
        times = [run.report["cognition_time_s"] for run in runs]
        construction_times = [run.report["store_construction_time_s"] for run in runs]
        projections = [deterministic_projection(run) for run in runs]
        if any(item != projections[0] for item in projections[1:]):
            raise AssertionError(f"non-deterministic structural result at dormant size {size}")
        encoded_projection = json.dumps(projections[0], sort_keys=True, separators=(",", ":")).encode("utf-8")
        metrics = projections[0]["metrics"]
        output.append(
            {
                "dormant_schemas": size,
                "repetitions": repetitions,
                "time_s": {"min": min(times), "median": statistics.median(times), "max": max(times)},
                "store_construction_time_s": {
                    "min": min(construction_times),
                    "median": statistics.median(construction_times),
                    "max": max(construction_times),
                },
                "total_schemas": runs[0].report["total_schemas"],
                "term_bytes_estimate": runs[0].report["term_bytes_estimate"],
                "graph_bytes_estimate": runs[0].report["graph_bytes_estimate"],
                "structural_digest": hashlib.sha256(encoded_projection).hexdigest(),
                "operation_counts": {
                    "candidates_retrieved": metrics["candidates_retrieved"],
                    "candidates_verified": metrics["candidates_verified"],
                    "compositions_proposed": metrics["compositions_proposed"],
                    "compositions_retained": metrics["compositions_retained"],
                    "active_edge_visits": metrics["active_edge_visits"],
                    "work_items_processed": metrics["work_items_processed"],
                    "frontier_sizes": metrics["frontier_sizes"],
                    "peak_workspace": metrics["peak_workspace"],
                },
                "_projection": projections[0],
            }
        )
    if output:
        baseline = output[0]["_projection"]
        for row in output[1:]:
            if row["_projection"] != baseline:
                raise AssertionError("dormant schemas changed normal-loop structure or operation counts")
    for row in output:
        row.pop("_projection")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit the four-frame report as JSON")
    parser.add_argument("--stress", nargs="*", type=int, help="run dormant-schema sizes")
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    if args.stress is not None:
        value: Any = run_stress(args.stress or [1000, 10000, 100000], args.repetitions)
    else:
        value = run_benchmark().report
    print(json.dumps(value, indent=2, sort_keys=True, default=list))


if __name__ == "__main__":
    main()
