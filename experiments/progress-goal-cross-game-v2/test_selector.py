from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("progress_goal_cross_v2_selector_test", HERE / "selector.py")
assert SPEC is not None and SPEC.loader is not None
S = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = S
SPEC.loader.exec_module(S)


def test_frozen_target_is_ls20() -> None:
    receipt = S.select(HERE.parents[1] / "environment_files")
    assert receipt["selected"]["game"] == "ls20"
    assert receipt["selected"]["version"] == "ls20-9607627b"
    assert {row["game"] for row in receipt["candidates"]} == {"ls20", "tr87"}
