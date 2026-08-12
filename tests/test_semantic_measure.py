from __future__ import annotations

import json
from pathlib import Path

import pytest

from reflector2.planner import BoundedBestFirstPlanner
from reflector2.r2.goal_contract import canonicalize_goal_proposals
from reflector2.r2.r2_1_adapter import FrameSchemaObserver
from reflector2.r2.scratchpad import (
    CONTROL_GOAL_ROLES,
    GENERATED_ROLE_MODALITIES,
    _action_evidence_refs,
    _acknowledge_semantic_plateau,
    _begin_semantic_revision,
    _failed_semantic_state_repeated,
    _finish_semantic_revision,
    _goal_proposal_contract_error,
    _goal_write_requires_compiler_repair,
    _merge_supported_goal_proposals,
    _measurement_matches_template,
    _pending_semantic_revision_unsatisfied,
    _post_action_null_history_claim,
    _record_semantic_compiler_feedback,
    _semantic_revision_is_substantive,
    _quarantine_goal_proposals,
    _quarantine_schema_hypotheses,
    _semantic_failure_signals,
    _semantic_failure_suspends_goal,
    control_goal_proposals,
    project_schema_hypotheses_to_goals,
    record_r2_semantic_projection,
    reset_episode_context,
)
from reflector2.r2.semantic_measure import (
    SEMANTIC_MEASURE_PROTOCOL,
    SemanticMeasureHypothesis,
    spatial_feature,
)
from reflector2.r2.affordance_frontier import (
    AFFORDANCE_FRONTIER_PROTOCOL,
    build_affordance_frontier,
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
            "relation": "minimum",
            "target": 0.0,
        },
    }
    value.update(changes)
    return value


def schema_hypothesis(**changes: object) -> dict:
    value = {
        "local_ref": "schema_hypothesis_1",
        "kind": "relational_dynamic",
        "relation_family": "coupling",
        "claim": "the two roles may form one coupled relation",
        "roles": ["actor", "target"],
        "goal_proposal_index": 0,
        "predicted_dynamics": [
            "changes_relative_position", "coherent_motion",
        ],
        "counterconditions": [
            "goal_residual_not_improved", "coherent_motion_absent",
        ],
        "confidence": "high",
        "confidence_basis": "visible_structure",
    }
    value.update(changes)
    return value


def test_generated_control_goal_ports_are_canonical_binary_interfaces():
    assert CONTROL_GOAL_ROLES == ("actor", "target")
    assert "required" not in GENERATED_ROLE_MODALITIES
    assert "suggested" in GENERATED_ROLE_MODALITIES


def test_typed_local_terminal_is_the_single_source_of_terminal_text():
    raw = proposed_goal()
    raw.pop("terminal_condition")
    raw["local_terminal"] = {"target": 0.0}
    accepted, _seen, rejected = _quarantine_goal_proposals([raw])
    assert rejected == []
    assert accepted[0]["local_terminal"] == {
        "observable": "proposed_spatial_completion_residual",
        "preferred_order": "decrease",
        "relation": "minimum",
        "target": 0.0,
    }
    assert accepted[0]["terminal_condition"] == (
        "proposed_spatial_completion_residual=0"
    )


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


def test_affordance_frontier_reports_geometry_without_naming_a_goal_or_binding():
    exact = entity("exact-private-id", {(3, 3)})
    distractor = entity("distractor-private-id", {(8, 8), (8, 9)})
    frontier = build_affordance_frontier([ring(), exact, distractor])

    assert frontier["protocol"] == AFFORDANCE_FRONTIER_PROTOCOL
    assert frontier["authority"] == "observation-derived-attention-only"
    assert frontier["control_authority"] is False
    topology = next(
        item for item in frontier["observations"]
        if item["observation_family"] == "spatial_topology"
    )
    assert topology["entities_with_nonempty_feature"] == 1
    complement = next(
        item for item in frontier["observations"]
        if item.get("left_feature") == "occupancy"
        and item.get("right_feature") == "enclosed_negative_space"
    )
    assert complement["best_normalized_residual"] == 0.0
    assert complement["measurable_pair_hypotheses"] == 2
    serialized = json.dumps(frontier, sort_keys=True).lower()
    assert "private-id" not in serialized
    for imposed_semantics in ("fit", "insert", "hole", "align", "yellow", "blue"):
        assert imposed_semantics not in serialized


