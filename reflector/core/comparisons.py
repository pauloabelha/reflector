"""Context-typed transformation systems and evidence-backed transfer maps."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass, field
from typing import Any

from .symbolic import Atom, Scene, Transition


def _identifier(prefix: str, *parts: str) -> str:
    return f"{prefix}-{hashlib.sha256('|'.join(parts).encode()).hexdigest()[:12]}"


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


Matrix = tuple[int, int, int, int]
SQUARE_SYMMETRIES: tuple[Matrix, ...] = (
    (1, 0, 0, 1),
    (0, -1, 1, 0),
    (-1, 0, 0, -1),
    (0, 1, -1, 0),
    (-1, 0, 0, 1),
    (1, 0, 0, -1),
    (0, 1, 1, 0),
    (0, -1, -1, 0),
)


def apply_matrix(matrix: Matrix, vector: tuple[int, int]) -> tuple[int, int]:
    return (
        matrix[0] * vector[0] + matrix[1] * vector[1],
        matrix[2] * vector[0] + matrix[3] * vector[1],
    )


@dataclass(frozen=True, slots=True)
class ContextOperator:
    operator_id: str
    domain_id: str
    action_id: int
    parameters: tuple[int, int]
    subject_id: str
    observed: bool
    evidence: tuple[str, ...]
    source_operator_id: str | None = None
    comparison_id: str | None = None
    comparison_path: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SystemComparison:
    comparison_id: str
    domain: str
    codomain: str
    matrix: Matrix
    correspondences: tuple[int, ...]
    evidence: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ComparisonPlan:
    actions: tuple[int, ...]
    confidence: float
    expansions: int
    inferred_operators: tuple[str, ...]


@dataclass(slots=True)
class ComparisonTransferSystem:
    """Learn finite square symmetries between perceived operator domains."""

    observed_operators: dict[tuple[str, int], ContextOperator] = field(
        default_factory=dict
    )
    inferred_operators: dict[tuple[str, int], ContextOperator] = field(
        default_factory=dict
    )
    comparisons: dict[tuple[str, str], SystemComparison] = field(
        default_factory=dict
    )
    rejected_comparisons: dict[tuple[str, str], tuple[str, ...]] = field(
        default_factory=dict
    )
    touching_goal_evidence: set[str] = field(default_factory=set)
    domain_tokens: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def domain(self, scene: Scene) -> str | None:
        markers = [item for item in scene.objects if item.area > 1]
        if not markers:
            return None
        tokens = tuple(
            sorted(
                _identifier(
                    "domain-token",
                    str(marker.color),
                    str(marker.area),
                    repr(marker.shape),
                    str(marker.bbox[2] - marker.bbox[0] + 1),
                    str(marker.bbox[3] - marker.bbox[1] + 1),
                )
                for marker in markers
            )
        )
        domain_id = _identifier(
            "domain",
            *tokens,
        )
        self.domain_tokens[domain_id] = tokens
        return domain_id

    def observe(
        self,
        transition: Transition,
        before: Scene,
        *,
        allow_transfer: bool,
        allow_composition: bool = True,
    ) -> tuple[str, ...]:
        """Record local operators, then infer only supported typed transfers."""

        before_ids = (
            {
                item.comparison_id
                for item in self.comparisons.values()
            }
            | {item.operator_id for item in self.observed_operators.values()}
            | {item.operator_id for item in self.inferred_operators.values()}
        )
        domain_id = self.domain(before)
        level_advanced = any(
            event.kind == "level_advanced" for event in transition.result
        )
        if domain_id is not None and not level_advanced:
            movements = [
                movement
                for term in transition.result_signature()
                if (movement := _movement(term)) is not None
            ]
            if len(movements) == 1:
                subject_id, parameters = movements[0]
                evidence_id = _identifier(
                    "context-evidence",
                    domain_id,
                    str(transition.action_id),
                    str(transition.before_index),
                    repr(parameters),
                )
                key = (domain_id, transition.action_id)
                existing = self.observed_operators.get(key)
                evidence = tuple(
                    sorted(
                        {
                            evidence_id,
                            *(existing.evidence if existing is not None else ()),
                        }
                    )
                )
                self.observed_operators[key] = ContextOperator(
                    operator_id=_identifier(
                        "context-operator",
                        domain_id,
                        str(transition.action_id),
                        repr(parameters),
                    ),
                    domain_id=domain_id,
                    action_id=transition.action_id,
                    parameters=parameters,
                    subject_id=subject_id,
                    observed=True,
                    evidence=evidence,
                )
        self._rebuild_comparisons()
        self._rebuild_inferences(
            allow_transfer=allow_transfer,
            allow_composition=allow_composition,
        )
        after_ids = (
            {
                item.comparison_id
                for item in self.comparisons.values()
            }
            | {item.operator_id for item in self.observed_operators.values()}
            | {item.operator_id for item in self.inferred_operators.values()}
        )
        return tuple(sorted(after_ids - before_ids))

    def _rebuild_comparisons(self) -> None:
        domains = sorted({key[0] for key in self.observed_operators})
        linked_mode = any(
            len(self.domain_tokens.get(domain, ())) > 1
            for domain in domains
        )
        comparisons: dict[tuple[str, str], SystemComparison] = {}
        rejected: dict[tuple[str, str], tuple[str, ...]] = {}
        for domain in domains:
            for codomain in domains:
                if domain == codomain:
                    continue
                if linked_mode and not (
                    set(self.domain_tokens.get(domain, ()))
                    & set(self.domain_tokens.get(codomain, ()))
                ):
                    continue
                shared = sorted(
                    action
                    for candidate_domain, action in self.observed_operators
                    if candidate_domain == domain
                    and (codomain, action) in self.observed_operators
                )
                non_collinear = any(
                    (
                        self.observed_operators[(domain, left)].parameters[0]
                        * self.observed_operators[(domain, right)].parameters[1]
                        - self.observed_operators[
                            (domain, left)
                        ].parameters[1]
                        * self.observed_operators[
                            (domain, right)
                        ].parameters[0]
                    )
                    != 0
                    for index, left in enumerate(shared)
                    for right in shared[index + 1 :]
                )
                if len(shared) < 2 or not non_collinear:
                    continue
                matches = [
                    matrix
                    for matrix in SQUARE_SYMMETRIES
                    if all(
                        apply_matrix(
                            matrix,
                            self.observed_operators[
                                (domain, action)
                            ].parameters,
                        )
                        == self.observed_operators[
                            (codomain, action)
                        ].parameters
                        for action in shared
                    )
                ]
                evidence = tuple(
                    sorted(
                        {
                            evidence
                            for action in shared
                            for operator in (
                                self.observed_operators[(domain, action)],
                                self.observed_operators[(codomain, action)],
                            )
                            for evidence in operator.evidence
                        }
                    )
                )
                if len(matches) != 1:
                    rejected[(domain, codomain)] = evidence
                    continue
                matrix = matches[0]
                comparisons[(domain, codomain)] = SystemComparison(
                    comparison_id=_identifier(
                        "system-comparison",
                        domain,
                        codomain,
                        repr(matrix),
                        *(str(action) for action in shared),
                    ),
                    domain=domain,
                    codomain=codomain,
                    matrix=matrix,
                    correspondences=tuple(shared),
                    evidence=evidence,
                )
        self.comparisons = comparisons
        self.rejected_comparisons = rejected

    def _rebuild_inferences(
        self,
        *,
        allow_transfer: bool,
        allow_composition: bool,
    ) -> None:
        inferred: dict[tuple[str, int], ContextOperator] = {}
        if allow_transfer:
            available = dict(self.observed_operators)
            for _hop in range(3):
                candidates: dict[
                    tuple[str, int], ContextOperator
                ] = {}
                for comparison in sorted(
                    self.comparisons.values(),
                    key=lambda item: item.comparison_id,
                ):
                    target_subjects = sorted(
                        {
                            item.subject_id
                            for (domain, _action), item in (
                                self.observed_operators.items()
                            )
                            if domain == comparison.codomain
                        }
                    )
                    if len(target_subjects) != 1:
                        continue
                    for (domain, action), source in sorted(
                        available.items()
                    ):
                        key = (comparison.codomain, action)
                        if domain != comparison.domain:
                            continue
                        if key in self.observed_operators:
                            continue
                        if not source.observed and not allow_composition:
                            continue
                        if comparison.comparison_id in source.comparison_path:
                            continue
                        path = (
                            *source.comparison_path,
                            comparison.comparison_id,
                        )
                        parameters = apply_matrix(
                            comparison.matrix, source.parameters
                        )
                        candidate = ContextOperator(
                            operator_id=_identifier(
                                "inferred-operator",
                                comparison.codomain,
                                str(action),
                                repr(parameters),
                                *path,
                            ),
                            domain_id=comparison.codomain,
                            action_id=action,
                            parameters=parameters,
                            subject_id=target_subjects[0],
                            observed=False,
                            evidence=tuple(
                                sorted(
                                    {
                                        *source.evidence,
                                        *comparison.evidence,
                                    }
                                )
                            ),
                            source_operator_id=source.operator_id,
                            comparison_id=comparison.comparison_id,
                            comparison_path=path,
                        )
                        existing = inferred.get(key) or candidates.get(key)
                        if existing is None or (
                            len(candidate.comparison_path),
                            candidate.operator_id,
                        ) < (
                            len(existing.comparison_path),
                            existing.operator_id,
                        ):
                            candidates[key] = candidate
                changed = False
                for key, candidate in candidates.items():
                    existing = inferred.get(key)
                    if existing is None or (
                        len(candidate.comparison_path),
                        candidate.operator_id,
                    ) < (
                        len(existing.comparison_path),
                        existing.operator_id,
                    ):
                        inferred[key] = candidate
                        changed = True
                if not changed:
                    break
                available = {**self.observed_operators, **inferred}
        self.inferred_operators = inferred

    def observe_goal(
        self,
        transition: Transition,
        before: Scene,
    ) -> tuple[str, ...]:
        if not any(event.kind == "level_advanced" for event in transition.result):
            return ()
        domain_id = self.domain(before)
        if domain_id is None:
            return ()
        operator = self.operator(domain_id, transition.action_id)
        if operator is None:
            return ()
        objects = {item.object_id: item for item in before.objects}
        subject = objects.get(operator.subject_id)
        if subject is None:
            return ()
        targets = [
            item
            for item in before.objects
            if item.object_id != subject.object_id and item.area == 1
        ]
        if len(targets) != 1:
            return ()
        projected = (
            subject.centroid[0] + operator.parameters[0],
            subject.centroid[1] + operator.parameters[1],
        )
        if (
            abs(projected[0] - targets[0].centroid[0])
            + abs(projected[1] - targets[0].centroid[1])
            != 1
        ):
            return ()
        evidence_id = _identifier(
            "comparison-touching-goal",
            operator.operator_id,
            *transition.result_signature(),
        )
        created = evidence_id not in self.touching_goal_evidence
        self.touching_goal_evidence.add(evidence_id)
        return (evidence_id,) if created else ()

    def operator(self, domain_id: str, action_id: int) -> ContextOperator | None:
        return self.observed_operators.get(
            (domain_id, action_id)
        ) or self.inferred_operators.get((domain_id, action_id))

    def plan_touching(
        self,
        scene: Scene,
        legal_actions: tuple[int, ...],
        *,
        max_depth: int,
        max_expansions: int,
    ) -> ComparisonPlan | None:
        if not self.touching_goal_evidence:
            return None
        domain_id = self.domain(scene)
        if domain_id is None:
            return None
        operators = sorted(
            (
                item.action_id,
                item.parameters,
                item.operator_id,
                item.observed,
            )
            for action in legal_actions
            if (item := self.operator(domain_id, action)) is not None
        )
        subjects = {
            item.subject_id
            for action in legal_actions
            if (item := self.operator(domain_id, action)) is not None
        }
        if not operators or len(subjects) != 1:
            return None
        objects = {item.object_id: item for item in scene.objects}
        mover = objects.get(next(iter(subjects)))
        if mover is None:
            return None
        targets = [
            item
            for item in scene.objects
            if item.object_id != mover.object_id and item.area == 1
        ]
        if len(targets) != 1:
            return None
        target = targets[0].centroid
        frontier: list[
            tuple[tuple[int, int], tuple[int, ...], tuple[str, ...]]
        ] = [(mover.centroid, (), ())]
        visited = {mover.centroid}
        expansions = 0
        for _depth in range(max_depth):
            next_frontier: list[
                tuple[tuple[int, int], tuple[int, ...], tuple[str, ...]]
            ] = []
            for position, actions, inferred_ids in frontier:
                for action, vector, operator_id, observed in operators:
                    if expansions >= max_expansions:
                        return None
                    expansions += 1
                    reached = (
                        position[0] + vector[0],
                        position[1] + vector[1],
                    )
                    sequence = (*actions, action)
                    used_inferred = (
                        inferred_ids
                        if observed
                        else (*inferred_ids, operator_id)
                    )
                    if (
                        abs(reached[0] - target[0])
                        + abs(reached[1] - target[1])
                        == 1
                    ):
                        return ComparisonPlan(
                            actions=sequence,
                            confidence=1.0,
                            expansions=expansions,
                            inferred_operators=tuple(sorted(set(used_inferred))),
                        )
                    if reached not in visited:
                        visited.add(reached)
                        next_frontier.append(
                            (reached, sequence, used_inferred)
                        )
            frontier = next_frontier
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "observed_operators": [
                item.to_dict()
                for item in sorted(
                    self.observed_operators.values(),
                    key=lambda value: value.operator_id,
                )
            ],
            "inferred_operators": [
                item.to_dict()
                for item in sorted(
                    self.inferred_operators.values(),
                    key=lambda value: value.operator_id,
                )
            ],
            "comparisons": [
                item.to_dict()
                for item in sorted(
                    self.comparisons.values(),
                    key=lambda value: value.comparison_id,
                )
            ],
            "rejected_comparisons": [
                {
                    "domain": domain,
                    "codomain": codomain,
                    "evidence": list(evidence),
                }
                for (domain, codomain), evidence in sorted(
                    self.rejected_comparisons.items()
                )
            ],
            "touching_goal_evidence": sorted(self.touching_goal_evidence),
            "domain_tokens": {
                domain: list(tokens)
                for domain, tokens in sorted(self.domain_tokens.items())
            },
        }
