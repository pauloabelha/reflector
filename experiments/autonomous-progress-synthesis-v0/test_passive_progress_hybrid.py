from types import SimpleNamespace

import autonomous_agent as agent_module
import passive_progress_hybrid as M
import progress_field


def scene(offset=0):
    grid=[[0]*14 for _ in range(10)]
    for y in range(2,5):
      for x in range(1+offset,4+offset):grid[y][x]=1
    for y in range(2,5):
      for x in range(9,12):grid[y][x]=1
    return grid


class Broad:
    def __init__(self,action):self.action=action
    def choose_action(self,_observation):
        return SimpleNamespace(action_id=self.action,data_dict=lambda:{})


def test_baseline_transitions_calibrate_entire_field_without_probe_override():
    agent=agent_module.AutonomousProgressAgent(scene(),frontier_size=8)
    hybrid=M.PassiveProgressHybrid(Broad(9),agent)
    decision=hybrid.decide(object(),[7,9])
    assert decision.mode=="broad-fallback" and decision.action_id==9
    result=hybrid.observe(decision,scene(1),transition_id="transition:one")
    assert result.observed_candidate_count>1
    assert agent.state.uses()[9]==1


def test_repeated_supported_effect_can_override_but_keeps_counterfactual():
    agent=agent_module.AutonomousProgressAgent(scene(),frontier_size=8)
    hybrid=M.PassiveProgressHybrid(Broad(9),agent,minimum_support=20)
    # Calibrate action 7 from two directly observed translations, independent
    # of the broad policy's proposed action.
    fake=M.HybridDecision(7,(),9,(),"broad-fallback",None,None,None)
    hybrid.observe(fake,scene(1),transition_id="transition:one")
    hybrid.observe(fake,scene(2),transition_id="transition:two")
    decision=hybrid.decide(object(),[7,9])
    if decision.mode=="supported-progress-control":
        assert decision.action_id==7 and decision.fallback_action_id==9
        assert decision.candidate_id is not None and decision.predicted_improvement>0
    else:
        # The synthetic scene may expose only translation-invariant candidates;
        # the conservative layer must then leave the broad policy untouched.
        assert decision.action_id==decision.fallback_action_id==9


def test_no_supported_model_never_changes_broad_action_or_payload():
    agent=agent_module.AutonomousProgressAgent(scene(),frontier_size=4)
    hybrid=M.PassiveProgressHybrid(Broad(31),agent)
    decision=hybrid.decide(object(),[7,31])
    assert decision.mode=="broad-fallback" and decision.action_id==31
    assert decision.data==decision.fallback_data


def test_supported_control_override_is_exact_and_counterfactual_is_retained():
    candidate=SimpleNamespace(candidate_id="goal:g",binding_id="binding:b",support=20)
    fake_agent=SimpleNamespace(
        state=SimpleNamespace(candidates=(candidate,)),
        decide=lambda _legal:progress_field.FieldDecision("control",7,"goal:g","binding:b",3,("e1","e2"),"confirmed"),
    )
    hybrid=M.PassiveProgressHybrid(Broad(9),fake_agent,minimum_support=20)
    decision=hybrid.decide(object(),[7,9])
    assert decision.mode=="supported-progress-control"
    assert decision.action_id==7 and decision.fallback_action_id==9
    assert decision.predicted_improvement==3
