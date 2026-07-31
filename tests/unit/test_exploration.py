from collections import Counter

import pytest

from reflector import MindConfig
from reflector.exploration import (
    STARTER_SCHEMA_SET,
    ActionRole,
    ActionToken,
    EpistemicExplorer,
    GroundedRole,
    RelationalScheme,
    RoleRelation,
)
from reflector.perception import SceneTracker
from reflector.symbolic import Observation


def _scene(observation: Observation):
    return SceneTracker().perceive(observation)[0]


def test_explorer_tries_each_simple_action_before_repeating() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0), (0, 9)),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer()
    explorer.observe(observation, scene)

    first = explorer.select(observation, scene, (1, 2))
    explorer.observe(observation, scene)
    second = explorer.select(observation, scene, (1, 2))
    explorer.observe(observation, scene)
    third = explorer.select(observation, scene, (1, 2))

    assert first.token.action_id == 1
    assert second.token.action_id == 2
    assert third.token.action_id == 1
    assert "least-repeated" in third.reason


def test_game_over_retains_only_phase_topology_algebra_as_retry_hypothesis() -> None:
    effects = {1: (0, -5), 2: (0, 5), 3: (-5, 0), 4: (5, 0)}
    explorer = EpistemicExplorer(phase_topology_planning=True)
    planner = explorer.phase_topology_planner
    planner.action_effects = dict(effects)
    planner.action_evidence = Counter({action_id: 3 for action_id in effects})
    planner.colored_mask = tuple(
        (x, y, 9 if x < 2 else 12) for x in range(4) for y in range(4)
    )
    planner.current_anchor = (5, 5)
    planner.operator_cells = ((6, 6),)
    planner.resource_resets = 2
    explorer.current_level = 1
    game_over = Observation.create(
        state="GAME_OVER",
        available_actions=(0,),
        frame=((0, 0), (0, 0)),
        levels_completed=1,
    )

    explorer.observe(game_over, _scene(game_over))

    assert planner.action_effects == {}
    assert planner.inherited_action_effects == effects
    assert planner.inherited_action_algebra_scope == "same-level-retry"
    assert planner.current_anchor is None
    assert planner.operator_cells == ()
    assert planner.resource_resets == 0


def test_explorer_generates_distinct_legal_object_clicks() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0, 0),
            (0, 2, 2, 0, 3, 0),
            (0, 2, 2, 0, 0, 0),
            (0, 0, 0, 0, 0, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer()
    explorer.observe(observation, scene)
    choices = []
    for _ in range(3):
        choice = explorer.select(observation, scene, (6,))
        choices.append(choice.token)
        explorer.observe(observation, scene)

    assert all(token.action_id == 6 for token in choices)
    assert len({token.data for token in choices}) == 3
    assert choices[0].data == (("x", 4), ("y", 1))
    assert choices[1].data == (("x", 1), ("y", 1))


def test_compact_component_frontier_activates_only_after_click_only_failure() -> None:
    frame = (
        (0, 0, 0, 0, 0, 0, 0, 0),
        (0, 2, 2, 2, 0, 1, 1, 0),
        (0, 2, 2, 2, 0, 1, 1, 0),
        (0, 2, 2, 2, 0, 0, 0, 0),
        (0, 3, 3, 3, 0, 0, 0, 0),
        (0, 3, 0, 0, 0, 0, 0, 0),
        (0, 3, 0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0, 0, 0),
    )
    click_only = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=frame,
    )
    mixed = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 6),
        frame=frame,
    )
    explorer = EpistemicExplorer(compact_component_frontier=True)
    scene = _scene(click_only)

    assert not explorer._uses_compact_component_frontier(click_only, scene)
    explorer.level_failures = 1
    assert explorer._uses_compact_component_frontier(click_only, scene)
    assert not explorer._uses_compact_component_frontier(mixed, _scene(mixed))
    assert explorer._compact_component_candidates(frame)[:3] == (
        (2, 2),
        (5, 1),
        (1, 4),
    )


def test_compact_component_frontier_masks_only_dominated_edge_strips() -> None:
    def frame(counter: int, *, interior: int = 0):
        rows = [[0] * 8 for _ in range(8)]
        rows[0] = [7] * 8
        rows[0][counter] = 4
        rows[3][3] = interior
        rows[4][3] = 2
        return tuple(tuple(row) for row in rows)

    first = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=frame(1),
    )
    second = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=frame(5),
    )
    changed = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=frame(5, interior=3),
    )
    explorer = EpistemicExplorer(compact_component_frontier=True)
    explorer.level_failures = 1

    assert explorer._state_key(first, _scene(first)) == explorer._state_key(
        second,
        _scene(second),
    )
    assert explorer._state_key(first, _scene(first)) != explorer._state_key(
        changed,
        _scene(changed),
    )


def test_compact_frontier_prefers_repeated_enclosure_interiors_over_edge_ui() -> None:
    rows = [[0] * 16 for _ in range(12)]
    rows[-1] = [7] * 16
    rows[-1][-2] = 4
    for left in (2, 9):
        for x in range(left, left + 5):
            rows[3][x] = 2
            rows[7][x] = 2
        for y in range(3, 8):
            rows[y][left] = 2
            rows[y][left + 4] = 2
        rows[5][left + 2] = 3
    frame = tuple(tuple(row) for row in rows)
    explorer = EpistemicExplorer(
        compact_component_frontier=True,
        compact_component_nuisance_filter=True,
    )

    assert explorer._compact_component_candidates(frame)[:2] == (
        (4, 5),
        (11, 5),
    )
    assert explorer.compact_component_nuisance_filtered == 1
    assert explorer.compact_component_enclosure_candidates >= 2


def test_compact_component_nuisance_filter_requires_frontier() -> None:
    with pytest.raises(ValueError, match="requires the compact component frontier"):
        MindConfig(enable_compact_component_nuisance_filter=True)


def test_compact_component_frontier_rejects_an_expanding_vocabulary() -> None:
    frame = tuple(
        tuple(1 if x in {2, 5} else 0 for x in range(8))
        for _y in range(8)
    )
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=frame,
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(compact_component_frontier=True)
    explorer.level_failures = 1

    active, diagnostic, candidates, objects = (
        explorer._compact_component_frontier_status(observation, scene)
    )

    assert not active
    assert diagnostic == "expands-perceptual-ontology"
    assert candidates > objects


def test_compact_component_frontier_latches_one_ontology_per_retry() -> None:
    compact_frame = (
        (0, 0, 0, 0, 0, 0, 0, 0),
        (0, 2, 2, 2, 0, 1, 1, 0),
        (0, 2, 2, 2, 0, 1, 1, 0),
        (0, 2, 2, 2, 0, 0, 0, 0),
        (0, 3, 3, 3, 0, 0, 0, 0),
        (0, 3, 0, 0, 0, 0, 0, 0),
        (0, 3, 0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0, 0, 0),
    )
    expanding_frame = tuple(
        tuple(1 if x in {2, 5} else 0 for x in range(8))
        for _y in range(8)
    )

    def observation(frame):
        return Observation.create(
            state="NOT_FINISHED",
            available_actions=(6,),
            frame=frame,
        )

    compact = observation(compact_frame)
    expanding = observation(expanding_frame)
    explorer = EpistemicExplorer(compact_component_frontier=True)
    explorer.level_failures = 1

    assert explorer._uses_compact_component_frontier(
        compact,
        _scene(compact),
    )
    assert explorer._uses_compact_component_frontier(
        expanding,
        _scene(expanding),
    )

    explorer._reset_compact_component_frontier_retry(retain_previous=True)
    explorer.level_failures = 2
    assert not explorer._uses_compact_component_frontier(
        expanding,
        _scene(expanding),
    )


