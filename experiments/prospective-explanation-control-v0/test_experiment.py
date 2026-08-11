from __future__ import annotations

import importlib.util
import sys
from dataclasses import replace
from pathlib import Path

from reflector2.explanations import (
    ActionRank,
    ExplanationDecision,
    ExplanationEngine,
    ProspectivePrediction,
)
from reflector2.perception import PerceptionBatch
from reflector2.runtime import Runtime, Workspace


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "prospective_explanation_control_v0", HERE / "experiment.py"
)
assert SPEC is not None and SPEC.loader is not None
EXP = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXP
SPEC.loader.exec_module(EXP)


def _record(
    action: int,
    *,
    progress: int = 0,
    failure: int = 0,
    signature=(('Change', ('Form',)),),
    explanation: int = 1,
):
    return EXP.ConsequenceRecord(
        explanation_id=explanation,
        source_schema_id=action,
        source_schema_hash=f"source-{action}",
        action_id=action,
        predicted_effects=signature,
        consequence_schema_ids=(10 + action,),
        consequence_schema_hashes=(f"consequence-{action}",),
        progress_support=progress,
        failure_support=failure,
        truncated=False,
    )


def _config(**changes):
    base = EXP.ExperimentConfig(
        seed=0,
        beam_size=8,
        max_consequences_per_explanation=16,
        max_expansions_per_decision=128,
        max_executed_overrides_per_game=8,
        max_packets_per_game=40,
    )
    return replace(base, **changes)


def _engine_fixture():
    runtime = Runtime()
    schema_id, _created = runtime.graph.add_schema(
        "OpaqueTransition",
        [
            ("Domain", ("?before",)),
            ("Codomain", ("?after",)),
            ("Intervention", ("arc-action:1",)),
            ("Change", ("Form",)),
        ],
        provenance="test",
    )
    runtime.workspace = Workspace("before", {schema_id: 1.0}, [], set())
    engine = ExplanationEngine(runtime)
    observed = PerceptionBatch("before", (), (), ())
    return runtime, engine, schema_id, observed


def test_frozen_games_equal_the_mechanical_pre_treatment_selection() -> None:
    EXP.verify_frozen_selection()


def test_no_prospective_evidence_exactly_preserves_baseline_order() -> None:
    ranks, distinct = EXP.rank_from_records((1, 2, 3), (3, 1, 2), ())
    assert not distinct
    assert [rank.action_id for rank in ranks] == [3, 1, 2]
    assert all(rank.score_tuple == (0, 0, 0, 0) for rank in ranks)


def test_equivalent_futures_fall_back_to_baseline() -> None:
    records = (_record(1, progress=1), _record(2, progress=1))
    ranks, distinct = EXP.rank_from_records((1, 2), (2, 1), records)
    assert not distinct
    assert [rank.action_id for rank in ranks] == [2, 1]


def test_progress_and_failure_consequences_can_override_without_weights() -> None:
    records = (
        _record(1, failure=1, signature=(("Preserve", ("Form",)),)),
        _record(2, progress=1, signature=(("Change", ("Form",)),)),
    )
    ranks, distinct = EXP.rank_from_records((1, 2), (1, 2), records)
    assert distinct
    assert ranks[0].action_id == 2
    assert ranks[0].score_tuple == (1, 0, 0, 1)


def test_unsupported_action_cannot_win_from_a_zero_tuple() -> None:
    runtime, engine, source, observed = _engine_fixture()
    signature = engine._effect_signature(source)
    prediction = ProspectivePrediction(0, source, 1, signature, 1.0, 0.0, 0.0)
    baseline = ExplanationDecision(
        1,
        "explanation",
        1,
        1,
        (
            ActionRank(1, -1.0, 0.0, 0.0, 1.0, 1.0, 1, False),
            ActionRank(2, 0.0, 0.0, 0.0, 0.0, 0.0, 0, True),
        ),
        (prediction,),
        (0,),
        {},
        False,
        False,
    )
    result = EXP.prospective_decision(engine, baseline, (1, 2), _config())
    assert result["selected"] == 1
    assert result["abstained"]


