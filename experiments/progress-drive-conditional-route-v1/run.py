from __future__ import annotations
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"fresh-1"
def load(n,p):s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
B=load("route_live_base",HERE.parent/"progress-goal-live-qwen-v1"/"live.py");T=load("route_live_tracker",HERE.parent/"progress-goal-generic-calibration-v1"/"tracker.py");R=load("route_live_kernel",HERE.parent/"progress-drive-conditional-route-v0"/"conditional_route.py");B.ARTIFACTS=ART;B.TRACKER=T
def payload(field,path,c,image):
 workspace={"protocol":"conditional-route-goal-v1","controlled_ref":"controlled0","terminal_ref":"terminal0","current_ref":"node0","reachable_node_count":len(field.nodes),"remaining_route_steps":len(path),"blocked_probes_are_topology_evidence":True,"empirical_support":0}
 schema={"type":"json_schema","json_schema":{"name":"route_goal","strict":True,"schema":{"type":"object","additionalProperties":False,"required":["protocol","family","controlled_ref","terminal_ref","potential","terminal"],"properties":{"protocol":{"const":"conditional-route-goal-v1"},"family":{"const":"navigation"},"controlled_ref":{"const":"controlled0"},"terminal_ref":{"const":"terminal0"},"potential":{"const":"RemainingRouteSteps"},"terminal":{"const":"ReachTerminal"}}}}}
 text="You are the semantic worker in a shared grounded workspace. Write the single support-zero progress goal justified by the reachable route and terminal. Do not emit actions, directions, colors, coordinates, or a route. Evidence alone changes support.\nEPISTEMIC_WORKSPACE\n"+json.dumps(workspace,sort_keys=True,separators=(",",":"))
 return {"model":c["model"],"temperature":c["temperature"],"seed":c["seed"],"max_tokens":c["max_tokens"],"thinking_budget_tokens":c["thinking_budget_tokens"],"messages":[{"role":"user","content":[{"type":"text","text":text},{"type":"image_url","image_url":{"url":image}}]}],"response_format":schema}
def main():
 c=json.loads((HERE/"config.json").read_text());game=c["development_game"];arcade,env=B.LAB.BASE.BASE.open_environment(ROOT/"environment_files",ART/"recordings",game);history=[]
 try:
  obs=env.observation_space or env.reset();initial=B.LAB.BASE.BASE.observation_record(obs);initial_grid=B.LAB.BASE.BASE.observation_grid(obs);legal=B.LAB.BASE.BASE.simple_legal_actions(env,obs);cal=B.generic_calibration(env,obs,game,legal);obs=cal["observation"];history=cal["history"]
  grids=(cal["initial_grid"],)+tuple(cal["grid_successors"]);motion=None;motion_action=None
  for i in range(len(legal)):
   rows=T.pixel_motion_hypotheses(grids[i],grids[i+1])
   if rows:
    if motion is not None:raise RuntimeError("calibration produced multiple unrelated movers")
    motion=rows[0];motion_action=int(legal[i])
  if motion is None:raise RuntimeError("no sparse action-correlated motion")
  field=R.infer_route_field(initial_grid,before_anchor=motion.before_anchor,after_anchor=motion.after_anchor,size=motion.size,actor_colors=motion.colors);current=motion.after_anchor;path=R.shortest_route(field,initial_grid,start=current)
  req=payload(field,path,c,B.LAB.BASE.grid_data_url(initial_grid));B.atomic_json(ART/"request.json",req);response=B.post_completion(c["endpoint"],req);B.atomic_json(ART/"response.json",response)
  if response["parsed"].get("terminal")!="ReachTerminal":raise RuntimeError("Qwen did not construct the grounded progress goal")
  mapping={motion.delta:motion_action};blocked=[]
  while B.LAB.BASE.BASE.observation_record(obs)["levels_completed"]<1 and len(history)<c["action_budget"]:
   path=R.shortest_route(field,initial_grid,start=current);wanted=R.desired_delta(current,path);candidates=[mapping[wanted]] if wanted in mapping else [int(a) for a in legal if int(a) not in mapping.values()]
   moved=False
   for action in candidates:
    before_grid=B.LAB.BASE.BASE.observation_grid(obs);before=B.LAB.BASE.BASE.observation_record(obs);obs=B.LAB.BASE.execute_action(env,game,action,{},"conditional-route-control");after=B.LAB.BASE.BASE.observation_record(obs);after_grid=B.LAB.BASE.BASE.observation_grid(obs);history.append({"action":action,"before":before,"after":after,"phase":"conditional-route","wanted_delta":wanted});B.atomic_json(ART/"checkpoint.json",{"history":history})
    if after["levels_completed"]>=1:moved=True;break
    before_anchor=R.controlled_anchor(before_grid,colors=motion.colors,mass=motion.mass,size=motion.size);after_anchor=R.controlled_anchor(after_grid,colors=motion.colors,mass=motion.mass,size=motion.size)
    if before_anchor==after_anchor:blocked.append({"node":current,"action":action});continue
    delta=after_anchor[0]-before_anchor[0],after_anchor[1]-before_anchor[1];mapping[delta]=action;current=after_anchor;moved=True;break
   if not moved:raise RuntimeError("no intervention reached the planned neighbor")
  final=B.LAB.BASE.BASE.observation_record(obs)
 finally:arcade.close_scorecard()
 B.ARTIFACTS=ART;replay=B.exact_replay(history,game);passed=final["levels_completed"]>=1 and len(history)<=c["completion_action_gate"] and replay;result={"verdict":"PASS" if passed else "FAIL","development_only":True,"initial_digest":initial["digest"],"actions":len(history),"action_sequence":[r["action"] for r in history],"levels_completed":final["levels_completed"],"final_digest":final["digest"],"exact_replay":replay,"qwen_goal":response["parsed"],"qwen_support":0,"learned_action_deltas":{str(k):v for k,v in mapping.items()},"blocked_probe_count":len(blocked)};B.atomic_json(ART/"RESULT.json",result);return 0 if passed else 1
if __name__=="__main__":raise SystemExit(main())
