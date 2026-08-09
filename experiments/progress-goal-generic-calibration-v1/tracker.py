"""Goal-agnostic stable entity tracking and action-correlated control discovery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


class CalibrationTrackingError(ValueError):
    pass


@dataclass(frozen=True)
class EntityEffect:
    entity_id: str
    before_anchor: tuple[int, int] | None
    after_anchor: tuple[int, int] | None
    delta: tuple[int, int] | None
    status: str


@dataclass(frozen=True)
class CalibrationStep:
    intervention_ref: str
    effects: tuple[EntityEffect, ...]


@dataclass(frozen=True)
class TrackedCalibration:
    initial_ids: tuple[str, ...]
    final_entities: tuple[tuple[str, Any], ...]
    steps: tuple[CalibrationStep, ...]
    controlled_candidates: tuple[str, ...]
    controlled_id: str | None
    movement_models: tuple[tuple[tuple[int, int], str], ...]
    unexplained_interventions: tuple[str, ...]


def _anchor(value: Any) -> tuple[int, int]:
    raw = getattr(value, "anchor", None)
    if not isinstance(raw, (tuple, list)) or len(raw) != 2:
        raise CalibrationTrackingError("tracked entity lacks a two-coordinate anchor")
    return int(raw[0]), int(raw[1])


def _shape_key(value: Any) -> tuple[int, tuple[int, int] | None]:
    area = int(getattr(value, "area", -1))
    cells = getattr(value, "normalized_cells", None)
    if not cells:
        return area, None
    width = 1 + max(int(x) for x, _ in cells)
    height = 1 + max(int(y) for _, y in cells)
    return area, tuple(sorted((width, height)))


def complete_correspondence(
    before: Sequence[Any],
    after: Sequence[Any],
    primary: Callable[[Sequence[Any], Sequence[Any]], Mapping[Any, Any]],
) -> dict[Any, Any]:
    """Complete an exact matcher across pose-dependent appearance changes.

    Exact/static matches are frozen first. Remaining entities may match only
    when area and unordered bounding dimensions agree; candidates are assigned
    by deterministic minimum displacement. This preserves a rotating controlled
    sprite without conflating already matched repeated stationary objects.
    """

    mapping = dict(primary(before, after))
    used = set(mapping.values())
    remaining_before = [item for item in before if item not in mapping]
    remaining_after = [item for item in after if item not in used]
    candidates = []
    for left in remaining_before:
        for right in remaining_after:
            if _shape_key(left) != _shape_key(right):
                continue
            la, ra = _anchor(left), _anchor(right)
            candidates.append((
                abs(la[0] - ra[0]) + abs(la[1] - ra[1]),
                la, ra, repr(getattr(left, "outline", "")),
                repr(getattr(right, "outline", "")), left, right,
            ))
    for _distance, _la, _ra, _lo, _ro, left, right in sorted(candidates, key=lambda row: row[:5]):
        if left in mapping or right in used:
            continue
        mapping[left] = right
        used.add(right)
    return mapping


def track_calibration(
    initial: Sequence[Any],
    successors: Sequence[Sequence[Any]],
    intervention_refs: Sequence[str],
    correspond: Callable[[Sequence[Any], Sequence[Any]], Mapping[Any, Any]],
) -> TrackedCalibration:
    """Track every entity; infer control only from repeated observed effects."""

    if len(successors) != len(intervention_refs):
        raise CalibrationTrackingError("successor/intervention lengths differ")
    current = tuple(initial)
    ids: dict[Any, str] = {item: f"e{index:03d}" for index, item in enumerate(current)}
    initial_ids = tuple(ids[item] for item in current)
    next_id = len(ids)
    steps: list[CalibrationStep] = []
    nonzero_by_entity: dict[str, list[tuple[str, tuple[int, int]]]] = {}
    zero_by_entity: dict[str, list[str]] = {}
    for ref, raw_after in zip(intervention_refs, successors):
        after = tuple(raw_after)
        mapping = dict(correspond(current, after))
        if any(before not in current or successor not in after for before, successor in mapping.items()):
            raise CalibrationTrackingError("correspondence escaped the supplied populations")
        reverse = {successor: before for before, successor in mapping.items()}
        if len(reverse) != len(mapping):
            raise CalibrationTrackingError("correspondence is not injective")
        effects: list[EntityEffect] = []
        new_ids: dict[Any, str] = {}
        for before in current:
            entity_id = ids[before]
            successor = mapping.get(before)
            if successor is None:
                effects.append(EntityEffect(entity_id, _anchor(before), None, None, "disappeared"))
                continue
            before_anchor, after_anchor = _anchor(before), _anchor(successor)
            delta = (after_anchor[0] - before_anchor[0], after_anchor[1] - before_anchor[1])
            effects.append(EntityEffect(entity_id, before_anchor, after_anchor, delta, "matched"))
            new_ids[successor] = entity_id
            if delta == (0, 0):
                zero_by_entity.setdefault(entity_id, []).append(str(ref))
            else:
                nonzero_by_entity.setdefault(entity_id, []).append((str(ref), delta))
        for successor in after:
            if successor in reverse:
                continue
            entity_id = f"e{next_id:03d}"
            next_id += 1
            new_ids[successor] = entity_id
            effects.append(EntityEffect(entity_id, None, _anchor(successor), None, "appeared"))
        steps.append(CalibrationStep(str(ref), tuple(sorted(effects, key=lambda item: item.entity_id))))
        current, ids = after, new_ids

    scores = {
        entity_id: len({ref for ref, _ in rows})
        for entity_id, rows in nonzero_by_entity.items()
    }
    maximum = max(scores.values(), default=0)
    candidates = tuple(sorted(entity_id for entity_id, score in scores.items() if score == maximum and score > 0))
    controlled = candidates[0] if len(candidates) == 1 else None
    models: list[tuple[tuple[int, int], str]] = []
    unexplained: list[str] = []
    if controlled is not None:
        by_ref = {ref: delta for ref, delta in nonzero_by_entity.get(controlled, [])}
        for ref in intervention_refs:
            if str(ref) in by_ref:
                models.append((by_ref[str(ref)], str(ref)))
            elif str(ref) in zero_by_entity.get(controlled, []):
                unexplained.append(str(ref))
    return TrackedCalibration(
        initial_ids=initial_ids,
        final_entities=tuple(sorted(((entity_id, item) for item, entity_id in ids.items()), key=lambda pair: pair[0])),
        steps=tuple(steps),
        controlled_candidates=candidates,
        controlled_id=controlled,
        movement_models=tuple(models),
        unexplained_interventions=tuple(unexplained),
    )


def workspace_transitions(calibration: TrackedCalibration) -> list[dict[str, Any]]:
    """Render all effects; never pretend an ambiguous controller is unique."""

    rows = []
    for step in calibration.steps:
        rows.append({
            "intervention_ref": step.intervention_ref,
            "controlled_id": calibration.controlled_id,
            "controlled_candidates": list(calibration.controlled_candidates),
            "entity_effects": [
                {
                    "entity_id": effect.entity_id,
                    "before_anchor": effect.before_anchor,
                    "after_anchor": effect.after_anchor,
                    "delta": effect.delta,
                    "status": effect.status,
                }
                for effect in step.effects
            ],
        })
    return rows


__all__ = ["CalibrationStep", "CalibrationTrackingError", "EntityEffect", "TrackedCalibration", "complete_correspondence", "track_calibration", "workspace_transitions"]
