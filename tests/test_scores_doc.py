import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_scores_headline_matches_authoritative_winner() -> None:
    summary = json.loads(
        (
            ROOT
            / "experiments"
            / "parallel-cognitive-workspace-v1-16"
            / "artifacts"
            / "SUMMARY.json"
        ).read_text()
    )
    results = {result["arm_id"]: result for result in summary["results"]}
    shared = results["shared_live_qwen"]
    control = results["r2_only"]
    scores = (ROOT / "SCORES.md").read_text()

    assert summary["binary_gate"]["verdict"] == "PASS"
    assert shared["levels_completed"] == 1
    assert control["levels_completed"] == 0
    assert f"**L1@{shared['actions']}**" in scores
    assert f"L0@{control['actions']}" in scores
    assert "has **not yet been submitted to Kaggle**" in scores


def test_scores_development_matrix_matches_all_public_artifacts() -> None:
    result_root = (
        ROOT
        / "experiments"
        / "autonomous-progress-synthesis-v0"
        / "artifacts"
        / "online-registry-development"
    )
    results = [json.loads(path.read_text()) for path in result_root.glob("*/RESULT.json")]
    scores = (ROOT / "SCORES.md").read_text()

    assert len(results) == 25
    assert sum(result["levels_completed"] >= 1 for result in results) == 16
    assert all(result["exact_replay"] for result in results)
    for result in results:
        label = f"L{result['levels_completed']}@{result['actions']}"
        assert f"| {result['game']} |" in scores
        assert label in scores
