"""Online, game-blind option induction for compositional progress goals.

The inducer consumes arbitrary consecutive transitions.  It maintains each
variable's situated grounding through exact geometric correspondence, learns
opaque action effects per variable, and proposes only actions whose learned
translation predicts lower potential.  Direct outcomes are returned in the
``EnvironmentOutcome`` contract consumed by ``SharedBroadPolicy``.
"""

from __future__ import annotations

from collections import defaultdict
from collections import Counter
from dataclasses import dataclass, replace
from itertools import product
from typing import Any, Mapping, Sequence

import broad_policy_bridge as bridge
import compositional_dsl as dsl
import progress_synthesis as synthesis


class OnlineOptionError(ValueError):
    pass


Grid = tuple[tuple[int, ...], ...]
MAX_CORRESPONDENCE_ALTERNATIVES = 32


@dataclass(frozen=True, slots=True)
class EffectObservation:
    schema_id: str
    lineage_id: str
    variable: str
    opaque_action: int
    delta: tuple[int, int]
    transition_id: str


@dataclass(frozen=True, slots=True)
class EvaluatorState:
    option_id: str
    schema_id: str
    lineage_id: str
    effect_variable: str
    binding_id: str
    binding: tuple[tuple[str, str], ...]
    potential_before: int
    predicted_after: int
    basis_ids: tuple[str, ...]
    frame_revision: int


@dataclass(frozen=True, slots=True)
class GroundingState:
    schema_id: str
    lineage_id: str
    alternatives: tuple[tuple[tuple[str, str], ...], ...]
    correspondence_status: str


def _grid(raw: Sequence[Sequence[int]]) -> Grid:
    grid = tuple(tuple(int(value) for value in row) for row in raw)
    if not grid or not grid[0] or any(len(row) != len(grid[0]) for row in grid):
        raise OnlineOptionError("observation must be a rectangular grid")
    return grid


def _fixed_lattice(raw: Sequence[Sequence[int]], factor: int) -> Grid:
    grid = _grid(raw)
    if factor == 1:return grid
    height,width=len(grid),len(grid[0])
    if height%factor or width%factor:raise OnlineOptionError("frame changed fixed lattice dimensions")
    rows=[]
    for top in range(0,height,factor):
        row=[]
        for left in range(0,width,factor):
            counts=Counter(grid[y][x] for y in range(top,top+factor) for x in range(left,left+factor))
            row.append(min(counts,key=lambda value:(-counts[value],value)))
        rows.append(tuple(row))
    return tuple(rows)


def _signature(region: Any) -> tuple[int, int, frozenset[tuple[int, int]]]:
    # Palette is deliberately absent.  Geometry is the observable invariant.
    return region.width, region.height, region.normalized


def _binding_id(schema_id: str, binding: Mapping[str, str]) -> str:
    return "grounding:" + synthesis.stable_hash(
        {"candidate_id": schema_id, "binding": dict(binding)}
    )[:24]


def _lineage_id(schema_id: str, binding: Mapping[str, str]) -> str:
    return "lineage:" + synthesis.stable_hash(
        {"schema_id": schema_id, "initial_binding": dict(sorted(binding.items()))}
    )[:24]


def _translated(region: Any, dx: int, dy: int) -> Any:
    return replace(
        region,
        x=region.x + dx,
        y=region.y + dy,
        cells=frozenset((x + dx, y + dy) for x, y in region.cells),
    )


def _correspond(
    before_scene: Any,
    after_scene: Any,
    binding: Mapping[str, str],
) -> tuple[tuple[dict[str, str], dict[str, tuple[int, int]]], ...]:
    before_by_id = {item.region_id: item for item in before_scene.regions}
    variables = sorted(binding)
    choices = []
    for variable in variables:
        source = before_by_id.get(binding[variable])
        if source is None:
            return ()
        matches = [
            item for item in after_scene.regions
            if _signature(item) == _signature(source)
        ]
        if not matches:
            return ()
        choices.append((variable, source, matches))
    rows = []
    for assignment in product(*(item[2] for item in choices)):
        if len({item.region_id for item in assignment}) != len(assignment):
            continue
        score = sum(
            abs(target.x - source.x) + abs(target.y - source.y)
            for (_variable, source, _matches), target in zip(choices, assignment, strict=True)
        )
        new_binding = {
            variable: target.region_id
            for (variable, _source, _matches), target in zip(choices, assignment, strict=True)
        }
        deltas = {
            variable: (target.x - source.x, target.y - source.y)
            for (variable, source, _matches), target in zip(choices, assignment, strict=True)
        }
        rows.append((score, new_binding, deltas))
    if not rows:
        return ()
    minimum = min(item[0] for item in rows)
    best = sorted(
        ((binding, deltas) for score, binding, deltas in rows if score == minimum),
        key=lambda item: tuple(sorted(item[0].items())),
    )
    if len(best) > MAX_CORRESPONDENCE_ALTERNATIVES:
        return ()
    return tuple(best)


