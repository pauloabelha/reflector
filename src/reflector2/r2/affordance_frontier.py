"""Bounded observation opportunities for semantic abduction.

The frontier is deliberately pre-semantic: providers report measurable
structure, not verbs, goals, object identities, or actions.  A semantic model
may name and compose the opportunities, but R2 must compile and test any such
proposal before it can affect control.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping, Protocol, Sequence

from reflector2.r2.semantic_measure import spatial_feature


AFFORDANCE_FRONTIER_PROTOCOL = "r2-observation-affordance-frontier-v0"
AFFORDANCE_PROVIDER_PROTOCOL = "r2-spatial-set-opportunities-v0"
MAX_AFFORDANCE_ENTITIES = 32
MAX_PAIR_HYPOTHESES = 992


class AffordanceProvider(Protocol):
    """Extension point for perceptual, temporal, symbolic, or UI channels."""

    name: str

    def observe(self, entities: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class _RelationProbe:
    left_feature: str
    right_feature: str
    comparison: str
    coordinate_frame: str
    include_separation_gap: bool = False


# These are measurement-language probes, not semantic categories.  In
# particular, none is assigned a verb or treated as desirable.
_SPATIAL_PROBES = (
    _RelationProbe("occupancy", "occupancy", "symmetric_difference_size", "intrinsic"),
    _RelationProbe("boundary", "boundary", "symmetric_difference_size", "scene", True),
    _RelationProbe("occupancy", "occupancy", "overlap_deficit", "scene", True),
    _RelationProbe("occupancy", "enclosed_negative_space", "symmetric_difference_size", "intrinsic"),
    _RelationProbe("occupancy", "enclosed_negative_space", "symmetric_difference_size", "scene", True),
    _RelationProbe("occupancy", "envelope_negative_space", "symmetric_difference_size", "intrinsic"),
    _RelationProbe("occupancy", "envelope_negative_space", "symmetric_difference_size", "scene", True),
)


def _compare(left: frozenset[tuple[float, float]], right: frozenset[tuple[float, float]], comparison: str) -> float:
    if comparison == "symmetric_difference_size":
        return float(len(left ^ right))
    if comparison == "left_unmatched_size":
        return float(len(left - right))
    if comparison == "right_unmatched_size":
        return float(len(right - left))
    return float(min(len(left), len(right)) - len(left & right))


def _gap(left: frozenset[tuple[float, float]], right: frozenset[tuple[float, float]]) -> float:
    if not left or not right:
        return 0.0
    return max(0.0, min(
        abs(ly - ry) + abs(lx - rx)
        for ly, lx in left for ry, rx in right
    ) - 1.0)


def _bounded_entities(entities: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    usable = [item for item in entities if item.get("cells")]
    # Preserve scale diversity without using palette, position, or identity as
    # semantic evidence. Stable source order breaks exact ties only.
    if len(usable) <= MAX_AFFORDANCE_ENTITIES:
        return usable
    ranked = sorted(enumerate(usable), key=lambda pair: (len(pair[1].get("cells", ())), pair[0]))
    small = ranked[: MAX_AFFORDANCE_ENTITIES // 2]
    large = ranked[-(MAX_AFFORDANCE_ENTITIES - len(small)):]
    return [item for _index, item in sorted([*small, *large])]


def _opportunity_ref(template: Mapping[str, Any]) -> str:
    payload = json.dumps(template, sort_keys=True, separators=(",", ":"))
    return f"affordance_{sha256(payload.encode()).hexdigest()[:16]}"


def _scale_bands(values: Sequence[tuple[float, float, int]]) -> list[dict[str, Any]]:
    bands = ((1, 4), (5, 16), (17, 64), (65, None))
    output = []
    for minimum, maximum in bands:
        members = [
            item for item in values
            if item[2] >= minimum and (maximum is None or item[2] <= maximum)
        ]
        if not members:
            continue
        best = min(members)
        output.append({
            "feature_support_range": [minimum, maximum],
            "measurable_pair_hypotheses": len(members),
            "best_normalized_residual": round(best[0], 6),
            "best_raw_residual": best[1],
            "best_feature_support": best[2],
        })
    return output


class SpatialSetAffordanceProvider:
    """Report anonymous relational measurements over current spatial entities."""

    name = "spatial-set"

    def observe(self, entities: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        bounded = _bounded_entities(entities)
        observations: list[dict[str, Any]] = []
        feature_cache: dict[tuple[int, str, str], frozenset[tuple[float, float]]] = {}

        def feature(index: int, name: str, frame: str) -> frozenset[tuple[float, float]]:
            key = (index, name, frame)
            if key not in feature_cache:
                feature_cache[key] = spatial_feature(bounded[index], name, coordinate_frame=frame)
            return feature_cache[key]

        for probe in _SPATIAL_PROBES:
            template = {
                "protocol": "r2-spatial-set-residual-v0",
                "left_source": "actor",
                "left_feature": probe.left_feature,
                "right_source": "target",
                "right_feature": probe.right_feature,
                "comparison": probe.comparison,
                "coordinate_frame": probe.coordinate_frame,
                "include_separation_gap": probe.include_separation_gap,
            }
            opportunity_ref = _opportunity_ref(template)
            template["basis_opportunity_ref"] = opportunity_ref
            values: list[tuple[float, float, int]] = []
            unmeasurable = 0
            enumerated = 0
            quotient_orientation = (
                probe.comparison in {
                    "symmetric_difference_size", "overlap_deficit",
                }
                and probe.left_feature == probe.right_feature
            )
            for left_index in range(len(bounded)):
                for right_index in range(len(bounded)):
                    if (
                        left_index == right_index
                        or (quotient_orientation and right_index < left_index)
                        or enumerated >= MAX_PAIR_HYPOTHESES
                    ):
                        continue
                    enumerated += 1
                    left = feature(left_index, probe.left_feature, probe.coordinate_frame)
                    right = feature(right_index, probe.right_feature, probe.coordinate_frame)
                    if not left or not right:
                        unmeasurable += 1
                        continue
                    raw = _compare(left, right, probe.comparison)
                    if probe.include_separation_gap:
                        raw += _gap(left, right)
                    support = len(left | right)
                    values.append((raw / max(1, support), raw, support))
            values.sort()
            best = values[0] if values else None
            runner_up = values[1] if len(values) > 1 else None
            near = 0 if best is None else sum(
                1 for normalized, _raw, _support in values
                if normalized <= best[0] + 0.05
            )
            observations.append({
                "observation_family": "spatial_set_relation",
                "provider_protocol": AFFORDANCE_PROVIDER_PROTOCOL,
                "opportunity_ref": opportunity_ref,
                "measurement_template": template,
                "left_feature": probe.left_feature,
                "right_feature": probe.right_feature,
                "comparison": probe.comparison,
                "coordinate_frame": probe.coordinate_frame,
                "include_separation_gap": probe.include_separation_gap,
                "role_orientation": (
                    "quotiented-commutative" if quotient_orientation
                    else "ordered"
                ),
                "measurable_pair_hypotheses": len(values),
                "unmeasurable_pair_hypotheses": unmeasurable,
                "best_normalized_residual": None if best is None else round(best[0], 6),
                "runner_up_normalized_residual": None if runner_up is None else round(runner_up[0], 6),
                "distinctiveness_margin": None if best is None or runner_up is None else round(runner_up[0] - best[0], 6),
                "near_best_pair_count": near,
                "best_raw_residual": None if best is None else best[1],
                "best_feature_support": None if best is None else best[2],
                "scale_bands": _scale_bands(values),
                "semantic_label": None,
                "desired": None,
            })

        enclosed_sizes = [
            len(feature(index, "enclosed_negative_space", "intrinsic"))
            for index in range(len(bounded))
        ]
        observations.append({
            "observation_family": "spatial_topology",
            "provider_protocol": AFFORDANCE_PROVIDER_PROTOCOL,
            "feature": "enclosed_negative_space",
            "entities_measured": len(bounded),
            "entities_with_nonempty_feature": sum(size > 0 for size in enclosed_sizes),
            "maximum_feature_support": max(enclosed_sizes, default=0),
            "total_feature_support": sum(enclosed_sizes),
            "semantic_label": None,
            "desired": None,
        })
        return observations


def build_affordance_frontier(
    entities: Sequence[Mapping[str, Any]],
    *,
    providers: Sequence[AffordanceProvider] | None = None,
) -> dict[str, Any]:
    """Build an anonymous, zero-authority semantic attention surface."""

    active = tuple(providers or (SpatialSetAffordanceProvider(),))
    observations: list[dict[str, Any]] = []
    for provider in active:
        observations.extend(provider.observe(entities))
    return {
        "protocol": AFFORDANCE_FRONTIER_PROTOCOL,
        "authority": "observation-derived-attention-only",
        "semantic_status": "unnamed-open",
        "control_authority": False,
        "entity_identities_exposed": False,
        "provider_names": [provider.name for provider in active],
        "observations": observations,
    }


__all__ = [
    "AFFORDANCE_FRONTIER_PROTOCOL",
    "AffordanceProvider",
    "SpatialSetAffordanceProvider",
    "build_affordance_frontier",
]
