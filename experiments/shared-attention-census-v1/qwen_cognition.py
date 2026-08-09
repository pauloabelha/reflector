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
MAX_SALIENCE_FILL_ROOTS = 4
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
CONTROL_OPERATORS = ("Decrease", "Increase")
MEASURES = (
    "TranslationAlignmentResidual",
    "ContactResidual",
    "OverlapResidual",
    "InteriorLayoutDisagreement",
    "OutlineDisagreement",
    "AreaDifference",
    "EnclosureCountDifference",
)
CONTROL_MEASURES = ("TranslationAlignmentResidual",)
ATTENTION_CHANNELS = ("compare", "control-relevance", "causal", "inspect")
CODE_ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"

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

The graph, not your conversational context, is authoritative. A non-compact request carries exact canonical events. A compact request carries an ordered projection: O/E/A rows exactly preserve the fields documented by delta_codec, while each G row is explicitly a small-lossy summary of a contiguous dormant run. Exact event bodies remain only in the authoritative ledger. The sparse attention cut is a bounded semantic projection, not a replacement for that ledger.

Return one strict JSON object matching the supplied schema. You may write only:
- variable-based schemas;
- situated explanations that bind a schema to stable graph object IDs;
- attention contributions over existing graph objects;
- expansion requests for stable IDs whose semantic payload projection should enter a later sparse cut.

Rules:
1. Never choose, name, order, repeat, or describe an environment action, button, policy, or game.
2. Never assert support, evidence count, confidence, confirmation, refutation, reward, or success. Every Qwen-created object begins with empirical support zero. Only environment evidence can change support.
3. Use only the supplied closed predicate, operator, measure, variable, object-reference, and attention-channel vocabularies.
4. A schema is generic and contains no concrete object IDs except basis dependencies.
5. An explanation must reference a visible schema and bind every used variable to a visible stable entity ID.
6. Attention changes a worker frontier only; it is not evidence.
7. An expansion request is not a cognitive assertion. Request only an ID present in object_index. Large exact raster/index bodies remain addressable by their digest and authoritative object ID rather than being copied into the prompt.
8. Do not invent missing deltas. If the visible cut is insufficient, request expansion or abstain.
9. Emit no prose, Markdown, comments, extra keys, action tokens, or game tokens.
10. Every situated explanation binding must point to a visible grounded entity or use OPEN for a port R2 must attempt to bind. Generic schemas may remain variable-only.
11. A schema can enter the control gate only with Decrease or Increase of TranslationAlignmentResidual. Explanation claims may use the broader semantic vocabulary but do not directly control.
12. Bind every variable used by the referenced schema conditions. Concrete bindings must make every condition true in visible entity descriptors or relation facts; use OPEN rather than guessing.
13. Treat a uniquely huge border-spanning component as scene/background unless transition evidence makes it causal; prefer compact repeated foreground structure for object-role hypotheses.
14. Seek discriminative relational contrasts, not tautologies: compare same-outline groups, interior-layout classes, motion roles, and competing pairings. A condition should help select the effect pair rather than merely restate that pair's current scalar value.
15. Use a third variable only when its relations disambiguate the two effect variables. If several groundings remain plausible, expose OPEN ports or request expansion instead of choosing arbitrarily.
16. When a visible structured criticism has status ambiguous-grounding, treat its bounded candidate_substitutions and effect_pairs as competing grounding witnesses. Inspect their distinguishing_relations together with the target schema and current relation set, then refine the schema conditions to retain exactly one effect pair. Do not repeat the criticized conditions unchanged. If the closed predicate vocabulary cannot distinguish one pair, request expansion or abstain.

In a compact initial materialization, object_columns arrays align by ordinal with object_index.ids. This columnar topology preserves every alias, kind, dependency, digest, creator, revision, and nonzero support entry. Initial attention_rows are explicitly small-lossy aggregates; exact contributions remain in the ledger.

