"""Bounded episode explanations that drive opaque ARC action selection.

This module introduces no schema language.  It assembles references to active
R2 schemas and bindings, projects ordinary transition schemas through the
existing Shadow machinery, and keeps only disposable episode-level scores.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import asdict, dataclass, field
from itertools import combinations
from typing import Any, Iterable, Sequence

from .perception import PerceptionBatch
from .runtime import Binding, REFUTED, REIFIED, Runtime, Workspace


EffectAtom = tuple[str, tuple[object, ...]]


@dataclass(frozen=True, slots=True)
class ExplanationConfig:
    max_explanations: int = 8
    max_constituents: int = 3
    complexity_penalty: float = 0.06
    discrimination_weight: float = 0.35
    risk_weight: float = 0.40
    support_weight: float = 0.20
    retire_after_refutations: int = 2

    def __post_init__(self) -> None:
        if not 1 <= self.max_explanations <= 64:
            raise ValueError("max_explanations must be in [1, 64]")
        if not 1 <= self.max_constituents <= 16:
            raise ValueError("max_constituents must be in [1, 16]")
        if self.retire_after_refutations < 1:
            raise ValueError("retire_after_refutations must be positive")


@dataclass(frozen=True, slots=True)
class ExplanationEvidence:
    decision: int
    action_id: int
    shadow_id: int
    status: str
    observed_schema_id: int


@dataclass(slots=True)
class Explanation:
    """A bounded situated assembly of references to ordinary R2 objects."""

    explanation_id: int
    created_decision: int
    last_active_decision: int
    constituent_schema_ids: tuple[int, ...]
    relevant_bindings: tuple[Binding, ...]
    unresolved_ports: tuple[int, ...]
    provenance: tuple[str, ...]
    commitments: list[int] = field(default_factory=list)
    evidence_accounted_for: list[ExplanationEvidence] = field(default_factory=list)
    contradictions: list[int] = field(default_factory=list)
    score: float = 0.0
    confirmations: int = 0
    refutations: int = 0
    retired: bool = False

    @property
    def schema_id(self) -> int:
        return self.constituent_schema_ids[0]


@dataclass(slots=True)
class TransitionOutcomeStats:
    observations: int = 0
    progress_total: float = 0.0
    reward_total: float = 0.0
    ineffective: int = 0
    regressions: int = 0


@dataclass(frozen=True, slots=True)
class ProspectivePrediction:
    explanation_id: int | None
    schema_id: int
    action_id: int
    signature: tuple[EffectAtom, ...]
    support: float
    progress: float
    risk: float


@dataclass(frozen=True, slots=True)
class ActionRank:
    action_id: int
    score: float
    predicted_progress: float
    discrimination: float
    risk: float
    support: float
    prediction_count: int
    abstained: bool


@dataclass(slots=True)
class ExplanationDecision:
    decision_id: int
    mode: str
    baseline_action_id: int
    selected_action_id: int
    rankings: tuple[ActionRank, ...]
    predictions: tuple[ProspectivePrediction, ...]
    explanation_ids: tuple[int, ...]
    shadow_by_explanation: dict[int, int]
    changed_top_action: bool
    selected_for_discrimination: bool


@dataclass(slots=True)
class ExplanationMetrics:
    explanations_constructed: int = 0
    active_counts: list[int] = field(default_factory=list)
    constituent_counts: list[int] = field(default_factory=list)
    explanation_lifetimes: list[int] = field(default_factory=list)
    explanation_changes: int = 0
    explanations_retired: int = 0
    prediction_commitments: int = 0
    shadows_reified: int = 0
    shadows_refuted: int = 0
    shadows_abstained: int = 0
    decisions: int = 0
    action_changes: int = 0
    progress_after_changed_actions: int = 0
    regressions_after_changed_actions: int = 0
    completions_after_changed_actions: int = 0
    discrimination_selections: int = 0
    discrimination_settlements: int = 0
    no_usable_explanation: int = 0
    no_action_prediction: int = 0
    single_trivial_explanation: int = 0
    calibration: list[tuple[float, int]] = field(default_factory=list)


class ExplanationEngine:
    """Episode-local explanation beam and action-ranking boundary."""

    def __init__(
        self, runtime: Runtime, config: ExplanationConfig | None = None
    ) -> None:
        self.runtime = runtime
        self.config = config or ExplanationConfig()
        self.metrics = ExplanationMetrics()
        self._next_explanation = 0
        self._decision = 0
        self._explanations: dict[int, Explanation] = {}
        self._identity: dict[tuple[int, ...], int] = {}
        self._active_ids: tuple[int, ...] = ()
        self._outcomes: dict[int, TransitionOutcomeStats] = defaultdict(
            TransitionOutcomeStats
        )

    @property
    def active_explanations(self) -> tuple[Explanation, ...]:
        return tuple(self._explanations[item] for item in self._active_ids)

    def _source_atoms(self, schema_id: int) -> tuple[tuple[str, tuple[Any, ...]], ...]:
        return self.runtime.graph.source_atoms(schema_id)

    def _transition_action(self, schema_id: int) -> str | None:
        atoms = self._source_atoms(schema_id)
        heads = {head for head, _arguments in atoms}
        if not {"Domain", "Codomain", "Intervention"} <= heads:
            return None
        actions = [arguments for head, arguments in atoms if head == "Intervention"]
        if len(actions) != 1 or len(actions[0]) != 1:
            return None
        value = actions[0][0]
        if isinstance(value, str) and not value.startswith("?v"):
            return value
        return None

    def _effect_signature(self, schema_id: int) -> tuple[EffectAtom, ...]:
        return tuple(
            sorted(
                (
                    (head, tuple(arguments))
                    for head, arguments in self._source_atoms(schema_id)
                    if head in {"Change", "Preserve"}
                ),
                key=repr,
            )
        )

    def _schema_support(self, schema_id: int) -> float:
        graph = self.runtime.graph
        positive = (
            graph.support[schema_id]
            + graph.prediction_success[schema_id]
            + graph.projection_support[schema_id]
        )
        negative = (
            graph.contradiction[schema_id]
            + graph.prediction_failure[schema_id]
            + graph.projection_failure[schema_id]
        )
        return (positive + 1.0) / (positive + negative + 2.0)

    def _connected_bindings(
        self, schema_id: int, workspace: Workspace
    ) -> tuple[Binding, ...]:
        graph = self.runtime.graph
        support_relation = graph.terms.intern_symbol("supports")
        sources = {
            graph.src[edge]
            for edge in workspace.active_edge_ids
            if graph.relation[edge] == support_relation
            and graph.dst[edge] == schema_id
        }
        bindings = [
            binding for binding in workspace.bindings if binding.schema_id in sources
        ]
        return tuple(
            sorted(
                bindings,
                key=lambda item: (
                    graph.canonical_hash[item.schema_id],
                    item.assignments,
                ),
            )[: self.config.max_constituents - 1]
        )

    def _candidate_schemas(
        self, workspace: Workspace, action_ids: Sequence[int]
    ) -> list[int]:
        legal = {f"arc-action:{action_id}" for action_id in action_ids}
        output = []
        for schema_id in sorted(
            workspace.activation,
            key=lambda item: self.runtime.graph.canonical_hash[item],
        ):
            action = self._transition_action(schema_id)
            if action in legal and self._effect_signature(schema_id):
                output.append(schema_id)
        return output

    def _explanation_score(
        self, schema_id: int, constituent_count: int, activation: float
    ) -> float:
        return (
            self._schema_support(schema_id)
            + 0.10 * activation
            - self.config.complexity_penalty * max(0, constituent_count - 1)
        )

    def construct(
        self, workspace: Workspace, action_ids: Sequence[int]
    ) -> tuple[Explanation, ...]:
        """Build a stable top-k beam using only the supplied active frontier."""

        candidates: list[tuple[float, str, tuple[int, ...], tuple[Binding, ...]]] = []
        for schema_id in self._candidate_schemas(workspace, action_ids):
            bindings = self._connected_bindings(schema_id, workspace)
            constituents = (schema_id,) + tuple(
                dict.fromkeys(binding.schema_id for binding in bindings)
            )
            score = self._explanation_score(
                schema_id, len(constituents), workspace.activation[schema_id]
            )
            candidates.append(
                (
                    score,
                    self.runtime.graph.canonical_hash[schema_id],
                    constituents,
                    bindings,
                )
            )
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        selected = candidates[: self.config.max_explanations]
        active: list[int] = []
        for score, _canonical, constituents, bindings in selected:
            explanation_id = self._identity.get(constituents)
            if explanation_id is None or self._explanations[explanation_id].retired:
                explanation_id = self._next_explanation
                self._next_explanation += 1
                provenance = tuple(
                    sorted(
                        {
                            source
                            for schema_id in constituents
                            for source in self.runtime.graph.provenance[schema_id]
                        }
                    )
                )
                explanation = Explanation(
                    explanation_id=explanation_id,
                    created_decision=self._decision,
                    last_active_decision=self._decision,
                    constituent_schema_ids=constituents,
                    relevant_bindings=bindings,
                    unresolved_ports=(),
                    provenance=provenance,
                    score=score,
                )
                self._explanations[explanation_id] = explanation
                self._identity[constituents] = explanation_id
                self.metrics.explanations_constructed += 1
                self.metrics.constituent_counts.append(len(constituents))
            else:
                explanation = self._explanations[explanation_id]
                explanation.last_active_decision = self._decision
                explanation.relevant_bindings = bindings
                explanation.score = score + 0.08 * explanation.confirmations - 0.20 * explanation.refutations
            active.append(explanation_id)

        previous = set(self._active_ids)
        current = set(active)
        if previous and previous != current:
            self.metrics.explanation_changes += 1
        for explanation_id in sorted(previous - current):
            explanation = self._explanations[explanation_id]
            if not explanation.retired:
                explanation.retired = True
                self.metrics.explanations_retired += 1
                self.metrics.explanation_lifetimes.append(
                    self._decision - explanation.created_decision
                )
        self._active_ids = tuple(active)
        self.metrics.active_counts.append(len(active))
        if not active:
            self.metrics.no_usable_explanation += 1
        elif len(active) == 1 and len(self._explanations[active[0]].constituent_schema_ids) == 1:
            self.metrics.single_trivial_explanation += 1
        return self.active_explanations

    def _projection_assignments(
        self, schema_id: int, observed: PerceptionBatch, decision_id: int
    ) -> dict[int, int] | None:
        atoms = self._source_atoms(schema_id)
        required_relations = {
            str(arguments[1])
            for head, arguments in atoms
            if head == "Before" and len(arguments) == 3
        }
        relation_values: dict[str, int] | None = None
        for region in sorted(observed.region_terms):
            values = {
                str(self.runtime.graph.terms.value(head)): value
                for head, value in self.runtime._entity_relations(
                    observed.facts, region
                ).items()
            }
            if required_relations <= values.keys():
                relation_values = values
                break
        if required_relations and relation_values is None:
            return None

        assignments: dict[int, int] = {}
        domain_term = self.runtime.graph.terms.intern_symbol(
            f"explanation-domain:{decision_id}"
        )
        for head, arguments in atoms:
            if head == "Domain" and len(arguments) == 1:
                variable = arguments[0]
                if isinstance(variable, str) and variable.startswith("?v"):
                    assignments[int(variable[2:])] = domain_term
            elif head == "Before" and len(arguments) == 3:
                domain, relation, value = arguments
                if isinstance(domain, str) and domain.startswith("?v"):
                    assignments[int(domain[2:])] = domain_term
                if (
                    isinstance(value, str)
                    and value.startswith("?v")
                    and relation_values is not None
                    and str(relation) in relation_values
                ):
                    assignments[int(value[2:])] = relation_values[str(relation)]
        variables = {
            int(argument[2:])
            for _head, arguments in atoms
            for argument in arguments
            if isinstance(argument, str) and argument.startswith("?v")
        }
        if not variables or len(assignments) / len(variables) < self.runtime.limits.min_shadow_bound_role_fraction:
            return None
        if set(assignments) == variables:
            # Codomain is intentionally prospective.  Keeping it open also
            # guarantees a real unresolved frontier for preserve-only schemas.
            codomain = next(
                (
                    argument
                    for head, arguments in atoms
                    for argument in arguments
                    if head == "Codomain"
                    and isinstance(argument, str)
                    and argument.startswith("?v")
                ),
                None,
            )
            if codomain is not None:
                assignments.pop(int(codomain[2:]), None)
        return assignments

    def _prediction(
        self, schema_id: int, action_id: int, explanation_id: int | None
    ) -> ProspectivePrediction:
        stats = self._outcomes[schema_id]
        progress = (
            stats.progress_total / stats.observations if stats.observations else 0.0
        )
        historical_risk = (
            (stats.ineffective + stats.regressions) / stats.observations
            if stats.observations
            else 0.0
        )
        signature = self._effect_signature(schema_id)
        structural_risk = 1.0 if signature and not any(head == "Change" for head, _args in signature) else 0.0
        graph = self.runtime.graph
        failures = graph.projection_failure[schema_id] + graph.prediction_failure[schema_id]
        successes = graph.projection_support[schema_id] + graph.prediction_success[schema_id]
        evidence_risk = failures / (successes + failures) if successes + failures else 0.0
        return ProspectivePrediction(
            explanation_id=explanation_id,
            schema_id=schema_id,
            action_id=action_id,
            signature=signature,
            support=self._schema_support(schema_id),
            progress=progress,
            risk=(historical_risk + structural_risk + evidence_risk) / 3.0,
        )

    @staticmethod
    def _disagreement(predictions: Sequence[ProspectivePrediction]) -> float:
        if len(predictions) < 2:
            return 0.0
        distances = []
        for left, right in combinations(predictions, 2):
            left_set = set(left.signature)
            right_set = set(right.signature)
            union = left_set | right_set
            distances.append(
                0.0 if not union else 1.0 - len(left_set & right_set) / len(union)
            )
        return sum(distances) / len(distances)

    def decide(
        self,
        *,
        mode: str,
        workspace: Workspace,
        observed: PerceptionBatch,
        legal_action_ids: Sequence[int],
        baseline_action_id: int,
    ) -> ExplanationDecision:
        if mode not in {"local-schema", "explanation"}:
            raise ValueError(f"unsupported explanation decision mode: {mode}")
        self._decision += 1
        self.metrics.decisions += 1
        action_ids = tuple(sorted(set(legal_action_ids)))
        predictions: list[ProspectivePrediction] = []
        explanation_ids: tuple[int, ...] = ()
        if mode == "explanation":
            explanations = self.construct(workspace, action_ids)
            explanation_ids = tuple(item.explanation_id for item in explanations)
            for explanation in explanations:
                token = self._transition_action(explanation.schema_id)
                if token is None:
                    continue
                action_id = int(token.rsplit(":", 1)[1])
                if action_id in action_ids:
                    predictions.append(
                        self._prediction(
                            explanation.schema_id,
                            action_id,
                            explanation.explanation_id,
                        )
                    )
        else:
            for schema_id in self._candidate_schemas(workspace, action_ids):
                token = self._transition_action(schema_id)
                if token is not None:
                    predictions.append(
                        self._prediction(
                            schema_id, int(token.rsplit(":", 1)[1]), None
                        )
                    )

        by_action: dict[int, list[ProspectivePrediction]] = defaultdict(list)
        for prediction in predictions:
            by_action[prediction.action_id].append(prediction)
        rankings: list[ActionRank] = []
        for action_id in action_ids:
            action_predictions = by_action.get(action_id, [])
            if not action_predictions:
                rankings.append(ActionRank(action_id, 0.0, 0.0, 0.0, 0.0, 0.0, 0, True))
                continue
            progress = sum(item.progress for item in action_predictions) / len(action_predictions)
            risk = sum(item.risk for item in action_predictions) / len(action_predictions)
            support = sum(item.support for item in action_predictions) / len(action_predictions)
            discrimination = self._disagreement(action_predictions) if mode == "explanation" else 0.0
            score = (
                progress
                + self.config.discrimination_weight * discrimination
                - self.config.risk_weight * risk
                + self.config.support_weight * support
            )
            rankings.append(
                ActionRank(
                    action_id,
                    score,
                    progress,
                    discrimination,
                    risk,
                    support,
                    len(action_predictions),
                    False,
                )
            )
        rankings.sort(
            key=lambda item: (
                -item.score,
                item.action_id != baseline_action_id,
                item.action_id,
            )
        )
        selected = rankings[0].action_id
        if not predictions:
            self.metrics.no_action_prediction += 1
        changed = selected != baseline_action_id
        if changed:
            self.metrics.action_changes += 1
        selected_rank = next(item for item in rankings if item.action_id == selected)
        selected_for_discrimination = (
            mode == "explanation" and selected_rank.discrimination > 0.0
        )
        if selected_for_discrimination:
            self.metrics.discrimination_selections += 1

        decision = ExplanationDecision(
            decision_id=self._decision,
            mode=mode,
            baseline_action_id=baseline_action_id,
            selected_action_id=selected,
            rankings=tuple(rankings),
            predictions=tuple(predictions),
            explanation_ids=explanation_ids,
            shadow_by_explanation={},
            changed_top_action=changed,
            selected_for_discrimination=selected_for_discrimination,
        )
        if mode == "explanation":
            self._commit_selected(decision, observed)
        self.runtime.trace.append(self.decision_trace(decision))
        return decision

    def _commit_selected(
        self, decision: ExplanationDecision, observed: PerceptionBatch
    ) -> None:
        for prediction in decision.predictions:
            if (
                prediction.action_id != decision.selected_action_id
                or prediction.explanation_id is None
            ):
                continue
            explanation = self._explanations[prediction.explanation_id]
            assignments = self._projection_assignments(
                prediction.schema_id, observed, decision.decision_id
            )
            if assignments is None:
                self.metrics.shadows_abstained += 1
                continue
            verified_constraints = {
                index
                for index, (head, arguments) in enumerate(
                    self.runtime.graph.definition_constraint_atoms(
                        prediction.schema_id
                    )
                )
                if head in {"Before", "Domain", "Intervention"}
                and all(
                    not (
                        isinstance(argument, str)
                        and argument.startswith("?v")
                    )
                    or int(argument[2:]) in assignments
                    for argument in arguments
                )
            }
            try:
                shadow = self.runtime.project_shadow(
                    prediction.schema_id,
                    assignments,
                    verified_constraints=verified_constraints,
                    carrier=f"explanation-decision:{decision.decision_id}",
                    provenance=f"explanation:{explanation.explanation_id}",
                    prospective_action=True,
                )
            except (RuntimeError, ValueError):
                self.metrics.shadows_abstained += 1
                continue
            explanation.unresolved_ports = tuple(
                sorted(set(shadow.open_roles) | set(shadow.open_constraints))
            )
            explanation.commitments.append(shadow.shadow_id)
            decision.shadow_by_explanation[explanation.explanation_id] = shadow.shadow_id
            self.metrics.prediction_commitments += 1

    def _ground_transition_batch(
        self,
        schema_id: int,
        before: PerceptionBatch,
        after: PerceptionBatch,
        decision_id: int,
    ) -> PerceptionBatch:
        atoms = self._source_atoms(schema_id)
        assignments: dict[str, object] = {}
        assignments["domain"] = f"explanation-domain:{decision_id}"
        assignments["codomain"] = f"explanation-codomain:{decision_id}"
        pairs = self.runtime._correspond_regions(before, after)
        before_relations: dict[str, int] = {}
        after_relations: dict[str, int] = {}
        if pairs:
            before_region, after_region, _form = pairs[0]
            before_relations = {
                str(self.runtime.graph.terms.value(head)): value
                for head, value in self.runtime._entity_relations(
                    before.facts, before_region
                ).items()
            }
            after_relations = {
                str(self.runtime.graph.terms.value(head)): value
                for head, value in self.runtime._entity_relations(
                    after.facts, after_region
                ).items()
            }
        variables: dict[str, object] = {}
        for head, arguments in atoms:
            if head == "Domain" and len(arguments) == 1 and str(arguments[0]).startswith("?v"):
                variables[str(arguments[0])] = assignments["domain"]
            elif head == "Codomain" and len(arguments) == 1 and str(arguments[0]).startswith("?v"):
                variables[str(arguments[0])] = assignments["codomain"]
            elif head in {"Before", "After"} and len(arguments) == 3:
                carrier, relation, value = arguments
                if isinstance(carrier, str) and carrier.startswith("?v"):
                    variables[carrier] = assignments[
                        "domain" if head == "Before" else "codomain"
                    ]
                source = before_relations if head == "Before" else after_relations
                if isinstance(value, str) and value.startswith("?v") and str(relation) in source:
                    prior = variables.get(value)
                    observed_value = self.runtime.graph.terms.value(source[str(relation)])
                    if prior is not None and prior != observed_value:
                        raise ValueError("observed transition violates its learned variable sharing")
                    variables[value] = observed_value
        facts = []
        for head, arguments in atoms:
            grounded = []
            for argument in arguments:
                if isinstance(argument, str) and argument.startswith("?v"):
                    if argument not in variables:
                        raise ValueError("learned transition could not be grounded from its own evidence")
                    grounded.append(variables[argument])
                else:
                    grounded.append(argument)
            facts.append(self.runtime.graph.terms.ground_atom(head, tuple(grounded)))
        return PerceptionBatch(
            context=f"explanation-outcome:{decision_id}",
            facts=tuple(facts),
            form_terms=(),
            region_terms=(),
            outline_terms=(),
            source="experience:transition",
        )

    def observe_outcome(
        self,
        decision: ExplanationDecision | None,
        *,
        before: PerceptionBatch,
        after: PerceptionBatch,
        observed_schema_id: int,
        progress_delta: float,
        reward: float | None,
    ) -> dict[str, Any] | None:
        stats = self._outcomes[observed_schema_id]
        stats.observations += 1
        stats.progress_total += progress_delta
        stats.reward_total += float(reward or 0.0)
        if progress_delta == 0 and not any(
            head == "Change" for head, _args in self._effect_signature(observed_schema_id)
        ):
            stats.ineffective += 1
        if progress_delta < 0:
            stats.regressions += 1
        if decision is None or decision.mode != "explanation":
            return None

        observed = self._ground_transition_batch(
            observed_schema_id, before, after, decision.decision_id
        )
        resolutions = []
        before_signatures = {
            prediction.signature
            for prediction in decision.predictions
            if prediction.action_id == decision.selected_action_id
        }
        surviving_signatures = set()
        prediction_by_explanation = {
            prediction.explanation_id: prediction
            for prediction in decision.predictions
            if prediction.explanation_id is not None
            and prediction.action_id == decision.selected_action_id
        }
        for explanation_id, shadow_id in sorted(decision.shadow_by_explanation.items()):
            explanation = self._explanations[explanation_id]
            prediction = prediction_by_explanation[explanation_id]
            support_before = prediction.support
            if self.runtime.reconcile_shadow(shadow_id, observed):
                status = REIFIED
                explanation.confirmations += 1
                explanation.score += 0.08
                surviving_signatures.add(prediction.signature)
                self.metrics.shadows_reified += 1
                confirmed = 1
            else:
                shadow = self.runtime.shadows[shadow_id]
                self.runtime.refute_shadow(
                    shadow_id,
                    incompatible_constraints=set(shadow.open_constraints),
                    contradictory_evidence=observed.facts,
                    context=observed.context,
                    provenance="experience:transition",
                )
                status = REFUTED
                explanation.refutations += 1
                explanation.contradictions.append(shadow_id)
                explanation.score -= 0.20
                self.metrics.shadows_refuted += 1
                confirmed = 0
            explanation.evidence_accounted_for.append(
                ExplanationEvidence(
                    decision.decision_id,
                    decision.selected_action_id,
                    shadow_id,
                    status,
                    observed_schema_id,
                )
            )
            self.metrics.calibration.append((support_before, confirmed))
            if explanation.refutations >= self.config.retire_after_refutations:
                explanation.retired = True
                self.metrics.explanations_retired += 1
                self.metrics.explanation_lifetimes.append(
                    decision.decision_id - explanation.created_decision
                )
            resolutions.append(
                {
                    "explanation": explanation_id,
                    "shadow": shadow_id,
                    "status": status,
                    "support_before": support_before,
                    "score_after": explanation.score,
                }
            )

        ambiguity_reduced = (
            len(before_signatures) > 1
            and len(surviving_signatures) < len(before_signatures)
        )
        if decision.selected_for_discrimination and ambiguity_reduced:
            self.metrics.discrimination_settlements += 1
        if decision.changed_top_action:
            if progress_delta > 0:
                self.metrics.progress_after_changed_actions += 1
                self.metrics.completions_after_changed_actions += int(progress_delta)
            elif progress_delta < 0:
                self.metrics.regressions_after_changed_actions += 1
        trace = {
            "event": "explanation-resolution",
            "decision": decision.decision_id,
            "selected_action": decision.selected_action_id,
            "observed_schema": self.runtime.graph.canonical_hash[observed_schema_id],
            "progress_delta": progress_delta,
            "resolutions": resolutions,
            "ambiguity_before": len(before_signatures),
            "ambiguity_after": len(surviving_signatures),
            "ambiguity_reduced": ambiguity_reduced,
        }
        self.runtime.trace.append(trace)
        return trace

    def reset_episode(self) -> None:
        for explanation_id in self._active_ids:
            explanation = self._explanations[explanation_id]
            if not explanation.retired:
                explanation.retired = True
                self.metrics.explanations_retired += 1
                self.metrics.explanation_lifetimes.append(
                    self._decision - explanation.created_decision
                )
        self._active_ids = ()

    def decision_trace(self, decision: ExplanationDecision) -> dict[str, Any]:
        return {
            "event": "explanation-decision",
            "decision": decision.decision_id,
            "mode": decision.mode,
            "active_explanations": [
                {
                    "id": explanation.explanation_id,
                    "support": explanation.score,
                    "schemas": [
                        self.runtime.graph.canonical_hash[schema_id]
                        for schema_id in explanation.constituent_schema_ids
                    ],
                    "binding_schemas": [
                        self.runtime.graph.canonical_hash[binding.schema_id]
                        for binding in explanation.relevant_bindings
                    ],
                    "open_ports": list(explanation.unresolved_ports),
                    "commitments": list(explanation.commitments),
                }
                for explanation in self.active_explanations
            ],
            "predictions": [
                {
                    "explanation": item.explanation_id,
                    "schema": self.runtime.graph.canonical_hash[item.schema_id],
                    "action": item.action_id,
                    "signature": [
                        [head, list(arguments)] for head, arguments in item.signature
                    ],
                    "support": item.support,
                    "progress": item.progress,
                    "risk": item.risk,
                }
                for item in decision.predictions
            ],
            "action_ranking": [asdict(item) for item in decision.rankings],
            "baseline_top": decision.baseline_action_id,
            "selected": decision.selected_action_id,
            "changed_top_action": decision.changed_top_action,
            "selected_for_discrimination": decision.selected_for_discrimination,
            "projected_shadows": dict(sorted(decision.shadow_by_explanation.items())),
        }

    def report(self) -> dict[str, Any]:
        active_counts = self.metrics.active_counts
        constituent_counts = self.metrics.constituent_counts
        lifetimes = self.metrics.explanation_lifetimes
        calibration = self.metrics.calibration
        changes = self.metrics.action_changes
        return {
            **asdict(self.metrics),
            "mean_active_explanations": sum(active_counts) / len(active_counts) if active_counts else 0.0,
            "max_active_explanations": max(active_counts, default=0),
            "mean_constituent_schema_count": sum(constituent_counts) / len(constituent_counts) if constituent_counts else 0.0,
            "mean_explanation_lifetime": sum(lifetimes) / len(lifetimes) if lifetimes else 0.0,
            "action_changing_precision": self.metrics.progress_after_changed_actions / changes if changes else None,
            "calibration_mean_support": sum(item[0] for item in calibration) / len(calibration) if calibration else None,
            "calibration_confirmation_rate": sum(item[1] for item in calibration) / len(calibration) if calibration else None,
        }


def bound_schema_ids(bindings: Iterable[Binding]) -> tuple[int, ...]:
    """Stable unique schema IDs from a predecessor binding frontier."""

    return tuple(sorted({binding.schema_id for binding in bindings}))
