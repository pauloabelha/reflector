from __future__ import annotations

import pytest

from reflector.core.permutation_transport import (
    FactoredOrbitDomain,
    FactoredOrbitGenerator,
    Frame,
    MarkerTarget,
    PermutationBounds,
    PermutationGenerator,
    PermutationSystem,
    Point,
    canonical_dihedral_shape,
    ground_polar_controller,
    infer_disjoint_polar_product,
    infer_disjoint_polar_product_diagnostic,
    infer_factored_interface_generator,
    infer_factored_orbit_generators,
    infer_path_cycle_permutations,
    infer_segmented_permutations,
    merge_factored_evidence,
    merge_generator_evidence,
    plan_factored_orbit_transport,
    plan_marker_transport,
)


def _blank_frame(width: int = 24, height: int = 24) -> list[list[int]]:
    return [[0 for _x in range(width)] for _y in range(height)]


def _freeze(pixels: list[list[int]]) -> Frame:
    return tuple(tuple(row) for row in pixels)


def _paint(
    values: dict[Point, int],
    *,
    width: int = 24,
    height: int = 24,
) -> Frame:
    pixels = _blank_frame(width, height)
    for (x, y), value in values.items():
        pixels[y][x] = value
    return _freeze(pixels)


def _cycle_generator(
    track: tuple[Point, ...],
    *,
    controller: Point,
    axis: str,
    pitch: int = 2,
    segment_count: int = 4,
) -> PermutationGenerator:
    slots = tuple(sorted(track))
    indexes = {point: index for index, point in enumerate(slots)}
    destinations = {
        point: track[(index + 1) % len(track)] for index, point in enumerate(track)
    }
    return PermutationGenerator.create(
        slots=slots,
        successor=tuple(indexes[destinations[point]] for point in slots),
        controller=controller,
        axis=axis,  # type: ignore[arg-type]
        pitch=pitch,
        segment_count=segment_count,
    )


def _apply_values(
    values: dict[Point, int],
    generator: PermutationGenerator,
) -> dict[Point, int]:
    output = dict(values)
    for source in generator.slots:
        output[generator.destination(source)] = values[source]
    return output


def _polar_fixture(
    *,
    scale: int = 1,
    ranks: int = 2,
) -> tuple[tuple[Point, ...], tuple[Point, ...]]:
    pitch = 2 * scale
    hubs = ((12 * scale, 12 * scale), (36 * scale, 12 * scale), (24 * scale, 36 * scale))
    rays = (
        (-1, -1),
        (0, -1),
        (1, -1),
        (1, 0),
        (1, 1),
        (0, 1),
        (-1, 1),
        (-1, 0),
    )
    modules = tuple(
        (
            hub[0] + ray[0] * pitch * rank,
            hub[1] + ray[1] * pitch * rank,
        )
        for hub in hubs
        for ray in rays
        for rank in range(1, ranks + 1)
    )
    anchor_rank = ranks + 1
    anchors = (
        (
            hubs[0][0] + anchor_rank * pitch,
            hubs[0][1] + anchor_rank * pitch,
        ),
        (
            hubs[1][0] - anchor_rank * pitch,
            hubs[1][1] + anchor_rank * pitch,
        ),
        (hubs[2][0], hubs[2][1] - anchor_rank * pitch),
    )
    return tuple(sorted((*modules, *anchors))), tuple(sorted(anchors))


def _apply_factored_effect(
    values: dict[Point, int],
    domain: FactoredOrbitDomain,
    generator: FactoredOrbitGenerator,
    module_index: int | None,
) -> dict[Point, int]:
    output = dict(values)
    if generator.kind == "interface":
        for interface in domain.interfaces:
            output[interface.anchor] = values[interface.outlet]
            output[interface.outlet] = values[interface.anchor]
        return output
    assert module_index is not None
    module = domain.modules[module_index]
    for point in module.slots:
        destination = module.point(
            generator.apply_coordinate(module.coordinate(point))
        )
        output[destination] = values[point]
    return output


