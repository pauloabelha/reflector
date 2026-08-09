"""Run the frozen live-Qwen progress-goal reconstruction gate."""

from __future__ import annotations

from collections import defaultdict
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from typing import Any
from urllib.request import Request, urlopen


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ARTIFACTS = HERE / "artifacts" / "fresh-1"


def load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


LAB = load("live_goal_lab_base", ROOT / "experiments/progress-goal-intervention-v0/lab.py")
GP = load("live_goal_protocol", HERE / "goal_protocol.py")


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def entity_rows(figures: Any) -> list[dict[str, Any]]:
    outlines = {value: f"oc{index}" for index, value in enumerate(sorted({item.outline for item in figures}))}
    interiors = {value: f"ic{index}" for index, value in enumerate(sorted({item.interior_pattern for item in figures}, key=repr))}
    output = []
    for index, figure in enumerate(figures):
        width = 1 + max(x for x, _ in figure.normalized_cells)
        height = 1 + max(y for _, y in figure.normalized_cells)
        output.append({
            "id": f"f{index:02d}",
            "kind": "region",
            "outline_class": outlines[figure.outline],
            "interior_class": interiors[figure.interior_pattern],
            "area": int(figure.area),
            "origin": list(figure.anchor),
            "size": [width, height],
        })
    return output


