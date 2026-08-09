import workspace_goal_revision as M


GOAL = {"family":"alignment","controlled_id":"p0","members":["e1"],"container_id":None,"potential":"AlignmentResidual","terminal":"Aligned","interaction_candidate":None,"rationale":"first"}


def request():
    goal={"type":"object","properties":{"family":{"enum":list(M.FAMILY_CONTRACTS)},"potential":{"enum":[v[0] for v in M.FAMILY_CONTRACTS.values()]},"terminal":{"enum":[v[1] for v in M.FAMILY_CONTRACTS.values()]}}}
    return {"messages":[{"content":[{"type":"text","text":"contract\nEPISTEMIC_WORKSPACE\n{}"},{"type":"image_url","image_url":{"url":"data:image/png;base64,AA"}}]}],"response_format":{"type":"json_schema","json_schema":{"schema":{"properties":{"goal":{"oneOf":[{"type":"null"},goal]}}}}}}


def test_feedback_is_compact_environment_evidence_and_preserves_multimodal_request():
    original=request();out=M.build_revision_payload(original,GOAL,{"status":"attention-suppressed-plateau","known_evaluations":21,"best_value":12,"environment_refutations":0,"last_reason":"no-new-minimum-within-patience"})
    assert out is not original and out["messages"][0]["content"][1]==original["messages"][0]["content"][1]
    assert "ENVIRONMENT_FEEDBACK" in out["messages"][0]["content"][0]["text"]
    assert "game" not in out["messages"][0]["content"][0]["text"].lower()
    branches=out["response_format"]["json_schema"]["schema"]["properties"]["goal"]["oneOf"][1:]
    assert len(branches)==6
    assert {(row["properties"]["family"]["const"],row["properties"]["potential"]["const"],row["properties"]["terminal"]["const"]) for row in branches}=={(key,*value) for key,value in M.FAMILY_CONTRACTS.items()}


def test_semantic_repeat_is_rejected_even_if_rationale_and_intervention_change():
    repeated=dict(GOAL,rationale="new prose",interaction_candidate="im9")
    result=M.compile_revision({"parsed":{}},{},GOAL,lambda _r,_w:{"accepted":True,"goal":repeated})
    assert not result["accepted"] and result["reason"]=="semantic-repeat-after-environment-feedback"


def test_nontrivial_revision_remains_support_zero():
    revised=dict(GOAL,family="connectivity",potential="ComponentDeficit",terminal="Connected")
    result=M.compile_revision({"parsed":{}},{},GOAL,lambda _r,_w:{"accepted":True,"goal":revised,"empirical_support":99})
    assert result["accepted"] and result["empirical_support"]==0 and "revision_of" in result


def test_revision_requires_a_real_failure_status():
    try:M.build_revision_payload(request(),GOAL,{"status":"active"})
    except M.GoalRevisionError:pass
    else:raise AssertionError("active goal was eligible for failure revision")
