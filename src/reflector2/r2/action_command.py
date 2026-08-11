"""Typed, evidence-grounded environment action commands.

This module knows only ARC's public transport schema.  It does not assign an
action a game meaning.  Parameterized actions are instantiated only at cells
that belong to a currently observed R2 region, so every proposed payload has a
direct visual evidence path.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence


CLICK_CANDIDATE_BUDGET = 64


def _stable_id(prefix: str, value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(body.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True, slots=True)
class ActionCommand:
    """One exact legal transport invocation plus its situated evidence."""

    action_id: int
    data_items: tuple[tuple[str, int], ...]
    command_id: str
    effect_scope_id: str | int
    payload_grounding: Mapping[str, Any] | None = None

    @classmethod
    def create(
        cls,
        action_id: int,
        data: Mapping[str, int] | None = None,
        *,
        payload_grounding: Mapping[str, Any] | None = None,
        effect_scope: Any | None = None,
    ) -> "ActionCommand":
        canonical = tuple(sorted((str(key), int(value)) for key, value in (data or {}).items()))
        command_id = _stable_id(
            "ac", {"action_id": int(action_id), "data": dict(canonical)},
        )
        scope_id: str | int = (
            int(action_id)
            if not canonical
            else _stable_id(
                "as",
                {
                    "action_id": int(action_id),
                    "data": dict(canonical),
                    "payload_schema": tuple(key for key, _value in canonical),
                    "effect_scope": effect_scope,
                },
            )
        )
        return cls(
            action_id=int(action_id),
            data_items=canonical,
            command_id=command_id,
            effect_scope_id=scope_id,
            payload_grounding=(
                None if payload_grounding is None else dict(payload_grounding)
            ),
        )

    @property
    def data(self) -> dict[str, int]:
        return dict(self.data_items)

    def document(self) -> dict[str, Any]:
        return {
            "protocol": "action-command-v1",
            "command_id": self.command_id,
            "action_id": self.action_id,
            "data": self.data,
            "effect_scope_id": self.effect_scope_id,
            "payload_grounding": (
                None if self.payload_grounding is None else dict(self.payload_grounding)
            ),
        }


def command_from_document(value: Mapping[str, Any]) -> ActionCommand:
    """Read a durable command while checking its exact canonical identity."""

    grounding = value.get("payload_grounding")
    command = ActionCommand.create(
        int(value["action_id"]),
        value.get("data", {}),
        payload_grounding=grounding if isinstance(grounding, Mapping) else None,
        effect_scope=value.get("effect_scope_id"),
    )
    # Older events have only action_id/data and intentionally acquire their
    # canonical identity here.  New documents must not lie about it.
    supplied = value.get("command_id")
    if supplied is not None and str(supplied) != command.command_id:
        raise ValueError("action command identity does not match its payload")
    if value.get("effect_scope_id") is not None:
        object.__setattr__(command, "effect_scope_id", value["effect_scope_id"])
    return command


def legal_action_ids(environment: Any, observation: Any) -> tuple[int, ...]:
    """Return simple actions and supported x/y parameterized actions."""

    available = {
        int(getattr(item, "value", item))
        for item in getattr(observation, "available_actions", ())
    }
    by_id = {
        int(getattr(item, "value", item)): item
        for item in getattr(environment, "action_space", ())
    }
    output: list[int] = []
    for action_id in sorted(available):
        transport = by_id.get(action_id)
        if transport is None:
            from arcengine import GameAction

            transport = GameAction.from_id(action_id)
        is_complex = getattr(transport, "is_complex", None)
        if not callable(is_complex) or not bool(is_complex()):
            output.append(action_id)
            continue
        fields = set(getattr(getattr(transport, "action_type", None), "model_fields", {}))
        if {"x", "y"} <= fields and fields <= {"game_id", "x", "y"}:
            output.append(action_id)
    return tuple(output)


def requires_payload(action_id: int) -> bool:
    from arcengine import GameAction

    return bool(GameAction.from_id(int(action_id)).is_complex())


def _representative_cell(region: Mapping[str, Any]) -> tuple[int, int]:
    cells = tuple((int(y), int(x)) for y, x in region.get("cells", ()))
    if not cells:
        raise ValueError("click grounding region has no observed cells")
    center_y2, center_x2 = (float(item) for item in region["center2"])
    return min(
        cells,
        key=lambda cell: (
            (2.0 * cell[0] - center_y2) ** 2 + (2.0 * cell[1] - center_x2) ** 2,
            cell[0],
            cell[1],
        ),
    )


def commands_for_frame(
    legal_actions: Sequence[int],
    observer: Any,
    *,
    budget: int = CLICK_CANDIDATE_BUDGET,
) -> tuple[ActionCommand, ...]:
    """Instantiate legal actions from the current grounded R2 workspace."""

    from arcengine import GameAction

    commands: list[ActionCommand] = []
    regions = tuple(getattr(observer, "last_regions", ()))
    height, width = tuple(getattr(observer, "frame_shape", (0, 0)))
    seen_coordinates: set[tuple[int, int]] = set()
    for action_id in sorted(set(int(item) for item in legal_actions)):
        transport = GameAction.from_id(action_id)
        if not transport.is_complex():
            commands.append(ActionCommand.create(action_id))
            continue
        fields = set(getattr(transport.action_type, "model_fields", {}))
        if not ({"x", "y"} <= fields and fields <= {"game_id", "x", "y"}):
            continue
        for region in regions:
            if len(seen_coordinates) >= int(budget):
                break
            y, x = _representative_cell(region)
            if (x, y) in seen_coordinates or not (0 <= x < width and 0 <= y < height):
                continue
            data = {"x": x, "y": y}
            transport.validate_data(data)
            seen_coordinates.add((x, y))
            structural_key = (
                int(region["value"]), int(region["area"]),
                tuple(tuple(int(part) for part in cell) for cell in region["shape"]),
            )
            grounding = {
                "kind": "observed-region-cell",
                "frame_digest": getattr(observer, "last_digest", None),
                "region_binding_id": str(region["binding_id"]),
                "cell_rc": [y, x],
                "region_structural_key": structural_key,
            }
            commands.append(ActionCommand.create(
                action_id,
                data,
                payload_grounding=grounding,
                effect_scope={"region_structural_key": structural_key},
            ))
    return tuple(sorted(commands, key=lambda item: (item.action_id, item.data_items)))


__all__ = [
    "ActionCommand", "CLICK_CANDIDATE_BUDGET", "command_from_document",
    "commands_for_frame", "legal_action_ids", "requires_payload",
]
