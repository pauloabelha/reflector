"""Checkpointed real-ARC relational transfer diagnostic.

All cognition added here is experiment-local. Game identity is used only for
transport, target selection, paths, and reporting; it never enters a schema or
an action ranking.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import tempfile
import time
from collections import Counter, defaultdict, deque
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from reflector2.perception import _outline_fingerprint, perceive_grid
from reflector2.raw_frame import load_first_grid
from reflector2.runtime import Runtime


HERE = Path(__file__).resolve().parent
DEFAULT_CORPUS = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/recordings/reflector-v14-graph-400"
)
DEFAULT_ENVIRONMENTS = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/environment_files"
)
DEFAULT_SOURCE = Path(
    "/home/pauloabelha/reflector-v164-pivot-goal/reports/"
    "v164-public-r1-recordings/ar25/"
    "ar25.reflectoragent.7c920744-1244-4c2d-bd8c-43c74f252adb.recording.jsonl"
)
SCHEMA_ATOMS = (
    ("SameOutline", ("?a", "?b")),
    ("SameOutline", ("?a", "?c")),
    ("SameInteriorLayout", ("?a", "?b")),
    ("DifferentInteriorLayout", ("?a", "?c")),
)

Grid = tuple[tuple[int, ...], ...]
Point = tuple[int, int]


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def append_jsonl(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(stable_json(value) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def frame_hash(grid: Grid) -> str:
    return hashlib.sha256(repr(grid).encode("utf-8")).hexdigest()


def observation_grid(observation: Any) -> Grid:
    value = observation.frame.tolist() if hasattr(observation.frame, "tolist") else observation.frame
    if isinstance(value, list) and value and hasattr(value[-1], "tolist"):
        value = value[-1].tolist()
    while (
        isinstance(value, list)
        and value
        and isinstance(value[0], list)
        and value[0]
        and isinstance(value[0][0], list)
    ):
        value = value[-1]
    if not isinstance(value, list) or not value or not isinstance(value[0], list):
        raise ValueError("ARC observation has no rectangular frame")
    return tuple(tuple(int(cell) for cell in row) for row in value)


def recording_grid(packet: dict[str, Any]) -> Grid:
    frame = packet["frame"]
    if frame and frame[0] and isinstance(frame[0][0], list):
        frame = frame[-1]
    return tuple(tuple(int(cell) for cell in row) for row in frame)


def components(points: set[Point]) -> list[set[Point]]:
    output: list[set[Point]] = []
    unseen = set(points)
    while unseen:
        start = min(unseen, key=lambda point: (point[1], point[0]))
        unseen.remove(start)
        queue = deque([start])
        component = {start}
        while queue:
            x, y = queue.popleft()
            for point in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if point in unseen:
                    unseen.remove(point)
                    component.add(point)
                    queue.append(point)
        output.append(component)
    return output


@dataclass(frozen=True, slots=True)
class Figure:
    outline: str
    primary_value: int
    contrast_count: int
    area: int
    anchor: Point
    centroid2: Point
    normalized_cells: tuple[Point, ...]
    interior_pattern: tuple[Point, ...]

    @property
    def local_key(self) -> tuple[str, int, int, int, tuple[Point, ...]]:
        return (
            self.outline,
            self.primary_value,
            self.contrast_count,
            self.area,
            self.normalized_cells,
            self.interior_pattern,
        )


@dataclass(frozen=True, slots=True)
class Motif:
    matching_pair: tuple[Figure, Figure]
    differing: Figure


@dataclass(frozen=True, slots=True)
class JointEffect:
    vector: Point
    differing_vector: Point
    residual_before: int
    residual_after: int
    mobile_key: tuple[Any, ...]
    fixed_key: tuple[Any, ...]
    differing_key: tuple[Any, ...]
    joint_movers: int
    mobile_anchor_before: Point
    mobile_anchor_after: Point
    fixed_anchor: Point
    mobile_centroid2_before: Point
    mobile_centroid2_after: Point
    fixed_centroid2: Point

    @property
    def decreases(self) -> bool:
        return self.residual_after < self.residual_before


def extract_figures(grid: Grid) -> tuple[Figure, ...]:
    counts = Counter(value for row in grid for value in row)
    background = max(counts, key=lambda value: (counts[value], -value))
    foreground = {
        (x, y)
        for y, row in enumerate(grid)
        for x, value in enumerate(row)
        if value != background
    }
    figures: list[Figure] = []
    for cells in components(foreground):
        min_x = min(x for x, _y in cells)
        min_y = min(y for _x, y in cells)
        normalized = tuple(sorted((x - min_x, y - min_y) for x, y in cells))
        colors = Counter(grid[y][x] for x, y in cells)
        primary = max(colors, key=lambda value: (colors[value], -value))
        area = len(cells)
        interior_pattern = tuple(
            sorted((x - min_x, y - min_y) for x, y in cells if grid[y][x] != primary)
        )
        figures.append(
            Figure(
                outline=_outline_fingerprint(cells),
                primary_value=primary,
                contrast_count=area - colors[primary],
                area=area,
                anchor=(min_x, min_y),
                centroid2=(
                    round(2 * sum(x for x, _y in cells) / area),
                    round(2 * sum(y for _x, y in cells) / area),
                ),
                normalized_cells=normalized,
                interior_pattern=interior_pattern,
            )
        )
    return tuple(sorted(figures, key=lambda item: (item.outline, item.anchor, item.local_key)))


def all_motifs(figures: Sequence[Figure]) -> tuple[Motif, ...]:
    by_outline: dict[str, list[Figure]] = defaultdict(list)
    for figure in figures:
        by_outline[figure.outline].append(figure)
    candidates: list[tuple[tuple[Any, ...], Motif]] = []
    for outline, group in sorted(by_outline.items()):
        for left, right, differing in itertools.permutations(group, 3):
            if left.local_key == right.local_key and left.anchor == right.anchor:
                continue
            if left.interior_pattern != right.interior_pattern:
                continue
            if differing.interior_pattern == left.interior_pattern:
                continue
            pair = tuple(sorted((left, right), key=lambda item: (item.anchor, item.local_key)))
            key = (
                -len(group),
                outline,
                pair[0].contrast_count,
                differing.contrast_count,
                pair[0].interior_pattern,
                differing.interior_pattern,
                pair[0].anchor,
                pair[1].anchor,
                differing.anchor,
            )
            candidates.append((key, Motif(pair, differing)))
    unique: dict[tuple[Any, ...], Motif] = {}
    for key, motif in candidates:
        identity = (
            tuple((item.local_key, item.anchor) for item in motif.matching_pair),
            motif.differing.local_key,
            motif.differing.anchor,
        )
        unique.setdefault(identity, motif)
    return tuple(unique[key] for key in sorted(unique, key=repr))


def find_motif(figures: Sequence[Figure]) -> Motif | None:
    motifs = all_motifs(figures)
    return motifs[0] if motifs else None


def residual(left: Figure, right: Figure) -> int:
    return abs(left.centroid2[0] - right.centroid2[0]) + abs(left.centroid2[1] - right.centroid2[1])


def correspond(before: Sequence[Figure], after: Sequence[Figure]) -> dict[Figure, Figure]:
    available = list(after)
    output: dict[Figure, Figure] = {}
    for source in sorted(before, key=lambda item: (item.local_key, item.anchor)):
        compatible = [item for item in available if item.local_key == source.local_key]
        if not compatible:
            continue
        selected = min(
            compatible,
            key=lambda item: (
                abs(item.anchor[0] - source.anchor[0]) + abs(item.anchor[1] - source.anchor[1]),
                item.anchor,
            ),
        )
        output[source] = selected
        available.remove(selected)
    return output


def joint_effects(before_grid: Grid, after_grid: Grid) -> tuple[JointEffect, ...]:
    before_figures = extract_figures(before_grid)
    after_figures = extract_figures(after_grid)
    mapping = correspond(before_figures, after_figures)
    output: list[JointEffect] = []
    for motif in all_motifs(before_figures):
        relevant = (*motif.matching_pair, motif.differing)
        if any(item not in mapping for item in relevant):
            continue
        deltas = {
            item: (
                mapping[item].anchor[0] - item.anchor[0],
                mapping[item].anchor[1] - item.anchor[1],
            )
            for item in relevant
        }
        left, right = motif.matching_pair
        moving_pair = [item for item in (left, right) if deltas[item] != (0, 0)]
        fixed_pair = [item for item in (left, right) if deltas[item] == (0, 0)]
        if len(moving_pair) != 1 or len(fixed_pair) != 1:
            continue
        mobile = moving_pair[0]
        fixed = fixed_pair[0]
        vector = deltas[mobile]
        differing_vector = deltas[motif.differing]
        if vector == (0, 0) or differing_vector == (0, 0):
            continue
        moved = sum(delta != (0, 0) for delta in deltas.values())
        output.append(
            JointEffect(
                vector=vector,
                differing_vector=differing_vector,
                residual_before=residual(mobile, fixed),
                residual_after=residual(mapping[mobile], mapping[fixed]),
                mobile_key=mobile.local_key,
                fixed_key=fixed.local_key,
                differing_key=motif.differing.local_key,
                joint_movers=moved,
                mobile_anchor_before=mobile.anchor,
                mobile_anchor_after=mapping[mobile].anchor,
                fixed_anchor=fixed.anchor,
                mobile_centroid2_before=mobile.centroid2,
                mobile_centroid2_after=mapping[mobile].centroid2,
                fixed_centroid2=fixed.centroid2,
            )
        )
    return tuple(
        sorted(
            output,
            key=lambda item: (
                not item.decreases,
                item.residual_after,
                item.mobile_anchor_before,
                item.fixed_anchor,
            ),
        )
    )


def joint_effect(before_grid: Grid, after_grid: Grid) -> JointEffect | None:
    effects = joint_effects(before_grid, after_grid)
    return effects[0] if effects else None


def r2_relation_counts(grid: Grid, context: str) -> dict[str, int]:
    runtime = Runtime()
    batch = perceive_grid(runtime.graph.terms, grid, context)
    names = Counter(str(runtime.graph.terms.value(head)) for head, _arguments in batch.facts)
    return {
        "figures": names["Kind"],
        "same_outline": names["SameOutline"],
        "same_interior": names["SameInteriorContrast"],
        "different_interior": names["DifferentInteriorContrast"],
    }


def layout_signature(grid: Grid) -> dict[str, Any]:
    by_outline: dict[str, list[Figure]] = defaultdict(list)
    for figure in extract_figures(grid):
        by_outline[figure.outline].append(figure)
    groups: list[dict[str, Any]] = []
    for outline, figures in sorted(by_outline.items()):
        if len(figures) < 2:
            continue
        layouts = Counter(figure.interior_pattern for figure in figures)
        same_pairs = sum(count * (count - 1) // 2 for count in layouts.values())
        total_pairs = len(figures) * (len(figures) - 1) // 2
        groups.append(
            {
                "outline_hash": outline,
                "group_size": len(figures),
                "largest_layout_class": max(layouts.values()),
                "layout_classes": len(layouts),
                "same_layout_pairs": same_pairs,
                "different_layout_pairs": total_pairs - same_pairs,
            }
        )
    motif_groups = [
        group
        for group in groups
        if group["group_size"] >= 3
        and group["same_layout_pairs"] >= 1
        and group["different_layout_pairs"] >= 2
    ]
    return {"groups": groups, "motif_groups": motif_groups}


def first_packet(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8").splitlines()[0])["data"]


def select_targets(corpus: Path, source_recording: Path, output: Path) -> dict[str, Any]:
    source_layout = layout_signature(load_first_grid(source_recording))
    if not source_layout["motif_groups"]:
        raise RuntimeError("source first frame has no layout motif")
    source_group = min(
        source_layout["motif_groups"],
        key=lambda group: (group["group_size"], group["outline_hash"]),
    )
    rows: list[dict[str, Any]] = []
    for recording in sorted(corpus.glob("*.recording.jsonl")):
        game = recording.name.split(".", 1)[0]
        packet = first_packet(recording)
        counts = r2_relation_counts(load_first_grid(recording), f"selector:{game}")
        layout = layout_signature(load_first_grid(recording))
        rows.append(
            {
                "game": game,
                "recording": str(recording),
                "legal_action_count": len(set(int(item) for item in packet["available_actions"])),
                **counts,
                "layout_groups": layout["groups"],
                "layout_motif_groups": layout["motif_groups"],
            }
        )
    positive_candidates: list[tuple[tuple[int, ...], dict[str, Any], dict[str, Any]]] = []
    for row in rows:
        if row["game"] == "ar25" or row["legal_action_count"] < 2:
            continue
        for group in row["layout_motif_groups"]:
            distance = (
                abs(group["group_size"] - source_group["group_size"]),
                abs(group["largest_layout_class"] - source_group["largest_layout_class"]),
                abs(group["layout_classes"] - source_group["layout_classes"]),
                abs(group["different_layout_pairs"] - source_group["different_layout_pairs"]),
            )
            positive_candidates.append((distance, row, group))
    if not positive_candidates:
        raise RuntimeError("no positive target satisfies the frozen rule")
    positive_distance, positive, positive_group = min(
        positive_candidates, key=lambda item: (item[0], item[1]["game"], item[2]["outline_hash"])
    )
    positive = {**positive, "selected_layout_group": positive_group, "source_distance": list(positive_distance)}
    negative_candidates = [
        row
        for row in rows
        if row["game"] not in {"ar25", positive["game"]}
        and row["legal_action_count"] >= 2
        and row["same_outline"] == 0
    ]
    if not negative_candidates:
        raise RuntimeError("no negative target satisfies the frozen rule")
    negative = min(negative_candidates, key=lambda row: row["game"])
    result = {
        "protocol": "PROPOSAL.md source-nearest mechanical first-frame selector",
        "source_excluded": "ar25",
        "source_layout_group": source_group,
        "positive": positive,
        "negative": negative,
        "positive_candidates": sorted({row["game"] for _distance, row, _group in positive_candidates}),
        "negative_candidates": [row["game"] for row in negative_candidates],
        "audit": rows,
    }
    atomic_json(output, result)
    return result


def source_packets(recording: Path) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for line in recording.read_text(encoding="utf-8").splitlines():
        packet = json.loads(line)["data"]
        output.append(packet)
        if int(packet.get("levels_completed", 0)) > 0:
            break
    if len(output) < 3 or int(output[-1].get("levels_completed", 0)) < 1:
        raise RuntimeError("source recording has no completed first-level chronology")
    return output


def learn_source_schema(recording: Path, output: Path, minimum_suffix: int) -> dict[str, Any]:
    packets = source_packets(recording)
    effects: list[dict[str, Any]] = []
    action_models: dict[int, list[JointEffect]] = defaultdict(list)
    for index in range(1, len(packets)):
        before = recording_grid(packets[index - 1])
        after = recording_grid(packets[index])
        action = int(packets[index]["action_input"]["id"])
        delta = int(packets[index]["levels_completed"]) - int(packets[index - 1]["levels_completed"])
        effect = joint_effect(before, after) if delta == 0 else None
        if effect is not None:
            action_models[action].append(effect)
        effects.append(
            {
                "transition": index,
                "source_local_action": action,
                "level_delta": delta,
                "effect": None if effect is None else asdict(effect),
            }
        )

    terminal_index = len(packets) - 1
    terminal_action = int(packets[-1]["action_input"]["id"])
    terminal_prediction: dict[str, Any] | None = None
    terminal_effect_rows = [
        item
        for item in effects
        if item["source_local_action"] == terminal_action and item["effect"] is not None
    ]
    if terminal_effect_rows:
        last_known = terminal_effect_rows[-1]
        model = last_known["effect"]
        decrement = int(model["residual_before"]) - int(model["residual_after"])
        unobserved = list(range(int(last_known["transition"]) + 1, terminal_index + 1))
        same_intervention_suffix = all(
            int(packets[index]["action_input"]["id"]) == terminal_action
            for index in unobserved
        )
        predicted_after = int(model["residual_after"]) - decrement * len(unobserved)
        terminal_prediction = {
            "transition": terminal_index,
            "last_direct_transition": int(last_known["transition"]),
            "last_direct_residual_after": int(model["residual_after"]),
            "per_intervention_decrement": decrement,
            "occluded_transition_count": len(unobserved),
            "same_intervention_suffix": same_intervention_suffix,
            "predicted_residual_after": predicted_after,
            "decreases": same_intervention_suffix and decrement > 0 and predicted_after <= 0,
            "model_support": len(action_models[terminal_action]),
        }

    decreasing = [
        item["transition"]
        for item in effects
        if item["effect"] is not None
        and item["effect"]["residual_after"] < item["effect"]["residual_before"]
    ]
    evidence = set(decreasing)
    if terminal_prediction and terminal_prediction["decreases"]:
        evidence.update(
            range(int(terminal_prediction["last_direct_transition"]) + 1, terminal_index + 1)
        )
    suffix: list[int] = []
    cursor = terminal_index
    while cursor in evidence:
        suffix.append(cursor)
        cursor -= 1
    suffix.reverse()
    admitted = len(suffix) >= minimum_suffix and bool(terminal_prediction and terminal_prediction["decreases"])
    schema_core = {
        "body": [[head, list(arguments)] for head, arguments in SCHEMA_ATOMS],
        "effect": ["Decrease", ["TranslationAlignmentResidual", "?a", "?b"]],
        "joint_effect": [
            "Preserve",
            ["CoupledIntervention", "one-matching-interior-member", "different-interior-member"],
        ],
        "provenance": "self-built",
        "schema_language": "r2-structural-v0",
    }
    result = {
        **schema_core,
        "schema_hash": stable_hash(schema_core),
        "admitted": admitted,
        "admission_rule": f"progress-ending strict-decrease suffix length >= {minimum_suffix}",
        "evidence": [f"source-transition:{index}" for index in suffix] if admitted else [],
        "evidence_count": len(suffix) if admitted else 0,
        "source": {
            "recording_sha256": file_hash(recording),
            "transitions_observed": len(packets) - 1,
            "terminal_level_delta": 1,
        },
        "terminal_prediction": terminal_prediction,
        "audit": effects,
        "forbidden_transfer_fields": [
            "source_local_action",
            "game_id",
            "color",
            "binding_id",
            "frame_id",
            "coordinate",
        ],
    }
    atomic_json(output, result)
    return result


@dataclass(frozen=True, slots=True)
class Decision:
    action_id: int
    fallback_action_id: int
    reason: str
    prior_provenances: tuple[str, ...]
    motif_bound: bool
    locally_confirmed: bool
    residual_before: int | None
    predicted_residual_after: int | None


class RelationalController:
    """Action-agnostic parent schemas plus target-local opaque action children."""

    def __init__(self, prior_provenances: Iterable[str]) -> None:
        self.prior_provenances = tuple(sorted(set(prior_provenances)))
        self.uses: Counter[int] = Counter()
        self.action_vectors: dict[int, list[Point]] = defaultdict(list)
        self.mobile_key: tuple[Any, ...] | None = None
        self.fixed_key: tuple[Any, ...] | None = None
        self.mobile_anchor: Point | None = None
        self.fixed_anchor: Point | None = None
        self.mobile_centroid2: Point | None = None
        self.fixed_centroid2: Point | None = None
        self.bindings = 0
        self.local_confirmations = 0
        self.prior_decisions = 0
        self.overrides = 0
        self.abstentions = 0

    def _modal_vector(self, action: int) -> tuple[Point, int] | None:
        if not self.action_vectors.get(action):
            return None
        counts = Counter(self.action_vectors[action])
        vector, support = min(counts.items(), key=lambda item: (-item[1], item[0]))
        return vector, support

    @property
    def residual(self) -> int | None:
        if self.mobile_centroid2 is None or self.fixed_centroid2 is None:
            return None
        return (
            abs(self.mobile_centroid2[0] - self.fixed_centroid2[0])
            + abs(self.mobile_centroid2[1] - self.fixed_centroid2[1])
        )

    def choose(self, grid: Grid, legal_actions: Sequence[int]) -> Decision:
        legal = tuple(sorted(set(int(item) for item in legal_actions)))
        if not legal:
            raise RuntimeError("no legal simple action remains after complex-action abstention")
        fallback = min(legal, key=lambda action: (self.uses[action], action))
        motif_bound = bool(layout_signature(grid)["motif_groups"])
        if not self.prior_provenances:
            self.abstentions += 1
            return Decision(fallback, fallback, "scratch-fallback", (), motif_bound, False, None, None)
        if not motif_bound and self.residual is None:
            self.abstentions += 1
            return Decision(
                fallback,
                fallback,
                "prior-antecedent-unbound",
                self.prior_provenances,
                False,
                False,
                None,
                None,
            )
        current = self.residual
        candidates: list[tuple[int, int, int, int]] = []
        if current is not None and self.mobile_centroid2 is not None and self.fixed_centroid2 is not None:
            for action in legal:
                model = self._modal_vector(action)
                if model is None:
                    continue
                vector, support = model
                predicted = (
                    abs(self.mobile_centroid2[0] + 2 * vector[0] - self.fixed_centroid2[0])
                    + abs(self.mobile_centroid2[1] + 2 * vector[1] - self.fixed_centroid2[1])
                )
                if predicted < current:
                    candidates.append((predicted, -support, self.uses[action], action))
        if not candidates:
            self.abstentions += 1
            return Decision(
                fallback,
                fallback,
                "prior-bound-awaiting-local-consequence" if motif_bound else "occluded-no-decreasing-consequence",
                self.prior_provenances,
                motif_bound,
                self.local_confirmations > 0,
                current,
                None,
            )
        predicted, _negative_support, _uses, selected = min(candidates)
        self.prior_decisions += 1
        if selected != fallback:
            self.overrides += 1
        return Decision(
            selected,
            fallback,
            "locally-confirmed-decrease",
            self.prior_provenances,
            motif_bound,
            True,
            current,
            predicted,
        )

    def observe(self, action: int, before: Grid, after: Grid, *, completed_level: bool) -> dict[str, Any]:
        self.uses[action] += 1
        effects = list(joint_effects(before, after)) if not completed_level else []
        selected: JointEffect | None = None
        if effects and self.mobile_anchor is not None and self.fixed_anchor is not None:
            consistent = [
                item
                for item in effects
                if item.mobile_anchor_before == self.mobile_anchor
                and item.fixed_anchor == self.fixed_anchor
            ]
            if consistent:
                selected = consistent[0]
        if selected is None and effects:
            selected = effects[0]
        if selected is not None:
            if self.mobile_anchor is None:
                self.bindings += 1
            self.mobile_key = selected.mobile_key
            self.fixed_key = selected.fixed_key
            self.mobile_anchor = selected.mobile_anchor_after
            self.fixed_anchor = selected.fixed_anchor
            self.mobile_centroid2 = selected.mobile_centroid2_after
            self.fixed_centroid2 = selected.fixed_centroid2
            self.action_vectors[action].append(selected.vector)
            if self.prior_provenances:
                self.local_confirmations += 1
        elif self.mobile_centroid2 is not None:
            model = self._modal_vector(action)
            if model is not None:
                vector, _support = model
                self.mobile_centroid2 = (
                    self.mobile_centroid2[0] + 2 * vector[0],
                    self.mobile_centroid2[1] + 2 * vector[1],
                )
                if self.mobile_anchor is not None:
                    self.mobile_anchor = (
                        self.mobile_anchor[0] + vector[0],
                        self.mobile_anchor[1] + vector[1],
                    )
        return {
            "joint_effect_candidates": len(effects),
            "selected_joint_effect": None if selected is None else asdict(selected),
            "residual_after_update": self.residual,
            "local_confirmation": bool(selected is not None and self.prior_provenances),
        }

    def report(self) -> dict[str, Any]:
        provenance_states = list(self.prior_provenances)
        if self.local_confirmations and "externally-proposed" in self.prior_provenances:
            provenance_states.append("externally-proposed-and-locally-confirmed")
        return {
            "prior_provenances": list(self.prior_provenances),
            "provenance_states": sorted(set(provenance_states)),
            "action_uses": {str(key): value for key, value in sorted(self.uses.items())},
            "action_vectors": {
                str(action): [list(vector) for vector in vectors]
                for action, vectors in sorted(self.action_vectors.items())
            },
            "bindings": self.bindings,
            "local_confirmations": self.local_confirmations,
            "prior_decisions": self.prior_decisions,
            "overrides": self.overrides,
            "abstentions": self.abstentions,
            "residual": self.residual,
        }


def observation_record(observation: Any) -> dict[str, Any]:
    grid = observation_grid(observation)
    available = sorted(
        int(getattr(item, "value", item))
        for item in getattr(observation, "available_actions", ())
    )
    record = {
        "frame_sha256": frame_hash(grid),
        "state": str(getattr(getattr(observation, "state", ""), "value", getattr(observation, "state", ""))),
        "levels_completed": int(getattr(observation, "levels_completed", 0)),
        "win_levels": int(getattr(observation, "win_levels", 0)),
        "full_reset": bool(getattr(observation, "full_reset", False)),
        "available_actions": available,
    }
    return {**record, "digest": stable_hash(record)}


def open_environment(environments: Path, recordings: Path, game: str) -> tuple[Any, Any]:
    from arc_agi import Arcade, OperationMode

    recordings.mkdir(parents=True, exist_ok=True)
    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments),
        recordings_dir=str(recordings),
    )
    environment = arcade.make(game, include_frame_data=True)
    if environment is None:
        arcade.close_scorecard()
        raise RuntimeError(f"could not open game {game}")
    return arcade, environment


def simple_legal_actions(environment: Any, observation: Any) -> tuple[int, ...]:
    available = {
        int(getattr(item, "value", item))
        for item in getattr(observation, "available_actions", ())
    }
    by_id = {
        int(getattr(item, "value", item)): item
        for item in getattr(environment, "action_space", ())
    }
    output: list[int] = []
    for action_id in sorted(available):
        transport = by_id.get(action_id)
        if transport is None:
            from arcengine import GameAction

            transport = GameAction.from_id(action_id)
        is_complex = getattr(transport, "is_complex", None)
        if callable(is_complex) and bool(is_complex()):
            continue
        output.append(action_id)
    return tuple(output)


def execute_action(environment: Any, game: str, action_id: int, data: dict[str, int], reason: str) -> Any:
    from arcengine import GameAction

    action = GameAction.from_id(action_id)
    if data:
        action.set_data(data)
    result = environment.step(
        action,
        data={**data, "game_id": game},
        reasoning={"experiment": "prior-accelerated-relational-transfer-v0", "reason": reason},
    )
    observation = result if result is not None else environment.observation_space
    if observation is None:
        raise RuntimeError("ARC returned no successor observation")
    return observation


def arm_provenances(arm: str, self_schema: dict[str, Any]) -> tuple[str, ...]:
    if arm == "scratch":
        return ()
    if arm == "self_transfer":
        if not self_schema.get("admitted"):
            raise RuntimeError("self-transfer requested without an admitted source schema")
        return ("transferred-self-built",)
    if arm == "external":
        return ("externally-proposed",)
    if arm == "combined":
        if not self_schema.get("admitted"):
            raise RuntimeError("combined requested without an admitted source schema")
        return ("externally-proposed", "transferred-self-built")
    raise ValueError(f"unknown arm {arm}")


def replay_committed(
    environments: Path,
    recordings: Path,
    game: str,
    history: Sequence[dict[str, Any]],
) -> tuple[Any, Any, RelationalController, Grid]:
    arcade, environment = open_environment(environments, recordings, game)
    observation = environment.observation_space
    if observation is None:
        observation = environment.reset()
    if observation is None:
        arcade.close_scorecard()
        raise RuntimeError("ARC produced no initial observation")
    controller = RelationalController(())  # caller replaces provenance after deterministic rebuild
    grid = observation_grid(observation)
    for item in history:
        before_record = observation_record(observation)
        if before_record["digest"] != item["before"]["digest"]:
            arcade.close_scorecard()
            raise RuntimeError(f"checkpoint replay predecessor mismatch at action {item['index']}")
        successor = execute_action(
            environment,
            game,
            int(item["action_id"]),
            {str(key): int(value) for key, value in item.get("data", {}).items()},
            "checkpoint-replay",
        )
        successor_record = observation_record(successor)
        if successor_record["digest"] != item["after"]["digest"]:
            arcade.close_scorecard()
            raise RuntimeError(f"checkpoint replay successor mismatch at action {item['index']}")
        grid = observation_grid(successor)
        observation = successor
    return arcade, environment, controller, grid


def rebuild_controller(
    provenance: tuple[str, ...], history: Sequence[dict[str, Any]]
) -> RelationalController:
    controller = RelationalController(provenance)
    for item in history:
        before = tuple(tuple(int(cell) for cell in row) for row in item["before_grid"])
        after = tuple(tuple(int(cell) for cell in row) for row in item["after_grid"])
        controller.observe(
            int(item["action_id"]),
            before,
            after,
            completed_level=int(item["after"]["levels_completed"]) > int(item["before"]["levels_completed"]),
        )
    return controller


def job_key(
    game: str,
    arm: str,
    config: dict[str, Any],
    selected: dict[str, Any],
    self_schema: dict[str, Any],
    external_prior: dict[str, Any],
) -> str:
    from importlib.metadata import version

    return stable_hash(
        {
            "protocol": "prior-relational-transfer-v0.2",
            "game": game,
            "arm": arm,
            "config": config,
            "selected_targets_hash": stable_hash(selected),
            "self_schema_hash": stable_hash(self_schema),
            "external_prior_hash": stable_hash(external_prior),
            "experiment_code_sha256": file_hash(Path(__file__)),
            "arc_agi_version": version("arc-agi"),
        }
    )


def verify_history(
    environments: Path,
    recordings: Path,
    game: str,
    history: Sequence[dict[str, Any]],
) -> bool:
    arcade, environment = open_environment(environments, recordings, game)
    try:
        observation = environment.observation_space
        if observation is None:
            observation = environment.reset()
        if observation is None:
            raise RuntimeError("verification produced no initial observation")
        for item in history:
            if observation_record(observation)["digest"] != item["before"]["digest"]:
                return False
            observation = execute_action(
                environment,
                game,
                int(item["action_id"]),
                {str(key): int(value) for key, value in item.get("data", {}).items()},
                "final-ledger-verification",
            )
            if observation_record(observation)["digest"] != item["after"]["digest"]:
                return False
        return True
    finally:
        arcade.close_scorecard()


def run_arm(payload: dict[str, Any]) -> dict[str, Any]:
    game = str(payload["game"])
    role = str(payload["target_role"])
    arm = str(payload["arm"])
    config = payload["config"]
    self_schema = payload["self_schema"]
    external_prior = payload["external_prior"]
    expected_key = str(payload["job_key"])
    artifacts = Path(payload["artifacts"])
    environments = Path(payload["environments"])
    checkpoint = artifacts / "checkpoints" / game / arm / "latest.json"
    progress = artifacts / "progress" / f"{game}--{arm}.json"
    trace = artifacts / "traces" / f"{game}--{arm}.jsonl"
    result_path = artifacts / "arms" / f"{game}--{arm}.json"
    provenance = arm_provenances(arm, self_schema)

    state: dict[str, Any]
    resumed = False
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
        if state.get("job_key") != expected_key:
            raise RuntimeError(f"incompatible checkpoint for {game}/{arm}")
        resumed = bool(state.get("history")) or state.get("pending") is not None
        if state.get("status") == "completed" and result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))
    else:
        state = {
            "job_key": expected_key,
            "game": game,
            "target_role": role,
            "arm": arm,
            "history": [],
            "pending": None,
            "status": "running",
        }
        atomic_json(checkpoint, state)
        atomic_json(progress, {**state, "history": [], "actions_committed": 0})
        trace.parent.mkdir(parents=True, exist_ok=True)
        trace.write_text("", encoding="utf-8")

    history: list[dict[str, Any]] = list(state.get("history", []))
    run_recordings = artifacts / "recordings" / game / arm / f"session-{len(history):02d}"
    arcade, environment, _unused, _grid = replay_committed(
        environments, run_recordings, game, history
    )
    controller = rebuild_controller(provenance, history)
    observation = environment.observation_space
    if observation is None:
        arcade.close_scorecard()
        raise RuntimeError("replayed environment has no observation")
    started = time.perf_counter()
    try:
        while len(history) < int(config["action_budget"]):
            before_record = observation_record(observation)
            if int(before_record["levels_completed"]) >= 1:
                break
            before_grid = observation_grid(observation)
            legal = simple_legal_actions(environment, observation)
            pending = state.get("pending")
            if pending is not None:
                if pending["before_digest"] != before_record["digest"]:
                    raise RuntimeError("pending checkpoint predecessor mismatch")
                action_id = int(pending["action_id"])
                decision_dict = dict(pending["decision"])
                if action_id not in legal:
                    raise RuntimeError("pending checkpoint action is no longer legal")
            else:
                decision = controller.choose(before_grid, legal)
                action_id = decision.action_id
                decision_dict = asdict(decision)
                pending = {
                    "index": len(history),
                    "before_digest": before_record["digest"],
                    "action_id": action_id,
                    "data": {},
                    "decision": decision_dict,
                }
                state = {**state, "pending": pending, "status": "running"}
                atomic_json(checkpoint, state)
                atomic_json(
                    progress,
                    {
                        "game": game,
                        "target_role": role,
                        "arm": arm,
                        "status": "pending-action",
                        "actions_committed": len(history),
                        "pending": pending,
                    },
                )

            successor = execute_action(
                environment, game, action_id, {}, str(decision_dict["reason"])
            )
            after_record = observation_record(successor)
            after_grid = observation_grid(successor)
            level_delta = int(after_record["levels_completed"]) - int(before_record["levels_completed"])
            learning = controller.observe(
                action_id,
                before_grid,
                after_grid,
                completed_level=level_delta > 0,
            )
            committed = {
                "index": len(history),
                "before": before_record,
                "action_id": action_id,
                "data": {},
                "decision": decision_dict,
                "after": after_record,
                "level_delta": level_delta,
                "learning": learning,
                "before_grid": [list(row) for row in before_grid],
                "after_grid": [list(row) for row in after_grid],
            }
            history.append(committed)
            state = {**state, "history": history, "pending": None, "status": "running"}
            atomic_json(checkpoint, state)
            atomic_json(
                progress,
                {
                    "game": game,
                    "target_role": role,
                    "arm": arm,
                    "status": "running",
                    "actions_committed": len(history),
                    "levels_completed": after_record["levels_completed"],
                    "last_action": action_id,
                    "last_reason": decision_dict["reason"],
                    "controller": controller.report(),
                },
            )
            append_jsonl(trace, {key: value for key, value in committed.items() if not key.endswith("_grid")})
            observation = successor
            if level_delta > 0:
                break
    finally:
        arcade.close_scorecard()

    final_record = observation_record(observation)
    verification_recordings = artifacts / "recordings" / game / arm / "verification"
    replay_verified = verify_history(
        environments, verification_recordings, game, history
    )
    result = {
        "game": game,
        "target_role": role,
        "arm": arm,
        "job_key": expected_key,
        "resumed": resumed,
        "actions": len(history),
        "levels_completed": int(final_record["levels_completed"]),
        "first_level_completed": int(final_record["levels_completed"]) >= 1,
        "final_state": final_record["state"],
        "final_digest": final_record["digest"],
        "replay_verified": replay_verified,
        "controller": controller.report(),
        "elapsed_this_process_s": time.perf_counter() - started,
    }
    atomic_json(result_path, result)
    state = {**state, "history": history, "pending": None, "status": "completed", "result": result}
    atomic_json(checkpoint, state)
    atomic_json(progress, {**result, "status": "completed"})
    return result


def append_status(message: str) -> None:
    with (HERE / "STATUS.md").open("a", encoding="utf-8") as stream:
        stream.write(message.rstrip() + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def analyze(results: Sequence[dict[str, Any]], output: Path) -> dict[str, Any]:
    by_role: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        by_role[str(result["target_role"])][str(result["arm"])] = result
    positive = by_role["positive"]
    negative = by_role["negative"]
    scratch = positive["scratch"]
    improvements: list[dict[str, Any]] = []
    for arm in ("self_transfer", "external", "combined"):
        result = positive[arm]
        completion_gain = bool(result["first_level_completed"] and not scratch["first_level_completed"])
        savings = None
        savings_fraction = None
        if result["first_level_completed"] and scratch["first_level_completed"]:
            savings = int(scratch["actions"]) - int(result["actions"])
            savings_fraction = savings / int(scratch["actions"]) if scratch["actions"] else 0.0
        improvements.append(
            {
                "arm": arm,
                "completion_gain": completion_gain,
                "action_savings": savings,
                "action_savings_fraction": savings_fraction,
            }
        )
    negative_regression = any(
        (
            int(negative[arm]["levels_completed"]) < int(negative["scratch"]["levels_completed"])
            or (
                negative["scratch"]["first_level_completed"]
                and not negative[arm]["first_level_completed"]
            )
        )
        for arm in ("self_transfer", "external", "combined")
    )
    promising = any(
        item["completion_gain"]
        or (
            item["action_savings_fraction"] is not None
            and item["action_savings_fraction"] >= 0.25
        )
        for item in improvements
    ) and not negative_regression
    bound_and_acted = any(
        positive[arm]["controller"]["prior_decisions"] > 0
        for arm in ("self_transfer", "external", "combined")
    )
    if promising:
        verdict = "PROMISING"
    elif negative_regression or bound_and_acted:
        verdict = "NEGATIVE"
    else:
        verdict = "INCONCLUSIVE"
    summary = {
        "verdict": verdict,
        "negative_regression": negative_regression,
        "improvements": improvements,
        "all_replay_verified": all(item["replay_verified"] for item in results),
        "arms": sorted(results, key=lambda item: (item["target_role"], item["arm"])),
    }
    atomic_json(output, summary)
    return summary


def write_results(summary: dict[str, Any], selected: dict[str, Any], config: dict[str, Any]) -> None:
    rows = []
    for item in summary["arms"]:
        controller = item["controller"]
        rows.append(
            f"| {item['target_role']} | {item['game']} | {item['arm']} | "
            f"{item['actions']} | {item['levels_completed']} | "
            f"{controller['prior_decisions']} | {controller['local_confirmations']} | "
            f"{controller['abstentions']} | {item['replay_verified']} |"
        )
    text = "\n".join(
        [
            "# Prior-Accelerated Relational Transfer v0 — Results",
            "",
            f"Verdict: **{summary['verdict']}**.",
            "",
            f"Mechanically selected positive target: `{selected['positive']['game']}` "
            f"at source-distance `{selected['positive']['source_distance']}`.",
            f"Mechanically selected negative control: `{selected['negative']['game']}`.",
            f"Action budget per arm: {config['action_budget']}.",
            "",
            "| Role | Game | Arm | Actions | Levels | Prior decisions | Local confirmations | Abstentions | Replay verified |",
            "|---|---|---|---:|---:|---:|---:|---:|---|",
            *rows,
            "",
            "## Transfer comparisons",
            "",
            "```json",
            json.dumps(summary["improvements"], indent=2, sort_keys=True),
            "```",
            "",
            f"Negative-control regression: `{summary['negative_regression']}`.",
            f"All final ledgers replay-verified: `{summary['all_replay_verified']}`.",
            "",
            "See `selected_targets.json`, `self_built_schema.json`, per-action JSONL traces, and atomic checkpoints for the full audit trail.",
            "",
        ]
    )
    (HERE / "RESULTS.md").write_text(text, encoding="utf-8")


def prepare(args: argparse.Namespace) -> dict[str, Any]:
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    selected = select_targets(args.corpus, args.source, HERE / "selected_targets.json")
    self_schema = learn_source_schema(
        args.source,
        HERE / "self_built_schema.json",
        int(config["source_minimum_decreasing_suffix"]),
    )
    if not self_schema["admitted"]:
        raise RuntimeError("source schema failed its frozen admission rule")
    manifest = {
        "prepared_at": "2026-08-08",
        "files": {
            name: file_hash(HERE / name)
            for name in (
                "PROPOSAL.md",
                "DESIGN_NOTES.md",
                "config.json",
                "external_prior.json",
                "selected_targets.json",
                "self_built_schema.json",
                "experiment.py",
            )
        },
        "source_recording": str(args.source),
        "source_recording_sha256": file_hash(args.source),
        "no_target_actions_executed": True,
    }
    atomic_json(HERE / "FROZEN_MANIFEST.json", manifest)
    append_status(
        "\n## 2026-08-08 — Frozen pre-run checkpoint\n\n"
        f"- Positive target: `{selected['positive']['game']}`; source distance: `{selected['positive']['source_distance']}`.\n"
        f"- Negative target: `{selected['negative']['game']}`.\n"
        f"- Self-built schema admitted with {self_schema['evidence_count']} chronological source transitions.\n"
        "- Source action identities are present only in the audit and absent from transferred schema identity/control.\n"
        "- No target action had been executed when `FROZEN_MANIFEST.json` was written.\n"
    )
    return {"selected": selected, "self_schema": self_schema, "manifest": manifest}


def run_parallel(args: argparse.Namespace) -> dict[str, Any]:
    config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
    selected = json.loads((HERE / "selected_targets.json").read_text(encoding="utf-8"))
    self_schema = json.loads((HERE / "self_built_schema.json").read_text(encoding="utf-8"))
    external = json.loads((HERE / "external_prior.json").read_text(encoding="utf-8"))
    tasks: list[dict[str, Any]] = []
    for role in ("positive", "negative"):
        game = selected[role]["game"]
        for arm in config["arms"]:
            tasks.append(
                {
                    "game": game,
                    "target_role": role,
                    "arm": arm,
                    "config": config,
                    "self_schema": self_schema,
                    "external_prior": external,
                    "job_key": job_key(game, arm, config, selected, self_schema, external),
                    "artifacts": str(HERE / "artifacts"),
                    "environments": str(args.environments),
                }
            )
    append_status(
        "\n## 2026-08-08 — Live run started\n\n"
        f"- Eight real-game arms launched with up to {config['max_parallel_workers']} isolated workers.\n"
        "- Per-action machine progress: `artifacts/progress/`; recoverable ledgers: `artifacts/checkpoints/`.\n"
    )
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=int(config["max_parallel_workers"])) as executor:
        futures = {executor.submit(run_arm, task): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            result = future.result()
            results.append(result)
            append_status(
                f"- Partial arm: `{task['target_role']}/{task['game']}/{task['arm']}` "
                f"completed with actions={result['actions']}, levels={result['levels_completed']}, "
                f"prior_decisions={result['controller']['prior_decisions']}, "
                f"replay_verified={result['replay_verified']}."
            )
    summary = analyze(results, HERE / "artifacts" / "summary.json")
    write_results(summary, selected, config)
    append_status(
        "\n## 2026-08-08 — Live run complete\n\n"
        f"- Verdict: `{summary['verdict']}`.\n"
        f"- All final ledgers replay-verified: `{summary['all_replay_verified']}`.\n"
    )
    return summary


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    subparsers = value.add_subparsers(dest="command", required=True)
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    prepare_parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
    subparsers.add_parser("analyze")
    return value


def main() -> None:
    args = parser().parse_args()
    if args.command == "prepare":
        result = prepare(args)
    elif args.command == "run":
        result = run_parallel(args)
    else:
        arm_results = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((HERE / "artifacts" / "arms").glob("*.json"))
        ]
        selected = json.loads((HERE / "selected_targets.json").read_text(encoding="utf-8"))
        config = json.loads((HERE / "config.json").read_text(encoding="utf-8"))
        result = analyze(arm_results, HERE / "artifacts" / "summary.json")
        write_results(result, selected, config)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
