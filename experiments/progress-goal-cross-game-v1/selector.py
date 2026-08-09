"""Metadata-only deterministic cross-game selector."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

SEED = "reflector2-v1.16-heldout-simple-action-selector-v1\0"
EXCLUDED = frozenset({"ar25", "wa30"})
EXPECTED = "g50t"


def select(environments: Path) -> dict[str, Any]:
    rows = []
    for directory in sorted(environments.iterdir()):
        metadata_paths = list(directory.glob("*/metadata.json"))
        if len(metadata_paths) != 1 or directory.name in EXCLUDED:
            continue
        metadata = json.loads(metadata_paths[0].read_text(encoding="utf-8"))
        if metadata.get("tags") != ["keyboard"]:
            continue
        digest = hashlib.sha256((SEED + directory.name).encode("utf-8")).hexdigest()
        rows.append({
            "game": directory.name,
            "version": str(metadata["game_id"]),
            "score": digest,
        })
    rows.sort(key=lambda item: (item["score"], item["game"]))
    if not rows or rows[0]["game"] != EXPECTED:
        raise RuntimeError("frozen metadata-only selection no longer resolves to g50t")
    return {
        "protocol": "metadata-only-cross-game-selector-v1",
        "seed": SEED,
        "excluded": sorted(EXCLUDED),
        "candidates": rows,
        "selected": rows[0],
    }