Predicate semantics: Same/DifferentOutline compare outline_class; Same/DifferentInteriorLayout compare interior_layout_class; Same/DifferentArea compare area; AlignedHorizontal/AlignedVertical, Touches, Disjoint, MovedTogether, MovedWhileStationary, and ChangedTogether require the corresponding visible relation fact (alignment may also be derived from centroids). TranslationAlignmentResidual is Manhattan centroid distance. ContactResidual is separation from contact. OverlapResidual is non-overlap. InteriorLayoutDisagreement, OutlineDisagreement, AreaDifference, and EnclosureCountDifference are semantic comparison measures for explanations only.

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
    """Columnar complete topology; semantic bodies live in the sparse cut."""

    objects = sorted(state.objects, key=lambda item: (item.created_revision, item.object_id))
    ordinal = {item.object_id: index for index, item in enumerate(objects)}
    creator_legend = sorted({item.created_by for item in objects})
    creator_code = {value: index for index, value in enumerate(creator_legend)}
    digest_pairs = [
        f"{stable_hash(item.identity)[:8]}.{stable_hash(item.payload)[:8]}"
        for item in objects
    ]
    support_nonzero = [
        [index, value]
        for index, item in enumerate(objects)
        if (value := GRAPH.support(state, item.object_id)) != 0
    ]

    edge_kinds = sorted({item.kind for item in state.edges})
    edge_kind_code = {value: index for index, value in enumerate(edge_kinds)}
    edge_rows = [
        [
            edge_kind_code[item.kind],
            ordinal[item.source_id],
            ordinal[item.target_id],
            stable_hash(item.payload)[:8],
        ]
        for item in state.edges
    ]

    attention_groups: dict[tuple[str, int, str], dict[str, Any]] = {}
    for item in state.attention:
        key = (item.worker, ordinal[item.object_id], item.channel)
        group = attention_groups.setdefault(
            key,
            {
                "total": 0,
                "count": 0,
                "maximum": 0,
                "latest_revision": -1,
                "basis": set(),
            },
        )
        group["total"] += item.weight
        group["count"] += 1
        group["maximum"] = max(group["maximum"], item.weight)
        group["latest_revision"] = max(group["latest_revision"], item.created_revision)
        group["basis"].update(ordinal[value] for value in item.basis_ids)
    attention_rows = [
        [
            worker,
            object_ordinal,
            channel,
            group["total"],
            group["count"],
            group["maximum"],
            group["latest_revision"],
            sorted(group["basis"]),
        ]
        for (worker, object_ordinal, channel), group in sorted(attention_groups.items())
    ]

    return {
        "revision": state.revision,
        "head_hash": state.head_hash,
        "object_columns": {
            "aligned_with": "object_index.ids",
            "creator_legend": creator_legend,
            "creator_codes": "".join(CODE_ALPHABET[creator_code[item.created_by]] for item in objects),
            "created_revision_deltas": [
                item.created_revision - (objects[index - 1].created_revision if index else 0)
                for index, item in enumerate(objects)
            ],
            "dependency_ordinals": [
                [ordinal[value] for value in item.dependency_ids] for item in objects
            ],
            "identity_payload_digest8_pairs": digest_pairs,
            "support_default": 0,
            "support_nonzero": support_nonzero,
        },
        "edge_columns": ["kind_code", "source_ordinal", "target_ordinal", "payload_digest8"],
        "edge_kind_legend": edge_kinds,
        "edge_rows": edge_rows,
        "attention_fidelity": "small-lossy aggregation by worker, object, and channel; exact contributions remain in authoritative ledger",
        "attention_columns": [
            "worker",
            "object_ordinal",
            "channel",
            "total_weight",
            "count",
            "maximum_weight",
            "latest_revision",
            "basis_ordinals_union",
        ],
        "attention_rows": attention_rows,
        "pickup_columns": ["direction", "object_ordinal", "trigger_kind", "revision"],
        "pickup_rows": [
            [item.direction, ordinal[item.object_id], item.trigger_kind, item.created_revision]
            for item in state.pickups
        ],
        "payload_rule": "all aliases, kinds, dependencies, digests, creators, revisions, and support are preserved columnarly; semantic payload projections are in sparse_cut",
    }


