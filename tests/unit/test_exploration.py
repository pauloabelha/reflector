from collections import Counter

import pytest

from reflector import MindConfig
from reflector.exploration import (
    STARTER_SCHEMA_SET,
    ActionRole,
    ActionToken,
    EpistemicExplorer,
    GroundedRole,
    RelationalScheme,
    RoleRelation,
)
from reflector.perception import SceneTracker
from reflector.symbolic import Observation


def _scene(observation: Observation):
    return SceneTracker().perceive(observation)[0]


def test_explorer_tries_each_simple_action_before_repeating() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0), (0, 9)),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer()
    explorer.observe(observation, scene)

    first = explorer.select(observation, scene, (1, 2))
    explorer.observe(observation, scene)
    second = explorer.select(observation, scene, (1, 2))
    explorer.observe(observation, scene)
    third = explorer.select(observation, scene, (1, 2))

    assert first.token.action_id == 1
    assert second.token.action_id == 2
    assert third.token.action_id == 1
    assert "least-repeated" in third.reason


def test_explorer_generates_distinct_legal_object_clicks() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0, 0),
            (0, 2, 2, 0, 3, 0),
            (0, 2, 2, 0, 0, 0),
            (0, 0, 0, 0, 0, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer()
    explorer.observe(observation, scene)
    choices = []
    for _ in range(3):
        choice = explorer.select(observation, scene, (6,))
        choices.append(choice.token)
        explorer.observe(observation, scene)

    assert all(token.action_id == 6 for token in choices)
    assert len({token.data for token in choices}) == 3
    assert choices[0].data == (("x", 4), ("y", 1))
    assert choices[1].data == (("x", 1), ("y", 1))


def test_explorer_navigates_known_edges_to_an_untried_frontier() -> None:
    left = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1,),
        frame=((1, 0),),
    )
    right = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 1),),
    )
    left_scene = _scene(left)
    right_scene = _scene(right)
    explorer = EpistemicExplorer()
    explorer.observe(left, left_scene)
    assert explorer.select(left, left_scene, (1,)).token.action_id == 1
    explorer.observe(right, right_scene)
    assert explorer.select(right, right_scene, (1, 2)).token.action_id == 2
    explorer.observe(left, left_scene)

    navigation = explorer.select(left, left_scene, (1,))

    assert navigation.token.action_id == 1
    assert "navigate-known-state-graph" in navigation.reason


def test_explorer_balances_interventions_across_novel_states() -> None:
    first = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((1, 0),),
    )
    second = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 1),),
    )
    first_scene = _scene(first)
    second_scene = _scene(second)
    explorer = EpistemicExplorer()
    explorer.observe(first, first_scene)

    action_one = explorer.select(first, first_scene, (1, 2))
    explorer.observe(second, second_scene)
    action_two = explorer.select(second, second_scene, (1, 2))

    assert action_one.token.action_id == 1
    assert action_two.token.action_id == 2


def test_hierarchical_fairness_prevents_click_coordinates_crowding_actions() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 6),
        frame=(
            (1, 0, 2, 0, 3),
            (0, 4, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(hierarchical_action_fairness=True)
    explorer.observe(observation, scene)

    choices = []
    for _ in range(6):
        choices.append(explorer.select(observation, scene, (1, 2, 6)).token.action_id)
        explorer.observe(observation, scene)

    assert choices == [1, 2, 6, 1, 2, 6]


def test_flat_exploration_preserves_coordinate_level_ablation() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 6),
        frame=(
            (1, 0, 2, 0, 3),
            (0, 4, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(hierarchical_action_fairness=False)
    explorer.observe(observation, scene)

    choices = []
    for _ in range(6):
        choices.append(explorer.select(observation, scene, (1, 2, 6)).token.action_id)
        explorer.observe(observation, scene)

    assert choices == [1, 2, 6, 6, 6, 6]


def test_boundary_nuisance_state_key_requires_action_independent_motion() -> None:
    def frame(position: int, *, interior: int = 0):
        rows = [[5] * 6 for _ in range(6)]
        rows[0][position] = 0
        rows[3][3] = interior
        return tuple(tuple(row) for row in rows)

    enabled = EpistemicExplorer(boundary_nuisance_state_key=True)
    positions = (5, 4, 3, 2, 1)
    for left, right, action_id in zip(
        positions,
        positions[1:],
        (1, 2, 3, 1),
    ):
        enabled._observe_boundary_nuisance(
            frame(left),
            frame(right),
            action_id,
        )

    assert enabled.boundary_nuisance_sides == {0}
    first = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3),
        frame=frame(1),
    )
    shifted = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3),
        frame=frame(0),
    )
    changed_interior = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3),
        frame=frame(0, interior=9),
    )

    assert enabled._state_key(first, _scene(first)) == enabled._state_key(
        shifted,
        _scene(shifted),
    )
    assert enabled._state_key(first, _scene(first)) != enabled._state_key(
        changed_interior,
        _scene(changed_interior),
    )

    one_action = EpistemicExplorer(boundary_nuisance_state_key=True)
    for left, right in zip(positions, positions[1:]):
        one_action._observe_boundary_nuisance(frame(left), frame(right), 1)
    assert one_action.boundary_nuisance_sides == set()

    inconsistent = EpistemicExplorer(boundary_nuisance_state_key=True)
    for left, right, action_id in zip(
        (5, 4, 3, 4, 3),
        (4, 3, 4, 3, 2),
        (1, 2, 3, 1, 2),
    ):
        inconsistent._observe_boundary_nuisance(
            frame(left),
            frame(right),
            action_id,
        )
    assert inconsistent.boundary_nuisance_sides == set()


