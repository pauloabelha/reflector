"""Local CLI for trace generation, replay, evaluation, and comparison."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from .compression import analyze_redundancy, counterfactual_replay, replay_policy
from .evaluation import compare_traces, evaluate_ablations, evaluate_trace
from .evolver import (
    descendants,
    evaluate_evolution_ablations,
    root_candidate,
    run_experiment,
)
from .experiments import ExperimentStore
from .graph import DependencyGraph
from .mind import MindConfig
from .mutations import (
    DeterministicMutationProvider,
    MutationProposal,
    MutationProvider,
    OpenAICompatibleMutationProvider,
)
from .policy import SymbolicPolicy
from .population import pareto_archive
from .symbolic import Observation
from .trace import EpisodeTrace
from .web_api import serve


def demo_trace() -> EpisodeTrace:
    """Create a deterministic miniature episode without an ARC dependency."""

    observations = (
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(1, 2),
            frame=((0, 0, 0), (0, 0, 0), (0, 0, 0)),
        ),
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(1, 2),
            frame=((0, 0, 0), (0, 9, 0), (0, 0, 0)),
        ),
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(1, 2),
            frame=((0, 0, 0), (0, 0, 9), (0, 0, 0)),
            levels_completed=1,
        ),
    )
    policy = SymbolicPolicy()
    for observation in observations:
        policy.choose_action(observation)
    return policy.trace


def load_trace(path: Path) -> EpisodeTrace:
    return EpisodeTrace.from_json(path.read_text(encoding="utf-8"))


def load_named_traces(paths: list[Path]) -> dict[str, EpisodeTrace]:
    traces = {path.stem: load_trace(path) for path in paths}
    if len(traces) != len(paths):
        raise ValueError("trace file stems must be unique")
    return traces


def main() -> None:
    parser = argparse.ArgumentParser(prog="reflector")
    commands = parser.add_subparsers(dest="command", required=True)

    demo = commands.add_parser("trace-demo")
    demo.add_argument("--output", type=Path, required=True)

    replay = commands.add_parser("replay")
    replay.add_argument("trace", type=Path)

    evaluate = commands.add_parser("evaluate")
    evaluate.add_argument("trace", type=Path)

    compare = commands.add_parser("compare")
    compare.add_argument("traces", nargs="+", type=Path)

    compression = commands.add_parser("compression")
    compression.add_argument("trace", type=Path)

    counterfactual = commands.add_parser("counterfactual")
    counterfactual.add_argument("trace", type=Path)

    ablations = commands.add_parser("ablations")
    ablations.add_argument("trace", type=Path)

    graph = commands.add_parser("graph")
    graph.add_argument("trace", type=Path)

    population = commands.add_parser("population-evaluate")
    population.add_argument("traces", nargs="+", type=Path)
    population.add_argument("--db", type=Path, required=True)
    population.add_argument("--name", default="population-evaluation")
    population.add_argument("--seed", type=int, default=0)
    population.add_argument("--config", type=Path)
    population.add_argument("--allow-network", action="store_true")

    evolve = commands.add_parser("evolve")
    evolve.add_argument("traces", nargs="+", type=Path)
    evolve.add_argument("--db", type=Path, required=True)
    evolve.add_argument("--name", default="symbolic-evolution")
    evolve.add_argument("--seed", type=int, default=0)
    evolve.add_argument("--provider-endpoint")
    evolve.add_argument("--provider-model")
    evolve.add_argument("--api-key-env")
    evolve.add_argument("--allow-network", action="store_true")

    lineage = commands.add_parser("lineage")
    lineage.add_argument("--db", type=Path, required=True)
    lineage.add_argument("--experiment", required=True)
    lineage.add_argument("--candidate")

    evolution_ablations = commands.add_parser("evolution-ablations")
    evolution_ablations.add_argument("--db", type=Path, required=True)
    evolution_ablations.add_argument("--experiment", required=True)

    web = commands.add_parser("web")
    web.add_argument("trace", type=Path)
    web.add_argument("--db", type=Path)
    web.add_argument("--host", default="127.0.0.1")
    web.add_argument("--port", type=int, default=8765)
    web.add_argument(
        "--static",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "web" / "dist",
    )

    args = parser.parse_args()
    if args.command == "trace-demo":
        trace = demo_trace()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(trace.to_json() + "\n", encoding="utf-8")
        print(args.output)
    elif args.command == "replay":
        report = load_trace(args.trace).replay(SymbolicPolicy)
        print(json.dumps(report, indent=2))
    elif args.command == "evaluate":
        print(json.dumps(evaluate_trace(load_trace(args.trace)).to_dict(), indent=2))
    elif args.command == "compare":
        print(json.dumps(compare_traces(load_named_traces(args.traces)), indent=2))
    elif args.command == "compression":
        print(
            json.dumps(
                analyze_redundancy(load_trace(args.trace)).to_dict(), indent=2
            )
        )
    elif args.command == "counterfactual":
        print(
            json.dumps(
                [
                    item.to_dict()
                    for item in counterfactual_replay(load_trace(args.trace))
                ],
                indent=2,
            )
        )
    elif args.command == "ablations":
        print(json.dumps(evaluate_ablations(load_trace(args.trace)), indent=2))
    elif args.command == "graph":
        policy = replay_policy(load_trace(args.trace))
        dependency_graph = DependencyGraph.build(
            policy.mind.schemas,
            policy.mind.concepts,
            policy.mind.hypotheses,
            policy.mind.abstractions,
        )
        print(json.dumps(dependency_graph.to_dict(), indent=2))
    elif args.command == "population-evaluate":
        config = (
            MindConfig.from_dict(
                json.loads(args.config.read_text(encoding="utf-8"))
            )
            if args.config is not None
            else MindConfig()
        )
        with ExperimentStore(args.db) as store:
            result = run_experiment(
                name=args.name,
                seed=args.seed,
                traces=load_named_traces(args.traces),
                candidates=(root_candidate(config),),
                store=store,
                network_disabled=not args.allow_network,
            )
        print(json.dumps(result.to_dict(), indent=2))
    elif args.command == "evolve":
        parent = root_candidate()
        providers: tuple[MutationProvider, ...]
        if args.provider_endpoint:
            if not args.provider_model:
                parser.error("--provider-model is required with --provider-endpoint")
            api_key = (
                os.environ.get(args.api_key_env)
                if args.api_key_env is not None
                else None
            )
            providers = (
                OpenAICompatibleMutationProvider(
                    args.provider_endpoint, args.provider_model, api_key
                ),
            )
        else:
            providers = tuple(
                DeterministicMutationProvider(proposal)
                for proposal in (
                    MutationProposal(
                        {"planner_max_expansions": 32},
                        "reduce bounded planning cost",
                    ),
                    MutationProposal(
                        {"information_weight": 1.5},
                        "increase epistemic exploration pressure",
                    ),
                    MutationProposal(
                        {"experiment_weight": 0.5},
                        "increase explicit experiment preference",
                    ),
                )
            )
        children = descendants(parent, providers, feedback={})
        with ExperimentStore(args.db) as store:
            result = run_experiment(
                name=args.name,
                seed=args.seed,
                traces=load_named_traces(args.traces),
                candidates=(parent, *children),
                store=store,
                network_disabled=not args.allow_network,
            )
        print(json.dumps(result.to_dict(), indent=2))
    elif args.command == "lineage":
        with ExperimentStore(args.db) as store:
            evaluated = store.evaluated(args.experiment)
            if args.candidate:
                payload: object = [
                    candidate.to_dict()
                    for candidate in store.lineage(
                        args.experiment, args.candidate
                    )
                ]
            else:
                payload = [
                    {
                        "candidate": candidate.to_dict(),
                        "fitness": fitness.to_dict(),
                    }
                    for candidate, fitness in pareto_archive(evaluated)
                ]
        print(json.dumps(payload, indent=2))
    elif args.command == "evolution-ablations":
        with ExperimentStore(args.db) as store:
            payload = evaluate_evolution_ablations(
                store.evaluated(args.experiment)
            )
        print(json.dumps(payload, indent=2))
    else:
        serve(
            trace=load_trace(args.trace),
            database=args.db,
            static_directory=args.static,
            host=args.host,
            port=args.port,
        )


if __name__ == "__main__":
    main()
