"""Generic planning for state-qualified visual obligations.

Some interactive tasks do not expose a useful geometric gradient.  A site is
completed only when it is visited while a separately visible state register
has the right value.  Other sites transform that register.  This module keeps
the transferable claim deliberately abstract and puts positions, visual
signatures, and opaque interventions in a situated binding.

Nothing here knows a game, palette, direction name, or action meaning.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
import hashlib
import json
from typing import Any, Mapping, Sequence


class GuardedObligationError(ValueError):
    pass


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")
    ).hexdigest()


Node = str
Register = tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GuardedObligation:
    obligation_id: str
    node: Node
    required_register: Register


@dataclass(frozen=True, slots=True)
class ArrivalEffect:
    """An empirically learned state change caused by entering one node."""

    node: Node
    before: Register
    after: Register
    evidence_ids: tuple[str, ...]
    direct: bool = True

    def __post_init__(self) -> None:
        if not self.node or not self.before or not self.after:
            raise GuardedObligationError("arrival effects require situated state")
        if not self.evidence_ids:
            raise GuardedObligationError("arrival effects require transition evidence")


@dataclass(frozen=True, slots=True)
class GuardedWorld:
    start_node: Node
    start_register: Register
    # Directed, action-labelled topology learned from observed motion.
    transitions: tuple[tuple[Node, int, Node], ...]
    obligations: tuple[GuardedObligation, ...]
    arrival_effects: tuple[ArrivalEffect, ...] = ()
    unexplored_transformer_nodes: tuple[Node, ...] = ()
    basis_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.start_node or not self.start_register:
            raise GuardedObligationError("world requires a current situated state")
        if not self.transitions or not self.obligations:
            raise GuardedObligationError("world requires topology and obligations")
        if not self.basis_ids:
            raise GuardedObligationError("world must cite observations")
        seen: dict[tuple[Node, int], Node] = {}
        for source, action, target in self.transitions:
            key = str(source), int(action)
            if key in seen and seen[key] != str(target):
                raise GuardedObligationError("opaque transition model is nonfunctional")
            seen[key] = str(target)
        ids = [item.obligation_id for item in self.obligations]
        if len(ids) != len(set(ids)):
            raise GuardedObligationError("obligation IDs must be unique")


@dataclass(frozen=True, slots=True)
class GuardedObservation:
    """A perceptual worker's action-blind, situated state estimate."""

    observation_id: str
    actor_node: Node
    register: Register
    live_obligations: tuple[GuardedObligation, ...]
    transformer_candidates: tuple[Node, ...] = ()


@dataclass(frozen=True, slots=True)
class GuardedTransition:
    transition_id: str
    before: GuardedObservation
    opaque_action: int
    after: GuardedObservation
    direct: bool = True


@dataclass(frozen=True, slots=True)
class GuardedCapability:
    candidate_id: str
    binding_id: str
    goal_ast: Mapping[str, Any]
    world: GuardedWorld
    attention: int = 88
    empirical_support: int = 0
    confirmations: int = 0
    refutations: int = 0


@dataclass(frozen=True, slots=True)
class GuardedPlan:
    candidate_id: str
    binding_id: str
    actions: tuple[int, ...]
    visited_nodes: tuple[Node, ...]
    register_trace: tuple[Register, ...]
    discharged: tuple[str, ...]
    complete: bool
    mode: str
    basis_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GuardedEvidence:
    candidate_id: str
    binding_id: str
    transition_id: str
    predicted_remaining: int
    observed_remaining: int | None
    direct: bool
    actor: str = "environment"

    def __post_init__(self) -> None:
        if self.actor != "environment":
            raise GuardedObligationError("only the environment may adjudicate a guarded goal")


