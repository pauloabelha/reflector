from reflector import MindConfig
from reflector.exploration import (
    ActionToken,
    CyclicAlignmentScheme,
    EpistemicExplorer,
)
from reflector.perception import SceneTracker
from reflector.symbolic import Observation


def _perimeter(
    left: int,
    top: int,
    right: int,
    bottom: int,
    pitch: int = 3,
) -> tuple[tuple[int, int], ...]:
    return EpistemicExplorer._rectangular_perimeter(
        left,
        top,
        right,
        bottom,
        pitch,
    )


def _frame(
    paths: tuple[tuple[tuple[tuple[int, int], ...], tuple[int, ...]], ...],
    anchors: tuple[tuple[tuple[int, int], int], ...],
    *,
    width: int = 42,
    height: int = 38,
) -> tuple[tuple[int, ...], ...]:
    pixels = [[0 for _x in range(width)] for _y in range(height)]
    for points, colors in paths:
        for (x, y), color in zip(points, colors):
            for dy in range(2):
                for dx in range(2):
                    pixels[y + dy][x + dx] = color
    for (x, y), marker in anchors:
        for marker_x, marker_y in (
            (x - 1, y - 1),
            (x + 2, y - 1),
            (x - 1, y + 2),
            (x + 2, y + 2),
        ):
            pixels[marker_y][marker_x] = marker
    return tuple(tuple(row) for row in pixels)


def _observation(
    frame: tuple[tuple[int, ...], ...],
    *,
    levels_completed: int = 0,
) -> Observation:
    return Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=frame,
        levels_completed=levels_completed,
    )


def test_marker_relative_anchor_detection_is_translation_and_recolor_invariant() -> (
    None
):
    path = _perimeter(5, 5, 14, 11)
    colors = (2, 7, 3, 2, 3, 2, 3, 2, 3, 2)
    source = _frame(((path, colors),), (((5, 5), 7),))
    translated_path = tuple((x + 9, y + 6) for x, y in path)
    recolored = tuple({2: 4, 3: 6, 7: 12}[color] for color in colors)
    translated = _frame(
        ((translated_path, recolored),),
        (((14, 11), 12),),
    )

    source_anchor = EpistemicExplorer._marked_anchors(source)
    translated_anchor = EpistemicExplorer._marked_anchors(translated)

    assert len(source_anchor) == len(translated_anchor) == 1
    assert source_anchor[0].point == (5, 5)
    assert translated_anchor[0].point == (14, 11)
    assert source_anchor[0].marker_color != translated_anchor[0].marker_color
    assert source_anchor[0].token_shape == translated_anchor[0].token_shape


def test_cyclic_goal_is_constructed_only_from_predicted_progress() -> None:
    path = _perimeter(5, 5, 14, 11)
    initial = (2, 3, 7, 2, 3, 2, 3, 2, 3, 2)
    one_shift = EpistemicExplorer._rotate_values(initial, 1)
    initial_frame = _frame(((path, initial),), (((5, 5), 7),))
    one_shift_frame = _frame(((path, one_shift),), (((5, 5), 7),))
    unrelated = tuple(tuple(0 for _x in range(42)) for _y in range(38))
    action_point = (1, 5)
    explorer = EpistemicExplorer(cyclic_sequence_alignment=True)

    explorer._observe_cyclic_transition(
        initial_frame,
        one_shift_frame,
        action_point,
        progressed=False,
    )
    assert explorer.cyclic_transport_evidence[("left", 1)] == 1
    assert explorer.cyclic_alignment_scheme is None

    explorer._observe_cyclic_transition(
        one_shift_frame,
        unrelated,
        action_point,
        progressed=True,
    )

    scheme = explorer.cyclic_alignment_scheme
    assert scheme is not None
    assert scheme.target_relation == "anchor-token-matches-markers"
    assert scheme.shift_direction == 1
    assert scheme.evidence == (
        "level-progress",
        "predicted-cyclic-transport",
        "marker-relative-match",
    )
    assert "7" not in repr(scheme)


def test_overlapping_tracks_are_factored_and_planned_compositionally() -> None:
    outer = _perimeter(12, 5, 24, 32)
    upper = tuple((x, 14) for x in range(6, 34, 3))
    lower = tuple((x, 23) for x in range(6, 34, 3))
    values = {point: 2 + index % 4 for index, point in enumerate(outer)}
    values.update({point: 2 + index % 4 for index, point in enumerate(upper)})
    values.update({point: 2 + index % 4 for index, point in enumerate(lower)})
    values[outer[3]] = 7
    values[lower[3]] = 7
    paths = (
        (outer, tuple(values[point] for point in outer)),
        (upper, tuple(values[point] for point in upper)),
        (lower, tuple(values[point] for point in lower)),
    )
    frame = _frame(
        paths,
        (
            ((24, 14), 7),
            ((24, 23), 7),
        ),
    )
    pixels = [list(row) for row in frame]
    controls = (
        (9, 5, 8),
        (27, 5, 14),
        (3, 14, 8),
        (36, 14, 14),
        (3, 23, 8),
        (36, 23, 14),
    )
    for x, y, color in controls:
        pixels[y][x] = color
        pixels[y + 1][x] = color
    frame = tuple(tuple(row) for row in pixels)
    observation = _observation(frame, levels_completed=1)
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(cyclic_sequence_alignment=True)
    explorer.cyclic_alignment_scheme = CyclicAlignmentScheme(
        scheme_id="cyclic-alignment-test",
        target_relation="anchor-token-matches-markers",
        controller_side="left",
        shift_direction=1,
        evidence=("synthetic-progress",),
    )
    explorer.observe(observation, scene)

    tracks = explorer._cyclic_tracks(frame)
    choice = explorer.select(observation, scene, (6,))

    assert [len(track.points) for track in tracks] == [26, 10, 10]
    assert choice.reason.endswith("cyclic-sequence-alignment")
    assert choice.token.action_id == 6
    assert explorer.cyclic_last_plan_length > 0
    assert explorer.cyclic_last_plan_length <= 12
    assert "scheme:cyclic-alignment-test" in explorer.last_scheme_components


