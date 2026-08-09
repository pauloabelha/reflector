"""Run the preregistered whole-suite shared-attention census on real ARC games."""

from __future__ import annotations

import argparse
import base64
import hashlib
import importlib.util
import io
import json
import os
import sys
import threading
import time
from collections import Counter
from concurrent.futures import CancelledError, Future, ThreadPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from PIL import Image


HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent


def _load(name: str, path: Path) -> Any:
    resolved = path.resolve()
    # Prefer the most recently loaded equivalent module.  This keeps dataclass
    # identity stable for embedders/tests that intentionally load the graph
    # before loading the runner.
    for existing in reversed(tuple(sys.modules.values())):
        existing_file = getattr(existing, "__file__", None)
        if existing_file is not None and Path(existing_file).resolve() == resolved:
            return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EG = _load("shared_attention_live_graph", HERE / "epistemic_graph.py")
LEDGER = _load("shared_attention_live_ledger", HERE / "ledger.py")
QC = _load("shared_attention_live_qwen", HERE / "qwen_cognition.py")
AMBIGUITY = _load("shared_attention_live_ambiguity", HERE / "ambiguity.py")
CENSUS = _load("shared_attention_live_census", HERE / "census.py")
V0 = _load("shared_attention_live_v0", HERE.parent / "parallel-cognitive-workspace-v0" / "experiment.py")
BASE = V0.V0.BASE

Grid = tuple[tuple[int, ...], ...]
ARTIFACTS = HERE / "artifacts"
STATUS_LOCK = threading.Lock()
ARC_PALETTE = (
    (0, 0, 0), (0, 116, 217), (255, 65, 54), (46, 204, 64),
    (255, 220, 0), (170, 170, 170), (240, 18, 190), (255, 133, 27),
    (127, 219, 255), (135, 12, 37), (255, 255, 255), (90, 90, 90),
    (100, 180, 255), (255, 130, 130), (140, 255, 150), (255, 245, 140),
)


def load_config() -> dict[str, Any]:
    return json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def build_jobs(config: Mapping[str, Any], *, artifacts_root: Path = ARTIFACTS) -> list[dict[str, Any]]:
    """Build profile-matched fresh job identities without creating their roots."""

    return [
        {
            "pair_id": f"{profile_id}--{game}",
            "profile_id": str(profile_id),
            "game": str(game),
            "arm_id": str(arm),
            "workspace_root": str(Path(artifacts_root) / "workspaces" / f"{profile_id}--{game}--{arm}"),
        }
        for profile_id in config["profiles"]
        for game in config["games"]
        for arm in config["arms"]
    ]


def append_status(message: str) -> None:
    with STATUS_LOCK:
        with (HERE / "STATUS.md").open("a", encoding="utf-8") as stream:
            stream.write(message.rstrip() + "\n")
            stream.flush()
            os.fsync(stream.fileno())


def grid_value(value: Any) -> Grid:
    return tuple(tuple(int(cell) for cell in row) for row in value)


def grid_png_bytes(grid: Grid, *, scale: int = 4) -> bytes:
    height = len(grid)
    width = len(grid[0]) if height else 0
    image = Image.new("RGB", (width, height))
    image.putdata([ARC_PALETTE[int(cell) % len(ARC_PALETTE)] for row in grid for cell in row])
    if scale > 1:
        image = image.resize((width * scale, height * scale), Image.Resampling.NEAREST)
    stream = io.BytesIO()
    image.save(stream, format="PNG", optimize=True)
    return stream.getvalue()


def grid_data_url(grid: Grid) -> str:
    return "data:image/png;base64," + base64.b64encode(grid_png_bytes(grid)).decode("ascii")


def persist_visual(root: Path, grid: Grid) -> tuple[str, str]:
    value = grid_png_bytes(grid)
    digest = hashlib.sha256(value).hexdigest()
    path = root / "blobs" / "visual" / f"{digest}.png"
    if not path.exists():
        LEDGER.atomic_bytes(path, value)
    return digest, str(path.relative_to(root))


def _mask_runs(cells: Sequence[Sequence[int]]) -> list[list[int]]:
    grouped: dict[int, list[int]] = {}
    for row, column in cells:
        grouped.setdefault(int(row), []).append(int(column))
    runs: list[list[int]] = []
    for row, columns in sorted(grouped.items()):
        ordered = sorted(set(columns))
        start = previous = ordered[0]
        for column in ordered[1:]:
            if column == previous + 1:
                previous = column
                continue
            runs.append([row, start, previous])
            start = previous = column
        runs.append([row, start, previous])
    return runs


def graph_state(root: Path) -> tuple[Any, list[Any]]:
    documents = LEDGER.graph_event_documents(LEDGER.list_events(root), root)
    events = [EG.event_from_document(item) for item in documents]
    return EG.replay(events), events


def commit_graph_events(root: Path, workspace_id: str, events: Sequence[Any]) -> None:
    events = tuple(events)
    if not events:
        return
    if len(events) == 1:
        event = events[0]
        document = EG.event_document(event)
        blob = LEDGER.put_blob(root, document)
        LEDGER.append_event(
            root,
            workspace_id=workspace_id,
            event_type="EpistemicGraphEvent",
            actor=str(event.actor),
            payload={"graph_event_blob": blob, "graph_revision": int(event.seq), "graph_event_hash": event.event_hash},
            event_id=f"outer:{event.event_id}",
        )
        return
    documents = [EG.event_document(event) for event in events]
    envelope = {
        "protocol": "shared-attention-graph-batch-v1",
        "count": len(documents),
        "first_revision": int(documents[0]["seq"]),
        "last_revision": int(documents[-1]["seq"]),
        "first_prev_hash": documents[0]["prev_hash"],
        "last_event_hash": documents[-1]["event_hash"],
        "documents": documents,
    }
    blob = LEDGER.put_blob(root, envelope)
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="EpistemicGraphBatch",
        actor="coordinator",
        payload={
            "graph_batch_blob": blob,
            "graph_event_count": len(documents),
            "first_graph_revision": int(documents[0]["seq"]),
            "last_graph_revision": int(documents[-1]["seq"]),
            "first_graph_prev_hash": documents[0]["prev_hash"],
            "last_graph_event_hash": documents[-1]["event_hash"],
        },
        event_id=f"outer-batch:{blob}",
    )


def persist_graph_events(root: Path, workspace_id: str, events: Sequence[Any]) -> tuple[dict[str, Any], ...]:
    before = len(LEDGER.list_events(root))
    commit_graph_events(root, workspace_id, events)
    return tuple(LEDGER.list_events(root)[before:])


def rebuild_graph(root: Path) -> tuple[Any, tuple[Any, ...]]:
    state, events = graph_state(root)
    return state, tuple(events)


def ingest_qwen_compilation(
    state: Any,
    compilation: Mapping[str, Any],
    *,
    response_id: str,
    proposal_attention_boost: float,
) -> Any:
    """Pure graph application used by tests and the live durable wrapper."""

    events: list[Any] = []
    object_ids: list[str] = []
    local_schema_ids: dict[str, str] = {}
    accepted = list(compilation.get("accepted", ()))
    ordered = [item for item in accepted if item.get("kind") == "schema"] + [
        item for item in accepted if item.get("kind") == "explanation"
    ]
    for index, original in enumerate(ordered):
        item = dict(original)
        dependencies = list(item.get("dependency_ids", ()))
        if item.get("kind") == "explanation" and str(item.get("schema_ref")) in local_schema_ids:
            resolved = local_schema_ids[str(item["schema_ref"])]
            dependencies.append(resolved)
            item["schema_ref"] = resolved
            item["identity"] = {**dict(item["identity"]), "schema_ref": resolved}
        item["dependency_ids"] = sorted(set(dependencies))
        result = EG.ingest_qwen_writes(state, (item,), response_id=f"{response_id}:{index}")
        state = result.state
        events.extend(result.events)
        object_ids.extend(result.object_ids)
        if item.get("kind") == "schema" and item.get("local_ref") is not None:
            local_schema_ids[str(item["local_ref"])] = result.object_ids[0]
    weight = max(1, min(100, int(round(32 * float(proposal_attention_boost)))))
    for index, object_id in enumerate(object_ids):
        event = EG.attention_event(
            state,
            worker="qwen",
            object_id=object_id,
            weight=weight,
            channel="inspect",
            basis_ids=(),
            contribution_key=f"compiled:{response_id}:{index}",
        )
        state = EG.apply_event(state, event)
        events.append(event)
    return EG.IngestResult(state, tuple(events), tuple(object_ids))


def record_frontier_pickups(
    state: Any,
    *,
    worker: str,
    object_ids: Sequence[str],
    previously_exposed_ids: Sequence[str],
    exposure_key: str,
) -> Any:
    events: list[Any] = []
    seen = set(previously_exposed_ids)
    for object_id in object_ids:
        item = next((value for value in state.objects if value.object_id == object_id), None)
        if item is None or item.created_by == worker or object_id in seen:
            continue
        event = EG.attention_event(
            state,
            worker=worker,
            object_id=object_id,
            weight=1,
            channel="frontier-exposure",
            basis_ids=(),
            contribution_key=f"{exposure_key}:{object_id}",
        )
        state = EG.apply_event(state, event)
        events.append(event)
        seen.add(object_id)
    return EG.IngestResult(state, tuple(events), tuple(object_ids))


def record_grounded_pickup(state: Any, pickup_id: str, downstream_id: str, *, worker: str) -> Any:
    event = EG.grounded_pickup_event(
        state,
        pickup_id=pickup_id,
        downstream_object_id=downstream_id,
        worker=worker,
    )
    return EG.IngestResult(EG.apply_event(state, event), (event,), edge_ids=(event.payload["item"]["edge_id"],))


def matching_structured_criticism(
    state: Any,
    *,
    worker: str,
    target_id: str,
    status: str,
    witness: Mapping[str, Any],
) -> Any | None:
    """Indexed semantic deduplication for unchanged grounding criticism."""

    witness_key = EG.stable_json(witness)
    return next(
        (
            item
            for item in EG.find_objects(
                state, kind="structured_criticism", created_by=worker
            )
            if target_id in item.dependency_ids
            and item.payload.get("status") == status
            and EG.stable_json(item.payload.get("structured_witness", {})) == witness_key
        ),
        None,
    )


