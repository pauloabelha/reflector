from __future__ import annotations

import pathlib
import sys

import pytest


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import collection_transport as ct
import capability_registry as registry


def world(actor=(1, 1)):
    grid = [[0] * 12 for _ in range(12)]
    # One equivalence class: actor plus two portable members.
    for x, y in (actor, (5, 1), (1, 5)):
        for yy in range(y, y + 2):
            for xx in range(x, x + 2):
                grid[yy][xx] = 1
    # A geometrically independent two-slot target.
    for yy in range(8, 10):
        for xx in range(7, 11):
            grid[yy][xx] = 2
    return grid


def observations(*, interaction=False):
    rows = [
        ct.CalibrationTransition(11, world((2, 1)), "transition:north"),
        ct.CalibrationTransition(12, world((1, 2)), "transition:east"),
        ct.CalibrationTransition(13, world((0, 1)), "transition:south"),
        ct.CalibrationTransition(14, world((1, 0)), "transition:west"),
        ct.CalibrationTransition(
            15,
            world(),
            "transition:interaction",
            interaction_effect="pickup" if interaction else None,
        ),
    ]
    return tuple(rows)


def test_observed_motion_resolves_roles_but_unproven_interaction_stays_open():
    capability = ct.induce_collection_capability(world(), observations())
    assert capability is not None
    assert capability.grounding.complete
    assert len(capability.grounding.member_ids) == 2
    assert capability.interaction_action is None
    assert capability.interaction_candidates == (15,)
    assert capability.empirical_support == 0
    assert capability.open_ports == ("?interaction",)
    document = ct.workspace_document(capability)
    assert document["created_by"] == "self_built"
    assert document["payload"]["ports"]["?interaction"]["status"] == ct.OPEN
    assert document["payload"]["empirical_support"] == 0
    assert "opaque_action" not in repr(document)


def test_structural_ambiguity_is_preserved_as_open_ports():
    capability = ct.induce_collection_capability(world(), ())
    assert capability is not None
    assert not capability.grounding.complete
    assert "?actor" in capability.open_ports and "?members" in capability.open_ports
    port = ct.workspace_document(capability)["payload"]["ports"]["?actor"]
    assert port["status"] == ct.OPEN and len(port["candidates"]) == 3


def test_direct_motor_evidence_does_not_grant_goal_support_or_execution():
    capability = ct.induce_collection_capability(world(), observations(interaction=True))
    assert capability is not None and capability.interaction_action == 15
    assert len(capability.motion_models) == 4
    assert capability.empirical_support == 0
    with pytest.raises(ct.CollectionCapabilityError, match="direct empirical support"):
        ct.compile_supported_transport(capability)
    probe = ct.compile_transport_probe(capability)
    assert len(probe.item_to_slot) == 1
    assert sum(step.kind == "drop" for step in probe.steps) == 1


def test_environment_goal_evidence_unlocks_generic_transport_plan():
    capability = ct.induce_collection_capability(world(), observations(interaction=True))
    assert capability is not None
    evidence = ct.GoalProgressEvidence(
        capability.candidate.candidate_id,
        capability.binding_id,
        "transition:progress",
        before=2,
        after=1,
        direct=True,
    )
    supported = ct.adjudicate_goal_evidence(capability, evidence)
    assert supported.empirical_support == 10
    assert supported.evidence_objects[0]["created_by"] == "environment"
    plan = ct.compile_supported_transport(supported)
    assert len(plan.item_to_slot) == 2
    assert set(plan.actions) <= {11, 12, 13, 14, 15}
    assert sum(step.kind == "pickup" for step in plan.steps) == 2
    assert sum(step.kind == "drop" for step in plan.steps) == 2


def test_indirect_or_non_environment_claim_cannot_authorize_control():
    capability = ct.induce_collection_capability(world(), observations(interaction=True))
    assert capability is not None
    indirect = ct.GoalProgressEvidence(
        capability.candidate.candidate_id,
        capability.binding_id,
        "transition:indirect",
        before=2,
        after=1,
        direct=False,
    )
    assert ct.adjudicate_goal_evidence(capability, indirect).empirical_support == 0
    forged = ct.GoalProgressEvidence(
        capability.candidate.candidate_id,
        capability.binding_id,
        "transition:forged",
        before=2,
        after=1,
        direct=True,
        created_by="worker",
    )
    with pytest.raises(ct.CollectionCapabilityError, match="only environment"):
        ct.adjudicate_goal_evidence(capability, forged)


def test_registry_surfaces_open_collection_option_without_game_selector():
    rows = registry.propose(world(), {row.opaque_action: row.after for row in observations()})
    matches = [row for row in rows if row.capability == "interactive:collection-transport"]
    assert len(matches) == 1
    assert matches[0].empirical_support == 0 and matches[0].interactive
    assert "?interaction" in matches[0].execution.open_ports
