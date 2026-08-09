from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v4_test", HERE / "goal_protocol.py")
assert SPEC is not None and SPEC.loader is not None
GP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GP
SPEC.loader.exec_module(GP)


def fixture():
    workspace = GP.build_workspace(
        entities=[
            {"id": "m0", "outline_class": "o", "interior_class": "i", "area": 4, "origin": [0, 0], "size": [2, 2]},
            {"id": "m1", "outline_class": "o", "interior_class": "i", "area": 4, "origin": [4, 0], "size": [2, 2]},
            {"id": "actor", "outline_class": "o", "interior_class": "a", "area": 4, "origin": [8, 0], "size": [2, 2]},
            {"id": "target", "outline_class": "t", "interior_class": "t", "area": 8, "origin": [0, 8], "size": [4, 2]},
        ],
        transitions=[
            {"intervention_ref": "move", "controlled_id": "actor", "observed_delta": [2, 0], "observation_changed": True},
            {"intervention_ref": "unknown", "controlled_id": "actor", "observed_delta": [0, 0], "observation_changed": False},
        ], frame={"height": 16, "width": 16},
    )
    goal = {
        "family": "collection_containment", "controlled_id": "target",
        "members": ["m0", "m1"], "container_id": "target",
        "potential": "OutsideCount", "terminal": "AllInside",
        "interaction_candidate": "move", "rationale": "test exact capacity",
    }
    return workspace, {"protocol": GP.PROTOCOL, "goal": goal}


def test_r2_returns_exact_port_criticism_without_support() -> None:
    workspace, response = fixture()
    compiled = GP.compile_response(response, workspace)
    assert compiled["reason"] == "r2-grounding-criticism"
    assert {row["kind"] for row in compiled["criticism"]} == {
        "controlled-role-contradicted", "interaction-port-explained-as-translation"
    }
    assert compiled["empirical_support"] == 0


def test_evidence_consistent_revision_is_accepted() -> None:
    workspace, response = fixture()
    response["goal"]["controlled_id"] = "actor"
    response["goal"]["interaction_candidate"] = "unknown"
    compiled = GP.compile_response(response, workspace)
    assert compiled["accepted"] is True and compiled["empirical_support"] == 0
