from __future__ import annotations

from reflector.core.permutation_transport import (
    Frame,
    MarkerTarget,
    PermutationBounds,
    PermutationGenerator,
    PermutationSystem,
    Point,
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
