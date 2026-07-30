import pytest

from reflector import MindConfig, SymbolicPolicy
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


def _nested_mapping_frame(
    *,
    connector_color: int = 14,
) -> tuple[tuple[int, ...], ...]:
    reference = (3, 5, 7, 9, 11, 13, 15)
    selectors = (7, 15, 11, 3, 13, 9, 5)
    pixels = [[0 for _x in range(56)] for _y in range(30)]
    for index, color in enumerate(reference):
        _paint(
            pixels,
            left=2 + index * 7,
            top=1,
            color=color,
            size=3,
            outline=True,
        )
    for color, top in ((8, 6), (14, 13)):
        for x in range(13, 38):
            pixels[top][x] = color
            pixels[top + 6][x] = color
        for y in range(top, top + 7):
            pixels[y][13] = color
            pixels[y][37] = color
    for left, top in (
        (16, 8),
        (22, 8),
        (34, 8),
        (16, 15),
        (22, 15),
        (28, 15),
        (34, 15),
    ):
        _paint(pixels, left=left, top=top, color=2, size=2)
    _paint(pixels, left=28, top=8, color=connector_color, size=2)
    for index, color in enumerate(selectors):
        _paint(
            pixels,
            left=2 + index * 7,
            top=26,
            color=color,
            size=2,
        )
    return tuple(tuple(row) for row in pixels)


def _nested_source_mapping_frame(
    *,
    child_payload_color: int = 7,
) -> tuple[tuple[int, ...], ...]:
    pixels = [list(row) for row in _nested_mapping_frame()]
    payloads = (
        (16, 8, 3),
        (22, 8, 5),
        (34, 8, 15),
        (16, 15, child_payload_color),
        (22, 15, 9),
        (28, 15, 11),
        (34, 15, 13),
    )
    for left, top, color in payloads:
        _paint(pixels, left=left, top=top, color=color, size=2)
    for index in range(7):
        _paint(
            pixels,
            left=2 + index * 7,
            top=26,
            color=2,
            size=2,
        )
    return tuple(tuple(row) for row in pixels)


def _sibling_container_mapping_frame() -> tuple[tuple[int, ...], ...]:
    reference = (3, 5, 7, 9, 11, 13, 15)
    selectors = (15, 5, 11, 3, 13, 9, 7)
    pixels = [[0 for _x in range(56)] for _y in range(31)]
    for index, color in enumerate(reference):
        _paint(
            pixels,
            left=2 + index * 7,
            top=1,
            color=color,
            size=3,
            outline=True,
        )
    for color, left, right, top in (
        (8, 13, 44, 6),
        (14, 13, 26, 14),
        (9, 31, 44, 14),
    ):
        for x in range(left, right + 1):
            pixels[top][x] = color
            pixels[top + 6][x] = color
        for y in range(top, top + 7):
            pixels[y][left] = color
            pixels[y][right] = color
    for left, top in (
        (16, 8),
        (28, 8),
        (40, 8),
        (16, 16),
        (22, 16),
        (34, 16),
        (40, 16),
    ):
        _paint(pixels, left=left, top=top, color=2, size=2)
    _paint(pixels, left=22, top=8, color=14, size=2)
    _paint(pixels, left=34, top=8, color=9, size=2)
    for index, color in enumerate(selectors):
        _paint(
            pixels,
            left=2 + index * 7,
            top=27,
            color=color,
            size=2,
        )
    return tuple(tuple(row) for row in pixels)


