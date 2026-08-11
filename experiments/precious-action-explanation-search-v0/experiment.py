"""CLI for the Precious Action same-state causal experiment."""

from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Any, Mapping, Sequence

import causal_protocol as cp
import branch_runner
import live_controls
import matched_executor
import snapshot_view


HERE = Path(__file__).resolve().parent
REPOSITORY = HERE.parent.parent
ARTIFACTS = HERE / "artifacts"
V0 = HERE.parent / "pcw-v1-16-qwen-executor-v0"
FROZEN_V116 = HERE.parent / "parallel-cognitive-workspace-v1-16"
FROZEN_RESULT = FROZEN_V116 / "artifacts" / "results" / "generic_prospective--ar25--shared_live_qwen.json"
FROZEN_WORKSPACE = FROZEN_V116 / "artifacts" / "workspaces" / "generic_prospective--ar25--shared_live_qwen"


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_v0() -> Any:
    """Load the preserved v0 adapter without copying or modifying it."""

    old_path = str(V0)
    if old_path not in sys.path:
        sys.path.insert(0, old_path)
    return _load_module("precious_action_v0_source", V0 / "experiment.py")


def load_config() -> dict[str, Any]:
    return json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def allocate_attempt_root(
    artifacts: Path, *, manifest_hash: str,
) -> tuple[str, Path]:
    """Allocate an immutable run namespace; never mix stale arm artifacts."""

    runs = artifacts / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    indices = []
    for item in runs.iterdir():
        if not item.is_dir() or not item.name.startswith("run-"):
            continue
        try:
            indices.append(int(item.name.split("-", 2)[1]))
        except (IndexError, ValueError):
            continue
    index = max(indices, default=0) + 1
    attempt_id = f"run-{index:03d}-{manifest_hash[:12]}"
    root = runs / attempt_id
    root.mkdir(parents=False, exist_ok=False)
    return attempt_id, root


def source_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    v0 = load_v0()
    v0_manifest = v0.build_manifest(v0.load_config())
    frozen_files = [
        "README.md", "PLAN.md", "INSIGHT_SOURCE_MAP.md", "config.json",
        "causal_protocol.py", "snapshot_view.py", "matched_executor.py",
        "branch_runner.py", "live_controls.py", "experiment.py",
        "test_causal_protocol.py",
    ]
    body = {
        "protocol": cp.PROTOCOL,
        "config": dict(config),
        "source_sha256": {name: _sha256(HERE / name) for name in frozen_files},
        "source_v0_manifest_hash": v0_manifest["manifest_hash"],
        "source_v0_primitive_set": v0_manifest["executor_primitive_set"],
        "frozen_v116_result_sha256": _sha256(FROZEN_RESULT),
        "authority": {
            "arm_a": "offline exact frozen PCW v1.16 candidate only",
            "arms_b_c_proposal_source": "qwen-executor",
            "commit_authority": "arbiter",
            "empirical_support_authority": "environment",
        },
    }
    return {**body, "manifest_hash": cp.stable_hash(body)}


def _frozen_documents(base: Any) -> tuple[
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]
]:
    events = base.LEDGER.list_events(FROZEN_WORKSPACE)
    decision_events = [item for item in events if item["event_type"] == "ActionDecision"]
    decision_documents = [
        base.LEDGER.read_blob(FROZEN_WORKSPACE, item["payload"]["decision_blob"])
        for item in decision_events
    ]
    history = base._history(events, FROZEN_WORKSPACE)
    return events, decision_events, decision_documents, history


