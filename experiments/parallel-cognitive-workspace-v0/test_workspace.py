from __future__ import annotations

import importlib.util
import json
import multiprocessing
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("parallel_workspace", HERE / "workspace.py")
assert SPEC is not None and SPEC.loader is not None
WORKSPACE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = WORKSPACE
SPEC.loader.exec_module(WORKSPACE)


def start_workspace(root: Path, workspace_id: str = "workspace-test") -> tuple[dict, dict]:
    started = WORKSPACE.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="WorkspaceStarted",
        actor="coordinator",
        payload={"job_key": "job-test"},
    )
    observation_blob = WORKSPACE.put_blob(root, {"grid": [[0, 0], [0, 0]]})
    observed = WORKSPACE.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="ObservationCommitted",
        actor="environment",
        payload={
            "observation_version": 0,
            "observation_digest": "observation-0",
            "observation_blob": observation_blob,
            "legal_actions": [3, 1, 1, 2],
            "levels_completed": 0,
        },
    )
    return started, observed


def append_decisions(root_text: str, workspace_id: str, worker: int, count: int) -> None:
    root = Path(root_text)
    decision_blob = WORKSPACE.put_blob(root, {"worker": worker})
    for index in range(count):
        WORKSPACE.commit_event(
            root,
            workspace_id=workspace_id,
            event_type="R2DecisionPublished",
            actor="r2",
            payload={
                "decision_id": f"decision-{worker}-{index}",
                "observation_version": 0,
                "observation_digest": "observation-0",
                "decision_blob": decision_blob,
            },
            event_id=f"event-decision-{worker}-{index}",
        )


def test_blob_store_is_canonical_content_addressed_and_detects_corruption(tmp_path: Path) -> None:
    first = WORKSPACE.put_blob(tmp_path, {"b": [2, 3], "a": 1})
    second = WORKSPACE.put_blob(tmp_path, {"a": 1, "b": [2, 3]})

    assert first == second
    assert WORKSPACE.read_blob(tmp_path, first) == {"a": 1, "b": [2, 3]}

    path = tmp_path / "blobs" / "sha256" / f"{first}.json"
    path.write_text('{"corrupt":true}\n', encoding="utf-8")
    with pytest.raises(WORKSPACE.WorkspaceError, match="blob hash mismatch"):
        WORKSPACE.read_blob(tmp_path, first)