def test_explorer_navigates_known_edges_to_an_untried_frontier() -> None:
    left = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1,),
        frame=((1, 0),),
    )
    right = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 1),),
    )
    left_scene = _scene(left)
    right_scene = _scene(right)
    explorer = EpistemicExplorer()
    explorer.observe(left, left_scene)
    assert explorer.select(left, left_scene, (1,)).token.action_id == 1
    explorer.observe(right, right_scene)
    assert explorer.select(right, right_scene, (1, 2)).token.action_id == 2
    explorer.observe(left, left_scene)

    navigation = explorer.select(left, left_scene, (1,))

    assert navigation.token.action_id == 1
    assert "navigate-known-state-graph" in navigation.reason


def test_explorer_balances_interventions_across_novel_states() -> None:
    first = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((1, 0),),
    )
    second = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 1),),
    )
    first_scene = _scene(first)
    second_scene = _scene(second)
    explorer = EpistemicExplorer()
    explorer.observe(first, first_scene)

    action_one = explorer.select(first, first_scene, (1, 2))
    explorer.observe(second, second_scene)
    action_two = explorer.select(second, second_scene, (1, 2))

    assert action_one.token.action_id == 1
    assert action_two.token.action_id == 2


def test_hierarchical_fairness_prevents_click_coordinates_crowding_actions() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 6),
        frame=(
            (1, 0, 2, 0, 3),
            (0, 4, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(hierarchical_action_fairness=True)
    explorer.observe(observation, scene)

    choices = []
    for _ in range(6):
        choices.append(explorer.select(observation, scene, (1, 2, 6)).token.action_id)
        explorer.observe(observation, scene)

    assert choices == [1, 2, 6, 1, 2, 6]


def test_flat_exploration_preserves_coordinate_level_ablation() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 6),
        frame=(
            (1, 0, 2, 0, 3),
            (0, 4, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(hierarchical_action_fairness=False)
    explorer.observe(observation, scene)

    choices = []
    for _ in range(6):
        choices.append(explorer.select(observation, scene, (1, 2, 6)).token.action_id)
        explorer.observe(observation, scene)

    assert choices == [1, 2, 6, 6, 6, 6]


def test_boundary_nuisance_state_key_requires_action_independent_motion() -> None:
    def frame(position: int, *, interior: int = 0):
        rows = [[5] * 6 for _ in range(6)]
        rows[0][position] = 0
        rows[3][3] = interior
        return tuple(tuple(row) for row in rows)

    enabled = EpistemicExplorer(boundary_nuisance_state_key=True)
    positions = (5, 4, 3, 2, 1)
    for left, right, action_id in zip(
        positions,
        positions[1:],
        (1, 2, 3, 1),
    ):
        enabled._observe_boundary_nuisance(
            frame(left),
            frame(right),
            action_id,
        )

    assert enabled.boundary_nuisance_sides == {0}
    first = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3),
        frame=frame(1),
    )
    shifted = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3),
        frame=frame(0),
    )
    changed_interior = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3),
        frame=frame(0, interior=9),
    )

    assert enabled._state_key(first, _scene(first)) == enabled._state_key(
        shifted,
        _scene(shifted),
    )
    assert enabled._state_key(first, _scene(first)) != enabled._state_key(
        changed_interior,
        _scene(changed_interior),
    )

    one_action = EpistemicExplorer(boundary_nuisance_state_key=True)
    for left, right in zip(positions, positions[1:]):
        one_action._observe_boundary_nuisance(frame(left), frame(right), 1)
    assert one_action.boundary_nuisance_sides == set()

    inconsistent = EpistemicExplorer(boundary_nuisance_state_key=True)
    for left, right, action_id in zip(
        (5, 4, 3, 4, 3),
        (4, 3, 4, 3, 2),
        (1, 2, 3, 1, 2),
    ):
        inconsistent._observe_boundary_nuisance(
            frame(left),
            frame(right),
            action_id,
        )
    assert inconsistent.boundary_nuisance_sides == set()


def test_boundary_nuisance_state_key_accepts_fixed_endpoint_monotone_strip() -> None:
    def frame(length: int, *, color: int = 0):
        rows = [[5] * 16 for _ in range(8)]
        for index in range(16 - length, 16):
            rows[0][index] = color
        return tuple(tuple(row) for row in rows)

    enabled = EpistemicExplorer(boundary_nuisance_state_key=True)
    for left, right, action_id in zip(
        range(1, 5),
        range(2, 6),
        (1, 2, 3, 1),
    ):
        enabled._observe_boundary_nuisance(
            frame(left),
            frame(right),
            action_id,
        )

    assert enabled.boundary_nuisance_sides == {0}
    assert enabled.to_dict()["boundary_nuisance_evidence"] == 4

    one_action = EpistemicExplorer(boundary_nuisance_state_key=True)
    for left, right in zip(range(1, 5), range(2, 6)):
        one_action._observe_boundary_nuisance(
            frame(left),
            frame(right),
            1,
        )
    assert one_action.boundary_nuisance_sides == set()

    color_changed = EpistemicExplorer(boundary_nuisance_state_key=True)
    color_changed._observe_boundary_nuisance(frame(1), frame(2), 1)
    color_changed._observe_boundary_nuisance(frame(2), frame(3), 2)
    color_changed._observe_boundary_nuisance(
        frame(3),
        frame(4, color=9),
        3,
    )
    color_changed._observe_boundary_nuisance(
        frame(4, color=9),
        frame(5, color=9),
        1,
    )
    assert color_changed.boundary_nuisance_sides == set()


def test_boundary_nuisance_fairness_activates_only_after_evidence() -> None:
    explorer = EpistemicExplorer(
        hierarchical_action_fairness=True,
        failure_conditioned_fairness=True,
        boundary_nuisance_state_key=True,
        boundary_nuisance_fairness=True,
    )

    assert not explorer.uses_action_family_schema

    explorer.boundary_nuisance_sides.add(0)
    assert explorer.uses_action_family_schema

    explorer._reset_boundary_nuisance_state()
    assert not explorer.uses_action_family_schema

    with pytest.raises(ValueError, match="boundary-nuisance fairness"):
        MindConfig(enable_boundary_nuisance_fairness=True)


def test_paired_object_contact_plan_is_structural_and_action_equivariant() -> None:
    def frame(extra_pair_member: bool = False):
        rows = [[1] * 20 for _ in range(20)]
        for y in range(5, 15):
            for x in range(2, 18):
                rows[y][x] = 5
        for center_x in ((5, 14, 10) if extra_pair_member else (5, 14)):
            for y in range(9, 12):
                for x in range(center_x - 1, center_x + 2):
                    rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    explorer = EpistemicExplorer(paired_object_contact_planning=True)
    grounding = explorer._ground_paired_objects(frame())

    assert grounding is not None
    assert grounding.reflection_axis == "horizontal"
    assert grounding.anchors == ((5, 10), (14, 10))
    assert grounding.substrate_color == 5
    assert explorer._ground_paired_objects(frame(extra_pair_member=True)) is None

    explorer.paired_grounding = grounding
    explorer.paired_effects = {
        7: ((1, 0), (-1, 0)),
        2: ((0, -1), (0, -1)),
    }
    first = explorer._paired_contact_plan(
        frame(),
        grounding.anchors,
        frozenset({2, 7}),
    )
    assert first is not None
    assert first[0] == 7
    assert first[1] == 3

    explorer.paired_effects = {
        3: ((1, 0), (-1, 0)),
        6: ((0, -1), (0, -1)),
    }
    permuted = explorer._paired_contact_plan(
        frame(),
        grounding.anchors,
        frozenset({3, 6}),
    )
    assert permuted is not None
    assert permuted[0] == 3
    assert permuted[1] == first[1]


