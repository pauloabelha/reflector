import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))

import pytest
import progress_synthesis as ps
import progress_field as pf


def candidate(attention=80):
    return ps._candidate("UncoveredRequirementCount",{"x":{"type":"Transformable"}},{"x":"region:a"},attention)


def test_attention_selects_probe_but_cannot_authorize_control():
    high=candidate(95);state=pf.make_state([high])
    decision=pf.decide(state,[3,1])
    assert decision.mode=="probe" and decision.opaque_action==1
    assert high.support==0


def test_two_direct_matching_improvements_authorize_control():
    item=candidate();state=pf.make_state([item])
    state=pf.observe(state,candidate_id=item.candidate_id,binding_id=item.binding_id,opaque_action=4,before=3,after=2,direct=True,transition_id="t1")
    assert pf.decide(state,[4]).mode=="probe"
    state=pf.observe(state,candidate_id=item.candidate_id,binding_id=item.binding_id,opaque_action=4,before=2,after=1,direct=True,transition_id="t2")
    decision=pf.decide(state,[4])
    assert decision.mode=="control" and decision.predicted_improvement==1
    assert decision.basis_evidence_ids==("t1","t2")


def test_indirect_and_conflicting_evidence_never_authorize_control():
    item=candidate();state=pf.make_state([item])
    state=pf.observe(state,candidate_id=item.candidate_id,binding_id=item.binding_id,opaque_action=2,before=3,after=2,direct=False,transition_id="t0")
    state=pf.observe(state,candidate_id=item.candidate_id,binding_id=item.binding_id,opaque_action=2,before=3,after=2,direct=True,transition_id="t1")
    state=pf.observe(state,candidate_id=item.candidate_id,binding_id=item.binding_id,opaque_action=2,before=2,after=3,direct=True,transition_id="t2")
    assert pf.decide(state,[2]).mode=="fallback"


def test_workspace_separates_attention_support_and_hides_action_ids():
    item=candidate();doc=pf.workspace_document(pf.make_state([item]));text=str(doc)
    row=doc["potentials"][0]
    assert row["attention"]==80 and row["empirical_support"]==0
    assert "opaque_action" not in text and "action_id" not in text


def test_duplicate_or_unaddressed_evidence_is_rejected():
    item=candidate();state=pf.make_state([item])
    with pytest.raises(pf.ProgressFieldError):
        pf.observe(state,candidate_id="missing",binding_id=item.binding_id,opaque_action=1,before=1,after=0,direct=True,transition_id="t")
    state=pf.observe(state,candidate_id=item.candidate_id,binding_id=item.binding_id,opaque_action=1,before=1,after=0,direct=True,transition_id="t")
    with pytest.raises(pf.ProgressFieldError):
        pf.observe(state,candidate_id=item.candidate_id,binding_id=item.binding_id,opaque_action=1,before=1,after=0,direct=True,transition_id="t")


def test_unresolved_attempt_is_durable_and_forces_experiment_to_advance():
    item=candidate();state=pf.make_state([item]);first=pf.decide(state,[1,2])
    state=pf.record_attempt(state,candidate_id=item.candidate_id,binding_id=item.binding_id,opaque_action=first.opaque_action)
    second=pf.decide(state,[1,2])
    assert second.opaque_action!=first.opaque_action
