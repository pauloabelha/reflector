"""Capability adapter for visually grounded conditional route fields."""
from __future__ import annotations
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from typing import Mapping,Sequence

HERE=Path(__file__).resolve().parent;EXPERIMENTS=HERE.parent
def _load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
TRACKER=_load("unified_route_tracker",EXPERIMENTS/"progress-goal-generic-calibration-v1"/"tracker.py")
ROUTE=_load("unified_route_kernel",EXPERIMENTS/"progress-drive-conditional-route-v0"/"conditional_route.py")

@dataclass(frozen=True)
class RouteOption:
    goal_ast:dict
    opaque_actions:tuple[int,...]
    route_nodes:tuple[tuple[int,int],...]
    controlled_signature:tuple[tuple[int,...],int,tuple[int,int]]
    field:object
    motion_actions:tuple[tuple[tuple[int,int],int],...]

def calibrated_controller(initial:Sequence[Sequence[int]],successors:Mapping[int,Sequence[Sequence[int]]]):
    rows={int(action):TRACKER.pixel_motion_hypotheses(initial,after) for action,after in successors.items()}
    signatures={}
    for action,motions in rows.items():
        for motion in motions:signatures.setdefault((motion.colors,motion.mass,motion.size),[]).append((action,motion))
    def rank(item):
        signature,observations=item;starts={motion.before_anchor for _action,motion in observations}
        return (-len({a for a,_ in observations}),len(starts),-len(signature[0]),-signature[1],signature)
    ranked=sorted(signatures.items(),key=rank)
    if not ranked:raise ROUTE.ConditionalRouteError("no action-correlated visual controller")
    signature,observations=ranked[0]
    if len(ranked)>1:
        left=(len({a for a,_ in ranked[0][1]}),-len({m.before_anchor for _a,m in ranked[0][1]}),len(ranked[0][0][0]),ranked[0][0][1])
        right=(len({a for a,_ in ranked[1][1]}),-len({m.before_anchor for _a,m in ranked[1][1]}),len(ranked[1][0][0]),ranked[1][0][1])
        if left==right:raise ROUTE.ConditionalRouteError("controller signature is ambiguous")
    mapping={motion.delta:action for action,motion in observations}
    if len(mapping)!=len(observations):raise ROUTE.ConditionalRouteError("opaque motion model is nonfunctional")
    return signature,observations,mapping

def compile_option(initial:Sequence[Sequence[int]],successors:Mapping[int,Sequence[Sequence[int]]])->RouteOption:
    signature,observations,mapping=calibrated_controller(initial,successors)
    seed=min(observations,key=lambda row:(row[0],row[1].delta))[1]
    field=ROUTE.infer_route_field(initial,before_anchor=seed.before_anchor,after_anchor=seed.after_anchor,size=seed.size,actor_colors=seed.colors)
    path=ROUTE.shortest_route(field,initial,start=seed.before_anchor);current=seed.before_anchor;actions=[]
    for node in path:
        delta=node[0]-current[0],node[1]-current[1]
        if delta not in mapping:break
        actions.append(mapping[delta]);current=node
    ast={"protocol":"autonomous-progress-synthesis-v0","type":"GoalPotential","roles":{"controlled":{"type":"ActionCorrelatedRegion"},"terminal":{"type":"ReachableMarker"}},"potential":{"type":"RemainingRouteSteps","direction":"minimize","lower_bound":0},"terminal":{"type":"ReachTerminal"}}
    return RouteOption(ast,tuple(actions),tuple(path),signature,field,tuple(sorted(mapping.items())))

def controlled_anchor(option:RouteOption,grid:Sequence[Sequence[int]])->tuple[int,int]:
    colors,mass,size=option.controlled_signature;return ROUTE.controlled_anchor(grid,colors=colors,mass=mass,size=size)

def desired_delta(option:RouteOption,grid:Sequence[Sequence[int]])->tuple[int,int]:
    current=controlled_anchor(option,grid);path=ROUTE.shortest_route(option.field,grid,start=current);return ROUTE.desired_delta(current,path)

__all__=["RouteOption","calibrated_controller","compile_option","controlled_anchor","desired_delta"]
