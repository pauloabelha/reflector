"""Logically isolated QwenExecutor over the shared physical FIFO server."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import time
from typing import Any, Mapping, Sequence

import analysis_sandbox
import protocol


@dataclass(frozen=True, slots=True)
class ExecutorCallResult:
    proposal: protocol.ExecutorProposal
    request_id: str
    computation_id: str
    proposal_event_id: str
    qwen_calls: int
    input_tokens: int
    output_tokens: int
    qwen_latency_s: float
    python_calls: int
    python_runtime_s: float
    failure_stages: tuple[str, ...]


def _usage(response: Mapping[str, Any]) -> tuple[int, int]:
    try:
        envelope = json.loads(response.get("raw_body") or "{}")
        usage = envelope.get("usage", {})
        return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
    except (TypeError, ValueError, json.JSONDecodeError):
        return 0, 0


class QwenExecutorWorker:
    """One stateless transport context with its own durable cursor/provenance."""

    worker_id = protocol.WORKER_ID

    def __init__(
        self, *, ledger: Any, fifo: Any, workspace_root: Any, workspace_id: str,
        arm: str, model_config: Mapping[str, Any], python_config: Mapping[str, Any],
    ) -> None:
        self.ledger = ledger
        self.fifo = fifo
        self.workspace_root = workspace_root
        self.workspace_id = str(workspace_id)
        self.arm = str(arm)
        self.model_config = dict(model_config)
        self.python_config = dict(python_config)
        self.tool_available = self.arm == "arm-c"

    def _call(self, request_id: str, stage: str, payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        request_blob = self.ledger.put_blob(self.workspace_root, payload)
        call_id = "executor-call:" + protocol.stable_hash({"request_id": request_id, "stage": stage, "request_blob": request_blob})
        future = self.fifo.submit(f"{self.workspace_id}:{self.worker_id}", payload)
        queued = self.ledger.append_event(
            self.workspace_root, workspace_id=self.workspace_id,
            event_type="ExecutorWorkerCallQueued", actor="qwen_executor",
            payload={
                "call_id": call_id, "request_id": request_id, "stage": stage,
                "request_blob": request_blob, "worker_context": self.worker_id,
                "physical_queue": "shared-qwen-global-fifo",
            },
            event_id=f"executor-call-queued:{call_id}",
        )
        started = time.perf_counter()
        queue_result = future.result(timeout=float(self.model_config.get("request_timeout_seconds", 180)) + 30)
        response = dict(queue_result.response)
        response_blob = self.ledger.put_blob(self.workspace_root, response)
        self.ledger.append_event(
            self.workspace_root, workspace_id=self.workspace_id,
            event_type="ExecutorWorkerCallCompleted", actor="qwen_executor",
            payload={
                "call_id": call_id, "request_id": request_id, "stage": stage,
                "queued_event_id": queued["event_id"], "response_blob": response_blob,
                "queue_sequence": int(queue_result.sequence),
                "latency_s": float(response.get("latency_s") or time.perf_counter() - started),
                "transport_error": response.get("transport_error"),
            },
            event_id=f"executor-call-completed:{call_id}:{response_blob}",
        )
        if response.get("transport_error") or not isinstance(response.get("parsed"), Mapping):
            detail = str(response.get("raw_body") or "invalid JSON")[:2000]
            raise RuntimeError(
                f"Executor {stage} request failed: "
                f"{response.get('transport_error') or 'invalid JSON'}; {detail}"
            )
        return response, dict(response["parsed"])

    def deliberate(self, snapshot: Mapping[str, Any], trigger_reasons: Sequence[str]) -> ExecutorCallResult:
        request_id = "executor-request:" + protocol.stable_hash({
            "workspace": self.workspace_id,
            "arm": self.arm,
            "snapshot_hash": snapshot["snapshot_hash"],
            "basis_seq": snapshot["decision_boundary"]["ledger_basis_seq"],
        })
        snapshot_blob = self.ledger.put_blob(self.workspace_root, snapshot)
        visible_snapshot = protocol.model_snapshot(snapshot)
        request_event = self.ledger.append_event(
            self.workspace_root, workspace_id=self.workspace_id,
            event_type="ExecutorRequest", actor="coordinator",
            payload={
                "request_id": request_id, "arm": self.arm,
                "worker_context": self.worker_id, "snapshot_blob": snapshot_blob,
                "snapshot_hash": snapshot["snapshot_hash"],
                "workspace_dependency_ids": sorted(
                    value for alias, value in snapshot["dependency_aliases"].items()
                    if alias.startswith("o")
                ),
                "trigger_reasons": list(trigger_reasons),
                "tool_available": self.tool_available,
                "semantic_private_state_visible": False,
                "successor_available": False,
            },
            event_id=f"executor-request:{request_id}",
        )

        failures: list[str] = []
        input_tokens = output_tokens = 0
        qwen_latency = 0.0
        stage1_payload = protocol.request_payload(
            model_config=self.model_config, snapshot=visible_snapshot, stage="analysis",
            tool_available=self.tool_available,
        )
        response1, analysis = self._call(request_id, "analysis", stage1_payload)
        prompt, completion = _usage(response1)
        input_tokens += prompt
        output_tokens += completion
        qwen_latency += float(response1.get("latency_s") or 0.0)

        raw_code = analysis.get("code")
        code = "\n".join(str(line) for line in raw_code) if isinstance(raw_code, list) else raw_code
        python_result: dict[str, Any] | None = None
        python_calls = 0
        python_runtime = 0.0
        missing_operation = str(analysis.get("missing_operation") or "").strip()
        if missing_operation:
            failures.append("SNAPSHOT_OR_TOOLING_INSUFFICIENT")
        if self.tool_available and analysis.get("mode") == "python" and isinstance(code, str) and code.strip():
            python_calls = 1
            try:
                python_result = analysis_sandbox.run_analysis(code, visible_snapshot, self.python_config)
                python_runtime = float(python_result.get("execution_time_s", 0.0))
                if python_result.get("status") == "timeout":
                    failures.append("PYTHON_TIMEOUT")
                elif python_result.get("status") != "ok":
                    failures.append("PYTHON_RUNTIME_FAILURE")
                    if "NameError" in str(python_result.get("stderr", "")):
                        failures.append("SNAPSHOT_OR_TOOLING_INSUFFICIENT")
            except analysis_sandbox.SandboxError as error:
                python_result = {"status": "generation-failure", "stderr": str(error), "stdout": "", "return_value": None, "execution_time_s": 0.0}
                failures.append("PYTHON_GENERATION_FAILED")
        elif self.tool_available:
            failures.append("NO_PROCEDURAL_COMPUTATION")
        elif analysis.get("mode") == "python":
            failures.append("NO_PROCEDURAL_COMPUTATION")

        computation = {
            "request_id": request_id,
            "worker_call_id": request_event["event_id"],
            "workspace_dependency_ids": list(analysis.get("dependencies", ())),
            "input_snapshot_hash": snapshot["snapshot_hash"],
            "mode": analysis.get("mode"),
            "findings": list(analysis.get("findings", ())),
            "generated_code": code,
            "code_hash": None if not isinstance(code, str) else protocol.stable_hash(code),
            "stdout": None if python_result is None else python_result.get("stdout"),
            "stderr": None if python_result is None else python_result.get("stderr"),
            "structured_return_value": None if python_result is None else python_result.get("return_value"),
            "python_status": None if python_result is None else python_result.get("status"),
            "python_execution_time_s": python_runtime,
            "missing_operation": missing_operation or None,
        }
        computation_blob = self.ledger.put_blob(self.workspace_root, computation)
        computation_id = "executor-computation:" + protocol.stable_hash(computation)
        self.ledger.append_event(
            self.workspace_root, workspace_id=self.workspace_id,
            event_type="ExecutorComputation", actor="qwen_executor",
            payload={
                "computation_id": computation_id, "request_id": request_id,
                "computation_blob": computation_blob, "snapshot_hash": snapshot["snapshot_hash"],
                "code_hash": computation["code_hash"], "python_status": computation["python_status"],
            }, event_id=f"executor-computation:{computation_id}",
        )

        stage2_payload = protocol.request_payload(
            model_config=self.model_config, snapshot=visible_snapshot, stage="proposal",
            intermediate=computation, tool_available=self.tool_available,
        )
        response2, proposal_value = self._call(request_id, "proposal", stage2_payload)
        proposal_value = protocol.normalize_response_keys(proposal_value)
        prompt, completion = _usage(response2)
        input_tokens += prompt
        output_tokens += completion
        qwen_latency += float(response2.get("latency_s") or 0.0)
        try:
            proposal = protocol.validate_proposal(
                proposal_value, request_id=request_id, snapshot=snapshot
            )
        except (KeyError, TypeError, ValueError, protocol.ProtocolError) as error:
            rejected = {
                "request_id": request_id,
                "snapshot_hash": snapshot["snapshot_hash"],
                "reason": f"{type(error).__name__}: {error}",
                "normalized_proposal": proposal_value,
            }
            rejected_blob = self.ledger.put_blob(self.workspace_root, rejected)
            self.ledger.append_event(
                self.workspace_root, workspace_id=self.workspace_id,
                event_type="ExecutorProposal", actor="qwen_executor",
                payload={
                    "request_id": request_id, "proposal_blob": rejected_blob,
                    "computation_id": computation_id,
                    "snapshot_hash": snapshot["snapshot_hash"],
                    "selected_action": None, "abstained": False,
                    "rejected": True, "rejection_reason": rejected["reason"],
                },
                event_id=f"executor-proposal-rejected:{request_id}:{rejected_blob}",
            )
            raise protocol.ProtocolError("PROPOSAL_UNGROUNDABLE") from error
        if proposal.selected_action is None:
            failures.append("EXECUTOR_ABSTAINED")
        proposal_blob = self.ledger.put_blob(self.workspace_root, protocol.proposal_document(proposal))
        proposal_event = self.ledger.append_event(
            self.workspace_root, workspace_id=self.workspace_id,
            event_type="ExecutorProposal", actor="qwen_executor",
            payload={
                "request_id": request_id, "proposal_blob": proposal_blob,
                "computation_id": computation_id, "snapshot_hash": snapshot["snapshot_hash"],
                "selected_action": proposal.selected_action,
                "abstained": proposal.selected_action is None,
            }, event_id=f"executor-proposal:{request_id}:{proposal_blob}",
        )
        latest = self.ledger.list_events(self.workspace_root)[-1]
        # v1.16's generic helper intentionally admits only its original four
        # cursors. The new logical worker owns a fifth file under the same
        # durable cursor directory without widening or reusing `qwen.json`.
        self.ledger.atomic_json(
            self.workspace_root / "cursors" / f"{self.worker_id}.json",
            {
                "protocol": protocol.PROTOCOL,
                "worker": self.worker_id,
                "ledger_seq": int(latest["seq"]),
                "graph_revision": int(snapshot["decision_boundary"]["graph_basis_revision"]),
                "metadata": {
                    "request_id": request_id,
                    "snapshot_hash": snapshot["snapshot_hash"],
                    "semantic_cursor_shared": False,
                },
            },
        )
        return ExecutorCallResult(
            proposal=proposal, request_id=request_id, computation_id=computation_id,
            proposal_event_id=str(proposal_event["event_id"]), qwen_calls=2,
            input_tokens=input_tokens, output_tokens=output_tokens,
            qwen_latency_s=qwen_latency, python_calls=python_calls,
            python_runtime_s=python_runtime, failure_stages=tuple(failures),
        )
