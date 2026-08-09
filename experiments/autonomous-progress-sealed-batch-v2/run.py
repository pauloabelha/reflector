from __future__ import annotations
import hashlib,importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;CONFIG=json.loads((HERE/"config.json").read_text());SOURCE=HERE.parent/"autonomous-progress-synthesis-v0";sys.path.insert(0,str(SOURCE))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader;m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
RUNNER=load("sealed_registry_runner",SOURCE/"run_registry_development.py")
def manifest():
 targets=tuple(CONFIG["targets"])
 if len(targets)!=16 or targets!=tuple(sorted(set(targets))):raise RuntimeError("invalid frozen target set")
 doc={"protocol":CONFIG["protocol"],"targets":targets,"action_budget":CONFIG["action_budget"],"mechanism_commit":CONFIG["mechanism_commit"]};doc["digest"]=hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(",",":")).encode()).hexdigest();return doc
def main():
 artifacts=HERE/"artifacts"/"fresh-1";RUNNER.ART=artifacts/"episodes";artifacts.mkdir(parents=True,exist_ok=True);receipt=manifest();(artifacts/"MANIFEST.json").write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n");results=[]
 for game in receipt["targets"]:
  try:results.append(RUNNER.run_game(game,limit=receipt["action_budget"]))
  except Exception as error:results.append({"game":game,"status":"ABSTAIN_OR_ERROR","error":f"{type(error).__name__}: {error}"})
 solved=[row["game"] for row in results if row.get("levels_completed",0)>=1 and row.get("exact_replay")];doc={"protocol":CONFIG["protocol"],"manifest_digest":receipt["digest"],"solved_count":len(solved),"solved_games":solved,"results":results};(artifacts/"RESULT.json").write_text(json.dumps(doc,indent=2,sort_keys=True)+"\n");print(json.dumps(doc,indent=2));return 0
if __name__=="__main__":raise SystemExit(main())