def test_paired_marker_relation_is_recolored_action_equivariant_and_credited() -> None:
    def frame(
        anchors: tuple[tuple[int, int], tuple[int, int]],
        *,
        marker_color: int,
    ) -> tuple[tuple[int, ...], ...]:
        rows = [[1] * 20 for _ in range(20)]
        for y in range(2, 18):
            for x in range(2, 18):
                rows[y][x] = 5
        for center_x in (5, 14):
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if (dx + dy) % 2 == 0:
                        rows[14 + dy][center_x + dx] = marker_color
        for center_x, center_y in anchors:
            for y in range(center_y - 1, center_y + 2):
                for x in range(center_x - 1, center_x + 2):
                    rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    initial = ((5, 6), (14, 6))
    moved = ((5, 7), (14, 7))
    explorer = EpistemicExplorer(
        paired_object_contact_planning=True,
        paired_terminal_relation_mode="marker-first",
    )
    initial_frame = frame(initial, marker_color=8)
    grounding = explorer._ground_paired_objects(initial_frame)
    assert grounding is not None
    explorer.paired_grounding = grounding
    explorer.paired_effects = {
        2: ((0, 1), (0, 1)),
        7: ((1, 0), (-1, 0)),
    }
    explorer.paired_probes = {2, 7}

    plan = explorer._paired_marker_plan(
        initial_frame,
        initial,
        frozenset({2, 7}),
    )
    assert plan is not None
    assert plan[:2] == (2, 8)
    assert plan[2] == ((5, 14), (14, 14))
    assert explorer.paired_marker_support == 10

    selected = explorer._select_paired_object_contact(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(2, 7),
            frame=initial_frame,
        ),
        (ActionToken(2), ActionToken(7)),
    )
    assert selected == ActionToken(2)
    assert explorer.paired_active_terminal_relation == "paired-marker-coverage"
    assert explorer.paired_relation_pending == (
        "paired-marker-coverage",
        16,
        14,
    )

    explorer._observe_paired_object_contact(
        initial_frame,
        frame(moved, marker_color=8),
        progressed=False,
    )
    assert explorer.paired_relation_confirmations == 1
    assert explorer.paired_relation_falsifications == 0

    explorer.paired_relation_target = ((5, 14), (14, 14))
    explorer.paired_relation_pending = (
        "paired-marker-coverage",
        2,
        0,
    )
    explorer._assess_paired_terminal_relation(initial)
    assert explorer.paired_relation_falsifications == 1
    assert explorer.paired_rejected_relation_targets == {
        ((5, 14), (14, 14))
    }
    accommodated = explorer._paired_marker_plan(
        initial_frame,
        initial,
        frozenset({2, 7}),
    )
    assert accommodated is not None
    assert accommodated[2] != ((5, 14), (14, 14))

    composed = EpistemicExplorer(
        paired_object_contact_planning=True,
        paired_contextual_transitions=True,
        paired_terminal_relation_mode="marker-first",
    )
    composed.paired_grounding = composed._ground_paired_objects(initial_frame)
    assert composed.paired_grounding is not None
    composed.paired_effects = explorer.paired_effects
    composed.paired_contextual_evidence = {
        (((5, 13), (14, 13)), 2): Counter({initial: 2})
    }
    composed_plan = composed._paired_marker_plan(
        initial_frame,
        initial,
        frozenset({2, 7}),
    )
    assert composed_plan is not None
    assert composed_plan[2] == ((14, 14), (5, 14))
    assert composed.paired_contextual_planner_uses > 0

    recolored = EpistemicExplorer(
        paired_object_contact_planning=True,
        paired_terminal_relation_mode="marker-first",
    )
    recolored_frame = frame(initial, marker_color=12)
    recolored.paired_grounding = recolored._ground_paired_objects(
        recolored_frame
    )
    assert recolored.paired_grounding is not None
    recolored.paired_effects = {
        9: ((0, 1), (0, 1)),
        3: ((1, 0), (-1, 0)),
    }
    recolored_plan = recolored._paired_marker_plan(
        recolored_frame,
        initial,
        frozenset({3, 9}),
    )
    assert recolored_plan is not None
    assert recolored_plan[:3] == (9, 8, ((5, 14), (14, 14)))

    with pytest.raises(ValueError, match="terminal relation hypotheses"):
        MindConfig(paired_terminal_relation_mode="marker-first")
    with pytest.raises(ValueError, match="must be contact-only"):
        MindConfig(
            enable_paired_object_contact_planning=True,
            paired_terminal_relation_mode="unknown",
        )


def test_paired_occlusion_procedure_reuses_progress_and_confirms_macro() -> None:
    def frame(
        anchors: tuple[tuple[int, int], tuple[int, int]] | None,
    ) -> tuple[tuple[int, ...], ...]:
        rows = [[1] * 20 for _ in range(20)]
        for y in range(2, 18):
            for x in range(2, 18):
                rows[y][x] = 5
        if anchors is not None:
            for center_x, center_y in anchors:
                for y in range(center_y - 1, center_y + 2):
                    for x in range(center_x - 1, center_x + 2):
                        rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    initial = ((5, 6), (14, 6))
    exit_anchors = ((6, 12), (13, 12))
    initial_frame = frame(initial)
    hidden_frame = frame(None)
    exit_frame = frame(exit_anchors)
    explorer = EpistemicExplorer(
        paired_object_contact_planning=True,
        paired_occlusion_procedure_mode="reuse-progress",
    )
    explorer.paired_grounding = explorer._ground_paired_objects(initial_frame)
    assert explorer.paired_grounding is not None

    explorer.paired_pending = ("contact", 7, initial)
    explorer._observe_paired_object_contact(
        initial_frame,
        initial_frame,
        progressed=True,
    )
    assert explorer.paired_progress_action == 7

    def observe_macro_once() -> None:
        explorer.paired_pending = ("plan", 2, initial)
        explorer._observe_paired_object_contact(
            initial_frame,
            hidden_frame,
            progressed=False,
        )
        assert explorer.paired_occlusion_active
        observation = Observation.create(
            state="NOT_FINISHED",
            available_actions=(2, 7),
            frame=hidden_frame,
        )
        first = explorer._select_paired_object_contact(
            observation,
            (ActionToken(2), ActionToken(7)),
        )
        assert first == ActionToken(7)
        explorer._observe_paired_object_contact(
            hidden_frame,
            hidden_frame,
            progressed=False,
        )
        second = explorer._select_paired_object_contact(
            observation,
            (ActionToken(2), ActionToken(7)),
        )
        assert second == ActionToken(7)
        explorer._observe_paired_object_contact(
            hidden_frame,
            exit_frame,
            progressed=False,
        )

    observe_macro_once()
    assert explorer.paired_occlusion_proposals == 1
    assert (
        explorer._confirmed_paired_occlusion_macro(initial, 2) is None
    )
    observe_macro_once()
    assert explorer.paired_occlusion_confirmations == 1
    assert explorer._confirmed_paired_occlusion_macro(initial, 2) == (
        (7, 7),
        exit_anchors,
    )

    with pytest.raises(ValueError, match="occlusion procedures"):
        MindConfig(paired_occlusion_procedure_mode="reuse-progress")
    with pytest.raises(ValueError, match="must be off"):
        MindConfig(
            enable_paired_object_contact_planning=True,
            paired_occlusion_procedure_mode="unknown",
        )


def test_paired_contact_merge_has_two_evidenced_continuations() -> None:
    def frame(merged_width: int = 0):
        rows = [[1] * 20 for _ in range(20)]
        for y in range(5, 15):
            for x in range(2, 18):
                rows[y][x] = 5
        if merged_width:
            for y in range(9, 12):
                for x in range(10 - merged_width // 2, 10 + merged_width // 2):
                    rows[y][x] = 10
        else:
            for center_x in (5, 14):
                for y in range(9, 12):
                    for x in range(center_x - 1, center_x + 2):
                        rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    explorer = EpistemicExplorer(paired_object_contact_planning=True)
    grounding = explorer._ground_paired_objects(frame())
    assert grounding is not None
    explorer.paired_grounding = grounding
    explorer.paired_contact_action = 7
    explorer.paired_pending = ("plan", 7, grounding.anchors)

    merged = frame(merged_width=6)
    explorer._observe_paired_object_contact(
        frame(),
        merged,
        progressed=False,
    )
    assert explorer.paired_latent_contact

    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(2, 7),
        frame=merged,
    )
    first = explorer._select_paired_object_contact(
        observation,
        (ActionToken(2), ActionToken(7)),
    )
    assert first == ActionToken(7)
    assert explorer.paired_contact_continuations == 1

    narrower = frame(merged_width=4)
    explorer._observe_paired_object_contact(
        merged,
        narrower,
        progressed=False,
    )
    second = explorer._select_paired_object_contact(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(2, 7),
            frame=narrower,
        ),
        (ActionToken(2), ActionToken(7)),
    )
    assert second == ActionToken(7)
    assert explorer.paired_contact_continuations == 2

    explorer._observe_paired_object_contact(
        narrower,
        narrower,
        progressed=False,
    )
    assert not explorer.paired_latent_contact
    assert explorer.paired_diagnostic == "contact-continuation-no-effect"


