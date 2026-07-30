"""Bounded symbolic inference and planning for projected token permutations.

The runtime-facing types in this module contain only episode-grounded perceptual
roles.  They do not name games, colors, actions, or absolute solution paths.
An effect is admitted only when a before/after observation exactly supports a
successor permutation over the declared conserved token-centroid domain.
"""

from __future__ import annotations

import hashlib
import itertools
import math
from collections import Counter, deque
from dataclasses import dataclass, replace
from typing import Literal, Self

type Point = tuple[int, int]
type Frame = tuple[tuple[int, ...], ...]
type ProjectedState = tuple[tuple[int, ...], ...]
type Axis = Literal["horizontal", "vertical", "path"]
type FactorCoordinate = tuple[int, int]
type FactoredEffectKind = Literal["local", "interface"]
type ControllerAxisRelation = Literal["parallel", "perpendicular"]


@dataclass(frozen=True, slots=True)
class PermutationBounds:
    """Deterministic inference and search limits."""

    min_segment_length: int = 3
    min_segment_count: int = 2
    max_segments: int = 6
    max_slots: int = 64
    max_cycle_orderings: int = 256
    max_generators: int = 8
    max_projected_states: int = 4096
    max_plan_depth: int = 32
    min_factor_directions: int = 4
    min_factor_ranks: int = 2
    min_factor_modules: int = 2
    max_factor_directions: int = 16
    max_factor_ranks: int = 8
    max_factor_modules: int = 8
    max_factored_slots: int = 256
    max_factorizations: int = 2
    max_factorization_search_states: int = 4096
    max_factored_states: int = 512


@dataclass(frozen=True, slots=True)
class MarkerTarget:
    """A percept-relative request to place one token color at one marker."""

    point: Point
    color: int


@dataclass(frozen=True, slots=True)
class PolarProductModule:
    """One empty-hub module with a cyclic direction factor and radial ranks."""

    hub: Point
    pitch: int
    rays: tuple[Point, ...]
    ranks: int
    points: tuple[tuple[Point, ...], ...]

    @property
    def factor_shape(self) -> tuple[int, int]:
        return len(self.rays), self.ranks

    @property
    def slots(self) -> tuple[Point, ...]:
        return tuple(point for ray in self.points for point in ray)

    def point(self, coordinate: FactorCoordinate) -> Point:
        direction, rank = coordinate
        return self.points[direction % len(self.rays)][rank % self.ranks]

    def coordinate(self, point: Point) -> FactorCoordinate:
        for direction, ray in enumerate(self.points):
            try:
                return direction, ray.index(point)
            except ValueError:
                continue
        raise KeyError(point)


@dataclass(frozen=True, slots=True)
class FactoredInterface:
    """A structurally adjacent anchor/outlet edge for one repeated module."""

    module_index: int
    anchor: Point
    outlet: Point


@dataclass(frozen=True, slots=True)
class FactoredOrbitDomain:
    """A unique exact cover by repeated polar-product modules and interfaces."""

    modules: tuple[PolarProductModule, ...]
    interfaces: tuple[FactoredInterface, ...]

    @property
    def factor_shape(self) -> tuple[int, int]:
        return self.modules[0].factor_shape

    @property
    def module_slots(self) -> tuple[Point, ...]:
        return tuple(
            sorted(point for module in self.modules for point in module.slots)
        )

    @property
    def anchor_slots(self) -> tuple[Point, ...]:
        return tuple(sorted(item.anchor for item in self.interfaces))

    @property
    def all_slots(self) -> tuple[Point, ...]:
        return tuple(sorted((*self.module_slots, *self.anchor_slots)))


@dataclass(frozen=True, slots=True)
class FactoredOrbitInference:
    """A factored-domain result with deterministic hypothesis-search evidence."""

    domain: FactoredOrbitDomain | None
    explored_states: int
    search_exhausted: bool


@dataclass(frozen=True, slots=True)
class _ExactCoverSearch:
    covers: tuple[tuple[PolarProductModule, ...], ...]
    explored_states: int
    search_exhausted: bool


@dataclass(frozen=True, slots=True)
class PolarControllerGrounding:
    """Coordinate-free module membership and intrinsic-axis relation."""

    module_index: int
    relation: ControllerAxisRelation


@dataclass(frozen=True, slots=True)
class FactoredOrbitGenerator:
    """A content-free factor translation or product of interface swaps."""

    effect_id: str
    kind: FactoredEffectKind
    factor_shape: tuple[int, int]
    delta: FactorCoordinate
    interface_count: int
    controllers: tuple[Point, ...]
    support: int

    @classmethod
    def create_local(
        cls,
        *,
        factor_shape: tuple[int, int],
        delta: FactorCoordinate,
        controller: Point,
    ) -> Self:
        directions, ranks = factor_shape
        if directions < 1 or ranks < 1:
            raise ValueError("factor dimensions must be positive")
        normalized = (delta[0] % directions, delta[1] % ranks)
        if normalized == (0, 0):
            raise ValueError("local effect must translate a non-empty factor")
        digest = hashlib.sha256(
            repr(("factored-orbit-v1", "local", factor_shape, normalized)).encode()
        ).hexdigest()[:16]
        return cls(
            effect_id=f"factored-orbit-{digest}",
            kind="local",
            factor_shape=factor_shape,
            delta=normalized,
            interface_count=0,
            controllers=(controller,),
            support=1,
        )

    @classmethod
    def create_interface(
        cls,
        *,
        factor_shape: tuple[int, int],
        interface_count: int,
        controller: Point,
    ) -> Self:
        if interface_count < 1:
            raise ValueError("interface effect requires at least one edge")
        digest = hashlib.sha256(
            repr(
                (
                    "factored-orbit-v1",
                    "interface",
                    factor_shape,
                    interface_count,
                )
            ).encode()
        ).hexdigest()[:16]
        return cls(
            effect_id=f"factored-orbit-{digest}",
            kind="interface",
            factor_shape=factor_shape,
            delta=(0, 0),
            interface_count=interface_count,
            controllers=(controller,),
            support=1,
        )

    def apply_coordinate(self, coordinate: FactorCoordinate) -> FactorCoordinate:
        directions, ranks = self.factor_shape
        return (
            (coordinate[0] + self.delta[0]) % directions,
            (coordinate[1] + self.delta[1]) % ranks,
        )


