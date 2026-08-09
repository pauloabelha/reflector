"""Bounded game-blind exploration over deterministic reset/replay worlds."""
from __future__ import annotations

from dataclasses import dataclass
import heapq
from typing import Any,Callable,Protocol,Sequence


class ExplorationError(RuntimeError):pass


class World(Protocol):
    def reset(self)->Any:...
    def step(self,opaque_action:int)->Any:...
    def key(self,observation:Any)->str:...
    def legal_actions(self,observation:Any)->Sequence[int]:...
    def completed(self,observation:Any)->bool:...
    def terminal(self,observation:Any)->bool:...


@dataclass(frozen=True,slots=True)
class SearchEdge:
    source_key:str
    opaque_action:int
    target_key:str
    replay_prefix_length:int
    completed:bool
    terminal:bool


@dataclass(frozen=True,slots=True)
class SearchResult:
    solved:bool
    solution:tuple[int,...]
    environment_actions:int
    reset_count:int
    discovered_states:int
    maximum_depth_reached:int
    edges:tuple[SearchEdge,...]
    stop_reason:str


def search(world:World,*,action_budget:int=400,max_depth:int=12,max_states:int=256,history_order:int=0,priority:Callable[[Any,tuple[int,...],str,str],tuple]|None=None)->SearchResult:
    """Breadth-first search with every replay action honestly charged.

    Only opaque action identities and observation equality are used.  A path is
    accepted solely when the environment reports completion.  Reset is an
    explicit epistemic operation and is counted separately.
    """
    if action_budget<1 or max_depth<1 or max_states<2 or history_order<0:raise ExplorationError("invalid search bound")
    root=world.reset();resets=1;root_key=world.key(root)
    if world.completed(root):return SearchResult(True,(),0,resets,1,0,(),"root-complete")
    def epistemic_key(observation,path):
        suffix=path[-history_order:] if history_order else ()
        return world.key(observation),suffix
    serial=0;queue=[((0,),serial,())];keys={epistemic_key(root,()):()};edges=[];spent=0;deepest=0
    while queue and spent<action_budget and len(keys)<max_states:
        _rank,_serial,prefix=heapq.heappop(queue)
        if len(prefix)>=max_depth:continue
        # Each sibling is an independent falsifiable intervention from the
        # exact same state; never rely on an implicit clone.
        probe_actions=None
        for action_index in range(10_000):
            if probe_actions is not None and action_index>=len(probe_actions):break
            if spent+len(prefix)+1>action_budget:break
            obs=world.reset();resets+=1
            valid=True
            for replay_action in prefix:
                obs=world.step(replay_action);spent+=1
                if world.terminal(obs) and not world.completed(obs):valid=False;break
            if not valid:break
            legal=tuple(sorted(set(map(int,world.legal_actions(obs)))))
            if probe_actions is None:probe_actions=legal
            action=probe_actions[action_index]
            if action not in legal:raise ExplorationError("legal actions changed under exact replay")
            source=world.key(obs);after=world.step(action);spent+=1;target=world.key(after)
            done=world.completed(after);dead=world.terminal(after)
            path=prefix+(action,);deepest=max(deepest,len(path))
            edges.append(SearchEdge(source,action,target,len(prefix),done,dead))
            target_epistemic=epistemic_key(after,path)
            if done:return SearchResult(True,path,spent,resets,len(keys)+int(target_epistemic not in keys),deepest,tuple(edges),"environment-completion")
            if not dead and target_epistemic not in keys and len(keys)<max_states:
                keys[target_epistemic]=path;serial+=1
                rank=priority(after,path,source,target) if priority is not None else (len(path),)
                if not isinstance(rank,tuple):raise ExplorationError("priority must return a tuple")
                heapq.heappush(queue,(rank,serial,path))
    reason="action-budget" if spent>=action_budget else "state-budget" if len(keys)>=max_states else "frontier-exhausted"
    return SearchResult(False,(),spent,resets,len(keys),deepest,tuple(edges),reason)


__all__=["ExplorationError","SearchEdge","SearchResult","World","search"]