def test_affordance_frontier_fails_open_when_a_feature_is_not_observed():
    solid_a = entity("a", {(0, 0), (0, 1)})
    solid_b = entity("b", {(4, 4), (4, 5)})
    frontier = build_affordance_frontier([solid_a, solid_b])
    complement = next(
        item for item in frontier["observations"]
        if item.get("right_feature") == "enclosed_negative_space"
    )
    assert complement["measurable_pair_hypotheses"] == 0
    assert complement["best_normalized_residual"] is None
    assert complement["desired"] is None


def test_affordance_frontier_is_palette_and_translation_invariant():
    source = [
        entity("first", {(2, 2), (2, 3), (3, 2)}),
        entity("second", {(6, 6), (6, 7), (7, 6)}),
    ]
    translated = [
        {**item, "binding_id": f"other-{index}", "value": 9 - index,
         "cells": [(y + 5, x + 7) for y, x in item["cells"]]}
        for index, item in enumerate(source)
    ]
    intrinsic = lambda frontier: next(
        item for item in frontier["observations"]
        if item.get("left_feature") == "occupancy"
        and item.get("right_feature") == "occupancy"
        and item.get("coordinate_frame") == "intrinsic"
    )
    assert intrinsic(build_affordance_frontier(source)) == intrinsic(
        build_affordance_frontier(translated)
    )


def test_affordance_reference_binds_qwen_to_the_exact_observed_measurement():
    frontier = build_affordance_frontier([ring(), entity("point", {(3, 3)})])
    observation = next(
        item for item in frontier["observations"]
        if item.get("left_feature") == "occupancy"
        and item.get("right_feature") == "enclosed_negative_space"
        and item.get("coordinate_frame") == "scene"
    )
    templates = {
        observation["opportunity_ref"]: observation["measurement_template"],
    }
    grounded = proposed_goal(
        measurement_hypothesis=observation["measurement_template"],
    )
    accepted, _seen, rejected = _quarantine_goal_proposals(
        [grounded], affordance_templates=templates,
    )
    assert len(accepted) == 1
    assert rejected == []

    mismatched = proposed_goal(measurement_hypothesis={
        **observation["measurement_template"],
        "right_feature": "occupancy",
    })
    accepted, _seen, rejected = _quarantine_goal_proposals(
        [mismatched], affordance_templates=templates,
    )
    assert accepted == []
    assert rejected[0]["detail"] == "affordance-measurement-template-mismatch"


def test_affordance_template_quotients_only_commutative_operand_order():
    frontier = build_affordance_frontier([ring(), entity("point", {(3, 3)})])
    observation = next(
        item for item in frontier["observations"]
        if item.get("left_feature") == "occupancy"
        and item.get("right_feature") == "enclosed_negative_space"
        and item.get("comparison") == "symmetric_difference_size"
    )
    template = observation["measurement_template"]
    swapped = {
        **template,
        "left_source": template["right_source"],
        "left_feature": template["right_feature"],
        "right_source": template["left_source"],
        "right_feature": template["left_feature"],
    }
    assert _measurement_matches_template(swapped, template)
    accepted, _seen, rejected = _quarantine_goal_proposals(
        [proposed_goal(measurement_hypothesis=swapped)],
        affordance_templates={observation["opportunity_ref"]: template},
    )
    assert rejected == []
    assert accepted[0]["measurement_hypothesis"] == template

    asymmetric = {**template, "comparison": "left_unmatched_size"}
    asymmetric_template = {
        **template, "comparison": "left_unmatched_size",
    }
    asymmetric_swapped = {
        **asymmetric,
        "left_source": asymmetric["right_source"],
        "left_feature": asymmetric["right_feature"],
        "right_source": asymmetric["left_source"],
        "right_feature": asymmetric["left_feature"],
    }
    assert not _measurement_matches_template(
        asymmetric_swapped, asymmetric_template,
    )

    raw_goal = proposed_goal(measurement_hypothesis=swapped)
    accepted_goals, _seen, _rejected = _quarantine_goal_proposals(
        [raw_goal],
        affordance_templates={observation["opportunity_ref"]: template},
    )
    hypotheses, hypothesis_rejections = _quarantine_schema_hypotheses(
        [schema_hypothesis()], [raw_goal], accepted_goals,
        affordance_templates={observation["opportunity_ref"]: template},
    )
    assert len(hypotheses) == 1
    assert hypothesis_rejections == []