def test_infers_disconnected_equal_pitch_successor_without_content_priors() -> None:
    segments = (
        ((2, 3), (4, 3), (6, 3)),
        ((12, 3), (14, 3), (16, 3)),
        ((2, 15), (4, 15), (6, 15)),
        ((12, 15), (14, 15), (16, 15)),
    )
    track = tuple(point for segment in segments for point in segment)
    expected = _cycle_generator(
        track,
        controller=(1, 3),
        axis="horizontal",
    )
    values = {point: 20 + index for index, point in enumerate(track)}
    before = _paint(values)
    after = _paint(_apply_values(values, expected))

    inferred = infer_segmented_permutations(
        before,
        after,
        tuple(sorted(values)),
        controller=(1, 3),
    )

    assert len(inferred) == 1
    assert inferred[0].slots == expected.slots
    assert inferred[0].successor == expected.successor
    assert inferred[0].axis == "horizontal"
    assert inferred[0].pitch == 2
    assert inferred[0].segment_count == 4

    repeated = PermutationGenerator.create(
        slots=inferred[0].slots,
        successor=inferred[0].successor,
        controller=(21, 15),
        axis=inferred[0].axis,
        pitch=inferred[0].pitch,
        segment_count=inferred[0].segment_count,
    )
    merged = merge_generator_evidence(inferred, repeated)
    assert len(merged) == 1
    assert merged[0].support == 2
    assert merged[0].controllers == ((1, 3), (21, 15))


def test_multiple_shared_generators_plan_only_marker_color_positions() -> None:
    horizontal_segments = (
        ((2, 4), (4, 4), (6, 4)),
        ((12, 4), (14, 4), (16, 4)),
        ((2, 14), (4, 14), (6, 14)),
        ((12, 14), (14, 14), (16, 14)),
    )
    vertical_segments = (
        ((4, 2), (4, 4), (4, 6)),
        ((14, 2), (14, 4), (14, 6)),
        ((4, 12), (4, 14), (4, 16)),
        ((14, 12), (14, 14), (14, 16)),
    )
    horizontal_track = tuple(
        point for segment in horizontal_segments for point in segment
    )
    vertical_track = tuple(point for segment in vertical_segments for point in segment)
    forward_horizontal = _cycle_generator(
        horizontal_track,
        controller=(1, 4),
        axis="horizontal",
    )
    reverse_horizontal = _cycle_generator(
        tuple(reversed(horizontal_track)),
        controller=(18, 4),
        axis="horizontal",
    )
    forward_vertical = _cycle_generator(
        vertical_track,
        controller=(4, 1),
        axis="vertical",
    )
    reverse_vertical = _cycle_generator(
        tuple(reversed(vertical_track)),
        controller=(4, 18),
        axis="vertical",
    )
    positions = tuple(sorted(set(horizontal_track) | set(vertical_track)))
    goal_values = {point: 100 + index for index, point in enumerate(positions)}
    marker_colors = (901, 902)
    marker_points = (horizontal_track[-1], vertical_track[-1])
    for point, color in zip(marker_points, marker_colors):
        goal_values[point] = color

    inferred: tuple[PermutationGenerator, ...] = ()
    for generator in (
        forward_horizontal,
        reverse_horizontal,
        forward_vertical,
        reverse_vertical,
    ):
        evidence = infer_segmented_permutations(
            _paint(goal_values),
            _paint(_apply_values(goal_values, generator)),
            positions,
            controller=generator.controllers[0],
        )
        assert len(evidence) == 1
        inferred = merge_generator_evidence(inferred, evidence[0])
    system = PermutationSystem.create(inferred)

    initial_values = _apply_values(goal_values, forward_horizontal)
    initial_values = _apply_values(initial_values, forward_vertical)
    frame = _paint(initial_values)
    targets = tuple(
        MarkerTarget(point=point, color=color)
        for point, color in zip(marker_points, marker_colors)
    )
    plan = plan_marker_transport(frame, positions, targets, system)

    assert len(system.generators) == 4
    assert len(system.shared_slots) == 4
    assert plan is not None
    assert 0 < len(plan.generator_ids) <= 2
    state = plan.initial_state
    for effect_id in plan.generator_ids:
        state = system.apply_state(state, effect_id)
    assert state == plan.goal_state


