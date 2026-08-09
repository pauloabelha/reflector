import guarded_visual_induction as M


def frame():
    g=[[0]*25 for _ in range(25)]
    # traversable field
    for y in range(2,18):
      for x in range(2,23):g[y][x]=1
    # actor, target frame+glyph, transformer, boundary register+glyph
    for y in range(12,14):
      for x in range(12,14):g[y][x]=2
    for x in range(17,22):g[3][x]=3;g[7][x]=3
    for y in range(3,8):g[y][17]=3;g[y][21]=3
    g[5][19]=4;g[6][19]=4
    g[9][7]=5;g[9][8]=5;g[10][8]=6
    for y in range(19,25):
      for x in range(6):g[y][x]=7
    g[21][2]=4;g[22][2]=4
    return tuple(tuple(row) for row in g)


def calibration(action,before,after,grid):return M.MotionCalibration(action,before,after,(2,2),grid,"transition:"+str(action))


def test_enumerates_source_blind_roles_and_probe_path_under_action_relabeling():
    initial=frame();revealed=[list(row) for row in initial]
    for y in range(12,14):
      for x in range(12,14):revealed[y][x]=1
    revealed=tuple(tuple(row) for row in revealed)
    rows=(calibration(91,(12,12),(10,12),revealed),calibration(7,(12,12),(14,12),revealed),calibration(44,(12,12),(12,10),revealed),calibration(3,(12,12),(12,14),revealed))
    hypotheses=M.enumerate_hypotheses(initial,rows)
    assert hypotheses
    first=hypotheses[0]
    assert first.current_register and first.required_register
    capability=M.probe_capability(first);plan=__import__('guarded_obligation_capability').plan_capability(capability)
    assert plan.mode=="probe-transformer" and plan.actions
    assert capability.empirical_support==0
    projected=__import__('region_object_projection').project_objects(initial,controlled_bboxes=((12,12,14,14),))
    register=next(row for row in projected if row.boundary_distance==0 and row.enclosure_count)
    assert M.observe_register(initial,register.bbox) is not None


def test_register_signature_prefers_structured_glyph_over_larger_uniform_fragment():
    item=__import__('region_object_projection').RegionObject(
        "vo:test",(0,0,8,8),(),2,(),True,False,0,1,
        ((9,((0,0),)*12),(9,((0,0),(1,0),(1,1)))),
    )
    signature=M._register_signature(item)
    assert signature is not None
    assert signature[1]=="shape:"+__import__('hashlib').sha256(
        repr(((0,0),(1,0),(1,1))).encode()
    ).hexdigest()[:20]
