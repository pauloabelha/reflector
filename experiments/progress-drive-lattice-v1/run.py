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


BASE = load("progress_drive_v1_base", HERE.parent / "progress-drive-lattice-v0" / "run.py")
BASE.HERE = HERE
BASE.ARTIFACTS = HERE / "artifacts" / "fresh-1"
BASE.RUNNER.ARTIFACTS = BASE.ARTIFACTS


if __name__ == "__main__":
    raise SystemExit(BASE.main())
