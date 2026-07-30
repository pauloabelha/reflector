from __future__ import annotations

from reflector.core.exploration import (
    ActionToken,
    CyclicAlignmentScheme,
    EpistemicExplorer,
)
from reflector.core.perception import SceneTracker
from reflector.core.permutation_transport import (
    PermutationBounds,
    ground_polar_controller,
)
from reflector.core.symbolic import Observation, Scene

type Point = tuple[int, int]
type Frame = tuple[tuple[int, ...], ...]

HUBS = ((15, 15), (45, 15), (30, 45))
PITCH = 3
RANKS = 2
RAYS = (
    (-1, -1),
    (0, -1),
    (1, -1),
    (1, 0),
    (1, 1),
    (0, 1),
    (-1, 1),
    (-1, 0),
)
ANCHORS = ((24, 24), (36, 24), (30, 36))
OUTLETS = ((21, 21), (39, 21), (30, 39))
VERTICAL_CONTROLLER_SHAPE = (
    (0, 0),
    (0, 1),
    (0, 2),
    (0, 3),
    (1, 0),
    (1, 1),
    (1, 2),
    (1, 3),
    (2, 1),
    (2, 2),
)
HORIZONTAL_CONTROLLER_SHAPE = (
    (0, 1),
    (0, 2),
    (1, 0),
    (1, 1),
    (1, 2),
    (2, 0),
    (2, 1),
    (2, 2),
    (3, 1),
    (3, 2),
)
PARALLEL_CONTROLLERS = ((15, 24), (45, 24), (30, 54))
PERPENDICULAR_CONTROLLERS = ((24, 15), (54, 15), (39, 45))
INTERFACE_CONTROLLER = (55, 54)


def _paint_shape(
    pixels: list[list[int]],
    origin: Point,
    shape: tuple[Point, ...],
    color: int,
) -> None:
    for local_x, local_y in shape:
        pixels[origin[1] + local_y][origin[0] + local_x] = color


def _paint_at_centroid(
    pixels: list[list[int]],
    centroid: Point,
    shape: tuple[Point, ...],
    color: int,
) -> None:
    _paint_shape(
        pixels,
        (
            centroid[0] - sum(point[0] for point in shape) // len(shape),
            centroid[1] - sum(point[1] for point in shape) // len(shape),
        ),
        shape,
        color,
    )


def _initial_frame() -> Frame:
    pixels = [[0 for _x in range(64)] for _y in range(64)]
    token_points = tuple(
        (
            hub[0] + ray[0] * PITCH * rank,
            hub[1] + ray[1] * PITCH * rank,
        )
        for hub in HUBS
        for ray in RAYS
        for rank in range(1, RANKS + 1)
    )
    values = {
        point: 20 + index for index, point in enumerate(token_points)
    }
    marker_colors = (201, 202, 203)
    for outlet, marker_color in zip(OUTLETS, marker_colors, strict=True):
        values[outlet] = marker_color
    for index, anchor in enumerate(ANCHORS):
        values[anchor] = 180 + index
    for point, color in values.items():
        _paint_shape(
            pixels,
            point,
            ((0, 0), (0, 1), (1, 0), (1, 1)),
            color,
        )
    for anchor, marker_color in zip(ANCHORS, marker_colors, strict=True):
        for point in (
            (anchor[0] - 1, anchor[1] - 1),
            (anchor[0] + 2, anchor[1] - 1),
            (anchor[0] - 1, anchor[1] + 2),
            (anchor[0] + 2, anchor[1] + 2),
        ):
            pixels[point[1]][point[0]] = marker_color
    for controller in (*PARALLEL_CONTROLLERS, *PERPENDICULAR_CONTROLLERS):
        _paint_at_centroid(
            pixels,
            controller,
            VERTICAL_CONTROLLER_SHAPE,
            240,
        )
    _paint_at_centroid(
        pixels,
        INTERFACE_CONTROLLER,
        HORIZONTAL_CONTROLLER_SHAPE,
        240,
    )
    return tuple(tuple(row) for row in pixels)


def _observation(frame: Frame) -> Observation:
    return Observation.create(
        state="NOT_FINISHED",
        available_actions=(0, 1, 2, 3, 4, 5, 6),
        frame=frame,
        levels_completed=0,
    )


def _with_controller(
    frame: Frame,
    centroid: Point,
    shape: tuple[Point, ...],
) -> Frame:
    output = [list(row) for row in frame]
    _paint_at_centroid(output, centroid, shape, 240)
    return tuple(tuple(row) for row in output)


def _controller_tokens(points: tuple[Point, ...]) -> tuple[ActionToken, ...]:
    return tuple(
        ActionToken(6, (("x", x), ("y", y)))
        for x, y in points
    )