def test_baseline_decision_uses_a_runtime_copy_and_cannot_contaminate_live_state() -> None:
    runtime, engine, _schema, observed = _engine_fixture()
    graph_before = (
        runtime.graph.schema_count,
        tuple(runtime.graph.canonical_hash),
        tuple(runtime.graph.support),
        tuple(runtime.graph.projection_support),
        tuple(runtime.graph.projection_failure),
    )
    shadows_before = dict(runtime.shadows)
    decision = EXP._baseline_decision(engine, observed, (1,), 1)
    assert decision.selected_action_id == 1
    assert (
        runtime.graph.schema_count,
        tuple(runtime.graph.canonical_hash),
        tuple(runtime.graph.support),
        tuple(runtime.graph.projection_support),
        tuple(runtime.graph.projection_failure),
    ) == graph_before
    assert runtime.shadows == shadows_before
    assert engine.runtime is runtime


def test_held_out_successor_has_no_input_path_to_ranking() -> None:
    runtime_a, engine_a, _schema_a, observed_a = _engine_fixture()
    runtime_b, engine_b, _schema_b, observed_b = _engine_fixture()
    decision_a = EXP._baseline_decision(engine_a, observed_a, (1,), 1)
    # A hypothetical successor exists only in this test variable; neither arm
    # accepts it as an argument at the decision boundary.
    held_out_successor = PerceptionBatch("future", ((999, (1,)),), (), ())
    assert held_out_successor.context == "future"
    decision_b = EXP._baseline_decision(engine_b, observed_b, (1,), 1)
    assert engine_a.decision_trace(decision_a) == engine_b.decision_trace(decision_b)
    assert runtime_a.cycle == runtime_b.cycle


def test_expansion_budget_is_hard_and_traced() -> None:
    runtime, engine, source, _observed = _engine_fixture()
    signature = engine._effect_signature(source)
    for index in range(8):
        schema_id, _created = runtime.graph.add_schema(
            f"Consequence{index}",
            [
                ("Domain", ("?before",)),
                ("Codomain", ("?after",)),
                ("Intervention", (f"arc-action:{index % 2 + 1}",)),
                ("Before", ("?before", f"Relation{index}", "?value")),
                ("After", ("?after", f"Relation{index}", "?value")),
                ("Change", ("Form",)),
            ],
            provenance="test",
        )
        runtime.workspace.activation[schema_id] = 1.0
    prediction = ProspectivePrediction(0, source, 1, signature, 1.0, 0.0, 0.0)
    decision = ExplanationDecision(
        1,
        "explanation",
        1,
        1,
        (ActionRank(1, 0.0, 0.0, 0.0, 0.0, 0.0, 1, False),),
        (prediction,),
        (0,),
        {},
        False,
        False,
    )
    records, reasons, expansions = EXP.build_consequence_records(
        engine, decision, (1, 2), _config(max_expansions_per_decision=2)
    )
    assert expansions == 2
    assert "expansion-budget" in reasons
    assert records[0].truncated


def test_scoring_records_contain_only_opaque_action_and_existing_ids() -> None:
    record = _record(2, progress=1)
    serialized = repr(EXP.rank_from_records((1, 2), (1, 2), (record,))).lower()
    assert all(word not in serialized for word in EXP.PROHIBITED)


def test_repeated_pure_ranking_is_structure_identical() -> None:
    records = (
        _record(1, progress=2, explanation=1),
        _record(1, progress=1, explanation=2),
        _record(2, failure=2),
    )
    assert EXP.rank_from_records((1, 2), (2, 1), records) == EXP.rank_from_records(
        (1, 2), (2, 1), records
    )


def test_progress_checkpoint_is_atomic_keyed_and_reloadable(tmp_path: Path) -> None:
    path = tmp_path / "progress.pickle"
    EXP._atomic_pickle(path, {"key": "frozen", "state": {"packet": 15}})
    assert EXP._load_progress(path, "frozen") == {"packet": 15}
    assert EXP._load_progress(path, "different-config") is None
    assert not list(tmp_path.glob(".*.tmp"))
