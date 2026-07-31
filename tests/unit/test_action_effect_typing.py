from __future__ import annotations

from reflector.core.action_effect_typing import (
    ProspectiveActionEffectTyper,
    infer_action_effect,
)
from reflector.core.action_translation_algebra import ActionIdentity
from reflector.core.exploration import ActionToken, EpistemicExplorer
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
