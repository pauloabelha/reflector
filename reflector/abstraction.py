"""Evidence-gated abstraction across schemas, concepts, and symbolic language."""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from .schemas import ConceptStore, Schema, SchemaStore, SyntheticConcept
from .symbolic import Atom, Event, Transition, canonical_atoms

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
    invented_by: str

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
    invention_mechanism_revision: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LanguageProposal:
    """One falsifiable trial made by a represented invention mechanism."""

    proposal_id: str
    mechanism_revision_id: str
    candidate_name: str
    signature: str
    algebra: str
    replaces: tuple[str, ...]
    evidence: tuple[str, ...]
    support: int
    raw_description_length: int
    compiled_description_length: int
    complexity: int
    utility: float
    accepted: bool
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class LanguageInventionMechanism:
    """A parented, evidence-bearing strategy for constructing a DSL operator."""

    revision_id: str
    parent_id: str | None
    strategy: str
    input_form: str
    output_form: str
    required_distinct_predicates: int
    minimum_support: int
    proposals: tuple[str, ...]
    accepted_operators: tuple[str, ...]
    rejected_proposals: tuple[str, ...]
    evidence: tuple[str, ...]
    complexity: int
    utility: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _initial_language_mechanism() -> LanguageInventionMechanism:
    return LanguageInventionMechanism(
        revision_id="language-inducer-v1-cyclic-predicates",
        parent_id=None,
        strategy="compile-enumerated-cyclic-predicates",
        input_form="predicate_stem_discrete_magnitude(object)",
        output_form="typed_group_operator(object,k)",
        required_distinct_predicates=3,
        minimum_support=4,
        proposals=(),
        accepted_operators=(),
        rejected_proposals=(),
        evidence=(),
        complexity=0,
        utility=0.0,
        status="untested",
    )


@dataclass(frozen=True, slots=True)
class ProcedureAbstraction:
    """A repeated goal-reaching context/action sequence."""

    procedure_id: str
    goal: str
    contexts: tuple[tuple[str, ...], ...]
    actions: tuple[int, ...]
    evidence: tuple[str, ...]
    support: int
    confidence: float
    raw_description_length: int
    compiled_description_length: int
    complexity: int
    utility: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class _ProcedureCandidate:
    goal: str
    contexts: tuple[tuple[str, ...], ...]
    actions: tuple[int, ...]
    evidence: set[str]
    support: int = 0