def test_boundary_nuisance_state_key_accepts_fixed_endpoint_monotone_strip() -> None:
    def frame(length: int, *, color: int = 0):
        rows = [[5] * 16 for _ in range(8)]
        for index in range(16 - length, 16):
            rows[0][index] = color
        return tuple(tuple(row) for row in rows)

    enabled = EpistemicExplorer(boundary_nuisance_state_key=True)
    for left, right, action_id in zip(
        range(1, 5),
        range(2, 6),
        (1, 2, 3, 1),
    ):
        enabled._observe_boundary_nuisance(
            frame(left),
            frame(right),
            action_id,
        )

    assert enabled.boundary_nuisance_sides == {0}
    assert enabled.to_dict()["boundary_nuisance_evidence"] == 4

    one_action = EpistemicExplorer(boundary_nuisance_state_key=True)
    for left, right in zip(range(1, 5), range(2, 6)):
        one_action._observe_boundary_nuisance(
            frame(left),
            frame(right),
            1,
        )
    assert one_action.boundary_nuisance_sides == set()

    color_changed = EpistemicExplorer(boundary_nuisance_state_key=True)
    color_changed._observe_boundary_nuisance(frame(1), frame(2), 1)
    color_changed._observe_boundary_nuisance(frame(2), frame(3), 2)
    color_changed._observe_boundary_nuisance(
        frame(3),
        frame(4, color=9),
        3,
    )
    color_changed._observe_boundary_nuisance(
        frame(4, color=9),
        frame(5, color=9),
        1,
    )
    assert color_changed.boundary_nuisance_sides == set()


def test_boundary_nuisance_fairness_activates_only_after_evidence() -> None:
    explorer = EpistemicExplorer(
        hierarchical_action_fairness=True,
        failure_conditioned_fairness=True,
        boundary_nuisance_state_key=True,
        boundary_nuisance_fairness=True,
    )

    assert not explorer.uses_action_family_schema

    explorer.boundary_nuisance_sides.add(0)
    assert explorer.uses_action_family_schema

    explorer._reset_boundary_nuisance_state()
    assert not explorer.uses_action_family_schema

    with pytest.raises(ValueError, match="boundary-nuisance fairness"):
        MindConfig(enable_boundary_nuisance_fairness=True)


def test_paired_object_contact_plan_is_structural_and_action_equivariant() -> None:
    def frame(extra_pair_member: bool = False):
        rows = [[1] * 20 for _ in range(20)]
        for y in range(5, 15):
            for x in range(2, 18):
                rows[y][x] = 5
        for center_x in ((5, 14, 10) if extra_pair_member else (5, 14)):
            for y in range(9, 12):
                for x in range(center_x - 1, center_x + 2):
                    rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    explorer = EpistemicExplorer(paired_object_contact_planning=True)
    grounding = explorer._ground_paired_objects(frame())

    assert grounding is not None
    assert grounding.reflection_axis == "horizontal"
    assert grounding.anchors == ((5, 10), (14, 10))
    assert grounding.substrate_color == 5
    assert explorer._ground_paired_objects(frame(extra_pair_member=True)) is None

    explorer.paired_grounding = grounding
    explorer.paired_effects = {
        7: ((1, 0), (-1, 0)),
        2: ((0, -1), (0, -1)),
    }
    first = explorer._paired_contact_plan(
        frame(),
        grounding.anchors,
        frozenset({2, 7}),
    )
    assert first is not None
    assert first[0] == 7
    assert first[1] == 3

    explorer.paired_effects = {
        3: ((1, 0), (-1, 0)),
        6: ((0, -1), (0, -1)),
    }
    permuted = explorer._paired_contact_plan(
        frame(),
        grounding.anchors,
        frozenset({3, 6}),
    )
    assert permuted is not None
    assert permuted[0] == 3
    assert permuted[1] == first[1]


def test_paired_contact_merge_has_two_evidenced_continuations() -> None:
    def frame(merged_width: int = 0):
        rows = [[1] * 20 for _ in range(20)]
        for y in range(5, 15):
            for x in range(2, 18):
                rows[y][x] = 5
        if merged_width:
            for y in range(9, 12):
                for x in range(10 - merged_width // 2, 10 + merged_width // 2):
                    rows[y][x] = 10
        else:
            for center_x in (5, 14):
                for y in range(9, 12):
                    for x in range(center_x - 1, center_x + 2):
                        rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    explorer = EpistemicExplorer(paired_object_contact_planning=True)
    grounding = explorer._ground_paired_objects(frame())
    assert grounding is not None
    explorer.paired_grounding = grounding
    explorer.paired_contact_action = 7
    explorer.paired_pending = ("plan", 7, grounding.anchors)

    merged = frame(merged_width=6)
    explorer._observe_paired_object_contact(
        frame(),
        merged,
        progressed=False,
    )
    assert explorer.paired_latent_contact

    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(2, 7),
        frame=merged,
    )
    first = explorer._select_paired_object_contact(
        observation,
        (ActionToken(2), ActionToken(7)),
    )
    assert first == ActionToken(7)
    assert explorer.paired_contact_continuations == 1

    narrower = frame(merged_width=4)
    explorer._observe_paired_object_contact(
        merged,
        narrower,
        progressed=False,
    )
    second = explorer._select_paired_object_contact(
        Observation.create(
            state="NOT_FINISHED",
            available_actions=(2, 7),
            frame=narrower,
        ),
        (ActionToken(2), ActionToken(7)),
    )
    assert second == ActionToken(7)
    assert explorer.paired_contact_continuations == 2

    explorer._observe_paired_object_contact(
        narrower,
        narrower,
        progressed=False,
    )
    assert not explorer.paired_latent_contact
    assert explorer.paired_diagnostic == "contact-continuation-no-effect"


