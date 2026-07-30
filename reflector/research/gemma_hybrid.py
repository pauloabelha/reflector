"""Research-only symbolic perception plus local Gemma action arbitration.

This module is intentionally outside the Kaggle inference overlay.  It exists
to test whether a small inference-time language model adds useful online rule
induction beyond the accepted purely symbolic agent.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections import Counter, deque
from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True, order=True, slots=True)
class HybridAction:
    action_id: int
    x: int = -1
    y: int = -1
    label: str = ""

    @property
    def data(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y} if self.action_id == 6 else {}


@dataclass(slots=True)
class _ActionOutcome:
    action: HybridAction
    before_digest: str
    after_digest: str | None = None
    state: str = "NOT_FINISHED"
    levels_before: int = 0
    levels_after: int | None = None
    hypothesis: str = ""

    def compact(self) -> dict[str, Any]:
        return {
            "action": self.action.label,
            "changed": (
                None
                if self.after_digest is None
                else self.before_digest != self.after_digest
            ),
            "state": self.state,
            "level_delta": (
                None
                if self.levels_after is None
                else self.levels_after - self.levels_before
            ),
            "hypothesis": self.hypothesis[:120],
        }


class GemmaHybridBrain:
    """Bounded online Gemma policy over symbolic, grounded action candidates."""

    def __init__(
        self,
        endpoint: str,
        *,
        model: str = "google_gemma-4-E2B-it-Q4_K_M.gguf",
        timeout: float = 60.0,
        max_history: int = 32,
        max_clicks: int = 24,
    ) -> None:
        self.endpoint = endpoint.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_history = max_history
        self.max_clicks = max_clicks
        self.history: list[_ActionOutcome] = []
        self.pending: _ActionOutcome | None = None
        self.previous_frame: tuple[tuple[int, ...], ...] | None = None
        self.requests = 0
        self.valid_responses = 0
        self.fallbacks = 0
        self.action_counts: Counter[int] = Counter()
        self.last_event: dict[str, Any] = {}

    def choose(
        self,
        *,
        frame: tuple[tuple[int, ...], ...],
        available_actions: Iterable[int],
        state: str,
        levels_completed: int,
    ) -> HybridAction:
        digest = self._digest(frame)
        self._settle_pending(digest, state, levels_completed)
        candidates = self._candidates(frame, available_actions)
        summary = self._summary(frame)
        difference = self._difference(self.previous_frame, frame)
        prompt = self._prompt(
            candidates=candidates,
            summary=summary,
            difference=difference,
            state=state,
            levels_completed=levels_completed,
        )
        raw_response = ""
        hypothesis = ""
        selected: HybridAction | None = None
        error: str | None = None
        try:
            raw_response = self._query(prompt)
            choice, hypothesis = self.parse_response(raw_response)
            if 0 <= choice < len(candidates):
                selected = candidates[choice]
                self.valid_responses += 1
            else:
                error = f"candidate-out-of-range:{choice}"
        except (OSError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            error = f"{type(exc).__name__}:{exc}"
        if selected is None:
            selected = min(
                candidates,
                key=lambda item: (
                    self.action_counts[item.action_id],
                    item,
                ),
            )
            hypothesis = f"deterministic fallback after {error}"
            self.fallbacks += 1
        self.requests += 1
        self.action_counts[selected.action_id] += 1
        self.pending = _ActionOutcome(
            action=selected,
            before_digest=digest,
            levels_before=levels_completed,
            hypothesis=hypothesis,
        )
        self.previous_frame = frame
        self.last_event = {
            "format": "reflector-gemma-hybrid-event-v1",
            "request": self.requests,
            "model": self.model,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "state_summary": summary,
            "difference": difference,
            "candidates": [
                {
                    "index": index,
                    "action_id": candidate.action_id,
                    "data": candidate.data,
                    "label": candidate.label,
                }
                for index, candidate in enumerate(candidates)
            ],
            "raw_response": raw_response[:1000],
            "selected": {
                "action_id": selected.action_id,
                "data": selected.data,
                "label": selected.label,
            },
            "hypothesis": hypothesis[:500],
            "fallback_error": error,
        }
        return selected

    def observe_terminal(
        self,
        *,
        frame: tuple[tuple[int, ...], ...],
        state: str,
        levels_completed: int,
    ) -> None:
        self._settle_pending(self._digest(frame), state, levels_completed)
        self.previous_frame = frame

    def metrics(self) -> dict[str, Any]:
        return {
            "requests": self.requests,
            "valid_responses": self.valid_responses,
            "fallbacks": self.fallbacks,
            "action_counts": dict(sorted(self.action_counts.items())),
            "retained_history": len(self.history),
        }

    def _settle_pending(
        self, digest: str, state: str, levels_completed: int
    ) -> None:
        if self.pending is None:
            return
        self.pending.after_digest = digest
        self.pending.state = state
        self.pending.levels_after = levels_completed
        self.history.append(self.pending)
        if len(self.history) > self.max_history:
            del self.history[: len(self.history) - self.max_history]
        self.pending = None

    def _prompt(
        self,
        *,
        candidates: tuple[HybridAction, ...],
        summary: dict[str, Any],
        difference: dict[str, Any],
        state: str,
        levels_completed: int,
    ) -> str:
        payload = {
            "objective": (
                "Infer the unknown game's causal rules online and complete "
                "levels efficiently. Action meanings are unknown."
            ),
            "constraints": [
                "Choose exactly one grounded legal candidate index.",
                "Use action/outcome evidence; do not assume arrow meanings.",
                "Distinguish autonomous animation from effects of your action.",
                "Preserve useful hidden commitments across visually similar states.",
                "Prefer a falsifiable experiment unless an evidenced plan exists.",
                "Avoid repeating a no-effect action in the same apparent state.",
            ],
            "state": state,
            "levels_completed": levels_completed,
            "scene": summary,
            "change_since_previous_decision": difference,
            "recent_action_outcomes": [
                item.compact() for item in self.history[-self.max_history :]
            ],
            "candidates": [
                {"index": index, "label": item.label}
                for index, item in enumerate(candidates)
            ],
            "response_schema": {
                "candidate": "integer candidate index",
                "hypothesis": "brief causal reason and expected observation",
            },
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def _query(self, prompt: str) -> str:
        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are the online causal controller inside an "
                            "ARC-AGI-3 agent. Return one JSON object only."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
                "max_tokens": 96,
                "chat_template_kwargs": {"enable_thinking": False},
            }
        ).encode()
        request = urllib.request.Request(
            f"{self.endpoint}/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read())
        content = payload["choices"][0]["message"]["content"]
        if not isinstance(content, str):
            raise ValueError("Gemma response content is not text")
        return content

    @staticmethod
    def parse_response(value: str) -> tuple[int, str]:
        start = value.find("{")
        end = value.rfind("}")
        if start < 0 or end < start:
            raise ValueError("Gemma response has no JSON object")
        payload = json.loads(value[start : end + 1])
        choice = payload.get("candidate")
        hypothesis = payload.get("hypothesis")
        if type(choice) is not int:
            raise ValueError("Gemma candidate must be an integer")
        if not isinstance(hypothesis, str) or not hypothesis.strip():
            raise ValueError("Gemma hypothesis must be non-empty")
        return choice, hypothesis.strip()

    def _candidates(
        self,
        frame: tuple[tuple[int, ...], ...],
        available_actions: Iterable[int],
    ) -> tuple[HybridAction, ...]:
        legal = tuple(sorted(set(int(value) for value in available_actions)))
        output = [
            HybridAction(action, label=f"ACTION{action}")
            for action in legal
            if 1 <= action <= 5
        ]
        if 6 in legal:
            for component in self._components(frame)[: self.max_clicks]:
                output.append(
                    HybridAction(
                        6,
                        x=component["centroid"][0],
                        y=component["centroid"][1],
                        label=(
                            "CLICK "
                            f"color={component['color']} "
                            f"area={component['area']} "
                            f"bbox={component['bbox']} "
                            f"at={component['centroid']}"
                        ),
                    )
                )
        if not output:
            raise ValueError("active state exposes no grounded legal candidates")
        return tuple(output)

    @classmethod
    def _summary(
        cls, frame: tuple[tuple[int, ...], ...]
    ) -> dict[str, Any]:
        if not frame:
            return {"size": [0, 0], "components": []}
        components = cls._components(frame)
        return {
            "size": [len(frame[0]), len(frame)],
            "component_count": len(components),
            "components": components[:32],
        }

    @staticmethod
    def _components(
        frame: tuple[tuple[int, ...], ...],
    ) -> list[dict[str, Any]]:
        height = len(frame)
        width = len(frame[0]) if height else 0
        seen: set[tuple[int, int]] = set()
        components: list[dict[str, Any]] = []
        for y0 in range(height):
            for x0 in range(width):
                if (y0, x0) in seen:
                    continue
                color = frame[y0][x0]
                region = {(y0, x0)}
                seen.add((y0, x0))
                queue = deque(((y0, x0),))
                while queue:
                    y, x = queue.popleft()
                    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        ny, nx = y + dy, x + dx
                        if (
                            0 <= ny < height
                            and 0 <= nx < width
                            and (ny, nx) not in seen
                            and frame[ny][nx] == color
                        ):
                            seen.add((ny, nx))
                            region.add((ny, nx))
                            queue.append((ny, nx))
                area = len(region)
                if area * 2 > max(1, width * height):
                    continue
                ys = [point[0] for point in region]
                xs = [point[1] for point in region]
                cx = round(sum(xs) / area)
                cy = round(sum(ys) / area)
                components.append(
                    {
                        "color": color,
                        "area": area,
                        "bbox": [min(xs), min(ys), max(xs), max(ys)],
                        "centroid": [cx, cy],
                        "edge": (
                            min(xs) == 0
                            or min(ys) == 0
                            or max(xs) == width - 1
                            or max(ys) == height - 1
                        ),
                    }
                )
        components.sort(
            key=lambda item: (
                item["edge"],
                -item["area"],
                item["color"],
                item["bbox"],
            )
        )
        return components

    @staticmethod
    def _difference(
        before: tuple[tuple[int, ...], ...] | None,
        after: tuple[tuple[int, ...], ...],
    ) -> dict[str, Any]:
        if before is None or len(before) != len(after):
            return {"available": False}
        changed = [
            (x, y)
            for y, row in enumerate(after)
            for x, value in enumerate(row)
            if y >= len(before)
            or x >= len(before[y])
            or before[y][x] != value
        ]
        if not changed:
            return {"available": True, "changed_cells": 0}
        xs = [point[0] for point in changed]
        ys = [point[1] for point in changed]
        return {
            "available": True,
            "changed_cells": len(changed),
            "changed_bbox": [min(xs), min(ys), max(xs), max(ys)],
        }

    @staticmethod
    def _digest(frame: tuple[tuple[int, ...], ...]) -> str:
        raw = bytes(value & 0xFF for row in frame for value in row)
        return hashlib.sha256(raw).hexdigest()[:16]
