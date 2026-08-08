"""Safeguards for the fixed 25-game context-spinoff diagnostic."""

from __future__ import annotations

import importlib.util
import inspect
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUNNER_PATH = HERE / "run_diagnostic.py"


def _load_runner():
    name = "reflector2_r2_25_game_context_spinoff_diagnostic"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


RUNNER = _load_runner()


def _established_binary_relation(runtime, name: str = "GenericRelation") -> int:
    schema_id, _created = runtime.graph.add_schema(
        name,
        [(name, ("?left", "?right"))],
        candidate=False,
        provenance="test:generic-relation",
    )
    return schema_id


def _ambiguous_transitions(relation_id: int):
    return [
        RUNNER.Transition(1, 2, frozenset(), frozenset()),
        RUNNER.Transition(2, 2, frozenset(), frozenset()),
        RUNNER.Transition(3, 3, frozenset({relation_id}), frozenset()),
        RUNNER.Transition(4, 3, frozenset({relation_id}), frozenset()),
    ]


def test_context_discovery_has_no_held_out_successor_input() -> None:
    parameters = inspect.signature(RUNNER._discover_context).parameters
    assert tuple(parameters) == (
        "runtime",
        "transitions",
        "current_features",
        "legal_actions",
        "config",
    )
    forbidden = {"successor", "held_out", "packet", "recorded_action", "level"}
    assert forbidden.isdisjoint(parameters)

    runtime = RUNNER._new_runtime(0)
    relation = _established_binary_relation(runtime)
    condition, reason = RUNNER._discover_context(
        runtime,
        _ambiguous_transitions(relation),
        frozenset(),
        (2, 3),
        RUNNER.DiagnosticConfig(),
    )
    assert reason == "eligible"
    assert condition is not None
    assert condition.schema_id == relation
    assert condition.present is False


def test_candidate_context_and_child_use_only_generic_relational_structure() -> None:
    runtime = RUNNER._new_runtime(0)
    relation = _established_binary_relation(runtime)
    candidates = RUNNER._relation_candidates(runtime, 64)
    assert relation in candidates

    condition = RUNNER.ContextCondition(relation, False, 2, 1.0, 2)
    parent = RUNNER._install_parent(runtime)
    child, created, _edge = RUNNER._install_child(runtime, parent, condition)
    assert created

    serialized = repr(runtime.graph.source_atoms(child)).lower()
    forbidden = {
        "game_id",
        "level_id",
        "coordinate",
        "controlled_object",
        "option",
        "qwen",
        "branch",
        "wall",
        "key",
        "mode",
    }
    assert all(token not in serialized for token in forbidden)
    assert runtime.graph.canonical_hash[relation] in serialized
    assert "bindingabsent" in serialized


def test_spinoff_preserves_parent_exactly() -> None:
    runtime = RUNNER._new_runtime(0)
    relation = _established_binary_relation(runtime)
    parent = RUNNER._install_parent(runtime)
    before_atoms = runtime.graph.source_atoms(parent)
    before_hash = runtime.graph.canonical_hash[parent]

    RUNNER._install_child(
        runtime,
        parent,
        RUNNER.ContextCondition(relation, True, 3, 1.0, 3),
    )

    assert runtime.graph.source_atoms(parent) == before_atoms
    assert runtime.graph.canonical_hash[parent] == before_hash


def test_serial_and_parallel_mapping_are_identical() -> None:
    jobs = [0, 1, 2, 3]
    serial = RUNNER._ordered_process_map(RUNNER._identity_worker, jobs, 1)
    parallel = RUNNER._ordered_process_map(RUNNER._identity_worker, jobs, 2)
    assert parallel == serial


def test_each_worker_starts_with_isolated_r2_state() -> None:
    for workers in (1, 2):
        results = RUNNER._ordered_process_map(
            RUNNER._identity_worker, [11, 12], workers
        )
        assert len(results) == 2
        assert {item["value"] for item in results} == {11, 12}
        assert len({item["kernel"] for item in results}) == 1
        for item in results:
            assert item["initial_schema_count"] + 1 == item["final_schema_count"]


def test_checkpoint_is_atomic_keyed_and_resumable(tmp_path: Path) -> None:
    recording = tmp_path / "sample.recording.jsonl"
    recording.write_text("stable input\n", encoding="utf-8")
    checkpoint = tmp_path / "checkpoint.json"
    job = {
        "game": "opaque",
        "recording": str(recording),
        "environments_root": str(tmp_path / "environments"),
        "config": RUNNER.asdict(RUNNER.DiagnosticConfig()),
        "checkpoint": str(checkpoint),
    }
    result = {"deterministic": {"game": "opaque"}, "timing": {}}
    RUNNER._atomic_json(
        checkpoint,
        {
            "checkpoint_format": RUNNER.CHECKPOINT_FORMAT,
            "key": RUNNER._checkpoint_key(job),
            "result": result,
        },
    )

    assert RUNNER._load_checkpoint(job) == result
    assert not list(tmp_path.glob(".*.tmp"))

    changed = dict(job)
    changed["config"] = {**job["config"], "min_context_support": 3}
    assert RUNNER._load_checkpoint(changed) is None
