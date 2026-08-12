"""Provider-neutral structured-model proposal boundary for planning."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Callable, Mapping, Protocol, runtime_checkable


MODEL_PROPOSAL_PROTOCOL = "control-factorization-model-proposal-v0"
StructuredInvoker = Callable[[Mapping[str, Any]], Mapping[str, Any]]


class PlanningModelError(RuntimeError):
    """A model proposal was unavailable or violated its data contract."""


@dataclass(frozen=True, slots=True)
class ModelProposal:
    command_ids: tuple[str, ...]
    milestone_shadow_id: str | None


@runtime_checkable
class PlanningModel(Protocol):
    name: str

    def propose(self, problem: Mapping[str, Any]) -> ModelProposal:
        """Propose command identities; the planner must validate every edge."""


def _request(
    problem: Mapping[str, Any], *, max_tokens: int, reasoning_effort: str | None,
) -> dict[str, Any]:
    schema = {
        "type": "object",
        "properties": {
            "command_ids": {
                "type": "array", "items": {"type": "string"},
            },
            "milestone_shadow_id": {"type": ["string", "null"]},
        },
        "required": ["command_ids", "milestone_shadow_id"],
        "additionalProperties": False,
    }
    request = {
        "messages": [
            {
                "role": "system",
                "content": (
                    "Propose a bounded command-id composition using only the supplied "
                    "supported effects. Prospective states are not evidence. Return JSON only."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(problem, sort_keys=True, separators=(",", ":")),
            },
        ],
        "max_tokens": max(1, int(max_tokens)),
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "control_factorization_proposal",
                "strict": True,
                "schema": schema,
            },
        },
    }
    if reasoning_effort:
        request["reasoning_effort"] = str(reasoning_effort)
    return request


def _invoke(
    invoker: StructuredInvoker,
    problem: Mapping[str, Any],
    *,
    max_tokens: int,
    reasoning_effort: str | None,
) -> ModelProposal:
    try:
        value = invoker(_request(
            problem, max_tokens=max_tokens, reasoning_effort=reasoning_effort,
        ))
    except PlanningModelError:
        raise
    except Exception as error:
        raise PlanningModelError(f"model invocation failed: {type(error).__name__}") from error
    if not isinstance(value, Mapping):
        raise PlanningModelError("model proposal must be an object")
    command_ids = value.get("command_ids")
    milestone = value.get("milestone_shadow_id")
    if (
        not isinstance(command_ids, list)
        or any(not isinstance(item, str) or not item for item in command_ids)
        or (milestone is not None and not isinstance(milestone, str))
    ):
        raise PlanningModelError("model proposal does not match the required schema")
    return ModelProposal(tuple(command_ids), milestone)


@dataclass(frozen=True, slots=True)
class QwenPlanningModel:
    """Qwen identity adapter over any provider-neutral structured invoker."""

    invoker: StructuredInvoker
    model_name: str = "qwen"
    max_tokens: int = 512
    reasoning_effort: str | None = None

    @property
    def name(self) -> str:
        return f"qwen:{self.model_name}"

    def propose(self, problem: Mapping[str, Any]) -> ModelProposal:
        return _invoke(
            self.invoker, problem, max_tokens=self.max_tokens,
            reasoning_effort=self.reasoning_effort,
        )


@dataclass(frozen=True, slots=True)
class LunaPlanningModel:
    """Luna identity adapter over any provider-neutral structured invoker."""

    invoker: StructuredInvoker
    model_name: str = "gpt-5.6-luna"
    max_tokens: int = 512
    reasoning_effort: str | None = "medium"

    @property
    def name(self) -> str:
        return f"luna:{self.model_name}"

    def propose(self, problem: Mapping[str, Any]) -> ModelProposal:
        return _invoke(
            self.invoker, problem, max_tokens=self.max_tokens,
            reasoning_effort=self.reasoning_effort,
        )
