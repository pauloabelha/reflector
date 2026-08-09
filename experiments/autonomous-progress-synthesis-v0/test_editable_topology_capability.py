from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location(
    "autonomous_editable_topology_capability_test",
    HERE / "editable_topology_capability.py",
)
assert spec is not None and spec.loader is not None
M = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = M
spec.loader.exec_module(M)


def scene():
    return (
        (1, 1, 0, 5, 5, 7, 7),
        (1, 1, 0, 5, 5, 7, 7),
        (0, 0, 0, 5, 5, 0, 0),
        (0, 0, 0, 5, 5, 8, 8),
    )


def capability(**overrides):
    options = {
        "simple_actions": (101,),
        "parameterized_actions": (907,),
        "max_depth": 4,
        "max_expansions": 100,
    }
    options.update(overrides)
    return M.compile_capability(scene(), **options)


def test_compile_is_game_blind_support_zero_and_separates_binding() -> None:
    item = capability()
    generic = M.workspace_document(item)
    situated = M.workspace_document(item, include_binding=True)

    assert item.empirical_support == 0
    assert item.goal_ast == M.generic_goal_ast()
    assert item.goal_ast["potential"]["type"] == "UnresolvedTopologyCount"
    assert item.goal_ast["mechanism"]["type"] == "EditableTopology"
    assert "situated_binding" not in generic
    assert situated["situated_binding"]["grounded_parameter_count"] > 0
    assert situated["empirical_support"] == 0
    generic_text = json.dumps(generic, sort_keys=True).lower()
    for forbidden in ("action_id", "opaque_action", "color", "coordinate", "game_id", '"x"', '"y"'):
        assert forbidden not in generic_text


def test_opaque_channels_are_inputs_not_constants() -> None:
    first = capability(simple_actions=(101,), parameterized_actions=(907,))
    second = capability(simple_actions=(13,), parameterized_actions=(29,))
    assert first.goal_ast == second.goal_ast
    assert first.candidate_id == second.candidate_id
    # Situated identities change, but transferable semantics do not.
    assert first.binding_id != second.binding_id
    assert [row.action_id for row in first.interventions] != [
        row.action_id for row in second.interventions
    ]
    assert all(row.token.startswith("iv:") for row in first.interventions)
    assert all(str(row.action_id) not in row.token for row in first.interventions)


def test_bounded_search_discovers_a_topology_edit_without_assuming_semantics() -> None:
    item = capability()

    def observe(prefix):
        opened = False
        position = 0
        for intervention in prefix:
            if intervention.data:
                opened = True
            elif opened or position == 0:
                position += 1
        return {"key": (position, opened), "done": position >= 2}

    result = M.plan(
        item,
        observe_prefix=observe,
        state_key=lambda state: state["key"],
        completed=lambda state: bool(state["done"]),
    )
    assert len(result.commands) == 3
    assert not result.commands[0].data
    assert result.commands[1].data
    assert not result.commands[2].data
    assert result.expanded <= item.max_expansions
    assert result.empirical_support == 0


def test_search_failure_and_configuration_are_hard_bounded() -> None:
    item = capability(max_depth=2, max_expansions=3)
    with pytest.raises(M.TOPOLOGY.NoEditableTopologyPlan):
        M.plan(
            item,
            observe_prefix=lambda _prefix: {"key": "same", "done": False},
            state_key=lambda state: state["key"],
            completed=lambda state: bool(state["done"]),
        )
    with pytest.raises(M.TopologyCapabilityError, match="search bound"):
        capability(max_depth=M.MAX_DEPTH + 1)
    with pytest.raises(M.TopologyCapabilityError, match="disjoint"):
        M.compile_capability(
            scene(),
            simple_actions=(5,),
            parameterized_actions=(5,),
        )


def test_registry_adapter_preserves_attention_support_separation() -> None:
    item = capability()
    row = M.registry_proposal(item)
    assert row == {
        "capability": "interactive:editable-topology",
        "goal_ast": item.goal_ast,
        "attention": 75,
        "empirical_support": 0,
        "execution": item,
        "interactive": True,
    }


def test_only_environment_can_adjudicate_support() -> None:
    item = capability()
    with pytest.raises(M.TopologyCapabilityError, match="only environment"):
        M.adjudicate(
            item,
            transition_ids=("transition:1",),
            completed=True,
            direct=True,
            actor="planner",
        )
    indirect = M.adjudicate(
        item,
        transition_ids=("transition:1",),
        completed=True,
        direct=False,
        actor="environment",
    )
    assert indirect.support_delta == 0
    direct = M.adjudicate(
        item,
        transition_ids=("transition:1", "transition:2"),
        completed=True,
        direct=True,
        actor="environment",
    )
    assert direct.support_delta == 1
    assert direct.created_by == "environment"


def test_consumed_development_aggregate_respects_adapter_bounds() -> None:
    # Consumes only the prior experiment's aggregate RESULT. No frame, source,
    # recording, target identity, or outcome-specific constant enters the adapter.
    result_path = (
        HERE.parent
        / "progress-drive-editable-topology-v0/artifacts/oracle-search/RESULT.json"
    )
    aggregate = json.loads(result_path.read_text(encoding="utf-8"))
    assert len(aggregate["actions"]) <= M.MAX_DEPTH
    assert len(aggregate["clicks"]) <= M.MAX_POINTS
    assert aggregate["expanded"] <= M.MAX_EXPANSIONS
