"""v1.9 evidence-return bridge over the frozen valid v1.8 experiment."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V18 = HERE.parent / "parallel-cognitive-workspace-v1-8"
V17 = HERE.parent / "parallel-cognitive-workspace-v1-7"
V16 = HERE.parent / "parallel-cognitive-workspace-v1-6"
V15 = HERE.parent / "parallel-cognitive-workspace-v1-5"
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V18_MODULE = _load("prospective_workspace_v19_base", V18 / "experiment.py")
BRIDGE = _load("prospective_workspace_v19_evidence", HERE / "evidence_bridge.py")
LIVE = _load("prospective_workspace_v19_live", HERE / "live_controller.py")
COGNITION = _load("prospective_workspace_v19_cognition", HERE / "evidence_revision.py")
BASE = V18_MODULE.BASE
_INGEST_TRANSITION_GRAPH = BASE.ingest_transition_graph


def _latest_relation_set(state: Any) -> Any | None:
    return max(
        (item for item in state.objects if item.kind == "relation_set"),
        key=lambda item: (item.created_revision, item.object_id),
        default=None,
    )


def _latest_derivation(state: Any, schema_id: str) -> Any | None:
    return max(
        (
            item
            for item in state.objects
            if item.kind == "qwen_derivation"
            and item.created_by == "qwen"
            and schema_id in item.dependency_ids
            and item.identity.get("semantic_object_id") == schema_id
        ),
        key=lambda item: (item.created_revision, item.object_id),
        default=None,
    )


def _return_evidence_as_criticism(
    root: Path,
    workspace_id: str,
    state: Any,
    *,
    after_grid: Any,
    legal: Sequence[int],
    selected_prediction_ids: Sequence[str],
) -> Any:
    schema_ids = sorted(
        {
            schema_id
            for prediction_id in selected_prediction_ids
            for schema_id in (BRIDGE.prediction_schema_id(state, prediction_id),)
            if schema_id is not None
        }
    )
    if not schema_ids:
        return state
    raw_grounding, _figures = BASE.V0.relational_state(after_grid, len(legal), ())
    grounding_state = BRIDGE.action_blind_grounding_state(raw_grounding)
    relation_set = _latest_relation_set(state)
    for schema_id in schema_ids:
        schema = BASE.EG.get_object(state, schema_id)
        derivation = _latest_derivation(state, schema_id)
        if schema is None or derivation is None:
            continue
        packet = BRIDGE.cumulative_evidence_packet(state, schema_id)
        if not packet["rows"]:
            continue
        witness = {
            "protocol": BRIDGE.RETURN_STATUS + "-v1.9",
            "status": BRIDGE.RETURN_STATUS,
            "instruction": (
                "Revise the tested schema in response to exact prospective outcomes. "
                "Local prediction support is not task success; use current relational "
                "evidence to retain, replace, or add conditions that remain uniquely groundable."
            ),
            "effect_variables": list(
                schema.payload.get("preferred_consequence", {}).get("arguments", ())
            ),
            "grounding_state": grounding_state,
            "evidence_packet": packet,
        }
        cited_ids = [*packet["evidence_ids"]]
        if relation_set is not None:
            cited_ids.append(relation_set.object_id)
        link = BASE.QC.explicit_criticism_link(
            derivation.object_id,
            target_schema=schema.payload,
            witness=witness,
            evidence_ids=tuple(cited_ids),
        )
        result = BASE.EG.ingest_structured_criticism(
            state,
            worker="r2",
            target_id=schema_id,
            status=BRIDGE.RETURN_STATUS,
            criticism_key=f"prospective-return:{schema_id}:{BASE.LEDGER.stable_hash(packet)}",
            payload={**dict(link["payload"]), "empirical_support_delta": 0},
            basis_ids=tuple(link["basis_ids"]),
        )
        state = BASE.apply_ingest(root, workspace_id, result)
        criticism_id = result.object_ids[0]
        attention = BASE.EG.attention_event(
            state,
            worker="r2",
            object_id=criticism_id,
            weight=12,
            channel="inspect",
            basis_ids=(schema_id,),
            contribution_key=f"prospective-return-attention:{criticism_id}",
        )
        state = BASE.apply_graph_event(root, workspace_id, state, attention)
    return state


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
    selected_ids = BRIDGE.selected_prediction_objects(state, evidence_dependency_ids)
    selected = BRIDGE.selected_judgments(state, evidence_dependency_ids, judgments)
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
        judgments=selected,
        prospective_evidence=prospective_evidence,
        evidence_dependency_ids=evidence_dependency_ids,
    )
    if selected:
        updated = _return_evidence_as_criticism(
            root,
            workspace_id,
            updated,
            after_grid=after_grid,
            legal=legal,
            selected_prediction_ids=selected_ids,
        )
    return updated


def load_config() -> dict[str, Any]:
    config = V18_MODULE.load_config()
    overlay = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    for key, value in overlay.items():
        if key in {"qwen", "prospective_control"}:
            config[key] = {**config[key], **value}
        else:
            config[key] = value
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    corpus = BASE.CENSUS.select_corpus(
        BASE.CENSUS.DEFAULT_RECORDINGS, BASE.CENSUS.DEFAULT_ENVIRONMENTS
    )
    selected = [item for item in corpus["games"] if item["game"] in set(config["games"])]
    body = {
        "protocol": str(config["workspace_protocol"]),
        "games": list(config["games"]),
        "arms": list(config["arms"]),
        "profiles": sorted(config["profiles"]),
        "environment_inputs": selected,
        "code_sha256": {
            "v1.8/experiment.py": BASE.LEDGER.file_hash(V18 / "experiment.py"),
            **{
                f"v1.9/{name}": BASE.LEDGER.file_hash(HERE / name)
                for name in (
                    "experiment.py",
                    "evidence_bridge.py",
                    "evidence_revision.py",
                    "live_controller.py",
                    "config.json",
                    "PROPOSAL.md",
                )
            },
        },
        "config_sha256": BASE.LEDGER.stable_hash(config),
        "changes_from_v1.8": [
            "prospective evidence creates an exact revision task",
            "only selected predictions receive support/refute edges",
            "four ambiguity probes plus one reserved revision-confirmation probe",
            "64-action causal runway",
        ],
        "forbidden_prior_inputs": list(config["forbidden_inputs"]),
    }
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


COGNITION.install(BASE.QC)
BASE.LC.ProspectiveWorkspaceController = LIVE.ProspectiveWorkspaceController
BASE.ingest_transition_graph = ingest_transition_graph
BASE.HERE = HERE
BASE.ARTIFACTS = HERE / "artifacts"
BASE.load_config = load_config
BASE.build_manifest = build_manifest
BASE._job_key = job_key


def main(argv: Sequence[str] | None = None) -> int:
    return int(BASE.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
