from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SEED = "reflector2-v1.16-heldout-simple-action-selector-v1\0"
EXCLUDED = frozenset({"ar25", "wa30", "g50t"})
EXPECTED = "ls20"


def select(environments: Path) -> dict[str, Any]:
    rows = []
    for directory in sorted(environments.iterdir()):
        paths = list(directory.glob("*/metadata.json"))
        if len(paths) != 1 or directory.name in EXCLUDED:
            continue
        metadata = json.loads(paths[0].read_text(encoding="utf-8"))
        if metadata.get("tags") != ["keyboard"]:
            continue
        rows.append({
            "game": directory.name, "version": str(metadata["game_id"]),
            "score": hashlib.sha256((SEED + directory.name).encode()).hexdigest(),
        })
    rows.sort(key=lambda item: (item["score"], item["game"]))
    if not rows or rows[0]["game"] != EXPECTED:
        raise RuntimeError("frozen selector no longer resolves to ls20")
    return {
        "protocol": "metadata-only-cross-game-selector-v2",
        "seed": SEED, "excluded": sorted(EXCLUDED),
        "candidates": rows, "selected": rows[0],
    }
