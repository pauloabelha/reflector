"""v1.11 condition-wise unbound repair over frozen v1.10."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V110 = HERE.parent / "parallel-cognitive-workspace-v1-10"
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"


def _load() -> Any:
    path = V110 / "experiment.py"
    spec = importlib.util.spec_from_file_location("prospective_workspace_v111_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load v1.10 substrate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V110_MODULE = _load()
BASE = V110_MODULE.BASE


def load_config() -> dict[str, Any]:
    config = V110_MODULE.load_config()
    overlay = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    config.update({key: value for key, value in overlay.items() if key != "qwen"})
    config["qwen"] = {**config["qwen"], **overlay["qwen"]}
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V110_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        "v1.4/ambiguity.py": BASE.LEDGER.file_hash(V14 / "ambiguity.py"),
        "v1.4/qwen_cognition.py": BASE.LEDGER.file_hash(V14 / "qwen_cognition.py"),
        "v1.11/experiment.py": BASE.LEDGER.file_hash(HERE / "experiment.py"),
        "v1.11/config.json": BASE.LEDGER.file_hash(HERE / "config.json"),
        "v1.11/PROPOSAL.md": BASE.LEDGER.file_hash(HERE / "PROPOSAL.md"),
    }
    body["changes_from_v1.10"] = [
        "condition-wise unbound near-miss diagnostics",
        "unique evidence citation grammar",
        "four call sources retimed from 0/12/24/36 to 0/8/16/24",
    ]
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
