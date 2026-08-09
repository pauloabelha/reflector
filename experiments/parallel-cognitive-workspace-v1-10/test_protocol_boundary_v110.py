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


EXPERIMENT = load("parallel_workspace_v110_test", HERE / "experiment.py")
GRAPH = EXPERIMENT.BASE.EG


def test_real_reducer_accepts_and_replays_prospective_evidence_criticism() -> None:
    state = GRAPH.GraphState()
    target_event = GRAPH.object_event(
        state,
        kind="schema",
        created_by="qwen",
        identity={"name": "live-schema"},
        payload={"conditions": []},
        event_key="target",
    )
    state = GRAPH.apply_event(state, target_event)
    target_id = state.objects[0].object_id
    evidence_event = GRAPH.object_event(
        state,
        kind="environment_evidence",
        created_by="environment",
        identity={"transition": "t0"},
        payload={"prospective": {"status": "supports"}},
        dependency_ids=(target_id,),
        event_key="evidence",
    )
    state = GRAPH.apply_event(state, evidence_event)
    evidence_id = state.objects[-1].object_id

    result = GRAPH.ingest_structured_criticism(
        state,
        worker="r2",
        target_id=target_id,
        status="prospective-evidence-return",
        criticism_key="return:t0",
        payload={"empirical_support_delta": 0},
        basis_ids=(evidence_id,),
    )
    criticism = GRAPH.get_object(result.state, result.object_ids[0])
    assert criticism is not None
    assert criticism.payload["status"] == "prospective-evidence-return"
    assert set(criticism.dependency_ids) == {target_id, evidence_id}
    assert GRAPH.support(result.state, criticism.object_id) == 0
    replayed = GRAPH.replay((target_event, evidence_event, *result.events))
    assert GRAPH.state_document(replayed) == GRAPH.state_document(result.state)


def test_v110_changes_only_identity_over_v19_config() -> None:
    config = EXPERIMENT.load_config()
    assert config["action_budget"] == 64
    assert config["prospective_control"]["max_ambiguous_probe_decisions"] == 4
    assert config["experiment"] == "parallel-cognitive-workspace-v1-10"
    assert config["workspace_protocol"] == "prospective-control-v1.10"
