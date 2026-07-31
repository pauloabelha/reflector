from collections import Counter

from reflector.core.mind import MindConfig
from reflector.core.phase_topology import (
    EmbeddedPattern,
    PhaseTopologyPlanner,
    _ground_complementary_display,
    _overlap_classes,
    _select_partition_view,
    components,
    embedded_patterns,
    infer_rigid_translation,
)
from reflector.runtime.policy import SymbolicPolicy

Frame = tuple[tuple[int, ...], ...]


def _frame(width: int, height: int, color: int = 0) -> list[list[int]]:
    return [[color for _x in range(width)] for _y in range(height)]


def _freeze(frame: list[list[int]]) -> Frame:
    return tuple(tuple(row) for row in frame)


def _paint_body(
    frame: list[list[int]],
    anchor: tuple[int, int],
    *,
    left_color: int = 9,
    right_color: int = 12,
) -> None:
    for local_y in range(4):
        for local_x in range(4):
            frame[anchor[1] + local_y][anchor[0] + local_x] = (
                left_color if local_x < 2 else right_color
            )


def _paint_display(
    frame: list[list[int]],
    bbox: tuple[int, int, int, int],
    pattern: tuple[tuple[int, int], ...],
    *,
    scale: int,
) -> None:
    min_x, min_y, max_x, max_y = bbox
    for y in range(min_y, max_y + 1):
        for x in range(min_x, max_x + 1):
            frame[y][x] = 5
    glyph_min_x = min_x + 2
    glyph_min_y = min_y + 2
    for logical_x, logical_y in pattern:
        for dy in range(scale):
            for dx in range(scale):
                frame[glyph_min_y + logical_y * scale + dy][
                    glyph_min_x + logical_x * scale + dx
                ] = 9


def _paint_meter(
    frame: list[list[int]],
    *,
    color: int,
    remaining_width: int,
) -> None:
    for y in range(len(frame) - 2, len(frame)):
        for x in range(5, 5 + remaining_width):
            frame[y][x] = color


def _paint_ring(
    frame: list[list[int]],
    origin: tuple[int, int],
    *,
    color: int,
) -> None:
    for local_y in range(3):
        for local_x in range(3):
            if (local_x, local_y) != (1, 1):
                frame[origin[1] + local_y][origin[0] + local_x] = color


def test_infers_multicolor_rigid_translation_without_object_identity() -> None:
    before = _frame(20, 14)
    after = _frame(20, 14)
    _paint_body(before, (3, 5))
    _paint_body(after, (5, 5))

    motion = infer_rigid_translation(_freeze(before), _freeze(after))

    assert motion is not None
    assert motion.before_anchor == (3, 5)
    assert motion.after_anchor == (5, 5)
    assert motion.displacement == (2, 0)
    assert motion.colors == frozenset({9, 12})
    assert len(motion.colored_mask) == 16


def test_embedded_patterns_compress_scale_but_preserve_relations() -> None:
    pattern = ((0, 0), (1, 0), (2, 0), (2, 1), (0, 2), (2, 2))
    frame = _frame(34, 16)
    _paint_display(frame, (1, 1, 10, 10), pattern, scale=2)
    _paint_display(frame, (18, 1, 24, 7), pattern, scale=1)

    displays = embedded_patterns(_freeze(frame))
    matching = [item for item in displays if item.pattern[2] == tuple(sorted(pattern))]

    assert {item.scale for item in matching} == {1, 2}
    assert {item.pattern[:2] for item in matching} == {(3, 3)}


def test_operator_observations_are_quotiented_across_partial_occlusion() -> None:
    full = ((10, 8), (11, 8), (10, 9), (11, 9))
    left_view = ((10, 8), (10, 9))
    top_view = ((10, 8), (11, 8))
    separate = ((30, 4), (31, 4))

    classes = _overlap_classes((left_view, separate, full, top_view))

    assert classes == (
        (separate, (separate,)),
        (full, (left_view, top_view, full)),
    )


def _embedded(
    *,
    host_color: int,
    glyph_color: int,
    bbox: tuple[int, int, int, int],
    pattern: tuple[tuple[int, int], ...],
    scale: int = 2,
) -> EmbeddedPattern:
    min_x, min_y, _max_x, _max_y = bbox
    cells = tuple(
        sorted(
            (min_x + 1 + scale * x, min_y + 1 + scale * y)
            for x, y in pattern
        )
    )
    return EmbeddedPattern(
        host_color=host_color,
        glyph_color=glyph_color,
        host_bbox=bbox,
        scale=scale,
        pattern=(3, 3, tuple(sorted(pattern))),
        glyph_cells=cells,
    )


