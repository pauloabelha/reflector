"""Persistent, action-free Qwen cognition over the shared epistemic graph.

The graph ledger is authoritative.  Qwen receives one complete initial
materialization and thereafter every graph event after its durable cursor in
strict order, plus a bounded dependency-closed attention cut.  Semantic
orientation is persisted as an ordinary zero-support graph object; model KV or
chat context is only a disposable transport cache.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import queue
import re
import sys
import threading
from concurrent.futures import Future
from dataclasses import asdict, dataclass, field
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


REQUEST_PROTOCOL = "shared-attention-qwen-request-v1.4"
RESPONSE_PROTOCOL = "shared-attention-qwen-response-v1.4"
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
17. When a visible structured criticism has status unbound, use its condition_diagnostics and blocking_condition_indices as an executable near-miss report. Remove or replace a blocking condition with a relation verified in the current relation set; do not repeat the unbound conjunction. Prefer a revised conjunction that is currently groundable and isolates one effect pair.
17. A pinned_causal_unit is an exact Qwen-derivation -> semantic-target -> later R2-criticism chain. Read all three exact-canonical objects together. Revise the semantic target in response to that criticism; do not mistake a derivation basis object or an unrelated later write for the criticized target.
18. When revision_task is present, either emit one evidence-citing semantic delta tied to that exact chain, emit bounded competing/open explanations, request expansion, or abstain. Renaming variables, reordering conjunctions, and reversing symmetric arguments are repeats, not revisions.
19. A control revision is valid only when complete visible grounding selects exactly one effect pair. OPEN must name its bounded candidate references. Citations are graph addresses and never empirical support.
20. When revision_task is null, you may bootstrap one initial schema proposal by setting both lineage fields to null and citing visible frame or relational evidence. Never invent lineage for an initial proposal.

In a compact initial materialization, object_columns arrays align by ordinal with object_index.ids. This columnar topology preserves every alias, kind, dependency, digest, creator, revision, and nonzero support entry. Initial attention_rows are explicitly small-lossy aggregates; exact contributions remain in the ledger.

Predicate semantics: Same/DifferentOutline compare outline_class; Same/DifferentInteriorLayout compare interior_layout_class; Same/DifferentArea compare area; AlignedHorizontal/AlignedVertical, Touches, Disjoint, MovedTogether, MovedWhileStationary, and ChangedTogether require the corresponding visible relation fact (alignment may also be derived from centroids). TranslationAlignmentResidual is Manhattan centroid distance. ContactResidual is separation from contact. OverlapResidual is non-overlap. InteriorLayoutDisagreement, OutlineDisagreement, AreaDifference, and EnclosureCountDifference are semantic comparison measures for explanations only.

EPISTEMIC_INPUT:
"""


class CognitionError(ValueError):
    """The canonical graph stream or Qwen write violates the protocol."""


@dataclass(frozen=True, slots=True)
class ContextAdmission:
    """Exact context occupancy for one already-rendered Qwen request."""

    prompt_tokens: int
    reserved_output_tokens: int
    occupied_tokens: int
    context_window_tokens: int
    headroom_tokens: int
    occupancy_fraction: float


class ContextAdmissionError(CognitionError):
    """A complete request plus its output reserve exceeds model context."""

    def __init__(self, report: ContextAdmission) -> None:
        self.report = report
        super().__init__(
            "Qwen context admission failed: "
            f"prompt {report.prompt_tokens} + reserved output "
            f"{report.reserved_output_tokens} = {report.occupied_tokens} exceeds "
            f"context window {report.context_window_tokens} by "
            f"{-report.headroom_tokens} tokens"
        )


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
    # Durable compiler-only facts.  This sidecar is persisted with the turn
    # but request_payload deliberately renders only ``document`` to Qwen.
    validation_context: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class AppliedCompilation:
    state: Any
    events: tuple[Any, ...]
    local_refs: dict[str, str]


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return GRAPH.stable_hash(value)


def admit_request_context(
    request: Mapping[str, Any],
    qwen: Mapping[str, Any],
    *,
    prompt_token_counter: Callable[[Mapping[str, Any]], int],
) -> ContextAdmission:
    """Require exact prompt-plus-output fit before completion transport.

    ``prompt_token_counter`` must count the complete rendered request using the
    serving stack's chat template and multimodal tokenization.  This boundary
    intentionally has no byte/character fallback: image tokens and template
    wrappers make such estimates unsafe for admission.  Reasoning tokens are
    part of the completion and therefore share the single ``max_tokens``
    reserve rather than being counted twice.
    """

    if not callable(prompt_token_counter):
        raise CognitionError("context admission requires an exact prompt token counter")
    context_window = qwen.get("context_window_tokens")
    reserved = request.get("max_tokens")
    configured_reserved = qwen.get("max_tokens", reserved)
    if (
        not isinstance(context_window, int)
        or isinstance(context_window, bool)
        or context_window < 1
    ):
        raise CognitionError("context_window_tokens must be a positive integer")
    if not isinstance(reserved, int) or isinstance(reserved, bool) or reserved < 0:
        raise CognitionError("request max_tokens must be a nonnegative integer")
    if configured_reserved != reserved:
        raise CognitionError("request max_tokens differs from configured output reserve")
    prompt_tokens = prompt_token_counter(request)
    if (
        not isinstance(prompt_tokens, int)
        or isinstance(prompt_tokens, bool)
        or prompt_tokens < 0
    ):
        raise CognitionError("prompt token counter must return a nonnegative integer")
    occupied = prompt_tokens + reserved
    report = ContextAdmission(
        prompt_tokens=prompt_tokens,
        reserved_output_tokens=reserved,
        occupied_tokens=occupied,
        context_window_tokens=context_window,
        headroom_tokens=context_window - occupied,
        occupancy_fraction=occupied / context_window,
    )
    if occupied > context_window:
        raise ContextAdmissionError(report)
    return report


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

    epistemic_kinds = {
        "schema",
        "binding",
        "explanation",
        "prediction",
        "action_proposal",
        "environment_evidence",
        "transition",
        "qwen_orientation",
    }
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


def _projected_object(state: Any, item: Any, *, exact: bool = False) -> dict[str, Any]:
    payload, omitted = _payload_projection(item.kind, item.payload)
    if exact and omitted:
        # Pinned causal objects may never be represented by a lossy semantic
        # projection.  Current derivations target schemas, so this is also a
        # guard against silently broadening the protocol later.
        payload = item.payload
        omitted = []
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
    if exact:
        value["created_revision"] = item.created_revision
        value["fidelity"] = "exact-canonical-object"
    if omitted:
        value["projection"] = {
            "omitted_large_fields": omitted,
            "canonical_object_id": item.object_id,
            "exact_payload_location": "authoritative_graph_ledger",
        }
    return value


