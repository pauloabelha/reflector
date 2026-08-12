"""R2 transport wiring for controller-agnostic planner backends."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
from typing import Any, Callable, Mapping

from reflector2.planner import (
    LunaPlanningModel,
    ModelPlanner,
    PlannerBackend,
    PlanningModelError,
    QwenPlanningModel,
    backend_from_name,
)
from reflector2.r2 import model_backend


Poster = Callable[[str, Any, float], Mapping[str, Any]]
Runner = Callable[..., subprocess.CompletedProcess[str]]


def browser_options(planner_config: Mapping[str, Any]) -> dict[str, Any]:
    """Return the small, server-owned planner surface exposed by Arcade."""

    active = str(
        planner_config.get("backend") or "bounded-best-first-v0"
    ).strip().lower()
    return {
        "active": active,
        "choices": [
            {
                "id": "prospect-planner-v0",
                "label": "Goal prospect (R2.3)",
                "selection": {"backend": "prospect-planner-v0"},
            },
            {
                "id": "bounded-best-first-v0",
                "label": "Deterministic search (default)",
                "selection": {"backend": "bounded-best-first-v0"},
            },
            {
                "id": "fallback-only-v0",
                "label": "Original one-step R2",
                "selection": {"backend": "fallback-only-v0"},
            },
            {
                "id": "model-selected",
                "label": "Model-validated (selected model)",
                "selection": {"backend": "model-selected"},
            },
        ],
    }


def resolve_browser_selection(
    planner_config: Mapping[str, Any],
    selection: Mapping[str, Any],
    serving_model_config: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate one Arcade planner choice and return its effective config."""

    if not isinstance(selection, Mapping) or set(selection) != {"backend"}:
        raise ValueError("planner selection must contain only backend")
    selected = str(selection.get("backend") or "").strip().lower()
    if selected not in {
        "prospect-planner-v0", "bounded-best-first-v0",
        "fallback-only-v0", "model-selected",
    }:
        raise ValueError(f"unknown planner selection: {selected!r}")
    if selected == "model-selected":
        provider = str(serving_model_config.get("provider") or "").strip().lower()
        selected = "model-luna" if provider == "openai" else "model-qwen"
    return {**dict(planner_config), "enabled": True, "backend": selected}


