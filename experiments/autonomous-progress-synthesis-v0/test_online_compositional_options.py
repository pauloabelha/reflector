from __future__ import annotations

import pathlib
import sys
from dataclasses import replace


sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import broad_policy_bridge as bridge
import compositional_dsl as dsl
import online_compositional_options as online
import progress_synthesis as synthesis


def frame(left=(1, 2), *, palette=(3, 7)):
    # Prime dimensions keep this synthetic observation on its native lattice.
    grid = [[0] * 17 for _ in range(11)]
    lx, ly = left
    for y in range(ly, ly + 2):
        for x in range(lx, lx + 2):
            grid[y][x] = palette[0]
    for y in range(2, 5):
        for x in range(13, 15):
            grid[y][x] = palette[1]
    return grid


def candidate(raw):
    scene = synthesis.perceive(raw)
    left, right = sorted(scene.regions, key=lambda row: row.x)
    return dsl.compile_candidate(
        {"op": "TranslationAlignmentResidual", "arguments": ["?moving", "?target"]},
        {"?moving": left.region_id, "?target": right.region_id},
        scene,
        attention=80,
    )


class Decision:
    action_id = 999

    def data_dict(self):
        return {}


class Baseline:
    def choose_action(self, observation):
        return Decision()

    def cognitive_event(self, observation, decision):
        return {"operative_state": {"consecutive_without_progress": 9}}


def test_consecutive_transitions_update_grounding_and_learn_region_effects():
    initial = frame()
    inducer = online.OnlineCompositionalOptionInducer(
        initial, legal_actions=(41,), candidates=(candidate(initial),)
    )
    inducer.observe_option_transition(
        opaque_action=41, after=frame((2, 2)), transition_id="transition:1"
    )
    inducer.observe_option_transition(
        opaque_action=41, after=frame((3, 2)), transition_id="transition:2"
    )
    state = inducer.grounding_state()[0]
    assert state.correspondence_status == "unique"
    proposals = inducer.option_proposals()
    assert len(proposals) == 1
    assert proposals[0].action_id == 41 and proposals[0].predicted_after < proposals[0].potential_before
    model = inducer.workspace_document()["effect_models"][0]
    assert model["delta"] == [1, 0]
    assert model["evidence_ids"] == ["transition:1", "transition:2"]


def test_palette_permutation_preserves_binding_and_direct_evaluation():
    initial = frame()
    inducer = online.OnlineCompositionalOptionInducer(
        initial, legal_actions=(73,), candidates=(candidate(initial),)
    )
    inducer.observe_option_transition(
        opaque_action=73,
        after=frame((2, 2), palette=(9, 4)),
        transition_id="transition:palette-1",
    )
    proposal = inducer.option_proposals()[0]
    evaluator = inducer.evaluator_state(proposal.candidate_id)
    assert evaluator is not None and evaluator.binding
    outcome = inducer.observe_option_transition(
        opaque_action=73,
        after=frame((3, 2), palette=(4, 9)),
        transition_id="transition:palette-2",
        executed_candidate_id=proposal.candidate_id,
    )
    assert outcome is not None and outcome.direct
    assert outcome.observed_after == proposal.predicted_after


def test_action_relabeling_changes_only_opaque_action_address():
    initial = frame()
    rows = []
    for action in (17, 811):
        inducer = online.OnlineCompositionalOptionInducer(
            initial, legal_actions=(action,), candidates=(candidate(initial),)
        )
        inducer.observe_option_transition(
            opaque_action=action,
            after=frame((2, 2)),
            transition_id=f"transition:{action}",
        )
        rows.append(inducer.option_proposals()[0])
    left, right = rows
    assert left.schema_id == right.schema_id
    assert (left.potential_before, left.predicted_after) == (
        right.potential_before,
        right.predicted_after,
    )
    assert (left.action_id, right.action_id) == (17, 811)


def test_binding_and_candidate_permutation_do_not_change_option_identity():
    initial = frame()
    original = candidate(initial)
    permuted = replace(
        original,
        binding={
            "?target": original.binding["?target"],
            "?moving": original.binding["?moving"],
        },
    )
    rows = []
    for supplied in ((original,), tuple(reversed((permuted,)))):
        inducer = online.OnlineCompositionalOptionInducer(
            initial, legal_actions=(37,), candidates=supplied
        )
        inducer.observe_option_transition(
            opaque_action=37,
            after=frame((2, 2)),
            transition_id="transition:permutation",
        )
        rows.append(inducer.option_proposals()[0])
    assert rows[0].candidate_id == rows[1].candidate_id
    assert rows[0].schema_id == rows[1].schema_id


