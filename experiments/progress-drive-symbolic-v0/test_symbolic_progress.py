from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

PATH = Path(__file__).with_name("symbolic_progress.py")
SPEC = spec_from_file_location("symbolic_progress_test", PATH)
S = module_from_spec(SPEC)
sys.modules[SPEC.name] = S
SPEC.loader.exec_module(S)


def stamp(grid, x, y, pattern, background):
    for yy, row in enumerate(pattern):
        for xx, cell in enumerate(row):
            grid[y + yy][x + xx] = 9 if cell else background


def test_example_lookup_is_grounded_and_rotation_invariant():
    grid = [[2] * 40 for _ in range(30)]
    a = ((0,1,0,0,0),(1,1,0,0,0),(0,1,0,0,0),(0,1,0,0,0),(1,1,1,0,0))
    b = ((1,1,0,0,0),(1,0,1,0,0),(1,1,0,0,0),(1,0,1,0,0),(1,0,1,0,0))
    panels = []
    for index, (left, right) in enumerate(((a,b),(b,a))):
        x, y = 2, 2 + index * 7
        panels.append({"origin": [x, y], "size": [17, 7]})
        stamp(grid, x + 1, y + 1, left, 2); stamp(grid, x + 11, y + 1, right, 2)
    for x, pattern in ((3, a), (10, b)):
        stamp(grid, x, 17, pattern, 2)
        stamp(grid, x, 24, a, 2)
    task = S.infer_task(grid, panels, mutation_origin=(3,24))
    assert task.desired == tuple(reversed(task.query))
    doc = S.workspace_document(task)
    assert doc["slot_count"] == 2 and doc["empirical_support"] == 0
    assert S.compile_desired({"protocol": doc["protocol"], "desired_outputs": list(task.desired)}, task) == task.desired
