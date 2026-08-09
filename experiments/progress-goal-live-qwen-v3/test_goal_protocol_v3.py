from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v3_test", HERE / "goal_protocol.py")
assert SPEC is not None and SPEC.loader is not None
GP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GP
SPEC.loader.exec_module(GP)


def workspace():
    return GP.build_workspace(
        entities=[
            {"id": "m0", "outline_class": "o", "interior_class": "i", "area": 4, "origin": [0, 0], "size": [2, 2]},
            {"id": "m1", "outline_class": "o", "interior_class": "i", "area": 4, "origin": [4, 0], "size": [2, 2]},
            {"id": "actor", "outline_class": "o", "interior_class": "a", "area": 4, "origin": [8, 0], "size": [2, 2]},
            {"id": "target", "outline_class": "t", "interior_class": "t", "area": 8, "origin": [0, 8], "size": [4, 2]},
        ],
        transitions=[{"intervention_ref": "im0", "controlled_id": "actor", "observed_delta": [0, 0], "observation_changed": False}],
        frame={"height": 16, "width": 16},
    )


def test_progress_deficit_is_explicit_and_abstention_is_illegal() -> None:
    value = workspace()
    row = value["capacity_hypotheses"][0]
    assert row["current_inside_count"] == 0 and row["outside_count"] == 2
    assert value["progress_opportunity_present"] is True
    branches = GP.response_schema(value)["properties"]["goal"]["oneOf"]
    assert not any(branch.get("type") == "null" for branch in branches)
    rejected = GP.compile_response({"protocol": GP.PROTOCOL, "goal": None}, value)
    assert rejected["reason"] == "progress-opportunity-requires-proposal"


def test_drive_rule_is_generic() -> None:
    text = GP.PROMPT.lower()
    assert "uncertainty calls for testing" in text
    for forbidden in ("wa30", "f05", "three-member", "yellow", "pickup"):
        assert forbidden not in text
