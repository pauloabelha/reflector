import pytest

from scripts.black_box_ascii_play import (
    normalize_frame,
    parse_action,
    render_ascii,
    summarize_diff,
    systematic_probe_actions,
)


def test_ascii_renderer_and_diff_preserve_observable_values() -> None:
    before = ((0, 0, 2), (0, 3, 2))
    after = ((0, 2, 2), (0, 3, 4))

    rendered = render_ascii(before, max_height=2)
    diff = summarize_diff(before, after)

    assert "size=3x2" in rendered
    assert "0=0" in rendered
    assert "1=2" in rendered
    assert "2=3" in rendered
    assert diff.changed_pixels == 2
    assert diff.bbox == (1, 0, 2, 1)
    assert dict(diff.transitions) == {"0->2": 1, "2->4": 1}


def test_normalize_frame_selects_last_animation_frame() -> None:
    assert normalize_frame([[[0, 0]], [[1, 1]]]) == ((1, 1),)


def test_action_parser_rejects_nonprotocol_semantics() -> None:
    assert parse_action("3") == (3, {})
    assert parse_action("6:12:9") == (6, {"x": 12, "y": 9})
    with pytest.raises(ValueError, match="invalid action"):
        parse_action("north")


def test_systematic_probe_uses_roles_not_fixed_coordinates() -> None:
    frame = (
        (0, 0, 0, 0, 0, 0),
        (0, 2, 0, 3, 3, 0),
        (0, 0, 0, 3, 3, 0),
    )
    actions = systematic_probe_actions(frame, (1, 2, 6))
    assert actions[:2] == ((1, {}), (2, {}))
    assert (6, {"x": 1, "y": 1}) in actions
    assert (6, {"x": 3, "y": 1}) in actions
