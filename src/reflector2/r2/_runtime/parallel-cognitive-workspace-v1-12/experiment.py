"""v1.12 compact causal revision over frozen v1.11."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V111 = HERE.parent / "parallel-cognitive-workspace-v1-11"
V19 = HERE.parent / "parallel-cognitive-workspace-v1-9"
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"


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


V111_MODULE = _load("prospective_workspace_v112_base", V111 / "experiment.py")
PACKET = _load("prospective_workspace_v112_packet", HERE / "causal_packet.py")
REVISION = _load("prospective_workspace_v112_response", HERE / "revision_response.py")
BASE = V111_MODULE.BASE
PACKET.install(BASE.QC)
REVISION.install(BASE.QC)


def load_config() -> dict[str, Any]:
    config = V111_MODULE.load_config()
    overlay = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    config.update({key: value for key, value in overlay.items() if key != "qwen"})
    config["qwen"] = {**config["qwen"], **overlay["qwen"]}
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V111_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        "v1.9/experiment.py": BASE.LEDGER.file_hash(V19 / "experiment.py"),
        "v1.4/qwen_cognition.py": BASE.LEDGER.file_hash(V14 / "qwen_cognition.py"),
        **{
            f"v1.12/{name}": BASE.LEDGER.file_hash(HERE / name)
            for name in (
                "experiment.py", "causal_packet.py", "revision_response.py",
                "config.json", "PROPOSAL.md",
            )
        },
    }
    body["changes_from_v1.11"] = [
        "semantically lossless nonrecursive causal revision packet",
        "action-free temporal relation grounding with frame provenance",
        "exclusive revision-or-abstain response contract",
        "completion maximum and reserve 2048 -> 3072",
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
