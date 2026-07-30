from __future__ import annotations

import json
from pathlib import Path

import pytest

from reflector.core.exploration import ActionToken, EpistemicExplorer
from reflector.core.mind import MindConfig
from reflector.core.perception import SceneTracker
from reflector.core.symbolic import Event, Observation
from reflector.research.event_audit import (
    ACTION_EFFECT_CONTEXT_CHANGE,
    audit_recording,
    structural_effect_signature,
)


def _frame(x: int) -> list[list[int]]:
    frame = [[0 for _ in range(9)] for _ in range(9)]
    frame[3][x] = 8
    frame[5][x] = 8
    return frame


def _row(frame: list[list[int]], action: int) -> str:
    return json.dumps(
        {
            "data": {
                "frame": [frame],
                "state": "NOT_FINISHED",
                "levels_completed": 0,
                "available_actions": [1, 2],
                "action_input": {"id": action},
            }
        }
    )


def test_structural_effect_signature_removes_identity_and_scale() -> None:
    left = structural_effect_signature(
        (Event("object_moved", "o1", ("4", "0")),)
    )
    right = structural_effect_signature(
        (Event("object_moved", "other", ("1", "0")),)
    )

    assert left == right == ("object_moved(1,0)",)


def test_recording_audit_preregisters_before_detecting_discontinuity(
    tmp_path: Path,
) -> None:
    recording = tmp_path / "game.agent.guid.recording.jsonl"
    recording.write_text(
        "\n".join(
            (
                _row(_frame(1), 1),
                _row(_frame(2), 1),
                _row(_frame(3), 1),
                _row(_frame(4), 1),
                _row(_frame(2), 1),
            )
        )
        + "\n",
        encoding="utf-8",
    )

    audit = audit_recording(recording)

    assert audit.transitions == 4
    assert audit.supported_predictions == 2
    assert audit.confirmations == 1
    assert len(audit.occurrences) == 1
    occurrence = audit.occurrences[0]
    assert occurrence.event_id == ACTION_EFFECT_CONTEXT_CHANGE.event_id
    assert occurrence.step == 4
    assert occurrence.group_arity == 2
    assert occurrence.prior_support == 3
    assert occurrence.expected_effect == ("repeated_form_effect(1,0|1,0)",)
    assert occurrence.observed_effect == ("repeated_form_effect(-1,0|-1,0)",)


def test_level_boundary_cannot_create_discontinuity(tmp_path: Path) -> None:
    recording = tmp_path / "game.agent.guid.recording.jsonl"
    rows = [
        json.loads(_row(_frame(1), 1)),
        json.loads(_row(_frame(2), 1)),
        json.loads(_row(_frame(3), 1)),
        json.loads(_row(_frame(1), 1)),
    ]
    rows[-1]["data"]["levels_completed"] = 1
    recording.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n",
        encoding="utf-8",
    )

    audit = audit_recording(recording)

    assert audit.occurrences == ()


def test_affordance_event_preregisters_one_exact_confirmation() -> None:
    explorer = EpistemicExplorer(
        repeated_form_event_mode="confirm-affordance"
    )
    token = ActionToken(1)
    still = tuple(tuple(row) for row in _frame(2))
    moved = tuple(tuple(row) for row in _frame(3))

    explorer._observe_repeated_form_effect_event(still, still, token)
    explorer._observe_repeated_form_effect_event(still, still, token)
    explorer._observe_repeated_form_effect_event(still, moved, token)

    assert explorer.repeated_form_event_detections == 1
    assert explorer.repeated_form_confirmation_token == token
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1,),
        frame=moved,
    )
    scene, _events = SceneTracker().perceive(observation)
    choice = explorer.select(observation, scene, (1,))
    assert choice.token == token
    assert "confirm-repeated-form-event" in choice.reason
    assert explorer.repeated_form_confirmation_token is None
    assert explorer.repeated_form_event_replays == 1


def test_phase_event_changes_belief_key_without_replaying() -> None:
    explorer = EpistemicExplorer(repeated_form_event_mode="phase-segment")
    token = ActionToken(1)
    still = tuple(tuple(row) for row in _frame(2))
    moved = tuple(tuple(row) for row in _frame(3))
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1,),
        frame=moved,
    )
    scene, _events = SceneTracker().perceive(observation)
    before_key = explorer._state_key(observation, scene)

    explorer._observe_repeated_form_effect_event(still, still, token)
    explorer._observe_repeated_form_effect_event(still, still, token)
    explorer._observe_repeated_form_effect_event(still, moved, token)

    assert explorer.repeated_form_event_phase == 1
    assert explorer.repeated_form_confirmation_token is None
    assert explorer._state_key(observation, scene) != before_key


def test_repeated_form_event_mode_is_constrained() -> None:
    with pytest.raises(ValueError, match="repeated_form_event_mode"):
        MindConfig(repeated_form_event_mode="unbounded-surprise")
