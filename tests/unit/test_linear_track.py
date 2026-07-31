from __future__ import annotations

from reflector.core.exploration import ActionToken, EpistemicExplorer
from reflector.core.linear_track import infer_linear_track
from reflector.core.symbolic import Observation

type Frame = tuple[tuple[int, ...], ...]


def _track_frame(marker_x: int) -> Frame:
    grid = [[5 for _x in range(40)] for _y in range(20)]
    for y in range(8, 11):
        for x in range(6, 30):
            grid[y][x] = 2
    for x in range(2, 6):
        grid[7][x] = 9
        grid[11][x] = 9
    for y in range(8, 11):
        grid[y][2] = 9
        grid[y][5] = 9
    for y in range(8, 10):
        for x in range(marker_x, marker_x + 2):
            grid[y][x] = 9
    return tuple(tuple(row) for row in grid)


def test_infers_unique_marker_and_framed_track_endpoint() -> None:
    layout = infer_linear_track(_track_frame(28))

    assert layout is not None
    assert layout.target == (3, 9)
    assert layout.marker == (28, 8)
    assert layout.distance > 0


def test_compiles_and_replays_only_a_distance_decreasing_action() -> None:
    before = _track_frame(28)
    after = _track_frame(24)
    explorer = EpistemicExplorer(linear_track_navigation=True)

    explorer._observe_linear_track(before, after, 2)
    selected = explorer._select_linear_track(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(1, 2),
            frame=after,
        ),
        (ActionToken(1), ActionToken(2)),
    )

    assert explorer.track_macro == (2,)
    assert explorer.track_compilations == 1
    assert selected == ActionToken(2)