def repair_grounded_pickup_edges(root: Path, workspace_id: str, state: Any) -> Any:
    """Complete a binding→pickup edge interrupted between durable events."""

    qwen_ids = {item.object_id for item in state.objects if item.created_by == "qwen"}
    existing_targets = {
        item.target_id for item in state.edges if item.kind == "grounds_pickup"
    }
    for binding in (
        item
        for item in state.objects
        if item.kind == "binding" and item.created_by == "r2" and item.object_id not in existing_targets
    ):
        schema_id = next((item for item in binding.dependency_ids if item in qwen_ids), None)
        if schema_id is None:
            continue
        pickup = next(
            (
                item
                for item in state.pickups
                if item.direction == "qwen->r2" and item.object_id == schema_id
            ),
            None,
        )
        if pickup is None:
            continue
        event = EG.grounded_pickup_event(
            state,
            pickup_id=pickup.pickup_id,
            downstream_object_id=binding.object_id,
            worker="r2",
            payload={"grounding_status": binding.payload.get("status", "bound"), "recovered": True},
        )
        state = apply_graph_event(root, workspace_id, state, event)
    return state


def apply_graph_event(
    root: Path,
    workspace_id: str,
    state: Any,
    event: Any,
    *,
    object_lookup: Mapping[str, Any] | None = None,
) -> Any:
    next_state = EG.apply_event(state, event, object_index=object_lookup)
    commit_graph_events(root, workspace_id, (event,))
    return next_state


def apply_ingest(root: Path, workspace_id: str, result: Any) -> Any:
    commit_graph_events(root, workspace_id, result.events)
    return result.state


def observation_value(observation: Any) -> tuple[dict[str, Any], Grid]:
    return BASE.observation_record(observation), BASE.observation_grid(observation)


def store_observation(root: Path, observation: Any) -> tuple[str, dict[str, Any], Grid]:
    record, grid = observation_value(observation)
    blob = LEDGER.put_blob(root, {"record": record, "grid": [list(row) for row in grid]})
    return blob, record, grid


def execute_action(environment: Any, game: str, action_id: int, data: Mapping[str, int], reason: str) -> Any:
    from arcengine import GameAction

    action = GameAction.from_id(int(action_id))
    if data:
        action.set_data(dict(data))
    result = environment.step(
        action,
        data={**dict(data), "game_id": game},
        reasoning={"experiment": "shared-attention-census-v1", "reason": reason},
    )
    observation = result if result is not None else environment.observation_space
    if observation is None:
        raise RuntimeError("ARC returned no successor observation")
    return observation


def opaque_intervention(workspace_id: str, action_id: int, data: Mapping[str, int] | None = None) -> str:
    return f"im:{LEDGER.stable_hash({'workspace': workspace_id, 'token': int(action_id), 'data_shape': sorted((data or {}).keys())})[:16]}"


def _object_payload(event: Any) -> dict[str, Any] | None:
    if event.event_type != "ObjectAdded":
        return None
    return event.payload.get("item")


def r2_workspace_document(cognition: Any, legal: Sequence[int]) -> dict[str, Any]:
    """A compact but lossless census of every currently live R2 alternative."""

    runtime = cognition.runtime
    graph = runtime.graph
    workspace = runtime.workspace
    explanations = () if workspace is None else cognition.explanations.construct(workspace, legal)
    if workspace is None:
        return {"cycle": runtime.cycle, "schemas": [], "bindings": [], "partial_bindings": [], "shadows": [], "explanations": []}
    schemas = []
    for schema_id in sorted(workspace.activation, key=lambda item: graph.canonical_hash[item]):
        schemas.append(
            {
                "id": graph.canonical_hash[schema_id],
                "activation_milli": int(round(workspace.activation[schema_id] * 1000)),
                "provenance": sorted(graph.provenance[schema_id]),
                "atoms": [
                    [
                        (f"OpaqueIntervention:{LEDGER.stable_hash(head)[:12]}" if str(head).startswith("arc-action:") else head),
                        list(arguments),
                    ]
                    for head, arguments in graph.source_atoms(schema_id)
                ],
            }
        )
    bindings = [
        {
            "schema": graph.canonical_hash[item.schema_id],
            "assignments": [[int(left), int(right)] for left, right in item.assignments],
            "resolved_assignments": [
                {
                    "role_index": int(left),
                    "term_id": int(right),
                    "term_value": graph.terms.value(right),
                    "visual_grounding": "OPEN",
                }
                for left, right in item.assignments
            ],
            "carrier": item.carrier,
            "activation_milli": int(round(item.activation * 1000)),
            "provenance": item.provenance,
        }
        for item in workspace.bindings
    ]
    partials = []
    for partial_id in workspace.partial_binding_ids:
        item = runtime.partial_bindings[partial_id]
        partials.append(
            {
                "id": item.partial_binding_id,
                "schema": graph.canonical_hash[item.schema_id],
                "assignments": [list(pair) for pair in item.assignments],
                "resolved_assignments": [
                    {
                        "role_index": int(left),
                        "term_id": int(right),
                        "term_value": graph.terms.value(right),
                        "visual_grounding": "OPEN",
                    }
                    for left, right in item.assignments
                ],
                "bound_roles": list(item.bound_roles),
                "unresolved_roles": list(item.unresolved_roles),
                "satisfied_constraints": list(item.satisfied_constraints),
                "unresolved_constraints": list(item.unresolved_constraints),
                "incompatible_constraints": list(item.incompatible_constraints),
                "provenance": item.provenance,
            }
        )
    shadows = []
    for shadow_id in workspace.shadow_ids:
        item = runtime.shadows[shadow_id]
        shadows.append(
            {
                "id": item.shadow_id,
                "schema": graph.canonical_hash[item.schema_id],
                "partial_binding": item.partial_binding_id,
                "assignments": [list(pair) for pair in item.assignments],
                "resolved_assignments": [
                    {
                        "role_index": int(left),
                        "term_id": int(right),
                        "term_value": graph.terms.value(right),
                        "visual_grounding": "OPEN",
                    }
                    for left, right in item.assignments
                ],
                "open_roles": list(item.open_roles),
                "open_constraints": list(item.open_constraints),
                "status": item.status,
                "provenance": item.provenance,
            }
        )
    return {
        "cycle": runtime.cycle,
        "schemas": schemas,
        "bindings": bindings,
        "partial_bindings": partials,
        "shadows": shadows,
        "explanations": [
            {
                "schemas": [graph.canonical_hash[item] for item in value.constituent_schema_ids],
                "provenance": list(value.provenance),
                "confirmations": value.confirmations,
                "refutations": value.refutations,
                "score_milli": int(round(value.score * 1000)),
            }
            for value in explanations
        ],
        "metrics": runtime.metrics.deterministic(),
    }


def sanitize_r2_value(value: Any) -> Any:
    """Remove opaque ARC intervention identities from every Qwen-visible R2 field."""

    if isinstance(value, Mapping):
        return {str(key): sanitize_r2_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize_r2_value(item) for item in value]
    if isinstance(value, str) and value.startswith("arc-action:"):
        return f"OpaqueIntervention:{LEDGER.stable_hash(value)[:12]}"
    return value


def ensure_graph_object(
    root: Path,
    workspace_id: str,
    state: Any,
    *,
    kind: str,
    created_by: str,
    identity: Mapping[str, Any],
    payload: Mapping[str, Any],
    dependency_ids: Sequence[str] = (),
    event_key: str,
    object_lookup: dict[str, Any] | None = None,
    pending_events: list[Any] | None = None,
) -> tuple[Any, str]:
    """Add one semantic object once, while retaining every later provenance event elsewhere."""

    candidate = EG.make_object(
        kind=kind,
        created_by=created_by,
        created_revision=state.revision + 1,
        identity=identity,
        payload=payload,
        dependency_ids=dependency_ids,
    )
    existing = (
        object_lookup.get(candidate.object_id)
        if object_lookup is not None
        else EG.get_object(state, candidate.object_id)
    )
    if existing is not None:
        if (
            existing.kind != candidate.kind
            or existing.created_by != candidate.created_by
            or existing.identity_json != candidate.identity_json
            or existing.payload_json != candidate.payload_json
            or existing.dependency_ids != candidate.dependency_ids
        ):
            raise RuntimeError(f"semantic graph object changed under stable identity: {candidate.object_id}")
        return state, existing.object_id
    event = EG.object_event(
        state,
        kind=kind,
        created_by=created_by,
        identity=identity,
        payload=payload,
        dependency_ids=dependency_ids,
        event_key=event_key,
    )
    state = EG.apply_event(state, event, object_index=object_lookup)
    if pending_events is None:
        commit_graph_events(root, workspace_id, (event,))
    else:
        pending_events.append(event)
    object_id = str(event.payload["item"]["object_id"])
    if object_lookup is not None:
        object_lookup[object_id] = candidate
    return state, object_id