def test_paired_contextual_transition_requires_confirmation_and_is_equivariant() -> None:
    def frame(
        anchors: tuple[tuple[int, int], tuple[int, int]],
    ) -> tuple[tuple[int, ...], ...]:
        rows = [[1] * 20 for _ in range(20)]
        for y in range(2, 18):
            for x in range(2, 18):
                rows[y][x] = 5
        for center_x, center_y in anchors:
            for y in range(center_y - 1, center_y + 2):
                for x in range(center_x - 1, center_x + 2):
                    rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    def confirmed_plan(
        *,
        initial: tuple[tuple[int, int], tuple[int, int]],
        transported: tuple[tuple[int, int], tuple[int, int]],
        effect: tuple[tuple[int, int], tuple[int, int]],
        contextual_action: int,
        alternate_action: int,
    ) -> tuple[EpistemicExplorer, tuple[int, int]]:
        explorer = EpistemicExplorer(
            paired_object_contact_planning=True,
            paired_contextual_transitions=True,
        )
        grounding = explorer._ground_paired_objects(frame(initial))
        assert grounding is not None
        explorer.paired_grounding = grounding
        explorer.paired_effects = {
            contextual_action: effect,
            alternate_action: effect,
        }
        represented = frozenset({contextual_action, alternate_action})

        before = explorer._paired_contact_plan(
            frame(initial),
            initial,
            represented,
        )
        assert before is not None
        assert before[0] == contextual_action

        for expected_count in (1, 2):
            explorer.paired_pending = ("plan", contextual_action, initial)
            explorer._observe_paired_object_contact(
                frame(initial),
                frame(transported),
                progressed=False,
            )
            evidence = explorer.paired_contextual_evidence[
                (initial, contextual_action)
            ]
            assert evidence[transported] == expected_count
            if expected_count == 1:
                still_unconfirmed = explorer._paired_contact_plan(
                    frame(initial),
                    initial,
                    represented,
                )
                assert still_unconfirmed is not None
                assert still_unconfirmed[0] == contextual_action

        after = explorer._paired_contact_plan(
            frame(initial),
            initial,
            represented,
        )
        assert after is not None
        assert after[0] == alternate_action
        assert explorer.paired_contextual_confirmations == 1
        assert explorer.paired_contextual_planner_uses > 0
        return explorer, after

    horizontal, horizontal_plan = confirmed_plan(
        initial=((5, 10), (14, 10)),
        transported=((4, 10), (15, 10)),
        effect=((1, 0), (-1, 0)),
        contextual_action=7,
        alternate_action=9,
    )
    vertical, vertical_plan = confirmed_plan(
        initial=((10, 5), (10, 14)),
        transported=((10, 4), (10, 15)),
        effect=((0, 1), (0, -1)),
        contextual_action=3,
        alternate_action=8,
    )
    assert horizontal_plan[1] == vertical_plan[1]

    conflict = ((3, 10), (16, 10))
    horizontal.paired_pending = (
        "plan",
        7,
        ((5, 10), (14, 10)),
    )
    horizontal._observe_paired_object_contact(
        frame(((5, 10), (14, 10))),
        frame(conflict),
        progressed=False,
    )
    assert (((5, 10), (14, 10)), 7) in (
        horizontal.paired_contextual_quarantined
    )
    assert horizontal.paired_contextual_conflicts == 1

    with pytest.raises(ValueError, match="paired contextual transitions"):
        MindConfig(enable_paired_contextual_transitions=True)


def test_paired_transport_family_requires_two_convergent_trigger_edges() -> None:
    def frame(
        anchors: tuple[tuple[int, int], tuple[int, int]],
        *,
        trigger: tuple[int, int] | None = None,
        trigger_color: int = 8,
    ) -> tuple[tuple[int, ...], ...]:
        rows = [[1] * 20 for _ in range(20)]
        for y in range(2, 18):
            for x in range(2, 18):
                rows[y][x] = 5
        if trigger is not None:
            rows[trigger[1]][trigger[0]] = trigger_color
        for center_x, center_y in anchors:
            for y in range(center_y - 1, center_y + 2):
                for x in range(center_x - 1, center_x + 2):
                    rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    initial = ((5, 8), (14, 8))
    second = ((5, 11), (14, 11))
    destination = ((5, 5), (14, 5))
    explorer = EpistemicExplorer(
        paired_object_contact_planning=True,
        paired_contextual_transitions=True,
        paired_transport_family=True,
    )
    grounding = explorer._ground_paired_objects(frame(initial))
    assert grounding is not None
    explorer.paired_grounding = grounding
    explorer.paired_effects = {
        2: ((0, 1), (0, 1)),
        4: ((1, 0), (-1, 0)),
    }

    first_frame = frame(initial, trigger=(14, 10))
    for _ in range(2):
        explorer.paired_pending = ("plan", 2, initial)
        explorer._observe_paired_object_contact(
            first_frame,
            frame(destination),
            progressed=False,
        )
    assert explorer.paired_transport_successor is None

    second_frame = frame(second, trigger=(7, 11))
    for _ in range(2):
        explorer.paired_pending = ("plan", 4, second)
        explorer._observe_paired_object_contact(
            second_frame,
            frame(destination),
            progressed=False,
        )
    assert explorer.paired_transport_trigger_color == 8
    assert explorer.paired_transport_successor == destination
    assert explorer.paired_transport_inductions == 1

    third = ((5, 14), (14, 14))
    third_frame = frame(third, trigger=(14, 16))
    nodes = explorer._paired_topology(third_frame, third)
    assert explorer._paired_transport_family_successor(
        third_frame,
        third,
        ((0, 1), (0, 1)),
        nodes,
    ) == destination

    recolored = EpistemicExplorer(
        paired_object_contact_planning=True,
        paired_contextual_transitions=True,
        paired_transport_family=True,
    )
    recolored.paired_contextual_evidence = {
        (initial, 7): Counter({destination: 2}),
        (second, 3): Counter({destination: 2}),
    }
    recolored.paired_contextual_trigger_colors = {
        (initial, 7): frozenset({12}),
        (second, 3): frozenset({12}),
    }
    recolored._induce_paired_transport_family()
    assert recolored.paired_transport_trigger_color == 12
    assert recolored.paired_transport_successor == destination

    divergent = ((5, 6), (14, 6))
    recolored.paired_contextual_evidence[(third, 9)] = Counter(
        {divergent: 2}
    )
    recolored.paired_contextual_trigger_colors[(third, 9)] = frozenset(
        {12}
    )
    recolored._induce_paired_transport_family()
    assert recolored.paired_transport_successor is None

    with pytest.raises(ValueError, match="paired transport family"):
        MindConfig(enable_paired_transport_family=True)


def test_paired_post_accommodation_plan_allowance_is_earned_once() -> None:
    explorer = EpistemicExplorer(
        paired_object_contact_planning=True,
        paired_contextual_transitions=True,
        paired_transport_family=True,
        paired_post_accommodation_plan=True,
    )
    assert explorer._paired_trial_cap() == 64

    explorer._earn_paired_post_accommodation_allowance(19)
    assert explorer._paired_trial_cap() == 64

    explorer.paired_transport_trigger_color = 8
    explorer.paired_transport_successor = ((5, 5), (14, 5))
    explorer._earn_paired_post_accommodation_allowance(19)
    assert explorer.paired_post_accommodation_allowance == 19
    assert explorer._paired_trial_cap() == 83

    explorer._earn_paired_post_accommodation_allowance(32)
    assert explorer.paired_post_accommodation_allowance == 19
    assert explorer._paired_trial_cap() == 83

    explorer._reset_paired_object_level()
    assert explorer.paired_post_accommodation_allowance == 0
    assert explorer._paired_trial_cap() == 64

    with pytest.raises(ValueError, match="post-accommodation plan"):
        MindConfig(enable_paired_post_accommodation_plan=True)


