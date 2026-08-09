"""Consumed-development black-box check for whole-scene object addressing."""
from __future__ import annotations
import importlib.util,json,pathlib,sys
from collections import Counter
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
BASE=load("editable_ka59_base",ROOT/"experiments/prior-accelerated-relational-transfer-v0/experiment.py")
ET=load("editable_ka59_core",HERE/"editable_topology.py")
def main():
 out=HERE/"artifacts"/"ka59-object-addressing";out.mkdir(parents=True,exist_ok=True);game="ka59";arcade,env=BASE.open_environment(ROOT/"environment_files",out/"recordings",game);counter=0
 try:
  obs=env.observation_space or env.reset();grid=BASE.observation_grid(obs);simple=BASE.simple_legal_actions(env,obs);points=ET.grounded_object_points(grid)[:4]
  def observe(prefix):
   nonlocal counter
   current=env.reset()
   for item in prefix:current=BASE.execute_action(env,game,item.action_id,item.payload(),"whole-scene-object-search");counter+=1
   record=BASE.observation_record(current);successor=BASE.observation_grid(current);return {"grid":successor,"semantic":tuple(successor[:-1]),"done":record["levels_completed"]>=1,"state":record["state"]}
  def available(state):
   dynamic=ET.grounded_object_points(state["grid"])[:4]
   return ET.intervention_vocabulary(simple,parameterized_action_id=6,interaction_points=dynamic)
  result=ET.search_observed_state_space((),observe_prefix=observe,state_key=lambda x:x["semantic"],completed=lambda x:x["done"],viable=lambda x:str(x["state"]).upper().rsplit(".",1)[-1] not in {"GAME_OVER","WIN"},interventions_for_state=available,max_depth=48,max_expansions=100000)
  current=env.reset();records=[]
  for item in result.plan:
   current=BASE.execute_action(env,game,item.action_id,item.payload(),"whole-scene-object-plan");records.append({"action":item.action_id,"data":item.payload()})
  final=BASE.observation_record(current);document={"actions":records,"factual_action_count":len(records),"planning_interactions":counter,"observed_state_count":result.observed_state_count,"grounded_points":points,"final":final};(out/"RESULT.json").write_text(json.dumps(document,indent=2,sort_keys=True)+"\n");print(json.dumps(document,indent=2));return 0
 finally:arcade.close_scorecard()
if __name__=="__main__":raise SystemExit(main())
