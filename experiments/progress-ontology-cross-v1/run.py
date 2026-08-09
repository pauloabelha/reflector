from __future__ import annotations
import importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"fresh-1"
def load(n,p):s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
B=load("ontology_base",HERE.parent/"progress-goal-live-qwen-v1"/"live.py");T=load("ontology_tracker",HERE.parent/"progress-goal-generic-calibration-v1"/"tracker.py");L=load("ontology_lattice",HERE.parent/"progress-drive-lattice-v0"/"lattice_progress.py");S=load("ontology_symbol",HERE.parent/"progress-drive-symbolic-v0"/"symbolic_progress.py");SP=load("ontology_symbol_protocol",HERE.parent/"progress-drive-symbolic-v1"/"protocol.py");R=load("ontology_route",HERE.parent/"progress-drive-conditional-route-v0"/"conditional_route.py");GP=load("ontology_goal_protocol",HERE.parent/"progress-goal-live-qwen-v7"/"goal_protocol.py");SEL=load("ontology_selector",HERE/"selector.py");B.TRACKER=T
def route_payload(field,path,c,image):
 w={"protocol":"conditional-route-goal-v1","controlled_ref":"controlled0","terminal_ref":"terminal0","reachable_node_count":len(field.nodes),"remaining_route_steps":len(path),"blocked_probes_are_topology_evidence":True,"empirical_support":0};schema={"type":"json_schema","json_schema":{"name":"route_goal","strict":True,"schema":{"type":"object","additionalProperties":False,"required":["protocol","family","controlled_ref","terminal_ref","potential","terminal"],"properties":{"protocol":{"const":"conditional-route-goal-v1"},"family":{"const":"navigation"},"controlled_ref":{"const":"controlled0"},"terminal_ref":{"const":"terminal0"},"potential":{"const":"RemainingRouteSteps"},"terminal":{"const":"ReachTerminal"}}}}};text="Construct the single support-zero progress goal from this grounded route workspace. Do not emit actions, directions, colors, coordinates or a route.\nEPISTEMIC_WORKSPACE\n"+json.dumps(w,sort_keys=True,separators=(",",":"));return {"model":c["model"],"temperature":c["temperature"],"seed":c["seed"],"max_tokens":c["max_tokens"],"thinking_budget_tokens":c["thinking_budget_tokens"],"messages":[{"role":"user","content":[{"type":"text","text":text},{"type":"image_url","image_url":{"url":image}}]}],"response_format":schema}
def execute(env,game,obs,action,history,root,phase):
 before=B.LAB.BASE.BASE.observation_record(obs);obs=B.LAB.BASE.execute_action(env,game,int(action),{},phase);after=B.LAB.BASE.BASE.observation_record(obs);history.append({"action":int(action),"before":before,"after":after,"phase":phase});B.atomic_json(root/"checkpoint.json",{"history":history});return obs
def motions(cal,legal):
 grids=(cal["initial_grid"],)+tuple(cal["grid_successors"]);groups={}
 for i,a in enumerate(legal):
  for row in T.pixel_motion_hypotheses(grids[i],grids[i+1]):groups.setdefault((row.colors,row.mass,row.size),[]).append((int(a),row))
 if not groups:return [],grids
 ranked=sorted(groups.items(),key=lambda x:(-len(x[1]),-len(x[0][0]),-x[0][1],x[0]))
 if len(ranked)>1 and len(ranked[0][1])==len(ranked[1][1]):return [],grids
 return ranked[0][1],grids