def test_scale_bands_preserve_larger_relations_when_singletons_tie():
    small_a = entity("small-a", {(0, 0)})
    small_b = entity("small-b", {(2, 2)})
    large_a = entity("large-a", {(y, x) for y in range(5) for x in range(5)})
    large_b = entity("large-b", {(y + 8, x + 8) for y in range(5) for x in range(5)})
    frontier = build_affordance_frontier([small_a, small_b, large_a, large_b])
    relation = next(
        item for item in frontier["observations"]
        if item.get("left_feature") == "occupancy"
        and item.get("right_feature") == "occupancy"
        and item.get("coordinate_frame") == "intrinsic"
    )
    assert {tuple(item["feature_support_range"]) for item in relation["scale_bands"]} >= {
        (1, 4), (17, 64),
    }


def test_commutative_same_feature_frontier_quotients_reversed_pair():
    horizontal_a = entity("a", {(0, 0), (0, 1)})
    horizontal_b = entity("b", {(4, 4), (4, 5)})
    corner = entity("c", {(8, 8), (9, 8), (9, 9)})
    frontier = build_affordance_frontier([
        horizontal_a, horizontal_b, corner,
    ])
    relation = next(
        item for item in frontier["observations"]
        if item.get("left_feature") == "occupancy"
        and item.get("right_feature") == "occupancy"
        and item.get("comparison") == "symmetric_difference_size"
        and item.get("coordinate_frame") == "intrinsic"
    )
    assert relation["role_orientation"] == "quotiented-commutative"
    assert relation["measurable_pair_hypotheses"] == 3
    assert relation["best_normalized_residual"] == 0.0
    assert relation["distinctiveness_margin"] > 0.0
    assert relation["near_best_pair_count"] == 1


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


def test_schema_hypothesis_confidence_compiles_only_as_attention_prior():
    raw_goal = proposed_goal()
    goals, _seen, _rejected = _quarantine_goal_proposals([raw_goal])
    hypotheses, rejected = _quarantine_schema_hypotheses(
        [schema_hypothesis()], [raw_goal], goals,
    )
    assert rejected == []
    assert len(hypotheses) == 1
    hypothesis = hypotheses[0]
    assert hypothesis["attention_priority"] == 3
    assert hypothesis["empirical_support"] == 0
    assert hypothesis["authority"] == "attention-prior-only"
    assert hypothesis["epistemic_status"] == (
        "ungrounded-semantic-schema-hypothesis"
    )

    projected = project_schema_hypotheses_to_goals(goals, hypotheses)
    assert projected[0]["_semantic_schema_hypotheses"] == hypotheses


def test_qwen_may_name_a_new_relation_family_but_cannot_add_new_dynamics():
    raw_goal = proposed_goal()
    goals, _seen, _rejected = _quarantine_goal_proposals([raw_goal])
    hypotheses, rejected = _quarantine_schema_hypotheses(
        [schema_hypothesis(relation_family="spatial_complementarity")],
        [raw_goal], goals,
    )
    assert rejected == []
    assert hypotheses[0]["relation_family"] == "spatial_complementarity"

    hypotheses, rejected = _quarantine_schema_hypotheses(
        [schema_hypothesis(predicted_dynamics=["magic_success"])],
        [raw_goal], goals,
    )
    assert hypotheses == []
    assert rejected[0]["reason"] == "schema-hypothesis-prediction"


def test_qwen_schema_ports_cannot_prebind_situated_entity_aliases():
    raw_goal = proposed_goal()
    goals, _seen, _rejected = _quarantine_goal_proposals([raw_goal])
    hypotheses, rejected = _quarantine_schema_hypotheses(
        [schema_hypothesis(claim="f01 and f03 form one coupled relation")],
        [raw_goal], goals,
    )
    assert hypotheses == []
    assert rejected == [{
        "reason": "schema-hypothesis-situated-identity",
        "hypothesis_index": 0,
    }]


def test_schema_hypothesis_must_reference_an_accepted_measurable_goal():
    invalid_goal = proposed_goal(measurement_hypothesis=None)
    goals, _seen, _rejected = _quarantine_goal_proposals([invalid_goal])
    hypotheses, rejected = _quarantine_schema_hypotheses(
        [schema_hypothesis()], [invalid_goal], goals,
    )
    assert hypotheses == []
    assert rejected == [{
        "reason": "schema-hypothesis-goal-not-accepted",
        "hypothesis_index": 0,
    }]