def test_complementary_display_grounding_is_translation_and_color_invariant() -> None:
    left = ((0, 0), (0, 2), (2, 0), (2, 1))
    right = tuple(
        sorted(
            set((x, y) for y in range(3) for x in range(3)) - set(left)
        )
    )
    goal = ((0, 0), (0, 2), (1, 0), (2, 0), (2, 1), (2, 2))
    outer = _embedded(
        host_color=7,
        glyph_color=2,
        bbox=(23, 31, 28, 36),
        pattern=left,
    )
    inner = _embedded(
        host_color=2,
        glyph_color=7,
        bbox=(21, 29, 30, 38),
        pattern=right,
    )
    target = _embedded(
        host_color=2,
        glyph_color=11,
        bbox=(4, 5, 10, 11),
        pattern=goal,
        scale=1,
    )

    grounded = _ground_complementary_display((target, inner, outer))

    assert grounded is not None
    hosts, current, fixed_goal = grounded
    assert set(hosts) == {outer.host_bbox, inner.host_bbox}
    assert current == inner
    assert fixed_goal == target


def test_complementary_display_grounding_abstains_on_ambiguity_and_overlap() -> None:
    left = ((0, 0), (0, 2), (2, 0), (2, 1))
    right = tuple(
        sorted(
            set((x, y) for y in range(3) for x in range(3)) - set(left)
        )
    )
    outer = _embedded(
        host_color=7,
        glyph_color=2,
        bbox=(23, 31, 28, 36),
        pattern=left,
    )
    inner = _embedded(
        host_color=2,
        glyph_color=7,
        bbox=(21, 29, 30, 38),
        pattern=right,
    )
    goal_a = _embedded(
        host_color=2,
        glyph_color=11,
        bbox=(4, 5, 10, 11),
        pattern=((0, 0), (2, 2)),
        scale=1,
    )
    goal_b = _embedded(
        host_color=2,
        glyph_color=13,
        bbox=(42, 5, 48, 11),
        pattern=((0, 0), (2, 2)),
        scale=1,
    )
    overlapping = _embedded(
        host_color=2,
        glyph_color=7,
        bbox=inner.host_bbox,
        pattern=((*right[:-1], left[0])),
    )

    assert _ground_complementary_display((outer, inner, goal_a, goal_b)) is None
    assert _ground_complementary_display((outer, overlapping, goal_a)) is None
    unmatched_role = _embedded(
        host_color=11,
        glyph_color=13,
        bbox=goal_a.host_bbox,
        pattern=goal_a.pattern[2],
        scale=1,
    )
    assert _ground_complementary_display((outer, inner, unmatched_role)) is None


def test_complementary_quotient_preserves_host_role_across_shape_change() -> None:
    left = ((0, 0), (0, 2), (2, 0), (2, 1))
    right = tuple(
        sorted(
            set((x, y) for y in range(3) for x in range(3)) - set(left)
        )
    )
    goal_pattern = ((0, 0), (0, 2), (1, 0), (2, 0), (2, 1), (2, 2))
    outer = _embedded(
        host_color=7,
        glyph_color=2,
        bbox=(23, 31, 28, 36),
        pattern=left,
    )
    inner = _embedded(
        host_color=2,
        glyph_color=7,
        bbox=(21, 29, 30, 38),
        pattern=right,
    )
    goal = _embedded(
        host_color=2,
        glyph_color=11,
        bbox=(4, 5, 10, 11),
        pattern=goal_pattern,
        scale=1,
    )
    transformed_inner = _embedded(
        host_color=2,
        glyph_color=7,
        bbox=inner.host_bbox,
        pattern=goal_pattern,
    )
    transformed_outer = EmbeddedPattern(
        host_color=7,
        glyph_color=2,
        host_bbox=outer.host_bbox,
        scale=2,
        pattern=(2, 2, ((0, 0), (1, 0), (1, 1))),
        glyph_cells=outer.glyph_cells,
    )

    previous = _select_partition_view(
        {
            outer.host_bbox: outer,
            inner.host_bbox: inner,
        },
        (outer.host_bbox, inner.host_bbox),
        goal,
    )
    selected = _select_partition_view(
        {
            transformed_outer.host_bbox: transformed_outer,
            transformed_inner.host_bbox: transformed_inner,
        },
        (outer.host_bbox, inner.host_bbox),
        goal,
    )

    assert previous == inner
    assert selected == transformed_inner
    assert previous.host_color == selected.host_color == goal.host_color
    assert previous.glyph_color == selected.glyph_color
    assert previous.pattern != selected.pattern


