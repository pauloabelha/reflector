from __future__ import annotations

import importlib.util
import hashlib
import json
from pathlib import Path
import sys


HERE = Path(__file__).resolve().parent


def load_analyzer():
    spec = importlib.util.spec_from_file_location(
        "click_causal_attribution_test", HERE / "click_causal_attribution.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def command(*, x=1, y=1):
    return {
        "protocol": "action-command-v1", "action_id": 6,
        "command_id": f"click:{x}:{y}", "data": {"x": x, "y": y},
        "effect_scope_id": "scope:test",
        "payload_grounding": {
            "kind": "observed-region-cell", "cell_rc": [y, x],
            "frame_digest": "frame:test", "region_binding_id": "binding:test",
            "region_structural_key": [2, 1, [[0, 0]]],
        },
    }


def envelope(*frames, settled=None):
    ordinal = len(frames) - 1 if settled is None else settled
    supports = list(frames)
    digests = [hashlib.sha256(json.dumps(
        frame, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest() for frame in supports]
    body = {
        "protocol": "ordered-observation-envelope-v1",
        "ordered_frames": supports, "support_digests": digests,
        "support_count": len(frames),
        "settled_support_ordinal": ordinal,
        "settled_support_digest": digests[ordinal],
    }
    return {**body, "digest": hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()}


def test_unchanged_settled_successor_never_infers_transient_effect():
    analyzer = load_analyzer()
    before = [[0, 0, 0], [0, 2, 0], [0, 0, 0]]
    transient = [[0, 0, 0], [0, 0, 2], [0, 0, 0]]
    result = analyzer.attribute_click(
        command(), before, envelope(transient, before),
    )

    assert result["classification"] == "abstain"
    assert result["reason"] == "settled-successor-unchanged"
    assert result["transient_change_observed"] is True
    assert result["effect_footprints"] == []


def test_one_connected_ordered_change_footprint_is_unique_observation_only():
    analyzer = load_analyzer()
    before = [[0, 0, 0], [0, 2, 0], [0, 0, 0]]
    middle = [[0, 0, 0], [0, 0, 2], [0, 0, 0]]
    after = [[0, 0, 0], [0, 0, 0], [0, 0, 2]]
    result = analyzer.attribute_click(command(), before, envelope(middle, after))

    assert result["classification"] == "unique"
    assert result["reason"] == "one-connected-observed-change-footprint"
    assert result["authority"] == "shadow-only-no-control-or-graph-authority"
    assert result["effect_footprints"] == [{
        "cell_count": 3, "bbox_rc": [1, 1, 2, 2],
        "contains_clicked_cell": True, "minimum_manhattan_from_click": 0,
    }]


def test_disconnected_change_footprints_remain_ambiguous():
    analyzer = load_analyzer()
    before = [[1, 0, 0, 0, 2]]
    after = [[3, 0, 0, 0, 4]]
    result = analyzer.attribute_click(
        command(x=0, y=0), before, envelope(after),
    )

    assert result["classification"] == "ambiguous"
    assert result["reason"] == "multiple-disconnected-observed-change-footprints"
    assert len(result["effect_footprints"]) == 2


def test_inexact_grounding_and_transport_mismatch_fail_to_abstention():
    analyzer = load_analyzer()
    exact = command()
    wrong_grounding = {**exact, "payload_grounding": {**exact["payload_grounding"], "cell_rc": [0, 0]}}
    assert analyzer.attribute_click(
        wrong_grounding, [[0, 0], [0, 2]], envelope([[0, 0], [0, 3]]),
    )["reason"] == "inexact-click-grounding"
    assert analyzer.attribute_click(
        exact, [[0, 0], [0, 2]], envelope([[0, 0], [0, 3]]),
        committed_data={"x": 0, "y": 0},
    )["reason"] == "decision-pending-commit-mismatch"
    corrupt_envelope = envelope([[0, 0], [0, 3]])
    corrupt_envelope["digest"] = "not-the-exact-envelope-digest"
    assert analyzer.attribute_click(
        exact, [[0, 0], [0, 2]], corrupt_envelope,
    )["reason"] == "invalid-observation-envelope-digest"


def test_run_aggregate_replays_exact_durable_click_and_omits_rows(tmp_path):
    analyzer = load_analyzer()
    episode = tmp_path / "episodes" / "pass-01--xy00--level-01"
    workspace = episode / "workspaces" / "workspace"
    events = workspace / "events"
    blobs = workspace / "blobs" / "sha256"
    events.mkdir(parents=True)
    blobs.mkdir(parents=True)
    exact = command(x=0, y=0)
    decision_hash, before_hash, after_hash = "decision", "before", "after"
    (blobs / f"{decision_hash}.json").write_text(json.dumps({
        "selected_command": exact,
    }), encoding="utf-8")
    (blobs / f"{before_hash}.json").write_text(json.dumps({
        "grid": [[1, 0]],
    }), encoding="utf-8")
    (blobs / f"{after_hash}.json").write_text(json.dumps({
        "grid": [[2, 0]],
        "observation_envelope": envelope([[2, 0]]),
    }), encoding="utf-8")
    (events / "00000000.json").write_text(json.dumps({
        "event_id": "pending", "event_type": "ActionPending",
        "payload": {"action_id": 6, "data": exact["data"], "decision_blob": decision_hash},
    }), encoding="utf-8")
    (events / "00000001.json").write_text(json.dumps({
        "event_id": "commit", "event_type": "TransitionCommitted", "seq": 1,
        "payload": {
            "action_id": 6, "data": exact["data"], "pending_event_id": "pending",
            "before_blob": before_hash, "after_blob": after_hash,
        },
    }), encoding="utf-8")

    report = analyzer.analyze_run(tmp_path)

    assert report["games_analyzed"] == 1
    assert report["games_with_clicks"] == 1
    assert report["click_transitions"] == 1
    assert report["classification_counts"] == {"unique": 1}
    assert report["games"][0]["game"] == "xy00"
    assert "rows" not in report["games"][0]
