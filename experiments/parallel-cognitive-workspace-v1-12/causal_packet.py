"""Bounded, exact-field revision capsules over the authoritative graph.

The graph remains the authority.  This module does *not* copy a dependency
closure into a Qwen request.  It renders the one latest evidence-return chain
as an addressable capsule: all facts needed for semantic revision are carried
verbatim, while canonical objects are retained by stable ID, direct ancestry,
and content digests.  An omitted dependency is therefore an address, never a
lossy prose summary and never an invitation to recursively inline the graph.

Stable API:

``build_causal_packet(qc, state)``
    Return the latest exact packet, or ``None`` when no eligible chain exists.

``build_revision_turn(qc, state, orientation, ...)``
    Return a minimal compiler-compatible ``CognitionTurn`` from that packet,
    or ``None``.  This is the closure-bypass boundary used by the runner.

``decode_probe_judgments(packet)``
    Losslessly join the columnar probe/binding tables into situated rows.

``wrap_build_turn(qc, fallback)`` / ``install(qc)``
    Use packet turns for evidence-return revisions and the inherited builder
    for every other cognitive turn.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


PROTOCOL = "exact-causal-revision-packet-v1.12"
STATUS = "prospective-evidence-return"
FIDELITY = (
    "exact semantic fields and direct ancestry; canonical objects remain "
    "addressable by stable graph id"
)


class CausalPacketError(RuntimeError):
    """An eligible causal chain violates the packet contract."""


def _objects(state: Any) -> dict[str, Any]:
    return {str(item.object_id): item for item in state.objects}


def _digest_node(qc: Any, item: Any) -> dict[str, Any]:
    """Exact address and direct ancestry without recursive materialization."""

    return {
        "id": str(item.object_id),
        "kind": str(item.kind),
        "revision": int(item.created_revision),
        "dependencies": [str(value) for value in item.dependency_ids],
    }


def _eligible_unit(qc: Any, state: Any) -> Mapping[str, Any] | None:
    for raw in qc.exact_causal_chains(state):
        if raw.get("criticism_status") == STATUS:
            return raw
    return None


def _witness(qc: Any, item: Any) -> Mapping[str, Any]:
    value = qc._criticism_witness(item.payload)
    if not isinstance(value, Mapping):
        raise CausalPacketError("criticism witness is not a mapping")
    return value


def _latest_ambiguity(
    qc: Any, state: Any, target_id: str, before_revision: int
) -> Any | None:
    candidates = []
    for item in state.objects:
        if (
            item.kind == "structured_criticism"
            and item.created_by == "r2"
            and item.created_revision < before_revision
            and item.identity.get("target_id") == target_id
            and item.payload.get("status") == "ambiguous-grounding"
        ):
            candidates.append(item)
    return max(candidates, key=lambda item: (item.created_revision, item.object_id), default=None)


def _one_dependency(objects: Mapping[str, Any], item: Any, kind: str) -> Any:
    rows = [objects[value] for value in item.dependency_ids if objects[value].kind == kind]
    if len(rows) != 1:
        raise CausalPacketError(f"{item.kind} must cite one {kind}, found {len(rows)}")
    return rows[0]


def _probe_tables(
    objects: Mapping[str, Any],
    evidence_ids: Sequence[str],
    binding_objects: Sequence[Any],
) -> tuple[dict[str, Any], tuple[Any, ...]]:
    """Losslessly join all executed judgments to predictions and transitions."""

    predictions_by_id = {
        str(item.identity["prediction_id"]): item
        for item in objects.values()
        if item.kind == "prediction" and isinstance(item.identity.get("prediction_id"), str)
    }
    graph_binding_by_candidate = {
        str(item.payload["candidate_id"]): item for item in binding_objects
    }
    binding_rows: dict[str, dict[str, Any]] = {}
    probes: list[list[Any]] = []
    judgments: list[dict[str, Any]] = []
    ancestry: dict[str, Any] = {}
    verdict_counts: dict[str, int] = {}

    ordered_evidence = sorted(
        (objects[value] for value in evidence_ids),
        key=lambda item: (item.created_revision, item.object_id),
    )
    for probe_index, evidence in enumerate(ordered_evidence):
        proposal = _one_dependency(objects, evidence, "action_proposal")
        transition = _one_dependency(objects, evidence, "transition")
        before_id = str(transition.payload["before_frame"])
        after_id = str(transition.payload["after_frame"])
        before = objects[before_id]
        after = objects[after_id]
        prospective = evidence.payload.get("prospective")
        if not isinstance(prospective, Mapping) or not isinstance(
            prospective.get("judgments"), list
        ):
            raise CausalPacketError("canonical evidence lacks prospective judgments")
        selected_ids = {str(value) for value in proposal.payload.get("selected_prediction_ids", ())}
        probes.append(
            [
                evidence.object_id,
                proposal.object_id,
                transition.object_id,
                before_id,
                after_id,
                prospective.get("plan_id"),
                prospective.get("basis_revision"),
                evidence.payload.get("level_delta"),
                evidence.payload.get("observation_changed"),
            ]
        )
        ancestry.update(
            {
                item.object_id: item
                for item in (evidence, proposal, transition, before, after)
            }
        )
        for judgment in prospective["judgments"]:
            prediction_id = str(judgment.get("prediction_id"))
            prediction = predictions_by_id.get(prediction_id)
            if prediction is None or prediction.object_id not in evidence.dependency_ids:
                raise CausalPacketError("judgment prediction is not canonical evidence ancestry")
            candidate_id = str(prediction.payload.get("candidate_id"))
            graph_binding = graph_binding_by_candidate.get(candidate_id)
            if graph_binding is None or graph_binding.object_id not in prediction.dependency_ids:
                raise CausalPacketError("prediction cannot be joined to situated binding")
            binding_id = str(judgment.get("binding_id"))
            if prediction.payload.get("binding_id") != binding_id:
                raise CausalPacketError("judgment/prediction binding mismatch")
            binding_rows.setdefault(
                binding_id,
                {
                    "graph_binding_id": graph_binding.object_id,
                    "binding_id": binding_id,
                    "candidate_id": candidate_id,
                    "effect_pair": list(graph_binding.payload["effect_pair"]),
                    "payload": dict(graph_binding.payload),
                },
            )
            verdict = str(judgment.get("status"))
            verdict_counts[verdict] = verdict_counts.get(verdict, 0) + 1
            judgments.append(
                {
                    "probe_index": probe_index,
                    "binding_id": binding_id,
                    "prediction_object_id": prediction.object_id,
                    "prediction_id": prediction_id,
                    "current_residual": prediction.payload.get("current_residual"),
                    "predicted_delta": judgment.get("predicted_delta"),
                    "predicted_residual": judgment.get("predicted_residual"),
                    "observed_delta": judgment.get("observed_delta"),
                    "observed_residual": judgment.get("observed_residual"),
                    "horizon": prediction.payload.get("horizon"),
                    "selected": prediction_id in selected_ids,
                    "modeled": prediction.payload.get("modeled"),
                    "model_support": prediction.payload.get("model_support"),
                    "verdict": verdict,
                    "reason": judgment.get("reason"),
                }
            )
            ancestry[prediction.object_id] = prediction

    ordered_bindings = sorted(binding_rows.values(), key=lambda row: row["binding_id"])
    binding_index = {row["binding_id"]: index for index, row in enumerate(ordered_bindings)}
    judgment_columns = [
        "probe_index",
        "binding_index",
        "prediction_object_id",
        "prediction_id",
        "current_residual",
        "predicted_delta",
        "predicted_residual",
        "observed_delta",
        "observed_residual",
        "horizon",
        "selected",
        "modeled",
        "model_support",
        "verdict",
        "reason",
    ]
    judgment_rows = [
        [
            row["probe_index"],
            binding_index[row["binding_id"]],
            *(row[column] for column in judgment_columns[2:]),
        ]
        for row in judgments
    ]
    return (
        {
            "protocol": "executed-probe-cohorts-exact-v1.12",
            "join": (
                "judgment.probe_index -> probes row; judgment.binding_index -> "
                "bindings row; no row is omitted by verdict or proposal selection"
            ),
            "counts": {
                "probes": len(probes),
                "judgments": len(judgment_rows),
                **dict(sorted(verdict_counts.items())),
            },
            "binding_columns": [
                "graph_binding_id",
                "binding_id",
                "candidate_id",
                "effect_pair",
                "payload",
            ],
            "bindings": [
                [row[column] for column in (
                    "graph_binding_id", "binding_id", "candidate_id", "effect_pair", "payload"
                )]
                for row in ordered_bindings
            ],
            "probe_columns": [
                "evidence_id",
                "proposal_id",
                "transition_id",
                "before_frame_id",
                "after_frame_id",
                "plan_id",
                "basis_revision",
                "level_delta",
                "observation_changed",
            ],
            "probes": probes,
            "judgment_columns": judgment_columns,
            "judgments": judgment_rows,
        },
        tuple(ancestry.values()),
    )


def decode_probe_judgments(packet: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Losslessly expand the columnar probe cohort into twelve situated rows."""

    table = packet.get("executed_probe_judgments")
    if not isinstance(table, Mapping):
        raise CausalPacketError("packet has no executed probe table")
    try:
        probes = [
            dict(zip(table["probe_columns"], row, strict=True))
            for row in table["probes"]
        ]
        bindings = [
            dict(zip(table["binding_columns"], row, strict=True))
            for row in table["bindings"]
        ]
        judgments = [
            dict(zip(table["judgment_columns"], row, strict=True))
            for row in table["judgments"]
        ]
        return [
            {
                **probes[int(row["probe_index"])],
                **bindings[int(row["binding_index"])],
                **row,
            }
            for row in judgments
        ]
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise CausalPacketError("invalid executed probe columnar contract") from error


