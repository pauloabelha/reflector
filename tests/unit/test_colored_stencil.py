from __future__ import annotations

from reflector import MindConfig, SymbolicPolicy
from reflector.core.colored_stencil import (
    POSE_COORDINATES,
    PrimaryStencilPlanner,
    StencilScene,
    StencilToken,
    apply_primary_stencil,
    infer_stencil_scene,
    primary_mask,
)
from reflector.kaggle import OVERLAY_FILES

Grid = tuple[tuple[int, ...], ...]


def _solid(size: int, color: int) -> Grid:
    return tuple(tuple(color for _x in range(size)) for _y in range(size))


def _paint_grid(
    pixels: list[list[int]],
    grid: Grid,
    *,
    left: int,
    top: int,
) -> None:
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            pixels[top + y][left + x] = value


def _outline(
    pixels: list[list[int]],
    *,
    left: int,
    top: int,
    color: int,
) -> None:
    for offset in range(5):
        pixels[top][left + offset] = color
        pixels[top + 4][left + offset] = color
        pixels[top + offset][left] = color
        pixels[top + offset][left + 4] = color


def _frame(
    reference: Grid,
    construction: Grid,
    *,
    selected: int = 2,
    palette: tuple[int, ...] = (2, 3, 4),
    shift_x: int = 0,
    shift_y: int = 0,
) -> tuple[tuple[int, ...], ...]:
    pixels = [[0 for _x in range(70)] for _y in range(55)]
    for index, color in enumerate(palette):
        left = shift_x + 4 + index * 8
        top = shift_y + 3
        _outline(pixels, left=left, top=top, color=9)
        for y in range(top + 1, top + 4):
            for x in range(left + 1, left + 4):
                pixels[y][x] = color
    _paint_grid(pixels, reference, left=shift_x + 3, top=shift_y + 30)
    _paint_grid(pixels, construction, left=shift_x + 42, top=shift_y + 30)
    _outline(
        pixels,
        left=shift_x + 44,
        top=shift_y + 16,
        color=selected,
    )
    return tuple(tuple(row) for row in pixels)


def test_primary_masks_are_relational_half_planes() -> None:
    for size in (6, 9, 10):
        for pose in POSE_COORDINATES:
            mask = primary_mask(size, pose)
            assert len(mask) == size
            assert all(len(row) == size for row in mask)
            assert any(value for row in mask for value in row)
            assert any(not value for row in mask for value in row)
        assert primary_mask(size, "n") == tuple(
            tuple(reversed(row)) for row in primary_mask(size, "n")
        )
        assert primary_mask(size, "nw") == tuple(
            tuple(reversed(row)) for row in primary_mask(size, "ne")
        )


def test_scene_grounding_survives_translation_and_palette_recoloring() -> None:
    base = _solid(10, 7)
    target = apply_primary_stencil(base, "n", 2)
    first = infer_stencil_scene(_frame(target, base))
    translated = infer_stencil_scene(
        _frame(
            tuple(tuple(30 if value == 2 else 70 for value in row) for row in target),
            _solid(10, 70),
            selected=30,
            palette=(30, 40, 50),
            shift_x=5,
            shift_y=2,
        )
    )
    assert first is not None
    assert translated is not None
    assert first.pose == translated.pose == "n"
    assert first.construction_bbox != translated.construction_bbox
    assert first.selected_color == 2
    assert translated.selected_color == 30


def test_exact_planner_composes_committed_and_prospective_layers() -> None:
    base = _solid(10, 7)
    committed = apply_primary_stencil(base, "n", 2)
    target = apply_primary_stencil(committed, "se", 3)
    scene = StencilScene(
        reference=target,
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=(
            (2, StencilToken(6, (("x", 2), ("y", 2)))),
            (3, StencilToken(6, (("x", 10), ("y", 2)))),
        ),
        selected_color=2,
        pose="n",
    )
    planner = PrimaryStencilPlanner(
        enabled=True,
        action_directions={
            1: (-1, 0),
            2: (0, 1),
            3: (1, 0),
            4: (0, -1),
        },
        last_scene=scene,
    )
    first = planner.select((), 0, (0, 1, 2, 3, 4, 5, 6))
    assert first == StencilToken(5)
    assert planner.submit_action == 5
    assert planner.last_target_pose == "se"
    assert planner.last_plan_length > 1
    assert planner.search_states > 0


def test_palette_selection_changes_only_the_active_attribute() -> None:
    base = _solid(10, 7)
    before = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=(
            (2, StencilToken(6, (("x", 2), ("y", 2)))),
            (3, StencilToken(6, (("x", 10), ("y", 2)))),
        ),
        selected_color=2,
        pose="n",
    )
    after = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=before.reference_bbox,
        construction_bbox=before.construction_bbox,
        palette=before.palette,
        selected_color=3,
        pose="n",
    )
    clicked = before.palette[1][1]
    planner = PrimaryStencilPlanner(
        enabled=True,
        current_level=0,
        pending_token=clicked,
        pending_scene=before,
    )
    planner._validate_pending(before, after, clicked)
    assert planner.palette_confirmations == 1
    assert planner.palette_conflicts == 0
    assert not planner.quarantined


def test_apply_control_commits_an_intermediate_layer() -> None:
    base = _solid(10, 7)
    after_grid = apply_primary_stencil(base, "n", 2)
    before = StencilScene(
        reference=apply_primary_stencil(after_grid, "se", 3),
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=((2, StencilToken(6, (("x", 2), ("y", 2)))),),
        selected_color=2,
        pose="n",
    )
    after = StencilScene(
        reference=before.reference,
        construction=after_grid,
        reference_bbox=before.reference_bbox,
        construction_bbox=before.construction_bbox,
        palette=before.palette,
        selected_color=2,
        pose="n",
    )
    planner = PrimaryStencilPlanner(enabled=True, submit_action=5)
    planner._validate_pending(before, after, StencilToken(5))
    assert planner.apply_predictions == 1
    assert planner.apply_confirmations == 1
    assert planner.apply_conflicts == 0
    assert not planner.quarantined


def test_feature_is_off_by_default_and_exported_when_enabled() -> None:
    assert MindConfig() == MindConfig(
        enable_colored_stencil_primary_planning=False
    )
    policy = SymbolicPolicy(
        MindConfig(enable_colored_stencil_primary_planning=True)
    )
    assert policy.explorer.colored_stencil_primary_planning
    assert "reflector/core/colored_stencil.py" in OVERLAY_FILES
