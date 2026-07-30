from __future__ import annotations

import io
import zipfile

import pytest

from reflector.core.exploration import (
    ActionRole,
    ActionToken,
    CyclicAlignmentScheme,
    EpistemicExplorer,
    GroundedRole,
)
from reflector.core.mind import MindConfig
from reflector.core.perception import SceneTracker
from reflector.core.permutation_transport import (
    PermutationBounds,
    PermutationGenerator,
    PermutationSystem,
    infer_path_cycle_permutations,
)
from reflector.core.symbolic import Observation
from reflector.kaggle import build_overlay
from reflector.runtime.policy import SymbolicPolicy

Point = tuple[int, int]
Frame = tuple[tuple[int, ...], ...]

HORIZONTAL_SEGMENTS = (
    ((6, 9), (9, 9), (12, 9)),
    ((24, 9), (27, 9), (30, 9)),
    ((6, 27), (9, 27), (12, 27)),
    ((24, 27), (27, 27), (30, 27)),
)
VERTICAL_SEGMENTS = (
    ((9, 6), (9, 9), (9, 12)),
    ((27, 6), (27, 9), (27, 12)),
    ((9, 24), (9, 27), (9, 30)),
    ((27, 24), (27, 27), (27, 30)),
)
HORIZONTAL_TRACK = tuple(point for segment in HORIZONTAL_SEGMENTS for point in segment)
VERTICAL_TRACK = tuple(point for segment in VERTICAL_SEGMENTS for point in segment)
TOKEN_POSITIONS = tuple(sorted(set(HORIZONTAL_TRACK) | set(VERTICAL_TRACK)))
TARGETS = ((HORIZONTAL_TRACK[-1], 70), (VERTICAL_TRACK[-1], 71))
HORIZONTAL_CONTROLLERS = ((2, 8), (2, 26))
VERTICAL_CONTROLLERS = ((38, 2), (38, 20))
HORIZONTAL_CONTROLLER_SHAPE = ((0, 0), (0, 1), (0, 2), (1, 1))
VERTICAL_CONTROLLER_SHAPE = ((0, 0), (1, 0), (1, 1), (2, 0))
PATH_TRACK = (
    (6, 9),
    (9, 9),
    (12, 9),
    (15, 9),
    (15, 12),
    (15, 15),
    (12, 15),
    (9, 15),
    (9, 18),
)
PATH_POSITIONS = tuple(sorted(PATH_TRACK))
PATH_TARGET = (PATH_TRACK[-1], 70)
PATH_CONTROLLER_ORIGIN = (2, 8)


def _generator(
    track: tuple[Point, ...],
    *,
    axis: str,
) -> PermutationGenerator:
    slots = tuple(sorted(track))
    indexes = {point: index for index, point in enumerate(slots)}
    destinations = {
        point: track[(index + 1) % len(track)] for index, point in enumerate(track)
    }
    return PermutationGenerator.create(
        slots=slots,
        successor=tuple(indexes[destinations[point]] for point in slots),
        controller=(0, 0),
        axis=axis,  # type: ignore[arg-type]
        pitch=3,
        segment_count=4,
    )


HORIZONTAL = _generator(HORIZONTAL_TRACK, axis="horizontal")
VERTICAL = _generator(VERTICAL_TRACK, axis="vertical")


def _goal_values() -> dict[Point, int]:
    values = {point: 20 + index for index, point in enumerate(TOKEN_POSITIONS)}
    for point, marker_color in TARGETS:
        values[point] = marker_color
    return values


def _apply(
    values: dict[Point, int],
    generator: PermutationGenerator,
) -> dict[Point, int]:
    output = dict(values)
    for source in generator.slots:
        output[generator.destination(source)] = values[source]
    return output


def _paint_shape(
    pixels: list[list[int]],
    origin: Point,
    shape: tuple[Point, ...],
    color: int,
) -> None:
    for local_x, local_y in shape:
        pixels[origin[1] + local_y][origin[0] + local_x] = color


