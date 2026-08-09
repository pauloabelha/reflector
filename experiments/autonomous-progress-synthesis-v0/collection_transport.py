"""Generic collection/transport capability induction and gated execution.

Situated roles and opaque motor meanings are inferred only from observations.
Unresolved roles/actions remain explicit OPEN ports.  Structural induction can
raise attention, never support; only addressed, direct environment evidence
can authorize execution of the transport goal.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
import importlib.util
from pathlib import Path
import sys
from typing import Any, Hashable, Mapping, Sequence

import progress_synthesis as synthesis


HERE = Path(__file__).resolve().parent
EXPERIMENTS = HERE.parent
OPEN = "OPEN"


def _load(name: str, path: Path) -> Any:
    resolved = path.resolve()
    for module in reversed(tuple(sys.modules.values())):
        source = getattr(module, "__file__", None)
        if source is not None and Path(source).resolve() == resolved:
            return module
    spec = importlib.util.spec_from_file_location(name, resolved)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {resolved}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


GOAL = _load(
    "autonomous_collection_goal_workspace",
    EXPERIMENTS / "progress-goal-intervention-v0" / "goal_workspace.py",
)
TRANSPORT = _load(
    "autonomous_collection_transport_planner",
    EXPERIMENTS / "progress-goal-intervention-v0" / "transport_goal.py",
)


class CollectionCapabilityError(ValueError):
    """The observational capability or requested execution is invalid."""


@dataclass(frozen=True, slots=True)
class CalibrationTransition:
    opaque_action: Hashable
    after: Sequence[Sequence[int]]
    evidence_id: str
    direct: bool = True
    interaction_effect: str | None = None


@dataclass(frozen=True, slots=True)
class MotionModel:
    delta: tuple[int, int]
    opaque_action: Hashable
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RoleAlternative:
    actor_id: str
    member_ids: tuple[str, ...]
    container_id: str


@dataclass(frozen=True, slots=True)
class RoleGrounding:
    actor_id: str | None
    member_ids: tuple[str, ...] | None
    container_id: str | None
    alternatives: tuple[RoleAlternative, ...]

    @property
    def complete(self) -> bool:
        return (
            self.actor_id is not None
            and self.member_ids is not None
            and self.container_id is not None
            and len(self.alternatives) == 1
        )


@dataclass(frozen=True, slots=True)
class CollectionCapability:
    candidate: Any
    binding_id: str
    observation_id: str
    grounding: RoleGrounding
    motion_models: tuple[MotionModel, ...]
    interaction_action: Hashable | None
    interaction_candidates: tuple[Hashable, ...]
    interaction_evidence_ids: tuple[str, ...]
    initial_grid: tuple[tuple[int, ...], ...]
    attention: int
    empirical_support: int = 0
    goal_evidence_ids: tuple[str, ...] = ()
    evidence_objects: tuple[Mapping[str, Any], ...] = ()

    @property
    def open_ports(self) -> tuple[str, ...]:
        ports = []
        if self.grounding.actor_id is None:
            ports.append("?actor")
        if self.grounding.member_ids is None:
            ports.append("?members")
        if self.grounding.container_id is None:
            ports.append("?container")
        if self.interaction_action is None:
            ports.append("?interaction")
        return tuple(ports)


@dataclass(frozen=True, slots=True)
class GoalProgressEvidence:
    candidate_id: str
    binding_id: str
    evidence_id: str
    before: int
    after: int
    direct: bool
    created_by: str = "environment"


def _grid(raw: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    grid = tuple(tuple(int(value) for value in row) for row in raw)
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise CollectionCapabilityError("observation must be a rectangular grid")
    return grid


def _signature(region: Any) -> tuple[int, int, frozenset[tuple[int, int]]]:
    return region.width, region.height, region.normalized


def _regions_by_signature(scene: Any) -> dict[Any, list[Any]]:
    output: dict[Any, list[Any]] = defaultdict(list)
    for region in scene.regions:
        output[_signature(region)].append(region)
    return output


def _observed_translations(
    before_scene: Any,
    after_scene: Any,
) -> tuple[tuple[str, tuple[int, int]], ...]:
    """Find exact one-out/one-in translations within perceptual classes."""

    before_groups = _regions_by_signature(before_scene)
    after_groups = _regions_by_signature(after_scene)
    rows = []
    for signature, before_regions in before_groups.items():
        after_regions = after_groups.get(signature, ())
        before_at = {(item.x, item.y): item for item in before_regions}
        after_at = {(item.x, item.y): item for item in after_regions}
        removed = sorted(set(before_at) - set(after_at), key=lambda point: (point[1], point[0]))
        added = sorted(set(after_at) - set(before_at), key=lambda point: (point[1], point[0]))
        if len(removed) != 1 or len(added) != 1:
            continue
        source, target = removed[0], added[0]
        delta = (target[1] - source[1], target[0] - source[0])  # row, column
        if delta != (0, 0):
            rows.append((before_at[source].region_id, delta))
    return tuple(sorted(rows))


def _role_alternatives(scene: Any) -> tuple[RoleAlternative, ...]:
    """Enumerate actor/member/container roles from equivalence and capacity."""

    groups = _regions_by_signature(scene)
    alternatives = set()
    for signature, peers in groups.items():
        item_width, item_height, _mask = signature
        if len(peers) < 2 or item_width < 1 or item_height < 1:
            continue
        peer_ids = {item.region_id for item in peers}
        for container in scene.regions:
            if container.region_id in peer_ids:
                continue
            if container.width % item_width or container.height % item_height:
                continue
            capacity = (container.width // item_width) * (container.height // item_height)
            if capacity != len(peers) - 1:
                continue
            for actor in peers:
                members = tuple(sorted(item.region_id for item in peers if item is not actor))
                alternatives.add((actor.region_id, members, container.region_id))
    return tuple(
        RoleAlternative(actor, members, container)
        for actor, members, container in sorted(alternatives)
    )


def _grounding(alternatives: Sequence[RoleAlternative]) -> RoleGrounding:
    rows = tuple(alternatives)
    actors = {row.actor_id for row in rows}
    members = {row.member_ids for row in rows}
    containers = {row.container_id for row in rows}
    return RoleGrounding(
        next(iter(actors)) if len(actors) == 1 else None,
        next(iter(members)) if len(members) == 1 else None,
        next(iter(containers)) if len(containers) == 1 else None,
        rows,
    )


def induce_collection_capability(
    initial: Sequence[Sequence[int]],
    transitions: Sequence[CalibrationTransition],
    *,
    observation_id: str | None = None,
) -> CollectionCapability | None:
    """Induce one bounded collection capability or return no hypothesis.

    A direct visual translation may resolve the actor port.  A no-motion action
    remains only an interaction candidate unless its transition carries an
    independently observed ``pickup``, ``drop``, or ``carry-start`` effect.
    """

    grid = _grid(initial)
    scene = synthesis.perceive(grid)
    alternatives = list(_role_alternatives(scene))
    if not alternatives:
        return None

    actor_votes: dict[str, int] = defaultdict(int)
    motor_rows: dict[tuple[tuple[int, int], Hashable], list[str]] = defaultdict(list)
    no_motion: list[Hashable] = []
    interactions: dict[Hashable, list[str]] = defaultdict(list)
    allowed_effects = {"pickup", "drop", "carry-start"}
    for transition in transitions:
        if not transition.direct:
            continue
        if not transition.evidence_id:
            raise CollectionCapabilityError("direct calibration requires an evidence ID")
        after_scene = synthesis.perceive(_grid(transition.after))
        translations = _observed_translations(scene, after_scene)
        if len(translations) == 1:
            actor_id, delta = translations[0]
            actor_votes[actor_id] += 1
            motor_rows[(delta, transition.opaque_action)].append(transition.evidence_id)
        else:
            no_motion.append(transition.opaque_action)
        if transition.interaction_effect is not None:
            if transition.interaction_effect not in allowed_effects:
                raise CollectionCapabilityError("unknown observed interaction effect")
            interactions[transition.opaque_action].append(transition.evidence_id)

    if actor_votes:
        maximum = max(actor_votes.values())
        observed_actors = {actor for actor, votes in actor_votes.items() if votes == maximum}
        alternatives = [row for row in alternatives if row.actor_id in observed_actors]
        if not alternatives:
            return None

    # Conflicting actions for the same delta remain unmodeled rather than being
    # resolved by action identity or ordering.
    actions_by_delta: dict[tuple[int, int], set[Hashable]] = defaultdict(set)
    for delta, action in motor_rows:
        actions_by_delta[delta].add(action)
    models = tuple(
        MotionModel(delta, next(iter(actions)), tuple(sorted(motor_rows[(delta, next(iter(actions)))])))
        for delta, actions in sorted(actions_by_delta.items())
        if len(actions) == 1
    )
    interaction_action = next(iter(interactions)) if len(interactions) == 1 else None
    interaction_evidence = (
        tuple(sorted(interactions[interaction_action]))
        if interaction_action is not None
        else ()
    )
    candidates = tuple(sorted(set(no_motion), key=repr))
    grounding = _grounding(alternatives)
    candidate = GOAL.make_candidate(provenance="self_built")
    obs_id = observation_id or f"obs:{GOAL.stable_hash(grid)}"
    if grounding.complete:
        situated = GOAL.make_binding(
            candidate,
            observation_id=obs_id,
            members=grounding.member_ids,
            container=grounding.container_id,
        )
        binding_id = situated.binding_id
    else:
        identity = {
            "candidate_id": candidate.candidate_id,
            "observation_id": obs_id,
            "alternatives": [
                [row.actor_id, list(row.member_ids), row.container_id]
                for row in grounding.alternatives
            ],
        }
        binding_id = f"gpb:{GOAL.stable_hash(identity)}"
    attention = min(95, 45 + 5 * len(models) + (15 if grounding.complete else 0))
    return CollectionCapability(
        candidate=candidate,
        binding_id=binding_id,
        observation_id=obs_id,
        grounding=grounding,
        motion_models=models,
        interaction_action=interaction_action,
        interaction_candidates=candidates,
        interaction_evidence_ids=interaction_evidence,
        initial_grid=grid,
        attention=attention,
    )


def workspace_document(capability: CollectionCapability) -> dict[str, Any]:
    """Render the shared-workspace view without leaking motor semantics."""

    grounding = capability.grounding
    actor_candidates = sorted({row.actor_id for row in grounding.alternatives})
    member_candidates = sorted({row.member_ids for row in grounding.alternatives})
    container_candidates = sorted({row.container_id for row in grounding.alternatives})

    def port(value: Any, candidates: Any) -> dict[str, Any]:
        return (
            {"status": "bound", "value": value}
            if value is not None
            else {"status": OPEN, "candidates": candidates}
        )

    return {
        "kind": "collection_transport_capability",
        "created_by": "self_built",
        "identity": {
            "candidate_id": capability.candidate.candidate_id,
            "binding_id": capability.binding_id,
        },
        "payload": {
            "goal_ast": dict(capability.candidate.ast),
            "ports": {
                "?actor": port(grounding.actor_id, actor_candidates),
                "?members": port(grounding.member_ids, member_candidates),
                "?container": port(grounding.container_id, container_candidates),
                "?interaction": {
                    "status": "bound" if capability.interaction_action is not None else OPEN,
                    "candidate_count": len(capability.interaction_candidates),
                },
            },
            "motion_model_count": len(capability.motion_models),
            "motion_evidence_ids": sorted(
                {value for model in capability.motion_models for value in model.evidence_ids}
            ),
            "interaction_evidence_ids": list(capability.interaction_evidence_ids),
            "attention": capability.attention,
            "empirical_support": capability.empirical_support,
            "goal_evidence_ids": list(capability.goal_evidence_ids),
            "authority": "environment-evidence-only",
        },
        "dependency_ids": [capability.observation_id, *capability.goal_evidence_ids],
    }


def adjudicate_goal_evidence(
    capability: CollectionCapability,
    evidence: GoalProgressEvidence,
) -> CollectionCapability:
    if evidence.candidate_id != capability.candidate.candidate_id or evidence.binding_id != capability.binding_id:
        raise CollectionCapabilityError("evidence addresses another capability")
    if evidence.created_by != "environment":
        raise CollectionCapabilityError("only environment may adjudicate goal support")
    if evidence.evidence_id in capability.goal_evidence_ids:
        raise CollectionCapabilityError("duplicate goal evidence")
    if not evidence.direct:
        return capability
    delta = evidence.before - evidence.after
    support_delta = 10 if delta > 0 else -3 if delta < 0 else 0
    if support_delta == 0:
        return replace(
            capability,
            goal_evidence_ids=capability.goal_evidence_ids + (evidence.evidence_id,),
        )
    evidence_object = GOAL.environment_support_object(
        candidate_id=capability.candidate.candidate_id,
        binding_id=capability.binding_id,
        evidence_ids=(evidence.evidence_id,),
        support_delta=support_delta,
        actor="environment",
    )
    return replace(
        capability,
        empirical_support=max(-100, min(100, capability.empirical_support + support_delta)),
        goal_evidence_ids=capability.goal_evidence_ids + (evidence.evidence_id,),
        evidence_objects=capability.evidence_objects + (evidence_object,),
    )


def compile_supported_transport(
    capability: CollectionCapability,
    *,
    obstacle_anchors: Sequence[tuple[int, int]] = (),
    minimum_support: int = 1,
) -> Any:
    """Compile only a fully grounded and empirically supported capability."""

    if capability.empirical_support < minimum_support:
        raise CollectionCapabilityError("goal lacks direct empirical support")
    return _compile_transport(capability, obstacle_anchors=obstacle_anchors)


def _compile_transport(
    capability: CollectionCapability,
    *,
    obstacle_anchors: Sequence[tuple[int, int]],
) -> Any:
    if not capability.grounding.complete:
        raise CollectionCapabilityError("collection roles still contain OPEN ports")
    if capability.interaction_action is None or not capability.interaction_evidence_ids:
        raise CollectionCapabilityError("interaction port lacks direct calibration evidence")
    movement = {model.delta: model.opaque_action for model in capability.motion_models}
    if not movement:
        raise CollectionCapabilityError("no directly calibrated movement model")
    scene = synthesis.perceive(capability.initial_grid)
    regions = {item.region_id: item for item in scene.regions}
    grounding = capability.grounding
    try:
        actor = regions[grounding.actor_id]
        members = [regions[value] for value in grounding.member_ids]
        container = regions[grounding.container_id]
    except KeyError as error:
        raise CollectionCapabilityError("grounded role is absent from planning observation") from error
    widths = {item.width for item in members}
    heights = {item.height for item in members}
    if len(widths) != 1 or len(heights) != 1:
        raise CollectionCapabilityError("portable members do not share one slot geometry")
    item_width, item_height = next(iter(widths)), next(iter(heights))
    slots = tuple(
        (row, column)
        for row in range(container.y, container.y + container.height, item_height)
        for column in range(container.x, container.x + container.width, item_width)
    )
    goal = TRANSPORT.CollectionTransportGoal(
        actor_anchor=(actor.y, actor.x),
        portable_item_anchors=tuple((item.y, item.x) for item in members),
        target_bbox=TRANSPORT.BoundingBox(
            container.y,
            container.x,
            container.y + container.height - 1,
            container.x + container.width - 1,
        ),
        target_slots=slots,
        learned_delta_actions=movement,
        interaction_action=capability.interaction_action,
        grid_bounds=TRANSPORT.GridBounds(scene.height, scene.width),
        obstacle_anchors=frozenset(obstacle_anchors),
    )
    return TRANSPORT.plan_transport(goal)


def compile_transport_probe(
    capability: CollectionCapability,
    *,
    obstacle_anchors: Sequence[tuple[int, int]] = (),
) -> Any:
    """Return one bounded transport attempt while goal support is still zero.

    The prefix ends at the first drop, so it can produce direct progress
    evidence without authorizing the remainder of an unsupported policy.
    Motor and interaction ports must already be empirically calibrated.
    """

    plan = _compile_transport(capability, obstacle_anchors=obstacle_anchors)
    end = next(
        (index + 1 for index, step in enumerate(plan.steps) if step.kind == "drop"),
        None,
    )
    if end is None:
        raise CollectionCapabilityError("transport probe has no adjudication boundary")
    first_assignment = plan.item_to_slot[:1]
    return TRANSPORT.TransportPlan(plan.steps[:end], first_assignment)


__all__ = [
    "CalibrationTransition",
    "CollectionCapability",
    "CollectionCapabilityError",
    "GoalProgressEvidence",
    "MotionModel",
    "OPEN",
    "RoleAlternative",
    "RoleGrounding",
    "adjudicate_goal_evidence",
    "compile_supported_transport",
    "compile_transport_probe",
    "induce_collection_capability",
    "workspace_document",
]
