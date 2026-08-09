from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("progress_goal_lab_test", HERE / "lab.py")
assert SPEC is not None and SPEC.loader is not None
LAB = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LAB
SPEC.loader.exec_module(LAB)


def figure(outline, interior, area, anchor, width, height):
    cells = tuple((x, y) for y in range(height) for x in range(width))
    return SimpleNamespace(
        outline=outline,
        interior_pattern=interior,
        area=area,
        anchor=anchor,
        normalized_cells=cells,
    )


def test_visual_grounder_finds_repeated_items_distinct_actor_and_exact_capacity() -> None:
    figures = (
        figure("shared", ((1, 1),), 4, (2, 2), 2, 2),
        figure("shared", ((1, 1),), 4, (6, 2), 2, 2),
        figure("shared", ((0, 0),), 4, (10, 2), 2, 2),
        figure("target", ((1, 0),), 8, (2, 8), 4, 2),
        figure("hud", (), 12, (0, 15), 12, 1),
    )
    roles = LAB.infer_roles(figures)
    assert roles["actor"]["id"] == "f02"
    assert [item["id"] for item in roles["items"]] == ["f00", "f01"]
    assert roles["container"]["id"] == "f03"
    assert LAB.target_slots(roles) == ((2, 8), (4, 8))

