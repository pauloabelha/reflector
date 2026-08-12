"""Minimum evidence-bounded verb-terminal contribution hypothesis for R2.3."""

from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import json
from typing import Any, Mapping, Sequence

from reflector2.planner import GoalContractBasis


GOAL_CONTRACT_PROTOCOL = "r2-goal-contract-v0"
GOAL_CONTRACT_STATUSES = frozenset({"OPEN", "SUPPORTED", "REFUTED"})
BUILTIN_GOAL_OBSERVABLES = (
    "fit_residual",
    "centroid_distance",
    "boundary_gap",
    "overlap_area",
    "overlap_deficit",
    "containment_violation",
    "symmetry_residual",
)


@dataclass(frozen=True, slots=True)
class StructuredTerminal:
    observable: str
    preferred_order: str
    relation: str
    target: float | str | bool | None

    def __post_init__(self) -> None:
        if self.preferred_order not in {"decrease", "increase", "maintain"}:
            raise ValueError("terminal preferred_order must be decrease, increase, or maintain")
        if self.relation not in {"equals", "minimum", "maximum", "observed"}:
            raise ValueError("unsupported terminal relation")
        if not self.observable:
            raise ValueError("terminal requires a measurable observable")

    def document(self) -> dict[str, Any]:
        return {
            "observable": self.observable,
            "preferred_order": self.preferred_order,
            "relation": self.relation,
            "target": self.target,
        }


@dataclass(frozen=True, slots=True)
class GoalControlSignature:
    """Structural control identity; lexical verb names are aliases."""

    role_interfaces: tuple[str, ...]
    measurable_potential: str
    preferred_order: str
    terminal_relation: str
    terminal_target: float | str | bool | None
    required_invariants: tuple[str, ...] = ()
    measurement_fingerprint: str | None = None

    @property
    def signature_id(self) -> str:
        return _stable_id(self.document()).replace("goal-contract:", "goal-control-signature:")

    def document(self) -> dict[str, Any]:
        return {
            "role_interfaces": list(self.role_interfaces),
            "measurable_potential": self.measurable_potential,
            "preferred_order": self.preferred_order,
            "terminal_relation": self.terminal_relation,
            "terminal_target": self.terminal_target,
            "required_invariants": list(self.required_invariants),
            "measurement_fingerprint": self.measurement_fingerprint,
        }


def _stable_id(value: Mapping[str, Any]) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return f"goal-contract:{sha256(body.encode('utf-8')).hexdigest()}"


