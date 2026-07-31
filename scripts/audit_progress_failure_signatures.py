"""Cluster normalized cognitive motifs adjacent to progress and failure."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from collections.abc import Hashable, Mapping
from pathlib import Path
from typing import Any


def _effect_families(event: dict[str, Any]) -> tuple[str, ...]:
    transition = event.get("transition")
    if not isinstance(transition, dict):
        return ()
    result = transition.get("result")
    if not isinstance(result, list):
        return ()
    return tuple(
        sorted(
            {
                str(item).split("(", 1)[0]
                for item in result
                if isinstance(item, str) and item
            }
        )
    )


def _reason(event: dict[str, Any]) -> str:
    decision = event.get("decision")
    if not isinstance(decision, dict):
        return "unknown"
    value = decision.get("reason")
    return str(value) if isinstance(value, str) and value else "unknown"


def _observation(event: dict[str, Any]) -> tuple[int, str]:
    observation = event.get("observation")
    if not isinstance(observation, dict):
        return (0, "")
    level = observation.get("levels_completed", 0)
    state = observation.get("state", "")
    return (
        int(level) if isinstance(level, int) and not isinstance(level, bool) else 0,
        str(state) if isinstance(state, str) else "",
    )


def _counter_dict[Key: Hashable](
    counter: Mapping[Key, int],
) -> dict[str, int]:
    return {
        json.dumps(key, separators=(",", ":"), ensure_ascii=True): count
        for key, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], repr(item[0])),
        )
    }


def _hashable(value: object) -> Hashable:
    if isinstance(value, list):
        return tuple(_hashable(item) for item in value)
    if isinstance(value, dict):
        return tuple(
            sorted((str(key), _hashable(item)) for key, item in value.items())
        )
    if isinstance(value, Hashable):
        return value
    return repr(value)


def _merge_encoded(
    target: Counter[Any],
    values: object,
) -> None:
    if not isinstance(values, dict):
        return
    for encoded, count in values.items():
        if not isinstance(encoded, str) or not isinstance(count, int):
            continue
        target[_hashable(json.loads(encoded))] += count


def audit_stream(path: Path, *, motif_width: int = 4) -> dict[str, object]:
    """Return bounded normalized motifs without retaining rendered states."""

    recent: list[str] = []
    previous_level = 0
    previous_reason = "unknown"
    progress_advisors: Counter[str] = Counter()
    failure_advisors: Counter[str] = Counter()
    progress_motifs: Counter[tuple[str, ...]] = Counter()
    failure_motifs: Counter[tuple[str, ...]] = Counter()
    progress_effects: Counter[tuple[str, ...]] = Counter()
    failure_effects: Counter[tuple[str, ...]] = Counter()
    events = 0
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            event = json.loads(line)
            if not isinstance(event, dict):
                continue
            events += 1
            level, state = _observation(event)
            reason = _reason(event)
            motif = tuple(recent[-motif_width:])
            effects = _effect_families(event)
            if level > previous_level:
                progress_advisors[previous_reason] += 1
                progress_motifs[motif] += 1
                progress_effects[effects] += 1
            if state == "GAME_OVER" or reason == "reset-required":
                failure_advisors[previous_reason] += 1
                failure_motifs[motif] += 1
                failure_effects[effects] += 1
            recent.append(reason)
            previous_reason = reason
            previous_level = level
    return {
        "stream": str(path),
        "stream_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "events": events,
        "progress_events": sum(progress_advisors.values()),
        "failure_events": sum(failure_advisors.values()),
        "progress_advisors": _counter_dict(progress_advisors),
        "failure_advisors": _counter_dict(failure_advisors),
        "progress_motifs": _counter_dict(progress_motifs),
        "failure_motifs": _counter_dict(failure_motifs),
        "progress_effect_families": _counter_dict(progress_effects),
        "failure_effect_families": _counter_dict(failure_effects),
    }


def audit_root(root: Path, *, motif_width: int = 4) -> dict[str, object]:
    """Aggregate one immutable cognitive stream per game."""

    results: dict[str, dict[str, object]] = {}
    progress_advisors: Counter[str] = Counter()
    failure_advisors: Counter[str] = Counter()
    progress_motifs: Counter[tuple[str, ...]] = Counter()
    failure_motifs: Counter[tuple[str, ...]] = Counter()
    for path in sorted(root.glob("*.cognitive.jsonl")):
        game = path.name.split(".", 1)[0]
        result = audit_stream(path, motif_width=motif_width)
        results[game] = result
        for target, name in (
            (progress_advisors, "progress_advisors"),
            (failure_advisors, "failure_advisors"),
            (progress_motifs, "progress_motifs"),
            (failure_motifs, "failure_motifs"),
        ):
            _merge_encoded(target, result[name])
    progress_events = tuple(
        value
        for result in results.values()
        if isinstance((value := result["progress_events"]), int)
    )
    failure_events = tuple(
        value
        for result in results.values()
        if isinstance((value := result["failure_events"]), int)
    )
    return {
        "format": "reflector-progress-failure-signature-audit-v1",
        "cognitive_root": str(root),
        "motif_width": motif_width,
        "games": len(results),
        "progress_events": sum(progress_events),
        "failure_events": sum(failure_events),
        "progress_advisors": _counter_dict(progress_advisors),
        "failure_advisors": _counter_dict(failure_advisors),
        "progress_motifs": _counter_dict(progress_motifs),
        "failure_motifs": _counter_dict(failure_motifs),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cognitive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--motif-width", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.motif_width <= 16:
        raise SystemExit("--motif-width must be between 1 and 16")
    payload = audit_root(args.cognitive_root, motif_width=args.motif_width)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
