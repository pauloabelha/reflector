import reset_replay_explorer as SEARCH
import workspace_potential_search as M
import progress_synthesis as PS


def grid(actor_x, target_x=5):
    row = [0] * 8
    row[actor_x] = 1
    row[target_x] = 2
    return tuple(tuple(row) for _ in range(2))


def grounded_goal(initial):
    scene = PS.perceive(initial, coarsen=False)
    actor = next(item for item in scene.regions if item.x == 1)
    target = next(item for item in scene.regions if item.x == 5)
    return M.compile_live_goal({
        "family": "alignment", "controlled_id": actor.region_id,
        "members": [target.region_id], "container_id": None,
        "potential": "AlignmentResidual", "terminal": "Aligned",
        "interaction_candidate": None, "rationale": "cheap visible test",
    }, initial, proposal_id="qwen:support-zero")


def test_support_zero_goal_tracks_roles_and_evaluates_without_authority():
    goal = grounded_goal(grid(1))
    assert goal.empirical_support == 0
    reading = M.evaluate(goal, grid(4))
    assert reading.value == 2 and reading.reason == "grounded-agreement"


def test_disagreeing_correspondences_are_unknown_not_cherry_picked():
    initial = (
        (0, 1, 0, 1, 0, 2, 0, 0),
        (0, 1, 0, 1, 0, 2, 0, 0),
    )
    scene = PS.perceive(initial, coarsen=False)
    actors = [item for item in scene.regions if item.value == 1]
    target = next(item for item in scene.regions if item.value == 2)
    goal = M.compile_live_goal({
        "family": "alignment", "controlled_id": actors[0].region_id,
        "members": [target.region_id], "container_id": None,
        "potential": "AlignmentResidual", "terminal": "Aligned",
        "interaction_candidate": None, "rationale": "ambiguous actor",
    }, initial)
    reading = M.evaluate(goal, initial)
    assert reading.value is None
    # The target shares the same palette-blind geometry too, so all three
    # regions participate in six injective assignments.
    assert reading.correspondence_count == 6
    assert reading.reason == "competing-correspondences-disagree"


class GuidedWorld:
    """Action 1 approaches the goal; action 2 creates distracting states."""
    def __init__(self): self.x = 1; self.noise = 0
    def observation(self):
        # Noise is visible but irrelevant to the grounded goal.
        rows = [list(row) for row in grid(self.x)]
        if self.noise: rows[1][7 - self.noise] = 3
        return tuple(tuple(row) for row in rows)
    def reset(self): self.x = 1; self.noise = 0; return self.observation()
    def step(self, action):
        if action == 1: self.x = min(5, self.x + 1)
        else: self.noise = min(3, self.noise + 1)
        return self.observation()
    def key(self, observation): return repr(observation)
    def legal_actions(self, observation): return (1, 2)
    def completed(self, observation): return self.x == 5
    def terminal(self, observation): return self.completed(observation)


def test_workspace_potential_guides_causal_search_to_environment_completion():
    initial = GuidedWorld().reset(); goal = grounded_goal(initial)
    # Shallow distracting branches consume the small honest replay budget in
    # breadth-first order.  The support-zero field instead prefers progress.
    blind = SEARCH.search(GuidedWorld(), action_budget=18, max_depth=5, history_order=2)
    guided = SEARCH.search(GuidedWorld(), action_budget=18, max_depth=5, history_order=2, priority=M.search_priority((goal,)))
    assert not blind.solved
    assert guided.solved and guided.solution == (1, 1, 1, 1)
    assert goal.empirical_support == 0


def test_invalid_family_pair_is_rejected():
    scene = PS.perceive(grid(1), coarsen=False)
    ids = [item.region_id for item in scene.regions]
    try:
        M.compile_live_goal({
            "family": "alignment", "controlled_id": ids[0], "members": [ids[1]],
            "container_id": None, "potential": "OutsideCount", "terminal": "AllInside",
            "interaction_candidate": None, "rationale": "bad",
        }, grid(1))
    except M.WorkspacePotentialError as error:
        assert "contract" in str(error)
    else:
        raise AssertionError("invalid semantic pair was accepted")