def test_sparse_factor_operator_requires_grounded_matching_arity() -> None:
    frame = _frame(64, 44, color=3)
    _paint_body(frame, (2, 2))
    stencil_cells = ((20, 10), (22, 10), (21, 11), (21, 12))
    for x, y in stencil_cells:
        frame[y][x] = 0
    left = ((0, 0), (0, 2), (2, 0), (2, 1))
    right = tuple(
        sorted(
            set((x, y) for y in range(3) for x in range(3)) - set(left)
        )
    )
    outer = _embedded(
        host_color=7,
        glyph_color=2,
        bbox=(43, 31, 48, 36),
        pattern=left,
    )
    inner = _embedded(
        host_color=2,
        glyph_color=7,
        bbox=(41, 29, 50, 38),
        pattern=right,
    )
    goal = _embedded(
        host_color=2,
        glyph_color=11,
        bbox=(30, 4, 36, 10),
        pattern=((0, 0), (2, 2)),
        scale=1,
    )
    planner = PhaseTopologyPlanner(
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(2, 2),
        traversable_colors={3},
        current_pattern=outer.pattern,
        goal_pattern=goal.pattern,
        pattern_candidates=(outer, inner, goal),
    )

    planner._refresh_operator(_freeze(frame))

    assert planner.operator_candidates == (tuple(sorted(stencil_cells)),)

    planner.pattern_candidates = (outer, goal)
    planner.operator_candidates = ()
    planner.operator_cells = ()
    planner._refresh_operator(_freeze(frame))

    assert planner.operator_candidates == ()


def test_complementary_display_probes_affordable_unknown_before_reset() -> None:
    frame = _frame(48, 34, color=3)
    _paint_body(frame, (20, 20))
    _paint_ring(frame, (16, 21), color=7)
    _paint_ring(frame, (6, 21), color=7)
    sparse_operator = tuple(
        sorted(((21, 16), (23, 16), (22, 17), (22, 18)))
    )
    for x, y in sparse_operator:
        frame[y][x] = 11
    palette_operator = tuple(
        sorted(((31, 16), (33, 16), (32, 17), (32, 18)))
    )
    for index, (x, y) in enumerate(palette_operator):
        frame[y][x] = 6 if index % 2 else 8
    left = ((0, 0), (0, 2), (2, 0), (2, 1))
    right = tuple(
        sorted(
            set((x, y) for y in range(3) for x in range(3)) - set(left)
        )
    )
    outer = _embedded(
        host_color=14,
        glyph_color=5,
        bbox=(3, 25, 8, 30),
        pattern=left,
    )
    inner = _embedded(
        host_color=5,
        glyph_color=14,
        bbox=(1, 23, 10, 32),
        pattern=right,
    )
    goal = _embedded(
        host_color=5,
        glyph_color=9,
        bbox=(2, 2, 8, 8),
        pattern=((0, 0), (0, 2), (1, 0), (2, 0), (2, 1), (2, 2)),
        scale=1,
    )
    resources = tuple(
        item
        for item in components(_freeze(frame))
        if item.color == 7 and item.bbox in {(6, 21, 8, 23), (16, 21, 18, 23)}
    )
    near_resource = next(
        item for item in resources if item.bbox == (16, 21, 18, 23)
    )
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(20, 20),
        traversable_colors={3},
        current_host=inner.host_bbox,
        current_view_hosts=(outer.host_bbox, inner.host_bbox),
        current_pattern=inner.pattern,
        current_glyph_color=inner.glyph_color,
        goal_host=goal.host_bbox,
        goal_pattern=goal.pattern,
        goal_glyph_color=goal.glyph_color,
        goal_cells=goal.glyph_cells,
        operator_candidates=(sparse_operator, palette_operator),
        pattern_candidates=(outer, inner, goal),
        budget_color=7,
        budget_area=40,
        budget_capacity=80,
        budget_unit=4,
        resource_candidates=resources,
    )

    selected = planner.select(_freeze(frame), (1, 2, 3, 4))

    assert selected == 1
    assert planner.operator_cells == sparse_operator
    assert planner.pending_resource is None
    assert planner.diagnostic == "executing-operator-option"

    planner.pending_action = None
    planner.pending_anchor = None
    planner.pending_source = None
    planner.active_operator = None
    planner.current_pattern = planner.goal_pattern
    planner.operator_effects[sparse_operator] = frozenset({"shape"})
    planner.contextual_transitions = 1
    planner.budget_area = planner.budget_capacity

    selected_palette = planner.select(_freeze(frame), (1, 2, 3, 4))

    assert selected_palette == 3
    assert planner.operator_cells == palette_operator
    assert planner.pending_resource is not None
    assert planner.active_resource is not None
    assert planner.active_resource[1] == near_resource.bbox
    assert planner.diagnostic == "executing-resource-reset-option"


