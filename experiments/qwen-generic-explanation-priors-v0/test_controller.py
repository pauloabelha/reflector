from __future__ import annotations

import importlib.util
import sys
from dataclasses import asdict
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("qwen_generic_prior_controller", HERE / "experiment.py")
assert SPEC is not None and SPEC.loader is not None
EXPERIMENT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPERIMENT
SPEC.loader.exec_module(EXPERIMENT)


Grid = tuple[tuple[int, ...], ...]


def scene(*, left_x: int = 2, right_x: int = 10) -> Grid:
    grid = [[0 for _x in range(24)] for _y in range(12)]
    for y in range(2, 5):
        for x in range(left_x, left_x + 3):
            grid[y][x] = 2
        for x in range(right_x, right_x + 3):
            grid[y][x] = 3
    return tuple(tuple(row) for row in grid)


def blank() -> Grid:
    return tuple(tuple(0 for _x in range(24)) for _y in range(12))


def binding(grid: Grid, *, action_deltas: dict[int, list[tuple[int, int]]] | None = None):
    figures = {item.primary_value: item for item in EXPERIMENT.BASE.extract_figures(grid)}
    left = figures[2]
    right = figures[3]
    return EXPERIMENT.PairBinding(
        template_hash="template-test",
        operator="Decrease",
        left_key=left.local_key,
        right_key=right.local_key,
        left_anchor=left.anchor,
        right_anchor=right.anchor,
        relative2=(
            left.centroid2[0] - right.centroid2[0],
            left.centroid2[1] - right.centroid2[1],
        ),
        action_deltas={} if action_deltas is None else action_deltas,
    )


def test_prior_cannot_act_before_target_local_confirmation() -> None:
    controller = EXPERIMENT.PairPotentialController(
        [binding(scene())], provenance="externally-proposed"
    )

    decision = controller.choose((2, 1))

    assert decision.action_id == 1
    assert decision.fallback_action_id == 1
    assert decision.prior_used is False
    assert decision.template_hash is None
    assert decision.reason == "no-locally-confirmed-improvement"
    assert controller.report()["local_confirmations"] == 0


@pytest.mark.parametrize(
    ("after", "expected_delta"),
    [
        (scene(left_x=3, right_x=10), (2, 0)),
        (scene(left_x=4, right_x=11), (2, 0)),
    ],
    ids=("one-mover", "both-movers-relative-delta"),
)
def test_direct_transition_learns_relative_delta_and_can_override(
    after: Grid, expected_delta: tuple[int, int]
) -> None:
    before = scene()
    controller = EXPERIMENT.PairPotentialController(
        [binding(before)], provenance="externally-proposed"
    )

    event = controller.observe(1, before, after)["bindings"][0]
    decision = controller.choose((1, 2))

    assert event == {
        "template_hash": "template-test",
        "direct": True,
        "delta": list(expected_delta),
        "residual": 14,
    }
    assert controller.bindings[0].action_deltas == {1: [expected_delta]}
    assert controller.report()["local_confirmations"] == 1
    assert decision.fallback_action_id == 2
    assert decision.action_id == 1
    assert decision.prior_used is True
    assert decision.residual_before == 14
    assert decision.predicted_residual_after == 12


def test_latent_projection_is_bounded_at_exactly_four_steps() -> None:
    before = scene()
    tracked = binding(before, action_deltas={1: [(2, 0)]})
    controller = EXPERIMENT.PairPotentialController(
        [tracked], provenance="externally-proposed"
    )

    events = [controller.observe(1, before, blank())["bindings"][0] for _ in range(5)]

    assert [event.get("direct") for event in events[:4]] == [False] * 4
    assert all("suspended" not in event for event in events[:4])
    assert events[4] == {
        "template_hash": "template-test",
        "direct": False,
        "suspended": True,
    }
    assert tracked.latent_steps == EXPERIMENT.MAX_LATENT_STEPS == 4
    assert controller.report()["latent_projections"] == 4
    assert controller.report()["local_confirmations"] == 0

    decision = controller.choose((1, 2))
    assert decision.prior_used is False
    assert decision.action_id == decision.fallback_action_id == 2


def test_visible_reappearance_learns_from_actual_before_state_not_latent_prediction() -> None:
    initial = scene()
    tracked = binding(initial, action_deltas={1: [(2, 0)]})
    original_anchors = (tracked.left_anchor, tracked.right_anchor)
    controller = EXPERIMENT.PairPotentialController(
        [tracked], provenance="externally-proposed"
    )

    latent = controller.observe(1, initial, blank())["bindings"][0]
    assert latent["direct"] is False
    assert tracked.relative2 == (-14, 0)
    assert (tracked.left_anchor, tracked.right_anchor) == original_anchors

    # The visible state is one cell ahead of the latent estimate. The next
    # real transition still moves only one cell, so its learned delta is +2,
    # not the +4 correction from the stale latent estimate to the successor.
    visible_before = scene(left_x=4, right_x=10)
    visible_after = scene(left_x=5, right_x=10)
    reappearance = controller.observe(1, visible_before, visible_after)["bindings"][0]

    assert reappearance == {
        "template_hash": "template-test",
        "direct": True,
        "delta": [2, 0],
        "residual": 10,
    }
    assert tracked.action_deltas == {1: [(2, 0), (2, 0)]}
    assert tracked.relative2 == (-10, 0)
    assert tracked.latent_steps == 0
    assert controller.report()["local_confirmations"] == 1


def test_unbound_mismatched_prior_has_byte_identical_fallback_decisions() -> None:
    unbound_grounding = {
        "template_hash": "foreign-template",
        "operator": "Decrease",
        "status": "unbound",
        "effect_pair": None,
    }
    mismatch_bindings = EXPERIMENT.bindings_from_groundings(
        [unbound_grounding], {"entities": [], "relations": []}, ()
    )
    scratch = EXPERIMENT.PairPotentialController((), provenance="scratch")
    mismatch = EXPERIMENT.PairPotentialController(
        mismatch_bindings, provenance="externally-proposed"
    )

    for _index in range(8):
        scratch_decision = scratch.choose((3, 1, 2))
        mismatch_decision = mismatch.choose((3, 1, 2))
        assert asdict(mismatch_decision) == asdict(scratch_decision)

        action = scratch_decision.action_id
        scratch.observe(action, blank(), blank())
        mismatch.observe(action, blank(), blank())

    assert mismatch_bindings == ()
    assert mismatch.report()["prior_decisions"] == scratch.report()["prior_decisions"] == 0
    assert mismatch.report()["action_uses"] == scratch.report()["action_uses"]
