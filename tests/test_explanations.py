from __future__ import annotations

from copy import deepcopy

import pytest

from reflector2.explanation_experiment import ordered_process_map
from reflector2.explanations import ExplanationConfig, ExplanationEngine
from reflector2.perception import PerceptionBatch
from reflector2.runtime import REFUTED, REIFIED, SHADOW, Runtime


def _batch(
    runtime: Runtime, context: str, *, count: int, extra: bool = True
) -> PerceptionBatch:
    terms = runtime.graph.terms
    region = terms.intern_symbol(f"region:{context}")
    form = terms.intern_symbol("form:shared")
    facts = [
        terms.ground_atom("Form", (f"region:{context}", "form:shared")),
        terms.ground_atom("Count", (f"region:{context}", count)),
    ]
    if extra:
        facts.append(terms.ground_atom("CurrentRelation", (f"anchor:{context}",)))
    return PerceptionBatch(
        context=context,
        facts=tuple(facts),
        form_terms=(form,),
        region_terms=(region,),
        outline_terms=(),
        source="test",
    )


def _fixture(*, max_explanations: int = 8):
    runtime = Runtime()
    context_schema, _created = runtime.graph.add_schema(
        "CurrentRelation",
        [("CurrentRelation", ("?x",))],
        candidate=False,
        provenance="test:active-frontier",
    )
    current = _batch(runtime, "current", count=1)
    workspace = runtime.observe(current, compose=False)
    before = _batch(runtime, "before", count=1)
    preserved = _batch(runtime, "preserved", count=1)
    changed = _batch(runtime, "changed", count=2)
    preserve_schema = runtime.learn_transition(
        before,
        preserved,
        "arc-action:1",
        predecessor_schema_ids=(context_schema,),
    )
    change_schema = runtime.learn_transition(
        before,
        changed,
        "arc-action:1",
        predecessor_schema_ids=(context_schema,),
    )
    assert preserve_schema in workspace.activation
    assert change_schema in workspace.activation
    engine = ExplanationEngine(
        runtime, ExplanationConfig(max_explanations=max_explanations)
    )
    return runtime, engine, workspace, current, before, preserved, changed, preserve_schema, change_schema


def _isolation_probe(value: int) -> tuple[int, int, tuple[str, ...]]:
    runtime = Runtime()
    initial = runtime.graph.schema_count
    runtime.graph.add_schema(
        "IsolationProbe",
        [("Probe", (f"job-{value}",))],
        candidate=False,
        provenance="test:worker-isolation",
    )
    return (
        initial,
        runtime.graph.schema_count,
        tuple(runtime.graph.canonical_hash[:initial]),
    )


def test_predictions_are_projected_before_successor_and_resolve_as_normal_shadows() -> None:
    (
        runtime,
        engine,
        workspace,
        current,
        before,
        _preserved,
        changed,
        _preserve_schema,
        change_schema,
    ) = _fixture()
    schema_count = runtime.graph.schema_count
    decision = engine.decide(
        mode="explanation",
        workspace=workspace,
        observed=current,
        legal_action_ids=(1, 2),
        baseline_action_id=2,
    )

    assert decision.selected_action_id == 1
    assert decision.changed_top_action
    assert decision.shadow_by_explanation
    assert runtime.graph.schema_count == schema_count
    assert all(
        runtime.shadows[shadow_id].status == SHADOW
        for shadow_id in decision.shadow_by_explanation.values()
    )

    trace = engine.observe_outcome(
        decision,
        before=before,
        after=changed,
        observed_schema_id=change_schema,
        progress_delta=1,
        reward=1.0,
    )
    assert trace is not None
    statuses = {
        runtime.shadows[shadow_id].status
        for shadow_id in decision.shadow_by_explanation.values()
    }
    assert statuses == {REIFIED, REFUTED}
    assert trace["ambiguity_reduced"]
    assert engine.metrics.shadows_reified == 1
    assert engine.metrics.shadows_refuted == 1

    next_decision = engine.decide(
        mode="explanation",
        workspace=workspace,
        observed=current,
        legal_action_ids=(1, 2),
        baseline_action_id=2,
    )
    learned_prediction = next(
        prediction
        for prediction in next_decision.predictions
        if prediction.schema_id == change_schema
    )
    assert learned_prediction.progress == 1.0


def test_construction_is_bounded_and_dormant_schemas_do_not_enter_candidates() -> None:
    runtime, engine, workspace, current, *_rest = _fixture(max_explanations=1)
    active_before = tuple(sorted(workspace.activation))
    for index in range(200):
        runtime.graph.add_schema(
            f"Dormant{index}",
            [(f"DormantHead{index}", (f"constant-{index}",))],
            candidate=False,
            provenance="test:dormant",
        )
    assert tuple(sorted(workspace.activation)) == active_before

    explanations = engine.construct(workspace, (1, 2))
    assert len(explanations) == 1
    assert engine.metrics.active_counts[-1] == 1
    assert all(
        "Dormant" not in runtime.graph.display_name[schema_id]
        for explanation in explanations
        for schema_id in explanation.constituent_schema_ids
    )


def test_decision_inputs_and_trace_exclude_game_level_and_coordinate_semantics() -> None:
    runtime, engine, workspace, current, *_rest = _fixture()
    contaminated_context = PerceptionBatch(
        context="arc:secret-game:level:99:x:12:y:7",
        facts=current.facts,
        form_terms=current.form_terms,
        region_terms=current.region_terms,
        outline_terms=current.outline_terms,
        source=current.source,
    )
    decision = engine.decide(
        mode="explanation",
        workspace=workspace,
        observed=contaminated_context,
        legal_action_ids=(1, 2),
        baseline_action_id=2,
    )
    serialized = repr(engine.decision_trace(decision)).lower()
    assert "secret-game" not in serialized
    assert "level:99" not in serialized
    assert "x:12" not in serialized
    assert "y:7" not in serialized
    assert all(
        runtime.shadows[shadow].carrier.startswith("explanation-decision:")
        for shadow in decision.shadow_by_explanation.values()
    )


def test_local_schema_ranking_has_no_explanation_commitments() -> None:
    runtime, engine, workspace, current, *_rest = _fixture()
    before = deepcopy(runtime.graph.source_atoms(0))
    decision = engine.decide(
        mode="local-schema",
        workspace=workspace,
        observed=current,
        legal_action_ids=(1, 2),
        baseline_action_id=2,
    )
    assert decision.selected_action_id == 1
    assert not decision.explanation_ids
    assert not decision.shadow_by_explanation
    assert runtime.graph.source_atoms(0) == before


def test_parallel_game_mapping_is_isolated_ordered_and_deterministic() -> None:
    jobs = [3, 1, 4, 2]
    serial = ordered_process_map(_isolation_probe, jobs, 1)
    parallel = ordered_process_map(_isolation_probe, jobs, 2)
    assert parallel == serial
    assert all(final == initial + 1 for initial, final, _kernel in parallel)
    assert len({kernel for _initial, _final, kernel in parallel}) == 1


@pytest.mark.parametrize(
    "kwargs",
    (
        {"max_explanations": 0},
        {"max_explanations": 65},
        {"max_constituents": 0},
        {"max_constituents": 17},
        {"retire_after_refutations": 0},
    ),
)
def test_explanation_config_rejects_unbounded_or_empty_limits(kwargs) -> None:
    with pytest.raises(ValueError):
        ExplanationConfig(**kwargs)