def select_frozen_battlefield(base: Any, config: Mapping[str, Any]) -> tuple[cp.Battlefield, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    events, decision_events, decision_documents, history = _frozen_documents(base)
    result = json.loads(FROZEN_RESULT.read_text(encoding="utf-8"))
    battlefield = cp.select_battlefield(
        decision_documents=decision_documents,
        decision_events=decision_events,
        counterfactual_branches=result["counterfactual_branches"],
        minimum_predecessors=int(config["battlefield"]["minimum_predecessor_transitions"]),
    )
    if battlefield.decision_index >= len(history):
        raise cp.CausalProtocolError("battlefield is outside recorded history")
    if str(history[battlefield.decision_index]["before"]["digest"]) != battlefield.before_digest:
        raise cp.CausalProtocolError("battlefield predecessor does not match history")
    return battlefield, events, decision_documents, history


def _prefix_graph_state(base: Any, events: Sequence[Mapping[str, Any]], cutoff_seq: int) -> Any:
    graph_events: list[Any] = []
    for event in events:
        if int(event["seq"]) >= int(cutoff_seq):
            break
        graph_events.extend(base.graph_events_from_outer(FROZEN_WORKSPACE, event))
    return base.EG.replay(graph_events)


def _workspace_document(state: Any, *, cycle: int) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "bindings": [], "partial_bindings": [], "shadows": [],
        "schemas": [], "explanations": [],
    }
    targets = {
        "r2_binding": "bindings", "binding": "bindings",
        "partial_binding": "partial_bindings", "shadow": "shadows",
        "schema": "schemas", "explanation": "explanations",
    }
    for item in state.objects:
        target = targets.get(str(item.kind))
        if target is None or item.object_id in state._index.invalidated:
            continue
        support, contradiction = state._index.evidence.get(item.object_id, (0, 0))
        grouped[target].append({
            "id": item.object_id,
            "kind": item.kind,
            "identity": item.identity,
            "payload": item.payload,
            "dependencies": list(item.dependency_ids),
            "support": int(support),
            "contradiction": int(contradiction),
        })
    return {
        "cycle": int(cycle),
        "metrics": {"live_graph_objects": sum(len(items) for items in grouped.values())},
        **grouped,
    }


def prepare_battlefield(config: Mapping[str, Any]) -> dict[str, Any]:
    v0 = load_v0()
    _v116, base = v0.load_frozen()
    battlefield, events, decisions, history = select_frozen_battlefield(base, config)
    prefix = history[: battlefield.decision_index]
    current = history[battlefield.decision_index]
    state = _prefix_graph_state(base, events, battlefield.action_decision_seq)
    baseline = decisions[battlefield.decision_index]
    plan = baseline["prospective_plan"]
    legal = sorted({int(item["action_id"]) for item in plan["predictions"]})
    route = cp.executor_route((), legal_actions=legal)
    if route != ("SOLE_POLICY_DECISION_BOUNDARY",):
        raise cp.CausalProtocolError("no-trigger route is not deterministic")

    # Existing PCW predictions and constraints are epistemic inputs, never a
    # competing live policy.  The selected A action is stored separately below.
    snapshot = sys.modules["protocol"].build_snapshot(
        state=state,
        ledger_events=[item for item in events if int(item["seq"]) < battlefield.action_decision_seq],
        legal_actions=legal,
        current_record=current["before"],
        current_grid=current["before_grid"],
        history=prefix,
        r2_workspace=_workspace_document(state, cycle=battlefield.decision_index),
        controller_report=baseline["controller"],
        prediction_matrix=plan["predictions"],
        max_recent_transitions=len(prefix),
        max_bytes=int(config["executor"]["snapshot_max_bytes"]),
    )
    model_snapshot = snapshot_view.compact_model_view(snapshot)
    if int(model_snapshot["encoded_bytes"]) > int(config["executor"]["model_snapshot_max_bytes"]):
        raise cp.CausalProtocolError(
            "MODEL_SNAPSHOT_EXCEEDS_BOUND:"
            f"{model_snapshot['encoded_bytes']} > {config['executor']['model_snapshot_max_bytes']}"
        )
    if any(
        int(item.get("action_id", -1)) == battlefield.baseline_action
        and item.get("selected")
        for item in model_snapshot["r2"]["prospective_prediction_matrix"]
    ):
        raise cp.CausalProtocolError("baseline selection leaked into B/C snapshot")

    manifest = source_manifest(config)
    prefix_identity = [
        {
            "transition_id": item["transition_event_id"],
            "action_id": item["action_id"],
            "data": item.get("data", {}),
            "before": item["before"]["digest"],
            "after": item["after"]["digest"],
        }
        for item in prefix
    ]
    primitive = manifest["source_v0_primitive_set"]
    identity = cp.IdentityEnvelope(
        protocol=cp.PROTOCOL,
        source_commit=str(config["source_commit"]),
        source_manifest_hash=str(manifest["manifest_hash"]),
        config_hash=cp.stable_hash(config),
        primitive_version=str(primitive["version"]),
        primitive_source_hash=str(primitive["source_sha256"]),
        game=str(config["game"]),
        seed=int(config["executor"]["seed"]),
        prefix_transition_count=len(prefix),
        prefix_hash=cp.stable_hash(prefix_identity),
        observation_hash=str(current["before"]["digest"]),
        snapshot_hash=str(snapshot["snapshot_hash"]),
    )
    cp.assert_same_identity([identity, identity])
    artifact = {
        "battlefield": asdict(battlefield),
        "identity": asdict(identity),
        "legal_actions": legal,
        "executor_route": list(route),
        "history_transition_count": len(prefix),
        "graph_revision": int(state.revision),
        "model_snapshot_bytes": int(model_snapshot["encoded_bytes"]),
        "baseline_candidate_sealed_from_executor": True,
    }
    baseline_artifact = {
        "experiment_arm": "arm-a",
        "decision_index": battlefield.decision_index,
        "before_digest": battlefield.before_digest,
        "selected_action": battlefield.baseline_action,
        "fallback_action": battlefield.fallback_action,
        "decision": baseline["decision"],
        "prospective_plan": plan,
        "source_event_id": battlefield.action_decision_event_id,
    }
    _write_json(ARTIFACTS / "protocol" / "manifest.json", manifest)
    _write_json(ARTIFACTS / "battlefield" / "battlefield.json", artifact)
    _write_json(ARTIFACTS / "battlefield" / "decision-snapshot.json", snapshot)
    _write_json(ARTIFACTS / "battlefield" / "model-snapshot.json", model_snapshot)
    _write_json(ARTIFACTS / "arm-a" / "candidate.json", baseline_artifact)
    return artifact


