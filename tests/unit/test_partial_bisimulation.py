from reflector.core.exploration import ActionRole, ActionToken, EpistemicExplorer
from reflector.core.partial_bisimulation import PartialBisimulation
from reflector.core.symbolic import Scene


def _empty_scene() -> Scene:
    return Scene(
        index=0,
        state="NOT_FINISHED",
        levels_completed=0,
        available_actions=(1, 2),
        objects=(),
        facts=(),
        frame_digest="recipient",
    )


def test_shared_commuting_role_licenses_donor_only_prediction() -> None:
    model = PartialBisimulation()
    domain = (1, 2)
    model.observe(
        source="donor",
        domain=domain,
        role=("move",),
        outcome="relative-translation",
    )
    model.observe(
        source="donor",
        domain=domain,
        role=("click",),
        outcome="component-birth",
    )
    model.observe(
        source="recipient",
        domain=domain,
        role=("move",),
        outcome="relative-translation",
    )

    prediction = model.predict(
        source="recipient",
        domain=domain,
        role=("click",),
    )
    update = model.observe(
        source="recipient",
        domain=domain,
        role=("click",),
        outcome="component-birth",
    )

    assert prediction is not None
    assert prediction.outcome == "component-birth"
    assert update.confirmed
    assert model.confirmations == 1


def test_conflicting_shared_role_prevents_profile_transfer() -> None:
    model = PartialBisimulation()
    domain = (1, 2)
    model.observe(
        source="donor",
        domain=domain,
        role=("move",),
        outcome="relative-translation",
    )
    model.observe(
        source="donor",
        domain=domain,
        role=("click",),
        outcome="component-birth",
    )
    model.observe(
        source="recipient",
        domain=domain,
        role=("move",),
        outcome="render-noop",
    )

    assert (
        model.predict(
            source="recipient",
            domain=domain,
            role=("click",),
        )
        is None
    )


def test_conflicting_donor_outcomes_force_ambiguous_abstention() -> None:
    model = PartialBisimulation()
    domain = (1, 2)
    for state, click_outcome in (
        ("donor-a", "component-birth"),
        ("donor-b", "component-death"),
    ):
        model.observe(
            source=state,
            domain=domain,
            role=("move",),
            outcome="relative-translation",
        )
        model.observe(
            source=state,
            domain=domain,
            role=("click",),
            outcome=click_outcome,
        )
    model.observe(
        source="recipient",
        domain=domain,
        role=("move",),
        outcome="relative-translation",
    )

    prediction = model.predict(
        source="recipient",
        domain=domain,
        role=("click",),
    )

    assert prediction is not None
    assert prediction.ambiguous
    assert prediction.outcome is None


def test_frontier_reports_only_untried_uniquely_predicted_roles() -> None:
    model = PartialBisimulation()
    domain = (1, 2, 3)
    model.observe(
        source="donor",
        domain=domain,
        role=("move",),
        outcome="relative-translation",
    )
    model.observe(
        source="donor",
        domain=domain,
        role=("click",),
        outcome="component-birth",
    )
    model.observe(
        source="recipient",
        domain=domain,
        role=("move",),
        outcome="relative-translation",
    )

    frontier = model.frontier_predictions(
        source="recipient",
        domain=domain,
        roles=(("move",), ("click",), ("other",)),
    )

    assert tuple(item.role for item in frontier) == (("click",),)
    assert model.abstract_frontier_roles == 1


def test_control_trust_requires_eight_flawless_level_predictions() -> None:
    model = PartialBisimulation()
    model.level_predictions = 8
    model.level_confirmations = 8

    assert model.trusted_for_control()
    model.level_conflicts = 1
    assert not model.trusted_for_control()
    model.reset_level()
    assert not model.trusted_for_control()


def test_trusted_abstract_frontier_selects_positive_donor_only_role() -> None:
    explorer = EpistemicExplorer(
        partial_bisimulation=True,
        abstract_causal_frontier=True,
    )
    model = explorer.partial_bisimulation_model
    move = ActionRole(1)
    create = ActionRole(2)
    model.profiles = {
        "donor": {
            move: {"relative-translation"},
            create: {"component-birth"},
        },
        "recipient": {move: {"relative-translation"}},
    }
    model.domains = {"donor": (1, 2), "recipient": (1, 2)}
    model.level_predictions = 8
    model.level_confirmations = 8

    selected = explorer._select_abstract_causal_frontier(
        (0, "NOT_FINISHED", "recipient"),
        (ActionToken(1), ActionToken(2)),
        _empty_scene(),
    )

    assert selected == ActionToken(2)
    assert explorer.abstract_causal_frontier_selections == 1
    assert explorer.abstract_causal_frontier_diagnostic == (
        "selected-novel-predicted-effect:component-birth"
    )


def test_abstract_frontier_abstains_after_partition_conflict() -> None:
    explorer = EpistemicExplorer(
        partial_bisimulation=True,
        abstract_causal_frontier=True,
    )
    model = explorer.partial_bisimulation_model
    model.level_predictions = 8
    model.level_confirmations = 7
    model.level_conflicts = 1

    selected = explorer._select_abstract_causal_frontier(
        (0, "NOT_FINISHED", "recipient"),
        (ActionToken(1), ActionToken(2)),
        _empty_scene(),
    )

    assert selected is None
    assert explorer.abstract_causal_frontier_selections == 0
    assert explorer.abstract_causal_frontier_diagnostic == (
        "awaiting-flawless-bisimulation-evidence"
    )
