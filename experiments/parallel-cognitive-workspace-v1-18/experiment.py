"""Unique-binding calibration repair over the frozen v1.17 experiment."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V117 = HERE.parent / "parallel-cognitive-workspace-v1-17"


def _load(name: str, path: Path) -> Any:
    resolved = path.resolve()
    for existing in reversed(tuple(sys.modules.values())):
        existing_file = getattr(existing, "__file__", None)
        if existing_file is not None and Path(existing_file).resolve() == resolved:
            return existing
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V117_MODULE = _load("prospective_workspace_v118_base", V117 / "experiment.py")
CALIBRATION = _load("prospective_workspace_v118_calibration", HERE / "calibration_controller.py")
BASE = V117_MODULE.BASE
LIVE_OWNER = sys.modules[BASE.LC.ProspectiveWorkspaceController.__module__]
CALIBRATION.install(BASE, LIVE_OWNER)

INGEST_OWNER = sys.modules[BASE.ingest_transition_graph.__module__]
_INGEST_TRANSITION_GRAPH = BASE.ingest_transition_graph


def ingest_transition_graph(
    root: Path,
    workspace_id: str,
    state: Any,
    cognition: Any,
    *,
    transition_id: str,
    before_grid: Any,
    after_grid: Any,
    before_record: Mapping[str, Any],
    after_record: Mapping[str, Any],
    legal: Sequence[int],
    intervention_ref: str,
    judgments: Sequence[Mapping[str, str]] = (),
    prospective_evidence: Mapping[str, Any] | None = None,
    evidence_dependency_ids: Sequence[str] = (),
) -> Any:
    selected_ids = INGEST_OWNER.BRIDGE.selected_prediction_objects(
        state, evidence_dependency_ids
    )
    rows = () if prospective_evidence is None else prospective_evidence.get("judgments", ())
    calibration_rows = [
        dict(item)
        for item in rows
        if isinstance(item, Mapping)
        and item.get("status") == "unresolved"
        and item.get("reason") == "no-prospective-model"
        and item.get("observed_delta") is not None
    ]
    updated = _INGEST_TRANSITION_GRAPH(
        root,
        workspace_id,
        state,
        cognition,
        transition_id=transition_id,
        before_grid=before_grid,
        after_grid=after_grid,
        before_record=before_record,
        after_record=after_record,
        legal=legal,
        intervention_ref=intervention_ref,
        judgments=judgments,
        prospective_evidence=prospective_evidence,
        evidence_dependency_ids=evidence_dependency_ids,
    )
    if not selected_ids or not calibration_rows:
        return updated
    evidence = max(
        (item for item in updated.objects if item.kind == "environment_evidence"),
        key=lambda item: (item.created_revision, item.object_id),
    )
    for row in calibration_rows:
        updated, _sample_id = BASE.ensure_graph_object(
            root,
            workspace_id,
            updated,
            kind="calibration_sample",
            created_by="r2",
            identity={
                "evidence_id": evidence.object_id,
                "prediction_id": row.get("prediction_id"),
            },
            payload={
                "protocol": "unique-binding-calibration-v1.18",
                "intervention_ref": intervention_ref,
                "binding_id": row.get("binding_id"),
                "prediction_id": row.get("prediction_id"),
                "observed_delta": row.get("observed_delta"),
                "observed_residual": row.get("observed_residual"),
                "direct": True,
                "model_created": True,
                "epistemic_support_delta": 0,
            },
            dependency_ids=tuple(sorted({evidence.object_id, *selected_ids})),
            event_key=f"calibration-sample:{evidence.object_id}:{row.get('prediction_id')}",
        )
    return INGEST_OWNER._return_evidence_as_criticism(
        root,
        workspace_id,
        updated,
        before_grid=before_grid,
        after_grid=after_grid,
        legal=legal,
        selected_prediction_ids=selected_ids,
    )


BASE.ingest_transition_graph = ingest_transition_graph


def load_config() -> dict[str, Any]:
    config = V117_MODULE.load_config()
    overlay = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    for key, value in overlay.items():
        if key in {"qwen", "prospective_control"}:
            config[key] = {**config[key], **value}
        else:
            config[key] = value
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V117_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        **{
            f"v1.18/{name}": BASE.LEDGER.file_hash(HERE / name)
            for name in ("experiment.py", "calibration_controller.py", "config.json", "PROPOSAL.md")
        },
    }
    body["changes_from_v1.17"] = [
        "support-free unique-binding opaque-action calibration",
        "direct zero action effects retained as invariant models",
        "calibration evidence returned as structured criticism",
        "one additional evidence-reading Qwen boundary at action 32",
    ]
    return {**body, "manifest_digest": BASE.LEDGER.stable_hash(body)}


def job_key(
    game: str,
    arm: str,
    profile_id: str,
    config: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> str:
    return BASE.LEDGER.stable_hash(
        {
            "protocol": config["workspace_protocol"],
            "game": game,
            "arm": arm,
            "profile": profile_id,
            "config": config,
            "manifest_digest": manifest["manifest_digest"],
        }
    )


def evaluate_calibration_gate(
    results: Sequence[Mapping[str, Any]], config: Mapping[str, Any]
) -> dict[str, Any]:
    del config
    by_arm = {str(item["arm_id"]): item for item in results}
    if set(by_arm) != {"r2_only", "shared_live_qwen"}:
        return {"verdict": "INVALID", "reasons": ["paired-arm-result-missing"]}
    control = by_arm["r2_only"]
    shared = by_arm["shared_live_qwen"]
    validity = {
        "same_initial_digest": control.get("initial_digest") == shared.get("initial_digest"),
        "factual_replay": bool(control.get("replay_verified"))
        and bool(shared.get("replay_verified")),
        "counterfactual_replay": bool(shared.get("counterfactual_exact")),
        "context": bool(shared.get("qwen_context_valid")),
        "transport": bool(shared.get("qwen_transport_successful"))
        and int(shared.get("qwen_valid_compilations", 0))
        == int(shared.get("qwen_calls", 0)),
        "support_authority": int(control.get("support_authority_violations", 0)) == 0
        and int(shared.get("support_authority_violations", 0)) == 0,
    }
    invalid = [name for name, value in validity.items() if not value]
    if invalid:
        return {"verdict": "INVALID", "validity": validity, "reasons": invalid}
    chain = dict(shared.get("prospective_chain", {}))
    kinds = dict(shared.get("graph_metrics", {}).get("object_kinds", {}))
    groundings = list(shared.get("groundings", ()))
    gates = {
        "unique_live_qwen_binding": any(
            item.get("status") == "bound" and int(item.get("effect_pair_count", 0)) == 1
            for item in groundings
        ),
        "direct_support_free_calibration_sample": int(kinds.get("calibration_sample", 0)) > 0,
        "calibration_evidence_return": int(kinds.get("structured_criticism", 0)) > 0,
        "evidence_driven_non_alpha_revision": int(
            chain.get("evidence_citing_revision_derivations", 0)
        )
        > 0,
        "unique_confirmed_revision_binding": int(
            chain.get("confirmed_revision_bindings", 0)
        )
        > 0,
        "revised_control_changed_action": int(
            chain.get("changed_control_decisions", 0)
        )
        > 0,
        "same_state_branch_favorable": int(
            shared.get("counterfactual_favorable_count", 0)
        )
        > 0,
    }
    failed = [name for name, value in gates.items() if not value]
    if failed:
        verdict = "FAIL"
    elif bool(shared.get("first_level_completed")) and (
        not bool(control.get("first_level_completed"))
        or int(shared.get("actions", 0)) <= int(control.get("actions", 0)) * 0.75
    ):
        verdict = "SCORE_PASS"
    else:
        verdict = "MECHANISM_PASS"
    return {"verdict": verdict, "validity": validity, "gates": gates, "reasons": failed}


BASE.HERE = HERE
BASE.ARTIFACTS = HERE / "artifacts"
BASE.load_config = load_config
BASE.build_manifest = build_manifest
BASE._job_key = job_key
BASE.evaluate_binary_gate = evaluate_calibration_gate


def main(argv: Sequence[str] | None = None) -> int:
    effective = tuple(sys.argv[1:] if argv is None else argv)
    V117_MODULE.validate_cli(effective)
    return int(BASE.main(effective))


if __name__ == "__main__":
    raise SystemExit(main())
