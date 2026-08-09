from broad_policy_bridge import BridgeError, EnvironmentOutcome, OptionProposal, SharedBroadPolicy,decode_frame
import pytest


class Decision:
    def __init__(self, action_id=1, data=None):self.action_id=action_id;self._data=data or {}
    def data_dict(self):return self._data


class Baseline:
    def __init__(self, stagnation=0):self.stagnation=stagnation;self.calls=0
    def choose_action(self, observation):self.calls+=1;return Decision(1,{"x":2})
    def cognitive_event(self, observation, decision):
        return {"format":"reflector-cognitive-event-v1","operative_state":{"consecutive_without_progress":self.stagnation}}


class Observation:
    def to_dict(self):return {"frame":[[0,1],[1,0]],"transition_id":"transition:0"}


def proposal(mode="probe"):
    return OptionProposal.create(schema_id="schema:generic",action_id=4,mode=mode,potential_before=3,predicted_after=2,basis_ids=("frame:0",),proposer="qwen",attention=90)


def alternate():
    return OptionProposal.create(schema_id="schema:alternate",action_id=3,mode="probe",potential_before=5,predicted_after=4,basis_ids=("frame:0",),proposer="r2",attention=70)


def test_no_option_is_exact_fallback_and_cognition_is_shared():
    policy=SharedBroadPolicy(Baseline())
    decision=policy.choose_action(Observation())
    assert (decision.action_id,dict(decision.data),decision.mode)==(1,{"x":2},"fallback")
    events=policy.workspace_document()["events"]
    assert events[0]["kind"]=="world_observation"
    assert "frame" not in events[0]["payload"]
    ref=events[0]["payload"]["frame_ref"]
    assert decode_frame(policy.frame_blobs,ref)==((0,1),(1,0))
    assert events[1]["kind"]=="broad_cognitive_event"


def test_attention_or_unconfirmed_control_cannot_override():
    policy=SharedBroadPolicy(Baseline(stagnation=99))
    option=proposal("control")
    decision=policy.choose_action(object(),option)
    assert decision.action_id==decision.fallback_action_id==1
    assert policy.workspace_document()["events"][-1]["support"]==0


def test_probe_requires_stagnation_and_records_same_state_fallback():
    quiet=SharedBroadPolicy(Baseline(stagnation=7),stagnation_threshold=8)
    assert quiet.choose_action(object(),proposal()).mode=="fallback"
    stuck=SharedBroadPolicy(Baseline(stagnation=8),stagnation_threshold=8)
    decision=stuck.choose_action(object(),proposal())
    assert (decision.mode,decision.action_id,decision.fallback_action_id)==("probe",4,1)
    event=stuck.workspace_document()["events"][-1]
    assert event["same_state_fallback"]=={"action_id":1,"data":{"x":2}}


def test_two_direct_matches_license_control_but_refutation_revokes():
    policy=SharedBroadPolicy(Baseline(stagnation=99))
    probe=proposal();policy.choose_action(object(),probe)
    for index in range(2):
        assert policy.adjudicate(EnvironmentOutcome(probe.candidate_id,f"transition:{index}",3,2,True))=="supports"
    control=OptionProposal.create(schema_id=probe.schema_id,action_id=probe.action_id,mode="control",potential_before=3,predicted_after=2,basis_ids=probe.basis_ids,proposer="r2")
    # Identity is semantic and independent of worker/mode.
    assert control.candidate_id==probe.candidate_id
    assert policy.choose_action(object(),control).mode=="control"
    assert policy.adjudicate(EnvironmentOutcome(control.candidate_id,"transition:bad",3,3,True))=="refutes"
    assert policy.choose_action(object(),control).mode=="fallback"


def test_option_identity_survives_new_state_and_provenance_basis():
    first=proposal()
    later=OptionProposal.create(schema_id=first.schema_id,action_id=first.action_id,mode="control",potential_before=2,predicted_after=1,basis_ids=("frame:9","evidence:4"),proposer="r2")
    assert later.candidate_id==first.candidate_id
    assert later.basis_ids!=(first.basis_ids)
    changed_effect=OptionProposal.create(schema_id=first.schema_id,action_id=first.action_id,mode="probe",potential_before=4,predicted_after=2,basis_ids=("frame:10",),proposer="r2")
    assert changed_effect.candidate_id!=first.candidate_id
    other_lineage=OptionProposal.create(schema_id=first.schema_id,lineage_id="grounding:other",effect_variable="?x",action_id=first.action_id,mode="probe",potential_before=3,predicted_after=2,basis_ids=("frame:11",),proposer="r2")
    assert other_lineage.candidate_id!=first.candidate_id


def test_unresolved_is_not_support_and_non_environment_authority_fails():
    policy=SharedBroadPolicy(Baseline(stagnation=99));option=proposal();policy.choose_action(object(),option)
    assert policy.adjudicate(EnvironmentOutcome(option.candidate_id,"transition:x",None,None,False))=="unresolved"
    assert policy.leases[option.candidate_id].confirmations==0
    with pytest.raises(BridgeError,match="only the environment"):
        EnvironmentOutcome(option.candidate_id,"transition:y",3,2,True,actor="qwen")


def test_frontier_rotates_across_unresolved_goal_families():
    policy=SharedBroadPolicy(Baseline(stagnation=99),max_option_probes=4)
    first,second=proposal(),alternate()
    d0=policy.choose_from_frontier(object(),(first,second))
    assert d0.candidate_id==first.candidate_id
    policy.adjudicate(EnvironmentOutcome(first.candidate_id,"transition:0",None,None,False))
    d1=policy.choose_from_frontier(object(),(first,second))
    assert d1.candidate_id==second.candidate_id
    assert policy.workspace_document()["probe_counts"]=={first.candidate_id:1,second.candidate_id:1}


def test_frames_use_lossless_sparse_deltas_and_periodic_checkpoints():
    policy=SharedBroadPolicy(Baseline())
    frames=[]
    for index in range(35):
        frame=[[(row+column)%2 for column in range(16)] for row in range(16)]
        for changed in range(index+1):frame[changed//16][changed%16]=2
        frames.append(tuple(tuple(row) for row in frame))
        class Current:
            def to_dict(self,frame=frame):return {"frame":frame}
        policy.choose_action(Current())
    refs=[event["payload"]["frame_ref"] for event in policy.events if event["kind"]=="world_observation"]
    assert all(decode_frame(policy.frame_blobs,ref)==frame for ref,frame in zip(refs,frames))
    assert {blob["codec"] for blob in policy.frame_blobs.values()}=={"rle-v1","delta-v1"}


def test_qwen_cut_has_current_pixels_addresses_and_truthful_omission():
    policy=SharedBroadPolicy(Baseline(stagnation=99))
    for index in range(4):
        class Current:
            def to_dict(self,index=index):return {"frame":[[0,index],[0,0]],"sequence":index}
        policy.choose_from_frontier(Current(),(proposal(),))
    context=policy.working_context(max_events=3,max_historical_frames=2)
    assert context["current_frame"]==[[0,3],[0,0]]
    assert len(context["historical_frame_refs"])==2
    assert context["omitted_event_count"]==len(policy.events)-3
    assert "small-lossy" in context["omission_fidelity"]
    assert context["active_options"][0]["empirical"]["control_eligible"] is False
