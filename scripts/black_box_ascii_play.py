"""Play an ARC-AGI-3 game through legal actions and emit ASCII/diff traces.

This diagnostic harness uses only the public black-box wrapper. It never
imports or inspects a game's implementation module.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

SYMBOLS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz@#"
Frame = tuple[tuple[int, ...], ...]


@dataclass(frozen=True, slots=True)
class DiffSummary:
    changed_pixels: int
    bbox: tuple[int, int, int, int] | None
    transitions: tuple[tuple[str, int], ...]


def normalize_frame(raw_frame: Any) -> Frame:
    """Select the last animation frame and normalize it to immutable rows."""

    value = raw_frame
    if hasattr(value, "tolist"):
        value = value.tolist()
    if (
        isinstance(value, list)
        and value
        and hasattr(value[-1], "tolist")
    ):
        value = value[-1].tolist()
    while (
        isinstance(value, list)
        and value
        and isinstance(value[0], list)
        and value[0]
        and isinstance(value[0][0], list)
    ):
        value = value[-1]
    if not isinstance(value, list):
        return ()
    return tuple(tuple(int(cell) for cell in row) for row in value)


def _symbol_map(frame: Frame) -> dict[int, str]:
    colors = sorted({cell for row in frame for cell in row})
    if len(colors) > len(SYMBOLS):
        raise ValueError("ASCII renderer has too many distinct values")
    return {color: SYMBOLS[index] for index, color in enumerate(colors)}


def render_ascii(
    frame: Frame,
    *,
    max_width: int = 64,
    max_height: int = 32,
) -> str:
    """Render a modal block downsample with an explicit value legend."""

    if not frame or not frame[0]:
        return "(empty frame)\n"
    width = len(frame[0])
    height = len(frame)
    if any(len(row) != width for row in frame):
        raise ValueError("frame rows must have equal width")
    symbols = _symbol_map(frame)
    x_step = max(1, (width + max_width - 1) // max_width)
    y_step = max(1, (height + max_height - 1) // max_height)
    rows: list[str] = []
    for top in range(0, height, y_step):
        rendered: list[str] = []
        for left in range(0, width, x_step):
            values = Counter(
                frame[y][x]
                for y in range(top, min(height, top + y_step))
                for x in range(left, min(width, left + x_step))
            )
            value = min(values, key=lambda item: (-values[item], item))
            rendered.append(symbols[value])
        rows.append("".join(rendered))
    legend = " ".join(
        f"{symbol}={color}" for color, symbol in symbols.items()
    )
    return (
        f"size={width}x{height} sample={x_step}x{y_step}\n"
        f"legend {legend}\n"
        + "\n".join(rows)
        + "\n"
    )


def summarize_diff(before: Frame, after: Frame) -> DiffSummary:
    if (
        not before
        or not after
        or len(before) != len(after)
        or any(len(left) != len(right) for left, right in zip(before, after))
    ):
        return DiffSummary(-1, None, ())
    changed: list[tuple[int, int]] = []
    transitions: Counter[str] = Counter()
    for y, (left, right) in enumerate(zip(before, after, strict=True)):
        for x, (old, new) in enumerate(zip(left, right, strict=True)):
            if old == new:
                continue
            changed.append((x, y))
            transitions[f"{old}->{new}"] += 1
    bbox = (
        (
            min(x for x, _y in changed),
            min(y for _x, y in changed),
            max(x for x, _y in changed),
            max(y for _x, y in changed),
        )
        if changed
        else None
    )
    return DiffSummary(
        changed_pixels=len(changed),
        bbox=bbox,
        transitions=tuple(transitions.most_common(12)),
    )


def parse_action(value: str) -> tuple[int, dict[str, int]]:
    """Parse ``ID`` or ``ID:X:Y`` without assigning semantic action names."""

    parts = value.split(":")
    if len(parts) not in {1, 3}:
        raise ValueError(f"invalid action specification: {value}")
    try:
        action_id = int(parts[0])
    except ValueError as error:
        raise ValueError(f"invalid action id: {parts[0]}") from error
    if not 0 <= action_id <= 7:
        raise ValueError(f"invalid action id: {action_id}")
    data = (
        {"x": int(parts[1]), "y": int(parts[2])}
        if len(parts) == 3
        else {}
    )
    return action_id, data


def systematic_probe_actions(
    frame: Frame,
    available_actions: Iterable[int],
) -> tuple[tuple[int, dict[str, int]], ...]:
    """Probe each plain control once and diverse visible components at most once."""

    legal = tuple(sorted(set(available_actions)))
    output: list[tuple[int, dict[str, int]]] = [
        (action, {}) for action in legal if action not in {0, 6}
    ]
    if 6 not in legal or not frame or not frame[0]:
        return tuple(output)
    background = Counter(cell for row in frame for cell in row).most_common(1)[0][0]
    height = len(frame)
    width = len(frame[0])
    visited: set[tuple[int, int]] = set()
    components: list[tuple[int, tuple[int, int]]] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in visited or frame[y][x] == background:
                continue
            color = frame[y][x]
            stack = [(x, y)]
            visited.add((x, y))
            points: list[tuple[int, int]] = []
            while stack:
                current = stack.pop()
                points.append(current)
                cx, cy = current
                for nx, ny in (
                    (cx - 1, cy),
                    (cx + 1, cy),
                    (cx, cy - 1),
                    (cx, cy + 1),
                ):
                    if (
                        0 <= nx < width
                        and 0 <= ny < height
                        and (nx, ny) not in visited
                        and frame[ny][nx] == color
                    ):
                        visited.add((nx, ny))
                        stack.append((nx, ny))
            centroid = (
                sum(point[0] for point in points) // len(points),
                sum(point[1] for point in points) // len(points),
            )
            components.append((len(points), centroid))
    ranked = sorted(components)
    selected: list[tuple[int, int]] = []
    if ranked:
        for index in (0, len(ranked) // 2, len(ranked) - 1):
            point = ranked[index][1]
            if point not in selected:
                selected.append(point)
    output.extend((6, {"x": x, "y": y}) for x, y in selected)
    return tuple(output)


def play(
    game: str,
    actions: Iterable[tuple[int, dict[str, int]]] | None,
    *,
    environments_dir: Path,
    recordings_dir: Path,
    systematic_probe: bool = False,
) -> tuple[list[dict[str, Any]], Frame]:
    from arc_agi import Arcade, OperationMode  # type: ignore[import-untyped]
    from arcengine import GameAction

    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments_dir),
        recordings_dir=str(recordings_dir),
    )
    environment = arcade.make(game, save_recording=True)
    if environment is None:
        raise RuntimeError(f"could not create game: {game}")
    raw = environment.observation_space
    frame = normalize_frame(raw.frame)
    selected_actions = (
        systematic_probe_actions(frame, raw.available_actions)
        if systematic_probe
        else tuple(actions or ())
    )
    events: list[dict[str, Any]] = [
        {
            "index": 0,
            "action": None,
            "state": raw.state.value,
            "levels_completed": raw.levels_completed,
            "available_actions": list(raw.available_actions),
            "ascii": render_ascii(frame),
        }
    ]
    for index, (action_id, data) in enumerate(selected_actions, start=1):
        if action_id not in raw.available_actions:
            raise ValueError(
                f"action {action_id} is not legal at step {index}; "
                f"available={raw.available_actions}"
            )
        action = GameAction.from_id(action_id)
        if data:
            action.set_data(data)
        raw = environment.step(
            action,
            data={**data, "game_id": game},
            reasoning={"diagnostic": "black-box-ascii-play"},
        )
        next_frame = normalize_frame(raw.frame)
        events.append(
            {
                "index": index,
                "action": {"id": action_id, "data": data},
                "state": raw.state.value,
                "levels_completed": raw.levels_completed,
                "available_actions": list(raw.available_actions),
                "diff": asdict(summarize_diff(frame, next_frame)),
                "ascii": render_ascii(next_frame),
            }
        )
        frame = next_frame
        if raw.state.value == "WIN":
            break
    arcade.close_scorecard(environment.scorecard_id)
    return events, frame


def render_markdown(game: str, events: list[dict[str, Any]]) -> str:
    lines = [
        f"# Black-box ASCII play: `{game}`",
        "",
        "Only legal public-wrapper observations and actions were used.",
        "",
    ]
    for event in events:
        lines.extend(
            (
                f"## Step {event['index']}",
                "",
                f"- Action: `{event['action']}`",
                f"- State: `{event['state']}`",
                f"- Levels completed: `{event['levels_completed']}`",
                f"- Available actions: `{event['available_actions']}`",
            )
        )
        if "diff" in event:
            lines.append(f"- Diff: `{event['diff']}`")
        lines.extend(("", "```text", event["ascii"].rstrip(), "```", ""))
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("game")
    parser.add_argument("actions", nargs="*")
    parser.add_argument("--environments-dir", type=Path, required=True)
    parser.add_argument("--recordings-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--systematic-probe", action="store_true")
    args = parser.parse_args()
    actions = tuple(parse_action(value) for value in args.actions)
    events, _frame = play(
        args.game,
        actions,
        environments_dir=args.environments_dir,
        recordings_dir=args.recordings_dir,
        systematic_probe=args.systematic_probe,
    )
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / f"{args.game}.black-box.json"
    markdown_path = output / f"{args.game}.black-box.md"
    json_path.write_text(json.dumps(events, indent=2) + "\n", encoding="utf-8")
    markdown_path.write_text(
        render_markdown(args.game, events),
        encoding="utf-8",
    )
    print(json_path)
    print(markdown_path)


if __name__ == "__main__":
    main()
