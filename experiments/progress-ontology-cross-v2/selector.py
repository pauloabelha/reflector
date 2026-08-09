from __future__ import annotations
import hashlib,json
from pathlib import Path
SEED="reflector2-progress-ontology-cross-v2\0"
EXCLUDED=frozenset({"ar25","wa30","ls20","g50t","tr87","tu93","dc22"})
EXPECTED="ka59"
def select(root:Path)->dict:
 rows=[]
 for d in sorted(root.iterdir()):
  p=list(d.glob("*/metadata.json"))
  if len(p)!=1 or d.name in EXCLUDED:continue
  m=json.loads(p[0].read_text())
  if m.get("tags")!=["keyboard_click"]:continue
  rows.append({"game":d.name,"version":m["game_id"],"score":hashlib.sha256((SEED+d.name).encode()).hexdigest()})
 rows.sort(key=lambda x:(x["score"],x["game"]))
 if not rows or rows[0]["game"]!=EXPECTED:raise RuntimeError("frozen selector changed")
 return {"seed":SEED,"excluded":sorted(EXCLUDED),"candidates":rows,"selected":rows[0]}