def test_inference_and_planning_abstain_when_evidence_or_bounds_are_missing() -> None:
    single_segment = ((2, 4), (4, 4), (6, 4), (8, 4))
    generator = _cycle_generator(
        single_segment,
        controller=(1, 4),
        axis="horizontal",
        segment_count=1,
    )
    values = {point: 30 + index for index, point in enumerate(single_segment)}

    assert (
        infer_segmented_permutations(
            _paint(values),
            _paint(_apply_values(values, generator)),
            single_segment,
            controller=(1, 4),
        )
        == ()
    )

    system = PermutationSystem.create((generator,))
    frame = _paint(values)
    target = MarkerTarget(point=single_segment[-1], color=values[single_segment[0]])
    assert (
        plan_marker_transport(
            frame,
            single_segment,
            (target,),
            system,
            bounds=PermutationBounds(max_projected_states=1),
        )
        is None
    )


@pytest.mark.parametrize(
    "path",
    (
        ((2, 2), (5, 2), (8, 2), (5, 5)),
        ((2, 2), (5, 2), (5, 5), (2, 5)),
        ((2, 2), (5, 2), (8, 2), (14, 2), (17, 2), (20, 2)),
        ((2, 2), (5, 2), (9, 2), (9, 5)),
    ),
    ids=("branch", "closed-loop", "disconnected", "nonuniform"),
)
def test_path_cycle_inference_rejects_non_simple_uniform_paths(
    path: tuple[Point, ...],
) -> None:
    values = {point: 30 + index for index, point in enumerate(path)}
    expected = _cycle_generator(
        path,
        controller=(1, 2),
        axis="path",
        pitch=3,
        segment_count=1,
    )

    assert (
        infer_path_cycle_permutations(
            _paint(values),
            _paint(_apply_values(values, expected)),
            tuple(sorted(path)),
            controller=(1, 2),
        )
        == ()
    )


def test_path_cycle_inference_retains_repeated_color_ambiguity() -> None:
    path = ((2, 2), (5, 2), (8, 2), (8, 5), (8, 8), (5, 8))
    before_values = dict(zip(path, (1, 1, 1, 1, 2, 1), strict=True))
    expected = _cycle_generator(
        path,
        controller=(1, 2),
        axis="path",
        pitch=3,
        segment_count=1,
    )

    candidates = infer_path_cycle_permutations(
        _paint(before_values),
        _paint(_apply_values(before_values, expected)),
        tuple(sorted(path)),
        controller=(1, 2),
    )

    assert len(candidates) == 4
    assert len({(item.slots, item.successor) for item in candidates}) == 4


def test_path_cycle_inference_is_exact_on_its_declared_token_domain() -> None:
    path = ((2, 2), (5, 2), (8, 2), (8, 5), (8, 8), (5, 8))
    subpath = path[:3]
    values = {point: 20 + index for index, point in enumerate(path)}
    expected = _cycle_generator(
        subpath,
        controller=(1, 2),
        axis="path",
        pitch=3,
        segment_count=1,
    )
    before = _paint(values)
    exact_after = _paint(_apply_values(values, expected))
    changed_outside_domain = dict(_apply_values(values, expected))
    changed_outside_domain[path[-1]] = 99

    exact = infer_path_cycle_permutations(
        before,
        exact_after,
        tuple(sorted(path)),
        controller=(1, 2),
    )
    assert len(exact) == 1
    assert set(exact[0].slots) == set(subpath)
    assert (
        infer_path_cycle_permutations(
            before,
            _paint(changed_outside_domain),
            tuple(sorted(path)),
            controller=(1, 2),
        )
        == ()
    )

    ui_changed = [list(row) for row in exact_after]
    ui_changed[0][0] = 91
    projected = infer_path_cycle_permutations(
        before,
        _freeze(ui_changed),
        tuple(sorted(path)),
        controller=(1, 2),
    )
    assert tuple(
        (item.slots, item.successor) for item in projected
    ) == tuple((item.slots, item.successor) for item in exact)


