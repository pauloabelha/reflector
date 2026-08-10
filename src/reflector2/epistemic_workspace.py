"""Durable shared epistemic workspace for native Reflector-II.

The native :class:`~reflector2.store.SchemaGraph` remains the executable
schema store.  This module supplies the missing shared cognitive substrate:
R2, semantic workers, and the environment all append objects to one
hash-chained history and read worker-specific, dependency-closed cuts of that
same history.

Attention and empirical authority are deliberately independent.  R2 and
semantic workers may make an object salient; only an environment-authored
evidence event can change its derived support.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from .runtime import Runtime


CREATORS = frozenset({"r2", "qwen", "environment", "kernel"})
WORKERS = frozenset({"r2", "qwen"})
VERDICTS = frozenset({"supports", "refutes", "invalidates", "unresolved"})
LIVE_BINDING_STATUSES = frozenset({"live", "bound", "ambiguous", "open"})
FORBIDDEN_WORKER_FIELDS = frozenset(
    {
        "support",
        "support_count",
        "confidence",
        "confirmed",
        "refuted",
        "empirical_probability",
    }
)


class EpistemicWorkspaceError(ValueError):
    """The requested mutation violates a workspace invariant."""


class FrontierCapacityError(EpistemicWorkspaceError):
    """The mandatory live epistemic closure cannot fit the supplied budget."""

    def __init__(self, *, budget: int, required: int) -> None:
        super().__init__(
            f"frontier budget {budget} is below mandatory closure cost {required}"
        )
        self.budget = budget
        self.required = required


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def content_hash(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _object(value: str) -> dict[str, Any]:
    parsed = json.loads(value)
    if not isinstance(parsed, dict):
        raise EpistemicWorkspaceError("canonical value is not an object")
    return parsed


def _assert_worker_payload(payload: Mapping[str, Any], creator: str) -> None:
    if creator == "environment":
        return
    stack: list[object] = [payload]
    while stack:
        value = stack.pop()
        if isinstance(value, Mapping):
            forbidden = FORBIDDEN_WORKER_FIELDS.intersection(map(str, value))
            if forbidden:
                names = ", ".join(sorted(forbidden))
                raise EpistemicWorkspaceError(
                    f"{creator} payload attempts to assert empirical authority: {names}"
                )
            stack.extend(value.values())
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            stack.extend(value)


@dataclass(frozen=True, slots=True)
class EpistemicObject:
    object_id: str
    kind: str
    creator: str
    created_revision: int
    semantic_key_json: str
    payload_json: str
    dependency_ids: tuple[str, ...]

    @property
    def semantic_key(self) -> dict[str, Any]:
        return _object(self.semantic_key_json)

    @property
    def payload(self) -> dict[str, Any]:
        return _object(self.payload_json)


@dataclass(frozen=True, slots=True)
class AttentionContribution:
    contribution_id: str
    worker: str
    object_id: str
    weight: int
    channel: str
    basis_ids: tuple[str, ...]
    created_revision: int


@dataclass(frozen=True, slots=True)
class EvidenceJudgment:
    evidence_id: str
    target_id: str
    verdict: str
    transition_id: str
    payload_json: str
    dependency_ids: tuple[str, ...]
    created_revision: int

    @property
    def payload(self) -> dict[str, Any]:
        return _object(self.payload_json)


@dataclass(frozen=True, slots=True)
class WorkspaceEvent:
    revision: int
    previous_hash: str | None
    event_type: str
    actor: str
    event_id: str
    body_json: str
    event_hash: str

    @property
    def body(self) -> dict[str, Any]:
        return _object(self.body_json)

    def document(self) -> dict[str, Any]:
        return {
            "revision": self.revision,
            "previous_hash": self.previous_hash,
            "event_type": self.event_type,
            "actor": self.actor,
            "event_id": self.event_id,
            "body": self.body,
            "event_hash": self.event_hash,
        }


@dataclass(frozen=True, slots=True)
class EpistemicFrontier:
    worker: str
    revision: int
    object_ids: tuple[str, ...]
    mandatory_ids: tuple[str, ...]
    omitted_root_ids: tuple[str, ...]
    estimated_units: int


class SharedEpistemicWorkspace:
    """Append-only epistemic world shared by native heterogeneous workers."""

    def __init__(self) -> None:
        self._events: list[WorkspaceEvent] = []
        self._objects: dict[str, EpistemicObject] = {}
        self._attention: dict[str, AttentionContribution] = {}
        self._evidence: dict[str, EvidenceJudgment] = {}

    @property
    def revision(self) -> int:
        return len(self._events) - 1

    @property
    def head_hash(self) -> str | None:
        return None if not self._events else self._events[-1].event_hash

    @property
    def events(self) -> tuple[WorkspaceEvent, ...]:
        return tuple(self._events)

    @property
    def objects(self) -> tuple[EpistemicObject, ...]:
        return tuple(
            sorted(self._objects.values(), key=lambda item: item.created_revision)
        )

    def object(self, object_id: str) -> EpistemicObject:
        try:
            return self._objects[object_id]
        except KeyError as exc:
            raise EpistemicWorkspaceError(f"unknown epistemic object: {object_id}") from exc

    def _append(self, event_type: str, actor: str, event_id: str, body: object) -> WorkspaceEvent:
        if actor not in CREATORS:
            raise EpistemicWorkspaceError(f"unknown event actor: {actor}")
        revision = len(self._events)
        body_json = canonical_json(body)
        envelope = {
            "revision": revision,
            "previous_hash": self.head_hash,
            "event_type": event_type,
            "actor": actor,
            "event_id": event_id,
            "body": json.loads(body_json),
        }
        event = WorkspaceEvent(
            revision=revision,
            previous_hash=self.head_hash,
            event_type=event_type,
            actor=actor,
            event_id=event_id,
            body_json=body_json,
            event_hash=content_hash(envelope),
        )
        self._events.append(event)
        return event

    def add_object(
        self,
        *,
        kind: str,
        semantic_key: Mapping[str, Any],
        payload: Mapping[str, Any],
        creator: str,
        dependency_ids: Iterable[str] = (),
    ) -> EpistemicObject:
        if creator not in CREATORS:
            raise EpistemicWorkspaceError(f"unknown object creator: {creator}")
        if not kind:
            raise EpistemicWorkspaceError("object kind must be non-empty")
        _assert_worker_payload(payload, creator)
        dependencies = tuple(sorted(set(dependency_ids)))
        missing = [item for item in dependencies if item not in self._objects]
        if missing:
            raise EpistemicWorkspaceError(
                f"object dependency is absent: {', '.join(missing)}"
            )
        semantic_key_json = canonical_json(dict(semantic_key))
        payload_json = canonical_json(dict(payload))
        object_id = "eo:" + content_hash(
            {"kind": kind, "semantic_key": json.loads(semantic_key_json)}
        )
        existing = self._objects.get(object_id)
        if existing is not None:
            if (
                existing.kind != kind
                or existing.creator != creator
                or existing.payload_json != payload_json
                or existing.dependency_ids != dependencies
            ):
                raise EpistemicWorkspaceError(
                    "stable epistemic identity was reused with different content"
                )
            return existing
        body = {
            "object_id": object_id,
            "kind": kind,
            "creator": creator,
            "semantic_key": json.loads(semantic_key_json),
            "payload": json.loads(payload_json),
            "dependency_ids": list(dependencies),
        }
        event = self._append("object-added", creator, object_id, body)
        value = EpistemicObject(
            object_id=object_id,
            kind=kind,
            creator=creator,
            created_revision=event.revision,
            semantic_key_json=semantic_key_json,
            payload_json=payload_json,
            dependency_ids=dependencies,
        )
        self._objects[object_id] = value
        return value

    def attend(
        self,
        *,
        worker: str,
        object_id: str,
        weight: int,
        channel: str,
        basis_ids: Iterable[str] = (),
        nonce: object | None = None,
    ) -> AttentionContribution:
        if worker not in WORKERS:
            raise EpistemicWorkspaceError(f"unknown cognitive worker: {worker}")
        if object_id not in self._objects:
            raise EpistemicWorkspaceError(f"attention target is absent: {object_id}")
        if not isinstance(weight, int) or isinstance(weight, bool) or weight <= 0:
            raise EpistemicWorkspaceError("attention weight must be a positive integer")
        basis = tuple(sorted(set(basis_ids)))
        if any(item not in self._objects for item in basis):
            raise EpistemicWorkspaceError("attention basis contains an absent object")
        key = {
            "worker": worker,
            "object_id": object_id,
            "weight": weight,
            "channel": channel,
            "basis_ids": basis,
            "nonce": nonce,
        }
        contribution_id = "ea:" + content_hash(key)
        existing = self._attention.get(contribution_id)
        if existing is not None:
            return existing
        body = {**key, "contribution_id": contribution_id}
        event = self._append("attention-contributed", worker, contribution_id, body)
        value = AttentionContribution(
            contribution_id=contribution_id,
            worker=worker,
            object_id=object_id,
            weight=weight,
            channel=channel,
            basis_ids=basis,
            created_revision=event.revision,
        )
        self._attention[contribution_id] = value
        return value

    def add_environment_evidence(
        self,
        *,
        target_id: str,
        verdict: str,
        transition_id: str,
        payload: Mapping[str, Any],
        dependency_ids: Iterable[str] = (),
        actor: str = "environment",
    ) -> EvidenceJudgment:
        if actor != "environment":
            raise EpistemicWorkspaceError("only the environment may author evidence")
        if target_id not in self._objects:
            raise EpistemicWorkspaceError(f"evidence target is absent: {target_id}")
        if verdict not in VERDICTS:
            raise EpistemicWorkspaceError(f"unknown evidence verdict: {verdict}")
        dependencies = tuple(sorted({target_id, *dependency_ids}))
        if any(item not in self._objects for item in dependencies):
            raise EpistemicWorkspaceError("evidence dependency contains an absent object")
        key = {
            "target_id": target_id,
            "verdict": verdict,
            "transition_id": transition_id,
            "payload": dict(payload),
            "dependency_ids": dependencies,
        }
        evidence_id = "ev:" + content_hash(key)
        existing = self._evidence.get(evidence_id)
        if existing is not None:
            return existing
        body = {**key, "evidence_id": evidence_id}
        event = self._append("environment-evidence", actor, evidence_id, body)
        value = EvidenceJudgment(
            evidence_id=evidence_id,
            target_id=target_id,
            verdict=verdict,
            transition_id=transition_id,
            payload_json=canonical_json(dict(payload)),
            dependency_ids=dependencies,
            created_revision=event.revision,
        )
        self._evidence[evidence_id] = value
        return value

    def evidence_counts(self, object_id: str) -> tuple[int, int, int]:
        self.object(object_id)
        supports = refutes = invalidates = 0
        for item in self._evidence.values():
            if item.target_id != object_id:
                continue
            supports += item.verdict == "supports"
            refutes += item.verdict == "refutes"
            invalidates += item.verdict == "invalidates"
        return supports, refutes, invalidates

    def support(self, object_id: str) -> int:
        supports, refutes, invalidates = self.evidence_counts(object_id)
        return supports - refutes - 1_000_000 * invalidates

    def attention(self, object_id: str, worker: str) -> int:
        self.object(object_id)
        if worker not in WORKERS:
            raise EpistemicWorkspaceError(f"unknown cognitive worker: {worker}")
        return sum(
            item.weight
            for item in self._attention.values()
            if item.object_id == object_id and item.worker == worker
        )

    def dependency_closure(self, root_ids: Iterable[str]) -> tuple[str, ...]:
        pending = list(dict.fromkeys(root_ids))
        seen: set[str] = set()
        while pending:
            object_id = pending.pop()
            if object_id in seen:
                continue
            value = self.object(object_id)
            seen.add(object_id)
            pending.extend(value.dependency_ids)
        return tuple(
            sorted(seen, key=lambda item: self._objects[item].created_revision)
        )

    def _estimated_units(self, object_ids: Iterable[str]) -> int:
        document = [
            {
                "id": item.object_id,
                "kind": item.kind,
                "creator": item.creator,
                "semantic_key": item.semantic_key,
                "payload": item.payload,
                "dependencies": item.dependency_ids,
                "support": self.support(item.object_id),
            }
            for item in (self._objects[object_id] for object_id in object_ids)
        ]
        return math.ceil(len(canonical_json(document)) / 4)

    def frontier(
        self,
        *,
        worker: str,
        budget: int,
        root_limit: int = 24,
    ) -> EpistemicFrontier:
        if worker not in WORKERS:
            raise EpistemicWorkspaceError(f"unknown cognitive worker: {worker}")
        if budget <= 0 or root_limit < 0:
            raise EpistemicWorkspaceError("frontier bounds must be non-negative")
        mandatory_roots = [
            item.object_id
            for item in self._objects.values()
            if item.kind == "binding"
            # A native matched schema instance is durable and addressable, but
            # it is not automatically an unresolved alternative.  Only an
            # explicitly declared competition/control set receives the
            # lossless mandatory-closure guarantee.  This prevents the full
            # exact R2 census from crowding cognition out of its own context.
            and item.payload.get("competition_set_id") is not None
            and str(item.payload.get("status", "live")) in LIVE_BINDING_STATUSES
            and self.evidence_counts(item.object_id)[2] == 0
        ]
        mandatory = self.dependency_closure(mandatory_roots)
        mandatory_cost = self._estimated_units(mandatory)
        if mandatory_cost > budget:
            raise FrontierCapacityError(budget=budget, required=mandatory_cost)
        selected = list(mandatory)
        selected_set = set(selected)
        candidates = [
            item
            for item in self._objects.values()
            if item.object_id not in selected_set
            and self.evidence_counts(item.object_id)[2] == 0
        ]
        candidates.sort(
            key=lambda item: (
                -self.attention(item.object_id, worker),
                -abs(self.support(item.object_id)),
                -item.created_revision,
                item.object_id,
            )
        )
        omitted: list[str] = []
        accepted_roots = 0
        for candidate in candidates:
            if accepted_roots >= root_limit:
                omitted.append(candidate.object_id)
                continue
            cluster = self.dependency_closure((candidate.object_id,))
            trial = list(dict.fromkeys((*selected, *cluster)))
            if self._estimated_units(trial) > budget:
                omitted.append(candidate.object_id)
                continue
            selected = trial
            selected_set.update(cluster)
            accepted_roots += 1
        return EpistemicFrontier(
            worker=worker,
            revision=self.revision,
            object_ids=tuple(selected),
            mandatory_ids=mandatory,
            omitted_root_ids=tuple(omitted),
            estimated_units=self._estimated_units(selected),
        )

    def deltas(self, cursor: int) -> tuple[WorkspaceEvent, ...]:
        if cursor < -1 or cursor > self.revision:
            raise EpistemicWorkspaceError("cursor is outside the event history")
        return tuple(self._events[cursor + 1 :])

    def ingest_native_runtime(self, runtime: Runtime) -> tuple[str, ...]:
        """Expose the current native R2 workspace without copying schema meaning.

        Schema objects are stable references to the authoritative native
        ``SchemaGraph`` rows.  Bindings are situated objects depending on those
        references.  Activation contributes R2 attention; it never changes
        empirical support.
        """

        current = runtime.workspace
        if current is None:
            raise EpistemicWorkspaceError("native runtime has no observed workspace")
        created: list[str] = []
        schema_objects: dict[int, EpistemicObject] = {}
        active_schema_ids = set(current.activation)
        active_schema_ids.update(binding.schema_id for binding in current.bindings)
        for schema_id in sorted(active_schema_ids, key=runtime.graph.canonical_hash.__getitem__):
            schema_hash = runtime.graph.canonical_hash[schema_id]
            value = self.add_object(
                kind="schema",
                semantic_key={"native_schema_hash": schema_hash},
                payload={
                    "native_schema_hash": schema_hash,
                    "display_name": runtime.graph.display_name[schema_id],
                    "depth": runtime.graph.depth[schema_id],
                },
                creator="r2",
            )
            schema_objects[schema_id] = value
            created.append(value.object_id)
            activation = max(1, int(round(100 * current.activation.get(schema_id, 0.0))))
            self.attend(
                worker="r2",
                object_id=value.object_id,
                weight=activation,
                channel="native-activation",
                nonce={"cycle": runtime.cycle, "context": current.context},
            )
        terms = runtime.graph.terms
        for binding in current.bindings:
            schema = schema_objects[binding.schema_id]
            assignments = [
                [variable, terms.value(term_id)]
                for variable, term_id in binding.assignments
            ]
            value = self.add_object(
                kind="binding",
                semantic_key={
                    "schema": schema.object_id,
                    "carrier": binding.carrier,
                    "assignments": assignments,
                },
                payload={
                    "status": "live",
                    "carrier": binding.carrier,
                    "assignments": assignments,
                    "provenance": binding.provenance,
                    "competition_set_id": None,
                },
                creator="r2",
                dependency_ids=(schema.object_id,),
            )
            created.append(value.object_id)
            self.attend(
                worker="r2",
                object_id=value.object_id,
                weight=max(1, int(round(100 * binding.activation))),
                channel="native-binding",
                basis_ids=(schema.object_id,),
                nonce={"cycle": runtime.cycle, "context": current.context},
            )
        return tuple(dict.fromkeys(created))

    def event_documents(self) -> tuple[dict[str, Any], ...]:
        return tuple(event.document() for event in self._events)

    @classmethod
    def replay(cls, documents: Iterable[Mapping[str, Any]]) -> "SharedEpistemicWorkspace":
        workspace = cls()
        for expected_revision, document in enumerate(documents):
            revision = int(document["revision"])
            if revision != expected_revision:
                raise EpistemicWorkspaceError("event revisions are not contiguous")
            previous_hash = document.get("previous_hash")
            if previous_hash != workspace.head_hash:
                raise EpistemicWorkspaceError("event hash chain is broken")
            event_type = str(document["event_type"])
            actor = str(document["actor"])
            event_id = str(document["event_id"])
            body = document["body"]
            envelope = {
                "revision": revision,
                "previous_hash": previous_hash,
                "event_type": event_type,
                "actor": actor,
                "event_id": event_id,
                "body": body,
            }
            if content_hash(envelope) != document.get("event_hash"):
                raise EpistemicWorkspaceError("event content hash is invalid")
            if event_type == "object-added":
                workspace.add_object(
                    kind=str(body["kind"]),
                    semantic_key=body["semantic_key"],
                    payload=body["payload"],
                    creator=actor,
                    dependency_ids=body["dependency_ids"],
                )
            elif event_type == "attention-contributed":
                workspace.attend(
                    worker=str(body["worker"]),
                    object_id=str(body["object_id"]),
                    weight=int(body["weight"]),
                    channel=str(body["channel"]),
                    basis_ids=body["basis_ids"],
                    nonce=body.get("nonce"),
                )
            elif event_type == "environment-evidence":
                workspace.add_environment_evidence(
                    target_id=str(body["target_id"]),
                    verdict=str(body["verdict"]),
                    transition_id=str(body["transition_id"]),
                    payload=body["payload"],
                    dependency_ids=[
                        item for item in body["dependency_ids"] if item != body["target_id"]
                    ],
                    actor=actor,
                )
            else:
                raise EpistemicWorkspaceError(f"unknown event type: {event_type}")
            if workspace.events[-1].event_id != event_id:
                raise EpistemicWorkspaceError("event identity changed during replay")
        return workspace