def ingest_r2_workspace_objects(
    root: Path,
    workspace_id: str,
    state: Any,
    cognition: Any,
    legal: Sequence[int],
    *,
    observation_key: str,
    basis_ids: Sequence[str],
) -> Any:
    """Materialize R2 cognition as addressable first-class graph objects.

    The content-addressed blob remains a recovery/expansion aid, but it is no
    longer the only representation Qwen can inspect.
    """

    document = sanitize_r2_value(r2_workspace_document(cognition, legal))
    blob = LEDGER.put_blob(root, document)
    object_lookup = {item.object_id: item for item in state.objects}
    pending_events: list[Any] = []
    schema_ids: dict[str, str] = {}
    current_ids: list[str] = []
    schema_activation: dict[str, int] = {}
    for item in document["schemas"]:
        semantic_payload = {
            "atoms": item["atoms"],
        }
        state, object_id = ensure_graph_object(
            root,
            workspace_id,
            state,
            kind="schema",
            created_by="r2",
            identity={"r2_schema_hash": item["id"]},
            payload=semantic_payload,
            event_key=f"r2-schema:{item['id']}",
            object_lookup=object_lookup,
            pending_events=pending_events,
        )
        schema_ids[str(item["id"])] = object_id
        schema_activation[object_id] = int(item["activation_milli"])
        current_ids.append(object_id)

    def materialize_many(kind: str, values: Sequence[Mapping[str, Any]]) -> None:
        nonlocal state
        for index, item in enumerate(values):
            schema_hashes = [str(item["schema"])] if item.get("schema") else [str(value) for value in item.get("schemas", ())]
            dependencies = [schema_ids[value] for value in schema_hashes if value in schema_ids]
            semantic_payload = {key: value for key, value in item.items() if key != "activation_milli"}
            semantic = LEDGER.stable_hash({"kind": kind, "value": semantic_payload})
            state, object_id = ensure_graph_object(
                root,
                workspace_id,
                state,
                kind=kind,
                created_by="r2",
                identity={"semantic_hash": semantic},
                payload=semantic_payload,
                dependency_ids=dependencies,
                event_key=f"r2-{kind}:{semantic}",
                object_lookup=object_lookup,
                pending_events=pending_events,
            )
            current_ids.append(object_id)

    materialize_many("r2_binding", document["bindings"])
    materialize_many("partial_binding", document["partial_bindings"])
    materialize_many("shadow", document["shadows"])
    materialize_many("explanation", document["explanations"])
    snapshot_payload = {
        "workspace_blob": blob,
        "cycle": document["cycle"],
        "schema_object_ids": [schema_ids[key] for key in sorted(schema_ids)],
        "active_object_ids": sorted(current_ids),
        "schema_activation_milli": dict(sorted(schema_activation.items())),
        "counts": {
            "schemas": len(document["schemas"]),
            "bindings": len(document["bindings"]),
            "partial_bindings": len(document["partial_bindings"]),
            "shadows": len(document["shadows"]),
            "explanations": len(document["explanations"]),
        },
        "expansion": "all listed objects are directly addressable; workspace_blob is exact recovery data",
    }
    result = EG.ingest_r2_runtime_summary(
        state,
        snapshot_payload,
        observation_key=observation_key,
        basis_ids=tuple(sorted(set((*basis_ids, *current_ids)))),
    )
    pending_events.extend(result.events)
    state = result.state
    commit_graph_events(root, workspace_id, pending_events)
    return state


def ingest_frame_objects(
    root: Path,
    workspace_id: str,
    state: Any,
    grid: Grid,
    *,
    frame_digest: str,
    frame_index: int,
    legal_count: int,
) -> tuple[Any, dict[str, str], str]:
    """Ground one perceptual layer all the way down to a persisted PNG/mask."""

    existing_frame = next(
        (
            item
            for item in EG.find_objects(state, kind="frame")
            if item.identity.get("frame_digest") == frame_digest
        ),
        None,
    )
    if existing_frame is not None:
        entity_ids = {
            str(item.payload.get("grounding", {}).get("local_component_ref")): item.object_id
            for item in EG.find_objects(state, kind="entity")
            if existing_frame.object_id in item.dependency_ids
        }
        return state, entity_ids, existing_frame.object_id
    png_digest, png_path = persist_visual(root, grid)
    frame_event = EG.object_event(
        state,
        kind="frame",
        created_by="environment",
        identity={"frame_digest": frame_digest},
        payload={
            "frame_index": frame_index,
            "width": len(grid[0]) if grid else 0,
            "height": len(grid),
            "png_sha256": png_digest,
            "png_blob": png_path,
            "pixel_digest": LEDGER.stable_hash(grid),
        },
        event_key=f"frame:{frame_digest}",
    )
    state = apply_graph_event(root, workspace_id, state, frame_event)
    frame_id = str(frame_event.payload["item"]["object_id"])
    relational, figures = V0.relational_state(grid, legal_count, ())
    entity_ids: dict[str, str] = {}
    for index, entity in enumerate(relational["entities"]):
        figure = figures[index] if index < len(figures) else None
        grounding: dict[str, Any] = {
            "frame_id": frame_id,
            "frame_index": frame_index,
            "local_component_ref": entity["id"],
            "bbox_origin_xy": entity.get("bounding_box_origin"),
        }
        if figure is not None:
            rows = [int(item[0]) for item in figure.normalized_cells]
            columns = [int(item[1]) for item in figure.normalized_cells]
            grounding.update(
                {
                    "anchor_rc": list(figure.anchor),
                    "bbox_height": max(rows) + 1 if rows else 0,
                    "bbox_width": max(columns) + 1 if columns else 0,
                    "mask_rle_rc": _mask_runs(figure.normalized_cells),
                    "mask_digest": LEDGER.stable_hash(figure.normalized_cells),
                }
            )
        event = EG.object_event(
            state,
            kind="entity",
            created_by="r2",
            identity={"frame": frame_id, "local_ref": entity["id"]},
            payload={**{key: value for key, value in entity.items() if key != "id"}, "grounding": grounding},
            dependency_ids=(frame_id,),
            event_key=f"region:{frame_digest}:{entity['id']}",
        )
        state = apply_graph_event(root, workspace_id, state, event)
        entity_ids[str(entity["id"])] = str(event.payload["item"]["object_id"])
    if relational["relations"]:
        dependencies = sorted(
            {
                entity_ids[item]
                for relation in relational["relations"]
                for item in relation["arguments"]
                if item in entity_ids
            }
        )
        event = EG.object_event(
            state,
            kind="relation_set",
            created_by="r2",
            identity={"frame": frame_id, "relation_set_digest": LEDGER.stable_hash(relational["relations"])},
            payload={"relations": relational["relations"], "frame_id": frame_id},
            dependency_ids=dependencies,
            event_key=f"relations:{frame_digest}",
        )
        state = apply_graph_event(root, workspace_id, state, event)
    return state, entity_ids, frame_id


def ingest_initial_graph(
    root: Path,
    workspace_id: str,
    state: Any,
    cognition: Any,
    grid: Grid,
    legal: Sequence[int],
) -> tuple[Any, dict[str, str]]:
    state, entity_ids, _frame_id = ingest_frame_objects(
        root,
        workspace_id,
        state,
        grid,
        frame_digest=LEDGER.stable_hash(grid),
        frame_index=0,
        legal_count=len(legal),
    )
    state = ingest_r2_workspace_objects(
        root,
        workspace_id,
        state,
        cognition,
        legal,
        observation_key="0",
        basis_ids=tuple(entity_ids.values()),
    )
    return state, entity_ids


def ingest_transition_graph(
    root: Path,
    workspace_id: str,
    state: Any,
    cognition: Any,
    *,
    transition_id: str,
    before_grid: Grid,
    after_grid: Grid,
    before_record: Mapping[str, Any],
    after_record: Mapping[str, Any],
    legal: Sequence[int],
    intervention_ref: str,
    judgments: Sequence[Mapping[str, str]] = (),
) -> Any:
    before_pixel_digest = LEDGER.stable_hash(before_grid)
    before_frame = next(
        (
            item.object_id
            for item in state.objects
            if item.kind == "frame" and item.payload.get("pixel_digest") == before_pixel_digest
        ),
        None,
    )
    state, entity_ids, after_frame = ingest_frame_objects(
        root,
        workspace_id,
        state,
        after_grid,
        frame_digest=str(after_record["digest"]),
        frame_index=int(after_record.get("levels_completed", 0)) * 10_000 + sum(item.kind == "frame" for item in state.objects),
        legal_count=len(legal),
    )
    transition_dependencies = tuple(value for value in (before_frame, after_frame) if value is not None)
    transition_event = EG.object_event(
        state,
        kind="transition",
        created_by="environment",
        identity={"transition_id": transition_id},
        payload={
            "before_frame": before_frame,
            "after_frame": after_frame,
            "intervention_ref": intervention_ref,
            "observation_changed": before_record.get("frame_sha256") != after_record.get("frame_sha256"),
        },
        dependency_ids=transition_dependencies,
        event_key=f"transition:{transition_id}",
    )
    state = apply_graph_event(root, workspace_id, state, transition_event)
    before_entities = {
        str(item.payload.get("grounding", {}).get("local_component_ref")): item.object_id
        for item in state.objects
        if item.kind == "entity" and before_frame in item.dependency_ids
    }
    before_figures = V0.V0.select_figures(before_grid)
    after_figures = V0.V0.select_figures(after_grid)
    correspondence = V0.V0.BASE.correspond(before_figures, after_figures)
    before_local = {figure: f"f{index:02d}" for index, figure in enumerate(before_figures)}
    after_local = {figure: f"f{index:02d}" for index, figure in enumerate(after_figures)}
    pairs = [
        {
            "before": before_entities[before_local[source]],
            "after": entity_ids[after_local[target]],
        }
        for source, target in correspondence.items()
        if before_local.get(source) in before_entities and after_local.get(target) in entity_ids
    ]
    if pairs:
        correspondence_dependencies = sorted(
            {
                str(transition_event.payload["item"]["object_id"]),
                *(value for pair in pairs for value in (pair["before"], pair["after"])),
            }
        )
        correspondence_event = EG.object_event(
            state,
            kind="correspondence_set",
            created_by="r2",
            identity={"transition_id": transition_id, "pairs_hash": LEDGER.stable_hash(pairs)},
            payload={"transition_id": transition_id, "pairs": pairs},
            dependency_ids=correspondence_dependencies,
            event_key=f"correspondence:{transition_id}",
        )
        state = apply_graph_event(root, workspace_id, state, correspondence_event)
    evidence = EG.ingest_environment_evidence(
        state,
        transition_id=transition_id,
        payload={
            "observation_changed": before_record.get("frame_sha256") != after_record.get("frame_sha256"),
            "level_delta": int(after_record.get("levels_completed", 0)) - int(before_record.get("levels_completed", 0)),
            "relations": V0.motion_relations(before_grid, after_grid),
        },
        judgments=judgments,
    )
    state = apply_ingest(root, workspace_id, evidence)
    return ingest_r2_workspace_objects(
        root,
        workspace_id,
        state,
        cognition,
        legal,
        observation_key=str(after_record["digest"]),
        basis_ids=tuple((*evidence.object_ids, *entity_ids.values(), str(transition_event.payload["item"]["object_id"]))),
    )


