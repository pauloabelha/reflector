"""Chronological read-only audit of prospective translation-law discovery."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from reflector.core.action_translation_algebra import (
    ActionAtom,
    ActionIdentity,
    ActionTranslationAlgebra,
    TranslationLaw,
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


def _law_dict(law: TranslationLaw, episode: int) -> dict[str, object]:
    return {
        "episode": episode,
        "action": {
            "action_id": law.action.action_id,
            "payload": law.action.payload,
        },
        "displacement": law.displacement,
        "proposal_sequence": law.proposal_sequence,
        "prospective_confirmations": law.prospective_confirmations,
        "distinct_source_states": law.distinct_source_states,
    }


def audit_recording(path: Path) -> dict[str, object]:
    learner = ActionTranslationAlgebra()
    previous: tuple[Frame, int, ActionIdentity | None] | None = None
    sequence = 0
    diagnostic_counts: Counter[str] = Counter()
    authoritative: dict[
        tuple[int, ActionIdentity, tuple[int, int]],
        TranslationLaw,
    ] = {}
    episodes = 1
    transitions = 0
    plain_transitions = 0
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
                    update = learner.observe(
                        sequence=sequence,
                        action=action,
                        before=before,
                        after=current_frame,
                    )
                    sequence += 1
                    diagnostic_counts[update.diagnostic] += 1
                    if update.authority is not None:
                        authoritative[
                            (
                                episodes,
                                update.authority.action,
                                update.authority.displacement,
                            )
                        ] = update.authority
                if (
                    previous_level != current_level
                    or current_state == "GAME_OVER"
                    or (action is not None and action.action_id == 0)
                ):
                    learner.reset_episode()
                    sequence = 0
                    episodes += 1
            previous = (current_frame, current_level, current_action)
    laws = tuple(
        sorted(
            authoritative.items(),
            key=lambda item: (
                item[0][0],
                item[1].action,
                item[1].displacement,
            ),
        )
    )
    inverse_pairs = {
        (
            left_key[0],
            tuple(sorted((left.displacement, right.displacement))),
        )
        for index, (left_key, left) in enumerate(laws)
        for right_key, right in laws[index + 1 :]
        if left_key[0] == right_key[0]
        and left.displacement
        == (-right.displacement[0], -right.displacement[1])
    }
    return {
        "recording": str(path),
        "recording_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "transitions": transitions,
        "plain_transitions": plain_transitions,
        "episodes": episodes,
        "authoritative_laws": tuple(
            _law_dict(law, key[0]) for key, law in laws
        ),
        "authoritative_law_count": len(laws),
        "inverse_displacement_pair_count": len(inverse_pairs),
        "diagnostics": dict(sorted(diagnostic_counts.items())),
    }


def audit_root(root: Path) -> dict[str, object]:
    results: dict[str, object] = {}
    for game_dir in sorted(path for path in root.iterdir() if path.is_dir()):
        recordings = tuple(sorted(game_dir.glob("*.jsonl")))
        if len(recordings) != 1:
            raise RuntimeError(
                f"expected one recording for {game_dir.name}, "
                f"found {len(recordings)}"
            )
        results[game_dir.name] = audit_recording(recordings[0])
    return {
        "format": "reflector-action-translation-audit-v1",
        "recordings_root": str(root),
        "games": len(results),
        "games_with_authority": sum(
            bool(result["authoritative_law_count"])
            for result in results.values()
            if isinstance(result, dict)
        ),
        "games_with_inverse_pairs": sum(
            bool(result["inverse_displacement_pair_count"])
            for result in results.values()
            if isinstance(result, dict)
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
