"""v1.14 typed grounding criticism over the frozen v1.13 experiment."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V113 = HERE.parent / "parallel-cognitive-workspace-v1-13"


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


V113_MODULE = _load("prospective_workspace_v114_base", V113 / "experiment.py")
DIAGNOSTICS = _load("prospective_workspace_v114_diagnostics", HERE / "grounding_diagnostics.py")
FEEDBACK = _load("prospective_workspace_v114_feedback", HERE / "compiler_feedback.py")
BASE = V113_MODULE.BASE

# Install cognition projections after the inherited packet/strict-response
# adapters, then persist rejected semantic writes before task integration.
DIAGNOSTICS.install(BASE.QC)
FEEDBACK.install(BASE.QC)
BASE.apply_qwen_compilation = FEEDBACK.wrap_apply_qwen_compilation(
    BASE.EG,
    BASE.QC,
    BASE.apply_qwen_compilation,
    BASE.apply_ingest,
)


def load_config() -> dict[str, Any]:
    config = V113_MODULE.load_config()
    config.update(json.loads((HERE / "config.json").read_text(encoding="utf-8")))
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V113_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        **{
            f"v1.14/{name}": BASE.LEDGER.file_hash(HERE / name)
            for name in (
                "experiment.py",
                "grounding_diagnostics.py",
                "compiler_feedback.py",
                "config.json",
                "PROPOSAL.md",
            )
        },
    }
    body["changes_from_v1.13"] = [
        "complete action-free predicate-to-effect-pair grounding diagnostics",
        "probe-derived relative-motion control-leverage diagnostics",
        "durable support-free compiler feedback for rejected semantic revisions",
        "closed-world validation only for complete nontruncated relation populations",
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


BASE.HERE = HERE
BASE.ARTIFACTS = HERE / "artifacts"
BASE.load_config = load_config
BASE.build_manifest = build_manifest
BASE._job_key = job_key


def main(argv: Sequence[str] | None = None) -> int:
    return int(BASE.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())