def template_from_schema_object(item: Any) -> Any | None:
    payload = item.payload
    consequence = payload.get("preferred_consequence", {})
    if consequence.get("measure") != "TranslationAlignmentResidual":
        return None
    if consequence.get("operator") not in {"Decrease", "Increase"}:
        return None
    arguments = consequence.get("arguments", [])
    conditions = [
        (str(value["predicate"]), tuple(str(arg) for arg in value["arguments"]))
        for value in payload.get("conditions", [])
    ]
    if len(arguments) != 2 or not conditions:
        return None
    identity = V0.V0.template_identity(conditions, str(consequence["operator"]), tuple(arguments))
    return V0.V0.Template(
        conditions=tuple(sorted(set(conditions))),
        operator=str(consequence["operator"]),
        effect_variables=tuple(arguments),
        canonical_hash=BASE.stable_hash(identity),
        provenance="externally-proposed",
    )


def task_states(events: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    output: dict[str, str] = {}
    for event in events:
        event_type = event["event_type"]
        if event_type == "QwenTaskQueued":
            output[str(event["payload"]["task_id"])] = "queued"
        elif event_type == "QwenTaskClaimed":
            output[str(event["payload"]["task_id"])] = "claimed"
        elif event_type == "QwenTaskCompleted":
            output[str(event["payload"]["task_id"])] = "completed"
        elif event_type == "QwenTaskAbandoned":
            output[str(event["payload"]["task_id"])] = "abandoned"
    return output


def orientation_path(root: Path) -> Path:
    return root / "qwen_orientation.json"


def read_orientation(root: Path, workspace_id: str) -> Any:
    if LEDGER.list_events(root):
        state, _events = graph_state(root)
        latest = QC.latest_orientation(state, workspace_id)
        if latest is not None:
            return latest
    path = orientation_path(root)
    if not path.exists():
        return QC.Orientation(workspace_id=workspace_id)
    return QC.orientation_from_document(
        json.loads(path.read_text(encoding="utf-8")), workspace_id=workspace_id
    )


def write_orientation(root: Path, value: Any) -> None:
    LEDGER.atomic_json(orientation_path(root), QC.orientation_document(value))


def visual_evidence_for_turn(root: Path, workspace_id: str) -> list[dict[str, str]]:
    events = LEDGER.list_events(root)
    history = _history(events, root)
    if history:
        latest = history[-1]
        transition_ref = f"vt:{LEDGER.stable_hash(latest['transition_event_id'])[:16]}"
        intervention_ref = opaque_intervention(workspace_id, int(latest["action_id"]), latest.get("data", {}))
        output = [
            {
                "label": f"IMMEDIATELY_PRECEDING_FRAME frame_ref=vf:{LEDGER.stable_hash(latest['before']['digest'])[:16]} transition_ref={transition_ref} intervention_ref={intervention_ref}",
                "data_url": grid_data_url(grid_value(latest["before_grid"])),
            },
            {
                "label": f"CURRENT_FRAME frame_ref=vf:{LEDGER.stable_hash(latest['after']['digest'])[:16]} transition_ref={transition_ref} role=after",
                "data_url": grid_data_url(grid_value(latest["after_grid"])),
            },
        ]
        if len(history) >= 9:
            candidates = history[:-1]
            salient = max(
                candidates,
                key=lambda item: (
                    int(item["after"].get("levels_completed", 0)) - int(item["before"].get("levels_completed", 0)),
                    sum(
                        left != right
                        for before_row, after_row in zip(item["before_grid"], item["after_grid"], strict=False)
                        for left, right in zip(before_row, after_row, strict=False)
                    ),
                    -int(item["index"]),
                ),
            )
            if salient["transition_event_id"] != latest["transition_event_id"]:
                output.append(
                    {
                        "label": f"HISTORICALLY_SALIENT_AFTER_FRAME frame_ref=vf:{LEDGER.stable_hash(salient['after']['digest'])[:16]} transition_ref=vt:{LEDGER.stable_hash(salient['transition_event_id'])[:16]} selection=structural-change",
                        "data_url": grid_data_url(grid_value(salient["after_grid"])),
                    }
                )
        return output
    initial = next(item for item in events if item["event_type"] == "InitialObservation")
    value = LEDGER.read_blob(root, initial["payload"]["observation_blob"])
    return [
        {
            "label": f"CURRENT_FRAME frame_ref=vf:{LEDGER.stable_hash(value['record']['digest'])[:16]} role=initial",
            "data_url": grid_data_url(grid_value(value["grid"])),
        }
    ]


def queue_qwen(
    root: Path,
    workspace_id: str,
    state: Any,
    graph_events: Sequence[Any],
    config: Mapping[str, Any],
    profile: Mapping[str, Any],
    fifo: Any,
    task_index: int,
) -> tuple[str, Any, Future[Any]]:
    orientation = read_orientation(root, workspace_id)
    request_id = f"qr:{LEDGER.stable_hash({'workspace': workspace_id, 'index': task_index})[:24]}"
    turn_budget = int(profile["frontier_token_budget"])
    turn = QC.build_turn(
        state,
        graph_events,
        orientation,
        request_id=request_id,
        token_budget=turn_budget,
        max_deltas=10_000,
        compact_ids=True,
    )
    request = QC.request_payload(
        turn,
        config["qwen"],
        visual_evidence=visual_evidence_for_turn(root, workspace_id),
    )
    request_blob = LEDGER.put_blob(root, request)
    turn_blob = LEDGER.put_blob(root, asdict(turn))
    task_id = LEDGER.stable_hash({"request": request_blob, "turn": turn_blob, "workspace": workspace_id})
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenTaskQueued",
        actor="coordinator",
        payload={"task_id": task_id, "request_blob": request_blob, "turn_blob": turn_blob, "basis_revision": state.revision},
        event_id=f"qwen-queued:{task_id}",
    )
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenTaskClaimed",
        actor="qwen",
        payload={"task_id": task_id, "queue": "global-fifo"},
        event_id=f"qwen-claimed:{task_id}",
    )
    return task_id, turn, fifo.submit(workspace_id, request)


def integrate_qwen(
    root: Path,
    workspace_id: str,
    state: Any,
    task_id: str,
    turn: Any,
    future: Future[Any],
    profile: Mapping[str, Any],
    *,
    action_count: int,
) -> tuple[Any, dict[str, Any]]:
    queue_result = future.result(timeout=660)
    response = queue_result.response
    response_blob = LEDGER.put_blob(root, response)
    compilation = QC.compile_response(response, turn)
    compilation_blob = LEDGER.put_blob(root, compilation)
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenTaskCompleted",
        actor="qwen",
        payload={
            "task_id": task_id,
            "queue_sequence": queue_result.sequence,
            "response_blob": response_blob,
            "compilation_blob": compilation_blob,
            "latency_s": response.get("latency_s"),
            "transport_error": response.get("transport_error"),
        },
        event_id=f"qwen-completed:{task_id}:{response_blob}",
    )
    state = apply_qwen_compilation(
        root,
        workspace_id,
        state,
        task_id,
        turn,
        compilation,
        profile,
        action_count=action_count,
    )
    return state, compilation


def apply_qwen_compilation(
    root: Path,
    workspace_id: str,
    state: Any,
    task_id: str,
    turn: Any,
    compilation: Mapping[str, Any],
    profile: Mapping[str, Any],
    *,
    action_count: int,
) -> Any:
    """Idempotently finish graph/orientation integration after a durable reply."""

    integrated_id = f"qwen-integrated:{task_id}"
    if any(item["event_id"] == integrated_id for item in LEDGER.list_events(root)):
        return state
    accepted = list(compilation.get("accepted", ()))

    def contribute_once(
        *, object_id: str, weight: int, channel: str, basis_ids: Sequence[str], contribution_key: str
    ) -> None:
        nonlocal state
        candidate = EG.make_attention(
            worker="qwen",
            object_id=object_id,
            weight=weight,
            channel=channel,
            basis_ids=basis_ids,
            created_revision=state.revision + 1,
            contribution_key=contribution_key,
        )
        if EG.has_attention(state, candidate.attention_id):
            return
        event = EG.attention_event(
            state,
            worker="qwen",
            object_id=object_id,
            weight=weight,
            channel=channel,
            basis_ids=basis_ids,
            contribution_key=contribution_key,
        )
        state = apply_graph_event(root, workspace_id, state, event)
    schemas = [item for item in accepted if item.get("kind") == "schema"]
    others = [item for item in accepted if item.get("kind") not in {"schema", "explanation", "attention"}]
    local_schema_ids: dict[str, str] = {}
    for item in schemas:
        situated = {
            **item,
            "payload": {**dict(item["payload"]), "eligible_step": action_count},
        }
        result = EG.ingest_qwen_writes(state, (situated,), response_id=f"{task_id}:{item['local_ref']}")
        state = apply_ingest(root, workspace_id, result)
        local_schema_ids[str(item["local_ref"])] = result.object_ids[0]
    for item in [value for value in accepted if value.get("kind") == "explanation"]:
        rewritten = dict(item)
        schema_ref = str(item.get("schema_ref"))
        dependency_ids = list(item.get("dependency_ids", ()))
        if schema_ref in local_schema_ids:
            dependency_ids.append(local_schema_ids[schema_ref])
            rewritten["schema_ref"] = local_schema_ids[schema_ref]
            rewritten["identity"] = {**dict(item["identity"]), "schema_ref": local_schema_ids[schema_ref]}
        rewritten["dependency_ids"] = sorted(set(dependency_ids))
        result = EG.ingest_qwen_writes(state, (rewritten,), response_id=f"{task_id}:{item['local_ref']}")
        state = apply_ingest(root, workspace_id, result)
    if others:
        state = apply_ingest(root, workspace_id, EG.ingest_qwen_writes(state, others, response_id=task_id))
    boost = max(1, min(100, int(round(32 * float(profile["proposal_attention_boost"])))))
    for object_id in local_schema_ids.values():
        contribute_once(
            object_id=object_id,
            weight=boost,
            channel="inspect",
            basis_ids=(),
            contribution_key=f"proposal:{task_id}:{object_id}",
        )
    for item in [value for value in accepted if value.get("kind") == "attention"]:
        contribute_once(
            object_id=str(item["object_id"]),
            weight=int(item["weight"]),
            channel=str(item["channel"]),
            basis_ids=tuple(item.get("basis_ids", ())),
            contribution_key=f"response:{task_id}:{item['object_id']}:{item['channel']}",
        )
    orientation = QC.advance_orientation(read_orientation(root, workspace_id), turn, compilation)
    orientation_spec = QC.orientation_object_spec(orientation)
    state, _orientation_id = ensure_graph_object(
        root,
        workspace_id,
        state,
        event_key=f"qwen-orientation:{task_id}",
        **orientation_spec,
    )
    write_orientation(root, orientation)
    LEDGER.append_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenTaskIntegrated",
        actor="coordinator",
        payload={"task_id": task_id, "graph_revision": state.revision, "action_count": action_count},
        event_id=integrated_id,
    )
    return state


