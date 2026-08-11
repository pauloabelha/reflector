"""Exact replay oracle and microbenchmark for batched ObjectAdded reduction."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import importlib.util
import json
from pathlib import Path
import statistics
import sys
import time
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent


def load_graph() -> Any:
    spec = importlib.util.spec_from_file_location(
        "object_batch_benchmark_graph", HERE / "epistemic_graph.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


GRAPH = load_graph()


def load_qwen() -> Any:
    spec = importlib.util.spec_from_file_location(
        "object_batch_benchmark_qwen", HERE / "qwen_cognition.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def object_spec(index: int, dependencies: Sequence[str] = ()) -> dict[str, Any]:
    return {
        "kind": "benchmark_object",
        "created_by": "r2",
        "identity": {"index": index},
        "payload": {"index": index, "parity": index % 2},
        "dependency_ids": tuple(dependencies),
        "event_key": f"benchmark:{index}",
    }


def sequential(state: Any, specs: Sequence[Mapping[str, Any]]) -> Any:
    events = []
    for value in specs:
        state, event, _object_id = GRAPH._ingest_object(
            state,
            kind=value["kind"], created_by=value["created_by"],
            identity=value["identity"], payload=value["payload"],
            dependency_ids=value["dependency_ids"], event_key=value["event_key"],
        )
        if event is not None:
            events.append(event)
    return state, tuple(events)


def microbenchmark(existing: int, batch_size: int, rounds: int) -> dict[str, Any]:
    predecessor_specs = [object_spec(index) for index in range(existing)]
    predecessor = GRAPH.ingest_object_batch(
        GRAPH.GraphState(), predecessor_specs
    ).state
    batch_specs = [object_spec(existing + index) for index in range(batch_size)]
    sequential_times = []
    batch_times = []
    for _round in range(rounds):
        started = time.perf_counter()
        expected_state, expected_events = sequential(predecessor, batch_specs)
        sequential_times.append(time.perf_counter() - started)

        started = time.perf_counter()
        observed = GRAPH.ingest_object_batch(predecessor, batch_specs)
        batch_times.append(time.perf_counter() - started)

        assert [asdict(item) for item in observed.events] == [
            asdict(item) for item in expected_events
        ]
        assert asdict(observed.state) == asdict(expected_state)
    sequential_median = statistics.median(sequential_times)
    batch_median = statistics.median(batch_times)
    return {
        "existing_objects": existing,
        "batch_objects": batch_size,
        "rounds": rounds,
        "sequential_seconds": sequential_times,
        "batch_seconds": batch_times,
        "sequential_median_seconds": sequential_median,
        "batch_median_seconds": batch_median,
        "speedup": sequential_median / batch_median,
        "exact_event_and_state_equality": True,
    }


def graph_documents(workspace: Path) -> list[tuple[str, list[dict[str, Any]]]]:
    output = []
    for path in sorted((workspace / "events").glob("*.json")):
        outer = json.loads(path.read_text(encoding="utf-8"))
        payload = outer["payload"]
        if outer["event_type"] == "EpistemicGraphEvent":
            digest = payload["graph_event_blob"]
            documents = [json.loads(
                (workspace / "blobs" / "sha256" / f"{digest}.json").read_text(
                    encoding="utf-8"
                )
            )]
        elif outer["event_type"] == "EpistemicGraphBatch":
            digest = payload["graph_batch_blob"]
            envelope = json.loads(
                (workspace / "blobs" / "sha256" / f"{digest}.json").read_text(
                    encoding="utf-8"
                )
            )
            documents = envelope["documents"]
        else:
            continue
        output.append((outer["event_type"], documents))
    return output


def full_workspace_specs(
    workspace: Path, events: Sequence[Any]
) -> list[dict[str, Any]]:
    """Recreate the complete hot-path spec stream, including dedup candidates."""
    summary_item = next(
        event.payload["item"]
        for event in reversed(events)
        if event.event_type == "ObjectAdded"
        and event.payload["item"]["kind"] == "runtime_summary"
    )
    summary_payload = json.loads(summary_item["payload_json"])
    workspace_digest = summary_payload["workspace_blob"]
    document = json.loads(
        (workspace / "blobs" / "sha256" / f"{workspace_digest}.json").read_text(
            encoding="utf-8"
        )
    )
    specs: list[dict[str, Any]] = []
    schema_ids: dict[str, str] = {}
    for item in document["schemas"]:
        value = {
            "kind": "schema",
            "created_by": "r2",
            "identity": {"r2_schema_hash": item["id"]},
            "payload": {"atoms": item["atoms"]},
            "dependency_ids": (),
            "event_key": f"r2-schema:{item['id']}",
        }
        specs.append(value)
        schema_ids[str(item["id"])] = GRAPH.make_object(
            kind=value["kind"], created_by=value["created_by"], created_revision=0,
            identity=value["identity"], payload=value["payload"], dependency_ids=(),
        ).object_id
    for kind, values in (
        ("r2_binding", document["bindings"]),
        ("partial_binding", document["partial_bindings"]),
        ("shadow", document["shadows"]),
        ("explanation", document["explanations"]),
    ):
        for item in values:
            schema_hashes = (
                [str(item["schema"])] if item.get("schema")
                else [str(value) for value in item.get("schemas", ())]
            )
            payload = {
                key: value for key, value in item.items()
                if key != "activation_milli"
            }
            semantic = GRAPH.stable_hash({"kind": kind, "value": payload})
            specs.append({
                "kind": kind,
                "created_by": "r2",
                "identity": {"semantic_hash": semantic},
                "payload": payload,
                "dependency_ids": tuple(
                    schema_ids[value] for value in schema_hashes if value in schema_ids
                ),
                "event_key": f"r2-{kind}:{semantic}",
            })
    specs.append({
        "kind": "runtime_summary",
        "created_by": "r2",
        "identity": json.loads(summary_item["identity_json"]),
        "payload": summary_payload,
        "dependency_ids": tuple(summary_item["dependency_ids"]),
        "event_key": (
            "r2-runtime:"
            + str(json.loads(summary_item["identity_json"])["observation_key"])
        ),
    })
    return specs


def frozen_replay_oracle(workspace: Path) -> dict[str, Any]:
    state = GRAPH.GraphState()
    all_events = []
    compared_batches = 0
    compared_objects = 0
    for outer_type, documents in graph_documents(workspace):
        events = tuple(GRAPH.event_from_document(item) for item in documents)
        all_events.extend(events)
        kinds = [
            event.payload["item"].get("kind")
            for event in events
            if event.event_type == "ObjectAdded"
        ]
        is_workspace_batch = (
            outer_type == "EpistemicGraphBatch"
            and events
            and len(kinds) == len(events)
            and "r2_binding" in kinds
        )
        if is_workspace_batch:
            specs = full_workspace_specs(workspace, events)
            expected = state
            for event in events:
                expected = GRAPH.apply_event(expected, event)
            observed = GRAPH.apply_object_events_batch(state, events)
            regenerated = GRAPH.ingest_object_batch(state, specs)
            assert [asdict(item) for item in regenerated.events] == [
                asdict(item) for item in events
            ]
            assert asdict(observed) == asdict(expected)
            assert asdict(regenerated.state) == asdict(expected)
            assert GRAPH.state_document(observed) == GRAPH.state_document(expected)
            state = observed
            compared_batches += 1
            compared_objects += len(events)
        else:
            for event in events:
                state = GRAPH.apply_event(state, event)
    started = time.perf_counter()
    sequential_final = GRAPH.GraphState()
    for event in all_events:
        sequential_final = GRAPH.apply_event(sequential_final, event)
    sequential_replay_seconds = time.perf_counter() - started
    started = time.perf_counter()
    batched_final = GRAPH.replay(all_events)
    batched_replay_seconds = time.perf_counter() - started
    assert asdict(batched_final) == asdict(sequential_final) == asdict(state)
    return {
        "workspace": str(workspace),
        "workspace_batches_compared": compared_batches,
        "object_events_compared": compared_objects,
        "final_revision": state.revision,
        "final_object_count": len(state.objects),
        "final_state_hash": GRAPH.state_document(state)["state_hash"],
        "exact_state_equality_after_every_workspace_batch": True,
        "byte_exact_event_regeneration_after_every_workspace_batch": True,
        "full_sequential_replay_seconds": sequential_replay_seconds,
        "full_batched_replay_seconds": batched_replay_seconds,
        "full_replay_speedup": sequential_replay_seconds / batched_replay_seconds,
    }


def build_turn_benchmark(workspace: Path) -> dict[str, Any]:
    qwen = load_qwen()
    documents = [
        document
        for _outer_type, values in graph_documents(workspace)
        for document in values
    ]
    events = tuple(qwen.GRAPH.event_from_document(item) for item in documents)
    state = qwen.GRAPH.replay(events)
    orientation_document = json.loads(
        (workspace / "qwen_orientation.json").read_text(encoding="utf-8")
    )
    orientation = qwen.orientation_from_document(
        orientation_document, workspace_id=workspace.name
    )
    original_replay = qwen.GRAPH.replay

    def sequential_replay(values: Sequence[Any]) -> Any:
        next_state = qwen.GRAPH.GraphState()
        for event in values:
            next_state = qwen.GRAPH.apply_event(next_state, event)
        return next_state

    qwen.GRAPH.replay = sequential_replay
    try:
        started = time.perf_counter()
        sequential_turn = qwen.build_turn(
            state, events, orientation,
            request_id="qr:object-batch-benchmark",
            token_budget=6400, max_deltas=10_000, compact_ids=True,
        )
        sequential_seconds = time.perf_counter() - started
    finally:
        qwen.GRAPH.replay = original_replay

    started = time.perf_counter()
    batched_turn = qwen.build_turn(
        state, events, orientation,
        request_id="qr:object-batch-benchmark",
        token_budget=6400, max_deltas=10_000, compact_ids=True,
    )
    batched_seconds = time.perf_counter() - started
    assert asdict(batched_turn) == asdict(sequential_turn)
    return {
        "workspace": str(workspace),
        "sequential_build_turn_seconds": sequential_seconds,
        "batched_build_turn_seconds": batched_seconds,
        "build_turn_speedup": sequential_seconds / batched_seconds,
        "exact_turn_equality": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--existing", type=int, default=3000)
    parser.add_argument("--batch-size", type=int, default=700)
    parser.add_argument("--rounds", type=int, default=3)
    parser.add_argument("--workspace", action="append", type=Path, default=[])
    parser.add_argument("--build-turn", action="store_true")
    args = parser.parse_args()
    result = {
        "microbenchmark": microbenchmark(args.existing, args.batch_size, args.rounds),
        "frozen_replay_oracles": [
            frozen_replay_oracle(path) for path in args.workspace
        ],
        "build_turn_benchmarks": (
            [build_turn_benchmark(path) for path in args.workspace]
            if args.build_turn else []
        ),
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
