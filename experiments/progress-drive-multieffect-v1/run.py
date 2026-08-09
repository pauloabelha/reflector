from __future__ import annotations
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"fresh-1"
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
B=load("multi_base",HERE.parent/"progress-goal-live-qwen-v1"/"live.py");T=load("multi_tracker",HERE.parent/"progress-goal-generic-calibration-v1"/"tracker.py");L=load("multi_lattice",HERE.parent/"progress-drive-lattice-v0"/"lattice_progress.py");S=load("multi_symbol",HERE.parent/"progress-drive-symbolic-v0"/"symbolic_progress.py");SP=load("multi_symbol_protocol",HERE.parent/"progress-drive-symbolic-v1"/"protocol.py");GP=load("multi_goal_protocol",HERE.parent/"progress-goal-live-qwen-v7"/"goal_protocol.py");SEL=load("multi_selector",HERE/"selector.py");B.ARTIFACTS=ART;B.TRACKER=T
def act(env,game,obs,action,history,phase):
 before=B.LAB.BASE.BASE.observation_record(obs);obs=B.LAB.BASE.execute_action(env,game,int(action),{},phase);after=B.LAB.BASE.BASE.observation_record(obs);history.append({"action":int(action),"before":before,"after":after,"phase":phase});B.atomic_json(ART/"checkpoint.json",{"history":history});return obs
def main():
 c=json.loads((HERE/"config.json").read_text());receipt=SEL.select(ROOT/"environment_files");B.atomic_json(ART/"SELECTION.json",receipt);game=receipt["selected"]["game"]
 arcade,env=B.LAB.BASE.BASE.open_environment(ROOT/"environment_files",ART/"recordings",game);history=[];mechanism="abstain";response=None
 try:
  obs=env.observation_space or env.reset();initial=B.LAB.BASE.BASE.observation_record(obs);initial_grid=B.LAB.BASE.BASE.observation_grid(obs);legal=B.LAB.BASE.BASE.simple_legal_actions(env,obs);figures=B.LAB.BASE.V0.V0.select_figures(initial_grid);panels=B.entity_rows(figures)
  cal=B.generic_calibration(env,obs,game,legal);obs=cal["observation"];history=cal["history"]
  if cal["pixel_controller"] is not None:
   mechanism="translation_affordance";grids=(cal["initial_grid"],)+tuple(cal["grid_successors"]);samples=tuple(L.motion_sample(grids[i],grids[i+1],before_anchor=r.before_anchor,after_anchor=r.after_anchor,size=r.size) for i,r in enumerate(cal["pixel_controller"]));field=L.infer_progress_field(samples);plan=L.plan_progress(field,cal["movement"])
   workspace=GP.build_workspace(entities=cal["entities"],transitions=cal["transition_rows"],frame={"height":len(initial_grid),"width":len(initial_grid[0])});req=GP.request_payload(workspace,c,B.LAB.BASE.grid_data_url(initial_grid));B.atomic_json(ART/"request.json",req);response=B.post_completion(c["endpoint"],req);B.atomic_json(ART/"response.json",response)
   actions=plan.actions
  else:
   first=cal["grid_successors"][0];changed=[(x,y) for y in range(len(first)) for x in range(len(first[0])) if initial_grid[y][x]!=first[y][x]]
   if not changed:raise RuntimeError("no calibrated visual effect class")
   task=S.infer_task(initial_grid,panels,mutation_origin=(min(x for x,y in changed),min(y for x,y in changed)));mechanism="symbolic_substitution";workspace=S.workspace_document(task);req=SP.request_payload(workspace,c,B.LAB.BASE.grid_data_url(initial_grid));B.atomic_json(ART/"request.json",req);response=B.post_completion(c["endpoint"],req);B.atomic_json(ART/"response.json",response);desired=S.compile_desired(response["parsed"],task)
   if desired!=task.desired:raise RuntimeError("semantic proposal contradicts grounded examples")
   actions=[]
   for index,(origin,target) in enumerate(zip(task.output_origins,desired)):
    count=0
    while S.glyph_signature(B.LAB.BASE.BASE.observation_grid(obs),origin)!=target:
     if count>=7:raise RuntimeError("symbol cycle exhausted")
     obs=act(env,game,obs,legal[1],history,"symbol-edit");count+=1
     if B.LAB.BASE.BASE.observation_record(obs)["levels_completed"]>=1:break
    if B.LAB.BASE.BASE.observation_record(obs)["levels_completed"]>=1:break
    if index+1<len(desired):obs=act(env,game,obs,legal[3],history,"slot-select")
   actions=()
  for action in actions:
   if len(history)>=int(c["action_budget"]) or B.LAB.BASE.BASE.observation_record(obs)["levels_completed"]>=1:break
   obs=act(env,game,obs,action,history,mechanism)
  final=B.LAB.BASE.BASE.observation_record(obs)
 finally:arcade.close_scorecard()
 B.ARTIFACTS=ART;replay=B.exact_replay(history,game);passed=final["levels_completed"]>=1 and len(history)<=c["completion_action_gate"] and replay;result={"verdict":"PASS" if passed else "FAIL","mechanism":mechanism,"initial_digest":initial["digest"],"actions":len(history),"action_sequence":[r["action"] for r in history],"levels_completed":final["levels_completed"],"final_digest":final["digest"],"exact_replay":replay,"qwen":None if response is None else response["parsed"]};B.atomic_json(ART/"RESULT.json",result);return 0 if passed else 1
if __name__=="__main__":raise SystemExit(main())
