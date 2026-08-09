import guarded_goal_protocol_v1 as M


def ws():return {"frame":{"width":20,"height":20},"visual_objects":[{"id":"actor","action_correlated":True},{"id":"hud","action_correlated":False},{"id":"target","action_correlated":False},{"id":"glyph","action_correlated":False},{"id":"switch","action_correlated":False}]}
def response():return {"protocol":M.PROTOCOL,"proposal":{"controlled_id":"actor","register_id":"hud","obligations":[{"site_id":"target","required_state_id":"glyph"}],"transformer_ids":["switch"],"rationale":"distinct visible roles"}}


def test_stable_id_contract_accepts_distinct_support_zero_roles():
    out=M.compile_response(response(),ws());assert out["accepted"] and out["empirical_support"]==0
    assert out["proposal"]["obligations"]==(("target","glyph"),)


def test_rejects_noncorrelated_controller_and_role_collapse():
    bad=response();bad["proposal"]["controlled_id"]="hud";assert M.compile_response(bad,ws())["reason"]=="controlled-not-action-correlated"
    bad=response();bad["proposal"]["transformer_ids"]=["target"];assert M.compile_response(bad,ws())["reason"]=="role-collapse"


def test_required_exemplar_may_be_embedded_in_site_composite():
    value=response();value["proposal"]["obligations"][0]["required_state_id"]="target"
    assert M.compile_response(value,ws())["accepted"]