def test_sparse_arity_prior_beats_proximity_without_typing_effect() -> None:
    frame = _frame(48, 34, color=3)
    _paint_body(frame, (20, 20))
    nearby_palette = ((21, 16), (22, 16), (21, 17), (22, 17))
    for index, (x, y) in enumerate(nearby_palette):
        frame[y][x] = 6 if index % 2 else 8
    sparse_shape = ((31, 16), (33, 16), (32, 17), (32, 18))
    for x, y in sparse_shape:
        frame[y][x] = 11
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(20, 20),
        traversable_colors={3},
        current_view_hosts=((1, 23, 10, 32), (3, 25, 8, 30)),
        current_pattern=(3, 3, ((0, 1), (1, 1), (2, 1))),
        current_glyph_color=14,
        goal_pattern=(3, 3, ((0, 0), (1, 1), (2, 2))),
        goal_glyph_color=9,
        operator_candidates=(nearby_palette, sparse_shape),
    )

    planner._select_operator_candidate(_freeze(frame))

    assert planner.operator_cells == sparse_shape
    assert planner.operator_effects == {}

    planner.operator_effects[nearby_palette] = frozenset({"palette"})
    planner.current_pattern = planner.goal_pattern
    planner._select_operator_candidate(_freeze(frame))

    assert planner.operator_cells == nearby_palette


def test_observed_operator_change_binds_current_phase_to_goal() -> None:
    previous = ((0, 0), (1, 0), (2, 0), (0, 1), (0, 2), (2, 2))
    goal = ((0, 0), (1, 0), (2, 0), (2, 1), (0, 2), (2, 2))
    before = _frame(34, 16)
    after = _frame(34, 16)
    _paint_display(before, (1, 1, 10, 10), previous, scale=2)
    _paint_display(after, (1, 1, 10, 10), goal, scale=2)
    _paint_display(before, (18, 1, 24, 7), goal, scale=1)
    _paint_display(after, (18, 1, 24, 7), goal, scale=1)
    planner = PhaseTopologyPlanner()

    planner.observe(
        _freeze(before),
        _freeze(after),
        action_id=4,
        progressed=False,
    )

    assert planner.current_pattern == planner.goal_pattern
    assert planner.current_host == (1, 1, 10, 10)
    assert planner.goal_host == (18, 1, 24, 7)
    assert planner.operator_applications == 1
    assert planner.diagnostic == "operator-induced-factor-transition"


def test_bound_factor_bundle_latches_goal_under_matching_transition() -> None:
    previous = ((0, 0), (0, 2), (1, 0), (2, 0), (2, 1), (2, 2))
    goal = ((0, 0), (0, 1), (0, 2), (1, 2), (2, 0), (2, 2))
    before = _frame(42, 18)
    after = _frame(42, 18)
    _paint_display(before, (1, 1, 10, 10), previous, scale=2)
    _paint_display(after, (1, 1, 10, 10), goal, scale=2)
    _paint_display(before, (24, 1, 30, 7), goal, scale=1)
    _paint_display(after, (24, 1, 30, 7), goal, scale=1)
    planner = PhaseTopologyPlanner(
        current_host=(1, 1, 10, 10),
        current_pattern=(3, 3, tuple(sorted(previous))),
        current_glyph_color=9,
        goal_host=(24, 1, 30, 7),
        goal_pattern=(3, 3, tuple(sorted(goal))),
        goal_glyph_color=9,
        operator_cells=((35, 12), (36, 12)),
        active_operator=((35, 12), (36, 12)),
    )

    planner.observe(
        _freeze(before),
        _freeze(after),
        action_id=3,
        progressed=False,
    )

    assert planner.current_host == (1, 1, 10, 10)
    assert planner.goal_host == (24, 1, 30, 7)
    assert planner.current_pattern == planner.goal_pattern
    assert planner.goal_latched
    assert planner.operator_applications == 1
    assert planner.operator_effects[planner.operator_cells] == frozenset({"shape"})
    assert planner.active_operator is None


