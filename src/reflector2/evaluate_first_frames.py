"""Evaluate the generic Reflector-II cycle on one first frame per game."""

from __future__ import annotations

import argparse
import copy
import os
import json
import statistics
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any, Iterable

from .perception import perceive_grid
from .raw_frame import load_first_grid, run_raw_frame
from .runtime import Runtime, Workspace
from .store import SchemaGraph


DEFAULT_RECORDING_GLOB = "*.recording.jsonl"
SUMMARY_METRICS = (
    "facts",
    "regions",
    "distinct_forms",
    "active_schemas",
    "active_edges",
    "candidates_retrieved",
    "compositions_proposed",
    "compositions_retained",
    "reusable_composite_candidates",
    "work_items_processed",
    "peak_workspace",
    "truncations",
    "perception_time_s",
    "runtime_time_s",
)
GENERIC_TYPE_CONSTANTS = frozenset({"Region", "Cell", "Figure"})


def game_id_from_recording(path: Path) -> str:
    """Return the stable game prefix from an ARC recording filename."""
    game_id = path.name.split(".", 1)[0]
    if not game_id:
        raise ValueError(f"cannot infer game id from {path.name!r}")
    return game_id


def discover_recordings(directory: Path) -> dict[str, Path]:
    """Discover exactly one deterministic recording per game in *directory*."""
    grouped: dict[str, list[Path]] = {}
    for path in sorted(directory.glob(DEFAULT_RECORDING_GLOB)):
        grouped.setdefault(game_id_from_recording(path), []).append(path)
    duplicates = {game: paths for game, paths in grouped.items() if len(paths) != 1}
    if duplicates:
        details = ", ".join(f"{game}={len(paths)}" for game, paths in sorted(duplicates.items()))
        raise ValueError(f"recording directory must contain one file per game; duplicates: {details}")
    return {game: paths[0] for game, paths in sorted(grouped.items())}


def _metric_summary(values: Iterable[int | float]) -> dict[str, int | float]:
    collected = list(values)
    if not collected:
        return {}
    return {
        "min": min(collected),
        "median": statistics.median(collected),
        "max": max(collected),
    }


def _is_useful_schema(candidate: dict[str, Any]) -> bool:
    """Check the minimum structural evidence for a reusable DAG schema."""
    return bool(
        candidate["depth"] > 0
        and candidate["uses"] >= 2
        and candidate["decompositions"] >= 1
        and len(candidate["body"]) >= 2
    )


def _is_richer_than_shape_type(candidate: dict[str, Any]) -> bool:
    """Separate attribute/relational chunks from the common Form+Kind chunk."""
    heads = {head for head, _arguments in candidate["body"]}
    return heads != {"Form", "Kind"}


def _evaluate_one(item: tuple[str, Path]) -> dict[str, Any]:
    """Pickle-safe independent per-game worker for process-pool evaluation."""
    game_id, recording = item
    try:
        raw = run_raw_frame(recording)
        candidates = raw["reusable_composites"]
        budget_pass = bool(
            raw["active_schemas"] <= raw["limits"]["active_nodes"]
            and raw["active_edges"] <= raw["limits"]["active_edges"]
            and raw["compositions_proposed"] <= raw["limits"]["composition_proposals"]
            and raw["candidates_retrieved"] <= 512
        )
        useful_schema_pass = bool(candidates) and all(
            _is_useful_schema(candidate) for candidate in candidates
        )
        richer_schema_candidates = sum(
            _is_richer_than_shape_type(candidate) for candidate in candidates
        )
        return {
            "game": game_id,
            **raw,
            "budget_pass": budget_pass,
            "useful_schema_pass": useful_schema_pass,
            "richer_schema_candidates": richer_schema_candidates,
            "richer_schema_pass": richer_schema_candidates > 0,
        }
    except Exception as error:  # Keep the corpus audit going and report every failure.
        return {
            "game": game_id,
            "recording": str(recording),
            "error": f"{type(error).__name__}: {error}",
            "budget_pass": False,
            "useful_schema_pass": False,
            "richer_schema_candidates": 0,
            "richer_schema_pass": False,
        }


