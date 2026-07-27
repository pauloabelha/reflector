"""Evidence-calibrated causal/temporal hypotheses and experiments."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any

from .schemas import SchemaStore
from .symbolic import Transition


@dataclass(frozen=True, slots=True)
class CausalHypothesis:
    hypothesis_id: str
    action_id: int
    effect: str
    support: int
    trials: int
    control_support: int
    control_trials: int
    strength: float
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "action_id": self.action_id,
            "effect": self.effect,
            "support": self.support,
            "trials": self.trials,
            "control_support": self.control_support,
            "control_trials": self.control_trials,
            "strength": self.strength,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class TemporalHypothesis:
    hypothesis_id: str
    antecedent: str
    consequent: str
    support: int
    opportunities: int

    @property
    def confidence(self) -> float:
        return (self.support + 1) / (self.opportunities + 2)

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "antecedent": self.antecedent,
            "consequent": self.consequent,
            "support": self.support,
            "opportunities": self.opportunities,
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class Experiment:
    action_id: int
    question: str
    expected_information_gain: float
    estimated_risk: float

    @property
    def score(self) -> float:
        return self.expected_information_gain - self.estimated_risk

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_id": self.action_id,
            "question": self.question,
            "expected_information_gain": self.expected_information_gain,
            "estimated_risk": self.estimated_risk,
            "score": self.score,
        }


@dataclass(slots=True)
class HypothesisStore:
    """Maintain causal controls and one-step temporal regularities."""

    causal: dict[str, CausalHypothesis] = field(default_factory=dict)
    temporal: dict[str, TemporalHypothesis] = field(default_factory=dict)
    _previous_effects: tuple[str, ...] = ()
    _temporal_counts: dict[tuple[str, str], int] = field(default_factory=dict)
    _antecedent_opportunities: dict[str, int] = field(default_factory=dict)

    def observe(
        self, transition: Transition, schemas: SchemaStore
    ) -> tuple[str, ...]:
        before = set(self.causal) | set(self.temporal)
        effects = tuple(
            sorted({event.kind for event in transition.result})
        )
        self._rebuild_causal(schemas)
        for antecedent in self._previous_effects:
            self._antecedent_opportunities[antecedent] = (
                self._antecedent_opportunities.get(antecedent, 0) + 1
            )
            for consequent in effects:
                pair = (antecedent, consequent)
                self._temporal_counts[pair] = self._temporal_counts.get(pair, 0) + 1
        self._previous_effects = effects
        self._rebuild_temporal()
        return tuple(sorted((set(self.causal) | set(self.temporal)) - before))

    def _rebuild_causal(self, schemas: SchemaStore) -> None:
        actions = tuple(sorted(schemas.action_trials))
        all_effects = {
            effect
            for action in actions
            for effect in schemas.event_kinds(action)
        }
        for action in actions:
            trials = schemas.action_trials[action]
            for effect in sorted(all_effects):
                support = round(schemas.event_probability(action, effect) * trials)
                controls = tuple(other for other in actions if other != action)
                control_trials = sum(schemas.action_trials[other] for other in controls)
                control_support = sum(
                    round(
                        schemas.event_probability(other, effect)
                        * schemas.action_trials[other]
                    )
                    for other in controls
                )
                action_rate = support / trials
                control_rate = (
                    control_support / control_trials if control_trials else 0.0
                )
                strength = action_rate - control_rate
                evidence = trials + control_trials
                confidence = abs(strength) * evidence / (evidence + 2)
                raw = f"action:{action}|effect:{effect}"
                hypothesis_id = (
                    "h-causal-" + hashlib.sha256(raw.encode()).hexdigest()[:10]
                )
                self.causal[hypothesis_id] = CausalHypothesis(
                    hypothesis_id=hypothesis_id,
                    action_id=action,
                    effect=effect,
                    support=support,
                    trials=trials,
                    control_support=control_support,
                    control_trials=control_trials,
                    strength=strength,
                    confidence=confidence,
                )

    def _rebuild_temporal(self) -> None:
        for (antecedent, consequent), support in sorted(
            self._temporal_counts.items()
        ):
            raw = f"{antecedent}->{consequent}"
            hypothesis_id = (
                "h-temporal-" + hashlib.sha256(raw.encode()).hexdigest()[:10]
            )
            self.temporal[hypothesis_id] = TemporalHypothesis(
                hypothesis_id=hypothesis_id,
                antecedent=antecedent,
                consequent=consequent,
                support=support,
                opportunities=self._antecedent_opportunities[antecedent],
            )

    def experiments(
        self, legal_actions: tuple[int, ...], schemas: SchemaStore
    ) -> tuple[Experiment, ...]:
        output: list[Experiment] = []
        for action in legal_actions:
            relevant = [
                hypothesis
                for hypothesis in self.causal.values()
                if hypothesis.action_id == action and hypothesis.strength > 0
            ]
            confidence = max(
                (hypothesis.confidence for hypothesis in relevant), default=0.0
            )
            trials = schemas.action_trials.get(action, 0)
            information = (1.0 - confidence) / math.sqrt(trials + 1)
            risk = schemas.event_text_probability(action, "GAME_OVER")
            question = (
                f"which-effect(action={action})"
                if not relevant
                else f"test({min(relevant, key=lambda item: item.confidence).hypothesis_id})"
            )
            output.append(Experiment(action, question, information, risk))
        return tuple(
            sorted(output, key=lambda item: (-item.score, item.action_id))
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "causal": [
                item.to_dict()
                for item in sorted(
                    self.causal.values(), key=lambda value: value.hypothesis_id
                )
            ],
            "temporal": [
                item.to_dict()
                for item in sorted(
                    self.temporal.values(), key=lambda value: value.hypothesis_id
                )
            ],
        }