def _causal_object_ids(unit: Mapping[str, Any]) -> frozenset[str]:
    return frozenset(
        str(unit[key])
        for key in ("derivation_id", "semantic_target_id", "criticism_id")
    )


def _latest_causal_units(state: Any, invalid: set[str]) -> tuple[dict[str, Any], ...]:
    """Return the newest exact derivation whose target was later criticized.

    Semantic objects deduplicate across calls.  Chronology therefore matters:
    a criticism can result only from a derivation at or before that criticism,
    never from a later alpha-identical write.
    """

    objects = {item.object_id: item for item in state.objects}
    derivations: dict[str, list[Any]] = {}
    for item in state.objects:
        if (
            item.kind != "qwen_derivation"
            or item.created_by != "qwen"
            or item.object_id in invalid
            or item.payload.get("write_kind") != "schema"
        ):
            continue
        target_id = item.identity.get("semantic_object_id")
        if (
            not isinstance(target_id, str)
            or target_id in invalid
            or target_id not in objects
            or target_id not in item.dependency_ids
        ):
            continue
        derivations.setdefault(target_id, []).append(item)

    criticisms = sorted(
        (
            item
            for item in state.objects
            if item.kind == "structured_criticism"
            and item.created_by == "r2"
            and item.object_id not in invalid
        ),
        key=lambda item: (item.created_revision, item.object_id),
        reverse=True,
    )
    for criticism in criticisms:
        target_id = criticism.identity.get("target_id")
        if (
            not isinstance(target_id, str)
            or target_id in invalid
            or target_id not in objects
            or target_id not in criticism.dependency_ids
        ):
            continue
        candidates = [
            item
            for item in derivations.get(target_id, ())
            if item.created_revision <= criticism.created_revision
        ]
        if not candidates:
            continue
        derivation = max(candidates, key=lambda item: (item.created_revision, item.object_id))
        return (
            {
                "protocol": "qwen-r2-causal-unit-v1.0",
                "fidelity": "exact-canonical-objects",
                "derivation_id": derivation.object_id,
                "semantic_target_id": target_id,
                "criticism_id": criticism.object_id,
                "derivation_revision": derivation.created_revision,
                "criticism_revision": criticism.created_revision,
            },
        )
    return ()