def test_schema_hypothesis_projects_to_entities_and_commands_at_zero_support():
    frame = [[0] * 12 for _ in range(12)]
    for y, x in ring()["cells"]:
        frame[y][x] = 2
    frame[8][8] = 1
    raw_goal = proposed_goal()
    goals, _seen, _rejected = _quarantine_goal_proposals([raw_goal])
    hypotheses, rejected = _quarantine_schema_hypotheses(
        [schema_hypothesis()], [raw_goal], goals,
    )
    assert rejected == []
    projected_goals = project_schema_hypotheses_to_goals(goals, hypotheses)

    observer = FrameSchemaObserver({"enabled": False})
    observer.fit_frame(frame)
    ranking = observer.rank_actions(
        (1,), fallback_action=1, semantic_goal=projected_goals,
    )
    explanation = next(
        item for item in ranking["explanations"]
        if item.get("schema_hypothesis_projections")
    )
    projection = explanation["schema_hypothesis_projections"][0]
    assert set(projection["entity_projection"]["role_bindings"]) == {
        "actor", "target",
    }
    assert projection["action_projection"]["command_id"] == "legacy-action:1"
    assert projection["action_projection"]["status"] == "open-effect-probe"
    assert projection["empirical_support"] == 0
    assert projection["model_confidence"] == "high"
    assert explanation["semantic_attention_priority"] == 3
    assert explanation["control_status"] != "PROGRESS_ELIGIBLE"
    semantic_facts = [
        fact for fact in observer.last_workspace.facts.values()
        if fact.predicate.startswith("SemanticSchemaProjection:")
    ]
    assert semantic_facts
    assert {fact.authority for fact in semantic_facts} == {"semantic-proposal"}


def _distance_goal() -> dict:
    return proposed_goal(
        verb="approach",
        schema_name="candidate relational approach",
        goal_family="contact",
        observable="centroid_distance",
        measurement_hypothesis=None,
        role_constraints=[{
            "predicate": "different_value",
            "arguments": ["actor", "target"],
            "modality": "suggested",
        }],
        terminal_condition="centroid_distance=0",
        local_terminal={
            "observable": "centroid_distance",
            "preferred_order": "decrease",
            "relation": "minimum",
            "target": 0.0,
        },
    )


def _two_role_frame(actor: tuple[int, int]) -> list[list[int]]:
    frame = [[0] * 9 for _ in range(9)]
    frame[actor[0]][actor[1]] = 1
    for y, x in ((1, 1), (1, 2), (2, 1), (2, 2)):
        frame[y][x] = 2
    return frame


def test_schema_dynamic_support_is_settled_separately_from_goal_support():
    raw_goal = _distance_goal()
    goals, _seen, _rejected = _quarantine_goal_proposals([raw_goal])
    hypotheses, rejected = _quarantine_schema_hypotheses([
        schema_hypothesis(
            relation_family="connection",
            predicted_dynamics=["changes_relative_position"],
            counterconditions=["goal_residual_not_improved"],
        ),
    ], [raw_goal], goals)
    assert rejected == []
    observer = FrameSchemaObserver({"enabled": False})
    before = _two_role_frame((7, 7))
    after = _two_role_frame((6, 7))
    observer.fit_frame(before)
    observer.rank_actions(
        (1,), fallback_action=1,
        semantic_goal=project_schema_hypotheses_to_goals(goals, hypotheses),
    )
    settlement = observer.settle_action(1, before, after)
    schema_settlement = settlement["schema_hypotheses"][0]
    assert schema_settlement["status"] == "SUPPORTED"
    assert schema_settlement["empirical_support"] == 1
    assert schema_settlement["authority"] == "environment-successor-settlement"
    assert settlement["potential"]["frontier_advanced"] is True
    assert settlement["mechanism"]["status"] == "OBSERVED"


def test_goal_nonprogress_can_refute_schema_without_erasing_observed_dynamic():
    raw_goal = _distance_goal()
    goals, _seen, _rejected = _quarantine_goal_proposals([raw_goal])
    hypotheses, rejected = _quarantine_schema_hypotheses([
        schema_hypothesis(
            predicted_dynamics=["changes_relative_position"],
            counterconditions=["goal_residual_not_improved"],
        ),
    ], [raw_goal], goals)
    assert rejected == []
    observer = FrameSchemaObserver({"enabled": False})
    before = _two_role_frame((6, 6))
    after = _two_role_frame((7, 6))
    observer.fit_frame(before)
    observer.rank_actions(
        (1,), fallback_action=1,
        semantic_goal=project_schema_hypotheses_to_goals(goals, hypotheses),
    )
    settlement = observer.settle_action(1, before, after)
    schema_settlement = settlement["schema_hypotheses"][0]
    assert any(
        item["status"] == "SUPPORTS"
        for item in schema_settlement["dynamic_judgments"]
    )
    assert any(
        item["countercondition"] == "goal_residual_not_improved"
        and item["consequence"] == "REFUTES"
        for item in schema_settlement["countercondition_judgments"]
    )
    assert schema_settlement["status"] == "REFUTED"
    assert schema_settlement["empirical_support"] == 0
    assert schema_settlement["empirical_refutations"] == 1


