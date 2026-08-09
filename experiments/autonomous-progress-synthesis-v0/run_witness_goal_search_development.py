"""Consumed-game diagnostic for exact R2 witnesses selected by live Qwen."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];ARTIFACTS=HERE/"artifacts/witness-goal-search-development"
GAME="ls20";TOTAL_BUDGET=400;CALIBRATION_BUDGET=4;SEARCH_BUDGET=396;MAX_DEPTH=16;MAX_STATES=256;HISTORY_ORDER=4
sys.path.insert(0,str(HERE))
import reset_replay_explorer as SEARCH
import run_broad_nonregression as R
import witness_goal_protocol as WITNESS
import workspace_potential_search as POTENTIAL


def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


LIVE=load("witness_goal_search_live_v7",ROOT/"experiments/progress-goal-live-qwen-v7/live.py").RUNNER
CONFIG=json.loads((ROOT/"experiments/progress-goal-live-qwen-v7/config.json").read_text(encoding="utf-8"))


class ArcadeWorld:
    def __init__(self,environment):self.environment=environment;self.observation=None
    def reset(self):self.observation=self.environment.reset();return self.observation
    def step(self,opaque_action):self.observation=R.BASE.execute_action(self.environment,GAME,opaque_action,{},"witness-goal-search");return self.observation
    def key(self,observation):return R.BASE.observation_record(observation)["digest"]
    def legal_actions(self,observation):return R.BASE.simple_legal_actions(self.environment,observation)
    def completed(self,observation):return int(observation.levels_completed)>=1
    def terminal(self,observation):return str(observation.state).upper().rsplit(".",1)[-1] in {"WIN","GAME_OVER"}


def exact_replay(solution):
    arcade,environment=R.BASE.open_environment(ROOT/"environment_files",ARTIFACTS/"solution-replay",GAME)
    try:
        observation=environment.observation_space or environment.reset()
        for action in solution:observation=R.BASE.execute_action(environment,GAME,action,{},"witness-solution-replay")
        return int(observation.levels_completed)>=1
    finally:arcade.close_scorecard()


def run(arm):
    arm_root=ARTIFACTS/arm;arcade,environment=R.BASE.open_environment(ROOT/"environment_files",arm_root/"search",GAME);LIVE.ARTIFACTS=arm_root/"calibration"
    response=compilation=None;policy=None
    try:
        observation=environment.observation_space or environment.reset();legal=R.BASE.simple_legal_actions(environment,observation)
        if len(legal)!=CALIBRATION_BUDGET:raise RuntimeError("frozen calibration budget mismatch")
        calibrated=LIVE.generic_calibration(environment,observation,GAME,legal);grid=R.BASE.observation_grid(calibrated["observation"])
        workspace=LIVE.GP.build_workspace(entities=calibrated["entities"],transitions=calibrated["transition_rows"],frame={"height":len(grid),"width":len(grid[0])})
        witnesses=WITNESS.enumerate_witnesses(workspace,grid)
        LIVE.atomic_json(arm_root/"witnesses.json",{"protocol":WITNESS.PROTOCOL,"witnesses":WITNESS.witness_projection(witnesses)})
        priority=None
        if arm=="shared_witness_attention":
            request=WITNESS.request_payload(workspace,witnesses,CONFIG,LIVE.LAB.BASE.grid_data_url(grid));LIVE.atomic_json(arm_root/"request.json",request)
            response=LIVE.post_completion(CONFIG["endpoint"],request);LIVE.atomic_json(arm_root/"response.json",response)
            compilation=WITNESS.compile_selection(response,witnesses)
            public={key:value for key,value in compilation.items() if key!="compiled"};LIVE.atomic_json(arm_root/"compilation.json",public)
            if compilation.get("accepted") and compilation.get("compiled") is not None:
                policy=POTENTIAL.AdaptivePotentialPolicy((compilation["compiled"],),projection=R.BASE.observation_grid,plateau_patience=12);priority=policy
        result=SEARCH.search(ArcadeWorld(environment),action_budget=SEARCH_BUDGET,max_depth=MAX_DEPTH,max_states=MAX_STATES,history_order=HISTORY_ORDER,priority=priority)
    finally:arcade.close_scorecard()
    return {"arm":arm,"solved":result.solved,"solution":list(result.solution),"exact_solution_replay":exact_replay(result.solution) if result.solved else False,"calibration_actions":CALIBRATION_BUDGET,"search_actions":result.environment_actions,"total_environment_actions":CALIBRATION_BUDGET+result.environment_actions,"resets":result.reset_count,"states":result.discovered_states,"maximum_depth":result.maximum_depth_reached,"stop_reason":result.stop_reason,"witness_count":len(witnesses),"selection":None if compilation is None else {key:value for key,value in compilation.items() if key not in {"compiled","goal"}},"selected_goal":None if compilation is None else compilation.get("goal"),"goal_attention_records":[] if policy is None else [{name:getattr(record,name) for name in record.__slots__} for record in policy.records()],"qwen_usage":None if response is None else response.get("usage")}


def main():
    rows=[run("causal_search_only"),run("shared_witness_attention")]
    document={"protocol":"live-witness-goal-search-development-v0","development_only":True,"consumed_game":GAME,"frozen_bounds":{"total_action_budget":TOTAL_BUDGET,"calibration":CALIBRATION_BUDGET,"max_depth":MAX_DEPTH,"max_states":MAX_STATES,"history_order":HISTORY_ORDER,"plateau_patience":12},"results":rows}
    ARTIFACTS.mkdir(parents=True,exist_ok=True);(ARTIFACTS/"RESULT.json").write_text(json.dumps(document,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(document,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
