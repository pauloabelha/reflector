from __future__ import annotations

from reflector.core.dihedral_analogy import (
    Mask,
    dihedral_variants,
    infer_dihedral_analogy,
)
from reflector.core.exploration import ActionToken, EpistemicExplorer
from reflector.core.symbolic import Observation

type Frame = tuple[tuple[int, ...], ...]


def _mask(*rows: str) -> Mask:
    return tuple(tuple(cell == "#" for cell in row) for row in rows)


def _draw_tile(
    grid: list[list[int]],
    x: int,
    y: int,
    color: int,
    mask: Mask,
) -> None:
    for offset in range(5):
        grid[y][x + offset] = color
        grid[y + 4][x + offset] = color
        grid[y + offset][x] = color
        grid[y + offset][x + 4] = color
    for local_y, row in enumerate(mask):
        for local_x, occupied in enumerate(row):
            grid[y + 1 + local_y][x + 1 + local_x] = (
                color if occupied else 5
            )


def _panel(
    *,
    selected: int,
    first_answer: Mask,
    second_answer: Mask,
) -> Frame:
    grid = [[2 for _x in range(30)] for _y in range(30)]
    for y in range(15, 30):
        grid[y] = [3 for _x in range(30)]
    inputs = (
        _mask("##.", "...", "..."),
        _mask("#..", "##.", "..."),
        _mask("###", "...", "..."),
        _mask("###", ".#.", "..."),
    )
    outputs = (
        _mask("#..", "#..", "..."),
        _mask("##.", "#..", "..."),
        _mask("#..", "#..", "#.."),
        _mask(".#.", "###", "..."),
    )
    for row, indexes in ((1, (0, 1)), (7, (2, 3))):
        for column, index in enumerate(indexes):
            _draw_tile(grid, 1 + column * 12, row, 10, inputs[index])
            _draw_tile(grid, 7 + column * 12, row, 7, outputs[index])
    query_masks = (
        dihedral_variants(inputs[0])[2],
        dihedral_variants(inputs[2])[2],
    )
    for index, query in enumerate(query_masks):
        _draw_tile(grid, 7 + index * 6, 16, 10, query)
    for index, answer in enumerate((first_answer, second_answer)):
        _draw_tile(grid, 7 + index * 6, 23, 7, answer)
    selector_x = 7 + selected * 6
    grid[22][selector_x] = 0
    grid[28][selector_x] = 0
    return tuple(tuple(row) for row in grid)


def _sequence_panel() -> Frame:
    grid = [[2 for _x in range(42)] for _y in range(30)]
    for y in range(15, 30):
        grid[y] = [3 for _x in range(42)]
    inputs = (
        _mask("##.", "...", "..."),
        _mask("#..", "##.", "..."),
        _mask("###", "...", "..."),
        _mask("###", ".#.", "..."),
    )
    outputs = (
        (_mask("#..", "#..", "..."),),
        (
            _mask("##.", "#..", "..."),
            _mask("...", ".#.", ".#."),
        ),
        (_mask("#..", "#..", "#.."),),
        (
            _mask(".#.", "###", "..."),
            _mask("##.", ".#.", "..."),
        ),
    )
    for row, indexes in ((1, (0, 1)), (7, (2, 3))):
        x = 1
        for index in indexes:
            _draw_tile(grid, x, row, 10, inputs[index])
            x += 6
            for output in outputs[index]:
                _draw_tile(grid, x, row, 7, output)
                x += 6
            x += 2
    transform = 2
    query_masks = (
        dihedral_variants(inputs[0])[transform],
        dihedral_variants(inputs[1])[transform],
    )
    for index, query in enumerate(query_masks):
        _draw_tile(grid, 10 + index * 6, 16, 10, query)
    arbitrary = _mask(".#.", "...", "...")
    for index in range(3):
        _draw_tile(grid, 10 + index * 6, 23, 7, arbitrary)
    grid[22][10] = 0
    grid[28][10] = 0
    return tuple(tuple(row) for row in grid)


def _sequence_to_sequence_panel() -> Frame:
    grid = [[2 for _x in range(64)] for _y in range(30)]
    for y in range(15, 30):
        grid[y] = [3 for _x in range(64)]
    inputs = (
        _mask("##.", "...", "..."),
        _mask("#..", "##.", "..."),
        _mask("###", "...", "..."),
        _mask("###", ".#.", "..."),
    )
    outputs = (
        _mask("#..", "#..", "..."),
        _mask("##.", "#..", "..."),
        _mask("#..", "#..", "#.."),
        _mask(".#.", "###", "..."),
    )
    demonstrations = (
        (((inputs[0],), (outputs[0],)), ((inputs[1], inputs[2]), (outputs[1], outputs[2]))),
        (((inputs[3],), (outputs[3], outputs[0])), ((inputs[0], inputs[1]), (outputs[2],))),
    )
    for y, groups in zip((1, 7), demonstrations, strict=True):
        x = 1
        for sources, targets in groups:
            for source in sources:
                _draw_tile(grid, x, y, 10, source)
                x += 6
            for target in targets:
                _draw_tile(grid, x, y, 7, target)
                x += 6
            x += 3
    transform = 2
    query_masks = tuple(
        dihedral_variants(mask)[transform]
        for mask in (inputs[1], inputs[2], inputs[3])
    )
    for index, query in enumerate(query_masks):
        _draw_tile(grid, 12 + index * 6, 16, 10, query)
    arbitrary = _mask(".#.", "...", "...")
    for index in range(4):
        _draw_tile(grid, 12 + index * 6, 23, 7, arbitrary)
    grid[22][12] = 0
    grid[28][12] = 0
    return tuple(tuple(row) for row in grid)