def test_path_cycle_inference_enforces_slot_and_candidate_bounds() -> None:
    path = ((2, 2), (5, 2), (8, 2), (8, 5), (8, 8), (5, 8))
    values = {point: 20 + index for index, point in enumerate(path)}
    expected = _cycle_generator(
        path,
        controller=(1, 2),
        axis="path",
        pitch=3,
        segment_count=1,
    )
    before = _paint(values)
    after = _paint(_apply_values(values, expected))

    assert (
        infer_path_cycle_permutations(
            before,
            after,
            (*tuple(sorted(path)), path[0]),
            controller=(1, 2),
        )
        == ()
    )
    assert (
        infer_path_cycle_permutations(
            before,
            after,
            tuple(sorted(path)),
            controller=(1, 2),
            bounds=PermutationBounds(max_slots=len(path) - 1),
        )
        == ()
    )
    assert (
        infer_path_cycle_permutations(
            before,
            after,
            tuple(sorted(path)),
            controller=(1, 2),
            bounds=PermutationBounds(max_cycle_orderings=0),
        )
        == ()
    )
    assert (
        infer_path_cycle_permutations(
            before,
            after,
            (*tuple(sorted(path[:-1])), (30, 2)),
            controller=(1, 2),
        )
        == ()
    )


@pytest.mark.parametrize("transform_index", range(8))
def test_path_cycle_inference_is_d4_translation_and_color_equivariant(
    transform_index: int,
) -> None:
    path = ((0, 0), (3, 0), (6, 0), (6, 3), (6, 6), (3, 6), (3, 9))
    controller = (-3, 0)

    def raw_transform(point: Point) -> Point:
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

    raw_points = tuple(raw_transform(point) for point in (*path, controller))
    shift_x = 4 - min(point[0] for point in raw_points)
    shift_y = 4 - min(point[1] for point in raw_points)

    def transform(point: Point) -> Point:
        raw_x, raw_y = raw_transform(point)
        return raw_x + shift_x, raw_y + shift_y

    transformed_path = tuple(transform(point) for point in path)
    transformed_controller = transform(controller)
    values = {
        point: 101 + index * 7 for index, point in enumerate(transformed_path)
    }
    expected = _cycle_generator(
        transformed_path,
        controller=transformed_controller,
        axis="path",
        pitch=3,
        segment_count=1,
    )

    candidates = infer_path_cycle_permutations(
        _paint(values),
        _paint(_apply_values(values, expected)),
        tuple(sorted(transformed_path)),
        transformed_controller,
    )

    assert len(candidates) == 1
    assert candidates[0].slots == expected.slots
    assert candidates[0].successor == expected.successor
    assert candidates[0].axis == "path"


@pytest.mark.parametrize("transform_index", range(8))
def test_polar_product_factorization_and_controller_roles_are_d4_equivariant(
    transform_index: int,
) -> None:
    points, anchors = _polar_fixture(scale=2)
    controller_shape = ((0, 0), (0, 1), (0, 2), (1, 0))

    def raw_transform(point: Point) -> Point:
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

    transformed = tuple(raw_transform(point) for point in points)
    shift_x = 7 - min(point[0] for point in transformed)
    shift_y = 9 - min(point[1] for point in transformed)

    def transform(point: Point) -> Point:
        x, y = raw_transform(point)
        return x + shift_x, y + shift_y

    transformed_points = tuple(transform(point) for point in points)
    transformed_anchors = tuple(transform(point) for point in anchors)
    domain = infer_disjoint_polar_product(
        transformed_points,
        transformed_anchors,
    )

    assert domain is not None
    assert len(domain.modules) == 3
    assert domain.factor_shape == (8, 2)
    assert {module.pitch for module in domain.modules} == {4}
    assert {item.anchor for item in domain.interfaces} == set(transformed_anchors)

    source_hub = (12 * 2, 12 * 2)
    source_controller = (source_hub[0], source_hub[1] + 3 * 4)
    transformed_shape = tuple(raw_transform(point) for point in controller_shape)
    local = ground_polar_controller(
        transform(source_controller),
        transformed_shape,
        domain,
    )
    assert local is not None
    assert local.relation == "parallel"
    assert canonical_dihedral_shape(transformed_shape) == (
        canonical_dihedral_shape(controller_shape)
    )


