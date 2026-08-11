"""Consumed-development visual placement check; no source state is imported."""
from __future__ import annotations
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
BASE=load("placement_ka59_base",ROOT/"experiments/prior-accelerated-relational-transfer-v0/experiment.py");P=load("placement_ka59_core",HERE/"object_placement.py")
def selected_anchor(grid):
 for y in range(1,len(grid)-1):
  for x in range(1,len(grid[0])-1):
   if grid[y][x]==0 and sum(grid[yy][xx]==14 for yy in range(y-1,y+2) for xx in range(x-1,x+2))>=7:return x-1,y-1
 raise RuntimeError("selected object marker is not uniquely visible")
def main():
 out=HERE/"artifacts"/"ka59-visual";out.mkdir(parents=True,exist_ok=True);game="ka59";arcade,env=BASE.open_environment(ROOT/"environment_files",out/"recordings",game)
 try:
  initial_obs=env.observation_space or env.reset();initial_grid=BASE.observation_grid(initial_obs);scene=P.infer_scene(initial_grid);origin=(scene.items[0].x,scene.items[0].y);mapping={}
  for action in BASE.simple_legal_actions(env,initial_obs):
   obs=env.reset();obs=BASE.execute_action(env,game,action,{},"placement-motion-calibration");after=P.infer_scene(BASE.observation_grid(obs));position=min(((b.x,b.y) for b in after.items),key=lambda p:abs(p[0]-origin[0])+abs(p[1]-origin[1]));delta=position[0]-origin[0],position[1]-origin[1]
   if delta!=(0,0) and (delta[0]==0 or delta[1]==0) and abs(delta[0] or delta[1])<=3:mapping[delta]=action
  observed_actions=set(mapping.values());missing=[a for a in BASE.simple_legal_actions(env,initial_obs) if a not in observed_actions]
  observed=set(mapping)
  if len(missing)==1:
   absent=next((d for d in tuple((-dx,-dy) for dx,dy in observed) if d not in observed),None)
   if absent is not None:mapping[absent]=missing[0]
  plan=P.plan_placement(scene,mapping,select_action_id=6);obs=env.reset();history=[]
  for step in plan.steps:
   attempts=0
   while True:
    data=dict(step.data);obs=BASE.execute_action(env,game,step.action_id,data,"visual-object-placement-closed-loop");history.append({"action":step.action_id,"data":data});record=BASE.observation_record(obs);attempts+=1
    if record["levels_completed"]>=1:break
    current=selected_anchor(BASE.observation_grid(obs))
    print(step.kind,step.before,"->",step.after,"attempt",attempts,"observed",current,flush=True)
    if step.kind=="select" or current==step.after:break
    if attempts>=8:raise RuntimeError(f"macro step failed to settle at {step.after}; observed {current}")
   if record["levels_completed"]>=1:break
  final=BASE.observation_record(obs);document={"mapping":{str(k):v for k,v in mapping.items()},"actions":history,"action_count":len(history),"levels_completed":final["levels_completed"],"final_digest":final["digest"]};(out/"RESULT.json").write_text(json.dumps(document,indent=2,sort_keys=True)+"\n");print(json.dumps(document,indent=2));return 0 if final["levels_completed"]>=1 else 1
 finally:arcade.close_scorecard()
if __name__=="__main__":raise SystemExit(main())