def test_failure_conditioned_fairness_preserves_parent_then_accommodates() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 6),
        frame=(
            (1, 0, 2, 0, 3),
            (0, 4, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    before = EpistemicExplorer(
        hierarchical_action_fairness=True,
        failure_conditioned_fairness=True,
    )
    before.observe(observation, scene)
    parent_choices = []
    for _ in range(6):
        parent_choices.append(
            before.select(observation, scene, (1, 2, 6)).token.action_id
        )
        before.observe(observation, scene)

    after = EpistemicExplorer(
        hierarchical_action_fairness=True,
        failure_conditioned_fairness=True,
    )
    after.observe(observation, scene)
    after.level_failures = 2
    accommodated_choices = []
    for _ in range(6):
        accommodated_choices.append(
            after.select(observation, scene, (1, 2, 6)).token.action_id
        )
        after.observe(observation, scene)

    assert parent_choices == [1, 2, 6, 6, 6, 6]
    assert accommodated_choices == [1, 2, 6, 1, 2, 6]


def test_failure_conditioned_fairness_requires_parent_mechanism() -> None:
    with pytest.raises(
        ValueError,
        match="failure-conditioned fairness requires hierarchical fairness",
    ):
        MindConfig(enable_failure_conditioned_fairness=True)


def test_successful_level_compiles_and_replays_coordinate_free_roles() -> None:
    first_level = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 0, 0),
        ),
        levels_completed=0,
    )
    second_level = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0),
            (0, 0, 0, 0),
            (0, 0, 1, 0),
        ),
        levels_completed=1,
    )
    first_scene = _scene(first_level)
    second_scene = _scene(second_level)
    explorer = EpistemicExplorer(successful_role_replay=True)
    explorer.observe(first_level, first_scene)

    learned = explorer.select(first_level, first_scene, (6,))
    explorer.observe(second_level, second_scene)
    replayed = explorer.select(second_level, second_scene, (6,))

    assert learned.token.data == (("x", 1), ("y", 1))
    assert replayed.token.data == (("x", 2), ("y", 2))
    assert replayed.reason.endswith("replay-successful-action-role")
    assert explorer.to_dict()["successful_program_length"] == 1


def test_pragmatic_disequilibrium_suspends_composite_replay() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0), (0, 0)),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(successful_role_replay=True)
    explorer.observe(observation, scene)
    explorer.successful_program = (ActionRole(2),)

    choice = explorer.select(
        observation,
        scene,
        (1, 2),
        pragmatic_disequilibrium=True,
    )

    assert choice.token.action_id == 1
    assert choice.reason.endswith("untried-current-state")
    assert explorer.successful_program == (ActionRole(2),)


def test_starter_schemas_are_content_free_and_enter_operative_credit() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=((0, 0, 0), (0, 9, 0), (0, 0, 0)),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(starter_schemas=True)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 1), ("y", 1))
    assert explorer.last_scheme_components == (
        "scheme:starter:intervene-on-object",
        "scheme:starter:probe-action-family",
    )
    assert explorer.to_dict()["starter_schemas"] == len(STARTER_SCHEMA_SET)
    serialized = repr(STARTER_SCHEMA_SET)
    assert "game_id" not in serialized
    assert "coordinate" not in serialized
    assert all(item.complexity_cost > 0 for item in STARTER_SCHEMA_SET)


def test_starter_action_schema_probes_each_legal_family() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 6),
        frame=(
            (1, 0, 2, 0, 3),
            (0, 4, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(starter_schemas=True)
    explorer.observe(observation, scene)

    choices = []
    for _ in range(6):
        choices.append(
            explorer.select(
                observation,
                scene,
                (1, 2, 6),
            ).token.action_id
        )
        explorer.observe(observation, scene)

    assert choices == [1, 2, 6, 1, 2, 6]


def test_relational_modifier_grounds_on_recolored_translated_objects() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0),
            (0, 7, 0, 8, 0),
            (0, 0, 0, 0, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(
        starter_schemas=True,
        relational_scheme_binding=True,
    )
    explorer.observe(observation, scene)
    scheme = RelationalScheme(
        scheme_id="translated",
        base_id="carry",
        modifier_id="manner",
        operator="full-manner",
        action_slots=(6, 6),
        constraints=(
            RoleRelation(
                color="different",
                area="same",
                shape="same",
                horizontal="right",
                vertical="aligned",
            ),
        ),
        evidence=("carry", "manner"),
    )
    explorer.relational_schemes[scheme.scheme_id] = scheme

    first = explorer.select(
        observation,
        scene,
        (6,),
        pragmatic_disequilibrium=True,
    )
    responsive = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (9, 9, 9, 9, 0),
            (0, 7, 0, 8, 0),
            (0, 0, 0, 0, 0),
        ),
    )
    responsive_scene = _scene(responsive)
    explorer.observe(responsive, responsive_scene)
    second = explorer.select(
        responsive,
        responsive_scene,
        (6,),
        pragmatic_disequilibrium=True,
    )

    assert first.token.data == (("x", 1), ("y", 1))
    assert second.token.data == (("x", 3), ("y", 1))
    assert "relational-scheme-binding" in second.reason
    assert "scheme:starter:bind-manner-to-action" in (
        explorer.last_scheme_components
    )
    assert repr(scheme).count("7") == 0
    assert repr(scheme).count("8") == 0


def test_no_effect_falsifies_only_the_grounded_relational_scheme() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0),),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(relational_scheme_binding=True)
    explorer.observe(observation, scene)
    scheme = RelationalScheme(
        scheme_id="falsified",
        base_id="base",
        modifier_id="modifier",
        operator="full-manner",
        action_slots=(2,),
        constraints=(RoleRelation(),),
        evidence=("base", "modifier"),
    )
    explorer.relational_schemes[scheme.scheme_id] = scheme

    first = explorer.select(
        observation,
        scene,
        (1, 2),
        pragmatic_disequilibrium=True,
    )
    explorer.observe(observation, scene)
    second = explorer.select(
        observation,
        scene,
        (1, 2),
        pragmatic_disequilibrium=True,
    )

    assert first.token.action_id == 2
    assert "relational-scheme-binding" in first.reason
    assert second.token.action_id == 1
    assert "relational-scheme-binding" not in second.reason
    assert explorer.to_dict()["falsified_relational_schemes"] == 1
    assert scheme.base_id == "base"
    assert scheme.modifier_id == "modifier"


def test_relational_program_identity_ignores_color_permutation_and_translation() -> None:
    source = (
        GroundedRole(
            ActionRole(6, color=2, area=1, shape=((0, 0),)),
            (1, 1),
        ),
        GroundedRole(
            ActionRole(6, color=3, area=1, shape=((0, 0),)),
            (3, 1),
        ),
    )
    transformed = (
        GroundedRole(
            ActionRole(6, color=8, area=1, shape=((0, 0),)),
            (11, 21),
        ),
        GroundedRole(
            ActionRole(6, color=7, area=1, shape=((0, 0),)),
            (13, 21),
        ),
    )

    assert EpistemicExplorer._relational_program_id(
        source
    ) == EpistemicExplorer._relational_program_id(transformed)


def test_relational_binding_is_inactive_before_pragmatic_disequilibrium() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0),),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(relational_scheme_binding=True)
    explorer.observe(observation, scene)
    explorer.relational_schemes["bound"] = RelationalScheme(
        scheme_id="bound",
        base_id="base",
        modifier_id="modifier",
        operator="full-manner",
        action_slots=(2,),
        constraints=(RoleRelation(),),
        evidence=("base", "modifier"),
    )

    choice = explorer.select(observation, scene, (1, 2))

    assert choice.token.action_id == 1
    assert choice.reason.endswith("untried-current-state")
    assert explorer.to_dict()["relational_scheme_trials"] == 0


