"""Persistent Qwen consumer for the event-sourced cognitive workspace.

The worker owns no queue state outside the canonical workspace ledger.  A
request is claimed before its content-addressed request blob is read, and every
attempt records exactly one content-addressed response document, including
transport and parsing failures.  A claim left by an earlier worker epoch is
abandoned on startup and is never silently replayed.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
WORKSPACE_SPEC = importlib.util.spec_from_file_location(
    "parallel_cognitive_workspace_worker_api", HERE / "workspace.py"
)
if WORKSPACE_SPEC is None or WORKSPACE_SPEC.loader is None:
    raise RuntimeError("cannot load workspace API")
WORKSPACE = importlib.util.module_from_spec(WORKSPACE_SPEC)
sys.modules[WORKSPACE_SPEC.name] = WORKSPACE
WORKSPACE_SPEC.loader.exec_module(WORKSPACE)


def new_worker_epoch() -> str:
    return f"qwen-{uuid.uuid4().hex}"


def _error_text(error: BaseException) -> str:
    return f"{type(error).__name__}: {error}"


def post_request(endpoint: str, request_value: Any, timeout: float) -> dict[str, Any]:
    """POST one exact canonical request value and retain the unmodified reply text."""

    started = time.perf_counter()
    raw_body: str | None = None
    content: str | None = None
    parsed: Any = None
    transport_error: str | None = None
    try:
        encoded = WORKSPACE.stable_json(request_value).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw_body = response.read().decode("utf-8")
        envelope = json.loads(raw_body)
        candidate = envelope["choices"][0]["message"]["content"]
        if not isinstance(candidate, str):
            raise TypeError("response content is not a string")
        content = candidate
        parsed = json.loads(content)
    except urllib.error.HTTPError as error:
        try:
            raw_body = error.read().decode("utf-8")
        except Exception:
            pass
        transport_error = _error_text(error)
    except Exception as error:
        transport_error = _error_text(error)
    return {
        "raw_body": raw_body,
        "content": content,
        "parsed": parsed,
        "latency_s": time.perf_counter() - started,
        "transport_error": transport_error,
    }


class QwenWorker(threading.Thread):
    """One persistent event-driven worker for a single workspace root."""

    def __init__(
        self,
        root: Path,
        endpoint: str,
        *,
        worker_epoch: str | None = None,
        poll_interval: float = 0.1,
        request_timeout: float = 600.0,
    ) -> None:
        super().__init__(name="parallel-cognitive-qwen", daemon=False)
        self.root = Path(root)
        self.endpoint = str(endpoint)
        self.worker_epoch = worker_epoch or new_worker_epoch()
        self.poll_interval = float(poll_interval)
        self.request_timeout = float(request_timeout)
        self._stop_requested = threading.Event()
        self.failure: BaseException | None = None

    def request_stop(self) -> None:
        self._stop_requested.set()

    def raise_if_failed(self) -> None:
        if self.failure is not None:
            raise RuntimeError("Qwen worker failed") from self.failure

    def _state(self) -> Any:
        return WORKSPACE.reduce_workspace(self.root)

    def abandon_startup_orphans(self) -> int:
        """Terminally abandon every claim visible at this worker epoch's start."""

        state = self._state()
        if state.workspace_id is None:
            return 0
        abandoned = 0
        for task in state.tasks:
            if task.status != "claimed":
                continue
            WORKSPACE.commit_event(
                self.root,
                workspace_id=state.workspace_id,
                event_type="QwenTaskAbandoned",
                actor="qwen",
                payload={
                    "task_id": task.task_id,
                    "reason": "claimed-without-response-on-worker-start",
                },
                basis={
                    "abandoning_worker_epoch": self.worker_epoch,
                    "orphaned_worker_epoch": task.worker_epoch,
                },
                event_id=f"qwen-abandon:{state.workspace_id}:{task.task_id}:{self.worker_epoch}",
            )
            abandoned += 1
            state = self._state()
        return abandoned

    def _claim_next(self) -> tuple[str, str, str] | None:
        """Claim the canonical first queued task or return when no task is ready."""

        state = self._state()
        if state.workspace_id is None or state.stopped:
            return None
        queued = next((task for task in state.tasks if task.status == "queued"), None)
        if queued is None:
            return None
        try:
            WORKSPACE.commit_event(
                self.root,
                workspace_id=state.workspace_id,
                event_type="QwenTaskClaimed",
                actor="qwen",
                payload={"task_id": queued.task_id, "worker_epoch": self.worker_epoch},
                basis={
                    "basis_observation_version": queued.basis_version,
                    "basis_observation_digest": queued.basis_digest,
                    "request_blob": queued.request_blob,
                },
                event_id=f"qwen-claim:{state.workspace_id}:{queued.task_id}:{self.worker_epoch}",
            )
        except WORKSPACE.WorkspaceError:
            refreshed = self._state()
            current = next((task for task in refreshed.tasks if task.task_id == queued.task_id), None)
            if current is None or current.status != "queued":
                return None
            raise
        return state.workspace_id, queued.task_id, queued.request_blob

    def process_one(self) -> bool:
        """Claim and finish one task.  Returns false when the queue is empty."""

        claimed = self._claim_next()
        if claimed is None:
            return False
        workspace_id, task_id, request_blob = claimed
        try:
            request_value = WORKSPACE.read_blob(self.root, request_blob)
            result = post_request(self.endpoint, request_value, self.request_timeout)
        except Exception as error:
            result = {
                "raw_body": None,
                "content": None,
                "parsed": None,
                "latency_s": 0.0,
                "transport_error": _error_text(error),
            }
        response_document = {
            "protocol": WORKSPACE.PROTOCOL,
            "task_id": task_id,
            "worker_epoch": self.worker_epoch,
            "request_blob": request_blob,
            **result,
        }
        response_blob = WORKSPACE.put_blob(self.root, response_document)
        WORKSPACE.commit_event(
            self.root,
            workspace_id=workspace_id,
            event_type="QwenReplyRecorded",
            actor="qwen",
            payload={
                "task_id": task_id,
                "worker_epoch": self.worker_epoch,
                "response_blob": response_blob,
            },
            basis={"request_blob": request_blob},
            event_id=f"qwen-reply:{workspace_id}:{task_id}:{self.worker_epoch}:{response_blob}",
        )
        return True

    def run(self) -> None:
        try:
            self.abandon_startup_orphans()
            while not self._stop_requested.is_set():
                state = self._state()
                if state.stopped:
                    break
                if not self.process_one():
                    self._stop_requested.wait(self.poll_interval)
        except BaseException as error:
            self.failure = error
            self._stop_requested.set()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--endpoint", required=True)
    parser.add_argument("--worker-epoch")
    parser.add_argument("--poll-interval", type=float, default=0.1)
    parser.add_argument("--request-timeout", type=float, default=600.0)
    args = parser.parse_args(argv)

    worker = QwenWorker(
        args.workspace_root,
        args.endpoint,
        worker_epoch=args.worker_epoch,
        poll_interval=args.poll_interval,
        request_timeout=args.request_timeout,
    )

    def stop_worker(_signum: int, _frame: Any) -> None:
        worker.request_stop()

    signal.signal(signal.SIGINT, stop_worker)
    signal.signal(signal.SIGTERM, stop_worker)
    worker.start()
    worker.join()
    worker.raise_if_failed()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