def _apply_selected_effect(
    explorer: EpistemicExplorer,
    frame: Frame,
    scene: Scene,
    token: ActionToken,
) -> Frame:
    represented = explorer._factored_token_domain(
        frame,
        bounds=explorer.segmented_permutation_bounds,
    )
    assert represented is not None
    _anchors, _positions, domain = represented
    grounding = explorer._grounding(token, scene)
    assert grounding.centroid is not None
    local = ground_polar_controller(
        grounding.centroid,
        grounding.role.shape,
        domain,
    )
    destinations = {point: point for point in domain.all_slots}
    if local is not None:
        delta = (7, 0) if local.relation == "parallel" else (0, 1)
        module = domain.modules[local.module_index]
        for point in module.slots:
            direction, rank = module.coordinate(point)
            destinations[point] = module.point(
                (
                    (direction + delta[0]) % domain.factor_shape[0],
                    (rank + delta[1]) % domain.factor_shape[1],
                )
            )
    else:
        assert grounding.centroid == INTERFACE_CONTROLLER
        for interface in domain.interfaces:
            destinations[interface.anchor] = interface.outlet
            destinations[interface.outlet] = interface.anchor

    source_colors = {
        point: frame[point[1]][point[0]] for point in domain.all_slots
    }
    objects = {
        item.centroid: item for item in explorer._frame_objects(frame)
    }
    output = [list(row) for row in frame]
    for source, destination in destinations.items():
        item = objects[destination]
        min_x, min_y, _max_x, _max_y = item.bbox
        for local_x, local_y in item.shape:
            output[min_y + local_y][min_x + local_x] = source_colors[source]
    return tuple(tuple(row) for row in output)


def test_runtime_confirms_repeated_factor_roles_and_solves_with_interface_commit() -> None:
    explorer = EpistemicExplorer(
        cyclic_sequence_alignment=True,
        segmented_permutation_transport=True,
        factored_orbit_transport=True,
    )
    explorer.cyclic_alignment_scheme = CyclicAlignmentScheme(
        scheme_id="synthetic-factored-marker-goal",
        target_relation="anchor-token-matches-markers",
        controller_side="structural",
        shift_direction=1,
        evidence=("synthetic-progress",),
    )
    observation = _observation(_initial_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer.observe(observation, scene)

    diagnostics: list[str] = []
    for _step in range(30):
        choice = explorer.select(
            observation,
            scene,
            observation.available_actions,
        )
        diagnostics.append(explorer.factored_orbit_diagnostic)
        assert choice.token.action_id == 6
        next_frame = _apply_selected_effect(
            explorer,
            observation.frame,
            scene,
            choice.token,
        )
        observation = _observation(next_frame)
        scene, _events = SceneTracker().perceive(observation)
        explorer.observe(observation, scene)
        anchors = explorer._marked_anchors(observation.frame)
        if explorer._anchors_satisfied(observation.frame, anchors):
            break

    assert explorer._anchors_satisfied(
        observation.frame,
        explorer._marked_anchors(observation.frame),
    )
    assert explorer.factored_orbit_confirmations == 3
    assert explorer.factored_orbit_conflicts == 0
    assert explorer.factored_orbit_module_count == 3
    assert explorer.factored_orbit_factor_shape == (8, 2)
    assert len(explorer.factored_orbit_generators) == 3
    assert "confirming-provisional-effect" in diagnostics
    assert "planned-confirmed-generator" in diagnostics
    assert len(diagnostics) <= 30


def test_factored_transport_is_exactly_off_by_default() -> None:
    frame = _initial_frame()
    observation = _observation(frame)
    scene, _events = SceneTracker().perceive(observation)
    default = EpistemicExplorer()
    explicit_off = EpistemicExplorer(factored_orbit_transport=False)
    default.observe(observation, scene)
    explicit_off.observe(observation, scene)

    assert default.select(
        observation,
        scene,
        observation.available_actions,
    ) == explicit_off.select(
        observation,
        scene,
        observation.available_actions,
    )
    assert default.to_dict() == explicit_off.to_dict()


def test_duplicate_local_controller_slot_is_rejected_as_ambiguous() -> None:
    duplicate = (15, 6)
    frame = _with_controller(
        _initial_frame(),
        duplicate,
        VERTICAL_CONTROLLER_SHAPE,
    )
    observation = _observation(frame)
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        cyclic_sequence_alignment=True,
        segmented_permutation_transport=True,
        factored_orbit_transport=True,
    )
    represented = explorer._factored_token_domain(
        frame,
        bounds=explorer.segmented_permutation_bounds,
    )
    assert represented is not None
    candidates = explorer._factored_controller_candidates(
        scene,
        _controller_tokens(
            (
                *PARALLEL_CONTROLLERS,
                *PERPENDICULAR_CONTROLLERS,
                INTERFACE_CONTROLLER,
                duplicate,
            )
        ),
        represented[2],
    )

    represented_points = {candidate.controller for candidate in candidates}
    assert duplicate not in represented_points
    assert represented_points.isdisjoint(PARALLEL_CONTROLLERS)
    assert explorer.factored_orbit_ambiguous_controller_slots == 1


