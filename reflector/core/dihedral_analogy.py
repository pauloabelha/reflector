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


@dataclass(frozen=True, slots=True)
class GroupedDihedralAnalogy:
    """A partition transported between fixed and editable glyph sequences."""

    groups: tuple[tuple[GlyphTile, ...], ...]
    targets: tuple[tuple[frozenset[Mask], ...], ...]
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
                if len(colors) > 2:
                    continue
                if len(colors) == 2 and color not in colors:
                    continue
                if colors == {color}:
                    continue
                mask = tuple(
                    tuple(cell == color for cell in row) for row in interior
                )
                tiles.append(GlyphTile(x, y, size, color, mask))
    return tuple(tiles)


def _disjoint_rows(
    tiles: tuple[GlyphTile, ...],
) -> tuple[tuple[GlyphTile, ...], ...]:
    rows: dict[tuple[int, int], list[GlyphTile]] = {}
    for tile in tiles:
        rows.setdefault((tile.y, tile.size), []).append(tile)
    disjoint_rows: list[tuple[GlyphTile, ...]] = []
    for items in rows.values():
        disjoint: list[GlyphTile] = []
        next_x = -1
        for item in sorted(items, key=lambda candidate: candidate.x):
            if item.x < next_x:
                continue
            disjoint.append(item)
            next_x = item.x + item.size
        if len(disjoint) >= 2:
            disjoint_rows.append(tuple(disjoint))
    return tuple(
        sorted(
            disjoint_rows,
            key=lambda items: (items[0].y, items[0].size),
        )
    )


def _color_runs(
    row: tuple[GlyphTile, ...],
) -> tuple[tuple[GlyphTile, ...], ...]:
    runs: list[list[GlyphTile]] = []
    for item in row:
        if not runs or runs[-1][0].color != item.color:
            runs.append([item])
        else:
            runs[-1].append(item)
    return tuple(tuple(run) for run in runs)


def _sequence_targets(
    query: tuple[GlyphTile, ...],
    answer: tuple[GlyphTile, ...],
    rows: tuple[tuple[GlyphTile, ...], ...],
) -> tuple[frozenset[Mask], ...] | None:
    relevant: list[tuple[tuple[GlyphTile, ...], tuple[GlyphTile, ...]]] = []
    for row in rows:
        if any(item.size != query[0].size for item in row):
            continue
        if set(item.color for item in row) != {
            query[0].color,
            answer[0].color,
        }:
            continue
        runs: list[list[GlyphTile]] = []
        for item in row:
            if not runs or runs[-1][0].color != item.color:
                runs.append([item])
            else:
                runs[-1].append(item)
        if (
            len(runs) % 2
            or any(
                run[0].color
                != (
                    query[0].color
                    if index % 2 == 0
                    else answer[0].color
                )
                for index, run in enumerate(runs)
            )
        ):
            return None
        relevant.extend(
            (tuple(runs[index]), tuple(runs[index + 1]))
            for index in range(0, len(runs), 2)
        )
    if len(relevant) < 4:
        return None
    target_sequences: set[tuple[frozenset[Mask], ...]] = set()
    frontier: list[tuple[int, tuple[frozenset[Mask], ...]]] = [(0, ())]
    expansions = 0
    while frontier and expansions < 128:
        position, compiled = frontier.pop()
        if position == len(query):
            target_sequences.add(compiled)
            continue
        for sources, outputs in relevant:
            destination = position + len(sources)
            if destination > len(query):
                continue
            if not all(
                query_tile.mask in dihedral_variants(source.mask)
                for query_tile, source in zip(
                    query[position:destination],
                    sources,
                    strict=True,
                )
            ):
                continue
            frontier.append(
                (
                    destination,
                    compiled
                    + tuple(
                        frozenset(dihedral_variants(output.mask))
                        for output in outputs
                    ),
                )
            )
            expansions += 1
    if len(target_sequences) != 1:
        return None
    targets = next(iter(target_sequences))
    return targets if len(targets) == len(answer) else None


def _bridge_targets(
    query: tuple[GlyphTile, ...],
    answer: tuple[GlyphTile, ...],
    rows: tuple[tuple[GlyphTile, ...], ...],
) -> tuple[frozenset[Mask], ...] | None:
    endpoint_colors = {query[0].color, answer[0].color}
    bridge_colors = {
        item.color
        for row in rows
        for item in row
        if item.color not in endpoint_colors
    }
    compiled_candidates: set[tuple[frozenset[Mask], ...]] = set()
    for bridge_color in bridge_colors:
        first: list[tuple[GlyphTile, GlyphTile]] = []
        second: list[tuple[GlyphTile, GlyphTile]] = []
        malformed = False
        for row in rows:
            if any(item.size != query[0].size for item in row):
                continue
            if set(item.color for item in row) != endpoint_colors | {
                bridge_color
            }:
                continue
            if len(row) % 2:
                malformed = True
                break
            for index in range(0, len(row), 2):
                left, right = row[index : index + 2]
                pair = {left.color, right.color}
                if pair == {query[0].color, bridge_color}:
                    source = left if left.color == query[0].color else right
                    bridge = right if source is left else left
                    first.append((source, bridge))
                elif pair == {bridge_color, answer[0].color}:
                    bridge = left if left.color == bridge_color else right
                    output = right if bridge is left else left
                    second.append((bridge, output))
                else:
                    malformed = True
                    break
            if malformed:
                break
        if malformed or len(first) < 2 or len(second) < 2:
            continue
        targets: list[frozenset[Mask]] = []
        for query_tile in query:
            bridges = tuple(
                bridge
                for source, bridge in first
                if query_tile.mask in dihedral_variants(source.mask)
            )
            output_classes = {
                frozenset(dihedral_variants(output.mask))
                for bridge, output in second
                if any(
                    source_bridge.mask
                    in dihedral_variants(bridge.mask)
                    for source_bridge in bridges
                )
            }
            if len(output_classes) != 1:
                break
            targets.append(next(iter(output_classes)))
        if len(targets) == len(query) == len(answer):
            compiled_candidates.add(tuple(targets))
    if len(compiled_candidates) != 1:
        return None
    return next(iter(compiled_candidates))


