"""One generic worker over synthesized, Qwen-composable progress potentials."""
from __future__ import annotations

from dataclasses import dataclass,replace
from typing import Sequence

import compositional_dsl as dsl
import progress_field as field
import progress_synthesis as synthesis


@dataclass(frozen=True)
class TransitionAdjudication:
    transition_id:str
    candidate_id:str|None
    binding_id:str|None
    before:int|None
    after:int|None
    direct:bool
    support_delta:int


class AutonomousProgressAgent:
    def __init__(self,initial_grid:Sequence[Sequence[int]],*,frontier_size:int=12):
        candidates=list(synthesis.synthesize(initial_grid))+list(dsl.propose(initial_grid))
        candidates.sort(key=lambda row:(-row.attention,row.candidate_id,row.binding_id))
        self.state=field.make_state(candidates[:frontier_size]);self.current_grid=tuple(tuple(map(int,row)) for row in initial_grid)

    def decide(self,legal_actions:Sequence[int])->field.FieldDecision:return field.decide(self.state,legal_actions)

    def _candidate(self,decision:field.FieldDecision):
        return next((row for row in self.state.candidates if (row.candidate_id,row.binding_id)==(decision.candidate_id,decision.binding_id)),None)

    @staticmethod
    def _values(candidate,before,after)->tuple[int|None,int|None,bool]:
        if candidate.ast.get("protocol")=="compositional-progress-dsl-v0":
            try:before_value=dsl.evaluate(candidate,before)
            except synthesis.SynthesisError:return None,None,False
            before_scene=synthesis.perceive(before);after_scene=synthesis.perceive(after)
            before_map={row.region_id:row for row in before_scene.regions};after_rows=list(after_scene.regions);options={}
            for variable,region_id in candidate.binding.items():
                source=before_map.get(region_id)
                if source is None:return before_value,None,False
                matches=[row for row in after_rows if (row.width,row.height,row.normalized)==(source.width,source.height,source.normalized)]
                if not matches:return before_value,None,False
                minimum=min(abs(row.x-source.x)+abs(row.y-source.y) for row in matches)
                options[variable]=[row for row in matches if abs(row.x-source.x)+abs(row.y-source.y)==minimum]
            assignments=[{}]
            for variable in sorted(options):
                assignments=[dict(row,**{variable:item.region_id}) for row in assignments for item in options[variable] if item.region_id not in row.values()]
            values=set()
            for binding in assignments:
                try:values.add(dsl.evaluate(replace(candidate,binding=binding),after))
                except synthesis.SynthesisError:pass
            return (before_value,next(iter(values)),True) if len(values)==1 else (before_value,None,False)
        try:before_value=synthesis.evaluate(candidate,before)
        except synthesis.SynthesisError:return None,None,False
        try:after_candidates=[row for row in synthesis.synthesize(after) if row.candidate_id==candidate.candidate_id]
        except synthesis.SynthesisError:return before_value,None,False
        values={synthesis.evaluate(row,after) for row in after_candidates};values.discard(None)
        return (before_value,next(iter(values)),True) if len(values)==1 else (before_value,None,False)

    def observe(self,decision:field.FieldDecision,after_grid:Sequence[Sequence[int]],*,transition_id:str)->TransitionAdjudication:
        candidate=self._candidate(decision);after=tuple(tuple(map(int,row)) for row in after_grid)
        if candidate is None:
            self.current_grid=after;return TransitionAdjudication(transition_id,None,None,None,None,False,0)
        before_value,after_value,direct=self._values(candidate,self.current_grid,after);old_support=candidate.support
        if isinstance(before_value,int) and isinstance(after_value,int):
            self.state=field.observe(self.state,candidate_id=candidate.candidate_id,binding_id=candidate.binding_id,opaque_action=decision.opaque_action,before=before_value,after=after_value,direct=direct,transition_id=transition_id)
        else:
            self.state=field.record_attempt(self.state,candidate_id=candidate.candidate_id,binding_id=candidate.binding_id,opaque_action=decision.opaque_action)
        self.current_grid=after
        updated=next(row for row in self.state.candidates if row.candidate_id==candidate.candidate_id and row.binding_id==candidate.binding_id)
        return TransitionAdjudication(transition_id,candidate.candidate_id,candidate.binding_id,before_value,after_value,direct,updated.support-old_support)

    def qwen_turn(self,*,frame_id:str,recent_transition_ids:Sequence[str]=())->dict:
        scene=synthesis.perceive(self.current_grid)
        return {"protocol":"shared-autonomous-progress-turn-v0","current_frame_id":frame_id,"recent_transition_ids":list(recent_transition_ids),"workspace":field.workspace_document(self.state),"composition_contract":dsl.qwen_contract(scene)}


__all__=["AutonomousProgressAgent","TransitionAdjudication"]
