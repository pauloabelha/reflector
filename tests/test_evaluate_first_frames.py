from __future__ import annotations

import json
from pathlib import Path

import pytest

from reflector2.evaluate_first_frames import (
    discover_recordings,
    evaluate_recordings,
    evaluate_transfer_matrix,
)


def _write_recording(path: Path, grid: list[list[int]]) -> None:
    path.write_text(json.dumps({"data": {"frame": [grid]}}) + "\n", encoding="utf-8")


def test_evaluates_one_first_frame_per_game(tmp_path: Path) -> None:
    _write_recording(tmp_path / "aa01.agent.first.recording.jsonl", [[0, 1], [0, 1]])
    _write_recording(tmp_path / "bb02.agent.second.recording.jsonl", [[0, 2], [2, 0]])

    report = evaluate_recordings(tmp_path, expected_games=2, workers=2)

    assert [game["game"] for game in report["games"]] == ["aa01", "bb02"]
    assert report["aggregate"]["games_succeeded"] == 2
    assert report["aggregate"]["games_failed"] == 0
    assert report["aggregate"]["budget_passes"] == 2
    assert report["aggregate"]["shapes"] == {"2x2": 2}
    assert report["protocol"]["game_metadata_used"] is False
    assert report["protocol"]["workers"] == 2


def test_rejects_duplicate_game_recordings(tmp_path: Path) -> None:
    _write_recording(tmp_path / "aa01.agent.one.recording.jsonl", [[0]])
    _write_recording(tmp_path / "aa01.agent.two.recording.jsonl", [[0]])

    with pytest.raises(ValueError, match="duplicates: aa01=2"):
        discover_recordings(tmp_path)


def test_rejects_unexpected_game_count(tmp_path: Path) -> None:
    _write_recording(tmp_path / "aa01.agent.one.recording.jsonl", [[0]])

    with pytest.raises(ValueError, match="expected 25 games, found 1"):
        evaluate_recordings(tmp_path, expected_games=25)


def test_transfer_matrix_is_directed_and_excludes_kernel_only_matches(tmp_path: Path) -> None:
    # These distinct games share a form.  The source's form-specific and
    # composite rows should therefore bind in the target; generic kernel rows
    # are deliberately not counted as transfer.
    grid = [[0, 1, 0], [0, 1, 0], [0, 1, 0]]
    _write_recording(tmp_path / "aa01.agent.first.recording.jsonl", grid)
    _write_recording(tmp_path / "bb02.agent.second.recording.jsonl", grid)

    report = evaluate_transfer_matrix(tmp_path, expected_games=2)

    assert report["game_ids"] == ["aa01", "bb02"]
    assert report["aggregate"]["cells"] == 4
    cell = report["matrix"]["aa01"]["bb02"]
    assert cell["source"] == "aa01"
    assert cell["target"] == "bb02"
    assert cell["transfer_detected"] is True
    assert cell["preexisting_bound_schemas"] >= 1
    assert cell["verified_bindings"] >= cell["preexisting_bound_schemas"]
    assert cell["grounded_transfer_detected"] is True
    assert cell["preexisting_grounded_bound_schemas"] >= 1
    assert cell["baseline_target_schema_overlap"] >= 1
    assert cell["target_new_non_kernel_schemas"] >= 0

    # Matrix cells are graph-copy isolated, so a second run has exactly the
    # same structural results rather than retaining mutations from the first.
    assert evaluate_transfer_matrix(tmp_path, expected_games=2)["matrix"] == report["matrix"]
