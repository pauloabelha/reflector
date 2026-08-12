"""Bounded model-proposed measurements over neutral spatial primitives.

The semantic model may select and compose primitives, but it cannot add code or
declare a proposal grounded.  This module is deliberately ignorant of verbs,
games, colors, action tokens, and desired solutions.  It only validates one
small declarative language and evaluates it over already-grounded entities.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping

from reflector2.r2.causal_entity import boundary, occupied_cells


SEMANTIC_MEASURE_PROTOCOL = "r2-spatial-set-residual-v0"
SPATIAL_SET_FEATURES = frozenset({
    "occupancy",
    "boundary",
    "enclosed_negative_space",
    "envelope_negative_space",
})
SPATIAL_SET_COMPARISONS = frozenset({
    "symmetric_difference_size",
    "left_unmatched_size",
    "right_unmatched_size",
    "overlap_deficit",
})
SPATIAL_SET_SOURCES = frozenset({"actor", "target"})
SPATIAL_COORDINATE_FRAMES = frozenset({"scene", "intrinsic"})
MAX_FEATURE_CELLS = 4096


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _normalize(cells: frozenset[tuple[float, float]]) -> frozenset[tuple[float, float]]:
    if not cells:
        return cells
    min_y = min(y for y, _x in cells)
    min_x = min(x for _y, x in cells)
    return frozenset((y - min_y, x - min_x) for y, x in cells)


def _empty_envelope(entity: Any) -> frozenset[tuple[float, float]]:
    cells = occupied_cells(entity)
    if not cells:
        return frozenset()
    min_y = int(min(y for y, _x in cells)); max_y = int(max(y for y, _x in cells))
    min_x = int(min(x for _y, x in cells)); max_x = int(max(x for _y, x in cells))
    return frozenset(
        (float(y), float(x))
        for y in range(min_y, max_y + 1)
        for x in range(min_x, max_x + 1)
        if (float(y), float(x)) not in cells
    )


def _enclosed_negative_space(entity: Any) -> frozenset[tuple[float, float]]:
    """Return empty cells enclosed by occupancy under four-connectivity."""

    cells = occupied_cells(entity)
    if not cells:
        return frozenset()
    min_y = int(min(y for y, _x in cells)); max_y = int(max(y for y, _x in cells))
    min_x = int(min(x for _y, x in cells)); max_x = int(max(x for _y, x in cells))
    limits = (min_y - 1, min_x - 1, max_y + 1, max_x + 1)
    exterior: set[tuple[float, float]] = set()
    frontier = [(float(limits[0]), float(limits[1]))]
    while frontier:
        point = frontier.pop()
        if point in exterior or point in cells:
            continue
        y, x = point
        if not (limits[0] <= y <= limits[2] and limits[1] <= x <= limits[3]):
            continue
        exterior.add(point)
        frontier.extend(((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)))
    return frozenset(
        (float(y), float(x))
        for y in range(min_y, max_y + 1)
        for x in range(min_x, max_x + 1)
        if (float(y), float(x)) not in cells
        and (float(y), float(x)) not in exterior
    )


def spatial_feature(
    entity: Any, feature: str, *, coordinate_frame: str = "scene",
) -> frozenset[tuple[float, float]]:
    """Evaluate one allowlisted spatial-set feature."""

    if feature == "occupancy":
        cells = occupied_cells(entity)
    elif feature == "boundary":
        cells = boundary(entity)
    elif feature == "enclosed_negative_space":
        cells = _enclosed_negative_space(entity)
    elif feature == "envelope_negative_space":
        cells = _empty_envelope(entity)
    else:
        raise ValueError(f"unsupported spatial feature: {feature!r}")
    if len(cells) > MAX_FEATURE_CELLS:
        raise ValueError("spatial feature exceeds bounded cell budget")
    return _normalize(cells) if coordinate_frame == "intrinsic" else cells


def _separation_gap(
    left: frozenset[tuple[float, float]],
    right: frozenset[tuple[float, float]],
) -> float:
    if not left or not right:
        return 0.0
    return max(0.0, min(
        abs(ly - ry) + abs(lx - rx)
        for ly, lx in left for ry, rx in right
    ) - 1.0)


@dataclass(frozen=True, slots=True)
class SemanticMeasureHypothesis:
    """One proposal-only residual definition compiled by R2."""

    observable: str
    left_source: str
    left_feature: str
    right_source: str
    right_feature: str
    comparison: str
    coordinate_frame: str = "scene"
    include_separation_gap: bool = False
    protocol: str = SEMANTIC_MEASURE_PROTOCOL

    def __post_init__(self) -> None:
        if self.protocol != SEMANTIC_MEASURE_PROTOCOL:
            raise ValueError("unsupported semantic measurement protocol")
        if not self.observable.startswith("proposed_"):
            raise ValueError("model-defined observable must start with proposed_")
        if self.left_source not in SPATIAL_SET_SOURCES or self.right_source not in SPATIAL_SET_SOURCES:
            raise ValueError("measurement source must be actor or target")
        if self.left_feature not in SPATIAL_SET_FEATURES or self.right_feature not in SPATIAL_SET_FEATURES:
            raise ValueError("unsupported measurement feature")
        if self.comparison not in SPATIAL_SET_COMPARISONS:
            raise ValueError("unsupported spatial-set comparison")
        if self.coordinate_frame not in SPATIAL_COORDINATE_FRAMES:
            raise ValueError("unsupported coordinate frame")
        if self.coordinate_frame == "intrinsic" and self.include_separation_gap:
            raise ValueError("intrinsic measurements cannot include scene separation")

    @classmethod
    def compile(
        cls, observable: str, value: Mapping[str, Any],
    ) -> "SemanticMeasureHypothesis":
        expected = {
            "protocol", "left_source", "left_feature", "right_source",
            "right_feature", "comparison", "coordinate_frame",
            "include_separation_gap",
        }
        if set(value) != expected:
            raise ValueError("semantic measurement fields do not match protocol")
        return cls(observable=str(observable), **dict(value))

    @property
    def fingerprint(self) -> str:
        return sha256(_canonical(self.document()).encode()).hexdigest()[:24]

    def document(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "left_source": self.left_source,
            "left_feature": self.left_feature,
            "right_source": self.right_source,
            "right_feature": self.right_feature,
            "comparison": self.comparison,
            "coordinate_frame": self.coordinate_frame,
            "include_separation_gap": self.include_separation_gap,
        }

    def evaluate(self, actor: Any, target: Any) -> float | None:
        entities = {"actor": actor, "target": target}
        left = spatial_feature(
            entities[self.left_source], self.left_feature,
            coordinate_frame=self.coordinate_frame,
        )
        right = spatial_feature(
            entities[self.right_source], self.right_feature,
            coordinate_frame=self.coordinate_frame,
        )
        # An empty selected feature supplies no grounding evidence.  Returning
        # None prevents a vacuous zero from becoming a control terminal.
        if not left or not right:
            return None
        if self.comparison == "symmetric_difference_size":
            value = float(len(left ^ right))
        elif self.comparison == "left_unmatched_size":
            value = float(len(left - right))
        elif self.comparison == "right_unmatched_size":
            value = float(len(right - left))
        else:
            value = float(min(len(left), len(right)) - len(left & right))
        if self.include_separation_gap:
            value += _separation_gap(left, right)
        return value


__all__ = [
    "MAX_FEATURE_CELLS",
    "SEMANTIC_MEASURE_PROTOCOL",
    "SPATIAL_COORDINATE_FRAMES",
    "SPATIAL_SET_COMPARISONS",
    "SPATIAL_SET_FEATURES",
    "SemanticMeasureHypothesis",
    "spatial_feature",
]