def evaluate_recordings(
    directory: Path,
    *,
    expected_games: int | None = None,
    workers: int = 1,
) -> dict[str, Any]:
    """Evaluate the first raw frame of every uniquely represented game."""
    recordings = discover_recordings(directory)
    if expected_games is not None and len(recordings) != expected_games:
        raise ValueError(f"expected {expected_games} games, found {len(recordings)}")

    if workers < 0:
        raise ValueError("workers must be zero (automatic) or a positive integer")
    items = list(recordings.items())
    actual_workers = min(len(items), (os.cpu_count() or 1) if workers == 0 else workers)
    started = time.perf_counter()
    if actual_workers == 1:
        games = [_evaluate_one(item) for item in items]
    else:
        with ProcessPoolExecutor(max_workers=actual_workers) as executor:
            games = list(executor.map(_evaluate_one, items))

    successful = [game for game in games if "error" not in game]
    failed = [game for game in games if "error" in game]
    aggregate = {
        "games_discovered": len(games),
        "games_succeeded": len(successful),
        "games_failed": len(failed),
        "budget_passes": sum(bool(game["budget_pass"]) for game in games),
        "useful_schema_passes": sum(bool(game["useful_schema_pass"]) for game in games),
        "richer_schema_passes": sum(bool(game["richer_schema_pass"]) for game in games),
        "total_richer_schemas": sum(game["richer_schema_candidates"] for game in games),
        "games_with_reusable_schemas": sum(
            game.get("reusable_composite_candidates", 0) > 0 for game in games
        ),
        "total_reusable_schemas": sum(
            game.get("reusable_composite_candidates", 0) for game in games
        ),
        "shapes": dict(
            sorted(Counter("x".join(map(str, game["shape"])) for game in successful).items())
        ),
        "metrics": {
            metric: _metric_summary(game[metric] for game in successful)
            for metric in SUMMARY_METRICS
        },
        "elapsed_time_s": time.perf_counter() - started,
    }
    return {
        "protocol": {
            "input": "final rendered layer of the first data.frame packet only",
            "recording_directory": str(directory),
            "recording_glob": DEFAULT_RECORDING_GLOB,
            "selection": "exactly one recording per game id; lexicographic game order",
            "workers": actual_workers,
            "game_metadata_used": False,
            "useful_schema_criterion": (
                "at least one reusable composite; every reported reusable composite has "
                "depth > 0, uses >= 2, a decomposition DAG, and at least two body atoms"
            ),
            "richer_schema_criterion": (
                "a reusable composite whose predicate heads are not exactly Form+Kind; "
                "this identifies attribute/relational structure without claiming task relevance"
            ),
        },
        "aggregate": aggregate,
        "games": games,
    }


def _observe_grid(
    recording: Path,
    *,
    graph: SchemaGraph | None = None,
    context: str,
) -> tuple[Runtime, Workspace]:
    """Observe one recording, optionally continuing from a copied graph.

    The caller owns ``graph``.  Transfer experiments always pass a deep-copied
    source graph here, so target observations cannot mutate another cell's
    source store.
    """
    runtime = Runtime(graph=graph)
    grid = load_first_grid(recording)
    batch = perceive_grid(runtime.graph.terms, grid, context)
    return runtime, runtime.observe(batch)


def _non_kernel_hashes(runtime: Runtime, schema_ids: Iterable[int]) -> set[str]:
    """Return schema identities excluding the fixed sensory kernel."""
    kernel_ids = set(runtime.kernel_schema_ids.values())
    return {
        runtime.graph.canonical_hash[schema_id]
        for schema_id in schema_ids
        if schema_id not in kernel_ids
    }


def _has_grounded_descriptor(runtime: Runtime, schema_id: int) -> bool:
    """Whether a schema has a non-type constant rather than only variables.

    This separates a generic constructed row such as ``Form(?x, ?form) ∧
    Kind(?x, Region)`` from a source-grounded row such as ``Form(?x,
    form:<fingerprint>)``.  It is still structural—not a claim that a palette
    value or a shape fingerprint has task semantics.
    """
    return any(
        not (isinstance(argument, str) and argument.startswith("?"))
        and argument not in GENERIC_TYPE_CONSTANTS
        for _head, arguments in runtime.graph.source_atoms(schema_id)
        for argument in arguments
    )


def _target_baseline(recording: Path, game_id: str) -> dict[str, Any]:
    runtime, workspace = _observe_grid(
        recording, context=f"transfer:baseline:{game_id}"
    )
    active_non_kernel = _non_kernel_hashes(runtime, workspace.activation)
    all_non_kernel = _non_kernel_hashes(runtime, range(runtime.graph.schema_count))
    return {
        "active_non_kernel_hashes": active_non_kernel,
        "all_non_kernel_hashes": all_non_kernel,
        "metrics": runtime.report(),
    }


