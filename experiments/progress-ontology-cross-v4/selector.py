from __future__ import annotations
import hashlib, json
from pathlib import Path

SEED = "reflector2-progress-ontology-cross-v4\0"
EXCLUDED = frozenset({"ar25", "wa30", "ls20", "g50t", "tr87", "tu93", "dc22", "ka59", "sp80"})
EXPECTED = "re86"

def select(root: Path) -> dict:
    rows = []
    for directory in sorted(root.iterdir()):
        metadata = list(directory.glob("*/metadata.json"))
        if len(metadata) != 1 or directory.name in EXCLUDED:
            continue
        document = json.loads(metadata[0].read_text())
        if document.get("tags") != ["keyboard_click"]:
            continue
        rows.append({
            "game": directory.name,
            "version": document["game_id"],
            "score": hashlib.sha256((SEED + directory.name).encode()).hexdigest(),
        })
    rows.sort(key=lambda row: (row["score"], row["game"]))
    if not rows or rows[0]["game"] != EXPECTED:
        raise RuntimeError("frozen selector changed")
    return {"seed": SEED, "excluded": sorted(EXCLUDED), "candidates": rows, "selected": rows[0]}
