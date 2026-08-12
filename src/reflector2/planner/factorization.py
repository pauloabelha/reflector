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
    max_goal_factorizations: int = 8
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
            max_goal_factorizations=max(
                1, int(raw.get("max_goal_factorizations", 8)),
            ),
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
            "max_goal_factorizations": self.max_goal_factorizations,
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


@dataclass(frozen=True, slots=True)
class GoalContractBasis:
    """Frozen controller projection of one evidence-bounded goal hypothesis.

    The planner cannot change this status or its evidence.  It only uses the
    projection to distinguish verb-terminal reachability from hypothesized
    environment-terminal relevance.
    """

    contract_id: str
    environment_terminal: str
    contributor_verb: str
    contributor_observable: str
    contributor_relation: str
    contributor_target: float | None
    status: str
    evidence: tuple[str, ...] = ()
    countercondition: str = "verb-terminal-without-environment-terminal"
    provenance: tuple[str, ...] = ()

    def document(self) -> dict[str, Any]:
        return {
            "contract_id": self.contract_id,
            "environment_terminal": self.environment_terminal,
            "candidate_contributor": {
                "verb": self.contributor_verb,
                "observable": self.contributor_observable,
                "relation": self.contributor_relation,
                "target": self.contributor_target,
            },
            "status": self.status,
            "evidence": list(self.evidence),
            "countercondition": self.countercondition,
            "provenance": list(self.provenance),
        }


@dataclass(frozen=True, slots=True)
class GoalProspect:
    """Derived bounded planning summary; never observation or evidence."""

    terminal_status: str
    best_supported_depth: int | None
    terminal_reaching_factorizations: int
    minimum_edge_support: int | None
    minimum_edge_confidence: float | None
    unresolved_preconditions: tuple[str, ...]
    protected_invariants: tuple[str, ...]
    identity_risk: str
    expected_local_verb_orientation: str
    search_budget_basis: Mapping[str, Any]
    option_preserving_first_commands: int = 0
    epistemic_status: str = "derived-prospective-summary-not-evidence"

    def document(self) -> dict[str, Any]:
        return {
            "terminal_status": self.terminal_status,
            "best_supported_depth": self.best_supported_depth,
            "terminal_reaching_factorizations": self.terminal_reaching_factorizations,
            "minimum_edge_support": self.minimum_edge_support,
            "minimum_edge_confidence": self.minimum_edge_confidence,
            "unresolved_preconditions": list(self.unresolved_preconditions),
            "protected_invariants": list(self.protected_invariants),
            "identity_risk": self.identity_risk,
            "expected_local_verb_orientation": self.expected_local_verb_orientation,
            "search_budget_basis": dict(self.search_budget_basis),
            "option_preserving_first_commands": self.option_preserving_first_commands,
            "epistemic_status": self.epistemic_status,
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
    goal_contract: GoalContractBasis | None = None
    unresolved_requirements: tuple[str, ...] = ()
    identity_risk: str = "none-known"
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
    current_goal_prospect: GoalProspect | None = None
    successor_goal_prospect: GoalProspect | None = None
    prospect_improvement_kind: str | None = None