@dataclass(frozen=True, slots=True)
class FactoredOrbitStep:
    effect_id: str
    module_index: int | None


@dataclass(frozen=True, slots=True)
class FactoredOrbitPlan:
    """A sequence of independently searched local steps plus interface commit."""

    steps: tuple[FactoredOrbitStep, ...]
    explored_states: int


@dataclass(frozen=True, slots=True)
class PermutationGenerator:
    """One evidenced permutation effect and its grounded controller roles.

    ``successor[index]`` is the destination slot index for the token currently
    at ``slots[index]``.  Controllers are evidence groundings, not constants in
    the symbolic operator.
    """

    effect_id: str
    slots: tuple[Point, ...]
    successor: tuple[int, ...]
    controllers: tuple[Point, ...]
    support: int
    axis: Axis
    pitch: int
    segment_count: int

    @classmethod
    def create(
        cls,
        *,
        slots: tuple[Point, ...],
        successor: tuple[int, ...],
        controller: Point,
        axis: Axis,
        pitch: int,
        segment_count: int,
    ) -> Self:
        """Construct a canonical, content-free generator."""

        if (
            not slots
            or len(slots) != len(successor)
            or len(set(slots)) != len(slots)
            or sorted(successor) != list(range(len(slots)))
        ):
            raise ValueError("successor must be a permutation of unique slots")
        if pitch < 1 or segment_count < 1:
            raise ValueError("pitch and segment_count must be positive")
        digest = hashlib.sha256(
            repr(("permutation-transport-v1", slots, successor)).encode()
        ).hexdigest()[:16]
        return cls(
            effect_id=f"permutation-{digest}",
            slots=slots,
            successor=successor,
            controllers=(controller,),
            support=1,
            axis=axis,
            pitch=pitch,
            segment_count=segment_count,
        )

    def destination(self, point: Point) -> Point:
        """Apply this generator to one percept-relative token position."""

        try:
            source_index = self.slots.index(point)
        except ValueError:
            return point
        return self.slots[self.successor[source_index]]

    def apply_points(self, points: tuple[Point, ...]) -> tuple[Point, ...]:
        """Apply the generator to indistinguishable projected token positions."""

        return tuple(sorted(self.destination(point) for point in points))


@dataclass(frozen=True, slots=True)
class PermutationSystem:
    """A deterministic collection of multiple observed generator families."""

    generators: tuple[PermutationGenerator, ...]

    @classmethod
    def create(
        cls,
        generators: tuple[PermutationGenerator, ...],
        *,
        bounds: PermutationBounds = PermutationBounds(),
    ) -> Self:
        """Validate and deterministically order an episode's generators."""

        if len(generators) > bounds.max_generators:
            raise ValueError("generator bound exceeded")
        ordered = tuple(
            sorted(
                generators,
                key=lambda item: (
                    item.effect_id,
                    item.controllers,
                    item.slots,
                ),
            )
        )
        if len({item.effect_id for item in ordered}) != len(ordered):
            raise ValueError("effect identifiers must be unique")
        all_slots = {point for item in ordered for point in item.slots}
        if len(all_slots) > bounds.max_slots:
            raise ValueError("slot bound exceeded")
        return cls(generators=ordered)

    @property
    def all_slots(self) -> tuple[Point, ...]:
        """Return the union lattice used by projected planning."""

        return tuple(
            sorted({point for item in self.generators for point in item.slots})
        )

    @property
    def shared_slots(self) -> tuple[Point, ...]:
        """Return slots shared by distinct permutation domains.

        Inverse directions over the same domain count once, so this reports
        junctions between transport families rather than every bidirectional
        slot.
        """

        domains = tuple({frozenset(item.slots) for item in self.generators})
        counts: Counter[Point] = Counter()
        for domain in domains:
            counts.update(domain)
        return tuple(sorted(point for point, count in counts.items() if count > 1))

    def generator(self, effect_id: str) -> PermutationGenerator:
        """Resolve a typed plan step to its evidenced generator."""

        for item in self.generators:
            if item.effect_id == effect_id:
                return item
        raise KeyError(effect_id)

    def apply_state(
        self,
        state: ProjectedState,
        effect_id: str,
    ) -> ProjectedState:
        """Apply one generator to marker-color position groups."""

        generator = self.generator(effect_id)
        slots = self.all_slots
        point_state = tuple(tuple(slots[index] for index in group) for group in state)
        updated = tuple(generator.apply_points(group) for group in point_state)
        indexes = {point: index for index, point in enumerate(slots)}
        return tuple(tuple(indexes[point] for point in group) for group in updated)


@dataclass(frozen=True, slots=True)
class PermutationPlan:
    """A bounded typed plan over generator identities."""

    generator_ids: tuple[str, ...]
    explored_states: int
    initial_state: ProjectedState
    goal_state: ProjectedState


