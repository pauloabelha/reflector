from reflector import EpisodeTrace, SymbolicPolicy
from reflector.cli import demo_trace
from reflector.evaluation import compare_traces, evaluate_trace


def test_trace_round_trip_and_deterministic_replay() -> None:
    trace = demo_trace()
    encoded = trace.to_json()
    restored = EpisodeTrace.from_json(encoded)
    assert restored.to_json() == encoded
    replay = restored.replay(SymbolicPolicy)
    assert all(item["matches"] for item in replay)


def test_trace_metrics_and_variant_comparison() -> None:
    trace = demo_trace()
    metrics = evaluate_trace(trace)
    assert metrics.actions == 3
    assert metrics.transitions == 2
    assert metrics.action_efficiency == 1 / 3
    assert 0 <= metrics.prediction_accuracy <= 1
    assert metrics.schema_count >= 1
    assert metrics.schema_reuse >= 0
    assert metrics.concept_reuse >= 0
    assert metrics.duplicate_schemas >= 0
    assert metrics.contradictory_schemas >= 0
    assert metrics.dead_schemas >= 0
    assert metrics.orphan_concepts == 0
    assert metrics.deterministic_replay_rate == 1.0
    report = compare_traces({"baseline": trace, "descendant": trace})
    assert tuple(report) == ("baseline", "descendant")