def test_option_identity_is_stable_as_potential_changes():
    initial = frame()
    inducer = online.OnlineCompositionalOptionInducer(
        initial, legal_actions=(55,), candidates=(candidate(initial),)
    )
    inducer.observe_option_transition(
        opaque_action=55, after=frame((2, 2)), transition_id="transition:a"
    )
    first = inducer.option_proposals()[0]
    inducer.observe_option_transition(
        opaque_action=55, after=frame((3, 2)), transition_id="transition:b"
    )
    second = inducer.option_proposals()[0]
    assert first.potential_before != second.potential_before
    assert first.candidate_id == second.candidate_id


def test_broad_bridge_consumes_frontier_and_adjudicates_evaluator_state():
    initial = frame()
    inducer = online.OnlineCompositionalOptionInducer(
        initial, legal_actions=(61,), candidates=(candidate(initial),)
    )
    inducer.observe_option_transition(
        opaque_action=61, after=frame((2, 2)), transition_id="transition:learn"
    )
    policy = bridge.SharedBroadPolicy(Baseline(), stagnation_threshold=1)
    decision = policy.choose_from_inducer(object(), inducer)
    assert decision.mode == "probe" and decision.action_id == 61
    verdict = policy.observe_inducer_transition(
        inducer,
        decision,
        after=frame((3, 2)),
        transition_id="transition:probe",
    )
    assert verdict == "supports"


def test_unlicensed_fallback_does_not_adjudicate_selected_option():
    initial=frame();inducer=online.OnlineCompositionalOptionInducer(initial,legal_actions=(61,),candidates=(candidate(initial),))
    inducer.observe_option_transition(opaque_action=61,after=frame((2,2)),transition_id="transition:learn")
    policy=bridge.SharedBroadPolicy(Baseline(),stagnation_threshold=99)
    decision=policy.choose_from_inducer(object(),inducer)
    assert decision.mode=="fallback" and decision.candidate_id is not None
    verdict=policy.observe_inducer_transition(inducer,decision,after=frame((2,2)),transition_id="transition:fallback")
    assert verdict is None and policy.leases[decision.candidate_id].confirmations==0


def test_indirect_transition_updates_correspondence_but_not_effect_model():
    initial = frame()
    inducer = online.OnlineCompositionalOptionInducer(
        initial, legal_actions=(23,), candidates=(candidate(initial),)
    )
    inducer.observe_option_transition(
        opaque_action=23,
        after=frame((2, 2)),
        transition_id="transition:indirect",
        direct=False,
    )
    assert inducer.grounding_state()[0].correspondence_status == "unique"
    assert inducer.option_proposals() == ()
    assert inducer.workspace_document()["effect_models"] == []


def test_effect_evidence_is_scoped_to_stable_grounding_lineage_and_variable():
    initial=frame();scene=synthesis.perceive(initial);left,right=sorted(scene.regions,key=lambda row:row.x)
    first=dsl.compile_candidate({"op":"TranslationAlignmentResidual","arguments":["?moving","?target"]},{"?moving":left.region_id,"?target":right.region_id},scene,attention=80)
    second=dsl.compile_candidate({"op":"TranslationAlignmentResidual","arguments":["?moving","?target"]},{"?moving":right.region_id,"?target":left.region_id},scene,attention=80)
    assert first.candidate_id==second.candidate_id
    inducer=online.OnlineCompositionalOptionInducer(initial,legal_actions=(42,),candidates=(first,second))
    inducer.observe_option_transition(opaque_action=42,after=frame((2,2)),transition_id="transition:lineage")
    models=inducer.workspace_document()["effect_models"]
    assert len({row["lineage_id"] for row in models})==2
    assert {(row["lineage_id"],row["variable"]) for row in models if row["delta"]!=[0,0]}=={
        (row.lineage_id,row.effect_variable) for row in inducer.option_proposals()
    }