def _frame(values: dict[Point, int], *, ui_counter: int) -> Frame:
    pixels = [[0 for _x in range(48)] for _y in range(42)]
    for (x, y), color in values.items():
        _paint_shape(
            pixels,
            (x, y),
            ((0, 0), (0, 1), (1, 0), (1, 1)),
            color,
        )
    for (x, y), marker_color in TARGETS:
        for marker_x, marker_y in (
            (x - 1, y - 1),
            (x + 2, y - 1),
            (x - 1, y + 2),
            (x + 2, y + 2),
        ):
            pixels[marker_y][marker_x] = marker_color
    for origin in HORIZONTAL_CONTROLLERS:
        _paint_shape(
            pixels,
            origin,
            HORIZONTAL_CONTROLLER_SHAPE,
            90,
        )
    for origin in VERTICAL_CONTROLLERS:
        _paint_shape(
            pixels,
            origin,
            VERTICAL_CONTROLLER_SHAPE,
            91,
        )
    pixels[0][0] = 100 + ui_counter
    return tuple(tuple(row) for row in pixels)


def _path_frame(values: dict[Point, int], *, ui_counter: int) -> Frame:
    pixels = [[0 for _x in range(27)] for _y in range(24)]
    for (x, y), color in values.items():
        _paint_shape(
            pixels,
            (x, y),
            ((0, 0), (0, 1), (1, 0), (1, 1)),
            color,
        )
    (target_x, target_y), marker_color = PATH_TARGET
    for marker_x, marker_y in (
        (target_x - 1, target_y - 1),
        (target_x + 2, target_y - 1),
        (target_x - 1, target_y + 2),
        (target_x + 2, target_y + 2),
    ):
        pixels[marker_y][marker_x] = marker_color
    _paint_shape(
        pixels,
        PATH_CONTROLLER_ORIGIN,
        HORIZONTAL_CONTROLLER_SHAPE,
        90,
    )
    pixels[0][0] = 100 + ui_counter
    return tuple(tuple(row) for row in pixels)


def _observation(
    frame: Frame,
    *,
    levels_completed: int = 0,
    state: str = "NOT_FINISHED",
) -> Observation:
    return Observation.create(
        state=state,
        available_actions=(6,),
        frame=frame,
        levels_completed=levels_completed,
    )


def _explorer(
    *,
    bounds: PermutationBounds = PermutationBounds(),
    path_cycle: bool = False,
) -> EpistemicExplorer:
    explorer = EpistemicExplorer(
        cyclic_sequence_alignment=True,
        segmented_permutation_transport=True,
        path_cycle_transport=path_cycle,
        segmented_permutation_bounds=bounds,
    )
    explorer.cyclic_alignment_scheme = CyclicAlignmentScheme(
        scheme_id="synthetic-marker-goal",
        target_relation="anchor-token-matches-markers",
        controller_side="left",
        shift_direction=1,
        evidence=("synthetic-progress",),
    )
    return explorer


def _path_observations() -> tuple[Observation, Observation, Observation]:
    goal_values = {point: 20 + index for index, point in enumerate(PATH_POSITIONS)}
    goal_values[PATH_TARGET[0]] = PATH_TARGET[1]
    generator = _generator(PATH_TRACK, axis="path")
    values0 = _apply(goal_values, generator)
    values1 = _apply(values0, generator)
    values2 = _apply(values1, generator)
    return tuple(
        _observation(_path_frame(values, ui_counter=index))
        for index, values in enumerate((values0, values1, values2))
    )


def _controller_click(origin: Point, *, horizontal: bool) -> Point:
    shape = HORIZONTAL_CONTROLLER_SHAPE if horizontal else VERTICAL_CONTROLLER_SHAPE
    points = tuple((origin[0] + x, origin[1] + y) for x, y in shape)
    return (
        sum(point[0] for point in points) // len(points),
        sum(point[1] for point in points) // len(points),
    )


def _issue_and_observe(
    explorer: EpistemicExplorer,
    before: Observation,
    after: Observation,
    click: Point,
) -> None:
    before_scene, _events = SceneTracker().perceive(before)
    if explorer.current_level is None:
        explorer.observe(before, before_scene)
    assert explorer.current_state is not None
    explorer.selection_frame = before.frame
    explorer._issue(
        explorer.current_state,
        ActionToken(6, (("x", click[0]), ("y", click[1]))),
        "synthetic-controller-probe",
        before_scene,
    )
    after_scene, _events = SceneTracker().perceive(after)
    explorer.observe(after, after_scene)


