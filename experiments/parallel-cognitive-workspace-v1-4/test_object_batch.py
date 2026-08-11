from __future__ import annotations

from dataclasses import asdict, replace
import importlib.util
from pathlib import Path
import random
import sys
from typing import Any, Mapping, Sequence

import pytest


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("object_batch_graph", HERE / "epistemic_graph.py")
assert SPEC is not None and SPEC.loader is not None
GRAPH = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = GRAPH
SPEC.loader.exec_module(GRAPH)


def spec(
    name: str,
    *,
    creator: str = "r2",
    dependencies: Sequence[str] = (),
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "test_object",
        "created_by": creator,
        "identity": {"name": name},
        "payload": dict(payload or {"name": name}),
        "dependency_ids": tuple(dependencies),
        "event_key": f"test:{name}",
    }


def object_id(value: Mapping[str, Any]) -> str:
    return GRAPH.make_object(
        kind=value["kind"], created_by=value["created_by"], created_revision=0,
        identity=value["identity"], payload=value["payload"],
        dependency_ids=value["dependency_ids"],
    ).object_id


def sequential(state: Any, specs: Sequence[Mapping[str, Any]]):
    events = []
    ids = []
    for value in specs:
        state, event, selected_id = GRAPH._ingest_object(
            state,
            kind=value["kind"],
            created_by=value["created_by"],
            identity=value["identity"],
            payload=value["payload"],
            dependency_ids=value["dependency_ids"],
            event_key=value["event_key"],
        )
        if event is not None:
            events.append(event)
        ids.append(selected_id)
    return state, tuple(events), tuple(ids)


def sequential_replay(events: Sequence[Any]):
    state = GRAPH.GraphState()
    for event in events:
        state = GRAPH.apply_event(state, event)
    return state


def assert_exact(predecessor: Any, specs: Sequence[Mapping[str, Any]]) -> None:
    expected_state, expected_events, expected_ids = sequential(predecessor, specs)
    observed = GRAPH.ingest_object_batch(predecessor, specs)
    assert [GRAPH.event_document(item) for item in observed.events] == [
        GRAPH.event_document(item) for item in expected_events
    ]
    assert observed.object_ids == expected_ids
    assert asdict(observed.state) == asdict(expected_state)
    assert GRAPH.state_document(observed.state) == GRAPH.state_document(expected_state)
    assert GRAPH.metrics(observed.state) == GRAPH.metrics(expected_state)


def test_batch_is_exact_for_dependencies_dedup_and_pickups() -> None:
    qwen = spec("qwen-root", creator="qwen")
    qwen_id = object_id(qwen)
    child = spec("r2-child", dependencies=(qwen_id,))
    child_id = object_id(child)
    grandchild = spec("r2-grandchild", dependencies=(child_id, qwen_id))
    assert_exact(GRAPH.GraphState(), (qwen, child, grandchild, child))

    result = GRAPH.ingest_object_batch(
        GRAPH.GraphState(), (qwen, child, grandchild, child)
    )
    assert len(result.events) == 3
    assert len(result.state.pickups) == 1
    pickup = result.state.pickups[0]
    assert pickup.object_id == qwen_id
    assert pickup.trigger_id == child_id
    assert pickup.created_revision == 1

    environment = spec(
        "environment-child", creator="environment", dependencies=(qwen_id,)
    )
    assert_exact(GRAPH.GraphState(), (qwen, environment))
    assert not GRAPH.ingest_object_batch(
        GRAPH.GraphState(), (qwen, environment)
    ).state.pickups


def test_batch_rejects_forward_or_missing_dependency() -> None:
    future = spec("future")
    broken = spec("broken", dependencies=(object_id(future),))
    with pytest.raises(GRAPH.EpistemicGraphError, match="dependency is missing"):
        GRAPH.ingest_object_batch(GRAPH.GraphState(), (broken, future))


def test_batch_rejects_stable_identity_content_collision() -> None:
    first = spec("same", payload={"version": 1})
    second = spec("same", payload={"version": 2})
    with pytest.raises(GRAPH.EpistemicGraphError, match="stable object identity"):
        GRAPH.ingest_object_batch(GRAPH.GraphState(), (first, second))


def test_batch_rejects_non_object_event() -> None:
    state, event, object_id_value = GRAPH._ingest_object(
        GRAPH.GraphState(), **{
            "kind": "test_object", "created_by": "r2", "identity": {"name": "x"},
            "payload": {}, "dependency_ids": (), "event_key": "x",
        }
    )
    attention = GRAPH.attention_event(
        state, worker="qwen", object_id=object_id_value, weight=1,
        channel="test", basis_ids=(), contribution_key="test",
    )
    with pytest.raises(GRAPH.EpistemicGraphError, match="non-ObjectAdded"):
        GRAPH.apply_object_events_batch(state, (attention,))


