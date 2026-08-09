"""Pure, action-opaque planning for collection-and-transport goals.

The planner deliberately knows nothing about a particular game or action ID.
Its only motor knowledge is a learned mapping from displacement vectors to
opaque action values.  The represented interaction model is:

1. move the actor adjacent to an item's anchor;
2. apply the interaction action to pick it up;
3. move actor and item together, preserving their offset, until the item is
   on an unused target slot; and
4. apply the same interaction action to drop it.

Movement is planned over anchor cells.  Fixed obstacle anchors and already
filled target slots cannot be entered.  A filled slot may be the actor's
current start cell immediately after a drop, so the actor can leave it.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from functools import lru_cache
from heapq import heappop, heappush
from itertools import count
from typing import Any, Hashable, Mapping, Sequence


Anchor = tuple[int, int]
Delta = tuple[int, int]
OpaqueAction = Hashable


class TransportGoalError(ValueError):
    """The goal or learned action model is malformed."""


class NoTransportPlan(TransportGoalError):
    """No complete pickup/carry/drop plan exists under the supplied model."""


@dataclass(frozen=True, slots=True)
class GridBounds:
    """A zero-origin rectangular anchor lattice."""

    height: int
    width: int

    def contains(self, anchor: Anchor) -> bool:
        row, column = anchor
        return 0 <= row < self.height and 0 <= column < self.width


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Inclusive target bounds: ``top,left,bottom,right``."""

    top: int
    left: int
    bottom: int
    right: int

    def contains(self, anchor: Anchor) -> bool:
        row, column = anchor
        return self.top <= row <= self.bottom and self.left <= column <= self.right

    def anchors(self) -> tuple[Anchor, ...]:
        return tuple(
            (row, column)
            for row in range(self.top, self.bottom + 1)
            for column in range(self.left, self.right + 1)
        )


@dataclass(frozen=True, slots=True)
class CollectionTransportGoal:
    """A grounded but action-semantic-free collection goal."""

    actor_anchor: Anchor
    portable_item_anchors: tuple[Anchor, ...]
    target_bbox: BoundingBox
    learned_delta_actions: Mapping[Delta, OpaqueAction]
    interaction_action: OpaqueAction
    grid_bounds: GridBounds
    obstacle_anchors: frozenset[Anchor] = frozenset()
    target_slots: tuple[Anchor, ...] | None = None


@dataclass(frozen=True, slots=True)
class PlanStep:
    """One auditable step; ``action`` remains completely opaque."""

    action: OpaqueAction
    kind: str
    actor_before: Anchor
    actor_after: Anchor
    item_index: int
    slot: Anchor | None = None


@dataclass(frozen=True, slots=True)
class TransportPlan:
    steps: tuple[PlanStep, ...]
    item_to_slot: tuple[tuple[int, Anchor], ...]

    @property
    def actions(self) -> tuple[OpaqueAction, ...]:
        return tuple(step.action for step in self.steps)


def _anchor(value: Sequence[int], label: str) -> Anchor:
    if (
        not isinstance(value, (tuple, list))
        or len(value) != 2
        or any(not isinstance(part, int) or isinstance(part, bool) for part in value)
    ):
        raise TransportGoalError(f"{label} must be a pair of integers")
    return int(value[0]), int(value[1])


