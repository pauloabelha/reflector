"""Live prospective controller used by the v1.4 paired gate.

This adapter keeps action-model calibration distinct from epistemic support.
Historical transitions may seed a prediction model, but only a prediction
committed after a Qwen revision and matched by a later direct transition can
authorize ordinary control.
"""

from __future__ import annotations

import importlib.util
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent


def _load(name: str, path: Path) -> Any:
    resolved = path.resolve()
    for module in reversed(tuple(sys.modules.values())):
        filename = getattr(module, "__file__", None)
        if filename is not None and Path(filename).resolve() == resolved:
            return module
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


PC = _load("prospective_control_live_v14", HERE / "prospective_control.py")
WORKSPACE_V0 = _load(
    "prospective_workspace_v0",
    HERE.parent / "parallel-cognitive-workspace-v0" / "experiment.py",
)
Q0 = WORKSPACE_V0.V0


@dataclass(slots=True)
class CandidateRecord:
    schema_object_id: str
    template_hash: str
    candidate_id: str
    operator: str
    effect_pair: tuple[str, str]
    pair_binding: Any
    activated_at_action: int
    revision_of: str | None
    population_complete: bool
    unique_population: bool
    graph_binding_id: str | None = None
    prospective_confirmations: int = 0
    prospective_refutations: int = 0

    @property
    def control_eligible(self) -> bool:
        return (
            self.revision_of is not None
            and self.population_complete
            and self.unique_population
        )


def _unordered_pair(value: Sequence[str]) -> tuple[str, str]:
    left, right = (str(item) for item in value)
    return tuple(sorted((left, right)))  # type: ignore[return-value]


def _modal_models(binding: Any) -> tuple[Any, ...]:
    output = []
    for action, values in sorted(binding.action_deltas.items()):
        if not values:
            continue
        counts = Counter(tuple(int(part) for part in value) for value in values)
        delta, support = min(counts.items(), key=lambda item: (-item[1], item[0]))
        output.append(PC.ActionModel(int(action), delta, int(support)))
    return tuple(output)


def _seed_historical_models(binding: Any, history: Sequence[Mapping[str, Any]]) -> None:
    """Trace a current pair backward and learn opaque action effects only.

    These samples never increment prospective confirmations and never create
    support edges. They merely let R2 make falsifiable predictions for a later
    active probe instead of relabeling blind fallback exploration as a probe.
    """

    left_key, right_key = binding.left_key, binding.right_key
    left_anchor, right_anchor = binding.left_anchor, binding.right_anchor
    for transition in reversed(tuple(history)):
        before = tuple(tuple(int(cell) for cell in row) for row in transition["before_grid"])
        after = tuple(tuple(int(cell) for cell in row) for row in transition["after_grid"])
        before_figures = Q0.select_figures(before)
        after_figures = Q0.select_figures(after)
        after_left = Q0.locate_figure(after_figures, left_key, left_anchor)
        after_right = Q0.locate_figure(after_figures, right_key, right_anchor)
        if after_left is None or after_right is None:
            break
        correspondence = Q0.BASE.correspond(before_figures, after_figures)
        inverse = {target: source for source, target in correspondence.items()}
        before_left = inverse.get(after_left)
        before_right = inverse.get(after_right)
        if before_left is None or before_right is None:
            break
        old_relative = (
            before_left.centroid2[0] - before_right.centroid2[0],
            before_left.centroid2[1] - before_right.centroid2[1],
        )
        new_relative = (
            after_left.centroid2[0] - after_right.centroid2[0],
            after_left.centroid2[1] - after_right.centroid2[1],
        )
        delta = (new_relative[0] - old_relative[0], new_relative[1] - old_relative[1])
        if delta != (0, 0):
            binding.action_deltas.setdefault(int(transition["action_id"]), []).append(delta)
        left_key, right_key = before_left.local_key, before_right.local_key
        left_anchor, right_anchor = before_left.anchor, before_right.anchor