def compile_capability(world: GuardedWorld, *, attention: int = 88) -> GuardedCapability:
    ast = {
        "protocol": "autonomous-progress-synthesis-v0",
        "type": "GoalPotential",
        "roles": {
            "controlled": {"type": "ActionCorrelatedPose"},
            "register": {"type": "PersistentVisibleState"},
            "obligations": {"type": "StateQualifiedSites"},
            "transformers": {"type": "SituatedStateTransformers"},
        },
        "potential": {
            "type": "UnsatisfiedGuardedObligationCount",
            "direction": "minimize",
            "lower_bound": 0,
        },
        "terminal": {"type": "AllGuardedObligationsSatisfied"},
    }
    cid = "goal:" + _hash(ast)[:24]
    binding = {
        "candidate_id": cid,
        "start_node": world.start_node,
        "start_register": world.start_register,
        "transitions": world.transitions,
        "obligations": [
            (row.obligation_id, row.node, row.required_register) for row in world.obligations
        ],
        "arrival_effects": [
            (row.node, row.before, row.after, row.evidence_ids, row.direct)
            for row in world.arrival_effects
        ],
        "unexplored_transformer_nodes": world.unexplored_transformer_nodes,
    }
    return GuardedCapability(
        cid,
        "grounding:" + _hash(binding)[:24],
        ast,
        world,
        max(0, min(100, int(attention))),
    )


def induce_from_transitions(
    current: GuardedObservation,
    transitions: Sequence[GuardedTransition],
) -> GuardedCapability:
    """Induce a situated guarded model solely from grounded observations.

    Register changes are attributed to the entered site only when the actor's
    pose is directly tracked across the same transition.  Conflicts remain
    explicit and are rejected by the planner; they are never majority-voted.
    """
    if not current.observation_id:
        raise GuardedObligationError("current observation needs a stable ID")
    moves = set(); effects = []; basis = {current.observation_id}
    for row in transitions:
        if not row.transition_id:
            raise GuardedObligationError("transition needs a stable ID")
        basis.update((row.transition_id, row.before.observation_id, row.after.observation_id))
        if not row.direct:
            continue
        moves.add((row.before.actor_node, int(row.opaque_action), row.after.actor_node))
        if row.before.register != row.after.register:
            effects.append(ArrivalEffect(
                row.after.actor_node,
                row.before.register,
                row.after.register,
                (row.transition_id,),
            ))
    world = GuardedWorld(
        current.actor_node,
        current.register,
        tuple(sorted(moves)),
        tuple(sorted(current.live_obligations, key=lambda item: item.obligation_id)),
        tuple(sorted(effects, key=lambda item: (item.node, item.before, item.after, item.evidence_ids))),
        tuple(sorted(set(current.transformer_candidates))),
        tuple(sorted(basis)),
    )
    return compile_capability(world)


def _maps(world: GuardedWorld):
    moves: dict[Node, list[tuple[int, Node]]] = {}
    for source, action, target in world.transitions:
        moves.setdefault(source, []).append((int(action), target))
    for rows in moves.values():
        rows.sort(key=lambda row: (row[0], row[1]))
    effects: dict[tuple[Node, Register], Register] = {}
    for row in world.arrival_effects:
        if not row.direct:
            continue
        key = row.node, row.before
        if key in effects and effects[key] != row.after:
            raise GuardedObligationError("conflicting direct arrival effects")
        effects[key] = row.after
    return moves, effects


def _discharge(
    obligations: Mapping[str, GuardedObligation],
    remaining: frozenset[str],
    node: Node,
    register: Register,
) -> tuple[frozenset[str], tuple[str, ...]]:
    won = tuple(sorted(
        oid for oid in remaining
        if obligations[oid].node == node and obligations[oid].required_register == register
    ))
    return remaining.difference(won), won


