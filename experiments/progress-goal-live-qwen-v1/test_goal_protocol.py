from __future__ import annotations

import importlib.util
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("live_goal_protocol_test", HERE / "goal_protocol.py")
assert SPEC is not None and SPEC.loader is not None
GP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GP
SPEC.loader.exec_module(GP)


def workspace():
    entities = [
        {"id": "e0", "outline_class": "o0", "interior_class": "i0", "area": 4, "origin": [0, 0], "size": [2, 2]},
        {"id": "e1", "outline_class": "o0", "interior_class": "i0", "area": 4, "origin": [4, 0], "size": [2, 2]},
        {"id": "actor", "outline_class": "o0", "interior_class": "i1", "area": 4, "origin": [8, 0], "size": [2, 2]},
        {"id": "target", "outline_class": "o1", "interior_class": "i2", "area": 8, "origin": [0, 8], "size": [4, 2]},
    ]
    transitions = [
        {"intervention_ref": "im0", "controlled_id": "actor", "observed_delta": [0, -2], "observation_changed": True},
        {"intervention_ref": "im1", "controlled_id": "actor", "observed_delta": [0, 0], "observation_changed": False},
    ]
    return GP.build_workspace(entities=entities, transitions=transitions, frame={"height": 16, "width": 16})


def test_workspace_exposes_classes_capacity_and_grounded_effects() -> None:
    value = workspace()
    assert {"e0", "e1"} in [set(item["members"]) for item in value["equivalence_classes"]]
    assert any(item["members"] == ["e0", "e1"] and item["container"] == "target" for item in value["capacity_hypotheses"])
    assert value["calibrated_transitions"][1]["intervention_ref"] == "im1"


def test_collection_goal_compiles_at_support_zero() -> None:
    value = workspace()
    response = {"protocol": GP.PROTOCOL, "goal": {
        "family": "collection_containment",
        "controlled_id": "actor",
        "members": ["e0", "e1"],
        "container_id": "target",
        "potential": "OutsideCount",
        "terminal": "AllInside",
        "interaction_candidate": "im1",
        "rationale": "A repeated class and exact-capacity region deserve a transport test.",
    }}
    compiled = GP.compile_response(response, value)
    assert compiled["accepted"] is True
    assert compiled["empirical_support"] == 0


def test_wrong_capacity_or_semantics_are_rejected() -> None:
    value = workspace()
    base = {
        "family": "collection_containment", "controlled_id": "actor",
        "members": ["e0"], "container_id": "target",
        "potential": "OutsideCount", "terminal": "AllInside",
        "interaction_candidate": "im1", "rationale": "test",
    }
    assert GP.compile_response({"protocol": GP.PROTOCOL, "goal": base}, value)["reason"] == "collection-grounding"
    wrong = {**base, "members": ["e0", "e1"], "potential": "AlignmentResidual"}
    assert GP.compile_response({"protocol": GP.PROTOCOL, "goal": wrong}, value)["reason"] == "family-semantics"


def test_prompt_is_generic_and_action_blind() -> None:
    text = GP.PROMPT.lower()
    for forbidden in ("wa30", "yellow", "blue", "action_1", "f00", "pickup the"):
        assert forbidden not in text
    payload = GP.request_payload(workspace(), {
        "model": "m", "max_tokens": 100, "thinking_budget_tokens": 50,
    }, "data:image/png;base64,AA==")
    assert payload["response_format"]["json_schema"]["strict"] is True