def merge_generator_evidence(
    generators: tuple[PermutationGenerator, ...],
    evidence: PermutationGenerator,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> tuple[PermutationGenerator, ...]:
    """Merge a repeated controller/effect observation without conflating effects."""

    output = list(generators)
    for index, item in enumerate(output):
        if item.slots != evidence.slots or item.successor != evidence.successor:
            continue
        output[index] = replace(
            item,
            controllers=tuple(sorted(set((*item.controllers, *evidence.controllers)))),
            support=item.support + evidence.support,
        )
        return PermutationSystem.create(
            tuple(output),
            bounds=bounds,
        ).generators
    output.append(evidence)
    return PermutationSystem.create(tuple(output), bounds=bounds).generators


def infer_disjoint_polar_product(
    token_positions: tuple[Point, ...],
    anchor_points: tuple[Point, ...],
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> FactoredOrbitDomain | None:
    """Return the unique domain, discarding diagnostic search evidence."""

    return infer_disjoint_polar_product_diagnostic(
        token_positions,
        anchor_points,
        bounds=bounds,
    ).domain


def infer_disjoint_polar_product_diagnostic(
    token_positions: tuple[Point, ...],
    anchor_points: tuple[Point, ...],
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> FactoredOrbitInference:
    """Find one exact repeated ``cyclic-direction × radial-rank`` cover.

    Hubs, pitch, factor sizes, module placement, and anchor interfaces are all
    induced from the supplied percept-relative slot geometry.  Multiple exact
    covers are deliberately treated as ambiguity rather than tie-broken.
    """

    points = tuple(sorted(set(token_positions)))
    anchors = tuple(sorted(set(anchor_points)))
    if (
        len(points) != len(token_positions)
        or len(anchors) != len(anchor_points)
        or not set(anchors).issubset(points)
        or len(points) > bounds.max_factored_slots
        or not bounds.min_factor_modules <= len(anchors) <= bounds.max_factor_modules
    ):
        return FactoredOrbitInference(None, 0, False)
    module_points = tuple(point for point in points if point not in set(anchors))
    if not module_points:
        return FactoredOrbitInference(None, 0, False)
    candidates = _polar_product_candidates(module_points, bounds=bounds)
    if not candidates:
        return FactoredOrbitInference(None, 0, False)

    solutions: dict[
        tuple[
            tuple[
                Point,
                int,
                tuple[Point, ...],
                int,
                tuple[tuple[Point, ...], ...],
            ],
            ...,
        ],
        tuple[PolarProductModule, ...],
    ] = {}
    explored_states = 0
    by_shape: dict[tuple[int, int], list[PolarProductModule]] = {}
    for candidate in candidates:
        by_shape.setdefault(candidate.factor_shape, []).append(candidate)
    target = frozenset(module_points)
    for shape_candidates in by_shape.values():
        remaining_states = bounds.max_factorization_search_states - explored_states
        if remaining_states < 1:
            return FactoredOrbitInference(None, explored_states, True)
        cover_search = _exact_module_covers(
            target,
            tuple(shape_candidates),
            bounds=bounds,
            max_states=remaining_states,
        )
        explored_states += cover_search.explored_states
        if cover_search.search_exhausted:
            return FactoredOrbitInference(None, explored_states, True)
        for cover in cover_search.covers:
            ordered = tuple(sorted(cover, key=lambda item: item.hub))
            key = tuple(
                (
                    item.hub,
                    item.pitch,
                    item.rays,
                    item.ranks,
                    item.points,
                )
                for item in ordered
            )
            solutions[key] = ordered
            if len(solutions) >= bounds.max_factorizations:
                return FactoredOrbitInference(None, explored_states, False)
    if len(solutions) != 1:
        return FactoredOrbitInference(None, explored_states, False)
    modules = next(iter(solutions.values()))
    if len(modules) != len(anchors):
        return FactoredOrbitInference(None, explored_states, False)
    interfaces = _infer_nearest_interfaces(modules, anchors)
    if interfaces is None:
        return FactoredOrbitInference(None, explored_states, False)
    return FactoredOrbitInference(
        FactoredOrbitDomain(modules=modules, interfaces=interfaces),
        explored_states,
        False,
    )


def canonical_dihedral_shape(shape: tuple[Point, ...]) -> tuple[Point, ...]:
    """Canonicalize a local bitmap shape over all eight D4 transforms."""

    if not shape:
        return ()
    variants: list[tuple[Point, ...]] = []
    for transform_index in range(8):
        transformed = tuple(
            _d4_transform(point, transform_index) for point in shape
        )
        min_x = min(point[0] for point in transformed)
        min_y = min(point[1] for point in transformed)
        variants.append(
            tuple(
                sorted((point[0] - min_x, point[1] - min_y) for point in transformed)
            )
        )
    return min(variants)


def ground_polar_controller(
    centroid: Point,
    shape: tuple[Point, ...],
    domain: FactoredOrbitDomain,
) -> PolarControllerGrounding | None:
    """Bind an elongated controller to one module by intrinsic-axis relation."""

    axis = _intrinsic_axis(shape)
    if axis is None or centroid in set(domain.all_slots):
        return None
    distances = tuple(
        (
            max(abs(centroid[0] - module.hub[0]), abs(centroid[1] - module.hub[1])),
            index,
        )
        for index, module in enumerate(domain.modules)
    )
    nearest_distance = min(item[0] for item in distances)
    nearest = tuple(index for distance, index in distances if distance == nearest_distance)
    if len(nearest) != 1:
        return None
    module_index = nearest[0]
    module = domain.modules[module_index]
    outer_radius = module.pitch * module.ranks
    if not outer_radius < nearest_distance <= outer_radius + 2 * module.pitch:
        return None
    dx = centroid[0] - module.hub[0]
    dy = centroid[1] - module.hub[1]
    if (axis == "horizontal" and dy == 0) or (
        axis == "vertical" and dx == 0
    ):
        relation: ControllerAxisRelation = "parallel"
    elif (axis == "horizontal" and dx == 0) or (
        axis == "vertical" and dy == 0
    ):
        relation = "perpendicular"
    else:
        return None
    return PolarControllerGrounding(module_index=module_index, relation=relation)


def infer_factored_orbit_generators(
    before: Frame,
    after: Frame,
    domain: FactoredOrbitDomain,
    module_index: int,
    controller: Point,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> tuple[FactoredOrbitGenerator, ...]:
    """Enumerate exact translations on one observed module's two factors."""

    dimensions = _shared_dimensions(before, after)
    if dimensions is None or not 0 <= module_index < len(domain.modules):
        return ()
    width, height = dimensions
    if any(
        not (0 <= point[0] < width and 0 <= point[1] < height)
        for point in domain.all_slots
    ):
        return ()
    module = domain.modules[module_index]
    module_slots = set(module.slots)
    changed = {
        point
        for point in domain.all_slots
        if _value(before, point) != _value(after, point)
    }
    if not changed or not changed.issubset(module_slots):
        return ()
    candidates: list[FactoredOrbitGenerator] = []
    directions, ranks = module.factor_shape
    for direction_delta in range(directions):
        for rank_delta in range(ranks):
            if (direction_delta, rank_delta) == (0, 0):
                continue
            evidence = FactoredOrbitGenerator.create_local(
                factor_shape=module.factor_shape,
                delta=(direction_delta, rank_delta),
                controller=controller,
            )
            if factored_effect_matches(
                before,
                after,
                domain,
                evidence,
                module_index=module_index,
            ):
                candidates.append(evidence)
                if len(candidates) > bounds.max_cycle_orderings:
                    return ()
    return tuple(sorted(candidates, key=lambda item: item.effect_id))


def infer_factored_interface_generator(
    before: Frame,
    after: Frame,
    domain: FactoredOrbitDomain,
    controller: Point,
) -> FactoredOrbitGenerator | None:
    """Infer one exact simultaneous swap across every anchor/outlet edge."""

    if any(
        _value(before, interface.anchor) == _value(before, interface.outlet)
        for interface in domain.interfaces
    ):
        return None
    evidence = FactoredOrbitGenerator.create_interface(
        factor_shape=domain.factor_shape,
        interface_count=len(domain.interfaces),
        controller=controller,
    )
    changed = {
        point
        for point in domain.all_slots
        if _value(before, point) != _value(after, point)
    }
    if not changed or not factored_effect_matches(
        before,
        after,
        domain,
        evidence,
        module_index=None,
    ):
        return None
    return evidence


def factored_effect_matches(
    before: Frame,
    after: Frame,
    domain: FactoredOrbitDomain,
    effect: FactoredOrbitGenerator,
    *,
    module_index: int | None,
) -> bool:
    """Check one effect against the complete conserved factored token domain."""

    dimensions = _shared_dimensions(before, after)
    if dimensions is None:
        return False
    width, height = dimensions
    if any(
        not (0 <= point[0] < width and 0 <= point[1] < height)
        for point in domain.all_slots
    ):
        return False
    if effect.factor_shape != domain.factor_shape:
        return False
    destinations: dict[Point, Point] = {
        point: point for point in domain.all_slots
    }
    if effect.kind == "local":
        if module_index is None or not 0 <= module_index < len(domain.modules):
            return False
        module = domain.modules[module_index]
        for point in module.slots:
            coordinate = module.coordinate(point)
            destinations[point] = module.point(effect.apply_coordinate(coordinate))
    else:
        if (
            module_index is not None
            or effect.interface_count != len(domain.interfaces)
        ):
            return False
        for interface in domain.interfaces:
            destinations[interface.anchor] = interface.outlet
            destinations[interface.outlet] = interface.anchor
    return all(
        _value(after, destination) == _value(before, source)
        for source, destination in destinations.items()
    )


def merge_factored_evidence(
    generators: tuple[FactoredOrbitGenerator, ...],
    evidence: FactoredOrbitGenerator,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> tuple[FactoredOrbitGenerator, ...]:
    """Merge support for an abstract factor effect across grounded controllers."""

    output = list(generators)
    for index, item in enumerate(output):
        if (
            item.kind != evidence.kind
            or item.factor_shape != evidence.factor_shape
            or item.delta != evidence.delta
            or item.interface_count != evidence.interface_count
        ):
            continue
        output[index] = replace(
            item,
            controllers=tuple(sorted(set((*item.controllers, *evidence.controllers)))),
            support=item.support + evidence.support,
        )
        return tuple(sorted(output, key=lambda candidate: candidate.effect_id))
    if len(output) >= bounds.max_generators:
        raise ValueError("generator bound exceeded")
    output.append(evidence)
    return tuple(sorted(output, key=lambda candidate: candidate.effect_id))


def plan_factored_orbit_transport(
    frame: Frame,
    targets: tuple[MarkerTarget, ...],
    domain: FactoredOrbitDomain,
    generators: tuple[FactoredOrbitGenerator, ...],
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> FactoredOrbitPlan | None:
    """Plan each independent module locally, followed by one interface commit."""

    dimensions = _shared_dimensions(frame, frame)
    if dimensions is None or not targets or not generators:
        return None
    target_by_anchor = {target.point: target.color for target in targets}
    if (
        len(target_by_anchor) != len(targets)
        or set(target_by_anchor) != set(domain.anchor_slots)
        or any(generator.factor_shape != domain.factor_shape for generator in generators)
    ):
        return None
    if all(_value(frame, point) == color for point, color in target_by_anchor.items()):
        return FactoredOrbitPlan(steps=(), explored_states=0)
    local_generators = tuple(
        sorted(
            (generator for generator in generators if generator.kind == "local"),
            key=lambda item: item.effect_id,
        )
    )
    interfaces = tuple(
        generator for generator in generators if generator.kind == "interface"
    )
    if not local_generators or len(interfaces) != 1:
        return None

    steps: list[FactoredOrbitStep] = []
    explored_states = 0
    interfaces_by_module = {
        interface.module_index: interface for interface in domain.interfaces
    }
    for module_index, module in enumerate(domain.modules):
        interface = interfaces_by_module.get(module_index)
        if interface is None:
            return None
        color = target_by_anchor[interface.anchor]
        current = tuple(
            sorted(
                module.coordinate(point)
                for point in module.slots
                if _value(frame, point) == color
            )
        )
        goal = (module.coordinate(interface.outlet),)
        if len(current) != len(goal):
            return None
        local_plan = _plan_factored_module(
            current,
            goal,
            local_generators,
            max_states=bounds.max_factored_states - explored_states,
            max_depth=bounds.max_plan_depth - len(steps) - 1,
        )
        if local_plan is None:
            return None
        effect_ids, local_explored = local_plan
        explored_states += local_explored
        if explored_states > bounds.max_factored_states:
            return None
        steps.extend(
            FactoredOrbitStep(effect_id=effect_id, module_index=module_index)
            for effect_id in effect_ids
        )
    steps.append(
        FactoredOrbitStep(effect_id=interfaces[0].effect_id, module_index=None)
    )
    if len(steps) > bounds.max_plan_depth:
        return None
    return FactoredOrbitPlan(steps=tuple(steps), explored_states=explored_states)


def infer_segmented_permutations(
    before: Frame,
    after: Frame,
    token_positions: tuple[Point, ...],
    controller: Point,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> tuple[PermutationGenerator, ...]:
    """Infer exact successor maps over disconnected equal-pitch segments.

    Multiple results mean that the observation is underdetermined.  A caller
    should promote only a unique result, or retain the candidates until another
    observation eliminates the ambiguity.
    """

    dimensions = _shared_dimensions(before, after)
    if dimensions is None:
        return ()
    width, height = dimensions
    points = tuple(sorted(set(token_positions)))
    if (
        len(points) != len(token_positions)
        or len(points) > bounds.max_slots
        or any(not (0 <= x < width and 0 <= y < height) for x, y in points)
    ):
        return ()
    changed = {
        point for point in points if _value(before, point) != _value(after, point)
    }
    if not changed:
        return ()

    candidates: dict[
        tuple[tuple[Point, ...], tuple[int, ...]],
        PermutationGenerator,
    ] = {}
    for axis in ("horizontal", "vertical"):
        segmented = _equal_pitch_segments(
            points,
            changed,
            axis=axis,
            bounds=bounds,
        )
        if segmented is None:
            continue
        pitch, raw_segments = segmented
        for direction in (1, -1):
            oriented: list[tuple[Point, ...]] = []
            valid = True
            for segment in raw_segments:
                ordered = segment if direction > 0 else tuple(reversed(segment))
                if not all(
                    _value(after, destination) == _value(before, source)
                    for source, destination in zip(ordered, ordered[1:])
                ):
                    valid = False
                    break
                oriented.append(ordered)
            if not valid:
                continue
            if math.factorial(len(oriented) - 1) > bounds.max_cycle_orderings:
                continue
            first = min(oriented)
            remaining = tuple(item for item in oriented if item != first)
            for tail in itertools.permutations(remaining):
                ordered_segments = (first, *tail)
                track = tuple(
                    point for segment in ordered_segments for point in segment
                )
                if not _predicts_cycle(before, after, track):
                    continue
                generator = _generator_from_track(
                    track,
                    controller=controller,
                    axis=axis,
                    pitch=pitch,
                    segment_count=len(ordered_segments),
                )
                candidates[(generator.slots, generator.successor)] = generator
                if len(candidates) > bounds.max_cycle_orderings:
                    return ()
    return tuple(
        sorted(
            candidates.values(),
            key=lambda item: (
                item.effect_id,
                item.axis,
                item.controllers,
            ),
        )
    )


def infer_path_cycle_permutations(
    before: Frame,
    after: Frame,
    token_positions: tuple[Point, ...],
    controller: Point,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> tuple[PermutationGenerator, ...]:
    """Infer rotations over intervals of one uniform simple rectilinear path.

    The exact boundary is the declared token-centroid domain: every changed
    token must belong to the inferred interval and every value on that interval
    must match one cyclic successor step.  Unrelated rendered UI is outside this
    projected operator.
    """

    dimensions = _shared_dimensions(before, after)
    if dimensions is None:
        return ()
    width, height = dimensions
    points = tuple(sorted(set(token_positions)))
    if (
        len(points) != len(token_positions)
        or len(points) < bounds.min_segment_length
        or len(points) > bounds.max_slots
        or any(not (0 <= x < width and 0 <= y < height) for x, y in points)
    ):
        return ()
    changed = {
        point for point in points if _value(before, point) != _value(after, point)
    }
    if not changed:
        return ()
    ordered = _rectilinear_path(points)
    if ordered is None:
        return ()

    candidates: dict[
        tuple[tuple[Point, ...], tuple[int, ...]],
        PermutationGenerator,
    ] = {}
    for start in range(len(ordered)):
        for stop in range(start + bounds.min_segment_length, len(ordered) + 1):
            segment = ordered[start:stop]
            segment_set = set(segment)
            if not changed.issubset(segment_set):
                continue
            if any(
                _value(before, point) != _value(after, point)
                for point in points
                if point not in segment_set
            ):
                continue
            for track in (segment, tuple(reversed(segment))):
                if not _predicts_cycle(before, after, track):
                    continue
                generator = _generator_from_track(
                    track,
                    controller=controller,
                    axis="path",
                    pitch=_path_pitch(track),
                    segment_count=1,
                )
                candidates[(generator.slots, generator.successor)] = generator
                if len(candidates) > bounds.max_cycle_orderings:
                    return ()
    return tuple(
        sorted(
            candidates.values(),
            key=lambda item: (item.effect_id, item.controllers),
        )
    )


def plan_marker_transport(
    frame: Frame,
    token_positions: tuple[Point, ...],
    targets: tuple[MarkerTarget, ...],
    system: PermutationSystem,
    *,
    bounds: PermutationBounds = PermutationBounds(),
) -> PermutationPlan | None:
    """BFS over only the positions of marker-matched token colors."""

    dimensions = _shared_dimensions(frame, frame)
    if dimensions is None or not targets or not system.generators:
        return None
    width, height = dimensions
    points = tuple(sorted(set(token_positions)))
    if (
        len(points) != len(token_positions)
        or len(points) > bounds.max_slots
        or any(not (0 <= x < width and 0 <= y < height) for x, y in points)
    ):
        return None
    slots = system.all_slots
    slot_set = set(slots)
    if not slot_set.issubset(points):
        return None
    indexes = {point: index for index, point in enumerate(slots)}
    targets_by_color: dict[int, list[Point]] = {}
    for target in targets:
        if target.point not in indexes:
            return None
        targets_by_color.setdefault(target.color, []).append(target.point)

    initial_groups: list[tuple[int, ...]] = []
    goal_groups: list[tuple[int, ...]] = []
    for color in sorted(targets_by_color):
        current = tuple(
            indexes[point] for point in slots if _value(frame, point) == color
        )
        color_goal = tuple(sorted(indexes[point] for point in targets_by_color[color]))
        if len(current) != len(color_goal):
            return None
        initial_groups.append(tuple(sorted(current)))
        goal_groups.append(color_goal)
    initial = tuple(initial_groups)
    goal_state = tuple(goal_groups)
    if initial == goal_state:
        return PermutationPlan(
            generator_ids=(),
            explored_states=0,
            initial_state=initial,
            goal_state=goal_state,
        )

    queue: deque[tuple[ProjectedState, tuple[str, ...]]] = deque([(initial, ())])
    seen = {initial}
    explored = 0
    ordered_generators = system.generators
    while queue and explored < bounds.max_projected_states:
        state, plan = queue.popleft()
        explored += 1
        if len(plan) >= bounds.max_plan_depth:
            continue
        for generator in ordered_generators:
            successor = system.apply_state(state, generator.effect_id)
            if successor == state or successor in seen:
                continue
            successor_plan = (*plan, generator.effect_id)
            if successor == goal_state:
                return PermutationPlan(
                    generator_ids=successor_plan,
                    explored_states=explored,
                    initial_state=initial,
                    goal_state=goal_state,
                )
            if len(seen) >= bounds.max_projected_states:
                return None
            seen.add(successor)
            queue.append((successor, successor_plan))
    return None


def _polar_product_candidates(
    points: tuple[Point, ...],
    *,
    bounds: PermutationBounds,
) -> tuple[PolarProductModule, ...]:
    centers = {
        ((left[0] + right[0]) // 2, (left[1] + right[1]) // 2)
        for index, left in enumerate(points)
        for right in points[index + 1 :]
        if (left[0] + right[0]) % 2 == 0
        and (left[1] + right[1]) % 2 == 0
    }
    point_set = set(points)
    candidates: dict[
        tuple[
            Point,
            int,
            tuple[Point, ...],
            int,
            tuple[tuple[Point, ...], ...],
        ],
        PolarProductModule,
    ] = {}
    for hub in sorted(centers):
        distances_by_ray: dict[Point, set[int]] = {}
        for point in points:
            dx = point[0] - hub[0]
            dy = point[1] - hub[1]
            distance = math.gcd(abs(dx), abs(dy))
            if distance == 0:
                continue
            ray = (dx // distance, dy // distance)
            distances_by_ray.setdefault(ray, set()).add(distance)
        pitches = sorted(
            {distance for distances in distances_by_ray.values() for distance in distances}
        )
        for pitch in pitches:
            if pitch < 1:
                continue
            prefix_by_ray: dict[Point, int] = {}
            for ray, distances in distances_by_ray.items():
                rank = 0
                while (rank + 1) * pitch in distances:
                    rank += 1
                if rank >= bounds.min_factor_ranks:
                    prefix_by_ray[ray] = min(rank, bounds.max_factor_ranks)
            if not prefix_by_ray:
                continue
            for ranks in range(
                bounds.min_factor_ranks,
                min(bounds.max_factor_ranks, max(prefix_by_ray.values())) + 1,
            ):
                rays = tuple(
                    sorted(
                        (
                            ray
                            for ray, prefix in prefix_by_ray.items()
                            if prefix >= ranks
                        ),
                        key=_ray_angle,
                    )
                )
                if not (
                    bounds.min_factor_directions
                    <= len(rays)
                    <= bounds.max_factor_directions
                    and _uniform_angular_cycle(rays)
                ):
                    continue
                module_points = tuple(
                    tuple(
                        (
                            hub[0] + ray[0] * pitch * rank,
                            hub[1] + ray[1] * pitch * rank,
                        )
                        for rank in range(1, ranks + 1)
                    )
                    for ray in rays
                )
                slots = {point for ray in module_points for point in ray}
                if len(slots) != len(rays) * ranks or not slots.issubset(point_set):
                    continue
                module = PolarProductModule(
                    hub=hub,
                    pitch=pitch,
                    rays=rays,
                    ranks=ranks,
                    points=module_points,
                )
                key = (hub, pitch, rays, ranks, module_points)
                candidates[key] = module
                if len(candidates) > bounds.max_cycle_orderings:
                    return ()
    return tuple(
        sorted(
            candidates.values(),
            key=lambda item: (
                -len(item.slots),
                item.factor_shape,
                item.hub,
                item.pitch,
                item.rays,
            ),
        )
    )


def _exact_module_covers(
    target: frozenset[Point],
    candidates: tuple[PolarProductModule, ...],
    *,
    bounds: PermutationBounds,
    max_states: int | None = None,
) -> _ExactCoverSearch:
    state_limit = (
        bounds.max_factorization_search_states
        if max_states is None
        else max_states
    )
    if state_limit < 1:
        return _ExactCoverSearch((), 0, True)
    by_point: dict[Point, tuple[PolarProductModule, ...]] = {
        point: tuple(
            candidate for candidate in candidates if point in set(candidate.slots)
        )
        for point in target
    }
    if any(not options for options in by_point.values()):
        return _ExactCoverSearch((), 0, False)
    output: list[tuple[PolarProductModule, ...]] = []
    seen: set[
        tuple[frozenset[Point], frozenset[PolarProductModule]]
    ] = set()
    explored_states = 0
    search_exhausted = False

    def search(
        covered: frozenset[Point],
        selected: tuple[PolarProductModule, ...],
    ) -> None:
        nonlocal explored_states, search_exhausted
        state = (covered, frozenset(selected))
        if search_exhausted or state in seen:
            return
        if explored_states >= state_limit:
            search_exhausted = True
            return
        seen.add(state)
        explored_states += 1
        if len(output) >= bounds.max_factorizations:
            return
        if covered == target:
            if bounds.min_factor_modules <= len(selected) <= bounds.max_factor_modules:
                output.append(selected)
            return
        if len(selected) >= bounds.max_factor_modules:
            return
        uncovered = target - covered
        point = min(
            uncovered,
            key=lambda item: (
                sum(
                    not set(candidate.slots).isdisjoint(covered)
                    for candidate in by_point[item]
                ),
                item,
            ),
        )
        for candidate in by_point[point]:
            if search_exhausted or len(output) >= bounds.max_factorizations:
                return
            slots = frozenset(candidate.slots)
            if slots.isdisjoint(covered):
                search(covered | slots, (*selected, candidate))

    search(frozenset(), ())
    return _ExactCoverSearch(
        tuple(output),
        explored_states,
        search_exhausted,
    )


def _infer_nearest_interfaces(
    modules: tuple[PolarProductModule, ...],
    anchors: tuple[Point, ...],
) -> tuple[FactoredInterface, ...] | None:
    interfaces: list[FactoredInterface] = []
    for anchor in anchors:
        module_choices: list[tuple[int, int, Point]] = []
        for module_index, module in enumerate(modules):
            distances = tuple(
                (
                    max(abs(anchor[0] - point[0]), abs(anchor[1] - point[1])),
                    point,
                )
                for point in module.slots
            )
            nearest_distance = min(item[0] for item in distances)
            nearest_points = tuple(
                point for distance, point in distances if distance == nearest_distance
            )
            if len(nearest_points) == 1:
                module_choices.append(
                    (nearest_distance, module_index, nearest_points[0])
                )
        if not module_choices:
            return None
        distance = min(item[0] for item in module_choices)
        nearest_modules = tuple(
            item for item in module_choices if item[0] == distance
        )
        if len(nearest_modules) != 1:
            return None
        _, module_index, outlet = nearest_modules[0]
        if distance != modules[module_index].pitch:
            return None
        interfaces.append(
            FactoredInterface(
                module_index=module_index,
                anchor=anchor,
                outlet=outlet,
            )
        )
    if {item.module_index for item in interfaces} != set(range(len(modules))):
        return None
    return tuple(sorted(interfaces, key=lambda item: item.module_index))


def _ray_angle(ray: Point) -> float:
    return math.atan2(ray[1], ray[0])


def _uniform_angular_cycle(rays: tuple[Point, ...]) -> bool:
    if len(rays) < 3 or len(set(rays)) != len(rays):
        return False
    angles = tuple(sorted(_ray_angle(ray) for ray in rays))
    gaps = tuple(
        (
            angles[(index + 1) % len(angles)]
            - angle
            + (2 * math.pi if index == len(angles) - 1 else 0)
        )
        for index, angle in enumerate(angles)
    )
    expected = 2 * math.pi / len(rays)
    return all(math.isclose(gap, expected, rel_tol=1e-9, abs_tol=1e-9) for gap in gaps)


def _intrinsic_axis(shape: tuple[Point, ...]) -> Axis | None:
    if not shape:
        return None
    width = max(point[0] for point in shape) - min(point[0] for point in shape) + 1
    height = max(point[1] for point in shape) - min(point[1] for point in shape) + 1
    if width == height:
        return None
    return "horizontal" if width > height else "vertical"


def _d4_transform(point: Point, transform_index: int) -> Point:
    x, y = point
    return (
        (x, y),
        (-x, y),
        (x, -y),
        (-x, -y),
        (y, x),
        (-y, x),
        (y, -x),
        (-y, -x),
    )[transform_index]


def _plan_factored_module(
    initial: tuple[FactorCoordinate, ...],
    goal: tuple[FactorCoordinate, ...],
    generators: tuple[FactoredOrbitGenerator, ...],
    *,
    max_states: int,
    max_depth: int,
) -> tuple[tuple[str, ...], int] | None:
    if initial == goal:
        return (), 0
    if max_states < 1 or max_depth < 1:
        return None
    queue: deque[
        tuple[tuple[FactorCoordinate, ...], tuple[str, ...]]
    ] = deque([(initial, ())])
    seen = {initial}
    explored = 0
    while queue and explored < max_states:
        state, plan = queue.popleft()
        explored += 1
        if len(plan) >= max_depth:
            continue
        for generator in generators:
            successor = tuple(
                sorted(generator.apply_coordinate(coordinate) for coordinate in state)
            )
            if successor == state or successor in seen:
                continue
            successor_plan = (*plan, generator.effect_id)
            if successor == goal:
                return successor_plan, explored
            if len(seen) >= max_states:
                return None
            seen.add(successor)
            queue.append((successor, successor_plan))
    return None


def _shared_dimensions(before: Frame, after: Frame) -> tuple[int, int] | None:
    if not before or not after or len(before) != len(after):
        return None
    width = len(before[0])
    if (
        width == 0
        or width != len(after[0])
        or any(len(row) != width for row in before)
        or any(len(row) != width for row in after)
    ):
        return None
    return width, len(before)


def _value(frame: Frame, point: Point) -> int:
    return frame[point[1]][point[0]]


def _equal_pitch_segments(
    points: tuple[Point, ...],
    changed: set[Point],
    *,
    axis: Axis,
    bounds: PermutationBounds,
) -> tuple[int, tuple[tuple[Point, ...], ...]] | None:
    groups: dict[int, list[Point]] = {}
    for point in points:
        key = point[1] if axis == "horizontal" else point[0]
        groups.setdefault(key, []).append(point)
    active = {
        key: sorted(
            group,
            key=lambda point: point[0] if axis == "horizontal" else point[1],
        )
        for key, group in groups.items()
        if any(point in changed for point in group)
    }
    differences: Counter[int] = Counter()
    for group in active.values():
        coordinates = [
            point[0] if axis == "horizontal" else point[1] for point in group
        ]
        differences.update(
            right - left
            for left, right in zip(coordinates, coordinates[1:])
            if right > left
        )
    if not differences:
        return None
    pitch = max(
        differences.items(),
        key=lambda item: (item[1], -item[0]),
    )[0]
    segments: list[tuple[Point, ...]] = []
    for group in active.values():
        run: list[Point] = []
        previous_coordinate: int | None = None
        for point in group:
            coordinate = point[0] if axis == "horizontal" else point[1]
            if (
                previous_coordinate is not None
                and coordinate - previous_coordinate != pitch
            ):
                if len(run) >= bounds.min_segment_length and any(
                    item in changed for item in run
                ):
                    segments.append(tuple(run))
                run = []
            run.append(point)
            previous_coordinate = coordinate
        if len(run) >= bounds.min_segment_length and any(
            item in changed for item in run
        ):
            segments.append(tuple(run))
    segments.sort()
    covered = {point for segment in segments for point in segment}
    if (
        not changed.issubset(covered)
        or not bounds.min_segment_count <= len(segments) <= bounds.max_segments
    ):
        return None
    return pitch, tuple(segments)


def _predicts_cycle(before: Frame, after: Frame, track: tuple[Point, ...]) -> bool:
    return all(
        _value(after, track[(index + 1) % len(track)]) == _value(before, source)
        for index, source in enumerate(track)
    )


def _rectilinear_path(points: tuple[Point, ...]) -> tuple[Point, ...] | None:
    """Return the canonical ordering of one uniform rectilinear path."""

    pitch = _path_pitch(points)
    if pitch < 1:
        return None
    point_set = set(points)
    neighbors = {
        point: tuple(
            sorted(
                candidate
                for candidate in (
                    (point[0] - pitch, point[1]),
                    (point[0] + pitch, point[1]),
                    (point[0], point[1] - pitch),
                    (point[0], point[1] + pitch),
                )
                if candidate in point_set
            )
        )
        for point in points
    }
    if any(len(items) > 2 for items in neighbors.values()):
        return None
    endpoints = tuple(
        sorted(point for point, items in neighbors.items() if len(items) == 1)
    )
    if len(endpoints) != 2:
        return None
    ordered = [endpoints[0]]
    previous: Point | None = None
    while len(ordered) < len(points):
        candidates = tuple(
            item for item in neighbors[ordered[-1]] if item != previous
        )
        if len(candidates) != 1 or candidates[0] in ordered:
            return None
        previous, current = ordered[-1], candidates[0]
        ordered.append(current)
    if set(ordered) != point_set:
        return None
    return tuple(ordered)


def _path_pitch(points: tuple[Point, ...]) -> int:
    """Return the greatest shared axial spacing of a rectilinear slot set."""

    differences = [
        difference
        for index, left in enumerate(points)
        for right in points[index + 1 :]
        for difference in (
            abs(right[0] - left[0]) if right[1] == left[1] else 0,
            abs(right[1] - left[1]) if right[0] == left[0] else 0,
        )
        if difference > 0
    ]
    if not differences:
        return 0
    pitch = differences[0]
    for difference in differences[1:]:
        pitch = math.gcd(pitch, difference)
    return pitch


def _generator_from_track(
    track: tuple[Point, ...],
    *,
    controller: Point,
    axis: Axis,
    pitch: int,
    segment_count: int,
) -> PermutationGenerator:
    slots = tuple(sorted(track))
    indexes = {point: index for index, point in enumerate(slots)}
    destinations = {
        source: track[(index + 1) % len(track)] for index, source in enumerate(track)
    }
    successor = tuple(indexes[destinations[point]] for point in slots)
    return PermutationGenerator.create(
        slots=slots,
        successor=successor,
        controller=controller,
        axis=axis,
        pitch=pitch,
        segment_count=segment_count,
    )