def test_scene_wide_coherent_motion_does_not_support_coupling_schema():
    observer = FrameSchemaObserver({"enabled": False})
    actor_before = entity("actor-before", {(2, 2)})
    target_before = entity("target-before", {(4, 4)})
    actor_after = entity("actor-after", {(3, 2)})
    target_after = entity("target-after", {(5, 4)})
    for item in (actor_before, target_before, actor_after, target_after):
        cells = item["cells"]
        item.update({
            "area": 1,
            "shape": ((0, 0),),
            "outline": ((0, 0),),
            "center2": (2.0 * cells[0][0], 2.0 * cells[0][1]),
        })
    settlement = observer._settle_schema_hypotheses({
        "schema_hypothesis_projections": [{
            "local_ref": "schema_hypothesis_1",
            "schema_id": "schema:coupling",
            "binding_id": "binding:coupling",
            "predicted_dynamics": ["coherent_motion"],
            "counterconditions": [],
            "action_projection": {
                "declared_dynamic_predictions": {"coherent_motion": True},
            },
        }],
    }, actor_before=actor_before, target_before=target_before,
       actor_after=actor_after, target_after=target_after,
       identity_status="UNIQUE", mechanism_status="CONFIRMED",
       actual_progress=0.0, evidence_ref="transition:global",
       global_transform={"delta": [1.0, 0.0]})[0]
    assert settlement["status"] == "OPEN"
    assert settlement["dynamic_judgments"][0]["reason"] == (
        "global-reference-frame-confound"
    )
    assert settlement["empirical_support"] == 0


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


def test_dependent_contract_separates_builtin_and_proposed_measurements():
    builtin = proposed_goal(
        observable="centroid_distance",
        measurement_hypothesis=None,
        local_terminal={
            "observable": "centroid_distance", "preferred_order": "decrease",
            "relation": "minimum", "target": 0.0,
        },
    )
    assert _goal_proposal_contract_error(builtin) is None
    assert _goal_proposal_contract_error(proposed_goal()) is None
    assert _goal_proposal_contract_error({
        **builtin, "measurement_hypothesis": negative_space_measure(),
    }) == "built-in-observable-must-not-carry-measurement-hypothesis"
    assert _goal_proposal_contract_error({
        **proposed_goal(), "measurement_hypothesis": None,
    }) == "proposed-observable-requires-measurement-hypothesis"
    assert _goal_proposal_contract_error({
        **builtin, "observable": "invented_distance",
        "local_terminal": {
            "observable": "invented_distance", "preferred_order": "decrease",
            "relation": "minimum", "target": 0.0,
        },
    }) == "observable-must-be-built-in-or-proposed"


def test_dependent_contract_rejects_incoherent_roles_and_terminals():
    assert _goal_proposal_contract_error(proposed_goal(
        potential_roles=["actor", "actor"],
    )) == "potential-roles-must-be-two-distinct-declared-roles"
    assert _goal_proposal_contract_error(proposed_goal(role_constraints=[{
        "predicate": "different_outline",
        "arguments": ["occluder", "occluder"],
        "modality": "suggested",
    }])) == "constraint-arguments-must-be-distinct-declared-roles"
    assert _goal_proposal_contract_error(proposed_goal(local_terminal={
        "observable": "centroid_distance", "preferred_order": "decrease",
        "relation": "minimum", "target": 0.0,
    })) == "local-terminal-observable-mismatch"
    assert _goal_proposal_contract_error(proposed_goal(
        terminal_class="maximum",
    )) == "direction-terminal-class-mismatch"
    assert _goal_proposal_contract_error(proposed_goal(local_terminal={
        "target": 0.0, "relation": "maximum",
    })) == "local-terminal-relation-mismatch"


