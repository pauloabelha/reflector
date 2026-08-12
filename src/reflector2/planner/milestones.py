"""Derive a very small milestone-shadow frontier from an active explanation."""

from __future__ import annotations

from hashlib import sha256
import json
from typing import Any

from .factorization import MilestoneShadow


TOLERANCE = 0.01


def milestone_satisfied(
    milestone: MilestoneShadow,
    value: float | None,
    initial: float | None,
    *,
    tolerance: float = TOLERANCE,
) -> bool:
    """Evaluate one projected milestone against a prospective measurement."""

    if value is None:
        return False
    if milestone.relation == "reached":
        return milestone.target is not None and abs(value - milestone.target) <= tolerance
    if initial is None:
        return False
    if milestone.relation == "decrease":
        return value < initial - tolerance
    if milestone.relation == "increase":
        return value > initial + tolerance
    if milestone.relation in {"maintain", "stable"}:
        return abs(value - initial) <= tolerance
    return False


def _id(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"milestone-shadow:{sha256(body.encode('utf-8')).hexdigest()}"


def derive_milestones(
    *,
    explanation_id: str,
    active_observable: str,
    preferred_direction: str,
    terminal_observable: str | None = None,
    terminal_value: float | None = 0.0,
    max_milestones: int = 4,
    preserves: tuple[str, ...] = ("role-identity", "mechanism-applicability"),
) -> tuple[MilestoneShadow, ...]:
    """Project generic residual completions; never infer a route or action."""

    proposals: list[tuple[str, str, str, float | None, bool, tuple[str, ...]]] = []
    terminal_measure = str(terminal_observable or active_observable)
    if terminal_value is not None:
        proposals.append((
            "TerminalCompletion", terminal_measure, "reached", float(terminal_value),
            True, (),
        ))
    if active_observable != terminal_measure or terminal_value is None:
        proposals.append((
            "ResidualReachedZero", active_observable, "reached", 0.0,
            False, ("post-completion-behavior",),
        ))
    proposals.append((
        "ResidualDecreased" if preferred_direction == "decrease" else
        "ResidualIncreased" if preferred_direction == "increase" else
        "ResidualPreserved",
        active_observable,
        preferred_direction,
        None,
        False,
        (),
    ))
    output = []
    seen = set()
    for kind, observable, relation, target, terminal, open_ports in proposals:
        signature = (kind, observable, relation, target, terminal)
        if signature in seen:
            continue
        seen.add(signature)
        value = {
            "explanation": explanation_id,
            "kind": kind,
            "observable": observable,
            "relation": relation,
            "target": target,
            "terminal": terminal,
        }
        output.append(MilestoneShadow(
            shadow_id=_id(value), kind=kind, observable=observable,
            relation=relation, target=target, terminal=terminal,
            preserves=preserves, open_ports=open_ports,
        ))
        if len(output) >= max(1, int(max_milestones)):
            break
    return tuple(output)