class ProspectiveWorkspaceController:
    """Preserve alternatives, probe prospectively, then gate revised control."""

    def __init__(self, *, max_probes: int = 4, max_control_decisions: int = 24) -> None:
        self.inner = Q0.PairPotentialController((), "externally-proposed")
        self.records: list[CandidateRecord] = []
        self.active_schema_ids: set[str] = set()
        self.action_uses: Counter[int] = self.inner.uses
        self.max_probes = int(max_probes)
        self.max_control_decisions = int(max_control_decisions)
        self.probe_decisions = 0
        self.control_decisions = 0
        self.last_plan: Any | None = None
        self.last_plan_records: dict[str, CandidateRecord] = {}

    def activate(
        self,
        template: Any,
        state: Mapping[str, Any],
        figures: Sequence[Any],
        *,
        action_count: int,
        source_task: str,
        history: Sequence[Mapping[str, Any]] = (),
        revision_of: str | None = None,
    ) -> dict[str, Any]:
        if source_task in self.active_schema_ids:
            return {"status": "duplicate-active", "schema_object_id": source_task}
        population = PC.grounding_alternatives(template, state)
        grouped: dict[tuple[str, str], Any] = {}
        for alternative in population.alternatives:
            grouped.setdefault(_unordered_pair(alternative.effect_pair), alternative)
        if not grouped:
            return {
                "status": "unbound",
                "grounding_count": population.observed_grounding_count,
                "population_complete": population.complete,
            }
        unique_population = len(grouped) == 1
        created: list[CandidateRecord] = []
        for pair, alternative in sorted(grouped.items()):
            grounding = {
                "status": "bound",
                "template_hash": template.canonical_hash,
                "operator": template.operator,
                "effect_pair": list(pair),
            }
            bindings = Q0.bindings_from_groundings((grounding,), dict(state), figures)
            if len(bindings) != 1:
                continue
            pair_binding = bindings[0]
            predecessor = next(
                (
                    record
                    for record in reversed(self.records)
                    if _unordered_pair(record.effect_pair) == pair
                ),
                None,
            )
            if predecessor is not None:
                pair_binding.action_deltas = {
                    int(action): [tuple(delta) for delta in values]
                    for action, values in predecessor.pair_binding.action_deltas.items()
                }
            else:
                _seed_historical_models(pair_binding, history)
            record = CandidateRecord(
                schema_object_id=source_task,
                template_hash=template.canonical_hash,
                candidate_id=alternative.candidate_id,
                operator=template.operator,
                effect_pair=pair,
                pair_binding=pair_binding,
                activated_at_action=int(action_count),
                revision_of=None if revision_of is None else str(revision_of),
                population_complete=population.complete,
                unique_population=unique_population,
            )
            self.records.append(record)
            self.inner.bindings.append(pair_binding)
            created.append(record)
        if not created:
            return {"status": "unbound", "population_complete": population.complete}
        self.active_schema_ids.add(source_task)
        return {
            "status": "bound" if unique_population and population.complete else "ambiguous-active",
            "template_hash": template.canonical_hash,
            "operator": template.operator,
            "effect_pair": list(created[0].effect_pair) if unique_population else None,
            "effect_pair_count": len(grouped),
            "grounding_count": population.observed_grounding_count,
            "population_complete": population.complete,
            "candidates": [
                {
                    "candidate_id": record.candidate_id,
                    "effect_pair": list(record.effect_pair),
                    "revision_control_eligible": record.control_eligible,
                }
                for record in created
            ],
        }

    def link_graph_binding(self, candidate_id: str, graph_binding_id: str) -> None:
        record = next(item for item in reversed(self.records) if item.candidate_id == candidate_id)
        record.graph_binding_id = str(graph_binding_id)

    def _active_records(self) -> list[CandidateRecord]:
        eligible_revisions = [item for item in self.records if item.control_eligible]
        if eligible_revisions:
            latest = max(item.activated_at_action for item in eligible_revisions)
            return [item for item in eligible_revisions if item.activated_at_action == latest]
        if not self.records:
            return []
        latest = max(item.activated_at_action for item in self.records)
        return [
            item
            for item in self.records
            if item.activated_at_action == latest and item.population_complete
        ]

    def plan(
        self,
        legal_actions: Sequence[int],
        *,
        observation_digest: str,
        basis_revision: int,
    ) -> tuple[Any, Any]:
        records = self._active_records()
        live_bindings = []
        self.last_plan_records = {}
        for record in records:
            alternative = PC.GroundingAlternative(
                candidate_id=record.candidate_id,
                template_hash=record.template_hash,
                substitution=(),
                effect_pair=record.effect_pair,
            )
            live = PC.LiveBinding.build(
                schema_object_id=record.schema_object_id,
                alternative=alternative,
                operator=record.operator,
                relative2=tuple(record.pair_binding.relative2),
                action_models=_modal_models(record.pair_binding),
                confirmations=(
                    record.prospective_confirmations if record.control_eligible else 0
                ),
            )
            live_bindings.append(live)
            self.last_plan_records[live.binding_id] = record
        planner = PC.ProspectiveController(live_bindings)
        plan = planner.plan(
            legal_actions,
            observation_digest=str(observation_digest),
            basis_revision=int(basis_revision),
            action_uses=self.action_uses,
        )
        if plan.mode == "probe" and self.probe_decisions >= self.max_probes:
            plan = PC.fallback_plan(
                plan,
                action_id=plan.fallback_action_id,
                reason="probe-budget-exhausted",
            )
        if plan.mode == "control" and self.control_decisions >= self.max_control_decisions:
            plan = PC.fallback_plan(
                plan,
                action_id=plan.fallback_action_id,
                reason="control-budget-exhausted",
            )
        selected = next(
            (
                prediction
                for prediction in plan.predictions
                if prediction.prediction_id in plan.selected_prediction_ids
            ),
            None,
        )
        record = None if selected is None else self.last_plan_records.get(selected.binding_id)
        if plan.mode == "probe":
            self.probe_decisions += 1
        elif plan.mode == "control":
            self.control_decisions += 1
        self.last_plan = plan
        decision = Q0.Decision(
            action_id=plan.action_id,
            fallback_action_id=plan.fallback_action_id,
            reason=f"prospective-{plan.mode}",
            template_hash=None if record is None else record.template_hash,
            residual_before=None if selected is None else selected.current_residual,
            predicted_residual_after=None if selected is None else selected.predicted_residual,
            prior_used=plan.mode == "control",
        )
        return decision, plan

    def observe(self, action: int, before_grid: Any, after_grid: Any) -> dict[str, Any]:
        learning = self.inner.observe(action, before_grid, after_grid)
        plan = self.last_plan
        if plan is None or int(action) != int(plan.action_id):
            return {**learning, "prospective_adjudication": None}
        observed: dict[str, Any] = {}
        binding_events = list(learning.get("bindings", ()))
        by_pair_binding = {
            id(record.pair_binding): record for record in self.records
        }
        for index, pair_binding in enumerate(self.inner.bindings):
            record = by_pair_binding.get(id(pair_binding))
            if record is None or index >= len(binding_events):
                continue
            event = binding_events[index]
            live_id = next(
                (
                    prediction.binding_id
                    for prediction in plan.predictions
                    if self.last_plan_records.get(prediction.binding_id) is record
                ),
                None,
            )
            if live_id is None:
                continue
            observed[live_id] = PC.ObservedConsequence(
                direct=bool(event.get("direct")),
                delta=(
                    None
                    if event.get("delta") is None
                    else tuple(int(item) for item in event["delta"])
                ),
                residual=(
                    None if event.get("residual") is None else int(event["residual"])
                ),
            )
        adjudication = PC.adjudicate(plan, action_id=int(action), observed=observed)
        if plan.mode == "probe":
            for judgment in adjudication.judgments:
                record = self.last_plan_records.get(judgment.binding_id)
                if record is None or not record.control_eligible:
                    continue
                if judgment.status == "supports":
                    record.prospective_confirmations += 1
                elif judgment.status == "refutes":
                    record.prospective_refutations += 1
        return {
            **learning,
            "prospective_adjudication": PC.document(adjudication),
        }

    def restore_plan(self, value: Mapping[str, Any]) -> None:
        """Restore a durably published plan before chronological transition replay."""

        predictions = tuple(
            PC.ProspectivePrediction(
                prediction_id=str(item["prediction_id"]),
                binding_id=str(item["binding_id"]),
                candidate_id=str(item["candidate_id"]),
                action_id=int(item["action_id"]),
                basis_revision=int(item["basis_revision"]),
                current_residual=int(item["current_residual"]),
                predicted_residual=(
                    None
                    if item.get("predicted_residual") is None
                    else int(item["predicted_residual"])
                ),
                predicted_delta=(
                    None
                    if item.get("predicted_delta") is None
                    else tuple(int(part) for part in item["predicted_delta"])
                ),
                model_support=int(item["model_support"]),
                modeled=bool(item["modeled"]),
            )
            for item in value.get("predictions", ())
        )
        self.last_plan = PC.ControlPlan(
            plan_id=str(value["plan_id"]),
            basis_revision=int(value["basis_revision"]),
            observation_digest=str(value["observation_digest"]),
            mode=str(value["mode"]),
            action_id=int(value["action_id"]),
            fallback_action_id=int(value["fallback_action_id"]),
            predictions=predictions,
            selected_prediction_ids=tuple(
                str(item) for item in value.get("selected_prediction_ids", ())
            ),
            discrimination_pairs=int(value.get("discrimination_pairs", 0)),
            probe_basis=(
                None if value.get("probe_basis") is None else str(value["probe_basis"])
            ),
        )
        by_candidate = {
            item.candidate_id: item for item in self._active_records()
        }
        self.last_plan_records = {
            prediction.binding_id: by_candidate[prediction.candidate_id]
            for prediction in predictions
            if prediction.candidate_id in by_candidate
        }
        if self.last_plan.mode == "probe":
            self.probe_decisions += 1
        elif self.last_plan.mode == "control":
            self.control_decisions += 1

    def report(self) -> dict[str, Any]:
        return {
            **self.inner.report(),
            "probe_decisions": self.probe_decisions,
            "control_decisions": self.control_decisions,
            "records": [
                {
                    "schema_object_id": item.schema_object_id,
                    "template_hash": item.template_hash,
                    "candidate_id": item.candidate_id,
                    "effect_pair": list(item.effect_pair),
                    "revision_of": item.revision_of,
                    "population_complete": item.population_complete,
                    "unique_population": item.unique_population,
                    "control_eligible": item.control_eligible,
                    "prospective_confirmations": item.prospective_confirmations,
                    "prospective_refutations": item.prospective_refutations,
                    "graph_binding_id": item.graph_binding_id,
                    "action_models": [asdict(model) for model in _modal_models(item.pair_binding)],
                }
                for item in self.records
            ],
        }