def activate_visible_qwen(
    root: Path,
    workspace_id: str,
    state: Any,
    controller: Any,
    grid: Grid,
    legal: Sequence[int],
    history: Sequence[dict[str, Any]],
    profile: Mapping[str, Any],
    activated: set[str],
    action_count: int,
) -> tuple[Any, list[dict[str, Any]]]:
    frontier = EG.frontier(
        state,
        worker="r2",
        budget=int(profile["frontier_token_budget"]),
        root_limit=int(profile["frontier_root_limit"]),
    )
    visible = set(frontier.object_ids)
    previously_exposed = {
        item.object_id
        for item in state.attention
        if item.worker == "r2" and item.channel == "frontier-exposure"
    }
    noticed = record_frontier_pickups(
        state,
        worker="r2",
        object_ids=frontier.object_ids,
        previously_exposed_ids=tuple(previously_exposed),
        exposure_key=f"r2-frontier:{action_count}",
    )
    if noticed.events:
        commit_graph_events(root, workspace_id, noticed.events)
        state = noticed.state
    relation_state, figures = V0.relational_state(grid, len(legal), history)
    records: list[dict[str, Any]] = []
    derivations_by_target: dict[str, list[Any]] = {}
    for derivation in EG.find_objects(state, kind="qwen_derivation", created_by="qwen"):
        for dependency in derivation.dependency_ids:
            derivations_by_target.setdefault(dependency, []).append(derivation)

    def criticize(schema_object_id: str, status: str, detail: Mapping[str, Any]) -> str:
        nonlocal state
        normalized_status = {
            "ambiguous": "ambiguous-grounding",
            "active-zero-evidence": "rejected",
        }.get(status, status)
        existing_criticism = matching_structured_criticism(
            state,
            worker="r2",
            target_id=schema_object_id,
            status=normalized_status,
            witness=detail,
        )
        if existing_criticism is not None:
            return existing_criticism.object_id
        result = EG.ingest_structured_criticism(
            state,
            worker="r2",
            target_id=schema_object_id,
            status=normalized_status,
            criticism_key=f"{schema_object_id}:{action_count}:{normalized_status}",
            payload={
                "observation_digest": LEDGER.stable_hash(grid),
                "structured_witness": dict(detail),
                "empirical_support_delta": 0,
            },
        )
        state = apply_ingest(root, workspace_id, result)
        criticism_id = result.object_ids[0]
        attention = EG.attention_event(
            state,
            worker="r2",
            object_id=criticism_id,
            weight=12,
            channel="inspect",
            basis_ids=(schema_object_id,),
            contribution_key=f"criticism-attention:{schema_object_id}:{action_count}:{status}",
        )
        state = apply_graph_event(root, workspace_id, state, attention)
        return criticism_id

    for item in EG.find_objects(state, kind="schema", created_by="qwen"):
        if item.object_id not in visible or item.object_id in activated:
            continue
        eligible_steps = [
            int(value.payload.get("call_local_payload", {}).get("eligible_step"))
            for value in derivations_by_target.get(item.object_id, ())
            if value.payload.get("call_local_payload", {}).get("eligible_step") is not None
        ]
        eligible_action = min(eligible_steps, default=action_count)
        if action_count - eligible_action > int(profile["attention_half_life_actions"]):
            continue
        template = template_from_schema_object(item)
        if template is None:
            activated.add(item.object_id)
            criticism_id = criticize(
                item.object_id,
                "unsupported-potential",
                {
                    "accepted_measure": "TranslationAlignmentResidual",
                    "accepted_operators": ["Decrease", "Increase"],
                    "received_consequence": item.payload.get("preferred_consequence", {}),
                },
            )
            records.append({"schema_object_id": item.object_id, "status": "unsupported-potential", "criticism_id": criticism_id})
            continue
        grounding = controller.activate(
            template,
            relation_state,
            figures,
            action_count=action_count,
            source_task=item.object_id,
        )
        if grounding["status"] in {"ambiguous", "unbound"}:
            grounding = {
                **grounding,
                **AMBIGUITY.compile_ambiguity_witness(template, relation_state),
            }
        record = {"schema_object_id": item.object_id, "template_hash": template.canonical_hash, **grounding}
        records.append(record)
        if grounding["status"] in {"bound", "duplicate-active"}:
            activated.add(item.object_id)
        if grounding["status"] in {"bound", "duplicate-active"}:
            binding_result = EG.ingest_groundings(
                state,
                ({
                    "binding_key": f"{item.object_id}:{action_count}:{grounding['status']}",
                    "payload": {**record, "legal_count": len(legal)},
                    "dependency_ids": [item.object_id],
                },),
                source="r2",
            )
            state = apply_ingest(root, workspace_id, binding_result)
            pickup = next(
                (value for value in reversed(state.pickups) if value.direction == "qwen->r2" and value.object_id == item.object_id),
                None,
            )
            if pickup is not None:
                event = EG.grounded_pickup_event(
                    state,
                    pickup_id=pickup.pickup_id,
                    downstream_object_id=binding_result.object_ids[0],
                    worker="r2",
                    payload={"grounding_status": grounding["status"]},
                )
                state = apply_graph_event(root, workspace_id, state, event)
        else:
            record["criticism_id"] = criticize(item.object_id, str(grounding["status"]), grounding)
    return state, records


def activate_then_maybe_queue_qwen(
    root: Path,
    workspace_id: str,
    state: Any,
    graph_events: Sequence[Any],
    pending_qwen: tuple[str, Any, Future[Any]] | None,
    *,
    live_qwen: bool,
    controller: Any,
    grid: Grid,
    legal: Sequence[int],
    history: Sequence[dict[str, Any]],
    profile: Mapping[str, Any],
    activated: set[str],
    config: Mapping[str, Any],
    fifo: Any,
    task_count: int,
) -> tuple[Any, Sequence[Any], tuple[str, Any, Future[Any]] | None, int, list[dict[str, Any]]]:
    """Durably adjudicate the current proposal before constructing its successor turn."""

    records: list[dict[str, Any]] = []
    if live_qwen:
        state, records = activate_visible_qwen(
            root,
            workspace_id,
            state,
            controller,
            grid,
            legal,
            history,
            profile,
            activated,
            len(history),
        )
    triggers = {int(item) for item in config["qwen"]["trigger_action_counts"]}
    if (
        live_qwen
        and pending_qwen is None
        and len(history) in triggers
        and task_count < int(config["qwen"]["max_calls_per_episode"])
    ):
        # Re-read only after activation returns: binding, structured criticism,
        # and grounded-pickup events are fsync-durable before this turn's basis.
        state, graph_events = graph_state(root)
        pending_qwen = queue_qwen(
            root,
            workspace_id,
            state,
            graph_events,
            config,
            profile,
            fifo,
            task_count,
        )
        task_count += 1
    return state, graph_events, pending_qwen, task_count, records


def _history(events: Sequence[Mapping[str, Any]], root: Path) -> list[dict[str, Any]]:
    by_id = {str(item["event_id"]): item for item in events}
    output = []
    for event in events:
        if event["event_type"] != "TransitionCommitted":
            continue
        payload = event["payload"]
        pending = by_id[str(payload["pending_event_id"])]["payload"]
        before = LEDGER.read_blob(root, str(payload["before_blob"]))
        after = LEDGER.read_blob(root, str(payload["after_blob"]))
        output.append(
            {
                "index": len(output),
                "action_id": int(pending["action_id"]),
                "data": dict(pending.get("data", {})),
                "before": before["record"],
                "after": after["record"],
                "before_grid": before["grid"],
                "after_grid": after["grid"],
                "transition_event_id": event["event_id"],
            }
        )
    return output


