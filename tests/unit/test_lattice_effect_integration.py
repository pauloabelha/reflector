from reflector.core.exploration import ActionToken, EpistemicExplorer
from reflector.core.perception import SceneTracker
from reflector.core.symbolic import Observation


def _marked_lattice_frame(
    *,
    origin: tuple[int, int] = (4, 4),
    colors: tuple[int, int, int, int, int, int] = (5, 4, 9, 6, 0, 2),
    values: dict[tuple[int, int], int] | None = None,
    malformed: tuple[int, int] | None = None,
    clue_overrides: dict[int, int] | None = None,
) -> tuple[tuple[int, ...], ...]:
    background, low, high, mark, same_symbol, different_symbol = colors
    size = 6
    step = 8
    width = origin[0] + step * 3 + size + 4
    height = origin[1] + step * 3 + size + 4
    pixels = [[background for _x in range(width)] for _y in range(height)]
    supplied = values or {}
    for row in range(3):
        for column in range(3):
            if (column, row) == (1, 1):
                continue
            start_x = origin[0] + column * step
            start_y = origin[1] + row * step
            value = supplied.get((column, row), low)
            for y in range(start_y, start_y + size):
                for x in range(start_x, start_x + size):
                    pixels[y][x] = value
            if malformed != (column, row):
                for y in range(start_y, start_y + 2):
                    for x in range(start_x + 2, start_x + 4):
                        pixels[y][x] = mark

    clue_x = origin[0] + step
    clue_y = origin[1] + step
    clue = [
        same_symbol,
        same_symbol,
        different_symbol,
        same_symbol,
        high,
        same_symbol,
        different_symbol,
        same_symbol,
        same_symbol,
    ]
    for index, value in (clue_overrides or {}).items():
        clue[index] = value
    subcell = size // 3
    for index, value in enumerate(clue):
        start_x = clue_x + index % 3 * subcell
        start_y = clue_y + index // 3 * subcell
        for y in range(start_y, start_y + subcell):
            for x in range(start_x, start_x + subcell):
                pixels[y][x] = value
    return tuple(tuple(row) for row in pixels)


def _observation(
    frame: tuple[tuple[int, ...], ...],
    *,
    action_id: int,
) -> Observation:
    return Observation.create(
        state="NOT_FINISHED",
        available_actions=(action_id,),
        frame=frame,
    )


def _ground_two_effects(
    *,
    origin: tuple[int, int] = (4, 4),
    colors: tuple[int, int, int, int, int, int] = (5, 4, 9, 6, 0, 2),
    action_id: int = 6,
    click_offset: tuple[int, int] = (0, 0),
) -> tuple[
    EpistemicExplorer,
    tuple[tuple[int, ...], ...],
    tuple[int, int],
]:
    low, high = colors[1], colors[2]
    explorer = EpistemicExplorer(
        complex_action=action_id,
        lattice_effect_planning=True,
    )
    explorer.learned_local_relation = {
        colors[4]: True,
        colors[5]: False,
    }
    initial = _marked_lattice_frame(origin=origin, colors=colors)
    grounding = explorer._lattice_effect_grounding(initial)
    assert grounding is not None
    top = min(grounding.anchors, key=lambda point: (point[1], point[0]))
    below = next(
        point
        for point in grounding.anchors
        if point[0] == top[0] and point[1] > top[1]
    )
    point_by_grid = {
        (
            (point[0] - top[0]) // 8,
            (point[1] - top[1]) // 8,
        ): point
        for point in grounding.anchors
    }
    top_grid = next(key for key, point in point_by_grid.items() if point == top)
    below_grid = next(key for key, point in point_by_grid.items() if point == below)
    after_top = _marked_lattice_frame(
        origin=origin,
        colors=colors,
        values={top_grid: high},
    )
    after_below = _marked_lattice_frame(
        origin=origin,
        colors=colors,
        values={below_grid: high, top_grid: low},
    )
    explorer._observe_lattice_effect_transition(
        initial,
        after_top,
        ActionToken(
            action_id,
            (
                ("x", top[0] + click_offset[0]),
                ("y", top[1] + click_offset[1]),
            ),
        ),
    )
    explorer._observe_lattice_effect_transition(
        after_top,
        after_below,
        ActionToken(
            action_id,
            (
                ("x", below[0] + click_offset[0]),
                ("y", below[1] + click_offset[1]),
            ),
        ),
    )
    return explorer, after_below, top


def test_lattice_effect_planner_learns_boundary_and_interior_effects() -> None:
    explorer, current, _top = _ground_two_effects()

    assert explorer.lattice_effect_model is not None
    assert tuple(
        effect.offset for effect in explorer.lattice_effect_model.effects
    ) == ((0, -8), (0, 0))
    observation = _observation(current, action_id=6)
    scene = SceneTracker().perceive(observation)[0]
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.reason.endswith("lattice-effect-planning")
    assert choice.token in explorer._tokens(observation, scene, (6,))
    assert explorer.to_dict()["lattice_effect_model_grounded"] == 1
    assert explorer.to_dict()["lattice_effect_plan_steps"] == 1


