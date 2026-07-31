"""Bounded prospective partial bisimulation over grounded action effects.

Raw rendered states are not merged by appearance.  Two states may act as
donor and recipient only after at least one shared grounded action role has a
deterministic matching outcome and no observed overlapping role conflicts.
An outcome for a donor-only role then becomes a prospective prediction for the
recipient.  Contradictions remain explicit partition-refinement evidence.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Hashable, Iterable
from dataclasses import dataclass, field

type Outcome = str
type Profile = dict[Hashable, set[Outcome]]

HARD_MAX_STATES = 2_048
HARD_MAX_ROLES_PER_STATE = 512
HARD_MAX_OUTCOMES_PER_ROLE = 16


@dataclass(frozen=True, slots=True)
class PartialBisimulationBounds:
    max_states: int = 512
    max_roles_per_state: int = 256
    max_outcomes_per_role: int = 4
    min_shared_roles: int = 1

    def __post_init__(self) -> None:
        limits = (
            ("max_states", self.max_states, HARD_MAX_STATES),
            (
                "max_roles_per_state",
                self.max_roles_per_state,
                HARD_MAX_ROLES_PER_STATE,
            ),
            (
                "max_outcomes_per_role",
                self.max_outcomes_per_role,
                HARD_MAX_OUTCOMES_PER_ROLE,
            ),
            ("min_shared_roles", self.min_shared_roles, HARD_MAX_ROLES_PER_STATE),
        )
        for name, value, hard_limit in limits:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= hard_limit
            ):
                raise ValueError(f"{name} must be in [1, {hard_limit}]")


@dataclass(frozen=True, slots=True)
class BisimulationPrediction:
    role: Hashable
    outcome: Outcome | None
    donor_states: int
    ambiguous: bool = False


@dataclass(frozen=True, slots=True)
class BisimulationUpdate:
    prediction: BisimulationPrediction | None
    confirmed: bool
    conflicted: bool
    diagnostic: str
    cap_failure: str | None = None


@dataclass(frozen=True, slots=True)
class CausalDiscrimination:
    role: Hashable
    outcome_counts: tuple[tuple[Outcome, int], ...]
    donor_states: int
    expected_elimination: float


@dataclass(slots=True)
class PartialBisimulation:
    """Episode-local compatible partial action/effect profiles."""

    bounds: PartialBisimulationBounds = field(
        default_factory=PartialBisimulationBounds
    )
    profiles: dict[str, Profile] = field(default_factory=dict)
    domains: dict[str, tuple[int, ...]] = field(default_factory=dict)
    observations: int = 0
    predictions: int = 0
    confirmations: int = 0
    conflicts: int = 0
    ambiguous_predictions: int = 0
    abstract_frontier_roles: int = 0
    discrimination_frontier_roles: int = 0
    outcome_counts: Counter[Outcome] = field(default_factory=Counter)
    level_predictions: int = 0
    level_confirmations: int = 0
    level_conflicts: int = 0
    level_outcome_counts: Counter[Outcome] = field(default_factory=Counter)
    cap_failure: str | None = None
    last_diagnostic: str = "exact-off"

    def reset_level(self) -> None:
        self.profiles.clear()
        self.domains.clear()
        self.level_predictions = 0
        self.level_confirmations = 0
        self.level_conflicts = 0
        self.level_outcome_counts.clear()
        self.cap_failure = None
        self.last_diagnostic = "level-reset"

    def observe(
        self,
        *,
        source: str,
        domain: tuple[int, ...],
        role: Hashable,
        outcome: Outcome,
    ) -> BisimulationUpdate:
        """Test a transferred prediction before adding the observed row."""

        self.observations += 1
        if self.cap_failure is not None:
            return self._update(
                None,
                False,
                False,
                f"fail-closed:{self.cap_failure}",
                self.cap_failure,
            )
        if source not in self.profiles:
            if len(self.profiles) >= self.bounds.max_states:
                self.cap_failure = "state-cap-exceeded"
                return self._update(
                    None,
                    False,
                    False,
                    "fail-closed:state-cap-exceeded",
                    self.cap_failure,
                )
            self.profiles[source] = {}
        profile = self.profiles[source]
        prediction = self.predict(
            source=source,
            domain=domain,
            role=role,
        )
        confirmed = False
        conflicted = False
        if prediction is not None:
            if prediction.ambiguous:
                self.ambiguous_predictions += 1
            elif prediction.outcome is not None:
                self.predictions += 1
                self.level_predictions += 1
                confirmed = prediction.outcome == outcome
                conflicted = not confirmed
                self.confirmations += int(confirmed)
                self.conflicts += int(conflicted)
                self.level_confirmations += int(confirmed)
                self.level_conflicts += int(conflicted)
        outcomes = profile.get(role)
        if outcomes is None:
            if len(profile) >= self.bounds.max_roles_per_state:
                self.cap_failure = "role-cap-exceeded"
                return self._update(
                    prediction,
                    confirmed,
                    conflicted,
                    "fail-closed:role-cap-exceeded",
                    self.cap_failure,
                )
            outcomes = set()
            profile[role] = outcomes
        if outcome not in outcomes:
            if len(outcomes) >= self.bounds.max_outcomes_per_role:
                self.cap_failure = "outcome-cap-exceeded"
                return self._update(
                    prediction,
                    confirmed,
                    conflicted,
                    "fail-closed:outcome-cap-exceeded",
                    self.cap_failure,
                )
            outcomes.add(outcome)
        self.domains[source] = domain
        self.outcome_counts[outcome] += 1
        self.level_outcome_counts[outcome] += 1
        if conflicted:
            diagnostic = "prediction-conflict-refines-partition"
        elif confirmed:
            diagnostic = "prospectively-confirmed-role-effect"
        elif prediction is not None and prediction.ambiguous:
            diagnostic = "ambiguous-donor-outcomes"
        else:
            diagnostic = "profile-observation"
        return self._update(
            prediction,
            confirmed,
            conflicted,
            diagnostic,
        )

    def predict(
        self,
        *,
        source: str,
        domain: tuple[int, ...],
        role: Hashable,
    ) -> BisimulationPrediction | None:
        """Transfer one donor-only role outcome through compatible profiles."""

        source_profile = self.profiles.get(source, {})
        if role in source_profile:
            return None
        donors = self._compatible_donors(source, domain)
        outcomes = {
            outcome
            for donor in donors
            if (outcome := self._deterministic(donor, role)) is not None
        }
        if not outcomes:
            return None
        if len(outcomes) > 1:
            return BisimulationPrediction(role, None, len(donors), True)
        return BisimulationPrediction(
            role,
            next(iter(outcomes)),
            len(donors),
        )

    def frontier_predictions(
        self,
        *,
        source: str,
        domain: tuple[int, ...],
        roles: Iterable[Hashable],
    ) -> tuple[BisimulationPrediction, ...]:
        """Return unique donor predictions for locally untried legal roles."""

        predictions = tuple(
            prediction
            for role in roles
            if (
                prediction := self.predict(
                    source=source,
                    domain=domain,
                    role=role,
                )
            )
            is not None
            and not prediction.ambiguous
            and prediction.outcome is not None
        )
        self.abstract_frontier_roles += len(predictions)
        return predictions

    def trusted_for_control(self, *, min_predictions: int = 8) -> bool:
        """Whether the current level has a flawless prospective trace gate."""

        return (
            self.cap_failure is None
            and self.level_predictions >= min_predictions
            and self.level_conflicts == 0
            and self.level_confirmations == self.level_predictions
        )

    def ready_for_discrimination(
        self,
        *,
        min_confirmations: int = 4,
    ) -> bool:
        """Whether the current quotient predicts well enough to query disagreement."""

        return (
            self.cap_failure is None
            and self.level_confirmations >= min_confirmations
            and self.level_confirmations * 4 >= self.level_predictions * 3
        )

    def discrimination_frontier(
        self,
        *,
        source: str,
        domain: tuple[int, ...],
        roles: Iterable[Hashable],
    ) -> tuple[CausalDiscrimination, ...]:
        """Return locally untried roles that distinguish compatible donors."""

        source_profile = self.profiles.get(source, {})
        donors = self._compatible_donors(source, domain)
        queries = []
        for role in roles:
            if role in source_profile:
                continue
            counts: Counter[Outcome] = Counter(
                outcome
                for donor in donors
                if (outcome := self._deterministic(donor, role)) is not None
            )
            if len(counts) <= 1:
                continue
            donor_states = sum(counts.values())
            expected_elimination = donor_states - sum(
                count * count for count in counts.values()
            ) / donor_states
            queries.append(
                CausalDiscrimination(
                    role=role,
                    outcome_counts=tuple(sorted(counts.items())),
                    donor_states=donor_states,
                    expected_elimination=expected_elimination,
                )
            )
        self.discrimination_frontier_roles += len(queries)
        return tuple(queries)

    def _compatible_donors(
        self,
        source: str,
        domain: tuple[int, ...],
    ) -> tuple[Profile, ...]:
        source_profile = self.profiles.get(source, {})
        return tuple(
            profile
            for state, profile in self.profiles.items()
            if state != source
            and self.domains.get(state) == domain
            and self.compatible(source_profile, profile)
        )

    def compatible(self, left: Profile, right: Profile) -> bool:
        shared = set(left) & set(right)
        if len(shared) < self.bounds.min_shared_roles:
            return False
        return all(
            len(left[role]) == 1
            and len(right[role]) == 1
            and left[role] == right[role]
            for role in shared
        )

    @staticmethod
    def _deterministic(profile: Profile, role: Hashable) -> Outcome | None:
        outcomes = profile.get(role)
        if outcomes is None or len(outcomes) != 1:
            return None
        return next(iter(outcomes))

    def _update(
        self,
        prediction: BisimulationPrediction | None,
        confirmed: bool,
        conflicted: bool,
        diagnostic: str,
        cap_failure: str | None = None,
    ) -> BisimulationUpdate:
        self.last_diagnostic = diagnostic
        return BisimulationUpdate(
            prediction,
            confirmed,
            conflicted,
            diagnostic,
            cap_failure,
        )
