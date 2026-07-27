from reflector import (
    Atom,
    ConceptStore,
    DependencyGraph,
    Event,
    Goal,
    HypothesisStore,
    SchemaStore,
    SymbolicPlanner,
    Transition,
)


def _transition(index: int, action: int, event: Event) -> Transition:
    return Transition(
        before_index=index,
        after_index=index + 1,
        context=(Atom("state", ("NOT_FINISHED",)),),
        action_id=action,
        action_data=(),
        result=(event,),
    )


def test_causal_controls_temporal_hypothesis_and_experiment() -> None:
    schemas = SchemaStore()
    hypotheses = HypothesisStore()
    evidence = (
        _transition(0, 1, Event("button_activated", "o1")),
        _transition(1, 2, Event("door_opened", "o2")),
        _transition(2, 1, Event("button_activated", "o1")),
        _transition(3, 2, Event("door_opened", "o2")),
    )
    for item in evidence:
        schemas.observe(item)
        hypotheses.observe(item, schemas)

    causes = [
        item
        for item in hypotheses.causal.values()
        if item.action_id == 1 and item.effect == "button_activated"
    ]
    assert causes and causes[0].strength > 0
    assert causes[0].control_trials == 2
    assert any(
        item.antecedent == "button_activated"
        and item.consequent == "door_opened"
        for item in hypotheses.temporal.values()
    )
    experiments = hypotheses.experiments((1, 2, 3), schemas)
    assert experiments[0].action_id == 3
    assert experiments[0].expected_information_gain == 1.0


def test_bounded_planner_and_dependency_graph() -> None:
    schemas = SchemaStore()
    hypotheses = HypothesisStore()
    for index in range(3):
        item = _transition(index, 3, Event("level_advanced", "game"))
        schemas.observe(item)
        hypotheses.observe(item, schemas)

    planner = SymbolicPlanner(max_depth=2, max_expansions=8)
    plan = planner.plan(
        Goal("level_advanced"), (3, 4), schemas, hypotheses
    )
    assert plan is not None
    assert plan.actions == (3,)
    assert 0 < plan.expansions <= 8

    concepts = ConceptStore()
    concepts.reflect(schemas)
    graph = DependencyGraph.build(schemas, concepts, hypotheses)
    assert any(kind == "schema" for kind in graph.nodes.values())
    assert any(kind == "concept" for kind in graph.nodes.values())
    assert any(edge.relation == "supported_by" for edge in graph.edges)