def _learn_shared_system() -> tuple[EpistemicExplorer, Observation]:
    explorer = _explorer()
    values0 = _apply(_apply(_goal_values(), HORIZONTAL), VERTICAL)
    values1 = _apply(values0, HORIZONTAL)
    values2 = _apply(values1, HORIZONTAL)
    values3 = _apply(values2, VERTICAL)
    values4 = _apply(values3, VERTICAL)
    observations = tuple(
        _observation(_frame(values, ui_counter=index))
        for index, values in enumerate((values0, values1, values2, values3, values4))
    )
    _issue_and_observe(
        explorer,
        observations[0],
        observations[1],
        _controller_click(HORIZONTAL_CONTROLLERS[0], horizontal=True),
    )
    _issue_and_observe(
        explorer,
        observations[1],
        observations[2],
        _controller_click(HORIZONTAL_CONTROLLERS[1], horizontal=True),
    )
    _issue_and_observe(
        explorer,
        observations[2],
        observations[3],
        _controller_click(VERTICAL_CONTROLLERS[0], horizontal=False),
    )
    _issue_and_observe(
        explorer,
        observations[3],
        observations[4],
        _controller_click(VERTICAL_CONTROLLERS[1], horizontal=False),
    )
    return explorer, observations[4]


def test_provisional_observation_cannot_plan_and_translated_repeat_confirms() -> None:
    explorer = _explorer()
    values0 = _apply(_goal_values(), HORIZONTAL)
    values1 = _apply(values0, HORIZONTAL)
    values2 = _apply(values1, HORIZONTAL)
    observations = tuple(
        _observation(_frame(values, ui_counter=index))
        for index, values in enumerate((values0, values1, values2))
    )
    _issue_and_observe(
        explorer,
        observations[0],
        observations[1],
        _controller_click(HORIZONTAL_CONTROLLERS[0], horizontal=True),
    )
    scene1, _events = SceneTracker().perceive(observations[1])
    tokens1 = explorer._tokens(observations[1], scene1, (6,))
    state1 = explorer.current_state
    assert state1 is not None

    assert len(explorer.segmented_permutation_proposals) == 1
    assert explorer.segmented_permutation_generators == ()
    assert explorer.segmented_permutation_predictions == 0
    assert (
        explorer._select_segmented_permutation_transport(
            observations[1],
            scene1,
            state1,
            tokens1,
        )
        is None
    )

    _issue_and_observe(
        explorer,
        observations[1],
        observations[2],
        _controller_click(HORIZONTAL_CONTROLLERS[1], horizontal=True),
    )

    assert explorer.segmented_permutation_proposals == {}
    assert explorer.segmented_permutation_predictions == 1
    assert explorer.segmented_permutation_confirmations == 1
    assert len(explorer.segmented_permutation_generators) == 1
    assert explorer.segmented_permutation_generators[0].support == 2
    assert len(explorer.segmented_permutation_generators[0].controllers) == 2


def test_confirmed_shared_domains_plan_one_represented_controller() -> None:
    explorer, observation = _learn_shared_system()
    scene, _events = SceneTracker().perceive(observation)
    tokens = explorer._tokens(observation, scene, (6,))
    system = PermutationSystem.create(explorer.segmented_permutation_generators)
    state = explorer.current_state
    assert state is not None

    selected = explorer._select_segmented_permutation_transport(
        observation,
        scene,
        state,
        tokens,
    )

    assert len(system.generators) == 2
    assert len(system.shared_slots) == 4
    assert selected is not None
    assert selected in tokens
    assert explorer.segmented_permutation_last_plan_length > 0
    assert explorer.segmented_permutation_search_states > 0
    assert explorer.segmented_permutation_diagnostic == ("planned-confirmed-generator")


def test_prospective_conflict_quarantines_controller_form() -> None:
    explorer = _explorer()
    values0 = _apply(_goal_values(), HORIZONTAL)
    values1 = _apply(values0, HORIZONTAL)
    before = _observation(_frame(values0, ui_counter=0))
    proposed = _observation(_frame(values1, ui_counter=1))
    conflict = _observation(_frame(values1, ui_counter=2))
    _issue_and_observe(
        explorer,
        before,
        proposed,
        _controller_click(HORIZONTAL_CONTROLLERS[0], horizontal=True),
    )
    controller_form = next(iter(explorer.segmented_permutation_proposals))

    _issue_and_observe(
        explorer,
        proposed,
        conflict,
        _controller_click(HORIZONTAL_CONTROLLERS[1], horizontal=True),
    )

    assert controller_form in explorer.segmented_permutation_quarantined_forms
    assert explorer.segmented_permutation_proposals == {}
    assert explorer.segmented_permutation_controller_effects == {}
    assert explorer.segmented_permutation_conflicts == 1
    assert explorer.segmented_permutation_diagnostic == (
        "prospective-prediction-conflict"
    )