def test_paired_contextual_transition_requires_confirmation_and_is_equivariant() -> None:
    def frame(
        anchors: tuple[tuple[int, int], tuple[int, int]],
    ) -> tuple[tuple[int, ...], ...]:
        rows = [[1] * 20 for _ in range(20)]
        for y in range(2, 18):
            for x in range(2, 18):
                rows[y][x] = 5
        for center_x, center_y in anchors:
            for y in range(center_y - 1, center_y + 2):
                for x in range(center_x - 1, center_x + 2):
                    rows[y][x] = 10
        return tuple(tuple(row) for row in rows)

    def confirmed_plan(
        *,
        initial: tuple[tuple[int, int], tuple[int, int]],
        transported: tuple[tuple[int, int], tuple[int, int]],
        effect: tuple[tuple[int, int], tuple[int, int]],
        contextual_action: int,
        alternate_action: int,
    ) -> tuple[EpistemicExplorer, tuple[int, int]]:
        explorer = EpistemicExplorer(
            paired_object_contact_planning=True,
            paired_contextual_transitions=True,
        )
        grounding = explorer._ground_paired_objects(frame(initial))
        assert grounding is not None
        explorer.paired_grounding = grounding
        explorer.paired_effects = {
            contextual_action: effect,
            alternate_action: effect,
        }
        represented = frozenset({contextual_action, alternate_action})

        before = explorer._paired_contact_plan(
            frame(initial),
            initial,
            represented,
        )
        assert before is not None
        assert before[0] == contextual_action

        for expected_count in (1, 2):
            explorer.paired_pending = ("plan", contextual_action, initial)
            explorer._observe_paired_object_contact(
                frame(initial),
                frame(transported),
                progressed=False,
            )
            evidence = explorer.paired_contextual_evidence[
                (initial, contextual_action)
            ]
            assert evidence[transported] == expected_count
            if expected_count == 1:
                still_unconfirmed = explorer._paired_contact_plan(
                    frame(initial),
                    initial,
                    represented,
                )
                assert still_unconfirmed is not None
                assert still_unconfirmed[0] == contextual_action

        after = explorer._paired_contact_plan(
            frame(initial),
            initial,
            represented,
        )
        assert after is not None
        assert after[0] == alternate_action
        assert explorer.paired_contextual_confirmations == 1
        assert explorer.paired_contextual_planner_uses > 0
        return explorer, after

    horizontal, horizontal_plan = confirmed_plan(
        initial=((5, 10), (14, 10)),
        transported=((4, 10), (15, 10)),
        effect=((1, 0), (-1, 0)),
        contextual_action=7,
        alternate_action=9,
    )
    vertical, vertical_plan = confirmed_plan(
        initial=((10, 5), (10, 14)),
        transported=((10, 4), (10, 15)),
        effect=((0, 1), (0, -1)),
        contextual_action=3,
        alternate_action=8,
    )
    assert horizontal_plan[1] == vertical_plan[1]

    conflict = ((3, 10), (16, 10))
    horizontal.paired_pending = (
        "plan",
        7,
        ((5, 10), (14, 10)),
    )
    horizontal._observe_paired_object_contact(
        frame(((5, 10), (14, 10))),
        frame(conflict),
        progressed=False,
    )
    assert (((5, 10), (14, 10)), 7) in (
        horizontal.paired_contextual_quarantined
    )
    assert horizontal.paired_contextual_conflicts == 1

    with pytest.raises(ValueError, match="paired contextual transitions"):
        MindConfig(enable_paired_contextual_transitions=True)


def test_failure_conditioned_fairness_preserves_parent_then_accommodates() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 6),
        frame=(
            (1, 0, 2, 0, 3),
            (0, 4, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    before = EpistemicExplorer(
        hierarchical_action_fairness=True,
        failure_conditioned_fairness=True,
    )
    before.observe(observation, scene)
    parent_choices = []
    for _ in range(6):
        parent_choices.append(
            before.select(observation, scene, (1, 2, 6)).token.action_id
        )
        before.observe(observation, scene)

    after = EpistemicExplorer(
        hierarchical_action_fairness=True,
        failure_conditioned_fairness=True,
    )
    after.observe(observation, scene)
    after.level_failures = 2
    accommodated_choices = []
    for _ in range(6):
        accommodated_choices.append(
            after.select(observation, scene, (1, 2, 6)).token.action_id
        )
        after.observe(observation, scene)

    assert parent_choices == [1, 2, 6, 6, 6, 6]
    assert accommodated_choices == [1, 2, 6, 1, 2, 6]


def test_failure_conditioned_fairness_requires_parent_mechanism() -> None:
    with pytest.raises(
        ValueError,
        match="failure-conditioned fairness requires hierarchical fairness",
    ):
        MindConfig(enable_failure_conditioned_fairness=True)


def test_successful_level_compiles_and_replays_coordinate_free_roles() -> None:
    first_level = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0),
            (0, 1, 0, 0),
            (0, 0, 0, 0),
        ),
        levels_completed=0,
    )
    second_level = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0),
            (0, 0, 0, 0),
            (0, 0, 1, 0),
        ),
        levels_completed=1,
    )
    first_scene = _scene(first_level)
    second_scene = _scene(second_level)
    explorer = EpistemicExplorer(successful_role_replay=True)
    explorer.observe(first_level, first_scene)

    learned = explorer.select(first_level, first_scene, (6,))
    explorer.observe(second_level, second_scene)
    replayed = explorer.select(second_level, second_scene, (6,))

    assert learned.token.data == (("x", 1), ("y", 1))
    assert replayed.token.data == (("x", 2), ("y", 2))
    assert replayed.reason.endswith("replay-successful-action-role")
    assert explorer.to_dict()["successful_program_length"] == 1


def test_pragmatic_disequilibrium_suspends_composite_replay() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0), (0, 0)),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(successful_role_replay=True)
    explorer.observe(observation, scene)
    explorer.successful_program = (ActionRole(2),)

    choice = explorer.select(
        observation,
        scene,
        (1, 2),
        pragmatic_disequilibrium=True,
    )

    assert choice.token.action_id == 1
    assert choice.reason.endswith("untried-current-state")
    assert explorer.successful_program == (ActionRole(2),)


