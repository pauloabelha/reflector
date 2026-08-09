from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Iterator


HERE = Path(__file__).resolve().parent


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


WORKSPACE = load_module("parallel_workspace_qwen_tests", HERE / "workspace.py")
WORKER = load_module("parallel_qwen_worker_tests", HERE / "qwen_worker.py")


class FakeQwenHandler(BaseHTTPRequestHandler):
    requests: list[Any] = []
    lock = threading.Lock()

    def do_POST(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        length = int(self.headers.get("Content-Length", "0"))
        value = json.loads(self.rfile.read(length))
        with self.lock:
            self.requests.append(value)
        content = json.dumps(
            {
                "protocol": "r2-qwen-cw-write-v0",
                "schema_writes": [],
                "explanation_writes": [],
                "counterfactual_writes": [],
                "experiment_writes": [],
            },
            sort_keys=True,
        )
        body = json.dumps({"choices": [{"message": {"content": content}}]}, sort_keys=True)
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def log_message(self, _format: str, *args: object) -> None:
        return


@contextmanager
def fake_qwen() -> Iterator[tuple[str, list[Any]]]:
    FakeQwenHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), FakeQwenHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address
        yield f"http://{host}:{port}/v1/chat/completions", FakeQwenHandler.requests
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def start_workspace(root: Path, workspace_id: str) -> None:
    WORKSPACE.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="WorkspaceStarted",
        actor="coordinator",
        payload={"job_key": f"job:{workspace_id}"},
    )
    observation_blob = WORKSPACE.put_blob(root, {"grid": [[0, 0], [0, 0]]})
    WORKSPACE.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="ObservationCommitted",
        actor="environment",
        payload={
            "observation_version": 0,
            "observation_digest": "observation-0",
            "observation_blob": observation_blob,
            "legal_actions": [1, 2],
            "levels_completed": 0,
        },
    )


def queue_task(root: Path, workspace_id: str, task_id: str, request: dict[str, Any]) -> str:
    request_blob = WORKSPACE.put_blob(root, request)
    projection_blob = WORKSPACE.put_blob(root, {"observation_version": 0})
    WORKSPACE.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenTaskQueued",
        actor="environment",
        payload={
            "task_id": task_id,
            "basis_observation_version": 0,
            "basis_observation_digest": "observation-0",
            "request_blob": request_blob,
            "projection_blob": projection_blob,
        },
    )
    return request_blob


def wait_for_status(root: Path, task_id: str, status: str, timeout: float = 5.0) -> Any:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = WORKSPACE.reduce_workspace(root)
        task = next((item for item in state.tasks if item.task_id == task_id), None)
        if task is not None and task.status == status:
            return task
        time.sleep(0.01)
    state = WORKSPACE.reduce_workspace(root)
    raise AssertionError(f"task {task_id} did not reach {status}: {state.tasks}")


def stop_worker(worker: Any) -> None:
    worker.request_stop()
    worker.join(timeout=5)
    assert not worker.is_alive()
    worker.raise_if_failed()


def test_worker_claims_exact_request_records_content_addressed_reply_and_keeps_polling(
    tmp_path: Path,
) -> None:
    workspace_id = "worker-roundtrip"
    start_workspace(tmp_path, workspace_id)
    request = {
        "model": "fake-qwen",
        "messages": [{"role": "user", "content": "frozen request"}],
        "temperature": 0,
    }
    request_blob = queue_task(tmp_path, workspace_id, "task-0", request)

    with fake_qwen() as (endpoint, received):
        worker = WORKER.QwenWorker(
            tmp_path,
            endpoint,
            worker_epoch="epoch-roundtrip",
            poll_interval=0.01,
            request_timeout=2,
        )
        worker.start()
        replied = wait_for_status(tmp_path, "task-0", "replied")

        assert received == [request]
        assert replied.worker_epoch == "epoch-roundtrip"
        assert replied.response_blob is not None
        response = WORKSPACE.read_blob(tmp_path, replied.response_blob)
        assert response["protocol"] == WORKSPACE.PROTOCOL
        assert response["task_id"] == "task-0"
        assert response["worker_epoch"] == "epoch-roundtrip"
        assert response["request_blob"] == request_blob
        assert response["transport_error"] is None
        assert response["latency_s"] >= 0
        assert isinstance(response["raw_body"], str)
        assert isinstance(response["content"], str)
        assert response["parsed"]["protocol"] == "r2-qwen-cw-write-v0"

        events = WORKSPACE.list_events(tmp_path)
        lifecycle = [
            event["type"]
            for event in events
            if event["payload"].get("task_id") == "task-0"
        ]
        assert lifecycle == ["QwenTaskQueued", "QwenTaskClaimed", "QwenReplyRecorded"]

        # The thread remains a live queue consumer after recording the reply.
        assert worker.is_alive()
        stop_worker(worker)


def test_restart_abandons_orphaned_claim_without_post_or_silent_retry(tmp_path: Path) -> None:
    workspace_id = "worker-restart"
    start_workspace(tmp_path, workspace_id)
    queue_task(tmp_path, workspace_id, "task-orphan", {"request": "must-not-replay"})
    WORKSPACE.commit_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="QwenTaskClaimed",
        actor="qwen",
        payload={"task_id": "task-orphan", "worker_epoch": "dead-epoch"},
    )

    with fake_qwen() as (endpoint, received):
        restarted = WORKER.QwenWorker(
            tmp_path,
            endpoint,
            worker_epoch="restart-epoch",
            poll_interval=0.01,
            request_timeout=2,
        )
        restarted.start()
        orphan = wait_for_status(tmp_path, "task-orphan", "abandoned")

        assert orphan.worker_epoch == "dead-epoch"
        assert orphan.response_blob is None
        assert orphan.reason == "claimed-without-response-on-worker-start"
        assert received == []
        stop_worker(restarted)

        # A later canonical task is processed normally by a fresh epoch.
        replacement_request = {"request": "fresh-task"}
        queue_task(tmp_path, workspace_id, "task-fresh", replacement_request)
        fresh = WORKER.QwenWorker(
            tmp_path,
            endpoint,
            worker_epoch="fresh-epoch",
            poll_interval=0.01,
            request_timeout=2,
        )
        fresh.start()
        completed = wait_for_status(tmp_path, "task-fresh", "replied")

        assert completed.worker_epoch == "fresh-epoch"
        assert received == [replacement_request]
        stop_worker(fresh)