def _validate(goal: CollectionTransportGoal) -> tuple[tuple[Anchor, ...], tuple[tuple[Delta, OpaqueAction], ...]]:
    bounds = goal.grid_bounds
    if (
        not isinstance(bounds.height, int)
        or isinstance(bounds.height, bool)
        or not isinstance(bounds.width, int)
        or isinstance(bounds.width, bool)
        or bounds.height <= 0
        or bounds.width <= 0
    ):
        raise TransportGoalError("grid bounds must have positive integer dimensions")
    bbox = goal.target_bbox
    if bbox.top > bbox.bottom or bbox.left > bbox.right:
        raise TransportGoalError("target bbox is inverted")
    bbox_corners = ((bbox.top, bbox.left), (bbox.bottom, bbox.right))
    if not all(bounds.contains(value) for value in bbox_corners):
        raise TransportGoalError("target bbox lies outside grid bounds")

    actor = _anchor(goal.actor_anchor, "actor anchor")
    items = tuple(
        _anchor(value, f"portable item {index}")
        for index, value in enumerate(goal.portable_item_anchors)
    )
    obstacles = frozenset(_anchor(value, "obstacle anchor") for value in goal.obstacle_anchors)
    for label, values in (("actor", (actor,)), ("portable item", items), ("obstacle", obstacles)):
        if not all(bounds.contains(value) for value in values):
            raise TransportGoalError(f"{label} anchor lies outside grid bounds")
    if len(set(items)) != len(items):
        raise TransportGoalError("portable item anchors must be distinct")
    if actor in obstacles or any(value in obstacles for value in items):
        raise TransportGoalError("actor/items cannot begin on fixed obstacles")

    raw_slots = bbox.anchors() if goal.target_slots is None else goal.target_slots
    slots = tuple(_anchor(value, "target slot") for value in raw_slots)
    if len(set(slots)) != len(slots):
        raise TransportGoalError("target slots must be distinct")
    if any(not bbox.contains(value) for value in slots):
        raise TransportGoalError("every target slot must lie inside target bbox")
    slots = tuple(sorted(value for value in slots if value not in obstacles))
    if len(slots) < len(items):
        raise TransportGoalError("target has fewer usable slots than portable items")

    try:
        hash(goal.interaction_action)
    except TypeError as error:
        raise TransportGoalError("opaque actions must be hashable") from error

    moves: list[tuple[Delta, OpaqueAction]] = []
    for raw_delta, action in goal.learned_delta_actions.items():
        delta = _anchor(raw_delta, "learned movement delta")
        if delta == (0, 0):
            raise TransportGoalError("a learned movement delta cannot be zero")
        try:
            hash(action)
        except TypeError as error:
            raise TransportGoalError("opaque actions must be hashable") from error
        moves.append((delta, action))
    if items and not moves:
        raise TransportGoalError("at least one learned movement delta is required")
    moves.sort(key=lambda item: (item[0][0], item[0][1], repr(item[1])))
    return slots, tuple(moves)


