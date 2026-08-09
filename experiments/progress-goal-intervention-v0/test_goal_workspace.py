from __future__ import annotations

from dataclasses import replace
import importlib.util
from pathlib import Path
import sys

import pytest


HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("progress_goal_workspace_v0_test", HERE / "goal_workspace.py")
assert spec is not None and spec.loader is not None
GW = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = GW
spec.loader.exec_module(GW)


def test_oracle_candidate_is_generic_declarative_and_support_zero() -> None:
    candidate = GW.make_candidate(provenance="oracle_intervention")
    document = GW.candidate_object(candidate, attention_boost=37)

    assert candidate.sham is False
    assert candidate.ast["potential"] == {
        "type": "OutsideCount",
        "members": "?members",
        "container": "?container",
        "direction": "minimize",
        "lower_bound": 0,
    }
    assert candidate.ast["terminal"]["type"] == "AllInside"
    assert document["created_by"] == "oracle_intervention"
    assert document["payload"]["attention_boost"] == 37
    assert document["payload"]["empirical_support"] == 0
    assert document["payload"]["intervention_mode"] == "candidate-attention"
    assert document["payload"]["epistemic_authority"] == "attention-only"
    assert document["dependency_ids"] == []
    assert "ports" not in document["payload"]


def test_mock_sham_has_distinct_provenance_and_identity() -> None:
    oracle = GW.make_candidate(provenance="oracle_intervention")
    sham = GW.make_candidate(provenance="mock_intervention", sham=True)

    assert sham.ast == oracle.ast
    assert sham.candidate_id != oracle.candidate_id
    assert GW.candidate_object(sham)["created_by"] == "mock_intervention"
    assert GW.candidate_object(sham)["payload"]["intervention_mode"] == "sham"
    with pytest.raises(GW.GoalWorkspaceError, match="sham and provenance"):
        GW.make_candidate(provenance="oracle_intervention", sham=True)
    with pytest.raises(GW.GoalWorkspaceError, match="sham and provenance"):
        GW.make_candidate(provenance="mock_intervention", sham=False)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("action_id",), 3),
        (("preferred_move",), "LEFT"),
        (("color",), "blue"),
        (("bbox",), [1, 2, 3, 4]),
        (("note",), "31,18"),
        (("game_id",), "ar25"),
        (("note",), "wa30"),
        (("note",), "g50t"),
    ],
)
def test_transferable_candidate_rejects_action_color_coordinate_and_game_leakage(path, value) -> None:
    ast = GW.goal_ast()
    target = ast
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(GW.GoalWorkspaceError, match="forbidden"):
        GW.make_candidate(provenance="oracle_intervention", ast=ast)


def test_ast_is_closed_and_bounded() -> None:
    ast = GW.goal_ast()
    ast["potential"]["type"] = "Distance"
    with pytest.raises(GW.GoalWorkspaceError, match="OutsideCount"):
        GW.validate_ast(ast)

    ast = GW.goal_ast(members_role="members", container_role="?container")
    with pytest.raises(GW.GoalWorkspaceError, match="two distinct bounded roles"):
        GW.validate_ast(ast)

    ast = GW.goal_ast()
    ast["terminal"]["members"] = "?container"
    with pytest.raises(GW.GoalWorkspaceError, match="AllInside"):
        GW.validate_ast(ast)


def test_candidate_identity_covers_ast_provenance_and_sham() -> None:
    candidate = GW.make_candidate(provenance="oracle_intervention")
    changed = replace(candidate, candidate_id="gp:" + "0" * 64)
    with pytest.raises(GW.GoalWorkspaceError, match="identity mismatch"):
        GW.validate_candidate(changed)


def test_situated_binding_is_optional_separate_and_addressed() -> None:
    candidate = GW.make_candidate(provenance="oracle_intervention")
    binding = GW.make_binding(
        candidate,
        observation_id="obs:0007",
        members=("entity:m0", "entity:m1"),
        container="entity:target",
    )
    document = GW.binding_object(binding)

    assert document["created_by"] == "oracle_intervention"
    assert document["payload"]["ports"] == {
        "?members": ["entity:m0", "entity:m1"],
        "?container": "entity:target",
    }
    assert document["payload"]["empirical_support"] == 0
    assert document["dependency_ids"] == [
        candidate.candidate_id,
        "obs:0007",
        "entity:m0",
        "entity:m1",
        "entity:target",
    ]


def test_situated_binding_enforces_population_and_address_bounds() -> None:
    candidate = GW.make_candidate(provenance="oracle_intervention")
    with pytest.raises(GW.GoalWorkspaceError, match="population"):
        GW.make_binding(
            candidate,
            observation_id="obs:1",
            members=(),
            container="entity:t",
        )
    with pytest.raises(GW.GoalWorkspaceError, match="container"):
        GW.make_binding(
            candidate,
            observation_id="obs:1",
            members=("entity:t",),
            container="entity:t",
        )
    with pytest.raises(GW.GoalWorkspaceError, match="opaque stable"):
        GW.make_binding(
            candidate,
            observation_id="obs:1",
            members=("31,18",),
            container="entity:t",
        )


def test_only_environment_can_create_support_change() -> None:
    candidate = GW.make_candidate(provenance="oracle_intervention")
    binding = GW.make_binding(
        candidate,
        observation_id="obs:1",
        members=("entity:m",),
        container="entity:t",
    )
    with pytest.raises(GW.GoalWorkspaceError, match="only environment"):
        GW.environment_support_object(
            candidate_id=candidate.candidate_id,
            binding_id=binding.binding_id,
            evidence_ids=("transition:1",),
            support_delta=10,
            actor="oracle_intervention",
        )
    with pytest.raises(GW.GoalWorkspaceError, match="nonzero bounded"):
        GW.environment_support_object(
            candidate_id=candidate.candidate_id,
            binding_id=binding.binding_id,
            evidence_ids=("transition:1",),
            support_delta=0,
            actor="environment",
        )

    evidence = GW.environment_support_object(
        candidate_id=candidate.candidate_id,
        binding_id=binding.binding_id,
        evidence_ids=("transition:1", "prediction:1"),
        support_delta=10,
        actor="environment",
    )
    assert evidence["created_by"] == "environment"
    assert evidence["payload"]["empirical_support_delta"] == 10
    assert evidence["dependency_ids"] == [
        candidate.candidate_id,
        binding.binding_id,
        "transition:1",
        "prediction:1",
    ]


def test_attention_never_aliases_support() -> None:
    candidate = GW.make_candidate(provenance="mock_intervention", sham=True)
    for boost in (0, 100):
        document = GW.candidate_object(candidate, attention_boost=boost)
        assert document["payload"]["attention_boost"] == boost
        assert document["payload"]["empirical_support"] == 0
    with pytest.raises(GW.GoalWorkspaceError, match="attention boost"):
        GW.candidate_object(candidate, attention_boost=101)
