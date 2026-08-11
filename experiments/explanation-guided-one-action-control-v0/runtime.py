"""Thread-safe live state and pacing gate used by the agent arcade."""

from __future__ import annotations

import threading
import time
import sys
from typing import Any, Mapping


# Configuration-aware prior: the measured local server needs about 5 s for
# this prompt and generates at 50 tokens/s. With the compact frame-0 contract,
# 640-token cap, and 192-token thinking budget, 14 s is the expected wait.
# It exists before this runtime has observed even one response of its own.
DEFAULT_QWEN_LATENCY_PRIOR_SECONDS = 14.0


def plain_frame(value: Any) -> list[list[int]]:
    """Normalize ndarray/list frame stacks to one JSON-safe 2-D grid."""

    while True:
        if hasattr(value, "tolist"):
            value = value.tolist()
            continue
        if not isinstance(value, list) or not value:
            break
        tail = value[-1]
        if hasattr(tail, "tolist"):
            value = tail.tolist()
            continue
        if isinstance(value[0], list) and value[0] and isinstance(value[0][0], list):
            value = tail
            continue
        break
    if not isinstance(value, list):
        return []
    return [[int(cell) for cell in row] for row in value]


class LiveRuntime:
    def __init__(self, *, qwen_latency_prior_seconds: float = DEFAULT_QWEN_LATENCY_PRIOR_SECONDS) -> None:
        self.condition = threading.Condition()
        self.paused = False
        self.step_tokens = 0
        self.delay_seconds = 1.0
        self.qwen_started_at: float | None = None
        self.qwen_durations: list[float] = []
        self.qwen_latency_prior_seconds = float(qwen_latency_prior_seconds)
        self.schema_observer: Any | None = None
        self.observation_envelope_builder: Any | None = None
        self.reset_requested = threading.Event()
        self.snapshot: dict[str, Any] = {
            "status": "idle", "frame": [], "observation_envelope": None,
            "turn": 0, "level_turn": 0,
            "decision": None, "settlement": None, "scratchpad": None,
            "r2_semantic_projection": None,
            "r2_1_schema_stats": None,
            "qwen": {
                "awaiting": False,
                "phase": "ready",
                "eta_seconds": round(self.qwen_latency_prior_seconds, 1),
                "remaining_seconds": round(self.qwen_latency_prior_seconds, 1),
                "eta_basis": "configuration-prior",
                "eta_samples": 0,
            },
        }

    def set_schema_observer(self, observer: Any) -> None:
        """Attach the R2.1 frame-local epistemic fitting layer."""
        self.schema_observer = observer

    def set_observation_envelope_builder(self, builder: Any) -> None:
        """Attach the lossless ordered-support normalizer used by this leaf."""
        self.observation_envelope_builder = builder

    def observation_surfaces(self, raw: Any) -> tuple[list[list[int]], dict[str, Any] | None]:
        if self.observation_envelope_builder is None:
            return plain_frame(raw.frame), None
        envelope = self.observation_envelope_builder(raw)
        frames = envelope["ordered_frames"]
        settled = int(envelope["settled_support_ordinal"])
        frame = [[int(cell) for cell in row] for row in frames[settled]]
        return frame, envelope

    def reset_schema_observer(self) -> None:
        """Clear all episode-local epistemic state before a new game starts."""
        reset = getattr(self.schema_observer, "reset_episode", None)
        if callable(reset):
            reset()

    def observe_schemas(self, frame: list[list[int]], turn: int) -> dict[str, Any] | None:
        if self.schema_observer is None or not frame:
            return None
        try:
            return self.schema_observer.fit_frame(frame, turn=turn)
        except Exception as error:
            # Epistemic telemetry must remain inspectable without masking the
            # underlying environment/controller failure mode.
            return {"engine": "R2.1", "turn": int(turn), "levels": [], "error": f"{type(error).__name__}: {error}"}

    def configure(self, *, paused: bool | None = None, speed: float | None = None, step: bool = False) -> dict[str, Any]:
        with self.condition:
            if paused is not None:
                self.paused = bool(paused)
            if speed is not None:
                if speed <= 0 or speed > 20:
                    raise ValueError("speed must be in (0, 20]")
                self.delay_seconds = 1.0 / float(speed)
            if step:
                self.paused = True
                self.step_tokens += 1
            self.condition.notify_all()
            return self.read()

    def read(self) -> dict[str, Any]:
        value = {**self.snapshot, "paused": self.paused, "speed": round(1.0 / self.delay_seconds, 3)}
        qwen = dict(value.get("qwen", {}))
        if qwen.get("awaiting") and self.qwen_started_at is not None:
            elapsed = max(0.0, time.monotonic() - self.qwen_started_at)
            eta = float(qwen.get("eta_seconds", 45.0))
            qwen.update({
                "elapsed_seconds": round(elapsed, 1),
                "remaining_seconds": round(max(0.0, eta - elapsed), 1),
                "progress_fraction": round(min(0.96, elapsed / max(1.0, eta)), 3),
            })
        value["qwen"] = qwen
        budget = value.get("level_action_budget", value.get("action_budget"))
        if isinstance(budget, int) and budget >= 0:
            value["actions_remaining"] = max(0, budget - int(value.get("level_turn", value.get("turn", 0))))
        return value

    def update(self, **values: Any) -> None:
        # Frame publication and R2.1 fitting are one atomic semantic event.
        # This includes frame 0 while Qwen is still forming its first
        # explanation; schema telemetry therefore never waits for an action.
        if "frame" in values and "r2_1_schema_stats" not in values:
            frame = plain_frame(values["frame"])
            values["frame"] = frame
            values["r2_1_schema_stats"] = self.observe_schemas(
                frame, int(values.get("turn", self.snapshot.get("turn", 0))),
            )
        with self.condition:
            if self.reset_requested.is_set():
                return
            self.snapshot.update(values)
            self.condition.notify_all()

    def record_r2_action_trace(self, trace: str) -> None:
        with self.condition:
            scratch = dict(self.snapshot.get("scratchpad") or {})
            traces = [*scratch.get("r2_action_traces", ()), str(trace)][-12:]
            self.snapshot["scratchpad"] = {**scratch, "r2_action_traces": traces}
            self.condition.notify_all()

    def set_qwen_scratchpad(self, note: Mapping[str, Any]) -> None:
        with self.condition:
            previous = dict(self.snapshot.get("scratchpad") or {})
            self.snapshot["scratchpad"] = {**dict(note), "r2_action_traces": previous.get("r2_action_traces", [])}
            self.condition.notify_all()

    def set_r2_semantic_projection(self, projection: Mapping[str, Any]) -> None:
        """Expose exactly the bounded R2 attention cut read by Semantic Qwen."""
        with self.condition:
            if self.reset_requested.is_set():
                return
            self.snapshot["r2_semantic_projection"] = dict(projection)
            self.condition.notify_all()

    def qwen_started(self, call_index: int, *, phase: str) -> None:
        with self.condition:
            if self.reset_requested.is_set():
                return
            self.qwen_started_at = time.monotonic()
            recent = self.qwen_durations[-3:]
            eta = sum(recent) / len(recent) if recent else self.qwen_latency_prior_seconds
            self.snapshot["qwen"] = {
                "awaiting": True,
                "phase": phase,
                "call_index": int(call_index),
                "eta_seconds": round(eta, 1),
                "elapsed_seconds": 0.0,
                "remaining_seconds": round(eta, 1),
                "progress_fraction": 0.0,
                "eta_basis": "observed" if recent else "configuration-prior",
                "eta_samples": len(self.qwen_durations),
            }
            self.condition.notify_all()

    def qwen_finished(self, *, accepted: bool, reason: str | None = None, learn_latency: bool = True) -> None:
        with self.condition:
            if self.reset_requested.is_set():
                return
            duration = 0.0 if self.qwen_started_at is None else max(0.0, time.monotonic() - self.qwen_started_at)
            if duration >= 1.0 and learn_latency:
                self.qwen_durations.append(duration)
            previous = dict(self.snapshot.get("qwen", {}))
            recent = self.qwen_durations[-3:]
            next_eta = sum(recent) / len(recent) if recent else self.qwen_latency_prior_seconds
            self.snapshot["qwen"] = {
                **previous,
                "awaiting": False,
                "phase": "written-to-workspace" if accepted else "response-rejected",
                "elapsed_seconds": round(duration, 1),
                "remaining_seconds": 0.0,
                "progress_fraction": 1.0,
                "reason": reason,
                "eta_samples": len(self.qwen_durations),
                "eta_seconds": round(next_eta, 1),
                "eta_basis": "observed" if recent else "configuration-prior",
            }
            self.qwen_started_at = None
            self.condition.notify_all()

    def request_reset(self) -> dict[str, Any]:
        """Cancel the current episode and atomically clear every live surface."""

        with self.condition:
            self.reset_requested.set()
            self.paused = False
            self.step_tokens = 0
            self.snapshot = {
                "status": "resetting",
                "frame": [],
                "observation_envelope": None,
                "turn": 0,
                "level_turn": 0,
                "decision": None,
                "settlement": None,
                "scratchpad": None,
                "r2_semantic_projection": None,
                "current_explanation": None,
                "salient_schemas": [],
                "metadata": None,
                "error": None,
                "r2_parallel_phase": None,
                "r2_1_schema_stats": None,
                "qwen": {
                    "awaiting": False,
                    "phase": "ready",
                    "eta_seconds": round(self.qwen_latency_prior_seconds, 1),
                    "remaining_seconds": round(self.qwen_latency_prior_seconds, 1),
                    "eta_basis": "configuration-prior",
                    "eta_samples": len(self.qwen_durations),
                },
            }
            self.condition.notify_all()
            return self.read()

    def finish_reset(self) -> None:
        with self.condition:
            if self.reset_requested.is_set():
                self.snapshot["status"] = "idle"
                self.reset_requested.clear()
                self.condition.notify_all()

    def before_action(self, environment: Any, controller: Any) -> None:
        if self.reset_requested.is_set():
            raise RuntimeError("arcade reset requested")
        raw = environment.observation_space
        frame, observation_envelope = self.observation_surfaces(raw)
        turn = int(self.snapshot.get("turn", 0))
        fast_path = bool(getattr(controller, "fast_path_active", False))
        schema_stats = (
            {**dict(self.snapshot.get("r2_1_schema_stats") or {}),
             "turn": turn, "cached": True, "fast_path": True, "elapsed_ms": 0.0}
            if fast_path else self.observe_schemas(frame, turn)
        )
        contract = None if controller.last_contract is None else dict(controller.last_contract)
        if contract is not None:
            current = contract.get("current_explanation")
            if (
                isinstance(self.snapshot.get("current_explanation"), Mapping)
                and isinstance(current, Mapping)
                and current.get("kind") == "winning-explanation-family"
            ):
                contract["current_explanation"] = dict(self.snapshot["current_explanation"])
            commit_prediction = getattr(self.schema_observer, "commit_prediction", None)
            if callable(commit_prediction):
                commit_prediction(
                    getattr(controller, "last_command", None)
                    or int(contract.get("selected_action", -1)),
                    contract.get("current_explanation"),
                )
        self.update(
            status="choosing",
            frame=frame,
            observation_envelope=observation_envelope,
            decision=contract,
            turn=turn,
            r2_1_schema_stats=schema_stats,
            fast_path=(controller.fast_path.document() if hasattr(controller, "fast_path") else None),
        )
        with self.condition:
            while self.paused and self.step_tokens == 0:
                self.condition.wait(timeout=1.0)
            if self.step_tokens:
                self.step_tokens -= 1
            delay = self.delay_seconds
        if self.reset_requested.wait(delay):
            raise RuntimeError("arcade reset requested")

    def after_action(self, successor: Any, controller: Any) -> None:
        if self.reset_requested.is_set():
            raise RuntimeError("arcade reset requested")
        raw = successor
        frame, observation_envelope = self.observation_surfaces(raw)
        turn = int(self.snapshot.get("turn", 0)) + 1
        previous_levels = int(self.snapshot.get("levels_completed", 0))
        levels_completed = int(raw.levels_completed)
        level_advanced = levels_completed > previous_levels
        if level_advanced:
            advance = getattr(self.schema_observer, "advance_level", None)
            if callable(advance):
                advance()
            scratchpad = sys.modules.get("one_action_scratchpad")
            advance_context = getattr(scratchpad, "advance_level_context", None)
            if callable(advance_context):
                advance_context()
        level_turn = 0 if level_advanced else int(self.snapshot.get("level_turn", 0)) + 1
        fast_path = bool(getattr(controller, "fast_path_active", False)) and not level_advanced
        schema_stats = (
            {**dict(self.snapshot.get("r2_1_schema_stats") or {}),
             "turn": turn, "cached": True, "fast_path": True, "elapsed_ms": 0.0}
            if fast_path else self.observe_schemas(frame, turn)
        )
        self.update(
            status="observing",
            frame=frame,
            observation_envelope=observation_envelope,
            turn=turn,
            level_turn=level_turn,
            r2_1_schema_stats=schema_stats,
            levels_completed=levels_completed,
            levels_total=int(raw.win_levels),
            level_transition=level_advanced,
            settlement=controller.settlements[-1] if controller.settlements else None,
            fast_path=(controller.fast_path.document() if hasattr(controller, "fast_path") else None),
        )

    def after_retry_reset(self, successor: Any, controller: Any) -> None:
        """Publish a same-level RESET without routing it through action learning."""
        if self.reset_requested.is_set():
            raise RuntimeError("arcade reset requested")
        frame, observation_envelope = self.observation_surfaces(successor)
        turn = int(self.snapshot.get("turn", 0)) + 1
        retry = getattr(self.schema_observer, "retry_level", None)
        if callable(retry):
            retry()
        scratchpad = sys.modules.get("one_action_scratchpad")
        retry_context = getattr(scratchpad, "retry_level_context", None)
        if callable(retry_context):
            retry_context()
        schema_stats = self.observe_schemas(frame, turn)
        self.update(
            status="observing",
            frame=frame,
            observation_envelope=observation_envelope,
            turn=turn,
            level_turn=int(self.snapshot.get("level_turn", 0)) + 1,
            r2_1_schema_stats=schema_stats,
            levels_completed=int(successor.levels_completed),
            levels_total=int(successor.win_levels),
            level_transition=False,
            retry_boundary=True,
            settlement=controller.settlements[-1] if controller.settlements else None,
            fast_path=(controller.fast_path.document() if hasattr(controller, "fast_path") else None),
        )

    def rebuild_retry_boundary(self, settlement: Mapping[str, Any]) -> None:
        """Apply retry scoping while reconstructing cognition from the ledger."""
        retry = getattr(self.schema_observer, "retry_level", None)
        if callable(retry):
            retry()
        scratchpad = sys.modules.get("one_action_scratchpad")
        retry_context = getattr(scratchpad, "retry_level_context", None)
        if callable(retry_context):
            retry_context()
        self.update(settlement=dict(settlement), retry_boundary=True)


LIVE_RUNTIME: LiveRuntime | None = None


def install_action_hook(base: Any, runtime: LiveRuntime) -> None:
    global LIVE_RUNTIME
    LIVE_RUNTIME = runtime
    if getattr(base, "_one_action_runtime_installed", False):
        return
    base._one_action_runtime_installed = True
    original_execute = base.execute_action

    def execute(environment: Any, game: str, action_id: int, data: Mapping[str, Any] | None = None, reasoning: Any = None) -> Any:
        controller = getattr(base, "_one_action_active_controller", None)
        live = controller is not None and not any(
            marker in str(reasoning).lower()
            for marker in ("replay", "counterfactual", "game-over-retry-reset")
        )
        if live:
            runtime.before_action(environment, controller)
        successor = original_execute(environment, game, action_id, data or {}, reasoning)
        if live:
            runtime.after_action(successor, controller)
        return successor

    base.execute_action = execute
