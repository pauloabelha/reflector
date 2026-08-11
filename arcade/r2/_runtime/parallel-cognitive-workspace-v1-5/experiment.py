"""Versioned v1.5 correction for the prospective shared-cognition ar25 gate.

v1.4 correctly stopped before a prompt because prospective environment
evidence redundantly exposed ``action_id``.  The outer ledger already owns that
opaque token and the epistemic graph already links the evidence to an
action-blind action-proposal object.  v1.5 changes only that transport seam.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"


def _load() -> Any:
    path = V14 / "experiment.py"
    spec = importlib.util.spec_from_file_location("prospective_workspace_v15_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load v1.4 substrate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load()
_INGEST_TRANSITION_GRAPH = BASE.ingest_transition_graph


def load_config() -> dict[str, Any]:
    return json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def epistemic_prospective_evidence(
    value: Mapping[str, Any] | None, *, intervention_ref: str
) -> dict[str, Any] | None:
    """Remove the redundant raw token while preserving exact adjudication."""

    if value is None:
        return None
    output = {str(key): item for key, item in value.items() if key != "action_id"}
    output["intervention_ref"] = str(intervention_ref)
    return output


def ingest_transition_graph(*args: Any, **kwargs: Any) -> Any:
    kwargs["prospective_evidence"] = epistemic_prospective_evidence(
        kwargs.get("prospective_evidence"),
        intervention_ref=str(kwargs["intervention_ref"]),
    )
    return _INGEST_TRANSITION_GRAPH(*args, **kwargs)


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    corpus = BASE.CENSUS.select_corpus(
        BASE.CENSUS.DEFAULT_RECORDINGS, BASE.CENSUS.DEFAULT_ENVIRONMENTS
    )
    selected = [
        item for item in corpus["games"] if item["game"] in set(config["games"])
    ]
    base_names = (
        "experiment.py",
        "ledger.py",
        "epistemic_graph.py",
        "ambiguity.py",
        "prospective_control.py",
        "live_controller.py",
        "qwen_cognition.py",
    )
    body = {
        "protocol": str(config["workspace_protocol"]),
        "games": list(config["games"]),
        "arms": list(config["arms"]),
        "profiles": sorted(config["profiles"]),
        "environment_inputs": selected,
        "code_sha256": {
            **{
                f"v1.4/{name}": BASE.LEDGER.file_hash(V14 / name)
                for name in base_names
            },
            "v1.5/experiment.py": BASE.LEDGER.file_hash(HERE / "experiment.py"),
            "v1.5/config.json": BASE.LEDGER.file_hash(HERE / "config.json"),
            "v1.5/PROPOSAL.md": BASE.LEDGER.file_hash(HERE / "PROPOSAL.md"),
        },
        "config_sha256": BASE.LEDGER.stable_hash(config),
        "single_change": "remove raw action_id from epistemic prospective evidence; retain opaque intervention_ref",
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


BASE.HERE = HERE
BASE.ARTIFACTS = HERE / "artifacts"
BASE.load_config = load_config
BASE.build_manifest = build_manifest
BASE._job_key = job_key
BASE.ingest_transition_graph = ingest_transition_graph


def main(argv: Sequence[str] | None = None) -> int:
    return int(BASE.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())

