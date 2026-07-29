import json
import subprocess
import threading
import time
from pathlib import Path

import pytest

from reflector.cli import demo_trace
from reflector.evolution.isolated_official import run_process_isolated_games
from reflector.evolution.official_population import (
    inference_fingerprint,
    operative_strategy_population,
    run_official_population_round,
)
from reflector.evolver import (
    descendants,
    evaluate_evolution_ablations,
    root_candidate,
    run_experiment,
)
from reflector.experiments import ExperimentManifest, ExperimentStore
from reflector.mind import MindConfig
from reflector.mutations import (
    DeterministicMutationProvider,
    MutationProposal,
)
from reflector.population import Candidate, Fitness, pareto_archive
from reflector.sandbox import evaluate_candidate, validate_candidate
from reflector.symbolic import Observation
from reflector.transforms import (
    color_holdout,
    color_permutation,
    transform_observation,
)


def test_genome_is_strict_serializable_and_bounded() -> None:
    config = MindConfig(
        planner_max_depth=4,
        planner_max_expansions=32,
        information_weight=1.5,
    )
    assert MindConfig.from_dict(config.to_dict()) == config
    with pytest.raises(ValueError, match="unknown"):
        MindConfig.from_dict({**config.to_dict(), "magic": True})
    with pytest.raises(ValueError, match="between 1 and 8"):
        MindConfig(planner_max_depth=9)
    with pytest.raises(ValueError, match="boolean"):
        MindConfig(enable_planning=1)  # type: ignore[arg-type]


def test_color_holdouts_are_seeded_and_preserve_protocol() -> None:
    trace = demo_trace()
    first = color_holdout(trace, 91)
    second = color_holdout(trace, 91)
    assert first.to_json() == second.to_json()
    assert color_permutation(91)[0] == 0
    assert len(color_permutation(91)) == 16
    high_color = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1,),
        frame=((0, 14),),
        levels_completed=0,
    )
    assert transform_observation(
        high_color, color_permutation(91)
    ).frame[0][1] in range(1, 16)
    assert len(first.steps) == len(trace.steps)
    assert [
        step.observation.available_actions for step in first.steps
    ] == [step.observation.available_actions for step in trace.steps]


def test_mutations_are_constrained_and_create_lineage() -> None:
    parent = root_candidate()
    provider = DeterministicMutationProvider(
        MutationProposal(
            {"planner_max_expansions": 16}, "smaller bounded search"
        )
    )
    (child,) = descendants(parent, (provider,), {})
    assert child.parent_id == parent.candidate_id
    assert child.generation == 1
    assert child.mutation_source == "DeterministicMutationProvider"
    assert child.config.planner_max_expansions == 16
    with pytest.raises(ValueError, match="unknown"):
        MutationProposal.from_dict(
            {"patch": {"source_code": "evil"}, "rationale": "invalid"}
        )


def test_pareto_archive_keeps_nondominated_candidates() -> None:
    first = Candidate.create(MindConfig(), rationale="first")
    second = Candidate.create(
        MindConfig(planner_max_expansions=32), rationale="second"
    )
    better = Fitness(2, 1.0, 0.8, 10, 20)
    worse = Fitness(1, 1.0, 0.7, 20, 30)
    archive = pareto_archive(((first, better), (second, worse)))
    assert archive == ((first, better),)


def test_evolution_ablation_matrix_separates_pressure_and_llm_source() -> None:
    root = root_candidate()
    llm = Candidate.create(
        MindConfig(information_weight=2.0),
        parent_id=root.candidate_id,
        generation=1,
        rationale="remote proposal",
        mutation_source="OpenAICompatibleMutationProvider",
    )
    root_fitness = Fitness(1, 1.0, 0.8, 10, 20, 3)
    llm_fitness = Fitness(2, 0.5, 0.7, 20, 25, 5)
    report = evaluate_evolution_ablations(
        ((root, root_fitness), (llm, llm_fitness))
    )
    assert report["score_only_evolution"] == (llm.candidate_id,)
    assert report["no_llm_mutation"] == (root.candidate_id,)


