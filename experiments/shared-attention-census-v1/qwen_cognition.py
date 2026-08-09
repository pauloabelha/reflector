"""Persistent, action-free Qwen cognition over the shared epistemic graph.

The graph ledger is authoritative.  Qwen receives one complete initial
materialization and thereafter every graph event after its durable cursor in
strict order, plus a bounded dependency-closed attention cut.  Semantic
orientation is persisted as an ordinary zero-support graph object; model KV or
chat context is only a disposable transport cache.
"""

from __future__ import annotations

import importlib.util
import json
import queue
import re
import sys
import threading
from concurrent.futures import Future
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence


HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GRAPH = _load("shared_attention_qwen_graph", HERE / "epistemic_graph.py")
V0_WORKER = _load(
    "shared_attention_qwen_v0_transport",
    HERE.parent / "parallel-cognitive-workspace-v0" / "qwen_worker.py",
)


REQUEST_PROTOCOL = "shared-attention-qwen-request-v1.0"
RESPONSE_PROTOCOL = "shared-attention-qwen-response-v1.0"
ORIENTATION_PROTOCOL = "shared-attention-qwen-orientation-v1.0"
MAX_DELTAS = 128
MAX_SCHEMA_WRITES = 1
MAX_EXPLANATION_WRITES = 1
MAX_ATTENTION_WRITES = 2
MAX_EXPANSIONS = 2
VARIABLES = ("?a", "?b", "?c", "?d")
PREDICATES = (
    "SameOutline",
    "DifferentOutline",
    "SameInteriorLayout",
    "DifferentInteriorLayout",
    "SameArea",
    "DifferentArea",
    "AlignedHorizontal",
    "AlignedVertical",
    "Touches",
    "Disjoint",
    "MovedTogether",
    "MovedWhileStationary",
    "ChangedTogether",
)
OPERATORS = ("Decrease", "Increase", "Preserve")
MEASURES = (
    "TranslationAlignmentResidual",
    "ContactResidual",
    "OverlapResidual",
    "InteriorLayoutDisagreement",
    "OutlineDisagreement",
    "AreaDifference",
    "EnclosureCountDifference",
)
ATTENTION_CHANNELS = ("compare", "control-relevance", "causal", "inspect")

FORBIDDEN_KEY = re.compile(
    r"(?:^|_)(?:actions?|action_id|action_token|button|games?|game_id|policy|command|support|support_count|evidence_count|confidence)(?:$|_)",
    re.IGNORECASE,
)
FORBIDDEN_TEXT = re.compile(
    r"(?:arc-action\s*[:_-]?\s*\d+|\baction\s*[:#_-]?\s*\d+|\bbutton\b|\b(?:up|down|left|right)\b|\b[a-z]{2}\d{2}\b)",
    re.IGNORECASE,
)
FORBIDDEN_INPUT_KEY = re.compile(
    r"(?:^|_)(?:actions?|action_id|action_token|button|games?|game_id|policy|command)(?:$|_)",
    re.IGNORECASE,
)
FORBIDDEN_INPUT_TEXT = re.compile(
    r"(?:arc-action\s*[:_-]?\s*\d+|\baction\s*[:#_-]?\s*\d+|\bbutton\b|\b[a-z]{2}\d{2}\b)",
    re.IGNORECASE,
)


PROMPT = """You are the Qwen cognition process sharing an immutable epistemic graph with R2.

The graph, not your conversational context, is authoritative. The first request contains a complete graph materialization. Later requests contain every graph event after your durable cursor in exact order. The sparse attention cut is a bounded view, not a replacement for those events.

Return one strict JSON object matching the supplied schema. You may write only:
- variable-based schemas;
- situated explanations that bind a schema to stable graph object IDs;
- attention contributions over existing graph objects;
- expansion requests for stable IDs whose complete content should enter a later sparse cut.

Rules:
1. Never choose, name, order, repeat, or describe an environment action, button, policy, or game.
2. Never assert support, evidence count, confidence, confirmation, refutation, reward, or success. Every Qwen-created object begins with empirical support zero. Only environment evidence can change support.
3. Use only the supplied closed predicate, operator, measure, variable, object-reference, and attention-channel vocabularies.
4. A schema is generic and contains no concrete object IDs except basis dependencies.
5. An explanation must reference a visible schema and bind every used variable to a visible stable entity ID.
6. Attention changes a worker frontier only; it is not evidence.
7. An expansion request is not a cognitive assertion. Request only an ID present in object_index.
8. Do not invent missing deltas. If the visible cut is insufficient, request expansion or abstain.
9. Emit no prose, Markdown, comments, extra keys, action tokens, or game tokens.
10. Every situated explanation binding must point to a visible grounded entity or use OPEN for a port R2 must attempt to bind. Generic schemas may remain variable-only.

EPISTEMIC_INPUT:
"""


class CognitionError(ValueError):
    """The canonical graph stream or Qwen write violates the protocol."""


@dataclass(frozen=True, slots=True)
class Orientation:
    workspace_id: str
    initialized: bool = False
    cursor_revision: int = -1
    cursor_hash: str | None = None
    focus_ids: tuple[str, ...] = ()
    expansion_ids: tuple[str, ...] = ()
    last_response_hash: str | None = None