def plan_capability(capability: GuardedCapability, *, max_expansions: int = 100_000) -> GuardedPlan:
    """Return the shortest known plan over pose, register, and obligations.

    If the exact goal cannot yet be reached, return the shortest information
    probe to an untested transformer.  Unknown effects are never fabricated.
    """
    world = capability.world
    moves, effects = _maps(world)
    obligations = {row.obligation_id: row for row in world.obligations}
    all_remaining = frozenset(obligations)
    start_remaining, initial_won = _discharge(
        obligations, all_remaining, world.start_node, world.start_register
    )
    start = world.start_node, world.start_register, start_remaining
    queue = deque([start]); parent = {start: None}; command: dict[Any, int] = {}
    arrived: dict[Any, tuple[str, ...]] = {start: initial_won}
    probe_targets = set(world.unexplored_transformer_nodes)
    first_probe = None
    goal = start if not start_remaining else None
    expansions = 0
    while queue and goal is None:
        state = queue.popleft(); expansions += 1
        if expansions > max_expansions:
            raise GuardedObligationError("guarded search exceeded its bound")
        node, register, remaining = state
        if node in probe_targets and state != start and first_probe is None:
            first_probe = state
        for action, target in moves.get(node, ()):
            next_register = effects.get((target, register), register)
            next_remaining, won = _discharge(
                obligations, remaining, target, next_register
            )
            nxt = target, next_register, next_remaining
            if nxt in parent:
                continue
            parent[nxt] = state; command[nxt] = action; arrived[nxt] = won
            if not next_remaining:
                goal = nxt; break
            queue.append(nxt)
    chosen = goal or first_probe
    if chosen is None:
        return GuardedPlan(
            capability.candidate_id, capability.binding_id, (),
            (world.start_node,), (world.start_register,), initial_won,
            False, "unreachable", tuple(sorted(set(world.basis_ids))),
        )
    states = []
    cursor = chosen
    while cursor is not None:
        states.append(cursor); cursor = parent[cursor]
    states.reverse()
    actions = tuple(command[state] for state in states[1:])
    discharged = tuple(oid for state in states for oid in arrived[state])
    return GuardedPlan(
        capability.candidate_id,
        capability.binding_id,
        actions,
        tuple(state[0] for state in states),
        tuple(state[1] for state in states),
        discharged,
        goal is not None,
        "control" if goal is not None else "probe-transformer",
        tuple(sorted(set(world.basis_ids) | {
            evidence for effect in world.arrival_effects for evidence in effect.evidence_ids
        })),
    )


def adjudicate(capability: GuardedCapability, evidence: GuardedEvidence) -> GuardedCapability:
    if evidence.candidate_id != capability.candidate_id or evidence.binding_id != capability.binding_id:
        raise GuardedObligationError("evidence targets another capability")
    if not evidence.direct or evidence.observed_remaining is None:
        return capability
    matched = evidence.observed_remaining == evidence.predicted_remaining
    return replace(
        capability,
        empirical_support=max(-100, min(100, capability.empirical_support + (10 if matched else -10))),
        confirmations=capability.confirmations + int(matched),
        refutations=capability.refutations + int(not matched),
    )


def workspace_document(capability: GuardedCapability, *, include_binding: bool = False) -> dict[str, Any]:
    document = {
        "kind": "goal_potential",
        "identity": {"candidate_id": capability.candidate_id},
        "payload": {
            "ast": dict(capability.goal_ast),
            "attention": capability.attention,
            "empirical_support": capability.empirical_support,
            "confirmations": capability.confirmations,
            "refutations": capability.refutations,
            "authority": "environment-evidence-only",
        },
    }
    if include_binding:
        document["binding"] = {
            "binding_id": capability.binding_id,
            "start_node": capability.world.start_node,
            "start_register": list(capability.world.start_register),
            "transitions": [list(row) for row in capability.world.transitions],
            "obligations": [
                {
                    "obligation_id": row.obligation_id,
                    "node": row.node,
                    "required_register": list(row.required_register),
                }
                for row in capability.world.obligations
            ],
            "arrival_effects": [
                {
                    "node": row.node,
                    "before": list(row.before),
                    "after": list(row.after),
                    "evidence_ids": list(row.evidence_ids),
                }
                for row in capability.world.arrival_effects if row.direct
            ],
            "basis_ids": list(capability.world.basis_ids),
        }
    return document


__all__ = [
    "ArrivalEffect", "GuardedCapability", "GuardedEvidence", "GuardedObservation",
    "GuardedObligation", "GuardedObligationError", "GuardedPlan", "GuardedTransition",
    "GuardedWorld", "adjudicate", "compile_capability", "induce_from_transitions",
    "plan_capability", "workspace_document",
]