def test_ambiguous_repeated_colors_do_not_create_a_proposal() -> None:
    values = {point: 40 + index for index, point in enumerate(TOKEN_POSITIONS)}
    for segment in HORIZONTAL_SEGMENTS:
        for index, point in enumerate(segment):
            values[point] = 2 + index
    before = _observation(_frame(values, ui_counter=0))
    after = _observation(_frame(_apply(values, HORIZONTAL), ui_counter=1))
    explorer = _explorer()

    _issue_and_observe(
        explorer,
        before,
        after,
        _controller_click(HORIZONTAL_CONTROLLERS[0], horizontal=True),
    )

    assert explorer.segmented_permutation_proposals == {}
    assert explorer.segmented_permutation_generators == ()
    assert explorer.segmented_permutation_diagnostic == "ambiguous-transition"


def test_controller_form_excludes_coordinates_colors_and_action_ids() -> None:
    shape = ((0, 0), (0, 1), (1, 0))
    first = GroundedRole(
        ActionRole(6, color=90, area=3, shape=shape),
        centroid=(3, 8),
    )
    transformed = GroundedRole(
        ActionRole(19, color=12, area=3, shape=shape),
        centroid=(31, 24),
    )

    first_form = EpistemicExplorer._segmented_controller_form(first)
    transformed_form = EpistemicExplorer._segmented_controller_form(transformed)

    assert first_form == transformed_form
    assert first_form is not None
    assert len(first_form) == 4


def test_path_cycle_inference_finds_nested_subpath_and_full_path() -> None:
    path = (
        (6, 6),
        (9, 6),
        (12, 6),
        (15, 6),
        (15, 9),
        (15, 12),
        (12, 12),
        (9, 12),
        (9, 15),
    )
    values = {point: 20 + index for index, point in enumerate(path)}

    def render(current: dict[Point, int]) -> Frame:
        pixels = [[0 for _x in range(24)] for _y in range(21)]
        for (x, y), color in current.items():
            pixels[y][x] = color
        return tuple(tuple(row) for row in pixels)

    def rotate(
        current: dict[Point, int],
        track: tuple[Point, ...],
    ) -> dict[Point, int]:
        updated = dict(current)
        for index, source in enumerate(track):
            updated[track[(index + 1) % len(track)]] = current[source]
        return updated

    subpath = path[:4]
    subpath_candidates = infer_path_cycle_permutations(
        render(values),
        render(rotate(values, subpath)),
        tuple(sorted(path)),
        (2, 6),
    )
    full_path_candidates = infer_path_cycle_permutations(
        render(values),
        render(rotate(values, path)),
        tuple(sorted(path)),
        (2, 12),
    )

    assert len(subpath_candidates) == 1
    assert set(subpath_candidates[0].slots) == set(subpath)
    assert subpath_candidates[0].axis == "path"
    assert len(full_path_candidates) == 1
    assert set(full_path_candidates[0].slots) == set(path)


def test_controller_form_distinguishes_corner_and_straight_path_contexts() -> None:
    positions = ((6, 6), (9, 6), (9, 9), (9, 12))
    shape = ((0, 0), (0, 1), (1, 0))
    corner = GroundedRole(
        ActionRole(6, color=90, area=3, shape=shape),
        centroid=(4, 6),
    )
    straight = GroundedRole(
        ActionRole(6, color=90, area=3, shape=shape),
        centroid=(7, 9),
    )

    corner_form = EpistemicExplorer._segmented_controller_form(corner, positions)
    straight_form = EpistemicExplorer._segmented_controller_form(
        straight,
        positions,
    )

    assert corner_form is not None
    assert straight_form is not None
    assert corner_form[:-1] == straight_form[:-1]
    assert corner_form[-1] != straight_form[-1]


def test_path_context_is_translation_and_d4_invariant() -> None:
    positions = ((6, 6), (9, 6), (9, 9), (9, 12))
    centroid = (7, 9)

    def transform(point: Point) -> Point:
        x, y = point
        return 30 - y, x + 11

    transformed_positions = tuple(transform(point) for point in positions)
    transformed_centroid = transform(centroid)
    assert EpistemicExplorer._controller_topology_context(
        centroid,
        positions,
    ) == EpistemicExplorer._controller_topology_context(
        transformed_centroid,
        transformed_positions,
    )
    assert EpistemicExplorer._segmented_controller_form(
        GroundedRole(
            ActionRole(6, color=90, area=1, shape=((0, 0),)),
            centroid=centroid,
        ),
        positions,
    ) == EpistemicExplorer._segmented_controller_form(
        GroundedRole(
            ActionRole(19, color=12, area=1, shape=((0, 0),)),
            centroid=transformed_centroid,
        ),
        transformed_positions,
    )


