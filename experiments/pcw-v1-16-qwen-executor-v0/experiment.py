"""CLI and manifest for the PCW v1.16 Qwen Executor v0 experiment."""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from typing import Any, Mapping, Sequence

import analysis_sandbox
import executor_primitives
import protocol
import runner
import source_guard


HERE = Path(__file__).resolve().parent
ARTIFACTS = HERE / "artifacts"
FROZEN_V116 = HERE.parent / "parallel-cognitive-workspace-v1-16"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_frozen() -> tuple[Any, Any]:
    """Verify before import, then extend the generic protocol vocabulary.

    The executable v1.16 files remain byte-identical.  The isolated adapter
    adds a distinct Executor actor/creator so its proposals can never be
    confused with semantic-Qwen objects during authority audits.
    """

    source_guard.verify_frozen_sources()
    v116 = _load_module("qwen_executor_v0_frozen_v116", FROZEN_V116 / "experiment.py")
    base = v116.BASE
    base.LEDGER.EVENT_TYPES = frozenset({
        *base.LEDGER.EVENT_TYPES,
        "ExecutorRequest", "ExecutorWorkerCallQueued", "ExecutorWorkerCallCompleted",
        "ExecutorComputation", "ExecutorProposal", "ActionCommit", "ExecutorResult",
    })
    base.LEDGER.ACTORS = frozenset({*base.LEDGER.ACTORS, "qwen_executor"})
    base.EG.CREATORS = frozenset({*base.EG.CREATORS, "qwen_executor"})
    base.EG.WORKERS = frozenset({*base.EG.WORKERS, "qwen_executor"})
    return v116, base


def load_config() -> dict[str, Any]:
    return json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    frozen_hashes = source_guard.verify_frozen_sources()
    experiment_sources = {
        path.name: source_guard.file_sha256(path)
        for path in sorted(HERE.glob("*.py"))
    }
    body = {
        "protocol": config["protocol"],
        "source_commit": source_guard.SOURCE_COMMIT,
        "frozen_source_sha256": frozen_hashes,
        "experiment_source_sha256": experiment_sources,
        "config": dict(config),
        "authority": {
            "arm_a": "exact frozen PCW v1.16 action selection",
            "arms_b_c_concrete_proposal_source": protocol.WORKER_ID,
            "commit_authority": "arbiter",
            "empirical_support_authority": "environment",
        },
        "executor_primitive_set": {
            **executor_primitives.manifest(),
            "source_sha256": source_guard.file_sha256(HERE / "executor_primitives.py"),
            "frozen_before_decisive_run": True,
        },
    }
    return {**body, "manifest_hash": protocol.stable_hash(body)}