def test_bound_factor_bundle_ignores_unrelated_occlusion_pattern() -> None:
    solved = ((0, 0), (0, 1), (0, 2), (1, 2), (2, 0), (2, 2))
    transient_before = ((0, 0), (1, 1))
    transient_after = ((0, 0), (0, 1), (1, 1))
    before = _frame(58, 18)
    after = _frame(58, 18)
    for frame in (before, after):
        _paint_display(frame, (1, 1, 10, 10), solved, scale=2)
        _paint_display(frame, (20, 1, 26, 7), solved, scale=1)
        _paint_display(frame, (46, 1, 51, 6), transient_after, scale=1)
    _paint_display(before, (34, 1, 39, 6), transient_before, scale=1)
    _paint_display(after, (34, 1, 39, 6), transient_after, scale=1)
    solved_pattern = (3, 3, tuple(sorted(solved)))
    planner = PhaseTopologyPlanner(
        current_host=(1, 1, 10, 10),
        current_pattern=solved_pattern,
        current_glyph_color=9,
        goal_host=(20, 1, 26, 7),
        goal_pattern=solved_pattern,
        goal_glyph_color=9,
        goal_latched=True,
    )

    planner.observe(
        _freeze(before),
        _freeze(after),
        action_id=2,
        progressed=False,
    )

    assert planner.current_host == (1, 1, 10, 10)
    assert planner.goal_host == (20, 1, 26, 7)
    assert planner.current_pattern == solved_pattern
    assert planner.goal_pattern == solved_pattern
    assert planner.goal_latched
    assert planner.operator_applications == 0


def test_phase_equal_planner_compiles_shortest_terminal_option() -> None:
    frame = _frame(20, 25, color=3)
    _paint_body(frame, (0, 15))
    for y in range(4, 11):
        for x in range(7):
            frame[y][x] = 5
    frame[5][0] = 9
    frame[9][4] = 9
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(0, 15),
        traversable_colors={3},
        current_pattern=(3, 3, ((0, 0), (2, 2))),
        goal_pattern=(3, 3, ((0, 0), (2, 2))),
        goal_host=(0, 4, 4, 10),
        goal_cells=((0, 5), (3, 8)),
    )

    selected = planner.select(_freeze(frame), (1, 2, 3, 4))

    assert selected == 1
    assert planner.last_plan_length == 2
    assert planner.diagnostic == "executing-terminal-option"


def test_conserved_body_teleport_adds_sparse_contextual_edge() -> None:
    before = _frame(24, 20, color=3)
    after = _frame(24, 20, color=3)
    _paint_body(before, (10, 10))
    _paint_body(after, (2, 10))
    planner = PhaseTopologyPlanner(
        action_effects={4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(10, 10),
        traversable_colors={3},
        current_pattern=(3, 3, ((0, 0),)),
        goal_pattern=(3, 3, ((0, 0),)),
        operator_cells=((11, 11),),
        pending_source=(10, 10),
        pending_anchor=(15, 10),
        pending_action=4,
    )

    planner.observe(
        _freeze(before),
        _freeze(after),
        action_id=4,
        progressed=False,
    )

    assert planner.action_effects == {4: (5, 0)}
    assert planner.current_anchor == (2, 10)
    assert planner.operator_applications == 0
    assert planner.contextual_transitions == 1
    assert planner.contextual_edges == {((10, 10), 4): (2, 10)}
    assert ((10, 10), 4) in planner.blocked_edges
    assert not planner.goal_latched
    assert planner.confirmations == 1
    assert planner.conflicts == 0
    assert planner.diagnostic == "contextual-anchor-edge-observed"

    planner.current_anchor = (10, 10)
    assert planner._search_path(
        _freeze(before),
        start=(10, 10),
        targets={(2, 10)},
    ) == (4,)


def test_post_resource_search_minimizes_contextual_risk_before_length() -> None:
    frame = _frame(30, 20, color=3)
    _paint_body(frame, (5, 5))
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(5, 5),
        traversable_colors={3},
        contextual_edges={((5, 5), 1): (15, 5)},
    )

    shortest = planner._search_path(
        _freeze(frame),
        start=(5, 5),
        targets={(15, 5)},
    )
    risk_aware = planner._search_path(
        _freeze(frame),
        start=(5, 5),
        targets={(15, 5)},
        prefer_fewer_contextual=True,
    )

    assert shortest == (1,)
    assert risk_aware == (4, 4)