def rebuild_controller(root: Path, initial_grid: Grid, legal: Sequence[int]) -> tuple[Any, Any, list[dict[str, Any]], set[str]]:
    cognition = V0.R2Cognition(initial_grid)
    controller = V0.WorkspaceController()
    history: list[dict[str, Any]] = []
    activated: set[str] = set()
    schemas: dict[str, Any] = {}
    current_grid = initial_grid
    current_legal = tuple(legal)
    events = LEDGER.list_events(root)
    by_id = {str(item["event_id"]): item for item in events}
    for event in events:
        if event["event_type"] == "EpistemicGraphEvent":
            graph_event = EG.event_from_document(LEDGER.read_blob(root, event["payload"]["graph_event_blob"]))
            raw = _object_payload(graph_event)
            if raw and raw["created_by"] == "qwen" and raw["kind"] == "schema":
                obj = EG._object_from_document(raw)
                template = template_from_schema_object(obj)
                if template is not None:
                    schemas[obj.object_id] = template
            if raw and raw["created_by"] == "r2" and raw["kind"] == "binding":
                obj = EG._object_from_document(raw)
                dependency = next((item for item in obj.dependency_ids if item in schemas), None)
                if dependency is not None and dependency not in activated:
                    relation_state, figures = V0.relational_state(current_grid, len(current_legal), history)
                    controller.activate(schemas[dependency], relation_state, figures, action_count=len(history), source_task=dependency)
                    activated.add(dependency)
            if raw and raw["created_by"] == "r2" and raw["kind"] == "structured_criticism":
                obj = EG._object_from_document(raw)
                dependency = next((item for item in obj.dependency_ids if item in schemas), None)
                if dependency is not None and obj.payload.get("status") == "unsupported-potential":
                    activated.add(dependency)
        elif event["event_type"] == "TransitionCommitted":
            payload = event["payload"]
            pending_event = by_id[str(payload["pending_event_id"])]
            before_blob = LEDGER.read_blob(root, str(payload["before_blob"]))
            after_blob = LEDGER.read_blob(root, str(payload["after_blob"]))
            after_grid = grid_value(after_blob["grid"])
            action_id = int(pending_event["payload"]["action_id"])
            controller.observe(action_id, current_grid, after_grid)
            cognition.observe_transition(action_id, after_grid)
            history.append(
                {
                    "index": len(history),
                    "action_id": action_id,
                    "data": dict(pending_event["payload"].get("data", {})),
                    "before": before_blob["record"],
                    "after": after_blob["record"],
                    "before_grid": before_blob["grid"],
                    "after_grid": after_blob["grid"],
                    "transition_event_id": event["event_id"],
                }
            )
            current_grid = after_grid
            current_legal = tuple(int(item) for item in after_blob["record"].get("available_actions", current_legal))
    return cognition, controller, history, activated


def open_replayed(root: Path, game: str, environments: Path, recordings: Path) -> tuple[Any, Any, Any]:
    arcade, environment = BASE.open_environment(environments, recordings, game)
    observation = environment.observation_space
    if observation is None:
        observation = environment.reset()
    if observation is None:
        arcade.close_scorecard()
        raise RuntimeError("ARC produced no initial observation")
    by_id = {str(item["event_id"]): item for item in LEDGER.list_events(root)}
    for event in LEDGER.list_events(root):
        if event["event_type"] != "TransitionCommitted":
            continue
        payload = event["payload"]
        before = BASE.observation_record(observation)
        if before["digest"] != payload["before_digest"]:
            arcade.close_scorecard()
            raise RuntimeError("replay predecessor mismatch")
        pending = by_id[str(payload["pending_event_id"])]["payload"]
        observation = execute_action(environment, game, pending["action_id"], pending.get("data", {}), "checkpoint-replay")
        if BASE.observation_record(observation)["digest"] != payload["after_digest"]:
            arcade.close_scorecard()
            raise RuntimeError("replay successor mismatch")
    return arcade, environment, observation


def verify_replay(root: Path, game: str, environments: Path, recordings: Path) -> bool:
    arcade, _environment, observation = open_replayed(root, game, environments, recordings)
    try:
        transitions = sum(item["event_type"] == "TransitionCommitted" for item in LEDGER.list_events(root))
        return transitions >= 0 and observation is not None
    except Exception:
        return False
    finally:
        arcade.close_scorecard()