def test_lattice_effect_planner_canonicalizes_offset_clicks_inside_nodes() -> None:
    explorer, _current, _top = _ground_two_effects(click_offset=(0, -2))

    assert explorer.lattice_effect_observations == 2
    assert explorer.lattice_effect_model is not None
    assert tuple(
        effect.offset for effect in explorer.lattice_effect_model.effects
    ) == ((0, -8), (0, 0))


def test_lattice_effect_planner_requires_diverse_probe_contexts() -> None:
    explorer = EpistemicExplorer(lattice_effect_planning=True)
    explorer.learned_local_relation = {0: True, 2: False}
    initial = _marked_lattice_frame()
    grounding = explorer._lattice_effect_grounding(initial)
    assert grounding is not None
    top = min(grounding.anchors, key=lambda point: (point[1], point[0]))
    after_top = _marked_lattice_frame(values={(0, 0): 9})
    token = ActionToken(6, (("x", top[0]), ("y", top[1])))

    explorer._observe_lattice_effect_transition(initial, after_top, token)
    explorer._observe_lattice_effect_transition(after_top, initial, token)

    assert explorer.lattice_effect_observations == 2
    assert len(set(explorer.lattice_effect_probe_contexts)) == 1
    assert explorer.lattice_effect_model is None
    assert explorer.lattice_effect_diagnostic == (
        "awaiting-diverse-effect-evidence"
    )


def test_lattice_effect_prediction_noop_mismatch_quarantines_model() -> None:
    explorer, current, top = _ground_two_effects()
    model = explorer.lattice_effect_model
    grounding = explorer._lattice_effect_grounding(current)
    assert model is not None
    assert grounding is not None
    assert model.apply(grounding.state, top) != grounding.state
    token = ActionToken(6, (("x", top[0]), ("y", top[1])))

    explorer._observe_lattice_effect_transition(current, current, token)

    assert explorer.lattice_effect_model is None
    assert explorer.lattice_effect_quarantined
    assert explorer.lattice_effect_prediction_mismatches == 1
    assert explorer.lattice_effect_transitions == []
    assert explorer.lattice_effect_probe_contexts == []
    assert explorer.lattice_effect_diagnostic == (
        "effect-model-prediction-mismatch-quarantined"
    )

    initial = _marked_lattice_frame()
    after_top = _marked_lattice_frame(values={(0, 0): 9})
    explorer._observe_lattice_effect_transition(initial, after_top, token)

    assert explorer.lattice_effect_observations == 2
    assert explorer.lattice_effect_model is None
    assert explorer.lattice_effect_transitions == []
    assert explorer.lattice_effect_diagnostic == "effect-model-quarantined"


def test_lattice_effect_plan_is_translation_recolor_and_action_role_equivariant() -> None:
    base, base_frame, base_top = _ground_two_effects()
    shifted, shifted_frame, shifted_top = _ground_two_effects(
        origin=(7, 9),
        colors=(1, 3, 13, 8, 10, 12),
        action_id=11,
    )
    base_observation = _observation(base_frame, action_id=6)
    shifted_observation = _observation(shifted_frame, action_id=11)
    base_scene = SceneTracker().perceive(base_observation)[0]
    shifted_scene = SceneTracker().perceive(shifted_observation)[0]
    base.observe(base_observation, base_scene)
    shifted.observe(shifted_observation, shifted_scene)

    base_choice = base.select(base_observation, base_scene, (6,))
    shifted_choice = shifted.select(shifted_observation, shifted_scene, (11,))

    base_data = dict(base_choice.token.data)
    shifted_data = dict(shifted_choice.token.data)
    assert shifted_choice.token.action_id == 11
    assert shifted_data["x"] - base_data["x"] == shifted_top[0] - base_top[0]
    assert shifted_data["y"] - base_data["y"] == shifted_top[1] - base_top[1]


def test_lattice_effect_grounding_rejects_mixed_actuator_forms() -> None:
    frame = _marked_lattice_frame(malformed=(0, 0))
    explorer = EpistemicExplorer(lattice_effect_planning=True)
    explorer.learned_local_relation = {0: True, 2: False}

    assert explorer._lattice_effect_grounding(frame) is None


def test_lattice_effect_grounding_rejects_unknown_adjacent_relation_symbol() -> None:
    frame = _marked_lattice_frame(clue_overrides={0: 3})
    explorer = EpistemicExplorer(lattice_effect_planning=True)
    explorer.learned_local_relation = {0: True, 2: False}

    assert explorer._lattice_effect_grounding(frame) is None


def test_lattice_effect_planner_is_an_exact_configuration_ablation() -> None:
    frame = _marked_lattice_frame()
    disabled = EpistemicExplorer(lattice_effect_planning=False)
    disabled.learned_local_relation = {0: True, 2: False}

    assert disabled._lattice_effect_grounding(frame) is None
    assert (
        disabled._select_lattice_effect_plan(
            _observation(frame, action_id=6),
            (),
        )
        is None
    )
