"""Consumed-development runner for the deployable online registry protocol."""
from __future__ import annotations
import argparse,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import online_registry_controller as ONLINE
import run_broad_nonregression as BROAD
from reflector import MindConfig,SymbolicPolicy

ART=HERE/"artifacts"/"online-registry-development"


def run(game:str,limit:int=96):
    root=ART/game;arcade,environment=BROAD.BASE.open_environment(BROAD.ROOT/"environment_files",root/"factual",game)
    observation=environment.observation_space or environment.reset();controller=ONLINE.OnlineCapabilityController();policy=None;history=[]
    try:
        while int(observation.levels_completed)<1 and len(history)<limit:
            record=BROAD.BASE.observation_record(observation)
            command=controller.decide(
                BROAD.BASE.observation_grid(observation),
                tuple(int(getattr(row,"value",row)) for row in observation.available_actions),
                state=record["state"],
            )
            if command is None:
                if policy is None:policy=SymbolicPolicy(MindConfig.from_dict(BROAD.CANDIDATE["config"]))
                decision=policy.choose_action(BROAD.symbolic(observation));action=decision.action_id;data=decision.data_dict();reason="broad-fallback"
            else:
                action=command.action_id;data=command.data_dict();reason=command.reason
            before=record;observation=BROAD.BASE.execute_action(environment,game,action,data,reason);after=BROAD.BASE.observation_record(observation)
            history.append({"action":action,"data":data,"reason":reason,"before":before["digest"],"after":after["digest"]})
        final=BROAD.BASE.observation_record(observation)
    finally:arcade.close_scorecard()
    replay_arcade,replay_environment=BROAD.BASE.open_environment(BROAD.ROOT/"environment_files",root/"replay",game);exact=True
    try:
        observation=replay_environment.observation_space or replay_environment.reset()
        for row in history:
            observation=BROAD.BASE.execute_action(replay_environment,game,row["action"],row["data"],"online-registry-replay")
            exact=exact and BROAD.BASE.observation_record(observation)["digest"]==row["after"]
    finally:replay_arcade.close_scorecard()
    result={"protocol":"online-capability-registry-development-v0","development_only":True,"game":game,"actions":len(history),"levels_completed":final["levels_completed"],"exact_replay":exact,"controller":controller.report(),"trace":history}
    target=root/"RESULT.json";target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n");return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--game",required=True);parser.add_argument("--limit",type=int,default=96);args=parser.parse_args()
    result=run(args.game,args.limit);print(json.dumps({k:v for k,v in result.items() if k!="trace"},indent=2,sort_keys=True));return 0 if result["levels_completed"]>=1 and result["exact_replay"] else 1


if __name__=="__main__":raise SystemExit(main())
