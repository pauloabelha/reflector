"""Shadow-only causal-footprint attribution for exact click transitions.

This module reads durable campaign artifacts and never participates in action
selection, graph persistence, or settlement.  A ``unique`` result means only
that one spatially connected observed-change footprint exists in the exact
ordered successor packet.  It is not a game rule, progress claim, or license
to execute another command.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


PROTOCOL = "r2.1-click-causal-attribution-shadow-v0"
Grid = tuple[tuple[int, ...], ...]
Cell = tuple[int, int]


def _digest(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _grid(value: Any) -> Grid | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    rows: list[tuple[int, ...]] = []
    width = None
    for row in value:
        if not isinstance(row, (list, tuple)) or not row:
            return None
        try:
            normalized = tuple(int(item) for item in row)
        except (TypeError, ValueError):
            return None
        width = len(normalized) if width is None else width
        if len(normalized) != width:
            return None
        rows.append(normalized)
    return tuple(rows)


def _components(cells: Iterable[Cell]) -> list[set[Cell]]:
    remaining = set(cells)
    components: list[set[Cell]] = []
    while remaining:
        seed = min(remaining)
        remaining.remove(seed)
        component = {seed}
        frontier = [seed]
        while frontier:
            row, column = frontier.pop()
            for neighbor in (
                (row - 1, column), (row + 1, column),
                (row, column - 1), (row, column + 1),
            ):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    component.add(neighbor)
                    frontier.append(neighbor)
        components.append(component)
    return components


def _footprint(component: set[Cell], *, click_rc: Cell) -> dict[str, Any]:
    rows = [cell[0] for cell in component]
    columns = [cell[1] for cell in component]
    return {
        "cell_count": len(component),
        "bbox_rc": [min(rows), min(columns), max(rows), max(columns)],
        "contains_clicked_cell": click_rc in component,
        "minimum_manhattan_from_click": min(
            abs(row - click_rc[0]) + abs(column - click_rc[1])
            for row, column in component
        ),
    }


def _result(classification: str, reason: str, **values: Any) -> dict[str, Any]:
    return {
        "protocol": PROTOCOL,
        "authority": "shadow-only-no-control-or-graph-authority",
        "classification": classification,
        "reason": reason,
        "effect_footprints": [],
        **values,
    }


def attribute_click(
    command: dict[str, Any], before_grid: Any,
    observation_envelope: dict[str, Any], *,
    settled_grid: Any | None = None,
    pending_action: int = 6, pending_data: dict[str, Any] | None = None,
    committed_action: int = 6, committed_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Classify an exact click successor without assigning semantic meaning."""
    if not isinstance(command, dict) or _as_int(command.get("action_id")) != 6:
        return _result("abstain", "not-an-exact-click-command")
    data = command.get("data")
    grounding = command.get("payload_grounding")
    if not isinstance(data, dict) or not isinstance(grounding, dict):
        return _result("abstain", "missing-click-data-or-grounding")
    if (
        command.get("protocol") != "action-command-v1"
        or not command.get("command_id")
        or command.get("effect_scope_id") is None
    ):
        return _result("abstain", "inexact-click-command-identity")
    try:
        x, y = int(data["x"]), int(data["y"])
    except (KeyError, TypeError, ValueError):
        return _result("abstain", "invalid-click-coordinate")
    if (
        grounding.get("kind") != "observed-region-cell"
        or list(grounding.get("cell_rc") or ()) != [y, x]
        or not grounding.get("frame_digest")
        or not grounding.get("region_binding_id")
        or grounding.get("region_structural_key") is None
    ):
        return _result("abstain", "inexact-click-grounding")
    pending_data = data if pending_data is None else pending_data
    committed_data = data if committed_data is None else committed_data
    if (
        pending_action != 6 or committed_action != 6
        or pending_data != data or committed_data != data
    ):
        return _result("abstain", "decision-pending-commit-mismatch")

    before = _grid(before_grid)
    if before is None:
        return _result("abstain", "invalid-predecessor-grid")
    if observation_envelope.get("protocol") != "ordered-observation-envelope-v1":
        return _result("abstain", "missing-ordered-observation-envelope")
    raw_frames = observation_envelope.get("ordered_frames")
    if not isinstance(raw_frames, list) or not raw_frames:
        return _result("abstain", "empty-ordered-observation-envelope")
    frames = [_grid(frame) for frame in raw_frames]
    if any(frame is None for frame in frames):
        return _result("abstain", "invalid-ordered-frame")
    ordered = [frame for frame in frames if frame is not None]
    if any(
        len(frame) != len(before) or len(frame[0]) != len(before[0])
        for frame in ordered
    ):
        return _result("abstain", "ordered-frame-shape-mismatch")
    ordinal = observation_envelope.get("settled_support_ordinal")
    support_digests = observation_envelope.get("support_digests")
    if (
        not isinstance(ordinal, int) or not 0 <= ordinal < len(ordered)
        or _as_int(observation_envelope.get("support_count")) != len(ordered)
        or not isinstance(support_digests, list)
        or support_digests != [_digest(frame) for frame in ordered]
        or observation_envelope.get("settled_support_digest") != support_digests[ordinal]
    ):
        return _result("abstain", "invalid-settled-support-identity")
    body = {
        "protocol": observation_envelope["protocol"],
        "ordered_frames": observation_envelope["ordered_frames"],
        "support_digests": support_digests,
        "support_count": observation_envelope["support_count"],
        "settled_support_ordinal": ordinal,
        "settled_support_digest": observation_envelope["settled_support_digest"],
    }
    if observation_envelope.get("digest") != _digest(body):
        return _result("abstain", "invalid-observation-envelope-digest")
    settled = ordered[ordinal]
    if settled_grid is not None and _grid(settled_grid) != settled:
        return _result("abstain", "settled-grid-envelope-mismatch")
    if not (0 <= y < len(before) and 0 <= x < len(before[0])):
        return _result("abstain", "click-coordinate-out-of-bounds")

    changed_cells: set[Cell] = set()
    for earlier, later in zip((before, *ordered), ordered):
        for row in range(len(before)):
            for column in range(len(before[0])):
                if earlier[row][column] != later[row][column]:
                    changed_cells.add((row, column))
    transient_changed = bool(changed_cells)
    if before == settled:
        # Transient animation is evidence, but a settled unchanged successor
        # cannot become a durable effect claim in this analyzer.
        return _result(
            "abstain", "settled-successor-unchanged",
            command_id=command.get("command_id"), click_rc=[y, x],
            ordered_frame_count=len(ordered),
            transient_change_observed=transient_changed,
        )

    components = _components(changed_cells)
    footprints = [
        _footprint(component, click_rc=(y, x)) for component in components
    ]
    common = {
        "command_id": command.get("command_id"),
        "effect_scope_id": command.get("effect_scope_id"),
        "click_rc": [y, x],
        "ordered_frame_count": len(ordered),
        "transient_change_observed": transient_changed,
        "effect_footprints": footprints,
    }
    if len(components) == 1:
        return _result("unique", "one-connected-observed-change-footprint", **common)
    if len(components) > 1:
        return _result("ambiguous", "multiple-disconnected-observed-change-footprints", **common)
    return _result("abstain", "no-observed-change-footprint", **common)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_episode(episode_root: Path) -> dict[str, Any]:
    workspaces = sorted((episode_root / "workspaces").glob("*"))
    if len(workspaces) != 1:
        raise RuntimeError(f"expected one workspace under {episode_root}")
    workspace = workspaces[0]
    blobs = workspace / "blobs" / "sha256"
    events = [_read_json(path) for path in sorted((workspace / "events").glob("*.json"))]
    pending_by_id = {
        event["event_id"]: event["payload"]
        for event in events if event.get("event_type") == "ActionPending"
    }
    rows: list[dict[str, Any]] = []
    for event in events:
        if event.get("event_type") != "TransitionCommitted":
            continue
        transition = event["payload"]
        if _as_int(transition.get("action_id")) != 6:
            continue
        pending = pending_by_id.get(transition.get("pending_event_id"))
        if (
            pending is None or not pending.get("decision_blob")
            or "data" not in pending or "data" not in transition
        ):
            result = _result("abstain", "missing-durable-pending-or-decision")
        else:
            decision = _read_json(blobs / f"{pending['decision_blob']}.json")
            command = decision.get("selected_command") or (
                decision.get("controller", {}).get("decision_contract", {}).get("selected_command")
            ) or {}
            before = _read_json(blobs / f"{transition['before_blob']}.json")
            after = _read_json(blobs / f"{transition['after_blob']}.json")
            result = attribute_click(
                command, before.get("grid"), after.get("observation_envelope") or {},
                settled_grid=after.get("grid"),
                pending_action=_as_int(pending.get("action_id")) or -1,
                pending_data=pending.get("data"),
                committed_action=_as_int(transition.get("action_id")) or -1,
                committed_data=transition.get("data"),
            )
        rows.append({"outer_sequence": event.get("seq"), **result})

    counts = Counter(row["classification"] for row in rows)
    reasons = Counter(row["reason"] for row in rows)
    return {
        "protocol": PROTOCOL,
        "episode": episode_root.name,
        "game": episode_root.name.split("--")[1] if "--" in episode_root.name else None,
        "click_transitions": len(rows),
        "classification_counts": dict(sorted(counts.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "ordered_frames_observed": sum(int(row.get("ordered_frame_count", 0)) for row in rows),
        "multi_frame_click_packets": sum(int(row.get("ordered_frame_count", 0)) > 1 for row in rows),
        "rows": rows,
    }


def analyze_run(run_root: Path, *, pass_prefix: str = "pass-01--") -> dict[str, Any]:
    episodes = [
        analyze_episode(path)
        for path in sorted((run_root / "episodes").glob(f"{pass_prefix}*"))
    ]
    totals: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    for episode in episodes:
        totals.update(episode["classification_counts"])
        reasons.update(episode["reason_counts"])
    return {
        "protocol": PROTOCOL,
        "authority": "shadow-only-no-control-or-graph-authority",
        "run_root": str(run_root),
        "pass_prefix": pass_prefix,
        "games_analyzed": len(episodes),
        "games_with_clicks": sum(episode["click_transitions"] > 0 for episode in episodes),
        "click_transitions": sum(episode["click_transitions"] for episode in episodes),
        "classification_counts": dict(sorted(totals.items())),
        "reason_counts": dict(sorted(reasons.items())),
        "ordered_frames_observed": sum(episode["ordered_frames_observed"] for episode in episodes),
        "multi_frame_click_packets": sum(episode["multi_frame_click_packets"] for episode in episodes),
        "games": [
            {key: value for key, value in episode.items() if key != "rows"}
            for episode in episodes
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--pass-prefix", default="pass-01--")
    args = parser.parse_args()
    print(json.dumps(analyze_run(args.run_root, pass_prefix=args.pass_prefix), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