def _relocatable_connector_mapping_frame(
    *,
    marker_left: int = 22,
    fixed_payload_color: int = 14,
    connector_outline: bool = True,
) -> tuple[tuple[int, ...], ...]:
    reference = (11, 8, 14, 9, 6, 12, 15)
    selectors = (11, 6, 12, 8, 15, 9, 14)
    pixels = [[0 for _x in range(56)] for _y in range(32)]
    for index, color in enumerate(reference):
        _paint(
            pixels,
            left=2 + index * 7,
            top=1,
            color=color,
            size=3,
            outline=True,
        )
    for color, left, right, top in (
        (8, 13, 44, 6),
        (14, 19, 38, 14),
    ):
        for x in range(left, right + 1):
            pixels[top][x] = color
            pixels[top + 6][x] = color
        for y in range(top, top + 7):
            pixels[y][left] = color
            pixels[y][right] = color
    for left, top in (
        (16, 8),
        (22, 8),
        (28, 8),
        (34, 8),
        (40, 8),
        (28, 16),
        (34, 16),
    ):
        _paint(pixels, left=left, top=top, color=2, size=2)
    _paint(
        pixels,
        left=marker_left,
        top=16,
        color=fixed_payload_color,
        size=2,
    )
    for index, color in enumerate(selectors):
        _paint(
            pixels,
            left=2 + index * 7,
            top=27,
            color=color,
            size=4,
            outline=color == 14 and connector_outline,
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


def test_nested_container_link_parameterizes_target_traversal() -> None:
    observation = _observation(_nested_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
    )
    explorer.observe(observation, scene)

    choices = tuple(
        explorer.select(observation, scene, (5, 6, 7)).token for _step in range(15)
    )
    target_clicks = tuple(
        dict(token.data)
        for token in choices
        if token.action_id == 6 and dict(token.data).get("y") in {8, 15}
    )

    assert target_clicks == (
        {"x": 16, "y": 8},
        {"x": 22, "y": 8},
        {"x": 16, "y": 15},
        {"x": 22, "y": 15},
        {"x": 28, "y": 15},
        {"x": 34, "y": 15},
        {"x": 34, "y": 8},
    )
    assert choices[-1] == ActionToken(5)
    assert explorer.nested_target_plan_active


def test_nested_container_traversal_abstains_on_unmatched_link() -> None:
    observation = _observation(_nested_mapping_frame(connector_color=6))
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
    )
    explorer.observe(observation, scene)

    explorer.select(observation, scene, (5, 6, 7))

    assert explorer.select_apply_program == ()
    assert not explorer.nested_target_plan_active


def test_nested_source_traversal_flattens_payloads_into_neutral_outputs() -> None:
    observation = _observation(_nested_source_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
        nested_source_traversal=True,
    )
    explorer.observe(observation, scene)

    choices = tuple(
        explorer.select(observation, scene, (5, 6, 7)).token for _step in range(15)
    )
    source_clicks = tuple(
        dict(token.data)
        for token in choices
        if token.action_id == 6 and dict(token.data).get("y") in {8, 15}
    )
    output_clicks = tuple(
        dict(token.data)
        for token in choices
        if token.action_id == 6 and dict(token.data).get("y") == 26
    )

    assert source_clicks == (
        {"x": 16, "y": 8},
        {"x": 22, "y": 8},
        {"x": 16, "y": 15},
        {"x": 22, "y": 15},
        {"x": 28, "y": 15},
        {"x": 34, "y": 15},
        {"x": 34, "y": 8},
    )
    assert output_clicks == tuple({"x": 2 + index * 7, "y": 26} for index in range(7))
    assert choices[-1] == ActionToken(5)
    assert explorer.nested_source_plan_active


def test_nested_source_traversal_requires_exact_reference_order() -> None:
    observation = _observation(
        _nested_source_mapping_frame(child_payload_color=6)
    )
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
        nested_source_traversal=True,
    )
    explorer.observe(observation, scene)

    explorer.select(observation, scene, (5, 6, 7))

    assert explorer.select_apply_program == ()
    assert not explorer.nested_source_plan_active


def test_enclosure_topology_separates_same_height_sibling_containers() -> None:
    observation = _observation(_sibling_container_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
        enclosure_target_traversal=True,
    )
    explorer.observe(observation, scene)

    choices = tuple(
        explorer.select(observation, scene, (5, 6, 7)).token for _step in range(15)
    )
    target_clicks = tuple(
        dict(token.data)
        for token in choices
        if token.action_id == 6 and dict(token.data).get("y") in {8, 16}
    )

    assert target_clicks == (
        {"x": 16, "y": 8},
        {"x": 16, "y": 16},
        {"x": 22, "y": 16},
        {"x": 28, "y": 8},
        {"x": 34, "y": 16},
        {"x": 40, "y": 16},
        {"x": 40, "y": 8},
    )
    assert choices[-1] == ActionToken(5)
    assert explorer.nested_target_plan_active


