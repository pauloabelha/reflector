from reflector import (
    AbstractionStore,
    Atom,
    ConceptStore,
    DependencyGraph,
    Event,
    Goal,
    HypothesisStore,
    SchemaStore,
    SymbolicPlanner,
    SymbolicPolicy,
    Transition,
)
from reflector.evaluation import evaluate_trace
from reflector.perception import SceneTracker
from reflector.symbolic import Observation


def _observe(
    schemas: SchemaStore,
    *,
    index: int,
    context: tuple[Atom, ...],
    action: int,
    event: Event,
) -> None:
    schemas.observe(
        Transition(
            before_index=index,
            after_index=index + 1,
            context=context,
            action_id=action,
            action_data=(),
            result=(event,),
        )
    )


def test_scene_derives_bounded_typed_spatial_relations() -> None:
    tracker = SceneTracker()
    scene, _events = tracker.perceive(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(1,),
            frame=((2, 0, 3), (0, 0, 0), (4, 0, 0)),
        )
    )
    facts = {item.text() for item in scene.facts}
    assert "left_of(o1,o2)" in facts
    assert "above(o1,o3)" in facts
    assert "aligned_y(o1,o2)" in facts


def test_persistent_shape_transition_emits_rotation_event() -> None:
    tracker = SceneTracker()
    tracker.perceive(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(5,),
            frame=((2, 0, 0), (2, 2, 0), (0, 0, 0)),
        )
    )
    scene, events = tracker.perceive(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(5,),
            frame=((2, 2, 0), (2, 0, 0), (0, 0, 0)),
        )
    )
    assert scene.objects[0].shape
    assert Event("rotated_90", "o1") in events


def test_schema_family_retention_requires_positive_compression_utility() -> None:
    schemas = SchemaStore()
    event = Event("door_opened", "door")
    contexts = (
        (
            Atom("state", ("NOT_FINISHED",)),
            Atom("left_of", ("activator", "door")),
        ),
        (
            Atom("state", ("NOT_FINISHED",)),
            Atom("above", ("activator", "door")),
        ),
    )
    for index, context in enumerate(contexts):
        _observe(
            schemas,
            index=index,
            context=context,
            action=5,
            event=event,
        )
    store = AbstractionStore(complexity_pressure=0.25)
    created = store.reflect(schemas, ConceptStore())
    assert created
    family = next(iter(store.schema_families.values()))
    assert family.member_schemas == tuple(sorted(schemas.schemas))
    assert family.result_predicates == ("door_opened",)
    assert family.utility > 0
    assert family.compiled_description_length < family.raw_description_length


def test_concept_hierarchy_has_children_evidence_and_utility() -> None:
    schemas = SchemaStore()
    for index in range(4):
        _observe(
            schemas,
            index=index,
            context=(Atom("state", ("NOT_FINISHED",)),),
            action=1 if index < 2 else 2,
            event=Event(
                "object_moved",
                "piece",
                ("1", "0") if index < 2 else ("0", "1"),
            ),
        )
    concepts = ConceptStore()
    concepts.reflect(schemas)
    store = AbstractionStore(complexity_pressure=0.0)
    store.reflect(schemas, concepts)
    concept_type = next(iter(store.concept_types.values()))
    assert set(concept_type.children) == set(concepts.concepts)
    assert concept_type.evidence == concept_type.children
    assert concept_type.utility > 0


def test_orientation_language_operator_is_compositional_and_evidence_gated() -> None:
    schemas = SchemaStore()
    index = 0
    for angle in (90, 180, 270):
        for _repeat in range(6):
            _observe(
                schemas,
                index=index,
                context=(Atom("state", ("NOT_FINISHED",)),),
                action=5,
                event=Event(f"rotated_{angle}", "piece"),
            )
            index += 1
    store = AbstractionStore()
    created = store.reflect(schemas, ConceptStore())
    assert created
    operator = next(iter(store.language_operators.values()))
    assert operator.name == "orientation_delta"
    assert operator.replaces == ("rotated_180", "rotated_270", "rotated_90")
    assert operator.utility > 0
    assert operator.evidence
    assert store.language_history[-1].parent_id == "language-v1-primitives"
    assert store.language_history[-1].operators == (operator.operator_id,)
    graph = DependencyGraph.build(
        schemas, ConceptStore(), HypothesisStore(), store
    )
    assert graph.nodes[operator.operator_id] == "language_operator"
    assert any(
        edge.source == operator.operator_id
        and edge.relation == "compiled_from"
        for edge in graph.edges
    )


