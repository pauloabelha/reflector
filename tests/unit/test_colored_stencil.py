from __future__ import annotations

from dataclasses import replace

from reflector import MindConfig, SymbolicPolicy
from reflector.core.colored_stencil import (
    POSE_COORDINATES,
    PrimaryStencilPlanner,
    SecondaryStencil,
    StencilScene,
    StencilToken,
    _StencilStroke,
    apply_primary_stencil,
    apply_secondary_stencil,
    canonical_secondary_mask,
    infer_stencil_scene,
    oriented_secondary_mask,
    primary_mask,
    project_secondary_mask,
    synthesize_stencil_strokes,
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


def _with_secondary_payload(
    frame: Grid,
    *,
    left: int,
    top: int,
    width: int,
    height: int,
    color: int,
) -> Grid:
    pixels = [list(row) for row in frame]
    for y in range(top, top + height):
        for x in range(left, left + width):
            pixels[y][x] = color
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


def test_secondary_payload_is_projected_from_visible_cardinal_geometry() -> None:
    base = _solid(10, 7)
    frame = _with_secondary_payload(
        _frame(base, base),
        left=45,
        top=10,
        width=4,
        height=3,
        color=2,
    )
    scene = infer_stencil_scene(frame)
    assert scene is not None
    assert scene.pose == "n"
    assert len(scene.secondary) == 1
    secondary = scene.secondary[0]
    assert sum(value for row in secondary.mask for value in row) == 12
    assert secondary.mask == tuple(
        tuple(y < 3 and 3 <= x < 7 for x in range(10))
        for y in range(10)
    )
    assert secondary.radial_rank == 1
    assert secondary.token.action_id == 6


def test_secondary_projection_is_translation_and_c4_equivariant() -> None:
    north_points = tuple(
        (30 + x, 20 + y)
        for y in range(3)
        for x in range(4)
    )
    west_points = tuple(
        (13 + x, 37 + y)
        for y in range(4)
        for x in range(3)
    )
    north = project_secondary_mask(
        10,
        construction_bbox=(27, 34, 36, 43),
        payload_points=north_points,
        pose="n",
    )
    west = project_secondary_mask(
        10,
        construction_bbox=(27, 34, 36, 43),
        payload_points=west_points,
        pose="w",
    )
    assert north is not None
    assert west is not None
    assert canonical_secondary_mask(north, "n") == canonical_secondary_mask(
        west,
        "w",
    )
    assert oriented_secondary_mask(north, "w") == west


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


def test_primary_only_preserves_parent_ungrounded_and_refresh_semantics() -> None:
    base = _solid(10, 7)
    token = StencilToken(1)
    scene = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=((2, StencilToken(6, (("x", 2), ("y", 2)))),),
        selected_color=2,
        pose="n",
    )
    parent_compatible = PrimaryStencilPlanner(
        enabled=True,
        current_level=0,
        pending_token=token,
        pending_scene=scene,
    )
    assert parent_compatible.observe((), 0) is None
    assert not parent_compatible.quarantined
    assert parent_compatible.diagnostic == "no-unique-stencil-scene"

    strict = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        current_level=0,
        pending_token=token,
        pending_scene=scene,
    )
    assert strict.observe((), 0) is None
    assert strict.quarantined
    assert strict.diagnostic == "pending-scene-ungrounded"

    refreshed = replace(
        scene,
        reference=apply_primary_stencil(base, "s", 3),
    )
    parent_compatible = PrimaryStencilPlanner(
        enabled=True,
        no_effect_poses={1: {"n"}},
    )
    assert not parent_compatible._validate_pending(scene, refreshed, token)
    assert not parent_compatible.quarantined
    assert parent_compatible.no_effect_poses == {}
    assert parent_compatible.diagnostic == "level-scene-refreshed"

    strict = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        no_effect_poses={1: {"n"}},
    )
    assert not strict._validate_pending(scene, refreshed, token)
    assert strict.quarantined
    assert strict.diagnostic == "pending-reference-changed"