def post_completion(endpoint: str, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    request = Request(endpoint, data=encoded, headers={"Content-Type": "application/json"}, method="POST")
    started = time.monotonic()
    with urlopen(request, timeout=180) as response:
        body = json.loads(response.read().decode("utf-8"))
    message = body["choices"][0]["message"]
    content = message.get("content", "")
    parsed = json.loads(content) if isinstance(content, str) else content
    return {
        "parsed": parsed,
        "content": content,
        "reasoning_content": message.get("reasoning_content", ""),
        "finish_reason": body["choices"][0].get("finish_reason"),
        "usage": body.get("usage", {}),
        "latency_seconds": time.monotonic() - started,
        "raw": body,
    }


def exact_replay(history: list[dict[str, Any]], game: str) -> bool:
    arcade, environment = LAB.BASE.BASE.open_environment(
        ROOT / "environment_files", ARTIFACTS / "replay", game
    )
    try:
        observation = environment.observation_space or environment.reset()
        for row in history:
            if LAB.BASE.BASE.observation_record(observation)["digest"] != row["before"]["digest"]:
                return False
            observation = LAB.BASE.execute_action(environment, game, row["action"], {}, "live-goal-exact-replay")
            if LAB.BASE.BASE.observation_record(observation)["digest"] != row["after"]["digest"]:
                return False
        return True
    finally:
        arcade.close_scorecard()


def main() -> int:
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    game = config["development_game"]
    arcade, environment = LAB.BASE.BASE.open_environment(
        ROOT / "environment_files", ARTIFACTS / "recordings", game
    )
    history: list[dict[str, Any]] = []
    try:
        observation = environment.observation_space or environment.reset()
        initial_record = LAB.BASE.BASE.observation_record(observation)
        initial_grid = LAB.BASE.BASE.observation_grid(observation)
        figures = LAB.BASE.V0.V0.select_figures(initial_grid)
        grounding_scaffold = LAB.infer_roles(figures)
        actor_outline = grounding_scaffold["actor"]["outline"]
        actor_area = grounding_scaffold["actor"]["area"]
        item_interior = grounding_scaffold["items"][0]["interior"]
        legal = LAB.BASE.BASE.simple_legal_actions(environment, observation)
        movement: dict[tuple[int, int], int] = {}
        intervention_actions: dict[str, int] = {}
        transition_rows: list[dict[str, Any]] = []
        for index, action in enumerate(legal):
            reference = f"im{index:02d}"
            intervention_actions[reference] = action
            before = LAB.BASE.BASE.observation_record(observation)
            before_grid = LAB.BASE.BASE.observation_grid(observation)
            before_anchor = LAB._actor_anchor(before_grid, item_interior, actor_outline, actor_area)
            observation = LAB.BASE.execute_action(environment, game, action, {}, "live-goal-calibration")
            after = LAB.BASE.BASE.observation_record(observation)
            after_grid = LAB.BASE.BASE.observation_grid(observation)
            after_anchor = LAB._actor_anchor(after_grid, item_interior, actor_outline, actor_area)
            delta = (after_anchor[0] - before_anchor[0], after_anchor[1] - before_anchor[1])
            if delta != (0, 0):
                movement[delta] = action
            transition_rows.append({
                "intervention_ref": reference,
                "controlled_id": grounding_scaffold["actor"]["id"],
                "observed_delta": list(delta),
                "observation_changed": before["frame_sha256"] != after["frame_sha256"],
            })
            history.append({"action": action, "before": before, "after": after, "phase": "calibration", "intervention_ref": reference})
            atomic_json(ARTIFACTS / "checkpoint.json", {"history": history})

        current_grid = LAB.BASE.BASE.observation_grid(observation)
        current_figures = LAB.BASE.V0.V0.select_figures(current_grid)
        workspace = GP.build_workspace(
            entities=entity_rows(current_figures),
            transitions=transition_rows,
            frame={"height": len(current_grid), "width": len(current_grid[0])},
        )
        payload = GP.request_payload(workspace, config, LAB.BASE.grid_data_url(current_grid))
        atomic_json(ARTIFACTS / "request.json", payload)
        response = post_completion(config["endpoint"], payload)
        atomic_json(ARTIFACTS / "response.json", response)
        compilation = GP.compile_response(response, workspace)
        atomic_json(ARTIFACTS / "compilation.json", compilation)

        goal = compilation.get("goal") if compilation.get("accepted") else None
        if not goal or goal.get("family") != "collection_containment":
            result = {
                "verdict": "FAIL", "reason": compilation.get("reason"),
                "initial_digest": initial_record["digest"], "actions": len(history),
                "levels_completed": LAB.BASE.BASE.observation_record(observation)["levels_completed"],
                "compilation": compilation,
            }
            atomic_json(ARTIFACTS / "RESULT.json", result)
            return 1

        by_id = {row["id"]: row for row in workspace["entities"]}
        controlled = by_id[goal["controlled_id"]]
        members = [by_id[item] for item in goal["members"]]
        container = by_id[goal["container_id"]]
        x0, y0 = container["origin"]
        member_width, member_height = members[0]["size"]
        slots = tuple(
            (x, y)
            for y in range(y0, y0 + container["size"][1], member_height)
            for x in range(x0, x0 + container["size"][0], member_width)
        )
        interaction_action = intervention_actions[goal["interaction_candidate"]]
        plan = LAB.TRANSPORT.plan_transport(LAB.TRANSPORT.CollectionTransportGoal(
            actor_anchor=tuple(controlled["origin"]),
            portable_item_anchors=tuple(tuple(item["origin"]) for item in members),
            target_bbox=LAB.TRANSPORT.BoundingBox(x0, y0, x0 + container["size"][0] - 1, y0 + container["size"][1] - 1),
            target_slots=slots,
            learned_delta_actions=movement,
            interaction_action=interaction_action,
            grid_bounds=LAB.TRANSPORT.GridBounds(len(current_grid[0]), len(current_grid)),
        ))
        for step in plan.steps:
            if len(history) >= int(config["action_budget"]):
                break
            before = LAB.BASE.BASE.observation_record(observation)
            observation = LAB.BASE.execute_action(environment, game, int(step.action), {}, f"live-goal-{step.kind}")
            after = LAB.BASE.BASE.observation_record(observation)
            history.append({
                "action": int(step.action), "before": before, "after": after,
                "phase": "goal-control", "step_kind": step.kind,
            })
            atomic_json(ARTIFACTS / "checkpoint.json", {"history": history, "compilation": compilation})
            if int(after["levels_completed"]) >= 1:
                break
        final = LAB.BASE.BASE.observation_record(observation)
    finally:
        arcade.close_scorecard()

    replay = exact_replay(history, game)
    passed = (
        int(final["levels_completed"]) >= 1
        and len(history) <= int(config["completion_action_gate"])
        and replay
    )
    result = {
        "verdict": "PASS" if passed else "FAIL",
        "initial_digest": initial_record["digest"],
        "actions": len(history),
        "action_sequence": [row["action"] for row in history],
        "levels_completed": int(final["levels_completed"]),
        "final_digest": final["digest"],
        "exact_replay": replay,
        "compilation": compilation,
        "qwen_usage": response.get("usage", {}),
        "qwen_latency_seconds": response.get("latency_seconds"),
    }
    atomic_json(ARTIFACTS / "RESULT.json", result)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