@dataclass(frozen=True, slots=True)
class CognitionTurn:
    request_id: str
    workspace_id: str
    basis_revision: int
    basis_hash: str | None
    mode: str
    document: dict[str, Any]
    id_aliases: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class AppliedCompilation:
    state: Any
    events: tuple[Any, ...]
    local_refs: dict[str, str]


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return GRAPH.stable_hash(value)


def cursor_document(state: Any) -> dict[str, Any]:
    return {"revision": int(state.revision), "head_hash": state.head_hash}


def workspace_key(workspace_id: str) -> str:
    """Opaque routing identity safe to persist inside the Qwen-visible graph."""

    return f"qw:{stable_hash({'workspace_id': str(workspace_id)})}"


def orientation_document(value: Orientation) -> dict[str, Any]:
    document = asdict(value)
    document.pop("workspace_id")
    return {
        "protocol": ORIENTATION_PROTOCOL,
        "workspace_key": workspace_key(value.workspace_id),
        **document,
    }


def orientation_from_document(value: Mapping[str, Any], *, workspace_id: str) -> Orientation:
    if value.get("protocol") != ORIENTATION_PROTOCOL:
        raise CognitionError("orientation protocol mismatch")
    required = {
        "protocol",
        "workspace_key",
        "initialized",
        "cursor_revision",
        "cursor_hash",
        "focus_ids",
        "expansion_ids",
        "last_response_hash",
    }
    if set(value) != required:
        raise CognitionError("orientation contract mismatch")
    if value["workspace_key"] != workspace_key(workspace_id):
        raise CognitionError("orientation workspace mismatch")
    return Orientation(
        workspace_id=str(workspace_id),
        initialized=bool(value["initialized"]),
        cursor_revision=int(value["cursor_revision"]),
        cursor_hash=None if value["cursor_hash"] is None else str(value["cursor_hash"]),
        focus_ids=tuple(str(item) for item in value["focus_ids"]),
        expansion_ids=tuple(str(item) for item in value["expansion_ids"]),
        last_response_hash=(
            None if value["last_response_hash"] is None else str(value["last_response_hash"])
        ),
    )


def orientation_object_spec(value: Orientation) -> dict[str, Any]:
    """Return a graph object specification; support remains graph-derived zero."""

    dependencies = tuple(sorted(set((*value.focus_ids, *value.expansion_ids))))
    return {
        "kind": "qwen_orientation",
        "created_by": "qwen",
        "identity": {
            "workspace_key": workspace_key(value.workspace_id),
            "cursor_revision": value.cursor_revision,
            "cursor_hash": value.cursor_hash,
        },
        "payload": orientation_document(value),
        "dependency_ids": dependencies,
    }


def latest_orientation(state: Any, workspace_id: str) -> Orientation | None:
    candidates = [
        item
        for item in state.objects
        if item.kind == "qwen_orientation"
        and item.payload.get("workspace_key") == workspace_key(workspace_id)
    ]
    if not candidates:
        return None
    selected = max(candidates, key=lambda item: (item.created_revision, item.object_id))
    return orientation_from_document(selected.payload, workspace_id=workspace_id)


def _validate_history(state: Any, events: Sequence[Any], orientation: Orientation) -> None:
    if len(events) != int(state.revision) + 1:
        raise CognitionError("graph history length does not match revision")
    for index, event in enumerate(events):
        if int(event.seq) != index:
            raise CognitionError("graph deltas are not a contiguous sequence")
    try:
        replayed = GRAPH.replay(events)
    except Exception as error:
        raise CognitionError("graph history does not replay") from error
    # Dynamic experiment imports can create equivalent dataclass types under
    # different module identities.  Compare their complete canonical documents
    # rather than Python class identity.
    if asdict(replayed) != asdict(state):
        raise CognitionError("graph state is not the canonical history reduction")
    if not orientation.initialized:
        if orientation.cursor_revision != -1 or orientation.cursor_hash is not None:
            raise CognitionError("uninitialized orientation has a nonempty cursor")
        return
    if orientation.cursor_revision < -1 or orientation.cursor_revision > state.revision:
        raise CognitionError("orientation cursor is outside graph history")
    expected_hash = (
        None
        if orientation.cursor_revision == -1
        else events[orientation.cursor_revision].event_hash
    )
    if expected_hash != orientation.cursor_hash:
        raise CognitionError("orientation cursor is not canonical")


def full_materialization(state: Any) -> dict[str, Any]:
    return {
        "revision": state.revision,
        "head_hash": state.head_hash,
        "objects": [
            {
                "id": item.object_id,
                "kind": item.kind,
                "created_by": item.created_by,
                "created_revision": item.created_revision,
                "identity": item.identity,
                "payload": item.payload,
                "dependencies": list(item.dependency_ids),
                "support": GRAPH.support(state, item.object_id),
            }
            for item in state.objects
        ],
        "edges": [
            {
                "id": item.edge_id,
                "kind": item.kind,
                "source": item.source_id,
                "target": item.target_id,
                "created_by": item.created_by,
                "created_revision": item.created_revision,
                "payload": item.payload,
            }
            for item in state.edges
        ],
        "attention": [asdict(item) for item in state.attention],
        "pickups": [asdict(item) for item in state.pickups],
    }


def event_document(event: Any) -> dict[str, Any]:
    """Lossless JSON representation: canonical payload_json is retained exactly."""

    return asdict(event)


def _replace_ids(value: Any, aliases: Mapping[str, str]) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _replace_ids(item, aliases) for key, item in value.items()}
    if isinstance(value, list):
        return [_replace_ids(item, aliases) for item in value]
    if isinstance(value, tuple):
        return [_replace_ids(item, aliases) for item in value]
    return aliases.get(value, value) if isinstance(value, str) else value


