from __future__ import annotations

from reflector.core.constellation_alignment import (
    infer_constellation_alignment,
)
from reflector.core.exploration import ActionToken, EpistemicExplorer
from reflector.core.symbolic import Observation

type Frame = tuple[tuple[int, ...], ...]


def _draw_plus(
    grid: list[list[int]],
    center: tuple[int, int],
    color: int,
    *,
    selected: bool,
) -> None:
    x, y = center
    for offset in range(-5, 6):
        if offset:
            grid[y][x + offset] = color
            grid[y + offset][x] = color
    grid[y][x] = 0 if selected else color


def _draw_ring(
    grid: list[list[int]],
    center: tuple[int, int],
    center_color: int,
) -> None:
    x, y = center
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            grid[y + dy][x + dx] = 4
    grid[y][x] = center_color


def _frame(
    *,
    red: tuple[int, int] = (36, 45),
    white: tuple[int, int] = (21, 27),
    selected: int = 9,
) -> Frame:
    grid = [[5 for _x in range(64)] for _y in range(64)]
    landmarks = {
        9: ((48, 16), (40, 24), (53, 24), (48, 35)),
        11: ((15, 3), (6, 9), (24, 9), (15, 17)),
    }
    for color, points in landmarks.items():
        for point in points:
            _draw_ring(grid, point, color)
    _draw_plus(grid, red, 9, selected=selected == 9)
    _draw_plus(grid, white, 11, selected=selected == 11)
    return tuple(tuple(row) for row in grid)


def test_infers_cross_targets_from_colored_landmark_intersections() -> None:
    layout = infer_constellation_alignment(_frame())

    assert layout is not None
    assert layout.selected_color == 9
    assert {
        item.color: (item.center, item.target)
        for item in layout.objects
    } == {
        9: ((36, 45), (48, 24)),
        11: ((21, 27), (15, 9)),
    }


def test_learns_translation_and_switch_controls_from_interventions() -> None:
    explorer = EpistemicExplorer(constellation_alignment=True)
    start = _frame()
    moved = _frame(red=(36, 42))
    switched = _frame(red=(36, 42), selected=11)

    explorer._observe_constellation_alignment(start, moved, 1)
    explorer._observe_constellation_alignment(moved, switched, 5)

    assert explorer.constellation_move_actions == {1: (0, -3)}
    assert explorer.constellation_switch_actions == {5}


def test_selects_grounded_move_then_switches_only_after_target_satisfaction() -> None:
    explorer = EpistemicExplorer(constellation_alignment=True)
    explorer.constellation_move_actions = {
        1: (0, -3),
        2: (0, 3),
        3: (-3, 0),
        4: (3, 0),
    }
    explorer.constellation_switch_actions = {5}
    tokens = tuple(ActionToken(action) for action in range(1, 6))

    selected = explorer._select_constellation_alignment(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=range(1, 6),
            frame=_frame(),
        ),
        tokens,
    )
    assert selected == ActionToken(1)

    selected = explorer._select_constellation_alignment(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=range(1, 6),
            frame=_frame(red=(48, 24)),
        ),
        tokens,
    )
    assert selected == ActionToken(5)
