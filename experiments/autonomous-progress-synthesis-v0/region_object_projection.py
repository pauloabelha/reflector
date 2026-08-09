"""Bounded, palette-agnostic object proposals from low-level components."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import progress_synthesis as synthesis


@dataclass(frozen=True, slots=True)
class RegionObject:
    object_id: str
    bbox: tuple[int, int, int, int]
    component_ids: tuple[str, ...]
    component_count: int
    normalized_component_shapes: tuple[tuple[tuple[int, int], ...], ...]
    touches_frame_boundary: bool
    action_correlated: bool
    boundary_distance: int
    enclosure_count: int
    embedded_state_signatures: tuple[tuple[int, tuple[tuple[int, int], ...]], ...]


def _touches(left, right) -> bool:
    ax1, ay1, ax2, ay2 = left; bx1, by1, bx2, by2 = right
    return ax1 <= bx2 + 1 and bx1 <= ax2 + 1 and ay1 <= by2 + 1 and by1 <= ay2 + 1


def project_objects(
    raw: Sequence[Sequence[int]],
    *,
    controlled_bboxes: Sequence[tuple[int, int, int, int]] = (),
    max_extent: int = 16,
    max_objects: int = 32,
) -> tuple[RegionObject, ...]:
    scene = synthesis.perceive(raw)
    components = [
        row for row in scene.regions
        if row.area <= max_extent * max_extent and row.width <= max_extent and row.height <= max_extent
    ]
    groups: list[list[Any]] = []
    for row in components:
        box = row.x, row.y, row.x + row.width, row.y + row.height
        matching = []
        for index, group in enumerate(groups):
            x1=min(item.x for item in group);y1=min(item.y for item in group)
            x2=max(item.x+item.width for item in group);y2=max(item.y+item.height for item in group)
            union=min(x1,box[0]),min(y1,box[1]),max(x2,box[2]),max(y2,box[3])
            if _touches((x1,y1,x2,y2),box) and union[2]-union[0]<=max_extent and union[3]-union[1]<=max_extent:
                matching.append(index)
        if not matching:
            groups.append([row]);continue
        first=matching[0];groups[first].append(row)
        for index in reversed(matching[1:]):groups[first].extend(groups.pop(index))
    output=[]
    for group in groups:
        x1=min(item.x for item in group);y1=min(item.y for item in group)
        x2=max(item.x+item.width for item in group);y2=max(item.y+item.height for item in group)
        component_ids=tuple(sorted({item.region_id for item in group}))
        shapes=tuple(sorted({tuple(sorted(item.normalized)) for item in group}))
        def canonical(item):
            cells=set(item.normalized);factor=1
            for candidate in range(2,min(item.width,item.height)+1):
                if item.width%candidate or item.height%candidate:continue
                blocks={(x//candidate,y//candidate) for x,y in cells}
                expanded={(bx*candidate+dx,by*candidate+dy) for bx,by in blocks for dx in range(candidate) for dy in range(candidate)}
                if expanded==cells:factor=candidate
            # Several source pixels may collapse onto one canonical cell.  The
            # canonical shape is a set of occupied cells, not a pixel-count
            # weighted multiset.
            return tuple(sorted({(x//factor,y//factor) for x,y in cells}))
        embedded=[]
        for item in group:
            if item.x>x1 and item.y>y1 and item.x+item.width<x2 and item.y+item.height<y2 and item.area>=1:
                embedded.append((int(item.value),canonical(item)))
        enclosures=sum(bool(item.holes) and item.width>=3 and item.height>=3 for item in group)
        identity={"bbox":[x1,y1,x2,y2],"component_shapes":shapes}
        correlated=any(_touches((x1,y1,x2,y2),tuple(map(int,box))) for box in controlled_bboxes)
        output.append(RegionObject(
            "vo:"+synthesis.stable_hash(identity)[:20],(x1,y1,x2,y2),component_ids,
            len(component_ids),shapes,x1==0 or y1==0 or x2==scene.width or y2==scene.height,correlated,
            min(x1,y1,scene.width-x2,scene.height-y2),enclosures,tuple(sorted(set(embedded))),
        ))
    return tuple(sorted(output,key=lambda row:(not row.action_correlated,row.bbox[1],row.bbox[0],row.object_id))[:max_objects])


def projection_document(objects: Sequence[RegionObject]) -> list[dict[str, Any]]:
    return [{
        "id":row.object_id,"bbox":list(row.bbox),"component_count":row.component_count,
        "shape_digest":synthesis.stable_hash(row.normalized_component_shapes)[:16],
        "touches_frame_boundary":row.touches_frame_boundary,
        "action_correlated":row.action_correlated,
        "boundary_distance":row.boundary_distance,"enclosure_count":row.enclosure_count,
        "embedded_state_count":len(row.embedded_state_signatures),
        "embedded_state_digests":[synthesis.stable_hash(value)[:16] for value in row.embedded_state_signatures],
    } for row in objects]


__all__=["RegionObject","project_objects","projection_document"]
