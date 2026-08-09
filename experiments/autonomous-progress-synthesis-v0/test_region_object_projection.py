import region_object_projection as M


def test_groups_nested_and_touching_components_into_stable_objects():
    grid=[[0]*14 for _ in range(14)]
    # Two-color controlled assembly, a nested framed marker, and a boundary panel.
    for y in (5,6):
        grid[y][5]=2;grid[y][6]=3
    for x in range(10,13):grid[2][x]=4;grid[4][x]=4
    for y in range(2,5):grid[y][10]=4;grid[y][12]=4
    grid[3][11]=5
    for y in range(11,14):
        for x in range(3):grid[y][x]=6
    rows=M.project_objects(grid,controlled_bboxes=((5,5,7,7),))
    assert any(row.action_correlated and row.bbox==(5,5,7,7) for row in rows)
    assert any(row.bbox==(10,2,13,5) and row.component_count>=2 for row in rows)
    assert any(row.touches_frame_boundary for row in rows)
    assert M.projection_document(rows)==M.projection_document(M.project_objects(grid,controlled_bboxes=((5,5,7,7),)))
