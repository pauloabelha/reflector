from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("shared_attention_census", HERE / "census.py")
assert SPEC is not None and SPEC.loader is not None
CENSUS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = CENSUS
SPEC.loader.exec_module(CENSUS)


def add_game(recordings: Path, environments: Path, game: str, revision: str = "revision") -> None:
    recordings.mkdir(parents=True, exist_ok=True)
    (recordings / f"{game}.reflectoragent.test.recording.jsonl").write_text(
        '{"type":"data","data":{}}\n', encoding="utf-8"
    )
    target = environments / game / revision
    target.mkdir(parents=True, exist_ok=True)
    (target / f"{game}.py").write_text(f"GAME = {game!r}\n", encoding="utf-8")
    (target / "metadata.json").write_text("{}\n", encoding="utf-8")


def test_selector_is_lexicographic_intersection_of_unique_usable_transports(tmp_path: Path) -> None:
    recordings = tmp_path / "recordings"
    environments = tmp_path / "environments"
    add_game(recordings, environments, "zz99")
    add_game(recordings, environments, "aa00")
    (recordings / "recording_only.reflectoragent.test.recording.jsonl").write_text("{}\n")
    invalid = environments / "environment_only" / "revision"
    invalid.mkdir(parents=True)
    (invalid / "metadata.json").write_text("{}\n")

    selected = CENSUS.select_corpus(recordings, environments)

    assert selected["game_ids"] == ["aa00", "zz99"]
    assert selected["recording_only"] == ["recording_only"]
    assert selected["environment_only"] == []
    assert all(len(item["recording_sha256"]) == 64 for item in selected["games"])
    assert selected["corpus_digest"] == CENSUS.stable_hash(selected["games"])


def test_actual_public_corpus_freezes_all_25_games_and_150_paired_jobs() -> None:
    manifest = CENSUS.build_manifest()
    frozen = json.loads((HERE / "FROZEN_CENSUS_MANIFEST.json").read_text(encoding="utf-8"))

    assert tuple(manifest["selection"]["game_ids"]) == CENSUS.EXPECTED_GAME_IDS
    assert len(manifest["selection"]["games"]) == 25
    assert manifest["selection"]["recording_only"] == []
    assert manifest["selection"]["environment_only"] == []
    profiles = manifest["paired_design"]["profiles"]
    assert [item["profile_id"] for item in profiles] == [
        "balanced", "wide_frontier", "persistent_proposal"
    ]
    assert {tuple(item["trigger_action_counts"]) for item in profiles} == {(0, 8, 16)}
    assert {item["max_calls_per_episode"] for item in profiles} == {3}
    assert {item["action_budget"] for item in profiles} == {32}
    assert [item["frontier_root_limit"] for item in profiles] == [12, 24, 12]
    assert [item["proposal_attention_boost"] for item in profiles] == [1.0, 1.0, 2.0]
    assert len(manifest["jobs"]) == 25 * 3 * 2
    assert len({item["job_id"] for item in manifest["jobs"]}) == 150
    pairs = {}
    for job in manifest["jobs"]:
        assert job["fresh_start_required"] is True
        assert job["resume_from_prior_experiment_forbidden"] is True
        pairs.setdefault(job["pair_id"], set()).add(job["arm_id"])
    assert len(pairs) == 75
    assert all(value == {"r2_only", "shared_attention_qwen"} for value in pairs.values())

    estimate = manifest["runtime_estimate"]
    assert estimate["maximum_environment_actions"] == 4800
    assert estimate["maximum_qwen_calls"] == 225
    assert estimate["paired_episode_count"] == 150
    assert 5.0 < estimate["planned_estimate_hours"] < 5.5
    assert 3.0 < estimate["serial_gpu_hours"] < 4.0
    assert frozen["game_ids"] == manifest["selection"]["game_ids"]
    assert frozen["corpus_digest"] == manifest["selection"]["corpus_digest"]
    assert frozen["manifest_digest"] == manifest["manifest_digest"]
    assert frozen["job_count"] == len(manifest["jobs"])


