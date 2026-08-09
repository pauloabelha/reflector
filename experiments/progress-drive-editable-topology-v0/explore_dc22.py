from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
from collections import deque

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = load(
    "editable_topology_base",
    ROOT / "experiments/prior-accelerated-relational-transfer-v0/experiment.py",
)


def clickable_centers(grid: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, int], ...]:
    """Return component-centre display coordinates from the visually separate control pane.

    The split is inferred from the widest full-height separator band, never a game ID or
    source coordinate. Components are foreground connected components to its right.
    """
    height, width = len(grid), len(grid[0])
    changes = [sum(grid[y][x] != grid[y][x - 1] for y in range(height)) for x in range(1, width)]
    split = max(range(1, width), key=lambda x: (changes[x - 1], x))
    points = {(x, y) for y in range(height) for x in range(split + 1, width) if grid[y][x] not in (0, 5)}
    components: list[set[tuple[int, int]]] = []
    while points:
        seed = points.pop()
        component = {seed}
        todo = [seed]
        while todo:
            x, y = todo.pop()
            for nxt in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if nxt in points:
                    points.remove(nxt)
                    component.add(nxt)
                    todo.append(nxt)
        components.append(component)
    centers = []
    for component in components:
        xs = [p[0] for p in component]
        ys = [p[1] for p in component]
        if len(component) >= 2:
            centers.append(((min(xs) + max(xs)) // 2, (min(ys) + max(ys)) // 2 + (64 - height) // 2))
    return tuple(sorted(set(centers)))


def replay(environment, actions: tuple[tuple[int, dict[str, int]], ...]):
    observation = environment.reset()
    for action_id, data in actions:
        observation = BASE.execute_action(environment, "dc22-fdcac232", action_id, data, "editable-topology-search")
    return BASE.observation_record(observation), BASE.observation_grid(observation)


def main() -> int:
    output = HERE / "artifacts" / "oracle-search"
    output.mkdir(parents=True, exist_ok=True)
    arcade, environment = BASE.open_environment(ROOT / "environment_files", output / "recordings", "dc22-fdcac232")
    try:
        initial_record, initial_grid = replay(environment, ())
        clicks = clickable_centers(initial_grid)
        actions = tuple((index, {}) for index in (1, 2, 3, 4)) + tuple((6, {"x": x, "y": y}) for x, y in clicks)
        queue = deque([()])
        seen = {initial_record["frame_sha256"]}
        max_depth = 28
        expanded = 0
        while queue:
            prefix = queue.popleft()
            if len(prefix) >= max_depth:
                continue
            for action in actions:
                candidate = prefix + (action,)
                record, _grid = replay(environment, candidate)
                expanded += 1
                if record["levels_completed"] >= 1:
                    result = {"actions": candidate, "record": record, "expanded": expanded, "clicks": clicks}
                    (output / "RESULT.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
                    print(json.dumps(result, indent=2))
                    return 0
                digest = record["frame_sha256"]
                if digest not in seen and record["state"].upper().rsplit(".", 1)[-1] not in {"GAME_OVER", "WIN"}:
                    seen.add(digest)
                    queue.append(candidate)
            if expanded % 100 == 0:
                print(json.dumps({"expanded": expanded, "frontier": len(queue), "seen": len(seen), "depth": len(prefix)}), flush=True)
        print(json.dumps({"expanded": expanded, "seen": len(seen), "clicks": clicks, "solved": False}))
        return 1
    finally:
        arcade.close_scorecard()


if __name__ == "__main__":
    raise SystemExit(main())