def test_connector_relocation_constructs_parent_child_topology() -> None:
    observation = _observation(_relocatable_connector_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
        enclosure_target_traversal=True,
        connector_relocation=True,
    )
    explorer.observe(observation, scene)

    choices = tuple(
        explorer.select(observation, scene, (5, 6, 7)).token for _step in range(17)
    )

    assert choices[:2] == (
        ActionToken(6, (("x", 22), ("y", 16))),
        ActionToken(6, (("x", 22), ("y", 8))),
    )
    target_clicks = tuple(
        dict(token.data)
        for token in choices[2:]
        if token.action_id == 6 and dict(token.data).get("y") in {8, 16}
    )
    assert target_clicks == (
        {"x": 16, "y": 8},
        {"x": 22, "y": 16},
        {"x": 28, "y": 16},
        {"x": 34, "y": 16},
        {"x": 28, "y": 8},
        {"x": 34, "y": 8},
        {"x": 40, "y": 8},
    )
    assert choices[-1] == ActionToken(5)
    assert explorer.nested_target_plan_active
    assert explorer.connector_relocation_plan_active
    assert explorer.select_apply_diagnostic == "connector-relocation-selected"
    assert "operator:relocate-connector" in explorer.last_scheme_components


def test_connector_relocation_abstains_without_exact_lattice_alignment() -> None:
    observation = _observation(
        _relocatable_connector_mapping_frame(marker_left=24)
    )
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
        enclosure_target_traversal=True,
        connector_relocation=True,
    )
    explorer.observe(observation, scene)

    explorer.select(observation, scene, (5, 6, 7))

    assert explorer.select_apply_program == ()
    assert not explorer.connector_relocation_plan_active


def test_constructive_connector_uses_fixed_payload_reference_alignment() -> None:
    observation = _observation(_relocatable_connector_mapping_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
        enclosure_target_traversal=True,
        constructive_connector_placement=True,
    )
    explorer.observe(observation, scene)

    choices = tuple(
        explorer.select(observation, scene, (5, 6, 7)).token
        for _step in range(15)
    )
    target_clicks = tuple(
        dict(token.data)
        for token in choices
        if token.action_id == 6 and dict(token.data).get("y") in {8, 16}
    )
    connector_point = dict(choices[4].data)

    assert target_clicks == (
        {"x": 16, "y": 8},
        {"x": 22, "y": 8},
        {"x": 28, "y": 8},
        {"x": 28, "y": 16},
        {"x": 34, "y": 16},
        {"x": 34, "y": 8},
        {"x": 40, "y": 8},
    )
    assert connector_point["y"] == 27
    assert observation.frame[connector_point["y"]][connector_point["x"]] == 14
    assert choices[-1] == ActionToken(5)
    assert explorer.nested_target_plan_active
    assert explorer.constructive_connector_plan_active
    assert not explorer.connector_relocation_plan_active
    assert explorer.select_apply_diagnostic == "constructive-connector-selected"
    assert (
        "operator:construct-connector-from-fixed-payload"
        in explorer.last_scheme_components
    )


def test_constructive_connector_requires_an_external_outline() -> None:
    observation = _observation(
        _relocatable_connector_mapping_frame(connector_outline=False)
    )
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        parameterized_select_apply_commit=True,
        multiline_target_binding=True,
        nested_target_traversal=True,
        enclosure_target_traversal=True,
        constructive_connector_placement=True,
    )
    explorer.observe(observation, scene)

    explorer.select(observation, scene, (5, 6, 7))

    assert explorer.select_apply_program == ()
    assert not explorer.constructive_connector_plan_active


def test_constructive_connector_config_requires_enclosure_traversal() -> None:
    with pytest.raises(
        ValueError,
        match="constructive connector placement requires enclosure",
    ):
        MindConfig(enable_constructive_connector_placement=True)


def test_constructive_connector_config_reaches_runtime_explorer() -> None:
    config = MindConfig(
        enable_parameterized_select_apply_commit=True,
        enable_multiline_target_binding=True,
        enable_nested_target_traversal=True,
        enable_enclosure_target_traversal=True,
        enable_constructive_connector_placement=True,
    )

    policy = SymbolicPolicy(config)

    assert policy.explorer.constructive_connector_placement
    assert policy.trace.mind_config[
        "enable_constructive_connector_placement"
    ]


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
    assert MindConfig() == MindConfig(
        enable_constructive_connector_placement=False
    )