def test_path_effect_is_confirmed_later_before_it_can_plan() -> None:
    before, proposed, confirmed = _path_observations()
    explorer = _explorer(path_cycle=True)
    click = _controller_click(PATH_CONTROLLER_ORIGIN, horizontal=True)

    _issue_and_observe(explorer, before, proposed, click)

    assert len(explorer.segmented_permutation_proposals) == 1
    assert explorer.segmented_permutation_generators == ()
    assert explorer.segmented_permutation_last_segmented_candidates == 0
    assert explorer.segmented_permutation_last_path_candidates == 1
    assert explorer.segmented_permutation_diagnostic == "provisional-observation"
    proposed_scene, _events = SceneTracker().perceive(proposed)
    proposed_tokens = explorer._tokens(proposed, proposed_scene, (6,))
    state = explorer.current_state
    assert state is not None
    assert (
        explorer._select_segmented_permutation_transport(
            proposed,
            proposed_scene,
            state,
            proposed_tokens,
        )
        is None
    )

    _issue_and_observe(explorer, proposed, confirmed, click)

    assert explorer.segmented_permutation_predictions == 1
    assert explorer.segmented_permutation_confirmations == 1
    assert len(explorer.segmented_permutation_generators) == 1
    generator = explorer.segmented_permutation_generators[0]
    assert generator.axis == "path"
    assert generator.support == 2
    assert len(generator.controllers) == 1
    confirmed_scene, _events = SceneTracker().perceive(confirmed)
    confirmed_tokens = explorer._tokens(confirmed, confirmed_scene, (6,))
    state = explorer.current_state
    assert state is not None
    selected = explorer._select_segmented_permutation_transport(
        confirmed,
        confirmed_scene,
        state,
        confirmed_tokens,
    )
    assert selected is not None
    assert explorer.segmented_permutation_last_plan_length > 0
    assert explorer.segmented_permutation_search_states > 0
    assert explorer.segmented_permutation_diagnostic == (
        "planned-confirmed-generator"
    )


def test_path_effect_conflict_quarantines_the_same_controller_form() -> None:
    before, proposed, _confirmed = _path_observations()
    explorer = _explorer(path_cycle=True)
    click = _controller_click(PATH_CONTROLLER_ORIGIN, horizontal=True)
    _issue_and_observe(explorer, before, proposed, click)
    controller_form = next(iter(explorer.segmented_permutation_proposals))
    goal_values = {point: 20 + index for index, point in enumerate(PATH_POSITIONS)}
    goal_values[PATH_TARGET[0]] = PATH_TARGET[1]
    reverse = _generator(tuple(reversed(PATH_TRACK)), axis="path")
    conflicting = _observation(
        _path_frame(_apply(goal_values, reverse), ui_counter=2)
    )

    _issue_and_observe(explorer, proposed, conflicting, click)

    assert controller_form in explorer.segmented_permutation_quarantined_forms
    assert explorer.segmented_permutation_proposals == {}
    assert explorer.segmented_permutation_generators == ()
    assert explorer.segmented_permutation_conflicts == 1
    assert explorer.segmented_permutation_diagnostic == (
        "prospective-prediction-conflict"
    )


def test_path_prediction_quarantines_when_the_token_domain_drifts() -> None:
    before, proposed, _confirmed = _path_observations()
    explorer = _explorer(path_cycle=True)
    click = _controller_click(PATH_CONTROLLER_ORIGIN, horizontal=True)
    _issue_and_observe(explorer, before, proposed, click)
    controller_form = next(iter(explorer.segmented_permutation_proposals))
    goal_values = {point: 20 + index for index, point in enumerate(PATH_POSITIONS)}
    goal_values[PATH_TARGET[0]] = PATH_TARGET[1]
    generator = _generator(PATH_TRACK, axis="path")
    drifted_values = _apply(_apply(goal_values, generator), generator)
    drifted_values.pop(PATH_TRACK[0])
    drifted = _observation(_path_frame(drifted_values, ui_counter=2))

    _issue_and_observe(explorer, proposed, drifted, click)

    assert controller_form in explorer.segmented_permutation_quarantined_forms
    assert explorer.segmented_permutation_proposals == {}
    assert explorer.segmented_permutation_generators == ()
    assert explorer.segmented_permutation_conflicts == 1
    assert explorer.segmented_permutation_diagnostic == (
        "prediction-domain-mismatch"
    )


