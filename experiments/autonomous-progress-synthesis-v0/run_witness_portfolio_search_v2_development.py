"""v2 portfolio: preserve long visually silent causal runs."""
from __future__ import annotations
import json
import run_witness_portfolio_search_development as BASE

ARTIFACTS=BASE.BASE.HERE/"artifacts/witness-portfolio-search-v2-development"


def main():
 BASE.ARTIFACTS=ARTIFACTS;BASE.HISTORY_MODE="run_length_suffix"
 rows=[BASE.run("causal_search_only"),BASE.run("shared_witness_portfolio")]
 doc={"protocol":"shared-witness-portfolio-search-development-v2","development_only":True,"consumed_game":BASE.BASE.GAME,"repair_after_v1":"run-length causal signature preserves long visually silent progress","treatment":"all exact witnesses live; prior Qwen selection changes attention only","frozen_bounds":{"total_action_budget":BASE.BASE.TOTAL_BUDGET,"calibration":BASE.BASE.CALIBRATION_BUDGET,"max_depth":BASE.BASE.MAX_DEPTH,"max_states":BASE.BASE.MAX_STATES,"history_order_runs":BASE.BASE.HISTORY_ORDER,"history_mode":"run_length_suffix","plateau_patience":12,"qwen_attention_boost":50},"results":rows}
 ARTIFACTS.mkdir(parents=True,exist_ok=True);(ARTIFACTS/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(doc,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
