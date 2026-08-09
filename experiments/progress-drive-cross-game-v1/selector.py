from __future__ import annotations

import hashlib
import json
from pathlib import Path

SEED = "reflector2-progress-drive-cross-v1\0"
EXCLUDED = frozenset({"ar25", "wa30", "ls20", "g50t"})
EXPECTED = "tr87"


def select(root: Path) -> dict:
    candidates = []
    for directory in sorted(root.iterdir()):
        paths = list(directory.glob("*/metadata.json"))
        if len(paths) != 1 or directory.name in EXCLUDED:
            continue
        metadata = json.loads(paths[0].read_text(encoding="utf-8"))
        if metadata.get("tags") != ["keyboard"]:
            continue
        candidates.append({
            "game": directory.name,
            "version": metadata["game_id"],
            "score": hashlib.sha256((SEED + directory.name).encode()).hexdigest(),
        })
    candidates.sort(key=lambda row: (row["score"], row["game"]))
    if not candidates or candidates[0]["game"] != EXPECTED:
        raise RuntimeError("frozen selector resolution changed")
    return {"seed": SEED, "excluded": sorted(EXCLUDED), "candidates": candidates, "selected": candidates[0]}
