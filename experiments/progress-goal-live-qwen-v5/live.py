from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent

def load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

RUNNER = load("live_goal_v5_runner_base", HERE.parent / "progress-goal-live-qwen-v1" / "live.py")
PROTOCOL = load("live_goal_v5_protocol", HERE / "goal_protocol.py")
RUNNER.HERE = HERE
RUNNER.ARTIFACTS = HERE / "artifacts" / "fresh-1"
RUNNER.GP = PROTOCOL

if __name__ == "__main__":
    raise SystemExit(RUNNER.main())
