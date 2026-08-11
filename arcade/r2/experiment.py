"""Production R2.2 Agent Arcade and headless ARC-AGI-3 controller."""

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
RUNTIME_ROOT = HERE / "_runtime"
V116 = RUNTIME_ROOT / "parallel-cognitive-workspace-v1-16" / "experiment.py"
PROJECT_ROOT = HERE.parents[1]
ARTIFACTS = PROJECT_ROOT / "artifacts" / "r2"


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
ACTION_COMMAND = _local("action_command")
OBSERVATION_ENVELOPE = _local("observation_envelope")
CONTROLLER = _local("controller")
INTEGRATION = _local("integration")
RUNTIME = _local("runtime")
ARCADE = _local("arcade")
FIRST_FRAME = _local("first_frame")
R2_1 = _local("r2_1_adapter")
MODEL_BACKEND = _local("model_backend")


def load_config() -> dict[str, Any]:
    config = V116_MODULE.load_config()
    override = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(config.get(key), Mapping):
            config[key] = {**dict(config[key]), **dict(value)}
        else:
            config[key] = value
    return MODEL_BACKEND.resolve_config(config)


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    sources = {
        str(source.relative_to(PROJECT_ROOT)): BASE.LEDGER.file_hash(source)
        for root in (HERE, RUNTIME_ROOT)
        for source in sorted(root.rglob("*"))
        if source.is_file()
        and (
            source.suffix == ".py"
            or source.name in {"config.json", "PROPOSAL.md", "STATUS.md"}
        )
        and not source.name.startswith("test_")
    }
    body = {
        "experiment": config["experiment"],
        "protocol": config["protocol"],
        "base_protocol": "prospective-control-v1.16",
        "runtime_ownership": "arcade.r2-independent-of-experiments",
        "sources": sources,
        "config": dict(config),
        "authority": {
            "semantic_hypotheses_and_scratchpad": "configured-model",
            "one_action_selection": "r2",
            "action_commit": "arbiter",
            "successor_and_empirical_support": "environment",
        },
        "semantic_model": MODEL_BACKEND.public_metadata(config["model"]),
    }
    return {**body, "manifest_digest": BASE.LEDGER.stable_hash(body)}


def install(runtime: Any | None = None) -> None:
    MODEL_BACKEND.install_token_counter(BASE.QC)
    SCRATCHPAD.install(BASE.QC)
    if not getattr(BASE, "_one_action_explanation_consolidation_due", False):
        BASE._one_action_explanation_consolidation_due = True
        original_qwen_revision_due = BASE.qwen_revision_due

        def qwen_revision_due(state: Any, workspace_id: str, **kwargs: Any) -> bool:
            scratchpad_due = getattr(
                BASE.QC, "epistemic_scratchpad_revision_due", None,
            )
            if callable(scratchpad_due) and scratchpad_due(state, workspace_id):
                return True
            due = getattr(BASE.QC, "explanation_consolidation_due", None)
            if callable(due) and due(state, workspace_id):
                return True
            return original_qwen_revision_due(
                state, workspace_id, **kwargs
            )

        BASE.qwen_revision_due = qwen_revision_due
    if not getattr(BASE, "_one_action_causal_visual_evidence", False):
        BASE._one_action_causal_visual_evidence = True
        visual_evidence_for_turn = BASE.visual_evidence_for_turn

        def causal_visual_evidence_for_turn(*args: Any, **kwargs: Any) -> list[dict[str, str]]:
            return SCRATCHPAD.causal_visual_evidence(
                visual_evidence_for_turn(*args, **kwargs)
            )

        BASE.visual_evidence_for_turn = causal_visual_evidence_for_turn
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
            turn = pending[1]
            consolidating = isinstance(
                getattr(turn, "document", {}).get("explanation_consolidation_task"),
                Mapping,
            )
            runtime.qwen_started(
                task_count + 1,
                phase=(
                    "consolidating-explanation" if consolidating else
                    "explaining-frame-0" if source_action == 0 else
                    "semantic-update"
                ),
            )
            return pending

        BASE.queue_qwen = queue_and_publish
    INTEGRATION.install(BASE)
    FIRST_FRAME.install(BASE, runtime)
    controller_type = CONTROLLER.controller_class(
        BASE.LC,
        runtime,
        fast_path_config=load_config().get("control", {}).get("fast_path", {}),
        action_commands=ACTION_COMMAND,
    )

    class ActiveController(controller_type):
        def __init__(self, **kwargs: Any) -> None:
            super().__init__(**kwargs)
            BASE._one_action_active_controller = self

    BASE.LC.ProspectiveWorkspaceController = ActiveController
    if runtime is not None:
        RUNTIME.install_action_hook(BASE, runtime)

    environment_base = BASE.BASE
    OBSERVATION_ENVELOPE.install(environment_base)
    if runtime is not None:
        runtime.set_observation_envelope_builder(OBSERVATION_ENVELOPE.from_observation)
    if not getattr(environment_base, "_one_action_parameterized_actions_installed", False):
        environment_base._one_action_parameterized_actions_installed = True
        environment_base.simple_legal_actions = ACTION_COMMAND.legal_action_ids
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


