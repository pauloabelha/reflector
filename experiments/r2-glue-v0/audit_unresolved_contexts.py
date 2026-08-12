"""Audit unresolved rigid-effect context demand in recorded Arcade runs.

This is read-only experiment tooling.  It reuses R2's exact component,
correspondence, rigidity, type-pooling, and command-scope code, but never fits a
workspace or updates a persistent model.  Identical recorded transitions are
deduplicated so repeated live reruns do not masquerade as independent evidence.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
from typing import Any

from reflector2.r2.r2_1_adapter import FrameSchemaObserver, _components


def _load_grid(workspace: Path, blob: str) -> list[list[int]]:
    document = json.loads(
        (workspace / "blobs" / "sha256" / f"{blob}.json").read_text()
    )
    return document["grid"]


def _regions(frame: list[list[int]], prefix: str) -> list[dict[str, Any]]:
    return [
        {**region, "binding_id": f"{prefix}:{index}"}
        for index, region in enumerate(_components(frame))
    ]


def audit(root: Path) -> dict[str, Any]:
    observer = FrameSchemaObserver()
    seen: set[tuple[str, str, str, int]] = set()
    records: list[dict[str, Any]] = []
    transition_count = 0
    for event_path in sorted(root.glob("run-*/workspaces/*/events/*.json")):
        event = json.loads(event_path.read_text())
        if event.get("event_type") != "TransitionCommitted":
            continue
        payload = event["payload"]
        workspace = event_path.parents[1]
        workspace_id = str(event.get("workspace_id", ""))
        game = workspace_id.split("--")[1] if "--" in workspace_id else "unknown"
        action = int(payload["action_id"])
        identity = (
            game, str(payload["before_digest"]), str(payload["after_digest"]), action,
        )
        if identity in seen:
            continue
        seen.add(identity)
        before = _load_grid(workspace, str(payload["before_blob"]))
        after = _load_grid(workspace, str(payload["after_blob"]))
        unresolved: list[dict[str, Any]] = []
        observer._learn_unassigned_atomic_effects(
            action,
            _regions(before, f"{payload['before_digest']}:before"),
            _regions(after, f"{payload['after_digest']}:after"),
            unresolved_contexts=unresolved,
        )
        transition_count += 1
        for item in unresolved:
            records.append({
                "game": game,
                "action": action,
                "before_digest": payload["before_digest"],
                "after_digest": payload["after_digest"],
                **item,
            })

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in records:
        signature = json.dumps({
            "game": item["game"],
            "effect_scope": item["effect_scope"],
            "region_type": item["region_type"],
            "outcomes": item["outcomes"],
        }, sort_keys=True, separators=(",", ":"))
        grouped[signature].append(item)
    repeated = [
        {
            "signature": json.loads(signature),
            "independent_transition_count": len(items),
            "transitions": [
                {
                    "before_digest": item["before_digest"],
                    "after_digest": item["after_digest"],
                }
                for item in items
            ],
        }
        for signature, items in sorted(grouped.items())
        if len(items) >= 2
    ]
    return {
        "protocol": "r2-unresolved-effect-context-audit-v0",
        "authority": "read-only-no-model-update",
        "deduplicated_transition_count": transition_count,
        "unresolved_context_record_count": len(records),
        "repeated_signature_count": len(repeated),
        "repeated_signatures": repeated,
        "records": records,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "root", nargs="?", type=Path,
        default=Path("artifacts/r2/arcade-runs"),
    )
    args = parser.parse_args()
    print(json.dumps(audit(args.root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
