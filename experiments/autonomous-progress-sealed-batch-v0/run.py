"""Frozen breadth runner; imports one immutable synthesis/control mechanism."""
from __future__ import annotations
import hashlib,importlib.util,json,pathlib,sys

HERE=pathlib.Path(__file__).resolve().parent
ROOT=HERE.parents[1]
CONFIG=json.loads((HERE/"config.json").read_text())
SYNTHESIS_DIR=HERE.parent/"autonomous-progress-synthesis-v0"
if str(SYNTHESIS_DIR) not in sys.path:sys.path.insert(0,str(SYNTHESIS_DIR))

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader
    module=importlib.util.module_from_spec(spec);sys.modules[name]=module;spec.loader.exec_module(module);return module

MATRIX=load("sealed_synthesis_matrix",SYNTHESIS_DIR/"run_development_matrix.py")

def manifest():
    universe=tuple(CONFIG["candidate_universe"]);excluded=set(CONFIG["development_exclusions"])
    expected=tuple(sorted(game for game in universe if game not in excluded))
    targets=tuple(CONFIG["targets"])
    if targets!=expected:raise RuntimeError("sealed targets are not the exact sorted universe minus exclusions")
    payload={"protocol":CONFIG["protocol"],"targets":targets,"development_exclusions":sorted(excluded),"action_budget":CONFIG["action_budget"]}
    payload["digest"]=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return payload

def main():
    receipt=manifest();artifacts=HERE/"artifacts"/"fresh-1";artifacts.mkdir(parents=True,exist_ok=True)
    (artifacts/"MANIFEST.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n")
    results=[]
    for game in receipt["targets"]:
        try:
            results.append(MATRIX.run_game(game,artifact_root=artifacts/"episodes",action_budget=CONFIG["action_budget"]))
        except Exception as error:
            results.append({"game":game,"status":"ABSTAIN_OR_ERROR","error":f"{type(error).__name__}: {error}"})
    solved=[row["game"] for row in results if row.get("levels_completed",0)>=1 and row.get("exact_replay")]
    document={"protocol":CONFIG["protocol"],"manifest_digest":receipt["digest"],"frozen_batch":True,"source_blind_runtime":True,"no_repairs_between_targets":True,"solved_games":solved,"solved_count":len(solved),"results":results}
    (artifacts/"RESULT.json").write_text(json.dumps(document,indent=2,sort_keys=True)+"\n")
    print(json.dumps(document,indent=2));return 0

if __name__=="__main__":raise SystemExit(main())