def test_successful_schemes_become_inputs_to_bounded_variations() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3),
        frame=((0, 0), (0, 9)),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(parameterized_scheme_variation=True)
    explorer.observe(observation, scene)
    explorer._learn_parameterized_variations(
        (ActionRole(1), ActionRole(2))
    )
    assert explorer.parameterized_schemes == {}

    explorer._learn_parameterized_variations(
        (ActionRole(3), ActionRole(2))
    )

    operators = {
        scheme.operator for scheme in explorer.parameterized_schemes.values()
    }
    assert {"prefix", "suffix", "interleave"}.issubset(operators)
    assert all(
        len(scheme.roles) <= 32
        and scheme.base_id
        and scheme.argument_id
        and len(scheme.evidence) == 2
        for scheme in explorer.parameterized_schemes.values()
    )

    choice = explorer.select(
        observation,
        scene,
        (1, 2, 3),
        pragmatic_disequilibrium=True,
        structure_scores={},
    )

    assert "parameterized-scheme-variation" in choice.reason
    assert explorer.last_scheme_components
    assert any(
        component.startswith("base:")
        for component in explorer.last_scheme_components
    )
    assert any(
        component.startswith("argument:")
        for component in explorer.last_scheme_components
    )
    assert explorer.to_dict()["parameterized_scheme_trials"] == 1

    explorer.observe(observation, scene)
    second = explorer.select(
        observation,
        scene,
        (1, 2, 3),
        pragmatic_disequilibrium=True,
        structure_scores={
            explorer.last_scheme_components[0]: -1
        },
    )
    assert second.token != choice.token


def test_multicolor_affordance_precedes_fragmented_color_objects() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0, 0, 0),
            (0, 2, 2, 3, 3, 0, 0),
            (0, 2, 4, 4, 3, 0, 0),
            (0, 0, 0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(multicolor_click_objects=True)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 2), ("y", 1))


def test_multicolor_affordance_is_an_exact_disabled_ablation() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0, 0, 0),
            (0, 2, 2, 3, 3, 0, 0),
            (0, 2, 4, 4, 3, 0, 0),
            (0, 0, 0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(multicolor_click_objects=False)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 5), ("y", 4))


def test_click_object_ontology_accommodates_only_after_failure() -> None:
    active = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0, 0, 0),
            (0, 2, 2, 3, 3, 0, 0),
            (0, 2, 4, 4, 3, 0, 0),
            (0, 0, 0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0, 5, 0),
        ),
    )
    failed = Observation.create(
        state="GAME_OVER",
        available_actions=(0,),
        frame=active.frame,
    )
    scene = _scene(active)
    explorer = EpistemicExplorer(click_object_accommodation=True)
    explorer.observe(active, scene)

    before = explorer.select(active, scene, (6,))
    explorer.observe(failed, _scene(failed))
    explorer.observe(active, scene)
    after = explorer.select(active, scene, (6,))

    assert before.token.data == (("x", 5), ("y", 4))
    assert after.token.data == (("x", 2), ("y", 1))
    assert explorer.to_dict()["perceptual_accommodations"] == 1
    assert explorer.to_dict()["attempts"] == 1


def test_productive_role_reuse_activates_only_after_repeated_failure() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0),
            (0, 2, 0, 3, 0),
            (0, 0, 0, 0, 0),
        ),
    )
    scene = _scene(observation)
    role = ActionRole(6, color=3, area=1, shape=((0, 0),))
    explorer = EpistemicExplorer(productive_role_reuse=True)
    explorer.observe(observation, scene)
    explorer.role_trials[role] = 1
    explorer.role_responses[role] = 1

    before = explorer.select(observation, scene, (6,))
    explorer.level_failures = 2
    explorer.level_interventions = explorer.min_productive_reuse_interventions
    after = explorer.select(observation, scene, (6,))

    assert before.token.data == (("x", 1), ("y", 1))
    assert after.token.data == (("x", 3), ("y", 1))
    assert after.reason.endswith("reuse-productive-action-role")


def test_deep_failure_productive_reuse_only_raises_the_failed_retry_cap() -> None:
    baseline = EpistemicExplorer()
    enabled = EpistemicExplorer(deep_failure_productive_reuse=True)

    assert baseline._productive_reuse_trial_cap() == 8
    assert enabled._productive_reuse_trial_cap() == 8
    enabled.level_failures = 2
    assert enabled._productive_reuse_trial_cap() == 64
    assert baseline._productive_reuse_trial_cap() == 8


def test_local_relation_solver_induces_and_repairs_repeated_panel_rule() -> None:
    size = 64
    pixels = [[5 for _x in range(size)] for _y in range(size)]
    directions = (
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    )
    clues = (
        ((2, 0, 2, 0, 8, 2, 2, 0, 0), (9, 8, 9, 8, 9, 9, 8, 8)),
        ((2, 0, 2, 0, 8, 0, 2, 0, 2), (9, 8, 9, 8, 8, 9, 8, 9)),
        ((0, 2, 2, 0, 8, 0, 2, 2, 0), (9, 9, 9, 8, 8, 9, 9, 8)),
        ((0, 2, 2, 0, 8, 0, 0, 2, 2), (9, 9, 9, 9, 9, 9, 9, 9)),
    )
    origins = ((4, 2), (38, 2), (4, 36), (36, 36))
    block_size = 6
    step = 8
    subcell = block_size // 3
    for (origin_x, origin_y), (clue, colors) in zip(origins, clues):
        center_x = origin_x + step
        center_y = origin_y + step
        for (dx, dy), color in zip(directions, colors):
            block_x = center_x + dx * step
            block_y = center_y + dy * step
            for y in range(block_y, block_y + block_size):
                for x in range(block_x, block_x + block_size):
                    pixels[y][x] = color
        for clue_index, color in enumerate(clue):
            clue_x = center_x + clue_index % 3 * subcell
            clue_y = center_y + clue_index // 3 * subcell
            for y in range(clue_y, clue_y + subcell):
                for x in range(clue_x, clue_x + subcell):
                    pixels[y][x] = color

    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=tuple(tuple(row) for row in pixels),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(local_relation_solver=True)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 38), ("y", 38))
    assert choice.reason.endswith("repair-local-relation")

    transfer_pixels = [[5 for _x in range(size)] for _y in range(size)]
    transfer_clues = (
        (0, 2, 2, 0, 12, 0, 0, 2, 0),
        (0, 2, 0, 2, 12, 2, 0, 0, 2),
    )
    for center_y, clue in zip((22, 38), transfer_clues):
        center_x = 28
        for dx, dy in directions:
            block_x = center_x + dx * step
            block_y = center_y + dy * step
            for y in range(block_y, block_y + block_size):
                for x in range(block_x, block_x + block_size):
                    transfer_pixels[y][x] = 9
        for clue_index, color in enumerate(clue):
            clue_x = center_x + clue_index % 3 * subcell
            clue_y = center_y + clue_index // 3 * subcell
            for y in range(clue_y, clue_y + subcell):
                for x in range(clue_x, clue_x + subcell):
                    transfer_pixels[y][x] = color
    transfer = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=tuple(tuple(row) for row in transfer_pixels),
        levels_completed=1,
    )
    transfer_scene = _scene(transfer)
    explorer.observe(transfer, transfer_scene)
    expected_transfer = ActionToken(6, (("x", 22), ("y", 16)))
    explorer.global_attempts[expected_transfer] = 10

    transferred_choice = explorer.select(transfer, transfer_scene, (6,))

    assert transferred_choice.token == expected_transfer
    assert transferred_choice.reason.endswith("repair-local-relation")
    assert explorer.to_dict()["learned_local_relations"] == 2

    conservation_pixels = [[5 for _x in range(size)] for _y in range(size)]
    conservation_clue = (2, 2, 2, 2, 8, 2, 2, 2, 2)
    for origin_x, origin_y in origins[:3]:
        center_x = origin_x + step
        center_y = origin_y + step
        for dx, dy in directions:
            block_x = center_x + dx * step
            block_y = center_y + dy * step
            for y in range(block_y, block_y + block_size):
                for x in range(block_x, block_x + block_size):
                    conservation_pixels[y][x] = 8
        for clue_index, color in enumerate(conservation_clue):
            clue_x = center_x + clue_index % 3 * subcell
            clue_y = center_y + clue_index // 3 * subcell
            for y in range(clue_y, clue_y + subcell):
                for x in range(clue_x, clue_x + subcell):
                    conservation_pixels[y][x] = color
    conservation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=tuple(tuple(row) for row in conservation_pixels),
        levels_completed=2,
    )
    conservation_scene = _scene(conservation)

    conserved_candidates = explorer._local_relation_candidates(
        conservation,
        conservation_scene,
    )

    assert conserved_candidates
    assert explorer.learned_local_relation == {0: True, 2: False}

    portfolio = EpistemicExplorer(
        successful_role_replay=True,
        local_relation_solver=True,
        constraint_first_role_replay=True,
    )
    portfolio.learned_local_relation = dict(explorer.learned_local_relation)
    portfolio.observe(conservation, conservation_scene)
    repair = portfolio._local_relation_candidates(
        conservation,
        conservation_scene,
    )[0]
    represented = portfolio._tokens(conservation, conservation_scene, (6,))
    replay_token = next(
        token
        for token in represented
        if token.data != (("x", repair[0]), ("y", repair[1]))
    )
    portfolio.successful_program = (
        portfolio._role(replay_token, conservation_scene),
    )

    portfolio_choice = portfolio.select(
        conservation,
        conservation_scene,
        (6,),
    )

    assert portfolio_choice.token.data == (
        ("x", repair[0]),
        ("y", repair[1]),
    )
    assert portfolio_choice.reason.endswith(
        "constraint-first-repair-local-relation"
    )


