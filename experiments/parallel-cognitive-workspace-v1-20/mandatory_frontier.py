"""Keep optional attention bounded while preserving mandatory epistemic truth."""

from __future__ import annotations

from dataclasses import asdict
from functools import wraps
import json
from typing import Any, Callable


class MandatoryFrontierCeilingError(RuntimeError):
    """The exact mandatory unit exceeds the frozen safe transport ceiling."""


def _retry_exact_required(
    function: Callable[..., Any],
    error_type: type[BaseException],
    *,
    budget_key: str,
    ceiling: int,
) -> Callable[..., Any]:
    @wraps(function)
    def wrapped(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except error_type as error:
            required = int(getattr(error, "required"))
            requested = int(kwargs[budget_key])
            if required <= requested:
                raise
            if required > ceiling:
                raise MandatoryFrontierCeilingError(
                    f"mandatory frontier {required} exceeds frozen ceiling {ceiling}"
                ) from error
            retry = dict(kwargs)
            retry[budget_key] = required
            result = function(*args, **retry)
            used = getattr(result, "used_tokens", None)
            if isinstance(result, dict):
                used = result.get("used_tokens", used)
            if used is not None and int(used) > required:
                raise MandatoryFrontierCeilingError(
                    "mandatory retry admitted material beyond the exact required unit"
                )
            return result

    wrapped.__mandatory_frontier_ceiling__ = ceiling  # type: ignore[attr-defined]
    return wrapped


def install(graph: Any, cognition: Any, *, ceiling: int) -> None:
    """Install the policy at both R2 and Qwen frontier construction seams."""

    if ceiling < 1:
        raise ValueError("mandatory frontier ceiling must be positive")
    if getattr(graph.frontier, "__mandatory_frontier_ceiling__", None) != ceiling:
        graph.frontier = _retry_exact_required(
            graph.frontier,
            graph.FrontierBudgetError,
            budget_key="budget",
            ceiling=ceiling,
        )
    if getattr(cognition.build_turn, "__mandatory_frontier_ceiling__", None) != ceiling:
        cognition.build_turn = _retry_exact_required(
            cognition.build_turn,
            graph.FrontierBudgetError,
            budget_key="token_budget",
            ceiling=ceiling,
        )


def install_exact_context_admission(
    cognition: Any,
    qwen: dict[str, Any],
    *,
    safety_margin_tokens: int,
) -> None:
    """Use the serving stack's exact multimodal count before real inference."""

    current = cognition.ResidentServerQueue
    if getattr(current, "__exact_context_admission__", None) == safety_margin_tokens:
        return
    original = current
    base_poster = cognition.V0_WORKER.post_request
    effective_window = int(qwen["context_window_tokens"]) - int(safety_margin_tokens)
    if effective_window < 1:
        raise ValueError("context safety margin consumes the complete window")

    def admitted_poster(endpoint: str, request: Any, timeout: float) -> dict[str, Any]:
        probe = {**dict(request), "max_tokens": 1}
        counted = base_poster(endpoint, probe, timeout)
        raw = counted.get("raw_body")
        if not isinstance(raw, str):
            raise cognition.CognitionError("exact context admission returned no body")
        try:
            envelope = json.loads(raw)
            prompt_tokens = int(envelope["usage"]["prompt_tokens"])
        except Exception as error:
            raise cognition.CognitionError(
                "exact context admission returned no serving-stack prompt count"
            ) from error
        report = cognition.admit_request_context(
            request,
            {**qwen, "context_window_tokens": effective_window},
            prompt_token_counter=lambda _request: prompt_tokens,
        )
        response = dict(base_poster(endpoint, request, timeout))
        response["context_admission"] = {
            **asdict(report),
            "physical_context_window_tokens": int(qwen["context_window_tokens"]),
            "safety_margin_tokens": int(safety_margin_tokens),
            "counted_request_hash": cognition.stable_hash(probe),
            "posted_request_hash": cognition.stable_hash(request),
            "only_difference_from_posted_request": "max_tokens=1",
            "semantic_output_discarded": True,
        }
        return response

    def queue_factory(endpoint: str, *, timeout: float = 600.0, poster=None):
        if poster is not None:
            raise cognition.CognitionError(
                "custom transport poster is incompatible with exact admission"
            )
        return original(endpoint, timeout=timeout, poster=admitted_poster)

    queue_factory.__exact_context_admission__ = safety_margin_tokens  # type: ignore[attr-defined]
    cognition.ResidentServerQueue = queue_factory
