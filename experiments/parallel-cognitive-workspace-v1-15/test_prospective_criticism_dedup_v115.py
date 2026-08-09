from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
V114 = HERE.parent / "parallel-cognitive-workspace-v1-14"
V19 = HERE.parent / "parallel-cognitive-workspace-v1-9"
FIXTURE_ROOT = V114 / "artifacts/workspaces/generic_prospective--ar25--shared_live_qwen"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


V114_EXPERIMENT = load("prospective_dedup_v115_base", V114 / "experiment.py")
BRIDGE = load("prospective_dedup_v115_bridge", V19 / "evidence_bridge.py")
DEDUP = load("prospective_dedup_v115_test", HERE / "prospective_criticism_dedup.py")
BASE = V114_EXPERIMENT.BASE
EG = BASE.EG
HASH = BASE.LEDGER.stable_hash


def fixture_state():
    return BASE.graph_state(FIXTURE_ROOT)[0]


def latest_selected_prediction(state):
    objects = {item.object_id: item for item in state.objects}
    evidence = max(
        (item for item in state.objects if item.kind == "environment_evidence"),
        key=lambda item: (item.created_revision, item.object_id),
    )
    proposal = next(
        objects[value]
        for value in evidence.dependency_ids
        if objects[value].kind == "action_proposal"
    )
    selected = tuple(proposal.payload["selected_prediction_objects"])
    assert selected
    return evidence, selected


def test_reproduced_same_packet_new_grounding_reuses_existing_criticism() -> None:
    state = fixture_state()
    evidence, selected = latest_selected_prediction(state)
    schema_id = BRIDGE.prediction_schema_id(state, selected[0])
    packet = BRIDGE.cumulative_evidence_packet(state, schema_id)
    key = DEDUP.criticism_key(HASH, schema_id, packet)
    existing = [
        item
        for item in state.objects
        if item.kind == "structured_criticism"
        and item.identity.get("criticism_key") == key
    ]
    assert len(existing) == 1
    old_grounding = existing[0].payload["structured_witness"]["grounding_state"]
    latest_relation = max(
        (item for item in state.objects if item.kind == "relation_set"),
        key=lambda item: item.created_revision,
    )
    # The preserved failure has moved beyond the grounding embedded in the
    # prior criticism, while the cumulative probe packet remains unchanged.
    assert latest_relation.created_revision > existing[0].created_revision
    assert old_grounding

    called = []

    def collision_if_called(*_args, **_kwargs):
        called.append(True)
        raise EG.EpistemicGraphError(
            "stable object identity was reused with different content"
        )

    wrapped = DEDUP.wrap_return_evidence_as_criticism(BRIDGE, HASH, collision_if_called)
    before_evidence = sum(item.kind == "environment_evidence" for item in state.objects)
    returned = wrapped(
        None,
        "fixture",
        state,
        before_grid="older-grounding",
        after_grid="newer-grounding",
        legal=(),
        selected_prediction_ids=selected,
    )
    assert returned is state
    assert called == []
    assert sum(item.kind == "environment_evidence" for item in returned.objects) == before_evidence
    selection = DEDUP.novel_packet_selection(BRIDGE, HASH, state, selected)
    assert selection["reused_schema_ids"] == (schema_id,)
    assert selection["selected_prediction_ids"] == ()
    assert evidence.object_id in {item.object_id for item in returned.objects}


def add_novel_probe_evidence(state, selected_prediction_id):
    prediction = EG.get_object(state, selected_prediction_id)
    assert prediction is not None
    proposal_event = EG.object_event(
        state,
        kind="action_proposal",
        created_by="r2",
        identity={"plan_id": "cp:v115-novel-probe"},
        payload={
            "mode": "probe",
            "plan_id": "cp:v115-novel-probe",
            "selected_prediction_ids": [prediction.payload["prediction_id"]],
            "selected_prediction_objects": [prediction.object_id],
        },
        dependency_ids=(prediction.object_id,),
        event_key="v115-novel-proposal",
    )
    state = EG.apply_event(state, proposal_event)
    proposal_id = proposal_event.payload["item"]["object_id"]
    evidence_event = EG.object_event(
        state,
        kind="environment_evidence",
        created_by="environment",
        identity={"transition_id": "v115-novel-probe-transition"},
        payload={
            "level_delta": 0,
            "observation_changed": True,
            "prospective": {
                "basis_revision": prediction.payload["basis_revision"],
                "plan_id": "cp:v115-novel-probe",
                "judgments": [
                    {
                        "binding_id": prediction.payload["binding_id"],
                        "prediction_id": prediction.payload["prediction_id"],
                        "status": "supports",
                        "reason": "direct-outcome-matched",
                        "predicted_delta": prediction.payload["predicted_delta"],
                        "observed_delta": prediction.payload["predicted_delta"],
                        "predicted_residual": prediction.payload["predicted_residual"],
                        "observed_residual": prediction.payload["predicted_residual"],
                    }
                ],
            },
        },
        dependency_ids=(proposal_id, prediction.object_id),
        event_key="v115-novel-evidence",
    )
    return EG.apply_event(state, evidence_event), evidence_event