def run_controls(config: Mapping[str, Any]) -> dict[str, Any]:
    positive = cp.adjudicate_verdict(
        identity_ok=True, replay_ok=True, b_valid=True, c_valid=True,
        c_treatment=cp.TreatmentResult(True, "PYTHON_EXECUTOR", ()),
        computation_changed_action=True,
        c_checkpoint_brier=0.05, b_checkpoint_brier=0.25,
        c_progress=1, b_progress=0, c_information=1, b_information=0,
        c_hard_risk_regression=False,
    )
    negative = cp.adjudicate_verdict(
        identity_ok=True, replay_ok=True, b_valid=True, c_valid=True,
        c_treatment=cp.TreatmentResult(True, "PYTHON_EXECUTOR", ()),
        computation_changed_action=False,
        c_checkpoint_brier=0.25, b_checkpoint_brier=0.05,
        c_progress=0, b_progress=1, c_information=0, b_information=1,
        c_hard_risk_regression=False,
    )
    inconclusive = cp.adjudicate_verdict(
        identity_ok=True, replay_ok=True, b_valid=True, c_valid=True,
        c_treatment=cp.TreatmentResult(False, "PYTHON_EXECUTOR", ("PYTHON_MODE_NOT_SELECTED",)),
        computation_changed_action=False,
        c_checkpoint_brier=None, b_checkpoint_brier=None,
        c_progress=None, b_progress=None, c_information=None, b_information=None,
        c_hard_risk_regression=False,
    )
    empty_history_rejected = False
    try:
        cp.validate_history_dependencies(["t000"], transition_ids=[])
    except cp.CausalProtocolError:
        empty_history_rejected = True
    no_trigger = cp.executor_route([], legal_actions=[1, 2])
    result = {
        "verdict_fixtures": {
            "positive": positive.status == cp.POSITIVE,
            "negative": negative.status == cp.NEGATIVE,
            "inconclusive": inconclusive.status == cp.INCONCLUSIVE,
        },
        "empty_history_false_claim_rejected": empty_history_rejected,
        "no_trigger_routes_to_executor": no_trigger == ("SOLE_POLICY_DECISION_BOUNDARY",),
        "no_legal_route_empty": cp.executor_route([], legal_actions=[]) == (),
    }
    result["passed"] = all(result["verdict_fixtures"].values()) and all(
        bool(value) for key, value in result.items()
        if key not in {"verdict_fixtures", "passed"}
    )
    _write_json(ARTIFACTS / "controls" / "causal-controls.json", result)
    return result


