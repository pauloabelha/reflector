from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v5_test", HERE / "goal_protocol.py")
assert SPEC is not None and SPEC.loader is not None
GP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GP
SPEC.loader.exec_module(GP)


def fixture(extra_zero: bool = False):
    transitions = [
        {"intervention_ref": "move", "controlled_id": "actor", "observed_delta": [2, 0], "observation_changed": True},
        {"intervention_ref": "unknown", "controlled_id": "actor", "observed_delta": [0, 0], "observation_changed": False},
    ]
    if extra_zero:
        transitions.append({"intervention_ref": "unknown2", "controlled_id": "actor", "observed_delta": [0, 0], "observation_changed": False})
    workspace = GP.build_workspace(
        entities=[
            {"id": "m0", "outline_class": "o", "interior_class": "i", "area": 4, "origin": [0, 0], "size": [2, 2]},
            {"id": "m1", "outline_class": "o", "interior_class": "i", "area": 4, "origin": [4, 0], "size": [2, 2]},
            {"id": "actor", "outline_class": "o", "interior_class": "a", "area": 4, "origin": [8, 0], "size": [2, 2]},
            {"id": "target", "outline_class": "t", "interior_class": "t", "area": 8, "origin": [0, 8], "size": [4, 2]},
        ], transitions=transitions, frame={"height": 16, "width": 16},
    )
    goal = {
        "family": "collection_containment", "controlled_id": "target",
        "members": ["m0", "m1"], "container_id": "target",
        "potential": "OutsideCount", "terminal": "AllInside",
        "interaction_candidate": "move", "rationale": "capacity deficit",
    }
    return workspace, goal


def test_semantics_survive_while_ports_are_separately_grounded() -> None:
    workspace, qwen_goal = fixture()
    compiled = GP.compile_response({"protocol": GP.PROTOCOL, "goal": qwen_goal}, workspace)
    assert compiled["accepted"] is True and compiled["empirical_support"] == 0
    assert compiled["qwen_goal"] == qwen_goal
    assert compiled["goal"]["controlled_id"] == "actor"
    assert compiled["goal"]["interaction_candidate"] == "unknown"
    assert {row["port"] for row in compiled["r2_grounding"]["port_witnesses"]} == {
        "controlled_id", "interaction_candidate"
    }


def test_ambiguous_open_ports_abstain() -> None:
    workspace, goal = fixture(extra_zero=True)
    compiled = GP.compile_response({"protocol": GP.PROTOCOL, "goal": goal}, workspace)
    assert compiled["accepted"] is False
    assert compiled["reason"] == "r2-open-port-ambiguous"
