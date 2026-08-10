"""Native game-blind prospective control over shared-workspace bindings."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Sequence

from .epistemic_workspace import content_hash
from .perception import Grid
from .shared_cognition import GroundedProposal, NativeSharedCognition, PredictionCommitment
from .visual_entities import VisualFigure, correspond_figures, extract_visual_figures


@dataclass(slots=True)
class TrackedPair:
    hypothesis_id: str
    binding_id: str
    operator: str
    revision_of: str | None
    left: VisualFigure
    right: VisualFigure
    action_deltas: dict[int, list[tuple[int, int]]] = field(default_factory=dict)
    prospective_confirmations: int = 0
    prospective_refutations: int = 0

    @property
    def relative2(self) -> tuple[int, int]:
        return (
            self.left.centroid2[0] - self.right.centroid2[0],
            self.left.centroid2[1] - self.right.centroid2[1],
        )

    @property
    def residual(self) -> int:
        x, y = self.relative2
        return abs(x) + abs(y)

    @property
    def control_eligible(self) -> bool:
        return self.revision_of is not None and self.prospective_confirmations > 0

    def modal_delta(self, action_id: int) -> tuple[tuple[int, int], int] | None:
        values = self.action_deltas.get(action_id, ())
        if not values:
            return None
        counts = Counter(values)
        delta, support = min(counts.items(), key=lambda item: (-item[1], item[0]))
        return delta, support


@dataclass(frozen=True, slots=True)
class NativeControlPlan:
    mode: str
    action_id: int
    fallback_action_id: int
    commitments: tuple[PredictionCommitment, ...]
    tracked_binding_ids: tuple[str, ...]
    reason: str


def _figure_index(value: object) -> int | None:
    text = str(value)
    if not text.startswith("figure:"):
        return None
    try:
        return int(text.rsplit(":", 1)[1])
    except ValueError:
        return None


class NativeProspectiveController:
    """Learn opaque effects, probe disagreements, and gate revised control."""

    def __init__(
        self,
        cognition: NativeSharedCognition,
        *,
        max_ambiguous_probes: int = 4,
        max_revision_probes: int = 1,
        max_control_decisions: int = 24,
    ) -> None:
        self.cognition = cognition
        self.max_ambiguous_probes = max_ambiguous_probes
        self.max_revision_probes = max_revision_probes
        self.max_control_decisions = max_control_decisions
        self.ambiguous_probes = 0
        self.revision_probes = 0
        self.control_decisions = 0
        self.action_uses: Counter[int] = Counter()
        self.records: list[TrackedPair] = []
        self.last_plan: NativeControlPlan | None = None
        self._opaque_to_action: dict[str, int] = {}

    @staticmethod
    def intervention_ref(action_id: int) -> str:
        return "im:" + content_hash({"opaque_channel": int(action_id)})[:24]

    def _current_records(self) -> list[TrackedPair]:
        if not self.records:
            return []
        confirmed = [
            item
            for item in self.records
            if item.control_eligible and self._has_improving_model(item)
        ]
        # Compute may raise attention, but a newer unsupported proposal cannot
        # evict a prospectively confirmed controller. Evidence-first priority
        # is the operational counterpart of support != salience.
        latest_hypothesis = (
            confirmed[-1].hypothesis_id
            if confirmed
            else self.records[-1].hypothesis_id
        )
        return [item for item in self.records if item.hypothesis_id == latest_hypothesis]

    @property
    def has_confirmed_control(self) -> bool:
        return any(
            item.control_eligible and self._has_improving_model(item)
            for item in self.records
        )

    def _has_improving_model(self, record: TrackedPair) -> bool:
        for action_id in record.action_deltas:
            model = record.modal_delta(action_id)
            if model is None:
                continue
            scalar = self._predicted_scalar_delta(record, model[0])
            gain = -scalar if record.operator == "Decrease" else scalar
            if gain > 0:
                return True
        return False

    def activate(self, grounded: GroundedProposal, grid: Grid) -> tuple[TrackedPair, ...]:
        if any(item.hypothesis_id == grounded.hypothesis_id for item in self.records):
            return ()
        figures = extract_visual_figures(grid)
        hypothesis = self.cognition.epistemic.object(grounded.hypothesis_id)
        operator = str(hypothesis.payload["operator"])
        revision_of = hypothesis.payload.get("revision_of")
        by_pair: dict[tuple[str, str], str] = {}
        for binding_id in grounded.binding_ids:
            binding = self.cognition.epistemic.object(binding_id)
            pair = binding.payload.get("effect_pair")
            if not isinstance(pair, list) or len(pair) != 2:
                continue
            key = tuple(sorted((str(pair[0]), str(pair[1]))))
            by_pair.setdefault(key, binding_id)
        created: list[TrackedPair] = []
        for pair, binding_id in sorted(by_pair.items()):
            indexes = tuple(_figure_index(value) for value in pair)
            if any(value is None or value >= len(figures) for value in indexes):
                continue
            left = figures[int(indexes[0])]
            right = figures[int(indexes[1])]
            predecessor = next(
                (
                    item
                    for item in reversed(self.records)
                    if frozenset((item.left.relative_identity, item.right.relative_identity))
                    == frozenset((left.relative_identity, right.relative_identity))
                ),
                None,
            )
            action_deltas = (
                {}
                if predecessor is None
                else {
                    action: list(values)
                    for action, values in predecessor.action_deltas.items()
                }
            )
            created.append(
                TrackedPair(
                    hypothesis_id=grounded.hypothesis_id,
                    binding_id=binding_id,
                    operator=operator,
                    revision_of=None if revision_of is None else str(revision_of),
                    left=left,
                    right=right,
                    action_deltas=action_deltas,
                )
            )
        self.records.extend(created)
        return tuple(created)

    @staticmethod
    def _predicted_scalar_delta(
        record: TrackedPair, vector: tuple[int, int]
    ) -> int:
        before = record.residual
        relative = record.relative2
        after = abs(relative[0] + vector[0]) + abs(relative[1] + vector[1])
        return after - before

    def _commit(
        self, records: Sequence[TrackedPair], action_id: int
    ) -> tuple[PredictionCommitment, ...]:
        intervention = self.intervention_ref(action_id)
        self._opaque_to_action[intervention] = action_id
        output: list[PredictionCommitment] = []
        for record in records:
            model = record.modal_delta(action_id)
            if model is None:
                continue
            vector, _support = model
            output.append(
                self.cognition.predict(
                    binding_id=record.binding_id,
                    intervention_ref=intervention,
                    current_residual=record.residual,
                    predicted_delta=self._predicted_scalar_delta(record, vector),
                    basis_revision=self.cognition.epistemic.revision,
                )
            )
        return tuple(output)

    def plan(
        self, legal_actions: Sequence[int], *, fallback_action_id: int | None = None
    ) -> NativeControlPlan:
        legal = tuple(sorted(set(int(value) for value in legal_actions)))
        if not legal:
            raise ValueError("prospective control requires legal interventions")
        fallback = (
            min(legal, key=lambda value: (self.action_uses[value], value))
            if fallback_action_id is None
            else int(fallback_action_id)
        )
        if fallback not in legal:
            raise ValueError("fallback intervention is not legal")
        records = self._current_records()
        selected = fallback
        mode = "fallback"
        reason = "no-live-grounding"

        # Confirmed revised hypotheses may exploit only an empirically learned
        # operator-consistent improvement.
        controls: list[tuple[float, int, int, int]] = []
        for action in legal:
            for record in records:
                if not record.control_eligible:
                    continue
                model = record.modal_delta(action)
                if model is None:
                    continue
                scalar = self._predicted_scalar_delta(record, model[0])
                gain = -scalar if record.operator == "Decrease" else scalar
                if gain > 0:
                    controls.append(
                        (-gain / max(1, record.residual), -model[1], self.action_uses[action], action)
                    )
        if controls and self.control_decisions < self.max_control_decisions:
            _gain, _support, _uses, selected = min(controls)
            mode, reason = "control", "confirmed-revised-potential"
            self.control_decisions += 1
        elif len(records) == 1 and records[0].revision_of is not None:
            # A unique revision receives one separately reserved prospective
            # confirmation probe before any control authority.
            candidates = []
            for action in legal:
                model = records[0].modal_delta(action)
                if model is None:
                    continue
                scalar = self._predicted_scalar_delta(records[0], model[0])
                gain = -scalar if records[0].operator == "Decrease" else scalar
                candidates.append((-gain, -model[1], self.action_uses[action], action))
            if candidates and self.revision_probes < self.max_revision_probes:
                _gain, _support, _uses, selected = min(candidates)
                mode, reason = "probe", "unique-revision-confirmation"
                self.revision_probes += 1
        elif len(records) == 1 and self.ambiguous_probes < self.max_ambiguous_probes:
            # A uniquely grounded initial proposal still needs a prospective
            # environmental return before Qwen can make an evidence-driven
            # revision. It receives no direct control authority.
            candidates = []
            for action in legal:
                model = records[0].modal_delta(action)
                if model is None:
                    continue
                scalar = self._predicted_scalar_delta(records[0], model[0])
                candidates.append(
                    (-abs(scalar), -model[1], self.action_uses[action], action)
                )
            if candidates:
                _magnitude, _support, _uses, selected = min(candidates)
                mode, reason = "probe", "unique-initial-evidence"
                self.ambiguous_probes += 1
        elif len(records) >= 2 and self.ambiguous_probes < self.max_ambiguous_probes:
            candidates = []
            for action in legal:
                outcomes = []
                modeled_records = []
                for record in records:
                    model = record.modal_delta(action)
                    if model is None:
                        continue
                    outcomes.append((model[0], self._predicted_scalar_delta(record, model[0])))
                    modeled_records.append(record)
                disagreement = sum(
                    left != right
                    for index, left in enumerate(outcomes)
                    for right in outcomes[index + 1 :]
                )
                if disagreement:
                    candidates.append(
                        (-disagreement, self.action_uses[action], action, tuple(modeled_records))
                    )
            if candidates:
                _disagreement, _uses, selected, _modeled = min(candidates)
                mode, reason = "probe", "alternative-disagreement"
                self.ambiguous_probes += 1

        commitments = () if mode == "fallback" else self._commit(records, selected)
        if mode != "fallback" and not commitments:
            selected, mode, reason = fallback, "fallback", "no-modeled-prediction"
        plan = NativeControlPlan(
            mode=mode,
            action_id=selected,
            fallback_action_id=fallback,
            commitments=commitments,
            tracked_binding_ids=tuple(item.binding_id for item in records),
            reason=reason,
        )
        self.last_plan = plan
        return plan

    def observe(self, action_id: int, before: Grid, after: Grid, *, transition_id: str) -> None:
        self.action_uses[int(action_id)] += 1
        before_figures = extract_visual_figures(before)
        after_figures = extract_visual_figures(after)
        correspondence = correspond_figures(before_figures, after_figures)
        observed_delta: dict[str, int | None] = {}
        direct: dict[str, bool] = {}
        for record in self.records:
            before_left = min(
                (item for item in before_figures if item.relative_identity == record.left.relative_identity),
                default=None,
                key=lambda item: item.anchor,
            )
            before_right = min(
                (item for item in before_figures if item.relative_identity == record.right.relative_identity),
                default=None,
                key=lambda item: item.anchor,
            )
            after_left = None if before_left is None else correspondence.get(before_left)
            after_right = None if before_right is None else correspondence.get(before_right)
            if after_left is None or after_right is None:
                observed_delta[record.binding_id] = None
                direct[record.binding_id] = False
                continue
            old = record.residual
            old_vector = record.relative2
            new_vector = (
                after_left.centroid2[0] - after_right.centroid2[0],
                after_left.centroid2[1] - after_right.centroid2[1],
            )
            vector_delta = (new_vector[0] - old_vector[0], new_vector[1] - old_vector[1])
            record.left, record.right = after_left, after_right
            scalar_delta = record.residual - old
            observed_delta[record.binding_id] = scalar_delta
            direct[record.binding_id] = True
            # Calibration is control competence, not epistemic support.
            record.action_deltas.setdefault(int(action_id), []).append(vector_delta)

        plan = self.last_plan
        if plan is None or plan.action_id != int(action_id):
            return
        by_binding = {item.binding_id: item for item in self.records}
        for commitment in plan.commitments:
            result = self.cognition.adjudicate(
                commitment,
                transition_id=transition_id,
                observed_delta=observed_delta.get(commitment.binding_id),
                direct=direct.get(commitment.binding_id, False),
            )
            record = by_binding[commitment.binding_id]
            if plan.reason == "unique-revision-confirmation":
                if result.verdict == "supports":
                    record.prospective_confirmations += 1
                elif result.verdict == "refutes":
                    record.prospective_refutations += 1

    def report(self) -> dict[str, object]:
        return {
            "ambiguous_probes": self.ambiguous_probes,
            "revision_probes": self.revision_probes,
            "control_decisions": self.control_decisions,
            "records": [
                {
                    "hypothesis_id": item.hypothesis_id,
                    "binding_id": item.binding_id,
                    "revision_of": item.revision_of,
                    "residual": item.residual,
                    "prospective_confirmations": item.prospective_confirmations,
                    "prospective_refutations": item.prospective_refutations,
                    "modeled_interventions": len(item.action_deltas),
                }
                for item in self.records
            ],
        }