def run_live_controls(config: Mapping[str, Any]) -> dict[str, Any]:
    battlefield = prepare_battlefield(config)
    snapshot = json.loads(
        (ARTIFACTS / "battlefield" / "decision-snapshot.json").read_text(encoding="utf-8")
    )
    v0 = load_v0()
    v116, base = v0.load_frozen()
    frozen_config = v116.load_config()
    model_config = {**dict(frozen_config["qwen"]), **dict(config["executor"])}
    manifest_hash = str(battlefield["identity"]["source_manifest_hash"])
    root = ARTIFACTS / "controls" / f"live-{manifest_hash[:12]}"
    root.mkdir(parents=True, exist_ok=False)
    fifo = base.QC.ResidentServerQueue(
        str(frozen_config["qwen"]["endpoint"]),
        timeout=float(config["executor"]["request_timeout_seconds"]),
    )
    try:
        result = live_controls.run(
            fifo=fifo, sandbox=sys.modules["analysis_sandbox"],
            model_config=model_config, python_config=config["python"],
            full_snapshot=snapshot, artifact_root=root,
        )
    finally:
        fifo.stop(drain=True)
    _write_json(ARTIFACTS / "controls" / "LIVE-LATEST.json", {
        "manifest_hash": manifest_hash,
        "relative_path": str(root.relative_to(ARTIFACTS)),
        "summary_hash": cp.stable_hash(result),
    })
    return result


def _selected_action(proposal: Mapping[str, Any] | None, legal: Sequence[int]) -> int | None:
    if proposal is None:
        return None
    return cp.validate_decision_coherence(proposal, legal_actions=legal)


