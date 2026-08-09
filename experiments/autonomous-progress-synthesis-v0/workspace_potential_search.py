"""Turn support-zero workspace goals into conservative search attention.

This module deliberately does not choose actions and does not change empirical
support.  It compiles a situated goal once, follows its visual roles through
later observations, and supplies a priority tuple to reset/replay search.  If
correspondence alternatives disagree about the potential, the value is
unknown rather than silently selecting a convenient grounding.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
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
class RolePattern:
    width: int
    height: int
    area: int
    components: tuple[tuple[int, int, RoleSignature], ...]


@dataclass(frozen=True, slots=True)
class WorkspacePotential:
    proposal_id: str
    family: str
    potential: str
    terminal: str
    controlled: RolePattern
    members: tuple[RolePattern, ...]
    container: RolePattern | None
    empirical_support: int = 0


@dataclass(frozen=True, slots=True)
class PotentialReading:
    proposal_id: str
    value: int | None
    correspondence_count: int
    reason: str


@dataclass(slots=True)
class GoalAttentionRecord:
    proposal_id: str
    empirical_support: int = 0
    attention: int = 0
    status: str = "active"
    evaluations: int = 0
    known_evaluations: int = 0
    best_value: int | None = None
    reference_value: int | None = None
    evaluations_since_improvement: int = 0
    environment_refutations: int = 0
    attention_suppressions: int = 0
    last_reason: str = "untried"


def _region(scene: PS.Scene, region_id: str) -> PS.Region:
    match = next((item for item in scene.regions if item.region_id == region_id), None)
    if match is None:
        raise WorkspacePotentialError(f"grounded role is not visible: {region_id}")
    return match


def _signature(region: PS.Region) -> RolePattern:
    component = RoleSignature(region.width, region.height, region.normalized)
    return RolePattern(region.width, region.height, region.area, ((0, 0, component),))


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


def _descriptor_pattern(row: Mapping[str, Any], scene: PS.Scene) -> RolePattern:
    try:
        x, y = map(int, row["origin"]); width, height = map(int, row["size"]); area = int(row["area"])
    except (KeyError, TypeError, ValueError) as error:
        raise WorkspacePotentialError("workspace entity lacks bounded visual grounding") from error
    exact = [item for item in scene.regions if (item.x, item.y, item.width, item.height, item.area) == (x, y, width, height, area)]
    if len(exact) == 1:
        return _signature(exact[0])
    eligible = [item for item in scene.regions if x <= item.x and y <= item.y and item.x + item.width <= x + width and item.y + item.height <= y + height]
    # Find the smallest non-overlapping component cover.  This binds compound
    # objects such as multicolour sprites without placing palette information
    # in the transferable role description.
    from itertools import combinations
    target_bounds = {(xx, yy) for yy in range(y, y + height) for xx in range(x, x + width)}
    covers = []
    for count in range(2, min(8, len(eligible)) + 1):
        for group in combinations(eligible, count):
            union = set().union(*(set(item.cells) for item in group))
            if len(union) != sum(item.area for item in group) or len(union) != area or not union <= target_bounds:
                continue
            xs, ys = zip(*union)
            if (min(xs), min(ys), max(xs) - min(xs) + 1, max(ys) - min(ys) + 1) != (x, y, width, height):
                continue
            components = tuple(sorted((item.x - x, item.y - y, RoleSignature(item.width, item.height, item.normalized)) for item in group))
            covers.append(RolePattern(width, height, area, components))
        if covers:
            break
    if len(covers) != 1:
        raise WorkspacePotentialError("workspace entity has no unique component grounding")
    return covers[0]


def compile_rendered_goal(goal: Mapping[str, Any], workspace: Mapping[str, Any], initial: Sequence[Sequence[int]], *, proposal_id: str = "workspace:goal") -> WorkspacePotential:
    """Compile aliases from the compact Qwen view back to pixel patterns."""
    required = {"family", "controlled_id", "members", "container_id", "potential", "terminal", "interaction_candidate", "rationale"}
    if set(goal) != required:
        raise WorkspacePotentialError("live goal fields do not match the closed contract")
    family = str(goal["family"])
    if family not in FAMILY_CONTRACTS or (goal["potential"], goal["terminal"]) != FAMILY_CONTRACTS[family]:
        raise WorkspacePotentialError("goal family and potential contract disagree")
    rows = {str(item["id"]): item for item in workspace.get("entities", ())}
    controlled_id = str(goal["controlled_id"]); members = tuple(map(str, goal["members"])); container_id = goal["container_id"]
    ids = (controlled_id,) + members + (() if container_id is None else (str(container_id),))
    if not members or len(ids) != len(set(ids)) or any(item not in rows for item in ids):
        raise WorkspacePotentialError("rendered role grounding is invalid")
    scene = PS.perceive(initial)
    return WorkspacePotential(
        proposal_id=str(proposal_id), family=family, potential=str(goal["potential"]), terminal=str(goal["terminal"]),
        controlled=_descriptor_pattern(rows[controlled_id], scene),
        members=tuple(_descriptor_pattern(rows[item], scene) for item in members),
        container=None if container_id is None else _descriptor_pattern(rows[str(container_id)], scene),
        empirical_support=0,
    )


def _matches(pattern: RolePattern, scene: PS.Scene) -> tuple[PS.Region, ...]:
    if len(pattern.components) == 1 and pattern.components[0][:2] == (0, 0):
        signature = pattern.components[0][2]
        return tuple(item for item in scene.regions if (item.width, item.height, item.normalized) == (signature.width, signature.height, signature.normalized))
    by_shape_position = {}
    for item in scene.regions:
        key = (item.x, item.y, item.width, item.height, item.normalized)
        by_shape_position.setdefault(key, []).append(item)
    anchors = set()
    first_dx, first_dy, first_signature = pattern.components[0]
    for item in scene.regions:
        if (item.width, item.height, item.normalized) == (first_signature.width, first_signature.height, first_signature.normalized):
            anchors.add((item.x - first_dx, item.y - first_dy))
    rows = []
    for x, y in sorted(anchors):
        components = []
        for dx, dy, signature in pattern.components:
            matches = by_shape_position.get((x + dx, y + dy, signature.width, signature.height, signature.normalized), ())
            if len(matches) != 1:
                components = []; break
            components.append(matches[0])
        if not components or len({item.region_id for item in components}) != len(components):
            continue
        cells = frozenset().union(*(item.cells for item in components))
        if len(cells) != pattern.area:
            continue
        identity = {"compound": [item.region_id for item in components], "anchor": [x, y]}
        rows.append(PS.Region("compound:" + PS.stable_hash(identity)[:20], x, y, pattern.width, pattern.height, cells, -1))
    return tuple(rows)


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


def search_priority(goals: Sequence[WorkspacePotential], *, projection=lambda observation: observation):
    """Return a deterministic attention-only priority callback for search."""
    frozen = tuple(goals)
    def priority(observation, path, _source_key, _target_key):
        rendered = projection(observation)
        readings = tuple(evaluate(goal, rendered) for goal in frozen)
        known = tuple(row.value for row in readings if row.value is not None)
        # Unknown hypotheses cannot outrank grounded ones.  Neither support nor
        # completion is inferred here; the environment retains both powers.
        return (0, min(known), len(path)) if known else (1, len(path))
    return priority


class AdaptivePotentialPolicy:
    """Test support-zero goals without letting a proxy monopolize search.

    The search callback is invoked only for nonterminal, non-complete successor
    states.  Therefore observing a claimed lower bound there is direct
    environment evidence against the goal's terminal equivalence.  Plateaus
    merely suppress attention; they do not change empirical support.
    """
    def __init__(self, goals: Sequence[WorkspacePotential], *, projection=lambda observation: observation, plateau_patience: int = 12, reference_values: Mapping[str, int] | None = None, attention_boosts: Mapping[str, int] | None = None):
        if plateau_patience < 1:
            raise WorkspacePotentialError("plateau patience must be positive")
        self.goals = tuple(goals); self.projection = projection; self.plateau_patience = int(plateau_patience)
        references = {} if reference_values is None else {str(key): int(value) for key, value in reference_values.items()}
        boosts = {} if attention_boosts is None else {str(key): int(value) for key, value in attention_boosts.items()}
        self._records = {goal.proposal_id: GoalAttentionRecord(goal.proposal_id, attention=boosts.get(goal.proposal_id, 0), reference_value=references.get(goal.proposal_id)) for goal in self.goals}

    def observe_noncompletion(self, readings: Sequence[PotentialReading]) -> tuple[Any, ...] | None:
        ranked = []; improved = {}
        for reading in readings:
            record = self._records[reading.proposal_id]; record.evaluations += 1; record.last_reason = reading.reason
            if record.status != "active" or reading.value is None:
                continue
            record.known_evaluations += 1
            if reading.value == 0:
                # The proposal explicitly claimed value==lower_bound as its
                # terminal predicate, while reality just said not complete.
                record.status = "refuted-terminal-proxy"; record.empirical_support -= 1
                record.environment_refutations += 1; record.last_reason = "lower-bound-without-environment-completion"
                continue
            if record.reference_value is None:
                record.reference_value = reading.value
            if record.best_value is None or reading.value < record.best_value:
                record.best_value = reading.value; record.evaluations_since_improvement = 0
                improved[reading.proposal_id] = True
            else:
                improved[reading.proposal_id] = False
            ranked.append((Fraction(reading.value, max(1, record.reference_value)), -record.attention, reading.correspondence_count, reading.proposal_id))
        if not ranked:
            return None
        selected = min(ranked)
        record = self._records[selected[-1]]
        # Only the hypothesis winning attention for this successor spends its
        # plateau patience. Other hypotheses may learn incidental new minima,
        # but are not exhausted by an experiment selected for somebody else.
        if not improved[selected[-1]]:
            record.evaluations_since_improvement += 1
            if record.evaluations_since_improvement >= self.plateau_patience:
                record.status = "attention-suppressed-plateau"; record.attention_suppressions += 1
                record.last_reason = "no-new-minimum-within-patience"
                remaining = [row for row in ranked if row[-1] != selected[-1]]
                return min(remaining, default=None)
        return selected

    def __call__(self, observation, path, _source_key, _target_key):
        rendered = self.projection(observation)
        readings = tuple(evaluate(goal, rendered) for goal in self.goals)
        selected = self.observe_noncompletion(readings)
        return (0,) + selected + (len(path),) if selected is not None else (1, len(path))

    def records(self) -> tuple[GoalAttentionRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))


__all__ = [
    "AdaptivePotentialPolicy", "FAMILY_CONTRACTS", "GoalAttentionRecord", "PotentialReading", "RolePattern", "RoleSignature", "WorkspacePotential",
    "WorkspacePotentialError", "compile_live_goal", "compile_rendered_goal", "evaluate", "search_priority",
]