def test_inert_interface_distractor_cannot_become_an_execution_binding() -> None:
    distractor = (5, 54)
    frame = _with_controller(
        _initial_frame(),
        distractor,
        HORIZONTAL_CONTROLLER_SHAPE,
    )
    observation = _observation(frame)
    scene, _events = SceneTracker().perceive(observation)
    explorer = EpistemicExplorer(
        cyclic_sequence_alignment=True,
        segmented_permutation_transport=True,
        factored_orbit_transport=True,
    )
    represented = explorer._factored_token_domain(
        frame,
        bounds=explorer.segmented_permutation_bounds,
    )
    assert represented is not None
    candidates = explorer._factored_controller_candidates(
        scene,
        _controller_tokens(
            (
                *PARALLEL_CONTROLLERS,
                *PERPENDICULAR_CONTROLLERS,
                INTERFACE_CONTROLLER,
                distractor,
            )
        ),
        represented[2],
    )

    assert candidates
    assert all(candidate.module_index is not None for candidate in candidates)
    assert distractor not in explorer.factored_orbit_unique_bindings.values()
    assert (
        INTERFACE_CONTROLLER
        not in explorer.factored_orbit_unique_bindings.values()
    )
    assert explorer.factored_orbit_ambiguous_controller_slots == 1

    explorer.cyclic_alignment_scheme = CyclicAlignmentScheme(
        scheme_id="synthetic-factored-marker-goal",
        target_relation="anchor-token-matches-markers",
        controller_side="structural",
        shift_direction=1,
        evidence=("synthetic-progress",),
    )
    explorer.observe(observation, scene)
    planned_distractor = False
    for _step in range(30):
        choice = explorer.select(
            observation,
            scene,
            observation.available_actions,
        )
        data = dict(choice.token.data)
        point = (data.get("x"), data.get("y"))
        planned_distractor = planned_distractor or (
            point == distractor
            and explorer.factored_orbit_diagnostic
            == "planned-confirmed-generator"
        )
        if (
            choice.reason.endswith("factored-orbit-transport")
            and point != distractor
        ):
            next_frame = _apply_selected_effect(
                explorer,
                observation.frame,
                scene,
                choice.token,
            )
        else:
            next_frame = observation.frame
        observation = _observation(next_frame)
        scene, _events = SceneTracker().perceive(observation)
        explorer.observe(observation, scene)

    assert not planned_distractor
    assert explorer.factored_orbit_conflicts == 0


def test_factored_level_reset_clears_authority_but_retains_total_evidence() -> None:
    explorer = EpistemicExplorer(
        cyclic_sequence_alignment=True,
        segmented_permutation_transport=True,
        factored_orbit_transport=True,
    )
    explorer.cyclic_alignment_scheme = CyclicAlignmentScheme(
        scheme_id="synthetic-factored-marker-goal",
        target_relation="anchor-token-matches-markers",
        controller_side="structural",
        shift_direction=1,
        evidence=("synthetic-progress",),
    )
    observation = _observation(_initial_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer.observe(observation, scene)
    choice = explorer.select(
        observation,
        scene,
        observation.available_actions,
    )
    changed = _apply_selected_effect(
        explorer,
        observation.frame,
        scene,
        choice.token,
    )
    changed_observation = _observation(changed)
    changed_scene, _events = SceneTracker().perceive(changed_observation)
    explorer.observe(changed_observation, changed_scene)
    assert explorer.factored_orbit_proposals
    assert explorer.factored_orbit_unique_bindings
    assert explorer.factored_orbit_total_observations == 1

    progressed = Observation.create(
        state="NOT_FINISHED",
        available_actions=(0, 1, 2, 3, 4, 5, 6),
        frame=changed,
        levels_completed=1,
    )
    progressed_scene, _events = SceneTracker().perceive(progressed)
    explorer.observe(progressed, progressed_scene)

    assert explorer.factored_orbit_proposals == {}
    assert explorer.factored_orbit_generators == ()
    assert explorer.factored_orbit_controller_effects == {}
    assert explorer.factored_orbit_unique_bindings == {}
    assert explorer.factored_orbit_confirmations == 0
    assert explorer.factored_orbit_total_observations == 1
    assert explorer.factored_orbit_diagnostic == "not-attempted"


def test_factorization_budget_exhaustion_is_traced_and_sticky_per_level() -> None:
    explorer = EpistemicExplorer(
        cyclic_sequence_alignment=True,
        segmented_permutation_transport=True,
        factored_orbit_transport=True,
        segmented_permutation_bounds=PermutationBounds(
            max_factorization_search_states=1
        ),
    )
    explorer.cyclic_alignment_scheme = CyclicAlignmentScheme(
        scheme_id="synthetic-factored-marker-goal",
        target_relation="anchor-token-matches-markers",
        controller_side="structural",
        shift_direction=1,
        evidence=("synthetic-progress",),
    )
    observation = _observation(_initial_frame())
    scene, _events = SceneTracker().perceive(observation)
    explorer.observe(observation, scene)
    explorer.select(observation, scene, observation.available_actions)

    telemetry = explorer.to_dict()
    assert explorer.factored_orbit_factorization_search_exhausted
    assert explorer.factored_orbit_factorization_states == 1
    assert (
        explorer.factored_orbit_diagnostic
        == "factorization-search-bound-exceeded"
    )
    assert telemetry["factored_orbit_factorization_search_exhausted"] == 1
    assert telemetry["factored_orbit_factorization_states"] == 1
