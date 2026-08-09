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

def test_blocked_assignment_uses_aligned_item_as_pusher():
 scene=M.PlacementScene(
  items=(M.Box(3,5,2,2),M.Box(7,5,2,2)),
  slots=(M.Box(13,4,4,4),M.Box(0,8,4,4)),
  blocked=frozenset((x,y) for x in range(10,12) for y in range(2,9)),
  bounds=M.Box(0,0,20,12),
 )
 push=M.plan_blocked_assignment_push(scene,{(1,0):4,(-1,0):3,(0,1):2,(0,-1):1},select_action_id=6)
 assert push.pusher_index==0 and push.blocked_item_index==1
 assert [step.action_id for step in push.steps]==[6,4,4,4]

def test_item_identity_survives_contact_with_slot_rim():
 initial=[[0]*12 for _ in range(8)]
 for ox in (1,5):
  for y in range(4,6):
   for x in range(ox,ox+2):initial[y][x]=7
 for y in range(1,5):
  for x in range(8,12):
   if x in (8,11) or y in (1,4):initial[y][x]=4
 scene=M.PlacementScene((M.Box(1,4,2,2),M.Box(5,4,2,2)),(M.Box(8,1,4,4),),frozenset(),M.Box(0,0,12,8))
 current=[row[:] for row in initial]
 for y in range(4,6):
  for x in range(5,7):current[y][x]=0
 for y in range(2,4):
  for x in range(7,9):current[y][x]=7
 tracked=M.track_item_scene(initial,current,scene)
 assert tracked.items==(M.Box(7,2,2,2),M.Box(1,4,2,2))
