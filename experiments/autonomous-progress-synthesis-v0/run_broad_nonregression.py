"""Consumed-development check that the empty option layer is action-identical."""
from __future__ import annotations
import importlib.util,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
V164=pathlib.Path("/home/pauloabelha/reflector-v164-pivot-goal")
sys.path.insert(0,str(HERE));sys.path.insert(0,str(V164))
from broad_policy_bridge import SharedBroadPolicy
from reflector import MindConfig,Observation,SymbolicPolicy

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

BASE=load("broad_nonregression_environment",ROOT/"experiments/prior-accelerated-relational-transfer-v0/experiment.py")
CANDIDATE=json.loads((V164/"candidates/v164-runtime-grounded-pivot-goal-400.json").read_text())

def symbolic(obs):
 state=getattr(obs.state,"value",str(obs.state))
 return Observation.create(state=state,available_actions=[int(getattr(x,"value",x)) for x in obs.available_actions],frame=BASE.observation_grid(obs),levels_completed=int(obs.levels_completed))

def run(game,wrapped):
 policy=SymbolicPolicy(MindConfig.from_dict(CANDIDATE["config"]));controller=SharedBroadPolicy(policy) if wrapped else policy
 root=HERE/"artifacts/broad-nonregression"/("wrapped" if wrapped else "direct")
 arcade,env=BASE.open_environment(ROOT/"environment_files",root,game);obs=env.observation_space or env.reset();rows=[]
 try:
  while int(obs.levels_completed)<1 and len(rows)<64:
   before=BASE.observation_record(obs);decision=controller.choose_action(symbolic(obs));data=dict(decision.data if wrapped else decision.data_dict());action=int(decision.action_id)
   obs=BASE.execute_action(env,game,action,data,"broad-nonregression");rows.append((action,data,before["digest"],BASE.observation_record(obs)["digest"]))
  policy.observe(symbolic(obs))
  return {"actions":rows,"levels_completed":int(obs.levels_completed),"final_digest":BASE.observation_record(obs)["digest"],"workspace_event_count":len(controller.events) if wrapped else None}
 finally:arcade.close_scorecard()

def main():
 game="cd82";direct=run(game,False);wrapped=run(game,True);same=direct["actions"]==wrapped["actions"] and direct["final_digest"]==wrapped["final_digest"] and direct["levels_completed"]==wrapped["levels_completed"]
 result={"protocol":"broad-policy-empty-layer-nonregression-v0","development_only":True,"game":game,"same":same,"direct":direct,"wrapped":wrapped}
 path=HERE/"artifacts/broad-nonregression/RESULT.json";path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");print(json.dumps({"same":same,"actions":len(direct["actions"]),"levels_completed":direct["levels_completed"],"workspace_events":wrapped["workspace_event_count"]}));return 0 if same and direct["levels_completed"]>=1 else 1

if __name__=="__main__":raise SystemExit(main())
