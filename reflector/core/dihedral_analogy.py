"""Infer bounded dihedral input/output analogies from framed glyph panels."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

type Frame = tuple[tuple[int, ...], ...]
type Mask = tuple[tuple[bool, ...], ...]


@dataclass(frozen=True, slots=True)
class GlyphTile:
    x: int
    y: int
    size: int
    color: int
    mask: Mask


@dataclass(frozen=True, slots=True)
class DihedralAnalogy:
    query_tiles: tuple[GlyphTile, ...]
    answer_tiles: tuple[GlyphTile, ...]
    targets: tuple[frozenset[Mask], ...]
    selected_index: int


def dihedral_variants(mask: Mask) -> tuple[Mask, ...]:
    """Return the eight square symmetries in a stable order."""

    def rotate(value: Mask) -> Mask:
        size = len(value)
        return tuple(
            tuple(value[size - 1 - x][y] for x in range(size))
            for y in range(size)
        )

    def reflect(value: Mask) -> Mask:
        return tuple(tuple(reversed(row)) for row in value)

    output: list[Mask] = []
    current = mask
    for _index in range(4):
        output.extend((current, reflect(current)))
        current = rotate(current)
    return tuple(output)


def _framed_tiles(frame: Frame) -> tuple[GlyphTile, ...]:
    if not frame or not frame[0]:
        return ()
    height = len(frame)
    width = len(frame[0])
    tiles: list[GlyphTile] = []
    for size in range(5, min(11, height + 1, width + 1)):
        for y in range(height - size + 1):
            for x in range(width - size + 1):
                border = (
                    tuple(frame[y][x : x + size])
                    + tuple(frame[y + size - 1][x : x + size])
                    + tuple(frame[row][x] for row in range(y + 1, y + size - 1))
                    + tuple(
                        frame[row][x + size - 1]
                        for row in range(y + 1, y + size - 1)
                    )
                )
                if len(set(border)) != 1:
                    continue
                color = border[0]
                interior = tuple(
                    tuple(frame[row][x + 1 : x + size - 1])
                    for row in range(y + 1, y + size - 1)
                )
                colors = {cell for row in interior for cell in row}
                if color not in colors or len(colors) != 2:
                    continue
                mask = tuple(
                    tuple(cell == color for cell in row) for row in interior
                )
                tiles.append(GlyphTile(x, y, size, color, mask))
    return tuple(tiles)


def infer_dihedral_analogy(frame: Frame) -> DihedralAnalogy | None:
    """Ground demonstrations, queries, targets, and the active answer slot."""

    tiles = _framed_tiles(frame)
    rows: dict[tuple[int, int], list[GlyphTile]] = {}
    for tile in tiles:
        rows.setdefault((tile.y, tile.size), []).append(tile)
    ordered_rows = tuple(
        tuple(sorted(items, key=lambda item: item.x))
        for (_key, items) in sorted(rows.items())
        if len(items) >= 2
    )
    training_pairs: list[tuple[GlyphTile, GlyphTile]] = []
    single_color_rows: list[tuple[GlyphTile, ...]] = []
    for row in ordered_rows:
        colors = tuple(item.color for item in row)
        if len(set(colors)) == 1:
            single_color_rows.append(row)
            continue
        if (
            len(row) % 2 == 0
            and len(set(colors)) == 2
            and all(
                colors[index] == colors[0 if index % 2 == 0 else 1]
                for index in range(len(colors))
            )
        ):
            training_pairs.extend(
                (row[index], row[index + 1])
                for index in range(0, len(row), 2)
            )
    candidates: list[DihedralAnalogy] = []
    for query in single_color_rows:
        for answer in single_color_rows:
            if (
                answer[0].y <= query[0].y
                or len(answer) != len(query)
                or answer[0].size != query[0].size
                or answer[0].color == query[0].color
            ):
                continue
            relevant = tuple(
                pair
                for pair in training_pairs
                if pair[0].color == query[0].color
                and pair[1].color == answer[0].color
                and pair[0].size == query[0].size
                and pair[1].size == answer[0].size
            )
            if len(relevant) < 4:
                continue
            targets: list[frozenset[Mask]] = []
            valid = True
            for query_tile in query:
                matches: list[Mask] = []
                matched_inputs = 0
                for source, target in relevant:
                    local = []
                    for transformed_source, transformed_target in zip(
                        dihedral_variants(source.mask),
                        dihedral_variants(target.mask),
                        strict=True,
                    ):
                        if transformed_source == query_tile.mask:
                            local.append(transformed_target)
                    if local:
                        matched_inputs += 1
                        matches.extend(local)
                target_set = frozenset(matches)
                if matched_inputs != 1 or not target_set:
                    valid = False
                    break
                targets.append(target_set)
            if not valid:
                continue
            background = Counter(
                cell for row in frame[answer[0].y :] for cell in row
            ).most_common(1)[0][0]
            selector_scores = []
            for index, tile in enumerate(answer):
                top = range(max(0, tile.y - 3), tile.y)
                bottom = range(
                    tile.y + tile.size,
                    min(len(frame), tile.y + tile.size + 3),
                )
                score = sum(
                    frame[y][x] != background
                    for y in (*top, *bottom)
                    for x in range(tile.x, tile.x + tile.size)
                )
                selector_scores.append((score, index))
            best_score = max(score for score, _index in selector_scores)
            selected = [
                index
                for score, index in selector_scores
                if score == best_score and score > 0
            ]
            if len(selected) != 1:
                continue
            candidates.append(
                DihedralAnalogy(
                    query,
                    answer,
                    tuple(targets),
                    selected[0],
                )
            )
    return candidates[0] if len(candidates) == 1 else None