def test_starter_schemas_are_content_free_and_enter_operative_credit() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=((0, 0, 0), (0, 9, 0), (0, 0, 0)),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(starter_schemas=True)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 1), ("y", 1))
    assert explorer.last_scheme_components == (
        "scheme:starter:intervene-on-object",
        "scheme:starter:probe-action-family",
    )
    assert explorer.to_dict()["starter_schemas"] == len(STARTER_SCHEMA_SET)
    serialized = repr(STARTER_SCHEMA_SET)
    assert "game_id" not in serialized
    assert "coordinate" not in serialized
    assert all(item.complexity_cost > 0 for item in STARTER_SCHEMA_SET)


def test_starter_action_schema_probes_each_legal_family() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 6),
        frame=(
            (1, 0, 2, 0, 3),
            (0, 4, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(starter_schemas=True)
    explorer.observe(observation, scene)

    choices = []
    for _ in range(6):
        choices.append(
            explorer.select(
                observation,
                scene,
                (1, 2, 6),
            ).token.action_id
        )
        explorer.observe(observation, scene)

    assert choices == [1, 2, 6, 1, 2, 6]


def test_relational_modifier_grounds_on_recolored_translated_objects() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0),
            (0, 7, 0, 8, 0),
            (0, 0, 0, 0, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(
        starter_schemas=True,
        relational_scheme_binding=True,
    )
    explorer.observe(observation, scene)
    scheme = RelationalScheme(
        scheme_id="translated",
        base_id="carry",
        modifier_id="manner",
        operator="full-manner",
        action_slots=(6, 6),
        constraints=(
            RoleRelation(
                color="different",
                area="same",
                shape="same",
                horizontal="right",
                vertical="aligned",
            ),
        ),
        evidence=("carry", "manner"),
    )
    explorer.relational_schemes[scheme.scheme_id] = scheme

    first = explorer.select(
        observation,
        scene,
        (6,),
        pragmatic_disequilibrium=True,
    )
    responsive = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (9, 9, 9, 9, 0),
            (0, 7, 0, 8, 0),
            (0, 0, 0, 0, 0),
        ),
    )
    responsive_scene = _scene(responsive)
    explorer.observe(responsive, responsive_scene)
    second = explorer.select(
        responsive,
        responsive_scene,
        (6,),
        pragmatic_disequilibrium=True,
    )

    assert first.token.data == (("x", 1), ("y", 1))
    assert second.token.data == (("x", 3), ("y", 1))
    assert "relational-scheme-binding" in second.reason
    assert "scheme:starter:bind-manner-to-action" in (
        explorer.last_scheme_components
    )
    assert repr(scheme).count("7") == 0
    assert repr(scheme).count("8") == 0


def test_no_effect_falsifies_only_the_grounded_relational_scheme() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0),),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(relational_scheme_binding=True)
    explorer.observe(observation, scene)
    scheme = RelationalScheme(
        scheme_id="falsified",
        base_id="base",
        modifier_id="modifier",
        operator="full-manner",
        action_slots=(2,),
        constraints=(RoleRelation(),),
        evidence=("base", "modifier"),
    )
    explorer.relational_schemes[scheme.scheme_id] = scheme

    first = explorer.select(
        observation,
        scene,
        (1, 2),
        pragmatic_disequilibrium=True,
    )
    explorer.observe(observation, scene)
    second = explorer.select(
        observation,
        scene,
        (1, 2),
        pragmatic_disequilibrium=True,
    )

    assert first.token.action_id == 2
    assert "relational-scheme-binding" in first.reason
    assert second.token.action_id == 1
    assert "relational-scheme-binding" not in second.reason
    assert explorer.to_dict()["falsified_relational_schemes"] == 1
    assert scheme.base_id == "base"
    assert scheme.modifier_id == "modifier"


def test_relational_program_identity_ignores_color_permutation_and_translation() -> None:
    source = (
        GroundedRole(
            ActionRole(6, color=2, area=1, shape=((0, 0),)),
            (1, 1),
        ),
        GroundedRole(
            ActionRole(6, color=3, area=1, shape=((0, 0),)),
            (3, 1),
        ),
    )
    transformed = (
        GroundedRole(
            ActionRole(6, color=8, area=1, shape=((0, 0),)),
            (11, 21),
        ),
        GroundedRole(
            ActionRole(6, color=7, area=1, shape=((0, 0),)),
            (13, 21),
        ),
    )

    assert EpistemicExplorer._relational_program_id(
        source
    ) == EpistemicExplorer._relational_program_id(transformed)


def test_relational_binding_is_inactive_before_pragmatic_disequilibrium() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=((0, 0),),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(relational_scheme_binding=True)
    explorer.observe(observation, scene)
    explorer.relational_schemes["bound"] = RelationalScheme(
        scheme_id="bound",
        base_id="base",
        modifier_id="modifier",
        operator="full-manner",
        action_slots=(2,),
        constraints=(RoleRelation(),),
        evidence=("base", "modifier"),
    )

    choice = explorer.select(observation, scene, (1, 2))

    assert choice.token.action_id == 1
    assert choice.reason.endswith("untried-current-state")
    assert explorer.to_dict()["relational_scheme_trials"] == 0