def test_malformed_goal_is_quarantined_without_losing_valid_siblings():
    malformed = proposed_goal(role_constraints=[{
        "predicate": "different_outline",
        "arguments": ["occluder", "occluder"],
        "modality": "anti-clue",
    }])
    accepted, seen, rejected = _quarantine_goal_proposals([
        malformed, proposed_goal(), proposed_goal(),
    ])
    assert len(accepted) == 1
    assert len(seen) == 1
    assert rejected == [{
        "reason": "goal-proposal-dependent-contract",
        "proposal_index": 0,
        "detail": "constraint-arguments-must-be-distinct-declared-roles",
    }]
    assert accepted[0]["goal_contract"] is None

    # Compiler-owned storage defaults do not make a repeated proposal novel.
    normalized_copy = dict(accepted[0])
    accepted, seen, rejected = _quarantine_goal_proposals([
        proposed_goal(), normalized_copy,
    ])
    assert len(accepted) == len(seen) == 1
    assert rejected == []


def test_total_goal_compile_failure_is_not_semantic_abstention():
    rejection = {"reason": "goal-proposal-dependent-contract"}
    assert _goal_write_requires_compiler_repair([{"verb": "align"}], [], [
        rejection,
    ])
    assert not _goal_write_requires_compiler_repair([], [], [])
    assert not _goal_write_requires_compiler_repair(
        [{"verb": "align"}, {"verb": "fit"}],
        [proposed_goal()],
        [rejection],
    )


def test_semantic_projection_keeps_rejection_feedback_over_raw_cae_geometry():
    rejected = proposed_goal()
    rejected.update({
        "r2_grounding_status": "rejected-ungrounded",
        "reason": "no measurable typed tuple satisfies schema-required constraints",
    })
    projection = record_r2_semantic_projection({
        "protocol": "r2.1-semantic-projection-v1",
        "rejected_semantic_proposals": [rejected],
        "latest_settlement": {"adjudication": "untested", "raw": "x" * 20000},
        "causal_entity_induction": {
            "protocol": "r2-causal-entity-v0",
            "candidates_generated": 1,
            "bindings": [{
                "causal_entity_id": "causal-entity:test",
                "member_binding_ids": ["a", "b"],
                "cells": [[index, index] for index in range(4000)],
                "shape": [[index, 0] for index in range(4000)],
                "action_conditioned_transforms": {
                    "1": [{"kind": "translation", "parameters": [-1, 0]}],
                },
                "epistemic_status": "SUPPORTED",
                "support": 2,
            }],
        },
        "causal_entities": [{"cells": [[index, index] for index in range(4000)]}],
    })
    encoded = json.dumps(projection, sort_keys=True)
    assert len(encoded) <= 12000
    assert "cells" not in encoded
    assert projection["rejected_semantic_proposals"][0]["reason"].startswith(
        "no measurable typed tuple"
    )
    binding = projection["causal_entity_induction"]["bindings"][0]
    assert binding["member_count"] == 2
    assert binding["epistemic_status"] == "SUPPORTED"


def test_compiler_repair_feedback_stays_in_one_projection_until_repaired():
    reset_episode_context()
    try:
        record_r2_semantic_projection({
            "protocol": "r2.1-semantic-projection-v1",
            "frame_digest": "frame-a",
        })
        _record_semantic_compiler_feedback([{
            "reason": "goal-proposal-dependent-contract",
            "proposal_index": 0,
            "detail": "affordance-measurement-template-mismatch",
        }])
        same_frame = record_r2_semantic_projection({
            "protocol": "r2.1-semantic-projection-v1",
            "frame_digest": "frame-a",
            "active_explanation": {},
            # Projection compaction may materialize an absent optional field
            # as null. Only the compiler itself may clear live diagnostics.
            "semantic_compiler_feedback": None,
        })
        feedback = same_frame["semantic_compiler_feedback"]
        assert feedback["status"] == "repair-required"
        assert feedback["diagnostics"][0]["detail"] == (
            "affordance-measurement-template-mismatch"
        )
        assert feedback["repair_contract"]["novel_measurement"] == (
            "set-basis_opportunity_ref-null"
        )

        next_frame = record_r2_semantic_projection({
            "protocol": "r2.1-semantic-projection-v1",
            "frame_digest": "frame-b",
        })
        assert next_frame["semantic_compiler_feedback"] == feedback
    finally:
        reset_episode_context()


