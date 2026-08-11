from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def load(name: str, path: Path):
    resolved = path.resolve()
    for existing in reversed(tuple(sys.modules.values())):
        existing_file = getattr(existing, "__file__", None)
        if existing_file is not None and Path(existing_file).resolve() == resolved:
            return existing
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PACKET = load("ambiguity_packet_v120_test", HERE / "ambiguity_packet.py")
EXPERIMENT = load("ambiguity_packet_experiment_v120_test", HERE / "experiment.py")
V112_PACKET = load(
    "ambiguity_packet_v112_regression_test",
    ROOT / "parallel-cognitive-workspace-v1-12/causal_packet.py",
)


@pytest.fixture(scope="module", params=[("18", 6400, 9843, 9), ("19", 10000, 10841, 12)])
def frozen(request):
    version, legacy_budget, legacy_required, alternative_count = request.param
    directory = ROOT / f"parallel-cognitive-workspace-v1-{version}"
    workspace = (
        directory
        / "artifacts/workspaces/generic_prospective--wa30--shared_live_qwen"
    )
    state, events = EXPERIMENT.BASE.rebuild_graph(workspace)
    orientation = EXPERIMENT.BASE.QC.latest_orientation(state, workspace.name)
    assert orientation is not None
    return {
        "version": version,
        "base": EXPERIMENT.BASE,
        "state": state,
        "events": events,
        "orientation": orientation,
        "legacy_budget": legacy_budget,
        "legacy_required": legacy_required,
        "alternative_count": alternative_count,
    }


def test_frozen_frontier_failure_is_reproduced(frozen) -> None:
    base = frozen["base"]
    # Dynamic experiment loading gives the same exception implementation a
    # distinct Python class identity, so assert its stable public contract.
    with pytest.raises(Exception) as raised:
        base.QC.sparse_cut(
            frozen["state"],
            token_budget=frozen["legacy_budget"],
            focus_ids=frozen["orientation"].focus_ids,
            expansion_ids=frozen["orientation"].expansion_ids,
        )
    assert type(raised.value).__name__ == "FrontierBudgetError"
    assert str(frozen["legacy_required"]) in str(raised.value)


def test_packet_is_bounded_and_orientation_independent(frozen) -> None:
    base = frozen["base"]
    state = frozen["state"]
    orientation = frozen["orientation"]
    turn = PACKET.build_turn(
        base.QC,
        state,
        orientation,
        request_id="fixture",
        token_budget=6400,
        compact_ids=True,
    )
    assert turn is not None
    assert turn.mode == PACKET.MODE
    assert turn.document["sparse_cut"]["used_tokens"] <= 6400
    assert len(
        turn.document["ambiguity_revision_packet"]["live_alternatives"]["rows"]
    ) == frozen["alternative_count"]

    no_focus = replace(orientation, focus_ids=(), expansion_ids=())
    second = PACKET.build_turn(
        base.QC,
        state,
        no_focus,
        request_id="fixture",
        token_budget=6400,
        compact_ids=True,
    )
    assert second is not None
    assert (
        second.document["ambiguity_revision_packet"]["packet_digest"]
        == turn.document["ambiguity_revision_packet"]["packet_digest"]
    )
    assert second.document["sparse_cut"]["used_tokens"] == turn.document["sparse_cut"]["used_tokens"]


