import json
import subprocess
import sys
from pathlib import Path


def test_official_run_emits_machine_readable_score_and_metrics(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[2]
    fixture = root / "tests" / "fixtures" / "official_toolkit"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "reflector.cli",
            "official-run",
            "bt11",
            "--environments-dir",
            str(fixture),
            "--recordings-dir",
            str(tmp_path / "recordings"),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert report["scorecard"]["score"] == 100.0
    assert report["agents"][0]["levels_completed"] == 5
    assert report["agents"][0]["trace_metrics"]["prediction_accuracy"] >= 0
    assert report["agents"][0]["trace_metrics"]["action_efficiency"] > 0
    assert report["agents"][0]["mind_config"]["enable_comparison_composition"]
    assert sum(report["agents"][0]["action_counts"].values()) == 72
    assert (
        sum(item["count"] for item in report["agents"][0]["decision_distribution"])
        == 72
    )
    assert sum(report["agents"][0]["reason_counts"].values()) == 72
    assert sum(report["agents"][0]["reason_detail_counts"].values()) == 72
    assert report["agents"][0]["exploration_metrics"]["states"] > 0
    assert len(report["source_commit"]) == 40


def test_official_run_lightweight_without_recordings(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[2]
    fixture = root / "tests" / "fixtures" / "official_toolkit"
    recordings = tmp_path / "recordings"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "reflector.cli",
            "official-run",
            "bt11",
            "--environments-dir",
            str(fixture),
            "--recordings-dir",
            str(recordings),
            "--no-recordings",
            "--lightweight",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert report["scorecard"]["score"] == 100.0
    assert "trace_metrics" not in report["agents"][0]
    assert sum(report["agents"][0]["action_counts"].values()) == 72
    assert report["agents"][0]["exploration_metrics"]["states"] > 0
    assert not list(recordings.glob("*.recording.jsonl"))


def test_public_run_refuses_incomplete_environment_inventory(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[2]
    fixture = root / "tests" / "fixtures" / "official_toolkit"
    output = tmp_path / "public-report.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "reflector.cli",
            "official-public-run",
            "--environments-dir",
            str(fixture),
            "--recordings-dir",
            str(tmp_path / "recordings"),
            "--output",
            str(output),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == 2
    assert "expected 25 unique games, found 1" in completed.stderr
    assert not output.exists()
