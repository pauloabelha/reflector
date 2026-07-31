"""Compare causal version-space queries with transported progress distance."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Hashable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.audit_partial_bisimulation import (
    Profile,
    _deterministic,
    causal_outcome,
    compatible_profiles,
)
from scripts.audit_terminal_viability_quotients import (
    _action_domain,
    _grounded_role,
    _objects,
)


@dataclass(frozen=True, slots=True)
class ChronologicalRow:
    source: str
    level: int
    reason: str
    transition: dict[str, object]
    terminal: bool


def _rows(path: Path) -> tuple[ChronologicalRow, ...]:
    output = []
    previous_digest = ""
    previous_level = 0
    previous_reason = ""
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
                output.append(
                    ChronologicalRow(
                        source=previous_digest,
                        level=previous_level,
                        reason=previous_reason,
                        transition=transition,
                        terminal=observation.get("state") == "GAME_OVER",
                    )
                )
            digest = observation.get("frame_digest")
            previous_digest = str(digest) if isinstance(digest, str) else ""
            level = observation.get("levels_completed")
            previous_level = (
                int(level)
                if isinstance(level, int) and not isinstance(level, bool)
                else previous_level
            )
            decision = event.get("decision")
            previous_reason = (
                str(decision.get("reason", ""))
                if isinstance(decision, dict)
                else ""
            )
    return tuple(output)


def _candidate_roles(transition: dict[str, object]) -> set[Hashable]:
    domain = _action_domain(transition)
    roles: set[Hashable] = {
        (action,) for action in domain if action != 6
    }
    if 6 not in domain:
        return roles
    roles.add((6, "background"))
    roles.update(
        (6, color, area, width, height)
        for color, area, _x, _y, width, height in _objects(transition)
    )
    return roles


def _generic(reason: str) -> bool:
    return (
        "hierarchical-action-family" in reason
        or "untried-current-state" in reason
        or "navigate-known-state-graph" in reason
        or "least-repeated-exhausted-state" in reason
    )


def _compatible_donors(
    profiles: dict[str, Profile],
    domains: dict[str, tuple[int, ...]],
    *,
    source: str,
    domain: tuple[int, ...],
) -> tuple[Profile, ...]:
    source_profile = profiles.get(source, {})
    return tuple(
        profile
        for state, profile in profiles.items()
        if state != source
        and domains.get(state) == domain
        and compatible_profiles(source_profile, profile)
    )


def _expected_elimination(counts: Counter[tuple[str, ...]]) -> float:
    total = sum(counts.values())
    if total == 0:
        return 0.0
    return total - sum(count * count for count in counts.values()) / total


def audit_cegis(rows: tuple[ChronologicalRow, ...]) -> dict[str, int | float]:
    """Measure chronological actions that distinguish compatible donors."""

    profiles: dict[str, Profile] = defaultdict(dict)
    domains: dict[str, tuple[int, ...]] = {}
    current_level: int | None = None
    metrics: Counter[str] = Counter()
    best_expected_total = 0.0
    for row in rows:
        if current_level != row.level:
            profiles = defaultdict(dict)
            domains = {}
            current_level = row.level
        transition = row.transition
        source_profile = profiles[row.source]
        domain = _action_domain(transition)
        role = _grounded_role(transition)
        outcome = causal_outcome(transition, terminal=row.terminal)
        donors = _compatible_donors(
            profiles,
            domains,
            source=row.source,
            domain=domain,
        )
        predicted_groups: dict[tuple[str, ...], int] = Counter(
            predicted
            for donor in donors
            if (predicted := _deterministic(donor, role)) is not None
        )
        if role not in source_profile and len(predicted_groups) > 1:
            hypotheses = sum(predicted_groups.values())
            eliminated = hypotheses - predicted_groups.get(outcome, 0)
            metrics["executed_ambiguous_queries"] += 1
            metrics["donor_hypotheses"] += hypotheses
            metrics["eliminated_hypotheses"] += eliminated
            metrics["queries_with_elimination"] += int(eliminated > 0)
            metrics["generic_queries"] += int(_generic(row.reason))
        opportunity_roles = 0
        best_expected = 0.0
        for candidate in _candidate_roles(transition) - set(source_profile):
            counts: Counter[tuple[str, ...]] = Counter(
                predicted
                for donor in donors
                if (predicted := _deterministic(donor, candidate)) is not None
            )
            if len(counts) <= 1:
                continue
            opportunity_roles += 1
            best_expected = max(best_expected, _expected_elimination(counts))
        if opportunity_roles:
            metrics["opportunity_states"] += 1
            metrics["opportunity_roles"] += opportunity_roles
            best_expected_total += best_expected
        source_profile.setdefault(role, set()).add(outcome)
        domains[row.source] = domain
    result: dict[str, int | float] = dict(metrics)
    result["best_expected_eliminations"] = best_expected_total
    hypotheses = metrics["donor_hypotheses"]
    result["executed_elimination_fraction"] = (
        metrics["eliminated_hypotheses"] / hypotheses if hypotheses else 0.0
    )
    return result


type CompletedLevel = tuple[
    dict[str, Profile],
    dict[str, tuple[int, ...]],
    dict[tuple[str, Hashable], int],
]


def audit_progress_transfer(
    rows: tuple[ChronologicalRow, ...],
) -> dict[str, int]:
    """Test cross-level distance labels only after a level has completed."""

    completed: list[CompletedLevel] = []
    metrics: Counter[str] = Counter()
    index = 0
    while index < len(rows):
        level = rows[index].level
        stop = index
        while stop < len(rows) and rows[stop].level == level:
            stop += 1
        segment = rows[index:stop]
        advances = stop < len(rows) and rows[stop].level > level
        profiles: dict[str, Profile] = defaultdict(dict)
        domains: dict[str, tuple[int, ...]] = {}
        occurrences: list[tuple[str, Hashable, int]] = []
        for offset, row in enumerate(segment):
            transition = row.transition
            source_profile = profiles[row.source]
            domain = _action_domain(transition)
            role = _grounded_role(transition)
            outcome = causal_outcome(transition, terminal=row.terminal)
            candidates: list[tuple[int, Hashable]] = []
            for candidate in _candidate_roles(transition) - set(source_profile):
                candidate_distances = []
                outcomes = set()
                for donor_profiles, donor_domains, donor_distances in completed:
                    for donor_state, donor_profile in donor_profiles.items():
                        if (
                            donor_domains.get(donor_state) != domain
                            or not compatible_profiles(
                                source_profile,
                                donor_profile,
                            )
                        ):
                            continue
                        donor_outcome = _deterministic(donor_profile, candidate)
                        distance = donor_distances.get((donor_state, candidate))
                        if donor_outcome is not None and distance is not None:
                            outcomes.add(donor_outcome)
                            candidate_distances.append(distance)
                if candidate_distances and len(outcomes) == 1:
                    candidates.append((min(candidate_distances), candidate))
            if candidates:
                best_distance = min(distance for distance, _role in candidates)
                best_roles = {
                    candidate
                    for distance, candidate in candidates
                    if distance == best_distance
                }
                if len(best_roles) == 1:
                    chosen = role in best_roles
                    generic = _generic(row.reason)
                    metrics["unique_potential_states"] += 1
                    metrics["potential_candidates"] += len(candidates)
                    metrics["base_chose_best"] += int(chosen)
                    metrics["generic_opportunities"] += int(generic)
                    metrics["generic_chose_best"] += int(generic and chosen)
                    progress_within_32 = advances and len(segment) - offset <= 32
                    metrics["best_progress_within_32"] += int(
                        chosen and progress_within_32
                    )
                    metrics["other_progress_within_32"] += int(
                        not chosen and progress_within_32
                    )
            source_profile.setdefault(role, set()).add(outcome)
            domains[row.source] = domain
            occurrences.append((row.source, role, offset))
        if advances:
            level_distances = {
                (source, role): len(segment) - offset
                for source, role, offset in occurrences
            }
            completed.append((dict(profiles), dict(domains), level_distances))
            metrics["completed_donor_levels"] += 1
        index = stop
    return dict(metrics)


def _sum_metrics(results: dict[str, dict[str, Any]], name: str) -> dict[str, Any]:
    keys = {
        key
        for result in results.values()
        for key, value in result[name].items()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    }
    return {
        key: sum(result[name].get(key, 0) for result in results.values())
        for key in sorted(keys)
        if key != "executed_elimination_fraction"
    }


def audit_root(root: Path) -> dict[str, object]:
    results = {}
    for path in sorted(root.glob("*.cognitive.jsonl")):
        rows = _rows(path)
        results[path.name.split(".", 1)[0]] = {
            "stream": str(path),
            "transitions": len(rows),
            "cegis": audit_cegis(rows),
            "progress_transfer": audit_progress_transfer(rows),
        }
    cegis = _sum_metrics(results, "cegis")
    donor_hypotheses = int(cegis.get("donor_hypotheses", 0))
    cegis["executed_elimination_fraction"] = (
        int(cegis.get("eliminated_hypotheses", 0)) / donor_hypotheses
        if donor_hypotheses
        else 0.0
    )
    return {
        "format": "reflector-causal-version-space-audit-v1",
        "cognitive_root": str(root),
        "games": len(results),
        "aggregate": {
            "cegis": cegis,
            "progress_transfer": _sum_metrics(results, "progress_transfer"),
        },
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
