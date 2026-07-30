from __future__ import annotations

from scripts.audit_action_translation_algebra import _action, _frame


def test_audit_normalizes_nested_frames_and_strips_game_identity() -> None:
    frame = _frame([[[[0, 2], [0, 0]]]])
    action = _action(
        {
            "id": 6,
            "data": {
                "game_id": "forbidden",
                "x": 3,
                "y": 4,
            },
        }
    )

    assert frame == ((0, 2), (0, 0))
    assert action is not None
    assert action.payload == (("x", 3), ("y", 4))