def _bridge_panel() -> Frame:
    grid = [[2 for _x in range(64)] for _y in range(42)]
    for y in range(26, 42):
        grid[y] = [3 for _x in range(64)]
    inputs = (
        _mask("##.", "...", "..."),
        _mask("#..", "##.", "..."),
        _mask("###", "...", "..."),
        _mask("###", ".#.", "..."),
    )
    bridges = (
        _mask("##.", ".#.", "..."),
        _mask("#..", ".#.", "..#"),
        _mask("#.#", ".#.", "..."),
        _mask(".#.", "###", "..."),
    )
    outputs = (
        _mask("#..", "#..", "..."),
        _mask("##.", "#..", "..."),
        _mask("#..", "#..", "#.."),
        _mask(".#.", "###", ".#."),
    )
    for y, (source, bridge, output) in zip(
        (1, 7, 13, 19),
        zip(inputs, bridges, outputs, strict=True),
        strict=True,
    ):
        _draw_tile(grid, 5, y, 11, bridge)
        _draw_tile(grid, 15, y, 7, output)
        _draw_tile(grid, 30, y, 10, source)
        _draw_tile(grid, 40, y, 11, bridge)
    for index, source in enumerate((inputs[0], inputs[2])):
        _draw_tile(grid, 20 + index * 6, 27, 10, source)
    arbitrary = _mask(".#.", "...", "...")
    for index in range(2):
        _draw_tile(grid, 20 + index * 6, 34, 7, arbitrary)
    grid[33][20] = 0
    grid[39][20] = 0
    return tuple(tuple(row) for row in grid)


def test_infers_dihedral_targets_and_selected_slot() -> None:
    arbitrary = _mask(".#.", "...", "...")
    layout = infer_dihedral_analogy(
        _panel(
            selected=0,
            first_answer=arbitrary,
            second_answer=arbitrary,
        )
    )

    assert layout is not None
    assert len(layout.query_tiles) == len(layout.answer_tiles) == 2
    assert all(1 <= len(targets) <= 8 for targets in layout.targets)
    assert layout.selected_index == 0


def test_retains_layout_when_selected_glyph_is_empty() -> None:
    layout = infer_dihedral_analogy(
        _panel(
            selected=0,
            first_answer=_mask("...", "...", "..."),
            second_answer=_mask(".#.", "...", "..."),
        )
    )

    assert layout is not None
    assert not any(cell for row in layout.answer_tiles[0].mask for cell in row)
    assert layout.selected_index == 0


def test_concatenates_variable_length_demonstrated_outputs() -> None:
    layout = infer_dihedral_analogy(_sequence_panel())

    assert layout is not None
    assert len(layout.query_tiles) == 2
    assert len(layout.answer_tiles) == len(layout.targets) == 3
    assert layout.selected_index == 0


def test_segments_and_substitutes_demonstrated_glyph_sequences() -> None:
    layout = infer_dihedral_analogy(_sequence_to_sequence_panel())

    assert layout is not None
    assert len(layout.query_tiles) == 3
    assert len(layout.answer_tiles) == len(layout.targets) == 4
    assert layout.selected_index == 0


def test_composes_glyph_relations_through_a_bridge_color() -> None:
    layout = infer_dihedral_analogy(_bridge_panel())

    assert layout is not None
    assert len(layout.query_tiles) == len(layout.answer_tiles) == 2
    assert layout.answer_tiles[0].mask not in layout.targets[0]
    assert layout.selected_index == 0


def test_explorer_learns_move_and_mutation_controls_prospectively() -> None:
    arbitrary = _mask(".#.", "...", "...")
    changed = _mask("...", ".#.", "...")
    first = _panel(
        selected=0,
        first_answer=arbitrary,
        second_answer=arbitrary,
    )
    mutated = _panel(
        selected=0,
        first_answer=changed,
        second_answer=arbitrary,
    )
    moved = _panel(
        selected=1,
        first_answer=changed,
        second_answer=arbitrary,
    )
    explorer = EpistemicExplorer(dihedral_analogy_alignment=True)
    explorer._observe_dihedral_analogy(first, mutated, 1)
    explorer._observe_dihedral_analogy(mutated, moved, 2)
    observation = Observation.create(
        state="NOT_FINISHED",
        available_actions=(1, 2),
        frame=moved,
    )

    selected = explorer._select_dihedral_analogy(
        observation,
        (ActionToken(1), ActionToken(2)),
    )

    assert explorer.analogy_mutation_actions == {1}
    assert explorer.analogy_move_actions == {2: 1}
    assert selected == ActionToken(1)
