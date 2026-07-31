"""Chronological read-only audit of prospectively typed action effects."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from reflector.core.action_effect_typing import (
    ActionEffectType,
    ProspectiveActionEffectTyper,
)
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


def _type_dict(
    effect_type: ActionEffectType,
    episode: int,
) -> dict[str, object]:
    return {
        "episode": episode,
        "action": {
            "action_id": effect_type.action.action_id,
            "payload": effect_type.action.payload,
        },
        "kind": effect_type.kind,
        "proposal_sequence": effect_type.proposal_sequence,
        "prospective_confirmations": effect_type.prospective_confirmations,
        "distinct_source_states": effect_type.distinct_source_states,
    }


def audit_recording(path: Path) -> dict[str, object]:
    typer = ProspectiveActionEffectTyper()
    previous: tuple[Frame, int, ActionIdentity | None] | None = None
    sequence = 0
    episodes = 1
    transitions = 0
    plain_transitions = 0
    diagnostics: Counter[str] = Counter()
    observed_kinds: Counter[str] = Counter()
    authoritative: dict[
        tuple[int, ActionIdentity, str],
        ActionEffectType,
    ] = {}
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
                if (
                    action is not None
                    and action.action_id != 0
                    and not action.payload
                    and previous_level == current_level
                ):
                    plain_transitions += 1
                    update = typer.observe(
                        sequence=sequence,
                        action=action,
                        before=before,
                        after=current_frame,
                    )
                    sequence += 1
                    diagnostics[update.diagnostic] += 1
                    observed_kinds[update.kind] += 1
                    if update.authority is not None:
                        authoritative[
                            (
                                episodes,
                                update.authority.action,
                                update.authority.kind,
                            )
                        ] = update.authority
                if (
                    previous_level != current_level
                    or current_state == "GAME_OVER"
                    or (action is not None and action.action_id == 0)
                ):
                    typer.reset_episode()
                    sequence = 0
                    episodes += 1
            previous = (current_frame, current_level, current_action)
    effect_types = tuple(
        sorted(
            authoritative.items(),
            key=lambda item: (
                item[0][0],
                item[1].action,
                item[1].kind,
            ),
        )
    )
    return {
        "recording": str(path),
        "recording_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "transitions": transitions,
        "plain_transitions": plain_transitions,
        "episodes": episodes,
        "observed_kinds": dict(sorted(observed_kinds.items())),
        "authoritative_types": tuple(
            _type_dict(effect_type, key[0])
            for key, effect_type in effect_types
        ),
        "authoritative_type_count": len(effect_types),
        "authoritative_nontranslation_type_count": sum(
            effect_type.kind != "relative-translation"
            for _key, effect_type in effect_types
        ),
        "diagnostics": dict(sorted(diagnostics.items())),
    }


def audit_root(root: Path) -> dict[str, object]:
    results: dict[str, object] = {}
    authoritative_kind_games: Counter[str] = Counter()
    for game_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        recordings = tuple(sorted(game_dir.glob("*.jsonl")))
        if len(recordings) != 1:
            raise RuntimeError(
                f"expected one recording for {game_dir.name}, "
                f"found {len(recordings)}"
            )
        result = audit_recording(recordings[0])
        results[game_dir.name] = result
        authoritative_kind_games.update(
            {
                item["kind"]
                for item in result["authoritative_types"]
                if isinstance(item, dict)
            }
        )
    return {
        "format": "reflector-action-effect-type-audit-v1",
        "recordings_root": str(root),
        "games": len(results),
        "games_with_authority": sum(
            bool(result["authoritative_type_count"])
            for result in results.values()
            if isinstance(result, dict)
        ),
        "games_with_nontranslation_authority": sum(
            bool(result["authoritative_nontranslation_type_count"])
            for result in results.values()
            if isinstance(result, dict)
        ),
        "authoritative_kind_game_counts": dict(
            sorted(authoritative_kind_games.items())
        ),
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