def build_causal_packet(qc: Any, state: Any) -> dict[str, Any] | None:
    """Render the latest evidence-return chain without dependency expansion.

    The target schema, live bindings, original ambiguity diagnosis, selected
    prospective rows, and current complete relational grounding are exact
    copies from canonical graph objects.  ``node_ancestry`` is deliberately a
    flat table: dependencies may point outside it and remain expandable by ID.
    """

    unit = _eligible_unit(qc, state)
    if unit is None:
        return None
    objects = _objects(state)
    try:
        derivation = objects[str(unit["derivation_id"])]
        target = objects[str(unit["semantic_target_id"])]
        criticism = objects[str(unit["criticism_id"])]
    except KeyError as error:
        raise CausalPacketError(f"causal unit references missing object: {error}") from error

    witness = _witness(qc, criticism)
    grounding = witness.get("grounding_state")
    if not isinstance(grounding, Mapping):
        raise CausalPacketError("evidence-return witness has no grounding state")
    evidence_packet = witness["evidence_packet"]
    evidence_ids = tuple(str(value) for value in evidence_packet.get("evidence_ids", ()))
    binding_objects = sorted(
        (
            item
            for item in state.objects
            if item.kind == "binding"
            and item.payload.get("schema_object_id") == target.object_id
        ),
        key=lambda item: item.object_id,
    )
    if not binding_objects:
        raise CausalPacketError("target schema has no situated bindings")
    executed_probes, probe_ancestry = _probe_tables(
        objects, evidence_ids, binding_objects
    )

    relation_objects = sorted(
        (
            objects[dependency_id]
            for dependency_id in criticism.dependency_ids
            if dependency_id in objects and objects[dependency_id].kind == "relation_set"
        ),
        key=lambda item: (item.created_revision, item.object_id),
    )
    if len(relation_objects) != 1:
        raise CausalPacketError("evidence criticism must cite one current relation set")
    relation_set = relation_objects[0]

    ambiguity = _latest_ambiguity(
        qc, state, target.object_id, int(criticism.created_revision)
    )
    if ambiguity is None:
        raise CausalPacketError("original ambiguity diagnosis is unavailable")
    ambiguity_witness = _witness(qc, ambiguity)

    ancestry_items = [
        derivation,
        target,
        ambiguity,
        criticism,
        relation_set,
        *binding_objects,
        *probe_ancestry,
    ]
    ancestry = {
        item.object_id: _digest_node(qc, item)
        for item in ancestry_items
    }
    packet: dict[str, Any] = {
        "protocol": PROTOCOL,
        "fidelity": FIDELITY,
        "graph_cursor": {
            "revision": int(state.revision),
            "head_hash": state.head_hash,
        },
        "causal_unit": dict(unit),
        "target_schema": {
            "id": target.object_id,
            "payload": dict(target.payload),
        },
        "grounding_diagnostics": {
            "criticism_id": ambiguity.object_id,
            "witness": dict(ambiguity_witness),
        },
        "executed_probe_judgments": executed_probes,
        "current_grounding": dict(grounding),
        "current_relation_set": {
            "id": relation_set.object_id,
            "revision": relation_set.created_revision,
            "content_digest": qc.stable_hash(
                {"identity": relation_set.identity, "payload": relation_set.payload}
            ),
        },
        "node_ancestry": {
            "columns": [
                "id", "kind", "revision", "dependencies"
            ],
            "rows": [
                [row[column] for column in (
                    "id", "kind", "revision", "dependencies"
                )]
                for row in (ancestry[value] for value in sorted(ancestry))
            ],
        },
    }
    packet["packet_digest"] = qc.stable_hash(packet)
    return packet


