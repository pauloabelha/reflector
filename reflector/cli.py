"""Local CLI for trace generation, replay, evaluation, and comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evaluation import compare_traces, evaluate_trace
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
    else:
        traces = {path.stem: load_trace(path) for path in args.traces}
        print(json.dumps(compare_traces(traces), indent=2))


if __name__ == "__main__":
    main()
