"""Executable one-action explanation-guided ARC controller."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V116 = HERE.parent / "parallel-cognitive-workspace-v1-16" / "experiment.py"
ARTIFACTS = HERE / "artifacts"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _local(name: str) -> Any:
    return _load(f"one_action_{name}", HERE / f"{name}.py")


V116_MODULE = _load("one_action_frozen_v116", V116)
BASE = V116_MODULE.BASE
SCRATCHPAD = _local("scratchpad")
CONTROLLER = _local("controller")
INTEGRATION = _local("integration")
RUNTIME = _local("runtime")
ARCADE = _local("arcade")
FIRST_FRAME = _local("first_frame")


def load_config() -> dict[str, Any]:
    config = V116_MODULE.load_config()
    override = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(config.get(key), Mapping):
            config[key] = {**dict(config[key]), **dict(value)}
        else:
            config[key] = value
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    sources = {
        path.name: BASE.LEDGER.file_hash(path)
        for path in sorted(HERE.glob("*.py"))
    }
    body = {
        "experiment": config["experiment"],
        "protocol": config["protocol"],
        "base_protocol": "prospective-control-v1.16",
        "sources": sources,
        "config": dict(config),
        "authority": {
            "semantic_hypotheses_and_scratchpad": "qwen",
            "one_action_selection": "r2",
            "action_commit": "arbiter",
            "successor_and_empirical_support": "environment",
        },
    }
    return {**body, "manifest_digest": BASE.LEDGER.stable_hash(body)}


def install(runtime: Any | None = None) -> None:
    SCRATCHPAD.install(BASE.QC)
    if runtime is not None and not getattr(BASE.QC, "_one_action_runtime_scratchpad", False):
        BASE.QC._one_action_runtime_scratchpad = True
        compile_response = BASE.QC.compile_response

        def compile_and_publish(response: Mapping[str, Any], turn: Any) -> dict[str, Any]:
            compilation = compile_response(response, turn)
            if isinstance(compilation.get("working_note"), Mapping):
                runtime.set_qwen_scratchpad(compilation["working_note"])
            accepted = tuple(compilation.get("accepted", ()))
            needs_explanation = getattr(turn, "mode", None) == "initial-full"
            accepted_ok = (
                any(item.get("kind") == "explanation" for item in accepted)
                if needs_explanation else bool(accepted)
            )
            transport_error = response.get("transport_error")
            rejected = tuple(compilation.get("rejected", ()))
            reason = str(transport_error) if transport_error else (
                "no valid frame-0 explanation" if needs_explanation and not accepted_ok else
                str(rejected[0].get("reason")) if rejected else None
            )
            runtime.qwen_finished(
                accepted=accepted_ok,
                reason=reason,
                learn_latency=not bool(transport_error),
            )
            return compilation

        BASE.QC.compile_response = compile_and_publish
    if runtime is not None and not getattr(BASE, "_one_action_runtime_qwen_queue", False):
        BASE._one_action_runtime_qwen_queue = True
        queue_qwen = BASE.queue_qwen

        def queue_and_publish(*args: Any, **kwargs: Any) -> Any:
            pending = queue_qwen(*args, **kwargs)
            task_count = int(args[-2]) if len(args) >= 2 else 0
            source_action = int(args[-1]) if args else 0
            runtime.qwen_started(
                task_count + 1,
                phase="explaining-frame-0" if source_action == 0 else "semantic-update",
            )
            return pending

        BASE.queue_qwen = queue_and_publish
    INTEGRATION.install(BASE)
    FIRST_FRAME.install(BASE, runtime)
    controller_type = CONTROLLER.controller_class(BASE.LC, runtime)

    class ActiveController(controller_type):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            BASE._one_action_active_controller = self

    BASE.LC.ProspectiveWorkspaceController = ActiveController
    if runtime is not None:
        RUNTIME.install_action_hook(BASE, runtime)

    environment_base = BASE.BASE
    if not getattr(environment_base, "_one_action_level_start_installed", False):
        environment_base._one_action_level_start_installed = True
        open_environment = environment_base.open_environment

        def open_at_selected_level(*args: Any, **kwargs: Any) -> Any:
            arcade, environment = open_environment(*args, **kwargs)
            level = int(getattr(environment_base, "_one_action_start_level", 0))
            if level:
                observation = environment.reset()
                total = int(observation.win_levels)
                if level >= total:
                    arcade.close_scorecard()
                    raise ValueError(f"level must be between 1 and {total}")
                environment._game.set_level(level)
                environment._game._action_count = 1
                environment.reset()
            return arcade, environment

        environment_base.open_environment = open_at_selected_level


def configure_base(artifact_root: Path = ARTIFACTS) -> dict[str, Any]:
    config = load_config()
    BASE.HERE = HERE
    BASE.ARTIFACTS = artifact_root
    BASE.load_config = load_config
    BASE.build_manifest = build_manifest

    def job_key(game: str, arm: str, profile_id: str, cfg: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
        return BASE.LEDGER.stable_hash({
            "protocol": cfg["workspace_protocol"], "game": game,
            "arm": arm, "profile": profile_id, "manifest": manifest["manifest_digest"],
        })

    BASE._job_key = job_key
    return config


def run_game(game: str = "ar25", *, level: int = 1, runtime: Any | None = None, artifact_root: Path = ARTIFACTS) -> dict[str, Any]:
    config = configure_base(artifact_root)
    config["start_level"] = int(level)
    install(runtime)
    if level < 1:
        raise ValueError("level must be positive")
    BASE.BASE._one_action_start_level = int(level) - 1
    manifest = build_manifest(config)
    artifact_root.mkdir(parents=True, exist_ok=True)
    BASE.LEDGER.atomic_json(artifact_root / "manifest.json", manifest)
    profile = str(config["primary_profile"])
    payload = {
        "game": game,
        "profile_id": profile,
        "arm_id": "shared_live_qwen",
        "config": config,
        "manifest": manifest,
        "environments": str(BASE.CENSUS.DEFAULT_ENVIRONMENTS),
    }
    fifo = BASE.QC.ResidentServerQueue(
        str(config["qwen"]["endpoint"]),
        timeout=float(config["qwen"]["request_timeout_seconds"]),
    )
    if runtime is not None:
        runtime.update(
            status="starting",
            game=game,
            metadata={
                "r2_version": manifest["experiment"],
                "protocol": manifest["protocol"],
                "manifest_digest": manifest["manifest_digest"],
                "game": game,
                "start_level": int(level),
                "action_budget": int(config["action_budget"]),
            },
            action_budget=int(config["action_budget"]),
        )
    try:
        result = BASE.run_episode(payload, fifo)
        if runtime is not None:
            runtime.update(status="complete", result=result)
        return result
    except Exception as error:
        if runtime is not None and not runtime.reset_requested.is_set():
            runtime.update(status="error", error=f"{type(error).__name__}: {error}")
        raise
    finally:
        fifo.stop(drain=True)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--arcade", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--game", default="ar25")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8767)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dry_run:
        config = configure_base(); install()
        print(json.dumps(build_manifest(config), indent=2, sort_keys=True))
        return 0
    if args.arcade:
        runtime = RUNTIME.LiveRuntime()

        def start(game: str, level: int) -> None:
            try:
                run_root = HERE / "arcade-runs" / f"run-{time.time_ns()}"
                run_game(game, level=level, runtime=runtime, artifact_root=run_root)
            except Exception:
                if not runtime.reset_requested.is_set():
                    traceback.print_exc()

        games = sorted(
            path.name
            for path in Path(BASE.CENSUS.DEFAULT_ENVIRONMENTS).iterdir()
            if path.is_dir()
        )
        ARCADE.serve(
            runtime,
            start,
            games=games,
            runs_root=HERE / "arcade-runs",
            host=args.host,
            port=args.port,
        )
        return 0
    result = run_game(args.game)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
