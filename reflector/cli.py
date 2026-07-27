"""Local CLI for trace generation, replay, evaluation, and comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .compression import analyze_redundancy, counterfactual_replay, replay_policy
from .evaluation import compare_traces, evaluate_ablations, evaluate_trace
from .graph import DependencyGraph
from .policy import SymbolicPolicy
from .symbolic import Observation
from .trace import EpisodeTrace


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
        traces = {path.stem: load_trace(path) for path in args.traces}
        print(json.dumps(compare_traces(traces), indent=2))
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
    else:
        policy = replay_policy(load_trace(args.trace))
        dependency_graph = DependencyGraph.build(
            policy.mind.schemas,
            policy.mind.concepts,
            policy.mind.hypotheses,
        )
        print(json.dumps(dependency_graph.to_dict(), indent=2))


if __name__ == "__main__":
    main()
