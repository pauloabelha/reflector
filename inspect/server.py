#!/usr/bin/env python3
"""Local read-only web inspector for one Reflector-II observation cycle."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
from collections import Counter, defaultdict, deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOT = PROJECT_ROOT / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from reflector2.perception import perceive_grid  # noqa: E402
from reflector2.raw_frame import load_first_grid  # noqa: E402
from reflector2.runtime import Runtime  # noqa: E402
from reflector2.store import SCHEMA_CANDIDATE, SCHEMA_ESTABLISHED  # noqa: E402

STATIC_ROOT = Path(__file__).resolve().parent / "static"
ASSIGNMENT_ROOT = Path(__file__).resolve().parent / "assignments"
MAX_BODY_BYTES = 4 * 1024 * 1024
MAX_SIDE = 128
RAW_RECORDING_DIRECTORY = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/recordings/reflector-v14-graph-400"
)
RAW_RECORDING = RAW_RECORDING_DIRECTORY / (
    "ar25.reflectoragent.3b673829-b481-46fb-9c8e-3af7bf0bb444.recording.jsonl"
)

def _raw_recordings() -> dict[str, Path]:
    recordings: dict[str, Path] = {}
    for path in sorted(RAW_RECORDING_DIRECTORY.glob("*.recording.jsonl")):
        game_id = path.name.split(".", 1)[0]
        if game_id in recordings:
            continue
        recordings[game_id] = path
    return recordings


def _fixture_catalog() -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for game_id, recording in _raw_recordings().items():
        grid = load_first_grid(recording)
        output.append(
            {
                "id": f"raw-{game_id}",
                "label": f"{game_id} · raw first frame",
                "group": "25-game evaluation",
                "shape": [len(grid), len(grid[0])],
            }
        )
    return output


def _load_assignment(game_id: str) -> dict[str, Any] | None:
    """Read optional inspector annotations; never feed them into Reflector."""
    path = ASSIGNMENT_ROOT / f"{game_id}.schema-labels.json"
    if not path.is_file():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("kind") != "schema-label-assignment":
        raise ValueError(f"invalid assignment file: {path.name}")
    return value


def _load_fixture(fixture_id: str) -> dict[str, Any]:
    game_id = fixture_id.removeprefix("raw-") if fixture_id.startswith("raw-") else ""
    recording = _raw_recordings().get(game_id)
    # Retain the original inspector URL as an ar25 compatibility alias.
    if fixture_id == "raw-public-frame":
        game_id, recording = "ar25", RAW_RECORDING if RAW_RECORDING.exists() else None
    if recording is not None:
        return {
            "id": fixture_id,
            "label": f"{game_id} · raw first frame",
            "grid": load_first_grid(recording),
            "background": None,
            "assignment": _load_assignment(game_id),
        }
    raise KeyError(fixture_id)


def _validate_grid(value: Any) -> tuple[tuple[int, ...], ...]:
    if not isinstance(value, list) or not value or not isinstance(value[0], list) or not value[0]:
        raise ValueError("grid must be a non-empty array of rows")
    width = len(value[0])
    if len(value) > MAX_SIDE or width > MAX_SIDE:
        raise ValueError(f"grid dimensions may not exceed {MAX_SIDE}×{MAX_SIDE}")
    if any(not isinstance(row, list) or len(row) != width for row in value):
        raise ValueError("grid must be rectangular")
    grid = []
    for row in value:
        converted = []
        for item in row:
            if not isinstance(item, int) or isinstance(item, bool) or not 0 <= item <= 65535:
                raise ValueError("grid values must be integers in 0..65535")
            converted.append(item)
        grid.append(tuple(converted))
    return tuple(grid)


def _format_atom(head: str, arguments: tuple[Any, ...]) -> str:
    return f"{head}({', '.join(str(item) for item in arguments)})"


def _static_relative(request_path: str) -> str | None:
    if request_path in {"/inspect", "/inspect/"}:
        return "index.html"
    if request_path.startswith("/inspect/"):
        return request_path.removeprefix("/inspect/")
    return None


def _visual_regions(
    grid: tuple[tuple[int, ...], ...], background: int
) -> list[dict[str, Any]]:
    height, width = len(grid), len(grid[0])
    regions = []
    # Match perception.py's sorted-value/component order, making region IDs a
    # stable bridge from runtime bindings back onto the rendered frame.
    for value in sorted({cell for row in grid for cell in row if cell != background}):
        unseen = {
            (x, y)
            for y in range(height)
            for x in range(width)
            if grid[y][x] == value
        }
        while unseen and len(regions) < 256:
            start = min(unseen, key=lambda point: (point[1], point[0]))
            queue = deque([start])
            unseen.remove(start)
            cells = []
            while queue:
                x, y = queue.popleft()
                cells.append([x, y])
                for neighbor in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    nx, ny = neighbor
                    if neighbor in unseen and 0 <= nx < width and 0 <= ny < height:
                        unseen.remove(neighbor)
                        queue.append(neighbor)
            xs = [cell[0] for cell in cells]
            ys = [cell[1] for cell in cells]
            regions.append(
                {
                    "id": len(regions),
                    "value": value,
                    "area": len(cells),
                    "bbox": [min(xs), min(ys), max(xs), max(ys)],
                    "cells": cells,
                }
            )
    return regions


def _bound_region_ids(
    bindings: list[dict[int, int]],
    terms: Any,
    region_terms: tuple[int, ...],
    figure_regions: dict[int, set[int]],
) -> list[int]:
    """Project region and cell bindings back to deterministic visual region IDs."""
    direct = {term: index for index, term in enumerate(region_terms)}
    output: set[int] = set()
    for binding in bindings:
        for term in binding.values():
            if term in direct:
                output.add(direct[term])
                continue
            if term in figure_regions:
                output.update(figure_regions[term])
                continue
            value = terms.value(term)
            if isinstance(value, str) and value.startswith("cell:inspect:frame-0:"):
                pieces = value.split(":")
                if len(pieces) >= 5 and pieces[3].isdigit():
                    output.add(int(pieces[3]))
    return sorted(output)


def analyze_grid(
    grid: tuple[tuple[int, ...], ...],
    *,
    background: int | None,
    palette: dict[str, str] | None = None,
) -> dict[str, Any]:
    counts = Counter(value for row in grid for value in row)
    actual_background = (
        max(counts, key=lambda value: (counts[value], -value)) if background is None else background
    )
    runtime = Runtime()
    batch = perceive_grid(
        runtime.graph.terms,
        grid,
        "inspect:frame-0",
        background=actual_background,
    )
    workspace = runtime.observe(batch)
    graph = runtime.graph
    terms = graph.terms
    active = set(workspace.activation)
    visual_regions = _visual_regions(grid, actual_background)

    binding_counts: dict[int, int] = Counter(schema_id for schema_id, _binding in workspace.bindings)
    bindings_by_schema: dict[int, list[dict[int, int]]] = defaultdict(list)
    for schema_id, binding in workspace.bindings:
        bindings_by_schema[schema_id].append(binding)
    shadows_by_schema: dict[int, list[dict[str, object]]] = defaultdict(list)
    for shadow in runtime.shadows.values():
        shadows_by_schema[shadow.schema_id].append(
            {
                "id": shadow.shadow_id,
                "status": shadow.status,
                "carrier": shadow.carrier,
                "open_roles": [f"?v{value}" for value in shadow.open_roles],
                "open_constraints": list(shadow.open_constraints),
                "child_roles": [
                    {
                        "role": role.role_index,
                        "schema": role.child_schema_id,
                        "status": role.status,
                        "assignments": [f"?v{variable}={terms.value(term)}" for variable, term in role.assignments],
                    }
                    for role in shadow.child_roles
                ],
                "constraints": [
                    {"constraint": constraint.constraint_index, "status": constraint.status}
                    for constraint in shadow.constraints
                ],
                "completed_roles": list(shadow.completed_roles),
                "completed_constraints": list(shadow.completed_constraints),
                "activation": round(shadow.activation, 4),
                "provenance": shadow.provenance,
            }
        )
    region_index = {term: index for index, term in enumerate(batch.region_terms)}
    figure_regions: dict[int, set[int]] = defaultdict(set)
    for head, arguments in batch.facts:
        if str(terms.value(head)) == "Contains" and len(arguments) == 2:
            figure, region = arguments
            if region in region_index:
                figure_regions[figure].add(region_index[region])
    reusable = set(runtime.reusable_composite_candidates())
    nodes = []
    for schema_id in sorted(active, key=lambda item: (graph.depth[item], graph.canonical_hash[item])):
        atoms = graph.source_atoms(schema_id)
        region_ids = _bound_region_ids(
            bindings_by_schema.get(schema_id, []), terms, batch.region_terms, figure_regions
        )
        decompositions = []
        for decomposition_id in graph.decomposition_out_index.get(schema_id, ()):
            occurrences = []
            for child, interface in graph.decomposition_occurrences(decomposition_id):
                occurrences.append(
                    {
                        "schema": child,
                        "name": graph.display_name[child],
                        "short_hash": graph.canonical_hash[child][:10],
                        "interface": [f"?v{child_var} → ?v{owner_var}" for child_var, owner_var in interface],
                    }
                )
            decompositions.append(
                {
                    "id": decomposition_id,
                    "provenance": sorted(graph.decomposition_provenance[decomposition_id]),
                    "occurrences": occurrences,
                }
            )
        nodes.append(
            {
                "id": schema_id,
                "hash": graph.canonical_hash[schema_id],
                "short_hash": graph.canonical_hash[schema_id][:10],
                "name": graph.display_name[schema_id],
                "depth": graph.depth[schema_id],
                "state": (
                    "candidate"
                    if graph.schema_state[schema_id] == SCHEMA_CANDIDATE
                    else "established"
                    if graph.schema_state[schema_id] == SCHEMA_ESTABLISHED
                    else "promoted"
                ),
                "activation": round(workspace.activation[schema_id], 4),
                "bindings": binding_counts.get(schema_id, 0),
                "binding_records": [
                    {
                        "status": "REIFIED",
                        "carrier": binding.carrier,
                        "activation": round(binding.activation, 4),
                        "provenance": binding.provenance,
                    }
                    for binding in workspace.bindings
                    if binding.schema_id == schema_id
                ],
                "region_ids": region_ids,
                "body": [_format_atom(head, args) for head, args in atoms],
                "definition_constraints": [
                    _format_atom(head, args) for head, args in graph.definition_constraint_atoms(schema_id)
                ],
                "interface": [
                    f"?v{value}"
                    for value in graph.interface_variables[
                        graph.interface_offset[schema_id] : graph.interface_offset[schema_id] + graph.interface_count[schema_id]
                    ]
                ],
                "shadows": shadows_by_schema.get(schema_id, []),
                "heads": sorted({head for head, _args in atoms}),
                "provenance": sorted(graph.provenance[schema_id]),
                "support": graph.support[schema_id],
                "contradiction": graph.contradiction[schema_id],
                "uses": graph.use_count[schema_id],
                "reusable_candidate": schema_id in reusable,
                "decompositions": decompositions,
            }
        )

    links = []
    for edge_id in sorted(workspace.active_edge_ids):
        source = graph.src[edge_id]
        destination = graph.dst[edge_id]
        if source not in active or destination not in active:
            continue
        links.append(
            {
                "source": source,
                "target": destination,
                "relation": str(terms.value(graph.relation[edge_id])),
                "weight": graph.weight[edge_id],
                "provenance": sorted(graph.edge_provenance[edge_id]),
            }
        )

    fact_counts: dict[str, int] = defaultdict(int)
    fact_sample = []
    for head, args in batch.facts:
        head_value = str(terms.value(head))
        fact_counts[head_value] += 1
        if len(fact_sample) < 80:
            fact_sample.append(_format_atom(head_value, tuple(terms.value(arg) for arg in args)))

    report = runtime.report()
    truncation_reasons = Counter(
        str(event["reason"])
        for event in runtime.trace
        if event["event"] == "truncation"
    )
    metrics = {
        key: report[key]
        for key in (
            "total_schemas",
            "active_schemas",
            "active_edges",
            "active_edge_visits",
            "candidates_retrieved",
            "candidates_verified",
            "compositions_proposed",
            "compositions_retained",
            "work_items_processed",
            "frontier_sizes",
            "peak_workspace",
            "truncations",
            "matching_time_s",
            "activation_time_s",
            "composition_time_s",
            "reusable_composite_candidates",
            "term_bytes_estimate",
            "graph_bytes_estimate",
        )
    }
    return {
        "shape": [len(grid), len(grid[0])],
        "grid": grid,
        "palette": palette or {},
        "background": actual_background,
        "value_counts": dict(sorted(counts.items())),
        "regions": visual_regions,
        "forms": sorted(str(terms.value(term)) for term in set(batch.form_terms)),
        "fact_counts": dict(sorted(fact_counts.items())),
        "fact_sample": fact_sample,
        "nodes": nodes,
        "links": links,
        "metrics": metrics,
        "truncation_reasons": dict(sorted(truncation_reasons.items())),
        "limits": {
            "active_nodes": runtime.limits.max_active_nodes,
            "active_edges": runtime.limits.max_active_edges,
            "composition_proposals": runtime.limits.max_composition_proposals,
            "composition_rounds": runtime.limits.max_composition_rounds,
            "binding_candidates": runtime.limits.max_binding_candidates,
            "facts_per_atom": runtime.limits.max_facts_per_atom,
            "transition_correspondences": runtime.limits.max_transition_correspondences,
            "analogy_candidates": runtime.limits.max_analogy_candidates,
        },
    }


class InspectorHandler(BaseHTTPRequestHandler):
    server_version = "ReflectorIIInspector/0.1"

    def log_message(self, format: str, *args: object) -> None:
        sys.stderr.write("[inspect] " + format % args + "\n")

    def _json(self, value: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        payload = json.dumps(value, separators=(",", ":"), default=list).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _error(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self._json({"error": message}, status)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/fixtures":
            self._json({"fixtures": _fixture_catalog()})
            return
        if parsed.path == "/api/fixture":
            fixture_id = parse_qs(parsed.query).get("id", [""])[0]
            try:
                self._json(_load_fixture(fixture_id))
            except KeyError:
                self._error("unknown fixture", HTTPStatus.NOT_FOUND)
            return
        if parsed.path == "/":
            self.send_response(HTTPStatus.PERMANENT_REDIRECT)
            self.send_header("Location", "/inspect/")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        relative = _static_relative(parsed.path)
        if relative is None:
            self._error("not found", HTTPStatus.NOT_FOUND)
            return
        target = (STATIC_ROOT / relative).resolve()
        if STATIC_ROOT not in target.parents and target != STATIC_ROOT:
            self._error("invalid path", HTTPStatus.FORBIDDEN)
            return
        if not target.is_file():
            self._error("not found", HTTPStatus.NOT_FOUND)
            return
        payload = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(payload)

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/analyze":
            self._error("not found", HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 < length <= MAX_BODY_BYTES:
                raise ValueError("request body is empty or too large")
            value = json.loads(self.rfile.read(length))
            grid = _validate_grid(value.get("grid"))
            background = value.get("background")
            if background is not None and not isinstance(background, int):
                raise ValueError("background must be an integer or null")
            palette = value.get("palette")
            if palette is not None and not isinstance(palette, dict):
                raise ValueError("palette must be an object")
            self._json(analyze_grid(grid, background=background, palette=palette))
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            self._error(str(error))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), InspectorHandler)
    print(f"Reflector-II inspector: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
