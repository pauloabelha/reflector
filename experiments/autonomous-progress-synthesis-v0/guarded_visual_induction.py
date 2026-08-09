"""Source-blind visual grounding for guarded-obligation capabilities."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Mapping, Sequence

import guarded_obligation_capability as guarded
import region_object_projection as objects


class GuardedVisualInductionError(ValueError):pass


Grid=tuple[tuple[int,...],...]


@dataclass(frozen=True,slots=True)
class MotionCalibration:
    opaque_action:int
    before_anchor:tuple[int,int]
    after_anchor:tuple[int,int]
    actor_size:tuple[int,int]
    after_grid:Grid
    transition_id:str


@dataclass(frozen=True,slots=True)
class VisualRoleHypothesis:
    hypothesis_id:str
    actor_id:str
    register_id:str
    obligation_id:str
    transformer_id:str
    actor_anchor:tuple[int,int]
    obligation_anchor:tuple[int,int]
    transformer_anchor:tuple[int,int]
    current_register:guarded.Register
    required_register:guarded.Register
    transitions:tuple[tuple[str,int,str],...]
    movement_actions:tuple[tuple[tuple[int,int],int],...]
    basis_ids:tuple[str,...]
    attention:int


def _grid(raw)->Grid:
    value=tuple(tuple(map(int,row)) for row in raw)
    if not value or not value[0] or any(len(row)!=len(value[0]) for row in value):raise GuardedVisualInductionError("rectangular frame required")
    return value


def _register_signature(item:objects.RegionObject)->guarded.Register|None:
    if not item.embedded_state_signatures:return None
    # Prefer structural diversity over raw area.  Large uniform enclosure
    # fragments are stable decoration; the embedded glyph is the component
    # whose canonical shape contains the richest arrangement of cells.
    # Palette tokens are situated observations, not transferable semantics.
    value,shape=max(
        item.embedded_state_signatures,
        key=lambda row:(len(set(row[1])),len(row[1]),row),
    )
    return ("palette:"+str(value),"shape:"+__import__('hashlib').sha256(repr(shape).encode()).hexdigest()[:20])


def _nearest_anchor(item:objects.RegionObject,start:tuple[int,int],steps:tuple[int,int],width:int,height:int)->tuple[int,int]:
    cx=(item.bbox[0]+item.bbox[2]-width)/2;cy=(item.bbox[1]+item.bbox[3]-height)/2
    sx,sy=steps
    x=start[0]+round((cx-start[0])/sx)*sx;y=start[1]+round((cy-start[1])/sy)*sy
    return int(x),int(y)


def enumerate_hypotheses(initial,calibrations:Sequence[MotionCalibration],*,max_hypotheses:int=16)->tuple[VisualRoleHypothesis,...]:
    grid=_grid(initial);direct=[row for row in calibrations if row.before_anchor!=row.after_anchor]
    if not direct: return ()
    starts={row.before_anchor for row in direct};sizes={row.actor_size for row in direct}
    if len(starts)!=1 or len(sizes)!=1:raise GuardedVisualInductionError("action-correlated actor is ambiguous")
    start=next(iter(starts));width,height=next(iter(sizes));deltas={(row.after_anchor[0]-row.before_anchor[0],row.after_anchor[1]-row.before_anchor[1]):row.opaque_action for row in direct}
    if len(deltas)!=len(direct):raise GuardedVisualInductionError("motion mapping conflicts")
    xs={abs(dx) for dx,dy in deltas if dx and not dy};ys={abs(dy) for dx,dy in deltas if dy and not dx}
    if len(xs)!=1 or len(ys)!=1:raise GuardedVisualInductionError("complete cardinal lattice is not calibrated")
    step_x,step_y=next(iter(xs)),next(iter(ys))
    actor_box=start[0],start[1],start[0]+width,start[1]+height
    projected=objects.project_objects(grid,controlled_bboxes=(actor_box,));actors=[row for row in projected if row.action_correlated]
    if len(actors)!=1:return ()
    actor=actors[0];others=[row for row in projected if row is not actor]
    # Infer substrate only from pixels revealed after the actor departed.
    substrate=[]
    for row in direct:
        x,y=row.before_anchor;patch=[row.after_grid[yy][xx] for yy in range(y,y+height) for xx in range(x,x+width)]
        if patch:substrate.append(Counter(patch).most_common(1)[0][0])
    if not substrate or len(set(substrate))!=1:return ()
    floor=substrate[0]
    nodes=set();max_y,max_x=len(grid)-height,len(grid[0])-width
    for y in range(start[1]%step_y,max_y+1,step_y):
      for x in range(start[0]%step_x,max_x+1,step_x):
        patch=[grid[yy][xx] for yy in range(y,y+height) for xx in range(x,x+width)]
        if patch.count(floor)>=len(patch)*4//5:nodes.add((x,y))
    nodes.add(start)
    anchored={row.object_id:_nearest_anchor(row,start,(step_x,step_y),width,height) for row in others}
    nodes.update(anchored.values())
    topology=[]
    for node in sorted(nodes):
      for delta,action in sorted(deltas.items()):
        target=node[0]+delta[0],node[1]+delta[1]
        if target in nodes:topology.append((f"node:{node[0]}:{node[1]}",int(action),f"node:{target[0]}:{target[1]}"))
    registers=[row for row in others if row.boundary_distance<=max(step_x,step_y) and row.enclosure_count and _register_signature(row)]
    obligations=[row for row in others if row.boundary_distance>max(step_x,step_y) and row.enclosure_count and _register_signature(row)]
    transformers=[row for row in others if row.boundary_distance>max(step_x,step_y) and row not in obligations]
    rows=[];basis=tuple(sorted({"frame:initial",*(row.transition_id for row in calibrations)}))
    for register in registers:
      current=_register_signature(register)
      for obligation in obligations:
        required=_register_signature(obligation)
        for transformer in transformers:
          body={"actor":actor.object_id,"register":register.object_id,"obligation":obligation.object_id,"transformer":transformer.object_id}
          hid="gvh:"+__import__('hashlib').sha256(repr(sorted(body.items())).encode()).hexdigest()[:20]
          attention=70+10*int(register.boundary_distance<step_x)+10*int(obligation.enclosure_count>0)+5*int(transformer.enclosure_count==0)
          rows.append(VisualRoleHypothesis(hid,actor.object_id,register.object_id,obligation.object_id,transformer.object_id,start,anchored[obligation.object_id],anchored[transformer.object_id],current,required,tuple(topology),tuple(sorted(deltas.items())),basis,attention))
    unique={row.hypothesis_id:row for row in rows}
    return tuple(sorted(unique.values(),key=lambda row:(-row.attention,row.hypothesis_id))[:max_hypotheses])


def probe_capability(hypothesis:VisualRoleHypothesis)->guarded.GuardedCapability:
    """Compile only a transformer probe until its register effect is observed."""
    world=guarded.GuardedWorld(
        f"node:{hypothesis.actor_anchor[0]}:{hypothesis.actor_anchor[1]}",hypothesis.current_register,
        hypothesis.transitions,
        (guarded.GuardedObligation("obligation:"+hypothesis.obligation_id,f"node:{hypothesis.obligation_anchor[0]}:{hypothesis.obligation_anchor[1]}",hypothesis.required_register),),
        (),
        (f"node:{hypothesis.transformer_anchor[0]}:{hypothesis.transformer_anchor[1]}",),
        hypothesis.basis_ids,
    )
    return guarded.compile_capability(world,attention=hypothesis.attention)


def observe_register(raw,reference_bbox:tuple[int,int,int,int])->guarded.Register|None:
    """Read one persistent register at its grounded screen address."""
    candidates=[row for row in objects.project_objects(raw) if row.bbox==tuple(reference_bbox)]
    values={_register_signature(row) for row in candidates}
    values.discard(None)
    return next(iter(values)) if len(values)==1 else None


__all__=["GuardedVisualInductionError","MotionCalibration","VisualRoleHypothesis","enumerate_hypotheses","observe_register","probe_capability"]