def _compact_object_index(
    state: Any,
    aliases: Mapping[str, str],
    object_ids: set[str] | None = None,
) -> dict[str, Any]:
    objects = sorted(
        (
            item
            for item in state.objects
            if object_ids is None or item.object_id in object_ids
        ),
        key=lambda item: (item.created_revision, item.object_id),
    )
    kinds = sorted({item.kind for item in objects})
    if len(kinds) > len(CODE_ALPHABET):
        raise CognitionError("too many object kinds for compact index")
    kind_code = {value: index for index, value in enumerate(kinds)}
    return {
        "encoding": "columnar-v1",
        "kind_legend": kinds,
        "ids": [aliases[item.object_id] for item in objects],
        "kind_codes": "".join(CODE_ALPHABET[kind_code[item.kind]] for item in objects),
    }


def _object_index_documents(value: Any) -> list[dict[str, str]]:
    if isinstance(value, list):
        return [{"id": str(item["id"]), "kind": str(item["kind"])} for item in value]
    if not isinstance(value, Mapping) or value.get("encoding") != "columnar-v1":
        raise CognitionError("object-index-contract")
    ids, codes, legend = value.get("ids"), value.get("kind_codes"), value.get("kind_legend")
    if not isinstance(ids, list) or not isinstance(codes, (list, str)) or not isinstance(legend, list):
        raise CognitionError("object-index-contract")
    if len(ids) != len(codes):
        raise CognitionError("object-index-contract")
    try:
        return [
            {
                "id": str(object_id),
                "kind": str(
                    legend[
                        CODE_ALPHABET.index(code)
                        if isinstance(codes, str)
                        else int(code)
                    ]
                ),
            }
            for object_id, code in zip(ids, codes)
        ]
    except (IndexError, TypeError, ValueError) as error:
        raise CognitionError("object-index-contract") from error


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
        width = 6
        alias = f"o{digest[:width]}"
        while alias in used:
            width += 2
            alias = f"o{digest[:width]}"
        used.add(alias)
        output[item.object_id] = alias
    return output


def _compact_deltas(events: Sequence[Any], aliases: Mapping[str, str], selected_ids: set[str]) -> list[list[Any]]:
    """Project live rows field-exactly; summarize contiguous dormant runs lossily."""

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


