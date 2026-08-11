"""Bounded, non-recursive ambiguity revision turns.

The ordinary sparse frontier is intentionally dependency closed.  That is a
good default, but a fresh Qwen schema can create many simultaneously-live R2
bindings and a structured criticism whose causal closure repeats both the
proposal-time and criticism-time relational worlds.  This adapter renders the
same revision problem once, as a flat addressable packet.

Canonical graph objects remain authoritative.  Semantic payloads needed by
the grounding compiler are copied exactly; ancestry outside the packet is
retained by stable ID and digest rather than recursively materialized.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


PROTOCOL = "ambiguity-revision-packet-v1.20"
MODE = "ambiguity-revision-packet"
STATUS = "ambiguous-grounding"


class AmbiguityPacketError(ValueError):
    """An eligible ambiguity does not satisfy the packet invariant."""


def _objects(state: Any) -> dict[str, Any]:
    return {item.object_id: item for item in state.objects}


def _project(item: Any, *, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """The smallest exact semantic object understood by the v1.4 compiler."""

    return {
        "id": item.object_id,
        "kind": item.kind,
        "identity": dict(item.identity),
        "payload": dict(item.payload if payload is None else payload),
        "dependencies": list(item.dependency_ids),
    }


def _eligible_unit(qc: Any, state: Any) -> Mapping[str, Any] | None:
    units = [
        item
        for item in qc.exact_causal_chains(state)
        if item.get("criticism_status") == STATUS
    ]
    if not units:
        return None
    return max(
        units,
        key=lambda item: (
            int(item.get("criticism_revision", -1)),
            str(item.get("criticism_id", "")),
        ),
    )


def _content_digest(qc: Any, item: Any) -> str:
    return qc.stable_hash(
        {
            "identity": item.identity,
            "payload": item.payload,
            "dependencies": list(item.dependency_ids),
        }
    )


def _schema_signatures(qc: Any, state: Any) -> list[list[str]]:
    output: list[list[str]] = []
    for item in state.objects:
        if item.kind != "schema":
            continue
        try:
            output.append([item.object_id, qc.alpha_schema_signature(item.payload)])
        except qc.CognitionError:
            continue
    return output


def _compact_criticism_payload(qc: Any, criticism: Any) -> dict[str, Any]:
    """Remove only witness rows exactly duplicated by other packet tables."""

    payload = dict(criticism.payload)
    witness = payload.get("structured_witness")
    if not isinstance(witness, Mapping):
        return payload
    compact = dict(witness)
    # `candidates` is the non-situated view of every live binding and is
    # reconstructed from live_alternatives. `effect_pairs` is reconstructed
    # from candidate_substitutions. Keep every substitution, diagnostic,
    # count, and truncation flag used by the grounding compiler.
    compact.pop("candidates", None)
    compact.pop("effect_pairs", None)
    compact["deduplicated_views"] = {
        "candidates": "ambiguity_revision_packet.live_alternatives",
        "effect_pairs": "structured_witness.candidate_substitutions",
    }
    payload["structured_witness"] = compact
    payload["canonical_payload_digest"] = qc.stable_hash(criticism.payload)
    return payload


def build_packet(qc: Any, state: Any) -> dict[str, Any] | None:
    """Build a semantically exact, flat packet for the latest ambiguity.

    All live bindings of the criticized schema and the complete cited
    relation set are materialized.  Direct dependencies which are not needed
    by the grounding compiler remain losslessly addressable in ``ancestry``.
    """

    unit = _eligible_unit(qc, state)
    if unit is None:
        return None
    objects = _objects(state)
    try:
        target = objects[str(unit["semantic_target_id"])]
        derivation = objects[str(unit["derivation_id"])]
        criticism = objects[str(unit["criticism_id"])]
    except KeyError as error:
        raise AmbiguityPacketError(f"causal unit references missing object: {error}") from error

    live_ids = set(qc.GRAPH.live_binding_ids(state))
    bindings = sorted(
        (
            item
            for item in state.objects
            if item.object_id in live_ids
            and item.kind == "binding"
            and item.payload.get("schema_object_id") == target.object_id
        ),
        key=lambda item: item.object_id,
    )
    if not bindings:
        raise AmbiguityPacketError("ambiguous target has no live bindings")

    relation_sets = sorted(
        (
            objects[value]
            for value in criticism.dependency_ids
            if value in objects and objects[value].kind == "relation_set"
        ),
        key=lambda item: (item.created_revision, item.object_id),
    )
    if not relation_sets:
        # The frozen grounding writer records the observation digest in the
        # criticism but, in its older format, cites schema+derivation rather
        # than the relation object directly.  Resolve that address exactly;
        # never fall back to a merely chronological relation packet.
        observation_digest = criticism.payload.get("observation_digest")
        # Relation sets depend on entities, not directly on their frame.  The
        # identity carries the exact frame address, so use it as the primary
        # frozen-format resolver.
        relation_sets = [
            item
            for item in state.objects
            if item.kind == "relation_set"
            and str(item.identity.get("frame")) in objects
            and objects[str(item.identity["frame"])].payload.get("pixel_digest")
            == observation_digest
        ]
        relation_sets.sort(key=lambda item: (item.created_revision, item.object_id))
    if len(relation_sets) != 1:
        raise AmbiguityPacketError("ambiguity criticism does not resolve one relation set")
    relation = relation_sets[0]
    entities = sorted(
        (
            objects[value]
            for value in relation.dependency_ids
            if value in objects and objects[value].kind == "entity"
        ),
        key=lambda item: item.object_id,
    )
    if len(entities) != len(relation.dependency_ids):
        raise AmbiguityPacketError("relation grounding has a missing/non-entity dependency")
    frame_ids = {
        dependency
        for entity in entities
        for dependency in entity.dependency_ids
        if dependency in objects and objects[dependency].kind == "frame"
    }
    if len(frame_ids) != 1:
        raise AmbiguityPacketError("relation entities do not share exactly one frame")
    frame = objects[next(iter(frame_ids))]

    semantic_nodes = [target, derivation, criticism, *bindings, relation, frame, *entities]
    visible_nodes = [target, derivation, criticism, relation, *entities]
    ancestry_ids = {
        dependency
        for item in semantic_nodes
        for dependency in item.dependency_ids
        if dependency in objects
    } | {item.object_id for item in semantic_nodes}
    ancestry = sorted(
        (objects[value] for value in ancestry_ids),
        key=lambda item: item.object_id,
    )
    binding_keys = sorted(set().union(*(item.payload.keys() for item in bindings)))
    common_binding_payload = {
        key: bindings[0].payload.get(key)
        for key in binding_keys
        if all(item.payload.get(key) == bindings[0].payload.get(key) for item in bindings)
    }
    variable_binding_keys = [key for key in binding_keys if key not in common_binding_payload]
    semantic_ids = {item.object_id for item in semantic_nodes}
    packet: dict[str, Any] = {
        "protocol": PROTOCOL,
        "fidelity": {
            "semantic_payloads": "exact except explicitly deduplicated criticism views",
            "ancestry": "flat stable-ID table; never recursive closure",
            "authority": "immutable epistemic graph ledger",
        },
        "graph_cursor": [int(state.revision), state.head_hash],
        "causal_unit": dict(unit),
        "live_alternatives": {
            "count": len(bindings),
            "common_payload": common_binding_payload,
            "identity_codec": "binding_key := common_payload.schema_object_id + ':' + candidate_id",
            "columns": ["id", *variable_binding_keys],
            "rows": [
                [
                    item.object_id,
                    *(item.payload.get(key) for key in variable_binding_keys),
                ]
                for item in bindings
            ],
            "population_complete": all(
                bool(item.payload.get("population_complete")) for item in bindings
            ),
        },
        "current_grounding": {
            "relation_set_id": relation.object_id,
            "relation_count": len(relation.payload.get("relations", ())),
            "frame_id": frame.object_id,
            "frame_payload": dict(frame.payload),
            "entity_ids": [item.object_id for item in entities],
        },
        "ancestry": {
            "columns": ["id", "kind", "creator", "revision", "dependencies"],
            "rows": [
                [
                    item.object_id,
                    item.kind,
                    item.created_by,
                    item.created_revision,
                    list(item.dependency_ids),
                ]
                for item in ancestry
            ],
            "off_packet_content_digests": [
                [item.object_id, _content_digest(qc, item)]
                for item in ancestry
                if item.object_id not in semantic_ids
            ],
        },
    }
    packet["packet_digest"] = qc.stable_hash(packet)
    # Private construction data is returned separately by deterministic lookup
    # in build_turn; it is deliberately not duplicated in the model packet.
    packet["_visible_ids"] = [item.object_id for item in visible_nodes]
    return packet


def decode_live_alternatives(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Losslessly decode the factored binding rows in a model packet."""

    table = packet["live_alternatives"]
    columns = list(table["columns"])
    common = dict(table["common_payload"])
    output: list[dict[str, Any]] = []
    for raw in table["rows"]:
        row = dict(zip(columns, raw, strict=True))
        object_id = str(row.pop("id"))
        payload = {**common, **row}
        candidate_id = str(payload["candidate_id"])
        identity = {
            "binding_key": f"{payload['schema_object_id']}:{candidate_id}"
        }
        output.append({"id": object_id, "identity": identity, "payload": payload})
    return output


