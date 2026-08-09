from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("goal_generic_tracker_test", HERE / "tracker.py")
assert SPEC is not None and SPEC.loader is not None
T = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = T
SPEC.loader.exec_module(T)


@dataclass(frozen=True)
class Node:
    identity: str
    anchor: tuple[int, int]
    area: int = 4
    normalized_cells: tuple[tuple[int, int], ...] = ((0, 0), (1, 0), (0, 1), (1, 1))


def correspond(before, after):
    by_identity = {item.identity: item for item in after}
    return {item: by_identity[item.identity] for item in before if item.identity in by_identity}


def test_control_is_discovered_without_any_goal_roles() -> None:
    initial = (Node("actor", (4, 4)), Node("other", (8, 8)))
    states = (
        (Node("actor", (4, 2)), Node("other", (8, 8))),
        (Node("actor", (4, 4)), Node("other", (8, 8))),
        (Node("actor", (4, 4)), Node("other", (8, 8))),
    )
    result = T.track_calibration(initial, states, ("i0", "i1", "i2"), correspond)
    assert result.controlled_id == "e000"
    assert result.movement_models == (((0, -2), "i0"), ((0, 2), "i1"))
    assert result.unexplained_interventions == ("i2",)
    assert T.workspace_transitions(result)[0]["controlled_candidates"] == ["e000"]


def test_tied_movers_remain_ambiguous_and_birth_death_are_preserved() -> None:
    initial = (Node("a", (0, 0)), Node("b", (2, 0)))
    states = ((Node("a", (1, 0)), Node("b", (3, 0)), Node("new", (9, 9))),)
    result = T.track_calibration(initial, states, ("i0",), correspond)
    assert result.controlled_id is None
    assert result.controlled_candidates == ("e000", "e001")
    statuses = {row.status for row in result.steps[0].effects}
    assert statuses == {"matched", "appeared"}


def test_relaxed_completion_preserves_rotating_unmatched_controller() -> None:
    before = (Node("old-pose", (4, 4)), Node("static", (8, 8)))
    after = (Node("new-pose", (4, 2)), Node("static", (8, 8)))

    def exact(left, right):
        by_id = {item.identity: item for item in right}
        return {item: by_id[item.identity] for item in left if item.identity in by_id}

    mapping = T.complete_correspondence(before, after, exact)
    assert mapping[before[0]] == after[0]
    result = T.track_calibration(
        before, (after,), ("i0",),
        lambda left, right: T.complete_correspondence(left, right, exact),
    )
    assert result.controlled_id == "e000"
    assert result.movement_models == (((0, -2), "i0"),)
