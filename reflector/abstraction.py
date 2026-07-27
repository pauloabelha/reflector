"""Evidence-gated abstraction across schemas, concepts, and symbolic language."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .schemas import ConceptStore, Schema, SchemaStore, SyntheticConcept

_ROTATION = re.compile(r"^rotated_(0|90|180|270|360)$")


def _predicate(term: str) -> str:
    return term.split("(", 1)[0]


def _identifier(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    return f"{prefix}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


@dataclass(frozen=True, slots=True)
class SchemaFamily:
    family_id: str
    action_id: int
    result_predicates: tuple[str, ...]
    member_schemas: tuple[str, ...]
    shared_context: tuple[str, ...]
    support: int
    reliability: float
    raw_description_length: int
    compiled_description_length: int
    complexity: int
    utility: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ConceptType:
    type_id: str
    name: str
    kind: str
    children: tuple[str, ...]
    evidence: tuple[str, ...]
    support: int
    raw_description_length: int
    compiled_description_length: int
    complexity: int
    utility: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LanguageOperator:
    operator_id: str
    name: str
    signature: str
    algebra: str
    replaces: tuple[str, ...]
    evidence: tuple[str, ...]
    support: int
    raw_description_length: int
    compiled_description_length: int
    complexity: int
    utility: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LanguageVersion:
    version_id: str
    parent_id: str | None
    operators: tuple[str, ...]
    evidence: tuple[str, ...]
    description_length: int
    utility: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AbstractionStore:
    """Reflect over learned structures without arbitrary code generation."""

    complexity_pressure: float = 1.0
    schema_families: dict[str, SchemaFamily] = field(default_factory=dict)
    concept_types: dict[str, ConceptType] = field(default_factory=dict)
    language_operators: dict[str, LanguageOperator] = field(default_factory=dict)
    language_history: list[LanguageVersion] = field(
        default_factory=lambda: [
            LanguageVersion(
                version_id="language-v1-primitives",
                parent_id=None,
                operators=(),
                evidence=(),
                description_length=0,
                utility=0.0,
            )
        ]
    )

    def reflect(
        self, schemas: SchemaStore, concepts: ConceptStore
    ) -> tuple[str, ...]:
        before = (
            set(self.schema_families)
            | set(self.concept_types)
            | set(self.language_operators)
        )
        self._reflect_schema_families(schemas)
        self._reflect_concept_types(concepts)
        self._reflect_language(schemas)
        after = (
            set(self.schema_families)
            | set(self.concept_types)
            | set(self.language_operators)
        )
        return tuple(sorted(after - before))

    def _reflect_schema_families(self, schemas: SchemaStore) -> None:
        groups: dict[tuple[int, tuple[str, ...]], list[Schema]] = {}
        for schema in schemas.schemas.values():
            signature = tuple(sorted({_predicate(item) for item in schema.result}))
            groups.setdefault((schema.action_id, signature), []).append(schema)
        for (action, results), members in sorted(groups.items()):
            if len(members) < 2:
                continue
            member_ids = tuple(sorted(item.schema_id for item in members))
            contexts = [
                {atom.text() for atom in member.context} for member in members
            ]
            shared = tuple(sorted(set.intersection(*contexts)))
            raw = sum(
                sum(len(atom.text()) for atom in item.context)
                + sum(len(result) for result in item.result)
                + 4
                for item in members
            )
            residual = sum(
                sum(len(term) for term in context - set(shared))
                for context in contexts
            )
            result_residual = sum(
                sum(
                    max(0, len(result) - len(_predicate(result)))
                    for result in item.result
                )
                for item in members
            )
            complexity = (
                len(str(action))
                + sum(map(len, results))
                + sum(map(len, shared))
                + 8
            )
            compiled = round(
                self.complexity_pressure * complexity
            ) + residual + result_residual + len(members) * 4
            reliability = sum(item.reliability for item in members) / len(members)
            utility = (raw - compiled) * reliability
            if utility <= 0:
                continue
            family_id = _identifier(
                "family", str(action), *results, *member_ids
            )
            self.schema_families[family_id] = SchemaFamily(
                family_id=family_id,
                action_id=action,
                result_predicates=results,
                member_schemas=member_ids,
                shared_context=shared,
                support=sum(item.support for item in members),
                reliability=reliability,
                raw_description_length=raw,
                compiled_description_length=compiled,
                complexity=complexity,
                utility=utility,
            )

    def _reflect_concept_types(self, concepts: ConceptStore) -> None:
        groups: dict[str, list[SyntheticConcept]] = {}
        for concept in concepts.concepts.values():
            groups.setdefault(concept.kind, []).append(concept)
        for kind, children in sorted(groups.items()):
            if len(children) < 2:
                continue
            child_ids = tuple(sorted(item.concept_id for item in children))
            raw = sum(len(item.kind) + len(item.name) for item in children)
            name = f"Type[{kind}]"
            complexity = len(name) + len(kind) + 8
            compiled = round(
                self.complexity_pressure * complexity
            ) + len(children) * 5
            utility = raw - compiled
            if utility <= 0:
                continue
            type_id = _identifier("type", kind, *child_ids)
            self.concept_types[type_id] = ConceptType(
                type_id=type_id,
                name=name,
                kind=kind,
                children=child_ids,
                evidence=child_ids,
                support=sum(item.support for item in children),
                raw_description_length=raw,
                compiled_description_length=compiled,
                complexity=complexity,
                utility=utility,
            )

    def _reflect_language(self, schemas: SchemaStore) -> None:
        evidence: dict[str, set[str]] = {}
        support: dict[str, int] = {}
        for schema in schemas.schemas.values():
            for result in schema.result:
                predicate = _predicate(result)
                match = _ROTATION.match(predicate)
                if match is None:
                    continue
                normalized = "rotated_0" if match.group(1) == "360" else predicate
                evidence.setdefault(normalized, set()).add(schema.schema_id)
                support[normalized] = support.get(normalized, 0) + schema.support
        if len(evidence) < 3 or sum(support.values()) < 4:
            return
        replaces = tuple(sorted(evidence))
        evidence_ids = tuple(
            sorted({item for values in evidence.values() for item in values})
        )
        raw = sum(len(name) * support[name] for name in replaces)
        signature = "orientation_delta(object,k)"
        algebra = "k in Z4; compose(a,b)=(a+b) mod 4"
        complexity = len(signature) + len(algebra)
        compiled = round(self.complexity_pressure * complexity) + sum(
            support.values()
        ) * 3
        utility = raw - compiled
        if utility <= 0:
            return
        operator_id = _identifier("operator", signature, *replaces)
        is_new = operator_id not in self.language_operators
        operator = LanguageOperator(
            operator_id=operator_id,
            name="orientation_delta",
            signature=signature,
            algebra=algebra,
            replaces=replaces,
            evidence=evidence_ids,
            support=sum(support.values()),
            raw_description_length=raw,
            compiled_description_length=compiled,
            complexity=complexity,
            utility=utility,
        )
        self.language_operators[operator_id] = operator
        if not is_new:
            return
        previous = self.language_history[-1]
        version_id = _identifier(
            "language",
            previous.version_id,
            *sorted(self.language_operators),
        )
        self.language_history.append(
            LanguageVersion(
                version_id=version_id,
                parent_id=previous.version_id,
                operators=tuple(sorted(self.language_operators)),
                evidence=evidence_ids,
                description_length=sum(
                    item.compiled_description_length
                    for item in self.language_operators.values()
                ),
                utility=sum(
                    item.utility for item in self.language_operators.values()
                ),
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_families": [
                item.to_dict()
                for item in sorted(
                    self.schema_families.values(),
                    key=lambda value: value.family_id,
                )
            ],
            "concept_types": [
                item.to_dict()
                for item in sorted(
                    self.concept_types.values(),
                    key=lambda value: value.type_id,
                )
            ],
            "language_operators": [
                item.to_dict()
                for item in sorted(
                    self.language_operators.values(),
                    key=lambda value: value.operator_id,
                )
            ],
            "language_history": [
                item.to_dict() for item in self.language_history
            ],
        }
