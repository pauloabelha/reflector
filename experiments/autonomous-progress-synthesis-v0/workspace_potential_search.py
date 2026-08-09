"""Turn support-zero workspace goals into conservative search attention.

This module deliberately does not choose actions and does not change empirical
support.  It compiles a situated goal once, follows its visual roles through
later observations, and supplies a priority tuple to reset/replay search.  If
correspondence alternatives disagree about the potential, the value is
unknown rather than silently selecting a convenient grounding.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Any, Mapping, Sequence

import progress_synthesis as PS


class WorkspacePotentialError(ValueError):
    pass


FAMILY_CONTRACTS = {
    "matching": ("MismatchCount", "AllMatched"),
    "alignment": ("AlignmentResidual", "Aligned"),
    "collection_containment": ("OutsideCount", "AllInside"),
    "connectivity": ("ComponentDeficit", "Connected"),
    "avoidance": ("CollisionRisk", "NoCollision"),
    "transformation": ("TransformationResidual", "TransformationComplete"),
}


@dataclass(frozen=True, slots=True)
class RoleSignature:
    width: int
    height: int
    normalized: frozenset[PS.Point]


@dataclass(frozen=True, slots=True)
class WorkspacePotential:
    proposal_id: str
    family: str
    potential: str
    terminal: str
    controlled: RoleSignature
    members: tuple[RoleSignature, ...]
    container: RoleSignature | None
    empirical_support: int = 0


@dataclass(frozen=True, slots=True)
class PotentialReading:
    proposal_id: str
    value: int | None
    correspondence_count: int
    reason: str


def _region(scene: PS.Scene, region_id: str) -> PS.Region:
    match = next((item for item in scene.regions if item.region_id == region_id), None)
    if match is None:
        raise WorkspacePotentialError(f"grounded role is not visible: {region_id}")
    return match


def _signature(region: PS.Region) -> RoleSignature:
    return RoleSignature(region.width, region.height, region.normalized)


def compile_live_goal(goal: Mapping[str, Any], initial: Sequence[Sequence[int]], *, proposal_id: str = "workspace:goal") -> WorkspacePotential:
    """Compile the existing live-Qwen goal contract without granting authority."""
    required = {"family", "controlled_id", "members", "container_id", "potential", "terminal", "interaction_candidate", "rationale"}
    if set(goal) != required:
        raise WorkspacePotentialError("live goal fields do not match the closed contract")
    family = str(goal["family"])
    if family not in FAMILY_CONTRACTS or (goal["potential"], goal["terminal"]) != FAMILY_CONTRACTS[family]:
        raise WorkspacePotentialError("goal family and potential contract disagree")
    members = tuple(map(str, goal["members"]))
    if not members or len(members) != len(set(members)):
        raise WorkspacePotentialError("member grounding must be a nonempty set")
    controlled_id = str(goal["controlled_id"])
    container_id = None if goal["container_id"] is None else str(goal["container_id"])
    grounded = (controlled_id,) + members + (() if container_id is None else (container_id,))
    if len(grounded) != len(set(grounded)):
        raise WorkspacePotentialError("situated roles must be distinct")
    scene = PS.perceive(initial)
    return WorkspacePotential(
        proposal_id=str(proposal_id), family=family, potential=str(goal["potential"]), terminal=str(goal["terminal"]),
        controlled=_signature(_region(scene, controlled_id)),
        members=tuple(_signature(_region(scene, item)) for item in members),
        container=None if container_id is None else _signature(_region(scene, container_id)),
        empirical_support=0,
    )


def _matches(signature: RoleSignature, scene: PS.Scene) -> tuple[PS.Region, ...]:
    return tuple(item for item in scene.regions if (item.width, item.height, item.normalized) == (signature.width, signature.height, signature.normalized))


def _assignments(goal: WorkspacePotential, scene: PS.Scene, *, limit: int = 256):
    signatures = (goal.controlled,) + goal.members + (() if goal.container is None else (goal.container,))
    domains = [_matches(signature, scene) for signature in signatures]
    if any(not domain for domain in domains):
        return ()
    # Product is bounded before materialization.  Repeated visual signatures
    # are legitimate competing correspondences, never arbitrarily collapsed.
    cardinality = 1
    for domain in domains:
        cardinality *= len(domain)
        if cardinality > limit:
            return ()
    rows = []
    for assignment in product(*domains):
        if len({item.region_id for item in assignment}) != len(assignment):
            continue
        rows.append(assignment)
    return tuple(rows)


def _inside(member: PS.Region, container: PS.Region) -> bool:
    # Full observed-mask containment is the conservative AllInside semantics.
    bounds = set((x, y) for y in range(container.y, container.y + container.height) for x in range(container.x, container.x + container.width))
    return bool(member.cells) and member.cells <= bounds


def _alignment(left: PS.Region, right: PS.Region) -> int:
    return abs((left.x * 2 + left.width) - (right.x * 2 + right.width)) + abs((left.y * 2 + left.height) - (right.y * 2 + right.height))


def _mask_mismatch(left: PS.Region, right: PS.Region) -> int:
    scale = max(left.width, right.width, left.height, right.height)
    def sample(region: PS.Region):
        return {(round(x * (scale - 1) / max(1, region.width - 1)), round(y * (scale - 1) / max(1, region.height - 1))) for x, y in region.normalized}
    return len(sample(left) ^ sample(right))


def _connected_component_deficit(regions: Sequence[PS.Region]) -> int:
    cells = set().union(*(set(item.cells) for item in regions))
    components = 0
    while cells:
        components += 1
        frontier = [cells.pop()]
        while frontier:
            x, y = frontier.pop()
            for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if point in cells:
                    cells.remove(point); frontier.append(point)
    return max(0, components - 1)


def _value(goal: WorkspacePotential, assignment: Sequence[PS.Region]) -> int | None:
    controlled = assignment[0]
    members = tuple(assignment[1:1 + len(goal.members)])
    container = None if goal.container is None else assignment[-1]
    if goal.potential == "MismatchCount":
        return sum(_mask_mismatch(controlled, member) for member in members)
    if goal.potential == "AlignmentResidual":
        targets = members + (() if container is None else (container,))
        return min((_alignment(controlled, target) for target in targets), default=None)
    if goal.potential == "OutsideCount":
        if container is None:
            return None
        return sum(not _inside(member, container) for member in members)
    if goal.potential == "ComponentDeficit":
        return _connected_component_deficit((controlled,) + members)
    if goal.potential == "CollisionRisk":
        hazards = members + (() if container is None else (container,))
        return sum(bool(controlled.cells & hazard.cells) for hazard in hazards)
    if goal.potential == "TransformationResidual":
        return min((_mask_mismatch(controlled, member) for member in members), default=None)
    return None


def evaluate(goal: WorkspacePotential, observation: Sequence[Sequence[int]]) -> PotentialReading:
    scene = PS.perceive(observation)
    assignments = _assignments(goal, scene)
    if not assignments:
        return PotentialReading(goal.proposal_id, None, 0, "ungrounded-or-overflow")
    values = {_value(goal, assignment) for assignment in assignments}
    if None in values or len(values) != 1:
        return PotentialReading(goal.proposal_id, None, len(assignments), "competing-correspondences-disagree")
    return PotentialReading(goal.proposal_id, values.pop(), len(assignments), "grounded-agreement")


def search_priority(goals: Sequence[WorkspacePotential]):
    """Return a deterministic attention-only priority callback for search."""
    frozen = tuple(goals)
    def priority(observation, path, _source_key, _target_key):
        readings = tuple(evaluate(goal, observation) for goal in frozen)
        known = tuple(row.value for row in readings if row.value is not None)
        # Unknown hypotheses cannot outrank grounded ones.  Neither support nor
        # completion is inferred here; the environment retains both powers.
        return (0, min(known), len(path)) if known else (1, len(path))
    return priority


__all__ = [
    "FAMILY_CONTRACTS", "PotentialReading", "RoleSignature", "WorkspacePotential",
    "WorkspacePotentialError", "compile_live_goal", "evaluate", "search_priority",
]
