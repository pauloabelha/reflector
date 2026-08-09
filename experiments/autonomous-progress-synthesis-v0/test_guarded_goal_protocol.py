import json
import guarded_goal_protocol as M


def workspace():
    return {"frame":{"width":17,"height":11},"transitions":[{"intervention_ref":"i0","changed":True}],"epistemic_rules":{"support":"environment-only"}}


def proposal():
    box=lambda x,y:{"x1":x,"y1":y,"x2":x+1,"y2":y+1}
    return {"protocol":M.PROTOCOL,"proposal":{"controlled_bbox":box(2,3),"register_bbox":box(0,9),"obligations":[{"site_bbox":box(8,2),"required_state_bbox":box(8,2)}],"transformer_bboxes":[box(5,5)],"rationale":"visible state panel and marked site deserve testing"}}


def test_request_is_visual_action_blind_and_strict():
    request=M.request_payload(workspace(),{"model":"q","max_tokens":500},"data:image/png;base64,AA")
    text=request["messages"][0]["content"][0]["text"].lower()
    assert "obligation sites" in text and "action meaning" in text
    assert request["response_format"]["json_schema"]["strict"] is True
    schema=request["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["proposal"]["oneOf"][1]["properties"]["obligations"]["maxItems"]==8


def test_compiler_accepts_addresses_at_support_zero_but_not_truth():
    out=M.compile_response(proposal(),workspace())
    assert out["accepted"] and out["empirical_support"]==0
    assert out["proposal"]["controlled_bbox"]==(2,3,3,4)
    assert "arrival-state-change" in out["required_r2_tests"]


def test_out_of_frame_and_collapsed_roles_are_rejected():
    bad=proposal();bad["proposal"]["controlled_bbox"]["x2"]=99
    assert M.compile_response(bad,workspace())["reason"]=="grounding-address"
    collapsed=proposal();collapsed["proposal"]["register_bbox"]=collapsed["proposal"]["controlled_bbox"]
    assert M.compile_response(collapsed,workspace())["reason"]=="role-collapse"


def test_abstention_is_valid_and_no_game_semantics_in_contract():
    out=M.compile_response({"protocol":M.PROTOCOL,"proposal":None},workspace())
    assert out["accepted"] and out["proposal"] is None
    contract=json.dumps(M.response_schema(17,11)).lower()+M.PROMPT.lower()
    assert "ls20" not in contract and "rotation" not in contract and "yellow" not in contract