def test_factored_effects_are_exact_and_plan_without_global_cross_product() -> None:
    points, anchors = _polar_fixture()
    domain = infer_disjoint_polar_product(points, anchors)
    assert domain is not None
    values = {point: 100 + index for index, point in enumerate(domain.all_slots)}
    width = max(point[0] for point in points) + 4
    height = max(point[1] for point in points) + 4

    angular = FactoredOrbitGenerator.create_local(
        factor_shape=domain.factor_shape,
        delta=(1, 0),
        controller=(0, 0),
    )
    radial = FactoredOrbitGenerator.create_local(
        factor_shape=domain.factor_shape,
        delta=(0, 1),
        controller=(0, 1),
    )
    angular_after = _apply_factored_effect(values, domain, angular, 0)
    radial_after = _apply_factored_effect(values, domain, radial, 1)
    angular_evidence = infer_factored_orbit_generators(
        _paint(values, width=width, height=height),
        _paint(angular_after, width=width, height=height),
        domain,
        0,
        (0, 0),
    )
    radial_evidence = infer_factored_orbit_generators(
        _paint(values, width=width, height=height),
        _paint(radial_after, width=width, height=height),
        domain,
        1,
        (0, 1),
    )
    assert len(angular_evidence) == 1
    assert angular_evidence[0].delta == (1, 0)
    assert len(radial_evidence) == 1
    assert radial_evidence[0].delta == (0, 1)

    interface = FactoredOrbitGenerator.create_interface(
        factor_shape=domain.factor_shape,
        interface_count=len(domain.interfaces),
        controller=(0, 2),
    )
    interface_after = _apply_factored_effect(values, domain, interface, None)
    interface_evidence = infer_factored_interface_generator(
        _paint(values, width=width, height=height),
        _paint(interface_after, width=width, height=height),
        domain,
        (0, 2),
    )
    assert interface_evidence is not None

    generators: tuple[FactoredOrbitGenerator, ...] = ()
    for evidence in (
        angular_evidence[0],
        FactoredOrbitGenerator.create_local(
            factor_shape=domain.factor_shape,
            delta=(1, 0),
            controller=(1, 0),
        ),
        radial_evidence[0],
        FactoredOrbitGenerator.create_local(
            factor_shape=domain.factor_shape,
            delta=(0, 1),
            controller=(1, 1),
        ),
        interface_evidence,
        FactoredOrbitGenerator.create_interface(
            factor_shape=domain.factor_shape,
            interface_count=len(domain.interfaces),
            controller=(0, 2),
        ),
    ):
        generators = merge_factored_evidence(generators, evidence)

    marker_targets: list[MarkerTarget] = []
    planned_values = dict(values)
    for index, edge in enumerate(domain.interfaces):
        marker_color = 900 + index
        marker_targets.append(MarkerTarget(edge.anchor, marker_color))
        planned_values[edge.anchor] = 700 + index
        source = domain.modules[edge.module_index].point((index + 2, 1))
        planned_values[source] = marker_color
    frame = _paint(planned_values, width=width, height=height)
    plan = plan_factored_orbit_transport(
        frame,
        tuple(marker_targets),
        domain,
        generators,
    )

    assert plan is not None
    assert plan.explored_states <= 3 * 16
    assert plan.steps[-1].module_index is None
    simulated = dict(planned_values)
    by_id = {generator.effect_id: generator for generator in generators}
    for step in plan.steps:
        simulated = _apply_factored_effect(
            simulated,
            domain,
            by_id[step.effect_id],
            step.module_index,
        )
    assert all(simulated[target.point] == target.color for target in marker_targets)


