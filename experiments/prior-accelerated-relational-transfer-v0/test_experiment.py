from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("prior_relational_transfer", HERE / "experiment.py")
assert SPEC is not None and SPEC.loader is not None
EXPERIMENT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPERIMENT
SPEC.loader.exec_module(EXPERIMENT)


def scene(*, mobile_x: int = 2, differing_y: int = 10) -> tuple[tuple[int, ...], ...]:
    grid = [[0 for _x in range(20)] for _y in range(20)]

    def square(x0: int, y0: int, primary: int, center: int | None = None) -> None:
        for y in range(y0, y0 + 3):
            for x in range(x0, x0 + 3):
                grid[y][x] = primary
        if center is not None:
            grid[y0 + 1][x0 + 1] = center

    square(mobile_x, 2, 2)
    square(10, 10, 3)
    square(2, differing_y, 4, 5)
    return tuple(tuple(row) for row in grid)


def test_palette_invariant_layout_motif() -> None:
    signature = EXPERIMENT.layout_signature(scene())

    assert len(signature["motif_groups"]) == 1
    group = signature["motif_groups"][0]
    assert group["group_size"] == 3
    assert group["same_layout_pairs"] == 1
    assert group["different_layout_pairs"] == 2


def test_joint_effect_tracks_coupled_figures_with_different_vectors() -> None:
    before = scene()
    after = scene(mobile_x=3, differing_y=9)

    effects = EXPERIMENT.joint_effects(before, after)

    assert effects
    assert effects[0].vector == (1, 0)
    assert effects[0].differing_vector == (0, -1)
    assert effects[0].decreases is True


def test_prior_needs_local_confirmation_then_overrides_fallback() -> None:
    controller = EXPERIMENT.RelationalController(("transferred-self-built",))
    before = scene()
    after = scene(mobile_x=3, differing_y=9)

    first = controller.choose(before, (1, 2))
    assert first.action_id == 1
    assert first.reason == "prior-bound-awaiting-local-consequence"

    learned = controller.observe(1, before, after, completed_level=False)
    assert learned["local_confirmation"] is True

    second = controller.choose(after, (1, 2))
    assert second.fallback_action_id == 2
    assert second.action_id == 1
    assert second.reason == "locally-confirmed-decrease"
    assert controller.report()["overrides"] == 1


def test_unbound_prior_exactly_matches_scratch_fallback() -> None:
    blank = tuple(tuple(0 for _x in range(8)) for _y in range(8))
    scratch = EXPERIMENT.RelationalController(())
    prior = EXPERIMENT.RelationalController(("externally-proposed",))

    assert scratch.choose(blank, (2, 3)).action_id == prior.choose(blank, (2, 3)).action_id == 2
    assert prior.report()["prior_decisions"] == 0


def test_external_confirmation_preserves_provenance() -> None:
    controller = EXPERIMENT.RelationalController(("externally-proposed",))
    controller.observe(1, scene(), scene(mobile_x=3, differing_y=9), completed_level=False)

    assert controller.report()["provenance_states"] == [
        "externally-proposed",
        "externally-proposed-and-locally-confirmed",
    ]


def test_atomic_json_replaces_complete_document(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    EXPERIMENT.atomic_json(path, {"history": [1]})
    EXPERIMENT.atomic_json(path, {"history": [1, 2], "pending": None})

    assert json.loads(path.read_text()) == {"history": [1, 2], "pending": None}
    assert not list(tmp_path.glob(".checkpoint.json.*"))


def test_source_schema_is_action_agnostic(tmp_path: Path) -> None:
    if not EXPERIMENT.DEFAULT_SOURCE.exists():
        pytest.skip("configured real source recording is unavailable")

    schema = EXPERIMENT.learn_source_schema(
        EXPERIMENT.DEFAULT_SOURCE, tmp_path / "schema.json", minimum_suffix=2
    )

    assert schema["admitted"] is True
    assert schema["evidence_count"] >= 2
    identity = {
        "body": schema["body"],
        "effect": schema["effect"],
        "joint_effect": schema["joint_effect"],
        "provenance": schema["provenance"],
        "schema_language": schema["schema_language"],
    }
    encoded = EXPERIMENT.stable_json(identity)
    assert "arc-action" not in encoded
    assert "ar25" not in encoded
    assert "source_local_action" not in encoded
