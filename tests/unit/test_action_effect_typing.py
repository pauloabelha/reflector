from __future__ import annotations

import pytest

from reflector.core.action_effect_typing import (
    ProspectiveActionEffectTyper,
    infer_action_effect,
)
from reflector.core.action_translation_algebra import ActionIdentity
from reflector.core.exploration import (
    ActionRole,
    ActionToken,
    EpistemicExplorer,
    GroundedRole,
    ProgressPathStep,
)
from reflector.core.mind import MindConfig
from reflector.core.perception import SceneTracker
from reflector.core.symbolic import Observation, Scene

type Frame = tuple[tuple[int, ...], ...]


def _frame(
    points: tuple[tuple[int, int, int], ...],
    *,
    width: int = 8,
    height: int = 6,
) -> Frame:
    grid = [[0 for _x in range(width)] for _y in range(height)]
    for x, y, color in points:
        grid[y][x] = color
    return tuple(tuple(row) for row in grid)


def _observation(frame: Frame) -> tuple[Observation, Scene]:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 5),
        frame=frame,
    )
    scene, _events = SceneTracker().perceive(observation)
    return observation, scene


def test_classifies_positive_effect_kinds_without_fixed_colors() -> None:
    single = _frame(((1, 2, 2),))
    recolored_single = _frame(((1, 2, 7),))
    translated = _frame(((3, 2, 7),))
    born = _frame(((1, 2, 2), (6, 4, 8)))

    assert infer_action_effect(single, single).kind == "render-noop"
    assert infer_action_effect(recolored_single, translated).kind == (
        "relative-translation"
    )
    assert infer_action_effect(single, born).kind == "component-birth"


def test_classifies_form_and_relative_layout_change() -> None:
    compact = _frame(((1, 2, 2), (2, 2, 2)))
    reshaped = _frame(((1, 2, 2), (1, 3, 2)))
    pair = _frame(((1, 2, 2), (6, 2, 2)))
    changed_layout = _frame(((2, 2, 2), (5, 2, 2)))

    assert infer_action_effect(compact, reshaped).kind == (
        "component-form-change"
    )
    assert infer_action_effect(pair, changed_layout).kind == (
        "relative-layout-change"
    )


def test_positive_effect_type_is_invariant_to_recoloring_and_translation() -> None:
    first = infer_action_effect(
        _frame(((1, 2, 2),)),
        _frame(((1, 2, 2), (6, 4, 8))),
    )
    transformed = infer_action_effect(
        _frame(((2, 1, 7),)),
        _frame(((2, 1, 7), (5, 3, 4))),
    )

    assert first.kind == transformed.kind == "component-birth"


def test_shortest_progress_path_compiles_and_run_length_encodes_roles() -> None:
    explorer = EpistemicExplorer(shortest_progress_path_reuse=True)
    states = tuple(
        (0, "NOT_FINISHED", f"state-{index}") for index in range(4)
    )
    first = ActionToken(1)
    repeated = ActionToken(2)
    detour = ActionToken(3)
    first_role = GroundedRole(ActionRole(1))
    repeated_role = GroundedRole(ActionRole(2))
    explorer.current_level = 0
    explorer.level_start_state = states[0]
    explorer.pending = (states[2], repeated)
    explorer.edges = {
        (states[0], first): states[1],
        (states[1], repeated): states[2],
        (states[0], detour): states[3],
        (states[3], detour): states[2],
    }
    explorer.edge_groundings = {
        (states[0], first): first_role,
        (states[1], repeated): repeated_role,
        (states[2], repeated): repeated_role,
        (states[0], detour): GroundedRole(ActionRole(3)),
        (states[3], detour): GroundedRole(ActionRole(3)),
    }
    explorer.state_status = {
        state: "NOT_FINISHED" for state in states
    }

    explorer._compile_shortest_progress_path()

    assert explorer.shortest_progress_path == (
        ProgressPathStep(ActionRole(1), 1),
        ProgressPathStep(ActionRole(2), 2),
    )
    assert explorer.shortest_progress_path_compilations == 1


def test_progress_role_match_ignores_color_when_shape_and_area_transfer() -> None:
    shape = ((0, 0), (0, 1), (1, 0), (1, 1))
    expected = ActionRole(6, color=3, area=4, shape=shape)
    transferred = ActionRole(6, color=9, area=4, shape=shape)
    unrelated = ActionRole(6, color=3, area=5, shape=((0, 0),))

    assert EpistemicExplorer._progress_role_similarity(
        expected, transferred
    ) == 5
    assert EpistemicExplorer._progress_role_similarity(
        expected, unrelated
    ) == 2


