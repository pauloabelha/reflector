"""Workspace contracts for a support-zero goal-potential intervention lab.

The transferable object says only *what relation would constitute progress*.
Situated entity addresses live in a separate optional binding.  Oracle and
mock interventions can therefore spend attention without acquiring epistemic
authority; only an environment evidence object may change support.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Mapping, Sequence


PROTOCOL = "goal-potential-workspace-v0"
AST_PROTOCOL = "goal-potential-ast-v0"
BINDING_PROTOCOL = "goal-potential-situated-binding-v0"
EVIDENCE_PROTOCOL = "goal-potential-environment-evidence-v0"
MAX_MEMBERS = 32
PROVENANCE_KINDS = frozenset({"oracle_intervention", "mock_intervention"})


class GoalWorkspaceError(ValueError):
    """A goal-potential object violates the intervention contract."""


def stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class GoalPotential:
    candidate_id: str
    provenance: str
    sham: bool
    ast: Mapping[str, Any]


@dataclass(frozen=True)
class SituatedBinding:
    binding_id: str
    candidate_id: str
    observation_id: str
    members: tuple[str, ...]
    container: str
    provenance: str


_FORBIDDEN_KEYS = re.compile(
    r"(?:^|_)(?:action|button|move|color|colour|palette|coord|coordinate|"
    r"bbox|bounding_box|row|column|pixel|mask|game|game_id)(?:$|_)",
    re.IGNORECASE,
)
_ACTION_TEXT = re.compile(
    r"(?:\bACTION[_ -]?\d+\b|\b(?:UP|DOWN|LEFT|RIGHT|CLICK|PRESS)\b)",
    re.IGNORECASE,
)
_COLOR_TEXT = re.compile(
    r"\b(?:red|orange|yellow|green|blue|purple|violet|pink|brown|black|white|gray|grey|cyan|magenta)\b",
    re.IGNORECASE,
)
_GAME_ID_TEXT = re.compile(r"^(?:[a-z]{1,3}\d{2,4}[a-z]?)$", re.IGNORECASE)
_COORD_TEXT = re.compile(r"^-?\d+\s*[,;:]\s*-?\d+$")
_OPAQUE_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{2,127}$")
_ROLE = re.compile(r"^\?[a-z][a-z0-9_]{0,31}$")


def _reject_transfer_leakage(value: Any, *, path: str = "candidate") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            name = str(key)
            if _FORBIDDEN_KEYS.search(name):
                raise GoalWorkspaceError(f"transferable candidate contains forbidden field: {path}.{name}")
            _reject_transfer_leakage(item, path=f"{path}.{name}")
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            _reject_transfer_leakage(item, path=f"{path}[{index}]")
        return
    if isinstance(value, str) and (
        _ACTION_TEXT.search(value)
        or _COLOR_TEXT.search(value)
        or _GAME_ID_TEXT.fullmatch(value)
        or _COORD_TEXT.fullmatch(value)
    ):
        raise GoalWorkspaceError(f"transferable candidate contains forbidden token: {path}")


def goal_ast(*, members_role: str = "?members", container_role: str = "?container") -> dict[str, Any]:
    """The complete bounded AST: zero outsiders iff every member is inside."""

    return {
        "protocol": AST_PROTOCOL,
        "type": "GoalPotential",
        "roles": [members_role, container_role],
        "potential": {
            "type": "OutsideCount",
            "members": members_role,
            "container": container_role,
            "direction": "minimize",
            "lower_bound": 0,
        },
        "terminal": {
            "type": "AllInside",
            "members": members_role,
            "container": container_role,
        },
    }


def validate_ast(ast: Mapping[str, Any]) -> None:
    _reject_transfer_leakage(ast)
    expected = {"protocol", "type", "roles", "potential", "terminal"}
    if not isinstance(ast, Mapping) or set(ast) != expected:
        raise GoalWorkspaceError("GoalPotential AST contract mismatch")
    if ast["protocol"] != AST_PROTOCOL or ast["type"] != "GoalPotential":
        raise GoalWorkspaceError("GoalPotential AST protocol/type mismatch")
    roles = ast["roles"]
    if (
        not isinstance(roles, list)
        or len(roles) != 2
        or len(set(roles)) != 2
        or any(not isinstance(item, str) or not _ROLE.fullmatch(item) for item in roles)
    ):
        raise GoalWorkspaceError("GoalPotential must declare two distinct bounded roles")
    potential = ast["potential"]
    if not isinstance(potential, Mapping) or set(potential) != {
        "type", "members", "container", "direction", "lower_bound"
    }:
        raise GoalWorkspaceError("OutsideCount contract mismatch")
    if (
        potential["type"] != "OutsideCount"
        or potential["members"] != roles[0]
        or potential["container"] != roles[1]
        or potential["direction"] != "minimize"
        or type(potential["lower_bound"]) is not int
        or potential["lower_bound"] != 0
    ):
        raise GoalWorkspaceError("OutsideCount must be nonnegative minimization over declared roles")
    terminal = ast["terminal"]
    if not isinstance(terminal, Mapping) or set(terminal) != {"type", "members", "container"}:
        raise GoalWorkspaceError("AllInside contract mismatch")
    if (
        terminal["type"] != "AllInside"
        or terminal["members"] != roles[0]
        or terminal["container"] != roles[1]
    ):
        raise GoalWorkspaceError("AllInside must use the OutsideCount roles")


def make_candidate(
    *,
    provenance: str,
    sham: bool = False,
    ast: Mapping[str, Any] | None = None,
) -> GoalPotential:
    if provenance not in PROVENANCE_KINDS:
        raise GoalWorkspaceError("unknown intervention provenance")
    if sham != (provenance == "mock_intervention"):
        raise GoalWorkspaceError("sham and provenance must distinguish mock from oracle")
    body = dict(goal_ast() if ast is None else ast)
    validate_ast(body)
    identity = {
        "protocol": PROTOCOL,
        "provenance": provenance,
        "sham": bool(sham),
        "ast": body,
    }
    return GoalPotential(
        candidate_id=f"gp:{stable_hash(identity)}",
        provenance=provenance,
        sham=bool(sham),
        ast=body,
    )


def validate_candidate(candidate: GoalPotential) -> None:
    if not _OPAQUE_ID.fullmatch(candidate.candidate_id) or not candidate.candidate_id.startswith("gp:"):
        raise GoalWorkspaceError("invalid goal-potential ID")
    if candidate.provenance not in PROVENANCE_KINDS:
        raise GoalWorkspaceError("unknown intervention provenance")
    if candidate.sham != (candidate.provenance == "mock_intervention"):
        raise GoalWorkspaceError("sham/provenance mismatch")
    validate_ast(candidate.ast)
    expected = make_candidate(
        provenance=candidate.provenance,
        sham=candidate.sham,
        ast=candidate.ast,
    ).candidate_id
    if candidate.candidate_id != expected:
        raise GoalWorkspaceError("goal-potential identity mismatch")


def candidate_object(candidate: GoalPotential, *, attention_boost: int = 20) -> dict[str, Any]:
    """Workspace object spec. Attention is not support."""

    validate_candidate(candidate)
    if type(attention_boost) is not int or not 0 <= attention_boost <= 100:
        raise GoalWorkspaceError("attention boost outside bounded range")
    return {
        "kind": "goal_potential",
        "created_by": candidate.provenance,
        "identity": {"candidate_id": candidate.candidate_id},
        "payload": {
            "protocol": PROTOCOL,
            "ast": dict(candidate.ast),
            "provenance": candidate.provenance,
            "sham": candidate.sham,
            "intervention_mode": "sham" if candidate.sham else "candidate-attention",
            "empirical_support": 0,
            "attention_boost": attention_boost,
            "epistemic_authority": "attention-only",
        },
        "dependency_ids": [],
    }


def make_binding(
    candidate: GoalPotential,
    *,
    observation_id: str,
    members: Sequence[str],
    container: str,
) -> SituatedBinding:
    validate_candidate(candidate)
    member_ids = tuple(str(item) for item in members)
    if not 1 <= len(member_ids) <= MAX_MEMBERS or len(set(member_ids)) != len(member_ids):
        raise GoalWorkspaceError("situated member population is empty, duplicate, or over bound")
    addresses = (str(observation_id), *member_ids, str(container))
    if any(not _OPAQUE_ID.fullmatch(item) for item in addresses):
        raise GoalWorkspaceError("situated bindings require opaque stable addresses")
    if container in member_ids:
        raise GoalWorkspaceError("container cannot also be a member")
    identity = {
        "candidate_id": candidate.candidate_id,
        "observation_id": str(observation_id),
        "members": list(member_ids),
        "container": str(container),
        "provenance": candidate.provenance,
    }
    return SituatedBinding(
        binding_id=f"gpb:{stable_hash(identity)}",
        candidate_id=candidate.candidate_id,
        observation_id=str(observation_id),
        members=member_ids,
        container=str(container),
        provenance=candidate.provenance,
    )


def binding_object(binding: SituatedBinding) -> dict[str, Any]:
    if not _OPAQUE_ID.fullmatch(binding.binding_id) or not binding.binding_id.startswith("gpb:"):
        raise GoalWorkspaceError("invalid situated binding ID")
    if binding.provenance not in PROVENANCE_KINDS:
        raise GoalWorkspaceError("unknown situated provenance")
    return {
        "kind": "goal_potential_binding",
        "created_by": binding.provenance,
        "identity": {"binding_id": binding.binding_id},
        "payload": {
            "protocol": BINDING_PROTOCOL,
            "candidate_id": binding.candidate_id,
            "observation_id": binding.observation_id,
            "ports": {
                "?members": list(binding.members),
                "?container": binding.container,
            },
            "provenance": binding.provenance,
            "empirical_support": 0,
            "epistemic_authority": "attention-only",
        },
        "dependency_ids": [
            binding.candidate_id,
            binding.observation_id,
            *binding.members,
            binding.container,
        ],
    }


def environment_support_object(
    *,
    candidate_id: str,
    binding_id: str | None,
    evidence_ids: Sequence[str],
    support_delta: int,
    actor: str,
) -> dict[str, Any]:
    """The sole API capable of expressing empirical support change."""

    if actor != "environment":
        raise GoalWorkspaceError("only environment may alter empirical support")
    if type(support_delta) is not int or not -100 <= support_delta <= 100 or support_delta == 0:
        raise GoalWorkspaceError("support delta must be a nonzero bounded integer")
    evidence = tuple(str(item) for item in evidence_ids)
    if not evidence or len(set(evidence)) != len(evidence):
        raise GoalWorkspaceError("environment support requires unique evidence addresses")
    addresses = (str(candidate_id), *evidence)
    if binding_id is not None:
        addresses = (*addresses, str(binding_id))
    if any(not _OPAQUE_ID.fullmatch(item) for item in addresses):
        raise GoalWorkspaceError("environment support contains an invalid address")
    identity = {
        "candidate_id": candidate_id,
        "binding_id": binding_id,
        "evidence_ids": list(evidence),
        "support_delta": support_delta,
    }
    return {
        "kind": "goal_potential_evidence",
        "created_by": "environment",
        "identity": {"evidence_key": f"gpe:{stable_hash(identity)}"},
        "payload": {
            "protocol": EVIDENCE_PROTOCOL,
            **identity,
            "empirical_support_delta": support_delta,
        },
        "dependency_ids": [
            candidate_id,
            *(() if binding_id is None else (binding_id,)),
            *evidence,
        ],
    }


__all__ = [
    "AST_PROTOCOL",
    "BINDING_PROTOCOL",
    "EVIDENCE_PROTOCOL",
    "GoalPotential",
    "GoalWorkspaceError",
    "MAX_MEMBERS",
    "PROTOCOL",
    "PROVENANCE_KINDS",
    "SituatedBinding",
    "binding_object",
    "candidate_object",
    "environment_support_object",
    "goal_ast",
    "make_binding",
    "make_candidate",
    "stable_hash",
    "validate_ast",
    "validate_candidate",
]
