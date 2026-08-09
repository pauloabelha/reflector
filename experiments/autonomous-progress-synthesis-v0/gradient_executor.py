"""Generic model-based option construction for compositional potentials."""
from __future__ import annotations

from dataclasses import dataclass,replace
from typing import Mapping,Sequence

import compositional_dsl as dsl
import progress_synthesis as synthesis


@dataclass(frozen=True)
class GradientPlan:
    variable:str
    start_value:int
    predicted_value:int
    translation:tuple[int,int]
    opaque_actions:tuple[int,...]


def moved_variables(candidate,before_raw:Sequence[Sequence[int]],after_raw:Sequence[Sequence[int]])->dict[str,tuple[int,int]]:
    before=synthesis.perceive(before_raw);after=synthesis.perceive(after_raw);before_map={row.region_id:row for row in before.regions};output={}
    for variable,region_id in candidate.binding.items():
        source=before_map.get(region_id)
        if source is None:continue
        matches=[row for row in after.regions if (row.width,row.height,row.normalized)==(source.width,source.height,source.normalized)]
        if not matches:continue
        distance=min(abs(row.x-source.x)+abs(row.y-source.y) for row in matches);nearest=[row for row in matches if abs(row.x-source.x)+abs(row.y-source.y)==distance]
        deltas={(row.x-source.x,row.y-source.y) for row in nearest}
        if len(deltas)==1 and next(iter(deltas))!=(0,0):output[variable]=next(iter(deltas))
    return output


def _translated(region:synthesis.Region,dx:int,dy:int)->synthesis.Region:
    return replace(region,x=region.x+dx,y=region.y+dy,cells=frozenset((x+dx,y+dy) for x,y in region.cells))


def plan(
    candidate,
    raw:Sequence[Sequence[int]],
    *,
    movable_variable:str,
    motion_actions:Mapping[tuple[int,int],int],
    max_steps:int=24,
)->GradientPlan:
    if candidate.ast.get("protocol")!="compositional-progress-dsl-v0":raise synthesis.SynthesisError("gradient executor requires compositional DSL")
    if movable_variable not in candidate.binding:raise synthesis.SynthesisError("movable variable is not grounded")
    cardinal=[delta for delta in motion_actions if (delta[0]==0)!=(delta[1]==0)]
    if not cardinal:raise synthesis.SynthesisError("no grounded cardinal motion model")
    magnitudes={abs(dx or dy) for dx,dy in cardinal}
    if len(magnitudes)!=1:raise synthesis.SynthesisError("motion model has inconsistent lattice steps")
    step=next(iter(magnitudes));scene=synthesis.perceive(raw);roles=dsl._region_map(scene,candidate.binding);start=dsl._eval(candidate.ast["potential"],roles)
    best=(start,0,0,0)
    for ix in range(-max_steps,max_steps+1):
        for iy in range(-max_steps,max_steps+1):
            if abs(ix)+abs(iy)>max_steps:continue
            dx,dy=ix*step,iy*step;trial=dict(roles);trial[movable_variable]=_translated(roles[movable_variable],dx,dy)
            value=dsl._eval(candidate.ast["potential"],trial);key=(value,abs(ix)+abs(iy),iy,ix)
            if key<(best[0],best[1],best[3]//step if step else 0,best[2]//step if step else 0):best=(value,abs(ix)+abs(iy),dx,dy)
    value,_distance,dx,dy=best
    if value>=start:raise synthesis.SynthesisError("no bounded translation improves the potential")
    actions=[]
    for delta,count in (((-step,0),max(0,-dx)//step),((step,0),max(0,dx)//step),((0,-step),max(0,-dy)//step),((0,step),max(0,dy)//step)):
        if count and delta not in motion_actions:raise synthesis.SynthesisError("improving translation needs an ungrounded intervention")
        actions.extend([motion_actions[delta]]*count)
    return GradientPlan(movable_variable,start,value,(dx,dy),tuple(actions))


__all__=["GradientPlan","moved_variables","plan"]
