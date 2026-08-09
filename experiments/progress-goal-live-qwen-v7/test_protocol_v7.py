from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v7_test", HERE / "goal_protocol.py")
assert SPEC is not None and SPEC.loader is not None
GP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GP
SPEC.loader.exec_module(GP)


def test_control_without_capacity_is_still_progress_opportunity() -> None:
    workspace = GP.build_workspace(
        entities=[{"id": "p", "outline_class": "moving", "interior_class": "multi", "area": 4, "origin": [1, 1], "size": [2, 2]}],
        transitions=[{"intervention_ref": "i", "controlled_id": "p", "observed_delta": [1, 0], "observation_changed": True}],
        frame={"height": 8, "width": 8},
    )
    assert workspace["capacity_hypotheses"] == []
    assert workspace["progress_opportunity_present"] is True
    assert workspace["control_opportunity"]["controlled_candidates"] == ["p"]
    assert not any(branch.get("type") == "null" for branch in GP.response_schema(workspace)["properties"]["goal"]["oneOf"])