def test_primary_only_preserves_parent_palette_and_apply_role_tolerance() -> None:
    base = _solid(10, 7)
    palette = (
        (2, StencilToken(6, (("x", 2), ("y", 2)))),
        (3, StencilToken(6, (("x", 10), ("y", 2)))),
    )
    mask = tuple(
        tuple(y == 0 for _x in range(10))
        for y in range(10)
    )
    secondary = (
        SecondaryStencil(
            mask,
            StencilToken(6, (("x", 4), ("y", 2))),
            1,
        ),
    )
    before = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=palette,
        selected_color=2,
        pose="n",
    )
    clicked = palette[1][1]
    palette_after = replace(
        before,
        reference_bbox=(1, 0, 10, 9),
        construction_bbox=(21, 0, 30, 9),
        palette=tuple(reversed(palette)),
        selected_color=3,
        pose="e",
        secondary=secondary,
    )
    parent_compatible = PrimaryStencilPlanner(enabled=True)
    assert parent_compatible._validate_pending(before, palette_after, clicked)
    assert parent_compatible.palette_confirmations == 1
    assert not parent_compatible.quarantined

    strict = PrimaryStencilPlanner(enabled=True, secondary_enabled=True)
    assert not strict._validate_pending(before, palette_after, clicked)
    assert strict.palette_confirmations == 0
    assert strict.palette_conflicts == 1
    assert strict.quarantined

    submit = StencilToken(5)
    applied = replace(
        before,
        construction=apply_primary_stencil(base, "n", 2),
        reference_bbox=(1, 0, 10, 9),
        construction_bbox=(21, 0, 30, 9),
        palette=tuple(reversed(palette)),
        secondary=secondary,
    )
    parent_compatible = PrimaryStencilPlanner(
        enabled=True,
        submit_action=submit.action_id,
    )
    assert parent_compatible._validate_pending(before, applied, submit)
    assert parent_compatible.apply_confirmations == 1
    assert not parent_compatible.quarantined

    strict = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        submit_action=submit.action_id,
    )
    assert not strict._validate_pending(before, applied, submit)
    assert strict.apply_confirmations == 0
    assert strict.apply_conflicts == 1
    assert strict.quarantined


def test_primary_only_preserves_parent_movement_and_complex_tolerance() -> None:
    base = _solid(10, 7)
    palette = (
        (2, StencilToken(6, (("x", 2), ("y", 2)))),
        (3, StencilToken(6, (("x", 10), ("y", 2)))),
    )
    before = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=palette,
        selected_color=2,
        pose="n",
    )
    moved = replace(
        before,
        reference_bbox=(1, 0, 10, 9),
        construction_bbox=(21, 0, 30, 9),
        palette=tuple(reversed(palette)),
        selected_color=3,
        pose="ne",
    )
    movement = StencilToken(1)
    parent_compatible = PrimaryStencilPlanner(enabled=True)
    assert parent_compatible._validate_pending(before, moved, movement)
    assert parent_compatible.action_directions == {1: (1, 0)}
    assert not parent_compatible.quarantined

    strict = PrimaryStencilPlanner(enabled=True, secondary_enabled=True)
    assert not strict._validate_pending(before, moved, movement)
    assert strict.action_directions == {}
    assert strict.quarantined
    assert strict.diagnostic == "movement-changed-grounded-roles"

    unclassified = StencilToken(5, (("x", 4), ("y", 4)))
    parent_compatible = PrimaryStencilPlanner(enabled=True)
    assert not parent_compatible._validate_pending(
        before,
        before,
        unclassified,
    )
    assert not parent_compatible.quarantined

    strict = PrimaryStencilPlanner(enabled=True, secondary_enabled=True)
    assert not strict._validate_pending(before, before, unclassified)
    assert strict.quarantined
    assert strict.diagnostic == "unclassified-complex-pending"


def test_secondary_requires_a_later_independent_overwrite_confirmation() -> None:
    base = _solid(10, 7)
    mask = tuple(
        tuple(y < 3 and 3 <= x < 7 for x in range(10))
        for y in range(10)
    )
    token = StencilToken(6, (("x", 4), ("y", 2)))
    palette = (
        (2, StencilToken(6, (("x", 2), ("y", 2)))),
        (3, StencilToken(6, (("x", 10), ("y", 2)))),
    )
    before = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=palette,
        selected_color=2,
        pose="n",
        secondary=(SecondaryStencil(mask, token, 1),),
    )
    proposed = StencilScene(
        reference=base,
        construction=apply_secondary_stencil(base, mask, 2),
        reference_bbox=before.reference_bbox,
        construction_bbox=before.construction_bbox,
        palette=palette,
        selected_color=2,
        pose="n",
        secondary=before.secondary,
    )
    planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        pending_kind="secondary-proposal",
        pending_secondary_mask=mask,
    )
    planner._validate_pending(before, proposed, token)
    assert planner.secondary_proposals == 1
    assert planner.secondary_confirmations == 0
    assert planner.secondary_canonical_mask is None

    confirmation_before = StencilScene(
        reference=base,
        construction=proposed.construction,
        reference_bbox=before.reference_bbox,
        construction_bbox=before.construction_bbox,
        palette=palette,
        selected_color=3,
        pose="n",
        secondary=before.secondary,
    )
    confirmation_after = StencilScene(
        reference=base,
        construction=apply_secondary_stencil(proposed.construction, mask, 3),
        reference_bbox=before.reference_bbox,
        construction_bbox=before.construction_bbox,
        palette=palette,
        selected_color=3,
        pose="n",
        secondary=before.secondary,
    )
    planner.pending_kind = "secondary-confirmation"
    planner.pending_secondary_mask = mask
    planner._validate_pending(confirmation_before, confirmation_after, token)
    assert planner.secondary_confirmations == 1
    assert planner.secondary_canonical_mask == mask
    assert planner.secondary_confirmed_poses == {"n"}
    assert not planner.quarantined


