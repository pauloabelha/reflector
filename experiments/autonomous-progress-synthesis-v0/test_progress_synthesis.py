from progress_synthesis import PotentialObservation, adjudicate, choose_focus, evaluate, infer_role_translation, public_document, synthesize


def placement_grid(palette=(0,2,7)):
    bg,item,slot=palette; g=[[bg]*24 for _ in range(20)]
    for x,y in ((2,2),(8,2)):
        for yy in range(y,y+3):
            for xx in range(x,x+3):g[yy][xx]=item
    for x,y in ((2,11),(10,11)):
        for yy in range(y,y+5):
            for xx in range(x,x+5):
                if xx in (x,x+4) or yy in (y,y+4):g[yy][xx]=slot
    return g


def flow_grid(palette=(12,4,6,9,11,1)):
    bg,emitter,stream,bar,sink,floor=palette;g=[[bg]*16 for _ in range(16)]
    g[0][9]=emitter;g[1][9]=stream
    for x in range(3,8):g[4][x]=bar
    for x in (4,10):
        g[13][x]=g[13][x+2]=sink
        for xx in range(x,x+3):g[14][xx]=sink
    for x in range(16):g[15][x]=floor
    return g


def test_compositional_synthesis_finds_placement_without_palette_contract():
    kinds={candidate.ast["potential"]["type"] for candidate in synthesize(placement_grid((13,41,29)))}
    assert "UnassignedMemberCount" in kinds


def test_compositional_synthesis_finds_flow_and_evaluates_progress():
    candidates=synthesize(flow_grid((31,7,22,44,18,3)))
    flow=next(c for c in candidates if c.ast["potential"]["type"]=="UnservedTerminalCount")
    assert evaluate(flow,flow_grid((31,7,22,44,18,3)))==2
    moved=flow_grid((31,7,22,44,18,3))
    for x in range(3,8):moved[4][x]=31
    for x in range(6,11):moved[4][x]=44
    # Re-synthesis creates situated identities for the new observation; the
    # transferable AST stays identical while the binding changes.
    moved_flow=next(c for c in synthesize(moved) if c.candidate_id==flow.candidate_id)
    assert evaluate(moved_flow,moved)==0


def test_scaled_rendering_does_not_change_generated_semantics():
    base=flow_grid();scaled=[[value for value in row for _ in range(4)] for row in base for _ in range(4)]
    base_kinds=[c.ast["potential"]["type"] for c in synthesize(base)]
    scaled_kinds=[c.ast["potential"]["type"] for c in synthesize(scaled)]
    assert base_kinds==scaled_kinds


def test_attention_is_not_support_and_only_direct_evidence_updates_support():
    candidate=synthesize(flow_grid())[0]
    assert candidate.support==0 and candidate.attention>0
    indirect=adjudicate(candidate,PotentialObservation(candidate.candidate_id,candidate.binding_id,2,0,False,"ev:indirect"))
    assert indirect.support==0 and indirect.evidence_count==0
    direct=adjudicate(candidate,PotentialObservation(candidate.candidate_id,candidate.binding_id,2,0,True,"ev:direct"))
    assert direct.support==10 and direct.evidence_count==1
    assert choose_focus([candidate,direct])==direct


def test_transferable_document_contains_no_situated_palette_or_coordinates():
    candidate=synthesize(placement_grid())[0];document=public_document(candidate);text=str(document)
    assert "binding" not in text and "bbox" not in text and "palette" not in text
    assert document["payload"]["empirical_support"]==0


def test_role_translation_is_learned_from_observation_not_action_name():
    before=placement_grid();candidate=next(c for c in synthesize(before) if c.ast["potential"]["type"]=="UnassignedMemberCount")
    after=[row[:] for row in before]
    for y in range(2,5):
        for x in range(2,5):after[y][x]=0
    for y in range(2,5):
        for x in range(3,6):after[y][x]=2
    assert infer_role_translation(candidate,before,after)==(1,0)


def test_sparse_specification_generates_coverage_goal():
    g=[[0]*25 for _ in range(25)]
    # Controller cross centered at (12,17).
    for x in range(7,18):g[17][x]=8
    for y in range(12,23):g[y][12]=8
    # Four framed requirements forming the same cross around (9,7).
    for x,y in ((9,3),(5,7),(13,7),(9,11)):
        for yy in range(y-1,y+2):
            for xx in range(x-1,x+2):g[yy][xx]=4
        g[y][x]=8
    kinds={c.ast["potential"]["type"] for c in synthesize(g)}
    assert "UncoveredRequirementCount" in kinds
