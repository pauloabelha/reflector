from __future__ import annotations

import importlib.util
import json
import multiprocessing as mp
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("shared_attention_ledger", HERE / "ledger.py")
assert SPEC is not None and SPEC.loader is not None
LEDGER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LEDGER
SPEC.loader.exec_module(LEDGER)


def _append_many(root: str, worker: int, count: int) -> None:
    path = Path(root)
    for index in range(count):
        LEDGER.append_event(
            path,
            workspace_id="ws",
            event_type="EpistemicGraphEvent",
            actor="r2",
            event_id=f"worker-{worker}-{index}",
            payload={"graph_event_blob": LEDGER.put_blob(path, {"worker": worker, "index": index})},
        )


def test_parallel_append_is_one_contiguous_chain(tmp_path: Path) -> None:
    context = mp.get_context("fork")
    workers = [context.Process(target=_append_many, args=(str(tmp_path), index, 6)) for index in range(4)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join(timeout=20)
        assert worker.exitcode == 0
    events = LEDGER.list_events(tmp_path)
    assert len(events) == 24
    assert [item["seq"] for item in events] == list(range(24))
    assert len({item["event_id"] for item in events}) == 24


def test_blob_cursor_idempotence_and_pending_protocol(tmp_path: Path) -> None:
    digest = LEDGER.put_blob(tmp_path, {"answer": 42})
    assert LEDGER.read_blob(tmp_path, digest) == {"answer": 42}
    start = LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="WorkspaceStarted",
        actor="coordinator",
        event_id="start",
        payload={"job_key": "k"},
    )
    assert LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="WorkspaceStarted",
        actor="coordinator",
        event_id="start",
        payload={"job_key": "k"},
    ) == start
    pending = LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="ActionPending",
        actor="arbiter",
        payload={"action_id": 1, "before_digest": "before"},
    )
    assert LEDGER.pending_action(LEDGER.list_events(tmp_path))["event_id"] == pending["event_id"]
    LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="TransitionCommitted",
        actor="environment",
        payload={"pending_event_id": pending["event_id"], "after_digest": "after"},
    )
    assert LEDGER.pending_action(LEDGER.list_events(tmp_path)) is None
    LEDGER.write_cursor(tmp_path, "qwen", ledger_seq=2, graph_revision=7, metadata={"calls": 1})
    assert LEDGER.read_cursor(tmp_path, "qwen")["graph_revision"] == 7


def test_completed_qwen_reply_can_be_marked_integrated_idempotently(tmp_path: Path) -> None:
    completed = LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="QwenTaskCompleted",
        actor="qwen",
        payload={"task_id": "task-0", "compilation_blob": "digest"},
        event_id="completed-task-0",
    )
    integrated = LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="QwenTaskIntegrated",
        actor="coordinator",
        payload={"task_id": "task-0", "graph_revision": 4, "action_count": 8},
        event_id="integrated-task-0",
    )
    assert completed["seq"] == 0
    assert integrated["seq"] == 1
    assert LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="QwenTaskIntegrated",
        actor="coordinator",
        payload={"task_id": "task-0", "graph_revision": 4, "action_count": 8},
        event_id="integrated-task-0",
    ) == integrated


def test_repair_head_and_tamper_detection(tmp_path: Path) -> None:
    event = LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="WorkspaceStarted",
        actor="coordinator",
        payload={"job_key": "k"},
    )
    (tmp_path / "HEAD.json").write_text(json.dumps({"seq": -1, "event_hash": "stale"}))
    assert LEDGER.repair_head(tmp_path) == {"seq": 0, "event_hash": event["event_hash"]}
    path = tmp_path / "events" / "00000000.json"
    value = json.loads(path.read_text())
    value["payload"] = {"job_key": "tampered"}
    path.write_text(json.dumps(value))
    with pytest.raises(LEDGER.LedgerError, match="hash mismatch"):
        LEDGER.list_events(tmp_path)


def test_graph_batch_rejects_metadata_that_does_not_match_documents(tmp_path: Path) -> None:
    document = {"seq": 7, "prev_hash": "before", "event_hash": "after"}
    blob = LEDGER.put_blob(
        tmp_path,
        {
            "protocol": "shared-attention-graph-batch-v1",
            "count": 2,
            "first_revision": 7,
            "last_revision": 7,
            "first_prev_hash": "before",
            "last_event_hash": "after",
            "documents": [document],
        },
    )
    LEDGER.append_event(
        tmp_path,
        workspace_id="ws",
        event_type="EpistemicGraphBatch",
        actor="coordinator",
        payload={
            "graph_batch_blob": blob,
            "graph_event_count": 2,
            "first_graph_revision": 7,
            "last_graph_revision": 7,
            "first_graph_prev_hash": "before",
            "last_graph_event_hash": "after",
        },
    )

    with pytest.raises(LEDGER.LedgerError, match="metadata mismatch"):
        LEDGER.graph_event_documents(LEDGER.list_events(tmp_path), tmp_path)
