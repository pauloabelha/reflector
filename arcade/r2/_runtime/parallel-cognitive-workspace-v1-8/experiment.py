"""v1.8 context-capacity wrapper over the frozen v1.7 experiment."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V17 = HERE.parent / "parallel-cognitive-workspace-v1-7"
V16 = HERE.parent / "parallel-cognitive-workspace-v1-6"
V15 = HERE.parent / "parallel-cognitive-workspace-v1-5"
V14 = HERE.parent / "parallel-cognitive-workspace-v1-4"


def _load() -> Any:
    path = V17 / "experiment.py"
    spec = importlib.util.spec_from_file_location("prospective_workspace_v18_base", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load v1.7 substrate: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


V17_MODULE = _load()
BASE = V17_MODULE.BASE


def load_config() -> dict[str, Any]:
    config = V17_MODULE.load_config()
    overlay = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    config.update({key: value for key, value in overlay.items() if key != "qwen"})
    config["qwen"] = {**config["qwen"], **overlay["qwen"]}
    return config


def build_manifest(config: Mapping[str, Any]) -> dict[str, Any]:
    corpus = BASE.CENSUS.select_corpus(
        BASE.CENSUS.DEFAULT_RECORDINGS, BASE.CENSUS.DEFAULT_ENVIRONMENTS
    )
    selected = [item for item in corpus["games"] if item["game"] in set(config["games"])]
    v14_names = (
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
            **{f"v1.4/{name}": BASE.LEDGER.file_hash(V14 / name) for name in v14_names},
            "v1.5/experiment.py": BASE.LEDGER.file_hash(V15 / "experiment.py"),
            "v1.6/experiment.py": BASE.LEDGER.file_hash(V16 / "experiment.py"),
            "v1.7/experiment.py": BASE.LEDGER.file_hash(V17 / "experiment.py"),
            "v1.8/experiment.py": BASE.LEDGER.file_hash(HERE / "experiment.py"),
            "v1.8/config.json": BASE.LEDGER.file_hash(HERE / "config.json"),
            "v1.8/PROPOSAL.md": BASE.LEDGER.file_hash(HERE / "PROPOSAL.md"),
        },
        "config_sha256": BASE.LEDGER.stable_hash(config),
        "single_change_from_v1.7": "Qwen context window 16384 -> 24576 tokens",
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


def main(argv: Sequence[str] | None = None) -> int:
    return int(BASE.main(argv))


if __name__ == "__main__":
    raise SystemExit(main())