def test_reverse_overwrite_synthesis_finds_exact_secondary_program() -> None:
    base = _solid(10, 0)
    north = tuple(
        tuple(y < 3 and 3 <= x < 7 for x in range(10))
        for y in range(10)
    )
    target = apply_primary_stencil(base, "se", 8)
    target = apply_primary_stencil(target, "e", 14)
    target = apply_primary_stencil(target, "nw", 15)
    target = apply_secondary_stencil(target, north, 12)
    strokes, states = synthesize_stencil_strokes(
        base,
        target,
        palette_colors=(8, 12, 14, 15),
        secondary_masks={"n": north},
        max_depth=16,
        max_states=50_000,
    )
    construction = base
    for stroke in strokes:
        construction = (
            apply_primary_stencil(construction, stroke.pose, stroke.color)
            if stroke.kind == "primary"
            else apply_secondary_stencil(
                construction,
                stroke.mask,
                stroke.color,
            )
        )
    assert construction == target
    assert len(strokes) == 4
    assert states < 64


def test_primary_only_preserves_parent_stage_cap_at_arbitrary_level() -> None:
    base = _solid(10, 70)
    scene = StencilScene(
        reference=apply_primary_stencil(base, "n", 30),
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=(
            (30, StencilToken(6, (("x", 2), ("y", 2)))),
            (40, StencilToken(6, (("x", 10), ("y", 2)))),
        ),
        selected_color=30,
        pose="n",
    )
    planner = PrimaryStencilPlanner(
        enabled=True,
        action_directions={
            11: (-1, 0),
            7: (0, 1),
            19: (1, 0),
            3: (0, -1),
        },
        last_scene=scene,
    )
    assert planner.select((), 97, (0, 19, 13, 7, 6, 3, 11)) is None
    assert planner.diagnostic == "stage-complete"
    assert planner.search_states == 0
    assert planner.pending_token is None


def test_secondary_mode_still_attempts_primary_at_arbitrary_level_and_action_ids() -> (
    None
):
    base = _solid(10, 70)
    target = apply_primary_stencil(base, "n", 30)
    scene = StencilScene(
        reference=target,
        construction=base,
        reference_bbox=(0, 0, 9, 9),
        construction_bbox=(20, 0, 29, 9),
        palette=(
            (30, StencilToken(6, (("x", 2), ("y", 2)))),
            (40, StencilToken(6, (("x", 10), ("y", 2)))),
        ),
        selected_color=30,
        pose="n",
    )
    planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        action_directions={
            11: (-1, 0),
            7: (0, 1),
            19: (1, 0),
            3: (0, -1),
        },
        last_scene=scene,
    )
    selected = planner.select(
        (),
        97,
        (0, 19, 13, 7, 6, 3, 11),
    )
    assert selected == StencilToken(13)
    assert planner.submit_action == 13
    assert planner.diagnostic == "executing-primary-stencil-plan"


def test_secondary_pose_probing_exhausts_once_and_abstains() -> None:
    base = _solid(6, 7)
    scene = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 5, 5),
        construction_bbox=(10, 0, 15, 5),
        palette=(
            (2, StencilToken(6, (("x", 2), ("y", 2)))),
            (3, StencilToken(6, (("x", 10), ("y", 2)))),
        ),
        selected_color=2,
        pose="n",
    )
    planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        action_directions={
            1: (-1, 0),
            2: (0, 1),
            3: (1, 0),
            4: (0, -1),
        },
    )
    for pose in ("n", "e", "s"):
        assert planner._secondary_induction_step(
            replace(scene, pose=pose)
        ) is not None
        planner._clear_pending()
    assert planner._secondary_induction_step(replace(scene, pose="w")) is None
    assert planner.secondary_inspected_poses == {"n", "e", "s", "w"}
    assert planner.secondary_pose_inspections == 4
    assert planner.secondary_probe_exhaustions == 1
    assert planner.secondary_probe_exhausted
    assert planner.diagnostic == "secondary-pose-probes-exhausted"
    assert planner._secondary_induction_step(replace(scene, pose="w")) is None
    assert planner.secondary_probe_exhaustions == 1