@pytest.mark.parametrize("seed", range(12))
def test_randomized_batches_are_byte_exact(seed: int) -> None:
    generator = random.Random(seed)
    specs = []
    ids = []
    for index in range(80):
        dependencies = tuple(
            sorted(generator.sample(ids, k=min(len(ids), generator.randrange(0, 4))))
        )
        value = spec(
            f"n{index:03d}",
            creator="qwen" if index % 7 == 0 else "r2",
            dependencies=dependencies,
            payload={"index": index, "sample": generator.randrange(10_000)},
        )
        specs.append(value)
        ids.append(object_id(value))
        if index % 13 == 0:
            specs.append(value)
    assert_exact(GRAPH.GraphState(), specs)


@pytest.mark.parametrize("seed", range(8))
def test_replay_matches_sequential_reducer_at_every_randomized_prefix(seed: int) -> None:
    generator = random.Random(seed)
    state = GRAPH.GraphState()
    events = []
    object_ids = []
    edge_pairs = set()
    for index in range(45):
        dependencies = tuple(
            sorted(generator.sample(object_ids, k=min(len(object_ids), generator.randrange(3))))
        )
        event = GRAPH.object_event(
            state,
            kind="random_object",
            created_by="qwen" if index % 9 == 0 else "r2",
            identity={"seed": seed, "index": index},
            payload={"sample": generator.randrange(1_000_000)},
            dependency_ids=dependencies,
            event_key=f"random:{seed}:{index}",
        )
        state = GRAPH.apply_event(state, event)
        events.append(event)
        object_ids.append(event.payload["item"]["object_id"])

        if index and index % 7 == 0:
            source, target = object_ids[-2:]
            if (source, target) not in edge_pairs:
                edge = GRAPH.edge_event(
                    state, kind="depends_on", source_id=source, target_id=target,
                    created_by="r2", event_key=f"edge:{seed}:{index}",
                )
                state = GRAPH.apply_event(state, edge)
                events.append(edge)
                edge_pairs.add((source, target))
        if index and index % 11 == 0:
            attention = GRAPH.attention_event(
                state, worker="qwen", object_id=object_ids[-1], weight=3,
                channel="test", basis_ids=(),
                contribution_key=f"attention:{seed}:{index}",
            )
            state = GRAPH.apply_event(state, attention)
            events.append(attention)

    for length in range(len(events) + 1):
        expected = sequential_replay(events[:length])
        observed = GRAPH.replay(events[:length])
        assert asdict(observed) == asdict(expected)
        assert GRAPH.state_document(observed) == GRAPH.state_document(expected)


def test_replay_corrupt_trace_rejects_identically_to_sequential() -> None:
    values = [spec(f"corrupt-{index}") for index in range(8)]
    _state, events, _ids = sequential(GRAPH.GraphState(), values)
    corruptions = []

    corruptions.append((*events[:3], replace(events[3], prev_hash="not-the-head"), *events[4:]))
    corruptions.append((*events[:4], replace(events[4], event_hash="0" * 64), *events[5:]))
    malformed_payload = GRAPH.stable_json({"wrong": {}})
    malformed = replace(events[5], payload_json=malformed_payload)
    malformed_envelope = {
        "seq": malformed.seq, "prev_hash": malformed.prev_hash,
        "event_type": malformed.event_type, "actor": malformed.actor,
        "event_id": malformed.event_id, "payload_json": malformed.payload_json,
    }
    malformed = replace(malformed, event_hash=GRAPH.stable_hash(malformed_envelope))
    corruptions.append((*events[:5], malformed, *events[6:]))

    for corrupted in corruptions:
        with pytest.raises(Exception) as sequential_error:
            sequential_replay(corrupted)
        with pytest.raises(type(sequential_error.value)) as batched_error:
            GRAPH.replay(corrupted)
        assert str(batched_error.value) == str(sequential_error.value)


@pytest.mark.parametrize("seed", range(12))
def test_randomized_corrupt_trace_failure_is_sequentially_identical(seed: int) -> None:
    generator = random.Random(seed)
    values = [
        spec(f"random-corrupt-{seed}-{index}", payload={"sample": generator.randrange(10_000)})
        for index in range(24)
    ]
    _state, events, _ids = sequential(GRAPH.GraphState(), values)
    index = generator.randrange(len(events))
    selected = events[index]
    mode = seed % 3
    if mode == 0:
        corrupted_event = replace(selected, prev_hash=f"bad-prev-{seed}")
    elif mode == 1:
        corrupted_event = replace(selected, event_hash=f"bad-hash-{seed}")
    else:
        corrupted_event = replace(
            selected, payload_json=GRAPH.stable_json({"malformed": seed})
        )
        envelope = {
            "seq": corrupted_event.seq,
            "prev_hash": corrupted_event.prev_hash,
            "event_type": corrupted_event.event_type,
            "actor": corrupted_event.actor,
            "event_id": corrupted_event.event_id,
            "payload_json": corrupted_event.payload_json,
        }
        corrupted_event = replace(
            corrupted_event, event_hash=GRAPH.stable_hash(envelope)
        )
    corrupted = (*events[:index], corrupted_event, *events[index + 1:])

    with pytest.raises(Exception) as sequential_error:
        sequential_replay(corrupted)
    with pytest.raises(type(sequential_error.value)) as batched_error:
        GRAPH.replay(corrupted)
    assert str(batched_error.value) == str(sequential_error.value)
