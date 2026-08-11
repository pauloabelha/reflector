from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXPERIMENT = load("parallel_workspace_v19_experiment_test", HERE / "experiment.py")


def test_frozen_v19_overlay_and_runtime_hooks() -> None:
    config = EXPERIMENT.load_config()
    assert config["action_budget"] == 64
    assert config["qwen"]["context_window_tokens"] == 24_576
    assert config["prospective_control"]["max_ambiguous_probe_decisions"] == 4
    assert config["prospective_control"]["max_revision_confirmation_probe_decisions"] == 1
    assert (
        EXPERIMENT.BASE.LC.ProspectiveWorkspaceController
        is EXPERIMENT.LIVE.ProspectiveWorkspaceController
    )
    assert EXPERIMENT.BASE.QC._EVIDENCE_REVISION_V19_INSTALLED is True


def test_action_free_packet_is_accepted_by_revision_contract() -> None:
    packet = EXPERIMENT.BRIDGE.action_blind_grounding_state(
        {
            "frame": {"height": 64, "width": 64},
            "opaque_legal_action_count": 7,
            "entities": [
                {"id": "f00", "area": 4},
                {"id": "f01", "area": 4},
            ],
            "relations": [
                {"predicate": "SameArea", "arguments": ["f00", "f01"]}
            ],
            "truncation": {"maximum_entities": 8, "entities_retained": 2},
        }
    )
    EXPERIMENT.COGNITION._validate_grounding_state_contract(EXPERIMENT.BASE.QC, packet)
    assert "opaque_legal_action_count" not in packet


def test_transition_ingest_filters_judgments_and_forwards_retry_boundary(monkeypatch) -> None:
    calls = []
    sentinel = object()

    def inherited(*args, **kwargs):
        calls.append((args, kwargs))
        return sentinel

    monkeypatch.setattr(EXPERIMENT, "_INGEST_TRANSITION_GRAPH", inherited)
    monkeypatch.setattr(
        EXPERIMENT.BRIDGE,
        "selected_prediction_objects",
        lambda _state, _dependencies: ("selected-prediction",),
    )
    monkeypatch.setattr(
        EXPERIMENT.BRIDGE,
        "selected_judgments",
        lambda _state, _dependencies, _judgments: (
            {"kind": "supports", "target_id": "selected-prediction"},
        ),
    )
    monkeypatch.setattr(
        EXPERIMENT,
        "_return_evidence_as_criticism",
        lambda _root, _workspace_id, state, **_kwargs: state,
    )

    result = EXPERIMENT.ingest_transition_graph(
        Path("root"),
        "workspace",
        object(),
        object(),
        transition_id="transition",
        before_grid=((0,),),
        after_grid=((1,),),
        before_record={"digest": "before"},
        after_record={"digest": "after"},
        legal=(1,),
        intervention_ref="intervention",
        judgments=(
            {"kind": "supports", "target_id": "selected-prediction"},
            {"kind": "refutes", "target_id": "unselected-prediction"},
        ),
        evidence_dependency_ids=("proposal", "selected-prediction"),
        boundary_kind="game-over-retry",
    )

    assert result is sentinel
    assert len(calls) == 1
    assert calls[0][1]["boundary_kind"] == "game-over-retry"
    assert calls[0][1]["judgments"] == (
        {"kind": "supports", "target_id": "selected-prediction"},
    )
