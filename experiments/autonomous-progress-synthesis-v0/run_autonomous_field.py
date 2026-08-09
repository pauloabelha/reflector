"""Development-only live test of the solver-free progress-field fallback."""
from __future__ import annotations
import importlib.util,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"autonomous-field"
sys.path.insert(0,str(HERE))
import autonomous_agent as AGENT

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
BASE=load("autonomous_field_base",ROOT/"experiments/prior-accelerated-relational-transfer-v0/experiment.py")

def terminal(record):return str(record["state"]).upper().rsplit(".",1)[-1] in {"GAME_OVER","WIN"} or record["levels_completed"]>=1

def run_game(game,limit=64):
    root=ART/game;arcade,env=BASE.open_environment(ROOT/"environment_files",root/"recordings",game);history=[]
    try:
        obs=env.observation_space or env.reset();initial=BASE.observation_record(obs);agent=AGENT.AutonomousProgressAgent(BASE.observation_grid(obs))
        for index in range(limit):
            legal=BASE.simple_legal_actions(env,obs)
            if not legal:break
            decision=agent.decide(legal);before=BASE.observation_record(obs)
            obs=BASE.execute_action(env,game,decision.opaque_action,{},"autonomous-progress-field");after=BASE.observation_record(obs)
            adjudication=agent.observe(decision,BASE.observation_grid(obs),transition_id=f"transition:{index}:"+after["digest"][:16])
            history.append({"action":decision.opaque_action,"mode":decision.mode,"candidate_id":decision.candidate_id,"before":before,"after":after,"adjudication":adjudication.__dict__})
            if terminal(after):break
        final=BASE.observation_record(obs)
    finally:arcade.close_scorecard()
    replay_arcade,replay_env=BASE.open_environment(ROOT/"environment_files",root/"replay",game)
    try:
        replay=replay_env.observation_space or replay_env.reset();exact=True
        for row in history:
            replay=BASE.execute_action(replay_env,game,row["action"],{},"exact-replay")
            exact=exact and BASE.observation_record(replay)["digest"]==row["after"]["digest"]
    finally:replay_arcade.close_scorecard()
    return {"game":game,"initial_digest":initial["digest"],"levels_completed":final["levels_completed"],"actions":len(history),"exact_replay":exact,"mode_counts":{mode:sum(row["mode"]==mode for row in history) for mode in ("probe","control","fallback")},"supporting_transitions":sum(row["adjudication"]["support_delta"]>0 for row in history),"trace":[{"opaque_action":row["action"],"mode":row["mode"],"candidate_id":row["candidate_id"],"before":row["adjudication"]["before"],"after":row["adjudication"]["after"],"direct":row["adjudication"]["direct"],"support_delta":row["adjudication"]["support_delta"]} for row in history]}

def main():
    results=[]
    for game in ("sp80","re86"):
        try:results.append(run_game(game))
        except Exception as error:results.append({"game":game,"error":f"{type(error).__name__}: {error}"})
    doc={"protocol":"solver-free-autonomous-progress-field-dev-v0","development_only":True,"results":results};ART.mkdir(parents=True,exist_ok=True);(ART/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n");print(json.dumps(doc,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
