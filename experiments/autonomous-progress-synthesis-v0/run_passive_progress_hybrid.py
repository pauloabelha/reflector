"""Consumed-development paired run of broad R2 plus passive shared evidence."""
from __future__ import annotations
import argparse,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import autonomous_agent as AGENT
import passive_progress_hybrid as PASSIVE
import run_broad_nonregression as R
from broad_policy_bridge import HybridDecision as BridgeDecision
from transactional_broad_policy import TransactionalBroadPolicy
from reflector import MindConfig,SymbolicPolicy

ART=HERE/"artifacts/passive-progress-hybrid-development"


def hybrid(game,limit=64):
    tx=TransactionalBroadPolicy(SymbolicPolicy(MindConfig.from_dict(R.CANDIDATE["config"])))
    arcade,env=R.BASE.open_environment(R.ROOT/"environment_files",ART/game/"factual",game)
    obs=env.observation_space or env.reset();agent=AGENT.AutonomousProgressAgent(R.BASE.observation_grid(obs));controller=PASSIVE.PassiveProgressHybrid(tx,agent);history=[]
    try:
        while int(obs.levels_completed)<1 and len(history)<limit:
            symbolic=R.symbolic(obs);legal=R.BASE.simple_legal_actions(env,obs)
            if not legal:break
            decision=controller.decide(symbolic,legal)
            bridge=BridgeDecision(
                decision.action_id,decision.data,
                "control" if decision.mode=="supported-progress-control" else "fallback",
                decision.fallback_action_id,decision.fallback_data,
                decision.candidate_id,decision.mode,
            )
            tx.commit_decision(symbolic,bridge)
            before=R.BASE.observation_record(obs);obs=R.BASE.execute_action(env,game,decision.action_id,dict(decision.data),decision.mode);after=R.BASE.observation_record(obs)
            terminal_state=str(after["state"]).upper().rsplit(".",1)[-1] in {"WIN","GAME_OVER"}
            adjudication=None if terminal_state else controller.observe(decision,R.BASE.observation_grid(obs),transition_id=f"transition:{len(history)}:{after['digest'][:16]}")
            history.append({"action":decision.action_id,"data":dict(decision.data),"fallback_action":decision.fallback_action_id,"mode":decision.mode,"candidate_id":decision.candidate_id,"before":before["digest"],"after":after["digest"],"observed_candidates":0 if adjudication is None else adjudication.observed_candidate_count})
        tx.observe(R.symbolic(obs));final=R.BASE.observation_record(obs)
    finally:arcade.close_scorecard()
    replay_arcade,replay_env=R.BASE.open_environment(R.ROOT/"environment_files",ART/game/"replay",game)
    try:
        replay=replay_env.observation_space or replay_env.reset();exact=True
        for row in history:
            replay=R.BASE.execute_action(replay_env,game,row["action"],row["data"],"passive-progress-replay")
            exact=exact and R.BASE.observation_record(replay)["digest"]==row["after"]
    finally:replay_arcade.close_scorecard()
    return {"actions":len(history),"levels_completed":int(final["levels_completed"]),"final_digest":final["digest"],"exact_replay":exact,"changed_actions":sum(row["action"]!=row["fallback_action"] for row in history),"mode_counts":{mode:sum(row["mode"]==mode for row in history) for mode in ("broad-fallback","supported-progress-control")},"multiplexed_observations":sum(row["observed_candidates"] for row in history),"trace":history}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--game",action="append",dest="games",required=True);args=parser.parse_args();rows=[]
    for game in args.games:
        baseline=R.run(game,False)
        try:treatment=hybrid(game);row={"game":game,"baseline":{"actions":len(baseline["actions"]),"levels_completed":baseline["levels_completed"],"final_digest":baseline["final_digest"]},"hybrid":treatment}
        except Exception as error:row={"game":game,"baseline":{"actions":len(baseline["actions"]),"levels_completed":baseline["levels_completed"],"final_digest":baseline["final_digest"]},"error":f"{type(error).__name__}: {error}"}
        rows.append(row);target=ART/game/"RESULT.json";target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(row,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    doc={"protocol":"passive-multiplexed-progress-hybrid-development-v0","development_only":True,"minimum_support":20,"speculative_divergent_probes":0,"results":rows}
    ART.mkdir(parents=True,exist_ok=True);(ART/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(doc,indent=2,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
