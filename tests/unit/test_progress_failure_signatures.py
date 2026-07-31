from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_progress_failure_signatures import (
    audit_root,
    audit_stream,
)


def _event(
    *,
    level: int,
    state: str = "NOT_FINISHED",
    reason: str = "epistemic-frontier:probe",
    result: tuple[str, ...] = (),
) -> str:
    return json.dumps(
        {
            "observation": {
                "levels_completed": level,
                "state": state,
            },
            "decision": {"reason": reason},
            "transition": {"result": list(result)},
        }
    )


def test_audit_normalizes_progress_and_failure_motifs(tmp_path: Path) -> None:
    stream = tmp_path / "aa00.cognitive.jsonl"
    stream.write_text(
        "\n".join(
            (
                _event(level=0, reason="advisor:a"),
                _event(level=0, reason="advisor:a"),
                _event(
                    level=1,
                    reason="advisor:b",
                    result=("level_advanced(scene)", "object_moved(o1,1,0)"),
                ),
                _event(level=1, reason="advisor:c"),
                _event(
                    level=1,
                    state="GAME_OVER",
                    reason="reset-required",
                    result=("state_changed(GAME_OVER)",),
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    result = audit_stream(stream, motif_width=2)

    assert result["progress_events"] == 1
    assert result["failure_events"] == 1
    assert result["progress_advisors"] == {'"advisor:a"': 1}
    assert result["failure_advisors"] == {'"advisor:c"': 1}
    assert result["progress_effect_families"] == {
        '["level_advanced","object_moved"]': 1
    }
    assert result["failure_effect_families"] == {
        '["state_changed"]': 1
    }


def test_root_audit_aggregates_one_stream_per_game(tmp_path: Path) -> None:
    for game in ("aa00", "bb00"):
        (tmp_path / f"{game}.cognitive.jsonl").write_text(
            _event(level=0, reason="advisor:a")
            + "\n"
            + _event(level=1, reason="advisor:b")
            + "\n",
            encoding="utf-8",
        )

    result = audit_root(tmp_path, motif_width=1)

    assert result["games"] == 2
    assert result["progress_events"] == 2
    assert result["failure_events"] == 0
    assert result["progress_advisors"] == {'"advisor:a"': 2}