def run_arm(arm,c,game):
 root=ART/arm;B.ARTIFACTS=root;arcade,env=B.LAB.BASE.BASE.open_environment(ROOT/"environment_files",root/"recordings",game);history=[];mechanism="cycle";response=None
 try:
  obs=env.observation_space or env.reset();initial=B.LAB.BASE.BASE.observation_record(obs);initial_grid=B.LAB.BASE.BASE.observation_grid(obs);legal=B.LAB.BASE.BASE.simple_legal_actions(env,obs);panels=B.entity_rows(B.LAB.BASE.V0.V0.select_figures(initial_grid));cal=B.generic_calibration(env,obs,game,legal);obs=cal["observation"];history=cal["history"]
  if arm=="r2_cycle":actions=[legal[i%len(legal)] for i in range(c["action_budget"]-len(history))]
  else:
   rows,grids=motions(cal,legal);actions=[]
   deltas={row.delta for _a,row in rows};magnitudes={abs(dx or dy) for dx,dy in deltas if bool(dx)!=bool(dy)}
   if len(rows)==len(legal) and len(deltas)>=4 and len(magnitudes)==1:
    mechanism="translation_affordance";sample_rows=[row for _a,row in sorted(rows)];field=L.infer_progress_field(tuple(L.motion_sample(grids[i],grids[i+1],before_anchor=row.before_anchor,after_anchor=row.after_anchor,size=row.size) for i,row in enumerate(sample_rows)));mapping={row.delta:a for a,row in rows};plan=L.plan_progress(field,mapping);actions=list(plan.actions);workspace=GP.build_workspace(entities=cal["entities"],transitions=cal["transition_rows"],frame={"height":len(initial_grid),"width":len(initial_grid[0])});req=GP.request_payload(workspace,c,B.LAB.BASE.grid_data_url(initial_grid))
   elif rows:
    mechanism="conditional_route";a0,motion=rows[0];field=R.infer_route_field(initial_grid,before_anchor=motion.before_anchor,after_anchor=motion.after_anchor,size=motion.size,actor_colors=motion.colors);current=motion.after_anchor;path=R.shortest_route(field,initial_grid,start=current);req=route_payload(field,path,c,B.LAB.BASE.grid_data_url(initial_grid));mapping={motion.delta:a0}
   else:
    changed=[(x,y) for y in range(len(initial_grid)) for x in range(len(initial_grid[0])) if initial_grid[y][x]!=grids[1][y][x]]
    if not changed:raise RuntimeError("effect ontology abstained")
    task=S.infer_task(initial_grid,panels,mutation_origin=(min(x for x,y in changed),min(y for x,y in changed)));mechanism="symbolic_substitution";workspace=S.workspace_document(task);req=SP.request_payload(workspace,c,B.LAB.BASE.grid_data_url(initial_grid))
   B.atomic_json(root/"request.json",req);response=B.post_completion(c["endpoint"],req);B.atomic_json(root/"response.json",response)
   if mechanism=="symbolic_substitution":
    desired=S.compile_desired(response["parsed"],task)
    if desired!=task.desired:raise RuntimeError("Qwen contradicted examples")
    for index,(origin,target) in enumerate(zip(task.output_origins,desired)):
     tries=0
     while S.glyph_signature(B.LAB.BASE.BASE.observation_grid(obs),origin)!=target:
      if tries>=7:raise RuntimeError("symbol cycle exhausted")
      obs=execute(env,game,obs,legal[1],history,root,"symbol-edit");tries+=1
      if B.LAB.BASE.BASE.observation_record(obs)["levels_completed"]>=1:break
     if B.LAB.BASE.BASE.observation_record(obs)["levels_completed"]>=1:break
     if index+1<len(desired):obs=execute(env,game,obs,legal[3],history,root,"slot-select")
   elif mechanism=="conditional_route":
    while B.LAB.BASE.BASE.observation_record(obs)["levels_completed"]<1 and len(history)<c["action_budget"]:
     path=R.shortest_route(field,initial_grid,start=current);want=R.desired_delta(current,path);candidates=[mapping[want]] if want in mapping else [int(a) for a in legal if int(a) not in mapping.values()];moved=False
     for action in candidates:
      before_grid=B.LAB.BASE.BASE.observation_grid(obs);obs=execute(env,game,obs,action,history,root,"conditional-route");after=B.LAB.BASE.BASE.observation_record(obs);after_grid=B.LAB.BASE.BASE.observation_grid(obs)
      if after["levels_completed"]>=1:moved=True;break
      ba=R.controlled_anchor(before_grid,colors=motion.colors,mass=motion.mass,size=motion.size);aa=R.controlled_anchor(after_grid,colors=motion.colors,mass=motion.mass,size=motion.size)
      if ba==aa:continue
      delta=aa[0]-ba[0],aa[1]-ba[1];mapping[delta]=action;current=aa;moved=True;break
     if not moved:raise RuntimeError("route action discovery exhausted")
  for action in actions:
   if len(history)>=c["action_budget"] or B.LAB.BASE.BASE.observation_record(obs)["levels_completed"]>=1:break
   obs=execute(env,game,obs,action,history,root,mechanism)
  final=B.LAB.BASE.BASE.observation_record(obs)
 finally:arcade.close_scorecard()
 B.ARTIFACTS=root;replay=B.exact_replay(history,game);result={"arm":arm,"mechanism":mechanism,"initial_digest":initial["digest"],"actions":len(history),"action_sequence":[r["action"] for r in history],"levels_completed":final["levels_completed"],"final_digest":final["digest"],"exact_replay":replay,"qwen":None if response is None else response["parsed"]};B.atomic_json(root/"RESULT.json",result);return result
def main():
 c=json.loads((HERE/"config.json").read_text());receipt=SEL.select(ROOT/"environment_files");B.atomic_json(ART/"SELECTION.json",receipt);game=receipt["selected"]["game"];results=[]
 for arm in ("r2_cycle","shared_progress_ontology"):
  try:results.append(run_arm(arm,c,game))
  except Exception as error:results.append({"arm":arm,"error":f"{type(error).__name__}: {error}"})
 same=len(results)==2 and all("initial_digest" in r for r in results) and results[0]["initial_digest"]==results[1]["initial_digest"];valid=same and all(r.get("exact_replay") for r in results);a,b=results;gain=valid and (b["levels_completed"]>a["levels_completed"] or (b["levels_completed"]>=1 and a["levels_completed"]>=1 and b["actions"]*4<=a["actions"]*3));summary={"verdict":"PASS" if gain else "FAIL" if valid else "INVALID","same_start":same,"results":results};B.atomic_json(ART/"RESULT.json",summary);return 0 if summary["verdict"]=="PASS" else 1
if __name__=="__main__":raise SystemExit(main())
