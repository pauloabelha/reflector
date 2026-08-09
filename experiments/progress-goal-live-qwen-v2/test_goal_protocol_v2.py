from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_v2_test", HERE / "goal_protocol.py")
assert SPEC is not None and SPEC.loader is not None
GP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GP
SPEC.loader.exec_module(GP)


def test_equal_area_thin_strip_is_not_a_container_but_exact_tiling_is() -> None:
    entities = [
        *({"id": f"m{i}", "outline_class": "o", "interior_class": "i", "area": 16, "origin": [i * 4, 0], "size": [4, 4]} for i in range(4)),
        {"id": "strip", "outline_class": "s", "interior_class": "s", "area": 64, "origin": [0, 63], "size": [64, 1]},
        {"id": "tile", "outline_class": "t", "interior_class": "t", "area": 64, "origin": [0, 8], "size": [16, 4]},
    ]
    workspace = GP.build_workspace(
        entities=entities,
        transitions=[{"intervention_ref": "im0", "controlled_id": "m0", "observed_delta": [0, 0], "observation_changed": False}],
        frame={"height": 64, "width": 64},
    )
    containers = {item["container"] for item in workspace["capacity_hypotheses"]}
    assert "strip" not in containers
    assert "tile" in containers
    assert all(item["integer_tiling"] is True for item in workspace["capacity_hypotheses"])