def run_matched_experiment(config: Mapping[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    deadline = started + int(config["runtime"]["global_deadline_seconds"])
    finalization_at = deadline - int(config["runtime"]["finalization_reserve_seconds"])
    battlefield_artifact = prepare_battlefield(config)
    attempt_id, attempt_root = allocate_attempt_root(
        ARTIFACTS,
        manifest_hash=str(battlefield_artifact["identity"]["source_manifest_hash"]),
    )
    _write_json(attempt_root / "battlefield.json", battlefield_artifact)
    _write_json(
        attempt_root / "manifest.json",
        json.loads((ARTIFACTS / "protocol" / "manifest.json").read_text(encoding="utf-8")),
    )
    _write_json(
        attempt_root / "RUN.json",
        {
            "attempt_id": attempt_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "RUNNING",
        },
    )
    full_snapshot = json.loads(
        (ARTIFACTS / "battlefield" / "decision-snapshot.json").read_text(encoding="utf-8")
    )
    model_snapshot = json.loads(
        (ARTIFACTS / "battlefield" / "model-snapshot.json").read_text(encoding="utf-8")
    )
    identity = battlefield_artifact["identity"]
    _write_json(attempt_root / "arm-b" / "identity.json", identity)
    _write_json(attempt_root / "arm-c" / "identity.json", identity)
    cp.assert_same_identity([
        cp.IdentityEnvelope(**identity), cp.IdentityEnvelope(**identity)
    ])

    v0 = load_v0()
    v116, base = v0.load_frozen()
    frozen_config = v116.load_config()
    battlefield, _events, _decisions, history = select_frozen_battlefield(base, config)
    frozen_result = json.loads(FROZEN_RESULT.read_text(encoding="utf-8"))
    recorded_branch = next(
        item for item in frozen_result["counterfactual_branches"]
        if int(item["decision_index"]) == battlefield.decision_index
    )
    # Qualify the exact environment prefix before either new model call. This
    # branch is the offline frozen-A comparator, never a live B/C policy head.
    arm_a_branch = branch_runner.run_exact_branch(
        base=base,
        game=str(config["game"]),
        environments=base.CENSUS.DEFAULT_ENVIRONMENTS,
        recordings=attempt_root / "recordings",
        prefix=history[: battlefield.decision_index],
        action_id=battlefield.baseline_action,
        arm="arm-a",
        expected_before_digest=battlefield.before_digest,
        effect_pair=recorded_branch.get("effect_pair", ()),
    )
    arm_a_exact = (
        arm_a_branch.after_digest == str(recorded_branch["actual"]["after_digest"])
    )
    _write_json(
        attempt_root / "counterfactuals" / "arm-a.json", asdict(arm_a_branch)
    )
    if not arm_a_exact:
        raise cp.CausalProtocolError("FROZEN_A_BRANCH_REPLAY_FAILED")
    model_config = {**dict(frozen_config["qwen"]), **dict(config["executor"])}
    fifo = base.QC.ResidentServerQueue(
        str(frozen_config["qwen"]["endpoint"]),
        timeout=float(config["executor"]["request_timeout_seconds"]),
    )
    executor_results: dict[str, matched_executor.MatchedExecutorResult] = {}
    live_failures: dict[str, str] = {}
    try:
        for arm in ("arm-b", "arm-c"):
            if time.monotonic() >= finalization_at:
                live_failures[arm] = "GLOBAL_DEADLINE_FINALIZATION_RESERVE"
                break
            writer = lambda name, value, arm=arm: _write_json(
                attempt_root / arm / name, value
            )
            worker = matched_executor.MatchedExecutor(
                fifo=fifo,
                sandbox=sys.modules["analysis_sandbox"],
                model_config=model_config,
                python_config=config["python"],
                artifact_writer=writer,
            )
            try:
                executor_results[arm] = worker.deliberate(
                    arm=arm, full_snapshot=full_snapshot,
                    model_snapshot=model_snapshot,
                )
                _write_json(
                    attempt_root / arm / "result.json",
                    asdict(executor_results[arm]),
                )
            except Exception as error:
                live_failures[arm] = f"{type(error).__name__}: {error}"
                _write_json(
                    attempt_root / arm / "failure.json",
                    {"arm": arm, "error": live_failures[arm]},
                )
    finally:
        fifo.stop(drain=True)

    legal = [int(item) for item in battlefield_artifact["legal_actions"]]
    selected = {
        arm: _selected_action(result.proposal, legal)
        for arm, result in executor_results.items()
    }
    can_branch = (
        set(executor_results) == {"arm-b", "arm-c"}
        and selected.get("arm-b") is not None
        and selected.get("arm-c") is not None
        and executor_results["arm-c"].treatment.engaged
    )
    branch_results: dict[str, branch_runner.BranchResult] = {"arm-a": arm_a_branch}
    evaluations: dict[str, dict[str, Any]] = {}
    replay_ok = False
    if can_branch:
        actions = {
            "arm-b": int(selected["arm-b"]),
            "arm-c": int(selected["arm-c"]),
        }
        for arm, action in actions.items():
            branch_results[arm] = branch_runner.run_exact_branch(
                base=base,
                game=str(config["game"]),
                environments=base.CENSUS.DEFAULT_ENVIRONMENTS,
                recordings=attempt_root / "recordings",
                prefix=history[: battlefield.decision_index],
                action_id=action,
                arm=arm,
                expected_before_digest=battlefield.before_digest,
                effect_pair=recorded_branch.get("effect_pair", ()),
            )
            _write_json(
                attempt_root / "counterfactuals" / f"{arm}.json",
                asdict(branch_results[arm]),
            )
        replay_ok = (
            all(item.prefix_exact for item in branch_results.values())
            and arm_a_exact
        )
        for arm in ("arm-b", "arm-c"):
            evaluations[arm] = branch_runner.evaluate_executor_branch(
                result=branch_results[arm],
                proposal=executor_results[arm].proposal,
            )
            _write_json(
                attempt_root / "counterfactuals" / f"{arm}-evaluation.json",
                evaluations[arm],
            )

    b_valid = "arm-b" in executor_results and selected.get("arm-b") is not None
    c_valid = "arm-c" in executor_results and selected.get("arm-c") is not None
    c_treatment = (
        executor_results["arm-c"].treatment
        if "arm-c" in executor_results
        else cp.TreatmentResult(False, "PYTHON_EXECUTOR", (live_failures.get("arm-c", "C_RESULT_MISSING"),))
    )
    verdict = cp.adjudicate_verdict(
        identity_ok=True,
        replay_ok=replay_ok,
        b_valid=b_valid,
        c_valid=c_valid,
        c_treatment=c_treatment,
        computation_changed_action=(
            can_branch and selected.get("arm-b") != selected.get("arm-c")
        ),
        c_checkpoint_brier=(
            evaluations.get("arm-c", {}).get("checkpoint_result", {}).get("brier_loss")
        ),
        b_checkpoint_brier=(
            evaluations.get("arm-b", {}).get("checkpoint_result", {}).get("brier_loss")
        ),
        c_progress=(None if "arm-c" not in branch_results else branch_results["arm-c"].progress_delta),
        b_progress=(None if "arm-b" not in branch_results else branch_results["arm-b"].progress_delta),
        c_information=(None if "arm-c" not in branch_results else branch_results["arm-c"].information_novelty),
        b_information=(None if "arm-b" not in branch_results else branch_results["arm-b"].information_novelty),
        c_hard_risk_regression=(
            False if not can_branch else (
                branch_results["arm-c"].hard_risk and not branch_results["arm-b"].hard_risk
            )
        ),
    )
    system_comparisons = {
        arm: asdict(cp.adjudicate_executor_vs_baseline(
            label=f"{arm.upper()}_VS_A",
            identity_ok=True,
            replay_ok=replay_ok,
            executor_valid=(arm in executor_results and selected.get(arm) is not None),
            action_changed=(can_branch and selected.get(arm) != battlefield.baseline_action),
            executor_progress=(
                None if arm not in branch_results else branch_results[arm].progress_delta
            ),
            baseline_progress=branch_results["arm-a"].progress_delta,
            executor_information=(
                None if arm not in branch_results else branch_results[arm].information_novelty
            ),
            baseline_information=branch_results["arm-a"].information_novelty,
            hard_risk_regression=(
                False if not can_branch else (
                    branch_results[arm].hard_risk and not branch_results["arm-a"].hard_risk
                )
            ),
        ))
        for arm in ("arm-b", "arm-c")
    }
    summary = {
        "protocol": cp.PROTOCOL,
        "attempt_id": attempt_id,
        "manifest_hash": identity["source_manifest_hash"],
        "battlefield": battlefield_artifact,
        "selected_actions": selected,
        "treatment": {
            arm: asdict(item.treatment) for arm, item in executor_results.items()
        },
        "live_failures": live_failures,
        "branches_executed": sorted(branch_results),
        "arm_a_exact_replay": arm_a_exact,
        "matched_branch_replay": replay_ok,
        "exact_replay": replay_ok,
        "evaluations": evaluations,
        "verdict": asdict(verdict),
        "system_comparisons": system_comparisons,
        "elapsed_s": time.monotonic() - started,
        "finalized_before_reserve": time.monotonic() < finalization_at,
    }
    _write_json(attempt_root / "RUN.json", {
        "attempt_id": attempt_id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "FINALIZED",
        "verdict": summary["verdict"],
    })
    _write_json(attempt_root / "SUMMARY.json", summary)
    _write_json(ARTIFACTS / "SUMMARY.json", summary)
    _write_json(ARTIFACTS / "LATEST.json", {
        "attempt_id": attempt_id,
        "relative_path": str(attempt_root.relative_to(ARTIFACTS)),
        "manifest_hash": identity["source_manifest_hash"],
        "summary_hash": cp.stable_hash(summary),
    })
    return summary


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--controls", action="store_true")
    modes.add_argument("--prepare-battlefield", action="store_true")
    modes.add_argument("--live-controls", action="store_true")
    modes.add_argument("--run", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    config = load_config()
    if args.dry_run:
        output = source_manifest(config)
        _write_json(ARTIFACTS / "protocol" / "manifest.json", output)
    elif args.controls:
        output = run_controls(config)
    elif args.prepare_battlefield:
        output = prepare_battlefield(config)
    elif args.live_controls:
        output = run_live_controls(config)
    else:
        output = run_matched_experiment(config)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
