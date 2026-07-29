from reflector import (
    Atom,
    Event,
    SchemaPrediction,
    SchemaStore,
    StructuralCreditLedger,
    Transition,
)


def _transition(
    index: int,
    context: tuple[Atom, ...],
    result: tuple[Event, ...],
) -> Transition:
    return Transition(
        before_index=index,
        after_index=index + 1,
        context=context,
        action_id=1,
        action_data=(),
        result=result,
    )


def test_prediction_is_frozen_before_perturbation_is_learned() -> None:
    store = SchemaStore()
    learned_context = (Atom("mode", ("ordinary",)),)
    expected = (Event("object_moved", "piece", ("1", "0")),)
    store.observe(_transition(0, learned_context, expected))
    store.observe(_transition(1, learned_context, expected))

    perturbed_context = (
        Atom("mode", ("ordinary",)),
        Atom("barrier_present"),
    )
    prediction = store.predict(1, perturbed_context)
    assert prediction is not None
    assert prediction.transferred
    assert prediction.result == ("object_moved(piece,1,0)",)

    outcome = _transition(
        2,
        perturbed_context,
        (Event("no_observed_change"),),
    )
    ledger = StructuralCreditLedger()
    assessment_id = ledger.assess(outcome, prediction)
    assessment = ledger.assessments[assessment_id]

    assert assessment.contradicted == ("object_moved(piece,1,0)",)
    assert assessment.pragmatic == ()
    assert assessment.perturbation == ("barrier_present",)
    assert assessment.response == "differentiate"

    # Learning the outcome happens only after the forecast and assessment.
    store.observe(outcome)
    exact = store.predict(1, perturbed_context)
    assert exact is not None
    assert not exact.transferred
    assert exact.result == ("no_observed_change(scene)",)


def test_structural_eligibility_credits_named_propositions_not_return() -> None:
    prediction = SchemaPrediction(
        action_id=1,
        result=("gate_opened(gate)",),
        evidence=("schema-opener",),
        evidence_contexts=(("gate_present",),),
        support=3,
        confidence=0.8,
        transferred=False,
    )
    ledger = StructuralCreditLedger(max_trace_age=2)
    first = _transition(
        0,
        (Atom("gate_present"),),
        (Event("switch_changed", "switch"),),
    )
    ledger.assess(first, prediction)
    assert ledger.credited_structures == {}

    later = _transition(
        1,
        (Atom("gate_present"),),
        (Event("gate_opened", "gate"),),
    )
    ledger.assess(later, None)

    assert ledger.credited_structures == {
        "schema-opener": {"gate_opened(gate)": 1}
    }


def test_integration_requires_an_evidenced_conditional_family() -> None:
    prediction = SchemaPrediction(
        action_id=1,
        result=("object_moved(piece,1,0)",),
        evidence=("schema-motion",),
        evidence_contexts=(("mode(ordinary)",),),
        support=4,
        confidence=0.8,
        transferred=True,
    )
    ledger = StructuralCreditLedger()
    outcome = _transition(
        0,
        (Atom("mode", ("ordinary",)), Atom("barrier_present")),
        (Event("no_observed_change"),),
    )
    assessment_id = ledger.assess(outcome, prediction)

    assert ledger.integrate(()) == ()
    assert ledger.assessments[assessment_id].response == "differentiate"

    integrated = ledger.integrate(
        ((1, ("no_observed_change",), ("barrier_present",), 2),)
    )
    assert integrated == (assessment_id,)
    assert ledger.assessments[assessment_id].response == "integrate"


