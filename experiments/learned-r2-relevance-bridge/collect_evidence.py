#!/usr/bin/env python3
"""Extract observed consequence/progress evidence from public JSONL traces."""

from __future__ import annotations

import argparse
import gc
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from reflector2.perception import PerceptionBatch, perceive_grid
from reflector2.runtime import Runtime

from relevance import (
    EvidenceRecord,
    EffectAtom,
    stable_hash,
    structural_binding_key,
)


def _batch(
    runtime: Runtime,
    observation: Mapping[str, Any],
    *,
    trajectory: str,
) -> tuple[PerceptionBatch, tuple[int, int]]:
    supports = observation.get("supports")
    if not isinstance(supports, list) or not supports:
        raise ValueError("observation has no ordered supports")
    support = supports[-1]
    if not isinstance(support, dict) or "grid" not in support:
        raise ValueError(
            "observation omits its grid; recollect the baseline without --omit-grids"
        )
    grid = support["grid"]
    if not isinstance(grid, list) or not grid or not isinstance(grid[0], list):
        raise ValueError("observation grid is malformed")
    normalized = tuple(tuple(int(cell) for cell in row) for row in grid)
    shape = (len(normalized), len(normalized[0]))
    context = (
        f"evidence:{trajectory}:observation:{int(observation['observation'])}:"
        f"support:{int(support.get('ordinal', len(supports) - 1))}"
    )
    return perceive_grid(runtime.graph.terms, normalized, context), shape


def _binding_key(
    runtime: Runtime,
    schema_id: int,
    before: PerceptionBatch,
    after: PerceptionBatch,
    effects: Sequence[EffectAtom],
) -> str:
    required = {
        str(arguments[1])
        for head, arguments in runtime.graph.source_atoms(schema_id)
        if head == "Before" and len(arguments) == 3
    }
    values: list[tuple[str, object]] = []
    pairs = runtime._correspond_regions(before, after)  # noqa: SLF001 - extractor audit
    if pairs:
        before_region, _after_region, _form = pairs[0]
        relations = {
            str(runtime.graph.terms.value(head)): runtime.graph.terms.value(value)
            for head, value in runtime._entity_relations(  # noqa: SLF001
                before.facts, before_region
            ).items()
        }
        values = sorted(
            (relation, relations[relation])
            for relation in required
            if relation in relations
        )
    return structural_binding_key(effects, values)


def extract_trace(
    path: Path,
    *,
    first_sequence: int,
) -> tuple[tuple[EvidenceRecord, ...], dict[str, Any]]:
    raw = path.read_bytes()
    trace_digest = stable_hash(raw.decode("utf-8"))
    trajectory = f"trajectory:{trace_digest}"
    observations: dict[int, Mapping[str, Any]] = {}
    transitions: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: {error}") from error
        if event.get("event") == "observation":
            observations[int(event["observation"])] = event
        elif event.get("event") == "transition":
            transitions.append(event)
    runtime = Runtime()
    records: list[EvidenceRecord] = []
    skipped_no_effect = 0
    for transition in transitions:
        before_id = int(transition["before"])
        after_id = int(transition["after"])
        if before_id not in observations or after_id not in observations:
            raise ValueError(
                f"{path}: transition {transition.get('transition')} lacks an observation"
            )
        before, shape = _batch(runtime, observations[before_id], trajectory=trajectory)
        after, _after_shape = _batch(
            runtime, observations[after_id], trajectory=trajectory
        )
        action = transition.get("action")
        if not isinstance(action, dict):
            raise ValueError(f"{path}: transition action is malformed")
        action_id = int(action["id"])
        action_token = str(action["token"])
        schema_id = runtime.learn_transition(before, after, action_token)
        effects: tuple[EffectAtom, ...] = tuple(
            (head, tuple(arguments))
            for head, arguments in runtime.graph.source_atoms(schema_id)
            if head in {"Change", "Preserve"}
        )
        if not effects:
            skipped_no_effect += 1
            continue
        transition_index = int(transition["transition"])
        before_head_counts = Counter(
            str(runtime.graph.terms.value(head)) for head, _arguments in before.facts
        )
        stratum = stable_hash(
            {
                "support_shape": list(shape),
                "before_fact_count": len(before.facts),
                "before_region_count": len(before.region_terms),
                "before_relation_counts": dict(sorted(before_head_counts.items())),
            }
        )
        records.append(
            EvidenceRecord(
                sequence=first_sequence + len(records),
                event_id=f"trace-event:{stable_hash([trace_digest, transition_index])}",
                context_id=f"trace-context:{stable_hash([trace_digest, before_id, after_id])}",
                trajectory_id=trajectory,
                pairing_stratum=f"structural-stratum:{stratum}",
                binding_key=_binding_key(
                    runtime, schema_id, before, after, effects
                ),
                consequence=effects,
                progress_delta=float(transition["progress_delta"]),
                opaque_action_id=action_id,
                source=f"historical-public-trace:{path.resolve()}#transition={transition_index}",
            )
        )
    return tuple(records), {
        "path": str(path.resolve()),
        "trace_digest": trace_digest,
        "transitions": len(transitions),
        "records": len(records),
        "skipped_no_structural_effect": skipped_no_effect,
        "outcomes": dict(
            Counter(record.outcome for record in records)
        ),
    }