def _cut_document(
    state: Any,
    selected_ids: set[str],
    mandatory: Sequence[str],
    causal_units: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    objects = {item.object_id: item for item in state.objects}
    visible_units = [
        dict(unit) for unit in causal_units if _causal_object_ids(unit).issubset(selected_ids)
    ]
    exact_ids = set().union(*(_causal_object_ids(unit) for unit in visible_units)) if visible_units else set()
    return {
        "protocol": "shared-attention-qwen-cut-v1.0",
        "graph_revision": state.revision,
        "objects": [
            _projected_object(
                state, objects[object_id], exact=object_id in exact_ids
            )
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
        "pinned_causal_units": visible_units,
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
    invalid = set(GRAPH.invalidated_ids(state))
    causal_units = _latest_causal_units(state, invalid)
    mandatory = GRAPH.live_binding_ids(state)
    selected = set(GRAPH.dependency_closure(state, mandatory))
    document = finalized(_cut_document(state, selected, mandatory, causal_units), 0)
    required = document["used_tokens"]
    if required > token_budget:
        raise GRAPH.FrontierBudgetError(budget=token_budget, required=required)

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
    causal_roots = tuple(
        object_id for unit in causal_units for object_id in _causal_object_ids(unit)
    )
    essential_roots = tuple(
        dict.fromkeys((*structural_roots, *ambiguity_roots, *causal_roots))
    )
    if ambiguity_roots or causal_units:
        proposed = selected.union(GRAPH.dependency_closure(state, essential_roots))
        candidate = finalized(_cut_document(state, proposed, mandatory, causal_units), 0)
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
        candidate = finalized(
            _cut_document(state, proposed, mandatory, causal_units), len(deferred)
        )
        if candidate["used_tokens"] <= token_budget:
            selected = proposed
            document = candidate
        elif root in priority_roots:
            deferred.append(root)
    document = finalized(
        _cut_document(state, selected, mandatory, causal_units), len(deferred)
    )
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


# ---------------------------------------------------------------------------
# v1.4 semantic-revision boundary
# ---------------------------------------------------------------------------

SYMMETRIC_PREDICATES = frozenset(
    {
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
)
SYMMETRIC_MEASURES = frozenset(
    {
        "TranslationAlignmentResidual",
        "ContactResidual",
        "OverlapResidual",
        "InteriorLayoutDisagreement",
        "OutlineDisagreement",
        "AreaDifference",
        "EnclosureCountDifference",
    }
)
EVIDENCE_KINDS = frozenset(
    {"relation_set", "transition", "environment_evidence", "frame"}
)


def alpha_canonical_schema(value: Mapping[str, Any]) -> dict[str, Any]:
    """Canonicalize a conjunctive schema modulo alpha-renaming and symmetry.

    Condition order has no semantic force.  Argument order is canonicalized
    only for predicates/measures whose protocol semantics are symmetric;
    notably ``MovedWhileStationary`` remains directed.
    """

    conditions = value.get("conditions")
    consequence = value.get("preferred_consequence")
    if not isinstance(conditions, list) or not conditions:
        raise CognitionError("alpha-schema-conditions")
    if not isinstance(consequence, Mapping):
        raise CognitionError("alpha-schema-consequence")
    variables = sorted(
        {
            str(argument)
            for item in (*conditions, consequence)
            for argument in item.get("arguments", ())
        }
    )
    if not variables or any(item not in VARIABLES for item in variables):
        raise CognitionError("alpha-schema-variable")
    canonical_names = VARIABLES[: len(variables)]
    candidates: list[tuple[str, dict[str, Any]]] = []
    for permutation in itertools.permutations(canonical_names):
        renaming = dict(zip(variables, permutation))
        atoms: list[dict[str, Any]] = []
        for raw in conditions:
            atom = _exact(raw, {"predicate", "arguments"}, "condition")
            predicate = str(atom["predicate"])
            arguments = [renaming[str(item)] for item in atom["arguments"]]
            if predicate in SYMMETRIC_PREDICATES:
                arguments.sort()
            atoms.append({"predicate": predicate, "arguments": arguments})
        atoms.sort(key=stable_json)
        if len({stable_json(item) for item in atoms}) != len(atoms):
            raise CognitionError("duplicate-condition-atom")
        normalized_consequence = {
            "operator": str(consequence.get("operator")),
            "measure": str(consequence.get("measure")),
            "arguments": [
                renaming[str(item)] for item in consequence.get("arguments", ())
            ],
        }
        if normalized_consequence["measure"] in SYMMETRIC_MEASURES:
            normalized_consequence["arguments"].sort()
        document = {
            "conditions": atoms,
            "preferred_consequence": normalized_consequence,
        }
        candidates.append((stable_json(document), document))
    if not candidates:
        raise CognitionError("alpha-schema-empty")
    return min(candidates, key=lambda item: item[0])[1]


def alpha_schema_signature(value: Mapping[str, Any]) -> str:
    """Stable semantic signature used for no-alpha-repeat admission."""

    return stable_hash(alpha_canonical_schema(value))


def alpha_equivalent_schema_ids(
    state: Any, schema: Mapping[str, Any]
) -> tuple[str, ...]:
    """Return graph schemas alpha-equivalent to ``schema`` at integration time."""

    signature = alpha_schema_signature(schema)
    matches: list[str] = []
    for item in state.objects:
        if item.kind != "schema":
            continue
        try:
            if alpha_schema_signature(item.payload) == signature:
                matches.append(item.object_id)
        except CognitionError:
            continue
    return tuple(sorted(matches))


def require_integration_alpha_novelty(state: Any, write: Mapping[str, Any]) -> None:
    """Reject a schema that became a repeat after its Qwen basis revision.

    The runner should call this immediately before ``ingest_qwen_writes`` for
    a compiled schema.  This closes the asynchronous turn/integration race
    without making model-visible context authoritative.
    """

    if write.get("kind") != "schema" or not isinstance(write.get("payload"), Mapping):
        raise CognitionError("integration-schema-contract")
    matches = alpha_equivalent_schema_ids(state, write["payload"])
    if matches:
        raise CognitionError(f"integration-alpha-repeat:{matches[0]}")


def explicit_criticism_link(
    derivation_id: str,
    *,
    target_schema: Mapping[str, Any],
    witness: Mapping[str, Any],
    evidence_ids: Sequence[str] = (),
) -> dict[str, Any]:
    """Fields for ``ingest_structured_criticism``'s payload/basis arguments.

    The graph API already inserts the semantic target dependency.  Passing the
    returned ``basis_ids`` adds the exact derivation and cited relational or
    transition evidence; the payload makes that derivation address explicit.
    """

    if not isinstance(derivation_id, str) or not derivation_id:
        raise CognitionError("criticism-derivation-id")
    if not isinstance(target_schema, Mapping):
        raise CognitionError("criticism-target-schema")
    if not isinstance(witness, Mapping):
        raise CognitionError("criticism-witness")
    linked_witness = {
        **dict(witness),
        "target_alpha_signature": alpha_schema_signature(target_schema),
    }
    return {
        "payload": {
            "derivation_id": derivation_id,
            "structured_witness": linked_witness,
        },
        "basis_ids": tuple(
            sorted({derivation_id, *(str(item) for item in evidence_ids)})
        ),
    }


def _criticism_witness(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = payload.get("structured_witness")
    return nested if isinstance(nested, Mapping) else payload


def _candidate_refs(payload: Mapping[str, Any]) -> list[str]:
    witness = _criticism_witness(payload)
    return sorted(
        {
            str(item["candidate_id"])
            for item in witness.get("candidate_substitutions", ())
            if isinstance(item, Mapping) and isinstance(item.get("candidate_id"), str)
        }
    )


def exact_causal_chains(state: Any) -> tuple[dict[str, Any], ...]:
    """Return explicitly linked derivation -> schema -> R2 criticism chains.

    v1.4 intentionally has no chronological fallback.  A criticism that does
    not name and depend on its causal derivation is not a revision task.
    """

    objects = {item.object_id: item for item in state.objects}
    invalid = set(GRAPH.invalidated_ids(state))
    output: list[dict[str, Any]] = []
    for criticism in state.objects:
        if (
            criticism.kind != "structured_criticism"
            or criticism.created_by != "r2"
            or criticism.object_id in invalid
        ):
            continue
        target_id = criticism.identity.get("target_id")
        derivation_id = criticism.identity.get(
            "derivation_id",
            criticism.payload.get(
                "derivation_id", criticism.payload.get("responds_to_derivation_id")
            ),
        )
        if not isinstance(target_id, str) or not isinstance(derivation_id, str):
            continue
        target = objects.get(target_id)
        derivation = objects.get(derivation_id)
        if (
            target is None
            or target.kind != "schema"
            or target.created_by != "qwen"
            or target_id in invalid
            or derivation is None
            or derivation.kind != "qwen_derivation"
            or derivation.created_by != "qwen"
            or derivation_id in invalid
            or derivation.identity.get("semantic_object_id") != target_id
            or target_id not in derivation.dependency_ids
            or target_id not in criticism.dependency_ids
            or derivation_id not in criticism.dependency_ids
            or derivation.created_revision >= criticism.created_revision
        ):
            continue
        try:
            target_signature = alpha_schema_signature(target.payload)
        except CognitionError:
            continue
        witness = _criticism_witness(criticism.payload)
        witness_signature = witness.get("target_alpha_signature")
        # A legacy template hash may be used only when it is already the exact
        # alpha signature.  Object IDs/controller hashes are not silently
        # treated as equivalent semantic proofs.
        if witness_signature is None:
            witness_signature = witness.get("template_hash")
        if witness_signature != target_signature:
            continue
        chain_ref = f"c:{stable_hash({'d': derivation_id, 't': target_id, 'c': criticism.object_id, 'dr': derivation.created_revision, 'cr': criticism.created_revision})[:24]}"
        output.append(
            {
                "protocol": "qwen-r2-causal-unit-v1.4",
                "fidelity": "exact-canonical-objects",
                "chain_ref": chain_ref,
                "derivation_id": derivation_id,
                "semantic_target_id": target_id,
                "criticism_id": criticism.object_id,
                "derivation_revision": derivation.created_revision,
                "criticism_revision": criticism.created_revision,
                "criticism_status": criticism.payload.get(
                    "status", criticism.identity.get("status")
                ),
                "target_alpha_signature": target_signature,
                "candidate_refs": _candidate_refs(criticism.payload),
            }
        )
    output.sort(
        key=lambda item: (
            int(item["criticism_revision"]),
            str(item["criticism_id"]),
        ),
        reverse=True,
    )
    return tuple(output[:1])


def prospective_evidence_after(
    state: Any, *, criticism_revision: int
) -> tuple[str, ...]:
    """Environment evidence with directly addressable prospective ancestry."""

    objects = {item.object_id: item for item in state.objects}
    output: list[str] = []
    for item in state.objects:
        if (
            item.kind != "environment_evidence"
            or item.created_by != "environment"
            or item.created_revision <= int(criticism_revision)
            or item.payload.get("prospective") is None
        ):
            continue
        dependency_kinds = {
            objects[dependency].kind
            for dependency in item.dependency_ids
            if dependency in objects
        }
        if {"prediction", "action_proposal"}.issubset(dependency_kinds):
            output.append(item.object_id)
    return tuple(sorted(output))


# sparse_cut resolves this global at call time; replacing the heuristic here
# upgrades the inherited frontier implementation without changing its budget,
# closure, compression, or pinning mechanics.
def _latest_causal_units(state: Any, invalid: set[str]) -> tuple[dict[str, Any], ...]:
    return tuple(
        item
        for item in exact_causal_chains(state)
        if not (_causal_object_ids(item) & invalid)
    )


_BUILD_TURN_V13 = build_turn


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
    """Build the inherited bounded turn plus a compact explicit revision task."""

    base = _BUILD_TURN_V13(
        state,
        events,
        orientation,
        request_id=request_id,
        token_budget=token_budget,
        max_deltas=max_deltas,
        compact_ids=compact_ids,
    )
    units = base.document["sparse_cut"].get("pinned_causal_units", ())
    revision_task = None
    if units:
        unit = dict(units[0])
        revision_task = {
            key: unit[key]
            for key in (
                "chain_ref",
                "derivation_id",
                "semantic_target_id",
                "criticism_id",
                "criticism_status",
                "target_alpha_signature",
                "candidate_refs",
            )
        }
    document = {**base.document, "revision_task": revision_task}
    signature_rows = []
    for item in state.objects:
        if item.kind != "schema":
            continue
        try:
            signature_rows.append(
                [item.object_id, alpha_schema_signature(item.payload)]
            )
        except CognitionError:
            continue
    visible_aliases = {
        str(item["id"]) for item in document["sparse_cut"].get("objects", ())
    }
    real_to_alias = {real: alias for alias, real in base.id_aliases}
    qualifying_prospective: list[str] = []
    exact_units = exact_causal_chains(state)
    if exact_units:
        for object_id in prospective_evidence_after(
            state,
            criticism_revision=int(exact_units[0]["criticism_revision"]),
        ):
            rendered = real_to_alias.get(object_id, object_id)
            if rendered in visible_aliases:
                qualifying_prospective.append(rendered)
    return CognitionTurn(
        request_id=base.request_id,
        workspace_id=base.workspace_id,
        basis_revision=base.basis_revision,
        basis_hash=base.basis_hash,
        mode=base.mode,
        document=document,
        id_aliases=base.id_aliases,
        validation_context={
            "schema_alpha_signatures": signature_rows,
            "exact_causal_chains": list(exact_units),
            "visible_post_criticism_prospective_evidence_ids": sorted(
                qualifying_prospective
            ),
        },
    )


def _v14_visible(turn: CognitionTurn) -> tuple[dict[str, dict[str, str]], set[str]]:
    object_index = {
        item["id"]: item
        for item in _object_index_documents(turn.document["object_index"])
    }
    visible = {str(item["id"]) for item in turn.document["sparse_cut"]["objects"]}
    if turn.mode == "initial-full" and not turn.id_aliases:
        visible.update(object_index)
    for delta in turn.document.get("ordered_lossless_deltas", ()):
        if isinstance(delta, Mapping) and "payload_json" in delta:
            item = json.loads(str(delta["payload_json"])).get("item", {})
            visible.update(
                str(item[key])
                for key in ("object_id", "source_id", "target_id")
                if key in item
            )
        elif isinstance(delta, list) and delta:
            if delta[0] == "O" and len(delta) >= 2:
                visible.add(str(delta[1]))
            elif delta[0] == "E" and len(delta) >= 4:
                visible.update((str(delta[2]), str(delta[3])))
            elif delta[0] == "A" and len(delta) >= 3:
                visible.add(str(delta[2]))
    visible.intersection_update(object_index)
    return object_index, visible


def _nullable(schema: Mapping[str, Any]) -> dict[str, Any]:
    return {"oneOf": [{"type": "null"}, dict(schema)]}


def response_schema(turn: CognitionTurn) -> dict[str, Any]:
    """Strict bounded v1.4 write grammar."""

    object_index, visible = _v14_visible(turn)
    documents = _visible_object_documents(turn)
    entity_ids = sorted(
        object_id
        for object_id in visible
        if object_index[object_id]["kind"] == "entity" and object_id in documents
    )
    evidence_ids = sorted(
        object_id
        for object_id in visible
        if object_index[object_id]["kind"] in EVIDENCE_KINDS
    )
    visible_schema_ids = sorted(
        object_id
        for object_id in visible
        if object_index[object_id]["kind"] == "schema" and object_id in documents
    )
    visible_id_schema = (
        {"enum": sorted(visible)}
        if visible
        else {"type": "string", "maxLength": 0}
    )
    entity_id_schema = (
        {"enum": entity_ids}
        if entity_ids
        else {"type": "string", "maxLength": 0}
    )
    evidence_id_schema = (
        {"enum": evidence_ids}
        if evidence_ids
        else {"type": "string", "maxLength": 0}
    )
    task = turn.document.get("revision_task")
    candidate_refs = list(task.get("candidate_refs", ())) if isinstance(task, Mapping) else []
    candidate_schema = (
        {"enum": candidate_refs}
        if candidate_refs
        else {"type": "string", "maxLength": 0}
    )
    target_id = task.get("semantic_target_id") if isinstance(task, Mapping) else None
    chain_ref = task.get("chain_ref") if isinstance(task, Mapping) else None
    revision_schema: dict[str, Any]
    if isinstance(target_id, str) and isinstance(chain_ref, str):
        revision_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "local_ref",
                "chain_ref",
                "revises_schema_id",
                "conditions",
                "preferred_consequence",
                "evidence_ids",
            ],
            "properties": {
                "local_ref": {"const": "s0"},
                "chain_ref": {"const": chain_ref},
                "revises_schema_id": {"const": target_id},
                "conditions": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": _atom_schema(),
                },
                "preferred_consequence": _consequence_schema(
                    operators=CONTROL_OPERATORS, measures=CONTROL_MEASURES
                ),
                "evidence_ids": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "uniqueItems": True,
                    "items": evidence_id_schema,
                },
            },
        }
    else:
        revision_schema = {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "local_ref",
                "chain_ref",
                "revises_schema_id",
                "conditions",
                "preferred_consequence",
                "evidence_ids",
            ],
            "properties": {
                "local_ref": {"const": "s0"},
                "chain_ref": {"type": "null"},
                "revises_schema_id": {"type": "null"},
                "conditions": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 4,
                    "items": _atom_schema(),
                },
                "preferred_consequence": _consequence_schema(
                    operators=CONTROL_OPERATORS, measures=CONTROL_MEASURES
                ),
                "evidence_ids": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 3,
                    "items": evidence_id_schema,
                },
            },
        }

    concrete_binding = {
        "type": "object",
        "additionalProperties": False,
        "required": ["variable", "object_id"],
        "properties": {
            "variable": {"enum": list(VARIABLES)},
            "object_id": entity_id_schema,
        },
    }
    open_binding = {
        "type": "object",
        "additionalProperties": False,
        "required": ["variable", "object_id", "candidate_refs"],
        "properties": {
            "variable": {"enum": list(VARIABLES)},
            "object_id": {"const": "OPEN"},
            "candidate_refs": {
                "type": "array",
                "minItems": 2,
                "maxItems": 6,
                "items": candidate_schema,
            },
        },
    }
    alternative = {
        "type": "object",
        "additionalProperties": False,
        "required": ["local_ref", "bindings", "claim", "evidence_ids"],
        "properties": {
            "local_ref": {"enum": ["e0", "e1"]},
            "bindings": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "items": {"oneOf": [concrete_binding, open_binding]},
            },
            "claim": _consequence_schema(),
            "evidence_ids": {
                "type": "array",
                "minItems": 1,
                "maxItems": 3,
                "uniqueItems": True,
                "items": evidence_id_schema,
            },
        },
    }
    observed_discriminator = {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "kind",
            "predicate",
            "arguments",
            "truth_by_alternative",
            "evidence_id",
        ],
        "properties": {
            "kind": {"const": "observed_relation"},
            "predicate": {"enum": list(PREDICATES)},
            "arguments": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"enum": list(VARIABLES)},
            },
            "truth_by_alternative": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["alternative_ref", "value"],
                    "properties": {
                        "alternative_ref": {"enum": ["e0", "e1"]},
                        "value": {"type": "boolean"},
                    },
                },
            },
            "evidence_id": evidence_id_schema,
        },
    }
    open_discriminator = {
        "type": "object",
        "additionalProperties": False,
        "required": ["kind", "variable", "candidate_refs", "basis_id"],
        "properties": {
            "kind": {"const": "open_port"},
            "variable": {"enum": list(VARIABLES)},
            "candidate_refs": {
                "type": "array",
                "minItems": 2,
                "maxItems": 6,
                "items": candidate_schema,
            },
            "basis_id": {"const": task.get("criticism_id") if isinstance(task, Mapping) else ""},
        },
    }
    schema_refs = ["s0", *visible_schema_ids]
    if isinstance(target_id, str) and target_id not in schema_refs:
        schema_refs.append(target_id)
    single_set = {
        "type": "object",
        "additionalProperties": False,
        "required": ["mode", "schema_ref", "alternatives", "discriminator"],
        "properties": {
            "mode": {"const": "single"},
            "schema_ref": {"enum": schema_refs},
            "alternatives": {
                "type": "array",
                "minItems": 1,
                "maxItems": 1,
                "items": alternative,
            },
            "discriminator": {"type": "null"},
        },
    }
    competing_set = {
        "type": "object",
        "additionalProperties": False,
        "required": ["mode", "schema_ref", "alternatives", "discriminator"],
        "properties": {
            "mode": {"const": "competing"},
            "schema_ref": {"enum": schema_refs},
            "alternatives": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": alternative,
            },
            "discriminator": {
                "oneOf": [observed_discriminator, open_discriminator]
            },
        },
    }
    attention = {
        "type": "object",
        "additionalProperties": False,
        "required": ["object_id", "weight", "channel", "basis_ids"],
        "properties": {
            "object_id": visible_id_schema,
            "weight": {"type": "integer", "minimum": 1, "maximum": 100},
            "channel": {"enum": list(ATTENTION_CHANNELS)},
            "basis_ids": {
                "type": "array",
                "maxItems": 4,
                "items": visible_id_schema,
            },
        },
    }
    expansion_ids = [item["id"] for item in _object_index_documents(turn.document["object_index"])]
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "protocol",
            "request_id",
            "basis_revision",
            "schema_revision",
            "explanation_set",
            "attention_contributions",
            "expansion_requests",
        ],
        "properties": {
            "protocol": {"const": RESPONSE_PROTOCOL},
            "request_id": {"const": turn.request_id},
            "basis_revision": {"const": turn.basis_revision},
            "schema_revision": _nullable(revision_schema),
            "explanation_set": {
                "oneOf": [{"type": "null"}, single_set, competing_set]
            },
            "attention_contributions": {
                "type": "array",
                "maxItems": MAX_ATTENTION_WRITES,
                "items": attention,
            },
            "expansion_requests": {
                "type": "array",
                "maxItems": MAX_EXPANSIONS,
                "items": (
                    {"enum": expansion_ids}
                    if expansion_ids
                    else {"type": "string", "maxLength": 0}
                ),
            },
        },
    }


