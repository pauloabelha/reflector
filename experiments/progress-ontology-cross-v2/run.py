from __future__ import annotations
import importlib.util,json,pathlib,sys
from collections import Counter
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"fresh-1"
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
V1=load("ontology_cross_v1_base",HERE.parent/"progress-ontology-cross-v1"/"run.py")
ET=load("ontology_cross_v2_editable",HERE.parent/"progress-drive-editable-topology-v0"/"editable_topology.py")
SEL=load("ontology_cross_v2_selector",HERE/"selector.py")
V1.ART=ART

def complex_actions(env,obs):
 available={int(getattr(x,"value",x)) for x in getattr(obs,"available_actions",())};out=[]
 for transport in getattr(env,"action_space",()):
  action_id=int(getattr(transport,"value",transport));test=getattr(transport,"is_complex",None)
  if action_id in available and callable(test) and test():out.append(action_id)
 return tuple(sorted(out))

def qwen_request(c,points,image):
 workspace={"protocol":"editable-topology-workspace-v1","grounded_interaction_count":len(points),"objective_candidates":["IncreaseReachableSet","DecreaseShortestReachablePath"],"terminal":"ReachTerminal","empirical_support":0}
 schema={"type":"json_schema","json_schema":{"name":"editable_topology_goal","strict":True,"schema":{"type":"object","additionalProperties":False,"required":["protocol","family","potential","terminal","support"],"properties":{"protocol":{"const":"editable-topology-goal-v1"},"family":{"const":"navigation"},"potential":{"enum":["IncreaseReachableSet","DecreaseShortestReachablePath"]},"terminal":{"const":"ReachTerminal"},"support":{"const":0}}}}}
 text="Write one support-zero progress goal for this grounded editable visual world. Do not emit actions, clicks, directions, coordinates, colors, game knowledge, or a route.\nEPISTEMIC_WORKSPACE\n"+json.dumps(workspace,sort_keys=True,separators=(",",":"))
 return {"model":c["model"],"temperature":c["temperature"],"seed":c["seed"],"max_tokens":c["max_tokens"],"thinking_budget_tokens":c["thinking_budget_tokens"],"messages":[{"role":"user","content":[{"type":"text","text":text},{"type":"image_url","image_url":{"url":image}}]}],"response_format":schema}

def editable_arm(c,game):
 root=ART/"shared_progress_ontology";V1.B.ARTIFACTS=root;arcade,env=V1.B.LAB.BASE.BASE.open_environment(ROOT/"environment_files",root/"recordings",game);counter={"transitions":0}
 try:
  obs=env.observation_space or env.reset();initial=V1.B.LAB.BASE.BASE.observation_record(obs);grid=V1.B.LAB.BASE.BASE.observation_grid(obs);simple=V1.B.LAB.BASE.BASE.simple_legal_actions(env,obs);complex_ids=complex_actions(env,obs)
  if not complex_ids:raise RuntimeError("effect ontology abstained: no parameterized action")
  backgrounds=frozenset(value for value,_count in Counter(v for row in grid for v in row).most_common(2));points=ET.grounded_interaction_points(grid,background_values=backgrounds)
  if not points:raise RuntimeError("effect ontology abstained: no grounded interaction components")
  req=qwen_request(c,points,V1.B.LAB.BASE.grid_data_url(grid));V1.B.atomic_json(root/"request.json",req);response=V1.B.post_completion(c["endpoint"],req);V1.B.atomic_json(root/"response.json",response)
  vocab=ET.intervention_vocabulary(simple,parameterized_action_id=complex_ids[0],interaction_points=points)
  def observe(prefix):
   current=env.reset()
   for item in prefix:
    current=V1.B.LAB.BASE.execute_action(env,game,item.action_id,item.payload(),"editable-topology-search");counter["transitions"]+=1
   record=V1.B.LAB.BASE.BASE.observation_record(current)
   return {"digest":record["frame_sha256"],"done":record["levels_completed"]>=1,"state":record["state"]}
  search=ET.search_observed_state_space(vocab,observe_prefix=observe,state_key=lambda x:x["digest"],completed=lambda x:x["done"],viable=lambda x:str(x["state"]).upper().rsplit(".",1)[-1] not in {"GAME_OVER","WIN"},max_depth=c["search_depth"],max_expansions=c["search_expansions"])
  obs=env.reset();history=[]
  for item in search.plan:
   before=V1.B.LAB.BASE.BASE.observation_record(obs);obs=V1.B.LAB.BASE.execute_action(env,game,item.action_id,item.payload(),"editable-topology-plan");after=V1.B.LAB.BASE.BASE.observation_record(obs);history.append({"action":item.action_id,"data":item.payload(),"before":before,"after":after,"phase":"editable-topology"})
  final=V1.B.LAB.BASE.BASE.observation_record(obs)
 finally:arcade.close_scorecard()
 replay=exact_replay(history,game);result={"arm":"shared_progress_ontology","mechanism":"editable_topology","initial_digest":initial["digest"],"actions":len(history),"action_sequence":[row["action"] for row in history],"levels_completed":final["levels_completed"],"final_digest":final["digest"],"exact_replay":replay,"planning_interactions":counter["transitions"],"observed_state_count":search.observed_state_count,"qwen":response["parsed"]};V1.B.atomic_json(root/"RESULT.json",result);return result

def exact_replay(history,game):
 root=ART/"replay";arcade,env=V1.B.LAB.BASE.BASE.open_environment(ROOT/"environment_files",root,game)
 try:
  obs=env.observation_space or env.reset()
  for row in history:obs=V1.B.LAB.BASE.execute_action(env,game,row["action"],row.get("data",{}),"exact-replay")
  return V1.B.LAB.BASE.BASE.observation_record(obs)["digest"]==history[-1]["after"]["digest"]
 finally:arcade.close_scorecard()

def main():
 c=json.loads((HERE/"config.json").read_text());receipt=SEL.select(ROOT/"environment_files");V1.B.atomic_json(ART/"SELECTION.json",receipt);game=receipt["selected"]["game"];results=[]
 try:results.append(V1.run_arm("r2_cycle",c,game))
 except Exception as error:results.append({"arm":"r2_cycle","error":f"{type(error).__name__}: {error}"})
 try:
  try:results.append(V1.run_arm("shared_progress_ontology",c,game))
  except Exception:results.append(editable_arm(c,game))
 except Exception as error:results.append({"arm":"shared_progress_ontology","error":f"{type(error).__name__}: {error}"})
 same=len(results)==2 and all("initial_digest" in x for x in results) and results[0]["initial_digest"]==results[1]["initial_digest"];valid=same and all(x.get("exact_replay") for x in results);a,b=results;gain=valid and (b["levels_completed"]>a["levels_completed"] or (b["levels_completed"]>=1 and a["levels_completed"]>=1 and b["actions"]*4<=a["actions"]*3));summary={"verdict":"PASS" if gain else "FAIL" if valid else "INVALID","same_start":same,"results":results};V1.B.atomic_json(ART/"RESULT.json",summary);print(json.dumps(summary,indent=2));return 0 if gain else 1
if __name__=="__main__":raise SystemExit(main())
