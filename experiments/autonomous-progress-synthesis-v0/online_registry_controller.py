"""Online state machine for the game-blind capability registry.

The controller obtains the same one-step evidence used by the development
registry through ordinary legal interaction: execute one opaque simple action,
observe its successor, reset, and repeat.  It then compiles the registry from
those observations.  No environment object, clone, source file, or game ID is
available at this boundary.

Returning ``None`` is an explicit abstention; the caller's broad policy remains
the fallback.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any,Mapping,Sequence

import deployment_capability_registry as registry
import route_option


@dataclass(frozen=True,slots=True)
class OnlineCommand:
    action_id:int
    data:tuple[tuple[str,int],...]=()
    reason:str="capability"

    def data_dict(self)->dict[str,int]:return dict(self.data)


class OnlineCapabilityController:
    RESET=0
    COMPLEX=6
    TERMINAL=frozenset({"WIN","GAME_OVER"})

    def __init__(self,*,max_calibration_actions:int=8,max_capability_actions:int=64):
        self.max_calibration_actions=int(max_calibration_actions)
        self.max_capability_actions=int(max_capability_actions)
        self.phase="uninitialized";self.initial=None;self.simple=();self.parameterized=()
        self.successors={};self.index=0;self.awaiting_action=None;self.selected=None
        self.queue=[];self.used=0;self.route_mapping={};self.symbolic_state=None
        self._symbolic_pending=None;self._symbolic_before=None;self.abstention=None

    @staticmethod
    def _grid(value:Sequence[Sequence[int]])->tuple[tuple[int,...],...]:
        return tuple(tuple(map(int,row)) for row in value)

    def _compile(self)->None:
        rows=registry.propose(self.initial,self.successors,parameterized_actions=self.parameterized)
        self.selected=registry.select_operational(rows)
        if self.selected is None:
            self.phase="abstained";self.abstention=tuple(
                (row.capability,registry.operational_status(row)) for row in rows
            );return
        kind=self.selected.capability;self.phase="executing"
        if kind.startswith("exact:"):self.queue=list(self.selected.execution.proposal.commands)
        elif kind.startswith("gradient:"):self.queue=list(self.selected.execution[2].opaque_actions)
        elif kind=="interactive:conditional-route":self.route_mapping=dict(self.selected.execution.motion_actions)
        elif kind=="interactive:symbolic-transformation":
            self.symbolic_state=registry.symbolic.SymbolicExecutionState()
        else:
            self.phase="abstained";self.abstention=((kind,registry.operational_status(self.selected)),)

    def _finish_symbolic_observation(self,grid)->None:
        if self._symbolic_pending is None:return
        self.symbolic_state=registry.symbolic.observe(
            self.selected.execution,self.symbolic_state,self._symbolic_pending,
            self._symbolic_before,grid,transition_id=f"online:{self.used}",
        )
        self._symbolic_pending=None;self._symbolic_before=None

    def _continue_exact(self,current)->bool:
        option=self.selected.execution;previous=option.proposal
        if previous.complete:return False
        try:
            matches=[row for row in registry.synthesis.synthesize(current) if row.candidate_id==option.candidate.candidate_id]
            if not matches:return False
            candidate=min(matches,key=lambda row:(-row.attention,row.binding_id))
            proposal=registry.exact.compile_execution(
                candidate,current,motion_actions=dict(option.motion_actions),
                parameterized_actions=option.parameterized_actions,
                release_actions=option.release_actions,
                grounding_memory=previous.grounding_memory,
            )
        except Exception:return False
        self.selected=registry.CapabilityProposal(
            self.selected.capability,self.selected.goal_ast,self.selected.attention,
            self.selected.empirical_support,
            registry.ExactOption(candidate,proposal,option.motion_actions,option.parameterized_actions,option.release_actions),
            self.selected.interactive,
        )
        self.queue=list(proposal.commands)
        return bool(self.queue)

    def decide(self,grid:Sequence[Sequence[int]],available_actions:Sequence[int],*,state:str="NOT_FINISHED")->OnlineCommand|None:
        current=self._grid(grid);state=str(state).upper().rsplit(".",1)[-1]
        if state in self.TERMINAL:return None
        available=tuple(sorted(set(map(int,available_actions))))
        if self.phase=="uninitialized":
            self.initial=current
            self.simple=tuple(action for action in available if action not in {self.RESET,self.COMPLEX})[:self.max_calibration_actions]
            self.parameterized=(self.COMPLEX,) if self.COMPLEX in available else ()
            if not self.simple:
                self.phase="abstained";self.abstention=(("registry","no-simple-calibration-actions"),);return None
            self.phase="calibrating"
        if self.phase=="calibrating":
            if self.awaiting_action is not None:
                self.successors[self.awaiting_action]=current;self.awaiting_action=None
                self.phase="resetting"
                return OnlineCommand(self.RESET,(),"capability-calibration-reset")
            if self.index<len(self.simple):
                action=self.simple[self.index];self.index+=1;self.awaiting_action=action
                return OnlineCommand(action,(),"capability-one-step-calibration")
        if self.phase=="resetting":
            if current!=self.initial:
                # Reset must be empirical.  Refuse to compile situated plans
                # against a state that was not actually restored.
                self.phase="abstained";self.abstention=(("registry","reset-did-not-restore-initial-observation"),);return None
            if self.index<len(self.simple):
                self.phase="calibrating";action=self.simple[self.index];self.index+=1;self.awaiting_action=action
                return OnlineCommand(action,(),"capability-one-step-calibration")
            self._compile()
        if self.phase!="executing" or self.used>=self.max_capability_actions:return None
        kind=self.selected.capability
        if kind.startswith("exact:"):
            if not self.queue and not self._continue_exact(current):return None
            command=self.queue.pop(0);self.used+=1
            return OnlineCommand(int(command.opaque_action),tuple(command.data),f"capability:{command.role}")
        if kind.startswith("gradient:"):
            if not self.queue:return None
            action=int(self.queue.pop(0));self.used+=1;return OnlineCommand(action,(),"capability:gradient")
        if kind=="interactive:conditional-route":
            wanted=route_option.desired_delta(self.selected.execution,current)
            action=self.route_mapping.get(wanted)
            if action is None:return None
            self.used+=1;return OnlineCommand(int(action),(),"capability:conditional-route")
        if kind=="interactive:symbolic-transformation":
            self._finish_symbolic_observation(current)
            command=registry.symbolic.decide(self.selected.execution,self.symbolic_state,current)
            if command is None:return None
            self._symbolic_pending=command;self._symbolic_before=current;self.used+=1
            return OnlineCommand(int(command.opaque_action),(),f"capability:{command.role}")
        return None

    def report(self)->dict[str,Any]:
        return {
            "phase":self.phase,"calibration_count":len(self.successors),
            "selected_capability":None if self.selected is None else self.selected.capability,
            "capability_actions":self.used,
            "abstention":None if self.abstention is None else [
                [kind,getattr(status,"__dict__",status)] for kind,status in self.abstention
            ],
        }


__all__=["OnlineCapabilityController","OnlineCommand"]
