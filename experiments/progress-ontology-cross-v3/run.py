from __future__ import annotations
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"fresh-1"
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
V2=load("ontology_v3_v2",HERE.parent/"progress-ontology-cross-v2"/"run.py");P=load("ontology_v3_placement",HERE.parent/"progress-drive-object-placement-v0"/"object_placement.py");SEL=load("ontology_v3_selector",HERE/"selector.py");V2.ART=ART;V2.V1.ART=ART
B=V2.V1.B
def terminal(record):return str(record["state"]).upper().rsplit(".",1)[-1] in {"GAME_OVER","WIN"} or record["levels_completed"]>=1
def execute(env,game,obs,action,data,history,phase):
 before=B.LAB.BASE.BASE.observation_record(obs);obs=B.LAB.BASE.execute_action(env,game,action,data,phase);after=B.LAB.BASE.BASE.observation_record(obs);history.append({"action":action,"data":data,"before":before,"after":after,"phase":phase});return obs
def replay(history,game,root):
 arcade,env=B.LAB.BASE.BASE.open_environment(ROOT/"environment_files",root,game)
 try:
  obs=env.observation_space or env.reset()
  for row in history:obs=B.LAB.BASE.execute_action(env,game,row["action"],row["data"],"exact-replay")
  return B.LAB.BASE.BASE.observation_record(obs)["digest"]==history[-1]["after"]["digest"]
 finally:arcade.close_scorecard()
def baseline(c,game):
 root=ART/"r2_cycle";arcade,env=B.LAB.BASE.BASE.open_environment(ROOT/"environment_files",root/"recordings",game);history=[]
 try:
  obs=env.observation_space or env.reset();initial=B.LAB.BASE.BASE.observation_record(obs);legal=B.LAB.BASE.BASE.simple_legal_actions(env,obs)
  for i in range(c["action_budget"]):
   if terminal(B.LAB.BASE.BASE.observation_record(obs)):break
   obs=execute(env,game,obs,legal[i%len(legal)],{},history,"cycle")
  final=B.LAB.BASE.BASE.observation_record(obs)
 finally:arcade.close_scorecard()
 result={"arm":"r2_cycle","initial_digest":initial["digest"],"actions":len(history),"levels_completed":final["levels_completed"],"final_digest":final["digest"],"exact_replay":replay(history,game,ART/"replay-cycle")};B.atomic_json(root/"RESULT.json",result);return result
def placement(c,game):
 root=ART/"shared_progress_ontology";arcade,env=B.LAB.BASE.BASE.open_environment(ROOT/"environment_files",root/"recordings",game);history=[]
 try:
  initial_obs=env.observation_space or env.reset();initial=B.LAB.BASE.BASE.observation_record(initial_obs);initial_grid=B.LAB.BASE.BASE.observation_grid(initial_obs);scene=P.infer_scene(initial_grid);legal=B.LAB.BASE.BASE.simple_legal_actions(env,initial_obs);complex_ids=V2.complex_actions(env,initial_obs)
  if not complex_ids:raise P.PlacementError("placement requires a parameterized selection")
  mapping={};calibration=[];origins={(b.x,b.y) for b in scene.items}
  for action in legal:
   probe=env.reset();probe=B.LAB.BASE.execute_action(env,game,action,{},"placement-calibration");tracked=P.track_item_scene(initial_grid,B.LAB.BASE.BASE.observation_grid(probe),scene);successors={(b.x,b.y) for b in tracked.items};gone=origins-successors;new=successors-origins
   delta=None
   if len(gone)==len(new)==1:
    a=next(iter(gone));z=next(iter(new));delta=(z[0]-a[0],z[1]-a[1]);mapping[delta]=action
   calibration.append({"action":action,"delta":delta})
  request=V2.qwen_request(c,tuple((b.x+b.width//2,b.y+b.height//2) for b in scene.items),B.LAB.BASE.grid_data_url(initial_grid));B.atomic_json(root/"request.json",request);response=B.post_completion(c["endpoint"],request);B.atomic_json(root/"response.json",response)
  obs=env.reset()
  try:assist=P.plan_blocked_assignment_push(scene,mapping,select_action_id=complex_ids[0]);prefix=assist.steps
  except P.NoPlacementPlan:prefix=()
  for step in prefix:obs=execute(env,game,obs,step.action_id,dict(step.data),history,step.kind)
  successor=P.track_item_scene(initial_grid,B.LAB.BASE.BASE.observation_grid(obs),scene);finish=P.plan_placement(successor,mapping,select_action_id=complex_ids[0])
  for step in finish.steps:
   obs=execute(env,game,obs,step.action_id,dict(step.data),history,step.kind)
   if terminal(B.LAB.BASE.BASE.observation_record(obs)):break
  final=B.LAB.BASE.BASE.observation_record(obs)
 finally:arcade.close_scorecard()
 result={"arm":"shared_progress_ontology","mechanism":"multi_object_placement","initial_digest":initial["digest"],"planning_interactions":len(calibration),"actions":len(history),"levels_completed":final["levels_completed"],"final_digest":final["digest"],"exact_replay":replay(history,game,ART/"replay-shared"),"qwen":response["parsed"]};B.atomic_json(root/"RESULT.json",result);return result
def shared(c,game):
 try:return placement(c,game)
 except (P.PlacementError,P.NoPlacementPlan) as placement_error:
  try:return V2.V1.run_arm("shared_progress_ontology",c,game)
  except Exception as dispatch_error:return {"arm":"shared_progress_ontology","status":"ontology_abstention","placement":str(placement_error),"dispatcher":f"{type(dispatch_error).__name__}: {dispatch_error}"}
def main():
 c=json.loads((HERE/"config.json").read_text());receipt=SEL.select(ROOT/"environment_files");B.atomic_json(ART/"SELECTION.json",receipt);game=receipt["selected"]["game"];results=[]
 for fn in (baseline,shared):
  try:results.append(fn(c,game))
  except Exception as error:results.append({"arm":"r2_cycle" if fn is baseline else "shared_progress_ontology","error":f"{type(error).__name__}: {error}"})
 same=len(results)==2 and all("initial_digest" in x for x in results) and results[0]["initial_digest"]==results[1]["initial_digest"];valid=same and all(x.get("exact_replay") for x in results);a,b=results;gain=valid and (b["levels_completed"]>a["levels_completed"] or (b["levels_completed"]>=1 and a["levels_completed"]>=1 and b["actions"]*4<=a["actions"]*3));summary={"verdict":"PASS" if gain else "FAIL" if valid else "ABSTAIN" if b.get("status")=="ontology_abstention" else "INVALID","same_start":same,"results":results};B.atomic_json(ART/"RESULT.json",summary);print(json.dumps(summary,indent=2));return 0 if gain else 1
if __name__=="__main__":raise SystemExit(main())