def infer_dihedral_analogy(frame: Frame) -> DihedralAnalogy | None:
    """Ground class-valued demonstrations, queries, and the active answer."""

    ordered_rows = _disjoint_rows(_framed_tiles(frame))
    mixed_rows: list[tuple[GlyphTile, ...]] = []
    ternary_rows: list[tuple[GlyphTile, ...]] = []
    single_color_rows: list[tuple[GlyphTile, ...]] = []
    for row in ordered_rows:
        colors = tuple(item.color for item in row)
        if len(set(colors)) == 1:
            single_color_rows.append(row)
            continue
        if len(set(colors)) == 2:
            mixed_rows.append(row)
        elif len(set(colors)) == 3:
            ternary_rows.append(row)
    candidates: list[DihedralAnalogy] = []
    for query in single_color_rows:
        for answer in single_color_rows:
            if (
                answer[0].y <= query[0].y
                or answer[0].size != query[0].size
                or answer[0].color == query[0].color
            ):
                continue
            targets = _sequence_targets(
                query,
                answer,
                tuple(mixed_rows),
            ) or _bridge_targets(
                query,
                answer,
                tuple(ternary_rows),
            )
            if targets is None:
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
                    targets,
                    selected[0],
                )
            )
    return candidates[0] if len(candidates) == 1 else None


def infer_grouped_dihedral_analogy(
    frame: Frame,
) -> GroupedDihedralAnalogy | None:
    """Infer an editable run partition equivalent to two fixed sequences.

    The fixed rows provide class-valued targets.  Alternating color runs in
    earlier rows provide the editable partition, so no color, coordinate, or
    run-length signature is privileged.
    """

    rows = _disjoint_rows(_framed_tiles(frame))
    single_rows = tuple(
        row for row in rows if len({item.color for item in row}) == 1
    )
    candidates: list[GroupedDihedralAnalogy] = []
    for source in single_rows:
        for answer in single_rows:
            if (
                source is answer
                or len(source) != len(answer)
                or source[0].size != answer[0].size
                or source[0].color == answer[0].color
            ):
                continue
            endpoint_colors = {source[0].color, answer[0].color}
            mixed = tuple(
                row
                for row in rows
                if row[0].y < min(source[0].y, answer[0].y)
                and all(item.size == source[0].size for item in row)
                and {item.color for item in row} == endpoint_colors
            )
            if not mixed:
                continue
            paired_runs: list[
                tuple[tuple[GlyphTile, ...], tuple[GlyphTile, ...]]
            ] = []
            malformed = False
            for row in mixed:
                runs = _color_runs(row)
                if (
                    len(runs) % 2
                    or any(
                        run[0].color
                        != (
                            source[0].color
                            if index % 2 == 0
                            else answer[0].color
                        )
                        for index, run in enumerate(runs)
                    )
                ):
                    malformed = True
                    break
                paired_runs.extend(
                    (runs[index], runs[index + 1])
                    for index in range(0, len(runs), 2)
                )
            if malformed or len(paired_runs) < 2:
                continue
            if (
                sum(len(left) for left, _right in paired_runs) != len(source)
                or sum(len(right) for _left, right in paired_runs)
                != len(answer)
            ):
                continue
            groups: list[tuple[GlyphTile, ...]] = []
            targets: list[tuple[frozenset[Mask], ...]] = []
            source_cursor = 0
            answer_cursor = 0
            for left, right in paired_runs:
                source_slice = source[
                    source_cursor : source_cursor + len(left)
                ]
                answer_slice = answer[
                    answer_cursor : answer_cursor + len(right)
                ]
                groups.extend((left, right))
                targets.extend(
                    (
                        tuple(
                            frozenset(dihedral_variants(tile.mask))
                            for tile in source_slice
                        ),
                        tuple(
                            frozenset(dihedral_variants(tile.mask))
                            for tile in answer_slice
                        ),
                    )
                )
                source_cursor += len(left)
                answer_cursor += len(right)

            selector_scores: list[tuple[int, int]] = []
            for index, group in enumerate(groups):
                group_left = min(tile.x for tile in group)
                group_right = max(tile.x + tile.size for tile in group)
                top = range(max(0, group[0].y - 3), group[0].y)
                bottom = range(
                    group[0].y + group[0].size,
                    min(
                        len(frame),
                        group[0].y + group[0].size + 3,
                    ),
                )
                band = tuple(
                    frame[y][x]
                    for y in (*top, *bottom)
                    for x in range(group_left, group_right)
                )
                if not band:
                    selector_scores.append((0, index))
                    continue
                background = Counter(band).most_common(1)[0][0]
                selector_scores.append(
                    (sum(cell != background for cell in band), index)
                )
            best_score = max(score for score, _index in selector_scores)
            selected = tuple(
                index
                for score, index in selector_scores
                if score == best_score and score > 0
            )
            if len(selected) != 1:
                continue
            candidates.append(
                GroupedDihedralAnalogy(
                    tuple(groups),
                    tuple(targets),
                    selected[0],
                )
            )
    return candidates[0] if len(candidates) == 1 else None
