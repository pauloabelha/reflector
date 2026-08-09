from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("evidence_bridge_v19_test", HERE / "evidence_bridge.py")
assert spec is not None and spec.loader is not None
BRIDGE = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = BRIDGE
spec.loader.exec_module(BRIDGE)


@dataclass(frozen=True)
class Obj:
    object_id: str
    kind: str
    created_by: str
    payload: dict
    dependency_ids: tuple[str, ...] = ()
    created_revision: int = 0


@dataclass(frozen=True)
class State:
    objects: tuple[Obj, ...]


def fixture_state() -> State:
    return State(
        (
            Obj("s", "schema", "qwen", {}),
            Obj("b", "binding", "r2", {}, ("s",)),
            Obj("p", "prediction", "r2", {"prediction_id": "pp", "candidate_id": "c"}, ("b",)),
            Obj("q", "prediction", "r2", {"prediction_id": "qq", "candidate_id": "d"}, ("b",)),
            Obj("a", "action_proposal", "r2", {"mode": "probe", "selected_prediction_objects": ["p"]}),
            Obj(
                "e",
                "environment_evidence",
                "environment",
                {
                    "level_delta": 0,
                    "prospective": {
                        "judgments": [
                            {"prediction_id": "pp", "binding_id": "lb", "status": "supports", "reason": "match", "predicted_delta": [1, 0], "observed_delta": [1, 0], "predicted_residual": 3, "observed_residual": 3},
                            {"prediction_id": "qq", "binding_id": "lb2", "status": "refutes", "reason": "miss"},
                        ]
                    },
                },
                ("a", "p", "q"),
                7,
            ),
        )
    )


def test_only_selected_predictions_receive_epistemic_judgments() -> None:
    state = fixture_state()
    assert BRIDGE.selected_prediction_objects(state, ("a", "p", "q")) == ("p",)
    assert BRIDGE.selected_judgments(
        state,
        ("a", "p", "q"),
        (
            {"kind": "supports", "target_id": "p"},
            {"kind": "refutes", "target_id": "q"},
        ),
    ) == ({"kind": "supports", "target_id": "p"},)


def test_packet_is_exact_selected_probe_evidence() -> None:
    packet = BRIDGE.cumulative_evidence_packet(fixture_state(), "s")
    assert packet["counts"] == {"supports": 1, "refutes": 0, "unresolved": 0}
    assert packet["evidence_ids"] == ["e"]
    assert len(packet["rows"]) == 1
    assert packet["rows"][0]["prediction_object_id"] == "p"


def test_grounding_projection_has_no_action_surface() -> None:
    projected = BRIDGE.action_blind_grounding_state(
        {"frame": {"height": 2}, "opaque_legal_action_count": 7, "entities": [], "relations": [], "truncation": {}}
    )
    assert "opaque_legal_action_count" not in projected
    assert projected["protocol"] == "exact-action-free-grounding-state-v1"
    assert projected["population_complete"] is True


def test_grounding_state_refuses_to_claim_a_saturated_population_is_complete() -> None:
    projected = BRIDGE.action_blind_grounding_state(
        {
            "entities": [{"id": f"f{index:02d}"} for index in range(8)],
            "relations": [],
            "truncation": {"entities_retained": 8, "maximum_entities": 8},
        }
    )
    assert projected["population_complete"] is False
    assert projected["truncated"] is True