def test_ambiguous_path_transition_remains_provisionally_unusable() -> None:
    before_values = dict(
        zip(
            PATH_TRACK,
            (1, 1, 1, 1, 1, 1, 1, 2, 1),
            strict=True,
        )
    )
    generator = _generator(PATH_TRACK, axis="path")
    before = _observation(_path_frame(before_values, ui_counter=0))
    after = _observation(
        _path_frame(_apply(before_values, generator), ui_counter=1)
    )
    explorer = _explorer(path_cycle=True)
    click = _controller_click(PATH_CONTROLLER_ORIGIN, horizontal=True)

    _issue_and_observe(explorer, before, after, click)

    assert explorer.segmented_permutation_last_segmented_candidates == 0
    assert explorer.segmented_permutation_last_path_candidates == 7
    assert explorer.segmented_permutation_proposals == {}
    assert explorer.segmented_permutation_generators == ()
    assert explorer.segmented_permutation_diagnostic == "ambiguous-transition"


def test_path_transport_is_exact_off_without_its_flag() -> None:
    before, proposed, _confirmed = _path_observations()
    explorer = _explorer(path_cycle=False)
    click = _controller_click(PATH_CONTROLLER_ORIGIN, horizontal=True)

    _issue_and_observe(explorer, before, proposed, click)

    assert explorer.segmented_permutation_proposals == {}
    assert explorer.segmented_permutation_generators == ()
    assert explorer.segmented_permutation_last_path_candidates == 0
    assert explorer.segmented_permutation_last_controller_context == ()
    assert explorer.segmented_permutation_diagnostic == (
        "no-exact-segmented-permutation"
    )


def test_bounds_reset_flag_off_and_submission_overlay() -> None:
    values = _apply(_goal_values(), HORIZONTAL)
    before = _observation(_frame(values, ui_counter=0))
    after = _observation(_frame(_apply(values, HORIZONTAL), ui_counter=1))
    bounded = _explorer(bounds=PermutationBounds(max_slots=8))
    _issue_and_observe(
        bounded,
        before,
        after,
        _controller_click(HORIZONTAL_CONTROLLERS[0], horizontal=True),
    )
    assert bounded.segmented_permutation_proposals == {}
    assert bounded.segmented_permutation_diagnostic == "domain-unrepresented"

    explorer, current = _learn_shared_system()
    earned_goal = explorer.cyclic_alignment_scheme
    progressed = _observation(
        current.frame,
        levels_completed=1,
    )
    progressed_scene, _events = SceneTracker().perceive(progressed)
    explorer.observe(progressed, progressed_scene)
    assert explorer.segmented_permutation_generators == ()
    assert explorer.segmented_permutation_controller_effects == {}
    assert explorer.cyclic_alignment_scheme is earned_goal

    default = EpistemicExplorer()
    explicit_off = EpistemicExplorer(segmented_permutation_transport=False)
    scene, _events = SceneTracker().perceive(before)
    default.observe(before, scene)
    explicit_off.observe(before, scene)
    assert default.select(before, scene, (6,)) == explicit_off.select(
        before,
        scene,
        (6,),
    )
    assert default.to_dict() == explicit_off.to_dict()

    with pytest.raises(
        ValueError,
        match="requires cyclic sequence alignment",
    ):
        MindConfig(enable_segmented_permutation_transport=True)
    config = MindConfig(
        enable_cyclic_sequence_alignment=True,
        enable_segmented_permutation_transport=True,
        enable_path_cycle_transport=True,
    )
    assert SymbolicPolicy(config).explorer.segmented_permutation_transport
    assert SymbolicPolicy(config).explorer.path_cycle_transport
    with pytest.raises(
        ValueError,
        match="path cycle transport requires segmented permutation transport",
    ):
        MindConfig(enable_path_cycle_transport=True)

    with zipfile.ZipFile(io.BytesIO(build_overlay())) as archive:
        assert "reflector/core/permutation_transport.py" in archive.namelist()