def test_manifest_store_and_lineage_round_trip(tmp_path) -> None:
    traces = {"demo": demo_trace()}
    manifest = ExperimentManifest.create("unit", 7, traces, (13,))
    assert manifest.experiment_id == ExperimentManifest.create(
        "unit", 7, traces, (13,)
    ).experiment_id
    parent = root_candidate()
    child = Candidate.create(
        MindConfig(planner_max_depth=2),
        parent_id=parent.candidate_id,
        generation=1,
        rationale="shallower",
    )
    fitness = Fitness(1, 1.0, 0.5, 4, 10)
    with ExperimentStore(tmp_path / "experiments.sqlite") as store:
        store.save_manifest(manifest)
        store.save_candidate(manifest.experiment_id, parent)
        store.save_candidate(manifest.experiment_id, child)
        store.save_evaluation(
            manifest.experiment_id, child.candidate_id, fitness, {"ok": True}
        )
        assert store.lineage(
            manifest.experiment_id, child.candidate_id
        ) == (parent, child)
        assert store.evaluated(manifest.experiment_id) == ((child, fitness),)


def test_candidate_validation_is_deterministic_and_network_isolated() -> None:
    traces = {"demo": demo_trace()}
    local = evaluate_candidate(MindConfig(), traces)
    assert local.deterministic
    assert local.runtime_ms > 0
    assert local.peak_memory_kib > 0
    assert local.fitness.genome_description_length > 0
    isolated = validate_candidate(MindConfig(), traces)
    assert isolated.deterministic
    assert isolated.network_isolated
    assert isolated.fitness == local.fitness


def test_end_to_end_population_experiment(tmp_path) -> None:
    trace = demo_trace()
    candidate = root_candidate()
    database = tmp_path / "population.sqlite"
    with ExperimentStore(database) as store:
        result = run_experiment(
            name="integration",
            seed=3,
            traces={"demo": trace},
            candidates=(candidate,),
            store=store,
            holdout_seeds=(17,),
        )
        assert result.archive[0][0] == candidate
        diagnostics = dict(result.diagnostics)[candidate.candidate_id]
        assert diagnostics["runtime_ms"] > 0
        assert diagnostics["peak_memory_kib"] > 0
        assert diagnostics["network_isolated"]
        assert store.evaluated(result.manifest.experiment_id)
    assert json.loads(json.dumps(result.to_dict()))["pareto_archive"]


def test_candidate_preserves_legacy_and_multi_parent_provenance() -> None:
    legacy = root_candidate().to_dict()
    legacy.pop("contributor_ids")
    legacy.pop("inference_fingerprint")
    restored = Candidate.from_dict(legacy)
    assert restored.contributor_ids == ()
    assert restored.inference_fingerprint is None

    donor = Candidate.create(
        MindConfig(enable_productive_role_reuse=True),
        parent_id=restored.candidate_id,
    )
    child = Candidate.create(
        donor.config,
        parent_id=restored.candidate_id,
        contributor_ids=(donor.candidate_id,),
        inference_fingerprint="a" * 64,
    )
    round_trip = Candidate.from_dict(child.to_dict())
    assert round_trip == child
    assert round_trip.contributor_ids == tuple(
        sorted((restored.candidate_id, donor.candidate_id))
    )


