"""Local CLI for trace generation, replay, evaluation, and comparison."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from contextlib import redirect_stdout
from importlib import import_module
from pathlib import Path

from .core.graph import DependencyGraph
from .core.mind import MindConfig
from .core.symbolic import Observation
from .evolution.evolver import (
    descendants,
    evaluate_evolution_ablations,
    root_candidate,
    run_experiment,
)
from .evolution.experiments import ExperimentStore
from .evolution.isolated_official import run_process_isolated_games
from .evolution.mutations import (
    DeterministicMutationProvider,
    MutationProposal,
    MutationProvider,
    OpenAICompatibleMutationProvider,
)
from .evolution.official_population import run_official_population_round
from .evolution.population import Candidate, pareto_archive
from .research.benchmark import run_validation
from .research.compression import (
    analyze_redundancy,
    counterfactual_replay,
    replay_policy,
)
from .research.evaluation import (
    compare_traces,
    evaluate_ablations,
    evaluate_trace,
)
from .research.official_eval import (
    expected_public_game_count,
    inventory_official_environments,
)
from .runtime.deployment import (
    CANDIDATE_ID_ENV,
    COGNITIVE_STREAM_DIR_ENV,
    CONFIG_ENV,
    INFERENCE_FINGERPRINT_ENV,
)
from .runtime.policy import SymbolicPolicy
from .runtime.trace import EpisodeTrace
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

    validate = commands.add_parser("validate")
    validate.add_argument("--seeds", type=int, default=30)
    validate.add_argument("--seed-start", type=int, default=0)
    validate.add_argument(
        "--suite",
        choices=("v1", "v2", "v3", "v4", "v5", "v6", "v7", "v8"),
        default="v1",
    )
    validate.add_argument("--output", type=Path)

    official_run = commands.add_parser("official-run")
    official_run.add_argument("games", nargs="+")
    official_run.add_argument("--environments-dir", type=Path, required=True)
    official_run.add_argument("--recordings-dir", type=Path, required=True)
    official_run.add_argument(
        "--config",
        type=Path,
        help="MindConfig JSON or serialized Candidate JSON to deploy",
    )
    official_run.add_argument(
        "--no-recordings",
        action="store_true",
        help="skip development replay recordings",
    )
    official_run.add_argument(
        "--lightweight",
        action="store_true",
        help="skip expensive post-run trace analysis",
    )
    official_run.add_argument(
        "--cognitive-stream-dir",
        type=Path,
        help="flush inspectable symbolic events to one JSONL file per game",
    )

    official_public = commands.add_parser("official-public-run")
    official_public.add_argument("--environments-dir", type=Path, required=True)
    official_public.add_argument("--recordings-dir", type=Path, required=True)
    official_public.add_argument("--output", type=Path, required=True)
    official_public.add_argument(
        "--config",
        type=Path,
        help="MindConfig JSON or serialized Candidate JSON to deploy",
    )
    official_public.add_argument(
        "--no-recordings",
        action="store_true",
        help="skip development replay recordings",
    )
    official_public.add_argument(
        "--lightweight",
        action="store_true",
        help="skip expensive post-run trace analysis",
    )
    official_public.add_argument(
        "--cognitive-stream-dir",
        type=Path,
        help="flush inspectable symbolic events to one JSONL file per game",
    )

    isolated_run = commands.add_parser("official-isolated-run")
    isolated_run.add_argument("games", nargs="+")
    isolated_run.add_argument("--environments-dir", type=Path, required=True)
    isolated_run.add_argument("--recordings-dir", type=Path, required=True)
    isolated_run.add_argument("--output", type=Path)
    isolated_run.add_argument("--config", type=Path)
    isolated_run.add_argument("--max-workers", type=int, default=4)
    isolated_run.add_argument("--timeout", type=float, default=1800.0)
    isolated_run.add_argument("--no-recordings", action="store_true")
    isolated_run.add_argument("--lightweight", action="store_true")
    isolated_run.add_argument("--cognitive-stream-dir", type=Path)

    isolated_public = commands.add_parser("official-isolated-public-run")
    isolated_public.add_argument("--environments-dir", type=Path, required=True)
    isolated_public.add_argument("--recordings-dir", type=Path, required=True)
    isolated_public.add_argument("--output", type=Path, required=True)
    isolated_public.add_argument("--config", type=Path)
    isolated_public.add_argument("--max-workers", type=int, default=4)
    isolated_public.add_argument("--timeout", type=float, default=1800.0)
    isolated_public.add_argument("--no-recordings", action="store_true")
    isolated_public.add_argument("--lightweight", action="store_true")
    isolated_public.add_argument("--cognitive-stream-dir", type=Path)

    official_population = commands.add_parser("official-population-run")
    official_population.add_argument("games", nargs="+")
    official_population.add_argument(
        "--parent",
        type=Path,
        required=True,
        help="serialized parent Candidate JSON",
    )
    official_population.add_argument(
        "--environments-dir",
        type=Path,
        required=True,
    )
    official_population.add_argument("--output", type=Path, required=True)
    official_population.add_argument("--offspring-output", type=Path)
    official_population.add_argument("--max-workers", type=int, default=4)
    official_population.add_argument("--reruns", type=int, default=2)
    official_population.add_argument("--timeout", type=float, default=1800.0)
    official_population.add_argument(
        "--cognitive-stream-dir",
        type=Path,
        help="persist per-candidate, per-rerun cognitive JSONL streams",
    )

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
    dashboard = commands.add_parser("dashboard")
    dashboard.add_argument(
        "--workspace",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
    )
    dashboard.add_argument("--host", default="127.0.0.1")
    dashboard.add_argument("--port", type=int, default=8765)
    dashboard.add_argument(
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
        report = load_trace(args.trace).replay()
        print(json.dumps(report, indent=2))
    elif args.command == "evaluate":
        print(json.dumps(evaluate_trace(load_trace(args.trace)).to_dict(), indent=2))
    elif args.command == "compare":
        print(json.dumps(compare_traces(load_named_traces(args.traces)), indent=2))
    elif args.command == "compression":
        print(
            json.dumps(analyze_redundancy(load_trace(args.trace)).to_dict(), indent=2)
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
            MindConfig.from_dict(json.loads(args.config.read_text(encoding="utf-8")))
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
                    for candidate in store.lineage(args.experiment, args.candidate)
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
            payload = evaluate_evolution_ablations(store.evaluated(args.experiment))
        print(json.dumps(payload, indent=2))
    elif args.command == "validate":
        payload = run_validation(
            args.seeds,
            args.seed_start,
            suite=args.suite,
        )
        rendered = json.dumps(payload, indent=2)
        if args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(rendered + "\n", encoding="utf-8")
            print(args.output)
        else:
            print(rendered)
    elif args.command in {
        "official-isolated-run",
        "official-isolated-public-run",
    }:
        inventory = None
        games = getattr(args, "games", None)
        if args.command == "official-isolated-public-run":
            project_root = Path(__file__).resolve().parent.parent
            try:
                inventory = inventory_official_environments(
                    args.environments_dir,
                    expected_games=expected_public_game_count(project_root),
                )
            except ValueError as error:
                parser.error(str(error))
            games = inventory.games
        if not games:
            parser.error("isolated official run has no games")
        try:
            isolated_payload = run_process_isolated_games(
                games=games,
                environments_dir=args.environments_dir,
                recordings_dir=args.recordings_dir,
                project_root=Path(__file__).resolve().parent.parent,
                config=args.config,
                max_workers=args.max_workers,
                timeout=args.timeout,
                no_recordings=args.no_recordings,
                lightweight=args.lightweight,
                cognitive_stream_dir=args.cognitive_stream_dir,
            )
        except (RuntimeError, ValueError) as error:
            parser.error(str(error))
        if inventory is not None:
            isolated_payload["environment_inventory"] = inventory.to_dict()
            isolated_payload["coverage"] = {
                "expected_games": inventory.expected_games,
                "discovered_games": len(inventory.games),
                "reported_agents": len(isolated_payload["agents"]),
                "complete": len(isolated_payload["agents"])
                == inventory.expected_games,
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(isolated_payload, indent=2) + "\n",
                encoding="utf-8",
            )
            print(args.output)
        elif args.output is not None:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(isolated_payload, indent=2) + "\n",
                encoding="utf-8",
            )
            print(args.output)
        else:
            print(json.dumps(isolated_payload, indent=2))
    elif args.command == "official-population-run":
        raw_parent = json.loads(args.parent.read_text(encoding="utf-8"))
        if not isinstance(raw_parent, dict) or "candidate_id" not in raw_parent:
            parser.error("--parent must contain a serialized Candidate")
        parent = Candidate.from_dict(raw_parent)
        try:
            population_round = run_official_population_round(
                parent=parent,
                games=args.games,
                environments_dir=args.environments_dir,
                project_root=Path(__file__).resolve().parent.parent,
                max_workers=args.max_workers,
                reruns=args.reruns,
                timeout=args.timeout,
                cognitive_stream_dir=args.cognitive_stream_dir,
            )
        except (RuntimeError, ValueError) as error:
            parser.error(str(error))
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(population_round.to_dict(), indent=2) + "\n",
            encoding="utf-8",
        )
        if args.offspring_output is not None:
            if population_round.offspring is None:
                parser.error(
                    "no offspring qualified; report was written with falsifying "
                    "evidence"
                )
            args.offspring_output.parent.mkdir(parents=True, exist_ok=True)
            args.offspring_output.write_text(
                json.dumps(population_round.offspring.to_dict(), indent=2) + "\n",
                encoding="utf-8",
            )
        print(args.output)
    elif args.command in {"official-run", "official-public-run"}:
        inventory = None
        games = getattr(args, "games", None)
        if args.command == "official-public-run":
            project_root = Path(__file__).resolve().parent.parent
            try:
                inventory = inventory_official_environments(
                    args.environments_dir,
                    expected_games=expected_public_game_count(project_root),
                )
            except ValueError as error:
                parser.error(str(error))
            games = list(inventory.games)
        if not games:
            raise RuntimeError("official run has no games")
        if args.config is not None:
            raw_config = json.loads(args.config.read_text(encoding="utf-8"))
            if not isinstance(raw_config, dict):
                parser.error("--config must contain a JSON object")
            selected_config = raw_config.get("config", raw_config)
            if not isinstance(selected_config, dict):
                parser.error("candidate config must be a JSON object")
            os.environ[CONFIG_ENV] = json.dumps(
                MindConfig.from_dict(selected_config).to_dict(),
                sort_keys=True,
                separators=(",", ":"),
            )
            candidate_id = raw_config.get("candidate_id")
            fingerprint = raw_config.get("inference_fingerprint")
            if isinstance(candidate_id, str):
                os.environ[CANDIDATE_ID_ENV] = candidate_id
            if isinstance(fingerprint, str):
                os.environ[INFERENCE_FINGERPRINT_ENV] = fingerprint
        if args.cognitive_stream_dir is not None:
            os.environ[COGNITIVE_STREAM_DIR_ENV] = str(
                args.cognitive_stream_dir.resolve()
            )
        os.environ["OPERATION_MODE"] = "offline"
        os.environ["ENVIRONMENTS_DIR"] = str(args.environments_dir.resolve())
        os.environ["RECORDINGS_DIR"] = str(args.recordings_dir.resolve())
        with redirect_stdout(sys.stderr):
            swarm_class = getattr(import_module("agents"), "Swarm")
            swarm = swarm_class(
                agent="reflector",
                ROOT_URL="http://localhost:8001",
                games=games,
                record=not args.no_recordings,
            )
            scorecard = swarm.main()
        if scorecard is None:
            raise RuntimeError("official harness returned no scorecard")
        agent_reports = []
        for agent in swarm.agents:
            official_policy: SymbolicPolicy = getattr(agent, "policy")
            decision_distribution = Counter(
                (step.decision.action_id, step.decision.data)
                for step in official_policy.trace.steps
            )
            reason_distribution = Counter(
                step.decision.reason.split(":", 1)[0]
                for step in official_policy.trace.steps
            )
            reason_detail_distribution = Counter(
                step.decision.reason for step in official_policy.trace.steps
            )
            agent_report = {
                "game_id": agent.game_id,
                "actions": agent.action_counter,
                "seconds": agent.seconds,
                "levels_completed": agent.levels_completed,
                "action_counts": dict(sorted(official_policy.action_counts.items())),
                "decision_distribution": [
                    {
                        "action_id": action_id,
                        "data": dict(data),
                        "count": count,
                    }
                    for (
                        action_id,
                        data,
                    ), count in sorted(decision_distribution.items())
                ],
                "reason_counts": dict(sorted(reason_distribution.items())),
                "reason_detail_counts": dict(
                    sorted(reason_detail_distribution.items())
                ),
                "mind_config": official_policy.mind.config.to_dict(),
                "agent_version": official_policy.trace.agent_version,
                "exploration_metrics": official_policy.explorer.to_dict(),
            }
            if not args.lightweight:
                agent_report["trace_metrics"] = evaluate_trace(
                    official_policy.trace
                ).to_dict()
            agent_reports.append(agent_report)
        source_result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent.parent,
            capture_output=True,
            text=True,
            check=False,
        )
        official_payload: dict[str, object] = {
            "scorecard": scorecard.model_dump(mode="json"),
            "agents": agent_reports,
            "source_commit": (
                source_result.stdout.strip() if source_result.returncode == 0 else None
            ),
        }
        if inventory is not None:
            coverage: dict[str, int | bool] = {
                "expected_games": inventory.expected_games,
                "discovered_games": len(inventory.games),
                "reported_agents": len(agent_reports),
                "complete": (
                    len(inventory.games)
                    == inventory.expected_games
                    == len(agent_reports)
                ),
            }
            official_payload["environment_inventory"] = inventory.to_dict()
            official_payload["coverage"] = coverage
            if coverage["complete"] is not True:
                raise RuntimeError(
                    "official public run returned incomplete agent coverage"
                )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(
                json.dumps(official_payload, indent=2) + "\n",
                encoding="utf-8",
            )
            print(args.output)
        else:
            print(json.dumps(official_payload, indent=2))
    elif args.command == "web":
        serve(
            trace=load_trace(args.trace),
            database=args.db,
            static_directory=args.static,
            host=args.host,
            port=args.port,
        )
    else:
        serve(
            trace=demo_trace(),
            database=None,
            static_directory=args.static,
            host=args.host,
            port=args.port,
            workspace=args.workspace,
        )


if __name__ == "__main__":
    main()