def _job_key(game: str, arm: str, profile_id: str, config: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    return LEDGER.stable_hash(
        {
            "protocol": config["workspace_protocol"],
            "game": game,
            "arm": arm,
            "profile": profile_id,
            "config": config,
            "manifest_digest": manifest["manifest_digest"],
            "code": {name: LEDGER.file_hash(HERE / name) for name in ("experiment.py", "ledger.py", "epistemic_graph.py", "qwen_cognition.py", "census.py")},
        }
    )


def run_episode(payload: Mapping[str, Any], fifo: Any | None = None) -> dict[str, Any]:
    game = str(payload["game"])
    arm = str(payload["arm_id"])
    profile_id = str(payload["profile_id"])
    config = dict(payload["config"])
    manifest = dict(payload["manifest"])
    profile = dict(config["profiles"][profile_id])
    environments = Path(payload.get("environments", CENSUS.DEFAULT_ENVIRONMENTS))
    workspace_id = f"{profile_id}--{game}--{arm}"
    root = ARTIFACTS / "workspaces" / workspace_id
    result_path = ARTIFACTS / "results" / f"{workspace_id}.json"
    job_key = _job_key(game, arm, profile_id, config, manifest)
    existing = LEDGER.list_events(root)
    if existing:
        start = existing[0]
        if start["event_type"] != "WorkspaceStarted" or start["payload"].get("job_key") != job_key:
            raise RuntimeError(f"incompatible checkpoint: {workspace_id}")
        if existing[-1]["event_type"] == "WorkspaceStopped" and result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))
        for task_id, status in task_states(existing).items():
            if status in {"queued", "claimed"}:
                LEDGER.append_event(root, workspace_id=workspace_id, event_type="QwenTaskAbandoned", actor="coordinator", payload={"task_id": task_id, "reason": "resume-orphan"})
    else:
        LEDGER.append_event(root, workspace_id=workspace_id, event_type="WorkspaceStarted", actor="coordinator", payload={"job_key": job_key, "game": game, "arm": arm, "profile": profile_id})

    recording_dir = ARTIFACTS / "recordings" / workspace_id / f"resume-{len(existing):05d}"
    if existing:
        arcade, environment, observation = open_replayed(root, game, environments, recording_dir)
    else:
        arcade, environment = BASE.open_environment(environments, recording_dir, game)
        observation = environment.observation_space
        if observation is None:
            observation = environment.reset()
        if observation is None:
            arcade.close_scorecard()
            raise RuntimeError("ARC produced no initial observation")
        blob, record, _grid = store_observation(root, observation)
        LEDGER.append_event(root, workspace_id=workspace_id, event_type="InitialObservation", actor="environment", payload={"observation_blob": blob, "digest": record["digest"], "levels_completed": record["levels_completed"]})

    events = LEDGER.list_events(root)
    initial_event = next(item for item in events if item["event_type"] == "InitialObservation")
    initial_blob = LEDGER.read_blob(root, initial_event["payload"]["observation_blob"])
    initial_grid = grid_value(initial_blob["grid"])
    legal = BASE.simple_legal_actions(environment, observation)
    cognition, controller, history, activated = rebuild_controller(root, initial_grid, legal)
    state, graph_events = graph_state(root)
    initial_graph_complete = any(
        item.kind == "runtime_summary" and item.identity.get("observation_key") == "0"
        for item in state.objects
    )
    if not initial_graph_complete:
        state, _entities = ingest_initial_graph(root, workspace_id, state, cognition, initial_grid, legal)
        state, graph_events = graph_state(root)

    # A reply is durable before its graph writes.  Finish any interrupted
    # integration from stored turn/compilation blobs; never call Qwen again.
    outer_events = LEDGER.list_events(root)
    queued_by_task = {
        str(item["payload"]["task_id"]): item
        for item in outer_events
        if item["event_type"] == "QwenTaskQueued"
    }
    integrated_tasks = {
        str(item["payload"]["task_id"])
        for item in outer_events
        if item["event_type"] == "QwenTaskIntegrated"
    }
    for completed in (
        item
        for item in outer_events
        if item["event_type"] == "QwenTaskCompleted"
        and str(item["payload"]["task_id"]) not in integrated_tasks
    ):
        task_id = str(completed["payload"]["task_id"])
        turn_value = LEDGER.read_blob(root, queued_by_task[task_id]["payload"]["turn_blob"])
        turn = QC.CognitionTurn(**turn_value)
        compilation = LEDGER.read_blob(root, completed["payload"]["compilation_blob"])
        state = apply_qwen_compilation(
            root,
            workspace_id,
            state,
            task_id,
            turn,
            compilation,
            profile,
            action_count=len(history),
        )
    state = repair_grounded_pickup_edges(root, workspace_id, state)

    pending = LEDGER.pending_action(LEDGER.list_events(root))
    if pending is not None:
        before_blob = pending["payload"]["before_blob"]
        before = LEDGER.read_blob(root, before_blob)
        if BASE.observation_record(observation)["digest"] != pending["payload"]["before_digest"]:
            arcade.close_scorecard()
            raise RuntimeError("pending predecessor mismatch")
        successor = execute_action(environment, game, pending["payload"]["action_id"], pending["payload"].get("data", {}), "pending-recovery")
        after_blob, after_record, after_grid = store_observation(root, successor)
        transition = LEDGER.append_event(root, workspace_id=workspace_id, event_type="TransitionCommitted", actor="environment", payload={"pending_event_id": pending["event_id"], "before_blob": before_blob, "after_blob": after_blob, "before_digest": pending["payload"]["before_digest"], "after_digest": after_record["digest"], "action_id": pending["payload"]["action_id"], "levels_completed": after_record["levels_completed"]})
        controller.observe(int(pending["payload"]["action_id"]), grid_value(before["grid"]), after_grid)
        cognition.observe_transition(int(pending["payload"]["action_id"]), after_grid)
        history = _history(LEDGER.list_events(root), root)
        state = ingest_transition_graph(root, workspace_id, state, cognition, transition_id=transition["event_id"], before_grid=grid_value(before["grid"]), after_grid=after_grid, before_record=before["record"], after_record=after_record, legal=BASE.simple_legal_actions(environment, successor), intervention_ref=opaque_intervention(workspace_id, int(pending["payload"]["action_id"]), pending["payload"].get("data", {})))
        observation = successor

    live_qwen = arm == "shared_attention_qwen"
    if live_qwen and fifo is None:
        raise RuntimeError("shared arm requires the single resident FIFO")
    pending_qwen: tuple[str, Any, Future[Any]] | None = None
    task_count = sum(value in {"completed", "abandoned"} for value in task_states(LEDGER.list_events(root)).values())
    started = time.perf_counter()
    stop_reason = "action-budget"
    qwen_compilations: list[dict[str, Any]] = []
    grounding_records: list[dict[str, Any]] = []
    try:
        while len(history) < int(config["action_budget"]):
            before_record, grid = observation_value(observation)
            if int(before_record["levels_completed"]) >= 1:
                stop_reason = "first-level-completed"
                break
            legal = BASE.simple_legal_actions(environment, observation)
            if not legal:
                stop_reason = "complex-only-epistemic-abstention"
                break

            if pending_qwen is not None and len(history) in {8, 16, 24, 32}:
                state, compilation = integrate_qwen(root, workspace_id, state, *pending_qwen, profile, action_count=len(history))
                qwen_compilations.append(compilation)
                pending_qwen = None

            state, graph_events, pending_qwen, task_count, records = (
                activate_then_maybe_queue_qwen(
                    root,
                    workspace_id,
                    state,
                    graph_events,
                    pending_qwen,
                    live_qwen=live_qwen,
                    controller=controller,
                    grid=grid,
                    legal=legal,
                    history=history,
                    profile=profile,
                    activated=activated,
                    config=config,
                    fifo=fifo,
                    task_count=task_count,
                )
            )
            grounding_records.extend(records)

            decision = controller.choose(legal)
            decision_document = {
                "decision": asdict(decision),
                "same_state_no_qwen_action": decision.fallback_action_id,
                "qwen_changed_action": decision.action_id != decision.fallback_action_id,
                "controller": controller.report(),
            }
            decision_blob = LEDGER.put_blob(root, decision_document)
            LEDGER.append_event(root, workspace_id=workspace_id, event_type="ActionDecision", actor="r2", payload={"decision_blob": decision_blob, "observation_digest": before_record["digest"]})
            before_blob = LEDGER.put_blob(root, {"record": before_record, "grid": [list(row) for row in grid]})
            pending_event = LEDGER.append_event(root, workspace_id=workspace_id, event_type="ActionPending", actor="arbiter", payload={"before_blob": before_blob, "before_digest": before_record["digest"], "action_id": decision.action_id, "data": {}, "decision_blob": decision_blob})
            successor = execute_action(environment, game, decision.action_id, {}, decision.reason)
            after_blob, after_record, after_grid = store_observation(root, successor)
            learning = controller.observe(decision.action_id, grid, after_grid)
            cognition.observe_transition(decision.action_id, after_grid)
            transition = LEDGER.append_event(root, workspace_id=workspace_id, event_type="TransitionCommitted", actor="environment", payload={"pending_event_id": pending_event["event_id"], "before_blob": before_blob, "after_blob": after_blob, "before_digest": before_record["digest"], "after_digest": after_record["digest"], "action_id": decision.action_id, "levels_completed": after_record["levels_completed"]})
            judgments: list[dict[str, str]] = []
            if decision.prior_used and decision.template_hash is not None:
                observed = next(
                    (
                        item
                        for item in learning.get("bindings", ())
                        if item.get("direct") and item.get("template_hash") == decision.template_hash
                    ),
                    None,
                )
                active_binding = next(
                    (item for item in controller.inner.bindings if item.template_hash == decision.template_hash),
                    None,
                )
                observed_improvement = (
                    observed is not None
                    and active_binding is not None
                    and decision.residual_before is not None
                    and (
                        int(observed["residual"]) < int(decision.residual_before)
                        if active_binding.operator == "Decrease"
                        else int(observed["residual"]) > int(decision.residual_before)
                    )
                )
                if observed_improvement:
                    for item in state.objects:
                        if item.kind == "binding" and item.payload.get("template_hash") == decision.template_hash:
                            judgments.append({"kind": "supports", "target_id": item.object_id})
            next_legal = BASE.simple_legal_actions(environment, successor)
            state = ingest_transition_graph(root, workspace_id, state, cognition, transition_id=transition["event_id"], before_grid=grid, after_grid=after_grid, before_record=before_record, after_record=after_record, legal=next_legal, intervention_ref=opaque_intervention(workspace_id, decision.action_id), judgments=judgments)
            history = _history(LEDGER.list_events(root), root)
            observation = successor
            progress = {
                "status": "running",
                "game": game,
                "arm_id": arm,
                "profile_id": profile_id,
                "actions": len(history),
                "levels_completed": int(after_record["levels_completed"]),
                "graph_metrics": EG.metrics(state),
                "qwen_tasks": task_states(LEDGER.list_events(root)),
            }
            LEDGER.atomic_json(ARTIFACTS / "progress" / f"{workspace_id}.json", progress)
            LEDGER.write_cursor(root, "environment", ledger_seq=LEDGER.list_events(root)[-1]["seq"], graph_revision=state.revision, metadata={"actions": len(history)})
            if int(after_record["levels_completed"]) >= 1:
                stop_reason = "first-level-completed"
                break

        if pending_qwen is not None:
            state, compilation = integrate_qwen(root, workspace_id, state, *pending_qwen, profile, action_count=len(history))
            qwen_compilations.append(compilation)
            pending_qwen = None
            legal = BASE.simple_legal_actions(environment, observation)
            state, records = activate_visible_qwen(root, workspace_id, state, controller, BASE.observation_grid(observation), legal, history, profile, activated, len(history))
            grounding_records.extend(records)
    finally:
        arcade.close_scorecard()

    final_record = BASE.observation_record(observation)
    replay_verified = verify_replay(root, game, environments, ARTIFACTS / "recordings" / workspace_id / "verification")
    events = LEDGER.list_events(root)
    decision_docs = [LEDGER.read_blob(root, item["payload"]["decision_blob"]) for item in events if item["event_type"] == "ActionDecision"]
    completed_tasks = [item for item in events if item["event_type"] == "QwenTaskCompleted"]
    queued_tasks = [item for item in events if item["event_type"] == "QwenTaskQueued"]
    response_documents = [LEDGER.read_blob(root, item["payload"]["response_blob"]) for item in completed_tasks]
    usages = []
    for document in response_documents:
        try:
            envelope = json.loads(document.get("raw_body") or "{}")
            usages.append(dict(envelope.get("usage", {})))
        except (TypeError, json.JSONDecodeError):
            usages.append({})
    turn_documents = [LEDGER.read_blob(root, item["payload"]["turn_blob"]) for item in queued_tasks]
    context_metrics = {
        "calls": len(completed_tasks),
        "prompt_tokens": sum(int(item.get("prompt_tokens", 0)) for item in usages),
        "completion_tokens": sum(int(item.get("completion_tokens", 0)) for item in usages),
        "max_prompt_tokens": max((int(item.get("prompt_tokens", 0)) for item in usages), default=0),
        "max_context_occupancy_fraction": max(
            (
                float(item.get("prompt_tokens", 0))
                / int(config["qwen"].get("context_window_tokens", 8192))
                for item in usages
            ),
            default=0.0,
        ),
        "latency_s": sum(float(item.get("latency_s") or 0.0) for item in response_documents),
        "transport_errors": sum(bool(item.get("transport_error")) for item in response_documents),
        "initial_full_object_count": initial_full_object_count(turn_documents),
        "sparse_cut_object_counts": [len(item["document"]["sparse_cut"]["objects"]) for item in turn_documents],
        "sparse_cut_estimated_tokens": [int(item["document"]["sparse_cut"]["used_tokens"]) for item in turn_documents],
        "delta_counts": [len(item["document"]["ordered_lossless_deltas"]) for item in turn_documents],
        "alias_counts": [len(item.get("id_aliases", ())) for item in turn_documents],
    }
    support_authority_violations = sum(
        item.kind in {"supports", "refutes", "invalidates"} and item.created_by != "environment"
        for item in state.edges
    )
    grounded_entities = [item for item in state.objects if item.kind == "entity" and item.payload.get("grounding", {}).get("frame_id")]
    open_ports = sum(
        len(item.payload.get("open_ports", ()))
        for item in state.objects
        if item.kind == "explanation" and item.created_by == "qwen"
    )
    result = {
        "protocol": config["workspace_protocol"],
        "game": game,
        "arm_id": arm,
        "profile_id": profile_id,
        "job_key": job_key,
        "initial_digest": initial_blob["record"]["digest"],
        "actions": len(history),
        "action_sequence": [int(item["action_id"]) for item in history],
        "levels_completed": int(final_record["levels_completed"]),
        "first_level_completed": int(final_record["levels_completed"]) >= 1,
        "stop_reason": stop_reason,
        "final_digest": final_record["digest"],
        "replay_verified": replay_verified,
        "graph_metrics": EG.metrics(state),
        "qwen_task_statuses": dict(sorted(Counter(task_states(events).values()).items())),
        "qwen_compilation_count": len(qwen_compilations),
        "qwen_valid_compilations": sum(bool(item.get("valid_json_contract")) for item in qwen_compilations),
        "qwen_accepted_writes": sum(len(item.get("accepted", ())) for item in qwen_compilations),
        "groundings": grounding_records,
        "qwen_changed_decisions": sum(bool(item.get("qwen_changed_action")) for item in decision_docs),
        "prior_decisions": sum(bool(item.get("decision", {}).get("prior_used")) for item in decision_docs),
        "qwen_context": context_metrics,
        "qwen_calls": context_metrics["calls"],
        "qwen_total_tokens": context_metrics["prompt_tokens"] + context_metrics["completion_tokens"],
        "qwen_reply_latency_s": context_metrics["latency_s"],
        "qwen_context_valid": (
            context_metrics["max_prompt_tokens"] + int(config["qwen"].get("max_tokens", 0))
            <= int(config["qwen"].get("context_window_tokens", 8192))
        ),
        "qwen_transport_successful": context_metrics["transport_errors"] == 0,
        "visual_grounding": {
            "frame_objects": sum(item.kind == "frame" for item in state.objects),
            "transition_objects": sum(item.kind == "transition" for item in state.objects),
            "grounded_region_objects": len(grounded_entities),
            "qwen_open_ports": open_ports,
        },
        "support_authority_violations": support_authority_violations,
        "elapsed_s": time.perf_counter() - started,
        "workspace_head": events[-1]["event_hash"],
    }
    LEDGER.append_event(root, workspace_id=workspace_id, event_type="WorkspaceStopped", actor="coordinator", payload={"reason": stop_reason, "result_hash": LEDGER.stable_hash(result)})
    LEDGER.atomic_json(result_path, result)
    LEDGER.atomic_json(ARTIFACTS / "progress" / f"{workspace_id}.json", {**result, "status": "completed"})
    return result