@dataclass(slots=True)
class AbstractionStore:
    """Reflect over learned structures without arbitrary code generation."""

    complexity_pressure: float = 1.0
    enable_language_meta_reflection: bool = True
    schema_families: dict[str, SchemaFamily] = field(default_factory=dict)
    concept_types: dict[str, ConceptType] = field(default_factory=dict)
    language_operators: dict[str, LanguageOperator] = field(default_factory=dict)
    language_proposals: dict[str, LanguageProposal] = field(
        default_factory=dict
    )
    language_mechanism_history: list[LanguageInventionMechanism] = field(
        default_factory=lambda: [_initial_language_mechanism()]
    )
    procedures: dict[str, ProcedureAbstraction] = field(default_factory=dict)
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
    _procedure_candidates: dict[str, _ProcedureCandidate] = field(
        default_factory=dict
    )
    _trajectory: list[tuple[tuple[str, ...], int, str]] = field(
        default_factory=list
    )

    def reflect(
        self, schemas: SchemaStore, concepts: ConceptStore
    ) -> tuple[str, ...]:
        before = (
            set(self.schema_families)
            | set(self.concept_types)
            | set(self.language_operators)
            | set(self.language_proposals)
            | {
                item.revision_id
                for item in self.language_mechanism_history
            }
        )
        self._reflect_schema_families(schemas)
        self._reflect_concept_types(concepts)
        self._reflect_language(schemas)
        after = (
            set(self.schema_families)
            | set(self.concept_types)
            | set(self.language_operators)
            | set(self.language_proposals)
            | {
                item.revision_id
                for item in self.language_mechanism_history
            }
        )
        return tuple(sorted(after - before))

    def action_transfer_value(
        self,
        action_id: int,
        schemas: SchemaStore,
        context: tuple[Atom, ...],
    ) -> float:
        """Compile accepted schema families into an unseen-context prior."""

        current = {atom.text() for atom in context}
        newest_by_result: dict[tuple[str, ...], SchemaFamily] = {}
        for family in self.schema_families.values():
            required = {
                term
                for term in family.shared_context
                if not term.startswith("synthetic_item(")
            }
            if (
                family.action_id != action_id
                or family.utility <= 0
                or "level_advanced" not in family.result_predicates
                or not required.issubset(current)
            ):
                continue
            previous = newest_by_result.get(family.result_predicates)
            if previous is None or (
                family.support,
                family.utility,
                family.family_id,
            ) > (
                previous.support,
                previous.utility,
                previous.family_id,
            ):
                newest_by_result[family.result_predicates] = family
        member_ids = {
            schema_id
            for family in newest_by_result.values()
            for schema_id in family.member_schemas
        }
        members = [
            schemas.schemas[schema_id]
            for schema_id in member_ids
            if schema_id in schemas.schemas
        ]
        support = sum(schema.support for schema in members)
        if not support:
            return 0.0
        return sum(
            schemas.result_value(schema.result) * schema.support
            for schema in members
        ) / support

    @staticmethod
    def abstract_context(context: tuple[Atom, ...]) -> tuple[str, ...]:
        """Remove incidental object identity and absolute position."""

        abstract: list[Atom] = []
        for atom in context:
            if atom.predicate in {
                "state",
                "object_count",
                "color_present",
                "action_available",
            }:
                abstract.append(atom)
            elif (
                atom.predicate == "object_signature"
                and len(atom.arguments) == 6
            ):
                abstract.append(
                    Atom(
                        "object_type",
                        (
                            atom.arguments[0],
                            atom.arguments[1],
                            atom.arguments[4],
                            atom.arguments[5],
                        ),
                    )
                )
        return tuple(atom.text() for atom in canonical_atoms(abstract))

    def observe_procedure(
        self,
        transition: Transition,
        schema_id: str,
        *,
        max_steps: int,
    ) -> tuple[str, ...]:
        """Compile repeated successful trajectories into executable macros."""

        kinds = {event.kind for event in transition.result}
        if kinds == {"no_observed_change"}:
            return ()
        self._trajectory.append(
            (
                self.abstract_context(transition.context),
                transition.action_id,
                schema_id,
            )
        )
        self._trajectory = self._trajectory[-max_steps:]
        if "level_advanced" not in kinds:
            if any(event.kind == "state_changed" for event in transition.result):
                self._trajectory.clear()
            return ()

        contexts = tuple(item[0] for item in self._trajectory)
        actions = tuple(item[1] for item in self._trajectory)
        evidence = {item[2] for item in self._trajectory}
        if len(actions) < 2:
            self._trajectory.clear()
            return ()
        raw_key = "|".join(
            (
                "level_advanced",
                *(f"{'/'.join(context)}=>{action}" for context, action in zip(
                    contexts, actions, strict=True
                )),
            )
        )
        procedure_id = _identifier("procedure", raw_key)
        candidate = self._procedure_candidates.get(procedure_id)
        if candidate is None:
            candidate = _ProcedureCandidate(
                goal="level_advanced",
                contexts=contexts,
                actions=actions,
                evidence=set(),
            )
            self._procedure_candidates[procedure_id] = candidate
        candidate.support += 1
        candidate.evidence.update(evidence)
        self._trajectory.clear()

        raw_unit = len(raw_key)
        complexity = raw_unit + 8
        raw = raw_unit * candidate.support
        compiled = round(
            self.complexity_pressure * complexity
        ) + candidate.support * len(actions) * 2
        utility = raw - compiled
        if utility <= 0:
            return ()
        is_new = procedure_id not in self.procedures
        self.procedures[procedure_id] = ProcedureAbstraction(
            procedure_id=procedure_id,
            goal=candidate.goal,
            contexts=candidate.contexts,
            actions=candidate.actions,
            evidence=tuple(sorted(candidate.evidence)),
            support=candidate.support,
            confidence=(candidate.support + 1) / (candidate.support + 2),
            raw_description_length=raw,
            compiled_description_length=compiled,
            complexity=complexity,
            utility=utility,
        )
        return (procedure_id,) if is_new else ()

    def procedure_match(
        self,
        context: tuple[Atom, ...],
        legal_actions: tuple[int, ...],
    ) -> tuple[tuple[int, ...], float, str] | None:
        """Return the strongest accepted procedure suffix for this context."""

        abstract = self.abstract_context(context)
        matches: list[
            tuple[float, float, int, str, tuple[int, ...]]
        ] = []
        for procedure in self.procedures.values():
            for index, candidate_context in enumerate(procedure.contexts):
                suffix = procedure.actions[index:]
                if (
                    candidate_context == abstract
                    and suffix
                    and suffix[0] in legal_actions
                ):
                    matches.append(
                        (
                            procedure.confidence,
                            procedure.utility,
                            procedure.support,
                            procedure.procedure_id,
                            suffix,
                        )
                    )
        if not matches:
            return None
        confidence, _utility, _support, procedure_id, suffix = max(matches)
        return suffix, confidence, procedure_id

    def normalize_transition(self, transition: Transition) -> Transition:
        """Express future rotation evidence in an accepted compositional DSL."""

        if not any(
            operator.name == "orientation_delta"
            for operator in self.language_operators.values()
        ):
            return transition
        normalized: list[Event] = []
        for event in transition.result:
            match = _ROTATION.match(event.kind)
            if match is None:
                normalized.append(event)
                continue
            angle = int(match.group(1)) % 360
            normalized.append(
                Event(
                    "orientation_delta",
                    event.subject,
                    (str(angle // 90), *event.arguments),
                )
            )
        return Transition(
            before_index=transition.before_index,
            after_index=transition.after_index,
            context=transition.context,
            action_id=transition.action_id,
            action_data=transition.action_data,
            result=tuple(normalized),
        )

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
        if not self.enable_language_meta_reflection:
            return
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
        if not evidence:
            return
        replaces = tuple(sorted(evidence))
        evidence_ids = tuple(
            sorted({item for values in evidence.values() for item in values})
        )
        raw = sum(len(name) * support[name] for name in replaces)
        signature = "orientation_delta(object,k)"
        algebra = "k in Z4; compose(a,b)=(a+b) mod 4"
        operator_id = _identifier("operator", signature, *replaces)
        mechanism = self.language_mechanism_history[-1]
        existing_operator = self.language_operators.get(operator_id)
        if existing_operator is not None and mechanism.status == "validated":
            return
        complexity = len(signature) + len(algebra)
        compiled = round(self.complexity_pressure * complexity) + sum(
            support.values()
        ) * 3
        utility = raw - compiled
        total_support = sum(support.values())
        accepted = (
            len(evidence) >= mechanism.required_distinct_predicates
            and total_support >= mechanism.minimum_support
            and utility > 0
        )
        reason = (
            "insufficient-distinct-predicates"
            if len(evidence) < mechanism.required_distinct_predicates
            else "insufficient-support"
            if total_support < mechanism.minimum_support
            else "nonpositive-counterfactual-utility"
            if utility <= 0
            else "accepted"
        )
        proposal_id = _identifier(
            "language-proposal",
            mechanism.revision_id,
            signature,
            str(total_support),
            *replaces,
            *evidence_ids,
        )
        self.language_proposals[proposal_id] = LanguageProposal(
            proposal_id=proposal_id,
            mechanism_revision_id=mechanism.revision_id,
            candidate_name="orientation_delta",
            signature=signature,
            algebra=algebra,
            replaces=replaces,
            evidence=evidence_ids,
            support=total_support,
            raw_description_length=raw,
            compiled_description_length=compiled,
            complexity=complexity,
            utility=utility,
            accepted=accepted,
            reason=reason,
        )
        if not accepted:
            return
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
            invented_by=(
                existing_operator.invented_by
                if existing_operator is not None
                else mechanism.revision_id
            ),
        )
        self.language_operators[operator_id] = operator
        proposal_ids = tuple(sorted(self.language_proposals))
        rejected = tuple(
            item.proposal_id
            for item in sorted(
                self.language_proposals.values(),
                key=lambda value: value.proposal_id,
            )
            if not item.accepted
        )
        mechanism_complexity = (
            len(mechanism.strategy.split("-"))
            + len(mechanism.input_form.split("_"))
            + len(mechanism.output_form.split("_"))
            + mechanism.required_distinct_predicates
            + mechanism.minimum_support
            + 8
        )
        mechanism_utility = utility - round(
            self.complexity_pressure * mechanism_complexity
        )
        if (
            existing_operator is not None
            and mechanism.status == "provisional"
            and mechanism_utility <= 0
        ):
            return
        mechanism_revision = _identifier(
            "language-inducer",
            mechanism.revision_id,
            operator_id,
            *proposal_ids,
        )
        revised = LanguageInventionMechanism(
            revision_id=mechanism_revision,
            parent_id=mechanism.revision_id,
            strategy=mechanism.strategy,
            input_form=mechanism.input_form,
            output_form=mechanism.output_form,
            required_distinct_predicates=(
                mechanism.required_distinct_predicates
            ),
            minimum_support=mechanism.minimum_support,
            proposals=proposal_ids,
            accepted_operators=tuple(
                sorted(
                    {
                        *mechanism.accepted_operators,
                        *self.language_operators,
                    }
                )
            ),
            rejected_proposals=rejected,
            evidence=tuple(sorted({*evidence_ids, proposal_id})),
            complexity=mechanism_complexity,
            utility=mechanism_utility,
            status="validated" if mechanism_utility > 0 else "provisional",
        )
        self.language_mechanism_history.append(revised)
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
                invention_mechanism_revision=revised.revision_id,
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
            "language_proposals": [
                item.to_dict()
                for item in sorted(
                    self.language_proposals.values(),
                    key=lambda value: value.proposal_id,
                )
            ],
            "language_mechanism_history": [
                item.to_dict() for item in self.language_mechanism_history
            ],
            "procedures": [
                item.to_dict()
                for item in sorted(
                    self.procedures.values(),
                    key=lambda value: value.procedure_id,
                )
            ],
            "language_history": [
                item.to_dict() for item in self.language_history
            ],
        }
