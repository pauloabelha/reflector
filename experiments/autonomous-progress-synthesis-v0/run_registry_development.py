"""One registry, five consumed mechanics, no game-conditioned capability path."""
from __future__ import annotations
import argparse,importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"registry-development";sys.path.insert(0,str(HERE))
import capability_registry as REGISTRY
import route_option as ROUTE
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p);assert s and s.loader;m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
BASE=load("registry_development_base",ROOT/"experiments/prior-accelerated-relational-transfer-v0/experiment.py")
def complex_actions(env,obs):
 available={int(getattr(x,"value",x)) for x in getattr(obs,"available_actions",())};out=[]
 for item in getattr(env,"action_space",()):
  action=int(getattr(item,"value",item));test=getattr(item,"is_complex",None)
  if action in available and callable(test) and test():out.append(action)
 return tuple(sorted(out))
def run_game(game,limit=64):
 root=ART/game;arcade,env=BASE.open_environment(ROOT/"environment_files",root/"recordings",game);history=[]
 try:
  initial_obs=env.observation_space or env.reset();initial=BASE.observation_record(initial_obs);grid=BASE.observation_grid(initial_obs);legal=BASE.simple_legal_actions(env,initial_obs);successors={}
  for action in legal:env.reset();successors[action]=BASE.observation_grid(BASE.execute_action(env,game,action,{},"capability-calibration"))
  panels=REGISTRY.symbolic.panel_rows(BASE.extract_figures(grid))
  proposals=REGISTRY.propose(grid,successors,parameterized_actions=complex_actions(env,initial_obs),symbolic_panels=panels)
  if not proposals:raise RuntimeError("capability registry abstained")
  selected=proposals[0];obs=env.reset()
  def act(action,data,role):
   nonlocal obs
   before=BASE.observation_record(obs);obs=BASE.execute_action(env,game,action,data,role);after=BASE.observation_record(obs);history.append({"action":action,"data":data,"before":before,"after":after,"role":role});return after
  if selected.capability.startswith("exact:"):
   option=selected.execution;proposal=option.proposal
   while len(history)<limit:
    for command in proposal.commands[:limit-len(history)]:
     if act(command.opaque_action,dict(command.data),command.role)["levels_completed"]>=1:break
    if BASE.observation_record(obs)["levels_completed"]>=1 or proposal.complete:break
    current_grid=BASE.observation_grid(obs);matches=[row for row in REGISTRY.synthesis.synthesize(current_grid) if row.candidate_id==option.candidate.candidate_id]
    if not matches:break
    current=min(matches,key=lambda row:(-row.attention,row.binding_id))
    proposal=REGISTRY.exact.compile_execution(current,current_grid,motion_actions=dict(option.motion_actions),parameterized_actions=option.parameterized_actions,release_actions=option.release_actions,grounding_memory=proposal.grounding_memory)
  elif selected.capability.startswith("gradient:"):
   _candidate,_variable,plan=selected.execution
   for action in plan.opaque_actions[:limit]:
    if act(action,{},"gradient-option")["levels_completed"]>=1:break
  elif selected.capability=="interactive:conditional-route":
   option=selected.execution;mapping=dict(option.motion_actions)
   while len(history)<limit and BASE.observation_record(obs)["levels_completed"]<1:
    current_grid=BASE.observation_grid(obs);wanted=ROUTE.desired_delta(option,current_grid);candidates=[mapping[wanted]] if wanted in mapping else [a for a in legal if a not in mapping.values()];moved=False
    for action in candidates:
     before_anchor=ROUTE.controlled_anchor(option,current_grid);after_record=act(action,{},"conditional-route")
     if after_record["levels_completed"]>=1:moved=True;break
     after_grid=BASE.observation_grid(obs);after_anchor=ROUTE.controlled_anchor(option,after_grid)
     if after_anchor==before_anchor:continue
     mapping[(after_anchor[0]-before_anchor[0],after_anchor[1]-before_anchor[1])]=action;moved=True;break
    if not moved:break
  elif selected.capability=="interactive:symbolic-transformation":
   option=selected.execution;state=REGISTRY.symbolic.SymbolicExecutionState()
   while len(history)<limit and BASE.observation_record(obs)["levels_completed"]<1:
    before_grid=BASE.observation_grid(obs);command=REGISTRY.symbolic.decide(option,state,before_grid)
    if command is None:break
    after_record=act(command.opaque_action,{},command.role);after_grid=BASE.observation_grid(obs)
    state=REGISTRY.symbolic.observe(option,state,command,before_grid,after_grid,transition_id="transition:"+after_record["digest"][:20])
  final=BASE.observation_record(obs)
 finally:arcade.close_scorecard()
 replay_arcade,replay_env=BASE.open_environment(ROOT/"environment_files",root/"replay",game)
 try:
  replay=replay_env.observation_space or replay_env.reset();exact=True
  for row in history:replay=BASE.execute_action(replay_env,game,row["action"],row["data"],"exact-replay");exact=exact and BASE.observation_record(replay)["digest"]==row["after"]["digest"]
 finally:replay_arcade.close_scorecard()
 return {"game":game,"selected_capability":selected.capability,"goal_ast":selected.goal_ast,"initial_support":selected.empirical_support,"calibration_actions":len(legal),"calibration_resets":len(legal)+1,"actions":len(history),"levels_completed":final["levels_completed"],"exact_replay":exact,"action_sequence":[row["action"] for row in history]}
def main():
 parser=argparse.ArgumentParser();parser.add_argument("--game",action="append",dest="games");args=parser.parse_args()
 results=[]
 for game in (tuple(args.games) if args.games else ("ar25","ka59","sp80","re86","tu93")):
  try:results.append(run_game(game))
  except Exception as error:results.append({"game":game,"error":f"{type(error).__name__}: {error}"})
 doc={"protocol":"unified-capability-registry-development-v0","development_only":True,"game_ids_used_only_by_harness":True,"results":results};ART.mkdir(parents=True,exist_ok=True);(ART/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n");print(json.dumps(doc,indent=2));return 0 if all(row.get("levels_completed",0)>=1 and row.get("exact_replay") for row in results) else 1
if __name__=="__main__":raise SystemExit(main())
