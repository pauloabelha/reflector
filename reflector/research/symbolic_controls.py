"""Reproducible, non-deployed symbolic controls for ARC-AGI-3.

These policies are deliberately kept outside ``reflector.runtime``.  They are
comparison instruments, not candidate features: promotion still requires an
implementation through the shared Kaggle inference path.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Iterable


@dataclass(frozen=True, order=True, slots=True)
class ControlAction:
    """A hashable ARC action, including coordinates for ACTION6."""

    action_id: int
    x: int = -1
    y: int = -1

    @property
    def data(self) -> dict[str, int]:
        if self.action_id != 6:
            return {}
        return {"x": self.x, "y": self.y}


@dataclass(slots=True)
class _Node:
    actions: tuple[ControlAction, ...]
    tried: set[ControlAction] = field(default_factory=set)
    edges: dict[ControlAction, bytes] = field(default_factory=dict)


class ObjectGraphControl:
    """Deterministic graph-frontier exploration over symbolic object actions.

    The control has no learned parameters, neural components, game identifiers,
    or privileged level data.  A node is a nuisance-reduced frame.  Its outgoing
    actions are the legal simple actions plus clicks on connected monochrome
    components.  When the current node is exhausted, breadth-first search
    returns the first action on a known shortest path to an open frontier.
    """

    def __init__(self, *, max_clicks: int = 128) -> None:
        self.max_clicks = max_clicks
        self.nodes: dict[bytes, _Node] = {}
        self.pending_state: bytes | None = None
        self.pending_action: ControlAction | None = None
        self.levels_completed = 0
        self.unique_states = 0
        self.frontier_routes = 0
        self.novel_transitions = 0

    def reset_level(self, levels_completed: int) -> None:
        self.nodes.clear()
        self.pending_state = None
        self.pending_action = None
        self.levels_completed = levels_completed

    def choose(
        self,
        *,
        frame: tuple[tuple[int, ...], ...],
        available_actions: Iterable[int],
        levels_completed: int,
    ) -> ControlAction:
        if levels_completed != self.levels_completed:
            self.reset_level(levels_completed)

        state = self._state_key(frame)
        actions = self._actions(frame, available_actions)
        node = self.nodes.get(state)
        if node is None:
            node = _Node(actions=actions)
            self.nodes[state] = node
            self.unique_states += 1

        if self.pending_state is not None and self.pending_action is not None:
            source = self.nodes.get(self.pending_state)
            if source is not None:
                old_target = source.edges.get(self.pending_action)
                source.edges[self.pending_action] = state
                if old_target != state:
                    self.novel_transitions += 1

        untried = tuple(action for action in node.actions if action not in node.tried)
        if untried:
            selected = untried[0]
        else:
            route_action = self._route_to_frontier(state)
            if route_action is None:
                # Exhausted or aliased graph: retry actions fairly and
                # deterministically instead of smuggling in game knowledge.
                selected = node.actions[
                    sum(1 for action in node.tried if action in node.actions)
                    % len(node.actions)
                ]
            else:
                selected = route_action
                self.frontier_routes += 1

        node.tried.add(selected)
        self.pending_state = state
        self.pending_action = selected
        return selected

    def abandon_transition(self) -> None:
        """Forget a pending edge after GAME_OVER before the reset frame."""

        self.pending_state = None
        self.pending_action = None

    def metrics(self) -> dict[str, int]:
        return {
            "unique_states": self.unique_states,
            "frontier_routes": self.frontier_routes,
            "novel_transitions": self.novel_transitions,
        }

    def _route_to_frontier(self, start: bytes) -> ControlAction | None:
        queue: deque[bytes] = deque((start,))
        first_action: dict[bytes, ControlAction | None] = {start: None}
        while queue:
            state = queue.popleft()
            node = self.nodes[state]
            if state != start and any(
                action not in node.tried for action in node.actions
            ):
                return first_action[state]
            for action, target in node.edges.items():
                if target not in self.nodes or target in first_action:
                    continue
                first_action[target] = first_action[state] or action
                queue.append(target)
        return None

    def _actions(
        self,
        frame: tuple[tuple[int, ...], ...],
        available_actions: Iterable[int],
    ) -> tuple[ControlAction, ...]:
        legal = tuple(sorted(set(int(action) for action in available_actions)))
        simple = tuple(ControlAction(action) for action in legal if 1 <= action <= 5)
        if 6 not in legal:
            if not simple:
                raise ValueError("active control state has no legal action")
            return simple
        clicks = tuple(
            ControlAction(6, x=x, y=y)
            for _, _, _, y, x in self._components(frame)[: self.max_clicks]
        )
        actions = simple + clicks
        if not actions:
            raise ValueError("active control state has no legal action")
        return actions

    @staticmethod
    def _components(
        frame: tuple[tuple[int, ...], ...],
    ) -> list[tuple[int, int, int, int, int]]:
        """Return prioritized ``(regularity, area, color, y, x)`` components."""

        height = len(frame)
        width = len(frame[0]) if height else 0
        seen: set[tuple[int, int]] = set()
        output: list[tuple[int, int, int, int, int]] = []
        for y0 in range(height):
            for x0 in range(width):
                if (y0, x0) in seen:
                    continue
                color = frame[y0][x0]
                region = {(y0, x0)}
                queue = deque(((y0, x0),))
                seen.add((y0, x0))
                while queue:
                    y, x = queue.popleft()
                    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        ny, nx = y + dy, x + dx
                        if (
                            0 <= ny < height
                            and 0 <= nx < width
                            and (ny, nx) not in seen
                            and frame[ny][nx] == color
                        ):
                            seen.add((ny, nx))
                            region.add((ny, nx))
                            queue.append((ny, nx))
                area = len(region)
                if area < 2 or area * 4 > max(1, height * width):
                    continue
                ys = [point[0] for point in region]
                xs = [point[1] for point in region]
                box_area = (max(ys) - min(ys) + 1) * (max(xs) - min(xs) + 1)
                regularity = area * 1000 // box_area
                # Prefer compact, salient objects.  The centroid is snapped to
                # an actual component pixel so every proposal is grounded.
                cy = sum(ys) // area
                cx = sum(xs) // area
                target_y, target_x = min(
                    region,
                    key=lambda point: (
                        abs(point[0] - cy) + abs(point[1] - cx),
                        point,
                    ),
                )
                output.append(
                    (regularity, area, color, target_y, target_x)
                )
        output.sort(
            key=lambda item: (-item[0], -item[1], -item[2], item[3], item[4])
        )
        return output

    @staticmethod
    def _state_key(frame: tuple[tuple[int, ...], ...]) -> bytes:
        """Mask thin edge strips, then encode the frame without dependencies."""

        if not frame:
            return b""
        grid = [list(row) for row in frame]
        height = len(grid)
        width = len(grid[0])
        counts: dict[int, int] = {}
        for row in grid:
            for value in row:
                counts[value] = counts.get(value, 0) + 1
        background = max(counts, key=lambda value: (counts[value], -value))
        edge = max(1, min(4, min(height, width) // 8))
        # Status/counter strips are frequently confined to a thin outer band.
        # Mask only rows/columns dominated by one non-background color; this is
        # intentionally conservative because walls can also touch borders.
        for y in tuple(range(edge)) + tuple(range(max(edge, height - edge), height)):
            row_counts: dict[int, int] = {}
            for value in grid[y]:
                row_counts[value] = row_counts.get(value, 0) + 1
            dominant = max(row_counts.values())
            if dominant * 5 >= width * 4:
                grid[y] = [background] * width
        for x in tuple(range(edge)) + tuple(range(max(edge, width - edge), width)):
            values = [grid[y][x] for y in range(height)]
            column_counts: dict[int, int] = {}
            for value in values:
                column_counts[value] = column_counts.get(value, 0) + 1
            dominant = max(column_counts.values())
            if dominant * 5 >= height * 4:
                for y in range(height):
                    grid[y][x] = background
        header = height.to_bytes(2, "little") + width.to_bytes(2, "little")
        return header + bytes(value & 0xFF for row in grid for value in row)
