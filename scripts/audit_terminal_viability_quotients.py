"""Audit coarser terminal-edge quotients against all observed safe outcomes."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from collections.abc import Hashable
from pathlib import Path

OBJECT_SIGNATURE = re.compile(
    r"^object_signature\((-?\d+),(-?\d+),(-?\d+),(-?\d+),"
    r"(-?\d+),(-?\d+)\)$"
)


def _transition_rows(path: Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    previous_digest = ""
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            if not isinstance(event, dict):
                continue
            observation = event.get("observation")
            transition = event.get("transition")
            if not isinstance(observation, dict):
                continue
            if isinstance(transition, dict) and transition:
                rows.append(
                    {
                        "transition": transition,
                        "terminal": observation.get("state") == "GAME_OVER",
                        "source_digest": previous_digest,
                    }
                )
            digest = observation.get("frame_digest")
            previous_digest = str(digest) if isinstance(digest, str) else ""
    return rows


def _context(transition: dict[str, object]) -> tuple[str, ...]:
    value = transition.get("context")
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if isinstance(item, str))


def _objects(
    transition: dict[str, object],
) -> tuple[tuple[int, int, int, int, int, int], ...]:
    parsed = []
    for item in _context(transition):
        match = OBJECT_SIGNATURE.match(item)
        if match is not None:
            color, area, cx, cy, width, height = (
                int(value) for value in match.groups()
            )
            parsed.append((color, area, cx, cy, width, height))
    return tuple(parsed)


def _action(transition: dict[str, object]) -> int:
    value = transition.get("action_id")
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else -1


def _action_domain(transition: dict[str, object]) -> tuple[int, ...]:
    output = []
    for item in _context(transition):
        if item.startswith("action_available(") and item.endswith(")"):
            try:
                output.append(int(item[17:-1]))
            except ValueError:
                continue
    return tuple(sorted(output))


def _grounded_role(transition: dict[str, object]) -> Hashable:
    action = _action(transition)
    data = transition.get("action_data")
    if action != 6 or not isinstance(data, dict):
        return (action,)
    x = data.get("x")
    y = data.get("y")
    if not isinstance(x, int) or not isinstance(y, int):
        return (action,)
    containing = []
    for color, area, cx, cy, width, height in _objects(transition):
        if (
            abs(x - cx) <= max(1, width // 2)
            and abs(y - cy) <= max(1, height // 2)
        ):
            containing.append((area, width, height, color))
    if not containing:
        return (action, "background")
    area, width, height, color = min(containing)
    return (action, color, area, width, height)


def signatures(transition: dict[str, object]) -> dict[str, Hashable]:
    """Return a nested family of increasingly contextual quotient keys."""

    action = _action(transition)
    role = _grounded_role(transition)
    objects = _objects(transition)
    object_count = len(objects)
    domain = _action_domain(transition)
    forms = tuple(sorted(Counter((area, width, height) for _, area, _, _, width, height in objects).items()))
    return {
        "action": (action,),
        "action-domain": (action, domain),
        "action-object-count": (action, object_count),
        "grounded-role": role,
        "grounded-role-domain": (role, domain),
        "grounded-role-object-count": (role, object_count),
        "grounded-role-scene-forms": (role, forms),
    }


def audit_root(root: Path) -> dict[str, object]:
    """Measure terminal support, safe aliasing, and prospective activation."""

    by_quotient: dict[
        str,
        dict[Hashable, dict[str, set[str]]],
    ] = defaultdict(
        lambda: defaultdict(lambda: {"terminal": set(), "safe": set()})
    )
    chronological: dict[str, list[tuple[Hashable, str, bool]]] = defaultdict(list)
    games = 0
    transitions = 0
    for path in sorted(root.glob("*.cognitive.jsonl")):
        games += 1
        game = path.name.split(".", 1)[0]
        for row in _transition_rows(path):
            transition = row["transition"]
            if not isinstance(transition, dict):
                continue
            terminal = bool(row["terminal"])
            source = str(row["source_digest"])
            transitions += 1
            for quotient, signature in signatures(transition).items():
                scoped_signature = (game, signature)
                outcome = "terminal" if terminal else "safe"
                by_quotient[quotient][scoped_signature][outcome].add(source)
                chronological[quotient].append(
                    (scoped_signature, source, terminal)
                )

    results: dict[str, object] = {}
    for quotient, edges in sorted(by_quotient.items()):
        candidates = {
            edge: outcomes
            for edge, outcomes in edges.items()
            if len(outcomes["terminal"]) >= 2
        }
        proposals: dict[Hashable, set[str]] = {}
        quarantined: set[Hashable] = set()
        authoritative: set[Hashable] = set()
        confirmations = 0
        post_authority_uses = 0
        confirmation_games: Counter[str] = Counter()
        for edge, source, terminal in chronological[quotient]:
            if edge in quarantined:
                continue
            if not terminal:
                if edge in proposals:
                    proposals.pop(edge, None)
                    authoritative.discard(edge)
                    quarantined.add(edge)
                continue
            sources = proposals.setdefault(edge, set())
            if edge in authoritative:
                post_authority_uses += 1
            if source not in sources:
                sources.add(source)
                if len(sources) == 2:
                    authoritative.add(edge)
                    confirmations += 1
                    if (
                        isinstance(edge, tuple)
                        and edge
                        and isinstance(edge[0], str)
                    ):
                        confirmation_games[edge[0]] += 1
        candidate_games = Counter(
            edge[0]
            for edge in candidates
            if isinstance(edge, tuple) and edge and isinstance(edge[0], str)
        )
        clean_candidate_games = Counter(
            edge[0]
            for edge, outcomes in candidates.items()
            if (
                not outcomes["safe"]
                and isinstance(edge, tuple)
                and edge
                and isinstance(edge[0], str)
            )
        )
        results[quotient] = {
            "represented_edges": len(edges),
            "candidate_edges": len(candidates),
            "candidate_edges_without_safe_alias": sum(
                not outcomes["safe"] for outcomes in candidates.values()
            ),
            "candidate_terminal_events": sum(
                len(outcomes["terminal"]) for outcomes in candidates.values()
            ),
            "candidate_safe_alias_events": sum(
                len(outcomes["safe"]) for outcomes in candidates.values()
            ),
            "prospective_confirmations": confirmations,
            "prospective_quarantines": len(quarantined),
            "post_authority_uses": post_authority_uses,
            "candidate_games": dict(sorted(candidate_games.items())),
            "clean_candidate_games": dict(
                sorted(clean_candidate_games.items())
            ),
            "prospective_confirmation_games": dict(
                sorted(confirmation_games.items())
            ),
        }
    return {
        "format": "reflector-terminal-viability-quotient-audit-v1",
        "cognitive_root": str(root),
        "games": games,
        "transitions": transitions,
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cognitive-root", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = audit_root(args.cognitive_root)
    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
