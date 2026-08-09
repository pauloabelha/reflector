from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("progress_goal_cross_selector_test", HERE / "selector.py")
assert SPEC is not None and SPEC.loader is not None
S = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = S
SPEC.loader.exec_module(S)


def test_frozen_metadata_only_selection() -> None:
    receipt = S.select(HERE.parents[1] / "environment_files")
    assert receipt["selected"]["game"] == "g50t"
    assert receipt["selected"]["version"] == "g50t-5849a774"
    assert {row["game"] for row in receipt["candidates"]} == {"g50t", "ls20", "tr87"}
