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
