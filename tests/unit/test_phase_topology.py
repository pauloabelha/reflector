from reflector.core.mind import MindConfig
from reflector.core.phase_topology import (
    PhaseTopologyPlanner,
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
) -> None:
    for local_y in range(4):
        for local_x in range(4):
            frame[anchor[1] + local_y][anchor[0] + local_x] = 9 if local_x < 2 else 12


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
    assert planner.diagnostic == "operator-induced-phase-transition"


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


def test_unexplained_operator_teleport_does_not_invent_contextual_rule() -> None:
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
    assert planner.contextual_transitions == 0
    assert not planner.goal_latched
    assert planner.confirmations == 0
    assert planner.conflicts == 1
    assert planner.diagnostic == "predicted-anchor-transition-blocked"


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
