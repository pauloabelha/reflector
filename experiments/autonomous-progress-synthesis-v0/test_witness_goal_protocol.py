import progress_synthesis as PS
import witness_goal_protocol as M


def fixture():
    grid=(
        (0,0,0,0,0,0,0,0,0),
        (0,1,1,0,0,2,2,2,0),
        (0,1,1,0,0,2,2,2,0),
        (0,3,3,0,0,0,0,0,0),
        (0,3,3,0,0,0,0,0,0),
    )
    scene=PS.perceive(grid,coarsen=False);target=next(item for item in scene.regions if item.x==5)
    workspace={"entities":[
        {"id":"p000","origin":[1,1],"size":[2,4],"area":8},
        {"id":"e000","origin":[target.x,target.y],"size":[target.width,target.height],"area":target.area},
    ],"control_opportunity":{"controlled_candidates":["p000"]},"equivalence_classes":[],"capacity_hypotheses":[]}
    return grid,workspace


def test_every_witness_is_pixel_grounded_nonterminal_and_support_zero():
    grid,workspace=fixture();rows=M.enumerate_witnesses(workspace,grid)
    assert rows
    assert all(row.current_value>0 and row.correspondence_count>=1 and row.empirical_support==0 for row in rows)
    assert all(row.compiled.empirical_support==0 for row in rows)


def test_selection_materializes_exact_witness_semantics_not_model_authored_cross_product():
    grid,workspace=fixture();rows=M.enumerate_witnesses(workspace,grid);chosen=rows[0]
    out=M.compile_selection({"protocol":M.PROTOCOL,"selection":{"witness_id":chosen.witness_id,"rationale":"test this exact observable"}},rows)
    assert out["accepted"] and out["goal"]["family"]==chosen.goal["family"]
    assert out["goal"]["potential"]==chosen.goal["potential"] and out["empirical_support"]==0


def test_retired_witness_is_absent_from_grammar_and_rejected_by_compiler():
    grid,workspace=fixture();rows=M.enumerate_witnesses(workspace,grid);retired=rows[0].witness_id
    schema=M.response_schema(rows,retired_ids=[retired]);enum=schema["properties"]["selection"]["oneOf"][1]["properties"]["witness_id"]["enum"]
    assert retired not in enum
    out=M.compile_selection({"protocol":M.PROTOCOL,"selection":{"witness_id":retired,"rationale":"repeat"}},rows,retired_ids=[retired])
    assert not out["accepted"] and out["reason"]=="witness-not-live"


def test_no_unique_controller_means_no_executable_witnesses():
    grid,workspace=fixture();workspace["control_opportunity"]={"controlled_candidates":["p000","e000"]}
    assert M.enumerate_witnesses(workspace,grid)==()


def test_witness_ids_and_semantics_do_not_encode_palette_or_actions():
    grid,workspace=fixture();rows=M.enumerate_witnesses(workspace,grid)
    text=str([(row.witness_id,row.goal) for row in rows]).lower()
    assert all(row.goal["interaction_candidate"] is None for row in rows)
    assert "im00" not in text and "opaqueintervention" not in text and "ar25" not in text and "wa30" not in text