def test_polar_product_falsifiers_abstain_on_incomplete_or_ambiguous_structure() -> None:
    points, anchors = _polar_fixture()
    module_point = next(point for point in points if point not in set(anchors))

    assert infer_disjoint_polar_product(
        tuple(point for point in points if point != module_point),
        anchors,
    ) is None
    assert infer_disjoint_polar_product(
        points,
        anchors,
        bounds=PermutationBounds(max_factor_directions=7),
    ) is None

    domain = infer_disjoint_polar_product(points, anchors)
    assert domain is not None
    module = domain.modules[0]
    assert ground_polar_controller(
        (module.hub[0], module.hub[1] + 3 * module.pitch),
        ((0, 0), (0, 1), (1, 0), (1, 1)),
        domain,
    ) is None

    values = {point: 100 + index for index, point in enumerate(domain.all_slots)}
    generator = FactoredOrbitGenerator.create_local(
        factor_shape=domain.factor_shape,
        delta=(1, 0),
        controller=(0, 0),
    )
    changed = _apply_factored_effect(values, domain, generator, 0)
    changed[domain.modules[1].slots[0]] += 1
    width = max(point[0] for point in points) + 4
    height = max(point[1] for point in points) + 4
    assert infer_factored_orbit_generators(
        _paint(values, width=width, height=height),
        _paint(changed, width=width, height=height),
        domain,
        0,
        (0, 0),
    ) == ()


def test_interface_requires_every_edge_to_be_visibly_discriminated() -> None:
    points, anchors = _polar_fixture()
    domain = infer_disjoint_polar_product(points, anchors)
    assert domain is not None
    values = {point: 100 + index for index, point in enumerate(domain.all_slots)}
    for interface in domain.interfaces[1:]:
        values[interface.outlet] = values[interface.anchor]
    after = dict(values)
    changed = domain.interfaces[0]
    after[changed.anchor], after[changed.outlet] = (
        values[changed.outlet],
        values[changed.anchor],
    )
    width = max(point[0] for point in points) + 4
    height = max(point[1] for point in points) + 4

    assert (
        infer_factored_interface_generator(
            _paint(values, width=width, height=height),
            _paint(after, width=width, height=height),
            domain,
            (0, 0),
        )
        is None
    )


def test_factorization_search_exhaustion_fails_closed() -> None:
    points, anchors = _polar_fixture()

    inference = infer_disjoint_polar_product_diagnostic(
        points,
        anchors,
        bounds=PermutationBounds(max_factorization_search_states=1),
    )

    assert inference.domain is None
    assert inference.explored_states == 1
    assert inference.search_exhausted


@pytest.mark.parametrize("transform_index", range(8))
def test_alternate_rank_factored_effect_is_d4_and_recolor_equivariant(
    transform_index: int,
) -> None:
    points, anchors = _polar_fixture(ranks=3)

    def raw_transform(point: Point) -> Point:
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

    raw_points = tuple(raw_transform(point) for point in points)
    shift_x = 4 - min(point[0] for point in raw_points)
    shift_y = 4 - min(point[1] for point in raw_points)

    def transform(point: Point) -> Point:
        x, y = raw_transform(point)
        return x + shift_x, y + shift_y

    transformed_points = tuple(transform(point) for point in points)
    transformed_anchors = tuple(transform(point) for point in anchors)
    domain = infer_disjoint_polar_product(
        transformed_points,
        transformed_anchors,
    )
    assert domain is not None
    assert domain.factor_shape == (8, 3)
    generator = FactoredOrbitGenerator.create_local(
        factor_shape=domain.factor_shape,
        delta=(1, 1),
        controller=(0, 0),
    )
    values = {
        point: 100 + index for index, point in enumerate(domain.all_slots)
    }
    changed = _apply_factored_effect(values, domain, generator, 0)
    width = max(point[0] for point in transformed_points) + 4
    height = max(point[1] for point in transformed_points) + 4

    inferred = infer_factored_orbit_generators(
        _paint(values, width=width, height=height),
        _paint(changed, width=width, height=height),
        domain,
        0,
        (0, 0),
    )
    recolored_values = {point: color * 7 + 3 for point, color in values.items()}
    recolored_changed = _apply_factored_effect(
        recolored_values,
        domain,
        generator,
        0,
    )
    recolored = infer_factored_orbit_generators(
        _paint(recolored_values, width=width, height=height),
        _paint(recolored_changed, width=width, height=height),
        domain,
        0,
        (0, 0),
    )

    assert len(inferred) == 1
    assert inferred[0].delta == (1, 1)
    assert len(recolored) == 1
    assert recolored[0].delta == inferred[0].delta
