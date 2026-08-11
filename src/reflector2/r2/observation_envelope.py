"""Lossless ordered ARC frame packets with an explicit settled support."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
import hashlib
import json
from typing import Any


Grid = tuple[tuple[int, ...], ...]
PROTOCOL = "ordered-observation-envelope-v1"


def _grid(value: Any) -> Grid:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ValueError("ARC support must be a non-empty rectangular grid")
    rows: list[tuple[int, ...]] = []
    width: int | None = None
    for raw_row in value:
        if hasattr(raw_row, "tolist"):
            raw_row = raw_row.tolist()
        if (
            not isinstance(raw_row, Sequence)
            or isinstance(raw_row, (str, bytes))
            or not raw_row
        ):
            raise ValueError("ARC support must be a non-empty rectangular grid")
        row = tuple(int(cell) for cell in raw_row)
        width = len(row) if width is None else width
        if len(row) != width:
            raise ValueError("ARC support must be a non-empty rectangular grid")
        rows.append(row)
    return tuple(rows)


def ordered_frames(frame: Any) -> tuple[Grid, ...]:
    """Normalize one grid or an ordered toolkit packet without reordering."""

    if hasattr(frame, "tolist"):
        frame = frame.tolist()
    if not isinstance(frame, Sequence) or isinstance(frame, (str, bytes)) or not frame:
        raise ValueError("ARC observation has no frame supports")
    first = frame[0]
    if hasattr(first, "tolist"):
        first = first.tolist()
    if not isinstance(first, Sequence) or isinstance(first, (str, bytes)) or not first:
        raise ValueError("ARC observation has no frame supports")
    first_cell = first[0]
    layers: Iterable[Any] = (frame,) if not isinstance(first_cell, Sequence) else frame
    return tuple(_grid(layer) for layer in layers)


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def from_observation(observation: Any) -> dict[str, Any]:
    """Return a JSON-safe packet whose last support is the settled frame."""

    supports = ordered_frames(observation.frame)
    serial = [[list(row) for row in grid] for grid in supports]
    digests = [_digest(grid) for grid in serial]
    settled = len(serial) - 1
    body = {
        "protocol": PROTOCOL,
        "ordered_frames": serial,
        "support_digests": digests,
        "support_count": len(serial),
        "settled_support_ordinal": settled,
        "settled_support_digest": digests[settled],
    }
    return {**body, "digest": _digest(body)}


def settled_frame(envelope: dict[str, Any]) -> list[list[int]]:
    supports = envelope["ordered_frames"]
    ordinal = int(envelope["settled_support_ordinal"])
    return [[int(cell) for cell in row] for row in supports[ordinal]]


def install(environment_base: Any) -> None:
    """Expose the envelope builder to inherited ledger storage."""

    environment_base.observation_envelope = from_observation