def test_deployed_policy_can_invent_orientation_operator_from_frames() -> None:
    shapes = (
        ((2, 0, 0), (2, 2, 0), (0, 0, 0)),
        ((2, 2, 0), (2, 0, 0), (0, 0, 0)),
        ((2, 2, 0), (0, 2, 0), (0, 0, 0)),
        ((0, 2, 0), (2, 2, 0), (0, 0, 0)),
    )
    sequence = (0, 1, 0, 2, 0, 3, 0) * 4
    policy = SymbolicPolicy()
    for shape_index in sequence:
        policy.choose_action(
            Observation.create(
                state="NOT_FINISHED",
                available_actions=(5,),
                frame=shapes[shape_index],
            )
        )
    operators = policy.mind.abstractions.language_operators
    assert operators
    operator = next(iter(operators.values()))
    assert operator.replaces == ("rotated_180", "rotated_270", "rotated_90")
    assert operator.utility > 0
    metrics = evaluate_trace(policy.trace)
    assert metrics.language_operator_count == 1
    assert metrics.abstraction_description_savings > 0
    assert any(
        event.kind == "orientation_delta"
        for step in policy.trace.steps
        if step.incoming_transition is not None
        for event in step.incoming_transition.result
    )


def test_retained_concept_becomes_a_later_schema_term() -> None:
    policy = SymbolicPolicy()
    for index in range(6):
        policy.choose_action(
            Observation.create(
                state="NOT_FINISHED",
                available_actions=(1,),
                frame=(
                    ((2, 0), (0, 0))
                    if index % 2 == 0
                    else ((0, 2), (0, 0))
                ),
            )
        )
    concept_id = next(
        concept.concept_id
        for concept in policy.mind.concepts.concepts.values()
        if "frame_changed(scene)" in concept.definition
    )
    compiled_schemas = [
        schema
        for schema in policy.mind.schemas.schemas.values()
        if Atom("synthetic_item", (concept_id,)) in schema.context
    ]
    assert compiled_schemas
    graph = policy.mind.snapshot()["dependency_graph"]
    assert {
        "source": compiled_schemas[0].schema_id,
        "relation": "uses",
        "target": concept_id,
    } in graph["edges"]


def test_schema_family_reliability_is_reused_by_bounded_planner() -> None:
    schemas = SchemaStore()
    for index, relation in enumerate(("left_of", "above")):
        _observe(
            schemas,
            index=index,
            context=(
                Atom("state", ("NOT_FINISHED",)),
                Atom(relation, ("switch", "exit")),
            ),
            action=3,
            event=Event("level_advanced", "game"),
        )
    abstractions = AbstractionStore(complexity_pressure=0.0)
    abstractions.reflect(schemas, ConceptStore())
    family = next(iter(abstractions.schema_families.values()))
    planner = SymbolicPlanner()
    plan = planner.plan(
        goal=Goal("level_advanced"),
        legal_actions=(3, 4),
        schemas=schemas,
        hypotheses=HypothesisStore(),
        abstractions=abstractions,
    )
    assert plan is not None
    assert plan.actions == (3,)
    assert plan.confidence == family.reliability


def test_repeated_successful_sequence_becomes_an_executable_procedure() -> None:
    schemas = SchemaStore()
    abstractions = AbstractionStore()
    contexts = tuple(
        (
            Atom("state", ("NOT_FINISHED",)),
            Atom("object_count", (str(stage + 1),)),
            Atom(
                "object_signature",
                ("2", str(stage + 1), str(stage), "0", "1", "1"),
            ),
        )
        for stage in range(3)
    )
    created: tuple[str, ...] = ()
    index = 0
    for _repeat in range(2):
        for stage, (context, action) in enumerate(
            zip(contexts, (1, 2, 3), strict=True)
        ):
            transition = Transition(
                before_index=index,
                after_index=index + 1,
                context=context,
                action_id=action,
                action_data=(),
                result=(
                    Event("level_advanced", "game")
                    if stage == 2
                    else Event("frame_changed")
                ,),
            )
            schema = schemas.observe(transition)
            created = (
                *created,
                *abstractions.observe_procedure(
                    transition, schema.schema_id, max_steps=3
                ),
            )
            index += 1

    assert created
    procedure = next(iter(abstractions.procedures.values()))
    assert procedure.actions == (1, 2, 3)
    assert procedure.support == 2
    assert procedure.evidence
    assert procedure.utility > 0
    moved_context = (
        Atom("state", ("NOT_FINISHED",)),
        Atom("object_count", ("2",)),
        Atom("object_signature", ("2", "2", "9", "9", "1", "1")),
    )
    match = abstractions.procedure_match(moved_context, (1, 2, 3))
    assert match is not None
    assert match[0] == (2, 3)
    graph = DependencyGraph.build(
        schemas, ConceptStore(), HypothesisStore(), abstractions
    )
    assert graph.nodes[procedure.procedure_id] == "procedure"
    assert any(
        edge.source == procedure.procedure_id
        and edge.relation == "compiled_from"
        for edge in graph.edges
    )
