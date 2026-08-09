from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
V111 = HERE.parent / "parallel-cognitive-workspace-v1-11"
TURN_BLOB = V111 / "artifacts/workspaces/generic_prospective--ar25--shared_live_qwen/blobs/sha256/79ac5bc87ffb54d61112649f77b11bba2cf6636aad6d35cb7cbee6264290f5ec.json"


def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


EXPERIMENT = load("workspace_v113_test", HERE / "experiment.py")
QC = EXPERIMENT.BASE.QC


def ambiguity_turn():
    return QC.CognitionTurn(**json.loads(TURN_BLOB.read_text(encoding="utf-8")))


def test_preprobe_revision_requires_relation_but_not_prospective_address() -> None:
    turn = ambiguity_turn()
    assert turn.document["revision_task"] is not None
    assert "causal_revision_packet" not in turn.document
    schema = QC.response_schema(turn)
    revision = schema["oneOf"][0]["properties"]["revision"]
    assert "relation_evidence_id" in revision["required"]
    assert "prospective_evidence_id" not in revision["required"]
    assert "evidence_ids" not in revision["properties"]
    payload = QC.request_payload(turn, EXPERIMENT.load_config()["qwen"])
    assert "pre-probe grounding repair" in payload["messages"][0]["content"]


def test_postprobe_packet_still_requires_both_address_classes() -> None:
    root = V111 / "artifacts/workspaces/generic_prospective--ar25--shared_live_qwen"
    state = EXPERIMENT.BASE.graph_state(root)[0]
    orientation = QC.Orientation(
        workspace_id="postprobe-fixture", initialized=True,
        cursor_revision=state.revision, cursor_hash=state.head_hash,
    )
    turn = EXPERIMENT.V112_MODULE.PACKET.build_revision_turn(
        QC, state, orientation, request_id="postprobe", token_budget=6400,
        compact_ids=True,
    )
    revision = QC.response_schema(turn)["oneOf"][0]["properties"]["revision"]
    assert {"relation_evidence_id", "prospective_evidence_id"} <= set(revision["required"])