def test_disabled_cyclic_alignment_is_an_exact_policy_ablation() -> None:
    frame = _frame(
        ((_perimeter(5, 5, 14, 11), (2, 7, 3, 2, 3, 2, 3, 2, 3, 2)),),
        (((5, 5), 7),),
    )
    observation = _observation(frame)
    scene, _events = SceneTracker().perceive(observation)
    default = EpistemicExplorer()
    explicit_off = EpistemicExplorer(cyclic_sequence_alignment=False)
    default.observe(observation, scene)
    explicit_off.observe(observation, scene)

    assert default.select(observation, scene, (6,)) == explicit_off.select(
        observation,
        scene,
        (6,),
    )
    assert default.to_dict() == explicit_off.to_dict()
    assert MindConfig() == MindConfig(enable_cyclic_sequence_alignment=False)


def test_cyclic_advisor_releases_control_at_its_level_trial_bound() -> None:
    frame = _frame(
        ((_perimeter(5, 5, 14, 11), (2, 7, 3, 2, 3, 2, 3, 2, 3, 2)),),
        (((5, 5), 7),),
    )
    observation = _observation(frame)
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(cyclic_sequence_alignment=True)
    explorer.cyclic_alignment_scheme = CyclicAlignmentScheme(
        scheme_id="cyclic-alignment-test",
        target_relation="anchor-token-matches-markers",
        controller_side="left",
        shift_direction=1,
        evidence=("synthetic-progress",),
    )
    explorer.cyclic_alignment_level_trials = (
        explorer.max_cyclic_alignment_trials_per_level
    )
    tokens = explorer._tokens(observation, scene, (6,))

    assert (
        explorer._select_cyclic_alignment(
            observation,
            scene,
            explorer._state_key(observation, scene),
            tokens,
        )
        is None
    )
    assert ActionToken(6) not in tokens


def test_graph_cycle_transport_is_grounded_only_by_an_exact_frame_shift() -> None:
    left_cycle = (
        (21, 19),
        (24, 19),
        (27, 19),
        (30, 22),
        (33, 25),
        (33, 28),
        (33, 31),
        (30, 34),
        (27, 37),
        (24, 37),
        (21, 37),
        (18, 34),
        (15, 31),
        (15, 28),
        (15, 25),
        (18, 22),
    )
    right_cycle = (
        (33, 19),
        (36, 19),
        (39, 19),
        (42, 22),
        (45, 25),
        (45, 28),
        (45, 31),
        (42, 34),
        (39, 37),
        (36, 37),
        (33, 37),
        (30, 34),
        (27, 31),
        (27, 28),
        (27, 25),
        (30, 22),
    )
    positions = tuple(sorted(set(left_cycle) | set(right_cycle)))
    values = {point: index + 20 for index, point in enumerate(positions)}
    before = _frame(
        ((positions, tuple(values[point] for point in positions)),),
        (
            ((15, 28), 90),
            ((45, 28), 91),
        ),
        width=64,
        height=64,
    )
    shifted = dict(values)
    rotated = EpistemicExplorer._rotate_values(
        tuple(values[point] for point in left_cycle),
        1,
    )
    shifted.update(zip(left_cycle, rotated))
    after = _frame(
        ((positions, tuple(shifted[point] for point in positions)),),
        (
            ((15, 28), 90),
            ((45, 28), 91),
        ),
        width=64,
        height=64,
    )
    explorer = EpistemicExplorer(
        cyclic_sequence_alignment=True,
        graph_cycle_transport=True,
    )

    assert explorer._cyclic_tracks(before) == ()
    graph_tracks = explorer._cyclic_tracks(
        before,
        include_graph_cycles=True,
    )
    explorer._observe_cyclic_transition(
        before,
        after,
        (25, 41),
        progressed=False,
    )

    assert any(len(track.points) == 16 for track in graph_tracks)
    assert len(explorer.grounded_cyclic_transports) == 1
    (grounded_points, controller), direction = next(
        iter(explorer.grounded_cyclic_transports.items())
    )
    assert set(grounded_points) == set(left_cycle)
    assert controller == (25, 41)
    assert direction in {-1, 1}


def test_graph_cycle_transport_requires_an_earned_alignment_goal() -> None:
    try:
        MindConfig(enable_graph_cycle_transport=True)
    except ValueError as error:
        assert str(error) == (
            "graph cycle transport requires cyclic sequence alignment"
        )
    else:
        raise AssertionError("graph cycle transport must require alignment")
