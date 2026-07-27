"""Evidence-backed operatory transformations and typed comparisons."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any

from .schemas import SchemaStore
from .symbolic import Atom, Scene, Transition


def _identifier(prefix: str, *parts: str) -> str:
    raw = "|".join(parts)
    return f"{prefix}-{hashlib.sha256(raw.encode()).hexdigest()[:12]}"


def _movement(term: str) -> tuple[str, tuple[int, int]] | None:
    atom = Atom.parse(term)
    if atom.predicate != "object_moved" or len(atom.arguments) != 3:
        return None
    try:
        return atom.arguments[0], (
            int(atom.arguments[1]),
            int(atom.arguments[2]),
        )
    except ValueError:
        return None


@dataclass(frozen=True, slots=True)
class OperatoryTransformation:
    transformation_id: str
    algebra: str
    parameters: tuple[int, int]
    action_id: int
    subjects: tuple[str, ...]
    evidence: tuple[str, ...]
    support: int
    confidence: float
    raw_description_length: int
    compiled_description_length: int
    complexity: int
    utility: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TransformationComposition:
    algebra: str
    parameters: tuple[int, int]
    components: tuple[str, ...]
    evidence: tuple[str, ...]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TransformationMorphism:
    morphism_id: str
    domain: str
    codomain: str
    algebra: str
    parameter_delta: tuple[int, int]
    evidence: tuple[str, ...]
    components: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ComparisonLawReport:
    typed_endpoints: bool
    identities: bool
    closed_composition: bool
    associative: bool
    transformations_checked: int
    composable_pairs_checked: int
    composable_triples_checked: int

    @property
    def passed(self) -> bool:
        return (
            self.typed_endpoints
            and self.identities
            and self.closed_composition
            and self.associative
        )

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "passed": self.passed}


@dataclass(frozen=True, slots=True)
class ModalReachability:
    possible: bool
    impossible_within_bounds: bool
    shortest_actions: tuple[int, ...]
    necessary_first_actions: tuple[int, ...]
    reachable_states: int
    expansions: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TransformationSystem:
    """Reflect learned movements into executable, bounded operator objects."""

    complexity_pressure: float = 1.0
    minimum_support: int = 2
    max_transformations: int = 24
    transformations: dict[str, OperatoryTransformation] = field(
        default_factory=dict
    )
    morphisms: dict[str, TransformationMorphism] = field(default_factory=dict)
    touching_goal_evidence: set[str] = field(default_factory=set)

    def reflect(self, schemas: SchemaStore) -> tuple[str, ...]:
        before = set(self.transformations) | set(self.morphisms)
        groups: dict[
            tuple[int, tuple[int, int]], list[tuple[str, str, int, float]]
        ] = {}
        for schema in schemas.schemas.values():
            # Level transitions commonly reset or replace a board.  Those
            # movements are environment bookkeeping, not the action's local
            # operatory effect.
            if any(
                term.split("(", 1)[0] in {"level_advanced", "WIN"}
                for term in schema.result
            ):
                continue
            for term in schema.result:
                movement = _movement(term)
                if movement is None:
                    continue
                subject, parameters = movement
                groups.setdefault((schema.action_id, parameters), []).append(
                    (
                        schema.schema_id,
                        subject,
                        schema.support,
                        schema.reliability,
                    )
                )

        candidates: list[OperatoryTransformation] = []
        for (action_id, parameters), rows in sorted(groups.items()):
            support = sum(row[2] for row in rows)
            if support < self.minimum_support:
                continue
            evidence = tuple(sorted({row[0] for row in rows}))
            subject_support: dict[str, int] = {}
            for _schema_id, subject, row_support, _reliability in rows:
                subject_support[subject] = (
                    subject_support.get(subject, 0) + row_support
                )
            strongest_subject_support = max(subject_support.values())
            subjects = tuple(
                sorted(
                    subject
                    for subject, subject_total in subject_support.items()
                    if subject_total == strongest_subject_support
                )
            )
            raw = sum(
                (len(row[0]) + len(row[1]) + len(str(parameters))) * row[2]
                for row in rows
            )
            complexity = (
                len("translation_z2")
                + len(str(action_id))
                + len(str(parameters))
                + sum(len(item) for item in subjects)
                + 12
            )
            compiled = round(
                self.complexity_pressure * complexity
            ) + support * 4
            utility = raw - compiled
            if utility <= 0:
                continue
            transformation_id = _identifier(
                "transform",
                str(action_id),
                repr(parameters),
                *subjects,
            )
            candidates.append(
                OperatoryTransformation(
                    transformation_id=transformation_id,
                    algebra="translation_z2",
                    parameters=parameters,
                    action_id=action_id,
                    subjects=subjects,
                    evidence=evidence,
                    support=support,
                    confidence=sum(row[3] for row in rows) / len(rows),
                    raw_description_length=raw,
                    compiled_description_length=compiled,
                    complexity=complexity,
                    utility=utility,
                )
            )
        candidates.sort(
            key=lambda item: (
                -item.support,
                -item.utility,
                item.transformation_id,
            )
        )
        # Keep only the strongest effect hypothesis for each primitive action.
        selected: dict[int, OperatoryTransformation] = {}
        for item in candidates:
            selected.setdefault(item.action_id, item)
        retained = sorted(
            selected.values(),
            key=lambda item: item.transformation_id,
        )[: self.max_transformations]
        self.transformations = {
            item.transformation_id: item for item in retained
        }
        self._build_morphisms()
        after = set(self.transformations) | set(self.morphisms)
        return tuple(sorted(after - before))

    def observe_goal(
        self,
        transition: Transition,
        before: Scene,
    ) -> tuple[str, ...]:
        """Ground a touching goal when a known operation advances a level."""

        if not any(event.kind == "level_advanced" for event in transition.result):
            return ()
        learned = [
            item
            for item in self.transformations.values()
            if item.action_id == transition.action_id
        ]
        new: list[str] = []
        objects = {item.object_id: item for item in before.objects}
        for transformation in learned:
            for subject_id in transformation.subjects:
                subject = objects.get(subject_id)
                if subject is None:
                    continue
                projected = (
                    subject.centroid[0] + transformation.parameters[0],
                    subject.centroid[1] + transformation.parameters[1],
                )
                for target in before.objects:
                    if target.object_id in transformation.subjects:
                        continue
                    distance = abs(projected[0] - target.centroid[0]) + abs(
                        projected[1] - target.centroid[1]
                    )
                    if distance != 1:
                        continue
                    evidence_id = _identifier(
                        "touching-goal",
                        transformation.transformation_id,
                        transition.result_signature()[0],
                    )
                    if evidence_id not in self.touching_goal_evidence:
                        new.append(evidence_id)
                    self.touching_goal_evidence.add(evidence_id)
        return tuple(sorted(new))

    def plan_touching(
        self,
        scene: Scene,
        legal_actions: tuple[int, ...],
        *,
        max_depth: int,
        max_expansions: int,
    ) -> tuple[tuple[int, ...], float, int] | None:
        """Plan with learned translations when one movable and one goal exist."""

        if not self.touching_goal_evidence:
            return None
        by_subject = {
            subject
            for item in self.transformations.values()
            for subject in item.subjects
        }
        movable = [item for item in scene.objects if item.object_id in by_subject]
        targets = [
            item for item in scene.objects if item.object_id not in by_subject
        ]
        if len(movable) != 1 or len(targets) != 1:
            return None
        operators = sorted(
            (
                item.action_id,
                item.parameters,
                item.confidence,
            )
            for item in self.transformations.values()
            if item.action_id in legal_actions
            and movable[0].object_id in item.subjects
        )
        if not operators:
            return None
        start = movable[0].centroid
        target = targets[0].centroid
        if abs(start[0] - target[0]) + abs(start[1] - target[1]) == 1:
            return None
        frontier: list[tuple[tuple[int, int], tuple[int, ...], float]] = [
            (start, (), 1.0)
        ]
        visited = {start}
        expansions = 0
        for _depth in range(max_depth):
            next_frontier: list[
                tuple[tuple[int, int], tuple[int, ...], float]
            ] = []
            for position, actions, confidence in frontier:
                for action_id, vector, operator_confidence in operators:
                    if expansions >= max_expansions:
                        return None
                    expansions += 1
                    reached = (
                        position[0] + vector[0],
                        position[1] + vector[1],
                    )
                    sequence = (*actions, action_id)
                    sequence_confidence = confidence * operator_confidence
                    if (
                        abs(reached[0] - target[0])
                        + abs(reached[1] - target[1])
                        == 1
                    ):
                        return sequence, sequence_confidence, expansions
                    if reached not in visited:
                        visited.add(reached)
                        next_frontier.append(
                            (reached, sequence, sequence_confidence)
                        )
            frontier = next_frontier
        return None

    def compose(
        self,
        *transformations: OperatoryTransformation,
    ) -> TransformationComposition:
        if not transformations:
            raise ValueError("at least one transformation is required")
        if any(
            item.algebra != transformations[0].algebra
            for item in transformations
        ):
            raise ValueError("transformation algebras do not match")
        return TransformationComposition(
            algebra=transformations[0].algebra,
            parameters=(
                sum(item.parameters[0] for item in transformations),
                sum(item.parameters[1] for item in transformations),
            ),
            components=tuple(
                item.transformation_id for item in transformations
            ),
            evidence=tuple(
                sorted(
                    {
                        evidence
                        for item in transformations
                        for evidence in item.evidence
                    }
                )
            ),
            confidence=min(item.confidence for item in transformations),
        )

    def inverse(
        self,
        transformation: OperatoryTransformation,
    ) -> OperatoryTransformation | None:
        target = (
            -transformation.parameters[0],
            -transformation.parameters[1],
        )
        return next(
            (
                item
                for item in self.transformations.values()
                if item.algebra == transformation.algebra
                and item.parameters == target
            ),
            None,
        )

    def modal_reachability(
        self,
        *,
        start: tuple[int, int],
        target: tuple[int, int],
        bounds: tuple[int, int, int, int],
        max_depth: int,
    ) -> ModalReachability:
        """Exhaust a finite bounded graph and report calibrated reachability."""

        min_x, min_y, max_x, max_y = bounds
        operators = sorted(
            (
                item.action_id,
                item.parameters,
            )
            for item in self.transformations.values()
        )
        frontier: list[tuple[tuple[int, int], tuple[int, ...]]] = [(start, ())]
        visited = {start}
        solutions: list[tuple[int, ...]] = []
        expansions = 0
        for _depth in range(max_depth + 1):
            next_frontier: list[tuple[tuple[int, int], tuple[int, ...]]] = []
            for state, path in frontier:
                if state == target:
                    solutions.append(path)
                    continue
                if len(path) == max_depth:
                    continue
                for action_id, vector in operators:
                    expansions += 1
                    reached = (
                        state[0] + vector[0],
                        state[1] + vector[1],
                    )
                    if not (
                        min_x <= reached[0] <= max_x
                        and min_y <= reached[1] <= max_y
                    ):
                        continue
                    if reached not in visited:
                        visited.add(reached)
                        next_frontier.append((reached, (*path, action_id)))
            if solutions:
                break
            frontier = next_frontier
        shortest = min(solutions) if solutions else ()
        first_actions = (
            tuple(sorted({path[0] for path in solutions if path}))
            if solutions
            else ()
        )
        necessary = first_actions if len(first_actions) == 1 else ()
        return ModalReachability(
            possible=bool(solutions),
            impossible_within_bounds=not solutions and not frontier,
            shortest_actions=shortest,
            necessary_first_actions=necessary,
            reachable_states=len(visited),
            expansions=expansions,
        )

    def _build_morphisms(self) -> None:
        values = sorted(
            self.transformations.values(),
            key=lambda item: item.transformation_id,
        )
        output: dict[str, TransformationMorphism] = {}
        for source in values:
            for target in values:
                delta = (
                    target.parameters[0] - source.parameters[0],
                    target.parameters[1] - source.parameters[1],
                )
                morphism_id = _identifier(
                    "morphism",
                    source.transformation_id,
                    target.transformation_id,
                    repr(delta),
                )
                output[morphism_id] = TransformationMorphism(
                    morphism_id=morphism_id,
                    domain=source.transformation_id,
                    codomain=target.transformation_id,
                    algebra=source.algebra,
                    parameter_delta=delta,
                    evidence=tuple(
                        sorted(set(source.evidence) | set(target.evidence))
                    ),
                )
        self.morphisms = output

    def identity(self, transformation_id: str) -> TransformationMorphism:
        if transformation_id not in self.transformations:
            raise ValueError(f"unknown transformation: {transformation_id}")
        return next(
            item
            for item in self.morphisms.values()
            if item.domain == transformation_id
            and item.codomain == transformation_id
        )

    def compose_morphisms(
        self,
        first: TransformationMorphism,
        second: TransformationMorphism,
    ) -> TransformationMorphism:
        if first.codomain != second.domain:
            raise ValueError("morphism endpoints do not compose")
        if first.algebra != second.algebra:
            raise ValueError("morphism algebras do not match")
        direct = next(
            (
                item
                for item in self.morphisms.values()
                if item.domain == first.domain
                and item.codomain == second.codomain
            ),
            None,
        )
        if direct is None:
            raise ValueError("composite is not closed")
        expected = (
            first.parameter_delta[0] + second.parameter_delta[0],
            first.parameter_delta[1] + second.parameter_delta[1],
        )
        if direct.parameter_delta != expected:
            raise ValueError("composite parameter map is inconsistent")
        return TransformationMorphism(
            morphism_id=direct.morphism_id,
            domain=direct.domain,
            codomain=direct.codomain,
            algebra=direct.algebra,
            parameter_delta=direct.parameter_delta,
            evidence=tuple(
                sorted(set(first.evidence) | set(second.evidence))
            ),
            components=(
                *(first.components or (first.morphism_id,)),
                *(second.components or (second.morphism_id,)),
            ),
        )

    def law_report(self) -> ComparisonLawReport:
        arrows = tuple(self.morphisms.values())
        typed = all(
            item.domain in self.transformations
            and item.codomain in self.transformations
            for item in arrows
        )
        identities = all(
            self.identity(item.transformation_id).parameter_delta == (0, 0)
            for item in self.transformations.values()
        )
        pairs = 0
        closed = True
        triples = 0
        associative = True
        by_endpoints = {
            (item.domain, item.codomain): item for item in arrows
        }
        for first in arrows:
            for second in arrows:
                if first.codomain != second.domain:
                    continue
                pairs += 1
                try:
                    self.compose_morphisms(first, second)
                except ValueError:
                    closed = False
                for third in arrows:
                    if second.codomain != third.domain:
                        continue
                    triples += 1
                    left = self.compose_morphisms(
                        self.compose_morphisms(first, second),
                        third,
                    )
                    right = self.compose_morphisms(
                        first,
                        self.compose_morphisms(second, third),
                    )
                    associative = associative and (
                        left.domain,
                        left.codomain,
                        left.parameter_delta,
                    ) == (
                        right.domain,
                        right.codomain,
                        right.parameter_delta,
                    )
                    associative = associative and (
                        left.domain,
                        left.codomain,
                    ) in by_endpoints
        return ComparisonLawReport(
            typed_endpoints=typed,
            identities=identities,
            closed_composition=closed,
            associative=associative,
            transformations_checked=len(self.transformations),
            composable_pairs_checked=pairs,
            composable_triples_checked=triples,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "transformations": [
                item.to_dict()
                for item in sorted(
                    self.transformations.values(),
                    key=lambda value: value.transformation_id,
                )
            ],
            "morphisms": [
                item.to_dict()
                for item in sorted(
                    self.morphisms.values(),
                    key=lambda value: value.morphism_id,
                )
            ],
            "touching_goal_evidence": sorted(self.touching_goal_evidence),
            "law_report": self.law_report().to_dict(),
        }
