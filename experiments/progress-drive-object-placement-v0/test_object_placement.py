from __future__ import annotations
import importlib.util,pathlib,sys
P=pathlib.Path(__file__).with_name("object_placement.py");S=importlib.util.spec_from_file_location("placement_tested",P);assert S and S.loader;M=importlib.util.module_from_spec(S);sys.modules[S.name]=M;S.loader.exec_module(M)
def test_infers_and_plans_selectable_object_placement():
 g=[[0]*15 for _ in range(10)]
 for ox,oy in ((1,1),(10,1)):
  for y in range(oy,oy+5):
   for x in range(ox,ox+5):
    if x in (ox,ox+4) or y in (oy,oy+4):g[y][x]=4
 for ox,oy in ((1,7),(7,7)):
  for y in range(oy,oy+3):
   for x in range(ox,ox+3):g[y][x]=14
 scene=M.infer_scene(g);plan=M.plan_placement(scene,{(0,-1):1,(0,1):2,(-1,0):3,(1,0):4},select_action_id=6)
 assert len(scene.items)==len(scene.slots)==2
 assert sum(step.kind=="select" for step in plan.steps)==2
 assert plan.steps[-1].after in {(2,2),(11,2)}
