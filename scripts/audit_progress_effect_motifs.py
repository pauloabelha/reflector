"""Audit prospectively typed motifs adjacent to real level progress."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any

from reflector.core.action_effect_typing import ProspectiveActionEffectTyper
from reflector.core.action_translation_algebra import (
    ActionAtom,
    ActionIdentity,
)

type Frame = tuple[tuple[int, ...], ...]


def _frame(value: Any) -> Frame:
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


def _action(value: object) -> ActionIdentity | None:
    if not isinstance(value, dict):
        return None
    action_id = value.get("id")
    if isinstance(action_id, bool) or not isinstance(action_id, int):
        return None
    raw_data = value.get("data", {})
    data = raw_data if isinstance(raw_data, dict) else {}
    payload: list[tuple[str, ActionAtom]] = []
    for name, atom in data.items():
        if name == "game_id" or isinstance(atom, bool):
            continue
        if isinstance(atom, (int, str)):
            payload.append((str(name), atom))
    return ActionIdentity(action_id, tuple(sorted(payload)))


def audit_recording(path: Path) -> dict[str, object]:
    typer = ProspectiveActionEffectTyper()
    previous: tuple[Frame, int, ActionIdentity | None] | None = None
    recent_kinds: deque[str] = deque(maxlen=8)
    sequence = 0
    transitions = 0
    progress_events: list[dict[str, object]] = []
    typed_exposures: Counter[tuple[str, ...]] = Counter()
    typed_progress: Counter[tuple[str, ...]] = Counter()
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            payload = json.loads(line)["data"]
            current_frame = _frame(payload.get("frame"))
            current_level = int(payload.get("levels_completed", 0))
            current_state = str(payload.get("state", ""))
            current_action = _action(payload.get("action_input"))
            if previous is not None:
                before, previous_level, action = previous
                transitions += 1
                progressed = current_level > previous_level
                reset = current_state == "GAME_OVER" or (
                    action is not None and action.action_id == 0
                )
                if (
                    action is not None
                    and action.action_id != 0
                    and not action.payload
                ):
                    prior_signature = tuple(
                        sorted(
                            item.kind
                            for item in typer.authoritative_types()
                            if item.action == action
                        )
                    )
                    if prior_signature:
                        typed_exposures[prior_signature] += 1
                    if progressed:
                        if prior_signature:
                            typed_progress[prior_signature] += 1
                        progress_events.append(
                            {
                                "from_level": previous_level,
                                "to_level": current_level,
                                "action_id": action.action_id,
                                "prior_authoritative_signature": prior_signature,
                                "recent_positive_effect_kinds": tuple(
                                    recent_kinds
                                ),
                                "prospectively_typed": bool(prior_signature),
                            }
                        )
                    elif not reset and previous_level == current_level:
                        update = typer.observe(
                            sequence=sequence,
                            action=action,
                            before=before,
                            after=current_frame,
                        )
                        sequence += 1
                        if update.kind != "render-noop":
                            recent_kinds.append(update.kind)
                if progressed or reset:
                    typer.reset_episode()
                    recent_kinds.clear()
                    sequence = 0
            previous = (current_frame, current_level, current_action)
    return {
        "recording": str(path),
        "recording_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "transitions": transitions,
        "progress_event_count": len(progress_events),
        "prospectively_typed_progress_event_count": sum(
            bool(item["prospectively_typed"]) for item in progress_events
        ),
        "progress_events": progress_events,
        "typed_signature_exposures": {
            "|".join(signature): count
            for signature, count in sorted(typed_exposures.items())
        },
        "typed_signature_progress": {
            "|".join(signature): count
            for signature, count in sorted(typed_progress.items())
        },
    }


def audit_root(root: Path) -> dict[str, object]:
    results: dict[str, object] = {}
    signature_exposures: Counter[str] = Counter()
    signature_progress: Counter[str] = Counter()
    for game_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        recordings = tuple(sorted(game_dir.glob("*.jsonl")))
        if len(recordings) != 1:
            raise RuntimeError(
                f"expected one recording for {game_dir.name}, "
                f"found {len(recordings)}"
            )
        result = audit_recording(recordings[0])
        results[game_dir.name] = result
        signature_exposures.update(result["typed_signature_exposures"])
        signature_progress.update(result["typed_signature_progress"])
    return {
        "format": "reflector-progress-effect-motif-audit-v1",
        "recordings_root": str(root),
        "games": len(results),
        "progress_events": sum(
            int(result["progress_event_count"])
            for result in results.values()
            if isinstance(result, dict)
        ),
        "prospectively_typed_progress_events": sum(
            int(result["prospectively_typed_progress_event_count"])
            for result in results.values()
            if isinstance(result, dict)
        ),
        "typed_signature_exposures": dict(sorted(signature_exposures.items())),
        "typed_signature_progress": dict(sorted(signature_progress.items())),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--recordings-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = audit_root(args.recordings_root)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
