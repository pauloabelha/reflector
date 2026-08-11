"""Deadline-bounded breadth experiment for the Reflector II 2.1 controller.

The parent process launches every episode in a fresh interpreter so monkey
patches, situated bindings, Qwen queues, and environment state cannot leak
between games.  The R2.1 episode itself retains supported mechanic knowledge
across level boundaries, as required by the architecture.
"""

from __future__ import annotations

import argparse
from collections import defaultdict, deque
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
R21_DIR = REPO / "experiments" / "explanation-guided-one-action-control-v0"
R21_EXPERIMENT = R21_DIR / "experiment.py"
ENVIRONMENTS = REPO / "environment_files"


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + f".tmp-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def r21_source_hashes() -> dict[str, str]:
    paths = [*sorted(R21_DIR.glob("*.py")), R21_DIR / "config.json", REPO / "R2_1.md"]
    return {str(path.relative_to(REPO)): file_hash(path) for path in paths}


def game_tags(game: str) -> tuple[str, ...]:
    metadata = next((ENVIRONMENTS / game).glob("*/metadata.json"))
    return tuple(json.loads(metadata.read_text(encoding="utf-8")).get("tags", ()))


def discover_games() -> list[str]:
    return sorted(path.name for path in ENVIRONMENTS.iterdir() if path.is_dir())


def breadth_order(games: Iterable[str]) -> list[str]:
    """Interleave control modalities so early deadline cuts remain diverse."""
    buckets: dict[str, deque[str]] = defaultdict(deque)
    for game in sorted(games):
        tags = set(game_tags(game))
        bucket = "mixed" if "keyboard_click" in tags else (
            "keyboard" if "keyboard" in tags else "click" if "click" in tags else "other"
        )
        buckets[bucket].append(game)
    order: list[str] = []
    keys = ("keyboard", "click", "mixed", "other")
    while any(buckets.values()):
        for key in keys:
            if buckets[key]:
                order.append(buckets[key].popleft())
    return order