def test_successful_schemes_become_inputs_to_bounded_variations() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2, 3),
        frame=((0, 0), (0, 9)),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(parameterized_scheme_variation=True)
    explorer.observe(observation, scene)
    explorer._learn_parameterized_variations(
        (ActionRole(1), ActionRole(2))
    )
    assert explorer.parameterized_schemes == {}

    explorer._learn_parameterized_variations(
        (ActionRole(3), ActionRole(2))
    )

    operators = {
        scheme.operator for scheme in explorer.parameterized_schemes.values()
    }
    assert {"prefix", "suffix", "interleave"}.issubset(operators)
    assert all(
        len(scheme.roles) <= 32
        and scheme.base_id
        and scheme.argument_id
        and len(scheme.evidence) == 2
        for scheme in explorer.parameterized_schemes.values()
    )

    choice = explorer.select(
        observation,
        scene,
        (1, 2, 3),
        pragmatic_disequilibrium=True,
        structure_scores={},
    )

    assert "parameterized-scheme-variation" in choice.reason
    assert explorer.last_scheme_components
    assert any(
        component.startswith("base:")
        for component in explorer.last_scheme_components
    )
    assert any(
        component.startswith("argument:")
        for component in explorer.last_scheme_components
    )
    assert explorer.to_dict()["parameterized_scheme_trials"] == 1

    explorer.observe(observation, scene)
    second = explorer.select(
        observation,
        scene,
        (1, 2, 3),
        pragmatic_disequilibrium=True,
        structure_scores={
            explorer.last_scheme_components[0]: -1
        },
    )
    assert second.token != choice.token


def test_multicolor_affordance_precedes_fragmented_color_objects() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0, 0, 0),
            (0, 2, 2, 3, 3, 0, 0),
            (0, 2, 4, 4, 3, 0, 0),
            (0, 0, 0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(multicolor_click_objects=True)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 2), ("y", 1))


def test_multicolor_affordance_is_an_exact_disabled_ablation() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0, 0, 0),
            (0, 2, 2, 3, 3, 0, 0),
            (0, 2, 4, 4, 3, 0, 0),
            (0, 0, 0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0, 5, 0),
        ),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(multicolor_click_objects=False)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 5), ("y", 4))


def test_click_object_ontology_accommodates_only_after_failure() -> None:
    active = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0, 0, 0),
            (0, 2, 2, 3, 3, 0, 0),
            (0, 2, 4, 4, 3, 0, 0),
            (0, 0, 0, 0, 0, 0, 0),
            (0, 0, 0, 0, 0, 5, 0),
        ),
    )
    failed = Observation.create(
        state="GAME_OVER",
        available_actions=(0,),
        frame=active.frame,
    )
    scene = _scene(active)
    explorer = EpistemicExplorer(click_object_accommodation=True)
    explorer.observe(active, scene)

    before = explorer.select(active, scene, (6,))
    explorer.observe(failed, _scene(failed))
    explorer.observe(active, scene)
    after = explorer.select(active, scene, (6,))

    assert before.token.data == (("x", 5), ("y", 4))
    assert after.token.data == (("x", 2), ("y", 1))
    assert explorer.to_dict()["perceptual_accommodations"] == 1
    assert explorer.to_dict()["attempts"] == 1


def test_productive_role_reuse_activates_only_after_repeated_failure() -> None:
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=(
            (0, 0, 0, 0, 0),
            (0, 2, 0, 3, 0),
            (0, 0, 0, 0, 0),
        ),
    )
    scene = _scene(observation)
    role = ActionRole(6, color=3, area=1, shape=((0, 0),))
    explorer = EpistemicExplorer(productive_role_reuse=True)
    explorer.observe(observation, scene)
    explorer.role_trials[role] = 1
    explorer.role_responses[role] = 1

    before = explorer.select(observation, scene, (6,))
    explorer.level_failures = 2
    explorer.level_interventions = explorer.min_productive_reuse_interventions
    after = explorer.select(observation, scene, (6,))

    assert before.token.data == (("x", 1), ("y", 1))
    assert after.token.data == (("x", 3), ("y", 1))
    assert after.reason.endswith("reuse-productive-action-role")