def test_secondary_plan_and_c4_probe_abstain_on_duplicate_mask_candidates() -> None:
    base = _solid(6, 7)
    mask = tuple(
        tuple(y == 0 and 1 <= x < 5 for x in range(6))
        for y in range(6)
    )
    first = SecondaryStencil(
        mask,
        StencilToken(6, (("x", 1), ("y", 1))),
        1,
    )
    second = SecondaryStencil(
        mask,
        StencilToken(6, (("x", 9), ("y", 1))),
        2,
    )
    scene = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 5, 5),
        construction_bbox=(10, 0, 15, 5),
        palette=((2, StencilToken(6, (("x", 2), ("y", 2)))),),
        selected_color=2,
        pose="n",
        secondary=(first, second),
    )
    stroke = _StencilStroke("secondary", "n", 2, mask)
    planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        submit_action=5,
    )
    assert planner._select_stroke_step(scene, (stroke,)) is None
    assert planner.secondary_plan_actions_issued == 0
    assert planner.secondary_plan_steps == 0
    assert planner.secondary_last_candidate_matches == 2
    assert planner.secondary_candidate_ambiguities == 1
    assert planner.diagnostic == "secondary-plan-component-ambiguous"

    c4_planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        secondary_canonical_mask=mask,
    )
    assert c4_planner._secondary_c4_probe_step(scene, "n") is None
    assert c4_planner.secondary_last_candidate_matches == 2
    assert c4_planner.secondary_candidate_ambiguities == 1
    assert c4_planner.secondary_c4_rejected_poses == {"n"}
    assert c4_planner.diagnostic == "secondary-c4-component-ambiguous"


def test_ungrounded_secondary_outcome_is_a_traced_causal_failure() -> None:
    base = _solid(6, 7)
    mask = tuple(
        tuple(y == 0 for _x in range(6))
        for y in range(6)
    )
    token = StencilToken(6, (("x", 1), ("y", 1)))
    scene = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 5, 5),
        construction_bbox=(10, 0, 15, 5),
        palette=((2, StencilToken(6, (("x", 2), ("y", 2)))),),
        selected_color=2,
        pose="n",
        secondary=(SecondaryStencil(mask, token, 1),),
    )
    planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        current_level=0,
        pending_token=token,
        pending_scene=scene,
        pending_kind="secondary-plan",
        pending_secondary_mask=mask,
        pending_secondary_context=True,
        pending_secondary_plan_action=True,
        secondary_plan_actions_issued=1,
    )
    assert planner.observe((), 0) is None
    assert planner.quarantined
    assert planner.secondary_conflicts == 1
    assert planner.secondary_causal_validation_failures == 1
    assert planner.secondary_plan_action_conflicts == 1
    assert planner.secondary_plan_steps == 0
    assert planner.diagnostic == "pending-scene-ungrounded"
    assert planner.pending_token is None


def test_reference_palette_and_exterior_mutations_fail_causal_validation() -> None:
    base = _solid(6, 7)
    changed_reference = apply_primary_stencil(base, "s", 3)
    mask = tuple(
        tuple(y == 0 for _x in range(6))
        for y in range(6)
    )
    token = StencilToken(6, (("x", 1), ("y", 1)))
    secondary = (SecondaryStencil(mask, token, 1),)
    palette = (
        (2, StencilToken(6, (("x", 2), ("y", 2)))),
        (3, StencilToken(6, (("x", 10), ("y", 2)))),
    )
    before = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 5, 5),
        construction_bbox=(10, 0, 15, 5),
        palette=palette,
        selected_color=2,
        pose="n",
        secondary=secondary,
    )
    exact = replace(
        before,
        construction=apply_secondary_stencil(base, mask, 2),
    )
    invalid_after_scenes = (
        replace(exact, reference=changed_reference),
        replace(exact, palette=tuple(reversed(palette))),
        replace(exact, secondary=()),
    )
    for after in invalid_after_scenes:
        planner = PrimaryStencilPlanner(
            enabled=True,
            secondary_enabled=True,
            pending_kind="secondary-plan",
            pending_secondary_mask=mask,
            pending_secondary_context=True,
        )
        assert not planner._validate_pending(before, after, token)
        assert planner.quarantined
        assert planner.secondary_confirmations == 0
        assert planner.secondary_conflicts == 1
        assert planner.secondary_causal_validation_failures == 1


