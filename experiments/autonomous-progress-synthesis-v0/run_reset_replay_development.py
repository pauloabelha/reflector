"""Frozen public-development breadth test for opaque reset/replay search."""
from __future__ import annotations
import argparse,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import reset_replay_explorer as SEARCH
import run_broad_nonregression as R

ART=HERE/"artifacts/reset-replay-development"


def causal_momentum(_observation,path,source_key,target_key):
    run=1
    while run<len(path) and path[-run-1]==path[-1]:run+=1
    changed=source_key!=target_key
    # Productive repeated interventions are coherent experiments.  An
    # unchanged transition loses priority immediately; depth is only a final
    # tie-breaker and never masquerades as evidence of progress.
    return (0 if changed else 1,-run if changed else 0,len(path),path)


class ArcadeWorld:
    def __init__(self,env,game):self.env=env;self.game=game;self.obs=None
    def reset(self):self.obs=self.env.reset();return self.obs
    def step(self,opaque_action):
        self.obs=R.BASE.execute_action(self.env,self.game,opaque_action,{},"bounded-reset-replay-search");return self.obs
    def key(self,observation):return R.BASE.observation_record(observation)["digest"]
    def legal_actions(self,observation):return R.BASE.simple_legal_actions(self.env,observation)
    def completed(self,observation):return int(observation.levels_completed)>=1
    def terminal(self,observation):return str(observation.state).upper().rsplit(".",1)[-1] in {"WIN","GAME_OVER"}


def run(game):
    arcade,env=R.BASE.open_environment(R.ROOT/"environment_files",ART/game/"search",game)
    try:result=SEARCH.search(ArcadeWorld(env,game),action_budget=400,max_depth=12,max_states=256,history_order=4,priority=causal_momentum)
    finally:arcade.close_scorecard()
    exact=False;final_digest=None
    if result.solved:
        replay_arcade,replay_env=R.BASE.open_environment(R.ROOT/"environment_files",ART/game/"solution-replay",game)
        try:
            obs=replay_env.observation_space or replay_env.reset()
            for action in result.solution:obs=R.BASE.execute_action(replay_env,game,action,{},"solution-replay")
            exact=int(obs.levels_completed)>=1;final_digest=R.BASE.observation_record(obs)["digest"]
        finally:replay_arcade.close_scorecard()
    return {"game":game,"solved":result.solved,"solution":list(result.solution),"environment_actions":result.environment_actions,"resets":result.reset_count,"discovered_states":result.discovered_states,"maximum_depth":result.maximum_depth_reached,"stop_reason":result.stop_reason,"exact_solution_replay":exact,"final_digest":final_digest,"edge_count":len(result.edges)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument("--game",action="append",required=True,dest="games");args=parser.parse_args()
    rows=[]
    for game in args.games:
        try:rows.append(run(game))
        except Exception as error:rows.append({"game":game,"error":f"{type(error).__name__}: {error}"})
    doc={"protocol":"opaque-reset-replay-development-v2","development_only":True,"frozen_bounds":{"action_budget":400,"max_depth":12,"max_states":256,"causal_history_order":4,"priority":"productive-causal-momentum-v0"},"results":rows}
    ART.mkdir(parents=True,exist_ok=True);(ART/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n");print(json.dumps(doc));return 0


if __name__=="__main__":raise SystemExit(main())
