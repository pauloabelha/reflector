"""Evidence-driven attentional economy over grounded progress potentials.

This module does not know games or action meanings.  It turns a bounded set of
observable potentials into an online experiment: probe unknown action/potential
pairs, remember direct effects, and exploit only repeatedly improving effects.
"""
from __future__ import annotations

from dataclasses import dataclass,replace
from statistics import median
from typing import Iterable,Mapping,Sequence

from progress_synthesis import GoalCandidate,PotentialObservation,adjudicate,evaluate,stable_hash


class ProgressFieldError(ValueError):pass


@dataclass(frozen=True)
class EffectRecord:
    candidate_id:str
    binding_id:str
    opaque_action:int
    before:int
    after:int
    direct:bool
    transition_id:str

    @property
    def improvement(self)->int:return self.before-self.after


@dataclass(frozen=True)
class FieldState:
    candidates:tuple[GoalCandidate,...]
    evidence:tuple[EffectRecord,...]=()
    action_uses:tuple[tuple[int,int],...]=()
    attempts:tuple[tuple[str,str,int,int],...]=()

    def uses(self)->dict[int,int]:return dict(self.action_uses)


@dataclass(frozen=True)
class FieldDecision:
    mode:str
    opaque_action:int
    candidate_id:str|None
    binding_id:str|None
    predicted_improvement:int|None
    basis_evidence_ids:tuple[str,...]
    reason:str


def make_state(candidates:Iterable[GoalCandidate])->FieldState:
    unique={(row.candidate_id,row.binding_id):row for row in candidates}
    ordered=tuple(sorted(unique.values(),key=lambda row:(-row.attention,row.candidate_id,row.binding_id)))
    return FieldState(ordered)


def observe(
    state:FieldState,
    *,
    candidate_id:str,
    binding_id:str,
    opaque_action:int,
    before:int,
    after:int,
    direct:bool,
    transition_id:str,
)->FieldState:
    if not transition_id:raise ProgressFieldError("evidence requires a transition ID")
    matches=[row for row in state.candidates if (row.candidate_id,row.binding_id)==(candidate_id,binding_id)]
    if len(matches)!=1:raise ProgressFieldError("evidence must address exactly one live potential")
    record=EffectRecord(candidate_id,binding_id,int(opaque_action),int(before),int(after),bool(direct),transition_id)
    if any(row.transition_id==transition_id and row.candidate_id==candidate_id and row.binding_id==binding_id for row in state.evidence):
        raise ProgressFieldError("duplicate transition evidence")
    updated=[]
    for candidate in state.candidates:
        if candidate is matches[0]:
            candidate=adjudicate(candidate,PotentialObservation(candidate_id,binding_id,before,after,direct,transition_id))
        updated.append(candidate)
    advanced=record_attempt(replace(state,candidates=tuple(updated),evidence=state.evidence+(record,)),candidate_id=candidate_id,binding_id=binding_id,opaque_action=opaque_action)
    return advanced


def record_attempt(state:FieldState,*,candidate_id:str,binding_id:str,opaque_action:int)->FieldState:
    if not any((row.candidate_id,row.binding_id)==(candidate_id,binding_id) for row in state.candidates):raise ProgressFieldError("attempt targets no live potential")
    key=(candidate_id,binding_id,int(opaque_action));counts={(a,b,c):n for a,b,c,n in state.attempts};counts[key]=counts.get(key,0)+1
    uses=state.uses();uses[int(opaque_action)]=uses.get(int(opaque_action),0)+1
    attempts=tuple(sorted((a,b,c,n) for (a,b,c),n in counts.items()))
    return replace(state,action_uses=tuple(sorted(uses.items())),attempts=attempts)


