from reflector.cli import demo_trace
from reflector.compression import analyze_redundancy, counterfactual_replay
from reflector.evaluation import ABLATIONS, evaluate_ablations


def test_recoverable_redundancy_and_counterfactual_utility() -> None:
    trace = demo_trace()
    report = analyze_redundancy(trace)
    assert report.repeated_rediscoveries >= 1
    assert report.recoverable_redundancy >= 1
    results = counterfactual_replay(trace)
    assert results
    assert all(result.action_savings == 0 for result in results)
    assert any(result.accepted and result.net_utility > 0 for result in results)


def test_named_ablation_matrix_runs() -> None:
    results = evaluate_ablations(demo_trace())
    assert set(results) == set(ABLATIONS)
    assert results["no_synthetic_concepts"]["concept_count"] == 0
    assert results["full"]["deterministic_replay_rate"] == 1.0