def test_global_relation_solver_coordinates_overlapping_clue_constraints() -> None:
    width, height = 48, 32
    pixels = [[5 for _x in range(width)] for _y in range(height)]
    size = 6
    clue_origins = {(12, 12), (28, 12)}
    shared_origin = (20, 12)
    for origin_y in (4, 12, 20):
        for origin_x in (4, 12, 20, 28, 36):
            origin = (origin_x, origin_y)
            if origin in clue_origins:
                continue
            color = 9 if origin == shared_origin else 8
            for y in range(origin_y, origin_y + size):
                for x in range(origin_x, origin_x + size):
                    pixels[y][x] = color
    subcell = size // 3
    clue = (0, 0, 0, 0, 8, 0, 0, 0, 0)
    for origin_x, origin_y in clue_origins:
        for clue_index, color in enumerate(clue):
            start_x = origin_x + clue_index % 3 * subcell
            start_y = origin_y + clue_index // 3 * subcell
            for y in range(start_y, start_y + subcell):
                for x in range(start_x, start_x + subcell):
                    pixels[y][x] = color
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=tuple(tuple(row) for row in pixels),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(
        local_relation_solver=True,
        global_relation_constraint_solver=True,
    )
    explorer.learned_local_relation = {0: True}

    candidates = explorer._local_relation_candidates(observation, scene)

    assert candidates == ((22, 14),)


def test_policy_explorer_is_an_exact_configuration_ablation() -> None:
    from reflector.mind import MindConfig
    from reflector.policy import SymbolicPolicy

    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=((0, 0, 0), (0, 9, 0), (0, 0, 0)),
    )
    enabled = SymbolicPolicy(MindConfig(enable_epistemic_state_graph=True))
    ablated = SymbolicPolicy(MindConfig(enable_epistemic_state_graph=False))

    enabled_decision = enabled.choose_action(observation)
    ablated_decision = ablated.choose_action(observation)

    assert enabled_decision.reason.startswith("epistemic-frontier:")
    assert ablated_decision.reason.startswith("schema-selection:")
    assert enabled_decision.action_id == ablated_decision.action_id == 6


def test_committed_trajectory_bfs_detours_around_evidenced_block() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {
        1: (1, 0),
        2: (0, 1),
        3: (-1, 0),
        4: (0, -1),
    }
    explorer.trajectory_contextual_blocks[((0, 0), 1)] = 1

    action = explorer._trajectory_bfs_action(
        (0, 0),
        (2, 0),
        represented=frozenset({1, 2, 3, 4}),
        frame_width=4,
        frame_height=4,
    )

    assert action == 2


def test_committed_trajectory_bfs_is_action_id_equivariant() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {
        4: (1, 0),
        1: (0, 1),
        2: (-1, 0),
        3: (0, -1),
    }
    explorer.trajectory_contextual_blocks[((0, 0), 4)] = 1

    action = explorer._trajectory_bfs_action(
        (0, 0),
        (2, 0),
        represented=frozenset({1, 2, 3, 4}),
        frame_width=4,
        frame_height=4,
    )

    assert action == 1


def test_committed_trajectory_bfs_honors_first_step_independence() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {
        1: (1, 0),
        2: (0, 1),
        3: (-1, 0),
        4: (0, -1),
    }

    action = explorer._trajectory_bfs_action(
        (0, 0),
        (2, 2),
        represented=frozenset({1, 2, 3, 4}),
        frame_width=4,
        frame_height=4,
        forbidden_first=frozenset({1, 3}),
    )

    assert action == 2


def _topology_fixture() -> tuple[tuple[int, ...], ...]:
    frame = [[0 for _x in range(15)] for _y in range(15)]
    for y in range(2, 13):
        for x in range(2, 13):
            frame[y][x] = 5
    for y in range(6, 9):
        for x in range(6, 9):
            frame[y][x] = 0
    for y in range(3, 5):
        for x in range(3, 5):
            frame[y][x] = 9
    frame[4][4] = 5
    frame[4][7] = 8
    for y in range(9, 11):
        for x in range(9, 11):
            frame[y][x] = 9
    frame[10][10] = 5
    return tuple(tuple(row) for row in frame)


def _topology_explorer(
    *,
    origin: tuple[int, int] = (3, 3),
    target: tuple[int, int] = (9, 9),
) -> EpistemicExplorer:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_origin = origin
    explorer.trajectory_current_anchor = origin
    explorer.trajectory_target_anchor = target
    explorer.trajectory_mover_signature = (
        8,
        3,
        3,
        (
            (0, 0),
            (0, 1),
            (0, 2),
            (1, 0),
            (1, 2),
            (2, 0),
            (2, 1),
            (2, 2),
        ),
    )
    explorer.trajectory_mover_color = 9
    explorer.trajectory_target_color = 9
    explorer.trajectory_effects = {
        1: (3, 0),
        2: (0, 3),
        3: (-3, 0),
        4: (0, -3),
    }
    return explorer


def test_committed_trajectory_topology_excludes_holes_and_marks_overlay() -> None:
    explorer = _topology_explorer()

    nodes, uncertain, support_color = explorer._trajectory_topology(
        _topology_fixture()
    )

    assert support_color == 5
    assert (6, 6) not in nodes
    assert (6, 3) in nodes
    assert (6, 3) in uncertain
    assert {(3, 3), (9, 9)} <= nodes
    assert len(nodes) <= 128


def test_committed_trajectory_topology_reflects_with_frame() -> None:
    frame = _topology_fixture()
    width = len(frame[0])
    reflected = tuple(tuple(reversed(row)) for row in frame)
    explorer = _topology_explorer()
    nodes, uncertain, _support = explorer._trajectory_topology(frame)
    reflected_explorer = _topology_explorer(
        origin=(width - 3 - 3, 3),
        target=(width - 9 - 3, 9),
    )
    reflected_nodes, reflected_uncertain, _reflected_support = (
        reflected_explorer._trajectory_topology(reflected)
    )

    def reflect_anchor(anchor: tuple[int, int]) -> tuple[int, int]:
        return (width - anchor[0] - 3, anchor[1])

    assert reflected_nodes == frozenset(map(reflect_anchor, nodes))
    assert reflected_uncertain == frozenset(
        map(reflect_anchor, uncertain)
    )


