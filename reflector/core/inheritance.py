"""Content-addressed symbolic schemes shipped with an offline descendant."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

EMPTY_SCHEME_LIBRARY_ROOT = (
    "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
)
EMPTY_EVIDENCE_LEDGER_ROOT = EMPTY_SCHEME_LIBRARY_ROOT
EMPTY_COMMON_SENSE_ROOT = (
    "9b720358c129ec040f946ceff6d9bf8e5ee8bd233f1d25824b8aa3d0e19d2611"
)
GROUNDING_KINDS = frozenset(
    {"action-family", "object", "region", "relation", "procedure"}
)


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode()).hexdigest()


def common_sense_root(library_root: str, evidence_root: str) -> str:
    """Bind deployable definitions to the evidence snapshot that admitted them."""

    return _digest(
        {
            "library_root": library_root,
            "ledger_root": evidence_root,
        }
    )


@dataclass(frozen=True, slots=True)
class SchemeDefinition:
    """Immutable meaning of one reusable operation.

    Empirical confidence is deliberately absent. Evidence changes over time;
    changing evidence must not silently change what a content hash denotes.
    """

    name: str
    operator: str
    parameters: tuple[str, ...]
    grounding: tuple[str, ...]
    preconditions: tuple[str, ...] = ()
    effects: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    goal_contract: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    composition: tuple[str, ...] = ()
    falsifiers: tuple[str, ...] = ()
    resource_cap: int = 1
    complexity_cost: int = 1

    def __post_init__(self) -> None:
        if not self.name or not self.operator:
            raise ValueError("scheme name and operator must be non-empty")
        for field_name in (
            "parameters",
            "grounding",
            "preconditions",
            "effects",
            "invariants",
            "goal_contract",
            "dependencies",
            "composition",
            "falsifiers",
        ):
            value = getattr(self, field_name)
            if type(value) is not tuple or any(
                not isinstance(item, str) or not item for item in value
            ):
                raise ValueError(
                    f"scheme {field_name} must be a tuple of non-empty strings"
                )
            if tuple(sorted(set(value))) != value:
                raise ValueError(
                    f"scheme {field_name} must be sorted and duplicate-free"
                )
        unknown_grounding = set(self.grounding) - GROUNDING_KINDS
        if unknown_grounding:
            raise ValueError(
                f"unknown scheme grounding kinds: {sorted(unknown_grounding)}"
            )
        if type(self.resource_cap) is not int or not 1 <= self.resource_cap <= 512:
            raise ValueError("scheme resource_cap must be between 1 and 512")
        if (
            type(self.complexity_cost) is not int
            or not 1 <= self.complexity_cost <= 10_000
        ):
            raise ValueError(
                "scheme complexity_cost must be between 1 and 10000"
            )
        for dependency in self.dependencies:
            if len(dependency) != 64 or any(
                character not in "0123456789abcdef" for character in dependency
            ):
                raise ValueError("scheme dependencies must be SHA-256 hashes")

    @property
    def scheme_id(self) -> str:
        return _digest(asdict(self))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return _canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SchemeDefinition":
        expected = {
            "name",
            "operator",
            "parameters",
            "grounding",
            "preconditions",
            "effects",
            "invariants",
            "goal_contract",
            "dependencies",
            "composition",
            "falsifiers",
            "resource_cap",
            "complexity_cost",
        }
        unknown = set(value) - expected
        missing = {"name", "operator", "parameters", "grounding"} - set(value)
        if unknown or missing:
            raise ValueError(
                f"invalid scheme fields; missing={sorted(missing)}, "
                f"unknown={sorted(unknown)}"
            )
        normalized = dict(value)
        for field_name in expected - {
            "name",
            "operator",
            "resource_cap",
            "complexity_cost",
        }:
            raw = normalized.get(field_name, ())
            if not isinstance(raw, (list, tuple)):
                raise ValueError(f"scheme {field_name} must be an array")
            normalized[field_name] = tuple(raw)
        return cls(**normalized)

    @classmethod
    def from_json(cls, value: str) -> "SchemeDefinition":
        try:
            raw = json.loads(value)
        except json.JSONDecodeError as error:
            raise ValueError("scheme definition must be valid JSON") from error
        if not isinstance(raw, dict):
            raise ValueError("scheme definition must be a JSON object")
        definition = cls.from_dict(raw)
        if definition.to_json() != value:
            raise ValueError("scheme definition JSON must be canonical")
        return definition


@dataclass(frozen=True, slots=True)
class SchemeLibrary:
    """Closed, deterministic Merkle snapshot inherited by one candidate."""

    definitions: tuple[SchemeDefinition, ...] = ()

    def __post_init__(self) -> None:
        identifiers = tuple(item.scheme_id for item in self.definitions)
        if identifiers != tuple(sorted(set(identifiers))):
            raise ValueError(
                "scheme definitions must be sorted by hash and duplicate-free"
            )
        available = set(identifiers)
        for definition in self.definitions:
            missing = set(definition.dependencies) - available
            if missing:
                raise ValueError(
                    f"scheme {definition.scheme_id} has missing dependencies: "
                    f"{sorted(missing)}"
                )

    @classmethod
    def create(
        cls, definitions: Iterable[SchemeDefinition] = ()
    ) -> "SchemeLibrary":
        by_id = {item.scheme_id: item for item in definitions}
        return cls(tuple(by_id[key] for key in sorted(by_id)))

    @classmethod
    def from_json_definitions(
        cls, definitions: Iterable[str]
    ) -> "SchemeLibrary":
        return cls.create(
            SchemeDefinition.from_json(definition)
            for definition in definitions
        )

    @property
    def root(self) -> str:
        return _digest([item.scheme_id for item in self.definitions])

    def json_definitions(self) -> tuple[str, ...]:
        return tuple(item.to_json() for item in self.definitions)

    def merge(self, *others: "SchemeLibrary") -> "SchemeLibrary":
        return self.create(
            item
            for library in (self, *others)
            for item in library.definitions
        )

    def grounded_components(
        self,
        *,
        relation: bool,
        object_bound: bool,
        region_bound: bool,
    ) -> tuple[str, ...]:
        """Return inherited definitions grounded by the current intervention."""

        present = {"action-family"}
        if relation:
            present.add("relation")
        if object_bound:
            present.add("object")
        if region_bound:
            present.add("region")
        return tuple(
            f"scheme:inherited:{definition.scheme_id}"
            for definition in self.definitions
            if definition.operator
            not in {"observe-event", "prioritize-intervention"}
            if set(definition.grounding).issubset(present)
        )


def starter_scheme_library() -> SchemeLibrary:
    """Return content-free priors equivalent to the historical starter forms."""

    specifications = (
        (
            "probe-action-family",
            "intervene",
            ("action-family",),
            ("action-family",),
            1,
        ),
        (
            "intervene-on-object",
            "intervene",
            ("action", "object"),
            ("action-family", "object"),
            2,
        ),
        (
            "intervene-on-region",
            "intervene",
            ("action", "visual-region"),
            ("action-family", "region"),
            3,
        ),
        (
            "repair-relation",
            "intervene",
            ("action", "relation", "source", "target"),
            ("action-family", "object", "relation"),
            3,
        ),
        (
            "bind-manner-to-action",
            "compose",
            ("base-scheme", "modifier-scheme", "role-relation"),
            ("procedure",),
            4,
        ),
        (
            "bounded-novelty",
            "intervene",
            ("action", "untried-state"),
            ("action-family",),
            2,
        ),
    )
    return SchemeLibrary.create(
        SchemeDefinition(
            name=name,
            operator=operator,
            parameters=parameters,
            grounding=tuple(sorted(grounding)),
            falsifiers=("no-predictive-or-pragmatic-credit",),
            resource_cap=8,
            complexity_cost=complexity,
        )
        for name, operator, parameters, grounding, complexity in specifications
    )


def general_reasoning_prior_library() -> SchemeLibrary:
    """Return falsifiable, game-agnostic priors for interactive reasoning."""

    shared_invariants = (
        "no-absolute-coordinate",
        "no-fixed-action-identifier",
        "no-fixed-color",
        "no-game-identifier",
        "prospective-conflict-quarantines-prior",
    )
    specifications = (
        SchemeDefinition(
            name="causal-scene-versus-nuisance-layer",
            operator="propose-representation",
            parameters=("persistent-region", "status-region"),
            grounding=("action-family", "region"),
            preconditions=("repeated-local-feedback",),
            effects=("factor-task-state-from-feedback-state",),
            invariants=shared_invariants,
            falsifiers=("putative-status-region-controls-task-transition",),
            resource_cap=8,
            complexity_cost=3,
        ),
        SchemeDefinition(
            name="persistent-relational-role-identity",
            operator="propose-representation",
            parameters=("object-role", "transformation"),
            grounding=("action-family", "object"),
            preconditions=("structural-role-reappears",),
            effects=("preserve-role-through-transformation",),
            invariants=shared_invariants,
            falsifiers=("role-prediction-conflicts-with-observation",),
            resource_cap=8,
            complexity_cost=2,
        ),
        SchemeDefinition(
            name="local-sparse-conserved-transition",
            operator="propose-transition",
            parameters=("affected-domain", "conserved-content"),
            grounding=("action-family", "object"),
            preconditions=("bounded-structural-effect",),
            effects=("prefer-local-conservative-model",),
            invariants=shared_invariants,
            falsifiers=("observed-effect-requires-nonlocal-nonconservation",),
            resource_cap=8,
            complexity_cost=2,
        ),
        SchemeDefinition(
            name="equivariant-operator-identity",
            operator="propose-transition",
            parameters=("operator", "relational-context"),
            grounding=("action-family", "object", "relation"),
            preconditions=("same-structural-role",),
            effects=("share-operator-across-equivariant-groundings",),
            invariants=tuple(
                sorted(
                    (
                        *shared_invariants,
                        "d4-equivariant",
                        "object-order-invariant",
                        "recoloring-invariant",
                        "translation-invariant",
                    )
                )
            ),
            falsifiers=("equivariant-projection-mismatches",),
            resource_cap=8,
            complexity_cost=3,
        ),
        SchemeDefinition(
            name="boundary-conditioned-no-effect",
            operator="propose-transition",
            parameters=("controller-role", "pose-context"),
            grounding=("action-family", "object", "relation"),
            preconditions=("controller-has-effect-elsewhere", "current-no-effect"),
            effects=("condition-no-effect-on-relational-context",),
            invariants=shared_invariants,
            falsifiers=("same-context-effect-is-inconsistent",),
            resource_cap=8,
            complexity_cost=2,
        ),
        SchemeDefinition(
            name="factored-controllability",
            operator="propose-representation",
            parameters=("action-subset", "controlled-factor"),
            grounding=("action-family", "object", "relation"),
            preconditions=("effects-separate-by-object-or-mode",),
            effects=("factor-joint-state-by-controller-role",),
            invariants=shared_invariants,
            falsifiers=("factorization-cannot-replay-observed-transition",),
            resource_cap=8,
            complexity_cost=3,
        ),
        SchemeDefinition(
            name="select-navigate-apply-commit-program",
            operator="propose-transition",
            parameters=("apply-role", "navigate-role", "select-role"),
            grounding=("action-family", "object", "relation"),
            preconditions=("action-effects-separate-by-phase",),
            effects=("compose-role-conditioned-state-transformers",),
            invariants=shared_invariants,
            falsifiers=("role-program-fails-prospective-replay",),
            resource_cap=8,
            complexity_cost=4,
        ),
        SchemeDefinition(
            name="constructive-last-write-wins-composition",
            operator="propose-planner",
            parameters=("intermediate-state", "ordered-operators"),
            grounding=("action-family", "object", "relation"),
            preconditions=("multiple-commits-supported",),
            effects=("search-nonmonotone-operator-compositions",),
            invariants=shared_invariants,
            falsifiers=("composition-projection-mismatches",),
            resource_cap=8,
            complexity_cost=4,
        ),
        SchemeDefinition(
            name="relational-goal-over-visible-roles",
            operator="propose-goal",
            parameters=("goal-relation", "visible-role"),
            grounding=("object", "relation"),
            preconditions=("stable-reference-or-target-role",),
            effects=("rank-relational-goal-predicates",),
            invariants=shared_invariants,
            falsifiers=("goal-predicate-holds-without-progress",),
            resource_cap=8,
            complexity_cost=3,
        ),
        SchemeDefinition(
            name="exact-search-after-causal-verification",
            operator="propose-planner",
            parameters=("bounded-state", "verified-transition"),
            grounding=("action-family", "object", "relation"),
            preconditions=("finite-grounded-domain", "transition-confirmed"),
            effects=("enumerate-exact-goal-program",),
            invariants=shared_invariants,
            falsifiers=("projected-transition-mismatches",),
            resource_cap=8,
            complexity_cost=3,
        ),
        SchemeDefinition(
            name="information-gain-causal-intervention",
            operator="propose-experiment",
            parameters=("discriminating-action", "hypothesis-set"),
            grounding=("action-family",),
            preconditions=("multiple-live-hypotheses",),
            effects=("rank-prospectively-discriminating-intervention",),
            invariants=shared_invariants,
            falsifiers=("intervention-does-not-distinguish-predictions",),
            resource_cap=8,
            complexity_cost=3,
        ),
        SchemeDefinition(
            name="ambiguity-abstention-and-conflict-quarantine",
            operator="guard-hypothesis",
            parameters=("grounding", "prediction"),
            grounding=("action-family",),
            preconditions=("grounding-or-transition-is-provisional",),
            effects=("abstain-on-ambiguity", "quarantine-on-conflict"),
            invariants=shared_invariants,
            falsifiers=("guard-allows-contradicted-plan",),
            resource_cap=8,
            complexity_cost=2,
        ),
    )
    return SchemeLibrary.create(specifications)