def test_local_relation_solver_induces_and_repairs_repeated_panel_rule() -> None:
    size = 64
    pixels = [[5 for _x in range(size)] for _y in range(size)]
    directions = (
        (-1, -1),
        (0, -1),
        (1, -1),
        (-1, 0),
        (1, 0),
        (-1, 1),
        (0, 1),
        (1, 1),
    )
    clues = (
        ((2, 0, 2, 0, 8, 2, 2, 0, 0), (9, 8, 9, 8, 9, 9, 8, 8)),
        ((2, 0, 2, 0, 8, 0, 2, 0, 2), (9, 8, 9, 8, 8, 9, 8, 9)),
        ((0, 2, 2, 0, 8, 0, 2, 2, 0), (9, 9, 9, 8, 8, 9, 9, 8)),
        ((0, 2, 2, 0, 8, 0, 0, 2, 2), (9, 9, 9, 9, 9, 9, 9, 9)),
    )
    origins = ((4, 2), (38, 2), (4, 36), (36, 36))
    block_size = 6
    step = 8
    subcell = block_size // 3
    for (origin_x, origin_y), (clue, colors) in zip(origins, clues):
        center_x = origin_x + step
        center_y = origin_y + step
        for (dx, dy), color in zip(directions, colors):
            block_x = center_x + dx * step
            block_y = center_y + dy * step
            for y in range(block_y, block_y + block_size):
                for x in range(block_x, block_x + block_size):
                    pixels[y][x] = color
        for clue_index, color in enumerate(clue):
            clue_x = center_x + clue_index % 3 * subcell
            clue_y = center_y + clue_index // 3 * subcell
            for y in range(clue_y, clue_y + subcell):
                for x in range(clue_x, clue_x + subcell):
                    pixels[y][x] = color

    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=tuple(tuple(row) for row in pixels),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(local_relation_solver=True)
    explorer.observe(observation, scene)

    choice = explorer.select(observation, scene, (6,))

    assert choice.token.data == (("x", 38), ("y", 38))
    assert choice.reason.endswith("repair-local-relation")

    transfer_pixels = [[5 for _x in range(size)] for _y in range(size)]
    transfer_clues = (
        (0, 2, 2, 0, 12, 0, 0, 2, 0),
        (0, 2, 0, 2, 12, 2, 0, 0, 2),
    )
    for center_y, clue in zip((22, 38), transfer_clues):
        center_x = 28
        for dx, dy in directions:
            block_x = center_x + dx * step
            block_y = center_y + dy * step
            for y in range(block_y, block_y + block_size):
                for x in range(block_x, block_x + block_size):
                    transfer_pixels[y][x] = 9
        for clue_index, color in enumerate(clue):
            clue_x = center_x + clue_index % 3 * subcell
            clue_y = center_y + clue_index // 3 * subcell
            for y in range(clue_y, clue_y + subcell):
                for x in range(clue_x, clue_x + subcell):
                    transfer_pixels[y][x] = color
    transfer = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=tuple(tuple(row) for row in transfer_pixels),
        levels_completed=1,
    )
    transfer_scene = _scene(transfer)
    explorer.observe(transfer, transfer_scene)
    expected_transfer = ActionToken(6, (("x", 22), ("y", 16)))
    explorer.global_attempts[expected_transfer] = 10

    transferred_choice = explorer.select(transfer, transfer_scene, (6,))

    assert transferred_choice.token == expected_transfer
    assert transferred_choice.reason.endswith("repair-local-relation")
    assert explorer.to_dict()["learned_local_relations"] == 2

    conservation_pixels = [[5 for _x in range(size)] for _y in range(size)]
    conservation_clue = (2, 2, 2, 2, 8, 2, 2, 2, 2)
    for origin_x, origin_y in origins[:3]:
        center_x = origin_x + step
        center_y = origin_y + step
        for dx, dy in directions:
            block_x = center_x + dx * step
            block_y = center_y + dy * step
            for y in range(block_y, block_y + block_size):
                for x in range(block_x, block_x + block_size):
                    conservation_pixels[y][x] = 8
        for clue_index, color in enumerate(conservation_clue):
            clue_x = center_x + clue_index % 3 * subcell
            clue_y = center_y + clue_index // 3 * subcell
            for y in range(clue_y, clue_y + subcell):
                for x in range(clue_x, clue_x + subcell):
                    conservation_pixels[y][x] = color
    conservation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=tuple(tuple(row) for row in conservation_pixels),
        levels_completed=2,
    )
    conservation_scene = _scene(conservation)

    conserved_candidates = explorer._local_relation_candidates(
        conservation,
        conservation_scene,
    )

    assert conserved_candidates
    assert explorer.learned_local_relation == {0: True, 2: False}

    portfolio = EpistemicExplorer(
        successful_role_replay=True,
        local_relation_solver=True,
        constraint_first_role_replay=True,
    )
    portfolio.learned_local_relation = dict(explorer.learned_local_relation)
    portfolio.observe(conservation, conservation_scene)
    repair = portfolio._local_relation_candidates(
        conservation,
        conservation_scene,
    )[0]
    represented = portfolio._tokens(conservation, conservation_scene, (6,))
    replay_token = next(
        token
        for token in represented
        if token.data != (("x", repair[0]), ("y", repair[1]))
    )
    portfolio.successful_program = (
        portfolio._role(replay_token, conservation_scene),
    )

    portfolio_choice = portfolio.select(
        conservation,
        conservation_scene,
        (6,),
    )

    assert portfolio_choice.token.data == (
        ("x", repair[0]),
        ("y", repair[1]),
    )
    assert portfolio_choice.reason.endswith(
        "constraint-first-repair-local-relation"
    )


def test_global_relation_solver_coordinates_overlapping_clue_constraints() -> None:
    width, height = 48, 32
    pixels = [[5 for _x in range(width)] for _y in range(height)]
    size = 6
    clue_origins = {(12, 12), (28, 12)}
    shared_origin = (20, 12)
    for origin_y in (4, 12, 20):
        for origin_x in (4, 12, 20, 28, 36):
            origin = (origin_x, origin_y)
            if origin in clue_origins:
                continue
            color = 9 if origin == shared_origin else 8
            for y in range(origin_y, origin_y + size):
                for x in range(origin_x, origin_x + size):
                    pixels[y][x] = color
    subcell = size // 3
    clue = (0, 0, 0, 0, 8, 0, 0, 0, 0)
    for origin_x, origin_y in clue_origins:
        for clue_index, color in enumerate(clue):
            start_x = origin_x + clue_index % 3 * subcell
            start_y = origin_y + clue_index // 3 * subcell
            for y in range(start_y, start_y + subcell):
                for x in range(start_x, start_x + subcell):
                    pixels[y][x] = color
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=tuple(tuple(row) for row in pixels),
    )
    scene = _scene(observation)
    explorer = EpistemicExplorer(
        local_relation_solver=True,
        global_relation_constraint_solver=True,
    )
    explorer.learned_local_relation = {0: True}

    candidates = explorer._local_relation_candidates(observation, scene)

    assert candidates == ((22, 14),)


def test_policy_explorer_is_an_exact_configuration_ablation() -> None:
    from reflector.mind import MindConfig
    from reflector.policy import SymbolicPolicy

    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(6,),
        frame=((0, 0, 0), (0, 9, 0), (0, 0, 0)),
    )
    enabled = SymbolicPolicy(MindConfig(enable_epistemic_state_graph=True))
    ablated = SymbolicPolicy(MindConfig(enable_epistemic_state_graph=False))

    enabled_decision = enabled.choose_action(observation)
    ablated_decision = ablated.choose_action(observation)

    assert enabled_decision.reason.startswith("epistemic-frontier:")
    assert ablated_decision.reason.startswith("schema-selection:")
    assert enabled_decision.action_id == ablated_decision.action_id == 6


def test_committed_trajectory_bfs_detours_around_evidenced_block() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {
        1: (1, 0),
        2: (0, 1),
        3: (-1, 0),
        4: (0, -1),
    }
    explorer.trajectory_contextual_blocks[((0, 0), 1)] = 1

    action = explorer._trajectory_bfs_action(
        (0, 0),
        (2, 0),
        represented=frozenset({1, 2, 3, 4}),
        frame_width=4,
        frame_height=4,
    )

    assert action == 2