def test_pickup_chain_metrics_separate_r_to_q_q_to_r_and_cost() -> None:
    digest = "a" * 64
    tasks = [
        {"task_id": "initial", "basis_version": 0, "recent_transition_count": 0},
        {"task_id": "revision", "basis_version": 4, "recent_transition_count": 4},
    ]
    adjudications = [
        {
            "task_id": "revision",
            "accepted_templates": [{"canonical_hash": digest}],
            "groundings": [{"status": "bound"}],
        }
    ]
    decisions = [
        {
            "decision": {"prior_used": True, "template_hash": digest},
            "qwen_changed_action": True,
        }
    ]
    replies = [
        {
            "latency_s": 12.5,
            "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        }
    ]

    metrics = CENSUS.pickup_chain_metrics_from_records(
        tasks, adjudications, decisions, replies
    )

    assert metrics["r_to_q_pickup_tasks"] == 1
    assert metrics["q_to_r_bound_tasks"] == 1
    assert metrics["q_to_r_pickup_tasks"] == 1
    assert metrics["q_to_r_changed_decisions"] == 1
    assert metrics["bidirectional_pickup_tasks"] == 1
    assert metrics["bidirectional_task_ids"] == ["revision"]
    assert metrics["qwen_reply_latency_s"] == 12.5
    assert metrics["qwen_total_tokens"] == 120


def result(
    game: str,
    arm: str,
    *,
    levels: int,
    actions: int,
    pickup: dict | None = None,
    telemetry: dict | None = None,
    replay: bool = True,
) -> dict:
    return {
        "profile_id": "balanced",
        "game": game,
        "arm_id": arm,
        "levels_completed": levels,
        "first_level_completed": levels >= 1,
        "actions": actions,
        "replay_verified": replay,
        "initial_observation_digest": f"initial-{game}",
        "elapsed_s": 10 if arm == "r2_only" else 30,
        "qwen_task_count": 0 if arm == "r2_only" else 3,
        "pickup": pickup or {"available": True},
        **({"epistemic_metrics": telemetry} if telemetry is not None else {}),
    }


def mini_manifest() -> dict:
    value = {
        "protocol": CENSUS.PROTOCOL,
        "selection": {"game_ids": ["gain", "pickup", "abstain", "regress"]},
        "paired_design": {
            "profiles": [{"profile_id": "balanced"}],
            "primary_profile": "balanced",
        },
    }
    return {**value, "manifest_digest": CENSUS.stable_hash(value)}


def test_analysis_assigns_buckets_a_through_d_and_aggregates_cost() -> None:
    results = [
        result("gain", "r2_only", levels=0, actions=32),
        result(
            "gain",
            "shared_attention_qwen",
            levels=1,
            actions=20,
            telemetry={
                "N_QR": 1,
                "N_RQ": 0,
                "complete_causal_chains": 1,
                "novelty_counts": {"ahead_of_r2": 1},
            },
        ),
        result("pickup", "r2_only", levels=0, actions=32),
        result(
            "pickup",
            "shared_attention_qwen",
            levels=0,
            actions=32,
            telemetry={
                "pickup_directions": {"qwen->r2": 4, "r2->qwen": 5},
                "grounded_pickup_directions": {"qwen->r2": 1, "r2->qwen": 1},
                "complete_causal_chains": 0,
                "novelty_counts": {"refinement": 1},
            },
        ),
        result("abstain", "r2_only", levels=0, actions=32),
        result(
            "abstain",
            "shared_attention_qwen",
            levels=0,
            actions=32,
            telemetry={
                "N_QR": 0,
                "N_RQ": 1,
                "novelty_classifications": ["ahead_of_r2", "paraphrase"],
            },
        ),
        result("regress", "r2_only", levels=1, actions=20),
        result("regress", "shared_attention_qwen", levels=0, actions=32),
    ]

    analysis = CENSUS.analyze_results(results, mini_manifest())

    assert analysis["complete"] is True
    assert analysis["overall_bucket_counts"] == {"A": 1, "B": 1, "C": 1, "D": 1}
    assert analysis["games_with_any_task_gain"] == ["gain"]
    assert analysis["games_with_any_regression_or_invalidity"] == ["regress"]
    profile = analysis["profiles"][0]
    assert profile["qwen_calls"] == 12
    assert profile["N_QR"] == 2
    assert profile["N_RQ"] == 2
    assert profile["complete_causal_chains"] == 1
    assert profile["harmful_pairs"] == 1
    assert profile["elapsed_overhead_s"] == 80
    assert profile["seconds_overhead_per_task_gain"] == 80
    assert analysis["games_flagged_harmful"] == ["regress"]
    assert analysis["verdict"] == "CONTROL_PROMISING"


def test_graph_native_telemetry_precedes_v0_fallback_and_fallback_remains_safe() -> None:
    native = CENSUS.normalized_episode_telemetry(
        {
            "graph_metrics": {
                "pickup_directions": {"qwen->r2": 20, "r2->qwen": 30},
                "grounded_pickup_directions": {"qwen->r2": 2, "r2->qwen": 3},
                "complete_causal_chains": [{"chain_id": "one"}],
                "qwen_novelty_counts": {"ahead_of_r2": 2, "paraphrase": 4},
            },
            "pickup": {"q_to_r_pickup_tasks": 99, "r_to_q_pickup_tasks": 99},
        }
    )
    assert native["telemetry_source"] == "graph_native"
    assert (native["N_QR"], native["N_RQ"]) == (2, 3)
    assert native["qwen_to_r2_exposures"] == 20
    assert native["r2_to_qwen_exposures"] == 30
    assert native["complete_causal_chains"] == 1
    assert native["meaningful_novelty"] == 2

    fallback = CENSUS.normalized_episode_telemetry(
        {"pickup": {"q_to_r_pickup_tasks": 2, "r_to_q_pickup_tasks": 1}}
    )
    assert fallback["telemetry_source"] == "v0_fallback"
    assert (fallback["N_QR"], fallback["N_RQ"]) == (2, 1)
    assert fallback["qwen_to_r2_exposures"] == 0
    assert fallback["r2_to_qwen_exposures"] == 0


def test_completed_ar25_shape_is_valid_but_exposure_is_not_mechanistic_pickup() -> None:
    common = {
        "profile_id": "balanced",
        "game": "ar25",
        "levels_completed": 0,
        "first_level_completed": False,
        "actions": 32,
        "replay_verified": True,
        "initial_digest": "8c9c38b5c049817e37ea6525b513983e3",
        "support_authority_violations": 0,
    }
    control = {
        **common,
        "arm_id": "r2_only",
        "elapsed_s": 622.46,
        "graph_metrics": {
            "pickup_directions": {},
            "grounded_pickup_directions": {},
        },
    }
    shared = {
        **common,
        "arm_id": "shared_attention_qwen",
        "elapsed_s": 906.80,
        "qwen_calls": 3,
        "qwen_context_valid": True,
        "qwen_transport_successful": True,
        "graph_metrics": {
            "pickup_count": 8,
            "pickup_directions": {"qwen->r2": 3, "r2->qwen": 5},
            "grounded_pickup_count": 0,
            "grounded_pickup_directions": {},
        },
    }

    comparison = CENSUS.classify_pair(control, shared)

    assert comparison["same_initial_observation"] is True
    assert comparison["replay_valid"] is True
    assert comparison["bucket"] == "D"
    assert comparison["bucket"] not in {"A", "B"}
    assert (comparison["N_QR"], comparison["N_RQ"]) == (0, 0)
    assert comparison["qwen_to_r2_exposures"] == 3
    assert comparison["r2_to_qwen_exposures"] == 5
    assert comparison["complete_causal_chains"] == 0


def test_analysis_rejects_duplicates_and_incomplete_pairs() -> None:
    manifest = mini_manifest()
    one = result("gain", "r2_only", levels=0, actions=32)
    with pytest.raises(CENSUS.CensusError, match="duplicate result"):
        CENSUS.analyze_results([one, one], manifest)
    with pytest.raises(CENSUS.CensusError, match="missing paired results"):
        CENSUS.analyze_results([one], manifest)
