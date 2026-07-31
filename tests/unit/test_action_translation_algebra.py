from __future__ import annotations

import pytest

from reflector.core.action_translation_algebra import (
    ActionIdentity,
    ActionTranslationAlgebra,
    TranslationBounds,
    infer_dominant_translation,
)
from reflector.core.exploration import (
    ActionToken,
    EpistemicExplorer,
)
from reflector.core.mind import MindConfig
from reflector.core.perception import SceneTracker
from reflector.core.symbolic import Observation, Scene

type Frame = tuple[tuple[int, ...], ...]


def _frame(anchor: tuple[int, int], *, color: int = 2, nuisance: int = 0) -> Frame:
    grid = [[0 for _x in range(9)] for _y in range(7)]
    x, y = anchor
    for dx, dy in ((0, 0), (1, 0), (0, 1)):
        grid[y + dy][x + dx] = color
    if nuisance:
        grid[0][nuisance] = 8
    return tuple(tuple(row) for row in grid)


def _rotate_clockwise(frame: Frame) -> Frame:
    return tuple(tuple(row) for row in zip(*frame[::-1], strict=True))


def test_infers_translation_independent_of_absolute_position_and_color() -> None:
    first = infer_dominant_translation(_frame((1, 2)), _frame((3, 2)))
    recolored = infer_dominant_translation(
        _frame((4, 3), color=7),
        _frame((6, 3), color=7),
    )

    assert first.displacement == recolored.displacement == (2, 0)
    assert first.diagnostic == "unique-dominant-translation"


def test_translation_is_equivariant_under_frame_rotation() -> None:
    before = _frame((1, 2))
    after = _frame((3, 2))

    original = infer_dominant_translation(before, after)
    rotated = infer_dominant_translation(
        _rotate_clockwise(before),
        _rotate_clockwise(after),
    )

    assert original.displacement == (2, 0)
    assert rotated.displacement == (0, 2)


def test_one_transition_proposes_but_distinct_later_source_authorizes() -> None:
    learner = ActionTranslationAlgebra()
    action = ActionIdentity(3)

    proposal = learner.observe(
        sequence=0,
        action=action,
        before=_frame((1, 2)),
        after=_frame((3, 2)),
    )
    confirmation = learner.observe(
        sequence=1,
        action=action,
        before=_frame((2, 4), nuisance=1),
        after=_frame((4, 4), nuisance=1),
    )

    assert proposal.authority is None
    assert proposal.predicted_displacement is None
    assert confirmation.predicted_displacement == (2, 0)
    assert confirmation.authority is not None
    assert confirmation.authority.prospective_confirmations == 1
    assert confirmation.authority.distinct_source_states == 2


def test_same_structural_source_cannot_self_confirm() -> None:
    learner = ActionTranslationAlgebra()
    action = ActionIdentity(3)
    before = _frame((1, 2))
    after = _frame((3, 2))

    learner.observe(sequence=0, action=action, before=before, after=after)
    repeated = learner.observe(
        sequence=1,
        action=action,
        before=before,
        after=after,
    )

    assert repeated.authority is None
    assert repeated.predicted_displacement is None
    assert learner.confirmations == 0


def test_contextual_noop_does_not_destroy_a_translation_law() -> None:
    learner = ActionTranslationAlgebra()
    action = ActionIdentity(3)
    learner.observe(
        sequence=0,
        action=action,
        before=_frame((1, 2)),
        after=_frame((3, 2)),
    )
    learner.observe(
        sequence=1,
        action=action,
        before=_frame((2, 4), nuisance=1),
        after=_frame((4, 4), nuisance=1),
    )

    blocked = learner.observe(
        sequence=2,
        action=action,
        before=_frame((5, 1), nuisance=2),
        after=_frame((5, 1), nuisance=2),
    )

    assert blocked.diagnostic == "contextual-noop-preserves-hypothesis"
    assert blocked.authority is not None
    assert learner.contextual_noops == 1
    assert not learner.quarantined_actions


def test_conflicting_nonzero_effect_quarantines_action() -> None:
    learner = ActionTranslationAlgebra()
    action = ActionIdentity(3)
    learner.observe(
        sequence=0,
        action=action,
        before=_frame((1, 2)),
        after=_frame((3, 2)),
    )

    conflict = learner.observe(
        sequence=1,
        action=action,
        before=_frame((2, 4)),
        after=_frame((2, 2)),
    )

    assert conflict.quarantined
    assert conflict.diagnostic == "conflicting-nonzero-translation"
    assert learner.authoritative_laws() == ()


def test_inverse_pairs_are_derived_only_from_authoritative_laws() -> None:
    learner = ActionTranslationAlgebra()
    right = ActionIdentity(4)
    left = ActionIdentity(3)
    pairs = (
        (_frame((1, 2)), _frame((3, 2))),
        (
            _frame((2, 4), nuisance=1),
            _frame((4, 4), nuisance=1),
        ),
    )
    for sequence, (before, after) in enumerate(pairs):
        learner.observe(
            sequence=sequence,
            action=right,
            before=before,
            after=after,
        )
        learner.observe(
            sequence=sequence + 2,
            action=left,
            before=after,
            after=before,
        )

    assert learner.inverse_pairs() == ((left, right),)


def test_caps_fail_closed_and_stay_sticky() -> None:
    learner = ActionTranslationAlgebra(
        TranslationBounds(max_frame_cells=32),
    )
    action = ActionIdentity(1)

    first = learner.observe(
        sequence=0,
        action=action,
        before=_frame((1, 2)),
        after=_frame((3, 2)),
    )
    second = learner.observe(
        sequence=1,
        action=action,
        before=((0, 0), (0, 2)),
        after=((0, 0), (2, 0)),
    )

    assert first.cap_failure == "frame-cell-cap-exceeded"
    assert second.cap_failure == "frame-cell-cap-exceeded"


