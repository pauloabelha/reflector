"""Generic visual inference and planning for editable flow-routing scenes."""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from typing import Mapping, Sequence


class FlowRoutingError(ValueError):
    pass


@dataclass(frozen=True)
class Component:
    value: int
    cells: frozenset[tuple[int, int]]
    x: int
    y: int
    width: int
    height: int

    @property
    def normalized(self) -> frozenset[tuple[int, int]]:
        return frozenset((x - self.x, y - self.y) for x, y in self.cells)


@dataclass(frozen=True)
class FlowScene:
    scale: int
    width: int
    height: int
    source_column: int
    reflector: Component
    receptacles: tuple[Component, ...]
    receptacle_ports: tuple[int, ...]


@dataclass(frozen=True)
class FlowPlan:
    target_x: int
    target_y: int
    move_delta: tuple[int, int]
    predicted_exit_columns: tuple[int, int]
    served_ports: tuple[int, ...]
    progress_before: int
    progress_after: int
    action_ids: tuple[int, ...]


def infer_scale(grid: Sequence[Sequence[int]]) -> int:
    if not grid or not grid[0]:
        raise FlowRoutingError("empty frame")
    width = len(grid[0])
    if any(len(row) != width for row in grid):
        raise FlowRoutingError("ragged frame")
    height = len(grid)
    # Interface overlays can introduce one-pixel run lengths even though the
    # world itself is rendered on a coarser lattice.  Select the largest small
    # tiling whose cells remain overwhelmingly constant.
    candidates = []
    for factor in range(2, 9):
        if width % factor or height % factor:
            continue
        represented = total = 0
        for top in range(0, height, factor):
            for left in range(0, width, factor):
                counts = Counter(
                    grid[y][x]
                    for y in range(top, top + factor)
                    for x in range(left, left + factor)
                )
                represented += max(counts.values()); total += factor * factor
        if represented / total >= 0.97:
            candidates.append(factor)
    return max(candidates, default=1)


def coarsen(grid: Sequence[Sequence[int]], scale: int | None = None) -> tuple[tuple[int, ...], ...]:
    scale = scale or infer_scale(grid)
    height, width = len(grid), len(grid[0])
    if height % scale or width % scale:
        raise FlowRoutingError("frame does not tile at inferred scale")
    rows = []
    for top in range(0, height, scale):
        row = []
        for left in range(0, width, scale):
            values = Counter(
                grid[y][x]
                for y in range(top, top + scale)
                for x in range(left, left + scale)
            )
            row.append(min(values, key=lambda value: (-values[value], value)))
        rows.append(tuple(row))
    return tuple(rows)


def components(grid: Sequence[Sequence[int]]) -> tuple[Component, ...]:
    height, width = len(grid), len(grid[0])
    seen: set[tuple[int, int]] = set()
    result = []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen:
                continue
            value = grid[y][x]
            queue = deque([(x, y)])
            cells: set[tuple[int, int]] = set()
            seen.add((x, y))
            while queue:
                cx, cy = queue.popleft()
                cells.add((cx, cy))
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in seen and grid[ny][nx] == value:
                        seen.add((nx, ny)); queue.append((nx, ny))
            xs, ys = zip(*cells)
            result.append(Component(value, frozenset(cells), min(xs), min(ys), max(xs)-min(xs)+1, max(ys)-min(ys)+1))
    return tuple(result)


def infer_scene(frame: Sequence[Sequence[int]]) -> FlowScene:
    scale = infer_scale(frame)
    grid = coarsen(frame, scale)
    height, width = len(grid), len(grid[0])
    parts = components(grid)
    background = Counter(value for row in grid for value in row).most_common(1)[0][0]
    foreground = [part for part in parts if part.value != background]

    shape_groups: dict[frozenset[tuple[int, int]], list[Component]] = {}
    for part in foreground:
        if part.width < width and part.height < height:
            shape_groups.setdefault(part.normalized, []).append(part)
    repeated = [
        tuple(sorted(group, key=lambda part: (part.x, part.y)))
        for group in shape_groups.values()
        if len(group) >= 2 and all(part.y >= height // 2 for part in group)
        and any(len(part.cells) < part.width * part.height for part in group)
    ]
    if not repeated:
        raise FlowRoutingError("no repeated open receptacle population")
    receptacles = max(repeated, key=lambda group: (len(group), sum(part.y for part in group)))
    ports = []
    for part in receptacles:
        top_cells = {x for x, y in part.cells if y == part.y}
        gaps = [x for x in range(part.x, part.x + part.width) if x not in top_cells]
        if len(gaps) != 1:
            raise FlowRoutingError("receptacle does not expose one top port")
        ports.append(gaps[0])

    bars = [
        part for part in foreground
        if part.height == 1 and part.width >= 3 and part.y < min(item.y for item in receptacles)
        and part.y > 0
    ]
    if not bars:
        raise FlowRoutingError("no editable horizontal reflector")
    reflector = min(bars, key=lambda part: (part.y, -part.width, part.x))

    singletons = [part for part in foreground if len(part.cells) == 1 and part.y < reflector.y]
    columns = Counter(part.x for part in singletons)
    candidates = [x for x, count in columns.items() if count >= 2]
    if not candidates:
        raise FlowRoutingError("no top-origin flow column")
    source_column = min(candidates, key=lambda x: (min(part.y for part in singletons if part.x == x), x))
    return FlowScene(scale, width, height, source_column, reflector, tuple(receptacles), tuple(sorted(ports)))


def plan_flow(scene: FlowScene, movement_actions: Mapping[tuple[int, int], int], trigger_action: int) -> FlowPlan:
    ports = scene.receptacle_ports
    if len(ports) != 2:
        raise FlowRoutingError("current splitter model requires exactly two terminal ports")
    left, right = ports
    target_x = left + 1
    expected_width = right - left - 1
    if expected_width != scene.reflector.width:
        raise FlowRoutingError("reflector span cannot terminate at both ports")
    if not target_x <= scene.source_column < target_x + scene.reflector.width:
        raise FlowRoutingError("source does not intersect the planned reflector")
    dx, dy = target_x - scene.reflector.x, 0
    actions = []
    for delta, count in (((1, 0), max(dx, 0)), ((-1, 0), max(-dx, 0)), ((0, 1), max(dy, 0)), ((0, -1), max(-dy, 0))):
        if count:
            if delta not in movement_actions:
                raise FlowRoutingError(f"missing opaque action model for {delta}")
            actions.extend([movement_actions[delta]] * count)
    actions.append(trigger_action)
    exits = (target_x - 1, target_x + scene.reflector.width)
    before = sum(port not in (scene.reflector.x - 1, scene.reflector.x + scene.reflector.width) for port in ports)
    after = sum(port not in exits for port in ports)
    return FlowPlan(target_x, scene.reflector.y, (dx, dy), exits, ports, before, after, tuple(actions))