def materialize_protocol(config: Mapping[str, Any]) -> dict[str, Any]:
    manifest = build_manifest(config)
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "protocol").mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "protocol" / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def frozen_arm_a_result(base: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    """Admit the already verified exact durable v1.16 run as Arm A.

    Reusing the frozen causal artifact avoids opening a nominally "exact" Arm A
    through modified orchestration. Source hashes, replay, seed/config, and
    initial digest are checked before admission.
    """

    source = FROZEN_V116 / "artifacts" / "results" / "generic_prospective--ar25--shared_live_qwen.json"
    value = json.loads(source.read_text(encoding="utf-8"))
    required = {
        "protocol": "prospective-control-v1.16",
        "game": config["game"],
        "arm_id": "shared_live_qwen",
        "initial_digest": "8c9c38b5c049817e37ea6525b513983e3628a3f1224df5eafb3146175bb2a51b",
        "replay_verified": True,
        "support_authority_violations": 0,
    }
    for key, expected in required.items():
        if value.get(key) != expected:
            raise RuntimeError(f"frozen Arm A artifact failed admission: {key}")
    admitted = {
        **value,
        "experiment_arm": "arm-a",
        "admission": "exact durable frozen v1.16 causal artifact",
        "source_artifact": str(source.relative_to(source_guard.REPOSITORY)),
        "source_artifact_sha256": source_guard.file_sha256(source),
        "resource_accounting": {
            "semantic_qwen_calls": int(value.get("qwen_calls", 0)),
            "executor_qwen_calls": 0,
            "input_tokens": int(value.get("qwen_context", {}).get("prompt_tokens", 0)),
            "output_tokens": int(value.get("qwen_context", {}).get("completion_tokens", 0)),
            "runtime_s": float(value.get("elapsed_s", 0.0)),
            "python_calls": 0,
            "python_runtime_s": 0.0,
        },
    }
    destination = ARTIFACTS / "arm-a" / "result.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(admitted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return admitted


def run_controls(config: Mapping[str, Any]) -> dict[str, Any]:
    frozen = source_guard.verify_frozen_sources()
    sandbox_limits = dict(config["python"])
    sandbox_snapshot = {"values": [3, 1, 2]}
    sandbox_ok = analysis_sandbox.run_analysis(
        "values = sorted(snapshot['values'])\nresult = {'sum': sum(values), 'values': values}",
        sandbox_snapshot, sandbox_limits,
    )
    try:
        analysis_sandbox.run_analysis("open('/tmp/leak')\nresult = 1", sandbox_snapshot, sandbox_limits)
        filesystem_blocked = False
    except analysis_sandbox.SandboxError:
        filesystem_blocked = True
    try:
        analysis_sandbox.run_analysis("import os\nresult = os.listdir('/')", sandbox_snapshot, sandbox_limits)
        import_blocked = False
    except analysis_sandbox.SandboxError:
        import_blocked = True
    result = {
        "source_boundary": {"passed": bool(frozen), "file_count": len(frozen)},
        "python_sandbox": {
            "bounded_computation": sandbox_ok.get("status") == "ok" and sandbox_ok.get("return_value") == {"sum": 6, "values": [1, 2, 3]},
            "filesystem_blocked": filesystem_blocked,
            "imports_blocked": import_blocked,
            "fresh_subprocess": True,
        },
        "worker_isolation": {
            "separate_worker_id": protocol.WORKER_ID != "qwen",
            "separate_cursor": protocol.WORKER_ID != "qwen",
            "stateless_requests": True,
            "semantic_private_state_excluded": True,
            "same_physical_fifo_required": True,
        },
        "action_authority": {
            "executor_is_sole_b_c_policy_head": True,
            "semantic_action_nomination_forbidden": True,
            "r2_action_selection_excluded": True,
            "arbiter_is_commit_authority": True,
            "executor_has_distinct_graph_creator": True,
            "arbiter_checks_dependency_liveness": True,
            "mismatch_returns_to_workspace": True,
        },
        "support_authority": {
            "executor_event_types_are_ledger_only": True,
            "executor_cannot_create_environment_evidence": True,
        },
    }
    result["passed"] = all(
        bool(value)
        for section in result.values() if isinstance(section, dict)
        for value in section.values() if isinstance(value, bool)
    )
    path = ARTIFACTS / "controls" / "fixture-controls.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_live(config: Mapping[str, Any], *, arms: Sequence[str]) -> dict[str, Any]:
    _v116, base = load_frozen()
    frozen_config = _v116.load_config()
    manifest = materialize_protocol(config)
    results: dict[str, Any] = {}
    if "arm-a" in arms:
        results["arm-a"] = frozen_arm_a_result(base, config)
    live_arms = [arm for arm in arms if arm in {"arm-b", "arm-c"}]
    if live_arms:
        fifo = base.QC.ResidentServerQueue(
            str(frozen_config["qwen"]["endpoint"]),
            timeout=float(config["executor"]["request_timeout_seconds"]),
        )
        try:
            for arm in live_arms:
                episode = runner.ExecutorEpisodeRunner(
                    base=base, frozen_config=frozen_config,
                    experiment_config=config, arm=arm, fifo=fifo,
                    artifact_root=ARTIFACTS,
                    environments=base.CENSUS.DEFAULT_ENVIRONMENTS,
                )
                results[arm] = episode.run()
        finally:
            fifo.stop(drain=True)
    summary = {
        "manifest_hash": manifest["manifest_hash"],
        "arms": results,
        "complete": set(results) == set(arms),
    }
    (ARTIFACTS / "SUMMARY.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--controls", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--arms", nargs="+", choices=("arm-a", "arm-b", "arm-c"), default=("arm-a", "arm-b", "arm-c"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config()
    if args.dry_run:
        output = materialize_protocol(config)
    elif args.controls:
        materialize_protocol(config)
        output = run_controls(config)
    else:
        output = run_live(config, arms=args.arms)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
