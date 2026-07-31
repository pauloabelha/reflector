"""Audit prospective partial bisimulation over grounded action/effect profiles."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from collections.abc import Hashable
from dataclasses import dataclass, field
from pathlib import Path

from scripts.audit_terminal_viability_quotients import (
    _action_domain,
    _grounded_role,
    _transition_rows,
)

type Outcome = tuple[str, ...]
type Profile = dict[Hashable, set[Outcome]]

IGNORED_EFFECTS = frozenset(
    {
        "frame_changed",
        "novel_state_reached",
    }
)


def _effect_names(transition: dict[str, object]) -> frozenset[str]:
    result = transition.get("result")
    if not isinstance(result, list):
        return frozenset()
    return frozenset(
        str(item).split("(", 1)[0]
        for item in result
        if isinstance(item, str) and item
    )


def causal_outcome(
    transition: dict[str, object],
    *,
    terminal: bool,
) -> Outcome:
    """Compress a rendered transition into causal effect families."""

    effects = _effect_names(transition)
    if "level_advanced" in effects:
        return ("progress",)
    if terminal:
        return ("terminal",)
    classes = []
    if effects & {
        "object_appeared",
        "object_disappeared",
        "area_changed",
    }:
        classes.append("structural")
    if effects & {
        "object_moved",
        "orientation_delta",
        "rotated_90",
        "rotated_180",
    }:
        classes.append("motion")
    if effects & {
        "state_changed",
        "color_changed",
    }:
        classes.append("phase")
    residual = effects - IGNORED_EFFECTS - {
        "level_advanced",
        "object_appeared",
        "object_disappeared",
        "area_changed",
        "object_moved",
        "orientation_delta",
        "rotated_90",
        "rotated_180",
        "state_changed",
        "color_changed",
    }
    classes.extend(sorted(f"effect:{name}" for name in residual))
    return tuple(classes) if classes else ("render-noop",)


def _deterministic(profile: Profile, role: Hashable) -> Outcome | None:
    outcomes = profile.get(role)
    if outcomes is None or len(outcomes) != 1:
        return None
    return next(iter(outcomes))


def compatible_profiles(
    left: Profile,
    right: Profile,
    *,
    min_shared_roles: int = 1,
) -> bool:
    """Whether observed overlapping roles define a commuting partial square."""

    shared = set(left) & set(right)
    if len(shared) < min_shared_roles:
        return False
    return all(
        len(left[role]) == 1
        and len(right[role]) == 1
        and left[role] == right[role]
        for role in shared
    )


@dataclass(slots=True)
class ProspectiveAudit:
    profiles: dict[str, Profile] = field(
        default_factory=lambda: defaultdict(dict)
    )
    domains: dict[str, tuple[int, ...]] = field(default_factory=dict)
    predictions: int = 0
    confirmations: int = 0
    conflicts: int = 0
    ambiguous_predictions: int = 0
    abstract_frontier_roles: int = 0
    prediction_outcomes: Counter[Outcome] = field(default_factory=Counter)

    def observe(
        self,
        *,
        source: str,
        domain: tuple[int, ...],
        role: Hashable,
        outcome: Outcome,
    ) -> None:
        source_profile = self.profiles[source]
        donors = [
            profile
            for state, profile in self.profiles.items()
            if state != source
            and self.domains.get(state) == domain
            and compatible_profiles(source_profile, profile)
        ]
        frontier = {
            donor_role
            for donor in donors
            for donor_role in donor
            if donor_role not in source_profile
            and _deterministic(donor, donor_role) is not None
        }
        self.abstract_frontier_roles += len(frontier)
        if role not in source_profile:
            predictions = {
                predicted
                for donor in donors
                if (predicted := _deterministic(donor, role)) is not None
            }
            if len(predictions) == 1:
                predicted = next(iter(predictions))
                self.predictions += 1
                self.prediction_outcomes[predicted] += 1
                if predicted == outcome:
                    self.confirmations += 1
                else:
                    self.conflicts += 1
            elif len(predictions) > 1:
                self.ambiguous_predictions += 1
        source_profile.setdefault(role, set()).add(outcome)
        self.domains[source] = domain


def _static_profile_metrics(
    profiles: dict[str, Profile],
    domains: dict[str, tuple[int, ...]],
) -> dict[str, int]:
    states = sorted(profiles)
    compatible_pairs = 0
    conflicting_pairs = 0
    compressed_states: set[str] = set()
    for index, left_state in enumerate(states):
        left = profiles[left_state]
        for right_state in states[index + 1 :]:
            if domains.get(left_state) != domains.get(right_state):
                continue
            right = profiles[right_state]
            shared = set(left) & set(right)
            if not shared:
                continue
            if compatible_profiles(left, right):
                compatible_pairs += 1
                compressed_states.update((left_state, right_state))
            else:
                conflicting_pairs += 1
    nondeterministic_state_roles = sum(
        len(outcomes) > 1
        for profile in profiles.values()
        for outcomes in profile.values()
    )
    return {
        "profiled_states": len(states),
        "states_with_compatible_peer": len(compressed_states),
        "compatible_state_pairs": compatible_pairs,
        "conflicting_state_pairs": conflicting_pairs,
        "nondeterministic_state_roles": nondeterministic_state_roles,
    }


def audit_stream(path: Path) -> dict[str, object]:
    """Audit one game without sharing state or evidence with any other game."""

    audit = ProspectiveAudit()
    rows = _transition_rows(path)
    outcome_counts: Counter[Outcome] = Counter()
    for row in rows:
        transition = row["transition"]
        if not isinstance(transition, dict):
            continue
        source = str(row["source_digest"])
        outcome = causal_outcome(
            transition,
            terminal=bool(row["terminal"]),
        )
        outcome_counts[outcome] += 1
        audit.observe(
            source=source,
            domain=_action_domain(transition),
            role=_grounded_role(transition),
            outcome=outcome,
        )
    return {
        "stream": str(path),
        "transitions": len(rows),
        **_static_profile_metrics(audit.profiles, audit.domains),
        "prospective_predictions": audit.predictions,
        "prospective_confirmations": audit.confirmations,
        "prospective_conflicts": audit.conflicts,
        "ambiguous_predictions": audit.ambiguous_predictions,
        "abstract_frontier_roles": audit.abstract_frontier_roles,
        "prediction_outcomes": {
            json.dumps(outcome): count
            for outcome, count in sorted(audit.prediction_outcomes.items())
        },
        "outcomes": {
            json.dumps(outcome): count
            for outcome, count in sorted(outcome_counts.items())
        },
    }


def audit_root(root: Path) -> dict[str, object]:
    """Aggregate immutable per-game audits while retaining process boundaries."""

    results = {
        path.name.split(".", 1)[0]: audit_stream(path)
        for path in sorted(root.glob("*.cognitive.jsonl"))
    }
    integer_metrics = (
        "transitions",
        "profiled_states",
        "states_with_compatible_peer",
        "compatible_state_pairs",
        "conflicting_state_pairs",
        "nondeterministic_state_roles",
        "prospective_predictions",
        "prospective_confirmations",
        "prospective_conflicts",
        "ambiguous_predictions",
        "abstract_frontier_roles",
    )
    aggregate: dict[str, int | float] = {
        metric: sum(
            value
            for result in results.values()
            if isinstance((value := result.get(metric)), int)
        )
        for metric in integer_metrics
    }
    predictions = int(aggregate["prospective_predictions"])
    aggregate["prospective_precision"] = (
        aggregate["prospective_confirmations"] / predictions
        if predictions
        else 0.0
    )
    return {
        "format": "reflector-partial-bisimulation-audit-v1",
        "cognitive_root": str(root),
        "games": len(results),
        "aggregate": aggregate,
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