def test_operator_rearm_leaves_before_reapplying_contact_transition() -> None:
    frame = _frame(20, 20, color=3)
    _paint_body(frame, (5, 5))
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(5, 5),
        traversable_colors={3},
        current_pattern=(3, 3, ((0, 0),)),
        goal_pattern=(3, 3, ((0, 0),)),
        operator_cells=((6, 6),),
        operator_applications=1,
    )

    selected = planner.select(_freeze(frame), (1, 2, 3, 4))

    assert selected == 1
    assert planner.pending_anchor == (5, 0)
    assert planner.diagnostic == "executing-operator-rearm-option"


def test_consumed_resource_requires_leave_before_next_option() -> None:
    frame = _frame(42, 32, color=3)
    _paint_body(frame, (19, 15))
    frame[10][19] = 4
    resource_cells = ((20, 16), (21, 16))
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(19, 15),
        traversable_colors={3},
        current_view_hosts=((1, 20, 6, 25), (0, 19, 7, 26)),
        current_pattern=(3, 3, ((0, 0),)),
        goal_pattern=(3, 3, ((2, 2),)),
        operator_cells=((31, 16), (32, 16)),
        operator_effects={
            ((31, 16), (32, 16)): frozenset({"shape"})
        },
        contextual_transitions=1,
        resource_rearm_cells=resource_cells,
    )

    selected = planner.select(_freeze(frame), (1, 2, 3, 4))

    assert selected == 2
    assert planner.pending_resource is None
    assert planner.pending_resource_back_edge == ((19, 20), 1)
    assert planner.diagnostic == "executing-resource-rearm-option"

    after = _frame(42, 32, color=3)
    _paint_body(after, (19, 20))
    after[10][19] = 4
    planner.observe(
        _freeze(frame),
        _freeze(after),
        action_id=2,
        progressed=False,
    )

    assert ((19, 20), 1) in planner.resource_exit_edges

    next_selected = planner.select(_freeze(after), (1, 2, 3, 4))

    assert next_selected != 1

    planner.pending_action = None
    planner.pending_anchor = None
    planner.pending_source = None
    planner.current_view_hosts = ()
    planner.current_anchor = (19, 15)
    planner.resource_rearm_cells = resource_cells
    planner.resource_exit_edges.clear()

    planner.select(_freeze(frame), (1, 2, 3, 4))

    assert planner.resource_rearm_cells == ()
    assert planner.diagnostic != "executing-resource-rearm-option"


def test_cross_level_action_algebra_transfers_after_recolored_commuting_square() -> (
    None
):
    effects = {1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)}
    planner = PhaseTopologyPlanner(
        action_effects=dict(effects),
        action_evidence=Counter({action_id: 3 for action_id in effects}),
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        traversable_colors={3},
    )
    planner.reset_level(retain_action_algebra=True)
    before = _frame(28, 18, color=6)
    after = _frame(28, 18, color=6)
    _paint_body(before, (3, 7), left_color=2, right_color=11)
    _paint_body(after, (8, 7), left_color=2, right_color=11)

    planner.observe(
        _freeze(before),
        _freeze(after),
        action_id=4,
        progressed=False,
    )

    assert planner.action_effects == effects
    assert planner.cross_level_transfer_confirmations == 1
    assert planner.cross_level_transfer_rejections == 0
    assert planner.transferred_action_algebra_active
    assert planner.active_action_algebra_scope == "cross-level"
    assert planner.inherited_action_effects == {}
    assert planner.traversable_colors == {6}
    assert planner.diagnostic == "cross-level-action-algebra-confirmed"


def test_cross_level_action_algebra_rejects_noncommuting_action() -> None:
    effects = {1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)}
    planner = PhaseTopologyPlanner(
        action_effects=dict(effects),
        action_evidence=Counter({action_id: 2 for action_id in effects}),
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
    )
    planner.reset_level(retain_action_algebra=True)
    before = _frame(28, 18, color=6)
    after = _frame(28, 18, color=6)
    _paint_body(before, (8, 7), left_color=2, right_color=11)
    _paint_body(after, (3, 7), left_color=2, right_color=11)

    planner.observe(
        _freeze(before),
        _freeze(after),
        action_id=4,
        progressed=False,
    )

    assert planner.action_effects == {4: (-5, 0)}
    assert planner.cross_level_transfer_confirmations == 0
    assert planner.cross_level_transfer_rejections == 1
    assert not planner.transferred_action_algebra_active
    assert planner.active_action_algebra_scope is None
    assert planner.inherited_action_effects == {}
    assert planner.diagnostic == "cross-level-action-algebra-rejected"