def test_progress_path_start_is_rebound_after_retry() -> None:
    explorer = EpistemicExplorer(shortest_progress_path_reuse=True)
    tracker = SceneTracker()
    active = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1,),
        frame=_frame(((1, 2, 3),)),
    )
    failed = Observation.create(
        state="GAME_OVER",
        available_actions=(0,),
        frame=active.frame,
    )
    first_scene, _events = tracker.perceive(active)
    failed_scene, _events = tracker.perceive(failed)
    retry_scene, _events = tracker.perceive(active)

    first = explorer.observe(active, first_scene)
    assert explorer.level_start_state == first
    explorer.observe(failed, failed_scene)
    assert explorer.level_start_state is None
    retry = explorer.observe(active, retry_scene)
    assert explorer.level_start_state == retry


def test_progress_path_enumerates_ambiguous_role_bindings() -> None:
    shape = ((0, 0), (0, 1), (1, 0), (1, 1))
    frame = _frame(
        (
            (1, 1, 3),
            (1, 2, 3),
            (2, 1, 3),
            (2, 2, 3),
            (5, 1, 8),
            (5, 2, 8),
            (6, 1, 8),
            (6, 2, 8),
        )
    )
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=frame,
    )
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(shortest_progress_path_reuse=True)
    explorer.shortest_progress_path = (
        ProgressPathStep(
            ActionRole(6, color=5, area=4, shape=shape),
            2,
        ),
    )
    state = (0, "NOT_FINISHED", "ambiguous")
    tokens = explorer._tokens(observation, scene, (6,))

    selections = tuple(
        explorer._select_shortest_progress_path_role(
            state,
            tokens,
            scene,
        )
        for _index in range(4)
    )

    assert selections[0] == selections[1]
    assert selections[2] == selections[3]
    assert selections[0] != selections[2]


def test_finite_orbit_composes_inverse_pair_with_silent_controls() -> None:
    explorer = EpistemicExplorer(finite_orbit_commit_exploration=True)
    first = (0, "NOT_FINISHED", "first")
    second = (0, "NOT_FINISHED", "second")
    generator = ActionToken(2)
    inverse = ActionToken(3)
    silent_one = ActionToken(1)
    silent_two = ActionToken(4)
    tokens = (silent_one, generator, inverse, silent_two)
    first_frame = _frame(((1, 2, 3),))
    second_frame = _frame(((3, 2, 3),))
    first_orbit = explorer._compact_component_state_digest(first_frame)
    second_orbit = explorer._compact_component_state_digest(second_frame)
    explorer.selection_frame = first_frame
    explorer.finite_orbit_edges = {
        (first_orbit, generator): second_orbit,
        (second_orbit, inverse): first_orbit,
        (first_orbit, silent_one): first_orbit,
        (first_orbit, silent_two): first_orbit,
    }
    explorer.attempts[(first, silent_one)] = 1
    explorer.attempts[(first, silent_two)] = 1

    assert explorer._select_finite_orbit_commit(first, tokens) == generator
    explorer.selection_frame = second_frame
    first_commit = explorer._select_finite_orbit_commit(second, tokens)
    assert first_commit == silent_one
    explorer.attempts[(second, first_commit)] += 1
    second_commit = explorer._select_finite_orbit_commit(second, tokens)
    assert second_commit == silent_two
    explorer.attempts[(second, second_commit)] += 1
    assert explorer._select_finite_orbit_commit(second, tokens) == generator


def test_one_positive_effect_proposes_and_distinct_source_confirms() -> None:
    typer = ProspectiveActionEffectTyper()
    action = ActionIdentity(5)
    first = typer.observe(
        sequence=0,
        action=action,
        before=_frame(((1, 2, 2),)),
        after=_frame(((1, 2, 2), (6, 4, 8))),
    )
    second = typer.observe(
        sequence=1,
        action=action,
        before=_frame(((2, 3, 7), (0, 0, 9))),
        after=_frame(((2, 3, 7), (0, 0, 9), (6, 4, 4))),
    )

    assert first.authority is None
    assert first.predicted_kind is None
    assert second.predicted_kind == "component-birth"
    assert second.authority is not None
    assert second.authority.kind == "component-birth"
    assert second.authority.distinct_source_states == 2


def test_noop_never_licenses_a_complement_type() -> None:
    typer = ProspectiveActionEffectTyper()
    action = ActionIdentity(4)
    frame = _frame(((1, 2, 2),))

    for sequence in range(3):
        result = typer.observe(
            sequence=sequence,
            action=action,
            before=frame,
            after=frame,
        )
        assert result.authority is None
        assert result.predicted_kind is None

    assert typer.authoritative_types() == ()
    assert typer.contextual_noops == 3


