"""One action-opaque registry over heterogeneous progress-goal capabilities."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any,Mapping,Sequence

import compositional_dsl as dsl
import collection_transport as collection
import executor_registry as exact
import gradient_executor as gradient
import guarded_obligation_capability as guarded
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
class OperationalStatus:
    """Whether a proposal can presently participate in control.

    Attention is deliberately absent from this judgment.  A salient object
    with unresolved grounding/effect ports remains useful workspace content,
    but it must not win the arbiter merely because it was expensive to form.
    """
    state:str
    reason:str
    open_ports:tuple[str,...]=()

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
            try:delta=synthesis.infer_role_translation(candidate,initial,after)
            except synthesis.SynthesisError:continue
            if delta is not None and (delta[0]==0)!=(delta[1]==0):motion[delta]=int(action)
    nonmotion=tuple(action for action in simple if action not in motion.values());rows=[]
    try:
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
    except (synthesis.SynthesisError,collection.CollectionCapabilityError):
        collection_capability=None
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


def propose_calibrated(
    current:Sequence[Sequence[int]],
    *,
    motion_actions:Mapping[tuple[int,int],int],
    parameterized_actions:Sequence[int]=(),
    release_actions:Sequence[int]=(),
)->tuple[CapabilityProposal,...]:
    """Compile exact situated capabilities from already observed action laws.

    Unlike :func:`propose`, this boundary needs no one-step reset successors.
    The caller supplies only action effects learned from ordinary live
    transitions.  Opaque action identities remain in the situated execution
    object and never enter the transferable goal AST.
    """
    normalized={
        (int(delta[0]),int(delta[1])):int(action)
        for delta,action in motion_actions.items()
        if (int(delta[0])==0)!=(int(delta[1])==0)
    }
    if len(set(normalized.values())) != len(normalized):
        raise synthesis.SynthesisError("one opaque action cannot denote multiple translations")
    try:candidates=list(synthesis.synthesize(current))
    except synthesis.SynthesisError:return ()
    executable={"UnassignedMemberCount","UnservedTerminalCount","UncoveredRequirementCount"}
    rows=[]
    for candidate in candidates:
        if candidate.ast["potential"]["type"] not in executable:continue
        try:
            execution=exact.compile_execution(
                candidate,
                current,
                motion_actions=normalized,
                parameterized_actions=tuple(map(int,parameterized_actions)),
                release_actions=tuple(map(int,release_actions)),
            )
        except Exception:continue
        option=ExactOption(
            candidate,
            execution,
            tuple(sorted(normalized.items())),
            tuple(map(int,parameterized_actions)),
            tuple(map(int,release_actions)),
        )
        rows.append(CapabilityProposal(
            "exact:"+candidate.ast["potential"]["type"],
            candidate.ast,
            candidate.attention,
            0,
            option,
            False,
        ))
    unique={(row.capability,row.execution.candidate.candidate_id,row.execution.proposal.binding_id):row for row in rows}
    return tuple(sorted(unique.values(),key=lambda row:(-row.attention,row.capability,str(row.execution))))


def propose_guarded(world:guarded.GuardedWorld)->CapabilityProposal:
    """Register one already-grounded, evidence-linked guarded task model."""
    capability=guarded.compile_capability(world)
    return CapabilityProposal(
        "interactive:guarded-obligations",
        dict(capability.goal_ast),
        capability.attention,
        capability.empirical_support,
        capability,
        True,
    )


def operational_status(proposal:CapabilityProposal)->OperationalStatus:
    """Return a game-blind execution contract for one registry object."""
    kind=proposal.capability
    if kind.startswith("exact:"):
        commands=tuple(getattr(getattr(proposal.execution,"proposal",None),"commands",()))
        return OperationalStatus("ready","compiled-exact-plan") if commands else OperationalStatus("blocked","empty-exact-plan")
    if kind.startswith("gradient:"):
        actions=tuple(getattr(proposal.execution[2],"opaque_actions",()))
        return OperationalStatus("ready","compiled-gradient-plan") if actions else OperationalStatus("blocked","empty-gradient-plan")
    if kind=="interactive:conditional-route":
        return OperationalStatus("ready","closed-loop-route-policy")
    if kind=="interactive:symbolic-transformation":
        return OperationalStatus("ready","closed-loop-symbolic-policy")
    if kind=="interactive:guarded-obligations":
        return OperationalStatus("ready","grounded-guarded-policy")
    if kind=="interactive:collection-transport":
        ports=tuple(getattr(proposal.execution,"open_ports",()))
        if ports:
            return OperationalStatus("blocked","unresolved-grounding-or-effect-ports",ports)
        try:collection.compile_transport_probe(proposal.execution)
        except Exception as error:
            return OperationalStatus("blocked",f"probe-compilation-failed:{type(error).__name__}")
        return OperationalStatus("probe","bounded-environment-adjudicated-transport-probe")
    if kind=="interactive:editable-topology":
        # Its planner consumes a replay/transition oracle.  That is useful in
        # an offline lab, but unavailable to a one-pass Kaggle controller.
        return OperationalStatus("offline-only","requires-transition-oracle")
    return OperationalStatus("blocked","no-runtime-adapter")


def select_operational(proposals:Sequence[CapabilityProposal])->CapabilityProposal|None:
    """Choose only proposals that can act or run a bounded empirical probe."""
    eligible=[]
    rank={"ready":0,"probe":1}
    for row in proposals:
        status=operational_status(row)
        if status.state in rank:
            eligible.append((rank[status.state],-row.empirical_support,-row.attention,row.capability,str(row.execution),row))
    return min(eligible)[-1] if eligible else None

__all__=["CapabilityProposal","ExactOption","OperationalStatus","operational_status","propose","propose_calibrated","propose_guarded","select_operational"]
