from __future__ import annotations

import pytest

from reflector2.epistemic_workspace import (
    EpistemicWorkspaceError,
    SharedEpistemicWorkspace,
)
from reflector2.perception import perceive_grid
from reflector2.runtime import Runtime


def _native_runtime() -> Runtime:
    runtime = Runtime()
    runtime.observe(
        perceive_grid(
            runtime.graph.terms,
            (
                (0, 0, 0, 0),
                (0, 2, 2, 0),
                (0, 2, 2, 0),
                (0, 0, 0, 0),
            ),
            context="frame:0",
        )
    )
    return runtime


def test_native_r2_schemas_and_bindings_enter_one_shared_world() -> None:
    runtime = _native_runtime()
    epistemic = SharedEpistemicWorkspace()

    object_ids = epistemic.ingest_native_runtime(runtime)

    assert object_ids
    assert {item.creator for item in epistemic.objects} == {"r2"}
    bindings = [item for item in epistemic.objects if item.kind == "binding"]
    assert bindings
    for binding in bindings:
        assert len(binding.dependency_ids) == 1
        assert epistemic.object(binding.dependency_ids[0]).kind == "schema"
        assert epistemic.support(binding.object_id) == 0

    qwen = epistemic.frontier(
        worker="qwen", budget=100_000, root_limit=len(epistemic.objects)
    )
    assert set(binding.object_id for binding in bindings).issubset(qwen.object_ids)
    assert set(qwen.mandatory_ids).issubset(qwen.object_ids)


def test_compute_changes_attention_but_only_reality_changes_support() -> None:
    epistemic = SharedEpistemicWorkspace()
    proposal = epistemic.add_object(
        kind="explanation",
        semantic_key={"claim": "x"},
        payload={"claim": "x deserves examination"},
        creator="qwen",
    )
    epistemic.attend(
        worker="r2",
        object_id=proposal.object_id,
        weight=500,
        channel="qwen-proposal",
    )
    assert epistemic.attention(proposal.object_id, "r2") == 500
    assert epistemic.support(proposal.object_id) == 0

    with pytest.raises(EpistemicWorkspaceError, match="empirical authority"):
        epistemic.add_object(
            kind="explanation",
            semantic_key={"claim": "forged"},
            payload={"claim": "forged", "support": 1},
            creator="qwen",
        )
    with pytest.raises(EpistemicWorkspaceError, match="only the environment"):
        epistemic.add_environment_evidence(
            target_id=proposal.object_id,
            verdict="supports",
            transition_id="transition:0",
            payload={"direct": True},
            actor="qwen",
        )

    epistemic.add_environment_evidence(
        target_id=proposal.object_id,
        verdict="supports",
        transition_id="transition:0",
        payload={"direct": True, "observed_delta": -1},
    )
    assert epistemic.support(proposal.object_id) == 1


def test_live_competing_bindings_and_dependencies_are_mandatory() -> None:
    epistemic = SharedEpistemicWorkspace()
    schema = epistemic.add_object(
        kind="schema",
        semantic_key={"body": "relation(?a,?b)"},
        payload={"body": "relation(?a,?b)"},
        creator="qwen",
    )
    bindings = [
        epistemic.add_object(
            kind="binding",
            semantic_key={"schema": schema.object_id, "candidate": index},
            payload={
                "status": "ambiguous",
                "candidate": index,
                "competition_set_id": schema.object_id,
            },
            creator="r2",
            dependency_ids=(schema.object_id,),
        )
        for index in range(3)
    ]
    noise = epistemic.add_object(
        kind="explanation",
        semantic_key={"noise": True},
        payload={"noise": True},
        creator="qwen",
    )
    epistemic.attend(
        worker="qwen", object_id=noise.object_id, weight=999, channel="noise"
    )

    frontier = epistemic.frontier(worker="qwen", budget=10_000, root_limit=0)

    assert set(frontier.object_ids) == {
        schema.object_id,
        *(binding.object_id for binding in bindings),
    }
    assert noise.object_id not in frontier.object_ids


def test_native_binding_census_is_exact_but_not_a_false_competition_set() -> None:
    runtime = _native_runtime()
    epistemic = SharedEpistemicWorkspace()
    epistemic.ingest_native_runtime(runtime)

    native_bindings = [item for item in epistemic.objects if item.kind == "binding"]
    assert native_bindings
    assert all(
        item.payload["competition_set_id"] is None for item in native_bindings
    )

    # The complete census remains durable/addressable, while a bounded worker
    # cut can omit low-attention background matches without losing authority.
    frontier = epistemic.frontier(worker="qwen", budget=1_500, root_limit=2)
    assert frontier.mandatory_ids == ()
    assert len(frontier.object_ids) < len(epistemic.objects)


def test_hash_chained_replay_and_lossless_worker_cursor() -> None:
    epistemic = SharedEpistemicWorkspace()
    schema = epistemic.add_object(
        kind="schema",
        semantic_key={"body": "p(?x)"},
        payload={"body": "p(?x)"},
        creator="r2",
    )
    cursor = epistemic.revision
    epistemic.attend(
        worker="qwen",
        object_id=schema.object_id,
        weight=10,
        channel="r2-discovery",
        nonce=1,
    )
    epistemic.add_environment_evidence(
        target_id=schema.object_id,
        verdict="refutes",
        transition_id="transition:1",
        payload={"direct": True},
    )

    deltas = epistemic.deltas(cursor)
    assert [item.event_type for item in deltas] == [
        "attention-contributed",
        "environment-evidence",
    ]
    replayed = SharedEpistemicWorkspace.replay(epistemic.event_documents())
    assert replayed.event_documents() == epistemic.event_documents()
    assert replayed.head_hash == epistemic.head_hash
    assert replayed.support(schema.object_id) == -1


def test_stable_identity_collision_is_never_silently_accepted() -> None:
    epistemic = SharedEpistemicWorkspace()
    epistemic.add_object(
        kind="schema",
        semantic_key={"body": "p(?x)"},
        payload={"body": "p(?x)"},
        creator="r2",
    )
    with pytest.raises(EpistemicWorkspaceError, match="different content"):
        epistemic.add_object(
            kind="schema",
            semantic_key={"body": "p(?x)"},
            payload={"body": "changed"},
            creator="r2",
        )