def evaluate_transfer_matrix(
    directory: Path,
    *,
    expected_games: int | None = None,
) -> dict[str, Any]:
    """Measure directed first-frame structural transfer for every game pair.

    Each source game is observed from a fresh graph once.  For every target,
    the completed source graph is deep-copied before the target is observed.
    This makes every cell independent: ``source -> target_a`` cannot alter
    ``source -> target_b``.  The target also has one fresh-runtime baseline.

    This is deliberately a *structural* transfer measurement.  A cell reports
    source-derived schemas that bind on the target and target-work deltas; it
    makes no prediction or task-success claim.
    """
    recordings = discover_recordings(directory)
    if expected_games is not None and len(recordings) != expected_games:
        raise ValueError(f"expected {expected_games} games, found {len(recordings)}")

    game_ids = list(recordings)
    baselines = {
        game_id: _target_baseline(recording, game_id)
        for game_id, recording in recordings.items()
    }
    sources: dict[str, dict[str, Any]] = {}
    for game_id, recording in recordings.items():
        runtime, _workspace = _observe_grid(
            recording, context=f"transfer:source:{game_id}"
        )
        non_kernel_ids = set(range(runtime.graph.schema_count)) - set(
            runtime.kernel_schema_ids.values()
        )
        sources[game_id] = {
            "graph": runtime.graph,
            "non_kernel_hashes": _non_kernel_hashes(runtime, non_kernel_ids),
            "grounded_hashes": {
                runtime.graph.canonical_hash[schema_id]
                for schema_id in non_kernel_ids
                if _has_grounded_descriptor(runtime, schema_id)
            },
        }

    matrix: dict[str, dict[str, dict[str, Any]]] = {}
    all_cells: list[dict[str, Any]] = []
    for source_id in game_ids:
        source = sources[source_id]
        source_hashes: set[str] = source["non_kernel_hashes"]
        source_grounded_hashes: set[str] = source["grounded_hashes"]
        row: dict[str, dict[str, Any]] = {}
        for target_id in game_ids:
            # deepcopy is the graph-generation boundary: no mutable term,
            # schema, link, evidence, or index state leaks between cells.
            target_runtime, target_workspace = _observe_grid(
                recordings[target_id],
                graph=copy.deepcopy(source["graph"]),
                context=f"transfer:{source_id}->{target_id}",
            )
            baseline = baselines[target_id]
            preexisting_ids = {
                schema_id
                for schema_id, schema_hash in enumerate(target_runtime.graph.canonical_hash)
                if schema_hash in source_hashes
            }
            bound_preexisting_ids = {
                schema_id
                for schema_id, _binding in target_workspace.bindings
                if schema_id in preexisting_ids
            }
            verified_bindings = sum(
                1
                for schema_id, _binding in target_workspace.bindings
                if schema_id in preexisting_ids
            )
            preexisting_grounded_ids = {
                schema_id
                for schema_id in preexisting_ids
                if target_runtime.graph.canonical_hash[schema_id] in source_grounded_hashes
            }
            bound_grounded_ids = bound_preexisting_ids & preexisting_grounded_ids
            grounded_verified_bindings = sum(
                1
                for schema_id, _binding in target_workspace.bindings
                if schema_id in preexisting_grounded_ids
            )
            target_new_hashes = (
                _non_kernel_hashes(
                    target_runtime, range(target_runtime.graph.schema_count)
                )
                - source_hashes
            )
            baseline_metrics = baseline["metrics"]
            target_metrics = target_runtime.report()
            overlap = source_hashes & baseline["active_non_kernel_hashes"]
            cell = {
                "source": source_id,
                "target": target_id,
                # This is the primary yes/no criterion: a source-derived,
                # non-kernel schema had at least one verified target binding.
                "transfer_detected": bool(bound_preexisting_ids),
                "preexisting_active_schemas": len(
                    {
                        schema_id
                        for schema_id in target_workspace.activation
                        if schema_id in preexisting_ids
                    }
                ),
                "preexisting_bound_schemas": len(bound_preexisting_ids),
                "verified_bindings": verified_bindings,
                # This stricter tier excludes source-created but fully generic
                # composites.  Grounded descriptors include form fingerprints
                # and other non-type constants, so it is more informative
                # about source-specific compatibility than the broad tier.
                "grounded_transfer_detected": bool(bound_grounded_ids),
                "preexisting_grounded_active_schemas": len(
                    set(target_workspace.activation) & preexisting_grounded_ids
                ),
                "preexisting_grounded_bound_schemas": len(bound_grounded_ids),
                "grounded_verified_bindings": grounded_verified_bindings,
                # A source/target overlap measured against the target's fresh
                # run avoids treating extra expansion from a transferred graph
                # as evidence by itself.
                "baseline_target_schema_overlap": len(overlap),
                "baseline_target_schema_overlap_fraction": (
                    len(overlap) / len(baseline["active_non_kernel_hashes"])
                    if baseline["active_non_kernel_hashes"]
                    else 0.0
                ),
                # Positive means the transferred run constructed fewer new
                # non-kernel rows than the fresh target baseline.  It is an
                # estimate, not a task-quality assertion.
                "new_schemas_avoided_estimate": (
                    len(baseline["all_non_kernel_hashes"]) - len(target_new_hashes)
                ),
                "active_schema_delta": (
                    target_metrics["active_schemas"] - baseline_metrics["active_schemas"]
                ),
                "active_edge_delta": (
                    target_metrics["active_edges"] - baseline_metrics["active_edges"]
                ),
                "candidates_retrieved_delta": (
                    target_metrics["candidates_retrieved"]
                    - baseline_metrics["candidates_retrieved"]
                ),
                "candidates_verified_delta": (
                    target_metrics["candidates_verified"]
                    - baseline_metrics["candidates_verified"]
                ),
                "compositions_proposed_delta": (
                    target_metrics["compositions_proposed"]
                    - baseline_metrics["compositions_proposed"]
                ),
                "compositions_retained_delta": (
                    target_metrics["compositions_retained"]
                    - baseline_metrics["compositions_retained"]
                ),
                "reusable_composite_candidates_delta": (
                    target_metrics["reusable_composite_candidates"]
                    - baseline_metrics["reusable_composite_candidates"]
                ),
                "work_items_delta": (
                    target_metrics["work_items_processed"]
                    - baseline_metrics["work_items_processed"]
                ),
                "truncations_delta": (
                    target_metrics["truncations"] - baseline_metrics["truncations"]
                ),
                "target_new_non_kernel_schemas": len(target_new_hashes),
            }
            row[target_id] = cell
            all_cells.append(cell)
        matrix[source_id] = row

    return {
        "protocol": {
            "kind": "directed-first-frame-structural-transfer",
            "input": "final rendered layer of the first data.frame packet only",
            "recording_directory": str(directory),
            "selection": "exactly one recording per game id; lexicographic game order",
            "source_learning": "one fresh Runtime observation per source game",
            "target_baseline": "one fresh Runtime observation per target game",
            "cell_isolation": "deep-copy completed source graph before every target observation",
            "kernel_exclusion": "fixed Runtime kernel schemas are excluded from transfer counts",
            "transfer_detected": (
                "at least one non-kernel schema present before the target observation "
                "has a verified target binding"
            ),
            "grounded_transfer_detected": (
                "at least one transferred non-kernel schema with a non-type grounded "
                "descriptor has a verified target binding; generic constructed composites "
                "with variables only are excluded"
            ),
            "scope": (
                "structural transfer only; no labels, actions, rewards, or held-out "
                "prediction performance are used"
            ),
        },
        "game_ids": game_ids,
        "matrix": matrix,
        "aggregate": {
            "cells": len(all_cells),
            "transfer_detected_cells": sum(cell["transfer_detected"] for cell in all_cells),
            "grounded_transfer_detected_cells": sum(
                cell["grounded_transfer_detected"] for cell in all_cells
            ),
            "off_diagonal_transfer_detected_cells": sum(
                cell["transfer_detected"] and cell["source"] != cell["target"]
                for cell in all_cells
            ),
            "off_diagonal_grounded_transfer_detected_cells": sum(
                cell["grounded_transfer_detected"] and cell["source"] != cell["target"]
                for cell in all_cells
            ),
            "verified_bindings": sum(cell["verified_bindings"] for cell in all_cells),
            "metrics": {
                metric: _metric_summary(cell[metric] for cell in all_cells)
                for metric in (
                    "preexisting_active_schemas",
                    "preexisting_bound_schemas",
                    "verified_bindings",
                    "preexisting_grounded_bound_schemas",
                    "grounded_verified_bindings",
                    "baseline_target_schema_overlap",
                    "new_schemas_avoided_estimate",
                    "work_items_delta",
                    "truncations_delta",
                )
            },
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("recording_directory", type=Path)
    parser.add_argument("--expected-games", type=int)
    parser.add_argument(
        "--workers",
        type=int,
        default=0,
        help="independent game processes; 0 uses available CPU cores (default)",
    )
    parser.add_argument(
        "--require-useful-every-game",
        action="store_true",
        help="exit unsuccessfully unless every game yields a reusable structural schema",
    )
    parser.add_argument(
        "--transfer-matrix",
        action="store_true",
        help="evaluate every directed source-to-target structural-transfer pair",
    )
    args = parser.parse_args()
    try:
        report = (
            evaluate_transfer_matrix(
                args.recording_directory, expected_games=args.expected_games
            )
            if args.transfer_matrix
            else evaluate_recordings(
                args.recording_directory, expected_games=args.expected_games, workers=args.workers
            )
        )
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(report, indent=2, sort_keys=True))
    aggregate = report["aggregate"]
    if not args.transfer_matrix and (aggregate["games_failed"] or (
        args.require_useful_every_game
        and aggregate["useful_schema_passes"] != aggregate["games_discovered"]
    )):
        sys.exit(1)


if __name__ == "__main__":
    main()