def test_repeated_disequilibrium_constructs_a_transferable_condition() -> None:
    prediction = SchemaPrediction(
        action_id=1,
        result=("level_advanced(scene)", "object_moved(piece,1,0)"),
        evidence=("schema-unblocked",),
        evidence_contexts=(("mode(ordinary)",),),
        support=4,
        confidence=0.8,
        transferred=True,
    )
    ledger = StructuralCreditLedger()
    for index, incidental in enumerate(("layout(a)", "layout(b)")):
        ledger.assess(
            _transition(
                index,
                (
                    Atom("mode", ("ordinary",)),
                    Atom("barrier_present"),
                    Atom.parse(incidental),
                ),
                (Event("no_observed_change"),),
            ),
            prediction,
        )

    assert ledger.last_constructed
    held_out = (
        Atom("mode", ("ordinary",)),
        Atom("barrier_present"),
        Atom("layout", ("held_out",)),
    )
    accommodated = ledger.accommodate_prediction(
        action_id=1,
        context=held_out,
        prediction=prediction,
    )

    assert accommodated is not None
    assert accommodated.transferred
    assert "level_advanced(scene)" not in accommodated.result
    assert "object_moved(piece,1,0)" not in accommodated.result
    assert accommodated.negated_predicates == (
        "level_advanced",
        "object_moved",
    )
    assert "no_observed_change" in accommodated.result
    assert any(
        item.condition == ("barrier_present",)
        for item in ledger.accommodations.values()
    )

    held_out_assessment = ledger.assess(
        _transition(
            4,
            held_out,
            (Event("no_observed_change"),),
        ),
        accommodated,
    )
    assessment = ledger.assessments[held_out_assessment]
    assert assessment.confirmed_absent == (
        "level_advanced",
        "object_moved",
    )
    assert assessment.contradicted_absent == ()
    assert not assessment.is_disequilibrium


def test_learned_negation_is_falsifiable_not_a_reward_penalty() -> None:
    prediction = SchemaPrediction(
        action_id=1,
        result=("no_observed_change(scene)",),
        evidence=("accommodation-barrier",),
        evidence_contexts=(("barrier_present",),),
        support=3,
        confidence=0.75,
        transferred=True,
        negated_predicates=("level_advanced", "object_moved"),
    )
    ledger = StructuralCreditLedger()
    assessment_id = ledger.assess(
        _transition(
            0,
            (Atom("barrier_present"), Atom("switch_on")),
            (Event("object_moved", "piece", ("1", "0")),),
        ),
        prediction,
    )
    assessment = ledger.assessments[assessment_id]

    assert assessment.confirmed_absent == ("level_advanced",)
    assert assessment.contradicted_absent == ("object_moved",)
    assert assessment.pragmatic == ()
    assert assessment.response == "differentiate"
    assert assessment.is_disequilibrium


def test_preregistered_hypothesis_credits_prediction_and_utility_separately() -> None:
    prediction = SchemaPrediction(
        action_id=1,
        result=("no_observed_change(scene)",),
        evidence=("schema-stable",),
        evidence_contexts=(("mode(stable)",),),
        support=4,
        confidence=0.8,
        transferred=False,
    )
    context = (Atom("mode", ("stable",)),)
    ledger = StructuralCreditLedger(
        pragmatic_disequilibrium_threshold=2
    )

    hypothesis_id = ledger.prime(
        before_index=0,
        action_id=1,
        context=context,
        prediction=prediction,
        scheme_components=("scheme:composed", "base:carry"),
    )
    primed = ledger.consume_primed(1)
    assert primed is not None
    first_id = ledger.assess(
        _transition(0, context, (Event("no_observed_change"),)),
        primed.prediction(),
        primed,
    )
    first = ledger.assessments[first_id]

    assert first.hypothesis_id == hypothesis_id
    assert first.confirmed == ("no_observed_change(scene)",)
    assert not first.is_disequilibrium
    assert first.scheme_components == ("base:carry", "scheme:composed")
    assert ledger.typed_credit["schema-stable"] == {
        "pragmatic_stagnation": 1,
        "predictive_support": 1,
    }

    ledger.prime(
        before_index=1,
        action_id=1,
        context=context,
        prediction=prediction,
        scheme_components=("scheme:composed",),
    )
    second = ledger.consume_primed(1)
    assert second is not None
    ledger.assess(
        _transition(1, context, (Event("no_observed_change"),)),
        second.prediction(),
        second,
    )

    assert ledger.pragmatic_disequilibrium
    assert ledger.consecutive_without_progress == 2
    assert ledger.typed_credit["schema-stable"][
        "predictive_support"
    ] == 2
    assert ledger.typed_credit["schema-stable"][
        "pragmatic_stagnation"
    ] == 2
    assert ledger.pragmatic_structure_scores()["scheme:composed"] == -2

    ledger.prime(
        before_index=2,
        action_id=1,
        context=context,
        prediction=prediction,
        scheme_components=("scheme:composed",),
    )
    progress = ledger.consume_primed(1)
    assert progress is not None
    ledger.assess(
        _transition(2, context, (Event("level_advanced"),)),
        progress.prediction(),
        progress,
    )
    assert not ledger.pragmatic_disequilibrium
    assert ledger.consecutive_without_progress == 0
    assert ledger.typed_credit["scheme:composed"]["pragmatic_progress"] == 1
