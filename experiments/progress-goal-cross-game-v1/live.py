from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

SELECTOR = load("progress_goal_cross_selector", HERE / "selector.py")
RUNNER = load("progress_goal_cross_runner", HERE.parent / "progress-goal-live-qwen-v1" / "live.py")
PROTOCOL = load("progress_goal_cross_protocol", HERE.parent / "progress-goal-live-qwen-v5" / "goal_protocol.py")
RUNNER.HERE = HERE
RUNNER.ARTIFACTS = HERE / "artifacts" / "fresh-1"
RUNNER.GP = PROTOCOL

if __name__ == "__main__":
    receipt = SELECTOR.select(ROOT / "environment_files")
    RUNNER.atomic_json(RUNNER.ARTIFACTS / "SELECTION_RECEIPT.json", receipt)
    raise SystemExit(RUNNER.main())
