from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("transport_goal_v0_test", HERE / "transport_goal.py")
assert SPEC is not None and SPEC.loader is not None
TG = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = TG
SPEC.loader.exec_module(TG)


MOVES = {
    (-1, 0): "opaque-north",
    (0, -1): "opaque-west",
    (0, 1): "opaque-east",
    (1, 0): "opaque-south",
}
INTERACT = "opaque-interaction"


def replay(goal, plan):
    position = goal.actor_anchor
    carried = None
    carried_offset = None
    remaining = {index: anchor for index, anchor in enumerate(goal.portable_item_anchors)}
    dropped = {}
    inverse_moves = {action: delta for delta, action in goal.learned_delta_actions.items()}
    for step in plan.steps:
        assert step.actor_before == position
        if step.kind in {"move", "carry"}:
            delta = inverse_moves[step.action]
            position = (position[0] + delta[0], position[1] + delta[1])
            assert position == step.actor_after
            assert goal.grid_bounds.contains(position)
            assert position not in goal.obstacle_anchors
            assert position not in dropped
        elif step.kind == "face":
            assert step.actor_before == step.actor_after == position
            delta = inverse_moves[step.action]
            assert remaining[step.item_index] == (
                position[0] + delta[0], position[1] + delta[1]
            )
        elif step.kind == "pickup":
            assert step.action == goal.interaction_action
            item_position = remaining[step.item_index]
            assert carried is None
            carried_offset = (item_position[0] - position[0], item_position[1] - position[1])
            assert carried_offset in goal.learned_delta_actions
            carried = step.item_index
            del remaining[step.item_index]
        elif step.kind == "drop":
            assert step.action == goal.interaction_action and carried_offset is not None
            item_position = (position[0] + carried_offset[0], position[1] + carried_offset[1])
            assert carried == step.item_index and item_position == step.slot
            assert goal.target_bbox.contains(item_position)
            dropped[item_position] = carried
            carried = None
            carried_offset = None
        else:  # pragma: no cover - protects the public step vocabulary
            raise AssertionError(step.kind)
    return position, carried, remaining, dropped


def test_shortest_pickup_carry_drop_plan_uses_opaque_actions() -> None:
    goal = TG.CollectionTransportGoal(
        actor_anchor=(1, 0),
        portable_item_anchors=((1, 1),),
        target_bbox=TG.BoundingBox(1, 3, 1, 3),
        target_slots=((1, 3),),
        learned_delta_actions=MOVES,
        interaction_action=INTERACT,
        grid_bounds=TG.GridBounds(3, 4),
    )
    plan = TG.plan_transport(goal)
    assert plan.actions == ("opaque-east", INTERACT, "opaque-east", "opaque-east", INTERACT)
    assert [step.kind for step in plan.steps] == ["face", "pickup", "carry", "carry", "drop"]
    assert plan.item_to_slot == ((0, (1, 3)),)
    assert replay(goal, plan)[2:] == ({}, {(1, 3): 0})


def test_fixed_obstacles_force_a_collision_free_detour() -> None:
    goal = TG.CollectionTransportGoal(
        actor_anchor=(2, 0),
        portable_item_anchors=((2, 1),),
        target_bbox=TG.BoundingBox(2, 4, 2, 4),
        target_slots=((2, 4),),
        learned_delta_actions=MOVES,
        interaction_action=INTERACT,
        grid_bounds=TG.GridBounds(5, 5),
        obstacle_anchors=frozenset({(2, 2), (2, 3)}),
    )
    plan = TG.plan_transport(goal)
    assert len(plan.actions) == 10
    assert all(step.actor_after not in goal.obstacle_anchors for step in plan.steps)
    assert replay(goal, plan)[2:] == ({}, {(2, 4): 0})


def test_planner_chooses_item_order_and_distinct_slots_globally() -> None:
    goal = TG.CollectionTransportGoal(
        actor_anchor=(0, 0),
        portable_item_anchors=((0, 4), (0, 1)),
        target_bbox=TG.BoundingBox(2, 2, 2, 3),
        target_slots=((2, 2), (2, 3)),
        learned_delta_actions=MOVES,
        interaction_action=INTERACT,
        grid_bounds=TG.GridBounds(4, 5),
    )
    plan = TG.plan_transport(goal)
    assert plan.item_to_slot[0][0] == 1  # nearby item is collected first
    assert len({slot for _, slot in plan.item_to_slot}) == 2
    _position, carried, remaining, dropped = replay(goal, plan)
    assert carried is None and remaining == {} and len(dropped) == 2


def test_anonymized_large_layout_remains_game_and_action_blind() -> None:
    # The dimensions and spread deliberately resemble a larger visual puzzle,
    # while every role and action remains anonymous and data supplied.
    goal = TG.CollectionTransportGoal(
        actor_anchor=(28, 28),
        portable_item_anchors=((16, 28), (32, 36), (32, 48), (44, 24)),
        target_bbox=TG.BoundingBox(27, 56, 30, 59),
        target_slots=((27, 56), (27, 57), (27, 58), (27, 59)),
        learned_delta_actions={
            (-1, 0): 713,
            (0, -1): 991,
            (0, 1): 208,
            (1, 0): 457,
        },
        interaction_action=664,
        grid_bounds=TG.GridBounds(64, 64),
        obstacle_anchors=frozenset((row, 40) for row in range(64) if row != 31),
    )
    plan = TG.plan_transport(goal)
    assert set(plan.actions) <= {713, 991, 208, 457, 664}
    assert sum(step.kind == "pickup" for step in plan.steps) == 4
    assert sum(step.kind == "drop" for step in plan.steps) == 4
    assert replay(goal, plan)[2:] == ({}, {slot: item for item, slot in plan.item_to_slot})


def test_unreachable_goal_and_invalid_capacity_fail_explicitly() -> None:
    blocked = TG.CollectionTransportGoal(
        actor_anchor=(0, 0),
        portable_item_anchors=((2, 2),),
        target_bbox=TG.BoundingBox(0, 2, 0, 2),
        target_slots=((0, 2),),
        learned_delta_actions=MOVES,
        interaction_action=INTERACT,
        grid_bounds=TG.GridBounds(3, 3),
        obstacle_anchors=frozenset({(1, 0), (1, 1), (1, 2)}),
    )
    with pytest.raises(TG.NoTransportPlan):
        TG.plan_transport(blocked)

    no_capacity = TG.CollectionTransportGoal(
        actor_anchor=(0, 0),
        portable_item_anchors=((1, 0), (1, 1)),
        target_bbox=TG.BoundingBox(2, 0, 2, 0),
        learned_delta_actions=MOVES,
        interaction_action=INTERACT,
        grid_bounds=TG.GridBounds(3, 3),
    )
    with pytest.raises(TG.TransportGoalError, match="fewer usable slots"):
        TG.plan_transport(no_capacity)
