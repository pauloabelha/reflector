"""Fresh four-arm developmental test for a generic collection goal.

The oracle contribution is restricted to a situated role binding.  Motor
semantics are learned from a common calibration prefix and all subsequent
actions are emitted by the same action-opaque planner.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = HERE / "artifacts" / "attempt-3"
ENVIRONMENTS = ROOT / "environment_files"


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load("progress_goal_base", ROOT / "experiments/parallel-cognitive-workspace-v1-4/experiment.py")
GOAL = _load("progress_goal_workspace", HERE / "goal_workspace.py")
TRANSPORT = _load("progress_goal_transport", HERE / "transport_goal.py")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def _figure_document(index: int, figure: Any) -> dict[str, Any]:
    width = 1 + max(x for x, _ in figure.normalized_cells)
    height = 1 + max(y for _, y in figure.normalized_cells)
    return {
        "id": f"f{index:02d}",
        "outline": figure.outline,
        "interior": repr(figure.interior_pattern),
        "area": figure.area,
        "anchor": tuple(figure.anchor),
        "width": width,
        "height": height,
    }


def infer_roles(figures: Sequence[Any]) -> dict[str, Any]:
    """Infer actor/items/container from visual equivalence and capacity only."""

    docs = [_figure_document(index, figure) for index, figure in enumerate(figures)]
    by_outline: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in docs:
        by_outline[item["outline"]].append(item)
    candidates: list[tuple[Any, dict[str, Any]]] = []
    for outline, group in by_outline.items():
        by_interior: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for item in group:
            by_interior[item["interior"]].append(item)
        repeated = sorted(
            (values for values in by_interior.values() if len(values) >= 2),
            key=lambda values: (-len(values), values[0]["interior"]),
        )
        if not repeated:
            continue
        items = repeated[0]
        actors = [item for item in group if item not in items and item["area"] == items[0]["area"]]
        if len(actors) != 1:
            continue
        for container in docs:
            if container in group or container["area"] != sum(item["area"] for item in items):
                continue
            item_width, item_height = items[0]["width"], items[0]["height"]
            if container["width"] % item_width or container["height"] % item_height:
                continue
            capacity = (container["width"] // item_width) * (container["height"] // item_height)
            if capacity != len(items):
                continue
            value = {
                "actor": actors[0],
                "items": tuple(sorted(items, key=lambda item: item["id"])),
                "container": container,
            }
            key = (-len(items), outline, actors[0]["id"], container["id"])
            candidates.append((key, value))
    if not candidates:
        raise RuntimeError("no complete collection-role grounding")
    return min(candidates, key=lambda item: item[0])[1]


def oracle_roles(figures: Sequence[Any]) -> dict[str, Any]:
    docs = {item["id"]: item for item in (_figure_document(i, f) for i, f in enumerate(figures))}
    return {
        "actor": docs["f02"],
        "items": (docs["f00"], docs["f01"], docs["f03"]),
        "container": docs["f05"],
    }


def target_slots(roles: Mapping[str, Any]) -> tuple[tuple[int, int], ...]:
    item = roles["items"][0]
    container = roles["container"]
    x0, y0 = container["anchor"]
    return tuple(
        (x, y)
        for y in range(y0, y0 + container["height"], item["height"])
        for x in range(x0, x0 + container["width"], item["width"])
    )


def _actor_anchor(grid: Any, item_interior: str, actor_outline: str, actor_area: int) -> tuple[int, int]:
    figures = BASE.V0.V0.select_figures(grid)
    matches = [
        figure for figure in figures
        if figure.outline == actor_outline
        and figure.area == actor_area
        and repr(figure.interior_pattern) != item_interior
    ]
    if len(matches) != 1:
        raise RuntimeError("actor correspondence is not unique")
    return tuple(matches[0].anchor)


def _act(environment: Any, game: str, action: int, reason: str) -> Any:
    return BASE.execute_action(environment, game, action, {}, reason)


def run_arm(arm: str, config: Mapping[str, Any]) -> dict[str, Any]:
    game = str(config["development_game"])
    arm_root = ARTIFACTS / arm
    recordings = arm_root / "recordings"
    arcade, environment = BASE.BASE.open_environment(ENVIRONMENTS, recordings, game)
    history: list[dict[str, Any]] = []
    try:
        observation = environment.observation_space or environment.reset()
        initial_record = BASE.BASE.observation_record(observation)
        initial_grid = BASE.BASE.observation_grid(observation)
        legal = BASE.BASE.simple_legal_actions(environment, observation)
        figures = BASE.V0.V0.select_figures(initial_grid)
        inferred = infer_roles(figures)
        roles = oracle_roles(figures) if arm == "generic_goal_oracle_bound" else inferred
        candidate = None
        binding = None
        if arm == "sham_goal":
            candidate = GOAL.make_candidate(provenance="mock_intervention", sham=True)
        elif arm.startswith("generic_goal"):
            candidate = GOAL.make_candidate(provenance="oracle_intervention")
            if arm == "generic_goal_oracle_bound" or arm == "generic_goal_unbound":
                binding = GOAL.make_binding(
                    candidate,
                    observation_id=f"obs:{initial_record['digest']}",
                    members=[item["id"] for item in roles["items"]],
                    container=roles["container"]["id"],
                )
        workspace = {
            "candidate": None if candidate is None else GOAL.candidate_object(candidate, attention_boost=int(config["mock_attention_boost"])),
            "binding": None if binding is None else GOAL.binding_object(binding),
        }

        actor_outline = roles["actor"]["outline"]
        item_interior = roles["items"][0]["interior"]
        actor_area = roles["actor"]["area"]
        movement: dict[tuple[int, int], int] = {}
        zero_actions: list[int] = []
        for action in legal:
            before_grid = BASE.BASE.observation_grid(observation)
            before_anchor = _actor_anchor(before_grid, item_interior, actor_outline, actor_area)
            before = BASE.BASE.observation_record(observation)
            observation = _act(environment, game, action, "fixed-common-calibration")
            after = BASE.BASE.observation_record(observation)
            after_grid = BASE.BASE.observation_grid(observation)
            after_anchor = _actor_anchor(after_grid, item_interior, actor_outline, actor_area)
            delta = (after_anchor[0] - before_anchor[0], after_anchor[1] - before_anchor[1])
            if delta == (0, 0):
                zero_actions.append(action)
            else:
                movement[delta] = action
            history.append({"action": action, "reason": "calibration", "before": before, "after": after, "actor_delta": delta})
            atomic_json(arm_root / "checkpoint.json", {"arm": arm, "history": history, "workspace": workspace})

        if arm.startswith("generic_goal"):
            if len(zero_actions) != 1 or len(movement) < 4:
                raise RuntimeError("calibration did not isolate movement and interaction")
            container = roles["container"]
            x0, y0 = container["anchor"]
            plan = TRANSPORT.plan_transport(TRANSPORT.CollectionTransportGoal(
                actor_anchor=_actor_anchor(BASE.BASE.observation_grid(observation), item_interior, actor_outline, actor_area),
                portable_item_anchors=tuple(item["anchor"] for item in roles["items"]),
                target_bbox=TRANSPORT.BoundingBox(x0, y0, x0 + container["width"] - 1, y0 + container["height"] - 1),
                target_slots=target_slots(roles),
                learned_delta_actions=movement,
                interaction_action=zero_actions[0],
                grid_bounds=TRANSPORT.GridBounds(len(initial_grid[0]), len(initial_grid)),
            ))
            planned = list(plan.actions)
        else:
            planned = [legal[index % len(legal)] for index in range(int(config["action_budget"]) - len(history))]

        for action in planned:
            if len(history) >= int(config["action_budget"]):
                break
            before = BASE.BASE.observation_record(observation)
            observation = _act(environment, game, int(action), "goal-directed" if arm.startswith("generic_goal") else "baseline-cycle")
            after = BASE.BASE.observation_record(observation)
            history.append({"action": int(action), "reason": "goal-directed" if arm.startswith("generic_goal") else "baseline-cycle", "before": before, "after": after})
            atomic_json(arm_root / "checkpoint.json", {"arm": arm, "history": history, "workspace": workspace})
            if int(after["levels_completed"]) >= int(config["level_target"]):
                break

        result = {
            "arm": arm,
            "initial_digest": initial_record["digest"],
            "actions": len(history),
            "action_sequence": [item["action"] for item in history],
            "levels_completed": int(BASE.BASE.observation_record(observation)["levels_completed"]),
            "final_digest": BASE.BASE.observation_record(observation)["digest"],
            "workspace": workspace,
            "inferred_roles": {
                "actor": inferred["actor"]["id"],
                "items": [item["id"] for item in inferred["items"]],
                "container": inferred["container"]["id"],
            },
            "situated_roles": {
                "actor": roles["actor"]["id"],
                "items": [item["id"] for item in roles["items"]],
                "container": roles["container"]["id"],
            },
        }
        atomic_json(arm_root / "result.json", result)
        return result
    finally:
        arcade.close_scorecard()


def main() -> int:
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    results = [run_arm(arm, config) for arm in config["arms"]]
    same_start = len({item["initial_digest"] for item in results}) == 1
    summary = {"same_start": same_start, "results": results}
    atomic_json(ARTIFACTS / "SUMMARY.json", summary)
    return 0 if same_start else 2


if __name__ == "__main__":
    raise SystemExit(main())
