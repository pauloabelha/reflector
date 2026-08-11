"""Durable event-sourced substrate for the parallel cognitive workspace.

The append-only event ledger is authoritative.  HEAD, reducer snapshots, and
worker cursors are replaceable caches which are always checked against it.
"""

from __future__ import annotations

import copy
import fcntl
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Iterable, Mapping


PROTOCOL = "parallel-cognitive-workspace-v0"
EVENT_TYPES = frozenset(
    {
        "WorkspaceStarted",
        "ObservationCommitted",
        "QwenTaskQueued",
        "QwenTaskClaimed",
        "QwenReplyRecorded",
        "QwenTaskAbandoned",
        "ExternalProposalAdjudicated",
        "R2DecisionPublished",
        "ActionPending",
        "TransitionCommitted",
        "WorkspaceStopped",
    }
)
ACTOR_AUTHORITY = {
    "WorkspaceStarted": frozenset({"coordinator"}),
    "ObservationCommitted": frozenset({"environment"}),
    "QwenTaskQueued": frozenset({"environment", "coordinator"}),
    "QwenTaskClaimed": frozenset({"qwen"}),
    "QwenReplyRecorded": frozenset({"qwen"}),
    "QwenTaskAbandoned": frozenset({"qwen", "coordinator"}),
    "ExternalProposalAdjudicated": frozenset({"r2"}),
    "R2DecisionPublished": frozenset({"r2"}),
    "ActionPending": frozenset({"environment"}),
    "TransitionCommitted": frozenset({"environment"}),
    "WorkspaceStopped": frozenset({"environment", "coordinator"}),
}
TERMINAL_TASK_STATES = frozenset({"abandoned", "adjudicated"})


class WorkspaceError(RuntimeError):
    """Raised when the durable ledger or an event violates the protocol."""


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json(path: Path, value: object) -> None:
    """Durably replace one JSON document and its directory entry."""

    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorkspaceError(f"invalid JSON document: {path}") from error
    if not isinstance(value, dict):
        raise WorkspaceError(f"expected JSON object: {path}")
    return value


def initialize_directories(root: Path) -> None:
    for relative in ("events", "blobs/sha256", "cursors", "snapshots"):
        (root / relative).mkdir(parents=True, exist_ok=True)


