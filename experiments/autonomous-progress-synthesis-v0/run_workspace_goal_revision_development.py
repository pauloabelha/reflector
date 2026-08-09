"""Ask live Qwen to revise the consumed ls20 proxy from exact search feedback."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = HERE / "artifacts" / "workspace-goal-revision-development-v1"
PRIOR = ROOT / "experiments/progress-goal-live-qwen-v7/artifacts/fresh-1"
ADAPTIVE = HERE / "artifacts/adaptive-workspace-goal-search-development/RESULT.json"

sys.path.insert(0, str(HERE))
import workspace_goal_revision as REVISION


def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec is not None and spec.loader is not None
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module


LIVE = load("workspace_goal_revision_live_v7", ROOT / "experiments/progress-goal-live-qwen-v7/live.py").RUNNER


def main() -> int:
    prior_request=json.loads((PRIOR/"request.json").read_text(encoding="utf-8"))
    prior_result=json.loads((PRIOR/"RESULT.json").read_text(encoding="utf-8"));prior_goal=prior_result["compilation"]["goal"]
    adaptive=json.loads(ADAPTIVE.read_text(encoding="utf-8"));record=adaptive["results"][1]["goal_attention_records"][0]
    text=prior_request["messages"][0]["content"][0]["text"]
    workspace=json.loads(text.split("EPISTEMIC_WORKSPACE\n",1)[1])
    request=REVISION.build_revision_payload(prior_request,prior_goal,record)
    LIVE.atomic_json(ARTIFACTS/"request.json",request)
    endpoint=json.loads((ROOT/"experiments/progress-goal-live-qwen-v7/config.json").read_text(encoding="utf-8"))["endpoint"]
    response=LIVE.post_completion(endpoint,request);LIVE.atomic_json(ARTIFACTS/"response.json",response)
    compilation=REVISION.compile_revision(response,workspace,prior_goal,LIVE.GP.compile_response)
    LIVE.atomic_json(ARTIFACTS/"compilation.json",compilation)
    result={"protocol":"workspace-goal-evidence-revision-development-v0","development_only":True,"consumed_game":"ls20","prior_semantics":json.loads(REVISION.semantic_signature(prior_goal)),"feedback":record,"compilation":compilation,"usage":response.get("usage",{}),"latency_seconds":response.get("latency_seconds")}
    LIVE.atomic_json(ARTIFACTS/"RESULT.json",result);print(json.dumps(result,sort_keys=True));return 0 if compilation.get("accepted") else 1


if __name__=="__main__":raise SystemExit(main())
