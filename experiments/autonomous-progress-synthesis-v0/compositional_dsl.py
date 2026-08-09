"""Closed, bounded, visually executable progress-potential grammar."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any,Mapping,Sequence

from progress_synthesis import GoalCandidate,Region,Scene,SynthesisError,perceive,stable_hash

OPS=frozenset({"TranslationAlignmentResidual","AxisMisalignment","BoundingBoxGap","NormalizedMaskMismatch","ContainmentDeficit","Sum","Max"})
MAX_DEPTH=3
MAX_NODES=12
MAX_TERMS=4


def _walk(value:Any,depth:int=0)->tuple[int,int]:
    if depth>MAX_DEPTH:raise SynthesisError("potential AST exceeds depth bound")
    if not isinstance(value,Mapping) or value.get("op") not in OPS:raise SynthesisError("unknown potential operator")
    op=value["op"]
    if op in {"Sum","Max"}:
        terms=value.get("terms")
        if not isinstance(terms,list) or not 2<=len(terms)<=MAX_TERMS:raise SynthesisError("composition arity is out of bounds")
        stats=[_walk(term,depth+1) for term in terms];return 1+sum(n for n,_ in stats),max(d for _,d in stats)
    if set(value)!={"op","arguments"} or not isinstance(value.get("arguments"),list) or len(value["arguments"])!=2:raise SynthesisError("primitive requires exactly two role variables")
    if any(not isinstance(arg,str) or not arg.startswith("?") for arg in value["arguments"]):raise SynthesisError("primitive arguments must be variables")
    return 1,depth


def validate_expression(expression:Mapping[str,Any])->None:
    nodes,_depth=_walk(expression)
    if nodes>MAX_NODES:raise SynthesisError("potential AST exceeds node bound")
    text=str(expression).lower()
    forbidden=("action","game","color","palette","pixel","bbox","coordinate","trajectory","ar25","wa30")
    if any(token in text for token in forbidden):raise SynthesisError("transferable AST contains a forbidden semantic shortcut")


def _variables(value:Mapping[str,Any])->set[str]:
    if value["op"] in {"Sum","Max"}:
        return set().union(*(_variables(term) for term in value["terms"]))
    return set(value["arguments"])


def compile_candidate(expression:Mapping[str,Any],binding:Mapping[str,str],scene:Scene,*,attention:int=50)->GoalCandidate:
    validate_expression(expression);variables=_variables(expression)
    if set(binding)!=variables:raise SynthesisError("binding must ground every and only declared variable")
    visible={region.region_id for region in scene.regions}
    if len(set(binding.values()))!=len(binding) or any(value not in visible for value in binding.values()):raise SynthesisError("binding is not an injective visible grounding")
    ast={"protocol":"compositional-progress-dsl-v0","type":"GoalPotential","roles":{var:{"type":"ObservedRegion"} for var in sorted(variables)},"potential":dict(expression),"direction":"minimize","lower_bound":0,"terminal":{"type":"EqualsLowerBound"}}
    cid="goal:"+stable_hash(ast)[:24];bid="grounding:"+stable_hash({"candidate_id":cid,"binding":dict(binding)})[:24]
    return GoalCandidate(cid,bid,ast,dict(binding),max(0,min(100,int(attention))))


def _primitive(op:str,a:str="?a",b:str="?b")->dict[str,Any]:return {"op":op,"arguments":[a,b]}


def propose(raw:Sequence[Sequence[int]],*,limit:int=96)->tuple[GoalCandidate,...]:
    scene=perceive(raw);rows=[];pair_rows=[]
    useful=[region for region in scene.regions if region.area>=2 and region.width<scene.width and region.height<scene.height]
    for left,right in combinations(useful,2):
        ratio=max(left.width/right.width,right.width/left.width,left.height/right.height,right.height/left.height)
        larger,smaller=(left,right) if left.area>=right.area else (right,left)
        containment=bool(larger.holes and larger.area>=smaller.area and abs((larger.width-2)-smaller.width)<=1 and abs((larger.height-2)-smaller.height)<=1)
        if ratio<=2 or containment:
            pair_rows.append((not containment,left.normalized!=right.normalized,ratio,left.region_id,right.region_id,left,right,containment))
    # Bound composition before allocating candidates.  The ordering is purely
    # structural: capacity-compatible and repeated-shape pairs first, then
    # scale similarity and stable addresses.
    max_pairs=max(8,(limit+3)//4)
    for _nc,_nd,_ratio,_lid,_rid,left,right,containment in sorted(pair_rows)[:max_pairs]:
        ratio=max(left.width/right.width,right.width/left.width,left.height/right.height,right.height/left.height);binding={"?a":left.region_id,"?b":right.region_id}
        if ratio<=2:
            rows.append(compile_candidate(_primitive("TranslationAlignmentResidual"),binding,scene,attention=45+(15 if left.normalized==right.normalized else 0)))
            rows.append(compile_candidate(_primitive("AxisMisalignment"),binding,scene,attention=35+(15 if left.normalized==right.normalized else 0)))
            rows.append(compile_candidate(_primitive("BoundingBoxGap"),binding,scene,attention=30))
            rows.append(compile_candidate(_primitive("NormalizedMaskMismatch"),binding,scene,attention=30+(15 if ratio<=1.25 else 0)))
        larger,smaller=(left,right) if left.area>=right.area else (right,left)
        if containment:
            rows.append(compile_candidate(_primitive("ContainmentDeficit"),{"?a":smaller.region_id,"?b":larger.region_id},scene,attention=55))
    unique={(row.candidate_id,row.binding_id):row for row in rows}
    return tuple(sorted(unique.values(),key=lambda row:(-row.attention,row.candidate_id,row.binding_id))[:limit])


def _region_map(scene:Scene,binding:Mapping[str,str])->dict[str,Region]:
    visible={region.region_id:region for region in scene.regions}
    try:return {variable:visible[region_id] for variable,region_id in binding.items()}
    except KeyError as error:raise SynthesisError("situated role is not visible") from error


def _eval(expression:Mapping[str,Any],roles:Mapping[str,Region])->int:
    op=expression["op"]
    if op in {"Sum","Max"}:
        values=[_eval(term,roles) for term in expression["terms"]]
        return sum(values) if op=="Sum" else max(values)
    left,right=(roles[var] for var in expression["arguments"])
    if op=="TranslationAlignmentResidual":return abs((left.x*2+left.width)-(right.x*2+right.width))+abs((left.y*2+left.height)-(right.y*2+right.height))
    if op=="AxisMisalignment":return min(abs((left.x*2+left.width)-(right.x*2+right.width)),abs((left.y*2+left.height)-(right.y*2+right.height)))
    if op=="BoundingBoxGap":
        dx=max(0,right.x-(left.x+left.width),left.x-(right.x+right.width));dy=max(0,right.y-(left.y+left.height),left.y-(right.y+right.height));return dx+dy
    if op=="NormalizedMaskMismatch":return len(left.normalized^right.normalized)
    if op=="ContainmentDeficit":
        return sum(not(right.x<=x<right.x+right.width and right.y<=y<right.y+right.height) for x,y in left.cells)
    raise SynthesisError("unreachable operator")


def evaluate(candidate:GoalCandidate,raw:Sequence[Sequence[int]])->int:
    scene=perceive(raw);return _eval(candidate.ast["potential"],_region_map(scene,candidate.binding))


def qwen_contract(scene:Scene)->dict[str,Any]:
    """Strict shared contract: semantics are open, observables remain closed."""
    return {"protocol":"compositional-progress-dsl-v0","allowed_operators":sorted(OPS),"limits":{"max_depth":MAX_DEPTH,"max_nodes":MAX_NODES,"max_terms":MAX_TERMS},"visible_region_ids":[row.region_id for row in scene.regions],"rule":"Proposals start at support zero; only direct environment transitions may raise support."}


__all__=["OPS","compile_candidate","evaluate","propose","qwen_contract","validate_expression"]
