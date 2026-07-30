"""Run a research-only symbolic control on official offline environments."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from contextlib import redirect_stdout
from importlib import import_module
from pathlib import Path
from typing import Any

from .official_eval import (
    expected_public_game_count,
    inventory_official_environments,
)


def run_control(
    *,
    games: tuple[str, ...],
    environments_dir: Path,
    recordings_dir: Path,
    action_budget: int,
) -> dict[str, Any]:
    """Evaluate each game in a fresh process and merge scorecard fields."""

    if action_budget < 1:
        raise ValueError("action budget must be positive")
    reports: list[dict[str, Any]] = []
    agent_reports: list[dict[str, Any]] = []
    for game in games:
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "reflector.research.symbolic_control_eval",
                "--environments-dir",
                str(environments_dir.resolve()),
                "--recordings-dir",
                str((recordings_dir / game).resolve()),
                "--action-budget",
                str(action_budget),
                "--child-game",
                game,
            ],
            cwd=Path(__file__).resolve().parents[2],
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(f"control harness failed for {game}: {detail}")
        json_lines = [
            line for line in completed.stdout.splitlines() if line.startswith("{")
        ]
        if not json_lines:
            raise RuntimeError(
                f"control harness returned no JSON for {game}: "
                f"{completed.stdout.strip()}"
            )
        child = json.loads(json_lines[-1])
        reports.append(child["environment"])
        agent_reports.append(child["agent"])

    project_root = Path(__file__).resolve().parents[2]
    source = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    status = subprocess.run(
        ["git", "status", "--short"],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )
    implementation_paths = (
        project_root / "reflector" / "research" / "symbolic_controls.py",
        project_root / "agents" / "templates" / "symbolic_graph_control.py",
    )
    implementation_sha256 = hashlib.sha256(
        b"".join(path.read_bytes() for path in implementation_paths)
    ).hexdigest()
    return {
        "kind": "research-symbolic-control-evaluation",
        "control": {
            "name": "object-graph-frontier-v1",
            "class": "purely-symbolic",
            "deterministic": True,
            "action_budget_per_game": action_budget,
            "training_on_official_games": False,
            "deployed_candidate": False,
        },
        "scorecard": {
            "score": sum(item["score"] for item in reports) / len(reports),
            "environments": reports,
            "total_environments_completed": sum(
                bool(item["completed"]) for item in reports
            ),
            "total_environments": len(reports),
            "total_levels_completed": sum(
                int(item["levels_completed"]) for item in reports
            ),
            "total_levels": sum(int(item["level_count"]) for item in reports),
            "total_actions": sum(int(item["actions"]) for item in reports),
        },
        "agents": agent_reports,
        "source_commit": (
            source.stdout.strip() if source.returncode == 0 else None
        ),
        "source_worktree_dirty": bool(status.stdout.strip()),
        "implementation_sha256": implementation_sha256,
        "execution": {
            "isolation": "one fresh Python process per game",
            "games": list(games),
        },
        "claim_boundary": (
            "Paired local public-development control; not a Kaggle score and "
            "not evidence about hidden-game generalization."
        ),
    }


def _run_one_control(
    *,
    game: str,
    environments_dir: Path,
    recordings_dir: Path,
    action_budget: int,
) -> dict[str, Any]:
    os.environ["OPERATION_MODE"] = "offline"
    os.environ["ENVIRONMENTS_DIR"] = str(environments_dir.resolve())
    os.environ["RECORDINGS_DIR"] = str(recordings_dir.resolve())
    os.environ["REFLECTOR_CONTROL_ACTION_BUDGET"] = str(action_budget)
    agents_module = import_module("agents")
    agent_module = import_module("agents.templates.symbolic_graph_control")
    agents_module.AVAILABLE_AGENTS["symbolic-graph-control"] = getattr(
        agent_module, "SymbolicGraphControlAgent"
    )
    swarm_class = getattr(agents_module, "Swarm")
    with redirect_stdout(sys.stderr):
        swarm = swarm_class(
            agent="symbolic-graph-control",
            ROOT_URL="http://localhost:8001",
            games=[game],
            record=False,
        )
        scorecard = swarm.main()
    if scorecard is None or len(swarm.agents) != 1:
        raise RuntimeError(f"control harness failed for {game}")
    report = scorecard.model_dump(mode="json")
    environments = report.get("environments", [])
    if len(environments) != 1:
        raise RuntimeError(f"control returned invalid coverage for {game}")
    agent = swarm.agents[0]
    return {
        "environment": environments[0],
        "agent": {
            "game_id": game,
            "actions": agent.action_counter,
            "levels_completed": agent.levels_completed,
            "control_metrics": agent.policy.metrics(),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--environments-dir", type=Path, required=True)
    parser.add_argument("--recordings-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--games", nargs="*")
    parser.add_argument("--action-budget", type=int, default=400)
    parser.add_argument("--child-game", help=argparse.SUPPRESS)
    args = parser.parse_args()

    if args.child_game:
        print(
            json.dumps(
                _run_one_control(
                    game=args.child_game,
                    environments_dir=args.environments_dir,
                    recordings_dir=args.recordings_dir,
                    action_budget=args.action_budget,
                )
            )
        )
        return
    if args.output is None:
        parser.error("--output is required")
    project_root = Path(__file__).resolve().parents[2]
    inventory = inventory_official_environments(
        args.environments_dir,
        expected_games=expected_public_game_count(project_root),
    )
    games = (
        tuple(sorted(set(args.games)))
        if args.games
        else inventory.games
    )
    unknown = sorted(set(games) - set(inventory.games))
    if unknown:
        parser.error(f"unknown public games: {', '.join(unknown)}")
    payload = run_control(
        games=games,
        environments_dir=args.environments_dir,
        recordings_dir=args.recordings_dir,
        action_budget=args.action_budget,
    )
    payload["environment_inventory"] = inventory.to_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