def test_context_conditioned_positive_types_can_coexist() -> None:
    typer = ProspectiveActionEffectTyper()
    action = ActionIdentity(6)
    transitions = (
        (
            _frame(((1, 2, 2),)),
            _frame(((1, 2, 2), (6, 4, 8))),
        ),
        (
            _frame(((2, 3, 7), (0, 0, 9))),
            _frame(((2, 3, 7), (0, 0, 9), (6, 4, 4))),
        ),
        (
            _frame(((1, 2, 2), (6, 4, 8))),
            _frame(((1, 2, 2),)),
        ),
        (
            _frame(((2, 3, 7), (0, 0, 9), (6, 4, 4))),
            _frame(((2, 3, 7), (0, 0, 9))),
        ),
    )
    for sequence, (before, after) in enumerate(transitions):
        typer.observe(
            sequence=sequence,
            action=action,
            before=before,
            after=after,
        )

    assert {item.kind for item in typer.authoritative_types()} == {
        "component-birth",
        "component-death",
    }


def test_explorer_effect_typing_is_exact_off_and_traces_live_authority() -> None:
    before_frame = _frame(((1, 2, 2),))
    before, before_scene = _observation(before_frame)
    off = EpistemicExplorer()
    off.observe(before, before_scene)
    assert off.to_dict()["action_effect_typing_observations"] == 0
    assert off.to_dict()["action_effect_typing_last_diagnostic"] == "exact-off"

    active = EpistemicExplorer(action_effect_typing=True)
    active.observe(before, before_scene)
    assert active.current_state is not None
    active.selection_frame = before_frame
    active._issue(  # noqa: SLF001
        active.current_state,
        ActionToken(5),
        "test-effect-proposal",
        before_scene,
    )
    born_frame = _frame(((1, 2, 2), (6, 4, 8)))
    born, born_scene = _observation(born_frame)
    active.observe(born, born_scene)

    distinct_frame = _frame(((2, 3, 7), (0, 0, 9)))
    _distinct, distinct_scene = _observation(distinct_frame)
    active.selection_frame = distinct_frame
    assert active.current_state is not None
    active._issue(  # noqa: SLF001
        active.current_state,
        ActionToken(5),
        "test-effect-confirmation",
        distinct_scene,
    )
    confirmed, confirmed_scene = _observation(
        _frame(((2, 3, 7), (0, 0, 9), (6, 4, 4)))
    )
    active.observe(confirmed, confirmed_scene)

    metrics = active.to_dict()
    assert metrics["action_effect_typing_observations"] == 2
    assert metrics["action_effect_typing_predictions"] == 1
    assert metrics["action_effect_typing_confirmations"] == 1
    assert metrics["action_effect_typing_current_types"] == 1
    assert metrics["action_effect_typing_last_kind"] == "component-birth"


def _seed_discriminative_action_types(explorer: EpistemicExplorer) -> None:
    typer = explorer.effect_typer
    translation = ActionIdentity(1)
    birth = ActionIdentity(2)
    transitions = (
        (
            translation,
            _frame(((1, 2, 2), (7, 0, 8))),
            _frame(((2, 2, 2), (7, 0, 8))),
        ),
        (
            translation,
            _frame(((3, 3, 7), (0, 0, 9))),
            _frame(((4, 3, 7), (0, 0, 9))),
        ),
        (
            birth,
            _frame(((1, 2, 2),)),
            _frame(((1, 2, 2), (6, 4, 8))),
        ),
        (
            birth,
            _frame(((2, 3, 7), (0, 0, 9))),
            _frame(((2, 3, 7), (0, 0, 9), (6, 4, 4))),
        ),
    )
    for sequence, (action, before, after) in enumerate(transitions):
        typer.observe(
            sequence=sequence,
            action=action,
            before=before,
            after=after,
        )


def test_positive_effect_family_fairness_requires_complete_distinctions() -> None:
    explorer = EpistemicExplorer(
        action_effect_typing=True,
        positive_effect_family_fairness=True,
    )
    _seed_discriminative_action_types(explorer)
    tokens = (ActionToken(1), ActionToken(2))

    first = explorer._select_positive_effect_family(tokens)  # noqa: SLF001
    second = explorer._select_positive_effect_family(tokens)  # noqa: SLF001

    assert first == ActionToken(1)
    assert second == ActionToken(2)
    assert explorer.positive_effect_family_selections == 2


def test_positive_effect_family_fairness_abstains_on_incomplete_typing() -> None:
    explorer = EpistemicExplorer(
        action_effect_typing=True,
        positive_effect_family_fairness=True,
    )
    _seed_discriminative_action_types(explorer)
    explorer.effect_typer.hypotheses.pop(ActionIdentity(2))

    selected = explorer._select_positive_effect_family(  # noqa: SLF001
        (ActionToken(1), ActionToken(2))
    )

    assert selected is None
    assert explorer.positive_effect_family_diagnostic == (
        "incomplete-positive-action-typing"
    )


def test_positive_effect_family_config_requires_effect_typing() -> None:
    with pytest.raises(
        ValueError,
        match="family fairness requires",
    ):
        MindConfig(enable_positive_effect_family_fairness=True)
