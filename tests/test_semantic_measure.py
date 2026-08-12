from __future__ import annotations

import json
from pathlib import Path

import pytest

from reflector2.planner import BoundedBestFirstPlanner
from reflector2.r2.goal_contract import canonicalize_goal_proposals
from reflector2.r2.r2_1_adapter import FrameSchemaObserver
from reflector2.r2.scratchpad import (
    _action_evidence_refs,
    _begin_semantic_revision,
    _failed_semantic_state_repeated,
    _finish_semantic_revision,
    _goal_proposal_contract_error,
    _pending_semantic_revision_unsatisfied,
    _post_action_null_history_claim,
    _semantic_revision_is_substantive,
    _quarantine_goal_proposals,
    _semantic_failure_signals,
    control_goal_proposals,
    record_r2_semantic_projection,
)
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