def active_runtime(runtime: Any | None = None) -> Any:
    """Return a runtime with the R2.2 observer installed for every run mode.

    The arcade supplies its presentation runtime explicitly.  Headless runs
    need the same epistemic/control substrate even though nobody is polling a
    browser endpoint; otherwise they silently fall back to the inherited PCW
    policy and cannot measure R2.2 at all.
    """
    if runtime is None:
        runtime = RUNTIME.LiveRuntime()
    if getattr(runtime, "schema_observer", None) is None:
        runtime.set_schema_observer(R2_1.FrameSchemaObserver())
    return runtime


def run_game(game: str = "ar25", *, level: int = 1, runtime: Any | None = None, artifact_root: Path = ARTIFACTS) -> dict[str, Any]:
    runtime = active_runtime(runtime)
    config = configure_base(artifact_root)
    MODEL_BACKEND.require_credentials(config["model"])
    config["start_level"] = int(level)
    install(runtime)
    SCRATCHPAD.reset_episode_context()
    if runtime is not None:
        runtime.reset_schema_observer()
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
        str(config["model"]["endpoint"]),
        timeout=float(config["model"]["request_timeout_seconds"]),
        poster=MODEL_BACKEND.build_poster(config["model"]),
    )
    if runtime is not None:
        runtime.update(
            status="starting",
            game=game,
            metadata={
                "r2_version": "R2.2",
                "controller": manifest["experiment"],
                "schema_engine": "parallel-recursive-schema-fitting",
                "protocol": manifest["protocol"],
                "manifest_digest": manifest["manifest_digest"],
                "game": game,
                "start_level": int(level),
                "action_budget": int(config["action_budget"]),
                "action_budget_scope": "per-level" if config.get("reset_action_budget_each_level") else "game",
                "semantic_model": MODEL_BACKEND.public_metadata(config["model"]),
            },
            action_budget=int(config["action_budget"]),
            level_action_budget=int(config["action_budget"]),
            level_turn=0,
            levels_completed=0,
        )
    try:
        result = {
            **BASE.run_episode(payload, fifo),
            "semantic_model": MODEL_BACKEND.public_metadata(config["model"]),
        }
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
    MODEL_BACKEND.add_cli_arguments(parser)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    MODEL_BACKEND.apply_cli_arguments(args)
    if args.dry_run:
        config = configure_base(); install()
        print(json.dumps(build_manifest(config), indent=2, sort_keys=True))
        return 0
    if args.arcade:
        runtime = active_runtime()

        arcade_config = load_config()

        def validate_model(selection: Mapping[str, Any]) -> None:
            MODEL_BACKEND.validate_browser_selection(arcade_config, selection)

        def start(game: str, level: int, selection: Mapping[str, Any]) -> None:
            try:
                with MODEL_BACKEND.browser_model_environment(arcade_config, selection):
                    run_root = ARTIFACTS / "arcade-runs" / f"run-{time.time_ns()}"
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
            runs_root=ARTIFACTS / "arcade-runs",
            model_options=MODEL_BACKEND.browser_options(arcade_config),
            validate_model=validate_model,
            host=args.host,
            port=args.port,
        )
        return 0
    result = run_game(args.game)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
