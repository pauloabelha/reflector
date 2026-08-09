from flow_routing import coarsen, infer_scene, plan_flow


def expanded(symbolic, scale=4):
    return tuple(tuple(value for value in row for _ in range(scale)) for row in symbolic for _ in range(scale))


def scene_grid():
    grid = [[12] * 16 for _ in range(16)]
    grid[0][9] = 4; grid[1][9] = 6
    for x in range(3, 8): grid[4][x] = 9
    for x in (4, 10):
        grid[13][x] = grid[13][x + 2] = 11
        for xx in range(x, x + 3): grid[14][xx] = 11
    for x in range(16): grid[15][x] = 1
    return tuple(tuple(row) for row in grid)


def test_infers_roles_from_scaled_pixels_without_palette_constants():
    frame = expanded(scene_grid())
    scene = infer_scene(frame)
    assert scene.scale == 4
    assert scene.source_column == 9
    assert (scene.reflector.x, scene.reflector.y, scene.reflector.width) == (3, 4, 5)
    assert scene.receptacle_ports == (5, 11)


def test_plans_zero_remaining_terminal_deficit():
    scene = infer_scene(expanded(scene_grid()))
    plan = plan_flow(scene, {(-1, 0): 3, (1, 0): 4, (0, -1): 1, (0, 1): 2}, 5)
    assert plan.predicted_exit_columns == (5, 11)
    assert plan.progress_before == 2 and plan.progress_after == 0
    assert plan.action_ids == (4, 4, 4, 5)


def test_palette_permutation_preserves_plan():
    permutation = {1: 31, 4: 44, 6: 46, 9: 49, 11: 51, 12: 52}
    remapped = tuple(tuple(permutation[value] for value in row) for row in scene_grid())
    plan = plan_flow(infer_scene(expanded(remapped)), {(-1, 0): 8, (1, 0): 7, (0, -1): 6, (0, 1): 5}, 4)
    assert plan.action_ids == (7, 7, 7, 4)
