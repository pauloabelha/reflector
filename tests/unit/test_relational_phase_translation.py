from reflector import MindConfig
from reflector.exploration import EpistemicExplorer
from reflector.perception import SceneTracker
from reflector.symbolic import Observation

_MOVER_SHAPE = ((0, 0), (1, 0), (2, 0), (1, 1))
_ACTIONS = (1, 2, 3, 4, 5, 6)


def _paint(
    pixels: list[list[int]],
    origin: tuple[int, int],
    color: int,
    shape: tuple[tuple[int, int], ...],
) -> None:
    for local_x, local_y in shape:
        pixels[origin[1] + local_y][origin[0] + local_x] = color


def _outline(
    pixels: list[list[int]],
    origin: tuple[int, int],
    size: tuple[int, int],
    color: int,
) -> None:
    width, height = size
    shape = tuple(
        (x, y)
        for y in range(height)
        for x in range(width)
        if x in {0, width - 1} or y in {0, height - 1}
    )
    _paint(pixels, origin, color, shape)


def _frame(
    *,
    mover: tuple[int, int],
    phase: int,
    edge_tick: int | None = None,
) -> tuple[tuple[int, ...], ...]:
    pixels = [[0 for _x in range(36)] for _y in range(26)]
    _paint(pixels, mover, 3, _MOVER_SHAPE)
    _paint(pixels, (13, 16), 7, _MOVER_SHAPE)
    _outline(pixels, (20, 2), (5, 6), 8)
    _outline(pixels, (26, 11), (6, 7), 10)
    marker = (22, 4) if phase == 0 else (29, 14)
    pixels[marker[1]][marker[0]] = 9
    if edge_tick is not None:
        pixels[-1][edge_tick] = 11
    return tuple(tuple(row) for row in pixels)


def _observation(
    frame: tuple[tuple[int, ...], ...],
    *,
    levels_completed: int = 0,
) -> Observation:
    return Observation.create(
        state="NOT_FINISHED",
        available_actions=_ACTIONS,
        frame=frame,
        levels_completed=levels_completed,
    )


def _ingest(
    explorer: EpistemicExplorer,
    tracker: SceneTracker,
    observation: Observation,
) -> None:
    scene, _events = tracker.perceive(observation)
    explorer.observe(observation, scene)


def _choose(
    explorer: EpistemicExplorer,
    tracker: SceneTracker,
    observation: Observation,
) -> int:
    scene, _events = tracker.perceive(observation)
    choice = explorer.select(observation, scene, _ACTIONS)
    assert choice.reason == "epistemic-frontier:shape-goal-translation"
    return choice.token.action_id


def test_phase_change_reprobes_and_quarantines_old_action_semantics() -> None:
    explorer = EpistemicExplorer(
        shape_goal_translation=True,
        relational_phase_translation=True,
    )
    tracker = SceneTracker()
    mover = (5, 12)
    phase = 0
    observation = _observation(_frame(mover=mover, phase=phase))
    _ingest(explorer, tracker, observation)
    actions: list[int] = []
    final_phase_effects: dict[int, tuple[int, int]] = {}
    phase_model_count = 0
    phase_transition_count = 0

    while mover != (13, 16):
        action = _choose(explorer, tracker, observation)
        actions.append(action)
        if phase == 0 and action == 3:
            mover = (mover[0] + 4, mover[1])
        elif phase == 0 and action == 5:
            phase = 1
        elif phase == 1 and action == 2:
            mover = (mover[0], mover[1] + 2)
        progressed = mover == (13, 16)
        if progressed:
            final_phase_effects = dict(explorer.shape_translation_effects)
            phase_model_count = len(explorer.shape_translation_phase_models)
            phase_transition_count = (
                explorer.shape_translation_phase_transition_count
            )
        observation = _observation(
            _frame(mover=mover, phase=phase),
            levels_completed=int(progressed),
        )
        _ingest(explorer, tracker, observation)

    assert actions == [1, 2, 3, 3, 4, 5, 1, 2, 2]
    assert phase_transition_count == 1
    assert phase_model_count == 2
    assert final_phase_effects == {2: (0, 2)}
    assert 3 not in final_phase_effects
    assert explorer.shape_translation_phase_blocked is False


def test_edge_animation_does_not_create_a_relational_phase() -> None:
    explorer = EpistemicExplorer(
        shape_goal_translation=True,
        relational_phase_translation=True,
    )
    tracker = SceneTracker()
    observation = _observation(_frame(mover=(5, 12), phase=0, edge_tick=1))
    _ingest(explorer, tracker, observation)

    assert _choose(explorer, tracker, observation) == 1
    observation = _observation(_frame(mover=(5, 12), phase=0, edge_tick=2))
    _ingest(explorer, tracker, observation)

    assert explorer.shape_translation_phase_transition_count == 0
    assert len(explorer.shape_translation_phase_models) == 1
    assert explorer.shape_translation_phase_blocked is False


def test_ambiguous_marker_hosts_block_phase_conditioned_advisor() -> None:
    pixels = [[0 for _x in range(36)] for _y in range(26)]
    _paint(pixels, (3, 3), 3, _MOVER_SHAPE)
    _paint(pixels, (11, 7), 7, _MOVER_SHAPE)
    _outline(pixels, (18, 2), (12, 12), 8)
    _outline(pixels, (21, 5), (6, 6), 10)
    pixels[8][24] = 9
    observation = _observation(tuple(tuple(row) for row in pixels))
    tracker = SceneTracker()
    scene, _events = tracker.perceive(observation)
    explorer = EpistemicExplorer(
        shape_goal_translation=True,
        relational_phase_translation=True,
    )
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, _ACTIONS)

    assert choice.reason != "epistemic-frontier:shape-goal-translation"
    assert explorer.shape_translation_phase_blocked is True
    assert explorer.shape_translation_diagnostic == "ambiguous-marker-host"


def test_relational_phase_translation_requires_shape_goal_translation() -> None:
    try:
        MindConfig(enable_relational_phase_translation=True)
    except ValueError as error:
        assert str(error) == (
            "relational phase translation requires shape-goal translation"
        )
    else:
        raise AssertionError("dependency validation did not reject invalid config")