def write_failed_progress(
    job: Mapping[str, Any],
    error: str,
    *,
    classification: Mapping[str, Any] | None = None,
    status: str = "failed",
) -> dict[str, Any]:
    """Atomically expose a terminal job failure without losing prior progress."""

    workspace_id = f"{job['profile_id']}--{job['game']}--{job['arm_id']}"
    path = ARTIFACTS / "progress" / f"{workspace_id}.json"
    existing: dict[str, Any] = {}
    if path.exists():
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                existing = value
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            pass
    failed = {
        **existing,
        "game": str(job["game"]),
        "profile_id": str(job["profile_id"]),
        "arm_id": str(job["arm_id"]),
        "status": status,
        "error": str(error),
    }
    if classification is not None:
        failed["failure_classification"] = dict(classification)
    LEDGER.atomic_json(path, failed)
    LEDGER.atomic_json(ARTIFACTS / "results" / f"{workspace_id}.json", failed)
    return failed


def classify_census_failure(
    error: BaseException | None = None,
    *,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Classify the small, explicit set of failures that invalidate the census.

    Ordinary environment, transport, controller, and job-local exceptions are
    isolated to their job.  Cancellation is reserved for evidence that the
    experiment's shared integrity assumptions are themselves broken.
    """

    if result is not None and int(result.get("support_authority_violations", 0)) > 0:
        return {
            "scope": "global",
            "category": "support_authority_violation",
            "request_cancellation": True,
        }
    if error is None:
        return None
    message = str(error).lower()
    if isinstance(error, LEDGER.LedgerError) and any(
        marker in message
        for marker in (
            "corrupt",
            "digest mismatch",
            "hash mismatch",
            "chain is not contiguous",
            "workspace id changed",
            "workspace id mismatch",
            "duplicate event id",
            "contract mismatch",
            "head exists without events",
            "batch metadata mismatch",
            "event id reused with different content",
        )
    ):
        return {
            "scope": "global",
            "category": "ledger_integrity_violation",
            "request_cancellation": True,
        }
    if isinstance(error, EG.EpistemicGraphError) and any(
        marker in message
        for marker in (
            "assert empirical support",
            "attempts to assert support",
            "attempts to assert empirical support",
            "support-changing edge requires environment evidence authority",
            "evidence authority",
            "hash mismatch",
            "hash-chain",
            "stable object id collision",
        )
    ):
        category = "support_authority_violation" if any(
            marker in message
            for marker in (
                "assert empirical support",
                "attempts to assert support",
                "attempts to assert empirical support",
                "support-changing edge requires environment evidence authority",
                "evidence authority",
            )
        ) else "graph_integrity_violation"
        return {"scope": "global", "category": category, "request_cancellation": True}
    if any(
        marker in message
        for marker in (
            "replay predecessor mismatch",
            "replay successor mismatch",
            "cross-workspace",
            "workspace leakage",
            "cross-workspace leakage",
        )
    ):
        return {
            "scope": "global",
            "category": "replay_or_workspace_invariant",
            "request_cancellation": True,
        }
    return {"scope": "job", "category": "independent_job_failure", "request_cancellation": False}


def census_counts(
    *,
    total: int,
    results: Sequence[Mapping[str, Any]],
    failures: Sequence[Mapping[str, Any]],
    cancelled: Sequence[Mapping[str, Any]],
) -> dict[str, int]:
    global_failures = sum(
        item.get("failure_classification", {}).get("scope") == "global"
        for item in failures
    )
    return {
        "total": int(total),
        "completed": len(results),
        "failed": len(failures),
        "cancelled": len(cancelled),
        "independent_job_failures": len(failures) - global_failures,
        "global_invariant_failures": global_failures,
    }


def initial_full_object_count(turn_documents: Sequence[Mapping[str, Any]]) -> int:
    """Count initial residency under compact and legacy turn encodings."""

    for turn in turn_documents:
        document = turn.get("document", {})
        materialization = document.get("full_materialization")
        if not isinstance(materialization, Mapping):
            continue
        object_index = document.get("object_index")
        if isinstance(object_index, Mapping) and isinstance(object_index.get("ids"), list):
            return len(object_index["ids"])
        objects = materialization.get("objects")
        if isinstance(objects, list):
            return len(objects)
    return 0


def run_census(config: Mapping[str, Any], manifest: Mapping[str, Any], *, games: Sequence[str] | None = None, profiles: Sequence[str] | None = None) -> dict[str, Any]:
    selected_games = tuple(games or config["games"])
    selected_profiles = tuple(profiles or config["profiles"])
    jobs = [
        {"game": game, "profile_id": profile_id, "arm_id": arm, "config": dict(config), "manifest": dict(manifest)}
        for profile_id in selected_profiles
        for game in selected_games
        for arm in config["arms"]
    ]
    fifo = QC.ResidentServerQueue(config["qwen"]["endpoint"], timeout=650)
    results: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    cancelled: list[dict[str, Any]] = []
    cancellation_requested = False
    append_status(f"\n## {time.strftime('%Y-%m-%d %H:%M:%S')} — live census launched\n\n- Jobs: {len(jobs)}; games: {len(selected_games)}; profiles: {len(selected_profiles)}; environment workers: {config['max_parallel_arc_workers']}.\n")
    try:
        with ThreadPoolExecutor(max_workers=int(config["max_parallel_arc_workers"]), thread_name_prefix="arc-census") as pool:
            futures = {pool.submit(run_episode, job, fifo): job for job in jobs}
            for future in as_completed(futures):
                job = futures[future]
                if future.cancelled():
                    classification = {
                        "scope": "job",
                        "category": "cancelled_after_global_invariant",
                        "request_cancellation": False,
                    }
                    failure = {
                        **job,
                        "status": "cancelled",
                        "error": "CancelledError: census-wide integrity cancellation",
                        "failure_classification": classification,
                    }
                    write_failed_progress(
                        job,
                        failure["error"],
                        classification=classification,
                        status="cancelled",
                    )
                    cancelled.append(failure)
                    counts = census_counts(total=len(jobs), results=results, failures=failures, cancelled=cancelled)
                    LEDGER.atomic_json(
                        ARTIFACTS / "PARTIAL_RESULTS.json",
                        {
                            **counts,
                            "counts": counts,
                            "results": sorted(results, key=lambda item: (item['profile_id'], item['game'], item['arm_id'])),
                            "failures": failures,
                            "cancelled_jobs": cancelled,
                            "cancellation_requested": cancellation_requested,
                        },
                    )
                    continue
                result: Mapping[str, Any] | None = None
                try:
                    result = future.result()
                    classification = classify_census_failure(result=result)
                    if classification is not None:
                        raise RuntimeError(
                            f"support authority violations reported: {result['support_authority_violations']}"
                        )
                    results.append(result)
                    append_status(f"- COMPLETE `{result['profile_id']}/{result['game']}/{result['arm_id']}`: levels={result['levels_completed']}, actions={result['actions']}, Q→R grounded={result['graph_metrics'].get('grounded_pickup_directions', {}).get('qwen->r2', 0)}, replay={result['replay_verified']}.")
                except CancelledError:
                    # ``future.cancelled`` is normally caught above; retain a
                    # defensive branch for Future implementations with races.
                    classification = {"scope": "job", "category": "cancelled_after_global_invariant", "request_cancellation": False}
                    failure = {**job, "status": "cancelled", "error": "CancelledError: census-wide integrity cancellation", "failure_classification": classification}
                    write_failed_progress(job, failure["error"], classification=classification, status="cancelled")
                    cancelled.append(failure)
                except Exception as error:
                    classification = classify_census_failure(error)
                    assert classification is not None
                    # A completed result can reveal an authority violation;
                    # preserve that stronger classification across the local
                    # exception used to enter this common failure path.
                    if result is not None:
                        result_classification = classify_census_failure(result=result)
                        if result_classification is not None:
                            classification = result_classification
                    failure = {
                        **job,
                        "status": "failed",
                        "error": f"{type(error).__name__}: {error}",
                        "failure_classification": classification,
                    }
                    write_failed_progress(job, failure["error"], classification=classification)
                    failures.append(failure)
                    append_status(f"- FAILED `{job['profile_id']}/{job['game']}/{job['arm_id']}`: {failure['error']}.")
                    if classification["request_cancellation"] and not cancellation_requested:
                        cancellation_requested = True
                        for other in futures:
                            if other is not future:
                                other.cancel()
                        append_status("- GLOBAL INVARIANT FAILURE: pending jobs cancelled; already-running workers may finish checkpoint boundaries.")
                counts = census_counts(total=len(jobs), results=results, failures=failures, cancelled=cancelled)
                LEDGER.atomic_json(
                    ARTIFACTS / "PARTIAL_RESULTS.json",
                    {
                        **counts,
                        "counts": counts,
                        "results": sorted(results, key=lambda item: (item['profile_id'], item['game'], item['arm_id'])),
                        "failures": failures,
                        "cancelled_jobs": cancelled,
                        "cancellation_requested": cancellation_requested,
                    },
                )
    finally:
        fifo.stop(drain=True)
    counts = census_counts(total=len(jobs), results=results, failures=failures, cancelled=cancelled)
    summary = {
        "results": results,
        "failures": failures,
        "cancelled_jobs": cancelled,
        "counts": counts,
        "cancellation_requested": cancellation_requested,
        "complete": len(results) == len(jobs) and not failures and not cancelled,
    }
    if summary["complete"] and len(selected_games) == 25 and len(selected_profiles) == 3:
        summary["analysis"] = CENSUS.analyze_results(results, manifest, require_complete=True)
    LEDGER.atomic_json(ARTIFACTS / "SUMMARY.json", summary)
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--games", nargs="*")
    parser.add_argument("--profiles", nargs="*")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config()
    if args.workers is not None:
        config["max_parallel_arc_workers"] = args.workers
    manifest = CENSUS.build_manifest()
    if args.dry_run:
        print(json.dumps({"manifest": manifest, "config": config}, indent=2, sort_keys=True))
        return 0
    result = run_census(config, manifest, games=args.games, profiles=args.profiles)
    print(json.dumps({"complete": result["complete"], "results": len(result["results"]), "failures": len(result["failures"])}, indent=2))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