def test_rejected_confirmation_does_not_increment_confirmations() -> None:
    base = _solid(6, 7)
    mask = tuple(
        tuple(y == 0 for _x in range(6))
        for y in range(6)
    )
    token = StencilToken(6, (("x", 1), ("y", 1)))
    palette = (
        (2, StencilToken(6, (("x", 2), ("y", 2)))),
        (3, StencilToken(6, (("x", 10), ("y", 2)))),
    )
    before = StencilScene(
        reference=base,
        construction=base,
        reference_bbox=(0, 0, 5, 5),
        construction_bbox=(10, 0, 15, 5),
        palette=palette,
        selected_color=2,
        pose="n",
    )
    after = replace(
        before,
        construction=apply_secondary_stencil(base, mask, 2),
    )
    planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        pending_kind="secondary-confirmation",
        pending_secondary_mask=mask,
        pending_secondary_context=True,
        secondary_proposed_mask=mask,
        secondary_proposed_color=2,
    )
    assert not planner._validate_pending(before, after, token)
    assert planner.secondary_confirmations == 0
    assert planner.secondary_conflicts == 1
    assert planner.diagnostic == "secondary-confirmation-not-independent"


def test_secondary_plan_step_counts_only_after_an_accepted_outcome() -> None:
    base = _solid(10, 7)
    before_frame = _with_secondary_payload(
        _frame(base, base),
        left=45,
        top=10,
        width=4,
        height=3,
        color=2,
    )
    before = infer_stencil_scene(before_frame)
    assert before is not None
    assert len(before.secondary) == 1
    component = before.secondary[0]
    planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        current_level=0,
        submit_action=5,
        last_scene=before,
    )
    stroke = _StencilStroke("secondary", "n", 2, component.mask)
    assert planner._select_stroke_step(before, (stroke,)) == component.token
    assert planner.secondary_plan_actions_issued == 1
    assert planner.secondary_plan_steps == 0

    after_frame = _with_secondary_payload(
        _frame(
            base,
            apply_secondary_stencil(base, component.mask, 2),
        ),
        left=45,
        top=10,
        width=4,
        height=3,
        color=2,
    )
    planner.observe(after_frame, 0)
    assert not planner.quarantined
    assert planner.secondary_plan_steps == 1
    assert planner.secondary_confirmations == 1
    assert planner.secondary_plan_action_conflicts == 0


def test_level_advance_resets_secondary_authority_and_trace_uses_c4_names() -> None:
    base = _solid(10, 7)
    mask = tuple(
        tuple(y < 3 and 3 <= x < 7 for x in range(10))
        for y in range(10)
    )
    planner = PrimaryStencilPlanner(
        enabled=True,
        secondary_enabled=True,
        current_level=0,
        secondary_proposed_mask=mask,
        secondary_proposed_color=2,
        secondary_canonical_mask=mask,
        secondary_confirmed_poses={"n", "e"},
        secondary_c4_confirmed=True,
        secondary_probe_target="s",
        secondary_inspected_poses={"n", "w"},
        secondary_c4_rejected_poses={"s"},
        secondary_probe_exhausted=True,
    )
    planner.observe(_frame(base, base), 1)
    assert planner.secondary_proposed_mask is None
    assert planner.secondary_canonical_mask is None
    assert planner.secondary_confirmed_poses == set()
    assert not planner.secondary_c4_confirmed
    assert planner.secondary_inspected_poses == set()
    assert planner.secondary_c4_rejected_poses == set()
    assert not planner.secondary_probe_exhausted
    assert planner.secondary_authority_resets == 1
    trace = planner.to_dict()
    assert "secondary_c4_confirmed" in trace
    assert not any("d4" in key.lower() for key in trace)


def test_feature_is_off_by_default_and_exported_when_enabled() -> None:
    assert MindConfig() == MindConfig(
        enable_colored_stencil_primary_planning=False,
        enable_colored_stencil_secondary_planning=False,
    )
    try:
        MindConfig(enable_colored_stencil_secondary_planning=True)
    except ValueError as error:
        assert "requires primary" in str(error)
    else:
        raise AssertionError("secondary planning must require the primary stage")
    policy = SymbolicPolicy(
        MindConfig(
            enable_colored_stencil_primary_planning=True,
            enable_colored_stencil_secondary_planning=True,
        )
    )
    assert policy.explorer.colored_stencil_primary_planning
    assert policy.explorer.colored_stencil_secondary_planning
    assert "reflector/core/colored_stencil.py" in OVERLAY_FILES
