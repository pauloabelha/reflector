"""Authoritative immutable epistemic graph and worker-specific frontiers.

Objects and edges are append-only.  Empirical support is derived exclusively
from environment-evidence edges; attention can affect a worker's frontier but
can never change support.  All reducers and rankings are deterministic.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from typing import Any, Iterable, Mapping, Sequence

from hashlib import sha256


WORKERS = frozenset({"r2", "qwen"})
CREATORS = frozenset({"r2", "qwen", "environment", "kernel"})
EVENT_TYPES = frozenset({"ObjectAdded", "EdgeAdded", "AttentionContributed"})
EVIDENCE_EDGE_KINDS = frozenset({"supports", "refutes", "invalidates"})
FORBIDDEN_WORKER_PAYLOAD_KEYS = frozenset(
    {"support", "support_count", "evidence_count", "confidence", "confirmed", "refuted"}
)
ATTENTION_HORIZON = 8


class EpistemicGraphError(ValueError):
    """The event or graph violates an epistemic invariant."""


class FrontierBudgetError(EpistemicGraphError):
    """The budget cannot represent every live binding and its dependencies."""

    def __init__(self, *, budget: int, required: int) -> None:
        super().__init__(f"frontier budget {budget} is below mandatory closure cost {required}")
        self.budget = budget
        self.required = required


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return sha256(stable_json(value).encode("utf-8")).hexdigest()


def _canonical_payload(value: Mapping[str, Any]) -> str:
    return stable_json(dict(value))


def _payload(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise EpistemicGraphError("canonical payload is not an object")
    return parsed


@dataclass(frozen=True, slots=True)
class EpistemicObject:
    object_id: str
    kind: str
    created_by: str
    created_revision: int
    identity_json: str
    payload_json: str
    dependency_ids: tuple[str, ...] = ()

    @property
    def identity(self) -> dict[str, Any]:
        return _payload(self.identity_json)

    @property
    def payload(self) -> dict[str, Any]:
        return _payload(self.payload_json)


@dataclass(frozen=True, slots=True)
class EpistemicEdge:
    edge_id: str
    kind: str
    source_id: str
    target_id: str
    created_by: str
    created_revision: int
    payload_json: str

    @property
    def payload(self) -> dict[str, Any]:
        return _payload(self.payload_json)


@dataclass(frozen=True, slots=True)
class AttentionContribution:
    attention_id: str
    worker: str
    object_id: str
    weight: int
    channel: str
    basis_ids: tuple[str, ...]
    created_revision: int


@dataclass(frozen=True, slots=True)
class PickupEvent:
    pickup_id: str
    direction: str
    from_worker: str
    to_worker: str
    object_id: str
    trigger_id: str
    trigger_kind: str
    created_revision: int


@dataclass(frozen=True, slots=True)
class GraphEvent:
    seq: int
    prev_hash: str | None
    event_type: str
    actor: str
    event_id: str
    payload_json: str
    event_hash: str

    @property
    def payload(self) -> dict[str, Any]:
        return _payload(self.payload_json)


@dataclass(frozen=True, slots=True)
class GraphState:
    revision: int = -1
    head_hash: str | None = None
    event_ids: tuple[str, ...] = ()
    objects: tuple[EpistemicObject, ...] = ()
    edges: tuple[EpistemicEdge, ...] = ()
    attention: tuple[AttentionContribution, ...] = ()
    pickups: tuple[PickupEvent, ...] = ()


@dataclass(frozen=True, slots=True)
class SaliencePolicy:
    worker: str
    kind_weights: tuple[tuple[str, int], ...]
    support_weight: int
    refute_weight: int
    own_attention_weight: int
    other_attention_weight: int
    recency_weight: int


@dataclass(frozen=True, slots=True)
class Frontier:
    frontier_id: str
    worker: str
    graph_revision: int
    token_budget: int
    used_tokens: int
    root_limit: int | None
    object_ids: tuple[str, ...]
    edge_ids: tuple[str, ...]
    mandatory_binding_ids: tuple[str, ...]
    selected_root_ids: tuple[str, ...]
    omitted_root_ids: tuple[str, ...]
    document_json: str

    @property
    def document(self) -> dict[str, Any]:
        return _payload(self.document_json)


@dataclass(frozen=True, slots=True)
class IngestResult:
    state: GraphState
    events: tuple[GraphEvent, ...]
    object_ids: tuple[str, ...] = ()
    edge_ids: tuple[str, ...] = ()


R2_POLICY = SaliencePolicy(
    worker="r2",
    kind_weights=(
        ("structured_criticism", 76),
        ("binding", 70),
        ("counterfactual", 58),
        ("environment_evidence", 52),
        ("schema", 46),
        ("explanation", 42),
        ("experiment", 38),
        ("entity", 30),
    ),
    support_weight=13,
    refute_weight=17,
    own_attention_weight=7,
    other_attention_weight=3,
    recency_weight=2,
)
QWEN_POLICY = SaliencePolicy(
    worker="qwen",
    kind_weights=(
        ("structured_criticism", 82),
        ("explanation", 70),
        ("experiment", 62),
        ("schema", 58),
        ("binding", 54),
        ("counterfactual", 48),
        ("environment_evidence", 36),
        ("entity", 28),
    ),
    support_weight=11,
    refute_weight=13,
    own_attention_weight=7,
    other_attention_weight=4,
    recency_weight=2,
)


def policy_for(worker: str) -> SaliencePolicy:
    if worker == "r2":
        return R2_POLICY
    if worker == "qwen":
        return QWEN_POLICY
    raise EpistemicGraphError(f"unknown worker: {worker}")


def make_object(
    *,
    kind: str,
    created_by: str,
    created_revision: int,
    identity: Mapping[str, Any],
    payload: Mapping[str, Any],
    dependency_ids: Sequence[str] = (),
) -> EpistemicObject:
    if created_by not in CREATORS:
        raise EpistemicGraphError(f"unknown object creator: {created_by}")
    if not kind:
        raise EpistemicGraphError("object kind is empty")
    if kind == "environment_evidence" and created_by != "environment":
        raise EpistemicGraphError("only the environment may create evidence")
    if created_by in WORKERS and FORBIDDEN_WORKER_PAYLOAD_KEYS.intersection(payload):
        raise EpistemicGraphError("worker object payload attempts to assert empirical support")
    identity_json = _canonical_payload(identity)
    payload_json = _canonical_payload(payload)
    dependencies = tuple(sorted(set(str(item) for item in dependency_ids)))
    object_id = f"eo:{stable_hash({'kind': kind, 'identity': json.loads(identity_json)})}"
    return EpistemicObject(
        object_id=object_id,
        kind=kind,
        created_by=created_by,
        created_revision=int(created_revision),
        identity_json=identity_json,
        payload_json=payload_json,
        dependency_ids=dependencies,
    )


def make_edge(
    *,
    kind: str,
    source_id: str,
    target_id: str,
    created_by: str,
    created_revision: int,
    payload: Mapping[str, Any] | None = None,
) -> EpistemicEdge:
    if created_by not in CREATORS:
        raise EpistemicGraphError(f"unknown edge creator: {created_by}")
    if source_id == target_id:
        raise EpistemicGraphError("self edge is not allowed")
    payload_json = _canonical_payload(payload or {})
    identity = {
        "kind": kind,
        "source": source_id,
        "target": target_id,
        "payload": json.loads(payload_json),
    }
    return EpistemicEdge(
        edge_id=f"ee:{stable_hash(identity)}",
        kind=kind,
        source_id=source_id,
        target_id=target_id,
        created_by=created_by,
        created_revision=int(created_revision),
        payload_json=payload_json,
    )


def make_attention(
    *,
    worker: str,
    object_id: str,
    weight: int,
    channel: str,
    basis_ids: Sequence[str],
    created_revision: int,
    contribution_key: str,
) -> AttentionContribution:
    if worker not in WORKERS:
        raise EpistemicGraphError(f"unknown attention worker: {worker}")
    if not 1 <= int(weight) <= 100:
        raise EpistemicGraphError("attention weight must be between 1 and 100")
    basis = tuple(sorted(set(str(item) for item in basis_ids)))
    identity = {
        "worker": worker,
        "object": object_id,
        "channel": channel,
        "basis": basis,
        "key": contribution_key,
    }
    return AttentionContribution(
        attention_id=f"ea:{stable_hash(identity)}",
        worker=worker,
        object_id=object_id,
        weight=int(weight),
        channel=str(channel),
        basis_ids=basis,
        created_revision=int(created_revision),
    )


def _item_document(item: EpistemicObject | EpistemicEdge | AttentionContribution) -> dict[str, Any]:
    return asdict(item)


def make_event(
    state: GraphState,
    *,
    event_type: str,
    actor: str,
    item: EpistemicObject | EpistemicEdge | AttentionContribution,
    event_key: str | None = None,
) -> GraphEvent:
    if event_type not in EVENT_TYPES:
        raise EpistemicGraphError(f"unknown graph event type: {event_type}")
    seq = state.revision + 1
    payload_json = _canonical_payload({"item": _item_document(item)})
    event_id = f"ge:{stable_hash({'type': event_type, 'actor': actor, 'key': event_key, 'payload': json.loads(payload_json)})}"
    envelope = {
        "seq": seq,
        "prev_hash": state.head_hash,
        "event_type": event_type,
        "actor": actor,
        "event_id": event_id,
        "payload_json": payload_json,
    }
    return GraphEvent(**envelope, event_hash=stable_hash(envelope))


def object_event(
    state: GraphState,
    *,
    kind: str,
    created_by: str,
    identity: Mapping[str, Any],
    payload: Mapping[str, Any],
    dependency_ids: Sequence[str] = (),
    event_key: str | None = None,
) -> GraphEvent:
    item = make_object(
        kind=kind,
        created_by=created_by,
        created_revision=state.revision + 1,
        identity=identity,
        payload=payload,
        dependency_ids=dependency_ids,
    )
    return make_event(state, event_type="ObjectAdded", actor=created_by, item=item, event_key=event_key)


def edge_event(
    state: GraphState,
    *,
    kind: str,
    source_id: str,
    target_id: str,
    created_by: str,
    payload: Mapping[str, Any] | None = None,
    event_key: str | None = None,
) -> GraphEvent:
    item = make_edge(
        kind=kind,
        source_id=source_id,
        target_id=target_id,
        created_by=created_by,
        created_revision=state.revision + 1,
        payload=payload,
    )
    return make_event(state, event_type="EdgeAdded", actor=created_by, item=item, event_key=event_key)


def attention_event(
    state: GraphState,
    *,
    worker: str,
    object_id: str,
    weight: int,
    channel: str,
    basis_ids: Sequence[str],
    contribution_key: str,
) -> GraphEvent:
    item = make_attention(
        worker=worker,
        object_id=object_id,
        weight=weight,
        channel=channel,
        basis_ids=basis_ids,
        created_revision=state.revision + 1,
        contribution_key=contribution_key,
    )
    return make_event(state, event_type="AttentionContributed", actor=worker, item=item)


def grounded_pickup_event(
    state: GraphState,
    *,
    pickup_id: str,
    downstream_object_id: str,
    worker: str,
    payload: Mapping[str, Any] | None = None,
) -> GraphEvent:
    pickup = next((item for item in state.pickups if item.pickup_id == pickup_id), None)
    if pickup is None or pickup.to_worker != worker:
        raise EpistemicGraphError("pickup is unknown or belongs to another worker")
    edge_payload = {"pickup_id": pickup_id, **dict(payload or {})}
    return edge_event(
        state,
        kind="grounds_pickup",
        source_id=pickup.object_id,
        target_id=downstream_object_id,
        created_by=worker,
        payload=edge_payload,
        event_key=f"grounded-pickup:{pickup_id}:{downstream_object_id}",
    )


def _object_from_document(value: Mapping[str, Any]) -> EpistemicObject:
    return EpistemicObject(
        object_id=str(value["object_id"]),
        kind=str(value["kind"]),
        created_by=str(value["created_by"]),
        created_revision=int(value["created_revision"]),
        identity_json=str(value["identity_json"]),
        payload_json=str(value["payload_json"]),
        dependency_ids=tuple(str(item) for item in value.get("dependency_ids", ())),
    )


def _edge_from_document(value: Mapping[str, Any]) -> EpistemicEdge:
    return EpistemicEdge(
        edge_id=str(value["edge_id"]),
        kind=str(value["kind"]),
        source_id=str(value["source_id"]),
        target_id=str(value["target_id"]),
        created_by=str(value["created_by"]),
        created_revision=int(value["created_revision"]),
        payload_json=str(value["payload_json"]),
    )


def _attention_from_document(value: Mapping[str, Any]) -> AttentionContribution:
    return AttentionContribution(
        attention_id=str(value["attention_id"]),
        worker=str(value["worker"]),
        object_id=str(value["object_id"]),
        weight=int(value["weight"]),
        channel=str(value["channel"]),
        basis_ids=tuple(str(item) for item in value.get("basis_ids", ())),
        created_revision=int(value["created_revision"]),
    )


def _objects(state: GraphState) -> dict[str, EpistemicObject]:
    return {item.object_id: item for item in state.objects}


def _pickup(
    state: GraphState,
    *,
    to_worker: str,
    object_id: str,
    trigger_id: str,
    trigger_kind: str,
    revision: int,
) -> PickupEvent | None:
    source = _objects(state).get(object_id)
    if (
        to_worker not in WORKERS
        or source is None
        or source.created_by not in WORKERS
        or source.created_by == to_worker
    ):
        return None
    identity = {"from": source.created_by, "to": to_worker, "object": object_id}
    pickup_id = f"ep:{stable_hash(identity)}"
    if any(item.pickup_id == pickup_id for item in state.pickups):
        return None
    return PickupEvent(
        pickup_id=pickup_id,
        direction=f"{source.created_by}->{to_worker}",
        from_worker=source.created_by,
        to_worker=to_worker,
        object_id=object_id,
        trigger_id=trigger_id,
        trigger_kind=trigger_kind,
        created_revision=revision,
    )


def apply_event(state: GraphState, event: GraphEvent) -> GraphState:
    """Apply one graph event without mutating the predecessor state."""

    if event.seq != state.revision + 1 or event.prev_hash != state.head_hash:
        raise EpistemicGraphError("graph event is not the next hash-chain member")
    envelope = {
        "seq": event.seq,
        "prev_hash": event.prev_hash,
        "event_type": event.event_type,
        "actor": event.actor,
        "event_id": event.event_id,
        "payload_json": event.payload_json,
    }
    if stable_hash(envelope) != event.event_hash:
        raise EpistemicGraphError("graph event hash mismatch")
    if event.event_id in state.event_ids:
        raise EpistemicGraphError("duplicate graph event")
    payload = event.payload
    if set(payload) != {"item"} or not isinstance(payload["item"], dict):
        raise EpistemicGraphError("graph event payload contract mismatch")
    objects = _objects(state)
    pickups = list(state.pickups)
    next_state = state

    if event.event_type == "ObjectAdded":
        item = _object_from_document(payload["item"])
        if event.actor != item.created_by or item.created_revision != event.seq:
            raise EpistemicGraphError("object creator/revision does not match event")
        if item.kind == "environment_evidence" and item.created_by != "environment":
            raise EpistemicGraphError("only environment may add evidence")
        if item.created_by in WORKERS and FORBIDDEN_WORKER_PAYLOAD_KEYS.intersection(item.payload):
            raise EpistemicGraphError("worker object attempts to assert support")
        if any(dependency not in objects for dependency in item.dependency_ids):
            raise EpistemicGraphError("object dependency is missing")
        existing = objects.get(item.object_id)
        if existing is not None:
            if existing != item:
                raise EpistemicGraphError("stable object id collision")
            raise EpistemicGraphError("duplicate object event")
        for dependency in item.dependency_ids:
            detected = _pickup(
                state,
                to_worker=item.created_by,
                object_id=dependency,
                trigger_id=item.object_id,
                trigger_kind="dependency",
                revision=event.seq,
            )
            if detected is not None:
                pickups.append(detected)
        next_state = replace(
            state,
            objects=tuple(sorted((*state.objects, item), key=lambda value: value.object_id)),
            pickups=tuple(sorted(pickups, key=lambda value: value.pickup_id)),
        )
    elif event.event_type == "EdgeAdded":
        item = _edge_from_document(payload["item"])
        if event.actor != item.created_by or item.created_revision != event.seq:
            raise EpistemicGraphError("edge creator/revision does not match event")
        if item.source_id not in objects or item.target_id not in objects:
            raise EpistemicGraphError("edge endpoint is missing")
        if item.kind in EVIDENCE_EDGE_KINDS:
            if item.created_by != "environment" or objects[item.source_id].kind != "environment_evidence":
                raise EpistemicGraphError("support-changing edge requires environment evidence authority")
        if item.kind == "grounds_pickup":
            pickup_id = item.payload.get("pickup_id")
            pickup = next((value for value in state.pickups if value.pickup_id == pickup_id), None)
            if (
                pickup is None
                or item.created_by != pickup.to_worker
                or item.source_id != pickup.object_id
                or objects[item.target_id].created_by != pickup.to_worker
            ):
                raise EpistemicGraphError("grounded pickup edge does not match its exposure")
        semantic = {(edge.kind, edge.source_id, edge.target_id) for edge in state.edges}
        if (item.kind, item.source_id, item.target_id) in semantic:
            raise EpistemicGraphError("duplicate semantic edge")
        next_state = replace(
            state,
            edges=tuple(sorted((*state.edges, item), key=lambda value: value.edge_id)),
        )
    elif event.event_type == "AttentionContributed":
        item = _attention_from_document(payload["item"])
        if event.actor != item.worker or item.created_revision != event.seq:
            raise EpistemicGraphError("attention worker/revision does not match event")
        if item.object_id not in objects or any(basis not in objects for basis in item.basis_ids):
            raise EpistemicGraphError("attention references a missing object")
        if any(existing.attention_id == item.attention_id for existing in state.attention):
            raise EpistemicGraphError("duplicate attention contribution")
        detected = _pickup(
            state,
            to_worker=item.worker,
            object_id=item.object_id,
            trigger_id=item.attention_id,
            trigger_kind="attention",
            revision=event.seq,
        )
        if detected is not None:
            pickups.append(detected)
        next_state = replace(
            state,
            attention=tuple(sorted((*state.attention, item), key=lambda value: value.attention_id)),
            pickups=tuple(sorted(pickups, key=lambda value: value.pickup_id)),
        )
    else:
        raise EpistemicGraphError(f"unsupported graph event: {event.event_type}")

    return replace(
        next_state,
        revision=event.seq,
        head_hash=event.event_hash,
        event_ids=(*state.event_ids, event.event_id),
    )


def replay(events: Iterable[GraphEvent]) -> GraphState:
    state = GraphState()
    for event in events:
        state = apply_event(state, event)
    return state


def evidence_counts(state: GraphState, object_id: str) -> tuple[int, int]:
    supports = sum(edge.kind == "supports" and edge.target_id == object_id for edge in state.edges)
    refutes = sum(edge.kind == "refutes" and edge.target_id == object_id for edge in state.edges)
    return supports, refutes


def support(state: GraphState, object_id: str) -> int:
    supports, refutes = evidence_counts(state, object_id)
    return supports - refutes


def invalidated_ids(state: GraphState) -> frozenset[str]:
    return frozenset(edge.target_id for edge in state.edges if edge.kind == "invalidates")


def live_binding_ids(state: GraphState) -> tuple[str, ...]:
    invalid = invalidated_ids(state)
    return tuple(
        item.object_id
        for item in state.objects
        if item.kind == "binding" and item.object_id not in invalid
    )


def salience(
    state: GraphState,
    worker: str,
    object_id: str,
    policy: SaliencePolicy | None = None,
) -> int:
    selected_policy = policy or policy_for(worker)
    if selected_policy.worker != worker:
        raise EpistemicGraphError("salience policy belongs to another worker")
    item = _objects(state).get(object_id)
    if item is None:
        raise EpistemicGraphError("salience object does not exist")
    kind_weights = dict(selected_policy.kind_weights)
    supports, refutes = evidence_counts(state, object_id)
    age = max(0, state.revision - item.created_revision)
    score = kind_weights.get(item.kind, 20)
    score += supports * selected_policy.support_weight
    score -= refutes * selected_policy.refute_weight
    score += max(0, ATTENTION_HORIZON - age) * selected_policy.recency_weight
    for contribution in state.attention:
        if contribution.object_id != object_id:
            continue
        attention_age = max(0, state.revision - contribution.created_revision)
        remaining = max(0, ATTENTION_HORIZON - attention_age)
        multiplier = (
            selected_policy.own_attention_weight
            if contribution.worker == worker
            else selected_policy.other_attention_weight
        )
        score += contribution.weight * remaining * multiplier
    return score


def dependency_ids(state: GraphState, object_id: str) -> tuple[str, ...]:
    item = _objects(state).get(object_id)
    if item is None:
        raise EpistemicGraphError(f"unknown object dependency root: {object_id}")
    dependencies = set(item.dependency_ids)
    dependencies.update(
        edge.source_id
        for edge in state.edges
        if edge.target_id == object_id and edge.kind in EVIDENCE_EDGE_KINDS
    )
    dependencies.update(
        edge.target_id
        for edge in state.edges
        if edge.source_id == object_id and edge.kind == "depends_on"
    )
    return tuple(sorted(dependencies))


def dependency_closure(state: GraphState, roots: Iterable[str]) -> tuple[str, ...]:
    objects = _objects(state)
    closure: set[str] = set()
    agenda = list(sorted(set(roots), reverse=True))
    while agenda:
        object_id = agenda.pop()
        if object_id in closure:
            continue
        if object_id not in objects:
            raise EpistemicGraphError(f"frontier dependency is missing: {object_id}")
        closure.add(object_id)
        agenda.extend(
            dependency
            for dependency in reversed(dependency_ids(state, object_id))
            if dependency not in closure
        )
    return tuple(sorted(closure))


def estimate_tokens(value: object) -> int:
    return max(1, (len(stable_json(value).encode("utf-8")) + 3) // 4)


def _frontier_document(
    state: GraphState,
    worker: str,
    selected_ids: Sequence[str],
    mandatory_binding_ids: Sequence[str],
    policy: SaliencePolicy | None = None,
    root_limit: int | None = None,
    selected_root_ids: Sequence[str] = (),
    omitted_root_count: int = 0,
) -> dict[str, Any]:
    selected = set(selected_ids)
    objects = _objects(state)
    selected_edges = tuple(
        edge
        for edge in state.edges
        if edge.source_id in selected and edge.target_id in selected
    )
    relevant_pickups = tuple(
        pickup for pickup in state.pickups if pickup.object_id in selected
    )
    return {
        "protocol": "shared-attention-frontier-v1",
        "worker": worker,
        "graph_revision": state.revision,
        "objects": [
            {
                "id": object_id,
                "kind": objects[object_id].kind,
                "created_by": objects[object_id].created_by,
                "identity": objects[object_id].identity,
                "payload": objects[object_id].payload,
                "dependencies": list(objects[object_id].dependency_ids),
                "support": support(state, object_id),
                "salience": salience(state, worker, object_id, policy),
            }
            for object_id in sorted(selected)
        ],
        "edges": [
            {
                "id": edge.edge_id,
                "kind": edge.kind,
                "source": edge.source_id,
                "target": edge.target_id,
                "payload": edge.payload,
            }
            for edge in sorted(selected_edges, key=lambda value: value.edge_id)
        ],
        "attention": [
            {
                "object": object_id,
                "r2": sum(
                    item.weight for item in state.attention if item.object_id == object_id and item.worker == "r2"
                ),
                "qwen": sum(
                    item.weight for item in state.attention if item.object_id == object_id and item.worker == "qwen"
                ),
            }
            for object_id in sorted(selected)
            if any(item.object_id == object_id for item in state.attention)
        ],
        "pickups": [asdict(item) for item in sorted(relevant_pickups, key=lambda value: value.pickup_id)],
        "mandatory_live_bindings": list(sorted(mandatory_binding_ids)),
        "selection": {
            "root_limit": root_limit,
            "mandatory_binding_roots_exempt": True,
            "selected_optional_roots": list(selected_root_ids),
            "omitted_optional_root_count": omitted_root_count,
        },
    }


def build_frontier(
    state: GraphState,
    *,
    worker: str,
    token_budget: int,
    root_limit: int | None = None,
    policy: SaliencePolicy | None = None,
) -> Frontier:
    """Greedily select a deterministic dependency-closed worker frontier.

    Every non-invalidated binding is mandatory.  If its complete dependency
    closure cannot fit, the function fails rather than hiding a competitor.
    """

    selected_policy = policy or policy_for(worker)
    if token_budget <= 0:
        raise FrontierBudgetError(budget=token_budget, required=1)
    if root_limit is not None and root_limit < 0:
        raise EpistemicGraphError("frontier root limit cannot be negative")
    mandatory_bindings = live_binding_ids(state)
    selected = set(dependency_closure(state, mandatory_bindings))
    document = _frontier_document(
        state,
        worker,
        tuple(selected),
        mandatory_bindings,
        selected_policy,
        root_limit,
    )
    used = estimate_tokens(document)
    if used > token_budget:
        raise FrontierBudgetError(budget=token_budget, required=used)

    invalid = invalidated_ids(state)
    candidates = sorted(
        (item.object_id for item in state.objects if item.object_id not in selected and item.object_id not in invalid),
        key=lambda object_id: (-salience(state, worker, object_id, selected_policy), object_id),
    )
    selected_roots: list[str] = []
    omitted_roots: list[str] = []
    for candidate in candidates:
        if candidate in selected:
            continue
        if root_limit is not None and len(selected_roots) >= root_limit:
            omitted_roots.append(candidate)
            continue
        proposed = selected.union(dependency_closure(state, (candidate,)))
        proposed_document = _frontier_document(
            state,
            worker,
            tuple(proposed),
            mandatory_bindings,
            selected_policy,
            root_limit,
            (*selected_roots, candidate),
            len(omitted_roots),
        )
        proposed_cost = estimate_tokens(proposed_document)
        if proposed_cost <= token_budget:
            selected = proposed
            document = proposed_document
            used = proposed_cost
            selected_roots.append(candidate)
        else:
            omitted_roots.append(candidate)

    # The final omitted-count metadata can cross a token digit boundary.  If
    # it does, evict the lowest-ranked optional root deterministically until
    # the complete rendered document fits again.  Mandatory roots never move.
    while True:
        selected = set(dependency_closure(state, (*mandatory_bindings, *selected_roots)))
        document = _frontier_document(
            state,
            worker,
            tuple(selected),
            mandatory_bindings,
            selected_policy,
            root_limit,
            tuple(selected_roots),
            len(omitted_roots),
        )
        used = estimate_tokens(document)
        if used <= token_budget:
            break
        if not selected_roots:
            raise FrontierBudgetError(budget=token_budget, required=used)
        omitted_roots.append(selected_roots.pop())

    object_ids = tuple(sorted(selected))
    edge_ids = tuple(
        sorted(
            edge.edge_id
            for edge in state.edges
            if edge.source_id in selected and edge.target_id in selected
        )
    )
    identity = {
        "worker": worker,
        "revision": state.revision,
        "budget": token_budget,
        "root_limit": root_limit,
        "objects": object_ids,
        "edges": edge_ids,
        "selected_roots": tuple(selected_roots),
    }
    return Frontier(
        frontier_id=f"ef:{stable_hash(identity)}",
        worker=worker,
        graph_revision=state.revision,
        token_budget=token_budget,
        used_tokens=used,
        root_limit=root_limit,
        object_ids=object_ids,
        edge_ids=edge_ids,
        mandatory_binding_ids=mandatory_bindings,
        selected_root_ids=tuple(selected_roots),
        omitted_root_ids=tuple(sorted(set(omitted_roots))),
        document_json=_canonical_payload(document),
    )


def pickup_events(state: GraphState, *, after_revision: int = -1) -> tuple[PickupEvent, ...]:
    return tuple(
        item
        for item in sorted(state.pickups, key=lambda value: (value.created_revision, value.pickup_id))
        if item.created_revision > after_revision
    )


def event_document(event: GraphEvent) -> dict[str, Any]:
    return asdict(event)


def event_from_document(value: Mapping[str, Any]) -> GraphEvent:
    required = {"seq", "prev_hash", "event_type", "actor", "event_id", "payload_json", "event_hash"}
    if set(value) != required:
        raise EpistemicGraphError("serialized graph event contract mismatch")
    return GraphEvent(
        seq=int(value["seq"]),
        prev_hash=None if value["prev_hash"] is None else str(value["prev_hash"]),
        event_type=str(value["event_type"]),
        actor=str(value["actor"]),
        event_id=str(value["event_id"]),
        payload_json=str(value["payload_json"]),
        event_hash=str(value["event_hash"]),
    )


def state_document(state: GraphState) -> dict[str, Any]:
    document = asdict(state)
    document["state_hash"] = stable_hash(document)
    return document


def deltas(state: GraphState, cursor: int = -1) -> dict[str, Any]:
    if cursor < -1 or cursor > state.revision:
        raise EpistemicGraphError("delta cursor is outside graph history")
    return {
        "protocol": "shared-attention-graph-delta-v1",
        "from_revision_exclusive": cursor,
        "through_revision": state.revision,
        "objects": [asdict(item) for item in state.objects if item.created_revision > cursor],
        "edges": [asdict(item) for item in state.edges if item.created_revision > cursor],
        "attention": [asdict(item) for item in state.attention if item.created_revision > cursor],
        "pickups": [asdict(item) for item in pickup_events(state, after_revision=cursor)],
    }


def metrics(state: GraphState) -> dict[str, Any]:
    kinds: dict[str, int] = {}
    for item in state.objects:
        kinds[item.kind] = kinds.get(item.kind, 0) + 1
    edge_kinds: dict[str, int] = {}
    for item in state.edges:
        edge_kinds[item.kind] = edge_kinds.get(item.kind, 0) + 1
    pickup_directions: dict[str, int] = {}
    pickup_triggers: dict[str, int] = {}
    for item in state.pickups:
        pickup_directions[item.direction] = pickup_directions.get(item.direction, 0) + 1
        pickup_triggers[item.trigger_kind] = pickup_triggers.get(item.trigger_kind, 0) + 1
    grounded_edges = [item for item in state.edges if item.kind == "grounds_pickup"]
    pickup_by_id = {item.pickup_id: item for item in state.pickups}
    grounded_directions: dict[str, int] = {}
    for edge in grounded_edges:
        pickup = pickup_by_id.get(edge.payload.get("pickup_id"))
        if pickup is not None:
            grounded_directions[pickup.direction] = grounded_directions.get(pickup.direction, 0) + 1
    return {
        "revision": state.revision,
        "head_hash": state.head_hash,
        "state_hash": state_document(state)["state_hash"],
        "object_count": len(state.objects),
        "object_kinds": dict(sorted(kinds.items())),
        "edge_count": len(state.edges),
        "edge_kinds": dict(sorted(edge_kinds.items())),
        "attention_count": len(state.attention),
        "attention_by_worker": {
            worker: sum(item.worker == worker for item in state.attention)
            for worker in sorted(WORKERS)
        },
        "pickup_count": len(state.pickups),
        "pickup_directions": dict(sorted(pickup_directions.items())),
        "pickup_exposure_count": len(state.pickups),
        "pickup_trigger_kinds": dict(sorted(pickup_triggers.items())),
        "grounded_pickup_count": len(grounded_edges),
        "grounded_pickup_directions": dict(sorted(grounded_directions.items())),
        "live_binding_count": len(live_binding_ids(state)),
        "supported_object_count": sum(support(state, item.object_id) > 0 for item in state.objects),
        "refuted_object_count": sum(support(state, item.object_id) < 0 for item in state.objects),
    }


def frontier(
    state: GraphState,
    *,
    worker: str,
    profile: str | SaliencePolicy | None = None,
    budget: int,
    root_limit: int | None = None,
) -> Frontier:
    if profile is None or profile == "default" or profile == worker:
        selected_policy = policy_for(worker)
    elif isinstance(profile, SaliencePolicy):
        selected_policy = profile
    else:
        raise EpistemicGraphError(f"unknown salience profile: {profile}")
    return build_frontier(
        state,
        worker=worker,
        token_budget=budget,
        root_limit=root_limit,
        policy=selected_policy,
    )


def _same_object_content(left: EpistemicObject, right: EpistemicObject) -> bool:
    return (
        left.object_id == right.object_id
        and left.kind == right.kind
        and left.created_by == right.created_by
        and left.identity_json == right.identity_json
        and left.payload_json == right.payload_json
        and left.dependency_ids == right.dependency_ids
    )


def _ingest_object(
    state: GraphState,
    *,
    kind: str,
    created_by: str,
    identity: Mapping[str, Any],
    payload: Mapping[str, Any],
    dependency_ids: Sequence[str],
    event_key: str,
) -> tuple[GraphState, GraphEvent | None, str]:
    candidate = make_object(
        kind=kind,
        created_by=created_by,
        created_revision=state.revision + 1,
        identity=identity,
        payload=payload,
        dependency_ids=dependency_ids,
    )
    existing = _objects(state).get(candidate.object_id)
    if existing is not None:
        if not _same_object_content(existing, candidate):
            raise EpistemicGraphError("stable object identity was reused with different content")
        return state, None, existing.object_id
    event = make_event(
        state,
        event_type="ObjectAdded",
        actor=created_by,
        item=candidate,
        event_key=event_key,
    )
    return apply_event(state, event), event, candidate.object_id


def ingest_r2_runtime_summary(
    state: GraphState,
    summary: Mapping[str, Any],
    *,
    observation_key: str,
    basis_ids: Sequence[str] = (),
) -> IngestResult:
    next_state, event, object_id = _ingest_object(
        state,
        kind="runtime_summary",
        created_by="r2",
        identity={"observation_key": observation_key, "summary_hash": stable_hash(summary)},
        payload=dict(summary),
        dependency_ids=basis_ids,
        event_key=f"r2-runtime:{observation_key}",
    )
    return IngestResult(next_state, () if event is None else (event,), (object_id,))


def ingest_groundings(
    state: GraphState,
    groundings: Sequence[Mapping[str, Any]],
    *,
    source: str,
) -> IngestResult:
    if source not in WORKERS:
        raise EpistemicGraphError("grounding source must be r2 or qwen")
    next_state = state
    events: list[GraphEvent] = []
    object_ids: list[str] = []
    for index, raw in enumerate(groundings):
        if not isinstance(raw, Mapping) or not {"binding_key", "payload", "dependency_ids"}.issubset(raw):
            raise EpistemicGraphError("grounding ingestion contract mismatch")
        next_state, event, object_id = _ingest_object(
            next_state,
            kind="binding",
            created_by=source,
            identity={"binding_key": raw["binding_key"]},
            payload=dict(raw["payload"]),
            dependency_ids=tuple(str(item) for item in raw["dependency_ids"]),
            event_key=f"grounding:{source}:{index}:{raw['binding_key']}",
        )
        if event is not None:
            events.append(event)
        object_ids.append(object_id)
    return IngestResult(next_state, tuple(events), tuple(object_ids))


def ingest_qwen_writes(
    state: GraphState,
    writes: Sequence[Mapping[str, Any]],
    *,
    response_id: str,
    basis_ids: Sequence[str] = (),
) -> IngestResult:
    """Ingest semantic Qwen objects plus response-specific provenance.

    A schema or explanation is an epistemic claim, not a model-call artifact.
    Its stable identity therefore excludes ``response_id`` and write position.
    The latter remain durable in a separate ``qwen_derivation`` object linked
    to the semantic object and every supplied basis dependency.  Repeating the
    same claim can consequently focus attention on one object without
    fabricating novelty, while its distinct derivations remain inspectable.
    """

    next_state = state
    events: list[GraphEvent] = []
    object_ids: list[str] = []
    for index, raw in enumerate(writes):
        if not isinstance(raw, Mapping) or not {"kind", "identity", "payload"}.issubset(raw):
            raise EpistemicGraphError("Qwen write ingestion contract mismatch")
        kind = str(raw["kind"])
        raw_identity = dict(raw["identity"])
        raw_payload = dict(raw["payload"])
        semantic_identity = {
            key: value for key, value in raw_identity.items() if key != "origin"
        }
        # Claims remain immutable semantic objects.  Call-local scheduling and
        # provenance belong to their derivation record, not their identity or
        # content.  Keeping those fields here was what made repeated identical
        # proposals appear novel.
        semantic_payload = {
            key: value
            for key, value in raw_payload.items()
            if key not in {"eligible_step", "provenance"}
        }
        supplied_dependencies = tuple(
            sorted(
                set(str(item) for item in basis_ids).union(
                    str(item) for item in raw.get("dependency_ids", ())
                )
            )
        )
        semantic_dependencies: tuple[str, ...]
        if kind == "schema":
            semantic_dependencies = ()
        elif kind == "explanation":
            bindings = raw_identity.get("bindings", raw_payload.get("bindings", {}))
            referenced = set(
                str(value) for value in bindings.values()
            ) if isinstance(bindings, Mapping) else set()
            schema_ref = raw_identity.get("schema_ref", raw.get("schema_ref"))
            if isinstance(schema_ref, str) and schema_ref.startswith("eo:"):
                referenced.add(schema_ref)
            semantic_dependencies = tuple(sorted(referenced))
        else:
            semantic_dependencies = supplied_dependencies
        next_state, event, object_id = _ingest_object(
            next_state,
            kind=kind,
            created_by="qwen",
            identity=semantic_identity,
            payload=semantic_payload,
            dependency_ids=semantic_dependencies,
            event_key=f"qwen-semantic:{stable_hash({'kind': kind, 'identity': semantic_identity})}",
        )
        if event is not None:
            events.append(event)
        object_ids.append(object_id)
        derivation_dependencies = tuple(sorted(set((*supplied_dependencies, object_id))))
        next_state, derivation_event, _derivation_id = _ingest_object(
            next_state,
            kind="qwen_derivation",
            created_by="qwen",
            identity={
                "response_id": str(response_id),
                "write_index": index,
                "semantic_object_id": object_id,
            },
            payload={
                "response_id": str(response_id),
                "write_index": index,
                "write_kind": kind,
                "call_local_payload": {
                    key: raw_payload[key]
                    for key in ("eligible_step", "provenance")
                    if key in raw_payload
                },
            },
            dependency_ids=derivation_dependencies,
            event_key=f"qwen-derivation:{response_id}:{index}:{object_id}",
        )
        if derivation_event is not None:
            events.append(derivation_event)
    return IngestResult(next_state, tuple(events), tuple(object_ids))


def ingest_structured_criticism(
    state: GraphState,
    *,
    worker: str,
    target_id: str,
    status: str,
    criticism_key: str,
    payload: Mapping[str, Any] | None = None,
    basis_ids: Sequence[str] = (),
) -> IngestResult:
    """Write non-empirical grounding/control criticism into the graph.

    Criticism says why a worker could not currently use or ground an object;
    it is not environmental refutation and therefore creates no support edge.
    The target is mandatory in the dependency closure so the criticism is
    intelligible whenever surfaced to the other worker.
    """

    if worker not in WORKERS:
        raise EpistemicGraphError("criticism source must be r2 or qwen")
    if target_id not in _objects(state):
        raise EpistemicGraphError("criticism target does not exist")
    allowed = frozenset(
        {
            "unsupported-potential",
            "unbound",
            "ambiguous-grounding",
            "refuted-grounding",
            "rejected",
        }
    )
    if status not in allowed:
        raise EpistemicGraphError("unknown structured criticism status")
    dependencies = tuple(sorted(set((str(target_id), *(str(item) for item in basis_ids)))))
    next_state, event, object_id = _ingest_object(
        state,
        kind="structured_criticism",
        created_by=worker,
        identity={
            "worker": worker,
            "target_id": str(target_id),
            "status": str(status),
            "criticism_key": str(criticism_key),
        },
        payload={**dict(payload or {}), "status": str(status)},
        dependency_ids=dependencies,
        event_key=f"structured-criticism:{worker}:{criticism_key}",
    )
    return IngestResult(next_state, () if event is None else (event,), (object_id,))


def ingest_environment_evidence(
    state: GraphState,
    *,
    transition_id: str,
    payload: Mapping[str, Any],
    judgments: Sequence[Mapping[str, str]] = (),
) -> IngestResult:
    next_state, evidence_event, evidence_id = _ingest_object(
        state,
        kind="environment_evidence",
        created_by="environment",
        identity={"transition_id": transition_id},
        payload=dict(payload),
        dependency_ids=(),
        event_key=f"environment-evidence:{transition_id}",
    )
    events: list[GraphEvent] = [] if evidence_event is None else [evidence_event]
    edge_ids: list[str] = []
    existing_semantic = {(item.kind, item.source_id, item.target_id) for item in next_state.edges}
    for index, judgment in enumerate(judgments):
        if set(judgment) != {"kind", "target_id"} or judgment["kind"] not in EVIDENCE_EDGE_KINDS:
            raise EpistemicGraphError("environment judgment contract mismatch")
        semantic = (str(judgment["kind"]), evidence_id, str(judgment["target_id"]))
        if semantic in existing_semantic:
            continue
        event = edge_event(
            next_state,
            kind=semantic[0],
            source_id=evidence_id,
            target_id=semantic[2],
            created_by="environment",
            event_key=f"environment-judgment:{transition_id}:{index}",
        )
        next_state = apply_event(next_state, event)
        events.append(event)
        edge = next(item for item in next_state.edges if item.created_revision == event.seq)
        edge_ids.append(edge.edge_id)
        existing_semantic.add(semantic)
    return IngestResult(next_state, tuple(events), (evidence_id,), tuple(edge_ids))