def _v14_exact_list(
    value: Any,
    *,
    minimum: int,
    maximum: int,
    label: str,
) -> list[Any]:
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise CognitionError(f"{label}-cap")
    return value


def _v14_evidence(
    value: Any,
    object_index: Mapping[str, Mapping[str, str]],
    visible: set[str],
) -> list[str]:
    items = _v14_exact_list(value, minimum=1, maximum=3, label="evidence")
    if len(set(items)) != len(items):
        raise CognitionError("duplicate-evidence-id")
    for object_id in items:
        if (
            object_id not in visible
            or object_index.get(str(object_id), {}).get("kind") not in EVIDENCE_KINDS
        ):
            raise CognitionError("evidence-not-visible")
    return [str(item) for item in items]


def _v14_candidate_rows(turn: CognitionTurn) -> dict[str, Mapping[str, Any]]:
    task = turn.document.get("revision_task")
    if not isinstance(task, Mapping):
        return {}
    criticism_id = str(task.get("criticism_id", ""))
    criticism = _visible_object_documents(turn).get(criticism_id, {})
    payload = criticism.get("payload", {})
    witness = _criticism_witness(payload) if isinstance(payload, Mapping) else {}
    return {
        str(item["candidate_id"]): item
        for item in witness.get("candidate_substitutions", ())
        if isinstance(item, Mapping) and isinstance(item.get("candidate_id"), str)
    }


