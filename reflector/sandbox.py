"""Clean, optionally network-isolated validation of deployable candidates."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .evaluation import TraceMetrics, evaluate_trace
from .mind import MindConfig
from .policy import SymbolicPolicy
from .population import Fitness
from .trace import EpisodeTrace


@dataclass(frozen=True, slots=True)
class ValidationReport:
    fitness: Fitness
    details: dict[str, dict[str, Any]]
    deterministic: bool
    network_isolated: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "fitness": self.fitness.to_dict(),
            "details": self.details,
            "deterministic": self.deterministic,
            "network_isolated": self.network_isolated,
        }


def _aggregate(metrics: dict[str, TraceMetrics]) -> Fitness:
    count = len(metrics)
    if count == 0:
        raise ValueError("candidate validation requires at least one trace")
    values = tuple(metrics.values())
    return Fitness(
        # Holdouts repeat recorded outcomes, so never count them as new levels.
        levels_advanced=sum(
            item.levels_advanced
            for name, item in metrics.items()
            if "::color-" not in name
        ),
        deterministic_replay_rate=sum(
            item.deterministic_replay_rate for item in values
        )
        / count,
        mean_schema_reliability=sum(
            item.mean_schema_reliability for item in values
        )
        / count,
        planner_expansions=sum(item.planner_expansions for item in values),
        schema_description_length=sum(
            item.schema_description_length for item in values
        ),
    )


def evaluate_candidate(
    config: MindConfig, traces: dict[str, EpisodeTrace]
) -> ValidationReport:
    factory = lambda: SymbolicPolicy(config)  # noqa: E731
    first = {
        name: evaluate_trace(trace, factory)
        for name, trace in sorted(traces.items())
    }
    second = {
        name: evaluate_trace(trace, factory)
        for name, trace in sorted(traces.items())
    }
    deterministic = first == second
    if not deterministic:
        raise RuntimeError("candidate evaluation was nondeterministic")
    return ValidationReport(
        fitness=_aggregate(first),
        details={name: metric.to_dict() for name, metric in first.items()},
        deterministic=True,
        network_isolated=False,
    )


def validate_candidate(
    config: MindConfig,
    traces: dict[str, EpisodeTrace],
    *,
    network_disabled: bool = True,
    timeout: float = 30.0,
) -> ValidationReport:
    """Validate in a fresh process, using a Linux network namespace by default."""

    project_root = Path(__file__).resolve().parent.parent
    with tempfile.TemporaryDirectory(prefix="reflector-candidate-") as temporary:
        directory = Path(temporary)
        input_path = directory / "input.json"
        output_path = directory / "output.json"
        input_path.write_text(
            json.dumps(
                {
                    "config": config.to_dict(),
                    "traces": {
                        name: trace.to_json()
                        for name, trace in sorted(traces.items())
                    },
                },
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        command = [
            sys.executable,
            "-m",
            "reflector.sandbox",
            "--worker",
            str(input_path),
            str(output_path),
        ]
        isolated = False
        if network_disabled:
            unshare = shutil.which("unshare")
            if unshare is None:
                raise RuntimeError(
                    "network-disabled validation requires Linux unshare"
                )
            command = [unshare, "-Urn", "--", *command]
            isolated = True
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": str(project_root),
            "PYTHONHASHSEED": "0",
            "LANG": "C.UTF-8",
        }
        completed = subprocess.run(
            command,
            cwd=project_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "candidate sandbox failed: "
                + (completed.stderr.strip() or completed.stdout.strip())
            )
        raw = json.loads(output_path.read_text(encoding="utf-8"))
    return ValidationReport(
        fitness=Fitness.from_dict(raw["fitness"]),
        details=raw["details"],
        deterministic=raw["deterministic"],
        network_isolated=isolated,
    )


def _worker(input_path: Path, output_path: Path) -> None:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    report = evaluate_candidate(
        MindConfig.from_dict(payload["config"]),
        {
            name: EpisodeTrace.from_json(value)
            for name, value in payload["traces"].items()
        },
    )
    output_path.write_text(
        json.dumps(report.to_dict(), sort_keys=True),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", nargs=2, metavar=("INPUT", "OUTPUT"))
    args = parser.parse_args()
    if args.worker is None:
        parser.error("--worker is required")
    _worker(Path(args.worker[0]), Path(args.worker[1]))


if __name__ == "__main__":
    main()
