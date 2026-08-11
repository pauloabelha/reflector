from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
V111 = HERE.parent / "parallel-cognitive-workspace-v1-11"
FIXTURE = (
    V111
    / "artifacts/workspaces/generic_prospective--ar25--shared_live_qwen"
)


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V111_MODULE = load("workspace_v111_packet_fixture", V111 / "experiment.py")
PACKET = load("causal_packet_v112_test", HERE / "causal_packet.py")
BASE = V111_MODULE.BASE


def fixture_state():
    return BASE.graph_state(FIXTURE)[0]


def test_due_predicate_is_exactly_packet_eligible_unit() -> None:
    state = fixture_state()
    assert PACKET.causal_revision_due(BASE.QC, state) is (
        PACKET.build_causal_packet(BASE.QC, state) is not None
    )

    empty_qc = SimpleNamespace(exact_causal_chains=lambda state: ())
    empty = SimpleNamespace(objects=[])
    assert PACKET.causal_revision_due(empty_qc, empty) is False
    assert PACKET.build_causal_packet(empty_qc, empty) is None


def test_malformed_eligible_packet_is_due_and_raises_in_builder() -> None:
    qc = SimpleNamespace(
        exact_causal_chains=lambda state: ({
            "criticism_status": PACKET.STATUS,
            "derivation_id": "missing-derivation",
            "semantic_target_id": "missing-target",
            "criticism_id": "missing-criticism",
        },)
    )
    state = SimpleNamespace(objects=[])
    assert PACKET.causal_revision_due(qc, state) is True
    with pytest.raises(PACKET.CausalPacketError, match="missing object"):
        PACKET.build_causal_packet(qc, state)


def test_packet_preserves_exact_fixture_semantics_and_flat_ancestry() -> None:
    state = fixture_state()
    packet = PACKET.build_causal_packet(BASE.QC, state)
    assert packet is not None
    unit = BASE.QC.exact_causal_chains(state)[0]
    objects = {item.object_id: item for item in state.objects}
    target = objects[unit["semantic_target_id"]]
    criticism = objects[unit["criticism_id"]]
    witness = BASE.QC._criticism_witness(criticism.payload)

    assert packet["target_schema"]["payload"] == target.payload
    assert packet["current_grounding"] == witness["grounding_state"]
    assert packet["grounding_diagnostics"]["witness"]["grounding_count"] == 6
    assert packet["grounding_diagnostics"]["witness"]["effect_pair_count"] == 3

    table = packet["executed_probe_judgments"]
    probes = [dict(zip(table["probe_columns"], row)) for row in table["probes"]]
    bindings = [dict(zip(table["binding_columns"], row)) for row in table["bindings"]]
    judgments = [dict(zip(table["judgment_columns"], row)) for row in table["judgments"]]
    decoded = PACKET.decode_probe_judgments(packet)
    assert table["counts"] == {
        "probes": 4,
        "judgments": 12,
        "supports": 8,
        "unresolved": 4,
    }
    assert sum(bool(row["selected"]) for row in judgments) == 8
    assert sum(not bool(row["selected"]) for row in judgments) == 4
    assert len(bindings) == 3
    assert len(decoded) == 12
    assert all(
        {
            "evidence_id", "proposal_id", "transition_id", "before_frame_id",
            "after_frame_id", "binding_id", "candidate_id", "effect_pair",
            "prediction_object_id", "current_residual", "predicted_delta",
            "predicted_residual", "observed_delta", "observed_residual",
            "horizon", "selected", "verdict", "reason",
        } <= set(row)
        for row in decoded
    )

    prediction_ids = set()
    for row in judgments:
        probe = probes[row["probe_index"]]
        binding = bindings[row["binding_index"]]
        evidence = objects[probe["evidence_id"]]
        proposal = objects[probe["proposal_id"]]
        transition = objects[probe["transition_id"]]
        prediction = objects[row["prediction_object_id"]]
        canonical_judgment = next(
            item
            for item in evidence.payload["prospective"]["judgments"]
            if item["prediction_id"] == row["prediction_id"]
        )
        prediction_ids.add(prediction.object_id)
        assert binding["binding_id"] == canonical_judgment["binding_id"]
        assert binding["candidate_id"] == prediction.payload["candidate_id"]
        assert binding["effect_pair"] == objects[binding["graph_binding_id"]].payload["effect_pair"]
        assert row["current_residual"] == prediction.payload["current_residual"]
        assert row["predicted_delta"] == canonical_judgment["predicted_delta"]
        assert row["predicted_residual"] == canonical_judgment["predicted_residual"]
        assert row["observed_delta"] == canonical_judgment["observed_delta"]
        assert row["observed_residual"] == canonical_judgment["observed_residual"]
        assert row["horizon"] == prediction.payload["horizon"]
        assert row["selected"] == (
            row["prediction_id"] in proposal.payload["selected_prediction_ids"]
        )
        assert row["verdict"] == canonical_judgment["status"]
        assert row["reason"] == canonical_judgment["reason"]
        assert probe["before_frame_id"] == transition.payload["before_frame"]
        assert probe["after_frame_id"] == transition.payload["after_frame"]

    ancestry_columns = packet["node_ancestry"]["columns"]
    ancestry = {
        row[0]: dict(zip(ancestry_columns, row))
        for row in packet["node_ancestry"]["rows"]
    }
    required_ids = {
        unit["derivation_id"],
        unit["semantic_target_id"],
        unit["criticism_id"],
        *(row["evidence_id"] for row in probes),
        *(row["proposal_id"] for row in probes),
        *(row["transition_id"] for row in probes),
        *(row["before_frame_id"] for row in probes),
        *(row["after_frame_id"] for row in probes),
        *prediction_ids,
    }
    assert required_ids <= set(ancestry)
    for object_id, row in ancestry.items():
        canonical = objects[object_id]
        assert row["dependencies"] == list(canonical.dependency_ids)
        assert row["kind"] == canonical.kind
        assert row["revision"] == canonical.created_revision

    # Direct ancestry is retained, but an off-packet dependency is not silently
    # pulled in.  This is the exact boundary that avoids recursive closure.
    external = {
        dependency
        for row in ancestry.values()
        for dependency in row["dependencies"]
        if dependency not in ancestry
    }
    assert external


