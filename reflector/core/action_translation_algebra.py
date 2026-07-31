"""Prospective discovery of bounded action-conditioned translation laws.

The retained law contains only an immutable action identity and a relative
displacement.  Game identity, colors, absolute coordinates, frame hashes, and
routes are deliberately absent.  Rendered colors are used only as an
episode-local correspondence constraint while comparing two adjacent frames.

One observation may propose a law but can never authorize it.  A later
structurally distinct source state must confirm the preregistered displacement.
Ambiguous component motion abstains, contextual no-ops remain collision
evidence, and a contradictory nonzero displacement quarantines the action.
"""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field

type Frame = tuple[tuple[int, ...], ...]
type Point = tuple[int, int]
type Shape = tuple[Point, ...]
type ActionAtom = int | str

HARD_MAX_FRAME_CELLS = 16_384
HARD_MAX_COMPONENTS = 512
HARD_MAX_COMPONENT_CELLS = 2_048
HARD_MAX_ACTIONS = 256
HARD_MAX_SOURCE_SIGNATURES = 512
HARD_MAX_DISPLACEMENT = 1_024


@dataclass(frozen=True, order=True, slots=True)
class ActionIdentity:
    """Complete intervention identity, including sorted structured payload."""

    action_id: int
    payload: tuple[tuple[str, ActionAtom], ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.action_id, bool) or not isinstance(self.action_id, int):
            raise ValueError("action_id must be an integer")
        if tuple(sorted(self.payload)) != self.payload:
            raise ValueError("action payload must be sorted")
        if len({name for name, _value in self.payload}) != len(self.payload):
            raise ValueError("action payload names must be unique")


