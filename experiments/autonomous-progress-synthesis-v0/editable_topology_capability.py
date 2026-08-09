"""Game-blind adapter for observed-state editable-topology search.

The transferable capability contains no action semantics or visual addresses.
Opaque intervention channels and grounded component points live only in its
situated binding.  Search is bounded, and neither a proposal nor a discovered
plan carries empirical support; only separately cited environment transitions
may adjudicate it.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Callable, Hashable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "progress-drive-editable-topology-v0" / "editable_topology.py"


def _load_source() -> Any:
    resolved = SOURCE.resolve()
    for module in reversed(tuple(sys.modules.values())):
        path = getattr(module, "__file__", None)
        if path is not None and Path(path).resolve() == resolved:
            return module
    spec = importlib.util.spec_from_file_location("autonomous_editable_topology_source", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("editable-topology source is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


TOPOLOGY = _load_source()
PROTOCOL = "autonomous-editable-topology-capability-v0"
AST_PROTOCOL = "autonomous-progress-goal-v0"
MAX_POINTS = 32
MAX_INTERVENTIONS = 160
MAX_DEPTH = 32
MAX_EXPANSIONS = 100_000


class TopologyCapabilityError(ValueError):
    pass


@dataclass(frozen=True)
class TopologyCapability:
    candidate_id: str
    binding_id: str
    goal_ast: Mapping[str, Any]
    attention: int
    empirical_support: int
    interventions: tuple[Any, ...]
    max_depth: int
    max_expansions: int


@dataclass(frozen=True)
class TopologyPlan:
    candidate_id: str
    binding_id: str
    commands: tuple[Any, ...]
    expanded: int
    observed_state_count: int
    empirical_support: int = 0


@dataclass(frozen=True)
class TopologyEvidence:
    candidate_id: str
    binding_id: str
    transition_ids: tuple[str, ...]
    completed: bool
    direct: bool
    support_delta: int
    created_by: str = "environment"


def stable_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def generic_goal_ast() -> dict[str, Any]:
    """A transferable mechanism hypothesis, with no situated control data."""

    return {
        "protocol": AST_PROTOCOL,
        "type": "GoalPotential",
        "potential": {
            "type": "UnresolvedTopologyCount",
            "direction": "minimize",
            "lower_bound": 0,
        },
        "mechanism": {
            "type": "EditableTopology",
            "claim": "a grounded intervention may change future reachability",
        },
        "terminal": {"type": "EnvironmentCompletion"},
    }


def _grid(raw: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    value = tuple(tuple(map(int, row)) for row in raw)
    if not value or not value[0] or any(len(row) != len(value[0]) for row in value):
        raise TopologyCapabilityError("initial observation must be a nonempty rectangle")
    return value


def _token(
    kind: str,
    channel_index: int,
    point_index: int | None = None,
    *,
    opaque_channel: int,
) -> str:
    return "iv:" + stable_hash(
        {
            "kind": kind,
            "channel_index": channel_index,
            "point_index": point_index,
            "opaque_channel": opaque_channel,
        }
    )[:16]


def compile_capability(
    initial: Sequence[Sequence[int]],
    *,
    simple_actions: Sequence[int],
    parameterized_actions: Sequence[int],
    attention: int = 75,
    max_points: int = MAX_POINTS,
    max_depth: int = MAX_DEPTH,
    max_expansions: int = MAX_EXPANSIONS,
) -> TopologyCapability:
    """Ground a bounded search vocabulary from current pixels and legal channels."""

    grid = _grid(initial)
    simple = tuple(sorted(set(map(int, simple_actions))))
    parameterized = tuple(sorted(set(map(int, parameterized_actions))))
    if set(simple).intersection(parameterized):
        raise TopologyCapabilityError("simple and parameterized channels must be disjoint")
    if not simple and not parameterized:
        raise TopologyCapabilityError("at least one legal opaque intervention is required")
    if type(attention) is not int or not 0 <= attention <= 100:
        raise TopologyCapabilityError("attention is outside the bounded range")
    if not 1 <= max_points <= MAX_POINTS:
        raise TopologyCapabilityError("grounded-point bound is invalid")
    if not 1 <= max_depth <= MAX_DEPTH or not 1 <= max_expansions <= MAX_EXPANSIONS:
        raise TopologyCapabilityError("search bound exceeds the frozen capability limit")

    counts = Counter(value for row in grid for value in row)
    inferred_background = frozenset(
        value for value, _count in counts.most_common(min(2, len(counts)))
    )
    panel = TOPOLOGY.grounded_interaction_points(
        grid,
        background_values=inferred_background,
    )
    scene = TOPOLOGY.grounded_object_points(
        grid,
        background_values=None,
        max_components=max_points,
    )
    points = tuple(sorted(set((*panel, *scene))))[:max_points]

    interventions = [
        TOPOLOGY.Intervention(
            _token("simple", index, opaque_channel=action), action
        )
        for index, action in enumerate(simple)
    ]
    for channel_index, action in enumerate(parameterized):
        for point_index, (x, y) in enumerate(points):
            interventions.append(
                TOPOLOGY.Intervention(
                    _token(
                        "grounded",
                        channel_index,
                        point_index,
                        opaque_channel=action,
                    ),
                    action,
                    (("x", int(x)), ("y", int(y))),
                )
            )
    if len(interventions) > MAX_INTERVENTIONS:
        raise TopologyCapabilityError("situated intervention vocabulary exceeds bound")
    ast = generic_goal_ast()
    candidate_id = "goal:" + stable_hash(ast)
    binding_basis = {
        "candidate_id": candidate_id,
        "simple_channel_count": len(simple),
        "parameterized_channel_count": len(parameterized),
        "point_count": len(points),
        "intervention_tokens": [item.token for item in interventions],
    }
    return TopologyCapability(
        candidate_id=candidate_id,
        binding_id="binding:" + stable_hash(binding_basis),
        goal_ast=ast,
        attention=attention,
        empirical_support=0,
        interventions=tuple(interventions),
        max_depth=max_depth,
        max_expansions=max_expansions,
    )


def plan(
    capability: TopologyCapability,
    *,
    observe_prefix: Callable[[tuple[Any, ...]], Mapping[str, object]],
    state_key: Callable[[Mapping[str, object]], Hashable],
    completed: Callable[[Mapping[str, object]], bool],
    viable: Callable[[Mapping[str, object]], bool] = lambda _state: True,
    interventions_for_state: Callable[[Mapping[str, object]], Sequence[Any]] | None = None,
) -> TopologyPlan:
    """Search only through observations returned by the supplied transition oracle."""

    result = TOPOLOGY.search_observed_state_space(
        capability.interventions,
        observe_prefix=observe_prefix,
        state_key=state_key,
        completed=completed,
        viable=viable,
        interventions_for_state=interventions_for_state,
        max_depth=capability.max_depth,
        max_expansions=capability.max_expansions,
    )
    return TopologyPlan(
        candidate_id=capability.candidate_id,
        binding_id=capability.binding_id,
        commands=tuple(result.plan),
        expanded=result.expanded,
        observed_state_count=result.observed_state_count,
        empirical_support=0,
    )


def adjudicate(
    capability: TopologyCapability,
    *,
    transition_ids: Sequence[str],
    completed: bool,
    direct: bool,
    actor: str,
) -> TopologyEvidence:
    """Create support-bearing evidence only from environment-authored transitions."""

    if actor != "environment":
        raise TopologyCapabilityError("only environment may adjudicate topology support")
    ids = tuple(str(value) for value in transition_ids)
    if not ids or len(ids) != len(set(ids)) or any(not value for value in ids):
        raise TopologyCapabilityError("adjudication requires unique transition addresses")
    support_delta = 1 if completed and direct else 0
    return TopologyEvidence(
        candidate_id=capability.candidate_id,
        binding_id=capability.binding_id,
        transition_ids=ids,
        completed=bool(completed),
        direct=bool(direct),
        support_delta=support_delta,
    )


def registry_proposal(capability: TopologyCapability) -> dict[str, Any]:
    """Fields consumed by capability_registry.CapabilityProposal."""

    return {
        "capability": "interactive:editable-topology",
        "goal_ast": dict(capability.goal_ast),
        "attention": capability.attention,
        "empirical_support": 0,
        "execution": capability,
        "interactive": True,
    }


def workspace_document(capability: TopologyCapability, *, include_binding: bool = False) -> dict[str, Any]:
    """Render generic semantics; situated channels are opt-in and action-opaque."""

    document: dict[str, Any] = {
        "protocol": PROTOCOL,
        "candidate_id": capability.candidate_id,
        "goal_ast": dict(capability.goal_ast),
        "attention": capability.attention,
        "empirical_support": 0,
        "authority": "only-direct-environment-evidence-changes-support",
    }
    if include_binding:
        document["situated_binding"] = {
            "binding_id": capability.binding_id,
            "intervention_refs": [item.token for item in capability.interventions],
            "grounded_parameter_count": sum(bool(item.data) for item in capability.interventions),
            "search_bounds": {
                "max_depth": capability.max_depth,
                "max_expansions": capability.max_expansions,
            },
        }
    return document


__all__ = [
    "AST_PROTOCOL",
    "MAX_DEPTH",
    "MAX_EXPANSIONS",
    "MAX_INTERVENTIONS",
    "MAX_POINTS",
    "PROTOCOL",
    "TopologyCapability",
    "TopologyCapabilityError",
    "TopologyEvidence",
    "TopologyPlan",
    "adjudicate",
    "compile_capability",
    "generic_goal_ast",
    "plan",
    "registry_proposal",
    "stable_hash",
    "workspace_document",
]
