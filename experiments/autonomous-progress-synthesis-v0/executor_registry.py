"""Executor registry for synthesized goal ASTs, never for game identities."""
from __future__ import annotations
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from typing import Mapping, Sequence

from progress_synthesis import GoalCandidate, SynthesisError, synthesize

HERE=Path(__file__).resolve().parent
EXPERIMENTS=HERE.parent

def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

PLACEMENT=_load("synthesis_placement_executor",EXPERIMENTS/"progress-drive-object-placement-v0"/"object_placement.py")
FLOW=_load("synthesis_flow_executor",EXPERIMENTS/"progress-drive-flow-routing-v0"/"flow_routing.py")


@dataclass(frozen=True)
class Command:
    opaque_action: int
    data: tuple[tuple[str,int],...]=()
    role: str="control"


@dataclass(frozen=True)
class ExecutionProposal:
    candidate_id: str
    binding_id: str
    potential_type: str
    expected_before: int
    expected_after: int
    commands: tuple[Command,...]
    complete: bool
    grounding_memory: object|None=None


@dataclass(frozen=True)
class PlacementMemory:
    reference_grid: tuple[tuple[int,...],...]
    initial_scene: object


def _situated(candidate:GoalCandidate,raw:Sequence[Sequence[int]])->GoalCandidate:
    matches=[item for item in synthesize(raw) if item.candidate_id==candidate.candidate_id]
    if not matches:raise SynthesisError("goal has no current grounding")
    # The binding with greatest structural attention is deterministic; exact
    # empirical support remains attached to the semantic goal, not guessed here.
    return min(matches,key=lambda item:(-item.attention,item.binding_id))


def compile_execution(
    candidate:GoalCandidate,
    raw:Sequence[Sequence[int]],
    *,
    motion_actions:Mapping[tuple[int,int],int],
    parameterized_actions:Sequence[int]=(),
    release_actions:Sequence[int]=(),
    grounding_memory:object|None=None,
)->ExecutionProposal:
    kind=candidate.ast["potential"]["type"]
    # A depleted set may cease to be perceptually enumerable after successful
    # assignments.  Its already-grounded role identity remains live through
    # the explicit tracking memory; do not demand rediscovery from the current
    # frame.  Other goal families still require fresh situated synthesis.
    if kind=="UnassignedMemberCount" and isinstance(grounding_memory,PlacementMemory):
        current=candidate
    else:
        current=_situated(candidate,raw)
    if kind=="UnassignedMemberCount":
        if len(parameterized_actions)!=1:raise SynthesisError("assignment requires exactly one opaque selection channel")
        if grounding_memory is None:
            scene=PLACEMENT.infer_scene(raw);memory=PlacementMemory(tuple(tuple(map(int,row)) for row in raw),scene)
        elif isinstance(grounding_memory,PlacementMemory):
            memory=grounding_memory;scene=PLACEMENT.track_item_scene(memory.reference_grid,raw,memory.initial_scene)
        else:raise SynthesisError("assignment grounding memory has wrong type")
        try:
            # A grounded interaction that may change another object's state is
            # tested before trusting a collision-free geometric simulation.
            assist=PLACEMENT.plan_blocked_assignment_push(scene,motion_actions,select_action_id=parameterized_actions[0]);complete=False
            steps=assist.steps
        except PLACEMENT.NoPlacementPlan:
            plan=PLACEMENT.plan_placement(scene,motion_actions,select_action_id=parameterized_actions[0]);complete=True
            steps=plan.steps
        commands=tuple(Command(step.action_id,tuple(step.data),step.kind) for step in steps)
        return ExecutionProposal(current.candidate_id,current.binding_id,kind,len(scene.items),0 if complete else len(scene.items)-1,commands,complete,memory)
    if kind=="UnservedTerminalCount":
        if len(release_actions)!=1:raise SynthesisError("coverage requires exactly one opaque release channel")
        scene=FLOW.infer_scene(raw);plan=FLOW.plan_flow(scene,motion_actions,release_actions[0])
        return ExecutionProposal(current.candidate_id,current.binding_id,kind,plan.progress_before,plan.progress_after,tuple(Command(action,(),"release" if action==release_actions[0] else "transform") for action in plan.action_ids),True,None)
    if kind=="UncoveredRequirementCount":
        if len(release_actions)!=1:raise SynthesisError("multi-controller coverage requires exactly one opaque focus-switch channel")
        steps={abs(dx or dy) for dx,dy in motion_actions if (dx==0)!=(dy==0)}
        if len(steps)!=1:raise SynthesisError("coverage requires one cardinal lattice step")
        step=next(iter(steps));commands=[];before=0
        assignments=sorted(current.binding["assignments"],key=lambda row:(not row["controller"]["active"],row["controller"]["controller_id"]))
        for index,assignment in enumerate(assignments):
            controller=assignment["controller"];mask={tuple(point) for point in controller["mask"]};requirements={tuple(point) for point in assignment["requirements"]};before+=len(requirements-{(controller["x"]+dx,controller["y"]+dy) for dx,dy in mask})
            options=[]
            # Candidate poses are induced by aligning an observed requirement
            # with an occupied mask cell.  We deliberately do not demand that
            # the object's bounding box remain on-screen: partially occluded or
            # clipped structures are valid visual-world hypotheses, and the
            # environment transition remains the authority on executability.
            anchors={(px-mx,py-my) for px,py in requirements for mx,my in mask}
            for tx,ty in anchors:
                dx,dy=tx-controller["x"],ty-controller["y"]
                if dx%step or dy%step:continue
                if all((px-tx,py-ty) in mask for px,py in requirements):
                    options.append((abs(dx)//step+abs(dy)//step,ty,tx,dx,dy))
            if not options:raise SynthesisError("no lattice translation covers the sparse specification")
            _,_,_,dx,dy=min(options)
            for delta,count in (((-step,0),max(0,-dx)//step),((step,0),max(0,dx)//step),((0,-step),max(0,-dy)//step),((0,step),max(0,dy)//step)):
                if count and delta not in motion_actions:raise SynthesisError("coverage needs an uncalibrated translation")
                commands.extend(Command(motion_actions[delta],(),"cover-requirements") for _ in range(count))
            if index<len(assignments)-1:commands.append(Command(release_actions[0],(),"switch-controller"))
        return ExecutionProposal(current.candidate_id,current.binding_id,kind,before,0,tuple(commands),True,None)
    raise SynthesisError(f"no executor for synthesized potential {kind}")
