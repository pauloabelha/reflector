"""Stable-ID role nomination over R2's bounded visual object proposals."""
from __future__ import annotations

import json
from typing import Any, Mapping

import guarded_goal_protocol as base

PROTOCOL="guarded-obligation-role-nomination-v1"
PROMPT=base.PROMPT+"""
R2 has supplied bounded visual_object IDs. Select only those IDs; do not invent boxes. The controlled role must be action-correlated. Register, obligation, required-state exemplar, and transformer roles must remain distinct objects until transitions prove a relation.
"""


def _ids(workspace):return [str(row["id"]) for row in workspace.get("visual_objects",())]


def response_schema(workspace:Mapping[str,Any])->dict[str,Any]:
    ids=_ids(workspace);ref={"enum":ids}
    site={"type":"object","additionalProperties":False,"required":["site_id","required_state_id"],"properties":{"site_id":ref,"required_state_id":ref}}
    proposal={"type":"object","additionalProperties":False,"required":["controlled_id","register_id","obligations","transformer_ids","rationale"],"properties":{
        "controlled_id":ref,"register_id":ref,
        "obligations":{"type":"array","minItems":1,"maxItems":8,"items":site},
        "transformer_ids":{"type":"array","minItems":1,"maxItems":8,"uniqueItems":True,"items":ref},
        "rationale":{"type":"string","minLength":1,"maxLength":320},
    }}
    return {"type":"object","additionalProperties":False,"required":["protocol","proposal"],"properties":{"protocol":{"const":PROTOCOL},"proposal":{"oneOf":[{"type":"null"},proposal]}}}


def request_payload(workspace:Mapping[str,Any],config:Mapping[str,Any],image_url:str)->dict[str,Any]:
    if not _ids(workspace):raise base.GuardedGoalProtocolError("workspace needs visual objects")
    return {"model":config["model"],"messages":[{"role":"user","content":[{"type":"text","text":PROMPT+"\nEPISTEMIC_WORKSPACE\n"+json.dumps(workspace,sort_keys=True,separators=(",",":"))},{"type":"text","text":"current visual frame"},{"type":"image_url","image_url":{"url":image_url}}]}],"temperature":config.get("temperature",0),"seed":config.get("seed",0),"max_tokens":config.get("max_tokens",2048),"thinking_budget_tokens":config.get("thinking_budget_tokens",1024),"stream":False,"response_format":{"type":"json_schema","json_schema":{"name":"guarded_obligation_role_nomination_v1","strict":True,"schema":response_schema(workspace)}}}


def compile_response(response:Mapping[str,Any],workspace:Mapping[str,Any])->dict[str,Any]:
    parsed=response.get("parsed",response);objects={str(row["id"]):row for row in workspace.get("visual_objects",())}
    if not isinstance(parsed,Mapping) or set(parsed)!={"protocol","proposal"} or parsed.get("protocol")!=PROTOCOL:return {"accepted":False,"reason":"top-level-contract","proposal":None}
    proposal=parsed.get("proposal")
    if proposal is None:return {"accepted":True,"reason":"abstain","proposal":None,"empirical_support":0}
    required={"controlled_id","register_id","obligations","transformer_ids","rationale"}
    if not isinstance(proposal,Mapping) or set(proposal)!=required:return {"accepted":False,"reason":"proposal-contract","proposal":None}
    try:
        controlled=str(proposal["controlled_id"]);register=str(proposal["register_id"])
        obligations=tuple((str(row["site_id"]),str(row["required_state_id"])) for row in proposal["obligations"])
        transformers=tuple(map(str,proposal["transformer_ids"]));refs={controlled,register,*transformers,*(x for row in obligations for x in row)}
    except (KeyError,TypeError):return {"accepted":False,"reason":"grounding-address","proposal":None}
    if not refs or any(ref not in objects for ref in refs):return {"accepted":False,"reason":"grounding-address","proposal":None}
    if not bool(objects[controlled].get("action_correlated")):return {"accepted":False,"reason":"controlled-not-action-correlated","proposal":None}
    # A site's required-state glyph may be embedded in the site composite.
    # Actor, register, sites, and transformers are independent causal roles and
    # may not be collapsed before transition evidence says otherwise.
    sites={site for site,_required in obligations}
    causal_roles={controlled,register,*transformers,*sites}
    if len(causal_roles)!=(2+len(transformers)+len(sites)):
        return {"accepted":False,"reason":"role-collapse","proposal":None}
    if any(required in {controlled,register,*transformers} for _site,required in obligations):
        return {"accepted":False,"reason":"role-collapse","proposal":None}
    return {"accepted":True,"reason":"support-zero-stable-role-nomination","proposal":{"controlled_id":controlled,"register_id":register,"obligations":obligations,"transformer_ids":transformers,"rationale":str(proposal["rationale"])},"empirical_support":0,"required_r2_tests":["persistent-register","arrival-state-change","state-qualified-discharge"]}


__all__=["PROMPT","PROTOCOL","compile_response","request_payload","response_schema"]
