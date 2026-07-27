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
