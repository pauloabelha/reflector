#!/usr/bin/env python3
"""Frozen generic + AR25 matched CAE experiment.

The AR25 arm reads three immutable visual blobs from one append-only Arcade
run.  It never contacts or acts on the environment.  Both atomic and lifted
conditions use the same two ACTION_2 successor transitions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import time

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from reflector2.r2.causal_entity import CausalEntityInducer  # noqa: E402
from reflector2.r2.r2_1_adapter import _components  # noqa: E402


RUN_ID = "run-1786496687295657139"
WORKSPACE = "generic_prospective--ar25--shared_live_qwen"
FRAME_SHA256 = (
    "e279d484f78d22b07378952ff8f11741761be483402fe3721f08cbfa15f16a09",
    "8cf4ec8be5d125e27464138d094dc3b3423f4e416bc3e1e37eac9c7fb2d11cc2",
    "44bfac350e9f7446b190026ff77930b043cdfe4e43959b1c5fb4441212033615",
)


def _frame_regions(blob_root: Path, digest: str):
    image = Image.open(blob_root / f"{digest}.png").convert("RGB")
    if image.size != (256, 256):
        raise ValueError(f"unexpected frozen Arcade image size: {image.size}")
    pixels = image.get_flattened_data() if hasattr(image, "get_flattened_data") else image.getdata()
    palette = {color: index for index, color in enumerate(sorted(set(pixels)))}
    frame = [
        [palette[image.getpixel((x * 4, y * 4))] for x in range(64)]
        for y in range(64)
    ]
    regions = _components(frame)
    for index, region in enumerate(regions):
        region["binding_id"] = f"frame:{digest[:12]}:region:{index}"
    return regions


def run_ar25(blob_root: Path) -> dict:
    frames = [_frame_regions(blob_root, digest) for digest in FRAME_SHA256]
    inducer = CausalEntityInducer(global_fraction=0.9)
    results = []
    selected_atomic_ids = []
    started = time.perf_counter()
    for index, (before, after) in enumerate(zip(frames, frames[1:]), start=1):
        preview = inducer.correspond(before, after)
        common = [
            item for item in preview
            if item.signature.kind == "translation" and item.signature.parameters == (3.0, 0.0)
        ]
        if len(common) != 7:
            raise AssertionError(f"frozen ACTION_2 basis expected 7 co-moving regions, got {len(common)}")
        atomic = max(common, key=lambda item: len(item.predecessor.cells)).predecessor.binding_id
        selected_atomic_ids.append(atomic)
        result = inducer.observe_transition(
            before, after,
            action_scope="ACTION_2",
            evidence_ref=f"arcade:{RUN_ID}:frame:{index + 1}",
            explained_binding_ids=(atomic,),
            predicted_changed_ids=(atomic,),
            demand=True,
        )
        results.append(result)
    supported = [item for item in results[-1].bindings if item.status == "SUPPORTED"]
    if len(supported) != 1:
        raise AssertionError("repeated frozen evidence did not support one bounded CAE")
    entity = supported[0]
    final_transitions = inducer.correspond(frames[1], frames[2])
    coherent_scope = tuple(
        item for item in final_transitions
        if item.signature.kind == "translation" and item.signature.parameters == (3.0, 0.0)
    )
    atomic_residual = inducer.scope_residual(
        coherent_scope,
        explained_binding_ids=(selected_atomic_ids[-1],),
        predicted_changed_ids=(selected_atomic_ids[-1],),
    )
    lifted_residual = inducer.scope_residual(
        coherent_scope,
        explained_binding_ids=tuple(item.predecessor.binding_id for item in coherent_scope),
        predicted_changed_ids=tuple(item.predecessor.binding_id for item in coherent_scope),
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 3)
    return {
        "protocol": "r2-causal-entity-glue-matched-v0",
        "status_legend": {
            "IMPLEMENTED": "executable production or test contract",
            "OBSERVED": "read from frozen environment/Arcade evidence",
            "INFERRED": "controlled consequence not yet executed live",
            "NOT_DEMONSTRATED": "no evidence in this experiment",
        },
        "basis": {
            "status": "OBSERVED",
            "run_id": RUN_ID,
            "workspace": WORKSPACE,
            "game": "ar25",
            "action_scope": "ACTION_2",
            "frame_sha256": list(FRAME_SHA256),
            "transitions": 2,
        },
        "held_constant": [
            "same frozen predecessor/successor frames", "same action scope",
            "same primitive segmentation", "same semantic proposal",
            "same planner and budgets", "no environment execution",
        ],
        "atomic_only": {
            "status": "OBSERVED",
            "actor_binding_ids": selected_atomic_ids,
            "changed_regions": atomic_residual.observed_changed_entities,
            "explained_changed_regions": atomic_residual.explained_changed_entities,
            "unexplained_changed_regions": atomic_residual.unexplained_changed_entities,
            "coverage": atomic_residual.coverage,
        },
        "causal_entity_lift": {
            "status": "INFERRED",
            "entity_id": entity.entity_id,
            "member_count": len(entity.member_binding_ids),
            "common_transform": entity.transform.document(),
            "identity_status": entity.identity_status,
            "support": entity.support,
            "contradictions": entity.contradictions,
            "internal_relation_residual": entity.internal_relation_residual,
            "coverage": lifted_residual.coverage,
            "unexplained_changed_regions": lifted_residual.unexplained_changed_entities,
        },
        "divergences": {
            "actor_granularity": "INFERRED: atomic 45-cell region -> supported 7-member causal entity",
            "planner_route": "NOT_DEMONSTRATED",
            "first_command": "NOT_DEMONSTRATED",
            "environment_settlement": "OBSERVED for member transformations; NOT_DEMONSTRATED for a live assembly-level prediction",
            "score": "NOT_DEMONSTRATED",
        },
        "runtime": {
            "experiment_elapsed_ms": elapsed_ms,
            "last_induction_ms": results[-1].elapsed_ms,
            "candidates_generated": results[-1].candidates_generated,
            "candidates_retained": results[-1].candidates_retained,
            "maximum_members": results[-1].maximum_members,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blob-root", type=Path, default=(
        ROOT / "artifacts" / "r2" / "arcade-runs" / RUN_ID / "workspaces" /
        WORKSPACE / "blobs" / "visual"
    ))
    parser.add_argument("--output", type=Path, default=Path(__file__).parent / "artifacts" / "AR25_MATCHED.json")
    args = parser.parse_args()
    result = run_ar25(args.blob_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