def test_packet_is_deterministic_and_fits_frozen_frontier_budget() -> None:
    state = fixture_state()
    first = PACKET.build_causal_packet(BASE.QC, state)
    second = PACKET.build_causal_packet(BASE.QC, state)
    assert first == second
    assert first is not None
    assert first["packet_digest"] == BASE.QC.stable_hash(
        {key: value for key, value in first.items() if key != "packet_digest"}
    )
    assert BASE.QC.GRAPH.estimate_tokens(first) < 6400
    assert len(json.dumps(first, sort_keys=True, separators=(",", ":"))) < 24576


def test_fixture_builds_compiler_compatible_revision_turn_below_budget() -> None:
    state = fixture_state()
    orientation = BASE.QC.Orientation(
        workspace_id="fixture-workspace",
        initialized=True,
        cursor_revision=state.revision,
        cursor_hash=state.head_hash,
    )
    turn = PACKET.build_revision_turn(
        BASE.QC,
        state,
        orientation,
        request_id="fixture-revision",
        token_budget=6400,
        compact_ids=True,
    )
    assert turn is not None
    assert turn.mode == "causal-revision-packet"
    assert turn.document["sparse_cut"]["used_tokens"] < 6400
    assert turn.document["sparse_cut"]["used_tokens"] == BASE.QC.GRAPH.estimate_tokens(
        turn.document
    )
    assert turn.document["sparse_cut"]["dependency_closed"] is False
    schema = BASE.QC.response_schema(turn)
    assert schema.get("type") == "object" or "oneOf" in schema
    assert turn.document["revision_task"]["criticism_status"] == PACKET.STATUS
    evidence = set(turn.validation_context["causal_prospective_evidence_ids"])
    visible = {item["id"] for item in turn.document["sparse_cut"]["objects"]}
    assert evidence <= visible
    assert turn.validation_context["relation_evidence_id"] in visible


def test_revision_packet_builder_never_traverses_dependency_closure() -> None:
    state = fixture_state()
    orientation = BASE.QC.Orientation(
        workspace_id="fixture-workspace",
        initialized=True,
        cursor_revision=state.revision,
        cursor_hash=state.head_hash,
    )
    original = BASE.QC.GRAPH.dependency_closure

    def forbidden(*_args, **_kwargs):
        raise AssertionError("revision packet must not expand graph closure")

    BASE.QC.GRAPH.dependency_closure = forbidden
    try:
        turn = PACKET.build_revision_turn(
            BASE.QC,
            state,
            orientation,
            request_id="fixture-no-closure",
            token_budget=6400,
            compact_ids=True,
        )
    finally:
        BASE.QC.GRAPH.dependency_closure = original
    assert turn is not None
