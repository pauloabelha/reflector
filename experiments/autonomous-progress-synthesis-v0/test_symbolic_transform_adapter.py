import pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))

import pytest
import capability_registry as registry
import progress_synthesis as synthesis
import symbolic_transform_adapter as adapter


A=((0,1,0,0,0),(1,1,0,0,0),(0,1,0,0,0),(0,1,0,0,0),(1,1,1,0,0))
B=((1,1,0,0,0),(1,0,1,0,0),(1,1,0,0,0),(1,0,1,0,0),(1,0,1,0,0))


def stamp(grid,x,y,pattern,background=2):
    for yy,row in enumerate(pattern):
        for xx,cell in enumerate(row):grid[y+yy][x+xx]=9 if cell else background


def fixture():
    grid=[[2]*40 for _ in range(32)];panels=[]
    for index,(left,right) in enumerate(((A,B),(B,A))):
        x,y=2,2+index*7;panels.append({"origin":[x,y],"size":[17,7]})
        stamp(grid,x+1,y+1,left);stamp(grid,x+11,y+1,right)
    stamp(grid,3,17,A);stamp(grid,10,17,B)
    stamp(grid,3,24,A);stamp(grid,10,24,B)
    grid[30][3]=7
    edit=[row[:] for row in grid];stamp(edit,3,24,B)
    advance=[row[:] for row in grid];advance[30][3]=2;advance[30][10]=7
    noop=[row[:] for row in grid]
    return grid,panels,{73:edit,11:advance,5:noop}


def test_registry_adapts_consumed_symbolic_kernel_without_action_semantics():
    initial,panels,successors=fixture()
    rows=registry.propose(initial,successors,symbolic_panels=panels)
    symbolic=[row for row in rows if row.capability=="interactive:symbolic-transformation"]
    assert len(symbolic)==1
    proposal=symbolic[0];option=proposal.execution
    assert proposal.empirical_support==0 and proposal.interactive
    assert (option.edit_action,option.advance_action)==(73,11)
    text=str(proposal.goal_ast).lower()
    assert "action" not in text and "game" not in text and "color" not in text


def test_closed_loop_requires_direct_effects_and_only_evidence_raises_support():
    initial,panels,successors=fixture();option=adapter.propose(initial,successors,panels=panels)[0]
    state=adapter.SymbolicExecutionState();command=adapter.decide(option,state,initial)
    assert command.opaque_action==73 and state.empirical_support==0
    edited=successors[73];state=adapter.observe(option,state,command,initial,edited,transition_id="t:edit-0")
    assert state.empirical_support==10
    command=adapter.decide(option,state,edited);assert command.opaque_action==11
    advanced=[row[:] for row in edited];advanced[30][3]=2;advanced[30][10]=7
    state=adapter.observe(option,state,command,edited,advanced,transition_id="t:focus-1")
    command=adapter.decide(option,state,advanced);assert command.opaque_action==73
    final=[row[:] for row in advanced];stamp(final,10,24,A)
    state=adapter.observe(option,state,command,advanced,final,transition_id="t:edit-1")
    assert adapter.evaluate(option,final)==0 and adapter.decide(option,state,final) is None
    assert state.empirical_support==20 and state.evidence_ids==("t:edit-0","t:focus-1","t:edit-1")


def test_ambiguous_or_unobserved_mechanisms_abstain_and_cycles_are_bounded():
    initial,panels,successors=fixture()
    ambiguous=dict(successors);ambiguous[74]=successors[73]
    assert adapter.propose(initial,ambiguous,panels=panels)==()
    assert adapter.propose(initial,{5:initial},panels=panels)==()
    option=adapter.propose(initial,successors,panels=panels)[0]
    state=adapter.SymbolicExecutionState(cycles_at_slot=option.max_cycles_per_slot)
    with pytest.raises(synthesis.SynthesisError,match="cycle"):
        adapter.decide(option,state,initial)


def test_workspace_separates_situated_calibration_from_transferable_ast():
    initial,panels,successors=fixture();option=adapter.propose(initial,successors,panels=panels)[0]
    document=adapter.workspace_document(option,adapter.SymbolicExecutionState(),initial)
    assert document["empirical_support"]==0 and len(document["calibration_evidence_ids"])==2
    assert "desired" not in str(document["ast"]).lower()


def test_generic_figure_adapter_emits_only_bounded_geometry():
    class Figure:
        anchor=(4,6);normalized_cells=((0,0),(2,1))
    assert adapter.panel_rows([Figure()])==({"origin":[4,6],"size":[3,2]},)
