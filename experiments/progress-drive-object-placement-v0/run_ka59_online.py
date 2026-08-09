"""Consumed-development online policy: four calibration probes, no rollouts."""
from __future__ import annotations
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
BASE=load("online_placement_base",ROOT/"experiments/prior-accelerated-relational-transfer-v0/experiment.py");P=load("online_placement_core",HERE/"object_placement.py")
def selected_anchor(grid):
 for y in range(1,len(grid)-1):
  for x in range(1,len(grid[0])-1):
   if grid[y][x]==0 and sum(grid[yy][xx]==14 for yy in range(y-1,y+2) for xx in range(x-1,x+2))>=7:return x-1,y-1
 raise RuntimeError("selected object is not grounded")
def main():
 out=HERE/"artifacts"/"ka59-online";out.mkdir(parents=True,exist_ok=True);game="ka59";arcade,env=BASE.open_environment(ROOT/"environment_files",out/"recordings",game)
 try:
  initial=env.observation_space or env.reset();scene=P.infer_scene(BASE.observation_grid(initial));origin=(scene.items[0].x,scene.items[0].y);mapping={};calibration=[];legal=BASE.simple_legal_actions(env,initial)
  for action in legal:
   obs=env.reset();obs=BASE.execute_action(env,game,action,{},"online-placement-calibration");after=selected_anchor(BASE.observation_grid(obs));delta=after[0]-origin[0],after[1]-origin[1];calibration.append({"action":action,"delta":delta})
   if delta!=(0,0) and (delta[0]==0)!=(delta[1]==0) and abs(delta[0] or delta[1])<=3:mapping[delta]=action
  missing=[a for a in legal if a not in mapping.values()];observed=set(mapping)
  if len(missing)==1:
   absent=next(((-dx,-dy) for dx,dy in observed if (-dx,-dy) not in observed),None)
   if absent:mapping[absent]=missing[0]
  assistance=P.plan_blocked_assignment_push(scene,mapping,select_action_id=6);obs=env.reset();history=[]
  for step in assistance.steps:
   if step.kind.startswith("select") and selected_anchor(BASE.observation_grid(obs))==step.before:continue
   obs=BASE.execute_action(env,game,step.action_id,dict(step.data),"online-blocked-assignment-push");history.append({"action":step.action_id,"data":dict(step.data),"phase":step.kind})
  successor=P.track_item_scene(BASE.observation_grid(initial),BASE.observation_grid(obs),scene);finish=P.plan_placement(successor,mapping,select_action_id=6)
  for step in finish.steps:
   if step.kind.startswith("select") and selected_anchor(BASE.observation_grid(obs))==step.before:continue
   obs=BASE.execute_action(env,game,step.action_id,dict(step.data),"online-placement-finish");history.append({"action":step.action_id,"data":dict(step.data),"phase":step.kind})
   if BASE.observation_record(obs)["levels_completed"]>=1:break
  final=BASE.observation_record(obs);document={"calibration":calibration,"planning_interactions":len(calibration),"factual_actions":len(history),"actions":history,"levels_completed":final["levels_completed"],"final_digest":final["digest"]};(out/"RESULT.json").write_text(json.dumps(document,indent=2,sort_keys=True)+"\n");print(json.dumps(document,indent=2));return 0 if final["levels_completed"]>=1 else 1
 finally:arcade.close_scorecard()
if __name__=="__main__":raise SystemExit(main())
