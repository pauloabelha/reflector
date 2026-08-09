import reset_replay_explorer as M


class Toy:
    def __init__(self):self.state="root";self.steps=0
    def reset(self):self.state="root";return self.state
    def step(self,a):
        self.steps+=1
        self.state={("root",1):"dead",("root",2):"middle",("middle",1):"win",("middle",2):"middle"}.get((self.state,a),"dead")
        return self.state
    def key(self,o):return o
    def legal_actions(self,o):return (1,2)
    def completed(self,o):return o=="win"
    def terminal(self,o):return o in {"win","dead"}


def test_finds_short_opaque_solution_and_charges_replay_actions():
    world=Toy();result=M.search(world,action_budget=20,max_depth=4)
    assert result.solved and result.solution==(2,1)
    assert result.environment_actions==world.steps==4
    assert result.reset_count==4
    assert result.discovered_states==3


def test_budget_stops_before_unfunded_replay_branch():
    result=M.search(Toy(),action_budget=2,max_depth=4)
    assert not result.solved and result.stop_reason=="action-budget"
    assert result.environment_actions==2


def test_depth_bound_is_a_valid_negative_not_completion():
    result=M.search(Toy(),action_budget=20,max_depth=1)
    assert not result.solved and result.stop_reason=="frontier-exhausted"


class HiddenMode:
    def __init__(self):self.count=0
    def reset(self):self.count=0;return self.count
    def step(self,a):
        if a==1:self.count+=1
        return self.count
    def key(self,o):return "same-pixels" if o<2 else "win"
    def legal_actions(self,o):return (1,)
    def completed(self,o):return o>=2
    def terminal(self,o):return o>=2


def test_causal_suffix_preserves_latent_state_hidden_by_identical_pixels():
    assert not M.search(HiddenMode(),action_budget=10,max_depth=3,history_order=0).solved
    result=M.search(HiddenMode(),action_budget=10,max_depth=3,history_order=2)
    assert result.solved and result.solution==(1,1)


class LongHiddenRun(HiddenMode):
    def completed(self,o):return o>=6
    def terminal(self,o):return o>=6
    def key(self,o):return "same-pixels" if o<6 else "win"


def test_run_length_signature_preserves_long_visually_silent_progress():
    assert not M.search(LongHiddenRun(),action_budget=30,max_depth=8,history_order=2,history_mode="action_suffix").solved
    result=M.search(LongHiddenRun(),action_budget=30,max_depth=8,history_order=2,history_mode="run_length_suffix")
    assert result.solved and result.solution==(1,)*6
