"""Demand-driven causal entity induction for the R2 situated workspace.

The module deliberately does not segment images and does not plan.  It treats
already-grounded spatial bindings as defeasible members, compares their
settled transformations, and retains a bounded frontier of higher-order
factorizations.  A candidate becomes control-eligible only after repeated
environment-cited support.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
from hashlib import sha256
import json
import math
import time
from typing import Any, Iterable, Mapping, Protocol, Sequence, runtime_checkable


CAE_PROTOCOL = "r2-causal-entity-v0"
IDENTITY_STATES = frozenset({"OPEN", "UNIQUE", "AMBIGUOUS", "BROKEN"})
EPISTEMIC_STATES = frozenset({"OPEN", "SUPPORTED", "CONTESTED", "REFUTED"})


def _stable_id(prefix: str, value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), default=list)
    return f"{prefix}:{sha256(body.encode()).hexdigest()[:24]}"


def _as_mapping(entity: Any) -> Mapping[str, Any]:
    if isinstance(entity, Mapping):
        return entity
    if hasattr(entity, "cells") and hasattr(entity, "binding_id"):
        return {
            "binding_id": getattr(entity, "binding_id"),
            "cells": getattr(entity, "cells"),
            "value": getattr(entity, "value", None),
            "kind": (
                "causal-entity-binding"
                if hasattr(entity, "member_binding_ids") else "region-binding"
            ),
            "epistemic_status": getattr(entity, "status", None),
        }
    document = getattr(entity, "document", None)
    if callable(document):
        return document()
    raise TypeError(f"not a spatial entity: {type(entity)!r}")


@runtime_checkable
class SpatialEntity(Protocol):
    """Small geometry interface consumed by generic R2 verbs/potentials."""

    @property
    def binding_id(self) -> str: ...

    @property
    def cells(self) -> tuple[tuple[float, float], ...]: ...

    def document(self) -> Mapping[str, Any]: ...


def occupied_cells(entity: Any) -> frozenset[tuple[float, float]]:
    value = _as_mapping(entity).get("cells", ())
    return frozenset((float(y), float(x)) for y, x in value)


def boundary(entity: Any) -> frozenset[tuple[float, float]]:
    cells = occupied_cells(entity)
    return frozenset(
        cell for cell in cells
        if any((cell[0] + dy, cell[1] + dx) not in cells for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)))
    )


def envelope(entity: Any) -> tuple[float, float, float, float] | None:
    cells = occupied_cells(entity)
    if not cells:
        return None
    ys, xs = [p[0] for p in cells], [p[1] for p in cells]
    return min(ys), min(xs), max(ys), max(xs)


def centroid(entity: Any) -> tuple[float, float]:
    cells = occupied_cells(entity)
    if not cells:
        return 0.0, 0.0
    return sum(y for y, _x in cells) / len(cells), sum(x for _y, x in cells) / len(cells)


def area(entity: Any) -> int:
    return len(occupied_cells(entity))


def topology(entity: Any) -> Mapping[str, int]:
    cells = occupied_cells(entity)
    if not cells:
        return {"components": 0, "holes": 0}
    remaining, components = set(cells), 0
    while remaining:
        components += 1
        frontier = [remaining.pop()]
        while frontier:
            y, x = frontier.pop()
            for point in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if point in remaining:
                    remaining.remove(point); frontier.append(point)
    box = envelope(entity)
    assert box is not None
    min_y, min_x, max_y, max_x = (int(v) for v in box)
    exterior: set[tuple[float, float]] = set()
    frontier = [(float(min_y - 1), float(min_x - 1))]
    limits = (min_y - 1, min_x - 1, max_y + 1, max_x + 1)
    while frontier:
        point = frontier.pop()
        if point in exterior or point in cells:
            continue
        y, x = point
        if not (limits[0] <= y <= limits[2] and limits[1] <= x <= limits[3]):
            continue
        exterior.add(point)
        frontier.extend(((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)))
    enclosed = {
        (float(y), float(x)) for y in range(min_y, max_y + 1) for x in range(min_x, max_x + 1)
        if (float(y), float(x)) not in cells and (float(y), float(x)) not in exterior
    }
    holes = 0
    while enclosed:
        holes += 1
        frontier = [enclosed.pop()]
        while frontier:
            y, x = frontier.pop()
            for point in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if point in enclosed:
                    enclosed.remove(point); frontier.append(point)
    return {"components": components, "holes": holes}


def normalized_shape(entity: Any, size: int = 16) -> frozenset[tuple[int, int]]:
    cells = occupied_cells(entity)
    box = envelope(entity)
    if not cells or box is None:
        return frozenset()
    min_y, min_x, max_y, max_x = box
    height, width = max(1.0, max_y - min_y), max(1.0, max_x - min_x)
    return frozenset(
        (round((y - min_y) * (size - 1) / height), round((x - min_x) * (size - 1) / width))
        for y, x in cells
    )


@dataclass(frozen=True, slots=True)
class RegionBinding:
    binding_id: str
    cells: tuple[tuple[float, float], ...]
    value: int | None = None
    source: Mapping[str, Any] = field(default_factory=dict, compare=False, repr=False)

    @classmethod
    def from_value(cls, value: Any) -> "RegionBinding":
        raw = _as_mapping(value)
        return cls(
            binding_id=str(raw.get("binding_id") or _stable_id("region", raw.get("cells", ()))),
            cells=tuple((float(y), float(x)) for y, x in raw.get("cells", ())),
            value=None if raw.get("value") is None else int(raw["value"]),
            source=raw,
        )

    def document(self) -> Mapping[str, Any]:
        return {**dict(self.source), "binding_id": self.binding_id, "cells": self.cells, "value": self.value}


@dataclass(frozen=True, slots=True)
class TransformSignature:
    kind: str
    parameters: tuple[float, ...] = ()

    def document(self) -> dict[str, Any]:
        return {"kind": self.kind, "parameters": list(self.parameters)}


@dataclass(frozen=True, slots=True)
class MemberTransition:
    predecessor: RegionBinding
    successor: RegionBinding
    signature: TransformSignature
    correspondence_residual: float
    lineage_id: str

    @property
    def changed(self) -> bool:
        return self.signature.kind != "invariant"

    def document(self) -> dict[str, Any]:
        return {
            "predecessor": self.predecessor.binding_id,
            "successor": self.successor.binding_id,
            "lineage_id": self.lineage_id,
            "transform": self.signature.document(),
            "correspondence_residual": self.correspondence_residual,
        }


@dataclass(frozen=True, slots=True)
class CausalScopeResidual:
    observed_changed_entities: int
    observed_changed_support: int
    explained_changed_entities: int
    explained_changed_support: int
    unexplained_changed_entities: int
    unexplained_changed_support: int
    predicted_changed_observed: int
    predicted_changed_missing: int
    predicted_invariants_violated: int
    coherent_unexplained_groups: tuple[tuple[str, ...], ...]
    ambiguous_global_change: bool = False

    @property
    def coverage(self) -> float:
        if self.observed_changed_support == 0:
            return 1.0
        return self.explained_changed_support / self.observed_changed_support

    @property
    def accommodation_required(self) -> bool:
        return (
            not self.ambiguous_global_change
            and bool(self.coherent_unexplained_groups)
            and (
                self.unexplained_changed_support > 0
                or self.predicted_changed_missing > 0
                or self.predicted_invariants_violated > 0
            )
        )

    def document(self) -> dict[str, Any]:
        return {
            "protocol": "r2-causal-scope-residual-v0",
            "observed_changed_entities": self.observed_changed_entities,
            "observed_changed_support": self.observed_changed_support,
            "explained_changed_entities": self.explained_changed_entities,
            "explained_changed_support": self.explained_changed_support,
            "unexplained_changed_entities": self.unexplained_changed_entities,
            "unexplained_changed_support": self.unexplained_changed_support,
            "predicted_changed_observed": self.predicted_changed_observed,
            "predicted_changed_missing": self.predicted_changed_missing,
            "predicted_invariants_violated": self.predicted_invariants_violated,
            "coherent_unexplained_groups": [list(group) for group in self.coherent_unexplained_groups],
            "ambiguous_global_change": self.ambiguous_global_change,
            "coverage": round(self.coverage, 6),
            "accommodation_required": self.accommodation_required,
        }


@dataclass(frozen=True, slots=True)
class CausalEntityBinding:
    """One situated, recursively usable higher-order spatial binding."""

    binding_id: str
    entity_id: str
    cells: tuple[tuple[float, float], ...]
    member_binding_ids: tuple[str, ...]
    primitive_member_ids: tuple[str, ...]
    transform: TransformSignature
    status: str
    identity_status: str
    support: int
    contradictions: int
    evidence: tuple[str, ...]
    internal_relation_residual: float
    member_values: tuple[int | None, ...] = ()
    action_conditioned_transforms: tuple[
        tuple[str, tuple[TransformSignature, ...]], ...
    ] = ()

    def __post_init__(self) -> None:
        if self.status not in EPISTEMIC_STATES:
            raise ValueError(f"invalid causal entity status: {self.status}")
        if self.identity_status not in IDENTITY_STATES:
            raise ValueError(f"invalid causal entity identity: {self.identity_status}")

    def document(self) -> Mapping[str, Any]:
        cells = tuple(sorted(self.cells))
        cy, cx = centroid(self)
        min_y = min((p[0] for p in cells), default=0.0)
        min_x = min((p[1] for p in cells), default=0.0)
        shape = tuple(sorted((y - min_y, x - min_x) for y, x in cells))
        values = {value for value in self.member_values if value is not None}
        topo = topology(self)
        return {
            "protocol": CAE_PROTOCOL,
            "kind": "causal-entity-binding",
            "spatial_interface": "SpatialEntity",
            "binding_id": self.binding_id,
            "causal_entity_id": self.entity_id,
            "cells": cells,
            "area": len(cells),
            "center2": (2.0 * cy, 2.0 * cx),
            "shape": shape,
            "outline": tuple(sorted((y - min_y, x - min_x) for y, x in boundary(self))),
            "hole_count": int(topo["holes"]),
            "value": next(iter(values)) if len(values) == 1 else -1,
            "member_binding_ids": self.member_binding_ids,
            "primitive_member_ids": self.primitive_member_ids,
            "membership": "situated-defeasible",
            "transform": self.transform.document(),
            "action_conditioned_transforms": {
                scope: [transform.document() for transform in transforms]
                for scope, transforms in self.action_conditioned_transforms
            },
            "epistemic_status": self.status,
            "identity_status": self.identity_status,
            "support": self.support,
            "contradictions": self.contradictions,
            "evidence_refs": self.evidence,
            "internal_relation_residual": self.internal_relation_residual,
        }


@dataclass(slots=True)
class _Hypothesis:
    entity_id: str
    lineages: tuple[str, ...]
    current_member_ids: tuple[str, ...]
    primitive_member_ids: tuple[str, ...]
    transform: TransformSignature
    support_evidence: list[str] = field(default_factory=list)
    contradiction_evidence: list[str] = field(default_factory=list)
    internal_relation_residual: float = 0.0
    identity_status: str = "OPEN"
    last_seen: int = 0
    minimum_support: int = 2
    action_transforms: dict[str, set[TransformSignature]] = field(default_factory=dict)

    @property
    def status(self) -> str:
        if self.contradiction_evidence:
            return "REFUTED" if len(self.contradiction_evidence) >= max(1, len(self.support_evidence) // 2) else "CONTESTED"
        return "SUPPORTED" if len(self.support_evidence) >= self.minimum_support else "OPEN"


@dataclass(frozen=True, slots=True)
class InductionResult:
    residual: CausalScopeResidual
    candidates_generated: int
    candidates_retained: int
    maximum_members: int
    elapsed_ms: float
    global_transform: TransformSignature | None
    bindings: tuple[CausalEntityBinding, ...]

    def document(self) -> dict[str, Any]:
        return {
            "protocol": CAE_PROTOCOL,
            "causal_scope_residual": self.residual.document(),
            "candidates_generated": self.candidates_generated,
            "candidates_retained": self.candidates_retained,
            "maximum_members": self.maximum_members,
            "fitting_time_ms": self.elapsed_ms,
            "global_transform": None if self.global_transform is None else self.global_transform.document(),
            "bindings": [dict(binding.document()) for binding in self.bindings],
        }


class CausalEntityInducer:
    """Sparse transformation-bucket induction with a bounded competing beam."""

    def __init__(
        self, *, max_candidates: int = 8, max_members: int = 12,
        minimum_support: int = 2, relation_tolerance: float = 0.05,
        global_fraction: float = 0.8,
    ) -> None:
        self.max_candidates = max(1, int(max_candidates))
        self.max_members = max(2, int(max_members))
        self.minimum_support = max(1, int(minimum_support))
        self.relation_tolerance = float(relation_tolerance)
        self.global_fraction = float(global_fraction)
        self.hypotheses: dict[tuple[str, ...], _Hypothesis] = {}
        self._lineage_by_binding: dict[str, str] = {}
        self._turn = 0

    @staticmethod
    def _correspondence_residual(left: RegionBinding, right: RegionBinding) -> float:
        a, b = normalized_shape(left), normalized_shape(right)
        shape = len(a ^ b) / max(1, len(a | b))
        mass = abs(area(left) - area(right)) / max(1, area(left), area(right))
        ly, lx = centroid(left); ry, rx = centroid(right)
        position = min(1.0, (abs(ly - ry) + abs(lx - rx)) / max(2.0, math.sqrt(max(1, area(left)))))
        value = 0.0 if left.value == right.value else 0.15
        return 0.45 * shape + 0.25 * mass + 0.25 * position + 0.05 * value

    @staticmethod
    def _transform(left: RegionBinding, right: RegionBinding) -> TransformSignature:
        ly, lx = centroid(left); ry, rx = centroid(right)
        dy, dx = round(ry - ly, 4), round(rx - lx, 4)
        if occupied_cells(left) == occupied_cells(right) and left.value != right.value:
            delta = None if left.value is None or right.value is None else float(right.value - left.value)
            return TransformSignature("recolor", () if delta is None else (delta,))
        if area(left) == area(right) and normalized_shape(left) == normalized_shape(right):
            return TransformSignature("invariant" if dy == 0 and dx == 0 else "translation", (dy, dx))
        lb, rb = envelope(left), envelope(right)
        left_shape, right_shape = normalized_shape(left), normalized_shape(right)
        shape_residual = len(left_shape ^ right_shape) / max(1, len(left_shape | right_shape))
        if lb is not None and rb is not None and shape_residual <= 0.65:
            lh, lw = max(1.0, lb[2] - lb[0] + 1), max(1.0, lb[3] - lb[1] + 1)
            rh, rw = max(1.0, rb[2] - rb[0] + 1), max(1.0, rb[3] - rb[1] + 1)
            return TransformSignature("scale", (round(rh / lh, 4), round(rw / lw, 4)))
        return TransformSignature("deformation", (round(area(right) / max(1, area(left)), 4),))

    def correspond(self, before: Sequence[Any], after: Sequence[Any]) -> tuple[MemberTransition, ...]:
        sources = tuple(RegionBinding.from_value(item) for item in before if _as_mapping(item).get("kind") != "causal-entity-binding")
        successors = tuple(RegionBinding.from_value(item) for item in after if _as_mapping(item).get("kind") != "causal-entity-binding")
        by_transform: dict[TransformSignature, list[tuple[float, int, int]]] = defaultdict(list)
        for li, left in enumerate(sources):
            same_value_indices = [
                ri for ri, right in enumerate(successors) if right.value == left.value
            ]
            candidate_indices = same_value_indices or list(range(len(successors)))
            for ri in candidate_indices:
                right = successors[ri]
                residual = self._correspondence_residual(left, right)
                if residual <= 0.72:
                    by_transform[self._transform(left, right)].append((residual, li, ri))

        def compatible_count(values: Sequence[tuple[float, int, int]]) -> int:
            left_seen: set[int] = set(); right_seen: set[int] = set(); count = 0
            for _residual, li, ri in sorted(values):
                if li not in left_seen and ri not in right_seen:
                    left_seen.add(li); right_seen.add(ri); count += 1
            return count

        # Coherent transformation is itself correspondence evidence.  This
        # resolves repeated identical dots whose nearest-position assignment
        # would otherwise erase their common action-conditioned motion.
        transform_order = sorted(
            by_transform,
            key=lambda signature: (
                -compatible_count(by_transform[signature]),
                signature.kind == "deformation",
                sum(abs(value) for value in signature.parameters),
                signature.kind, signature.parameters,
            ),
        )
        used_left: set[int] = set(); used_right: set[int] = set(); output = []
        for signature in transform_order:
            for residual, li, ri in sorted(by_transform[signature]):
                if li in used_left or ri in used_right:
                    continue
                left, right = sources[li], successors[ri]
                lineage = self._lineage_by_binding.get(left.binding_id) or _stable_id(
                    "member-lineage", {"origin": left.binding_id, "shape": sorted(normalized_shape(left))},
                )
                self._lineage_by_binding[left.binding_id] = lineage
                self._lineage_by_binding[right.binding_id] = lineage
                output.append(MemberTransition(left, right, signature, round(residual, 6), lineage))
                used_left.add(li); used_right.add(ri)
        return tuple(output)

    @staticmethod
    def _internal_residual(transitions: Sequence[MemberTransition]) -> float:
        if len(transitions) < 2:
            return 0.0
        residuals = []
        for index, left in enumerate(transitions):
            ly0, lx0 = centroid(left.predecessor); ly1, lx1 = centroid(left.successor)
            for right in transitions[index + 1:]:
                ry0, rx0 = centroid(right.predecessor); ry1, rx1 = centroid(right.successor)
                before = (ry0 - ly0, rx0 - lx0); after = (ry1 - ly1, rx1 - lx1)
                scale = max(1.0, abs(before[0]) + abs(before[1]))
                residuals.append((abs(before[0] - after[0]) + abs(before[1] - after[1])) / scale)
        return sum(residuals) / max(1, len(residuals))

    @staticmethod
    def scope_residual(
        transitions: Sequence[MemberTransition], *, explained_binding_ids: Iterable[str] = (),
        predicted_changed_ids: Iterable[str] = (), predicted_invariant_ids: Iterable[str] = (),
        ambiguous_global_change: bool = False,
    ) -> CausalScopeResidual:
        changed = [item for item in transitions if item.changed]
        explained = set(str(item) for item in explained_binding_ids)
        predicted_changed = set(str(item) for item in predicted_changed_ids)
        predicted_invariant = set(str(item) for item in predicted_invariant_ids)
        explained_changed = [item for item in changed if item.predecessor.binding_id in explained]
        unexplained = [item for item in changed if item.predecessor.binding_id not in explained]
        groups: dict[TransformSignature, list[str]] = defaultdict(list)
        for item in changed:
            groups[item.signature].append(item.predecessor.binding_id)
        coherent = tuple(sorted(
            tuple(sorted(ids)) for ids in groups.values() if len(ids) >= 2
        ))
        changed_ids = {item.predecessor.binding_id for item in changed}
        return CausalScopeResidual(
            observed_changed_entities=len(changed),
            observed_changed_support=sum(area(item.predecessor) for item in changed),
            explained_changed_entities=len(explained_changed),
            explained_changed_support=sum(area(item.predecessor) for item in explained_changed),
            unexplained_changed_entities=len(unexplained),
            unexplained_changed_support=sum(area(item.predecessor) for item in unexplained),
            predicted_changed_observed=len(predicted_changed & changed_ids),
            predicted_changed_missing=len(predicted_changed - changed_ids),
            predicted_invariants_violated=len(predicted_invariant & changed_ids),
            coherent_unexplained_groups=coherent,
            ambiguous_global_change=ambiguous_global_change,
        )

    def _binding(self, hypothesis: _Hypothesis, transitions: Sequence[MemberTransition]) -> CausalEntityBinding | None:
        by_lineage = {item.lineage_id: item.successor for item in transitions}
        members = [by_lineage.get(lineage) for lineage in hypothesis.lineages]
        if any(member is None for member in members):
            hypothesis.identity_status = "AMBIGUOUS"
            return None
        realized = [member for member in members if member is not None]
        current_ids = tuple(member.binding_id for member in realized)
        hypothesis.current_member_ids = current_ids
        cells = tuple(sorted(set().union(*(occupied_cells(member) for member in realized))))
        binding_id = _stable_id("causal-entity-binding", {
            "entity": hypothesis.entity_id, "members": current_ids, "turn": self._turn,
        })
        return CausalEntityBinding(
            binding_id=binding_id, entity_id=hypothesis.entity_id, cells=cells,
            member_binding_ids=current_ids, primitive_member_ids=current_ids,
            transform=hypothesis.transform, status=hypothesis.status,
            identity_status=hypothesis.identity_status,
            support=len(hypothesis.support_evidence), contradictions=len(hypothesis.contradiction_evidence),
            evidence=tuple((*hypothesis.support_evidence, *hypothesis.contradiction_evidence)),
            internal_relation_residual=hypothesis.internal_relation_residual,
            member_values=tuple(member.value for member in realized),
            action_conditioned_transforms=tuple(
                (scope, tuple(sorted(transforms, key=lambda item: (item.kind, item.parameters))))
                for scope, transforms in sorted(hypothesis.action_transforms.items())
            ),
        )

    def observe_transition(
        self, before: Sequence[Any], after: Sequence[Any], *, action_scope: Any,
        evidence_ref: str, explained_binding_ids: Iterable[str] = (),
        predicted_changed_ids: Iterable[str] = (), predicted_invariant_ids: Iterable[str] = (),
        demand: bool = True,
    ) -> InductionResult:
        started = time.perf_counter(); self._turn += 1
        scope_key = str(action_scope)
        transitions = self.correspond(before, after)
        changed = [item for item in transitions if item.changed]
        buckets: dict[TransformSignature, list[MemberTransition]] = defaultdict(list)
        for item in changed:
            buckets[item.signature].append(item)
        largest = max((len(group) for group in buckets.values()), default=0)
        global_signature = None
        if len(transitions) >= 3 and largest / max(1, len(transitions)) >= self.global_fraction:
            global_signature = max(buckets, key=lambda signature: len(buckets[signature]))
        residual = self.scope_residual(
            transitions, explained_binding_ids=explained_binding_ids,
            predicted_changed_ids=predicted_changed_ids,
            predicted_invariant_ids=predicted_invariant_ids,
            ambiguous_global_change=global_signature is not None,
        )

        transition_by_lineage = {item.lineage_id: item for item in transitions}
        for hypothesis in self.hypotheses.values():
            evidence = [transition_by_lineage.get(lineage) for lineage in hypothesis.lineages]
            if any(item is None for item in evidence):
                hypothesis.identity_status = "AMBIGUOUS"
                continue
            members = [item for item in evidence if item is not None]
            # Entity identity is membership plus preserved internal relations.
            # The effect is conditional on the intervention scope: opposite
            # actions may move the same entity in opposite directions without
            # refuting its identity. State may condition an action's effect,
            # so only loss of within-transition coherence/member breakaway is
            # contradictory identity evidence.
            observed_signatures = {item.signature for item in members}
            observed_transform = next(iter(observed_signatures)) if len(observed_signatures) == 1 else None
            coherent = observed_transform is not None
            relation_residual = self._internal_residual(members)
            citation = _stable_id("cae-settlement", {
                "basis": evidence_ref, "entity": hypothesis.entity_id,
                "action_scope": scope_key,
                "transforms": [item.signature.document() for item in members],
            })
            if coherent and relation_residual <= self.relation_tolerance:
                if citation not in hypothesis.support_evidence:
                    hypothesis.support_evidence.append(citation)
                hypothesis.identity_status = "UNIQUE" if len(hypothesis.support_evidence) >= self.minimum_support else "OPEN"
                hypothesis.transform = observed_transform
                hypothesis.action_transforms.setdefault(scope_key, set()).add(observed_transform)
                hypothesis.current_member_ids = tuple(item.successor.binding_id for item in members)
                hypothesis.internal_relation_residual = relation_residual
            else:
                if citation not in hypothesis.contradiction_evidence:
                    hypothesis.contradiction_evidence.append(citation)
                hypothesis.identity_status = "BROKEN"
            hypothesis.last_seen = self._turn

        generated = 0
        if demand and residual.accommodation_required and global_signature is None:
            explained = set(str(item) for item in explained_binding_ids)
            for signature, group in sorted(buckets.items(), key=lambda item: (-len(item[1]), item[0].kind, item[0].parameters)):
                # Include the locally explained member when it shares the same
                # transform: accommodation lifts the whole causal scope, not
                # merely the leftover fragments.
                if len(group) < 2 or len(group) > self.max_members:
                    continue
                if (
                    not any(item.predecessor.binding_id not in explained for item in group)
                    and residual.predicted_changed_missing == 0
                    and residual.predicted_invariants_violated == 0
                ):
                    continue
                relation_residual = self._internal_residual(group)
                if relation_residual > self.relation_tolerance:
                    continue
                lineages = tuple(sorted(item.lineage_id for item in group))
                generated += 1
                citation = _stable_id("cae-settlement", {
                    "basis": evidence_ref, "action_scope": str(action_scope),
                    "lineages": lineages, "transform": signature.document(),
                })
                hypothesis = self.hypotheses.get(lineages)
                if hypothesis is None:
                    hypothesis = _Hypothesis(
                        entity_id=_stable_id("causal-entity", {"origin_diagram": lineages}),
                        lineages=lineages,
                        current_member_ids=tuple(item.successor.binding_id for item in group),
                        primitive_member_ids=tuple(item.successor.binding_id for item in group),
                        transform=signature,
                        support_evidence=[citation],
                        internal_relation_residual=relation_residual,
                        identity_status="OPEN",
                        last_seen=self._turn,
                        minimum_support=self.minimum_support,
                        action_transforms={scope_key: {signature}},
                    )
                    self.hypotheses[lineages] = hypothesis

        ordered = sorted(
            self.hypotheses.values(),
            key=lambda item: (
                item.status != "SUPPORTED", item.status == "REFUTED",
                len(item.contradiction_evidence), -len(item.support_evidence),
                len(item.lineages), item.entity_id,
            ),
        )[:self.max_candidates]
        bindings = tuple(binding for item in ordered if (binding := self._binding(item, transitions)) is not None)
        return InductionResult(
            residual=residual, candidates_generated=generated,
            candidates_retained=len(ordered),
            maximum_members=max((len(item.lineages) for item in ordered), default=0),
            elapsed_ms=round((time.perf_counter() - started) * 1000.0, 3),
            global_transform=global_signature, bindings=bindings,
        )

    def supported_bindings(self) -> tuple[_Hypothesis, ...]:
        return tuple(item for item in self.hypotheses.values() if item.status == "SUPPORTED" and item.identity_status == "UNIQUE")

    def remap_bindings(self, aliases: Mapping[str, str]) -> None:
        """Replace provisional successor IDs with fitted workspace atom IDs."""
        for old, new in aliases.items():
            lineage = self._lineage_by_binding.get(str(old))
            if lineage is not None:
                self._lineage_by_binding[str(new)] = lineage
        for hypothesis in self.hypotheses.values():
            hypothesis.current_member_ids = tuple(
                str(aliases.get(member, member)) for member in hypothesis.current_member_ids
            )

    def reset_situated(self) -> None:
        self.hypotheses.clear(); self._lineage_by_binding.clear(); self._turn = 0


def fit_residual(actor: Any, target: Any) -> float:
    """Generic FIT potential over any two SpatialEntity implementations."""
    actor_cells, target_cells = occupied_cells(actor), occupied_cells(target)
    if not actor_cells or not target_cells:
        return math.inf
    gap = max(0.0, min(abs(ay - ty) + abs(ax - tx) for ay, ax in actor_cells for ty, tx in target_cells) - 1.0)
    overlap_deficit = min(len(actor_cells), len(target_cells)) - len(actor_cells & target_cells)
    return float(gap + overlap_deficit)


def causal_coverage_for(entity: Any, supported: Sequence[CausalEntityBinding]) -> float:
    raw = _as_mapping(entity)
    binding_id = str(raw.get("binding_id", ""))
    if raw.get("kind") == "causal-entity-binding" and raw.get("epistemic_status") == "SUPPORTED":
        return 1.0
    containing = [item for item in supported if binding_id in item.primitive_member_ids and item.status == "SUPPORTED"]
    if not containing:
        return 1.0
    return max(1.0 / max(1, len(item.primitive_member_ids)) for item in containing)


__all__ = [
    "CAE_PROTOCOL", "CausalEntityBinding", "CausalEntityInducer",
    "CausalScopeResidual", "InductionResult", "MemberTransition", "RegionBinding",
    "SpatialEntity", "TransformSignature", "area", "boundary", "causal_coverage_for",
    "centroid", "envelope", "fit_residual", "normalized_shape", "occupied_cells", "topology",
]
