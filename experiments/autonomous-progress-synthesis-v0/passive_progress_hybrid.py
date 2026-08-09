"""Conservative broad-policy composition with a shared progress field.

The broad policy remains authoritative while its ordinary transitions
simultaneously calibrate every measurable workspace potential.  Only a
repeatedly environment-supported improving effect may override the next broad
decision.  No exploratory divergence is introduced by this layer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Protocol, Sequence

import autonomous_agent as autonomous


class HybridError(ValueError):
    pass


class DecisionLike(Protocol):
    action_id: int
    def data_dict(self) -> Mapping[str,int]: ...


class BroadPolicy(Protocol):
    def choose_action(self, observation: Any) -> DecisionLike: ...


@dataclass(frozen=True, slots=True)
class HybridDecision:
    action_id: int
    data: tuple[tuple[str,int],...]
    fallback_action_id: int
    fallback_data: tuple[tuple[str,int],...]
    mode: str
    candidate_id: str|None
    binding_id: str|None
    predicted_improvement: int|None


class PassiveProgressHybrid:
    def __init__(self,broad:BroadPolicy,agent:autonomous.AutonomousProgressAgent,*,minimum_support:int=20):
        if minimum_support<1:raise HybridError("minimum support must be positive")
        self.broad=broad;self.agent=agent;self.minimum_support=int(minimum_support)

    @staticmethod
    def _data(decision:DecisionLike)->tuple[tuple[str,int],...]:
        raw=decision.data_dict() if hasattr(decision,"data_dict") else getattr(decision,"data",())
        return tuple(sorted((str(k),int(v)) for k,v in (dict(raw) if not isinstance(raw,dict) else raw).items()))

    def decide(self,observation:Any,legal_actions:Sequence[int])->HybridDecision:
        fallback=self.broad.choose_action(observation);fallback_data=self._data(fallback)
        field=self.agent.decide(legal_actions)
        candidate=next((row for row in self.agent.state.candidates if (row.candidate_id,row.binding_id)==(field.candidate_id,field.binding_id)),None)
        eligible=field.mode=="control" and candidate is not None and candidate.support>=self.minimum_support and field.opaque_action in set(map(int,legal_actions))
        if eligible:
            return HybridDecision(field.opaque_action,(),int(fallback.action_id),fallback_data,"supported-progress-control",field.candidate_id,field.binding_id,field.predicted_improvement)
        return HybridDecision(int(fallback.action_id),fallback_data,int(fallback.action_id),fallback_data,"broad-fallback",None,None,None)

    def observe(self,decision:HybridDecision,after_grid,*,transition_id:str):
        # The selected candidate is attribution only.  AutonomousProgressAgent
        # multiplexes the physical transition over every live potential.
        field_decision=__import__('progress_field').FieldDecision(
            "control" if decision.mode=="supported-progress-control" else "fallback",
            decision.action_id,decision.candidate_id,decision.binding_id,
            decision.predicted_improvement,(),decision.mode,
        )
        return self.agent.observe(field_decision,after_grid,transition_id=transition_id)


__all__=["HybridDecision","HybridError","PassiveProgressHybrid"]
