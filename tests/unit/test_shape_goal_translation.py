from reflector import MindConfig
from reflector.exploration import EpistemicExplorer
from reflector.perception import SceneTracker
from reflector.symbolic import Observation

_MOVER_SHAPE = ((0, 0), (1, 0), (2, 0), (1, 1))
_DECOY_SHAPE = ((0, 0), (1, 0), (0, 1), (1, 1))


def _paint_shape(
    pixels: list[list[int]],
    *,
    origin: tuple[int, int],
    color: int,
    shape: tuple[tuple[int, int], ...],
) -> None:
    for local_x, local_y in shape:
        pixels[origin[1] + local_y][origin[0] + local_x] = color


def _frame(
    *,
    mover: tuple[int, int],
    target: tuple[int, int] = (13, 9),
    decoy: tuple[int, int] = (18, 5),
    extra_target: tuple[int, int] | None = None,
) -> tuple[tuple[int, ...], ...]:
    pixels = [[0 for _x in range(24)] for _y in range(18)]
    _paint_shape(pixels, origin=mover, color=3, shape=_MOVER_SHAPE)
    _paint_shape(pixels, origin=target, color=7, shape=_MOVER_SHAPE)
    if extra_target is not None:
        _paint_shape(
            pixels,
            origin=extra_target,
            color=9,
            shape=_MOVER_SHAPE,
        )
    _paint_shape(pixels, origin=decoy, color=5, shape=_DECOY_SHAPE)
    return tuple(tuple(row) for row in pixels)


def _observation(
    frame: tuple[tuple[int, ...], ...],
    *,
    levels_completed: int = 0,
) -> Observation:
    return Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3, 4, 6),
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
) -> tuple[int, str]:
    scene, _events = tracker.perceive(observation)
    choice = explorer.select(observation, scene, (1, 2, 3, 4, 6))
    return choice.token.action_id, choice.reason


def test_evidenced_translations_compose_toward_unique_exact_shape() -> None:
    explorer = EpistemicExplorer(shape_goal_translation=True)
    tracker = SceneTracker()
    mover = (5, 5)
    decoy = (18, 5)
    observation = _observation(_frame(mover=mover, decoy=decoy))
    _ingest(explorer, tracker, observation)
    effects = {
        1: ((0, -2), (0, -2)),
        2: ((0, 2), (0, 2)),
        3: ((2, 0), (0, 0)),
        4: ((-2, 0), (0, 0)),
    }
    actions = []
    learned_effects: dict[int, tuple[int, int]] = {}
    application_trials = 0
    max_occluded_steps = 0

    while mover != (13, 9):
        action_id, reason = _choose(explorer, tracker, observation)
        assert reason == "epistemic-frontier:shape-goal-translation"
        actions.append(action_id)
        mover_effect, decoy_effect = effects[action_id]
        mover = (
            mover[0] + mover_effect[0],
            mover[1] + mover_effect[1],
        )
        decoy = (
            decoy[0] + decoy_effect[0],
            decoy[1] + decoy_effect[1],
        )
        if mover == (13, 9):
            learned_effects = dict(explorer.shape_translation_effects)
            application_trials = explorer.shape_translation_application_trials
            observation = _observation(
                _frame(mover=(4, 4)),
                levels_completed=1,
            )
        else:
            observation = _observation(_frame(mover=mover, decoy=decoy))
        _ingest(explorer, tracker, observation)
        max_occluded_steps = max(
            max_occluded_steps,
            explorer.shape_translation_occluded_steps,
        )

    assert actions == [1, 2, 2, 2, 3, 3, 3, 3]
    assert learned_effects == {
        1: (0, -2),
        2: (0, 2),
        3: (2, 0),
    }
    assert application_trials == 5
    assert max_occluded_steps == 1
    assert explorer.last_scheme_components == (
        "scheme:evidenced-shape-goal-translation",
        "relation:exact-normalized-shape",
        "operator:apply-evidenced-translation",
    )
    assert explorer.shape_translation_effects == {}
    assert explorer.shape_translation_probes == set()
    assert explorer.shape_translation_level_trials == 0
    assert explorer.shape_translation_application_trials == 0


