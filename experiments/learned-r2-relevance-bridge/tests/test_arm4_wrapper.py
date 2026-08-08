from __future__ import annotations

import sys
from pathlib import Path


EXPERIMENT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(EXPERIMENT))

from relevance import EvidenceRecord, train_snapshot  # noqa: E402
from run_experiment import Arm4Controller  # noqa: E402
from reflector2.explanations import ExplanationConfig, ExplanationEngine  # noqa: E402
from reflector2.perception import PerceptionBatch  # noqa: E402
from reflector2.runtime import Runtime  # noqa: E402


def batch(runtime: Runtime, context: str, count: int) -> PerceptionBatch:
    terms = runtime.graph.terms
    region = terms.intern_symbol(f"region:{context}")
    form = terms.intern_symbol("form:shared")
    return PerceptionBatch(
        context=context,
        facts=(
            terms.ground_atom("Form", (f"region:{context}", "form:shared")),
            terms.ground_atom("Count", (f"region:{context}", count)),
            terms.ground_atom("CurrentRelation", (f"anchor:{context}",)),
        ),
        form_terms=(form,),
        region_terms=(region,),
        outline_terms=(),
        source="test",
    )


def runtime_fixture() -> tuple[Runtime, PerceptionBatch]:
    runtime = Runtime()
    context_schema, _ = runtime.graph.add_schema(
        "CurrentRelation",
        [("CurrentRelation", ("?x",))],
        candidate=False,
        provenance="test:active",
    )
    current = batch(runtime, "current", 1)
    workspace = runtime.observe(current, compose=False)
    before = batch(runtime, "before", 1)
    runtime.learn_transition(
        before,
        batch(runtime, "preserved", 1),
        "arc-action:1",
        predecessor_schema_ids=(context_schema,),
    )
    runtime.learn_transition(
        before,
        batch(runtime, "changed", 2),
        "arc-action:2",
        predecessor_schema_ids=(context_schema,),
    )
    assert workspace is runtime.workspace
    return runtime, current


def relevance_snapshot():
    preserve = (("Preserve", ("Count",)),)
    return train_snapshot(
        (
            EvidenceRecord(
                1,
                "learn-1",
                "context-1",
                "trajectory",
                "stratum",
                "binding-1",
                preserve,
                1,
            ),
            EvidenceRecord(
                2,
                "learn-2",
                "context-2",
                "trajectory",
                "stratum",
                "binding-2",
                preserve,
                1,
            ),
        )
    )


def test_arm4_uses_frozen_explanation_ranking_then_commits_executed_action() -> None:
    ordinary_runtime, ordinary_current = runtime_fixture()
    ordinary = ExplanationEngine(ordinary_runtime, ExplanationConfig())
    ordinary_decision = ordinary.decide(
        mode="explanation",
        workspace=ordinary_runtime.workspace,
        observed=ordinary_current,
        legal_action_ids=(1, 2),
        baseline_action_id=1,
    )

    arm4_runtime, arm4_current = runtime_fixture()
    controller = Arm4Controller(
        arm4_runtime,
        relevance_snapshot(),
        ExplanationConfig(),
        "report-only-group",
    )
    decision = controller.decide(
        mode="explanation",
        workspace=arm4_runtime.workspace,
        observed=arm4_current,
        legal_action_ids=(1, 2),
        baseline_action_id=1,
    )

    assert decision.frozen_explanation.rankings == ordinary_decision.rankings
    assert (
        decision.frozen_explanation.selected_action_id
        == ordinary_decision.selected_action_id
    )
    assert decision.executed_explanation.selected_action_id == decision.selected_action_id
    assert decision.relevance.changed_from_explanation
    committed_actions = {
        prediction.action_id
        for prediction in decision.executed_explanation.predictions
        if prediction.explanation_id
        in decision.executed_explanation.shadow_by_explanation
    }
    assert committed_actions <= {decision.selected_action_id}

    after = batch(arm4_runtime, "after", 1)
    arm4_runtime.observe(after, compose=False)
    observed_schema = arm4_runtime.learn_transition(
        arm4_current,
        after,
        f"arc-action:{decision.selected_action_id}",
    )
    resolution = controller.observe_outcome(
        decision,
        before=arm4_current,
        after=after,
        observed_schema_id=observed_schema,
        progress_delta=1,
        reward=1.0,
    )
    assert resolution is not None
    assert resolution["learned_relevance"] is not None
    assert {
        item["status"]
        for item in resolution["learned_relevance"]["resolutions"]
    } == {"REIFIED"}


def test_arm4_trace_contains_no_report_group_in_ranking_provenance() -> None:
    runtime, current = runtime_fixture()
    controller = Arm4Controller(
        runtime,
        relevance_snapshot(),
        ExplanationConfig(),
        "secret-game-id-used-for-reporting-only",
    )
    decision = controller.decide(
        mode="explanation",
        workspace=runtime.workspace,
        observed=current,
        legal_action_ids=(1, 2),
        baseline_action_id=1,
    )
    assert "secret-game-id" not in repr(controller.decision_trace(decision))
