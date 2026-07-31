import json
from pathlib import Path

from scripts.audit_terminal_viability_quotients import audit_root


def _event(
    *,
    digest: str,
    action: int,
    state: str = "NOT_FINISHED",
    with_transition: bool = True,
) -> dict[str, object]:
    return {
        "observation": {"frame_digest": digest, "state": state},
        "transition": (
            {
                "action_id": action,
                "action_data": {},
                "context": [
                    "action_available(1)",
                    "action_available(2)",
                    "object_signature(2,1,1,1,1,1)",
                ],
            }
            if with_transition
            else {}
        ),
    }


def test_audit_exposes_safe_aliases_in_coarse_terminal_quotient(
    tmp_path: Path,
) -> None:
    path = tmp_path / "game.cognitive.jsonl"
    events = [
        _event(digest="source-a", action=1, with_transition=False),
        _event(digest="source-b", action=1, state="GAME_OVER"),
        _event(digest="source-c", action=1, state="GAME_OVER"),
        _event(digest="source-d", action=1),
    ]
    path.write_text(
        "".join(json.dumps(event) + "\n" for event in events),
        encoding="utf-8",
    )

    result = audit_root(tmp_path)
    action = result["results"]["action"]

    assert action["candidate_edges"] == 1
    assert action["candidate_edges_without_safe_alias"] == 0
    assert action["prospective_confirmations"] == 1
    assert action["prospective_quarantines"] == 1
