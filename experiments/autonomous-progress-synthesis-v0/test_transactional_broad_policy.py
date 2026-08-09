from dataclasses import dataclass
from types import SimpleNamespace
from broad_policy_bridge import HybridDecision
from transactional_broad_policy import TransactionalBroadPolicy


@dataclass(frozen=True)
class Decision:
    action_id:int
    data:tuple=()
    reason:str="fallback"
    def data_dict(self):return dict(self.data)


class Policy:
    def __init__(self):
        self.observed=[];self._previous_decision=None;self._decision_epoch=0;self.action_counts={}
        self.mind=SimpleNamespace(config=SimpleNamespace(enable_semantic_scheme_outcomes=False),prime_hypothesis=lambda *a,**k:None)
        self.explorer=SimpleNamespace(clear_decision_scheme=lambda:None)
        self.trace=[]
    def choose_action(self,observation):
        update=self.observe(observation);decision=self._record(Decision(1));self._append_trace(observation,decision,update);self._previous_decision=decision;self._decision_epoch+=1;return decision
    def observe(self,observation):self.observed.append((observation,self._previous_decision));return "update"
    def cognitive_event(self,observation,decision):return {"decision":decision.action_id,"epoch":self._decision_epoch}
    def _record(self,decision):self.action_counts[decision.action_id]=self.action_counts.get(decision.action_id,0)+1;return decision
    def _append_trace(self,observation,decision,update):self.trace.append((decision,update))


def hybrid(action,mode="fallback"):
    return HybridDecision(action,(),mode,1,(),None if mode=="fallback" else "option:x","test")


def test_fallback_commits_preview_exactly_once():
    tx=TransactionalBroadPolicy(Policy());fallback=tx.choose_action("s0");assert fallback.action_id==1
    tx.commit_decision("s0",hybrid(1));assert tx.policy._decision_epoch==1 and len(tx.policy.observed)==1 and tx.policy._previous_decision.action_id==1


def test_override_is_the_only_decision_committed_to_causal_state():
    tx=TransactionalBroadPolicy(Policy());tx.choose_action("s0");tx.commit_decision("s0",hybrid(4,"probe"))
    assert tx.policy._decision_epoch==1
    assert tx.policy._previous_decision.action_id==4
    assert tx.policy.action_counts=={4:1}
    assert [row[0].action_id for row in tx.policy.trace]==[4]


def test_next_observation_is_attributed_to_actual_override():
    tx=TransactionalBroadPolicy(Policy());tx.choose_action("s0");tx.commit_decision("s0",hybrid(4,"control"));tx.choose_action("s1")
    assert tx._preview.observed[-1][1].action_id==4


def test_committed_fast_path_uses_no_clone_or_pending_transaction():
    tx=TransactionalBroadPolicy(Policy());decision=tx.choose_action_committed("s0")
    assert decision.action_id==1 and tx._preview is None
    assert tx.policy._decision_epoch==1 and tx.policy._previous_decision.action_id==1
