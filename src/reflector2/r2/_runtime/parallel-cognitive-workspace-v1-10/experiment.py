"""v1.10 protocol-vocabulary repair over frozen v1.9."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V19 = HERE.parent / "parallel-cognitive-workspace-v1-9"
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"


def _load() -> Any:
    path = V19 / "experiment.py"
    resolved = path.resolve()
    for existing in reversed(tuple(sys.modules.values())):
        existing_file = getattr(existing, "__file__", None)
        if existing_file is not None and Path(existing_file).resolve() == resolved:
            return existing
    spec = importlib.util.spec_from_file_location("prospective_workspace_v110_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load v1.9 substrate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V19_MODULE = _load()
BASE = V19_MODULE.BASE


def load_config() -> dict[str, Any]:
    config = V19_MODULE.load_config()
    config.update(json.loads((HERE / "config.json").read_text(encoding="utf-8")))
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V19_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        "v1.4/epistemic_graph.py": BASE.LEDGER.file_hash(V14 / "epistemic_graph.py"),
        "v1.10/experiment.py": BASE.LEDGER.file_hash(HERE / "experiment.py"),
        "v1.10/config.json": BASE.LEDGER.file_hash(HERE / "config.json"),
        "v1.10/PROPOSAL.md": BASE.LEDGER.file_hash(HERE / "PROPOSAL.md"),
    }
    body["single_change_from_v1.9"] = (
        "admit prospective-evidence-return in the authoritative graph criticism vocabulary"
    )
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


def main(argv: Sequence[str] | None = None) -> int:
    return int(BASE.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
