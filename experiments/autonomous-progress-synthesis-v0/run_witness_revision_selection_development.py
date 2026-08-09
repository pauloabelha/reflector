"""Retire a tested proxy and require live Qwen to select another exact witness."""
from __future__ import annotations
import importlib.util,json
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];ARTIFACTS=HERE/"artifacts/witness-revision-selection-development"
PRIOR=HERE/"artifacts/witness-goal-search-development/RESULT.json";GAME="ls20"
sys.path.insert(0,str(HERE));import witness_goal_protocol as WITNESS


def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);assert spec is not None and spec.loader is not None
 module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


LIVE=load("witness_revision_live_v7",ROOT/"experiments/progress-goal-live-qwen-v7/live.py").RUNNER
CONFIG=json.loads((ROOT/"experiments/progress-goal-live-qwen-v7/config.json").read_text(encoding="utf-8"))


def main():
 prior=json.loads(PRIOR.read_text(encoding="utf-8"))["results"][1];retired=prior["selection"]["witness_id"];record=prior["goal_attention_records"][0]
 arcade,environment=LIVE.LAB.BASE.BASE.open_environment(ROOT/"environment_files",ARTIFACTS/"recordings",GAME);LIVE.ARTIFACTS=ARTIFACTS/"calibration"
 try:
  observation=environment.observation_space or environment.reset();legal=LIVE.LAB.BASE.BASE.simple_legal_actions(environment,observation)
  calibrated=LIVE.generic_calibration(environment,observation,GAME,legal);grid=LIVE.LAB.BASE.BASE.observation_grid(calibrated["observation"])
  workspace=LIVE.GP.build_workspace(entities=calibrated["entities"],transitions=calibrated["transition_rows"],frame={"height":len(grid),"width":len(grid[0])})
  witnesses=WITNESS.enumerate_witnesses(workspace,grid)
  feedback={"retired_witness_id":retired,"status":record["status"],"known_evaluations":record["known_evaluations"],"best_value":record["best_value"],"empirical_support":record["empirical_support"],"rule":"retirement changes attention; it is not support for another witness"}
  request=WITNESS.request_payload(workspace,witnesses,CONFIG,LIVE.LAB.BASE.grid_data_url(grid),retired_ids=[retired],feedback=feedback);LIVE.atomic_json(ARTIFACTS/"request.json",request)
  response=LIVE.post_completion(CONFIG["endpoint"],request);LIVE.atomic_json(ARTIFACTS/"response.json",response)
  compilation=WITNESS.compile_selection(response,witnesses,retired_ids=[retired]);public={key:value for key,value in compilation.items() if key!="compiled"};LIVE.atomic_json(ARTIFACTS/"compilation.json",public)
 finally:arcade.close_scorecard()
 result={"protocol":"retired-witness-reselection-development-v0","development_only":True,"consumed_game":GAME,"retired_witness_id":retired,"feedback":feedback,"live_witness_count":len(WITNESS.witness_projection(witnesses,retired_ids=[retired])),"compilation":public,"usage":response.get("usage",{})}
 LIVE.atomic_json(ARTIFACTS/"RESULT.json",result);print(json.dumps(result,sort_keys=True));return 0 if compilation.get("accepted") else 1


if __name__=="__main__":raise SystemExit(main())
