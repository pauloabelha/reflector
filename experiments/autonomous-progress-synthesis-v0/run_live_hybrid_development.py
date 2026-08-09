"""Consumed-development run of v164 plus live online workspace options."""
from __future__ import annotations
import argparse,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import compositional_dsl as DSL
import online_compositional_options as ONLINE
from broad_policy_bridge import SharedBroadPolicy
from transactional_broad_policy import TransactionalBroadPolicy
import run_broad_nonregression as R
from reflector import MindConfig,SymbolicPolicy

ART=HERE/"artifacts/live-hybrid-development"

def hybrid(game,limit=64):
 policy=SymbolicPolicy(MindConfig.from_dict(R.CANDIDATE["config"]));tx=TransactionalBroadPolicy(policy);controller=SharedBroadPolicy(tx,stagnation_threshold=24,max_option_probes=2,max_divergent_probes=2)
 arcade,env=R.BASE.open_environment(R.ROOT/"environment_files",ART/game/"factual",game);obs=env.observation_space or env.reset();initial=R.BASE.observation_grid(obs);legal=R.BASE.simple_legal_actions(env,obs)
 try:candidates=DSL.propose(initial)
 except Exception:candidates=()
 inducer=ONLINE.OnlineCompositionalOptionInducer(initial,legal_actions=legal,candidates=candidates);history=[]
 try:
  while int(obs.levels_completed)<1 and len(history)<limit:
   before=R.BASE.observation_record(obs);decision=controller.choose_from_inducer(R.symbolic(obs),inducer);obs=R.BASE.execute_action(env,game,decision.action_id,dict(decision.data),f"hybrid-{decision.mode}");after=R.BASE.observation_record(obs);transition_id=f"transition:{len(history)}:{after['digest'][:16]}"
   verdict=controller.observe_inducer_transition(inducer,decision,after=R.BASE.observation_grid(obs),transition_id=transition_id,direct=True)
   history.append({"action":decision.action_id,"data":dict(decision.data),"mode":decision.mode,"candidate_id":decision.candidate_id,"fallback_action":decision.fallback_action_id,"verdict":verdict,"before":before["digest"],"after":after["digest"]})
  tx.observe(R.symbolic(obs));final=R.BASE.observation_record(obs)
 finally:arcade.close_scorecard()
 replay_arcade,replay_env=R.BASE.open_environment(R.ROOT/"environment_files",ART/game/"replay",game);replay=replay_env.observation_space or replay_env.reset();exact=True
 try:
  for row in history:replay=R.BASE.execute_action(replay_env,game,row["action"],row["data"],"hybrid-replay");exact=exact and R.BASE.observation_record(replay)["digest"]==row["after"]
 finally:replay_arcade.close_scorecard()
 return {"actions":len(history),"levels_completed":final["levels_completed"],"final_digest":final["digest"],"exact_replay":exact,"mode_counts":{mode:sum(row["mode"]==mode for row in history) for mode in ("fallback","passive_probe","probe","control")},"changed_actions":sum(row["action"]!=row["fallback_action"] for row in history),"leases":controller.workspace_document()["leases"],"trace":history}

def main():
 parser=argparse.ArgumentParser();parser.add_argument("--game",required=True);args=parser.parse_args()
 game=args.game;baseline=R.run(game,False);treatment=hybrid(game)
 row={"game":game,"baseline":{"actions":len(baseline["actions"]),"levels_completed":baseline["levels_completed"],"final_digest":baseline["final_digest"]},"hybrid":treatment}
 doc={"protocol":"broad-live-hybrid-development-v1","development_only":True,"policy":{"stagnation_threshold":24,"max_divergent_probes":2,"passive_probe":"same-action prospective evidence"},"results":[row]}
 target=ART/game/"RESULT.json";target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n")
 print(json.dumps({"game":game,"baseline_levels":row["baseline"]["levels_completed"],"hybrid_levels":treatment["levels_completed"],"baseline_actions":row["baseline"]["actions"],"hybrid_actions":treatment["actions"],"modes":treatment["mode_counts"],"changed_actions":treatment["changed_actions"],"exact":treatment["exact_replay"]}));return 0 if treatment["exact_replay"] else 1

if __name__=="__main__":raise SystemExit(main())