def test_repeated_nonprogress_revises_goal_without_refuting_mechanism():
    def document(
        count: int, confirmations: int = 0, progress_confirmations: int = 0,
    ) -> dict:
        return {"scratchpad_context": {"r2_semantic_projection": {
            "active_explanation": {
                "control_status": "PROBE_ELIGIBLE",
                "confirmations": confirmations,
                "progress_confirmations": progress_confirmations,
                "nonprogress_observations": count,
                "mechanism": {"confidence": 1.0},
            },
            "competing_explanations": [],
            "rejected_semantic_proposals": [],
        }}}

    assert _semantic_failure_signals(document(1)) == ()
    assert _semantic_failure_signals(document(2)) == ({
        "kind": "r2-goal-potential-nonprogress",
        "count": 1,
        "threshold": 2,
        "mechanism_authority": "preserve-independently",
    },)
    # Confirming a stationary mechanism does not support the goal potential.
    assert _semantic_failure_signals(document(2, confirmations=1))
    assert _semantic_failure_signals(document(2, progress_confirmations=1)) == ()

    mixed = document(2)
    mixed["scratchpad_context"]["r2_semantic_projection"]["competing_explanations"] = [{
        "control_status": "PROGRESS_ELIGIBLE",
        "progress_confirmations": 1,
    }]
    assert _semantic_failure_signals(mixed) == ()


def test_exact_semantic_state_repetition_is_stale_only_on_evidenced_failure():
    prior_scratchpad = {
        "game_objective": "Infer completion",
        "explanation": "One relation may matter",
        "goal": "Test the relation",
        "expectation": "The residual may decrease",
        "notes": "Uncertain",
    }
    document = {
        "model_scratchpad": prior_scratchpad,
        "prior_working_note": {
            "transition_evidence_ref": "r2-transition:old",
        },
        "scratchpad_context": {
            "r2_transition_observation": {
                "evidence_ref": "r2-transition:new",
            },
            "r2_semantic_projection": {
                "active_explanation": {
                    "control_status": "PROBE_ELIGIBLE",
                    "progress_confirmations": 0,
                    "nonprogress_observations": 2,
                },
                "competing_explanations": [],
                "rejected_semantic_proposals": [],
            },
        },
    }

    assert _failed_semantic_state_repeated(document, prior_scratchpad)
    notes_only = {**prior_scratchpad, "notes": "The latest probe did not progress"}
    assert _failed_semantic_state_repeated(document, notes_only)
    revised = {
        **notes_only,
        "expectation": "A different relation must now predict progress",
    }
    assert _semantic_revision_is_substantive(prior_scratchpad, revised)
    assert not _failed_semantic_state_repeated(document, revised)

    no_failure = json.loads(json.dumps(document))
    no_failure["scratchpad_context"]["r2_semantic_projection"][
        "active_explanation"
    ]["nonprogress_observations"] = 1
    assert not _failed_semantic_state_repeated(no_failure, prior_scratchpad)

    no_new_evidence = json.loads(json.dumps(document))
    no_new_evidence["prior_working_note"][
        "transition_evidence_ref"
    ] = "r2-transition:new"
    assert not _failed_semantic_state_repeated(no_new_evidence, prior_scratchpad)


def test_evidenced_semantic_revision_obligation_survives_transient_signal():
    scratchpad = {
        "game_objective": "Infer completion",
        "explanation": "One relation may matter",
        "goal": "Test the relation",
        "expectation": "The residual may decrease",
        "notes": "Uncertain",
    }
    signals = ({"kind": "r2-goal-potential-nonprogress", "count": 1},)
    _finish_semantic_revision()
    try:
        _begin_semantic_revision(scratchpad, "r2-transition:trigger", signals)
        assert _pending_semantic_revision_unsatisfied(scratchpad)
        cosmetic = {**scratchpad, "explanation": "A relation may still matter"}
        assert _pending_semantic_revision_unsatisfied(cosmetic)
        revised = {
            **cosmetic,
            "notes": "The latest probe did not progress",
        }
        assert not _pending_semantic_revision_unsatisfied(revised)
    finally:
        _finish_semantic_revision()
    assert not _pending_semantic_revision_unsatisfied(scratchpad)


def test_pending_revision_suspends_only_failed_goal_control_authority():
    scratchpad = {
        "game_objective": "Infer completion",
        "explanation": "One relation may matter",
        "goal": "Test the relation",
        "expectation": "The residual may decrease",
        "notes": "Uncertain",
    }
    failed = {
        "verb": "align",
        "observable": "alignment_residual",
        "direction": "decrease",
        "terminal_condition": "zero",
    }
    alternative = {
        "verb": "contain",
        "observable": "negative_space_residual",
        "direction": "decrease",
        "terminal_condition": "zero",
    }
    _finish_semantic_revision()
    try:
        _begin_semantic_revision(
            scratchpad,
            "r2-transition:trigger",
            ({"kind": "r2-goal-potential-nonprogress", "count": 3},),
            (failed,),
        )
        assert control_goal_proposals([failed]) == []
        assert control_goal_proposals([failed, alternative]) == [alternative]
    finally:
        _finish_semantic_revision()
    assert control_goal_proposals([failed]) == [failed]