def test_reducer_enforces_authority_task_lifecycle_and_pending_transition(tmp_path: Path) -> None:
    workspace_id = "authority-test"
    start_workspace(tmp_path, workspace_id)
    request_blob = WORKSPACE.put_blob(tmp_path, {"request": 1})
    projection_blob = WORKSPACE.put_blob(tmp_path, {"state": 0})

    with pytest.raises(WORKSPACE.WorkspaceError, match="cannot emit"):
        WORKSPACE.commit_event(
            tmp_path,
            workspace_id=workspace_id,
            event_type="QwenTaskQueued",
            actor="r2",
            payload={
                "task_id": "task-1",
                "basis_observation_version": 0,
                "basis_observation_digest": "observation-0",
                "request_blob": request_blob,
                "projection_blob": projection_blob,
            },
        )

    WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="QwenTaskQueued",
        actor="environment",
        payload={
            "task_id": "task-1",
            "basis_observation_version": 0,
            "basis_observation_digest": "observation-0",
            "request_blob": request_blob,
            "projection_blob": projection_blob,
        },
    )
    with pytest.raises(WORKSPACE.WorkspaceError, match="only one Qwen task"):
        WORKSPACE.commit_event(
            tmp_path,
            workspace_id=workspace_id,
            event_type="QwenTaskQueued",
            actor="environment",
            payload={
                "task_id": "task-2",
                "basis_observation_version": 0,
                "basis_observation_digest": "observation-0",
                "request_blob": request_blob,
                "projection_blob": projection_blob,
            },
        )
    WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="QwenTaskClaimed",
        actor="qwen",
        payload={"task_id": "task-1", "worker_epoch": "epoch-a"},
    )
    with pytest.raises(WORKSPACE.WorkspaceError, match="worker epoch mismatch"):
        WORKSPACE.commit_event(
            tmp_path,
            workspace_id=workspace_id,
            event_type="QwenReplyRecorded",
            actor="qwen",
            payload={"task_id": "task-1", "worker_epoch": "epoch-b", "response_blob": "reply"},
        )
    response_blob = WORKSPACE.put_blob(tmp_path, {"reply": []})
    WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="QwenReplyRecorded",
        actor="qwen",
        payload={"task_id": "task-1", "worker_epoch": "epoch-a", "response_blob": response_blob},
    )
    adjudication_blob = WORKSPACE.put_blob(tmp_path, {"accepted": []})
    WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="ExternalProposalAdjudicated",
        actor="r2",
        payload={"task_id": "task-1", "verdict": "rejected", "adjudication_blob": adjudication_blob},
    )

    decision_blob = WORKSPACE.put_blob(tmp_path, {"action": 2})
    decision = WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="R2DecisionPublished",
        actor="r2",
        payload={
            "decision_id": "decision-current",
            "observation_version": 0,
            "observation_digest": "observation-0",
            "decision_blob": decision_blob,
        },
    )
    with pytest.raises(WORKSPACE.WorkspaceError, match="no current R2 decision"):
        WORKSPACE.commit_event(
            tmp_path,
            workspace_id=workspace_id,
            event_type="ActionPending",
            actor="environment",
            payload={
                "before_version": 0,
                "before_digest": "observation-0",
                "action_id": 2,
                "data": {},
                "decision_event_id": "stale-decision-event",
            },
        )
    pending = WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="ActionPending",
        actor="environment",
        payload={
            "before_version": 0,
            "before_digest": "observation-0",
            "action_id": 2,
            "data": {},
            "decision_event_id": decision["event_id"],
        },
    )
    with pytest.raises(WORKSPACE.WorkspaceError, match="already pending"):
        WORKSPACE.commit_event(
            tmp_path,
            workspace_id=workspace_id,
            event_type="ActionPending",
            actor="environment",
            payload={
                "before_version": 0,
                "before_digest": "observation-0",
                "action_id": 1,
                "data": {},
                "decision_event_id": None,
            },
        )
    after_blob = WORKSPACE.put_blob(tmp_path, {"grid": [[1, 0], [0, 0]]})
    with pytest.raises(WORKSPACE.WorkspaceError, match="action mismatch"):
        WORKSPACE.commit_event(
            tmp_path,
            workspace_id=workspace_id,
            event_type="TransitionCommitted",
            actor="environment",
            payload={
                "pending_event_id": pending["event_id"],
                "before_version": 0,
                "before_digest": "observation-0",
                "action_id": 1,
                "after_version": 1,
                "after_digest": "observation-1",
                "after_blob": after_blob,
                "legal_actions": [1, 2, 3],
                "levels_completed": 0,
            },
        )
    WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="TransitionCommitted",
        actor="environment",
        payload={
            "pending_event_id": pending["event_id"],
            "before_version": 0,
            "before_digest": "observation-0",
            "action_id": 2,
            "after_version": 1,
            "after_digest": "observation-1",
            "after_blob": after_blob,
            "legal_actions": [1, 2, 3],
            "levels_completed": 0,
        },
    )

    state = WORKSPACE.reduce_workspace(tmp_path)
    assert state.observation_version == 1
    assert state.observation_digest == "observation-1"
    assert state.pending_action is None
    assert state.tasks[0].status == "adjudicated"
    assert state.tasks[0].adjudication == "rejected"
    assert len(state.transitions) == 1


def test_flock_serializes_multiprocess_commits_without_loss(tmp_path: Path) -> None:
    workspace_id = "parallel-append-test"
    start_workspace(tmp_path, workspace_id)
    context = multiprocessing.get_context("fork")
    processes = [
        context.Process(target=append_decisions, args=(str(tmp_path), workspace_id, worker, 8))
        for worker in range(4)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=20)
        assert process.exitcode == 0

    events = WORKSPACE.list_events(tmp_path)
    state = WORKSPACE.reduce_events(events)
    assert len(events) == 2 + 4 * 8
    assert [event["seq"] for event in events] == list(range(len(events)))
    assert len({event["event_id"] for event in events}) == len(events)
    assert state.head_seq == len(events) - 1
    assert json.loads((tmp_path / "HEAD.json").read_text())["event_hash"] == events[-1]["event_hash"]