def build_turn(
    qc: Any,
    state: Any,
    orientation: Any,
    *,
    request_id: str,
    token_budget: int,
    compact_ids: bool = False,
) -> Any | None:
    """Create a compiler-compatible ambiguity turn without graph closure."""

    packet = build_packet(qc, state)
    if packet is None:
        return None
    objects = _objects(state)
    visible_ids = tuple(packet.pop("_visible_ids"))
    criticism_id = str(packet["causal_unit"]["criticism_id"])
    visible = [
        _project(
            objects[value],
            payload=(
                _compact_criticism_payload(qc, objects[value])
                if value == criticism_id
                else None
            ),
        )
        for value in visible_ids
    ]
    unit = packet["causal_unit"]

    referenced = set(visible_ids)
    referenced.update(
        dependency for item in visible for dependency in item["dependencies"]
    )
    referenced.update(
        str(row[0]) for row in packet["live_alternatives"]["rows"]
    )
    for row in packet["ancestry"]["rows"]:
        referenced.add(str(row[0]))
        referenced.update(str(value) for value in row[4])
    aliases = qc._stable_aliases(state) if compact_ids else {}
    real_to_alias = (
        {real: alias for real, alias in aliases.items() if real in referenced}
        if compact_ids
        else {value: value for value in referenced}
    )
    rendered_visible = qc._replace_ids(visible, real_to_alias) if compact_ids else visible
    rendered_packet = qc._replace_ids(packet, real_to_alias) if compact_ids else packet
    render = lambda value: str(real_to_alias.get(str(value), str(value)))
    task = {
        key: qc._replace_ids(unit[key], real_to_alias) if compact_ids else unit[key]
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
    document = {
        "protocol": qc.REQUEST_PROTOCOL,
        "request_id": str(request_id),
        "mode": MODE,
        "from_cursor": {
            "revision": orientation.cursor_revision,
            "head_hash": orientation.cursor_hash,
        },
        "through_cursor": qc.cursor_document(state),
        "full_materialization": None,
        "ordered_lossless_deltas": [],
        "delta_codec": {
            "fidelity": "superseded by exact ambiguity packet for this revision turn",
            "authority": "canonical immutable graph ledger",
        },
        "sparse_cut": {
            "protocol": "ambiguity-revision-compiler-view-v1.20",
            "graph_revision": state.revision,
            "objects": rendered_visible,
            "edges": [],
            "mandatory_live_bindings": [
                render(row[0]) for row in packet["live_alternatives"]["rows"]
            ],
            "pinned_causal_units": [],
            "dependency_closed": False,
            "closure_policy": "exact semantic nodes plus flat ancestry; no recursive expansion",
        },
        "object_index": [
            {"id": item["id"], "kind": item["kind"], "dependencies": item["dependencies"]}
            for item in rendered_visible
        ],
        "revision_task": task,
        "ambiguity_revision_packet": rendered_packet,
        "allowed_vocabulary": {
            "variables": list(qc.VARIABLES),
            "predicates": list(qc.PREDICATES),
            "operators": list(qc.OPERATORS),
            "measures": list(qc.MEASURES),
            "attention_channels": list(qc.ATTENTION_CHANNELS),
            "control_gate": {
                "operators": list(qc.CONTROL_OPERATORS),
                "measures": list(qc.CONTROL_MEASURES),
            },
        },
    }
    document["sparse_cut"]["token_budget"] = int(token_budget)
    document["sparse_cut"]["used_tokens"] = 0
    used = 0
    for _ in range(4):
        measured = qc.GRAPH.estimate_tokens(document)
        if measured == used:
            break
        used = measured
        document["sparse_cut"]["used_tokens"] = int(used)
    if used > token_budget:
        raise qc.GRAPH.FrontierBudgetError(budget=token_budget, required=used)

    id_aliases = tuple(
        sorted((alias, real) for real, alias in real_to_alias.items() if alias != real)
    )
    return qc.CognitionTurn(
        request_id=str(request_id),
        workspace_id=orientation.workspace_id,
        basis_revision=state.revision,
        basis_hash=state.head_hash,
        mode=MODE,
        document=document,
        id_aliases=id_aliases,
        validation_context={
            "schema_alpha_signatures": _schema_signatures(qc, state),
            "exact_causal_chains": [dict(unit)],
            "ambiguity_packet_digest": packet["packet_digest"],
            "relation_evidence_id": render(packet["current_grounding"]["relation_set_id"]),
        },
    )


def wrap_build_turn(qc: Any, fallback: Callable[..., Any]) -> Callable[..., Any]:
    def wrapped(
        state: Any,
        events: Sequence[Any],
        orientation: Any,
        *,
        request_id: str,
        token_budget: int,
        max_deltas: int | None = None,
        compact_ids: bool = False,
    ) -> Any:
        turn = build_turn(
            qc,
            state,
            orientation,
            request_id=request_id,
            token_budget=token_budget,
            compact_ids=compact_ids,
        )
        if turn is not None:
            return turn
        kwargs = {
            "request_id": request_id,
            "token_budget": token_budget,
            "compact_ids": compact_ids,
        }
        if max_deltas is not None:
            kwargs["max_deltas"] = max_deltas
        return fallback(state, events, orientation, **kwargs)

    return wrapped


def install(qc: Any) -> Any:
    if getattr(qc, "_AMBIGUITY_PACKET_V120_INSTALLED", False):
        return qc
    qc._AMBIGUITY_PACKET_V120_BASE_BUILD_TURN = qc.build_turn
    qc.build_turn = wrap_build_turn(qc, qc.build_turn)
    qc._AMBIGUITY_PACKET_V120_INSTALLED = True
    return qc


__all__ = [
    "AmbiguityPacketError",
    "MODE",
    "PROTOCOL",
    "build_packet",
    "build_turn",
    "decode_live_alternatives",
    "install",
    "wrap_build_turn",
]
