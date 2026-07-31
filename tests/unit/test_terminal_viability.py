from reflector.core.exploration import (
    ActionRole,
    ActionToken,
    EpistemicExplorer,
)
from reflector.core.perception import SceneTracker
from reflector.core.symbolic import Observation
from reflector.core.terminal_viability import TerminalEdgeViability


def _frame(
    point: tuple[int, int],
    *,
    color: int = 2,
    nuisance: tuple[int, int] | None = None,
) -> tuple[tuple[int, ...], ...]:
    rows = [[0] * 7 for _ in range(7)]
    rows[point[1]][point[0]] = color
    if nuisance is not None:
        rows[nuisance[1]][nuisance[0]] = color + 1
    return tuple(tuple(row) for row in rows)


def test_one_terminal_observation_cannot_authorize_avoidance() -> None:
    model = TerminalEdgeViability()
    frame = _frame((1, 2))

    update = model.observe(frame=frame, role=("move", 1), terminal=True)

    assert update.diagnostic == "proposed-terminal-edge"
    assert not update.authority
    assert not model.authoritative(frame, ("move", 1))


def test_distinct_concrete_source_prospectively_confirms_terminal_edge() -> None:
    model = TerminalEdgeViability()
    first = _frame((1, 2), color=2)
    translated_and_recolored = _frame((4, 3), color=7)

    model.observe(frame=first, role=("move", 1), terminal=True)
    update = model.observe(
        frame=translated_and_recolored,
        role=("move", 1),
        terminal=True,
    )

    assert update.diagnostic == "prospectively-confirmed-terminal-edge"
    assert update.authority
    assert model.authoritative(first, ("move", 1))


def test_duplicate_exact_source_does_not_confirm_terminal_edge() -> None:
    model = TerminalEdgeViability()
    frame = _frame((1, 2))

    model.observe(frame=frame, role=("move", 1), terminal=True)
    update = model.observe(frame=frame, role=("move", 1), terminal=True)

    assert update.diagnostic == "duplicate-concrete-terminal-source"
    assert not update.authority
    assert model.predictions == 0


def test_safe_counterexample_quarantines_aliased_terminal_edge() -> None:
    model = TerminalEdgeViability()
    first = _frame((1, 2), color=2)
    translated = _frame((4, 3), color=7)

    model.observe(frame=first, role=("move", 1), terminal=True)
    update = model.observe(
        frame=translated,
        role=("move", 1),
        terminal=False,
    )

    assert update.diagnostic == "safe-counterexample-quarantined-edge"
    assert update.quarantined
    assert not model.authoritative(first, ("move", 1))


def test_action_role_separates_otherwise_identical_scene_edges() -> None:
    model = TerminalEdgeViability()
    first = _frame((1, 2), color=2)
    translated = _frame((4, 3), color=7)

    model.observe(frame=first, role=("move", 1), terminal=True)
    update = model.observe(
        frame=translated,
        role=("move", 2),
        terminal=True,
    )

    assert update.diagnostic == "proposed-terminal-edge"
    assert not update.authority


def test_role_only_mode_ignores_scene_but_requires_distinct_frames() -> None:
    model = TerminalEdgeViability(role_only=True)
    first = _frame((1, 2), color=2)
    structurally_different = _frame((1, 2), color=2, nuisance=(6, 6))

    model.observe(frame=first, role=("click", "object-a"), terminal=True)
    update = model.observe(
        frame=structurally_different,
        role=("click", "object-a"),
        terminal=True,
    )

    assert update.authority
    assert model.authoritative(first, ("click", "object-a"))


def test_explorer_filters_only_authoritative_terminal_role() -> None:
    first = _frame((1, 2), color=2)
    translated = _frame((4, 3), color=7)
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=first,
    )
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(terminal_edge_viability_credit=True)
    explorer.terminal_viability.observe(
        frame=first,
        role=ActionRole(1),
        terminal=True,
    )
    explorer.terminal_viability.observe(
        frame=translated,
        role=ActionRole(1),
        terminal=True,
    )
    explorer.selection_frame = first

    filtered = explorer._viability_filtered_generic_tokens(
        (ActionToken(1), ActionToken(2)),
        scene,
    )

    assert filtered == (ActionToken(2),)
    assert explorer.terminal_viability_filtered_tokens == 1
    assert explorer.terminal_viability_filter_selections == 1


def test_exact_off_explorer_preserves_terminal_choice_domain() -> None:
    frame = _frame((1, 2), color=2)
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=frame,
    )
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer()
    tokens = (ActionToken(1), ActionToken(2))

    assert explorer._viability_filtered_generic_tokens(tokens, scene) == tokens