def test_ambiguous_equal_support_abstains() -> None:
    before = (
        (0, 0, 0, 0, 0, 0, 0),
        (0, 2, 0, 0, 0, 3, 0),
        (0, 0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0, 0),
    )
    after = (
        (0, 0, 0, 0, 0, 0, 0),
        (0, 0, 2, 0, 3, 0, 0),
        (0, 0, 0, 0, 0, 0, 0),
        (0, 0, 0, 0, 0, 0, 0),
    )

    result = infer_dominant_translation(before, after)

    assert result.displacement is None
    assert result.diagnostic == "ambiguous-dominant-translation"


def test_oversized_substrate_is_omitted_without_raising_the_object_bound() -> None:
    before = (
        (0, 0, 0, 0, 0, 0, 0),
        (0, 9, 9, 9, 0, 0, 0),
        (0, 9, 9, 9, 0, 0, 0),
        (0, 9, 9, 9, 0, 0, 0),
        (0, 0, 0, 0, 0, 2, 0),
        (0, 0, 0, 0, 0, 0, 0),
    )
    after = (
        (0, 0, 0, 0, 0, 0, 0),
        (0, 9, 9, 9, 0, 0, 0),
        (0, 9, 9, 9, 0, 0, 0),
        (0, 9, 9, 9, 0, 0, 0),
        (0, 0, 0, 0, 2, 0, 0),
        (0, 0, 0, 0, 0, 0, 0),
    )

    result = infer_dominant_translation(
        before,
        after,
        bounds=TranslationBounds(max_component_cells=8),
    )

    assert result.cap_failure is None
    assert result.omitted_oversized_components == 2
    assert result.displacement == (-1, 0)


def _observation(frame: Frame) -> tuple[Observation, Scene]:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3, 4),
        frame=frame,
    )
    scene, _events = SceneTracker().perceive(observation)
    return observation, scene


def test_explorer_integration_is_exact_off_and_traces_active_authority() -> None:
    off = EpistemicExplorer()
    first_observation, first_scene = _observation(_frame((1, 2)))
    off.observe(first_observation, first_scene)
    assert off.to_dict()["action_translation_observations"] == 0
    assert off.to_dict()["action_translation_last_diagnostic"] == "exact-off"

    active = EpistemicExplorer(action_translation_algebra=True)
    active.observe(first_observation, first_scene)
    token = ActionToken(3)
    assert active.current_state is not None
    active.selection_frame = _frame((1, 2))
    active._issue(  # noqa: SLF001
        active.current_state,
        token,
        "test-translation-proposal",
        first_scene,
    )
    first_after, first_after_scene = _observation(_frame((3, 2)))
    active.observe(first_after, first_after_scene)

    distinct_before = _frame((2, 4), nuisance=1)
    distinct_before_observation, distinct_before_scene = _observation(
        distinct_before
    )
    active.selection_frame = distinct_before
    assert active.current_state is not None
    active._issue(  # noqa: SLF001
        active.current_state,
        token,
        "test-translation-confirmation",
        distinct_before_scene,
    )
    distinct_after, distinct_after_scene = _observation(
        _frame((4, 4), nuisance=1)
    )
    active.observe(distinct_after, distinct_after_scene)

    metrics = active.to_dict()
    assert metrics["action_translation_observations"] == 2
    assert metrics["action_translation_predictions"] == 1
    assert metrics["action_translation_confirmations"] == 1
    assert metrics["action_translation_authority_events"] == 1
    assert metrics["action_translation_current_laws"] == 1
    assert metrics["action_translation_last_diagnostic"] == (
        "prospectively-confirmed-translation-law"
    )


def _seed_inverse_pair(explorer: EpistemicExplorer) -> None:
    right = ActionIdentity(2)
    left = ActionIdentity(3)
    for sequence, (before, after) in enumerate(
        (
            (_frame((1, 2)), _frame((3, 2))),
            (
                _frame((2, 4), nuisance=1),
                _frame((4, 4), nuisance=1),
            ),
        )
    ):
        explorer.translation_algebra.observe(
            sequence=sequence,
            action=right,
            before=before,
            after=after,
        )
        explorer.translation_algebra.observe(
            sequence=sequence + 2,
            action=left,
            before=after,
            after=before,
        )


def test_orbit_probe_runs_one_generator_until_contextual_noop() -> None:
    explorer = EpistemicExplorer(
        action_translation_algebra=True,
        action_translation_orbit_probe=True,
    )
    _seed_inverse_pair(explorer)
    before, before_scene = _observation(_frame((1, 2), nuisance=6))
    explorer.observe(before, before_scene)

    first = explorer.select(before, before_scene, (2, 3))
    assert first.token.action_id == 2
    moved, moved_scene = _observation(_frame((3, 2), nuisance=6))
    explorer.observe(moved, moved_scene)

    second = explorer.select(moved, moved_scene, (2, 3))
    assert second.token.action_id == 2
    explorer.observe(moved, moved_scene)

    after_block = explorer.select(moved, moved_scene, (2, 3))
    assert after_block.token.action_id == 3
    telemetry = explorer.to_dict()
    assert telemetry["action_translation_probe_completed_rays"] == 1
    assert telemetry["action_translation_probe_selections"] == 3


def test_orbit_probe_config_requires_translation_algebra() -> None:
    with pytest.raises(
        ValueError,
        match="orbit probing requires",
    ):
        MindConfig(enable_action_translation_orbit_probe=True)