def test_novel_probe_packet_passes_to_fallback_and_creates_new_criticism() -> None:
    original = fixture_state()
    _latest, selected = latest_selected_prediction(original)
    state, evidence_event = add_novel_probe_evidence(original, selected[0])
    schema_id = BRIDGE.prediction_schema_id(state, selected[0])
    packet = BRIDGE.cumulative_evidence_packet(state, schema_id)
    new_key = DEDUP.criticism_key(HASH, schema_id, packet)
    assert not any(
        item.kind == "structured_criticism"
        and item.identity.get("criticism_key") == new_key
        for item in state.objects
    )
    calls = []

    def pure_fallback(
        _root,
        _workspace_id,
        current,
        *,
        before_grid,
        after_grid,
        legal,
        selected_prediction_ids,
    ):
        calls.append(tuple(selected_prediction_ids))
        result = EG.ingest_structured_criticism(
            current,
            worker="r2",
            target_id=schema_id,
            status=BRIDGE.RETURN_STATUS,
            criticism_key=new_key,
            payload={"structured_witness": {"evidence_packet": packet}},
            basis_ids=tuple(packet["evidence_ids"]),
        )
        next_state = current
        for event in result.events:
            next_state = EG.apply_event(next_state, event)
        return next_state

    wrapped = DEDUP.wrap_return_evidence_as_criticism(BRIDGE, HASH, pure_fallback)
    before_count = sum(item.kind == "environment_evidence" for item in state.objects)
    returned = wrapped(
        None,
        "fixture",
        state,
        before_grid=None,
        after_grid=None,
        legal=(),
        selected_prediction_ids=selected,
    )
    assert calls == [selected]
    assert any(
        item.kind == "structured_criticism"
        and item.identity.get("criticism_key") == new_key
        for item in returned.objects
    )
    assert sum(item.kind == "environment_evidence" for item in returned.objects) == before_count
    assert evidence_event.payload["item"]["object_id"] in {
        item.object_id for item in returned.objects
    }


def test_mixed_schema_groups_pass_only_novel_packet_predictions() -> None:
    # A compact synthetic bridge isolates the grouping/filtering invariant.
    class Bridge:
        RETURN_STATUS = "prospective-evidence-return"

        @staticmethod
        def prediction_schema_id(_state, prediction_id):
            return {"p-old": "s-old", "p-new-a": "s-new", "p-new-b": "s-new"}.get(
                prediction_id
            )

        @staticmethod
        def cumulative_evidence_packet(_state, schema_id):
            return {"rows": [{"schema": schema_id}], "schema_object_id": schema_id}

    old_packet = Bridge.cumulative_evidence_packet(None, "s-old")
    old_key = DEDUP.criticism_key(HASH, "s-old", old_packet)
    object_type = type("Object", (), {})
    old = object_type()
    old.kind = "structured_criticism"
    old.created_by = "r2"
    old.identity = {"criticism_key": old_key}
    old.payload = {
        "status": Bridge.RETURN_STATUS,
        "structured_witness": {"evidence_packet": old_packet},
    }
    state = type("State", (), {"objects": (old,)})()
    selection = DEDUP.novel_packet_selection(
        Bridge, HASH, state, ("p-new-a", "p-old", "p-new-b")
    )
    assert selection["reused_schema_ids"] == ("s-old",)
    assert selection["novel_schema_ids"] == ("s-new",)
    assert selection["selected_prediction_ids"] == ("p-new-a", "p-new-b")