def load_r21() -> Any:
    spec = importlib.util.spec_from_file_location("r21_breadth_worker", R21_EXPERIMENT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {R21_EXPERIMENT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compact_result(result: dict[str, Any], *, game: str, level: int) -> dict[str, Any]:
    wanted = (
        "actions", "levels_completed", "first_level_completed", "elapsed_s",
        "stop_reason", "replay_verified", "support_authority_violations",
        "qwen_calls", "qwen_total_tokens", "qwen_valid_compilations",
        "qwen_changed_decisions", "qwen_transport_successful", "initial_digest",
        "final_digest", "workspace_head",
    )
    row = {key: result.get(key) for key in wanted}
    row.update({
        "game": game,
        "start_level": level,
        "status": "complete",
        "r2_1_experiment_sha256": file_hash(R21_EXPERIMENT),
        "r2_1_config_sha256": file_hash(R21_DIR / "config.json"),
        "r2_1_source_hashes": r21_source_hashes(),
        "source_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True,
            capture_output=True, check=False,
        ).stdout.strip(),
    })
    return row


def worker(game: str, level: int, artifact_root: Path, result_path: Path) -> int:
    started = time.monotonic()
    try:
        result = load_r21().run_game(game, level=level, artifact_root=artifact_root)
        row = compact_result(result, game=game, level=level)
        row["worker_elapsed_s"] = round(time.monotonic() - started, 3)
        atomic_json(result_path, row)
        return 0
    except BaseException as error:
        atomic_json(result_path, {
            "game": game,
            "start_level": level,
            "status": "error",
            "error_type": type(error).__name__,
            "error": str(error),
            "traceback": traceback.format_exc(),
            "worker_elapsed_s": round(time.monotonic() - started, 3),
        })
        return 1


def aggregate(rows: list[dict[str, Any]], *, run_id: str, started_at: str, deadline_s: int) -> dict[str, Any]:
    completed = [row for row in rows if row.get("status") == "complete"]
    return {
        "protocol": "r2.1-kaggle-breadth-v0",
        "run_id": run_id,
        "started_at": started_at,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "global_deadline_seconds": deadline_s,
        "runs_started": len(rows),
        "runs_completed": len(completed),
        "runs_timed_out": sum(row.get("status") == "timeout" for row in rows),
        "runs_errored": sum(row.get("status") == "error" for row in rows),
        "games_attempted": sorted({str(row["game"]) for row in rows}),
        "games_clearing_a_level": sorted({
            str(row["game"]) for row in completed if int(row.get("levels_completed") or 0) > 0
        }),
        "total_levels_completed": sum(int(row.get("levels_completed") or 0) for row in completed),
        "total_actions": sum(int(row.get("actions") or 0) for row in completed),
        "replay_failures": sum(row.get("replay_verified") is False for row in completed),
        "authority_violations": sum(int(row.get("support_authority_violations") or 0) for row in completed),
        "rows": rows,
    }


def run_batch(args: argparse.Namespace) -> int:
    games = breadth_order(discover_games())
    run_id = args.run_id or datetime.now(timezone.utc).strftime("run-%Y%m%dT%H%M%SZ")
    root = HERE / "artifacts" / run_id
    root.mkdir(parents=True, exist_ok=False)
    started_at = datetime.now(timezone.utc).isoformat()
    started = time.monotonic()
    finalization_at = started + args.global_seconds - args.reserve_seconds
    manifest = {
        "protocol": "r2.1-kaggle-breadth-v0",
        "run_id": run_id,
        "preregistered_games": games,
        "schedule": "modality-interleaved breadth pass, then deeper start-level passes if time remains",
        "episode_isolation": "fresh interpreter and artifact root per game/start-level",
        "global_deadline_seconds": args.global_seconds,
        "finalization_reserve_seconds": args.reserve_seconds,
        "per_run_timeout_seconds": args.per_run_seconds,
        "controller_continues_across_levels": True,
        "r2_1_document_sha256": file_hash(REPO / "R2_1.md"),
        "r2_1_experiment_sha256": file_hash(R21_EXPERIMENT),
        "r2_1_config_sha256": file_hash(R21_DIR / "config.json"),
        "source_revision": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO, text=True, capture_output=True, check=False
        ).stdout.strip(),
        "started_at": started_at,
    }
    atomic_json(root / "manifest.json", manifest)
    rows: list[dict[str, Any]] = []
    pass_index = 0
    while time.monotonic() < finalization_at:
        pass_index += 1
        start_level = pass_index
        launched_this_pass = 0
        for game in games:
            remaining = finalization_at - time.monotonic()
            if remaining < 30:
                break
            launched_this_pass += 1
            run_name = f"pass-{pass_index:02d}--{game}--level-{start_level:02d}"
            run_root = root / "episodes" / run_name
            result_path = root / "outcomes" / f"{run_name}.json"
            result_path.parent.mkdir(parents=True, exist_ok=True)
            command = [
                sys.executable, str(Path(__file__).resolve()), "--worker",
                "--game", game, "--level", str(start_level),
                "--artifact-root", str(run_root), "--result-path", str(result_path),
            ]
            episode_started = time.monotonic()
            log_path = root / "logs" / f"{run_name}.log"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.Popen(
                    command, cwd=REPO, stdout=log, stderr=subprocess.STDOUT, text=True
                )
                timeout = max(1.0, min(float(args.per_run_seconds), remaining))
                try:
                    return_code = process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=15)
                    row = {
                        "game": game, "start_level": start_level, "status": "timeout",
                        "worker_elapsed_s": round(time.monotonic() - episode_started, 3),
                        "artifact_root": str(run_root.relative_to(REPO)),
                    }
                    atomic_json(result_path, row)
                else:
                    if result_path.exists():
                        row = json.loads(result_path.read_text(encoding="utf-8"))
                    else:
                        row = {
                            "game": game, "start_level": start_level, "status": "error",
                            "error": f"worker exited {return_code} without an outcome",
                        }
                    row["return_code"] = return_code
                    row["artifact_root"] = str(run_root.relative_to(REPO))
            row["log"] = str(log_path.relative_to(REPO))
            rows.append(row)
            summary = aggregate(rows, run_id=run_id, started_at=started_at, deadline_s=args.global_seconds)
            atomic_json(root / "summary.json", summary)
            print(json.dumps({
                "run": run_name, "status": row.get("status"),
                "levels_completed": row.get("levels_completed"),
                "actions": row.get("actions"), "elapsed_s": row.get("worker_elapsed_s"),
            }, sort_keys=True), flush=True)
        if launched_this_pass < len(games):
            break
    summary = aggregate(rows, run_id=run_id, started_at=started_at, deadline_s=args.global_seconds)
    summary["finished_at"] = datetime.now(timezone.utc).isoformat()
    summary["wall_elapsed_s"] = round(time.monotonic() - started, 3)
    atomic_json(root / "summary.json", summary)
    print(json.dumps(summary, indent=2, sort_keys=True), flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--game")
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--artifact-root", type=Path)
    parser.add_argument("--result-path", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--global-seconds", type=int, default=27_300)
    parser.add_argument("--reserve-seconds", type=int, default=900)
    parser.add_argument("--per-run-seconds", type=int, default=900)
    parser.add_argument("--list-games", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.list_games:
        print("\n".join(breadth_order(discover_games())))
        return 0
    if args.worker:
        if not args.game or args.artifact_root is None or args.result_path is None:
            raise SystemExit("--worker requires --game, --artifact-root, and --result-path")
        return worker(args.game, args.level, args.artifact_root, args.result_path)
    if args.global_seconds <= args.reserve_seconds:
        raise SystemExit("global deadline must exceed finalization reserve")
    return run_batch(args)


if __name__ == "__main__":
    raise SystemExit(main())