def _measurement_fingerprint(value: Mapping[str, Any] | None) -> str | None:
    """Hash the measured function, never its observational provenance."""

    if value is None:
        return None
    semantic = dict(value)
    semantic.pop("basis_opportunity_ref", None)
    return sha256(json.dumps(
        semantic, sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()[:24]


@dataclass(frozen=True, slots=True)
class GoalContract:
    """One falsifiable relation from a grounded verb terminal to the world."""

    contract_id: str
    environment_terminal: str
    contributor_verb: str
    contributor_observable: str
    contributor_relation: str
    contributor_target: float | None
    status: str = "OPEN"
    evidence: tuple[str, ...] = ()
    countercondition: str = "verb-terminal-without-environment-terminal"
    provenance: tuple[str, ...] = ()
    local_terminal: StructuredTerminal | None = None
    control_signature: GoalControlSignature | None = None
    environment_terminal_structure: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if self.status not in GOAL_CONTRACT_STATUSES:
            raise ValueError(f"invalid GoalContract status: {self.status!r}")

    def planner_basis(self) -> GoalContractBasis:
        return GoalContractBasis(
            contract_id=self.contract_id,
            environment_terminal=self.environment_terminal,
            contributor_verb=self.contributor_verb,
            contributor_observable=self.contributor_observable,
            contributor_relation=self.contributor_relation,
            contributor_target=self.contributor_target,
            status=self.status,
            evidence=self.evidence,
            countercondition=self.countercondition,
            provenance=self.provenance,
        )

    def document(self) -> dict[str, Any]:
        return {
            "protocol": GOAL_CONTRACT_PROTOCOL,
            **self.planner_basis().document(),
            "local_terminal": (
                None if self.local_terminal is None else self.local_terminal.document()
            ),
            "control_signature": (
                None if self.control_signature is None else {
                    "signature_id": self.control_signature.signature_id,
                    **self.control_signature.document(),
                }
            ),
            "environment_terminal_structure": (
                None if self.environment_terminal_structure is None
                else dict(self.environment_terminal_structure)
            ),
            "authority": {
                "semantic_model": "proposal-only",
                "r2": "compile-and-maintain-hypothesis",
                "environment": "sole-support-and-refutation-source",
            },
        }


def compile_goal_contract(
    proposal: Mapping[str, Any],
    *,
    contributor_verb: str,
    contributor_observable: str,
    contributor_target: float | None,
    proposal_citations: Sequence[str] = (),
    provenance: Sequence[str] = ("semantic-proposal",),
    role_interfaces: Sequence[str] = ("SpatialEntity", "SpatialEntity"),
    preferred_order: str = "decrease",
    required_invariants: Sequence[str] = (),
    measurement_hypothesis: Mapping[str, Any] | None = None,
) -> GoalContract:
    """Compile model structure as OPEN; proposal text can never support it."""

    raw_environment_terminal = proposal.get("environment_terminal", "")
    if isinstance(raw_environment_terminal, Mapping):
        environment_terminal_structure = dict(raw_environment_terminal)
        environment_terminal = str(raw_environment_terminal.get("observable", "")).strip()
    else:
        environment_terminal_structure = {
            "observable": str(raw_environment_terminal).strip(),
            "relation": "observed", "target": True,
        }
        environment_terminal = str(raw_environment_terminal).strip()
    relation = str(proposal.get("contributor_relation", "reached")).strip()
    countercondition = str(
        proposal.get(
            "countercondition",
            "verb-terminal-without-environment-terminal",
        )
    ).strip()
    if not environment_terminal:
        raise ValueError("GoalContract requires an observable environment_terminal")
    if relation not in {"reached", "minimum", "maximum"}:
        raise ValueError("GoalContract contributor_relation is unsupported")
    raw_local = proposal.get("local_terminal")
    if isinstance(raw_local, Mapping):
        local_terminal = StructuredTerminal(
            observable=str(raw_local.get("observable", "")).strip(),
            preferred_order=str(raw_local.get("preferred_order", preferred_order)).strip(),
            relation=str(raw_local.get("relation", "equals")).strip(),
            target=raw_local.get("target"),
        )
        if local_terminal.observable != str(contributor_observable):
            raise ValueError("GoalContract local terminal must measure the contributor observable")
    else:
        local_terminal = StructuredTerminal(
            observable=str(contributor_observable),
            preferred_order=str(preferred_order),
            relation={"reached": "equals", "minimum": "minimum", "maximum": "maximum"}[relation],
            target=contributor_target,
        )
    signature = GoalControlSignature(
        role_interfaces=tuple(str(item) for item in role_interfaces),
        measurable_potential=local_terminal.observable,
        preferred_order=local_terminal.preferred_order,
        terminal_relation=local_terminal.relation,
        terminal_target=local_terminal.target,
        required_invariants=tuple(sorted(str(item) for item in required_invariants)),
        measurement_fingerprint=_measurement_fingerprint(
            measurement_hypothesis,
        ),
    )
    identity = {
        "environment_terminal": environment_terminal,
        "control_signature": signature.document(),
        "contributor_relation": relation,
        "countercondition": countercondition,
    }
    # Proposal citations remain provenance. They are deliberately not copied to
    # empirical evidence, which only settlement below may append.
    proposal_sources = tuple(str(item) for item in proposal_citations if str(item))
    provenance_sources = tuple(str(item) for item in provenance if str(item))
    return GoalContract(
        contract_id=_stable_id(identity),
        environment_terminal=environment_terminal,
        contributor_verb=str(contributor_verb),
        contributor_observable=str(contributor_observable),
        contributor_relation=relation,
        contributor_target=(
            None if contributor_target is None else float(contributor_target)
        ),
        status="OPEN",
        evidence=(),
        countercondition=countercondition,
        provenance=tuple(dict.fromkeys((*provenance_sources, *proposal_sources))),
        local_terminal=local_terminal,
        control_signature=signature,
        environment_terminal_structure=environment_terminal_structure,
    )


def goal_control_signature(
    proposal: Mapping[str, Any], *,
    role_interfaces: Sequence[str] = ("SpatialEntity", "SpatialEntity"),
    required_invariants: Sequence[str] = (),
) -> GoalControlSignature:
    raw = proposal.get("local_terminal")
    observable = str((raw or {}).get("observable", proposal.get("observable", "")))
    preferred = str((raw or {}).get("preferred_order", proposal.get("direction", "")))
    relation = str((raw or {}).get("relation", "equals"))
    target = (raw or {}).get("target", 0.0 if preferred == "decrease" else None)
    terminal = StructuredTerminal(observable, preferred, relation, target)
    return GoalControlSignature(
        tuple(str(item) for item in role_interfaces), terminal.observable,
        terminal.preferred_order, terminal.relation, terminal.target,
        tuple(sorted(str(item) for item in required_invariants)),
        _measurement_fingerprint(
            proposal.get("measurement_hypothesis")
            if isinstance(proposal.get("measurement_hypothesis"), Mapping)
            else None
        ),
    )


def canonicalize_goal_proposals(
    proposals: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, Any], ...]:
    """Merge lexical aliases only when their complete control structure agrees."""
    grouped: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        signature = goal_control_signature(proposal)
        current = grouped.get(signature.signature_id)
        verb = str(proposal.get("verb", ""))
        if current is None:
            grouped[signature.signature_id] = {
                "control_signature": signature,
                "semantic_aliases": (verb,),
                "proposal": dict(proposal),
            }
        else:
            current["semantic_aliases"] = tuple(dict.fromkeys((*current["semantic_aliases"], verb)))
    return tuple(grouped[key] for key in sorted(grouped))


def settle_goal_contract(
    contract: GoalContract,
    *,
    verb_terminal_observed: bool,
    environment_terminal_observed: bool,
    evidence_ref: str,
    causal_boundary_closed: bool = True,
) -> GoalContract:
    """Settle only the cited contributor relation, never unrelated success."""

    citation = str(evidence_ref).strip()
    if not citation:
        raise ValueError("GoalContract settlement requires an environment evidence citation")
    if not verb_terminal_observed:
        # Environment success without the cited verb completion is unrelated to
        # this relation and therefore supplies it no support.
        return contract
    if environment_terminal_observed:
        return replace(
            contract,
            status="SUPPORTED",
            evidence=tuple(dict.fromkeys((*contract.evidence, citation))),
        )
    if causal_boundary_closed:
        return replace(
            contract,
            status="REFUTED",
            evidence=tuple(dict.fromkeys((*contract.evidence, citation))),
        )
    return contract