def put_blob(root: Path, value: object) -> str:
    """Store canonical JSON by SHA-256; concurrent identical puts are safe."""

    initialize_directories(root)
    encoded = (stable_json(value) + "\n").encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    path = root / "blobs" / "sha256" / f"{digest}.json"
    if path.exists():
        if path.read_bytes() != encoded:
            raise WorkspaceError(f"blob digest collision or corruption: {digest}")
        return digest
    descriptor, temporary = tempfile.mkstemp(prefix=f".{digest}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return digest


def read_blob(root: Path, digest: str) -> Any:
    path = root / "blobs" / "sha256" / f"{digest}.json"
    encoded = path.read_bytes()
    if hashlib.sha256(encoded).hexdigest() != digest:
        raise WorkspaceError(f"blob hash mismatch: {digest}")
    return json.loads(encoded)


@dataclass(frozen=True, slots=True)
class TaskState:
    task_id: str
    status: str
    basis_version: int
    basis_digest: str
    request_blob: str
    projection_blob: str
    worker_epoch: str | None = None
    response_blob: str | None = None
    adjudication: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class WorkspaceState:
    workspace_id: str | None = None
    job_key: str | None = None
    head_seq: int = -1
    head_hash: str | None = None
    event_ids: tuple[str, ...] = ()
    observation_version: int | None = None
    observation_digest: str | None = None
    observation_blob: str | None = None
    legal_actions: tuple[int, ...] = ()
    levels_completed: int = 0
    observations: tuple[tuple[int, str, str], ...] = ()
    transitions: tuple[str, ...] = ()
    pending_action: dict[str, Any] | None = None
    tasks: tuple[TaskState, ...] = ()
    latest_r2_decision: dict[str, Any] | None = None
    stopped: bool = False
    stop_reason: str | None = None


def _event_without_hash(event: Mapping[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in event.items() if key != "event_hash"}


def event_hash(event: Mapping[str, Any]) -> str:
    return stable_hash(_event_without_hash(event))


def make_event(
    *,
    workspace_id: str,
    seq: int,
    prev_event_hash: str | None,
    event_type: str,
    actor: str,
    payload: Mapping[str, Any],
    basis: Mapping[str, Any] | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    basis_value = copy.deepcopy(dict(basis or {}))
    payload_value = copy.deepcopy(dict(payload))
    identity = event_id or stable_hash(
        {
            "workspace_id": workspace_id,
            "type": event_type,
            "actor": actor,
            "basis": basis_value,
            "payload": payload_value,
        }
    )
    event = {
        "protocol": PROTOCOL,
        "workspace_id": workspace_id,
        "seq": int(seq),
        "event_id": identity,
        "type": event_type,
        "actor": actor,
        "prev_event_hash": prev_event_hash,
        "basis": basis_value,
        "payload": payload_value,
    }
    return {**event, "event_hash": event_hash(event)}


def _require_fields(payload: Mapping[str, Any], fields: Iterable[str], event_type: str) -> None:
    missing = [field for field in fields if field not in payload]
    if missing:
        raise WorkspaceError(f"{event_type} missing fields: {missing}")


def _task_map(state: WorkspaceState) -> dict[str, TaskState]:
    return {task.task_id: task for task in state.tasks}


def _with_tasks(state: WorkspaceState, tasks: Mapping[str, TaskState]) -> WorkspaceState:
    return replace(state, tasks=tuple(tasks[key] for key in sorted(tasks)))


def _observation_at(state: WorkspaceState, version: int) -> tuple[int, str, str] | None:
    return next((item for item in state.observations if item[0] == version), None)


def _validate_envelope(state: WorkspaceState, event: Mapping[str, Any]) -> None:
    required = {
        "protocol",
        "workspace_id",
        "seq",
        "event_id",
        "type",
        "actor",
        "prev_event_hash",
        "basis",
        "payload",
        "event_hash",
    }
    if set(event) != required:
        raise WorkspaceError("event envelope contract mismatch")
    if event["protocol"] != PROTOCOL:
        raise WorkspaceError("event protocol mismatch")
    if event["type"] not in EVENT_TYPES:
        raise WorkspaceError(f"unknown event type: {event['type']}")
    if event["actor"] not in ACTOR_AUTHORITY[event["type"]]:
        raise WorkspaceError(f"actor {event['actor']} cannot emit {event['type']}")
    if event_hash(event) != event["event_hash"]:
        raise WorkspaceError("event hash mismatch")
    if event["event_id"] in state.event_ids:
        raise WorkspaceError(f"duplicate event id: {event['event_id']}")
    if event["seq"] != state.head_seq + 1:
        raise WorkspaceError("event sequence is not contiguous")
    if event["prev_event_hash"] != state.head_hash:
        raise WorkspaceError("event predecessor hash mismatch")
    if state.workspace_id is not None and event["workspace_id"] != state.workspace_id:
        raise WorkspaceError("workspace id mismatch")
    if not isinstance(event["basis"], dict) or not isinstance(event["payload"], dict):
        raise WorkspaceError("basis and payload must be objects")


def reduce_event(state: WorkspaceState, event: Mapping[str, Any]) -> WorkspaceState:
    """Purely apply one validated event to immutable canonical state."""

    _validate_envelope(state, event)
    kind = str(event["type"])
    payload = event["payload"]
    next_state = state

    if kind == "WorkspaceStarted":
        if state.head_seq != -1:
            raise WorkspaceError("WorkspaceStarted must be the first event")
        _require_fields(payload, ("job_key",), kind)
        next_state = replace(
            state,
            workspace_id=str(event["workspace_id"]),
            job_key=str(payload["job_key"]),
        )
    elif state.workspace_id is None:
        raise WorkspaceError("workspace has not started")
    elif state.stopped:
        raise WorkspaceError("workspace is already stopped")
    elif kind == "ObservationCommitted":
        _require_fields(
            payload,
            ("observation_version", "observation_digest", "observation_blob", "legal_actions", "levels_completed"),
            kind,
        )
        version = int(payload["observation_version"])
        if state.observation_version is not None or version != 0:
            raise WorkspaceError("ObservationCommitted is only valid for initial version 0")
        actions = tuple(sorted(set(int(item) for item in payload["legal_actions"])))
        next_state = replace(
            state,
            observation_version=version,
            observation_digest=str(payload["observation_digest"]),
            observation_blob=str(payload["observation_blob"]),
            legal_actions=actions,
            levels_completed=int(payload["levels_completed"]),
            observations=((version, str(payload["observation_digest"]), str(payload["observation_blob"])),),
        )
    elif kind == "QwenTaskQueued":
        _require_fields(
            payload,
            ("task_id", "basis_observation_version", "basis_observation_digest", "request_blob", "projection_blob"),
            kind,
        )
        if state.observation_version is None:
            raise WorkspaceError("cannot queue Qwen before an observation")
        if any(task.status not in TERMINAL_TASK_STATES for task in state.tasks):
            raise WorkspaceError("only one Qwen task may be outstanding")
        version = int(payload["basis_observation_version"])
        digest = str(payload["basis_observation_digest"])
        if version != state.observation_version or digest != state.observation_digest:
            raise WorkspaceError("Qwen task basis is not the current observation")
        tasks = _task_map(state)
        task_id = str(payload["task_id"])
        if task_id in tasks:
            raise WorkspaceError("Qwen task id already exists")
        tasks[task_id] = TaskState(
            task_id=task_id,
            status="queued",
            basis_version=version,
            basis_digest=digest,
            request_blob=str(payload["request_blob"]),
            projection_blob=str(payload["projection_blob"]),
        )
        next_state = _with_tasks(state, tasks)
    elif kind == "QwenTaskClaimed":
        _require_fields(payload, ("task_id", "worker_epoch"), kind)
        tasks = _task_map(state)
        task = tasks.get(str(payload["task_id"]))
        if task is None or task.status != "queued":
            raise WorkspaceError("only a queued Qwen task may be claimed")
        tasks[task.task_id] = replace(task, status="claimed", worker_epoch=str(payload["worker_epoch"]))
        next_state = _with_tasks(state, tasks)
    elif kind == "QwenReplyRecorded":
        _require_fields(payload, ("task_id", "worker_epoch", "response_blob"), kind)
        tasks = _task_map(state)
        task = tasks.get(str(payload["task_id"]))
        if task is None or task.status != "claimed":
            raise WorkspaceError("reply requires a claimed Qwen task")
        if str(payload["worker_epoch"]) != task.worker_epoch:
            raise WorkspaceError("Qwen reply worker epoch mismatch")
        tasks[task.task_id] = replace(task, status="replied", response_blob=str(payload["response_blob"]))
        next_state = _with_tasks(state, tasks)
    elif kind == "QwenTaskAbandoned":
        _require_fields(payload, ("task_id", "reason"), kind)
        tasks = _task_map(state)
        task = tasks.get(str(payload["task_id"]))
        if task is None or task.status not in {"queued", "claimed"}:
            raise WorkspaceError("only queued or claimed Qwen tasks may be abandoned")
        tasks[task.task_id] = replace(task, status="abandoned", reason=str(payload["reason"]))
        next_state = _with_tasks(state, tasks)
    elif kind == "ExternalProposalAdjudicated":
        _require_fields(payload, ("task_id", "verdict", "adjudication_blob"), kind)
        tasks = _task_map(state)
        task = tasks.get(str(payload["task_id"]))
        if task is None or task.status != "replied":
            raise WorkspaceError("adjudication requires a recorded Qwen reply")
        verdict = str(payload["verdict"])
        if verdict not in {"accepted", "rejected", "deferred"}:
            raise WorkspaceError("unknown adjudication verdict")
        tasks[task.task_id] = replace(task, status="adjudicated", adjudication=verdict)
        next_state = _with_tasks(state, tasks)
    elif kind == "R2DecisionPublished":
        _require_fields(
            payload,
            ("decision_id", "observation_version", "observation_digest", "decision_blob"),
            kind,
        )
        version = int(payload["observation_version"])
        observed = _observation_at(state, version)
        if observed is None or observed[1] != str(payload["observation_digest"]):
            raise WorkspaceError("R2 decision references an unknown observation")
        if version == state.observation_version and state.pending_action is None:
            decision = copy.deepcopy(dict(payload))
            decision["event_id"] = str(event["event_id"])
            next_state = replace(state, latest_r2_decision=decision)
    elif kind == "ActionPending":
        _require_fields(
            payload,
            ("before_version", "before_digest", "action_id", "data", "decision_event_id"),
            kind,
        )
        if state.observation_version is None or state.pending_action is not None:
            raise WorkspaceError("an action is already pending or no observation exists")
        if int(payload["before_version"]) != state.observation_version or str(payload["before_digest"]) != state.observation_digest:
            raise WorkspaceError("pending action predecessor mismatch")
        action = int(payload["action_id"])
        if action not in state.legal_actions:
            raise WorkspaceError("pending action is not legal")
        decision_event_id = payload["decision_event_id"]
        if decision_event_id is not None and (
            state.latest_r2_decision is None
            or str(decision_event_id) != state.latest_r2_decision.get("event_id")
        ):
            raise WorkspaceError("pending action references no current R2 decision")
        pending = copy.deepcopy(dict(payload))
        pending["event_id"] = str(event["event_id"])
        next_state = replace(state, pending_action=pending)
    elif kind == "TransitionCommitted":
        _require_fields(
            payload,
            (
                "pending_event_id",
                "before_version",
                "before_digest",
                "action_id",
                "after_version",
                "after_digest",
                "after_blob",
                "legal_actions",
                "levels_completed",
            ),
            kind,
        )
        pending = state.pending_action
        if pending is None:
            raise WorkspaceError("transition has no pending action")
        if str(payload["pending_event_id"]) != pending["event_id"]:
            raise WorkspaceError("transition pending-event mismatch")
        if int(payload["before_version"]) != state.observation_version or str(payload["before_digest"]) != state.observation_digest:
            raise WorkspaceError("transition predecessor observation mismatch")
        if int(payload["action_id"]) != int(pending["action_id"]):
            raise WorkspaceError("transition action mismatch")
        after_version = int(payload["after_version"])
        if after_version != int(state.observation_version) + 1:
            raise WorkspaceError("transition must advance exactly one observation version")
        after_digest = str(payload["after_digest"])
        after_blob = str(payload["after_blob"])
        actions = tuple(sorted(set(int(item) for item in payload["legal_actions"])))
        next_state = replace(
            state,
            observation_version=after_version,
            observation_digest=after_digest,
            observation_blob=after_blob,
            legal_actions=actions,
            levels_completed=int(payload["levels_completed"]),
            observations=(*state.observations, (after_version, after_digest, after_blob)),
            transitions=(*state.transitions, str(event["event_id"])),
            pending_action=None,
            latest_r2_decision=None,
        )
    elif kind == "WorkspaceStopped":
        _require_fields(payload, ("reason",), kind)
        if state.pending_action is not None:
            raise WorkspaceError("cannot stop with a pending action")
        next_state = replace(state, stopped=True, stop_reason=str(payload["reason"]))

    return replace(
        next_state,
        head_seq=int(event["seq"]),
        head_hash=str(event["event_hash"]),
        event_ids=(*state.event_ids, str(event["event_id"])),
    )


def _event_path(root: Path, seq: int) -> Path:
    return root / "events" / f"{seq:08d}.json"


def list_events(root: Path) -> list[dict[str, Any]]:
    paths = sorted((root / "events").glob("*.json")) if (root / "events").exists() else []
    events = [_read_json(path) for path in paths]
    for index, event in enumerate(events):
        if Path(paths[index]).stem != f"{index:08d}" or int(event.get("seq", -1)) != index:
            raise WorkspaceError("event files are not a contiguous sequence")
    return events


def reduce_events(events: Iterable[Mapping[str, Any]]) -> WorkspaceState:
    state = WorkspaceState()
    for event in events:
        state = reduce_event(state, event)
    return state


def reduce_workspace(root: Path) -> WorkspaceState:
    return reduce_events(list_events(root))


def _head_value(event: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "seq": int(event["seq"]),
        "event_id": str(event["event_id"]),
        "event_hash": str(event["event_hash"]),
    }


def _repair_head_locked(root: Path) -> dict[str, Any] | None:
    initialize_directories(root)
    head_path = root / "HEAD.json"
    events = list_events(root)
    if not events:
        if head_path.exists():
            raise WorkspaceError("HEAD exists without ledger events")
        return None
    if head_path.exists():
        head = _read_json(head_path)
        seq = int(head.get("seq", -1))
        if seq < 0 or seq >= len(events):
            raise WorkspaceError("HEAD sequence is outside the ledger")
        if _head_value(events[seq]) != head:
            raise WorkspaceError("HEAD does not match its ledger event")
        orphan_count = len(events) - seq - 1
        if orphan_count > 1:
            raise WorkspaceError("more than one orphan successor follows HEAD")
        if orphan_count == 1:
            successor = events[seq + 1]
            if successor["prev_event_hash"] != head["event_hash"]:
                raise WorkspaceError("orphan successor does not extend HEAD")
            reduce_events(events[: seq + 2])
            head = _head_value(successor)
            atomic_json(head_path, head)
        return head
    if len(events) != 1 or int(events[0]["seq"]) != 0:
        raise WorkspaceError("missing HEAD can repair only one genesis event")
    reduce_events(events)
    head = _head_value(events[0])
    atomic_json(head_path, head)
    return head


def repair_head(root: Path) -> dict[str, Any] | None:
    initialize_directories(root)
    lock_path = root / "commit.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        return _repair_head_locked(root)


def commit_event(
    root: Path,
    *,
    workspace_id: str,
    event_type: str,
    actor: str,
    payload: Mapping[str, Any],
    basis: Mapping[str, Any] | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Validate and append one event under the workspace commit lock."""

    initialize_directories(root)
    lock_path = root / "commit.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        _repair_head_locked(root)
        events = list_events(root)
        state = reduce_events(events)
        candidate_id = event_id or stable_hash(
            {
                "workspace_id": workspace_id,
                "type": event_type,
                "actor": actor,
                "basis": dict(basis or {}),
                "payload": dict(payload),
            }
        )
        for existing in events:
            if existing["event_id"] != candidate_id:
                continue
            expected = make_event(
                workspace_id=workspace_id,
                seq=int(existing["seq"]),
                prev_event_hash=existing["prev_event_hash"],
                event_type=event_type,
                actor=actor,
                payload=payload,
                basis=basis,
                event_id=candidate_id,
            )
            if _event_without_hash(existing) != _event_without_hash(expected):
                raise WorkspaceError("event id was reused for different content")
            return existing
        event = make_event(
            workspace_id=workspace_id,
            seq=state.head_seq + 1,
            prev_event_hash=state.head_hash,
            event_type=event_type,
            actor=actor,
            payload=payload,
            basis=basis,
            event_id=candidate_id,
        )
        reduce_event(state, event)
        atomic_json(_event_path(root, int(event["seq"])), event)
        atomic_json(root / "HEAD.json", _head_value(event))
        return event


def state_document(state: WorkspaceState) -> dict[str, Any]:
    value = asdict(state)
    value["legal_actions"] = list(state.legal_actions)
    value["observations"] = [list(item) for item in state.observations]
    value["transitions"] = list(state.transitions)
    value["event_ids"] = list(state.event_ids)
    value["tasks"] = [asdict(task) for task in state.tasks]
    return value


def write_snapshot(root: Path, state: WorkspaceState | None = None, name: str = "latest") -> Path:
    canonical = state or reduce_workspace(root)
    document = state_document(canonical)
    snapshot = {
        "protocol": PROTOCOL,
        "through_seq": canonical.head_seq,
        "head_hash": canonical.head_hash,
        "state": document,
        "state_hash": stable_hash(document),
    }
    path = root / "snapshots" / f"{name}.json"
    atomic_json(path, snapshot)
    return path


def load_snapshot(root: Path, name: str = "latest") -> WorkspaceState:
    snapshot = _read_json(root / "snapshots" / f"{name}.json")
    if snapshot.get("protocol") != PROTOCOL or stable_hash(snapshot.get("state")) != snapshot.get("state_hash"):
        raise WorkspaceError("snapshot content hash mismatch")
    seq = int(snapshot.get("through_seq", -2))
    events = list_events(root)
    if seq < -1 or seq >= len(events):
        raise WorkspaceError("snapshot sequence is outside the ledger")
    canonical = reduce_events(events[: seq + 1])
    if canonical.head_hash != snapshot.get("head_hash") or state_document(canonical) != snapshot.get("state"):
        raise WorkspaceError("snapshot is not canonical for its ledger prefix")
    return canonical


def write_cursor(
    root: Path,
    worker: str,
    *,
    seq: int,
    event_hash_value: str | None,
    metadata: Mapping[str, Any] | None = None,
) -> Path:
    events = list_events(root)
    if seq == -1:
        if event_hash_value is not None:
            raise WorkspaceError("pre-ledger cursor hash must be null")
    elif seq < 0 or seq >= len(events) or events[seq]["event_hash"] != event_hash_value:
        raise WorkspaceError("cursor does not reference a canonical event")
    document = {
        "protocol": PROTOCOL,
        "worker": worker,
        "seq": seq,
        "event_hash": event_hash_value,
        "metadata": copy.deepcopy(dict(metadata or {})),
    }
    value = {**document, "cursor_hash": stable_hash(document)}
    path = root / "cursors" / f"{worker}.json"
    atomic_json(path, value)
    return path


def load_cursor(root: Path, worker: str) -> dict[str, Any]:
    value = _read_json(root / "cursors" / f"{worker}.json")
    document = {key: copy.deepcopy(item) for key, item in value.items() if key != "cursor_hash"}
    if value.get("protocol") != PROTOCOL or value.get("worker") != worker:
        raise WorkspaceError("cursor identity mismatch")
    if stable_hash(document) != value.get("cursor_hash"):
        raise WorkspaceError("cursor content hash mismatch")
    events = list_events(root)
    seq = int(value["seq"])
    if seq == -1:
        if value.get("event_hash") is not None:
            raise WorkspaceError("pre-ledger cursor hash must be null")
    elif seq < 0 or seq >= len(events) or events[seq]["event_hash"] != value.get("event_hash"):
        raise WorkspaceError("cursor is not on the canonical ledger")
    return value
