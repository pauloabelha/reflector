from __future__ import annotations
import hashlib,importlib.util,json,pathlib,sys
HERE=pathlib.Path(__file__).resolve().parent;CONFIG=json.loads((HERE/"config.json").read_text());SOURCE=HERE.parent/"autonomous-progress-synthesis-v0";sys.path.insert(0,str(SOURCE))
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);assert spec and spec.loader;m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
RUNNER=load("sealed_registry_v3_runner",SOURCE/"run_registry_development.py")
def atomic(path,value):
 tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(value,indent=2,sort_keys=True)+"\n");tmp.replace(path)
def manifest():
 targets=tuple(CONFIG["targets"])
 if len(targets)!=16 or targets!=tuple(sorted(set(targets))):raise RuntimeError("invalid frozen targets")
 doc={"protocol":CONFIG["protocol"],"targets":targets,"action_budget":CONFIG["action_budget"],"mechanism_commit":CONFIG["mechanism_commit"]};doc["digest"]=hashlib.sha256(json.dumps(doc,sort_keys=True,separators=(",",":")).encode()).hexdigest();return doc
def main():
 artifacts=HERE/"artifacts"/"fresh-1";RUNNER.ART=artifacts/"episodes";artifacts.mkdir(parents=True,exist_ok=True);receipt=manifest();atomic(artifacts/"MANIFEST.json",receipt);rows=[]
 for game in receipt["targets"]:
  try:row=RUNNER.run_game(game,limit=receipt["action_budget"])
  except Exception as error:row={"game":game,"status":"ABSTAIN_OR_ERROR","error":f"{type(error).__name__}: {error}"}
  rows.append(row);atomic(artifacts/"PARTIAL.json",{"manifest_digest":receipt["digest"],"terminal_games":[x["game"] for x in rows],"results":rows});print(json.dumps({"game":game,"levels_completed":row.get("levels_completed",0),"capability":row.get("selected_capability"),"error":row.get("error")}),flush=True)
 solved=[row["game"] for row in rows if row.get("levels_completed",0)>=1 and row.get("exact_replay")];doc={"protocol":CONFIG["protocol"],"manifest_digest":receipt["digest"],"solved_count":len(solved),"solved_games":solved,"results":rows};atomic(artifacts/"RESULT.json",doc);return 0
if __name__=="__main__":raise SystemExit(main())
