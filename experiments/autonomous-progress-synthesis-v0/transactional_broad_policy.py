"""Transactional preview/commit adapter for the frozen Reflector policy API."""
from __future__ import annotations
import copy
from typing import Any,Mapping

from broad_policy_bridge import BridgeError,HybridDecision


class TransactionalBroadPolicy:
    """Compute fallback on a clone and causally commit only the executed action.

    This adapter is intentionally version-pinned to the public methods and
    private commit sequence of the frozen v164 SymbolicPolicy.  Packaging must
    hash that source.  It prevents an override outcome from being attributed to
    the same-state fallback that was never executed.
    """
    def __init__(self,policy:Any)->None:
        self.policy=policy;self._preview=None;self._fallback=None;self._event=None

    def choose_action(self,observation:Any)->Any:
        if self._preview is not None:raise BridgeError("previous preview was not committed")
        rollback=copy.deepcopy(self.policy)
        committed=self.policy;fallback=committed.choose_action(observation)
        self.policy=rollback
        self._preview=committed;self._fallback=fallback;self._event=committed.cognitive_event(observation,fallback)
        return fallback

    def choose_action_committed(self,observation:Any)->Any:
        """Fast exact path when no workspace option can compete."""
        if self._preview is not None:raise BridgeError("previous preview was not committed")
        fallback=self.policy.choose_action(observation)
        self._fallback=fallback;self._event=self.policy.cognitive_event(observation,fallback)
        return fallback

    def cognitive_event(self,observation:Any,decision:Any)->Mapping[str,Any]:
        if self._event is None or decision is not self._fallback:raise BridgeError("cognitive event has no matching preview")
        return self._event

    def commit_decision(self,observation:Any,decision:HybridDecision)->None:
        if self._preview is None or self._fallback is None:raise BridgeError("no pending fallback preview")
        fallback_data=tuple(sorted((str(k),int(v)) for k,v in self._fallback.data_dict().items()))
        same=decision.action_id==self._fallback.action_id and decision.data==fallback_data
        if same:
            self.policy=self._preview
        else:
            if decision.mode not in {"probe","control"}:raise BridgeError("only an audited option may replace fallback")
            update=self.policy.observe(observation)
            if self.policy.mind.config.enable_semantic_scheme_outcomes:self.policy.explorer.clear_decision_scheme()
            actual=type(self._fallback)(decision.action_id,data=decision.data,reason=f"shared-workspace:{decision.mode}:{decision.candidate_id}")
            actual=self.policy._record(actual)
            self.policy.mind.prime_hypothesis(actual,scheme_components=())
            self.policy._append_trace(observation,actual,update)
            self.policy._previous_decision=actual;self.policy._decision_epoch+=1
        self._preview=None;self._fallback=None;self._event=None

    def __getattr__(self,name:str)->Any:
        return getattr(self.policy,name)


__all__=["TransactionalBroadPolicy"]