def _project(item: Any, *, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    return {
        "id": item.object_id,
        "kind": item.kind,
        "creator": item.created_by,
        "revision": item.created_revision,
        "identity": dict(item.identity),
        "payload": dict(item.payload if payload is None else payload),
        "dependencies": list(item.dependency_ids),
    }


def _strings(value: Any) -> set[str]:
    """All scalar strings in a JSON-like value (keys are protocol, not IDs)."""

    if isinstance(value, Mapping):
        return set().union(*(_strings(item) for item in value.values())) if value else set()
    if isinstance(value, (list, tuple)):
        return set().union(*(_strings(item) for item in value)) if value else set()
    return {value} if isinstance(value, str) else set()


def build_revision_turn(
    qc: Any,
    state: Any,
    orientation: Any,
    *,
    request_id: str,
    token_budget: int,
    compact_ids: bool = False,
) -> Any | None:
    """Build a minimal v1.4-compiler-compatible packet turn.

    ``token_budget`` applies to the complete packet document.  The function
    never asks ``dependency_closure`` to expand a referenced object.
    """

    packet = build_causal_packet(qc, state)
    if packet is None:
        return None
    objects = _objects(state)
    unit = packet["causal_unit"]
    criticism = objects[str(unit["criticism_id"])]
    target = objects[str(unit["semantic_target_id"])]
    derivation = objects[str(unit["derivation_id"])]
    witness = _witness(qc, criticism)
    probe_table = packet["executed_probe_judgments"]
    evidence_column = probe_table["probe_columns"].index("evidence_id")
    evidence_ids = tuple(row[evidence_column] for row in probe_table["probes"])
    relation_id = str(packet["current_relation_set"]["id"])

    # The compiler needs semantic bodies only for its target/criticism checks.
    # Evidence and relation nodes are exact citable addresses; their semantic
    # content is already carried once in the packet, avoiding duplication.
    visible_objects = [
        _project(target),
        _project(derivation),
        _project(
            criticism,
            payload={
                "status": STATUS,
                "derivation_id": derivation.object_id,
                "structured_witness": {
                    "protocol": witness.get("protocol"),
                    "status": STATUS,
                    "target_alpha_signature": witness.get("target_alpha_signature"),
                    "effect_variables": witness.get("effect_variables"),
                    "grounding_state": witness.get("grounding_state"),
                },
            },
        ),
        *(
            _project(
                objects[value],
                payload={"canonical_payload_digest": qc.stable_hash(objects[value].payload)},
            )
            for value in evidence_ids
        ),
        _project(
            objects[relation_id],
            payload={"canonical_payload_digest": qc.stable_hash(objects[relation_id].payload)},
        ),
    ]
    real_ids = {str(item["id"]) for item in visible_objects}
    stable_aliases = qc._stable_aliases(state) if compact_ids else {}
    # Alias every canonical graph ID named by the capsule, including direct
    # off-capsule ancestors.  The alias sidecar is not rendered into the Qwen
    # prompt, so this is lossless dictionary compression rather than omission.
    referenced_ids = _strings(packet) | _strings(visible_objects)
    real_to_alias = (
        {
            real: alias
            for real, alias in stable_aliases.items()
            if real in referenced_ids or real in real_ids
        }
        if compact_ids
        else {real: real for real in real_ids}
    )
    rendered_objects = (
        qc._replace_ids(visible_objects, real_to_alias) if compact_ids else visible_objects
    )
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
    } | {
        "causing_evidence_ids": [render(value) for value in evidence_ids],
        "grounding_state_digest": qc.stable_hash(witness["grounding_state"]),
    }
    rendered_relation_id = render(relation_id)
    document = {
        "protocol": qc.REQUEST_PROTOCOL,
        "request_id": str(request_id),
        "mode": "causal-revision-packet",
        "from_cursor": {
            "revision": orientation.cursor_revision,
            "head_hash": orientation.cursor_hash,
        },
        "through_cursor": qc.cursor_document(state),
        "full_materialization": None,
        "ordered_lossless_deltas": [],
        "delta_codec": {
            "fidelity": "deltas superseded by exact addressable causal packet for this revision turn",
            "authority": "canonical immutable graph ledger",
        },
        "sparse_cut": {
            "protocol": "causal-revision-compiler-view-v1.12",
            "graph_revision": state.revision,
                "objects": rendered_objects,
                "edges": [],
                "mandatory_live_bindings": [],
                # The exact unit is carried once in causal_revision_packet and
                # its response-critical fields once in revision_task.
                "pinned_causal_units": [],
            "dependency_closed": False,
            "closure_policy": "stable IDs plus direct ancestry; no recursive materialization",
        },
        "object_index": [
            {
                "id": item["id"],
                "kind": item["kind"],
                "dependencies": item["dependencies"],
            }
            for item in rendered_objects
        ],
        "revision_task": task,
        "causal_revision_packet": rendered_packet,
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
    aliases = tuple(
        sorted((alias, real) for real, alias in real_to_alias.items() if alias != real)
    )
    schema_signatures = []
    for item in state.objects:
        if item.kind == "schema":
            try:
                schema_signatures.append([item.object_id, qc.alpha_schema_signature(item.payload)])
            except qc.CognitionError:
                pass
    return qc.CognitionTurn(
        request_id=str(request_id),
        workspace_id=orientation.workspace_id,
        basis_revision=state.revision,
        basis_hash=state.head_hash,
        mode="causal-revision-packet",
        document=document,
        id_aliases=aliases,
        validation_context={
            "schema_alpha_signatures": schema_signatures,
            "exact_causal_chains": [dict(unit)],
            "evidence_revision_unit": dict(unit),
            "causal_prospective_evidence_ids": [render(value) for value in evidence_ids],
            "visible_post_criticism_prospective_evidence_ids": [
                render(value) for value in evidence_ids
            ],
            "exact_grounding_state_digest": qc.stable_hash(witness["grounding_state"]),
            "causal_packet_digest": packet["packet_digest"],
            "relation_evidence_id": rendered_relation_id,
        },
    )


def wrap_build_turn(qc: Any, fallback: Callable[..., Any]) -> Callable[..., Any]:
    """Prefer a bounded packet turn; preserve inherited behavior otherwise."""

    def build_turn(
        state: Any,
        events: Sequence[Any],
        orientation: Any,
        *,
        request_id: str,
        token_budget: int,
        max_deltas: int | None = None,
        compact_ids: bool = False,
    ) -> Any:
        # The packet is state-derived and cursor-addressed; ``events`` remains
        # available for the inherited fallback when no eligible chain exists.
        packet_turn = build_revision_turn(
            qc,
            state,
            orientation,
            request_id=request_id,
            token_budget=token_budget,
            compact_ids=compact_ids,
        )
        if packet_turn is not None:
            return packet_turn
        kwargs = {
            "request_id": request_id,
            "token_budget": token_budget,
            "compact_ids": compact_ids,
        }
        if max_deltas is not None:
            kwargs["max_deltas"] = max_deltas
        return fallback(state, events, orientation, **kwargs)

    return build_turn


def install(qc: Any) -> Any:
    """Idempotently install the v1.12 closure-bypass builder."""

    if getattr(qc, "_CAUSAL_PACKET_V112_INSTALLED", False):
        return qc
    qc._CAUSAL_PACKET_V112_BASE_BUILD_TURN = qc.build_turn
    qc.build_turn = wrap_build_turn(qc, qc.build_turn)
    qc._CAUSAL_PACKET_V112_INSTALLED = True
    return qc


__all__ = [
    "CausalPacketError",
    "FIDELITY",
    "PROTOCOL",
    "STATUS",
    "build_causal_packet",
    "build_revision_turn",
    "decode_probe_judgments",
    "install",
    "wrap_build_turn",
]