def test_committed_trajectory_bfs_is_action_id_equivariant() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {
        4: (1, 0),
        1: (0, 1),
        2: (-1, 0),
        3: (0, -1),
    }
    explorer.trajectory_contextual_blocks[((0, 0), 4)] = 1

    action = explorer._trajectory_bfs_action(
        (0, 0),
        (2, 0),
        represented=frozenset({1, 2, 3, 4}),
        frame_width=4,
        frame_height=4,
    )

    assert action == 1


def test_committed_trajectory_bfs_honors_first_step_independence() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {
        1: (1, 0),
        2: (0, 1),
        3: (-1, 0),
        4: (0, -1),
    }

    action = explorer._trajectory_bfs_action(
        (0, 0),
        (2, 2),
        represented=frozenset({1, 2, 3, 4}),
        frame_width=4,
        frame_height=4,
        forbidden_first=frozenset({1, 3}),
    )

    assert action == 2


def _topology_fixture() -> tuple[tuple[int, ...], ...]:
    frame = [[0 for _x in range(15)] for _y in range(15)]
    for y in range(2, 13):
        for x in range(2, 13):
            frame[y][x] = 5
    for y in range(6, 9):
        for x in range(6, 9):
            frame[y][x] = 0
    for y in range(3, 5):
        for x in range(3, 5):
            frame[y][x] = 9
    frame[4][4] = 5
    frame[4][7] = 8
    for y in range(9, 11):
        for x in range(9, 11):
            frame[y][x] = 9
    frame[10][10] = 5
    return tuple(tuple(row) for row in frame)


def _topology_explorer(
    *,
    origin: tuple[int, int] = (3, 3),
    target: tuple[int, int] = (9, 9),
) -> EpistemicExplorer:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_origin = origin
    explorer.trajectory_current_anchor = origin
    explorer.trajectory_target_anchor = target
    explorer.trajectory_mover_signature = (
        8,
        3,
        3,
        (
            (0, 0),
            (0, 1),
            (0, 2),
            (1, 0),
            (1, 2),
            (2, 0),
            (2, 1),
            (2, 2),
        ),
    )
    explorer.trajectory_mover_color = 9
    explorer.trajectory_target_color = 9
    explorer.trajectory_effects = {
        1: (3, 0),
        2: (0, 3),
        3: (-3, 0),
        4: (0, -3),
    }
    return explorer


def test_committed_trajectory_topology_excludes_holes_and_marks_overlay() -> None:
    explorer = _topology_explorer()

    nodes, uncertain, support_color = explorer._trajectory_topology(
        _topology_fixture()
    )

    assert support_color == 5
    assert (6, 6) not in nodes
    assert (6, 3) in nodes
    assert (6, 3) in uncertain
    assert {(3, 3), (9, 9)} <= nodes
    assert len(nodes) <= 128


def test_committed_trajectory_topology_reflects_with_frame() -> None:
    frame = _topology_fixture()
    width = len(frame[0])
    reflected = tuple(tuple(reversed(row)) for row in frame)
    explorer = _topology_explorer()
    nodes, uncertain, _support = explorer._trajectory_topology(frame)
    reflected_explorer = _topology_explorer(
        origin=(width - 3 - 3, 3),
        target=(width - 9 - 3, 9),
    )
    reflected_nodes, reflected_uncertain, _reflected_support = (
        reflected_explorer._trajectory_topology(reflected)
    )

    def reflect_anchor(anchor: tuple[int, int]) -> tuple[int, int]:
        return (width - anchor[0] - 3, anchor[1])

    assert reflected_nodes == frozenset(map(reflect_anchor, nodes))
    assert reflected_uncertain == frozenset(
        map(reflect_anchor, uncertain)
    )


def test_committed_trajectory_refreshes_disconnected_uncertain_gate() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {
        7: (0, 1),
        3: (0, -1),
        9: (1, 0),
    }
    explorer.trajectory_effect_evidence.update({7: 2, 3: 2, 9: 2})
    explorer.trajectory_contextual_blocks[((0, 1), 7)] = 1

    action = explorer._trajectory_gate_refresh_action(
        (0, 1),
        represented=frozenset({3, 7, 9}),
        allowed_nodes=frozenset({(0, 0), (0, 1), (0, 2)}),
        uncertain_nodes=frozenset({(0, 2)}),
    )

    assert action == 3


def test_committed_trajectory_does_not_refresh_without_gate_evidence() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {1: (0, -1), 2: (0, 1)}

    action = explorer._trajectory_gate_refresh_action(
        (0, 1),
        represented=frozenset({1, 2}),
        allowed_nodes=frozenset({(0, 0), (0, 1), (0, 2)}),
        uncertain_nodes=frozenset({(0, 2)}),
    )

    assert action is None


def test_committed_trajectory_refresh_varies_least_used_action_role() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_effects = {1: (0, 1), 4: (1, 0)}
    explorer.trajectory_effect_evidence.update({1: 2, 4: 2})
    explorer.trajectory_contextual_blocks[((2, 2), 9)] = 1
    explorer.trajectory_gate_refresh_actions[1] = 2

    action = explorer._trajectory_gate_refresh_action(
        (0, 0),
        represented=frozenset({1, 4}),
        allowed_nodes=frozenset({(0, 0), (0, 1), (1, 0)}),
        uncertain_nodes=frozenset({(2, 2)}),
    )

    assert action == 4

    explorer.trajectory_effects = {7: (0, 1), 2: (1, 0)}
    explorer.trajectory_effect_evidence = Counter({7: 2, 2: 2})
    explorer.trajectory_gate_refresh_actions = Counter({7: 2})
    action = explorer._trajectory_gate_refresh_action(
        (0, 0),
        represented=frozenset({2, 7}),
        allowed_nodes=frozenset({(0, 0), (0, 1), (1, 0)}),
        uncertain_nodes=frozenset({(2, 2)}),
    )

    assert action == 2


