from reflector.exploration import ActionRole, ActionToken, EpistemicExplorer
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
