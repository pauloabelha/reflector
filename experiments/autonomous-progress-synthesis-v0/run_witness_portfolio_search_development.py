"""Ablate single-witness fixation: keep the whole grounded field live."""
from __future__ import annotations
import json
from pathlib import Path

import run_witness_goal_search_development as BASE

ARTIFACTS=BASE.HERE/"artifacts/witness-portfolio-search-development"
PRIOR=BASE.HERE/"artifacts/witness-goal-search-development/RESULT.json"
HISTORY_MODE="action_suffix"


def run(arm):
 arm_root=ARTIFACTS/arm;arcade,environment=BASE.R.BASE.open_environment(BASE.ROOT/"environment_files",arm_root/"search",BASE.GAME);BASE.LIVE.ARTIFACTS=arm_root/"calibration";policy=None
 try:
  observation=environment.observation_space or environment.reset();legal=BASE.R.BASE.simple_legal_actions(environment,observation)
  calibrated=BASE.LIVE.generic_calibration(environment,observation,BASE.GAME,legal);grid=BASE.R.BASE.observation_grid(calibrated["observation"])
  workspace=BASE.LIVE.GP.build_workspace(entities=calibrated["entities"],transitions=calibrated["transition_rows"],frame={"height":len(grid),"width":len(grid[0])})
  witnesses=BASE.WITNESS.enumerate_witnesses(workspace,grid);priority=None;selected_id=None
  if arm=="shared_witness_portfolio":
   prior=json.loads(PRIOR.read_text(encoding="utf-8"))["results"][1];selected_id=prior["selection"]["witness_id"]
   if selected_id not in {item.witness_id for item in witnesses}:raise RuntimeError("prior Qwen selection is absent from fresh exact witnesses")
   policy=BASE.POTENTIAL.AdaptivePotentialPolicy(tuple(item.compiled for item in witnesses),projection=BASE.R.BASE.observation_grid,plateau_patience=12,reference_values={item.witness_id:item.current_value for item in witnesses},attention_boosts={selected_id:50});priority=policy
  result=BASE.SEARCH.search(BASE.ArcadeWorld(environment),action_budget=BASE.SEARCH_BUDGET,max_depth=BASE.MAX_DEPTH,max_states=BASE.MAX_STATES,history_order=BASE.HISTORY_ORDER,history_mode=HISTORY_MODE,priority=priority)
 finally:arcade.close_scorecard()
 return {"arm":arm,"solved":result.solved,"solution":list(result.solution),"exact_solution_replay":BASE.exact_replay(result.solution) if result.solved else False,"calibration_actions":BASE.CALIBRATION_BUDGET,"search_actions":result.environment_actions,"total_environment_actions":BASE.CALIBRATION_BUDGET+result.environment_actions,"resets":result.reset_count,"states":result.discovered_states,"maximum_depth":result.maximum_depth_reached,"stop_reason":result.stop_reason,"witness_count":len(witnesses),"qwen_attention_boost":selected_id,"goal_attention_records":[] if policy is None else [{name:getattr(record,name) for name in record.__slots__} for record in policy.records()]}


def main():
 rows=[run("causal_search_only"),run("shared_witness_portfolio")]
 doc={"protocol":"shared-witness-portfolio-search-development-v0","development_only":True,"consumed_game":BASE.GAME,"treatment":"all exact witnesses live; prior Qwen selection changes attention only","frozen_bounds":{"total_action_budget":BASE.TOTAL_BUDGET,"calibration":BASE.CALIBRATION_BUDGET,"max_depth":BASE.MAX_DEPTH,"max_states":BASE.MAX_STATES,"history_order":BASE.HISTORY_ORDER,"plateau_patience":12,"qwen_attention_boost":50},"results":rows}
 ARTIFACTS.mkdir(parents=True,exist_ok=True);(ARTIFACTS/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(doc,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
