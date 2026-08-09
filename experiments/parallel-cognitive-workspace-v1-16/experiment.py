"""v1.16 counterfactual-verification ledger repair over frozen v1.15."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V115 = HERE.parent / "parallel-cognitive-workspace-v1-15"
COUNTERFACTUAL_EVENT = "CounterfactualBranchVerified"


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


V115_MODULE = _load("prospective_workspace_v116_base", V115 / "experiment.py")
BASE = V115_MODULE.BASE
BASE.LEDGER.EVENT_TYPES = frozenset((*BASE.LEDGER.EVENT_TYPES, COUNTERFACTUAL_EVENT))


def load_config() -> dict[str, Any]:
    config = V115_MODULE.load_config()
    config.update(json.loads((HERE / "config.json").read_text(encoding="utf-8")))
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V115_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        **{
            f"v1.16/{name}": BASE.LEDGER.file_hash(HERE / name)
            for name in ("experiment.py", "config.json", "PROPOSAL.md")
        },
    }
    body["single_change_from_v1.15"] = (
        "admit coordinator-authored CounterfactualBranchVerified to the durable ledger"
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
