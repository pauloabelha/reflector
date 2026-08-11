"""Frozen, semantic-free primitives exposed to the v0 Python Executor.

This is intentionally a small adapter over data PCW already materializes.  It
contains no ARC role names, palette meanings, action meanings, game rules, or
episode policy.  Episode-specific composition belongs in generated code.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Mapping, Sequence


PRIMITIVE_SET_VERSION = "executor-generic-primitives-v0.1"


def get_object(snapshot: Mapping[str, Any], object_id: str) -> dict[str, Any] | None:
    graph = snapshot["epistemic_graph"]
    for item in graph["objects"]:
        if item["id"] == object_id:
            return dict(item)
    schema_catalog = graph.get("schema_catalog", {"columns": [], "rows": []})
    for row in schema_catalog["rows"]:
        if row[0] == object_id:
            item = dict(zip(schema_catalog["columns"], row))
            item["kind"] = "schema"
            item["created_by"] = "workspace"
            return item
    catalog = graph["binding_catalog"]
    columns = catalog["columns"]
    schema_registry = catalog["schema_registry"]
    for row in catalog["rows"]:
        if row[0] == object_id:
            item = dict(zip(columns, row))
            item["kind"] = "r2_binding"
            item["schema"] = schema_registry.get(item["schema"], item["schema"])
            return item
    return None


def query_objects(
    snapshot: Mapping[str, Any], *, kind: str | None = None,
    created_by: str | None = None, live_only: bool = True,
) -> list[dict[str, Any]]:
    graph = snapshot["epistemic_graph"]
    result = [
        dict(item) for item in graph["objects"]
        if (kind is None or item["kind"] == kind)
        and (created_by is None or item["created_by"] == created_by)
        and (not live_only or not item.get("invalidated", False))
    ]
    if kind in {None, "schema"} and created_by in {None, "workspace"}:
        schema_catalog = graph.get("schema_catalog", {"columns": [], "rows": []})
        result.extend(
            item for row in schema_catalog["rows"]
            if (item := get_object(snapshot, row[0])) is not None
            and (not live_only or not item.get("invalidated", False))
        )
    if kind in {None, "r2_binding"} and created_by in {None, "r2"}:
        result.extend(
            item for row in graph["binding_catalog"]["rows"]
            if (item := get_object(snapshot, row[0])) is not None
            and (not live_only or not item.get("invalidated", False))
        )
    return result


def query_transitions(
    snapshot: Mapping[str, Any], *, action_id: int | None = None,
    event_id: str | None = None,
) -> list[dict[str, Any]]:
    return [
        dict(item) for item in snapshot["full_relevant_transition_history"]
        if (action_id is None or int(item["opaque_action"]["action_id"]) == int(action_id))
        and (event_id is None or item["transition_id"] == event_id)
    ]


def manhattan(left: Sequence[int], right: Sequence[int]) -> int:
    if len(left) != len(right):
        raise ValueError("points must have equal dimensions")
    return sum(abs(int(a) - int(b)) for a, b in zip(left, right))


def bounding_box(cells: Sequence[Sequence[int]]) -> list[int] | None:
    points = [(int(item[0]), int(item[1])) for item in cells]
    if not points:
        return None
    return [
        min(row for row, _column in points), min(column for _row, column in points),
        max(row for row, _column in points), max(column for _row, column in points),
    ]


def bbox_relation(left: Sequence[int], right: Sequence[int]) -> dict[str, Any]:
    if len(left) != 4 or len(right) != 4:
        raise ValueError("bounding boxes must be [min_row,min_column,max_row,max_column]")
    lr0, lc0, lr1, lc1 = (int(value) for value in left)
    rr0, rc0, rr1, rc1 = (int(value) for value in right)
    row_gap = max(0, rr0 - lr1 - 1, lr0 - rr1 - 1)
    column_gap = max(0, rc0 - lc1 - 1, lc0 - rc1 - 1)
    overlap = row_gap == 0 and column_gap == 0 and not (
        lr1 < rr0 or rr1 < lr0 or lc1 < rc0 or rc1 < lc0
    )
    return {
        "overlap": overlap,
        "left_contains_right": lr0 <= rr0 and lc0 <= rc0 and lr1 >= rr1 and lc1 >= rc1,
        "right_contains_left": rr0 <= lr0 and rc0 <= lc0 and rr1 >= lr1 and rc1 >= lc1,
        "adjacent": not overlap and row_gap + column_gap == 0,
        "axis_gap": [row_gap, column_gap],
    }


def grid_diff(before: Sequence[Sequence[int]], after: Sequence[Sequence[int]]) -> list[list[int]]:
    if len(before) != len(after) or any(len(left) != len(right) for left, right in zip(before, after)):
        raise ValueError("grids must have equal rectangular shapes")
    return [
        [row, column, int(left), int(right)]
        for row, (before_row, after_row) in enumerate(zip(before, after))
        for column, (left, right) in enumerate(zip(before_row, after_row))
        if int(left) != int(right)
    ]


def bfs(
    adjacency: Mapping[Any, Sequence[Any]], start: Any,
    goals: Sequence[Any], max_depth: int = 64,
) -> list[Any] | None:
    targets = set(goals)
    queue = deque([(start, [start])])
    visited = {start}
    while queue:
        node, path = queue.popleft()
        if node in targets:
            return path
        if len(path) - 1 >= int(max_depth):
            continue
        for neighbor in sorted(adjacency.get(node, ()), key=str):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, [*path, neighbor]))
    return None


def manifest() -> dict[str, Any]:
    return {
        "version": PRIMITIVE_SET_VERSION,
        "functions": {
            "get_object(id)": "stable-ID lookup over current workspace objects",
            "query_objects(kind,created_by,live_only)": "filter current workspace objects",
            "query_transitions(action_id,event_id)": "filter complete relevant history",
            "manhattan(left,right)": "integer L1 distance",
            "bounding_box(cells)": "axis-aligned cell bounding box",
            "bbox_relation(left,right)": "overlap, containment, adjacency, and axis gap",
            "grid_diff(before,after)": "exact changed-cell tuples",
            "bfs(adjacency,start,goals,max_depth)": "generic caller-supplied graph search",
        },
    }


def bound_namespace(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "get_object": lambda object_id: get_object(snapshot, object_id),
        "query_objects": lambda **kwargs: query_objects(snapshot, **kwargs),
        "query_transitions": lambda **kwargs: query_transitions(snapshot, **kwargs),
        "manhattan": manhattan, "bounding_box": bounding_box,
        "bbox_relation": bbox_relation, "grid_diff": grid_diff, "bfs": bfs,
    }
