"""One action-opaque registry over heterogeneous progress-goal capabilities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Mapping,Sequence

import compositional_dsl as dsl
import collection_transport as collection
import executor_registry as exact
import gradient_executor as gradient
import progress_synthesis as synthesis
import route_option
import symbolic_transform_adapter as symbolic

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
    symbolic_panels:Sequence[Mapping[str,object]]=(),
)->tuple[CapabilityProposal,...]:
    simple=tuple(sorted(map(int,successors)))
    try:high=list(synthesis.synthesize(initial))
    except synthesis.SynthesisError:high=[]
    executable_kinds={"UnassignedMemberCount","UnservedTerminalCount","UncoveredRequirementCount"}
    exact_candidates=[candidate for candidate in high if candidate.ast["potential"]["type"] in executable_kinds]
    motion={}
    for action,after in successors.items():
        for candidate in exact_candidates:
            delta=synthesis.infer_role_translation(candidate,initial,after)
            if delta is not None and (delta[0]==0)!=(delta[1]==0):motion[delta]=int(action)
    nonmotion=tuple(action for action in simple if action not in motion.values());rows=[]
    collection_capability=collection.induce_collection_capability(
        initial,
        tuple(
            collection.CalibrationTransition(
                opaque_action=action,
                after=after,
                evidence_id="transition:" + synthesis.stable_hash(
                    {"opaque_action": int(action), "after": after}
                )[:20],
            )
            for action,after in sorted(successors.items())
        ),
    )
    if collection_capability is not None:
        rows.append(CapabilityProposal(
            "interactive:collection-transport",
            dict(collection_capability.candidate.ast),
            collection_capability.attention,
            collection_capability.empirical_support,
            collection_capability,
            True,
        ))
    for candidate in exact_candidates:
        try:
            execution=exact.compile_execution(candidate,initial,motion_actions=motion,parameterized_actions=parameterized_actions,release_actions=nonmotion)
            option=ExactOption(candidate,execution,tuple(sorted(motion.items())),tuple(parameterized_actions),nonmotion)
            rows.append(CapabilityProposal("exact:"+candidate.ast["potential"]["type"],candidate.ast,candidate.attention,0,option,False))
        except Exception:pass
    try:
        option=route_option.compile_option(initial,successors);rows.append(CapabilityProposal("interactive:conditional-route",option.goal_ast,90,0,option,True))
    except Exception:pass
    try:
        for option in symbolic.propose(initial,successors,panels=symbolic_panels):
            rows.append(CapabilityProposal("interactive:symbolic-transformation",option.candidate.ast,option.candidate.attention,0,option,True))
    except (synthesis.SynthesisError, symbolic.SYMBOLIC.SymbolicProgressError):pass
    try:compositional=dsl.propose(initial)
    except synthesis.SynthesisError:compositional=()
    before_scene=None;delta_by_action={}
    if compositional:
        try:
            before_scene=synthesis.perceive(initial)
            for action,after in successors.items():
                after_scene=synthesis.perceive(after);deltas={}
                for source in before_scene.regions:
                    matches=[row for row in after_scene.regions if (row.width,row.height,row.normalized)==(source.width,source.height,source.normalized)]
                    if not matches:continue
                    distance=min(abs(row.x-source.x)+abs(row.y-source.y) for row in matches);nearest=[row for row in matches if abs(row.x-source.x)+abs(row.y-source.y)==distance]
                    values={(row.x-source.x,row.y-source.y) for row in nearest}
                    if len(values)==1 and next(iter(values))!=(0,0):deltas[source.region_id]=next(iter(values))
                delta_by_action[int(action)]=deltas
        except synthesis.SynthesisError:delta_by_action={}
    for candidate in compositional:
        for variable,region_id in candidate.binding.items():
            local={}
            for action,deltas in delta_by_action.items():
                if region_id in deltas:local[deltas[region_id]]=action
            if not local:continue
            try:
                execution=gradient.plan(candidate,initial,movable_variable=variable,motion_actions=local)
                rows.append(CapabilityProposal("gradient:"+candidate.ast["potential"]["op"],candidate.ast,candidate.attention,0,(candidate,variable,execution),False))
            except Exception:pass
    unique={(__import__('json').dumps(row.goal_ast,sort_keys=True),row.capability,str(row.execution)):row for row in rows}
    return tuple(sorted(unique.values(),key=lambda row:(-row.attention,row.interactive,row.capability,str(row.execution))))

__all__=["CapabilityProposal","ExactOption","propose"]
