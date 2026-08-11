"""Deterministic prompt view over a lossless immutable decision snapshot."""

from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

import causal_protocol as cp


MAX_BY_KIND = {
    "explanation": 4,
    "schema": 2,
    "entity": 0,
    "partial_binding": 0,
    "shadow": 0,
    "prediction": 0,
    "relation_set": 0,
    "environment_evidence": 0,
    "action_proposal": 0,
    "runtime_summary": 0,
    "frame": 0,
    "transition": 0,
    "qwen_derivation": 1,
    "binding": 1,
}


def _copy(value: Any) -> Any:
    return json.loads(cp.stable_json(value))


def _rank(document: Mapping[str, Any]) -> tuple[int, int, int, str]:
    return (
        0 if bool(document.get("invalidated")) else 1,
        int(document.get("support", 0)) - int(document.get("contradiction", 0)),
        int(document.get("created_revision", 0)),
        str(document.get("id", "")),
    )


def _compact_history(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    keys = (
        "transition_id", "index", "opaque_action", "structured_delta",
        "animation_transient_summary",
    )
    compacted = [{key: _copy(item.get(key)) for key in keys} for item in items]
    for item in compacted:
        delta = item.get("structured_delta")
        if not isinstance(delta, dict):
            continue
        cells = list(delta.get("changed_cells", ()))
        delta.pop("changed_cells", None)
    return compacted


def compact_model_view(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Keep a checkable active packet while hashing every omitted object.

    The returned view is for the Qwen prompt. Bounded Python receives the full
    snapshot, so compaction never removes information from C's computational
    substrate.
    """

    view = _copy(snapshot)
    view.pop("dependency_aliases", None)
    view["full_snapshot_hash"] = str(snapshot["snapshot_hash"])
    origin_grid = view.pop("history_origin_grid", None)
    view["history_origin_grid_reference"] = {
        "available_to_python": origin_grid is not None,
        "grid_hash": cp.stable_hash(origin_grid),
    }
    current = view.get("current_observation")
    if isinstance(current, dict) and "raw_grid" in current:
        raw_grid = current.pop("raw_grid")
        row_runs: list[list[list[int]]] = []
        for row in raw_grid:
            runs: list[list[int]] = []
            for value in row:
                value = int(value)
                if runs and runs[-1][0] == value:
                    runs[-1][1] += 1
                else:
                    runs.append([value, 1])
            row_runs.append(runs)
        current["raw_grid_row_runs"] = row_runs
        current["raw_grid_encoding"] = "per-row [value,count] runs"
    view["full_relevant_transition_history"] = _compact_history(
        snapshot["full_relevant_transition_history"]
    )
    progress = view.pop("progress_history", [])
    view["progress_history_summary"] = {
        "count": len(progress),
        "level_change_indices": [
            int(item["index"]) for item in progress
            if int(item["levels_before"]) != int(item["levels_after"])
        ],
        "full_history_hash": cp.stable_hash(progress),
    }

    graph = view["epistemic_graph"]
    all_objects = list(graph.get("objects", ()))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in all_objects:
        grouped.setdefault(str(item.get("kind", "unknown")), []).append(item)
    kept: list[dict[str, Any]] = []
    omitted: dict[str, dict[str, Any]] = {}
    for kind, items in sorted(grouped.items()):
        limit = MAX_BY_KIND.get(kind, len(items))
        ordered = sorted(items, key=_rank, reverse=True)
        selected = ordered[:limit]
        rejected = ordered[limit:]
        kept.extend(selected)
        if rejected:
            omitted[kind] = {
                "count": len(rejected),
                "objects_hash": cp.stable_hash(rejected),
                "selection": f"top-{limit}-by-live-support-recency",
            }
    for item in kept:
        if str(item.get("kind")) == "runtime_summary":
            payload = item.get("payload", {})
            dependencies = list(item.get("dependencies", ()))
            item["dependencies"] = []
            item["payload"] = {
                "cycle": payload.get("cycle"),
                "counts": payload.get("counts", {}),
                "full_payload_hash": cp.stable_hash(payload),
                "dependency_count": len(dependencies),
                "dependencies_hash": cp.stable_hash(dependencies),
            }
        if str(item.get("kind")) == "structured_criticism":
            payload = item.get("payload", {})
            witness = payload.get("structured_witness", {})
            evidence = witness.get("evidence_packet", {})
            grounding = witness.get("grounding_state", {})
            item["payload"] = {
                "status": payload.get("status"),
                "empirical_support_delta": payload.get("empirical_support_delta"),
                "structured_witness": {
                    "effect_variables": witness.get("effect_variables", []),
                    "evidence_packet": {
                        "counts": evidence.get("counts", {}),
                        "rows": list(evidence.get("rows", ()))[:2],
                        "schema_object_id": evidence.get("schema_object_id"),
                        "full_packet_hash": cp.stable_hash(evidence),
                    },
                    "grounding_state": {
                        "entities": list(grounding.get("entities", ()))[:6],
                        "relations": list(grounding.get("relations", ()))[:12],
                        "population_complete": grounding.get("population_complete"),
                        "full_grounding_hash": cp.stable_hash(grounding),
                    },
                },
                "full_payload_hash": cp.stable_hash(payload),
            }
    graph["objects"] = sorted(kept, key=lambda item: str(item.get("id", "")))

    catalog = graph["binding_catalog"]
    rows = list(catalog.get("rows", ()))
    kept_rows = rows[:1]
    if len(rows) > len(kept_rows):
        catalog["omitted_rows"] = {
            "count": len(rows) - len(kept_rows),
            "rows_hash": cp.stable_hash(rows[len(kept_rows):]),
            "selection": "first-stable-binding-id",
        }
    catalog["rows"] = kept_rows
    registry = dict(catalog.get("schema_registry", {}))
    columns = list(catalog.get("columns", ()))
    schema_index = columns.index("schema") if "schema" in columns else None
    referenced_schemas = {
        str(row[schema_index])
        for row in kept_rows
        if schema_index is not None and len(row) > schema_index
    }
    catalog["schema_registry"] = {
        key: value for key, value in registry.items() if str(key) in referenced_schemas
    }
    omitted_registry = {
        key: value for key, value in registry.items() if str(key) not in referenced_schemas
    }
    if omitted_registry:
        catalog["omitted_schema_registry"] = {
            "count": len(omitted_registry),
            "registry_hash": cp.stable_hash(omitted_registry),
            "full_registry_available_to_python": True,
        }
    inherited_omission = catalog.get("omitted_live_bindings")
    if isinstance(inherited_omission, dict):
        catalog["omitted_live_bindings"] = {
            "count": inherited_omission.get("count"),
            "full_rows_hash": inherited_omission.get("full_rows_hash"),
            "selection_rule": inherited_omission.get("selection_rule"),
        }
    visible_ids = {str(item.get("id")) for item in graph["objects"]}
    visible_ids.update(str(item[0]) for item in kept_rows)
    graph["edges"] = [
        item for item in graph.get("edges", ())
        if str(item.get("source")) in visible_ids and str(item.get("target")) in visible_ids
    ]
    graph["compaction"] = {
        "omitted_by_kind": omitted,
        "full_objects_count": len(all_objects),
        "full_objects_hash": cp.stable_hash(all_objects),
        "full_edges_hash": cp.stable_hash(snapshot["epistemic_graph"].get("edges", ())),
        "full_data_available_to_python": True,
    }
    view["encoded_bytes"] = len(cp.stable_json(view).encode("utf-8"))
    return view