def test_official_population_runs_in_parallel_and_breeds_only_gated_traits(
    tmp_path,
) -> None:
    root = root_candidate(
        MindConfig(
            enable_epistemic_state_graph=True,
            enable_click_object_accommodation=True,
            enable_local_relation_solver=True,
        )
    )
    project_root = Path(__file__).resolve().parents[2]
    fingerprint = inference_fingerprint(project_root)
    strategies = operative_strategy_population(
        root,
        source_fingerprint=fingerprint,
    )
    assert [item.name for item in strategies] == [
        "relation-repair-control",
        "action-family-fairness",
        "successful-structural-replay",
        "productive-role-reuse",
        "constraint-first-structural-replay",
    ]
    assert len({item.candidate.candidate_id for item in strategies}) == 5

    active = 0
    maximum_active = 0
    lock = threading.Lock()

    def fake_run(command, **_kwargs):
        nonlocal active, maximum_active
        config_path = Path(command[command.index("--config") + 1])
        config = json.loads(config_path.read_text())["config"]
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.01)
        with lock:
            active -= 1

        levels = 2
        score = 10.0
        if config["enable_hierarchical_action_fairness"]:
            levels = 1
            score = 5.0
        elif config["enable_successful_role_replay"]:
            score = 11.0
        elif config["enable_productive_role_reuse"]:
            levels = 3
            score = 12.0
        report = {
            "scorecard": {
                "score": score,
                "total_levels_completed": levels,
                "total_actions": 80,
                "environments": [
                    {
                        "id": "game-a1b2",
                        "levels_completed": levels,
                        "actions": 80,
                        "score": score,
                        "completed": False,
                        "runs": [{"level_actions": [4] * levels}],
                    }
                ],
            },
            "agents": [{"game_id": "game", "mind_config": config}],
            "source_commit": "b" * 40,
        }
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(report),
            stderr="",
        )

    result = run_official_population_round(
        parent=root,
        games=("game",),
        environments_dir=tmp_path,
        project_root=project_root,
        max_workers=4,
        reruns=2,
        command_runner=fake_run,
    )

    assert maximum_active > 1
    assert len(result.outcomes) == 10
    assert [item.field for item in result.inherited_traits] == [
        "enable_productive_role_reuse",
        "enable_successful_role_replay",
    ]
    assert result.offspring is not None
    assert result.offspring.config.enable_productive_role_reuse
    assert result.offspring.config.enable_successful_role_replay
    assert not result.offspring.config.enable_hierarchical_action_fairness
    assert len(result.offspring.contributor_ids) == 3
    assert result.offspring.inference_fingerprint == fingerprint


def test_official_games_run_in_parallel_process_commands_and_merge_evidence(
    tmp_path,
) -> None:
    active = 0
    maximum_active = 0
    lock = threading.Lock()
    commands: list[list[str]] = []

    def fake_run(command, **_kwargs):
        nonlocal active, maximum_active
        game = command[command.index("official-run") + 1]
        commands.append(command)
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.01)
        with lock:
            active -= 1
        levels = 1 if game == "alpha" else 2
        score = 10.0 if game == "alpha" else 30.0
        report = {
            "scorecard": {
                "environments": [
                    {
                        "id": f"{game}-version",
                        "levels_completed": levels,
                        "actions": 40,
                        "score": score,
                        "completed": False,
                        "level_count": 4,
                        "runs": [{"level_actions": [4] * levels}],
                    }
                ]
            },
            "agents": [{"game_id": game, "mind_config": MindConfig().to_dict()}],
            "source_commit": "c" * 40,
        }
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=json.dumps(report),
            stderr="",
        )

    report = run_process_isolated_games(
        games=("beta", "alpha"),
        environments_dir=tmp_path,
        recordings_dir=tmp_path / "recordings",
        project_root=Path(__file__).resolve().parents[2],
        max_workers=2,
        command_runner=fake_run,
    )

    assert maximum_active == 2
    assert all(
        command[command.index("official-run") + 1]
        in {"alpha", "beta"}
        for command in commands
    )
    assert len(commands) == 2
    assert report["kind"] == "process-isolated-official-evaluation"
    assert report["execution"]["isolation"] == "one fresh Python process per game"
    assert report["scorecard"]["score"] == 20.0
    assert report["scorecard"]["total_levels_completed"] == 3
    assert report["scorecard"]["total_actions"] == 80
    assert report["scorecard"]["total_levels"] == 8
    assert [agent["game_id"] for agent in report["agents"]] == [
        "alpha",
        "beta",
    ]
