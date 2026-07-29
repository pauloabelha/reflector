"""Process-isolated parallel execution for attributable official-game evidence."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, Iterable


def _canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()
    ).hexdigest()


def _run_game(
    *,
    game: str,
    environments_dir: Path,
    recordings_dir: Path,
    project_root: Path,
    config: Path | None,
    no_recordings: bool,
    lightweight: bool,
    cognitive_stream_dir: Path | None,
    timeout: float,
    command_runner: Callable[..., subprocess.CompletedProcess[str]],
) -> tuple[str, dict[str, Any]]:
    command = [
        sys.executable,
        "-m",
        "reflector.cli",
        "official-run",
        game,
        "--environments-dir",
        str(environments_dir),
        "--recordings-dir",
        str(recordings_dir / game),
    ]
    if config is not None:
        command.extend(("--config", str(config)))
    if no_recordings:
        command.append("--no-recordings")
    if lightweight:
        command.append("--lightweight")
    if cognitive_stream_dir is not None:
        command.extend(
            ("--cognitive-stream-dir", str(cognitive_stream_dir))
        )
    completed = command_runner(
        command,
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"isolated official game {game} failed: {detail}")
    try:
        report = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"isolated official game {game} returned invalid JSON"
        ) from error
    agents = report.get("agents")
    environments = report.get("scorecard", {}).get("environments")
    if (
        not isinstance(agents, list)
        or len(agents) != 1
        or agents[0].get("game_id") != game
        or not isinstance(environments, list)
        or len(environments) != 1
        or environments[0].get("id", "").split("-", 1)[0] != game
    ):
        raise RuntimeError(
            f"isolated official game {game} returned mismatched coverage"
        )
    return game, report


def run_process_isolated_games(
    *,
    games: Iterable[str],
    environments_dir: Path,
    recordings_dir: Path,
    project_root: Path,
    config: Path | None = None,
    max_workers: int = 4,
    timeout: float = 1800.0,
    no_recordings: bool = True,
    lightweight: bool = True,
    cognitive_stream_dir: Path | None = None,
    command_runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Run each game in a fresh process, in parallel, then merge evidence."""

    selected = tuple(sorted(set(games)))
    if not selected:
        raise ValueError("isolated official execution requires at least one game")
    if max_workers < 1:
        raise ValueError("max_workers must be positive")
    resolved_project = project_root.resolve()
    resolved_environments = environments_dir.resolve()
    resolved_recordings = recordings_dir.resolve()
    resolved_config = config.resolve() if config is not None else None
    resolved_stream = (
        cognitive_stream_dir.resolve()
        if cognitive_stream_dir is not None
        else None
    )
    with ThreadPoolExecutor(max_workers=min(max_workers, len(selected))) as pool:
        futures = [
            pool.submit(
                _run_game,
                game=game,
                environments_dir=resolved_environments,
                recordings_dir=resolved_recordings,
                project_root=resolved_project,
                config=resolved_config,
                no_recordings=no_recordings,
                lightweight=lightweight,
                cognitive_stream_dir=resolved_stream,
                timeout=timeout,
                command_runner=command_runner,
            )
            for game in selected
        ]
        reports = dict(future.result() for future in futures)

    source_commits = {report.get("source_commit") for report in reports.values()}
    if len(source_commits) != 1:
        raise RuntimeError(
            "isolated official games did not use one frozen source commit"
        )
    environments = [
        reports[game]["scorecard"]["environments"][0] for game in selected
    ]
    agents = [reports[game]["agents"][0] for game in selected]
    total_levels = sum(environment["level_count"] for environment in environments)
    scorecard = {
        "source_url": None,
        "tags": ["agent", "reflector", "process-isolated"],
        "opaque": None,
        "card_id": None,
        "api_key": None,
        "score": sum(environment["score"] for environment in environments)
        / len(environments),
        "environments": environments,
        "tags_scores": [],
        "competition_mode": None,
        "total_environments_completed": sum(
            bool(environment["completed"]) for environment in environments
        ),
        "total_environments": len(environments),
        "total_levels_completed": sum(
            environment["levels_completed"] for environment in environments
        ),
        "total_levels": total_levels,
        "total_actions": sum(environment["actions"] for environment in environments),
    }
    return {
        "kind": "process-isolated-official-evaluation",
        "scorecard": scorecard,
        "agents": agents,
        "source_commit": source_commits.pop(),
        "execution": {
            "isolation": "one fresh Python process per game",
            "parallel": True,
            "max_workers": min(max_workers, len(selected)),
            "games": list(selected),
            "child_report_sha256": {
                game: _canonical_hash(reports[game]) for game in selected
            },
            "claim_boundary": (
                "Local official public-development evidence; not a Kaggle "
                "leaderboard score."
            ),
        },
    }
