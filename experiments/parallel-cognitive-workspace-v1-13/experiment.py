"""v1.13 phase-correct revision dispatch over frozen v1.12."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V112 = HERE.parent / "parallel-cognitive-workspace-v1-12"


def _load() -> Any:
    path = V112 / "experiment.py"
    spec = importlib.util.spec_from_file_location("prospective_workspace_v113_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load v1.12 substrate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V112_MODULE = _load()
BASE = V112_MODULE.BASE


def load_config() -> dict[str, Any]:
    config = V112_MODULE.load_config()
    config.update(json.loads((HERE / "config.json").read_text(encoding="utf-8")))
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V112_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        "v1.12/revision_response.py": BASE.LEDGER.file_hash(V112 / "revision_response.py"),
        "v1.13/experiment.py": BASE.LEDGER.file_hash(HERE / "experiment.py"),
        "v1.13/config.json": BASE.LEDGER.file_hash(HERE / "config.json"),
        "v1.13/PROPOSAL.md": BASE.LEDGER.file_hash(HERE / "PROPOSAL.md"),
    }
    body["single_change_from_v1.12"] = (
        "phase-correct strict revision evidence-address contract"
    )
    return {**body, "manifest_digest": BASE.LEDGER.stable_hash(body)}


def job_key(game: str, arm: str, profile_id: str, config: Mapping[str, Any], manifest: Mapping[str, Any]) -> str:
    return BASE.LEDGER.stable_hash({
        "protocol": config["workspace_protocol"], "game": game, "arm": arm,
        "profile": profile_id, "config": config, "manifest_digest": manifest["manifest_digest"],
    })


BASE.HERE = HERE
BASE.ARTIFACTS = HERE / "artifacts"
BASE.load_config = load_config
BASE.build_manifest = build_manifest
BASE._job_key = job_key


def main(argv: Sequence[str] | None = None) -> int:
    return int(BASE.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