def test_deterministic_event_retry_is_idempotent_but_id_reuse_is_rejected(tmp_path: Path) -> None:
    workspace_id = "idempotence-test"
    start_workspace(tmp_path, workspace_id)
    decision_blob = WORKSPACE.put_blob(tmp_path, {"action": 1})
    payload = {
        "decision_id": "decision-stable",
        "observation_version": 0,
        "observation_digest": "observation-0",
        "decision_blob": decision_blob,
    }
    first = WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="R2DecisionPublished",
        actor="r2",
        payload=payload,
        event_id="stable-event-id",
    )
    retry = WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="R2DecisionPublished",
        actor="r2",
        payload=payload,
        event_id="stable-event-id",
    )

    assert retry == first
    assert len(WORKSPACE.list_events(tmp_path)) == 3
    with pytest.raises(WORKSPACE.WorkspaceError, match="reused for different content"):
        WORKSPACE.commit_event(
            tmp_path,
            workspace_id=workspace_id,
            event_type="R2DecisionPublished",
            actor="r2",
            payload={**payload, "decision_id": "different-decision"},
            event_id="stable-event-id",
        )


def test_head_repairs_exactly_one_orphan_successor(tmp_path: Path) -> None:
    workspace_id = "repair-test"
    _started, observed = start_workspace(tmp_path, workspace_id)
    decision_blob = WORKSPACE.put_blob(tmp_path, {"action": 1})
    orphan = WORKSPACE.make_event(
        workspace_id=workspace_id,
        seq=2,
        prev_event_hash=observed["event_hash"],
        event_type="R2DecisionPublished",
        actor="r2",
        payload={
            "decision_id": "decision-orphan",
            "observation_version": 0,
            "observation_digest": "observation-0",
            "decision_blob": decision_blob,
        },
    )
    WORKSPACE.atomic_json(tmp_path / "events" / "00000002.json", orphan)

    repaired = WORKSPACE.repair_head(tmp_path)

    assert repaired == {
        "protocol": WORKSPACE.PROTOCOL,
        "seq": 2,
        "event_id": orphan["event_id"],
        "event_hash": orphan["event_hash"],
    }
    assert WORKSPACE.reduce_workspace(tmp_path).head_hash == orphan["event_hash"]


def test_snapshot_and_cursor_are_canonical_ledger_checked_caches(tmp_path: Path) -> None:
    _started, observed = start_workspace(tmp_path, "cache-test")
    state = WORKSPACE.reduce_workspace(tmp_path)
    WORKSPACE.write_snapshot(tmp_path, state)
    WORKSPACE.write_cursor(
        tmp_path,
        "r2",
        seq=observed["seq"],
        event_hash_value=observed["event_hash"],
        metadata={"controller_rebuild": "through-observation-0"},
    )

    assert WORKSPACE.load_snapshot(tmp_path) == state
    cursor = WORKSPACE.load_cursor(tmp_path, "r2")
    assert cursor["seq"] == 1
    assert cursor["metadata"] == {"controller_rebuild": "through-observation-0"}

    cursor_path = tmp_path / "cursors" / "r2.json"
    corrupted = json.loads(cursor_path.read_text())
    corrupted["seq"] = 0
    WORKSPACE.atomic_json(cursor_path, corrupted)
    with pytest.raises(WORKSPACE.WorkspaceError, match="cursor content hash mismatch"):
        WORKSPACE.load_cursor(tmp_path, "r2")

    snapshot_path = tmp_path / "snapshots" / "latest.json"
    corrupted_snapshot = json.loads(snapshot_path.read_text())
    corrupted_snapshot["state"]["levels_completed"] = 9
    WORKSPACE.atomic_json(snapshot_path, corrupted_snapshot)
    with pytest.raises(WORKSPACE.WorkspaceError, match="snapshot content hash mismatch"):
        WORKSPACE.load_snapshot(tmp_path)
