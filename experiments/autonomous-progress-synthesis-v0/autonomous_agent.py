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
    observed_candidate_count:int=0


class AutonomousProgressAgent:
    def __init__(self,initial_grid:Sequence[Sequence[int]],*,frontier_size:int=12):
        try:candidates=list(synthesis.synthesize(initial_grid))
        except synthesis.SynthesisError:candidates=[]
        try:candidates.extend(dsl.propose(initial_grid))
        except synthesis.SynthesisError:pass
        candidates.sort(key=lambda row:(-row.attention,row.candidate_id,row.binding_id))
        self.state=field.make_state(candidates[:frontier_size]);self.current_grid=tuple(tuple(map(int,row)) for row in initial_grid)

    def decide(self,legal_actions:Sequence[int])->field.FieldDecision:return field.decide(self.state,legal_actions)

    def _candidate(self,decision:field.FieldDecision):
        return next((row for row in self.state.candidates if (row.candidate_id,row.binding_id)==(decision.candidate_id,decision.binding_id)),None)

    @staticmethod
    def _tracked_values(candidate,before,after)->tuple[int|None,int|None,bool,dict|None]:
        if candidate.ast.get("protocol")=="compositional-progress-dsl-v0":
            try:before_value=dsl.evaluate(candidate,before)
            except synthesis.SynthesisError:return None,None,False,None
            before_scene=synthesis.perceive(before);after_scene=synthesis.perceive(after)
            before_map={row.region_id:row for row in before_scene.regions};after_rows=list(after_scene.regions);options={}
            for variable,region_id in candidate.binding.items():
                source=before_map.get(region_id)
                if source is None:return before_value,None,False,None
                matches=[row for row in after_rows if (row.width,row.height,row.normalized)==(source.width,source.height,source.normalized)]
                if not matches:return before_value,None,False,None
                minimum=min(abs(row.x-source.x)+abs(row.y-source.y) for row in matches)
                options[variable]=[row for row in matches if abs(row.x-source.x)+abs(row.y-source.y)==minimum]
            assignments=[{}]
            for variable in sorted(options):
                assignments=[dict(row,**{variable:item.region_id}) for row in assignments for item in options[variable] if item.region_id not in row.values()]
            values=[]
            for binding in assignments:
                try:values.append((dsl.evaluate(replace(candidate,binding=binding),after),binding))
                except synthesis.SynthesisError:pass
            return (before_value,values[0][0],True,values[0][1]) if len(values)==1 else (before_value,None,False,None)
        try:before_value=synthesis.evaluate(candidate,before)
        except synthesis.SynthesisError:return None,None,False,None
        try:after_candidates=[row for row in synthesis.synthesize(after) if row.candidate_id==candidate.candidate_id]
        except synthesis.SynthesisError:return before_value,None,False,None
        rows=[]
        for row in after_candidates:
            value=synthesis.evaluate(row,after)
            if value is not None:rows.append((value,dict(row.binding)))
        return (before_value,rows[0][0],True,rows[0][1]) if len(rows)==1 else (before_value,None,False,None)

    @staticmethod
    def _values(candidate,before,after)->tuple[int|None,int|None,bool]:
        """Compatibility projection for callers that do not need lineage."""
        left,right,direct,_binding=AutonomousProgressAgent._tracked_values(candidate,before,after)
        return left,right,direct

    def observe(self,decision:field.FieldDecision,after_grid:Sequence[Sequence[int]],*,transition_id:str)->TransitionAdjudication:
        selected=self._candidate(decision);after=tuple(tuple(map(int,row)) for row in after_grid)
        observations={};rebindings={};selected_values=(None,None,False);old_support=None if selected is None else selected.support
        for candidate in self.state.candidates:
            before_value,after_value,direct,binding=self._tracked_values(candidate,self.current_grid,after)
            key=candidate.candidate_id,candidate.binding_id
            observations[key]=(before_value,after_value,direct) if isinstance(before_value,int) and isinstance(after_value,int) else None
            if direct and binding is not None:rebindings[key]=binding
            if selected is candidate:selected_values=before_value,after_value,direct
        self.state=field.observe_transition(
            self.state,opaque_action=decision.opaque_action,
            transition_id=transition_id,observations=observations,
        )
        self.state=replace(self.state,candidates=tuple(
            replace(candidate,binding=rebindings.get((candidate.candidate_id,candidate.binding_id),candidate.binding))
            for candidate in self.state.candidates
        ))
        self.current_grid=after
        if selected is None:return TransitionAdjudication(transition_id,None,None,None,None,False,0,sum(value is not None for value in observations.values()))
        updated=next(row for row in self.state.candidates if row.candidate_id==selected.candidate_id and row.binding_id==selected.binding_id)
        return TransitionAdjudication(transition_id,selected.candidate_id,selected.binding_id,*selected_values,updated.support-old_support,sum(value is not None for value in observations.values()))

    def qwen_turn(self,*,frame_id:str,recent_transition_ids:Sequence[str]=())->dict:
        scene=synthesis.perceive(self.current_grid)
        return {"protocol":"shared-autonomous-progress-turn-v0","current_frame_id":frame_id,"recent_transition_ids":list(recent_transition_ids),"workspace":field.workspace_document(self.state),"composition_contract":dsl.qwen_contract(scene)}


__all__=["AutonomousProgressAgent","TransitionAdjudication"]