@dataclass(slots=True)
class StructuredPosterInvoker:
    """Normalize R2's existing provider-neutral poster to a model callable."""

    config: Mapping[str, Any]
    poster: Poster | None = None
    _post: Poster = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._post = self.poster or model_backend.build_poster(self.config)

    def __call__(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        result = self._post(
            str(self.config["endpoint"]), request,
            float(self.config.get("request_timeout_seconds", 600)),
        )
        error = result.get("transport_error")
        if error:
            raise PlanningModelError(str(error))
        parsed = result.get("parsed")
        if not isinstance(parsed, Mapping):
            raise PlanningModelError("planner model returned no structured object")
        return parsed


@dataclass(frozen=True, slots=True)
class QwenCliInvoker:
    """Process transport for a local Qwen GGUF when no HTTP server is active."""

    executable: Path
    model: Path
    context_size: int = 8192
    threads: int = 16
    timeout_seconds: int = 180
    grammar_constrained: bool = False
    runner: Runner = field(default=subprocess.run, repr=False, compare=False)

    @staticmethod
    def _structured_object(text: str) -> Mapping[str, Any]:
        decoder = json.JSONDecoder()
        matches = []
        for offset, character in enumerate(text):
            if character != "{":
                continue
            try:
                value, _end = decoder.raw_decode(text[offset:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, Mapping) and "command_ids" in value:
                matches.append(value)
        if not matches:
            raise PlanningModelError("Qwen CLI returned no structured planner object")
        return matches[-1]

    @staticmethod
    def _grammar(messages: list[Any]) -> str:
        problem = None
        for item in reversed(messages):
            if not isinstance(item, Mapping) or item.get("role") != "user":
                continue
            try:
                candidate = json.loads(str(item.get("content") or ""))
            except json.JSONDecodeError:
                continue
            if isinstance(candidate, Mapping):
                problem = candidate
                break
        if problem is None:
            raise PlanningModelError("Qwen CLI could not recover the planner problem")
        command_ids = sorted({
            str(item.get("command_id"))
            for item in problem.get("supported_effects", ())
            if isinstance(item, Mapping) and item.get("command_id")
        })
        milestone_ids = sorted({
            str(item.get("shadow_id"))
            for item in problem.get("milestone_shadows", ())
            if isinstance(item, Mapping) and item.get("shadow_id")
        })
        if not command_ids:
            raise PlanningModelError("Qwen CLI planner problem has no supported commands")

        def literal(value: str) -> str:
            return json.dumps(value)

        command = " | ".join(literal(json.dumps(item)) for item in command_ids)
        milestone = " | ".join(
            [literal("null"), *(literal(json.dumps(item)) for item in milestone_ids)]
        )
        return "\n".join((
            'root ::= "{" ws "\\\"command_ids\\\"" ws ":" ws "[" ws command-list? "]" ws "," ws "\\\"milestone_shadow_id\\\"" ws ":" ws milestone ws "}"',
            'command-list ::= command (ws "," ws command)*',
            f"command ::= {command}",
            f"milestone ::= {milestone}",
            'ws ::= [ \\t\\n]*',
        ))

    def __call__(self, request: Mapping[str, Any]) -> Mapping[str, Any]:
        if not self.executable.is_file() or not self.model.is_file():
            raise PlanningModelError("Qwen CLI executable or model is missing")
        messages = request.get("messages")
        if not isinstance(messages, list):
            raise PlanningModelError("Qwen CLI request has no messages")
        prompt = "\n\n".join(
            f"{item.get('role', 'user').upper()}: {item.get('content', '')}"
            for item in messages if isinstance(item, Mapping)
        )
        prompt += (
            "\n\nReturn only the JSON object required by this schema: "
            + json.dumps(request.get("response_format", {}), sort_keys=True)
        )
        command = [
            str(self.executable), "-m", str(self.model),
            "-c", str(max(512, int(self.context_size))),
            "-n", str(max(32, int(request.get("max_tokens", 512)))),
            "-t", str(max(1, int(self.threads))),
            "--no-warmup", "--no-display-prompt", "--simple-io", "--single-turn",
            "--reasoning-budget", "0", "--temp", "0", "-p", prompt,
        ]
        if self.grammar_constrained:
            command.extend(("--grammar", self._grammar(messages)))
        try:
            completed = self.runner(
                command, text=True, capture_output=True,
                timeout=max(1, int(self.timeout_seconds)), check=False,
            )
        except Exception as error:
            raise PlanningModelError(
                f"Qwen CLI invocation failed: {type(error).__name__}"
            ) from error
        if completed.returncode != 0:
            raise PlanningModelError(
                f"Qwen CLI exited with status {completed.returncode}"
            )
        return self._structured_object(completed.stdout)


def build_planner_backend(
    planner_config: Mapping[str, Any],
    serving_model_config: Mapping[str, Any],
    *,
    poster: Poster | None = None,
) -> PlannerBackend:
    """Build deterministic, fallback, Qwen, or Luna planner from configuration."""

    selected = str(
        planner_config.get("backend") or "bounded-best-first-v0"
    ).strip().lower()
    if selected not in {"model", "model-qwen", "model-luna"}:
        return backend_from_name(selected)
    adapter = str(planner_config.get("model_adapter") or "").strip().lower()
    if selected == "model-qwen":
        adapter = "qwen"
    elif selected == "model-luna":
        adapter = "luna"
    if adapter not in {"qwen", "luna"}:
        raise ValueError("model planner requires model_adapter 'qwen' or 'luna'")
    transport = str(planner_config.get("model_transport") or "http").strip().lower()
    if adapter == "qwen" and transport == "cli":
        invoker = QwenCliInvoker(
            executable=Path(str(planner_config.get("qwen_cli_executable") or "")),
            model=Path(str(planner_config.get("qwen_cli_model") or "")),
            context_size=int(planner_config.get("model_context_tokens", 8192)),
            threads=int(planner_config.get("model_threads", 16)),
            timeout_seconds=int(planner_config.get("model_timeout_seconds", 180)),
        )
    elif transport == "http":
        invoker = StructuredPosterInvoker(serving_model_config, poster=poster)
    else:
        raise ValueError(f"unsupported planner model transport: {transport!r}")
    common = {
        "invoker": invoker,
        "model_name": str(serving_model_config.get("model") or adapter),
        "max_tokens": int(planner_config.get("model_max_tokens", 512)),
        "reasoning_effort": planner_config.get(
            "model_reasoning_effort", serving_model_config.get("reasoning_effort"),
        ),
    }
    model = QwenPlanningModel(**common) if adapter == "qwen" else LunaPlanningModel(**common)
    return ModelPlanner(model)
