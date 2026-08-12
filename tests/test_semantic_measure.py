from __future__ import annotations

from pathlib import Path

import pytest

from reflector2.planner import BoundedBestFirstPlanner
from reflector2.r2.goal_contract import canonicalize_goal_proposals
from reflector2.r2.r2_1_adapter import FrameSchemaObserver
from reflector2.r2.semantic_measure import (
    SEMANTIC_MEASURE_PROTOCOL,
    SemanticMeasureHypothesis,
    spatial_feature,
)


def entity(binding_id: str, cells: set[tuple[int, int]]) -> dict:
    return {"binding_id": binding_id, "cells": sorted(cells), "value": 1}


def negative_space_measure(**changes: object) -> dict:
    value = {
        "protocol": SEMANTIC_MEASURE_PROTOCOL,
        "left_source": "actor",
        "left_feature": "occupancy",
        "right_source": "target",
        "right_feature": "enclosed_negative_space",
        "comparison": "symmetric_difference_size",
        "coordinate_frame": "scene",
        "include_separation_gap": True,
    }
    value.update(changes)
    return value


def proposed_goal(**changes: object) -> dict:
    value = {
        "verb": "complete",
        "schema_name": "candidate spatial completion",
        "goal_family": "unknown",
        "roles": ["actor", "target"],
        "potential_roles": ["actor", "target"],
        "role_constraints": [],
        "observable": "proposed_spatial_completion_residual",
        "measurement_hypothesis": negative_space_measure(),
        "direction": "decrease",
        "terminal_class": "minimum",
        "terminal_condition": "proposed_spatial_completion_residual=0",
        "local_terminal": {
            "observable": "proposed_spatial_completion_residual",
            "preferred_order": "decrease",
            "relation": "equals",
            "target": 0.0,
        },
    }
    value.update(changes)
    return value


def ring() -> dict:
    return entity("ring", {
        (2, 2), (2, 3), (2, 4),
        (3, 2),         (3, 4),
        (4, 2), (4, 3), (4, 4),
    })


def test_neutral_negative_space_feature_is_geometric_not_lexical():
    assert spatial_feature(ring(), "enclosed_negative_space") == frozenset({(3.0, 3.0)})
    assert len(spatial_feature(ring(), "envelope_negative_space")) == 1


def test_proposed_measure_has_a_scene_gradient_and_exact_terminal():
    hypothesis = SemanticMeasureHypothesis.compile(
        "proposed_spatial_completion_residual", negative_space_measure(),
    )
    far = entity("far", {(8, 8)})
    exact = entity("exact", {(3, 3)})
    assert hypothesis.evaluate(far, ring()) > hypothesis.evaluate(exact, ring())
    assert hypothesis.evaluate(exact, ring()) == 0.0


def test_empty_selected_feature_fails_open_instead_of_becoming_zero():
    hypothesis = SemanticMeasureHypothesis.compile(
        "proposed_spatial_completion_residual", negative_space_measure(),
    )
    solid = entity("solid", {(2, 2), (2, 3), (3, 2), (3, 3)})
    assert hypothesis.evaluate(entity("candidate", {(2, 2)}), solid) is None


@pytest.mark.parametrize("changes", [
    {"protocol": "arbitrary-code-v0"},
    {"left_feature": "color_named_slot"},
    {"comparison": "run_python"},
    {"coordinate_frame": "intrinsic", "include_separation_gap": True},
])
def test_measurement_language_rejects_out_of_contract_constructions(changes):
    with pytest.raises(ValueError):
        SemanticMeasureHypothesis.compile(
            "proposed_candidate_residual", negative_space_measure(**changes),
        )


def test_adapter_compiles_a_model_proposal_without_granting_authority():
    frame = [[0] * 12 for _ in range(12)]
    for y, x in ring()["cells"]:
        frame[y][x] = 2
    frame[8][8] = 1
    observer = FrameSchemaObserver(
        {"enabled": True, "backend": "bounded-best-first-v0"},
        BoundedBestFirstPlanner(),
    )
    observer.fit_frame(frame)
    fitted = observer._bind_verb_schemas([proposed_goal()])
    assert len(fitted) == 1
    assert "proposed_spatial_completion_residual" in observer.semantic_measurements
    assert fitted[0]["r2_role_bindings"]
    # Compilation and measurability are not empirical support or action authority.
    assert all(
        record["prospective"] is False
        for record in observer.last_potential_states.values()
        if record["observable"] == "proposed_spatial_completion_residual"
    )


def test_custom_observable_requires_a_measurement_and_conflicts_fail_closed():
    frame = [[0] * 8 for _ in range(8)]
    frame[1][1] = 1; frame[5][5] = 2
    observer = FrameSchemaObserver({"enabled": False})
    observer.fit_frame(frame)
    assert observer._bind_verb_schemas([
        proposed_goal(measurement_hypothesis=None),
    ]) == []
    assert "requires measurement_hypothesis" in observer.last_rejected_goals[0]["reason"]

    first = proposed_goal()
    second = proposed_goal(
        verb="compare",
        measurement_hypothesis=negative_space_measure(
            right_feature="envelope_negative_space",
        ),
    )
    observer._bind_verb_schemas([first, second])
    assert any("conflicts" in item["reason"] for item in observer.last_rejected_goals)


def test_verb_label_does_not_mandate_an_observable_or_direction():
    frame = [[0] * 8 for _ in range(8)]
    frame[1][1] = 1; frame[5][5] = 2
    observer = FrameSchemaObserver({"enabled": False})
    observer.fit_frame(frame)
    goal = proposed_goal(
        verb="fit",
        goal_family="separation",
        observable="centroid_distance",
        measurement_hypothesis=None,
        direction="increase",
        terminal_class="maximum",
        terminal_condition="maximum",
        local_terminal={
            "observable": "centroid_distance", "preferred_order": "increase",
            "relation": "maximum", "target": None,
        },
    )
    assert observer._bind_verb_schemas([goal])


def test_measurement_definition_is_part_of_control_identity():
    first = proposed_goal()
    second = proposed_goal(
        verb="match",
        measurement_hypothesis=negative_space_measure(
            right_feature="envelope_negative_space",
        ),
    )
    assert len(canonicalize_goal_proposals([first, second])) == 2


def test_prompt_source_contains_no_privileged_fit_mapping_or_game_tokens():
    source = (Path(__file__).parents[1] / "src/reflector2/r2/scratchpad.py").read_text()
    measure_source = (
        Path(__file__).parents[1] / "src/reflector2/r2/semantic_measure.py"
    ).read_text().lower()
    lowered = source.lower()
    assert "fit should use fit_residual" not in lowered
    assert "fit normally decreases fit_residual" not in lowered
    assert "fit requires only" not in lowered
    assert "r2-spatial-set-residual-v0" in source
    for forbidden in ("ar25", "yellow", "blue l", "action_1"):
        assert forbidden not in measure_source