def observe_transition(
    state:FieldState,
    *,
    opaque_action:int,
    transition_id:str,
    observations:Mapping[tuple[str,str],tuple[int,int,bool]|None],
)->FieldState:
    """Adjudicate one transition against every addressed live potential.

    A world transition is shared evidence, not private feedback for whichever
    hypothesis nominated the action.  Candidate-specific attempts are updated
    for the whole rendered field while the physical intervention use is
    counted exactly once.
    """
    if not transition_id:raise ProgressFieldError("evidence requires a transition ID")
    live={(row.candidate_id,row.binding_id):row for row in state.candidates}
    if not set(observations)<=set(live):raise ProgressFieldError("batch evidence targets a non-live potential")
    if any(row.transition_id==transition_id for row in state.evidence):raise ProgressFieldError("duplicate transition evidence")
    updated=[];evidence=list(state.evidence);attempts={(a,b,c):n for a,b,c,n in state.attempts}
    for key,candidate in live.items():
        if key not in observations:
            updated.append(candidate);continue
        attempt=key+(int(opaque_action),);attempts[attempt]=attempts.get(attempt,0)+1
        values=observations[key]
        if values is not None:
            before,after,direct=values
            record=EffectRecord(key[0],key[1],int(opaque_action),int(before),int(after),bool(direct),transition_id)
            evidence.append(record)
            candidate=adjudicate(candidate,PotentialObservation(key[0],key[1],before,after,direct,transition_id))
        updated.append(candidate)
    uses=state.uses();uses[int(opaque_action)]=uses.get(int(opaque_action),0)+1
    return FieldState(
        tuple(updated),tuple(evidence),tuple(sorted(uses.items())),
        tuple(sorted((a,b,c,n) for (a,b,c),n in attempts.items())),
    )


def _model(state:FieldState,candidate:GoalCandidate,action:int)->tuple[int|None,tuple[str,...]]:
    rows=[row for row in state.evidence if row.direct and row.candidate_id==candidate.candidate_id and row.binding_id==candidate.binding_id and row.opaque_action==action]
    if len(rows)<2:return None,tuple(row.transition_id for row in rows)
    values=[row.improvement for row in rows]
    direction=1 if median(values)>0 else -1 if median(values)<0 else 0
    if any((value>0)-(value<0)!=direction for value in values):return None,tuple(row.transition_id for row in rows)
    return int(median(values)),tuple(row.transition_id for row in rows)


def decide(state:FieldState,legal_actions:Sequence[int])->FieldDecision:
    legal=tuple(sorted(set(map(int,legal_actions))))
    if not legal:raise ProgressFieldError("no legal opaque action")
    # Evidence-backed progress dominates attention.  Structural salience can
    # decide what to test, but never authorizes control by itself.
    control=[]
    for candidate in state.candidates:
        for action in legal:
            expected,basis=_model(state,candidate,action)
            if expected is not None and expected>0:
                control.append((-expected,-candidate.support,-candidate.attention,action,candidate.candidate_id,candidate.binding_id,candidate,basis))
    if control:
        _a,_s,_t,action,_cid,_bid,candidate,basis=min(control)
        return FieldDecision("control",action,candidate.candidate_id,candidate.binding_id,-_a,basis,"confirmed-progress-effect")

    attempts={(a,b,c):n for a,b,c,n in state.attempts}
    probes=[]
    for candidate in state.candidates:
        for action in legal:
            count=attempts.get((candidate.candidate_id,candidate.binding_id,action),0)
            if count<2:
                probes.append((count,-candidate.attention,state.uses().get(action,0),candidate.candidate_id,candidate.binding_id,action,candidate))
    if probes:
        _n,_attention,_uses,_cid,_bid,action,candidate=min(probes)
        return FieldDecision("probe",action,candidate.candidate_id,candidate.binding_id,None,(),"reduce-action-potential-uncertainty")
    action=min(legal,key=lambda item:(state.uses().get(item,0),item))
    return FieldDecision("fallback",action,None,None,None,(),"no-supported-progress-effect")


def workspace_document(state:FieldState)->dict:
    """Action-blind shared view; opaque actions are stable local references."""
    rows=[]
    for candidate in state.candidates:
        effects=[]
        for action in sorted({key for key,_count in state.action_uses}):
            expected,basis=_model(state,candidate,action)
            effects.append({"intervention_ref":"iv:"+stable_hash({"opaque":action})[:12],"predicted_improvement":expected,"evidence_ids":list(basis)})
        rows.append({"candidate_id":candidate.candidate_id,"binding_id":candidate.binding_id,"ast":candidate.ast,"attention":candidate.attention,"empirical_support":candidate.support,"current_value":None,"effects":effects})
    return {"protocol":"shared-progress-field-v0","authority":"only-direct-environment-evidence-changes-support","potentials":rows,"evidence_count":len(state.evidence)}


__all__=["EffectRecord","FieldDecision","FieldState","ProgressFieldError","decide","make_state","observe","observe_transition","record_attempt","workspace_document"]
