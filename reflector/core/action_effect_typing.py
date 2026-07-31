"""Bounded prospective typing of positively observed action effects.

Action types are induced from rendered transitions without game identity,
fixed colors, absolute coordinates, or an assumed API action vocabulary.
No-op is retained only as contextual inapplicability; it never licenses a
type by complement.  A positive effect kind gains authority only after a
later structurally distinct source confirms the preregistered kind.
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field

from .action_translation_algebra import (
    ActionIdentity,
    TranslationBounds,
    infer_dominant_translation,
    structural_source_signature,
)

type Frame = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]
type Shape = tuple[Point, ...]

HARD_MAX_EFFECTS_PER_ACTION = 16
HARD_MAX_ACTIONS = 256
HARD_MAX_SOURCE_SIGNATURES = 512


@dataclass(frozen=True, slots=True)
class EffectTypingBounds:
    translation: TranslationBounds = field(default_factory=TranslationBounds)
    max_actions: int = 64
    max_effects_per_action: int = 8
    max_source_signatures: int = 128
    min_prospective_confirmations: int = 1

    def __post_init__(self) -> None:
        limits = (
            ("max_actions", self.max_actions, HARD_MAX_ACTIONS),
            (
                "max_effects_per_action",
                self.max_effects_per_action,
                HARD_MAX_EFFECTS_PER_ACTION,
            ),
            (
                "max_source_signatures",
                self.max_source_signatures,
                HARD_MAX_SOURCE_SIGNATURES,
            ),
            (
                "min_prospective_confirmations",
                self.min_prospective_confirmations,
                HARD_MAX_SOURCE_SIGNATURES,
            ),
        )
        for name, value, hard_limit in limits:
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or not 1 <= value <= hard_limit
            ):
                raise ValueError(f"{name} must be in [1, {hard_limit}]")


@dataclass(frozen=True, slots=True)
class ActionEffectObservation:
    kind: str
    source_signature: str | None
    frame_changed: bool
    cap_failure: str | None = None


@dataclass(frozen=True, slots=True)
class ActionEffectType:
    action: ActionIdentity
    kind: str
    proposal_sequence: int
    prospective_confirmations: int
    distinct_source_states: int


@dataclass(frozen=True, slots=True)
class ActionEffectUpdate:
    action: ActionIdentity
    kind: str
    diagnostic: str
    predicted_kind: str | None
    authority: ActionEffectType | None
    cap_failure: str | None = None


@dataclass(slots=True)
class _EffectHypothesis:
    proposal_sequence: int
    source_signatures: set[str] = field(default_factory=set)
    prospective_confirmations: int = 0


@dataclass(slots=True)
class ProspectiveActionEffectTyper:
    """Finite positive version space for context-conditioned action types."""

    bounds: EffectTypingBounds = field(default_factory=EffectTypingBounds)
    hypotheses: dict[
        ActionIdentity,
        dict[str, _EffectHypothesis],
    ] = field(default_factory=dict)
    observations: int = 0
    positive_observations: int = 0
    predictions: int = 0
    confirmations: int = 0
    contextual_noops: int = 0
    cap_failure: str | None = None

    def reset_episode(self) -> None:
        self.hypotheses.clear()
        self.observations = 0
        self.positive_observations = 0
        self.predictions = 0
        self.confirmations = 0
        self.contextual_noops = 0
        self.cap_failure = None

    def observe(
        self,
        *,
        sequence: int,
        action: ActionIdentity,
        before: Frame,
        after: Frame,
    ) -> ActionEffectUpdate:
        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 0
        ):
            raise ValueError("sequence must be a non-negative integer")
        self.observations += 1
        if self.cap_failure is not None:
            return ActionEffectUpdate(
                action,
                "unrepresented",
                f"fail-closed:{self.cap_failure}",
                None,
                None,
                self.cap_failure,
            )
        if (
            action not in self.hypotheses
            and len(self.hypotheses) >= self.bounds.max_actions
        ):
            self.cap_failure = "action-cap-exceeded"
            return ActionEffectUpdate(
                action,
                "unrepresented",
                "fail-closed:action-cap-exceeded",
                None,
                None,
                self.cap_failure,
            )
        observation = infer_action_effect(
            before,
            after,
            bounds=self.bounds,
        )
        if observation.cap_failure is not None:
            self.cap_failure = observation.cap_failure
            return ActionEffectUpdate(
                action,
                observation.kind,
                f"fail-closed:{observation.cap_failure}",
                None,
                None,
                observation.cap_failure,
            )
        if observation.kind == "render-noop":
            self.contextual_noops += 1
            return ActionEffectUpdate(
                action,
                observation.kind,
                "contextual-noop-no-positive-type",
                None,
                None,
            )

        self.positive_observations += 1
        action_hypotheses = self.hypotheses.setdefault(action, {})
        hypothesis = action_hypotheses.get(observation.kind)
        source = observation.source_signature
        if hypothesis is None:
            if len(action_hypotheses) >= self.bounds.max_effects_per_action:
                self.cap_failure = "effect-kind-cap-exceeded"
                return ActionEffectUpdate(
                    action,
                    observation.kind,
                    "fail-closed:effect-kind-cap-exceeded",
                    None,
                    None,
                    self.cap_failure,
                )
            action_hypotheses[observation.kind] = _EffectHypothesis(
                proposal_sequence=sequence,
                source_signatures={source} if source is not None else set(),
            )
            return ActionEffectUpdate(
                action,
                observation.kind,
                "proposed-positive-effect-type",
                None,
                None,
            )

        predicted = (
            observation.kind
            if source is not None and source not in hypothesis.source_signatures
            else None
        )
        if predicted is not None:
            self.predictions += 1
        confirmed = False
        if source is not None and source not in hypothesis.source_signatures:
            if len(hypothesis.source_signatures) >= self.bounds.max_source_signatures:
                self.cap_failure = "source-signature-cap-exceeded"
                return ActionEffectUpdate(
                    action,
                    observation.kind,
                    "fail-closed:source-signature-cap-exceeded",
                    predicted,
                    None,
                    self.cap_failure,
                )
            hypothesis.source_signatures.add(source)
            if predicted is not None:
                hypothesis.prospective_confirmations += 1
                self.confirmations += 1
                confirmed = True
        authority = self._authority(action, observation.kind, hypothesis)
        return ActionEffectUpdate(
            action,
            observation.kind,
            (
                "prospectively-confirmed-positive-effect-type"
                if confirmed
                else "authoritative-positive-effect-type-retained"
                if authority is not None
                else "repeated-positive-effect-source"
            ),
            predicted,
            authority,
        )

    def authoritative_types(self) -> tuple[ActionEffectType, ...]:
        return tuple(
            effect_type
            for action, kinds in sorted(self.hypotheses.items())
            for kind, hypothesis in sorted(kinds.items())
            for effect_type in (self._authority(action, kind, hypothesis),)
            if effect_type is not None
        )

    def _authority(
        self,
        action: ActionIdentity,
        kind: str,
        hypothesis: _EffectHypothesis,
    ) -> ActionEffectType | None:
        if (
            hypothesis.prospective_confirmations
            < self.bounds.min_prospective_confirmations
            or len(hypothesis.source_signatures) < 2
        ):
            return None
        return ActionEffectType(
            action=action,
            kind=kind,
            proposal_sequence=hypothesis.proposal_sequence,
            prospective_confirmations=hypothesis.prospective_confirmations,
            distinct_source_states=len(hypothesis.source_signatures),
        )


@dataclass(frozen=True, slots=True)
class _FrameProfile:
    component_count: int
    forms: tuple[tuple[Shape, int], ...]
    relative_layout: str


def infer_action_effect(
    before: Frame,
    after: Frame,
    *,
    bounds: EffectTypingBounds | None = None,
) -> ActionEffectObservation:
    """Classify one positive rendered effect without negative complements."""

    active = bounds if bounds is not None else EffectTypingBounds()
    source = structural_source_signature(
        before,
        bounds=active.translation,
    )
    translation = infer_dominant_translation(
        before,
        after,
        bounds=active.translation,
    )
    if translation.cap_failure is not None:
        return ActionEffectObservation(
            "unrepresented",
            source,
            True,
            translation.cap_failure,
        )
    if before == after:
        return ActionEffectObservation("render-noop", source, False)
    if translation.displacement is not None:
        return ActionEffectObservation("relative-translation", source, True)
    old, old_failure = _frame_profile(before, active.translation)
    new, new_failure = _frame_profile(after, active.translation)
    failure = old_failure or new_failure
    if failure is not None or old is None or new is None:
        return ActionEffectObservation(
            "unrepresented",
            source,
            True,
            failure or "profile-unrepresented",
        )
    if new.component_count > old.component_count:
        kind = "component-birth"
    elif new.component_count < old.component_count:
        kind = "component-death"
    elif new.forms != old.forms:
        kind = "component-form-change"
    elif new.relative_layout != old.relative_layout:
        kind = "relative-layout-change"
    else:
        kind = "residual-render-change"
    return ActionEffectObservation(kind, source, True)


def _frame_profile(
    frame: Frame,
    bounds: TranslationBounds,
) -> tuple[_FrameProfile | None, str | None]:
    if (
        not frame
        or not frame[0]
        or any(len(row) != len(frame[0]) for row in frame)
    ):
        return None, "malformed-frame"
    if len(frame) * len(frame[0]) > bounds.max_frame_cells:
        return None, "frame-cell-cap-exceeded"
    background = max(
        Counter(value for row in frame for value in row).items(),
        key=lambda item: (item[1], -item[0]),
    )[0]
    seen: set[Point] = set()
    forms: Counter[Shape] = Counter()
    anchors: list[tuple[Shape, Point]] = []
    for y, row in enumerate(frame):
        for x, color in enumerate(row):
            if color == background or (x, y) in seen:
                continue
            queue = deque(((x, y),))
            seen.add((x, y))
            points: list[Point] = []
            while queue:
                px, py = queue.popleft()
                points.append((px, py))
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    neighbor = px + dx, py + dy
                    if (
                        0 <= neighbor[0] < len(row)
                        and 0 <= neighbor[1] < len(frame)
                        and neighbor not in seen
                        and frame[neighbor[1]][neighbor[0]] == color
                    ):
                        seen.add(neighbor)
                        queue.append(neighbor)
            if len(points) > bounds.max_component_cells:
                continue
            min_x = min(px for px, _py in points)
            min_y = min(py for _px, py in points)
            shape = tuple(sorted((px - min_x, py - min_y) for px, py in points))
            forms[shape] += 1
            anchors.append((shape, (min_x, min_y)))
            if len(anchors) > bounds.max_components:
                return None, "component-cap-exceeded"
    if anchors:
        min_x = min(anchor[0] for _shape, anchor in anchors)
        min_y = min(anchor[1] for _shape, anchor in anchors)
    else:
        min_x = min_y = 0
    relative = repr(
        tuple(
            sorted(
                (
                    shape,
                    anchor[0] - min_x,
                    anchor[1] - min_y,
                )
                for shape, anchor in anchors
            )
        )
    )
    return (
        _FrameProfile(
            component_count=len(anchors),
            forms=tuple(sorted(forms.items())),
            relative_layout=relative,
        ),
        None,
    )
