"""Matched verbal/Python Executor calls for one immutable decision boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import time
from typing import Any, Mapping, Sequence

import causal_protocol as cp


SYSTEM_PROMPT = """You are Reflector's sole motor-policy worker in this arm.

Free internal computation is cheap; real actions are precious. Think over the
live grounded explanations before spending one action. Use actions to make
progress or cheaply falsify control-relevant explanations. Raw disagreement is
not enough: prefer disagreement that can change later control. Hard risk is a
gate. Preserve option value and avoid redundant tests.

Semantic Qwen invents explanations. R2 grounds them and supplies predictions,
contradictions, evidence, and constraints. Neither selects the next action.
You alone may rank and propose concrete legal actions, but the arbiter alone
commits one. Existing PCW predictions are evidence-bearing inputs, not a policy
score to rerank.

Use only the supplied immutable state. Opaque actions, colors, and objects have
no assumed meaning. Generated reasoning or code is computation, never empirical
support. Every candidate must cite dependencies and make a one-step executable
prediction. Any mismatch invalidates its procedural assumptions."""


class ExecutorFailure(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MatchedExecutorResult:
    arm: str
    request_id: str
    analysis: Mapping[str, Any]
    computation: Mapping[str, Any]
    proposal: Mapping[str, Any] | None
    treatment: cp.TreatmentResult
    qwen_calls: int
    prompt_tokens: int
    completion_tokens: int
    qwen_latency_s: float
    python_calls: int
    python_runtime_s: float


def _usage(response: Mapping[str, Any]) -> tuple[int, int]:
    try:
        envelope = json.loads(response.get("raw_body") or "{}")
        usage = envelope.get("usage", {})
        return int(usage.get("prompt_tokens", 0)), int(usage.get("completion_tokens", 0))
    except (TypeError, ValueError, json.JSONDecodeError):
        return 0, 0


def visible_dependencies(snapshot: Mapping[str, Any]) -> tuple[str, ...]:
    graph = snapshot["epistemic_graph"]
    refs = {str(snapshot["current_observation"]["reference"])}
    refs.update(str(item["transition_id"]) for item in snapshot["full_relevant_transition_history"])
    refs.update(str(item["id"]) for item in graph.get("objects", ()))
    refs.update(str(row[0]) for row in graph.get("binding_catalog", {}).get("rows", ()))
    refs.update(str(row[0]) for row in graph.get("schema_catalog", {}).get("rows", ()))
    return tuple(sorted(refs))


def _nullable(inner: Mapping[str, Any]) -> dict[str, Any]:
    return {"anyOf": [dict(inner), {"type": "null"}]}


def _reference_schema() -> dict[str, Any]:
    """Keep grammar small; exact membership is checked against the snapshot."""

    return {"type": "string", "minLength": 1, "maxLength": 96}


def analysis_schema(*, arm: str, dependencies: Sequence[str]) -> dict[str, Any]:
    python = arm == "arm-c"
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["mode", "dependencies", "findings", "code", "missing_operation"],
        "properties": {
            "mode": {"type": "string", "enum": ["python" if python else "verbal"]},
            "dependencies": {
                "type": "array", "items": _reference_schema(),
                "minItems": 1, "maxItems": 8,
            },
            "findings": {
                "type": "array", "items": {"type": "string", "maxLength": 180},
                "minItems": 1, "maxItems": 4,
            },
            "code": (
                {
                    "type": "string", "minLength": 1, "maxLength": 800,
                }
                if python else {"type": "null"}
            ),
            "missing_operation": _nullable({"type": "string", "maxLength": 160}),
        },
    }


def proposal_schema(
    *, legal_actions: Sequence[int], dependencies: Sequence[str], computation_id: str,
    finding_count: int,
) -> dict[str, Any]:
    action = {"type": "integer", "enum": sorted({int(item) for item in legal_actions})}
    dependency = _reference_schema()
    checkpoint = {
        "type": "object", "additionalProperties": False,
        "required": [
            "grid_changed", "changed_cell_count_min", "changed_cell_count_max",
            "level_delta", "terminal_expected", "confidence_milli",
        ],
        "properties": {
            "grid_changed": {"type": "boolean"},
            "changed_cell_count_min": {"type": "integer", "minimum": 0, "maximum": 4096},
            "changed_cell_count_max": {"type": "integer", "minimum": 0, "maximum": 4096},
            "level_delta": {"type": "integer", "minimum": -1, "maximum": 1},
            "terminal_expected": {"type": "boolean"},
            "confidence_milli": {"type": "integer", "minimum": 0, "maximum": 1000},
        },
    }
    candidate = {
        "type": "object", "additionalProperties": False,
        "required": [
            "action_id", "dependencies", "computation_dependencies", "finding_refs",
            "computed_reason", "value_case", "expected_checkpoint", "invalidate_on",
        ],
        "properties": {
            "action_id": action,
            "dependencies": {"type": "array", "items": dependency, "minItems": 1, "maxItems": 8},
            "computation_dependencies": {
                "type": "array", "items": {"type": "string", "enum": [computation_id]},
                "minItems": 1, "maxItems": 1,
            },
            "finding_refs": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": [f"finding:{i}" for i in range(int(finding_count))],
                },
                "minItems": 1, "maxItems": max(1, int(finding_count)),
            },
            "computed_reason": {"type": "string", "minLength": 1, "maxLength": 240},
            "value_case": {
                "type": "object", "additionalProperties": False,
                "required": ["progress", "discrimination", "option_value", "risk", "redundancy"],
                "properties": {
                    "progress": {"type": "string", "enum": ["positive", "neutral", "negative", "unknown"]},
                    "discrimination": {"type": "string", "enum": ["high", "medium", "low"]},
                    "option_value": {"type": "string", "enum": ["preserves", "reduces", "unknown"]},
                    "risk": {"type": "string", "enum": ["high", "medium", "low", "unknown"]},
                    "redundancy": {"type": "string", "enum": ["high", "medium", "low"]},
                },
            },
            "expected_checkpoint": checkpoint,
            "invalidate_on": {
                "type": "array", "minItems": 1, "maxItems": 4,
                "items": {"type": "string", "enum": [
                    "CHECKPOINT_MISMATCH", "UNEXPECTED_TERMINAL", "HARD_CONTRADICTION",
                    "DEPENDENCY_INVALIDATED", "REPRESENTATION_INADEQUATE",
                ]},
            },
        },
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": [
            "candidate_actions", "decision", "missing_operation", "abstention_dependencies",
        ],
        "properties": {
            "candidate_actions": {"type": "array", "items": candidate, "minItems": 1, "maxItems": 2},
            "decision": {
                "anyOf": [
                    {
                        "type": "object", "additionalProperties": False,
                        "required": ["kind", "action_id"],
                        "properties": {"kind": {"type": "string", "enum": ["select"]}, "action_id": action},
                    },
                    {
                        "type": "object", "additionalProperties": False,
                        "required": ["kind", "reason"],
                        "properties": {
                            "kind": {"type": "string", "enum": ["abstain"]},
                            "reason": {"type": "string", "enum": [
                                "SNAPSHOT_OR_TOOLING_INSUFFICIENT", "HARD_RISK_BLOCKED",
                                "NO_DISCRIMINATING_ACTION", "NO_LEGAL_ACTION",
                            ]},
                        },
                    },
                ]
            },
            "missing_operation": _nullable({"type": "string", "maxLength": 160}),
            "abstention_dependencies": {"type": "array", "items": dependency, "maxItems": 8},
        },
    }


def checkpoint_document(value: Mapping[str, Any]) -> dict[str, Any]:
    minimum = int(value["changed_cell_count_min"])
    maximum = int(value["changed_cell_count_max"])
    if minimum > maximum:
        raise cp.CausalProtocolError("CHECKPOINT_COUNT_RANGE_REVERSED")
    return {
        "confidence": int(value["confidence_milli"]) / 1000.0,
        "predicates": [
            {"observable": "grid_changed", "operator": "eq", "value": bool(value["grid_changed"])},
            {"observable": "changed_cell_count", "operator": "ge", "value": minimum},
            {"observable": "changed_cell_count", "operator": "le", "value": maximum},
            {"observable": "level_delta", "operator": "eq", "value": int(value["level_delta"])},
            {
                "observable": "terminal",
                "operator": "eq",
                "value": bool(value["terminal_expected"]),
            },
        ],
    }


class MatchedExecutor:
    def __init__(
        self, *, fifo: Any, sandbox: Any, model_config: Mapping[str, Any],
        python_config: Mapping[str, Any], artifact_writer: Any,
    ) -> None:
        self.fifo = fifo
        self.sandbox = sandbox
        self.model_config = dict(model_config)
        self.python_config = dict(python_config)
        self.artifact_writer = artifact_writer

    def _payload(self, *, task: str, content: Mapping[str, Any], schema: Mapping[str, Any], name: str, max_tokens: int) -> dict[str, Any]:
        return {
            "model": self.model_config["model"],
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": cp.stable_json({"task": task, **dict(content)})},
            ],
            "temperature": self.model_config.get("temperature", 0),
            "top_p": self.model_config.get("top_p", 1),
            "seed": self.model_config.get("seed", 0),
            "max_tokens": int(max_tokens),
            "thinking_budget_tokens": int(self.model_config.get("thinking_budget_tokens", 1024)),
            "stream": False,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "strict": True, "schema": dict(schema)},
            },
        }

    def _call(self, *, context: str, stage: str, payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        self.artifact_writer(f"{stage}-request.json", payload)
        started = time.perf_counter()
        result = self.fifo.submit(context, dict(payload)).result(
            timeout=float(self.model_config.get("request_timeout_seconds", 180)) + 30
        )
        response = dict(result.response)
        response["measured_latency_s"] = time.perf_counter() - started
        self.artifact_writer(f"{stage}-response.json", response)
        if response.get("transport_error") or not isinstance(response.get("parsed"), Mapping):
            raise ExecutorFailure(
                f"{stage} failed: {response.get('transport_error') or 'invalid structured response'}"
            )
        return response, dict(response["parsed"])

    def deliberate(
        self, *, arm: str, full_snapshot: Mapping[str, Any], model_snapshot: Mapping[str, Any],
    ) -> MatchedExecutorResult:
        if arm not in {"arm-b", "arm-c"}:
            raise ValueError("matched Executor supports B/C only")
        dependencies = visible_dependencies(model_snapshot)
        legal = [int(item["action_id"]) for item in model_snapshot["legal_opaque_actions"]]
        request_id = f"request:{arm}:" + cp.stable_hash({
            "arm": arm, "snapshot_hash": full_snapshot["snapshot_hash"],
            "model_view_hash": cp.stable_hash(model_snapshot),
        })
        context = f"precious-action:{arm}:qwen-executor"
        python = arm == "arm-c"
        analysis_task = (
            "Analyze the explanation beam and all legal actions without selecting one. "
            "For each useful finding, identify a history pattern, counterexample, geometry fact, "
            "or control-relevant disagreement. Every dependencies item MUST be copied exactly "
            "from valid_dependency_ids; do not name fields, tools, or concepts as dependencies. "
            + (
                "You MUST use Python. Return one short Python program in code. "
                "The sandbox exposes the full immutable snapshot, safe builtins, and only the frozen generic primitives. "
                "Available signature: query_transitions(action_id=None,event_id=None). "
                "Use it to compute action/effect counts or counterexamples; do not merely echo constants. "
                "Do not write comments, functions, print calls, or prose strings. The last line must assign a JSON-safe result. "
                "A valid pattern is: rows=query_transitions(); acts=[1,2,3]; "
                "counts={a:len(query_transitions(action_id=a)) for a in acts}; "
                "result={'total':len(rows),'counts':counts}. Adapt it to the supplied legal actions."
                if python else
                "Reason verbally from the compact snapshot. Set code=null."
            )
        )
        stage1 = self._payload(
            task=analysis_task,
            content={
                "arm": arm,
                "available_tool": "run_analysis(code)" if python else None,
                "tool_rule": "generic operations only; computation is not empirical support",
                "missing_operation_rule": "null unless a missing generic primitive actually prevents analysis",
                "valid_dependency_ids": list(dependencies),
                "snapshot": model_snapshot,
            },
            schema=analysis_schema(arm=arm, dependencies=dependencies),
            name=f"precious_action_analysis_{arm[-1]}",
            max_tokens=int(self.model_config["max_tokens_stage_1"]),
        )
        response1, analysis = self._call(context=context, stage="analysis", payload=stage1)
        prompt_tokens, completion_tokens = _usage(response1)
        latency = float(response1.get("latency_s") or response1.get("measured_latency_s", 0.0))
        available = set(dependencies)
        analysis_dependencies = {str(item) for item in analysis.get("dependencies", ())}
        if not analysis_dependencies <= available:
            raise cp.CausalProtocolError("ANALYSIS_DEPENDENCY_NOT_VISIBLE")
        cp.validate_history_dependencies(
            analysis["dependencies"],
            transition_ids=[
                str(item["transition_id"])
                for item in model_snapshot["full_relevant_transition_history"]
            ],
        )
        raw_code = analysis.get("code")
        code = str(raw_code) if isinstance(raw_code, str) else None
        python_result = None
        python_calls = 0
        python_runtime = 0.0
        if python:
            if not code:
                computation = {
                    "mode": analysis.get("mode"), "generated_code": code,
                    "python_status": None, "code_hash": None,
                    "structured_return_value": None, "computation_id": "",
                }
                treatment = cp.TreatmentResult(False, "PYTHON_EXECUTOR", ("EMPTY_CODE",))
                return MatchedExecutorResult(
                    arm, request_id, analysis, computation, None, treatment, 1,
                    prompt_tokens, completion_tokens, latency, 0, 0.0,
                )
            python_calls = 1
            try:
                python_result = self.sandbox.run_analysis(code, full_snapshot, self.python_config)
            except Exception as error:
                python_result = {
                    "status": "generation-failure", "stdout": "", "stderr": f"{type(error).__name__}: {error}",
                    "return_value": None, "execution_time_s": 0.0,
                }
            python_runtime = float(python_result.get("execution_time_s", 0.0))
        findings = list(analysis.get("findings", ()))
        if python_result is not None and str(python_result.get("status")) == "ok":
            encoded_result = cp.stable_json(python_result.get("return_value"))
            findings = [
                "python_result=" + (
                    encoded_result if len(encoded_result) <= 1200
                    else encoded_result[:1100] + ":sha256=" + cp.stable_hash(encoded_result)
                )
            ]
        computation_body = {
            "arm": arm,
            "request_id": request_id,
            "input_snapshot_hash": full_snapshot["snapshot_hash"],
            "mode": analysis.get("mode"),
            "workspace_dependency_ids": list(analysis.get("dependencies", ())),
            "findings": findings,
            "generated_code": code,
            "code_hash": None if code is None else cp.stable_hash(code),
            "python_status": None if python_result is None else python_result.get("status"),
            "stdout": None if python_result is None else python_result.get("stdout"),
            "stderr": None if python_result is None else python_result.get("stderr"),
            "structured_return_value": None if python_result is None else python_result.get("return_value"),
            "python_execution_time_s": python_runtime,
            "missing_operation": analysis.get("missing_operation"),
        }
        computation_id = "computation:" + cp.stable_hash(computation_body)
        computation = {**computation_body, "computation_id": computation_id}
        self.artifact_writer("computation.json", computation)

        if python and str(computation["python_status"]) != "ok":
            treatment = cp.TreatmentResult(False, "PYTHON_EXECUTOR", ("PYTHON_NOT_SUCCESSFUL",))
            return MatchedExecutorResult(
                arm, request_id, analysis, computation, None, treatment, 1,
                prompt_tokens, completion_tokens, latency, python_calls, python_runtime,
            )

        proposal_task = (
            "Rank up to two legal primitive actions using progress, decision-relevant explanation discrimination, "
            "option value, hard risk, and redundancy. Select exactly one unless a typed abstention is genuinely forced. "
            "Cite the intermediate computation and findings. Predict the immediate successor with a changed-cell range, "
            "level delta, terminal expectation, and calibrated confidence. Every dependencies or abstention_dependencies "
            "item MUST be copied exactly from valid_dependency_ids. Use computation_id only in computation_dependencies. "
            "Every finding_refs item MUST be copied exactly from valid_finding_refs. Emit no prose outside the schema."
        )
        valid_finding_refs = [f"finding:{i}" for i in range(len(computation["findings"]))]
        stage2 = self._payload(
            task=proposal_task,
            content={
                "arm": arm,
                "snapshot": model_snapshot,
                "intermediate_computation": {
                    "computation_id": computation_id,
                    "mode": computation["mode"],
                    "workspace_dependency_ids": computation["workspace_dependency_ids"],
                    "findings": computation["findings"],
                    "python_status": computation["python_status"],
                    "structured_return_value": computation["structured_return_value"],
                    "missing_operation": computation["missing_operation"],
                },
                "valid_dependency_ids": list(dependencies),
                "valid_finding_refs": valid_finding_refs,
            },
            schema=proposal_schema(
                legal_actions=legal, dependencies=dependencies, computation_id=computation_id,
                finding_count=len(computation["findings"]),
            ),
            name=f"precious_action_proposal_{arm[-1]}",
            max_tokens=int(self.model_config["max_tokens_stage_2"]),
        )
        response2, proposal = self._call(context=context, stage="proposal", payload=stage2)
        prompt, completion = _usage(response2)
        prompt_tokens += prompt
        completion_tokens += completion
        latency += float(response2.get("latency_s") or response2.get("measured_latency_s", 0.0))
        cp.validate_decision_coherence(proposal, legal_actions=legal)
        if not set(proposal.get("abstention_dependencies", ())) <= available:
            raise cp.CausalProtocolError("ABSTENTION_DEPENDENCY_NOT_VISIBLE")
        findings = {f"finding:{i}" for i in range(len(computation["findings"]))}
        for candidate in proposal["candidate_actions"]:
            if not set(candidate["dependencies"]) <= available:
                raise cp.CausalProtocolError("CANDIDATE_DEPENDENCY_NOT_VISIBLE")
            if candidate["computation_dependencies"] != [computation_id]:
                raise cp.CausalProtocolError("CANDIDATE_COMPUTATION_PROVENANCE_INVALID")
            if not set(candidate["finding_refs"]) <= findings:
                raise cp.CausalProtocolError("CANDIDATE_FINDING_PROVENANCE_INVALID")
            checkpoint_document(candidate["expected_checkpoint"])
        treatment = cp.assess_treatment(arm=arm, computation=computation, proposal=proposal)
        self.artifact_writer("proposal.json", proposal)
        self.artifact_writer("treatment.json", asdict(treatment))
        return MatchedExecutorResult(
            arm, request_id, analysis, computation, proposal, treatment, 2,
            prompt_tokens, completion_tokens, latency, python_calls, python_runtime,
        )