def test_supported_recent_plateau_requests_revision_without_suspension():
    document = {
        "scratchpad_context": {
            "r2_semantic_projection": {
                "active_explanation": {
                    "control_goal_key": "control-goal:supported",
                    "control_status": "PROBE_ELIGIBLE",
                    "progress_confirmations": 7,
                    "nonprogress_observations": 9,
                    "best_observed_potential": 27.0,
                    "frontier_stagnation_steps": 4,
                },
                "competing_explanations": [],
                "rejected_semantic_proposals": [],
            },
        },
    }
    signals = _semantic_failure_signals(document)
    assert [item["kind"] for item in signals] == [
        "r2-goal-potential-plateau",
    ]
    assert not _semantic_failure_suspends_goal(signals)
    _acknowledge_semantic_plateau(document)
    assert not _semantic_failure_signals(document)
    new_frontier = json.loads(json.dumps(document))
    new_frontier["scratchpad_context"]["r2_semantic_projection"][
        "active_explanation"
    ]["best_observed_potential"] = 24.0
    assert _semantic_failure_signals(new_frontier)
    reset_episode_context()
    progressed = json.loads(json.dumps(document))
    progressed["scratchpad_context"]["r2_semantic_projection"][
        "active_explanation"
    ]["frontier_stagnation_steps"] = 0
    assert not _semantic_failure_signals(progressed)


def test_supported_plateau_merge_preserves_prior_and_adds_only_distinct_goals():
    prior = proposed_goal()
    alternative = proposed_goal(
        verb="contain",
        schema_name="candidate containment",
        observable="proposed_containment_residual",
        local_terminal={
            "observable": "proposed_containment_residual",
            "preferred_order": "decrease",
            "relation": "minimum",
            "target": 0.0,
        },
    )
    normalized_prior = _quarantine_goal_proposals([prior])[0][0]
    normalized_alternative = _quarantine_goal_proposals([alternative])[0][0]
    assert _merge_supported_goal_proposals([prior], []) == [normalized_prior]
    assert _merge_supported_goal_proposals([prior], [prior]) == [normalized_prior]
    assert _merge_supported_goal_proposals([prior], [alternative]) == [
        normalized_prior,
        normalized_alternative,
    ]


def test_post_action_scratchpad_cannot_deny_authoritative_history():
    document = {
        "scratchpad_context": {
            "r2_transition_observation": {
                "evidence_ref": "r2-transition:observed",
            },
        },
    }
    coherent = {
        "game_objective": "Open",
        "explanation": "The latest transition moved one entity",
        "goal": "Revise the relation hypothesis",
        "expectation": "A fresh relation should predict change",
        "notes": "The prior hypothesis did not progress",
    }
    assert not _post_action_null_history_claim(document, coherent)
    contradictory = {
        **coherent,
        "notes": "No prior state to compare against",
    }
    assert _post_action_null_history_claim(document, contradictory)
    assert not _post_action_null_history_claim(
        {"scratchpad_context": {"r2_transition_observation": None}},
        contradictory,
    )


def test_action_alias_evidence_uses_single_canonical_prior_note_projection():
    document = {
        "prior_working_note": {
            "action_aliases": [{
                "action_id": "ACTION_4",
                "alias": "interact?",
                "status": "tentative",
                "evidence_refs": ["r2-transition:prior"],
            }],
        },
        "scratchpad_context": {
            "r2_transition_observation": {
                "action": 4,
                "evidence_ref": "r2-transition:current",
                "prediction_settlement": {},
            },
            "r2_semantic_projection": {},
        },
    }

    assert _action_evidence_refs(document) == {
        "ACTION_4": (
            "r2-transition:current",
            "r2-transition:prior",
        ),
    }


def test_prompt_source_contains_no_privileged_fit_mapping_or_game_tokens():
    source = (Path(__file__).parents[1] / "src/reflector2/r2/scratchpad.py").read_text()
    measure_source = (
        Path(__file__).parents[1] / "src/reflector2/r2/semantic_measure.py"
    ).read_text().lower()
    lowered = source.lower()
    assert "fit should use fit_residual" not in lowered
    assert "fit normally decreases fit_residual" not in lowered
    assert "fit requires only" not in lowered
    assert "natural-language-scratchpad-not-revised" not in source
    assert "r2-spatial-set-residual-v0" in source
    for forbidden in ("ar25", "yellow", "blue l", "action_1"):
        assert forbidden not in measure_source
