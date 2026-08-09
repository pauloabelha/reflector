from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


PATH = Path(__file__).with_name("lattice_progress.py")
SPEC = spec_from_file_location("progress_lattice_test_module", PATH)
L = module_from_spec(SPEC)
sys.modules[SPEC.name] = L
SPEC.loader.exec_module(L)


def grid(actor=(2, 6), transformed=False):
    rows = [[4] * 8 for _ in range(8)]
    for x, y in ((0, 4), (2, 4), (4, 4), (6, 4), (6, 2), (2, 6)):
        for yy in range(y, y + 2):
            for xx in range(x, x + 2):
                rows[yy][xx] = 3
    rows[4][0] = 8  # overlay while most of its traversable substrate remains
    for yy in range(2):
        for xx in range(6, 8):
            rows[yy][xx] = 9  # terminal-like region adjoining the path
    for yy in range(actor[1], actor[1] + 2):
        for xx in range(actor[0], actor[0] + 2):
            rows[yy][xx] = 7 if transformed else 6
    return rows


def test_visual_field_and_action_opaque_itinerary():
    before = grid((2, 6))
    after = grid((2, 4))
    sample = L.motion_sample(before, after, before_anchor=(2, 6), after_anchor=(2, 4), size=(2, 2))
    field = L.infer_progress_field([sample])
    assert field.substrate == 3
    assert field.background == 4
    assert field.overlay_affordances == ((0, 4),)
    assert field.terminal_candidates == ((6, 0),)
    plan = L.plan_progress(field, {(0, -2): 91, (0, 2): 27, (-2, 0): 44, (2, 0): 18})
    assert plan.waypoints == ((0, 4), (6, 0))
    assert plan.actions == (44, 18, 18, 18, 91, 91)


def test_rejects_incomplete_control_basis():
    before = grid((2, 6))
    after = grid((2, 4))
    field = L.infer_progress_field([L.motion_sample(before, after, before_anchor=(2, 6), after_anchor=(2, 4), size=(2, 2))])
    try:
        L.plan_progress(field, {(0, -1): 1})
    except L.ProgressFieldError as error:
        assert "four directions" in str(error)
    else:
        raise AssertionError("incomplete control basis was accepted")
