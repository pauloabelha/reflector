from __future__ import annotations
import importlib.util, json, pathlib, sys

HERE=pathlib.Path(__file__).resolve().parent; ROOT=HERE.parents[1]; ART=HERE/"artifacts"/"fresh-1"
def load(n,p):
 s=importlib.util.spec_from_file_location(n,p); assert s and s.loader; m=importlib.util.module_from_spec(s);sys.modules[n]=m;s.loader.exec_module(m);return m
BASE=load("symbolic_live_base",HERE.parent/"progress-goal-live-qwen-v1"/"live.py")
TRACKER=load("symbolic_live_tracker",HERE.parent/"progress-goal-generic-calibration-v1"/"tracker.py")
SYMBOL=load("symbolic_live_kernel",HERE.parent/"progress-drive-symbolic-v0"/"symbolic_progress.py")
PROTO=load("symbolic_live_protocol",HERE/"protocol.py")
BASE.ARTIFACTS=ART; BASE.TRACKER=TRACKER

def main():
 c=json.loads((HERE/"config.json").read_text()); game=c["development_game"]
 arcade,env=BASE.LAB.BASE.BASE.open_environment(ROOT/"environment_files",ART/"recordings",game); history=[]
 try:
  obs=env.observation_space or env.reset(); initial=BASE.LAB.BASE.BASE.observation_record(obs); initial_grid=BASE.LAB.BASE.BASE.observation_grid(obs)
  legal=BASE.LAB.BASE.BASE.simple_legal_actions(env,obs); figures=BASE.LAB.BASE.V0.V0.select_figures(initial_grid); panels=BASE.entity_rows(figures)
  calibrated=BASE.generic_calibration(env,obs,game,legal); obs=calibrated["observation"];history=calibrated["history"]
  first_after=calibrated["grid_successors"][0]; changed=[(x,y) for y in range(len(initial_grid)) for x in range(len(initial_grid[0])) if initial_grid[y][x]!=first_after[y][x]]
  mutation_origin=(min(x for x,y in changed),min(y for x,y in changed))
  task=SYMBOL.infer_task(initial_grid,panels,mutation_origin=mutation_origin); workspace=SYMBOL.workspace_document(task)
  BASE.atomic_json(ART/"workspace.json",workspace); req=PROTO.request_payload(workspace,c,BASE.LAB.BASE.grid_data_url(initial_grid));BASE.atomic_json(ART/"request.json",req)
  response=BASE.post_completion(c["endpoint"],req);BASE.atomic_json(ART/"response.json",response)
  desired=SYMBOL.compile_desired(response["parsed"],task)
  if desired!=task.desired: raise SYMBOL.SymbolicProgressError("Qwen output contradicts demonstrated mapping")
  BASE.atomic_json(ART/"compilation.json",{"accepted":True,"support":0,"desired_outputs":desired,"rule":response["parsed"]["rule"]})
  mutation_action=int(legal[1]); next_slot_action=int(legal[3])
  for index,(origin,target) in enumerate(zip(task.output_origins,desired)):
   attempts=0
   while SYMBOL.glyph_signature(BASE.LAB.BASE.BASE.observation_grid(obs),origin)!=target:
    if attempts>=7 or len(history)>=int(c["action_budget"]): raise RuntimeError("cyclic edit failed to reach grounded token")
    before=BASE.LAB.BASE.BASE.observation_record(obs);obs=BASE.LAB.BASE.execute_action(env,game,mutation_action,{},"grounded-symbol-edit");after=BASE.LAB.BASE.BASE.observation_record(obs)
    history.append({"action":mutation_action,"before":before,"after":after,"phase":"symbol-edit","slot":index});attempts+=1
    if int(after["levels_completed"])>=1:break
   if int(BASE.LAB.BASE.BASE.observation_record(obs)["levels_completed"])>=1:break
   if index+1<len(desired):
    before=BASE.LAB.BASE.BASE.observation_record(obs);obs=BASE.LAB.BASE.execute_action(env,game,next_slot_action,{},"grounded-slot-select");after=BASE.LAB.BASE.BASE.observation_record(obs)
    history.append({"action":next_slot_action,"before":before,"after":after,"phase":"slot-select","slot":index+1})
   BASE.atomic_json(ART/"checkpoint.json",{"history":history})
  final=BASE.LAB.BASE.BASE.observation_record(obs)
 finally: arcade.close_scorecard()
 replay=BASE.exact_replay(history,game); passed=int(final["levels_completed"])>=1 and len(history)<=int(c["completion_action_gate"]) and replay
 result={"verdict":"PASS" if passed else "FAIL","development_only":True,"initial_digest":initial["digest"],"actions":len(history),"action_sequence":[r["action"] for r in history],"levels_completed":int(final["levels_completed"]),"final_digest":final["digest"],"exact_replay":replay,"qwen_support":0,"qwen_rule":response["parsed"]["rule"],"qwen_desired_outputs":desired,"grounded_desired_outputs":task.desired,"qwen_usage":response["usage"]}
 BASE.atomic_json(ART/"RESULT.json",result);return 0 if passed else 1
if __name__=="__main__":raise SystemExit(main())
