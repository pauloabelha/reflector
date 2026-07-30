"""Content-addressed symbolic schemes shipped with an offline descendant."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Iterable

EMPTY_SCHEME_LIBRARY_ROOT = (
    "4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945"
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
