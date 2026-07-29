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
    cognitive_streams = tmp_path / "cognitive-streams"
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
            "--cognitive-stream-dir",
            str(cognitive_streams),
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
    stream_files = list(cognitive_streams.glob("*.cognitive.jsonl"))
    assert len(stream_files) == 1
    events = [
        json.loads(line)
        for line in stream_files[0].read_text(encoding="utf-8").splitlines()
    ]
    assert len(events) == report["agents"][0]["actions"]
    assert events[0]["format"] == "reflector-cognitive-event-v1"
    assert events[0]["deployment"]["game_id"] == "bt11"
    assert events[0]["advisor_arbitration"]


def test_official_isolated_run_uses_child_process_and_merges_evidence(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[2]
    fixture = root / "tests" / "fixtures" / "official_toolkit"
    cognitive_streams = tmp_path / "cognitive-streams"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "reflector.cli",
            "official-isolated-run",
            "bt11",
            "--environments-dir",
            str(fixture),
            "--recordings-dir",
            str(tmp_path / "recordings"),
            "--no-recordings",
            "--lightweight",
            "--cognitive-stream-dir",
            str(cognitive_streams),
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=40,
        check=True,
    )
    report = json.loads(completed.stdout)
    assert report["kind"] == "process-isolated-official-evaluation"
    assert report["execution"]["parallel"]
    assert report["execution"]["max_workers"] == 1
    assert report["scorecard"]["score"] == 100.0
    assert report["scorecard"]["total_levels_completed"] == 5
    assert report["scorecard"]["total_actions"] == 72
    assert [agent["game_id"] for agent in report["agents"]] == ["bt11"]
    assert len(list(cognitive_streams.glob("*.cognitive.jsonl"))) == 1


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


def test_official_population_isolates_parallel_candidate_configs(
    tmp_path: Path,
) -> None:
    root = Path(__file__).parents[2]
    fixture = root / "tests" / "fixtures" / "official_toolkit"
    parent = root / "candidates" / "v23-goal-directed-relation-repair-400.json"
    output = tmp_path / "population.json"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "reflector.cli",
            "official-population-run",
            "bt11",
            "--parent",
            str(parent),
            "--environments-dir",
            str(fixture),
            "--output",
            str(output),
            "--max-workers",
            "4",
            "--reruns",
            "2",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    report = json.loads(output.read_text())
    assert completed.stdout.strip() == str(output)
    assert len(report["strategies"]) == 9
    assert len(report["outcomes"]) == 18
    assert len(
        {
            item["candidate"]["candidate_id"]
            for item in report["strategies"]
        }
    ) == 9
    by_strategy = {
        name: [
            (
                outcome["total_levels_completed"],
                outcome["score"],
                outcome["total_actions"],
            )
            for outcome in report["outcomes"]
            if outcome["strategy"] == name
        ]
        for name in {
            outcome["strategy"] for outcome in report["outcomes"]
        }
    }
    assert all(len(runs) == 2 and runs[0] == runs[1] for runs in by_strategy.values())
    inherited = report["inherited_traits"]
    offspring = report["offspring"]
    assert (offspring is None) == (not inherited)
    if offspring is not None:
        for trait in inherited:
            assert offspring["config"][trait["field"]] == trait["value"]
            assert trait["donor_id"] in offspring["contributor_ids"]
