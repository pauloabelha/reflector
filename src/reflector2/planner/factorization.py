"""Epistemically typed runtime artifacts for prospective causal composition.

None of these values is an observation or evidence.  A factorization is a
bounded control justification whose first edge may be submitted to the normal
one-action commit/settlement path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping


@dataclass(frozen=True, slots=True)
class PlannerConfig:
    enabled: bool = True
    max_depth: int = 8
    max_frontier: int = 64
    max_expansions: int = 256
    max_milestones: int = 4
    minimum_effect_support: int = 1
    minimum_effect_confidence: float = 0.6

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "PlannerConfig":
        raw = dict(value or {})
        return cls(
            enabled=bool(raw.get("enabled", True)),
            max_depth=max(1, int(raw.get("max_depth", 8))),
            max_frontier=max(1, int(raw.get("max_frontier", 64))),
            max_expansions=max(1, int(raw.get("max_expansions", 256))),
            max_milestones=max(1, int(raw.get("max_milestones", 4))),
            minimum_effect_support=max(1, int(raw.get("minimum_effect_support", 1))),
            minimum_effect_confidence=float(raw.get("minimum_effect_confidence", 0.6)),
        )

    def document(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "max_depth": self.max_depth,
            "max_frontier": self.max_frontier,
            "max_expansions": self.max_expansions,
            "max_milestones": self.max_milestones,
            "minimum_effect_support": self.minimum_effect_support,
            "minimum_effect_confidence": self.minimum_effect_confidence,
        }


@dataclass(frozen=True, slots=True)
class SupportedCausalEffect:
    command_id: str
    command: Mapping[str, Any]
    actor_delta: tuple[float, float]
    target_delta: tuple[float, float]
    support: int
    contradictions: int
    confidence: float
    risk: int = 0

    @property
    def supported(self) -> bool:
        return self.support > 0 and self.confidence > 0.0


@dataclass(frozen=True, slots=True)
class MilestoneShadow:
    shadow_id: str
    kind: str
    observable: str
    relation: str
    target: float | None
    terminal: bool
    preserves: tuple[str, ...] = ()
    open_ports: tuple[str, ...] = ()

    def document(self) -> dict[str, Any]:
        return {
            "shadow_id": self.shadow_id,
            "kind": self.kind,
            "observable": self.observable,
            "relation": self.relation,
            "target": self.target,
            "terminal": self.terminal,
            "preserves": list(self.preserves),
            "open_ports": list(self.open_ports),
            "epistemic_status": "prospective-shadow",
        }


Transition = Callable[[Any, SupportedCausalEffect], Any | None]
Measure = Callable[[Any, str], float | None]
Invariant = Callable[[Any], bool]
StateKey = Callable[[Any], str]


@dataclass(frozen=True, slots=True)
class ControlProblem:
    explanation_id: str
    verb: str
    initial_state: Any
    active_observable: str
    preferred_direction: str
    initial_value: float
    effects: tuple[SupportedCausalEffect, ...]
    milestones: tuple[MilestoneShadow, ...]
    transition: Transition = field(repr=False, compare=False)
    measure: Measure = field(repr=False, compare=False)
    invariants_hold: Invariant = field(repr=False, compare=False)
    state_key: StateKey = field(repr=False, compare=False)
    protected_invariants: tuple[str, ...] = ()
    model_view: Any | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True, slots=True)
class ProspectiveStep:
    depth: int
    command_id: str
    command: Mapping[str, Any]
    causal_support: int
    causal_confidence: float
    potential_before: float | None
    potential_after: float | None
    state_key: str
    epistemic_status: str = "hypothetical"

    def document(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "command_id": self.command_id,
            "command": dict(self.command),
            "causal_support": self.causal_support,
            "causal_confidence": self.causal_confidence,
            "potential_before": self.potential_before,
            "potential_after": self.potential_after,
            "state_key": self.state_key,
            "epistemic_status": self.epistemic_status,
        }


@dataclass(frozen=True, slots=True)
class ControlFactorization:
    explanation_id: str
    verb: str
    milestone: MilestoneShadow
    steps: tuple[ProspectiveStep, ...]
    protected_invariants: tuple[str, ...]
    terminal_reached: bool
    useful_milestone_reached: bool

    @property
    def first_command(self) -> Mapping[str, Any]:
        return self.steps[0].command


@dataclass(frozen=True, slots=True)
class SearchResult:
    status: str
    factorization: ControlFactorization | None
    expansions: int
    generated: int
    frontier_peak: int
    maximum_depth_reached: int
    elapsed_ms: float
    config: PlannerConfig
    reason: str | None = None