def test_committed_trajectory_refreshes_disconnected_uncertain_gate() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {
        7: (0, 1),
        3: (0, -1),
        9: (1, 0),
    }
    explorer.trajectory_effect_evidence.update({7: 2, 3: 2, 9: 2})
    explorer.trajectory_contextual_blocks[((0, 1), 7)] = 1

    action = explorer._trajectory_gate_refresh_action(
        (0, 1),
        represented=frozenset({3, 7, 9}),
        allowed_nodes=frozenset({(0, 0), (0, 1), (0, 2)}),
        uncertain_nodes=frozenset({(0, 2)}),
    )

    assert action == 3


def test_committed_trajectory_does_not_refresh_without_gate_evidence() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {1: (0, -1), 2: (0, 1)}

    action = explorer._trajectory_gate_refresh_action(
        (0, 1),
        represented=frozenset({1, 2}),
        allowed_nodes=frozenset({(0, 0), (0, 1), (0, 2)}),
        uncertain_nodes=frozenset({(0, 2)}),
    )

    assert action is None


def test_committed_trajectory_refresh_varies_least_used_action_role() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {1: (0, 1), 4: (1, 0)}
    explorer.trajectory_effect_evidence.update({1: 2, 4: 2})
    explorer.trajectory_contextual_blocks[((2, 2), 9)] = 1
    explorer.trajectory_gate_refresh_actions[1] = 2

    action = explorer._trajectory_gate_refresh_action(
        (0, 0),
        represented=frozenset({1, 4}),
        allowed_nodes=frozenset({(0, 0), (0, 1), (1, 0)}),
        uncertain_nodes=frozenset({(2, 2)}),
    )

    assert action == 4

    explorer.trajectory_effects = {7: (0, 1), 2: (1, 0)}
    explorer.trajectory_effect_evidence = Counter({7: 2, 2: 2})
    explorer.trajectory_gate_refresh_actions = Counter({7: 2})
    action = explorer._trajectory_gate_refresh_action(
        (0, 0),
        represented=frozenset({2, 7}),
        allowed_nodes=frozenset({(0, 0), (0, 1), (1, 0)}),
        uncertain_nodes=frozenset({(2, 2)}),
    )

    assert action == 2


def test_committed_trajectory_retains_full_enacted_inverse_order() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    enacted = ((0, 1), (0, 0), (1, 0), (0, 0), (0, -1))

    for anchor in enacted:
        assert explorer._record_trajectory_enacted(anchor)

    assert tuple(explorer.trajectory_enacted_path) == enacted
    assert explorer.trajectory_enacted_path.count((0, 0)) == 2

    reflected = EpistemicExplorer(committed_trajectory_planning=True)
    for x, y in enacted:
        assert reflected._record_trajectory_enacted((-x, y))

    assert tuple(reflected.trajectory_enacted_path) == tuple(
        (-x, y) for x, y in enacted
    )


def test_committed_trajectory_enacted_path_is_bounded() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)

    for index in range(32):
        assert explorer._record_trajectory_enacted((index, 0))

    assert not explorer._record_trajectory_enacted((32, 0))
    assert explorer.trajectory_disabled
    assert explorer.trajectory_diagnostic == "enacted-trajectory-cap-reached"


def test_committed_trajectory_plan_cap_is_paid_by_bounded_enacted_path() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)

    assert explorer._trajectory_plan_cap() == 20

    explorer.trajectory_committed_macro = tuple((index, 0) for index in range(7))
    assert explorer._trajectory_plan_cap() == 27

    explorer.trajectory_committed_macro = tuple(
        (index, 0) for index in range(32)
    )
    assert explorer._trajectory_plan_cap() == 32


def test_committed_trajectory_gate_cooldown_requires_successful_ticks() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    first = ((0, 0), 1)
    repeated = ((2, 0), 4)
    explorer.trajectory_contextual_blocks.update({first: 1, repeated: 3})
    explorer.trajectory_gate_cooldowns.update({first: 1, repeated: 3})

    explorer._advance_trajectory_gate_cooldowns()

    assert first not in explorer.trajectory_contextual_blocks
    assert first not in explorer.trajectory_gate_cooldowns
    assert explorer.trajectory_contextual_blocks[repeated] == 3
    assert explorer.trajectory_gate_cooldowns[repeated] == 2

    explorer._advance_trajectory_gate_cooldowns()
    explorer._advance_trajectory_gate_cooldowns()

    assert repeated not in explorer.trajectory_contextual_blocks
    assert repeated not in explorer.trajectory_gate_cooldowns


def test_committed_trajectory_first_replay_axis_is_action_equivariant() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_origin = (4, 4)
    explorer.trajectory_committed_macro = ((4, 7), (4, 4), (7, 4))
    explorer.trajectory_effects = {
        1: (0, 3),
        2: (3, 0),
        3: (0, -3),
        4: (-3, 0),
    }

    assert explorer._trajectory_replay_parallel_actions() == frozenset(
        {1, 3}
    )

    explorer.trajectory_effects = {
        4: (0, 3),
        1: (3, 0),
        2: (0, -3),
        3: (-3, 0),
    }
    assert explorer._trajectory_replay_parallel_actions() == frozenset(
        {2, 4}
    )

    explorer.trajectory_replay_started = True
    assert explorer._trajectory_replay_parallel_actions() == frozenset()


def test_committed_trajectory_avoids_next_replay_anchor() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_origin = (0, 0)
    explorer.trajectory_committed_macro = (
        (0, 1),
        (0, 0),
        (1, 0),
    )
    explorer.trajectory_effects = {
        8: (-1, 0),
        2: (1, 0),
        6: (0, 1),
        4: (0, -1),
    }
    explorer.trajectory_replay_started = True
    explorer.trajectory_replay_cursor = 1

    assert explorer._trajectory_replay_forbidden_actions(
        (1, 0)
    ) == frozenset({8})

    explorer.trajectory_effects = {
        3: (-1, 0),
        7: (1, 0),
        1: (0, 1),
        5: (0, -1),
    }
    assert explorer._trajectory_replay_forbidden_actions(
        (1, 0)
    ) == frozenset({3})


def test_committed_trajectory_retry_retains_only_same_level_accommodation() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_stage = "navigate"
    explorer.trajectory_effects = {1: (1, 0), 2: (0, 1)}
    explorer.trajectory_effect_evidence.update({1: 2, 2: 2})
    explorer.trajectory_probes.update({1, 2})
    explorer.trajectory_contextual_blocks[((6, 6), 1)] = 1
    explorer.trajectory_committed_macro = ((0, 1), (0, 2))
    explorer.trajectory_previous_failed_macro_action = 2
    explorer.trajectory_replay_cursor = 1
    explorer.trajectory_plan_steps = 7

    explorer._reset_committed_trajectory_level(retain_accommodation=True)

    assert explorer.trajectory_stage == "not-attempted"
    assert explorer.trajectory_effects == {1: (1, 0), 2: (0, 1)}
    assert explorer.trajectory_effect_evidence == {1: 2, 2: 2}
    assert explorer.trajectory_probes == {1, 2}
    assert explorer.trajectory_contextual_blocks == {}
    assert explorer.trajectory_committed_macro == ()
    assert explorer.trajectory_previous_failed_macro_action == 2
    assert explorer.trajectory_replay_cursor == 0
    assert explorer.trajectory_plan_steps == 0

    explorer._reset_committed_trajectory_level()

    assert explorer.trajectory_effects == {}
    assert explorer.trajectory_effect_evidence == {}
    assert explorer.trajectory_probes == set()
    assert explorer.trajectory_contextual_blocks == {}
    assert explorer.trajectory_previous_failed_macro_action is None
