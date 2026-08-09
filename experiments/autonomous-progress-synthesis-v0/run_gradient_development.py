"""Development proof for source-blind compositional macro control."""
from __future__ import annotations
import importlib.util,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent;ROOT=HERE.parents[1];ART=HERE/"artifacts"/"gradient-development";sys.path.insert(0,str(HERE))
import compositional_dsl as DSL
import gradient_executor as GRADIENT

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module
BASE=load("gradient_development_base",ROOT/"experiments/prior-accelerated-relational-transfer-v0/experiment.py")

def run_game(game,*,artifact_root=ART,action_budget=64):
    root=pathlib.Path(artifact_root)/game;arcade,env=BASE.open_environment(ROOT/"environment_files",root/"recordings",game);history=[]
    try:
        obs=env.observation_space or env.reset();initial=BASE.observation_record(obs);grid=BASE.observation_grid(obs);candidates=DSL.propose(grid);simple=BASE.simple_legal_actions(env,obs);models={}
        for action in simple:
            before=env.reset();before_grid=BASE.observation_grid(before);after=BASE.execute_action(env,game,action,{},"opaque-motion-calibration");after_grid=BASE.observation_grid(after)
            for candidate in candidates:
                for variable,delta in GRADIENT.moved_variables(candidate,before_grid,after_grid).items():models.setdefault((candidate.candidate_id,candidate.binding_id,variable),{})[delta]=action
        plans=[]
        for candidate in candidates:
            for (candidate_id,binding_id,variable),motion in models.items():
                if (candidate_id,binding_id)!=(candidate.candidate_id,candidate.binding_id):continue
                try:
                    plan=GRADIENT.plan(candidate,grid,movable_variable=variable,motion_actions=motion,max_steps=min(24,action_budget))
                    plans.append((-candidate.attention,plan.predicted_value,-(plan.start_value-plan.predicted_value),len(plan.opaque_actions),candidate.candidate_id,candidate.binding_id,variable,candidate,plan))
                except Exception:continue
        if not plans:raise RuntimeError("no compositional potential has a grounded improving macro")
        *_rank,variable,candidate,plan=min(plans);obs=env.reset()
        for action in plan.opaque_actions[:action_budget]:
            before=BASE.observation_record(obs);obs=BASE.execute_action(env,game,action,{},"compositional-progress-option");after=BASE.observation_record(obs);history.append({"action":action,"before":before,"after":after})
            if after["levels_completed"]>=1:break
        final=BASE.observation_record(obs)
    finally:arcade.close_scorecard()
    replay_arcade,replay_env=BASE.open_environment(ROOT/"environment_files",root/"replay",game)
    try:
        replay=replay_env.observation_space or replay_env.reset();exact=True
        for row in history:
            replay=BASE.execute_action(replay_env,game,row["action"],{},"exact-replay");exact=exact and BASE.observation_record(replay)["digest"]==row["after"]["digest"]
    finally:replay_arcade.close_scorecard()
    return {"game":game,"initial_digest":initial["digest"],"selected_ast":candidate.ast,"candidate_id":candidate.candidate_id,"binding_id":candidate.binding_id,"movable_variable":variable,"initial_support":candidate.support,"attention":candidate.attention,"predicted_before":plan.start_value,"predicted_after":plan.predicted_value,"predicted_translation":plan.translation,"opaque_actions":[row["action"] for row in history],"factual_actions":len(history),"levels_completed":final["levels_completed"],"exact_replay":exact,"final_digest":final["digest"]}

def main():
    result=run_game("ar25");doc={"protocol":"compositional-gradient-development-v0","source_blind_runtime":True,"development_only":True,"result":result};ART.mkdir(parents=True,exist_ok=True);(ART/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n");print(json.dumps(doc,indent=2));return 0 if result["levels_completed"]>=1 and result["exact_replay"] else 1
if __name__=="__main__":raise SystemExit(main())
