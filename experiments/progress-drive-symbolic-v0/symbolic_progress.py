"""Ground editable visual analogy tasks into an action-opaque symbol program."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Mapping, Sequence


class SymbolicProgressError(ValueError):
    pass


Grid = tuple[tuple[int, ...], ...]


@dataclass(frozen=True)
class SymbolicTask:
    examples: tuple[tuple[str, str], ...]
    query: tuple[str, ...]
    editable: tuple[str, ...]
    desired: tuple[str, ...]
    input_origins: tuple[tuple[int, int], ...]
    output_origins: tuple[tuple[int, int], ...]
    slot_step: int


def _grid(value: Sequence[Sequence[int]]) -> Grid:
    rows = tuple(tuple(int(cell) for cell in row) for row in value)
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise SymbolicProgressError("grid must be rectangular")
    return rows


def _rot(mask):
    n = len(mask)
    return tuple(tuple(mask[n - 1 - j][i] for j in range(n)) for i in range(n))


def glyph_signature(grid: Sequence[Sequence[int]], origin: tuple[int, int], *, size: int = 5) -> str:
    rows = _grid(grid)
    x, y = origin
    if x <= 0 or y < 0 or y + size > len(rows) or x + size > len(rows[0]):
        raise SymbolicProgressError("glyph lies outside the frame")
    background = rows[y][x - 1]
    mask = tuple(tuple(int(rows[yy][xx] != background) for xx in range(x, x + size)) for yy in range(y, y + size))
    variants = []
    current = mask
    for _ in range(4):
        variants.append(current)
        variants.append(tuple(tuple(reversed(row)) for row in current))
        current = _rot(current)
    canonical = min("".join(str(cell) for row in item for cell in row) for item in variants)
    return "g:" + hashlib.sha256(canonical.encode()).hexdigest()[:12]


def _nonbackground(grid: Grid, origin: tuple[int, int], size: int = 5) -> int:
    x, y = origin
    background = grid[y][x - 1]
    return sum(grid[yy][xx] != background for yy in range(y, y + size) for xx in range(x, x + size))


def infer_task(grid: Sequence[Sequence[int]], panels: Sequence[Mapping[str, object]], *, mutation_origin: tuple[int, int]) -> SymbolicTask:
    rows = _grid(grid)
    suitable = [row for row in panels if tuple(row.get("size", ())) == (17, 7)]
    if len(suitable) < 2:
        raise SymbolicProgressError("no repeated two-glyph example panels")
    examples = []
    for panel in suitable:
        x, y = map(int, panel["origin"])
        examples.append((glyph_signature(rows, (x + 1, y + 1)), glyph_signature(rows, (x + 11, y + 1))))
    mapping = dict(examples)
    if len(mapping) != len(examples):
        raise SymbolicProgressError("example inputs are not functional and unique")

    output_x, output_y = mutation_origin
    candidates = []
    for step in range(5, 11):
        origins = []
        first_background = rows[output_y][output_x - 1]
        x = output_x
        while x + 5 <= len(rows[0]) and rows[output_y][x - 1] == first_background and _nonbackground(rows, (x, output_y)) >= 3:
            origins.append((x, output_y))
            x += step
        if len(origins) < 2:
            continue
        for y in range(0, output_y):
            input_origins = tuple((x, y) for x, _ in origins)
            try:
                signatures = tuple(glyph_signature(rows, origin) for origin in input_origins)
            except SymbolicProgressError:
                continue
            matches = sum(item in mapping for item in signatures)
            candidates.append((matches == len(origins), matches, len(origins), -step, y, tuple(origins), input_origins, signatures))
    if not candidates:
        raise SymbolicProgressError("editable slot row is not recoverable")
    complete, matches, count, negative_step, _y, output_origins, input_origins, query = max(candidates)
    if not complete or matches != count:
        raise SymbolicProgressError("query row does not ground in demonstrated inputs")
    step = -negative_step
    editable = tuple(glyph_signature(rows, origin) for origin in output_origins)
    desired = tuple(mapping[item] for item in query)
    return SymbolicTask(tuple(sorted(mapping.items())), query, editable, desired, input_origins, output_origins, step)


def workspace_document(task: SymbolicTask) -> dict:
    inputs = {value for value, _ in task.examples}
    outputs = {value for _, value in task.examples}
    return {
        "protocol": "grounded-symbolic-progress-v1",
        "examples": [{"input": left, "output": right} for left, right in task.examples],
        "query": list(task.query),
        "current_editable": list(task.editable),
        "allowed_input_ids": sorted(inputs),
        "allowed_output_ids": sorted(outputs),
        "slot_count": len(task.query),
        "empirical_support": 0,
    }


def compile_desired(response: Mapping[str, object], task: SymbolicTask) -> tuple[str, ...]:
    if response.get("protocol") != "grounded-symbolic-progress-v1":
        raise SymbolicProgressError("response protocol mismatch")
    desired = tuple(str(item) for item in response.get("desired_outputs", ()))
    demonstrated = {right for _left, right in task.examples}
    if len(desired) != len(task.query) or any(item not in demonstrated for item in desired):
        raise SymbolicProgressError("desired output is not grounded in demonstrations")
    return desired


__all__ = ["SymbolicProgressError", "SymbolicTask", "compile_desired", "glyph_signature", "infer_task", "workspace_document"]
