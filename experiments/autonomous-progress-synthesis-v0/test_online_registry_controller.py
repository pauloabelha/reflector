import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import online_registry_controller as online
from test_route_option import frame


def test_calibration_is_action_observation_reset_and_then_executes(monkeypatch):
    plan=type("Plan",(),{"commands":(type("C",(),{"opaque_action":9,"data":(),"role":"test"})(),)})()
    option=type("Option",(),{"proposal":plan})()
    proposal=__import__('capability_registry').CapabilityProposal("exact:test",{},10,0,option,False)
    monkeypatch.setattr(online.registry,"propose",lambda *a,**k:(proposal,))
    controller=online.OnlineCapabilityController()
    initial=((0,0),(0,1));changed=((0,0),(1,1))
    assert controller.decide(initial,(0,1),state="NOT_FINISHED").action_id==1
    assert controller.decide(changed,(0,1)).action_id==0
    command=controller.decide(initial,(0,1))
    assert command.action_id==9 and controller.report()["calibration_count"]==1


def test_failed_reset_abstains_without_situated_control(monkeypatch):
    controller=online.OnlineCapabilityController();initial=((0,0),(0,1));changed=((1,0),(0,1))
    assert controller.decide(initial,(0,1)).action_id==1
    assert controller.decide(changed,(0,1)).action_id==0
    assert controller.decide(changed,(0,1)) is None
    assert controller.report()["phase"]=="abstained"


def test_incomplete_exact_phase_recompiles_from_current_observation(monkeypatch):
    memory=object()
    first_command=type("C",(),{"opaque_action":9,"data":(),"role":"enable"})()
    second_command=type("C",(),{"opaque_action":8,"data":(),"role":"finish"})()
    first_plan=type("Plan",(),{"commands":(first_command,),"complete":False,"grounding_memory":memory})()
    second_plan=type("Plan",(),{"commands":(second_command,),"complete":True,"grounding_memory":memory})()
    candidate=type("Candidate",(),{"candidate_id":"goal:x","attention":1,"binding_id":"b:x"})()
    option=__import__('capability_registry').ExactOption(candidate,first_plan,(((1,0),9),),(),())
    proposal=__import__('capability_registry').CapabilityProposal("exact:test",{},10,0,option,False)
    monkeypatch.setattr(online.registry,"propose",lambda *a,**k:(proposal,))
    monkeypatch.setattr(online.registry.synthesis,"synthesize",lambda grid:(candidate,))
    monkeypatch.setattr(online.registry.exact,"compile_execution",lambda *a,**k:second_plan)
    controller=online.OnlineCapabilityController();initial=((0,0),(0,1));changed=((0,0),(1,1))
    assert controller.decide(initial,(0,1)).action_id==1
    assert controller.decide(changed,(0,1)).action_id==0
    assert controller.decide(initial,(0,1)).action_id==9
    assert controller.decide(changed,(0,1)).action_id==8


def test_gradient_requires_direct_potential_improvement_before_continuing(monkeypatch):
    gradient=type("Gradient",(),{"opaque_actions":(9,8)})()
    candidate=type("Candidate",(),{"candidate_id":"goal:g"})()
    proposal=__import__('deployment_capability_registry').CapabilityProposal("gradient:test",{},10,0,(candidate,"?x",gradient),False)
    monkeypatch.setattr(online.registry,"propose",lambda *a,**k:(proposal,))
    controller=online.OnlineCapabilityController();initial=((0,0),(0,1));changed=((0,0),(1,1))
    values=iter((5,4));monkeypatch.setattr(controller,"_measure",lambda grid:next(values))
    assert controller.decide(initial,(0,1)).action_id==1
    assert controller.decide(changed,(0,1)).action_id==0
    assert controller.decide(initial,(0,1)).action_id==9
    assert controller.decide(changed,(0,1)).action_id==8
    assert controller._licensed


def test_unconfirmed_gradient_abstains_after_one_prospective_action(monkeypatch):
    gradient=type("Gradient",(),{"opaque_actions":(9,8)})()
    candidate=type("Candidate",(),{"candidate_id":"goal:g"})()
    proposal=__import__('deployment_capability_registry').CapabilityProposal("gradient:test",{},10,0,(candidate,"?x",gradient),False)
    monkeypatch.setattr(online.registry,"propose",lambda *a,**k:(proposal,))
    controller=online.OnlineCapabilityController();initial=((0,0),(0,1));changed=((0,0),(1,1))
    monkeypatch.setattr(controller,"_measure",lambda grid:5)
    assert controller.decide(initial,(0,1)).action_id==1
    assert controller.decide(changed,(0,1)).action_id==0
    assert controller.decide(initial,(0,1)).action_id==9
    assert controller.decide(changed,(0,1)) is None
    assert controller.report()["phase"]=="abstained" and controller.used==1


def test_refuted_goal_resets_before_trying_distinct_next_hypothesis(monkeypatch):
    def proposal(name,action):
        gradient=type("Gradient",(),{"opaque_actions":(action,)})()
        candidate=type("Candidate",(),{"candidate_id":"goal:"+name})()
        return __import__('deployment_capability_registry').CapabilityProposal("gradient:"+name,{"goal":name},10,0,(candidate,"?x",gradient),False)
    first,second=proposal("a",9),proposal("b",8)
    monkeypatch.setattr(online.registry,"propose",lambda *a,**k:(first,second))
    controller=online.OnlineCapabilityController();initial=((0,0),(0,1));changed=((0,0),(1,1))
    values=iter((5,5,4));monkeypatch.setattr(controller,"_measure",lambda grid:next(values))
    assert controller.decide(initial,(0,1)).action_id==1
    assert controller.decide(changed,(0,1)).action_id==0
    assert controller.decide(initial,(0,1)).action_id==9
    assert controller.decide(changed,(0,1)).action_id==0
    assert controller.decide(initial,(0,1)).action_id==8
    assert controller._tested==["gradient:a","gradient:b"]