def test_cross_level_hypothesis_waits_through_scene_discontinuity() -> None:
    effects = {1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)}
    planner = PhaseTopologyPlanner(
        action_effects=dict(effects),
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
    )
    planner.reset_level(retain_action_algebra=True)
    before = _frame(28, 18, color=0)
    after = _frame(28, 18, color=6)
    _paint_body(before, (3, 7), left_color=2, right_color=11)
    _paint_body(after, (8, 7), left_color=2, right_color=11)

    planner.observe(
        _freeze(before),
        _freeze(after),
        action_id=4,
        progressed=False,
    )

    assert planner.action_effects == {}
    assert planner.inherited_action_effects == effects
    assert planner.cross_level_transfer_confirmations == 0
    assert planner.cross_level_transfer_rejections == 0
    assert not planner.transferred_action_algebra_active
    assert planner.inherited_action_algebra_scope == "cross-level"


def test_same_level_retry_algebra_uses_distinct_prospective_authority() -> None:
    effects = {1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)}
    planner = PhaseTopologyPlanner(
        action_effects=dict(effects),
        action_evidence=Counter({action_id: 4 for action_id in effects}),
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
    )
    planner.reset_level(
        retain_action_algebra=True,
        retention_scope="same-level-retry",
    )
    before = _frame(28, 18, color=6)
    after = _frame(28, 18, color=6)
    _paint_body(before, (3, 7), left_color=2, right_color=11)
    _paint_body(after, (8, 7), left_color=2, right_color=11)

    planner.observe(
        _freeze(before),
        _freeze(after),
        action_id=4,
        progressed=False,
    )

    assert planner.action_effects == effects
    assert planner.transferred_action_algebra_active
    assert planner.active_action_algebra_scope == "same-level-retry"
    assert planner.retry_transfer_confirmations == 1
    assert planner.retry_transfer_rejections == 0
    assert planner.cross_level_transfer_confirmations == 0
    assert planner.diagnostic == "retry-action-algebra-confirmed"


def test_temporal_meter_and_same_role_reset_are_learned_relationally() -> None:
    frames = []
    for anchor, remaining_width in (
        ((2, 10), 12),
        ((6, 10), 10),
        ((10, 10), 8),
    ):
        frame = _frame(40, 30, color=3)
        _paint_ring(frame, (15, 10), color=7)
        _paint_ring(frame, (27, 5), color=7)
        _paint_meter(frame, color=7, remaining_width=remaining_width)
        _paint_body(frame, anchor)
        frames.append(_freeze(frame))
    reset = _frame(40, 30, color=3)
    _paint_ring(reset, (27, 5), color=7)
    _paint_meter(reset, color=7, remaining_width=12)
    _paint_body(reset, (14, 10))
    frames.append(_freeze(reset))
    planner = PhaseTopologyPlanner()

    planner.observe(frames[0], frames[1], action_id=4, progressed=False)
    planner.observe(frames[1], frames[2], action_id=4, progressed=False)

    assert planner.budget_color == 7
    assert planner.budget_unit == 4
    assert planner.budget_capacity == 24
    assert planner.remaining_budget == 4
    assert {item.bbox for item in planner.resource_candidates} == {
        (15, 10, 17, 12),
        (27, 5, 29, 7),
    }

    planner.observe(frames[2], frames[3], action_id=4, progressed=False)

    assert planner.resource_resets == 1
    assert planner.horizon_resets == 0
    assert planner.remaining_budget == 6
    assert {item.bbox for item in planner.resource_candidates} == {(27, 5, 29, 7)}


def test_joint_resource_reappearance_restarts_bounded_horizon_options() -> None:
    frame = _frame(40, 30, color=3)
    _paint_ring(frame, (15, 10), color=7)
    _paint_ring(frame, (27, 5), color=7)
    _paint_meter(frame, color=7, remaining_width=12)
    frozen = _freeze(frame)
    planner = PhaseTopologyPlanner(
        budget_color=7,
        budget_unit=4,
        budget_capacity=24,
        budget_area=24,
        selections=83,
        operator_applications=7,
        active_operator=((4, 4), (5, 4)),
        resource_exit_edges={((10, 10), 1)},
    )
    _meter, resources = planner._temporal_components(frozen)
    planner.consumed_resources = {
        (item.color, item.bbox, item.shape) for item in resources
    }

    planner.observe(frozen, frozen, action_id=1, progressed=False)

    assert planner.horizon_resets == 1
    assert planner.consumed_resources == set()
    assert len(planner.resource_candidates) == 2
    assert planner.selections == 0
    assert planner.operator_applications == 0
    assert planner.active_operator is None
    assert planner.resource_exit_edges == set()