def test_shape_goal_translation_abstains_on_ambiguous_goal() -> None:
    observation = _observation(
        _frame(mover=(5, 5), extra_target=(15, 11))
    )
    tracker = SceneTracker()
    scene, _events = tracker.perceive(observation)
    explorer = EpistemicExplorer(shape_goal_translation=True)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (1, 2, 3, 4, 6))

    assert choice.reason != "epistemic-frontier:shape-goal-translation"
    assert explorer.shape_translation_probes == set()
    assert explorer.shape_translation_diagnostic == "no-unique-shape-pair"


def test_falsified_translation_is_invalidated_and_not_repeated() -> None:
    explorer = EpistemicExplorer(shape_goal_translation=True)
    tracker = SceneTracker()
    mover = (5, 5)
    decoy = (18, 5)
    observation = _observation(_frame(mover=mover, decoy=decoy))
    _ingest(explorer, tracker, observation)

    action_id, _reason = _choose(explorer, tracker, observation)
    assert action_id == 1
    mover = (5, 3)
    decoy = (16, 3)
    observation = _observation(_frame(mover=mover, decoy=decoy))
    _ingest(explorer, tracker, observation)

    action_id, _reason = _choose(explorer, tracker, observation)
    assert action_id == 2
    mover = (5, 5)
    decoy = (16, 5)
    observation = _observation(_frame(mover=mover, decoy=decoy))
    _ingest(explorer, tracker, observation)

    action_id, _reason = _choose(explorer, tracker, observation)
    assert action_id == 2
    _ingest(explorer, tracker, observation)

    action_id, reason = _choose(explorer, tracker, observation)
    assert action_id == 3
    assert reason == "epistemic-frontier:shape-goal-translation"
    assert 2 in explorer.shape_translation_invalid_actions
    assert 2 not in explorer.shape_translation_effects


def test_animated_border_cannot_validate_blocked_occluded_translation() -> None:
    explorer = EpistemicExplorer(shape_goal_translation=True)
    tracker = SceneTracker()
    mover = (5, 5)
    decoy = (18, 5)
    observation = _observation(_frame(mover=mover, decoy=decoy))
    _ingest(explorer, tracker, observation)
    effects = {
        1: ((0, -2), (0, -2)),
        2: ((0, 2), (0, 2)),
        3: ((2, 0), (0, 0)),
    }

    for expected_action in (1, 2, 2, 2, 3, 3, 3):
        action_id, reason = _choose(explorer, tracker, observation)
        assert action_id == expected_action
        assert reason == "epistemic-frontier:shape-goal-translation"
        mover_effect, decoy_effect = effects[action_id]
        mover = (
            mover[0] + mover_effect[0],
            mover[1] + mover_effect[1],
        )
        decoy = (
            decoy[0] + decoy_effect[0],
            decoy[1] + decoy_effect[1],
        )
        observation = _observation(_frame(mover=mover, decoy=decoy))
        _ingest(explorer, tracker, observation)

    assert mover == (11, 9)
    assert explorer.shape_translation_occluded_steps == 1
    action_id, reason = _choose(explorer, tracker, observation)
    assert action_id == 3
    assert reason == "epistemic-frontier:shape-goal-translation"

    border_only = [list(row) for row in observation.frame]
    border_only[0][0] = 9
    blocked = _observation(tuple(tuple(row) for row in border_only))
    _ingest(explorer, tracker, blocked)

    assert 3 in explorer.shape_translation_invalid_actions
    assert 3 not in explorer.shape_translation_effects
    assert (
        explorer.shape_translation_diagnostic
        == "translation-prediction-falsified"
    )


def test_shape_goal_translation_is_exactly_off_by_default() -> None:
    observation = _observation(_frame(mover=(5, 5)))
    tracker = SceneTracker()
    scene, _events = tracker.perceive(observation)
    default = EpistemicExplorer()
    explicit_off = EpistemicExplorer(shape_goal_translation=False)
    default.observe(observation, scene)
    explicit_off.observe(observation, scene)

    assert default.select(observation, scene, (1, 2, 3, 4, 6)) == (
        explicit_off.select(observation, scene, (1, 2, 3, 4, 6))
    )
    assert default.to_dict() == explicit_off.to_dict()
    assert MindConfig() == MindConfig(enable_shape_goal_translation=False)