def test_all_live_alternatives_round_trip_exactly(frozen) -> None:
    base = frozen["base"]
    state = frozen["state"]
    packet = PACKET.build_packet(base.QC, state)
    assert packet is not None
    decoded = PACKET.decode_live_alternatives(packet)
    objects = {item.object_id: item for item in state.objects}
    unit = packet["causal_unit"]
    target_id = unit["semantic_target_id"]
    expected = sorted(
        (
            item
            for item in state.objects
            if item.object_id in set(base.EG.live_binding_ids(state))
            and item.kind == "binding"
            and item.payload.get("schema_object_id") == target_id
        ),
        key=lambda item: item.object_id,
    )
    assert len(decoded) == len(expected) == frozen["alternative_count"]
    for row, item in zip(decoded, expected, strict=True):
        assert row == {
            "id": item.object_id,
            "identity": dict(item.identity),
            "payload": dict(item.payload),
        }

    criticism = objects[unit["criticism_id"]]
    witness = criticism.payload["structured_witness"]
    canonical_candidates = {
        item["candidate_id"] for item in witness.get("candidates", ())
    }
    decoded_candidates = {item["payload"]["candidate_id"] for item in decoded}
    assert decoded_candidates == canonical_candidates


def test_causal_relation_and_grounding_are_exact_and_compiler_visible(frozen) -> None:
    base = frozen["base"]
    state = frozen["state"]
    orientation = frozen["orientation"]
    turn = PACKET.build_turn(
        base.QC,
        state,
        orientation,
        request_id="fixture",
        token_budget=6400,
        compact_ids=True,
    )
    assert turn is not None
    # Building the strict response grammar exercises the visible criticism,
    # target schema, relation facts, entity IDs, and causal task addresses.
    schema = base.QC.response_schema(turn)
    assert len(schema["oneOf"]) == 2
    abstention = {"abstain": True}
    compiled = base.QC.compile_response(abstention, turn)
    assert compiled["valid_json_contract"] is True
    assert compiled["rejected"] == []

    aliases = dict(turn.id_aliases)
    rendered_relation = turn.document["ambiguity_revision_packet"]["current_grounding"][
        "relation_set_id"
    ]
    relation_id = aliases.get(rendered_relation, rendered_relation)
    relation = next(item for item in state.objects if item.object_id == relation_id)
    visible = {
        aliases.get(item["id"], item["id"]): item
        for item in turn.document["sparse_cut"]["objects"]
    }
    decoded_payload = base.QC._replace_ids(visible[relation_id]["payload"], aliases)
    assert decoded_payload == dict(relation.payload)
    assert len(relation.payload["relations"]) == 64


def test_install_is_idempotent_and_fallback_is_preserved(frozen) -> None:
    del frozen
    qc = SimpleNamespace(build_turn=lambda *_args, **_kwargs: "fallback")
    PACKET.install(qc)
    first = qc.build_turn
    PACKET.install(qc)
    assert qc.build_turn is first


def test_live_v120_failure_is_a_distinct_unique_grounding_phase() -> None:
    """The ambiguity adapter must not claim to repair an evidence-only bug."""

    workspace = (
        HERE
        / "artifacts/workspaces/generic_prospective--wa30--shared_live_qwen"
    )
    state, _events = EXPERIMENT.BASE.rebuild_graph(workspace)
    units = EXPERIMENT.BASE.QC.exact_causal_chains(state)
    assert len(units) == 1
    unit = units[0]
    assert unit["criticism_status"] == "prospective-evidence-return"
    assert not any(
        item.kind == "structured_criticism"
        and item.payload.get("status") == "ambiguous-grounding"
        for item in state.objects
    )
    target_id = unit["semantic_target_id"]
    target_bindings = [
        item
        for item in state.objects
        if item.kind == "binding"
        and item.payload.get("schema_object_id") == target_id
    ]
    assert len(target_bindings) == 1
    assert target_bindings[0].payload["status"] == "bound"
    assert target_bindings[0].payload["effect_pair_count"] == 1

    # Correct phase routing: this adapter declines the turn. The inherited
    # v1.12 packet then exposes its independent invalid assumption that every
    # evidence-return chain must have begun ambiguous.
    assert PACKET.build_packet(EXPERIMENT.BASE.QC, state) is None
    with pytest.raises(Exception) as raised:
        V112_PACKET.build_causal_packet(EXPERIMENT.BASE.QC, state)
    assert type(raised.value).__name__ == "CausalPacketError"
    assert "original ambiguity diagnosis is unavailable" in str(raised.value)
