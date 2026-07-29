from reflector import MindConfig
from reflector.exploration import ActionToken, EpistemicExplorer
from reflector.perception import SceneTracker
from reflector.symbolic import Observation


def _paint(
    pixels: list[list[int]],
    *,
    left: int,
    top: int,
    color: int,
    size: int,
    outline: bool = False,
) -> None:
    for y in range(top, top + size):
        for x in range(left, left + size):
            if not outline or x in {left, left + size - 1} or y in {
                top,
                top + size - 1,
            }:
                pixels[y][x] = color


def _mapping_frame(
    *,
    reference_colors: tuple[int, ...] = (3, 5, 7),
    selector_colors: tuple[int, ...] = (7, 3, 5),
) -> tuple[tuple[int, ...], ...]:
    pixels = [[0 for _x in range(20)] for _y in range(20)]
    for index, color in enumerate(reference_colors):
        _paint(
            pixels,
            left=2 + index * 6,
            top=1,
            color=color,
            size=3,
            outline=True,
        )
        _paint(
            pixels,
            left=2 + index * 6,
            top=8,
            color=2,
            size=2,
        )
    for index, color in enumerate(selector_colors):
        _paint(
            pixels,
            left=2 + index * 6,
            top=16,
            color=color,
            size=2,
        )
    return tuple(tuple(row) for row in pixels)


def _observation(
    frame: tuple[tuple[int, ...], ...],
    *,
    levels_completed: int = 0,
) -> Observation:
    return Observation.create(
        state="NOT_FINISHED",
        available_actions=(5, 6, 7),
        frame=frame,
        levels_completed=levels_completed,
    )


def _multiline_mapping_frame() -> tuple[tuple[int, ...], ...]:
    reference = (3, 5, 7, 9, 11, 13, 15)
    selectors = (7, 15, 11, 3, 13, 9, 5)
    pixels = [[0 for _x in range(56)] for _y in range(23)]
    for index, color in enumerate(reference):
        _paint(
            pixels,
            left=2 + index * 7,
            top=1,
            color=color,
            size=3,
            outline=True,
        )
    targets = (
        (16, 7),
        (22, 7),
        (28, 7),
        (16, 12),
        (22, 12),
        (28, 12),
        (34, 12),
    )
    for left, top in targets:
        _paint(pixels, left=left, top=top, color=2, size=2)
    for index, color in enumerate(selectors):
        _paint(
            pixels,
            left=2 + index * 7,
            top=19,
            color=color,
            size=2,
        )
    return tuple(tuple(row) for row in pixels)


def test_parameterized_mapping_binds_attributes_then_applies_and_commits() -> None:
    observation = _observation(_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(parameterized_select_apply_commit=True)
    explorer.observe(observation, scene)

    choices = tuple(
        explorer.select(observation, scene, (5, 6, 7)).token for _step in range(7)
    )

    assert choices == (
        ActionToken(6, (("x", 8), ("y", 16))),
        ActionToken(6, (("x", 2), ("y", 8))),
        ActionToken(6, (("x", 14), ("y", 16))),
        ActionToken(6, (("x", 8), ("y", 8))),
        ActionToken(6, (("x", 2), ("y", 16))),
        ActionToken(6, (("x", 14), ("y", 8))),
        ActionToken(5),
    )
    assert explorer.select_apply_level_trials == 7


def test_multiline_targets_accommodate_the_same_attribute_binding() -> None:
    observation = _observation(_multiline_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
    )
    explorer.observe(observation, scene)

    choices = tuple(
        explorer.select(observation, scene, (5, 6, 7)).token for _step in range(15)
    )

    expected_targets = (
        (16, 7),
        (22, 7),
        (28, 7),
        (16, 12),
        (22, 12),
        (28, 12),
        (34, 12),
    )
    selector_x_by_color = {7: 2, 15: 9, 11: 16, 3: 23, 13: 30, 9: 37, 5: 44}
    expected = []
    for color, target in zip((3, 5, 7, 9, 11, 13, 15), expected_targets):
        expected.extend(
            (
                ActionToken(
                    6,
                    (("x", selector_x_by_color[color]), ("y", 19)),
                ),
                ActionToken(6, (("x", target[0]), ("y", target[1]))),
            )
        )
    expected.append(ActionToken(5))
    assert choices == tuple(expected)


def test_multiline_order_is_a_bounded_symbolic_variation() -> None:
    observation = _observation(_multiline_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        spatial_order_variation=True,
    )
    explorer.observe(observation, scene)

    choices = tuple(
        explorer.select(observation, scene, (5, 6, 7)).token for _step in range(63)
    )
    target_clicks = tuple(
        dict(token.data)
        for token in choices
        if token.action_id == 6 and dict(token.data).get("y") in {7, 12}
    )

    assert len(explorer._spatial_target_orderings(
        explorer._multiline_target_layouts(
            explorer._frame_objects(observation.frame),
            size=7,
            above=2,
            below=20,
        )[0]
    )) == 4
    assert tuple(token.action_id for token in choices).count(5) == 4
    assert tuple(token.action_id for token in choices).count(7) == 3
    assert target_clicks[:7] == (
        {"x": 16, "y": 7},
        {"x": 22, "y": 7},
        {"x": 28, "y": 7},
        {"x": 16, "y": 12},
        {"x": 22, "y": 12},
        {"x": 28, "y": 12},
        {"x": 34, "y": 12},
    )
    assert target_clicks[7:14] == (
        {"x": 16, "y": 7},
        {"x": 22, "y": 7},
        {"x": 28, "y": 7},
        {"x": 34, "y": 12},
        {"x": 28, "y": 12},
        {"x": 22, "y": 12},
        {"x": 16, "y": 12},
    )


def test_multiline_accommodation_is_silent_without_exact_cardinality() -> None:
    frame = [list(row) for row in _multiline_mapping_frame()]
    frame[12][34] = 0
    frame[12][35] = 0
    frame[13][34] = 0
    frame[13][35] = 0
    observation = _observation(tuple(tuple(row) for row in frame))
    scene, _events = SceneTracker().perceive(observation)
    enabled = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
    )
    parent = EpistemicExplorer(parameterized_select_apply_commit=True)
    enabled.observe(observation, scene)
    parent.observe(observation, scene)

    assert enabled.select(observation, scene, (5, 6, 7)) == parent.select(
        observation,
        scene,
        (5, 6, 7),
    )


def test_mapping_requires_an_exact_reference_selector_color_bijection() -> None:
    observation = _observation(
        _mapping_frame(selector_colors=(7, 3, 9)),
    )
    scene, _events = SceneTracker().perceive(observation)
    enabled = EpistemicExplorer(parameterized_select_apply_commit=True)
    default = EpistemicExplorer()
    enabled.observe(observation, scene)
    default.observe(observation, scene)

    assert enabled.select(observation, scene, (5, 6, 7)) == default.select(
        observation,
        scene,
        (5, 6, 7),
    )
    assert enabled.select_apply_program == ()


def test_select_apply_commit_is_exactly_off_by_default() -> None:
    observation = _observation(_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    default = EpistemicExplorer()
    explicit_off = EpistemicExplorer(parameterized_select_apply_commit=False)
    default.observe(observation, scene)
    explicit_off.observe(observation, scene)

    assert default.select(observation, scene, (5, 6, 7)) == explicit_off.select(
        observation,
        scene,
        (5, 6, 7),
    )
    assert default.to_dict() == explicit_off.to_dict()
    assert MindConfig() == MindConfig(enable_parameterized_select_apply_commit=False)
