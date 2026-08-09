from __future__ import annotations
import hashlib, json
from pathlib import Path
SEED="reflector2-multieffect-cross-v1\0"; EXCLUDED=frozenset({"ar25","wa30","ls20","g50t","tr87"}); EXPECTED="tu93"
def select(root:Path)->dict:
 rows=[]
 for d in sorted(root.iterdir()):
  paths=list(d.glob("*/metadata.json"))
  if len(paths)!=1 or d.name in EXCLUDED:continue
  m=json.loads(paths[0].read_text())
  if m.get("tags")!=["keyboard_click"]:continue
  rows.append({"game":d.name,"version":m["game_id"],"score":hashlib.sha256((SEED+d.name).encode()).hexdigest()})
 rows.sort(key=lambda r:(r["score"],r["game"]))
 if not rows or rows[0]["game"]!=EXPECTED:raise RuntimeError("selector resolution changed")
 return {"seed":SEED,"excluded":sorted(EXCLUDED),"candidates":rows,"selected":rows[0]}
