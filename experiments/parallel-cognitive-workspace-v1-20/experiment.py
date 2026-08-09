"""Two-tier exact-frontier repair over the frozen v1.19 experiment."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V119 = HERE.parent / "parallel-cognitive-workspace-v1-19"


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


V119_MODULE = _load("prospective_workspace_v120_base", V119 / "experiment.py")
POLICY = _load("prospective_workspace_v120_frontier", HERE / "mandatory_frontier.py")
BASE = V119_MODULE.BASE


def load_config() -> dict[str, Any]:
    config = V119_MODULE.load_config()
    overlay = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    for key, value in overlay.items():
        if key == "profiles":
            config[key] = {
                **config[key],
                **{
                    profile: {**config[key].get(profile, {}), **settings}
                    for profile, settings in value.items()
                },
            }
        elif key == "qwen":
            config[key] = {**config[key], **value}
        else:
            config[key] = value
    return config


CONFIG = load_config()
POLICY.install(
    BASE.EG,
    BASE.QC,
    ceiling=int(
        CONFIG["profiles"][CONFIG["primary_profile"]]["mandatory_frontier_ceiling"]
    ),
)
POLICY.install_exact_context_admission(
    BASE.QC,
    CONFIG["qwen"],
    safety_margin_tokens=int(CONFIG["qwen"]["context_safety_margin_tokens"]),
)


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    body = V119_MODULE.build_manifest(config)
    body = {key: value for key, value in body.items() if key != "manifest_digest"}
    body["code_sha256"] = {
        **dict(body["code_sha256"]),
        **{
            f"v1.20/{name}": BASE.LEDGER.file_hash(HERE / name)
            for name in ("experiment.py", "mandatory_frontier.py", "config.json", "PROPOSAL.md")
        },
    }
    body["changes_from_v1.19"] = [
        "separate 6400-unit optional attention budget from 14000-unit mandatory exact ceiling",
        "retry a failed frontier at its exact measured required size only",
        "exact serving-stack multimodal prompt admission with 512-token safety margin",
        "no semantic, controller, prompt, compiler, schedule, gate, or action-budget change",
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
BASE.evaluate_binary_gate = V119_MODULE.V118_MODULE.evaluate_calibration_gate


def main(argv: Sequence[str] | None = None) -> int:
    effective = tuple(sys.argv[1:] if argv is None else argv)
    V119_MODULE.V118_MODULE.V117_MODULE.validate_cli(effective)
    return int(BASE.main(effective))


if __name__ == "__main__":
    raise SystemExit(main())
