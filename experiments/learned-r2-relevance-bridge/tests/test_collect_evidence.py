from __future__ import annotations

import json
import sys
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))

from collect_evidence import collect  # noqa: E402


def observation(index: int, grid: list[list[int]]) -> dict[str, object]:
    return {
        "event": "observation",
        "observation": index,
        "supports": [{"ordinal": 0, "grid": grid}],
    }


def test_collector_reconstructs_effect_from_grids_after_progress_is_observed(
    tmp_path: Path,
) -> None:
    before = [[0] * 5 for _ in range(5)]
    after = [[0] * 5 for _ in range(5)]
    before[2][2] = 1
    after[2][3] = 1
    events = [
        observation(0, before),
        {
            "event": "transition",
            "transition": 0,
            "before": 0,
            "after": 1,
            "action": {"id": 4, "token": "arc-action:4", "data": {}},
            "progress_delta": 1,
        },
        observation(1, after),
    ]
    path = tmp_path / "public-baseline.trace.jsonl"
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )

    records, report = collect((path,))
    assert len(records) == 1
    assert records[0].progress_delta == 1
    assert records[0].outcome == "positive"
    assert records[0].consequence
    assert {head for head, _arguments in records[0].consequence} == {"Preserve"}
    assert "arc-action" not in repr(records[0].consequence)
    assert report["positive_progress_records"] == 1


def test_collector_rejects_traces_without_grid_support(tmp_path: Path) -> None:
    path = tmp_path / "omitted.trace.jsonl"
    events = [
        {
            "event": "observation",
            "observation": 0,
            "supports": [{"ordinal": 0, "shape": [5, 5]}],
        },
        {
            "event": "transition",
            "transition": 0,
            "before": 0,
            "after": 1,
            "action": {"id": 1, "token": "arc-action:1", "data": {}},
            "progress_delta": 1,
        },
        {
            "event": "observation",
            "observation": 1,
            "supports": [{"ordinal": 0, "shape": [5, 5]}],
        },
    ]
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    try:
        collect((path,))
    except ValueError as error:
        assert "omits its grid" in str(error)
    else:
        raise AssertionError("grid-less trace was accepted")


def test_collector_accepts_official_arc_recording_packets(tmp_path: Path) -> None:
    before = [[0] * 5 for _ in range(5)]
    after = [[0] * 5 for _ in range(5)]
    before[2][2] = 1
    after[2][3] = 1
    packets = [
        {
            "timestamp": "before",
            "data": {
                "frame": [before],
                "levels_completed": 0,
                "full_reset": False,
                "action_input": {"id": 0, "data": {}},
            },
        },
        {
            "timestamp": "after",
            "data": {
                "frame": [after],
                "levels_completed": 1,
                "full_reset": False,
                "action_input": {"id": 3, "data": {}},
            },
        },
    ]
    path = tmp_path / "public.recording.jsonl"
    path.write_text(
        "".join(json.dumps(packet) + "\n" for packet in packets), encoding="utf-8"
    )
    records, report = collect((path,))
    assert len(records) == 1
    assert records[0].progress_delta == 1
    assert records[0].opaque_action_id == 3
    assert report["traces"][0]["format"] == "arc-toolkit-recording"