@dataclass(frozen=True, slots=True)
class TranslationBounds:
    max_frame_cells: int = 4_096
    max_components: int = 128
    max_component_cells: int = 512
    max_actions: int = 64
    max_source_signatures: int = 128
    max_displacement: int = 64
    min_prospective_confirmations: int = 1

    def __post_init__(self) -> None:
        limits = (
            ("max_frame_cells", self.max_frame_cells, HARD_MAX_FRAME_CELLS),
            ("max_components", self.max_components, HARD_MAX_COMPONENTS),
            (
                "max_component_cells",
                self.max_component_cells,
                HARD_MAX_COMPONENT_CELLS,
            ),
            ("max_actions", self.max_actions, HARD_MAX_ACTIONS),
            (
                "max_source_signatures",
                self.max_source_signatures,
                HARD_MAX_SOURCE_SIGNATURES,
            ),
            ("max_displacement", self.max_displacement, HARD_MAX_DISPLACEMENT),
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
class TranslationObservation:
    displacement: Point | None
    source_signature: str | None
    supporting_forms: int
    diagnostic: str
    omitted_oversized_components: int = 0
    cap_failure: str | None = None


@dataclass(frozen=True, slots=True)
class TranslationLaw:
    action: ActionIdentity
    displacement: Point
    proposal_sequence: int
    prospective_confirmations: int
    distinct_source_states: int


@dataclass(frozen=True, slots=True)
class TranslationUpdate:
    action: ActionIdentity
    diagnostic: str
    predicted_displacement: Point | None
    observed_displacement: Point | None
    authority: TranslationLaw | None
    quarantined: bool
    cap_failure: str | None = None


@dataclass(slots=True)
class _ActionHypothesis:
    displacement: Point
    proposal_sequence: int
    source_signatures: set[str] = field(default_factory=set)
    prospective_confirmations: int = 0
    predictions: int = 0
    contextual_noops: int = 0


@dataclass(slots=True)
class ActionTranslationAlgebra:
    """Episode-local finite version space for relative translation effects."""

    bounds: TranslationBounds = field(default_factory=TranslationBounds)
    hypotheses: dict[ActionIdentity, _ActionHypothesis] = field(
        default_factory=dict
    )
    quarantined_actions: set[ActionIdentity] = field(default_factory=set)
    observations: int = 0
    predictions: int = 0
    confirmations: int = 0
    conflicts: int = 0
    contextual_noops: int = 0
    cap_failure: str | None = None

    def reset_episode(self) -> None:
        self.hypotheses.clear()
        self.quarantined_actions.clear()
        self.observations = 0
        self.predictions = 0
        self.confirmations = 0
        self.conflicts = 0
        self.contextual_noops = 0
        self.cap_failure = None

    def observe(
        self,
        *,
        sequence: int,
        action: ActionIdentity,
        before: Frame,
        after: Frame,
    ) -> TranslationUpdate:
        """Register a fit or prospective result without same-row promotion."""

        if (
            isinstance(sequence, bool)
            or not isinstance(sequence, int)
            or sequence < 0
        ):
            raise ValueError("sequence must be a non-negative integer")
        self.observations += 1
        if self.cap_failure is not None:
            return TranslationUpdate(
                action,
                f"fail-closed:{self.cap_failure}",
                None,
                None,
                None,
                action in self.quarantined_actions,
                self.cap_failure,
            )
        if (
            action not in self.hypotheses
            and action not in self.quarantined_actions
            and len(self.hypotheses) + len(self.quarantined_actions)
            >= self.bounds.max_actions
        ):
            self.cap_failure = "action-cap-exceeded"
            return TranslationUpdate(
                action,
                "fail-closed:action-cap-exceeded",
                None,
                None,
                None,
                False,
                self.cap_failure,
            )
        observation = infer_dominant_translation(
            before,
            after,
            bounds=self.bounds,
        )
        if observation.cap_failure is not None:
            self.cap_failure = observation.cap_failure
            return TranslationUpdate(
                action,
                observation.diagnostic,
                None,
                None,
                None,
                action in self.quarantined_actions,
                observation.cap_failure,
            )
        if action in self.quarantined_actions:
            return TranslationUpdate(
                action,
                "abstain:quarantined-action",
                None,
                observation.displacement,
                None,
                True,
            )

        hypothesis = self.hypotheses.get(action)
        source = observation.source_signature
        if hypothesis is None:
            if observation.displacement is None or source is None:
                return TranslationUpdate(
                    action,
                    observation.diagnostic,
                    None,
                    observation.displacement,
                    None,
                    False,
                )
            self.hypotheses[action] = _ActionHypothesis(
                observation.displacement,
                sequence,
                {source},
            )
            return TranslationUpdate(
                action,
                "proposed-translation-law",
                None,
                observation.displacement,
                None,
                False,
            )

        predicted = (
            hypothesis.displacement
            if source is not None and source not in hypothesis.source_signatures
            else None
        )
        if predicted is not None:
            hypothesis.predictions += 1
            self.predictions += 1
        if observation.displacement is None:
            if predicted is not None:
                hypothesis.contextual_noops += 1
                self.contextual_noops += 1
            return TranslationUpdate(
                action,
                (
                    "contextual-noop-preserves-hypothesis"
                    if predicted is not None
                    else observation.diagnostic
                ),
                predicted,
                None,
                self._authority(action, hypothesis),
                False,
            )
        if observation.displacement != hypothesis.displacement:
            self.hypotheses.pop(action, None)
            self.quarantined_actions.add(action)
            self.conflicts += 1
            return TranslationUpdate(
                action,
                "conflicting-nonzero-translation",
                predicted,
                observation.displacement,
                None,
                True,
            )
        confirmed = False
        if source is not None and source not in hypothesis.source_signatures:
            if len(hypothesis.source_signatures) >= self.bounds.max_source_signatures:
                self.cap_failure = "source-signature-cap-exceeded"
                return TranslationUpdate(
                    action,
                    "fail-closed:source-signature-cap-exceeded",
                    predicted,
                    observation.displacement,
                    None,
                    False,
                    self.cap_failure,
                )
            hypothesis.source_signatures.add(source)
            if predicted is not None:
                hypothesis.prospective_confirmations += 1
                self.confirmations += 1
                confirmed = True
        authority = self._authority(action, hypothesis)
        return TranslationUpdate(
            action,
            (
                "prospectively-confirmed-translation-law"
                if confirmed
                else "authoritative-translation-law-retained"
                if authority is not None
                else "repeated-fit-source"
            ),
            predicted,
            observation.displacement,
            authority,
            False,
        )

    def authoritative_laws(self) -> tuple[TranslationLaw, ...]:
        return tuple(
            law
            for action, hypothesis in sorted(self.hypotheses.items())
            for law in (self._authority(action, hypothesis),)
            if law is not None
        )

    def inverse_pairs(
        self,
    ) -> tuple[tuple[ActionIdentity, ActionIdentity], ...]:
        laws = self.authoritative_laws()
        return tuple(
            (left.action, right.action)
            for index, left in enumerate(laws)
            for right in laws[index + 1 :]
            if left.displacement
            == (-right.displacement[0], -right.displacement[1])
        )

    def _authority(
        self,
        action: ActionIdentity,
        hypothesis: _ActionHypothesis,
    ) -> TranslationLaw | None:
        if (
            hypothesis.prospective_confirmations
            < self.bounds.min_prospective_confirmations
            or len(hypothesis.source_signatures) < 2
        ):
            return None
        return TranslationLaw(
            action,
            hypothesis.displacement,
            hypothesis.proposal_sequence,
            hypothesis.prospective_confirmations,
            len(hypothesis.source_signatures),
        )


@dataclass(frozen=True, slots=True)
class _Component:
    color: int
    shape: Shape
    anchor: Point

    @property
    def form(self) -> tuple[int, Shape]:
        return len(self.shape), self.shape


def infer_dominant_translation(
    before: Frame,
    after: Frame,
    *,
    bounds: TranslationBounds | None = None,
) -> TranslationObservation:
    """Infer one uniquely best nonzero displacement from persistent forms."""

    active = bounds if bounds is not None else TranslationBounds()
    old, old_failure, old_omitted = _components(before, active)
    new, new_failure, new_omitted = _components(after, active)
    omitted = old_omitted + new_omitted
    failure = old_failure or new_failure
    if failure is not None:
        return TranslationObservation(
            None,
            None,
            0,
            f"fail-closed:{failure}",
            omitted,
            failure,
        )
    source_signature = _source_signature(old)
    old_groups: dict[tuple[int, int, Shape], list[Point]] = defaultdict(list)
    new_groups: dict[tuple[int, int, Shape], list[Point]] = defaultdict(list)
    for item in old:
        old_groups[(item.color, *item.form)].append(item.anchor)
    for item in new:
        new_groups[(item.color, *item.form)].append(item.anchor)
    displacement_support: Counter[Point] = Counter()
    for group in old_groups.keys() & new_groups.keys():
        left = set(old_groups[group])
        right = set(new_groups[group])
        if len(left) != len(right):
            continue
        residual_left = tuple(sorted(left - right))
        residual_right = tuple(sorted(right - left))
        if len(residual_left) != 1 or len(residual_right) != 1:
            continue
        displacement = (
            residual_right[0][0] - residual_left[0][0],
            residual_right[0][1] - residual_left[0][1],
        )
        if displacement == (0, 0):
            continue
        if max(abs(displacement[0]), abs(displacement[1])) > active.max_displacement:
            continue
        displacement_support[displacement] += 1
    if not displacement_support:
        return TranslationObservation(
            None,
            source_signature,
            0,
            "no-unambiguous-nonzero-translation",
            omitted,
        )
    ranked = displacement_support.most_common()
    best, support = ranked[0]
    if len(ranked) > 1 and ranked[1][1] == support:
        return TranslationObservation(
            None,
            source_signature,
            support,
            "ambiguous-dominant-translation",
            omitted,
        )
    return TranslationObservation(
        best,
        source_signature,
        support,
        "unique-dominant-translation",
        omitted,
    )


def structural_source_signature(
    frame: Frame,
    *,
    bounds: TranslationBounds | None = None,
) -> str | None:
    """Return a color- and global-translation-invariant bounded scene key."""

    active = bounds if bounds is not None else TranslationBounds()
    components, failure, _omitted = _components(frame, active)
    if failure is not None:
        return None
    return _source_signature(components)


def _components(
    frame: Frame,
    bounds: TranslationBounds,
) -> tuple[tuple[_Component, ...], str | None, int]:
    if (
        not frame
        or not frame[0]
        or any(len(row) != len(frame[0]) for row in frame)
    ):
        return (), "malformed-frame", 0
    height = len(frame)
    width = len(frame[0])
    if height * width > bounds.max_frame_cells:
        return (), "frame-cell-cap-exceeded", 0
    background = max(
        Counter(value for row in frame for value in row).items(),
        key=lambda item: (item[1], -item[0]),
    )[0]
    seen: set[Point] = set()
    output: list[_Component] = []
    omitted_oversized = 0
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or frame[y][x] == background:
                continue
            color = frame[y][x]
            queue = deque(((x, y),))
            seen.add((x, y))
            points: list[Point] = []
            while queue:
                point = queue.popleft()
                points.append(point)
                px, py = point
                for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    neighbor = px + dx, py + dy
                    if (
                        0 <= neighbor[0] < width
                        and 0 <= neighbor[1] < height
                        and neighbor not in seen
                        and frame[neighbor[1]][neighbor[0]] == color
                    ):
                        seen.add(neighbor)
                        queue.append(neighbor)
            if len(points) > bounds.max_component_cells:
                omitted_oversized += 1
                continue
            min_x = min(px for px, _py in points)
            min_y = min(py for _px, py in points)
            shape = tuple(sorted((px - min_x, py - min_y) for px, py in points))
            output.append(_Component(color, shape, (min_x, min_y)))
            if len(output) > bounds.max_components:
                return (), "component-cap-exceeded", omitted_oversized
    return tuple(output), None, omitted_oversized


def _source_signature(components: tuple[_Component, ...]) -> str:
    """Describe relative form layout without colors or absolute translation."""

    if not components:
        canonical: tuple[tuple[object, ...], ...] = ()
    else:
        min_x = min(item.anchor[0] for item in components)
        min_y = min(item.anchor[1] for item in components)
        canonical = tuple(
            sorted(
                (
                    len(item.shape),
                    item.shape,
                    item.anchor[0] - min_x,
                    item.anchor[1] - min_y,
                )
                for item in components
            )
        )
    return hashlib.sha256(repr(canonical).encode()).hexdigest()
