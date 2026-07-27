import json

import pytest

from reflector.cli import demo_trace
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
        assert store.evaluated(result.manifest.experiment_id)
    assert json.loads(json.dumps(result.to_dict()))["pareto_archive"]
