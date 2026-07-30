"""Recording-derived audits for action-conditioned structural events.

This module is development-only.  It turns immutable official recordings into
machine-readable evidence before a policy mutation is proposed.  In
particular, it prevents a visual interpretation of a montage from silently
becoming the premise of an offspring.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

from ..core.inheritance import SchemeDefinition
from ..core.perception import SceneTracker
from ..core.symbolic import Event, Observation, Scene

_IGNORED_EVENTS = frozenset(
    {
        "frame_changed",
        "level_advanced",
        "novel_state_reached",
        "state_changed",
    }
)


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class EventDefinition:
    """Immutable content-free event recognizer proposed for inheritance."""

    name: str
    preconditions: tuple[str, ...]
    event: tuple[str, ...]
    invariants: tuple[str, ...]
    falsifiers: tuple[str, ...]
    minimum_support: int
    complexity_cost: int

    @property
    def event_id(self) -> str:
        return _digest(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["event_id"] = self.event_id
        return value


ACTION_EFFECT_CONTEXT_CHANGE = EventDefinition(
    name="action-effect-context-change",
    preconditions=(
        "same-level",
        "same-action-role",
        "stable-prior-structural-effect",
    ),
    event=("observed-effect-differs-from-supported-effect",),
    invariants=("no-game-identifier", "no-absolute-coordinate", "no-color"),
    falsifiers=(
        "insufficient-prior-support",
        "level-boundary",
        "only-rendering-metadata-changed",
    ),
    minimum_support=2,
    complexity_cost=4,
)


STABLE_REPEATED_FORM_ACTION_EFFECT = SchemeDefinition(
    name="stable-repeated-form-action-effect",
    operator="observe-event",
    parameters=(
        "action-role",
        "repeated-form-subject",
        "supported-effect",
    ),
    grounding=("action-family", "object"),
    preconditions=(
        "same-action-role",
        "same-level",
        "stable-prior-structural-effect",
    ),
    effects=("prior-structural-effect-repeats",),
    invariants=(
        "no-absolute-coordinate",
        "no-fixed-color",
        "no-game-identifier",
    ),
    falsifiers=("supported-effect-deviates",),
    resource_cap=1,
    complexity_cost=4,
)


@dataclass(frozen=True, slots=True)
class EventOccurrence:
    event_id: str
    step: int
    level: int
    action_id: int
    subject_digest: str
    group_arity: int
    prior_support: int
    expected_effect: tuple[str, ...]
    observed_effect: tuple[str, ...]
    progressed: bool

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["expected_effect"] = list(self.expected_effect)
        value["observed_effect"] = list(self.observed_effect)
        return value


@dataclass(frozen=True, slots=True)
class RecordingEventAudit:
    recording: str
    recording_sha256: str
    transitions: int
    supported_predictions: int
    confirmations: int
    occurrences: tuple[EventOccurrence, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "recording": self.recording,
            "recording_sha256": self.recording_sha256,
            "transitions": self.transitions,
            "supported_predictions": self.supported_predictions,
            "confirmations": self.confirmations,
            "occurrences": [item.to_dict() for item in self.occurrences],
        }


def _direction(value: int) -> str:
    return "negative" if value < 0 else "positive" if value > 0 else "zero"


def _normalized_motion(arguments: tuple[str, ...]) -> tuple[str, str]:
    if len(arguments) < 2:
        return ("unknown", "unknown")
    dx, dy = int(arguments[0]), int(arguments[1])
    divisor = math.gcd(abs(dx), abs(dy)) or 1
    return (str(dx // divisor), str(dy // divisor))


def structural_effect_signature(events: Iterable[Event]) -> tuple[str, ...]:
    """Remove object identity, color, coordinates, and rendering-only change."""

    output: list[str] = []
    counts: Counter[str] = Counter()
    for event in events:
        if event.kind in _IGNORED_EVENTS:
            continue
        if event.kind == "object_moved":
            dx, dy = _normalized_motion(event.arguments)
            output.append(f"object_moved({dx},{dy})")
        elif event.kind == "area_changed" and len(event.arguments) >= 2:
            before, after = int(event.arguments[0]), int(event.arguments[1])
            output.append(f"area_changed({_direction(after - before)})")
        elif event.kind.startswith("rotated_"):
            output.append(event.kind)
        elif event.kind in {"object_appeared", "object_disappeared"}:
            counts[event.kind] += 1
        elif event.kind == "object_flow":
            qualitative = tuple(
                item
                for item in event.arguments
                if item in {"shape_preserved", "shape_changed"}
            )
            output.append(
                "object_flow"
                if not qualitative
                else f"object_flow({','.join(qualitative)})"
            )
        elif event.kind == "frame_difference":
            # Its size/properties are retained, but its absolute region is not.
            output.append(
                "frame_difference"
                if not event.arguments
                else f"frame_difference({','.join(event.arguments)})"
            )
    output.extend(f"{kind}(count:{count})" for kind, count in counts.items())
    return tuple(sorted(output)) or ("no_structural_change",)


def _row_data(line: str) -> dict[str, Any]:
    raw = json.loads(line)
    data = raw.get("data", raw)
    if not isinstance(data, dict):
        raise ValueError("recording row data must be an object")
    return data


def _observation(data: dict[str, Any]) -> Observation:
    raw_frame = data.get("frame", ())
    frame = raw_frame[-1] if (
        isinstance(raw_frame, list)
        and raw_frame
        and isinstance(raw_frame[0], list)
        and raw_frame[0]
        and isinstance(raw_frame[0][0], list)
    ) else raw_frame
    return Observation.create(
        state=str(data["state"]),
        available_actions=tuple(int(item) for item in data["available_actions"]),
        frame=frame,
        levels_completed=int(data.get("levels_completed", 0)),
    )


def _action_id(data: dict[str, Any]) -> int | None:
    action = data.get("action_input")
    if not isinstance(action, dict) or "id" not in action:
        return None
    return int(action["id"])


def _action_role(data: dict[str, Any], scene: Scene) -> str | None:
    """Return a structural action binding, or abstain if it is ungrounded."""

    action_id = _action_id(data)
    if action_id is None:
        return None
    action = data.get("action_input")
    action_data = action.get("data", {}) if isinstance(action, dict) else {}
    if not isinstance(action_data, dict):
        return None
    if "x" not in action_data and "y" not in action_data:
        return _digest({"action_id": action_id})
    x, y = action_data.get("x"), action_data.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        return None
    for item in scene.objects:
        min_x, min_y, _max_x, _max_y = item.bbox
        if (x - min_x, y - min_y) in item.shape:
            return _digest(
                {
                    "action_id": action_id,
                    "target": {
                        "color": item.color,
                        "area": item.area,
                        "shape": item.shape,
                    },
                }
            )
    return None


def _repeated_form_groups(
    scene: Scene,
) -> dict[
    tuple[int, int, tuple[tuple[int, int], ...]],
    tuple[tuple[int, int], ...],
]:
    groups: dict[
        tuple[int, int, tuple[tuple[int, int], ...]],
        list[tuple[int, int]],
    ] = {}
    for item in scene.objects:
        groups.setdefault(
            (item.color, item.area, item.shape),
            [],
        ).append(item.centroid)
    return {
        key: tuple(sorted(anchors, key=lambda point: (point[1], point[0])))
        for key, anchors in groups.items()
        if 2 <= len(anchors) <= 8
    }

def _group_effects(
    before: Scene,
    after: Scene,
) -> tuple[tuple[str, int, tuple[str, ...]], ...]:
    old = _repeated_form_groups(before)
    new = _repeated_form_groups(after)
    output = []
    for form in sorted(old.keys() & new.keys(), key=repr):
        left, right = old[form], new[form]
        if len(left) != len(right):
            continue
        motions = tuple(
            (after_x - before_x, after_y - before_y)
            for (before_x, before_y), (after_x, after_y) in zip(left, right)
        )
        divisor = 0
        for dx, dy in motions:
            divisor = math.gcd(divisor, abs(dx))
            divisor = math.gcd(divisor, abs(dy))
        divisor = divisor or 1
        normalized = tuple(
            sorted((dx // divisor, dy // divisor) for dx, dy in motions)
        )
        signature = (
            "repeated_form_effect("
            + "|".join(f"{dx},{dy}" for dx, dy in normalized)
            + ")",
        )
        output.append(
            (
                _digest(
                    {
                        "area": form[1],
                        "shape": form[2],
                        "color": form[0],
                    }
                ),
                len(left),
                signature,
            )
        )
    return tuple(output)


def audit_recording(
    path: Path,
    *,
    definition: EventDefinition = ACTION_EFFECT_CONTEXT_CHANGE,
) -> RecordingEventAudit:
    """Detect supported action-effect discontinuities in one recording."""

    payload = path.read_bytes()
    rows = tuple(
        _row_data(line)
        for line in payload.decode().splitlines()
        if line.strip()
    )
    tracker = SceneTracker()
    previous_observation: Observation | None = None
    histories: dict[
        tuple[str, int, str],
        Counter[tuple[str, ...]],
    ] = {}
    transitions = 0
    supported_predictions = 0
    confirmations = 0
    occurrences: list[EventOccurrence] = []

    for step, data in enumerate(rows):
        observation = _observation(data)
        boundary = (
            previous_observation is None
            or observation.levels_completed
            != previous_observation.levels_completed
            or previous_observation.state != "NOT_FINISHED"
            or observation.state != "NOT_FINISHED"
        )
        if boundary:
            tracker = SceneTracker()
            previous_scene, _events = tracker.perceive(observation)
            histories.clear()
            previous_observation = observation
            continue

        scene, _events = tracker.perceive(observation)
        action_id = _action_id(data)
        action_role = _action_role(data, previous_scene)
        previous_observation = observation
        if action_id is None or action_id == 0 or action_role is None:
            previous_scene = scene
            continue
        transitions += 1
        for subject_digest, arity, signature in _group_effects(
            previous_scene,
            scene,
        ):
            history = histories.setdefault(
                (subject_digest, arity, action_role),
                Counter(),
            )
            if history:
                expected, support = max(
                    history.items(),
                    key=lambda item: (item[1], item[0]),
                )
                if support >= definition.minimum_support:
                    supported_predictions += 1
                    if signature == expected:
                        confirmations += 1
                    else:
                        occurrences.append(
                            EventOccurrence(
                                event_id=definition.event_id,
                                step=step,
                                level=observation.levels_completed,
                                action_id=action_id,
                                subject_digest=subject_digest,
                                group_arity=arity,
                                prior_support=support,
                                expected_effect=expected,
                                observed_effect=signature,
                                progressed=False,
                            )
                        )
            history[signature] += 1
        previous_scene = scene

    return RecordingEventAudit(
        recording=str(path),
        recording_sha256=hashlib.sha256(payload).hexdigest(),
        transitions=transitions,
        supported_predictions=supported_predictions,
        confirmations=confirmations,
        occurrences=tuple(occurrences),
    )


def audit_partition(
    paths: Iterable[Path],
    *,
    partition: str,
    definition: EventDefinition = ACTION_EFFECT_CONTEXT_CHANGE,
) -> dict[str, Any]:
    """Return a canonical cross-recording event evidence report."""

    audits = tuple(
        audit_recording(path, definition=definition)
        for path in sorted(paths)
    )
    return {
        "kind": "recording-derived-event-audit-v1",
        "partition": partition,
        "definition": definition.to_dict(),
        "recordings": [item.to_dict() for item in audits],
        "summary": {
            "recordings": len(audits),
            "transitions": sum(item.transitions for item in audits),
            "supported_predictions": sum(
                item.supported_predictions for item in audits
            ),
            "confirmations": sum(item.confirmations for item in audits),
            "occurrences": sum(len(item.occurrences) for item in audits),
            "recordings_with_occurrence": sum(
                bool(item.occurrences) for item in audits
            ),
        },
    }