def _compact_materialization(state: Any, aliases: Mapping[str, str]) -> dict[str, Any]:
    """Complete topology/index; payload bodies live in the sparse cut."""

    return {
        "revision": state.revision,
        "head_hash": state.head_hash,
        "objects": [
            {
                "id": aliases[item.object_id],
                "kind": item.kind,
                "created_by": item.created_by,
                "created_revision": item.created_revision,
                "dependencies": [aliases[value] for value in item.dependency_ids],
                "identity_digest": stable_hash(item.identity)[:16],
                "payload_digest": stable_hash(item.payload)[:16],
                "support": GRAPH.support(state, item.object_id),
            }
            for item in state.objects
        ],
        "edges": [
            {
                "kind": item.kind,
                "source": aliases[item.source_id],
                "target": aliases[item.target_id],
                "created_by": item.created_by,
                "created_revision": item.created_revision,
                "payload_digest": stable_hash(item.payload)[:16],
            }
            for item in state.edges
        ],
        "attention": [
            {
                "worker": item.worker,
                "object": aliases[item.object_id],
                "weight": item.weight,
                "channel": item.channel,
                "basis": [aliases[value] for value in item.basis_ids],
                "revision": item.created_revision,
            }
            for item in state.attention
        ],
        "pickups": [
            {
                "direction": item.direction,
                "object": aliases[item.object_id],
                "trigger_kind": item.trigger_kind,
                "revision": item.created_revision,
            }
            for item in state.pickups
        ],
        "payload_rule": "complete topology; full payloads are rendered in sparse_cut and may be requested by alias",
    }


def _compact_event(event: Any, aliases: Mapping[str, str]) -> list[Any]:
    item = event.payload["item"]
    if event.event_type == "ObjectAdded":
        return [
            "O",
            aliases[item["object_id"]],
            item["kind"],
            [aliases[value] for value in item["dependency_ids"]],
        ]
    if event.event_type == "EdgeAdded":
        return ["E", item["kind"], aliases[item["source_id"]], aliases[item["target_id"]]]
    return ["A", item["worker"], aliases[item["object_id"]], item["weight"]]


def _stable_aliases(state: Any) -> dict[str, str]:
    output: dict[str, str] = {}
    used: set[str] = set()
    for item in sorted(state.objects, key=lambda value: value.object_id):
        digest = item.object_id.split(":", 1)[-1]
        width = 8
        alias = f"o{digest[:width]}"
        while alias in used:
            width += 2
            alias = f"o{digest[:width]}"
        used.add(alias)
        output[item.object_id] = alias
    return output


def _compact_deltas(events: Sequence[Any], aliases: Mapping[str, str], selected_ids: set[str]) -> list[list[Any]]:
    """Keep epistemically live rows exact; summarize contiguous dormant runs."""

    rows: list[list[Any]] = []
    pending: list[Any] = []

    def flush() -> None:
        if not pending:
            return
        counts: dict[str, int] = {}
        for event in pending:
            item = event.payload["item"]
            label = f"{event.event_type[0]}:{item.get('kind', item.get('channel', 'attention'))}"
            counts[label] = counts.get(label, 0) + 1
        rows.append(["G", len(pending), counts, stable_hash([item.event_hash for item in pending])[:10]])
        pending.clear()

    epistemic_kinds = {"schema", "binding", "explanation", "environment_evidence", "transition", "qwen_orientation"}
    for event in events:
        item = event.payload["item"]
        if event.event_type == "ObjectAdded":
            critical = item["object_id"] in selected_ids or item["kind"] in epistemic_kinds
        elif event.event_type == "EdgeAdded":
            critical = (
                item["kind"] in {"supports", "refutes", "invalidates", "grounds_pickup"}
                or item["source_id"] in selected_ids
                or item["target_id"] in selected_ids
            )
        else:
            critical = item["worker"] == "qwen" or item["object_id"] in selected_ids
        if critical:
            flush()
            rows.append(_compact_event(event, aliases))
        else:
            pending.append(event)
    flush()
    return rows


def _cut_document(state: Any, selected_ids: set[str], mandatory: Sequence[str]) -> dict[str, Any]:
    objects = {item.object_id: item for item in state.objects}
    return {
        "protocol": "shared-attention-qwen-cut-v1.0",
        "graph_revision": state.revision,
        "objects": [
            {
                "id": object_id,
                "kind": objects[object_id].kind,
                "created_by": objects[object_id].created_by,
                "identity": objects[object_id].identity,
                "payload": objects[object_id].payload,
                "dependencies": list(GRAPH.dependency_ids(state, object_id)),
                "support": GRAPH.support(state, object_id),
                "salience": GRAPH.salience(state, "qwen", object_id),
            }
            for object_id in sorted(selected_ids)
        ],
        "edges": [
            {
                "id": edge.edge_id,
                "kind": edge.kind,
                "source": edge.source_id,
                "target": edge.target_id,
                "payload": edge.payload,
            }
            for edge in state.edges
            if edge.source_id in selected_ids and edge.target_id in selected_ids
        ],
        "mandatory_live_bindings": sorted(mandatory),
    }