def _payload_projection(kind: str, payload: Mapping[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return a semantic view without mutating or weakening graph authority.

    Large raster runs and opaque runtime indexes are still addressable through
    their stable digests/blob references.  The canonical payload remains in
    the graph ledger and is never rewritten by this projection.
    """

    projected = dict(payload)
    omitted: list[str] = []
    if kind == "entity" and isinstance(projected.get("grounding"), Mapping):
        grounding = dict(projected["grounding"])
        if "mask_rle_rc" in grounding:
            grounding.pop("mask_rle_rc")
            omitted.append("grounding.mask_rle_rc")
        projected["grounding"] = grounding
    if kind == "runtime_summary":
        for key in ("schema_ids", "shadow_statuses"):
            value = projected.pop(key, None)
            if value is None:
                continue
            projected[f"{key}_index"] = {
                "count": len(value),
                "digest": stable_hash(value)[:16],
            }
            omitted.append(key)
    return projected, omitted


def _projected_object(state: Any, item: Any) -> dict[str, Any]:
    payload, omitted = _payload_projection(item.kind, item.payload)
    value = {
        "id": item.object_id,
        "kind": item.kind,
        "created_by": item.created_by,
        "identity": item.identity,
        "payload": payload,
        "dependencies": list(GRAPH.dependency_ids(state, item.object_id)),
        "support": GRAPH.support(state, item.object_id),
        "salience": GRAPH.salience(state, "qwen", item.object_id),
    }
    if omitted:
        value["projection"] = {
            "omitted_large_fields": omitted,
            "canonical_object_id": item.object_id,
            "exact_payload_location": "authoritative_graph_ledger",
        }
    return value


def _cut_document(state: Any, selected_ids: set[str], mandatory: Sequence[str]) -> dict[str, Any]:
    objects = {item.object_id: item for item in state.objects}
    return {
        "protocol": "shared-attention-qwen-cut-v1.0",
        "graph_revision": state.revision,
        "objects": [_projected_object(state, objects[object_id]) for object_id in sorted(selected_ids)],
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
    relation_sets = [item for item in state.objects if item.kind == "relation_set" and item.object_id not in invalid]
    latest_relation_revision = max((item.created_revision for item in relation_sets), default=-1)
    structural_roots = sorted(
        item.object_id for item in relation_sets if item.created_revision == latest_relation_revision
    )
    ambiguity_criticisms = [
        item
        for item in state.objects
        if item.kind == "structured_criticism"
        and item.object_id not in invalid
        and item.payload.get("status") == "ambiguous-grounding"
    ]
    latest_criticism_revision = max(
        (item.created_revision for item in ambiguity_criticisms), default=-1
    )
    ambiguity_roots = sorted(
        item.object_id
        for item in ambiguity_criticisms
        if item.created_revision == latest_criticism_revision
    )
    # An ambiguity request is intelligible only as one unit: the criticism
    # carries concrete competing witnesses, its dependency closure carries the
    # criticized schema, and the latest relation packet carries the current
    # entities/facts needed to assess a discriminating refinement.  If this
    # essential unit cannot fit, fail explicitly instead of asking Qwen to
    # reason from a counts-only fragment.
    essential_roots = tuple(dict.fromkeys((*structural_roots, *ambiguity_roots)))
    if ambiguity_roots:
        proposed = selected.union(GRAPH.dependency_closure(state, essential_roots))
        candidate = finalized(_cut_document(state, proposed, mandatory), 0)
        if candidate["used_tokens"] > token_budget:
            raise GRAPH.FrontierBudgetError(
                budget=token_budget, required=candidate["used_tokens"]
            )
        selected = proposed
        document = candidate
    # Give the latest relational packet first opportunity to fit.  A mistaken
    # model focus must not permanently hide the current entities it should be
    # comparing; explicit expansions and prior focus follow immediately.
    priority_roots = list(
        dict.fromkeys((*essential_roots, *expansion_ids, *focus_ids))
    )
    remaining = sorted(
        object_ids - set(priority_roots) - selected - set(invalid),
        key=lambda object_id: (-GRAPH.salience(state, "qwen", object_id), object_id),
    )[:MAX_SALIENCE_FILL_ROOTS]
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
    # Initial residency exposes the complete compact catalog once.  Later
    # turns keep a rolling catalog of the dependency-closed live cut; newly
    # seen dormant IDs remain in ordered delta rows and in the durable alias
    # map, but are not redundantly retransmitted forever.
    indexed_real_ids = None if mode == "initial-full" else set(selected_real_ids)
    object_index: Any = (
        _compact_object_index(state, real_to_alias, indexed_real_ids)
        if compact_ids
        else [
            {
                "id": real_to_alias[item.object_id],
                "kind": item.kind,
                "dependencies": [real_to_alias[value] for value in item.dependency_ids],
            }
            for item in state.objects
            if indexed_real_ids is None or item.object_id in indexed_real_ids
        ]
    )
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
                "fidelity": "mixed compact projection, not a lossless event stream",
                "O_E_A": "field-exact for the fields named by rows; payloads, sequence numbers, and event hashes are omitted",
                "G": "small-lossy contiguous dormant run; event count, kind counts, and ordered-run digest retained",
                "authority": "exact canonical events remain in the graph ledger; request stable object expansion for semantic payload projection",
            }
            if compact_ids
            else {
                "fidelity": "exact canonical event documents",
                "rows_are_contiguous_and_ordered": True,
            }
        ),
        "sparse_cut": rendered_cut,
        "object_index": object_index,
        "allowed_vocabulary": {
            "variables": list(VARIABLES),
            "predicates": list(PREDICATES),
            "operators": list(OPERATORS),
            "measures": list(MEASURES),
            "attention_channels": list(ATTENTION_CHANNELS),
            "control_gate": {
                "operators": list(CONTROL_OPERATORS),
                "measures": list(CONTROL_MEASURES),
            },
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


def _consequence_schema(
    *,
    operators: Sequence[str] = OPERATORS,
    measures: Sequence[str] = MEASURES,
) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["operator", "measure", "arguments"],
        "properties": {
            "operator": {"enum": list(operators)},
            "measure": {"enum": list(measures)},
            "arguments": {
                "type": "array",
                "minItems": 1,
                "maxItems": 2,
                "items": {"enum": list(VARIABLES)},
            },
        },
    }


def response_schema(turn: CognitionTurn) -> dict[str, Any]:
    objects = _object_index_documents(turn.document["object_index"])
    all_ids = sorted(item["id"] for item in objects)
    visible_ids = {
        item["id"] for item in turn.document["sparse_cut"]["objects"]
    }
    if turn.mode == "initial-full" and not turn.id_aliases:
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
    semantic_documents = _visible_object_documents(turn)
    entity_ids = sorted(
        item["id"]
        for item in objects
        if (
            item["kind"] == "entity"
            and item["id"] in visible_ids
            and item["id"] in semantic_documents
        )
    )
    schema_ids = sorted(
        item["id"]
        for item in objects
        if (
            item["kind"] == "schema"
            and item["id"] in visible_ids
            and isinstance(
                semantic_documents.get(item["id"], {}).get("payload", {}).get("conditions"),
                list,
            )
        )
    )
    visible_id_schema = (
        {"enum": sorted(visible_ids)}
        if visible_ids
        else {"type": "string", "maxLength": 0}
    )
    expansion_id_schema = (
        {"type": "string", "pattern": r"^o[0-9a-f]{6,64}$"}
        if turn.id_aliases
        else ({"enum": all_ids} if all_ids else {"type": "string", "maxLength": 0})
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
            "preferred_consequence": _consequence_schema(
                operators=CONTROL_OPERATORS,
                measures=CONTROL_MEASURES,
            ),
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


def _validate_consequence(
    value: Any,
    variables: set[str],
    *,
    operators: Sequence[str] = OPERATORS,
    measures: Sequence[str] = MEASURES,
) -> dict[str, Any]:
    item = _exact(value, {"operator", "measure", "arguments"}, "consequence")
    arguments = item["arguments"]
    if item["operator"] not in operators or item["measure"] not in measures:
        raise CognitionError("unsupported-consequence")
    if not isinstance(arguments, list) or not 1 <= len(arguments) <= 2:
        raise CognitionError("consequence-arguments")
    if any(argument not in variables for argument in arguments):
        raise CognitionError("unbound-consequence-variable")
    return dict(item)


def _visible_object_documents(turn: CognitionTurn) -> dict[str, Mapping[str, Any]]:
    """Objects whose semantic descriptors, not merely IDs, are visible."""

    documents: dict[str, Mapping[str, Any]] = {}
    materialization = turn.document.get("full_materialization")
    if isinstance(materialization, Mapping):
        for raw in materialization.get("objects", ()):
            if isinstance(raw, Mapping) and isinstance(raw.get("payload"), Mapping):
                documents[str(raw["id"])] = raw
    for raw in turn.document["sparse_cut"]["objects"]:
        if isinstance(raw, Mapping) and isinstance(raw.get("payload"), Mapping):
            documents[str(raw["id"])] = raw
    for delta in turn.document.get("ordered_lossless_deltas", ()):
        if not isinstance(delta, Mapping) or "payload_json" not in delta:
            continue
        envelope = json.loads(str(delta["payload_json"]))
        raw = envelope.get("item", {})
        if raw.get("object_id") is None or raw.get("kind") is None:
            continue
        payload = raw.get("payload")
        if payload is None and isinstance(raw.get("payload_json"), str):
            payload = json.loads(raw["payload_json"])
        identity = raw.get("identity")
        if identity is None and isinstance(raw.get("identity_json"), str):
            identity = json.loads(raw["identity_json"])
        if isinstance(payload, Mapping):
            documents[str(raw["object_id"])] = {
                "id": str(raw["object_id"]),
                "kind": str(raw["kind"]),
                "identity": identity or {},
                "payload": payload,
                "dependencies": list(raw.get("dependency_ids", ())),
            }
    return documents


def _entity_local_refs(document: Mapping[str, Any]) -> set[str]:
    output: set[str] = set()
    identity = document.get("identity", {})
    payload = document.get("payload", {})
    grounding = payload.get("grounding", {}) if isinstance(payload, Mapping) else {}
    for source, key in (
        (identity, "local_ref"),
        (payload, "local_ref"),
        (payload, "id"),
        (grounding, "local_component_ref"),
    ):
        if isinstance(source, Mapping) and source.get(key) is not None:
            output.add(str(source[key]))
    return output


def _grounding_view(
    turn: CognitionTurn,
) -> tuple[dict[str, Mapping[str, Any]], set[tuple[str, str, str]]]:
    documents = _visible_object_documents(turn)
    entities = {
        object_id: value
        for object_id, value in documents.items()
        if value.get("kind") == "entity"
    }
    local_to_ids: dict[str, set[str]] = {}
    for object_id, value in entities.items():
        for local_ref in _entity_local_refs(value):
            local_to_ids.setdefault(local_ref, set()).add(object_id)

    symmetric = {
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
        "ChangedTogether",
    }
    facts: set[tuple[str, str, str]] = set()
    for value in documents.values():
        payload = value.get("payload", {})
        relations = payload.get("relations", ()) if isinstance(payload, Mapping) else ()
        if not isinstance(relations, list):
            continue
        scoped_ids = {
            str(item)
            for item in value.get("dependencies", ())
            if str(item) in entities
        }

        def resolve(raw: Any) -> str | None:
            candidate = str(raw)
            if candidate in entities:
                return candidate
            matches = local_to_ids.get(candidate, set())
            if scoped_ids:
                matches = matches.intersection(scoped_ids)
            return next(iter(matches)) if len(matches) == 1 else None

        for relation in relations:
            if not isinstance(relation, Mapping):
                continue
            arguments = relation.get("arguments")
            predicate = str(relation.get("predicate", ""))
            if predicate not in PREDICATES or not isinstance(arguments, list) or len(arguments) != 2:
                continue
            left, right = resolve(arguments[0]), resolve(arguments[1])
            if left is None or right is None:
                continue
            facts.add((predicate, left, right))
            if predicate in symmetric:
                facts.add((predicate, right, left))
    return entities, facts


def _condition_holds(
    predicate: str,
    left_id: str,
    right_id: str,
    entities: Mapping[str, Mapping[str, Any]],
    facts: set[tuple[str, str, str]],
) -> bool | None:
    if (predicate, left_id, right_id) in facts:
        return True
    opposite = {
        "SameOutline": "DifferentOutline",
        "DifferentOutline": "SameOutline",
        "SameInteriorLayout": "DifferentInteriorLayout",
        "DifferentInteriorLayout": "SameInteriorLayout",
        "SameArea": "DifferentArea",
        "DifferentArea": "SameArea",
        "Touches": "Disjoint",
        "Disjoint": "Touches",
    }.get(predicate)
    if opposite is not None and (opposite, left_id, right_id) in facts:
        return False
    left = entities.get(left_id, {}).get("payload", {})
    right = entities.get(right_id, {}).get("payload", {})
    if not isinstance(left, Mapping) or not isinstance(right, Mapping):
        return None
    comparisons = {
        "SameOutline": ("outline_class", True),
        "DifferentOutline": ("outline_class", False),
        "SameInteriorLayout": ("interior_layout_class", True),
        "DifferentInteriorLayout": ("interior_layout_class", False),
        "SameArea": ("area", True),
        "DifferentArea": ("area", False),
    }
    if predicate in comparisons:
        field, equal = comparisons[predicate]
        if field not in left or field not in right:
            return None
        return (left[field] == right[field]) is equal
    if predicate in {"AlignedHorizontal", "AlignedVertical"}:
        left_centroid, right_centroid = left.get("centroid2"), right.get("centroid2")
        if not (
            isinstance(left_centroid, list)
            and isinstance(right_centroid, list)
            and len(left_centroid) == 2
            and len(right_centroid) == 2
        ):
            return None
        axis = 1 if predicate == "AlignedHorizontal" else 0
        return left_centroid[axis] == right_centroid[axis]
    # Contact and temporal predicates require an explicit visible relation.
    return None


def _validate_situated_conditions(
    conditions: Sequence[Mapping[str, Any]],
    assignments: Mapping[str, str],
    turn: CognitionTurn,
) -> None:
    used_variables = _variables_in_conditions(conditions)
    if not used_variables.issubset(assignments):
        raise CognitionError("missing-condition-binding")
    entities, facts = _grounding_view(turn)
    for condition in conditions:
        left_id, right_id = (assignments[str(value)] for value in condition["arguments"])
        if "OPEN" in {left_id, right_id}:
            continue
        result = _condition_holds(
            str(condition["predicate"]), left_id, right_id, entities, facts
        )
        if result is False:
            raise CognitionError("condition-false")
        if result is None:
            raise CognitionError("condition-unverifiable")


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

    object_index = {
        item["id"]: item
        for item in _object_index_documents(turn.document["object_index"])
    }
    visible = {item["id"] for item in turn.document["sparse_cut"]["objects"]}
    if turn.mode == "initial-full" and not turn.id_aliases:
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
            consequence = _validate_consequence(
                item["preferred_consequence"],
                variables,
                operators=CONTROL_OPERATORS,
                measures=CONTROL_MEASURES,
            )
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

    visible_documents = _visible_object_documents(turn)
    existing_schemas = {
        object_id
        for object_id, value in object_index.items()
        if (
            value["kind"] == "schema"
            and object_id in visible
            and isinstance(
                visible_documents.get(object_id, {}).get("payload", {}).get("conditions"),
                list,
            )
        )
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
                    object_id not in visible
                    or object_id not in visible_documents
                    or object_index.get(object_id, {}).get("kind") != "entity"
                ):
                    raise CognitionError("binding-entity-not-visible")
                if object_id != "OPEN" and object_id in assignments.values():
                    raise CognitionError("binding-not-injective")
                assignments[variable] = object_id
            if item["schema_ref"] in local_schemas:
                conditions = local_schemas[item["schema_ref"]]["payload"]["conditions"]
            else:
                schema_document = visible_documents.get(str(item["schema_ref"]), {})
                schema_payload = schema_document.get("payload", {})
                conditions = (
                    schema_payload.get("conditions")
                    if isinstance(schema_payload, Mapping)
                    else None
                )
                if not isinstance(conditions, list):
                    raise CognitionError("schema-conditions-not-visible")
            _validate_situated_conditions(conditions, assignments, turn)
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
    known_expansion_ids = set(object_index).union(alias for alias, _real in turn.id_aliases)
    for index, object_id in enumerate(expansions):
        if object_id not in known_expansion_ids:
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