def plan_transport(goal: CollectionTransportGoal) -> TransportPlan:
    """Return a shortest complete plan, with deterministic tie-breaking.

    Search is exact over item order and target-slot assignment.  Each movement
    leg is a breadth-first search because every learned action has unit action
    cost, irrespective of the displacement it produces.
    """

    slots, moves = _validate(goal)
    actor = _anchor(goal.actor_anchor, "actor anchor")
    items = tuple(_anchor(value, "portable item") for value in goal.portable_item_anchors)
    obstacles = frozenset(goal.obstacle_anchors)
    bounds = goal.grid_bounds

    @lru_cache(maxsize=None)
    def route(
        start: Anchor,
        end: Anchor,
        blocked: frozenset[Anchor],
        carried_offset: Delta | None = None,
    ) -> tuple[tuple[Anchor, Anchor, OpaqueAction], ...] | None:
        if start == end:
            return ()
        queue = deque([start])
        predecessor: dict[Anchor, tuple[Anchor, OpaqueAction]] = {}
        visited = {start}
        while queue:
            current = queue.popleft()
            for (delta_row, delta_column), action in moves:
                successor = (current[0] + delta_row, current[1] + delta_column)
                carried_successor = None if carried_offset is None else (
                    successor[0] + carried_offset[0], successor[1] + carried_offset[1]
                )
                if (
                    successor in visited
                    or successor in blocked
                    or not bounds.contains(successor)
                    or (
                        carried_successor is not None
                        and (carried_successor in blocked or not bounds.contains(carried_successor))
                    )
                ):
                    continue
                predecessor[successor] = (current, action)
                if successor == end:
                    path: list[tuple[Anchor, Anchor, OpaqueAction]] = []
                    cursor = successor
                    while cursor != start:
                        previous, used_action = predecessor[cursor]
                        path.append((previous, cursor, used_action))
                        cursor = previous
                    return tuple(reversed(path))
                visited.add(successor)
                queue.append(successor)
        return None

    initial_remaining = frozenset(range(len(items)))
    initial_free = frozenset(slots)
    # Entries are (cost, deterministic serial, actor, remaining, free, steps,
    # assignments). A serial avoids comparing opaque actions on equal costs.
    serial = count()
    frontier: list[tuple[int, int, Anchor, frozenset[int], frozenset[Anchor], tuple[PlanStep, ...], tuple[tuple[int, Anchor], ...]]] = []
    heappush(frontier, (0, next(serial), actor, initial_remaining, initial_free, (), ()))
    best: dict[tuple[Anchor, frozenset[int], frozenset[Anchor]], int] = {
        (actor, initial_remaining, initial_free): 0
    }

    while frontier:
        cost, _serial, position, remaining, free_slots, steps, assignments = heappop(frontier)
        state_key = (position, remaining, free_slots)
        if cost != best.get(state_key):
            continue
        if not remaining:
            return TransportPlan(steps=steps, item_to_slot=assignments)
        occupied = frozenset(set(slots) - set(free_slots))
        for item_index in sorted(remaining):
            item_anchor = items[item_index]
            other_items = frozenset(items[index] for index in remaining if index != item_index)
            for interaction_delta, _ in moves:
                approach = (
                    item_anchor[0] - interaction_delta[0],
                    item_anchor[1] - interaction_delta[1],
                )
                to_item = route(
                    position,
                    approach,
                    obstacles | occupied | other_items | {item_anchor},
                )
                if to_item is None:
                    continue
                pickup_steps = tuple(
                    PlanStep(action, "move", before, after, item_index)
                    for before, after, action in to_item
                ) + (
                    # Attempting the displacement into the occupied item is a
                    # grounded orientation probe: position is predicted to be
                    # preserved while the actor acquires the interaction pose.
                    PlanStep(
                        goal.learned_delta_actions[interaction_delta],
                        "face",
                        approach,
                        approach,
                        item_index,
                    ),
                    PlanStep(
                        goal.interaction_action,
                        "pickup",
                        approach,
                        approach,
                        item_index,
                    ),
                )
                carried_offset = (
                    item_anchor[0] - approach[0],
                    item_anchor[1] - approach[1],
                )
                for slot in sorted(free_slots):
                    destination = (
                        slot[0] - carried_offset[0],
                        slot[1] - carried_offset[1],
                    )
                    to_slot = route(
                        approach,
                        destination,
                        obstacles | occupied | other_items,
                        carried_offset,
                    )
                    if to_slot is None:
                        continue
                    carry_steps = tuple(
                        PlanStep(action, "carry", before, after, item_index, slot)
                        for before, after, action in to_slot
                    ) + (
                        PlanStep(
                            goal.interaction_action,
                            "drop",
                            destination,
                            destination,
                            item_index,
                            slot,
                        ),
                    )
                    new_remaining = remaining - {item_index}
                    new_free = free_slots - {slot}
                    new_cost = cost + len(pickup_steps) + len(carry_steps)
                    new_key = (destination, new_remaining, new_free)
                    if new_cost >= best.get(new_key, 1 << 60):
                        continue
                    best[new_key] = new_cost
                    heappush(
                        frontier,
                        (
                            new_cost,
                            next(serial),
                            destination,
                            new_remaining,
                            new_free,
                            steps + pickup_steps + carry_steps,
                            assignments + ((item_index, slot),),
                        ),
                    )
    raise NoTransportPlan("no collision-free complete transport plan exists")


__all__ = [
    "Anchor",
    "BoundingBox",
    "CollectionTransportGoal",
    "Delta",
    "GridBounds",
    "NoTransportPlan",
    "OpaqueAction",
    "PlanStep",
    "TransportGoalError",
    "TransportPlan",
    "plan_transport",
]
