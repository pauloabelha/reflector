import causal_sweep_explorer as M


class TurnWorld:
    def __init__(self): self.x=0;self.y=0;self.steps=0
    def reset(self): self.x=0;self.y=0;return (self.x,self.y)
    def step(self,action):
        self.steps+=1
        if action==17:self.x=min(5,self.x+1)
        elif action==93 and self.x==5:self.y=min(4,self.y+1)
        return self.x,self.y
    def key(self,o):return repr(o)
    def legal_actions(self,o):return (17,93)
    def completed(self,o):return o==(5,4)
    def terminal(self,o):return self.completed(o)


def test_coherent_sweeps_find_long_run_then_turn_without_action_semantics():
    world=TurnWorld();result=M.search(world,action_budget=300,max_run=8,max_segments=3)
    assert result.solved
    assert result.solution==(17,)*5+(93,)*4
    assert result.environment_actions==world.steps
    assert result.maximum_segments<=2


class HiddenRun:
    def __init__(self):self.count=0
    def reset(self):self.count=0;return self.count
    def step(self,action):
        if action==41:self.count+=1
        return self.count
    def key(self,o):return "same" if o<6 else "done"
    def legal_actions(self,o):return (41,)
    def completed(self,o):return o>=6
    def terminal(self,o):return self.completed(o)


def test_one_sweep_preserves_visually_silent_causal_progress():
    result=M.search(HiddenRun(),action_budget=20,max_run=8,history_order=2)
    assert result.solved and result.solution==(41,)*6


class DeadBranch(TurnWorld):
    def step(self,action):
        if action==99:self.x=-1
        else:return super().step(action)
        self.steps+=1;return self.x,self.y
    def legal_actions(self,o):return (17,93,99)
    def terminal(self,o):return self.x<0 or self.completed(o)


def test_terminal_failure_branch_does_not_block_other_sweeps():
    result=M.search(DeadBranch(),action_budget=400,max_run=8,max_segments=3)
    assert result.solved and 99 not in result.solution


def test_invalid_bounds_fail_before_touching_world():
    try:M.search(TurnWorld(),max_run=0)
    except M.SweepError as error:assert "bound" in str(error)
    else:raise AssertionError("expected SweepError")


class SurpriseWorld:
    """Many shallow states, but one structural event opens a short solution."""
    def __init__(self):self.path=[]
    def reset(self):self.path=[];return tuple(self.path)
    def step(self,action):self.path.append(action);return tuple(self.path)
    def key(self,o):return repr(o)
    def legal_actions(self,o):return tuple(range(8))
    def completed(self,o):return o==((7,)*3+(6,))
    def terminal(self,o):return self.completed(o)


def test_priority_expands_structural_event_despite_large_discovered_queue():
    world=SurpriseWorld()
    def priority(_before,_after,path,_segments):return (0 if path==(7,)*3 else 1,)
    result=M.search(world,action_budget=500,max_actions=5,max_segments=2,max_run=4,max_states=20,priority=priority)
    assert result.solved and result.solution==(7,7,7,6)