def _v14_candidate_assignment(row: Mapping[str, Any]) -> dict[str, str]:
    output: dict[str, str] = {}
    for pair in row.get("substitution", ()):
        if isinstance(pair, list) and len(pair) == 2:
            output[str(pair[0])] = str(pair[1])
    return output


def _validate_unique_revision(
    conditions: Sequence[Mapping[str, Any]], turn: CognitionTurn
) -> None:
    task = turn.document.get("revision_task")
    if not isinstance(task, Mapping):
        raise CognitionError("revision-task-absent")
    criticism = _visible_object_documents(turn).get(str(task["criticism_id"]), {})
    payload = criticism.get("payload", {})
    witness = _criticism_witness(payload) if isinstance(payload, Mapping) else {}
    if any(
        bool(witness.get(key))
        for key in (
            "enumeration_truncated",
            "candidate_substitutions_truncated",
            "effect_pairs_truncated",
        )
    ):
        raise CognitionError("grounding-validation-truncated")
    rows = list(_v14_candidate_rows(turn).values())
    if len(rows) < 2:
        raise CognitionError("grounding-candidates-insufficient")
    entities, facts = _grounding_view(turn)
    original_pairs = {
        tuple(sorted(str(item) for item in row.get("effect_pair", ())))
        for row in rows
        if len(row.get("effect_pair", ())) == 2
    }
    retained: set[tuple[str, str]] = set()
    for row in rows:
        assignment = _v14_candidate_assignment(row)
        keep = True
        for condition in conditions:
            arguments = [str(item) for item in condition["arguments"]]
            if any(variable not in assignment for variable in arguments):
                raise CognitionError("grounding-validation-missing-variable")
            result = _condition_holds(
                str(condition["predicate"]),
                assignment[arguments[0]],
                assignment[arguments[1]],
                entities,
                facts,
            )
            if result is None:
                raise CognitionError("grounding-validation-unknown")
            if not result:
                keep = False
                break
        if keep:
            pair = tuple(sorted(str(item) for item in row.get("effect_pair", ())))
            if len(pair) == 2:
                retained.add(pair)
    if len(original_pairs) < 2 or len(retained) != 1 or retained == original_pairs:
        raise CognitionError("grounding-not-unique")


