"""Pure prospective-control primitives for a shared epistemic workspace.

The module deliberately knows nothing about any ARC game or action meaning.
It preserves relational grounding alternatives, projects every legal opaque
action through every live binding with a learned model, selects only genuine
discriminating probes, and classifies direct environmental outcomes.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
AMBIGUITY_PATH = HERE / "ambiguity.py"
SPEC = importlib.util.spec_from_file_location("shared_attention_v14_ambiguity", AMBIGUITY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load ambiguity compiler: {AMBIGUITY_PATH}")
AMBIGUITY = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AMBIGUITY
SPEC.loader.exec_module(AMBIGUITY)


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_id(prefix: str, value: object) -> str:
    digest = hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


@dataclass(frozen=True, slots=True)
class GroundingAlternative:
    candidate_id: str
    template_hash: str
    substitution: tuple[tuple[str, str], ...]
    effect_pair: tuple[str, str]


@dataclass(frozen=True, slots=True)
class AlternativeSet:
    template_hash: str
    alternatives: tuple[GroundingAlternative, ...]
    complete: bool
    observed_grounding_count: int
    enumeration_limit: int


def grounding_alternatives(
    template: Any,
    relation_state: Mapping[str, Any],
    *,
    enumeration_limit: int = 64,
) -> AlternativeSet:
    """Return every enumerated substitution without collapsing effect pairs.

    ``complete`` is false whenever the underlying join or either rendering was
    truncated.  A caller may retain those rows epistemically, but must not use
    them as if they were an exhaustive control population.
    """

    witness = AMBIGUITY.compile_ambiguity_witness(
        template,
        relation_state,
        max_candidates=enumeration_limit,
        max_effect_pairs=enumeration_limit,
        enumeration_limit=enumeration_limit,
    )
    effect_variables = tuple(str(item) for item in witness["effect_variables"])
    alternatives: list[GroundingAlternative] = []
    for raw in witness["candidate_substitutions"]:
        substitution = tuple(
            sorted((str(variable), str(entity)) for variable, entity in raw["substitution"])
        )
        by_variable = dict(substitution)
        if not all(variable in by_variable for variable in effect_variables):
            continue
        effect_pair = (by_variable[effect_variables[0]], by_variable[effect_variables[1]])
        identity = {
            "template_hash": str(witness["template_hash"]),
            "substitution": substitution,
            "effect_pair": effect_pair,
        }
        alternatives.append(
            GroundingAlternative(
                candidate_id=stable_id("ga", identity),
                template_hash=str(witness["template_hash"]),
                substitution=substitution,
                effect_pair=effect_pair,
            )
        )
    alternatives.sort(key=lambda item: item.candidate_id)
    complete = not any(
        bool(witness[key])
        for key in (
            "enumeration_truncated",
            "candidate_substitutions_truncated",
            "effect_pairs_truncated",
        )
    )
    return AlternativeSet(
        template_hash=str(witness["template_hash"]),
        alternatives=tuple(alternatives),
        complete=complete,
        observed_grounding_count=int(witness["grounding_count_observed"]),
        enumeration_limit=enumeration_limit,
    )


@dataclass(frozen=True, slots=True)
class ActionModel:
    action_id: int
    delta: tuple[int, int]
    support: int

    def __post_init__(self) -> None:
        if self.support < 1:
            raise ValueError("action-model support must be positive")


@dataclass(frozen=True, slots=True)
class LiveBinding:
    binding_id: str
    schema_object_id: str
    candidate_id: str
    operator: str
    effect_pair: tuple[str, str]
    relative2: tuple[int, int]
    action_models: tuple[ActionModel, ...] = ()
    confirmations: int = 0

    def __post_init__(self) -> None:
        if self.operator not in {"Decrease", "Increase"}:
            raise ValueError("binding operator must be Decrease or Increase")
        if self.confirmations < 0:
            raise ValueError("binding confirmations cannot be negative")
        action_ids = [item.action_id for item in self.action_models]
        if len(action_ids) != len(set(action_ids)):
            raise ValueError("a binding may have only one model per action")

    @classmethod
    def build(
        cls,
        *,
        schema_object_id: str,
        alternative: GroundingAlternative,
        operator: str,
        relative2: tuple[int, int],
        action_models: Sequence[ActionModel] = (),
        confirmations: int = 0,
    ) -> "LiveBinding":
        identity = {
            "schema_object_id": schema_object_id,
            "candidate_id": alternative.candidate_id,
            "effect_pair": alternative.effect_pair,
        }
        return cls(
            binding_id=stable_id("lb", identity),
            schema_object_id=schema_object_id,
            candidate_id=alternative.candidate_id,
            operator=operator,
            effect_pair=alternative.effect_pair,
            relative2=relative2,
            action_models=tuple(sorted(action_models, key=lambda item: item.action_id)),
            confirmations=confirmations,
        )

    @property
    def residual(self) -> int:
        return abs(self.relative2[0]) + abs(self.relative2[1])


@dataclass(frozen=True, slots=True)
class ProspectivePrediction:
    prediction_id: str
    binding_id: str
    candidate_id: str
    action_id: int
    basis_revision: int
    current_residual: int
    predicted_residual: int | None
    predicted_delta: tuple[int, int] | None
    model_support: int
    modeled: bool

    @property
    def outcome_signature(self) -> tuple[Any, ...] | None:
        if not self.modeled:
            return None
        return (self.predicted_delta, self.predicted_residual)


@dataclass(frozen=True, slots=True)
class ControlPlan:
    plan_id: str
    basis_revision: int
    observation_digest: str
    mode: str
    action_id: int
    fallback_action_id: int
    predictions: tuple[ProspectivePrediction, ...]
    selected_prediction_ids: tuple[str, ...]
    discrimination_pairs: int
    probe_basis: str | None


class ProspectiveController:
    def __init__(self, bindings: Sequence[LiveBinding]) -> None:
        self.bindings = tuple(sorted(bindings, key=lambda item: item.binding_id))
        ids = [item.binding_id for item in self.bindings]
        if len(ids) != len(set(ids)):
            raise ValueError("live binding ids must be unique")

    def prediction_matrix(
        self,
        legal_actions: Sequence[int],
        *,
        observation_digest: str,
        basis_revision: int,
    ) -> tuple[ProspectivePrediction, ...]:
        legal = tuple(sorted(set(int(item) for item in legal_actions)))
        if not legal:
            raise ValueError("at least one legal action is required")
        output: list[ProspectivePrediction] = []
        for binding in self.bindings:
            models = {item.action_id: item for item in binding.action_models}
            for action in legal:
                model = models.get(action)
                predicted = None
                if model is not None:
                    vector = (
                        binding.relative2[0] + model.delta[0],
                        binding.relative2[1] + model.delta[1],
                    )
                    predicted = abs(vector[0]) + abs(vector[1])
                identity = {
                    "binding_id": binding.binding_id,
                    "action_id": action,
                    "observation_digest": observation_digest,
                    "basis_revision": basis_revision,
                }
                output.append(
                    ProspectivePrediction(
                        prediction_id=stable_id("pp", identity),
                        binding_id=binding.binding_id,
                        candidate_id=binding.candidate_id,
                        action_id=action,
                        basis_revision=basis_revision,
                        current_residual=binding.residual,
                        predicted_residual=predicted,
                        predicted_delta=None if model is None else model.delta,
                        model_support=0 if model is None else model.support,
                        modeled=model is not None,
                    )
                )
        return tuple(output)

    def plan(
        self,
        legal_actions: Sequence[int],
        *,
        observation_digest: str,
        basis_revision: int,
        action_uses: Mapping[int, int] | None = None,
    ) -> ControlPlan:
        legal = tuple(sorted(set(int(item) for item in legal_actions)))
        if not legal:
            raise ValueError("at least one legal action is required")
        uses = {int(key): int(value) for key, value in (action_uses or {}).items()}
        fallback = min(legal, key=lambda action: (uses.get(action, 0), action))
        predictions = self.prediction_matrix(
            legal, observation_digest=observation_digest, basis_revision=basis_revision
        )
        bindings = {item.binding_id: item for item in self.bindings}
        improving: list[tuple[float, int, int, int, str]] = []
        for prediction in predictions:
            if prediction.predicted_residual is None:
                continue
            binding = bindings[prediction.binding_id]
            if binding.confirmations < 1:
                continue
            improvement = (
                prediction.current_residual - prediction.predicted_residual
                if binding.operator == "Decrease"
                else prediction.predicted_residual - prediction.current_residual
            )
            if improvement > 0:
                improving.append(
                    (
                        -(improvement / max(1, prediction.current_residual)),
                        -prediction.model_support,
                        uses.get(prediction.action_id, 0),
                        prediction.action_id,
                        prediction.prediction_id,
                    )
                )
        if improving:
            _gain, _support, _uses, action, prediction_id = min(improving)
            mode = "control"
            selected = (prediction_id,)
            disagreement = 0
            probe_basis = None
        else:
            confirmation_probes: list[tuple[int, int, int, int, str]] = []
            if len(self.bindings) == 1 and self.bindings[0].confirmations == 0:
                binding = self.bindings[0]
                for prediction in predictions:
                    if prediction.predicted_residual is None:
                        continue
                    preferred_gain = (
                        prediction.current_residual - prediction.predicted_residual
                        if binding.operator == "Decrease"
                        else prediction.predicted_residual - prediction.current_residual
                    )
                    confirmation_probes.append(
                        (
                            -preferred_gain,
                            -prediction.model_support,
                            uses.get(prediction.action_id, 0),
                            prediction.action_id,
                            prediction.prediction_id,
                        )
                    )
            if confirmation_probes:
                _gain, _support, _uses, action, prediction_id = min(confirmation_probes)
                mode = "probe"
                selected = (prediction_id,)
                disagreement = 0
                probe_basis = "single-binding-confirmation"
            else:
                probe_candidates: list[tuple[int, int, int, int, tuple[str, ...]]] = []
                for action in legal:
                    modeled = [
                        item for item in predictions if item.action_id == action and item.modeled
                    ]
                    disagreements = sum(
                        left.outcome_signature != right.outcome_signature
                        for index, left in enumerate(modeled)
                        for right in modeled[index + 1 :]
                    )
                    if disagreements <= 0:
                        continue
                    selected_ids = tuple(sorted(item.prediction_id for item in modeled))
                    probe_candidates.append(
                        (
                            -disagreements,
                            -min(item.model_support for item in modeled),
                            uses.get(action, 0),
                            action,
                            selected_ids,
                        )
                    )
                if probe_candidates:
                    negative_disagreement, _support, _uses, action, selected = min(probe_candidates)
                    mode = "probe"
                    disagreement = -negative_disagreement
                    probe_basis = "alternative-disagreement"
                else:
                    action = fallback
                    mode = "fallback"
                    selected = ()
                    disagreement = 0
                    probe_basis = None
        plan_identity = {
            "basis_revision": basis_revision,
            "observation_digest": observation_digest,
            "action_id": action,
            "mode": mode,
            "prediction_ids": [item.prediction_id for item in predictions],
            "selected_prediction_ids": selected,
            "probe_basis": probe_basis,
        }
        return ControlPlan(
            plan_id=stable_id("cp", plan_identity),
            basis_revision=basis_revision,
            observation_digest=observation_digest,
            mode=mode,
            action_id=action,
            fallback_action_id=fallback,
            predictions=predictions,
            selected_prediction_ids=selected,
            discrimination_pairs=disagreement,
            probe_basis=probe_basis,
        )


@dataclass(frozen=True, slots=True)
class ObservedConsequence:
    direct: bool
    delta: tuple[int, int] | None = None
    residual: int | None = None


@dataclass(frozen=True, slots=True)
class PredictionJudgment:
    prediction_id: str
    binding_id: str
    status: str
    reason: str
    predicted_delta: tuple[int, int] | None
    observed_delta: tuple[int, int] | None
    predicted_residual: int | None
    observed_residual: int | None


@dataclass(frozen=True, slots=True)
class Adjudication:
    plan_id: str
    basis_revision: int
    action_id: int
    judgments: tuple[PredictionJudgment, ...]

    @property
    def counts(self) -> dict[str, int]:
        output = {"supports": 0, "refutes": 0, "unresolved": 0}
        for item in self.judgments:
            output[item.status] += 1
        return output


def adjudicate(
    plan: ControlPlan,
    *,
    action_id: int,
    observed: Mapping[str, ObservedConsequence],
) -> Adjudication:
    """Compare direct reality with every alternative's chosen-action shadow."""

    if int(action_id) != plan.action_id:
        raise ValueError("executed action does not match prospective plan")
    judgments: list[PredictionJudgment] = []
    for prediction in plan.predictions:
        if prediction.action_id != action_id:
            continue
        consequence = observed.get(prediction.binding_id)
        if not prediction.modeled:
            status, reason = "unresolved", "no-prospective-model"
        elif consequence is None or not consequence.direct:
            status, reason = "unresolved", "outcome-not-directly-observable"
        elif (
            consequence.delta == prediction.predicted_delta
            and consequence.residual == prediction.predicted_residual
        ):
            status, reason = "supports", "direct-outcome-matched"
        else:
            status, reason = "refutes", "direct-outcome-contradicted"
        judgments.append(
            PredictionJudgment(
                prediction_id=prediction.prediction_id,
                binding_id=prediction.binding_id,
                status=status,
                reason=reason,
                predicted_delta=prediction.predicted_delta,
                observed_delta=None if consequence is None else consequence.delta,
                predicted_residual=prediction.predicted_residual,
                observed_residual=None if consequence is None else consequence.residual,
            )
        )
    return Adjudication(
        plan_id=plan.plan_id,
        basis_revision=plan.basis_revision,
        action_id=action_id,
        judgments=tuple(judgments),
    )


def revise_bindings(
    bindings: Sequence[LiveBinding], adjudication: Adjudication
) -> tuple[LiveBinding, ...]:
    """Return an immutable binding revision after direct matched predictions."""

    confirmed_ids = {
        item.binding_id for item in adjudication.judgments if item.status == "supports"
    }
    return tuple(
        replace(item, confirmations=item.confirmations + 1)
        if item.binding_id in confirmed_ids
        else item
        for item in bindings
    )


def fallback_plan(
    source: ControlPlan, *, action_id: int, reason: str
) -> ControlPlan:
    """Conservatively demote a budget-blocked plan without losing its matrix."""

    identity = {
        "source_plan_id": source.plan_id,
        "action_id": int(action_id),
        "reason": str(reason),
    }
    return ControlPlan(
        plan_id=stable_id("cp", identity),
        basis_revision=source.basis_revision,
        observation_digest=source.observation_digest,
        mode="fallback",
        action_id=int(action_id),
        fallback_action_id=int(action_id),
        predictions=source.predictions,
        selected_prediction_ids=(),
        discrimination_pairs=0,
        probe_basis=str(reason),
    )


def document(value: object) -> dict[str, Any]:
    """Canonical test/graph adapter representation for any public dataclass."""

    return asdict(value)
