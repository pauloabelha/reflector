from __future__ import annotations

import pytest

from reflector.core.permutation_transport import (
    Frame,
    MarkerTarget,
    PermutationBounds,
    PermutationGenerator,
    PermutationSystem,
    Point,
    infer_path_cycle_permutations,
    infer_segmented_permutations,
    merge_generator_evidence,
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