def test_temporal_csp_uses_latest_feasible_reset_before_operator() -> None:
    frame = _frame(40, 30, color=3)
    _paint_ring(frame, (16, 21), color=7)
    _paint_meter(frame, color=7, remaining_width=4)
    _paint_body(frame, (20, 20))
    frozen = _freeze(frame)
    resource = next(
        item
        for item in components(frozen)
        if item.color == 7 and item.bbox == (16, 21, 18, 23)
    )
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(20, 20),
        traversable_colors={3},
        current_pattern=(3, 3, ((0, 0),)),
        goal_pattern=(3, 3, ((2, 2),)),
        operator_cells=((21, 21), (22, 21)),
        operator_applications=1,
        budget_color=7,
        budget_area=8,
        budget_capacity=80,
        budget_unit=4,
        resource_candidates=(resource,),
    )

    selected = planner.select(frozen, (1, 2, 3, 4))

    assert selected == 3
    assert planner.pending_resource is not None
    assert planner.active_resource == planner.pending_resource
    assert planner.last_plan_length == 1
    assert planner.diagnostic == "executing-resource-reset-option"

    planner.pending_action = None
    planner.pending_anchor = None
    planner.pending_source = None
    planner.current_pattern = planner.goal_pattern
    planner.goal_host = (30, 20, 33, 23)
    planner.goal_cells = ((31, 21),)

    committed = planner.select(frozen, (1, 2, 3, 4))

    assert committed == 3
    assert planner.diagnostic == "executing-resource-reset-option"


def test_transferred_algebra_cannot_schedule_reset_before_local_operator_effect() -> (
    None
):
    frame = _frame(40, 30, color=3)
    _paint_ring(frame, (16, 21), color=7)
    _paint_meter(frame, color=7, remaining_width=4)
    _paint_body(frame, (20, 20))
    frozen = _freeze(frame)
    resource = next(
        item
        for item in components(frozen)
        if item.color == 7 and item.bbox == (16, 21, 18, 23)
    )
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        transferred_action_algebra_active=True,
        current_anchor=(20, 20),
        traversable_colors={3},
        current_pattern=(3, 3, ((0, 0),)),
        goal_pattern=(3, 3, ((2, 2),)),
        operator_cells=((21, 11), (22, 11)),
        budget_color=7,
        budget_area=8,
        budget_capacity=80,
        budget_unit=4,
        resource_candidates=(resource,),
    )

    selected = planner.select(frozen, (1, 2, 3, 4))

    assert selected == 1
    assert planner.pending_resource is None
    assert planner.diagnostic == "executing-operator-option"

    planner.pending_action = None
    planner.pending_anchor = None
    planner.pending_source = None
    planner.operator_applications = 1
    selected_after_local_effect = planner.select(frozen, (1, 2, 3, 4))

    assert selected_after_local_effect == 3
    assert planner.pending_resource is not None
    assert planner.diagnostic == "executing-resource-reset-option"


def test_temporal_csp_schedules_reset_when_equal_goal_exceeds_budget() -> None:
    frame = _frame(40, 30, color=6)
    _paint_ring(frame, (11, 21), color=2)
    _paint_meter(frame, color=2, remaining_width=4)
    _paint_body(frame, (20, 20))
    frozen = _freeze(frame)
    resource = next(
        item
        for item in components(frozen)
        if item.color == 2 and item.bbox == (11, 21, 13, 23)
    )
    phase = (3, 3, ((0, 0), (2, 2)))
    planner = PhaseTopologyPlanner(
        action_effects={1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)},
        colored_mask=tuple(
            (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
        ),
        current_anchor=(20, 20),
        traversable_colors={6},
        current_pattern=phase,
        goal_pattern=phase,
        goal_host=(0, 20, 3, 23),
        goal_cells=((1, 21),),
        budget_color=2,
        budget_area=8,
        budget_capacity=80,
        budget_unit=4,
        resource_candidates=(resource,),
    )

    selected = planner.select(frozen, (1, 2, 3, 4))

    assert selected == 3
    assert planner.pending_resource is not None
    assert planner.last_plan_length == 2
    assert planner.diagnostic == "executing-resource-reset-option"


def test_phase_topology_is_serializable_and_exactly_off_by_default() -> None:
    default = MindConfig()
    enabled = MindConfig(enable_phase_topology_planning=True)

    assert default == MindConfig(enable_phase_topology_planning=False)
    assert not SymbolicPolicy(default).explorer.phase_topology_planning
    assert SymbolicPolicy(enabled).explorer.phase_topology_planning
    assert MindConfig.from_dict(enabled.to_dict()) == enabled
