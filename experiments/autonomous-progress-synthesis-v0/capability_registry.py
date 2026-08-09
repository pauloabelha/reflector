"""One action-opaque registry over heterogeneous progress-goal capabilities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Mapping,Sequence

import compositional_dsl as dsl
import executor_registry as exact
import gradient_executor as gradient
import progress_synthesis as synthesis
import route_option

@dataclass(frozen=True)
class CapabilityProposal:
    capability:str
    goal_ast:dict
    attention:int
    empirical_support:int
    execution:Any
    interactive:bool

@dataclass(frozen=True)
class ExactOption:
    candidate:Any
    proposal:Any
    motion_actions:tuple[tuple[tuple[int,int],int],...]
    parameterized_actions:tuple[int,...]
    release_actions:tuple[int,...]

def propose(
    initial:Sequence[Sequence[int]],
    successors:Mapping[int,Sequence[Sequence[int]]],
    *,
    parameterized_actions:Sequence[int]=(),
)->tuple[CapabilityProposal,...]:
    simple=tuple(sorted(map(int,successors)))
    try:high=list(synthesis.synthesize(initial))
    except synthesis.SynthesisError:high=[]
    motion={}
    for action,after in successors.items():
        deltas=[synthesis.infer_role_translation(candidate,initial,after) for candidate in high]
        delta=next((row for row in deltas if row is not None and (row[0]==0)!=(row[1]==0)),None)
        if delta is not None:motion[delta]=int(action)
    nonmotion=tuple(action for action in simple if action not in motion.values());rows=[]
    for candidate in high:
        try:
            execution=exact.compile_execution(candidate,initial,motion_actions=motion,parameterized_actions=parameterized_actions,release_actions=nonmotion)
            option=ExactOption(candidate,execution,tuple(sorted(motion.items())),tuple(parameterized_actions),nonmotion)
            rows.append(CapabilityProposal("exact:"+candidate.ast["potential"]["type"],candidate.ast,candidate.attention,0,option,False))
        except Exception:pass
    try:
        option=route_option.compile_option(initial,successors);rows.append(CapabilityProposal("interactive:conditional-route",option.goal_ast,90,0,option,True))
    except Exception:pass
    try:compositional=dsl.propose(initial)
    except synthesis.SynthesisError:compositional=()
    for candidate in compositional:
        for variable,region_id in candidate.binding.items():
            local={}
            for action,after in successors.items():
                moved=gradient.moved_variables(candidate,initial,after)
                if variable in moved:local[moved[variable]]=int(action)
            if not local:continue
            try:
                execution=gradient.plan(candidate,initial,movable_variable=variable,motion_actions=local)
                rows.append(CapabilityProposal("gradient:"+candidate.ast["potential"]["op"],candidate.ast,candidate.attention,0,(candidate,variable,execution),False))
            except Exception:pass
    unique={(__import__('json').dumps(row.goal_ast,sort_keys=True),row.capability,str(row.execution)):row for row in rows}
    return tuple(sorted(unique.values(),key=lambda row:(-row.attention,row.interactive,row.capability,str(row.execution))))

__all__=["CapabilityProposal","ExactOption","propose"]
