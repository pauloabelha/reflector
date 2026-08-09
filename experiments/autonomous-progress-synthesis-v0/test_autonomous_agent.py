import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import autonomous_agent as aa


def scene(offset=0):
    g=[[0]*14 for _ in range(10)]
    for y in range(2,5):
        for x in range(1+offset,4+offset):g[y][x]=1
    for y in range(2,5):
        for x in range(9,12):g[y][x]=1
    return g


def test_agent_probes_then_can_learn_from_direct_correspondence():
    agent=aa.AutonomousProgressAgent(scene(),frontier_size=4)
    first=agent.decide([1]);assert first.mode=="probe"
    result=agent.observe(first,scene(1),transition_id="t1")
    assert result.candidate_id is not None
    assert result.direct in {True,False}
    assert agent.qwen_turn(frame_id="f1",recent_transition_ids=["t1"])["current_frame_id"]=="f1"


def test_qwen_turn_exposes_one_workspace_not_a_private_qwen_state():
    agent=aa.AutonomousProgressAgent(scene(),frontier_size=3);turn=agent.qwen_turn(frame_id="frame:0")
    text=str(turn)
    assert "workspace" in turn and "composition_contract" in turn
    assert "qwen_state" not in text and "action_id" not in text