def _v14_bindings(
    raw_bindings: Any,
    *,
    turn: CognitionTurn,
    conditions: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    bindings = _v14_exact_list(raw_bindings, minimum=1, maximum=3, label="binding")
    object_index, visible = _v14_visible(turn)
    documents = _visible_object_documents(turn)
    candidates = _v14_candidate_rows(turn)
    assignments: dict[str, str] = {}
    open_domains: dict[str, tuple[str, ...]] = {}
    for raw in bindings:
        if not isinstance(raw, Mapping):
            raise CognitionError("binding-contract")
        variable = str(raw.get("variable"))
        if variable not in VARIABLES or variable in assignments:
            raise CognitionError("binding-variable")
        object_id = str(raw.get("object_id"))
        if object_id == "OPEN":
            item = _exact(raw, {"variable", "object_id", "candidate_refs"}, "open-binding")
            refs = _v14_exact_list(
                item["candidate_refs"], minimum=2, maximum=6, label="open-candidate"
            )
            if len(set(refs)) != len(refs) or any(ref not in candidates for ref in refs):
                raise CognitionError("open-candidate-ref")
            open_domains[variable] = tuple(str(item) for item in refs)
        else:
            _exact(raw, {"variable", "object_id"}, "concrete-binding")
            if (
                object_id not in visible
                or object_id not in documents
                or object_index.get(object_id, {}).get("kind") != "entity"
                or object_id in assignments.values()
            ):
                raise CognitionError("binding-entity-not-visible")
        assignments[variable] = object_id
    if not any(value != "OPEN" for value in assignments.values()):
        raise CognitionError("all-bindings-open")
    used = _variables_in_conditions(conditions)
    if not used.issubset(assignments):
        raise CognitionError("missing-condition-binding")
    concrete = {key: value for key, value in assignments.items() if value != "OPEN"}
    for variable, refs in open_domains.items():
        values: set[str] = set()
        for ref in refs:
            candidate = _v14_candidate_assignment(candidates[ref])
            if any(candidate.get(key) != value for key, value in concrete.items()):
                raise CognitionError("open-candidate-inconsistent")
            if variable not in candidate:
                raise CognitionError("open-candidate-missing-variable")
            values.add(candidate[variable])
        if len(values) < 2:
            raise CognitionError("open-domain-not-competing")
    _validate_situated_conditions(conditions, assignments, turn)
    return assignments, open_domains


def compile_response(response: Mapping[str, Any], turn: CognitionTurn) -> dict[str, Any]:
    """Compile strict v1.4 semantic revisions and bounded explanations."""

    parsed = response.get("parsed", response)
    keys = {
        "protocol",
        "request_id",
        "basis_revision",
        "schema_revision",
        "explanation_set",
        "attention_contributions",
        "expansion_requests",
    }
    if not isinstance(parsed, Mapping) or set(parsed) != keys:
        return {
            "valid_json_contract": False,
            "accepted": [],
            "rejected": [{"reason": "top-level-contract"}],
        }
    if (
        parsed["protocol"] != RESPONSE_PROTOCOL
        or parsed["request_id"] != turn.request_id
        or parsed["basis_revision"] != turn.basis_revision
    ):
        return {
            "valid_json_contract": False,
            "accepted": [],
            "rejected": [{"reason": "basis-contract"}],
        }
    if _forbidden(parsed):
        return {
            "valid_json_contract": False,
            "accepted": [],
            "rejected": [{"reason": "forbidden-action-game-or-authority-token"}],
        }

    object_index, visible = _v14_visible(turn)
    documents = _visible_object_documents(turn)
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    local_schema: dict[str, Any] | None = None
    task = turn.document.get("revision_task")

    raw_revision = parsed["schema_revision"]
    if raw_revision is not None:
        try:
            revision = _exact(
                raw_revision,
                {
                    "local_ref",
                    "chain_ref",
                    "revises_schema_id",
                    "conditions",
                    "preferred_consequence",
                    "evidence_ids",
                },
                "schema-revision",
            )
            is_revision = isinstance(task, Mapping)
            if revision["local_ref"] != "s0":
                raise CognitionError("schema-local-ref")
            if is_revision:
                if (
                    revision["chain_ref"] != task["chain_ref"]
                    or revision["revises_schema_id"]
                    != task["semantic_target_id"]
                ):
                    raise CognitionError("causal-chain-mismatch")
            elif (
                revision["chain_ref"] is not None
                or revision["revises_schema_id"] is not None
            ):
                raise CognitionError("initial-proposal-lineage-must-be-null")
            conditions = _v14_exact_list(
                revision["conditions"], minimum=1, maximum=4, label="condition"
            )
            for condition in conditions:
                atom = _exact(condition, {"predicate", "arguments"}, "condition")
                if atom["predicate"] not in PREDICATES:
                    raise CognitionError("unknown-predicate")
                if (
                    not isinstance(atom["arguments"], list)
                    or len(atom["arguments"]) != 2
                    or any(item not in VARIABLES for item in atom["arguments"])
                ):
                    raise CognitionError("condition-arguments")
            variables = _variables_in_conditions(conditions)
            consequence = _validate_consequence(
                revision["preferred_consequence"],
                variables,
                operators=CONTROL_OPERATORS,
                measures=CONTROL_MEASURES,
            )
            evidence_ids = _v14_evidence(
                revision["evidence_ids"], object_index, visible
            )
            if is_revision and not any(
                object_index[object_id]["kind"] == "relation_set"
                for object_id in evidence_ids
            ):
                raise CognitionError("missing-relation-evidence-citation")
            prospective_ids = {
                str(item)
                for item in turn.validation_context.get(
                    "visible_post_criticism_prospective_evidence_ids", ()
                )
            }
            if is_revision and prospective_ids and prospective_ids.isdisjoint(
                evidence_ids
            ):
                raise CognitionError("missing-prospective-evidence-citation")
            candidate_schema = {
                "conditions": conditions,
                "preferred_consequence": consequence,
            }
            signature = alpha_schema_signature(candidate_schema)
            prior_signatures = {
                str(row[1])
                for row in turn.validation_context.get(
                    "schema_alpha_signatures", ()
                )
                if isinstance(row, (list, tuple)) and len(row) == 2
            }
            if signature in prior_signatures or (
                is_revision and signature == task["target_alpha_signature"]
            ):
                raise CognitionError("alpha-repeat")
            lineage: list[str] = []
            if is_revision:
                _validate_unique_revision(conditions, turn)
                lineage = [
                    str(task["derivation_id"]),
                    str(task["semantic_target_id"]),
                    str(task["criticism_id"]),
                ]
            semantic_payload = {
                "conditions": conditions,
                "preferred_consequence": consequence,
                "provenance": "externally-proposed",
                "alpha_signature": signature,
            }
            if is_revision:
                semantic_payload.update(
                    {
                        "revision_of": str(task["semantic_target_id"]),
                        "causal_chain_ref": str(task["chain_ref"]),
                    }
                )
            local_schema = {
                "kind": "schema",
                "local_ref": "s0",
                "identity": {
                    "origin": "qwen",
                    "conditions": conditions,
                    "preferred_consequence": consequence,
                },
                "payload": semantic_payload,
                "dependency_ids": sorted(set((*lineage, *evidence_ids))),
                "support": 0,
                "evidence": [],
            }
            accepted.append(local_schema)
        except (CognitionError, KeyError, TypeError) as error:
            rejected.append(
                {
                    "kind": "schema",
                    "index": 0,
                    "reason": str(error),
                    "raw": raw_revision,
                }
            )

    raw_set = parsed["explanation_set"]
    explanation_records: list[dict[str, Any]] = []
    if raw_set is not None:
        try:
            explanation_set = _exact(
                raw_set,
                {"mode", "schema_ref", "alternatives", "discriminator"},
                "explanation-set",
            )
            mode = str(explanation_set["mode"])
            expected_count = 1 if mode == "single" else 2 if mode == "competing" else 0
            if expected_count == 0:
                raise CognitionError("explanation-mode")
            alternatives = _v14_exact_list(
                explanation_set["alternatives"],
                minimum=expected_count,
                maximum=expected_count,
                label="explanation",
            )
            schema_ref = str(explanation_set["schema_ref"])
            if schema_ref == "s0":
                if local_schema is None:
                    raise CognitionError("unknown-schema-ref")
                conditions = local_schema["payload"]["conditions"]
            else:
                schema_document = documents.get(schema_ref)
                if (
                    schema_ref not in visible
                    or object_index.get(schema_ref, {}).get("kind") != "schema"
                    or not isinstance(schema_document, Mapping)
                ):
                    raise CognitionError("unknown-schema-ref")
                conditions = schema_document.get("payload", {}).get("conditions")
                if not isinstance(conditions, list):
                    raise CognitionError("schema-conditions-not-visible")
            seen_refs: set[str] = set()
            signatures: set[str] = set()
            compiled_alternatives: list[dict[str, Any]] = []
            assignment_by_ref: dict[str, dict[str, str]] = {}
            open_by_ref: dict[str, dict[str, tuple[str, ...]]] = {}
            for raw in alternatives:
                alternative = _exact(
                    raw,
                    {"local_ref", "bindings", "claim", "evidence_ids"},
                    "explanation",
                )
                local_ref = str(alternative["local_ref"])
                if local_ref not in {"e0", "e1"} or local_ref in seen_refs:
                    raise CognitionError("explanation-local-ref")
                seen_refs.add(local_ref)
                assignments, open_domains = _v14_bindings(
                    alternative["bindings"], turn=turn, conditions=conditions
                )
                claim = _validate_consequence(
                    alternative["claim"], set(assignments)
                )
                evidence_ids = _v14_evidence(
                    alternative["evidence_ids"], object_index, visible
                )
                alternative_signature = stable_json(
                    {
                        "assignments": assignments,
                        "open_domains": open_domains,
                        "claim": claim,
                    }
                )
                if alternative_signature in signatures:
                    raise CognitionError("duplicate-explanation-alternative")
                signatures.add(alternative_signature)
                assignment_by_ref[local_ref] = assignments
                open_by_ref[local_ref] = open_domains
                compiled_alternatives.append(
                    {
                        "kind": "explanation",
                        "local_ref": local_ref,
                        "schema_ref": schema_ref,
                        "identity": {
                            "origin": "qwen",
                            "schema_ref": schema_ref,
                            "bindings": assignments,
                            "open_candidate_refs": open_domains,
                        },
                        "payload": {
                            "bindings": assignments,
                            "open_ports": sorted(open_domains),
                            "open_candidate_refs": open_domains,
                            "claim": claim,
                            "competition_mode": mode,
                            "provenance": "externally-proposed",
                        },
                        "dependency_ids": sorted(
                            set(
                                (
                                    *evidence_ids,
                                    *(
                                        value
                                        for value in assignments.values()
                                        if value != "OPEN"
                                    ),
                                    *(() if schema_ref == "s0" else (schema_ref,)),
                                )
                            )
                        ),
                        "support": 0,
                        "evidence": [],
                    }
                )
            discriminator = explanation_set["discriminator"]
            if mode == "single":
                if discriminator is not None:
                    raise CognitionError("single-discriminator")
            else:
                if not isinstance(discriminator, Mapping):
                    raise CognitionError("competing-discriminator")
                kind = str(discriminator.get("kind"))
                if kind == "observed_relation":
                    item = _exact(
                        discriminator,
                        {
                            "kind",
                            "predicate",
                            "arguments",
                            "truth_by_alternative",
                            "evidence_id",
                        },
                        "observed-discriminator",
                    )
                    predicate = str(item["predicate"])
                    arguments = item["arguments"]
                    if (
                        predicate not in PREDICATES
                        or not isinstance(arguments, list)
                        or len(arguments) != 2
                    ):
                        raise CognitionError("discriminator-predicate")
                    _v14_evidence([item["evidence_id"]], object_index, visible)
                    if object_index[str(item["evidence_id"])]["kind"] != "relation_set":
                        raise CognitionError("discriminator-needs-relation-set")
                    rows = _v14_exact_list(
                        item["truth_by_alternative"],
                        minimum=2,
                        maximum=2,
                        label="discriminator-truth",
                    )
                    stated: dict[str, bool] = {}
                    entities, facts = _grounding_view(turn)
                    for raw in rows:
                        row = _exact(
                            raw, {"alternative_ref", "value"}, "discriminator-truth"
                        )
                        ref = str(row["alternative_ref"])
                        if ref in stated or ref not in assignment_by_ref or not isinstance(row["value"], bool):
                            raise CognitionError("discriminator-truth-ref")
                        assignment = assignment_by_ref[ref]
                        if any(
                            variable not in assignment or assignment[variable] == "OPEN"
                            for variable in arguments
                        ):
                            raise CognitionError("discriminator-open-variable")
                        actual = _condition_holds(
                            predicate,
                            assignment[str(arguments[0])],
                            assignment[str(arguments[1])],
                            entities,
                            facts,
                        )
                        if actual is None or bool(row["value"]) is not actual:
                            raise CognitionError("discriminator-not-evidenced")
                        stated[ref] = actual
                    if set(stated) != set(assignment_by_ref) or len(set(stated.values())) != 2:
                        raise CognitionError("discriminator-not-distinguishing")
                elif kind == "open_port":
                    item = _exact(
                        discriminator,
                        {"kind", "variable", "candidate_refs", "basis_id"},
                        "open-discriminator",
                    )
                    if not isinstance(task, Mapping) or item["basis_id"] != task["criticism_id"]:
                        raise CognitionError("open-discriminator-basis")
                    variable = str(item["variable"])
                    refs = tuple(
                        str(value)
                        for value in _v14_exact_list(
                            item["candidate_refs"],
                            minimum=2,
                            maximum=6,
                            label="open-discriminator",
                        )
                    )
                    if not any(
                        variable in domains and set(refs).issubset(domains[variable])
                        for domains in open_by_ref.values()
                    ):
                        raise CognitionError("open-discriminator-domain")
                else:
                    raise CognitionError("competing-discriminator-kind")
            explanation_records = compiled_alternatives
            accepted.extend(compiled_alternatives)
        except (CognitionError, KeyError, TypeError) as error:
            rejected.append(
                {
                    "kind": "explanation_set",
                    "index": 0,
                    "reason": str(error),
                    "raw": raw_set,
                }
            )

    attention = parsed["attention_contributions"]
    if not isinstance(attention, list) or len(attention) > MAX_ATTENTION_WRITES:
        return {
            "valid_json_contract": False,
            "accepted": [],
            "rejected": [{"reason": "attention-cap"}],
        }
    for index, raw in enumerate(attention):
        try:
            item = _exact(
                raw, {"object_id", "weight", "channel", "basis_ids"}, "attention"
            )
            if item["object_id"] not in visible:
                raise CognitionError("attention-object-not-visible")
            if not isinstance(item["weight"], int) or not 1 <= item["weight"] <= 100:
                raise CognitionError("attention-weight")
            if item["channel"] not in ATTENTION_CHANNELS:
                raise CognitionError("attention-channel")
            basis_ids = item["basis_ids"]
            if not isinstance(basis_ids, list) or any(value not in visible for value in basis_ids):
                raise CognitionError("attention-basis-not-visible")
            accepted.append(
                {
                    "kind": "attention",
                    "worker": "qwen",
                    "object_id": item["object_id"],
                    "weight": item["weight"],
                    "channel": item["channel"],
                    "basis_ids": sorted(set(basis_ids)),
                    "support": 0,
                    "evidence": [],
                }
            )
        except (CognitionError, KeyError, TypeError) as error:
            rejected.append(
                {"kind": "attention", "index": index, "reason": str(error), "raw": raw}
            )

    expansions = parsed["expansion_requests"]
    if not isinstance(expansions, list) or len(expansions) > MAX_EXPANSIONS:
        return {
            "valid_json_contract": False,
            "accepted": [],
            "rejected": [{"reason": "expansion-cap"}],
        }
    known = set(object_index).union(alias for alias, _real in turn.id_aliases)
    valid_expansions: list[str] = []
    for index, object_id in enumerate(expansions):
        if object_id not in known:
            rejected.append(
                {
                    "kind": "expansion",
                    "index": index,
                    "reason": "unknown-expansion-id",
                    "raw": object_id,
                }
            )
        else:
            valid_expansions.append(str(object_id))
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
        "schema_revision_accepted": local_schema is not None
        and any(item.get("kind") == "schema" for item in accepted),
        "schema_write_mode": (
            None
            if local_schema is None
            else "revision"
            if isinstance(task, Mapping)
            else "initial-proposal"
        ),
        "explanation_alternative_count": len(explanation_records),
    }
