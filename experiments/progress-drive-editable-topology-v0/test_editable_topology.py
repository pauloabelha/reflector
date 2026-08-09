from __future__ import annotations

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("editable_topology_tested", HERE / "editable_topology.py")
assert spec and spec.loader
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


def test_grounded_panel_and_topology_edit_plan() -> None:
    grid = (
        (1, 1, 0, 5, 5, 7, 7),
        (1, 1, 0, 5, 5, 7, 7),
        (0, 0, 0, 5, 5, 0, 0),
        (0, 0, 0, 5, 5, 8, 8),
    )
    points = M.grounded_interaction_points(grid, background_values=frozenset({0, 5}))
    assert points == ((6, 30),)
    vocab = M.intervention_vocabulary(
        (1, 2), parameterized_action_id=6, interaction_points=((6, 30), (6, 33))
    )
    assert [item.token for item in vocab] == [
        "simple:1", "simple:2", "grounded-component:0", "grounded-component:1"
    ]

    def observe(prefix):
        door_open = any(item.token == "grounded-component:1" for item in prefix)
        position = 0
        for item in prefix:
            if item.token == "simple:1" and (door_open or position == 0):
                position += 1
        return {"key": (position, door_open), "done": position >= 2}

    result = M.search_observed_state_space(
        vocab,
        observe_prefix=observe,
        state_key=lambda state: state["key"],
        completed=lambda state: bool(state["done"]),
        max_depth=4,
    )
    assert [item.token for item in result.plan] == [
        "simple:1", "grounded-component:1", "simple:1"
    ]


def test_search_deduplicates_visual_states_and_has_a_hard_budget() -> None:
    action = M.Intervention("noop", 1)
    try:
        M.search_observed_state_space(
            (action,),
            observe_prefix=lambda prefix: {"digest": "same", "done": False},
            state_key=lambda state: state["digest"],
            completed=lambda state: state["done"],
            max_depth=5,
        )
    except M.NoEditableTopologyPlan as error:
        assert "observed 1 states" in str(error)
    else:
        raise AssertionError("expected a bounded failure")


def test_global_object_addresses_are_not_limited_to_a_side_panel() -> None:
    grid = (
        (0, 0, 0, 0, 0, 0),
        (0, 3, 3, 0, 4, 4),
        (0, 3, 3, 0, 4, 4),
        (0, 0, 0, 0, 0, 0),
    )
    assert M.grounded_object_points(
        grid, background_values=frozenset({0})
    ) == ((1, 31), (4, 31))


def test_parameterized_addresses_can_be_regrounded_after_motion() -> None:
    move = M.Intervention("move", 1)
    def observe(prefix):
        position=0;selected=False
        for item in prefix:
            if item.token.startswith("select:"):selected=int(item.token.split(":")[1])==position
            elif item.token=="move" and selected:position+=1;selected=False
        return {"position":position,"selected":selected,"done":position==2}
    result=M.search_observed_state_space(
        (),observe_prefix=observe,state_key=lambda s:(s["position"],s["selected"]),completed=lambda s:s["done"],max_depth=4,
        interventions_for_state=lambda state:(M.Intervention(f"select:{state['position']}",6),move),
    )
    assert [item.token for item in result.plan]==["select:0","move","select:1","move"]