class OnlineCompositionalOptionInducer:
    """Maintain live compositional groundings and opaque transition models."""

    def __init__(
        self,
        initial: Sequence[Sequence[int]],
        *,
        legal_actions: Sequence[int],
        candidates: Sequence[Any] | None = None,
        proposer: str = "r2",
    ) -> None:
        if proposer not in {"r2", "qwen", "kernel"}:
            raise OnlineOptionError("unknown option proposer")
        raw_initial = _grid(initial)
        initial_scene = synthesis.perceive(raw_initial)
        factor_x=len(raw_initial[0])//initial_scene.width;factor_y=len(raw_initial)//initial_scene.height
        if factor_x != factor_y or factor_x < 1:
            raise OnlineOptionError("initial perception has no stable square lattice")
        self.lattice_factor=factor_x
        self.current_grid = _fixed_lattice(raw_initial,self.lattice_factor)
        self.current_scene = synthesis.perceive(self.current_grid,coarsen=False)
        rows = tuple(dsl.propose(self.current_grid) if candidates is None else candidates)
        self.candidates: dict[str, Any] = {}
        self.lineages: dict[tuple[str, str], tuple[dict[str, str], ...]] = {}
        for candidate in rows:
            if candidate.ast.get("protocol") != "compositional-progress-dsl-v0":
                raise OnlineOptionError("online inducer accepts compositional goal ASTs only")
            dsl.validate_expression(candidate.ast["potential"])
            self.candidates[candidate.candidate_id] = candidate
            lineage=_lineage_id(candidate.candidate_id,candidate.binding)
            key=(candidate.candidate_id,lineage)
            self.lineages.setdefault(key, tuple())
            existing = list(self.lineages[key])
            if dict(candidate.binding) not in existing:
                existing.append(dict(candidate.binding))
            self.lineages[key] = tuple(existing)
        self.legal_actions = tuple(sorted({int(value) for value in legal_actions}))
        self.proposer = proposer
        self.frame_revision = 0
        self.effects: list[EffectObservation] = []
        self.evaluators: dict[str, EvaluatorState] = {}
        self.recent_transition_ids: list[str] = []

    def _usable_effects(self) -> dict[tuple[str, str, str, int], tuple[tuple[int, int], tuple[str, ...]]]:
        grouped: dict[tuple[str, str, str, int], list[EffectObservation]] = defaultdict(list)
        for row in self.effects:
            grouped[(row.schema_id, row.lineage_id, row.variable, row.opaque_action)].append(row)
        output = {}
        for key, rows in grouped.items():
            deltas = {row.delta for row in rows}
            if len(deltas) == 1:
                output[key] = (
                    next(iter(deltas)),
                    tuple(sorted({row.transition_id for row in rows})),
                )
        return output

    def option_proposals(
        self,
        *,
        control_candidate_ids: frozenset[str] = frozenset(),
    ) -> tuple[bridge.OptionProposal, ...]:
        models = self._usable_effects()
        proposals: dict[str, bridge.OptionProposal] = {}
        self.evaluators = {}
        for schema_id, candidate in sorted(self.candidates.items()):
          for (lineage_schema,lineage_id),alternatives in sorted(self.lineages.items()):
            if lineage_schema != schema_id:continue
            if len(alternatives) != 1:continue
            for binding in alternatives:
                situated = replace(
                    candidate,
                    binding=dict(binding),
                    binding_id=_binding_id(schema_id, binding),
                )
                try:
                    roles = dsl._region_map(self.current_scene, situated.binding)
                    before = dsl._eval(situated.ast["potential"], roles)
                except synthesis.SynthesisError:
                    continue
                for variable in sorted(binding):
                    for action in self.legal_actions:
                        model = models.get((schema_id, lineage_id, variable, action))
                        if model is None:
                            continue
                        (dx, dy), evidence_ids = model
                        trial = dict(roles)
                        trial[variable] = _translated(roles[variable], dx, dy)
                        predicted = dsl._eval(situated.ast["potential"], trial)
                        if predicted >= before:
                            continue
                        basis = (
                            f"frame:{self.frame_revision}",
                            *evidence_ids,
                            situated.binding_id,
                        )
                        probe = bridge.OptionProposal.create(
                            schema_id=schema_id,
                            action_id=action,
                            mode="probe",
                            potential_before=before,
                            predicted_after=predicted,
                            basis_ids=basis,
                            proposer=self.proposer,
                            attention=situated.attention,
                            lineage_id=lineage_id,
                            effect_variable=variable,
                        )
                        proposal = (
                            replace(probe, mode="control")
                            if probe.candidate_id in control_candidate_ids
                            else probe
                        )
                        proposals[proposal.candidate_id] = proposal
                        self.evaluators[proposal.candidate_id] = EvaluatorState(
                            proposal.candidate_id,
                            schema_id,
                            lineage_id,
                            variable,
                            situated.binding_id,
                            tuple(sorted(binding.items())),
                            before,
                            predicted,
                            tuple(sorted(set(basis))),
                            self.frame_revision,
                        )
        return tuple(
            sorted(
                proposals.values(),
                key=lambda item: (
                    item.predicted_after - item.potential_before,
                    -item.attention,
                    item.candidate_id,
                ),
            )
        )

    def observe_option_transition(
        self,
        *,
        opaque_action: int,
        after: Sequence[Sequence[int]],
        transition_id: str,
        executed_candidate_id: str | None = None,
        direct: bool = True,
    ) -> bridge.EnvironmentOutcome | None:
        if not transition_id:
            raise OnlineOptionError("transition requires a stable evidence ID")
        after_grid = _fixed_lattice(after,self.lattice_factor)
        after_scene = synthesis.perceive(after_grid,coarsen=False)
        outcome = None
        evaluator = self.evaluators.get(executed_candidate_id or "")
        if evaluator is not None:
            candidate = self.candidates[evaluator.schema_id]
            source_binding = dict(evaluator.binding)
            correspondences = _correspond(self.current_scene, after_scene, source_binding)
            values = set()
            for binding, _deltas in correspondences:
                situated = replace(
                    candidate,
                    binding=binding,
                    binding_id=_binding_id(candidate.candidate_id, binding),
                )
                try:
                    values.add(dsl.evaluate(situated, after_grid))
                except synthesis.SynthesisError:
                    pass
            observed_after = next(iter(values)) if len(values) == 1 else None
            outcome = bridge.EnvironmentOutcome(
                evaluator.option_id,
                transition_id,
                evaluator.potential_before,
                observed_after,
                bool(direct and observed_after is not None),
            )

        updated_lineages: dict[tuple[str,str], tuple[dict[str, str], ...]] = {}
        for (schema_id,lineage_id), alternatives in self.lineages.items():
            next_rows: dict[tuple[tuple[str, str], ...], dict[str, str]] = {}
            delta_rows: dict[str, set[tuple[int, int]]] = defaultdict(set)
            for binding in alternatives:
                for new_binding, deltas in _correspond(
                    self.current_scene, after_scene, binding
                ):
                    key = tuple(sorted(new_binding.items()))
                    next_rows[key] = new_binding
                    for variable, delta in deltas.items():
                        delta_rows[variable].add(delta)
            updated_lineages[(schema_id,lineage_id)] = tuple(
                next_rows[key] for key in sorted(next_rows)
            )
            if direct:
                for variable, deltas in delta_rows.items():
                    if len(deltas) == 1:
                        delta = next(iter(deltas))
                        self.effects.append(
                            EffectObservation(
                                schema_id,
                                lineage_id,
                                variable,
                                int(opaque_action),
                                delta,
                                transition_id,
                            )
                        )
        self.lineages = updated_lineages
        self.current_grid = after_grid
        self.current_scene = after_scene
        self.frame_revision += 1
        self.recent_transition_ids.append(transition_id)
        return outcome

    def grounding_state(self) -> tuple[GroundingState, ...]:
        return tuple(
            GroundingState(
                schema_id,
                lineage_id,
                tuple(tuple(sorted(binding.items())) for binding in alternatives),
                "unique" if len(alternatives) == 1 else "ambiguous" if alternatives else "unbound",
            )
            for (schema_id,lineage_id), alternatives in sorted(self.lineages.items())
        )

    def evaluator_state(self, option_id: str) -> EvaluatorState | None:
        return self.evaluators.get(option_id)

    def workspace_document(self) -> dict[str, Any]:
        models = self._usable_effects()
        return {
            "protocol": "online-compositional-options-v0",
            "authority": "direct-environment-transitions-only",
            "frame_revision": self.frame_revision,
            "groundings": [
                {
                    "schema_id": row.schema_id,
                    "lineage_id": row.lineage_id,
                    "status": row.correspondence_status,
                    "alternative_count": len(row.alternatives),
                }
                for row in self.grounding_state()
            ],
            "effect_models": [
                {
                    "schema_id": key[0],
                    "lineage_id": key[1],
                    "variable": key[2],
                    "intervention_ref": "iv:" + synthesis.stable_hash({"opaque": key[3]})[:16],
                    "delta": list(value[0]),
                    "evidence_ids": list(value[1]),
                }
                for key, value in sorted(models.items())
            ],
            "recent_transition_ids": self.recent_transition_ids[-16:],
        }


__all__ = [
    "EffectObservation",
    "EvaluatorState",
    "GroundingState",
    "OnlineCompositionalOptionInducer",
    "OnlineOptionError",
]
