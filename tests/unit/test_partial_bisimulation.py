from reflector.core.partial_bisimulation import PartialBisimulation


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