def test_committed_trajectory_retains_full_enacted_inverse_order() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    enacted = ((0, 1), (0, 0), (1, 0), (0, 0), (0, -1))

    for anchor in enacted:
        assert explorer._record_trajectory_enacted(anchor)

    assert tuple(explorer.trajectory_enacted_path) == enacted
    assert explorer.trajectory_enacted_path.count((0, 0)) == 2

    reflected = EpistemicExplorer(committed_trajectory_planning=True)
    for x, y in enacted:
        assert reflected._record_trajectory_enacted((-x, y))

    assert tuple(reflected.trajectory_enacted_path) == tuple(
        (-x, y) for x, y in enacted
    )


def test_committed_trajectory_enacted_path_is_bounded() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)

    for index in range(32):
        assert explorer._record_trajectory_enacted((index, 0))

    assert not explorer._record_trajectory_enacted((32, 0))
    assert explorer.trajectory_disabled
    assert explorer.trajectory_diagnostic == "enacted-trajectory-cap-reached"


def test_committed_trajectory_plan_cap_is_paid_by_bounded_enacted_path() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)

    assert explorer._trajectory_plan_cap() == 20

    explorer.trajectory_committed_macro = tuple((index, 0) for index in range(7))
    assert explorer._trajectory_plan_cap() == 27

    explorer.trajectory_committed_macro = tuple(
        (index, 0) for index in range(32)
    )
    assert explorer._trajectory_plan_cap() == 32


def test_committed_trajectory_gate_cooldown_requires_successful_ticks() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    first = ((0, 0), 1)
    repeated = ((2, 0), 4)
    explorer.trajectory_contextual_blocks.update({first: 1, repeated: 3})
    explorer.trajectory_gate_cooldowns.update({first: 1, repeated: 3})

    explorer._advance_trajectory_gate_cooldowns()

    assert first not in explorer.trajectory_contextual_blocks
    assert first not in explorer.trajectory_gate_cooldowns
    assert explorer.trajectory_contextual_blocks[repeated] == 3
    assert explorer.trajectory_gate_cooldowns[repeated] == 2

    explorer._advance_trajectory_gate_cooldowns()
    explorer._advance_trajectory_gate_cooldowns()

    assert repeated not in explorer.trajectory_contextual_blocks
    assert repeated not in explorer.trajectory_gate_cooldowns


def test_committed_trajectory_first_replay_axis_is_action_equivariant() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_origin = (4, 4)
    explorer.trajectory_committed_macro = ((4, 7), (4, 4), (7, 4))
    explorer.trajectory_effects = {
        1: (0, 3),
        2: (3, 0),
        3: (0, -3),
        4: (-3, 0),
    }

    assert explorer._trajectory_replay_parallel_actions() == frozenset(
        {1, 3}
    )

    explorer.trajectory_effects = {
        4: (0, 3),
        1: (3, 0),
        2: (0, -3),
        3: (-3, 0),
    }
    assert explorer._trajectory_replay_parallel_actions() == frozenset(
        {2, 4}
    )

    explorer.trajectory_replay_started = True
    assert explorer._trajectory_replay_parallel_actions() == frozenset()


def test_committed_trajectory_avoids_next_replay_anchor() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_origin = (0, 0)
    explorer.trajectory_committed_macro = (
        (0, 1),
        (0, 0),
        (1, 0),
    )
    explorer.trajectory_effects = {
        8: (-1, 0),
        2: (1, 0),
        6: (0, 1),
        4: (0, -1),
    }
    explorer.trajectory_replay_started = True
    explorer.trajectory_replay_cursor = 1

    assert explorer._trajectory_replay_forbidden_actions(
        (1, 0)
    ) == frozenset({8})

    explorer.trajectory_effects = {
        3: (-1, 0),
        7: (1, 0),
        1: (0, 1),
        5: (0, -1),
    }
    assert explorer._trajectory_replay_forbidden_actions(
        (1, 0)
    ) == frozenset({3})


def test_committed_trajectory_retry_retains_only_same_level_accommodation() -> None:
    explorer = EpistemicExplorer(committed_trajectory_planning=True)
    explorer.trajectory_stage = "navigate"
    explorer.trajectory_effects = {1: (1, 0), 2: (0, 1)}
    explorer.trajectory_effect_evidence.update({1: 2, 2: 2})
    explorer.trajectory_probes.update({1, 2})
    explorer.trajectory_contextual_blocks[((6, 6), 1)] = 1
    explorer.trajectory_committed_macro = ((0, 1), (0, 2))
    explorer.trajectory_previous_failed_macro_action = 2
    explorer.trajectory_replay_cursor = 1
    explorer.trajectory_plan_steps = 7

    explorer._reset_committed_trajectory_level(retain_accommodation=True)

    assert explorer.trajectory_stage == "not-attempted"
    assert explorer.trajectory_effects == {1: (1, 0), 2: (0, 1)}
    assert explorer.trajectory_effect_evidence == {1: 2, 2: 2}
    assert explorer.trajectory_probes == {1, 2}
    assert explorer.trajectory_contextual_blocks == {}
    assert explorer.trajectory_committed_macro == ()
    assert explorer.trajectory_previous_failed_macro_action == 2
    assert explorer.trajectory_replay_cursor == 0
    assert explorer.trajectory_plan_steps == 0

    explorer._reset_committed_trajectory_level()

    assert explorer.trajectory_effects == {}
    assert explorer.trajectory_effect_evidence == {}
    assert explorer.trajectory_probes == set()
    assert explorer.trajectory_contextual_blocks == {}
    assert explorer.trajectory_previous_failed_macro_action is None
