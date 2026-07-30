import json
import threading
import urllib.request

import pytest

from reflector.cli import demo_trace
from reflector.evolver import root_candidate
from reflector.experiments import ExperimentManifest, ExperimentStore
from reflector.population import Fitness
from reflector.web_api import (
    analyze_trace,
    branch_replay,
    create_server,
    live_snapshot,
)


def test_analysis_reconstructs_symbolic_state_and_explanations() -> None:
    analysis = analyze_trace(demo_trace())
    assert analysis["trace"]["step_count"] == 3
    assert all(step["decision_matches"] for step in analysis["steps"])
    final = analysis["final_symbolic_state"]
    assert final["schemas"]["schemas"]
    assert final["hypotheses"]["causal"]
    assert final["abstractions"]["language_history"][0][
        "version_id"
    ] == "language-v1-primitives"
    assert analysis["steps"][0]["recorded_decision"]["reason"]


def test_branch_replay_is_bounded_and_explicit_about_limitations() -> None:
    trace = demo_trace()
    branch = branch_replay(
        trace,
        from_step=1,
        patch={"information_weight": 1.5},
    )
    assert branch["mode"] == "trace-only-policy-branch"
    assert "fixed" in branch["limitation"]
    assert branch["config"]["information_weight"] == 1.5
    assert len(branch["steps"]) == 2
    with pytest.raises(ValueError, match="outside"):
        branch_replay(trace, from_step=99, patch={})


def test_experiment_report_includes_pareto_and_genealogy(tmp_path) -> None:
    trace = demo_trace()
    manifest = ExperimentManifest.create("web", 4, {"demo": trace})
    parent = root_candidate()
    contributor = type(parent).create(
        parent.config,
        rationale="independent contributor",
    )
    child = type(parent).create(
        parent.config,
        parent_id=parent.candidate_id,
        contributor_ids=(contributor.candidate_id,),
        generation=1,
        rationale="child",
    )
    with ExperimentStore(tmp_path / "web.sqlite") as store:
        store.save_manifest(manifest)
        for candidate, candidate_fitness in (
            (parent, Fitness(1, 1.0, 0.5, 3, 10)),
            (contributor, Fitness(1, 1.0, 0.5, 3, 10)),
            (child, Fitness(2, 1.0, 0.5, 2, 12)),
        ):
            store.save_candidate(manifest.experiment_id, candidate)
            store.save_evaluation(
                manifest.experiment_id,
                candidate.candidate_id,
                candidate_fitness,
                {"candidate": candidate.candidate_id},
            )
        listing = store.list_experiments()
        report = store.experiment_report(manifest.experiment_id)
    assert listing[0]["candidate_count"] == 3
    assert len(report["candidates"]) == 3
    assert sorted(
        report["lineage_edges"], key=lambda edge: edge["relationship"]
    ) == [
        {
            "source": parent.candidate_id,
            "target": child.candidate_id,
            "relationship": "backbone",
        },
        {
            "source": contributor.candidate_id,
            "target": child.candidate_id,
            "relationship": "contributor",
        },
    ]
    assert all(item["pareto"] for item in report["candidates"])
    child_report = next(
        item
        for item in report["candidates"]
        if item["candidate"]["candidate_id"] == child.candidate_id
    )
    assert child_report["parent_improvement"]
    assert child_report["parent_improvement"]["levels_advanced"] == 1
    assert child_report["parent_improvement"]["planner_expansions"] == 1
    assert child_report["parent_improvement"][
        "schema_description_length"
    ] == -2


def test_local_http_api_and_static_shell(tmp_path) -> None:
    static = tmp_path / "dist"
    static.mkdir()
    (static / "index.html").write_text("<main>Reflector</main>", encoding="utf-8")
    try:
        server = create_server(
            trace=demo_trace(),
            database=None,
            static_directory=static,
            port=0,
        )
    except PermissionError:
        pytest.skip("test sandbox forbids binding a loopback socket")
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urllib.request.urlopen(f"{base}/api/health") as response:
            assert json.loads(response.read())["status"] == "ok"
        request = urllib.request.Request(
            f"{base}/api/branch",
            data=json.dumps(
                {"from_step": 0, "patch": {"planner_max_depth": 2}}
            ).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request) as response:
            assert json.loads(response.read())["config"][
                "planner_max_depth"
            ] == 2
        with urllib.request.urlopen(base) as response:
            assert b"Reflector" in response.read()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_live_snapshot_discovers_best_games_and_latest_candidate(tmp_path) -> None:
    reports = tmp_path / "reports"
    candidates = tmp_path / "candidates"
    reports.mkdir()
    candidates.mkdir()
    (reports / "official.json").write_text(
        json.dumps(
            {
                "scorecard": {
                    "score": 12.5,
                    "total_levels_completed": 2,
                    "total_levels": 4,
                    "total_environments_completed": 0,
                    "total_environments": 25,
                    "total_actions": 40,
                    "environments": [
                        {
                            "id": "demo-hash",
                            "levels_completed": 2,
                            "level_count": 4,
                            "score": 50.0,
                            "actions": 40,
                            "completed": False,
                            "runs": [{"level_actions": [10, 30, 0, 0]}],
                        }
                    ],
                }
            }
        ),
        encoding="utf-8",
    )
    (candidates / "offspring.json").write_text(
        json.dumps(
            {
                "candidate_id": "candidate-new",
                "parent_id": "candidate-old",
                "generation": 3,
                "rationale": "test",
                "mutation_source": "unit",
                "inference_fingerprint": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    snapshot = live_snapshot(tmp_path)
    assert snapshot["best_full"]["score"] == 12.5
    assert snapshot["games"][0]["game"] == "demo"
    assert snapshot["games"][0]["level_actions"] == [10, 30, 0, 0]
    assert snapshot["offspring"]["candidate_id"] == "candidate-new"