def sparse_cut(
    state: Any,
    *,
    token_budget: int,
    focus_ids: Sequence[str] = (),
    expansion_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Select a deterministic bounded cut without ever breaking dependencies."""

    def finalized(document: Mapping[str, Any], deferred_count: int) -> dict[str, Any]:
        value = {
            **document,
            "token_budget": token_budget,
            "used_tokens": 0,
            "dependency_closed": True,
            "deferred_expansion_count": deferred_count,
        }
        # The decimal representation of used_tokens contributes to its own
        # estimate, so converge the tiny fixed point explicitly.
        for _attempt in range(4):
            measured = GRAPH.estimate_tokens(value)
            if measured == value["used_tokens"]:
                break
            value["used_tokens"] = measured
        return value

    object_ids = {item.object_id for item in state.objects}
    unknown = sorted((set(focus_ids) | set(expansion_ids)) - object_ids)
    if unknown:
        raise CognitionError(f"orientation references missing stable IDs: {unknown}")
    mandatory = GRAPH.live_binding_ids(state)
    selected = set(GRAPH.dependency_closure(state, mandatory))
    document = finalized(_cut_document(state, selected, mandatory), 0)
    required = document["used_tokens"]
    if required > token_budget:
        raise GRAPH.FrontierBudgetError(budget=token_budget, required=required)

    invalid = GRAPH.invalidated_ids(state)
    priority_roots = list(dict.fromkeys((*expansion_ids, *focus_ids)))
    remaining = sorted(
        object_ids - set(priority_roots) - selected - set(invalid),
        key=lambda object_id: (-GRAPH.salience(state, "qwen", object_id), object_id),
    )
    deferred: list[str] = []
    for root in (*priority_roots, *remaining):
        if root in invalid or root in selected:
            continue
        proposed = selected.union(GRAPH.dependency_closure(state, (root,)))
        candidate = finalized(_cut_document(state, proposed, mandatory), len(deferred))
        if candidate["used_tokens"] <= token_budget:
            selected = proposed
            document = candidate
        elif root in priority_roots:
            deferred.append(root)
    document = finalized(_cut_document(state, selected, mandatory), len(deferred))
    document["dependency_closed"] = all(
        set(GRAPH.dependency_ids(state, object_id)).issubset(selected)
        for object_id in selected
    )
    if document["used_tokens"] > token_budget:
        raise GRAPH.FrontierBudgetError(budget=token_budget, required=document["used_tokens"])
    return document


def build_turn(
    state: Any,
    events: Sequence[Any],
    orientation: Orientation,
    *,
    request_id: str,
    token_budget: int,
    max_deltas: int = MAX_DELTAS,
    compact_ids: bool = False,
) -> CognitionTurn:
    """Build one request solely from canonical graph state and durable orientation."""

    _validate_history(state, events, orientation)
    if FORBIDDEN_TEXT.search(str(request_id)):
        raise CognitionError("request ID leaks an action or game token")
    mode = "initial-full" if not orientation.initialized else "ordered-deltas"
    deltas = [] if not orientation.initialized else list(events[orientation.cursor_revision + 1 :])
    if len(deltas) > max_deltas:
        raise CognitionError("lossless delta window exceeds the frozen bound")
    cut = sparse_cut(
        state,
        token_budget=token_budget,
        focus_ids=orientation.focus_ids,
        expansion_ids=orientation.expansion_ids,
    )
    real_to_alias = (
        _stable_aliases(state)
        if compact_ids
        else {item.object_id: item.object_id for item in state.objects}
    )
    rendered_cut = _replace_ids(cut, real_to_alias) if compact_ids else cut
    selected_real_ids = {item["id"] for item in cut["objects"]}
    object_index = [
        {
            "id": real_to_alias[item.object_id],
            "kind": item.kind,
            **({} if compact_ids else {"dependencies": [real_to_alias[value] for value in item.dependency_ids]}),
        }
        for item in state.objects
    ]
    document = {
        "protocol": REQUEST_PROTOCOL,
        "request_id": str(request_id),
        "mode": mode,
        "from_cursor": {
            "revision": orientation.cursor_revision,
            "head_hash": orientation.cursor_hash,
        },
        "through_cursor": cursor_document(state),
        "full_materialization": (
            (_compact_materialization(state, real_to_alias) if compact_ids else full_materialization(state))
            if mode == "initial-full"
            else None
        ),
        "ordered_lossless_deltas": (
            _compact_deltas(deltas, real_to_alias, selected_real_ids)
            if compact_ids
            else [event_document(item) for item in deltas]
        ),
        "delta_codec": (
            {
                "from_seq_exclusive": orientation.cursor_revision,
                "rows_are_contiguous_and_ordered": True,
                "rows": "[O,id,kind,deps] | [E,kind,source,target] | [A,worker,object,weight] | [G,event_count,kind_counts,ordered_run_hash10]",
                "payloads": "expand object alias through object_index; exact prefix is authenticated by through_cursor.head_hash",
                "G": "small-lossy dormant run: order/count/hash retained; exact events remain in authoritative ledger",
            }
            if compact_ids
            else None
        ),
        "sparse_cut": rendered_cut,
        "object_index": object_index,
        "allowed_vocabulary": {
            "variables": list(VARIABLES),
            "predicates": list(PREDICATES),
            "operators": list(OPERATORS),
            "measures": list(MEASURES),
            "attention_channels": list(ATTENTION_CHANNELS),
        },
    }
    if _forbidden_input(document):
        raise CognitionError("canonical graph projection leaks an action or game token")
    return CognitionTurn(
        request_id=str(request_id),
        workspace_id=orientation.workspace_id,
        basis_revision=state.revision,
        basis_hash=state.head_hash,
        mode=mode,
        document=document,
        id_aliases=tuple(sorted((alias, real) for real, alias in real_to_alias.items() if alias != real)),
    )


def _atom_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["predicate", "arguments"],
        "properties": {
            "predicate": {"enum": list(PREDICATES)},
            "arguments": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"enum": list(VARIABLES)},
            },
        },
    }


def _consequence_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["operator", "measure", "arguments"],
        "properties": {
            "operator": {"enum": list(OPERATORS)},
            "measure": {"enum": list(MEASURES)},
            "arguments": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {"enum": list(VARIABLES)},
            },
        },
    }


def response_schema(turn: CognitionTurn) -> dict[str, Any]:
    objects = turn.document["object_index"]
    all_ids = sorted(item["id"] for item in objects)
    visible_ids = {
        item["id"] for item in turn.document["sparse_cut"]["objects"]
    }
    if turn.mode == "initial-full":
        visible_ids.update(all_ids)
    for delta in turn.document["ordered_lossless_deltas"]:
        if "payload_json" in delta:
            payload = json.loads(delta["payload_json"])
            item = payload.get("item", {})
            for key in ("object_id", "source_id", "target_id"):
                if key in item:
                    visible_ids.add(str(item[key]))
        elif isinstance(delta, Mapping):
            item = delta.get("item", {})
            for key in ("id", "source", "target", "object"):
                if key in item:
                    visible_ids.add(str(item[key]))
        elif isinstance(delta, list) and len(delta) >= 2:
            if delta[0] == "O":
                visible_ids.add(str(delta[1]))
            elif delta[0] == "E" and len(delta) >= 4:
                visible_ids.update((str(delta[2]), str(delta[3])))
            elif delta[0] == "A" and len(delta) >= 3:
                visible_ids.add(str(delta[2]))
    visible_ids.intersection_update(all_ids)
    entity_ids = sorted(
        item["id"]
        for item in objects
        if item["kind"] == "entity" and item["id"] in visible_ids
    )
    schema_ids = sorted(
        item["id"]
        for item in objects
        if item["kind"] == "schema" and item["id"] in visible_ids
    )
    visible_id_schema = (
        {"enum": sorted(visible_ids)}
        if visible_ids
        else {"type": "string", "maxLength": 0}
    )
    expansion_id_schema = (
        {"enum": all_ids} if all_ids else {"type": "string", "maxLength": 0}
    )
    entity_schema = {"enum": [*entity_ids, "OPEN"]}
    schema_ref_schema = (
        {"enum": ["s0", "s1", *schema_ids]}
        if schema_ids
        else {"enum": ["s0", "s1"]}
    )
    basis = {"type": "array", "maxItems": 4, "items": visible_id_schema}
    schema_write = {
        "type": "object",
        "additionalProperties": False,
        "required": ["local_ref", "conditions", "preferred_consequence", "basis_ids"],
        "properties": {
            "local_ref": {"enum": ["s0", "s1"]},
            "conditions": {"type": "array", "minItems": 1, "maxItems": 4, "items": _atom_schema()},
            "preferred_consequence": _consequence_schema(),
            "basis_ids": basis,
        },
    }
    explanation_write = {
        "type": "object",
        "additionalProperties": False,
        "required": ["local_ref", "schema_ref", "bindings", "claim", "basis_ids"],
        "properties": {
            "local_ref": {"enum": ["e0", "e1"]},
            "schema_ref": schema_ref_schema,
            "bindings": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["variable", "object_id"],
                    "properties": {
                        "variable": {"enum": list(VARIABLES)},
                        "object_id": entity_schema,
                    },
                },
            },
            "claim": _consequence_schema(),
            "basis_ids": basis,
        },
    }
    attention_write = {
        "type": "object",
        "additionalProperties": False,
        "required": ["object_id", "weight", "channel", "basis_ids"],
        "properties": {
            "object_id": visible_id_schema,
            "weight": {"type": "integer", "minimum": 1, "maximum": 100},
            "channel": {"enum": list(ATTENTION_CHANNELS)},
            "basis_ids": basis,
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "protocol",
            "request_id",
            "basis_revision",
            "schema_writes",
            "explanation_writes",
            "attention_contributions",
            "expansion_requests",
        ],
        "properties": {
            "protocol": {"const": RESPONSE_PROTOCOL},
            "request_id": {"const": turn.request_id},
            "basis_revision": {"const": turn.basis_revision},
            "schema_writes": {"type": "array", "maxItems": MAX_SCHEMA_WRITES, "items": schema_write},
            "explanation_writes": {"type": "array", "maxItems": MAX_EXPLANATION_WRITES, "items": explanation_write},
            "attention_contributions": {"type": "array", "maxItems": MAX_ATTENTION_WRITES, "items": attention_write},
            "expansion_requests": {
                "type": "array",
                "maxItems": MAX_EXPANSIONS,
                "items": expansion_id_schema,
            },
        },
    }


def request_payload(
    turn: CognitionTurn,
    qwen: Mapping[str, Any],
    *,
    visual_evidence: Sequence[Mapping[str, str]] = (),
) -> dict[str, Any]:
    content: str | list[dict[str, Any]]
    text = PROMPT + stable_json(turn.document)
    if visual_evidence:
        parts: list[dict[str, Any]] = [{"type": "text", "text": text}]
        for item in visual_evidence:
            parts.append({"type": "text", "text": str(item["label"])})
            parts.append(
                {
                    "type": "image_url",
                    "image_url": {"url": str(item["data_url"])},
                }
            )
        content = parts
    else:
        content = text
    return {
        "model": qwen["model"],
        "messages": [{"role": "user", "content": content}],
        "temperature": qwen.get("temperature", 0),
        "top_p": qwen.get("top_p", 1),
        "seed": qwen.get("seed", 0),
        "max_tokens": qwen.get("max_tokens", 900),
        "thinking_budget_tokens": qwen.get("thinking_budget_tokens", qwen.get("thinking_budget", 256)),
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "shared_attention_qwen_response_v1",
                "strict": True,
                "schema": response_schema(turn),
            },
        },
    }


def _forbidden(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(FORBIDDEN_KEY.search(str(key)) or _forbidden(item) for key, item in value.items())
    if isinstance(value, (list, tuple)):
        return any(_forbidden(item) for item in value)
    return isinstance(value, str) and bool(FORBIDDEN_TEXT.search(value))


def _forbidden_input(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            FORBIDDEN_INPUT_KEY.search(str(key)) or _forbidden_input(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_forbidden_input(item) for item in value)
    return isinstance(value, str) and bool(FORBIDDEN_INPUT_TEXT.search(value))


def _exact(value: Any, keys: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != keys:
        raise CognitionError(f"{label}-contract")
    return value


def _variables_in_conditions(conditions: Sequence[Mapping[str, Any]]) -> set[str]:
    return {str(item) for condition in conditions for item in condition["arguments"]}


def _validate_consequence(value: Any, variables: set[str]) -> dict[str, Any]:
    item = _exact(value, {"operator", "measure", "arguments"}, "consequence")
    arguments = item["arguments"]
    if item["operator"] not in OPERATORS or item["measure"] not in MEASURES:
        raise CognitionError("unsupported-consequence")
    if not isinstance(arguments, list) or not 1 <= len(arguments) <= 2:
        raise CognitionError("consequence-arguments")
    if any(argument not in variables for argument in arguments):
        raise CognitionError("unbound-consequence-variable")
    return dict(item)


def compile_response(response: Mapping[str, Any], turn: CognitionTurn) -> dict[str, Any]:
    parsed = response.get("parsed", response)
    top_keys = {
        "protocol",
        "request_id",
        "basis_revision",
        "schema_writes",
        "explanation_writes",
        "attention_contributions",
        "expansion_requests",
    }
    if not isinstance(parsed, Mapping) or set(parsed) != top_keys:
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "top-level-contract"}]}
    if (
        parsed["protocol"] != RESPONSE_PROTOCOL
        or parsed["request_id"] != turn.request_id
        or parsed["basis_revision"] != turn.basis_revision
    ):
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "basis-contract"}]}
    if _forbidden(parsed):
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "forbidden-action-game-or-authority-token"}]}

    object_index = {item["id"]: item for item in turn.document["object_index"]}
    visible = {item["id"] for item in turn.document["sparse_cut"]["objects"]}
    if turn.mode == "initial-full":
        visible.update(object_index)
    for delta in turn.document["ordered_lossless_deltas"]:
        if "payload_json" in delta:
            payload = json.loads(delta["payload_json"])
            item = payload.get("item", {})
            for key in ("object_id", "source_id", "target_id"):
                if key in item:
                    visible.add(str(item[key]))
        elif isinstance(delta, Mapping):
            item = delta.get("item", {})
            for key in ("id", "source", "target", "object"):
                if key in item:
                    visible.add(str(item[key]))
        elif isinstance(delta, list) and len(delta) >= 2:
            if delta[0] == "O":
                visible.add(str(delta[1]))
            elif delta[0] == "E" and len(delta) >= 4:
                visible.update((str(delta[2]), str(delta[3])))
            elif delta[0] == "A" and len(delta) >= 3:
                visible.add(str(delta[2]))

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    local_schemas: dict[str, dict[str, Any]] = {}

    schema_writes = parsed["schema_writes"]
    explanation_writes = parsed["explanation_writes"]
    attention_writes = parsed["attention_contributions"]
    expansions = parsed["expansion_requests"]
    if not isinstance(schema_writes, list) or len(schema_writes) > MAX_SCHEMA_WRITES:
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "schema-cap"}]}
    if not isinstance(explanation_writes, list) or len(explanation_writes) > MAX_EXPLANATION_WRITES:
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "explanation-cap"}]}
    if not isinstance(attention_writes, list) or len(attention_writes) > MAX_ATTENTION_WRITES:
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "attention-cap"}]}
    if not isinstance(expansions, list) or len(expansions) > MAX_EXPANSIONS:
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "expansion-cap"}]}

    for index, raw in enumerate(schema_writes):
        try:
            item = _exact(raw, {"local_ref", "conditions", "preferred_consequence", "basis_ids"}, "schema")
            if item["local_ref"] not in {"s0", "s1"} or item["local_ref"] in local_schemas:
                raise CognitionError("schema-local-ref")
            conditions = item["conditions"]
            if not isinstance(conditions, list) or not 1 <= len(conditions) <= 4:
                raise CognitionError("condition-cap")
            for condition in conditions:
                atom = _exact(condition, {"predicate", "arguments"}, "condition")
                if atom["predicate"] not in PREDICATES:
                    raise CognitionError("unknown-predicate")
                if not isinstance(atom["arguments"], list) or len(atom["arguments"]) != 2:
                    raise CognitionError("condition-arguments")
                if any(value not in VARIABLES for value in atom["arguments"]):
                    raise CognitionError("condition-variable")
            variables = _variables_in_conditions(conditions)
            consequence = _validate_consequence(item["preferred_consequence"], variables)
            basis_ids = item["basis_ids"]
            if not isinstance(basis_ids, list) or any(value not in visible for value in basis_ids):
                raise CognitionError("schema-basis-not-visible")
            compiled = {
                "kind": "schema",
                "local_ref": item["local_ref"],
                "identity": {"origin": "qwen", "conditions": conditions, "preferred_consequence": consequence},
                "payload": {"conditions": conditions, "preferred_consequence": consequence, "provenance": "externally-proposed"},
                "dependency_ids": sorted(set(basis_ids)),
                "support": 0,
                "evidence": [],
            }
            local_schemas[item["local_ref"]] = compiled
            accepted.append(compiled)
        except (CognitionError, KeyError, TypeError) as error:
            rejected.append({"kind": "schema", "index": index, "reason": str(error), "raw": raw})

    existing_schemas = {
        object_id
        for object_id, value in object_index.items()
        if value["kind"] == "schema" and object_id in visible
    }
    local_explanations: set[str] = set()
    for index, raw in enumerate(explanation_writes):
        try:
            item = _exact(raw, {"local_ref", "schema_ref", "bindings", "claim", "basis_ids"}, "explanation")
            if item["local_ref"] not in {"e0", "e1"} or item["local_ref"] in local_explanations:
                raise CognitionError("explanation-local-ref")
            if item["schema_ref"] not in existing_schemas | set(local_schemas):
                raise CognitionError("unknown-schema-ref")
            bindings = item["bindings"]
            if not isinstance(bindings, list) or not 1 <= len(bindings) <= 3:
                raise CognitionError("binding-cap")
            assignments: dict[str, str] = {}
            for raw_binding in bindings:
                binding = _exact(raw_binding, {"variable", "object_id"}, "binding")
                variable = str(binding["variable"])
                object_id = str(binding["object_id"])
                if variable not in VARIABLES or variable in assignments:
                    raise CognitionError("binding-variable")
                if object_id != "OPEN" and (
                    object_id not in visible or object_index.get(object_id, {}).get("kind") != "entity"
                ):
                    raise CognitionError("binding-entity-not-visible")
                if object_id != "OPEN" and object_id in assignments.values():
                    raise CognitionError("binding-not-injective")
                assignments[variable] = object_id
            claim = _validate_consequence(item["claim"], set(assignments))
            basis_ids = item["basis_ids"]
            if not isinstance(basis_ids, list) or any(value not in visible for value in basis_ids):
                raise CognitionError("explanation-basis-not-visible")
            dependencies = sorted(set([*basis_ids, *(value for value in assignments.values() if value != "OPEN")]))
            if item["schema_ref"] in existing_schemas:
                dependencies.append(item["schema_ref"])
            compiled = {
                "kind": "explanation",
                "local_ref": item["local_ref"],
                "schema_ref": item["schema_ref"],
                "identity": {"origin": "qwen", "schema_ref": item["schema_ref"], "bindings": assignments},
                "payload": {
                    "bindings": assignments,
                    "open_ports": sorted(variable for variable, value in assignments.items() if value == "OPEN"),
                    "claim": claim,
                    "provenance": "externally-proposed",
                },
                "dependency_ids": sorted(set(dependencies)),
                "support": 0,
                "evidence": [],
            }
            local_explanations.add(str(item["local_ref"]))
            accepted.append(compiled)
        except (CognitionError, KeyError, TypeError) as error:
            rejected.append({"kind": "explanation", "index": index, "reason": str(error), "raw": raw})

    for index, raw in enumerate(attention_writes):
        try:
            item = _exact(raw, {"object_id", "weight", "channel", "basis_ids"}, "attention")
            if item["object_id"] not in visible:
                raise CognitionError("attention-object-not-visible")
            if not isinstance(item["weight"], int) or not 1 <= item["weight"] <= 100:
                raise CognitionError("attention-weight")
            if item["channel"] not in ATTENTION_CHANNELS:
                raise CognitionError("attention-channel")
            if not isinstance(item["basis_ids"], list) or any(value not in visible for value in item["basis_ids"]):
                raise CognitionError("attention-basis-not-visible")
            accepted.append(
                {
                    "kind": "attention",
                    "worker": "qwen",
                    "object_id": item["object_id"],
                    "weight": item["weight"],
                    "channel": item["channel"],
                    "basis_ids": sorted(set(item["basis_ids"])),
                    "support": 0,
                    "evidence": [],
                }
            )
        except (CognitionError, KeyError, TypeError) as error:
            rejected.append({"kind": "attention", "index": index, "reason": str(error), "raw": raw})

    valid_expansions = []
    for index, object_id in enumerate(expansions):
        if object_id not in object_index:
            rejected.append({"kind": "expansion", "index": index, "reason": "unknown-expansion-id", "raw": object_id})
        else:
            valid_expansions.append(object_id)
    alias_to_real = dict(turn.id_aliases)
    if alias_to_real:
        accepted = [_replace_ids(item, alias_to_real) for item in accepted]
        valid_expansions = [alias_to_real.get(item, item) for item in valid_expansions]
    return {
        "valid_json_contract": True,
        "accepted": accepted,
        "rejected": rejected,
        "expansion_requests": sorted(set(valid_expansions)),
        "support_assigned": 0,
    }


def apply_compilation(
    state: Any,
    compilation: Mapping[str, Any],
    *,
    response_key: str,
) -> AppliedCompilation:
    """Purely apply accepted writes with graph authority and local-ref resolution.

    The caller remains responsible for durably appending the returned events.
    No support edge is created here; every newly created Qwen object therefore
    has graph-derived support zero.
    """

    if not compilation.get("valid_json_contract"):
        raise CognitionError("cannot apply an invalid Qwen response")
    current = state
    events: list[Any] = []
    local_refs: dict[str, str] = {}
    for index, item in enumerate(compilation.get("accepted", ())):
        kind = item.get("kind")
        if kind in {"schema", "explanation"}:
            dependencies = [local_refs.get(value, value) for value in item["dependency_ids"]]
            identity = dict(item["identity"])
            payload = dict(item["payload"])
            if kind == "explanation":
                resolved_schema = local_refs.get(str(item["schema_ref"]), str(item["schema_ref"]))
                identity["schema_ref"] = resolved_schema
                payload["schema_ref"] = resolved_schema
                dependencies.append(resolved_schema)
            candidate = GRAPH.make_object(
                kind=kind,
                created_by="qwen",
                created_revision=current.revision + 1,
                identity=identity,
                payload=payload,
                dependency_ids=dependencies,
            )
            existing = next(
                (value for value in current.objects if value.object_id == candidate.object_id),
                None,
            )
            if existing is None:
                event = GRAPH.object_event(
                    current,
                    kind=kind,
                    created_by="qwen",
                    identity=identity,
                    payload=payload,
                    dependency_ids=dependencies,
                    event_key=f"{response_key}:{index}:{item['local_ref']}",
                )
                current = GRAPH.apply_event(current, event)
                events.append(event)
                object_id = candidate.object_id
                if GRAPH.support(current, object_id) != 0:
                    raise CognitionError("new Qwen object did not begin at support zero")
            else:
                object_id = existing.object_id
            local_refs[str(item["local_ref"])] = object_id
        elif kind == "attention":
            event = GRAPH.attention_event(
                current,
                worker="qwen",
                object_id=str(item["object_id"]),
                weight=int(item["weight"]),
                channel=str(item["channel"]),
                basis_ids=item["basis_ids"],
                contribution_key=f"{response_key}:{index}",
            )
            current = GRAPH.apply_event(current, event)
            events.append(event)
        else:
            raise CognitionError(f"unsupported accepted write kind: {kind}")
    return AppliedCompilation(current, tuple(events), local_refs)


def advance_orientation(
    previous: Orientation,
    turn: CognitionTurn,
    compilation: Mapping[str, Any],
) -> Orientation:
    if previous.workspace_id != turn.workspace_id:
        raise CognitionError("orientation workspace mismatch")
    focus = sorted(
        {
            str(item["object_id"])
            for item in compilation.get("accepted", ())
            if item.get("kind") == "attention"
        }
    )
    return Orientation(
        workspace_id=previous.workspace_id,
        initialized=True,
        cursor_revision=turn.basis_revision,
        cursor_hash=turn.basis_hash,
        focus_ids=tuple(focus),
        expansion_ids=tuple(compilation.get("expansion_requests", ())),
        last_response_hash=stable_hash(compilation),
    )


@dataclass(frozen=True, slots=True)
class QueueResult:
    sequence: int
    workspace_id: str
    response: dict[str, Any]


class ResidentServerQueue:
    """One FIFO transport thread shared by every game workspace."""

    def __init__(
        self,
        endpoint: str,
        *,
        timeout: float = 600.0,
        poster: Callable[[str, Any, float], dict[str, Any]] = V0_WORKER.post_request,
    ) -> None:
        self.endpoint = str(endpoint)
        self.timeout = float(timeout)
        self.poster = poster
        self._queue: queue.Queue[tuple[int, str, Any, Future[QueueResult]] | None] = queue.Queue()
        self._sequence = 0
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, name="shared-attention-qwen-fifo", daemon=False)
        self._started = False

    def start(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._thread.start()

    def submit(self, workspace_id: str, request: Any) -> Future[QueueResult]:
        self.start()
        with self._lock:
            sequence = self._sequence
            self._sequence += 1
            future: Future[QueueResult] = Future()
            # Allocation and enqueue are one critical section, so concurrent
            # ARC workers cannot place sequence n+1 ahead of sequence n.
            self._queue.put((sequence, str(workspace_id), request, future))
        return future

    def _run(self) -> None:
        while True:
            task = self._queue.get()
            try:
                if task is None:
                    return
                sequence, workspace_id, request, future = task
                if future.set_running_or_notify_cancel():
                    try:
                        response = self.poster(self.endpoint, request, self.timeout)
                        future.set_result(QueueResult(sequence, workspace_id, response))
                    except BaseException as error:
                        future.set_exception(error)
            finally:
                self._queue.task_done()

    def stop(self, *, drain: bool = True) -> None:
        if not self._started:
            return
        if drain:
            self._queue.join()
        self._queue.put(None)
        self._thread.join(timeout=max(5.0, self.timeout + 1.0))
        if self._thread.is_alive():
            raise RuntimeError("resident Qwen queue did not stop")
