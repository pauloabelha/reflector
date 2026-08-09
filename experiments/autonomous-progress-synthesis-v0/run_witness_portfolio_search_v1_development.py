"""v1 portfolio: only the attention-winning witness spends patience."""
from __future__ import annotations
import json
import run_witness_portfolio_search_development as BASE

ARTIFACTS=BASE.BASE.HERE/"artifacts/witness-portfolio-search-v1-development"


def main():
 BASE.ARTIFACTS=ARTIFACTS
 rows=[BASE.run("causal_search_only"),BASE.run("shared_witness_portfolio")]
 doc={"protocol":"shared-witness-portfolio-search-development-v1","development_only":True,"consumed_game":BASE.BASE.GAME,"repair_after_v0":"only attention-winning witness spends plateau patience","treatment":"all exact witnesses remain live; prior Qwen selection changes attention only","frozen_bounds":{"total_action_budget":BASE.BASE.TOTAL_BUDGET,"calibration":BASE.BASE.CALIBRATION_BUDGET,"max_depth":BASE.BASE.MAX_DEPTH,"max_states":BASE.BASE.MAX_STATES,"history_order":BASE.BASE.HISTORY_ORDER,"plateau_patience":12,"qwen_attention_boost":50},"results":rows}
 ARTIFACTS.mkdir(parents=True,exist_ok=True);(ARTIFACTS/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n",encoding="utf-8");print(json.dumps(doc,sort_keys=True));return 0


if __name__=="__main__":raise SystemExit(main())
