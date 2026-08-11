"""Crash-safe generic ledger for one shared epistemic workspace.

The ledger is the sole ordered durable history. Environment control records,
epistemic graph events, worker tasks, and lifecycle records all use the same
hash chain. Large values are stored as content-addressed blobs.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence


PROTOCOL = "shared-attention-ledger-v1"
EVENT_TYPES = frozenset(
    {
        "WorkspaceStarted",
        "InitialObservation",
        "EpistemicGraphEvent",
        "EpistemicGraphBatch",
        "QwenTaskQueued",
        "QwenTaskClaimed",
        "QwenTaskCompleted",
        "QwenTaskIntegrated",
        "QwenTaskAbandoned",
        "ActionDecision",
        "ActionPending",
        "TransitionCommitted",
        "WorkerCursorAdvanced",
        "WorkspaceStopped",
    }
)
ACTORS = frozenset({"coordinator", "environment", "arbiter", "r2", "qwen"})


class LedgerError(RuntimeError):
    pass


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(value)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_json(path: Path, value: object) -> None:
    atomic_bytes(path, (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8"))


def initialize(root: Path) -> None:
    for relative in ("events", "blobs/sha256", "cursors", "snapshots"):
        (root / relative).mkdir(parents=True, exist_ok=True)


def put_blob(root: Path, value: object) -> str:
    encoded = stable_json(value).encode("utf-8")
    digest = hashlib.sha256(encoded).hexdigest()
    path = root / "blobs" / "sha256" / f"{digest}.json"
    if path.exists():
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise LedgerError(f"corrupt existing blob: {digest}")
        return digest
    atomic_bytes(path, encoded)
    return digest


def read_blob(root: Path, digest: str) -> Any:
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise LedgerError("invalid blob digest")
    path = root / "blobs" / "sha256" / f"{digest}.json"
    encoded = path.read_bytes()
    if hashlib.sha256(encoded).hexdigest() != digest:
        raise LedgerError(f"blob digest mismatch: {digest}")
    return json.loads(encoded)


def event_hash(event: Mapping[str, Any]) -> str:
    return stable_hash({key: value for key, value in event.items() if key != "event_hash"})


def make_event(
    *,
    workspace_id: str,
    seq: int,
    prev_hash: str | None,
    event_type: str,
    actor: str,
    payload: Mapping[str, Any],
    event_id: str | None = None,
) -> dict[str, Any]:
    if event_type not in EVENT_TYPES:
        raise LedgerError(f"unsupported event type: {event_type}")
    if actor not in ACTORS:
        raise LedgerError(f"unsupported actor: {actor}")
    base = {
        "protocol": PROTOCOL,
        "workspace_id": workspace_id,
        "seq": int(seq),
        "prev_hash": prev_hash,
        "event_type": event_type,
        "actor": actor,
        "event_id": event_id
        or stable_hash(
            {
                "workspace_id": workspace_id,
                "event_type": event_type,
                "actor": actor,
                "payload": dict(payload),
            }
        ),
        "payload": dict(payload),
    }
    return {**base, "event_hash": stable_hash(base)}


def _read_event(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "protocol",
        "workspace_id",
        "seq",
        "prev_hash",
        "event_type",
        "actor",
        "event_id",
        "payload",
        "event_hash",
    }
    if set(value) != required or value["protocol"] != PROTOCOL:
        raise LedgerError(f"event contract mismatch: {path}")
    if event_hash(value) != value["event_hash"]:
        raise LedgerError(f"event hash mismatch: {path}")
    return value


def list_events(root: Path) -> list[dict[str, Any]]:
    paths = sorted((root / "events").glob("*.json")) if (root / "events").exists() else []
    events = [_read_event(path) for path in paths]
    seen_ids: set[str] = set()
    previous: str | None = None
    workspace_id: str | None = None
    for seq, event in enumerate(events):
        if event["seq"] != seq or event["prev_hash"] != previous:
            raise LedgerError("event chain is not contiguous")
        if workspace_id is None:
            workspace_id = str(event["workspace_id"])
        elif event["workspace_id"] != workspace_id:
            raise LedgerError("workspace id changed inside ledger")
        if event["event_id"] in seen_ids:
            raise LedgerError("duplicate event id")
        seen_ids.add(str(event["event_id"]))
        previous = str(event["event_hash"])
    return events


def repair_head(root: Path) -> dict[str, Any] | None:
    initialize(root)
    events = list_events(root)
    expected = None if not events else {
        "seq": events[-1]["seq"],
        "event_hash": events[-1]["event_hash"],
    }
    head_path = root / "HEAD.json"
    if expected is None:
        if head_path.exists():
            raise LedgerError("HEAD exists without events")
        return None
    observed = json.loads(head_path.read_text(encoding="utf-8")) if head_path.exists() else None
    if observed != expected:
        atomic_json(head_path, expected)
    return expected


def append_event(
    root: Path,
    *,
    workspace_id: str,
    event_type: str,
    actor: str,
    payload: Mapping[str, Any],
    event_id: str | None = None,
) -> dict[str, Any]:
    initialize(root)
    lock_path = root / "commit.lock"
    with lock_path.open("a+b") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        events = list_events(root)
        if events and events[0]["workspace_id"] != workspace_id:
            raise LedgerError("workspace id mismatch")
        candidate = make_event(
            workspace_id=workspace_id,
            seq=len(events),
            prev_hash=None if not events else str(events[-1]["event_hash"]),
            event_type=event_type,
            actor=actor,
            payload=payload,
            event_id=event_id,
        )
        existing = next((item for item in events if item["event_id"] == candidate["event_id"]), None)
        if existing is not None:
            comparable = {key: value for key, value in existing.items() if key not in {"seq", "prev_hash", "event_hash"}}
            proposed = {key: value for key, value in candidate.items() if key not in {"seq", "prev_hash", "event_hash"}}
            if comparable != proposed:
                raise LedgerError("event id reused with different content")
            return existing
        path = root / "events" / f"{candidate['seq']:08d}.json"
        atomic_json(path, candidate)
        atomic_json(root / "HEAD.json", {"seq": candidate["seq"], "event_hash": candidate["event_hash"]})
        return candidate


def cursor_path(root: Path, worker: str) -> Path:
    if worker not in {"environment", "r2", "qwen", "coordinator"}:
        raise LedgerError("invalid cursor worker")
    return root / "cursors" / f"{worker}.json"


def write_cursor(
    root: Path,
    worker: str,
    *,
    ledger_seq: int,
    graph_revision: int,
    metadata: Mapping[str, Any] | None = None,
) -> None:
    atomic_json(
        cursor_path(root, worker),
        {
            "protocol": PROTOCOL,
            "worker": worker,
            "ledger_seq": int(ledger_seq),
            "graph_revision": int(graph_revision),
            "metadata": dict(metadata or {}),
        },
    )


def read_cursor(root: Path, worker: str) -> dict[str, Any] | None:
    path = cursor_path(root, worker)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def graph_event_documents(events: Sequence[Mapping[str, Any]], root: Path) -> list[dict[str, Any]]:
    """Flatten durable graph transactions into their exact inner documents.

    A batch blob is made visible by one outer-ledger append, so recovery sees
    either all of its graph events or none of them.  The documents themselves
    retain their original graph sequence and hash chain and are replayed by
    ``epistemic_graph`` exactly as legacy singleton events are.
    """

    output: list[dict[str, Any]] = []
    for event in events:
        event_type = event["event_type"]
        if event_type == "EpistemicGraphEvent":
            document = read_blob(root, str(event["payload"]["graph_event_blob"]))
            if not isinstance(document, dict):
                raise LedgerError("graph event blob must contain one document")
            output.append(document)
            continue
        if event_type != "EpistemicGraphBatch":
            continue
        payload = event["payload"]
        envelope = read_blob(root, str(payload["graph_batch_blob"]))
        if not isinstance(envelope, dict) or set(envelope) != {
            "protocol",
            "count",
            "first_revision",
            "last_revision",
            "first_prev_hash",
            "last_event_hash",
            "documents",
        }:
            raise LedgerError("graph batch contract mismatch")
        if envelope["protocol"] != "shared-attention-graph-batch-v1":
            raise LedgerError("unsupported graph batch protocol")
        documents = envelope["documents"]
        if not isinstance(documents, list) or not documents or not all(
            isinstance(document, dict) for document in documents
        ):
            raise LedgerError("graph batch documents must be a nonempty list")
        expected = {
            "graph_event_count": len(documents),
            "first_graph_revision": documents[0].get("seq"),
            "last_graph_revision": documents[-1].get("seq"),
            "first_graph_prev_hash": documents[0].get("prev_hash"),
            "last_graph_event_hash": documents[-1].get("event_hash"),
        }
        envelope_expected = {
            "graph_event_count": envelope["count"],
            "first_graph_revision": envelope["first_revision"],
            "last_graph_revision": envelope["last_revision"],
            "first_graph_prev_hash": envelope["first_prev_hash"],
            "last_graph_event_hash": envelope["last_event_hash"],
        }
        if expected != envelope_expected or any(payload.get(key) != value for key, value in expected.items()):
            raise LedgerError("graph batch metadata mismatch")
        output.extend(documents)
    return output


def pending_action(events: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    pending: Mapping[str, Any] | None = None
    for event in events:
        if event["event_type"] == "ActionPending":
            if pending is not None:
                raise LedgerError("second action pending before commit")
            pending = event
        elif event["event_type"] == "TransitionCommitted":
            if pending is None or event["payload"].get("pending_event_id") != pending["event_id"]:
                raise LedgerError("transition does not commit current pending action")
            pending = None
    return pending