def extract_official_recording(
    path: Path,
    *,
    first_sequence: int,
) -> tuple[tuple[EvidenceRecord, ...], dict[str, Any]]:
    """Extract consecutive transitions from an ARC toolkit recording."""

    raw = path.read_bytes()
    decoded = raw.decode("utf-8")
    trace_digest = stable_hash(decoded)
    trajectory = f"trajectory:{trace_digest}"
    packets: list[Mapping[str, Any]] = []
    for line_number, line in enumerate(decoded.splitlines(), 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"{path}:{line_number}: {error}") from error
        data = event.get("data")
        if not isinstance(data, dict):
            raise ValueError(f"{path}:{line_number}: recording packet has no data")
        packets.append(data)
    runtime = Runtime()
    records: list[EvidenceRecord] = []
    skipped_no_effect = 0
    skipped_reset = 0
    for packet_index, (prior, current) in enumerate(
        zip(packets, packets[1:], strict=False), 1
    ):
        action = current.get("action_input")
        if not isinstance(action, dict):
            raise ValueError(f"{path}: packet {packet_index} has no action_input")
        action_id = int(action.get("id", 0))
        if action_id == 0 or bool(current.get("full_reset", False)):
            skipped_reset += 1
            continue
        prior_frame = prior.get("frame")
        current_frame = current.get("frame")
        if (
            not isinstance(prior_frame, list)
            or not prior_frame
            or not isinstance(current_frame, list)
            or not current_frame
        ):
            raise ValueError(f"{path}: recording packet omits frame data")
        before_observation = {
            "observation": packet_index - 1,
            "supports": [{"ordinal": 0, "grid": prior_frame[-1]}],
        }
        after_observation = {
            "observation": packet_index,
            "supports": [{"ordinal": 0, "grid": current_frame[-1]}],
        }
        before, shape = _batch(
            runtime, before_observation, trajectory=trajectory
        )
        after, _after_shape = _batch(
            runtime, after_observation, trajectory=trajectory
        )
        schema_id = runtime.learn_transition(
            before, after, f"arc-action:{action_id}"
        )
        effects: tuple[EffectAtom, ...] = tuple(
            (head, tuple(arguments))
            for head, arguments in runtime.graph.source_atoms(schema_id)
            if head in {"Change", "Preserve"}
        )
        if not effects:
            skipped_no_effect += 1
            continue
        before_head_counts = Counter(
            str(runtime.graph.terms.value(head)) for head, _arguments in before.facts
        )
        stratum = stable_hash(
            {
                "support_shape": list(shape),
                "before_fact_count": len(before.facts),
                "before_region_count": len(before.region_terms),
                "before_relation_counts": dict(sorted(before_head_counts.items())),
            }
        )
        progress_delta = float(current.get("levels_completed", 0)) - float(
            prior.get("levels_completed", 0)
        )
        records.append(
            EvidenceRecord(
                sequence=first_sequence + len(records),
                event_id=f"recording-event:{stable_hash([trace_digest, packet_index])}",
                context_id=f"recording-context:{stable_hash([trace_digest, packet_index - 1, packet_index])}",
                trajectory_id=trajectory,
                pairing_stratum=f"structural-stratum:{stratum}",
                binding_key=_binding_key(
                    runtime, schema_id, before, after, effects
                ),
                consequence=effects,
                progress_delta=progress_delta,
                opaque_action_id=action_id,
                source=f"official-recording:{path.resolve()}#packet={packet_index}",
            )
        )
    return tuple(records), {
        "path": str(path.resolve()),
        "format": "arc-toolkit-recording",
        "trace_digest": trace_digest,
        "transitions": max(0, len(packets) - 1),
        "records": len(records),
        "skipped_reset": skipped_reset,
        "skipped_no_structural_effect": skipped_no_effect,
        "outcomes": dict(Counter(record.outcome for record in records)),
    }


def collect(paths: Sequence[Path]) -> tuple[tuple[EvidenceRecord, ...], dict[str, Any]]:
    records: list[EvidenceRecord] = []
    reports: list[dict[str, Any]] = []
    for path in paths:
        first_line = next(
            (line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()),
            "",
        )
        if not first_line:
            raise ValueError(f"{path}: trace is empty")
        first_event = json.loads(first_line)
        extractor = (
            extract_official_recording
            if isinstance(first_event.get("data"), dict)
            else extract_trace
        )
        extracted, report = extractor(path, first_sequence=len(records) + 1)
        records.extend(extracted)
        reports.append(report)
        # Each source is reconstructed in an isolated temporary R2 runtime.
        # Release its large term store before starting the next grid stream.
        gc.collect()
    return tuple(records), {
        "traces": reports,
        "records": len(records),
        "positive_progress_records": sum(
            record.progress_delta > 0 for record in records
        ),
        "ordered_evidence_digest": stable_hash(
            [record.to_dict() for record in records]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trace", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument(
        "--require-positive",
        action="store_true",
        help="reject streams that cannot train the progress bridge",
    )
    args = parser.parse_args()
    records, report = collect(tuple(args.trace))
    if not records:
        raise SystemExit("no structural consequence records were extracted")
    if args.require_positive and not report["positive_progress_records"]:
        raise SystemExit("extracted stream has no genuine positive progress")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(
            json.dumps(record.to_dict(), sort_keys=True, separators=(",", ":"))
            + "\n"
            for record in records
        ),
        encoding="utf-8",
    )
    report_path = args.report or args.output.with_suffix(".report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
