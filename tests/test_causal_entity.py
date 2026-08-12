from __future__ import annotations

from pathlib import Path
import inspect

import pytest

from reflector2.r2.causal_entity import (
    CausalEntityBinding,
    CausalEntityInducer,
    MemberTransition,
    RegionBinding,
    TransformSignature,
    area,
    boundary,
    fit_residual,
    normalized_shape,
    topology,
)
from reflector2.r2.goal_contract import (
    canonicalize_goal_proposals,
    compile_goal_contract,
)
from reflector2.r2.r2_1_adapter import DefeasibleRoleGrounder, FrameSchemaObserver


def region(name: str, y: int, x: int, value: int = 1, cells=((0, 0), (0, 1))):
    return {
        "binding_id": name,
        "cells": tuple((y + dy, x + dx) for dy, dx in cells),
        "value": value,
    }


def translate(items, dy: int, dx: int, suffix: str, moving=None):
    moving = {item["binding_id"] for item in items} if moving is None else set(moving)
    return [
        {
            **item,
            "binding_id": f"{item['binding_id']}{suffix}",
            "cells": tuple(
                (y + (dy if item["binding_id"] in moving else 0), x + (dx if item["binding_id"] in moving else 0))
                for y, x in item["cells"]
            ),
        }
        for item in items
    ]


def causal_scene(member_count=3, same_color=False):
    moving = [region(chr(97 + i), i * 4, 0, 1 if same_color else i + 1) for i in range(member_count)]
    static = [region("s", 20, 12, 8), region("t", 24, 12, 9)]
    return moving + static


def settle_twice(before, moving_ids, *, action=2):
    inducer = CausalEntityInducer()
    after = translate(before, 1, 0, "1", moving_ids)
    first = inducer.observe_transition(
        before, after, action_scope=action, evidence_ref="transition:1",
        explained_binding_ids=[next(iter(moving_ids))],
        predicted_changed_ids=[next(iter(moving_ids))],
    )
    current_moving = {f"{item}1" for item in moving_ids}
    later = translate(after, 1, 0, "2", current_moving)
    second = inducer.observe_transition(
        after, later, action_scope=action, evidence_ref="transition:2",
        explained_binding_ids=[next(iter(current_moving))],
        predicted_changed_ids=[next(iter(current_moving))],
    )
    return inducer, first, second, after, later


def supported(result):
    return [item for item in result.bindings if item.status == "SUPPORTED"]


def test_disconnected_different_color_members_form_from_repeated_consequence():
    before = causal_scene(3)
    _inducer, first, second, _after, _later = settle_twice(before, {"a", "b", "c"})
    assert first.bindings[0].status == "OPEN"
    assert len(supported(second)) == 1
    assert len(supported(second)[0].member_binding_ids) == 3
    assert supported(second)[0].transform == TransformSignature("translation", (1.0, 0.0))


def test_same_color_stationary_distractor_is_not_a_member():
    before = causal_scene(3, same_color=True)
    before.append(region("d", 12, 0, 1))
    _inducer, _first, second, _after, _later = settle_twice(before, {"a", "b", "c"})
    entity = supported(second)[0]
    assert len(entity.member_binding_ids) == 3
    assert all(not member.startswith("d") for member in entity.member_binding_ids)


def test_global_motion_is_a_competing_explanation_not_a_giant_entity():
    before = [region(name, index * 4, 0, index + 1) for index, name in enumerate("abcd")]
    after = translate(before, 1, 0, "1")
    result = CausalEntityInducer().observe_transition(
        before, after, action_scope=4, evidence_ref="global",
        explained_binding_ids=["a"], predicted_changed_ids=["a"],
    )
    assert result.global_transform == TransformSignature("translation", (1.0, 0.0))
    assert result.bindings == ()
    assert result.residual.ambiguous_global_change


def test_member_breakaway_refutes_large_entity_and_retains_subgroup_candidate():
    before = causal_scene(3)
    inducer, _first, second, _after, later = settle_twice(before, {"a", "b", "c"})
    assert supported(second)
    moving = {item["binding_id"] for item in later if item["binding_id"].startswith(("a", "b"))}
    broken = translate(later, 1, 0, "3", moving)
    predicted_whole = {item["binding_id"] for item in later if item["binding_id"].startswith(("a", "b", "c"))}
    result = inducer.observe_transition(
        later, broken, action_scope=2, evidence_ref="breakaway",
        explained_binding_ids=predicted_whole, predicted_changed_ids=predicted_whole,
    )
    assert any(item.status == "REFUTED" and len(item.member_binding_ids) == 3 for item in result.bindings)
    assert any(item.status == "OPEN" and len(item.member_binding_ids) == 2 for item in result.bindings)


def test_subgroup_and_larger_group_remain_competing_until_settlement():
    before = causal_scene(3)
    inducer, _first, _second, _after, later = settle_twice(before, {"a", "b", "c"})
    moving = {item["binding_id"] for item in later if item["binding_id"].startswith(("a", "b"))}
    broken = translate(later, 1, 0, "3", moving)
    predicted_whole = {item["binding_id"] for item in later if item["binding_id"].startswith(("a", "b", "c"))}
    result = inducer.observe_transition(
        later, broken, action_scope=2, evidence_ref="split",
        explained_binding_ids=predicted_whole, predicted_changed_ids=predicted_whole,
    )
    assert sorted(len(item.member_binding_ids) for item in result.bindings) == [2, 3]


def test_preserved_relative_geometry_has_zero_internal_residual():
    before = causal_scene(3)
    inducer = CausalEntityInducer()
    transitions = inducer.correspond(before, translate(before, 2, -1, "x", {"a", "b", "c"}))
    moving = [item for item in transitions if item.changed]
    assert inducer._internal_residual(moving) == 0.0


def test_internal_relation_violation_is_detectable():
    one = MemberTransition(
        RegionBinding.from_value(region("a", 0, 0)), RegionBinding.from_value(region("a1", 1, 0)),
        TransformSignature("deformation", (1.0,)), 0.0, "la",
    )
    two = MemberTransition(
        RegionBinding.from_value(region("b", 4, 0)), RegionBinding.from_value(region("b1", 8, 0)),
        TransformSignature("deformation", (1.0,)), 0.0, "lb",
    )
    assert CausalEntityInducer._internal_residual([one, two]) > 0.05


def test_translation_does_not_change_normalized_shape_or_topology():
    before = region("a", 2, 3, cells=((0, 0), (0, 1), (1, 0)))
    after = translate([before], 4, -2, "1")[0]
    assert normalized_shape(before) == normalized_shape(after)
    assert topology(before) == topology(after)
    assert len(boundary(before)) == len(boundary(after))


def test_recoloring_is_represented_without_pretending_it_is_translation():
    before = causal_scene(2)
    after = [{**item, "binding_id": item["binding_id"] + "1", "value": item["value"] + 1} for item in before]
    transitions = CausalEntityInducer().correspond(before, after)
    changed = [item for item in transitions if item.changed and item.predecessor.binding_id in {"a", "b"}]
    assert changed and all(item.signature.kind == "recolor" for item in changed)


def test_scaling_signature_is_supported_when_normalized_geometry_is_compatible():
    small = region("a", 0, 0, cells=((0, 0), (0, 1), (1, 0), (1, 1)))
    large = region("a1", 0, 0, cells=tuple((y, x) for y in range(3) for x in range(3)))
    signature = CausalEntityInducer._transform(RegionBinding.from_value(small), RegionBinding.from_value(large))
    assert signature.kind == "scale"


@pytest.mark.parametrize("member_count", [2, 3, 7])
def test_different_member_counts_are_supported_without_fixed_ontology(member_count):
    before = causal_scene(member_count)
    moving = {chr(97 + index) for index in range(member_count)}
    _inducer, _first, second, _after, _later = settle_twice(before, moving)
    assert len(supported(second)[0].member_binding_ids) == member_count


def assembly(name, cells):
    return CausalEntityBinding(
        binding_id=name, entity_id="entity:" + name, cells=tuple(cells),
        member_binding_ids=(name + ":m1", name + ":m2"),
        primitive_member_ids=(name + ":m1", name + ":m2"),
        transform=TransformSignature("translation", (1.0, 0.0)),
        status="SUPPORTED", identity_status="UNIQUE", support=2, contradictions=0,
        evidence=("environment:1", "environment:2"), internal_relation_residual=0.0,
    )


def test_assembly_to_assembly_fit_uses_union_occupancy():
    left = assembly("left", ((0, 0), (0, 2)))
    right = assembly("right", ((0, 1), (0, 3)))
    assert fit_residual(left, right) == 2.0


def test_region_to_assembly_fit_is_polymorphic():
    primitive = region("p", 0, 0, cells=((0, 0), (0, 2)))
    composite = assembly("target", ((0, 0), (0, 2)))
    assert fit_residual(primitive, composite) == 0.0
    assert area(composite) == 2


def test_primitive_bindings_are_not_deleted_when_assembly_exists():
    before = causal_scene(2)
    _inducer, _first, second, _after, later = settle_twice(before, {"a", "b"})
    workspace = [*later, *[item.document() for item in supported(second)]]
    assert sum(item.get("kind") == "causal-entity-binding" for item in workspace) == 1
    assert sum(item.get("kind") != "causal-entity-binding" for item in workspace) == len(later)


def test_high_scope_residual_requests_assembly_accommodation():
    before = causal_scene(3)
    after = translate(before, 1, 0, "1", {"a", "b", "c"})
    result = CausalEntityInducer().observe_transition(
        before, after, action_scope=2, evidence_ref="high",
        explained_binding_ids=["a"], predicted_changed_ids=["a"],
    )
    assert result.residual.coverage == pytest.approx(1 / 3)
    assert result.residual.accommodation_required
    assert result.candidates_generated == 1


def test_low_scope_residual_causes_no_unnecessary_grouping():
    before = causal_scene(3)
    after = translate(before, 1, 0, "1", {"a"})
    result = CausalEntityInducer().observe_transition(
        before, after, action_scope=2, evidence_ref="low",
        explained_binding_ids=["a"], predicted_changed_ids=["a"],
    )
    assert result.residual.coverage == 1.0
    assert not result.residual.accommodation_required
    assert result.bindings == ()


def test_planner_package_does_not_import_or_construct_causal_entities():
    planner = Path(__file__).parents[1] / "src" / "reflector2" / "planner"
    source = "\n".join(path.read_text() for path in planner.glob("*.py"))
    assert "CausalEntityInducer" not in source
    assert "CausalEntityBinding(" not in source


def test_inducer_contains_no_game_or_named_action_ontology():
    source = inspect.getsource(CausalEntityInducer).lower()
    for forbidden in ("ar25", "action_1", "action_2", "move up", "move down", "fit_residual"):
        assert forbidden not in source


def test_simulation_and_geometry_supply_no_empirical_support():
    inducer = CausalEntityInducer()
    left, right = assembly("left", ((0, 0),)), assembly("right", ((1, 0),))
    assert fit_residual(left, right) >= 0
    assert inducer.hypotheses == {}


def test_environment_settlement_supports_then_refutes_assembly_prediction():
    before = causal_scene(2)
    inducer, _first, second, _after, later = settle_twice(before, {"a", "b"})
    assert supported(second)
    moving = {item["binding_id"] for item in later if item["binding_id"].startswith("a")}
    broken = translate(later, 1, 0, "3", moving)
    settled = inducer.observe_transition(
        later, broken, action_scope=2, evidence_ref="environment:break",
        explained_binding_ids=moving, predicted_changed_ids=moving,
    )
    assert any(item.status == "REFUTED" for item in settled.bindings)


def test_candidate_search_is_bounded_and_never_enumerates_power_set():
    before = causal_scene(7)
    result = CausalEntityInducer(max_candidates=2).observe_transition(
        before, translate(before, 1, 0, "1", set("abcdefg")),
        action_scope=2, evidence_ref="bounded",
        explained_binding_ids=["a"], predicted_changed_ids=["a"],
    )
    assert result.candidates_generated <= 1
    assert result.candidates_retained <= 2


def test_entity_identity_is_not_exact_member_binding_id_equality():
    before = causal_scene(2)
    _inducer, first, second, _after, _later = settle_twice(before, {"a", "b"})
    assert first.bindings[0].entity_id == second.bindings[0].entity_id
    assert first.bindings[0].member_binding_ids != second.bindings[0].member_binding_ids


def test_opposite_action_effects_support_one_entity_identity_without_conflict():
    before = causal_scene(3)
    inducer = CausalEntityInducer()
    above = translate(before, -1, 0, "u", {"a", "b", "c"})
    first = inducer.observe_transition(
        before, above, action_scope="north", evidence_ref="environment:north",
    )
    restored = translate(above, 1, 0, "d", {"au", "bu", "cu"})
    second = inducer.observe_transition(
        above, restored, action_scope="south", evidence_ref="environment:south",
    )
    entity = supported(second)[0]
    assert entity.entity_id == first.bindings[0].entity_id
    assert entity.contradictions == 0
    assert dict(entity.action_conditioned_transforms) == {
        "north": (TransformSignature("translation", (-1.0, 0.0)),),
        "south": (TransformSignature("translation", (1.0, 0.0)),),
    }


def test_state_conditioned_effect_variation_does_not_refute_entity_identity():
    before = causal_scene(2)
    inducer = CausalEntityInducer()
    middle = translate(before, 1, 0, "1", {"a", "b"})
    inducer.observe_transition(before, middle, action_scope=2, evidence_ref="state:1")
    after = translate(middle, 2, 0, "2", {"a1", "b1"})
    result = inducer.observe_transition(middle, after, action_scope=2, evidence_ref="state:2")
    entity = supported(result)[0]
    assert entity.contradictions == 0
    assert dict(entity.action_conditioned_transforms)["2"] == (
        TransformSignature("translation", (1.0, 0.0)),
        TransformSignature("translation", (2.0, 0.0)),
    )


def test_live_successor_first_order_uses_saved_predecessor_and_reifies_immediately():
    def frame(offset: int) -> list[list[int]]:
        grid = [[0] * 24 for _ in range(24)]
        for value, y in enumerate((3, 8, 13), start=1):
            grid[y + offset][4] = value
            grid[y + offset][5] = value
        grid[20][18] = 8
        grid[20][19] = 8
        return grid

    observer = FrameSchemaObserver({"enabled": False})
    before, middle, after = frame(0), frame(1), frame(2)
    observer.fit_frame(before, turn=0)
    observer.fit_frame(middle, turn=1)  # Live runtime fits successor first.
    first = observer.settle_action(2, before, middle)
    assert first["causal_scope_residual"]["observed_changed_entities"] >= 3
    assert first["causal_entity_induction"]["candidates_generated"] == 1
    assert not observer.last_causal_entities  # One settlement is still OPEN.

    observer.fit_frame(after, turn=2)
    second = observer.settle_action(2, middle, after)
    assert any(
        item["epistemic_status"] == "SUPPORTED"
        and item["identity_status"] == "UNIQUE"
        and len(item["member_binding_ids"]) == 3
        for item in observer.last_causal_entities
    )
    assert any(
        item["epistemic_status"] == "SUPPORTED"
        for item in second["causal_entity_induction"]["bindings"]
    )
    effect = observer._effect_model(2, observer.last_causal_entities[0])
    assert effect["status"] == "SUPPORTED"
    assert effect["delta"] == (1.0, 0.0)
    assert effect["source"] == "causal-entity-settlement"
    entity_id = observer.last_causal_entities[0]["binding_id"]
    grounded = DefeasibleRoleGrounder(
        observer.last_regions, measure=observer._measure,
        relation_bindings=observer.last_relation_bindings,
    ).ground({
        "verb": "approach", "observable": "centroid_distance",
        "roles": ["actor", "target"], "potential_roles": ["actor", "target"],
        "role_constraints": [],
    })
    assert any(entity_id in item["situated_roles"].values() for item in grounded)


def test_goal_identity_uses_structure_not_lexical_verb_name():
    base = {
        "observable": "fit_residual", "direction": "decrease",
        "local_terminal": {
            "observable": "fit_residual", "preferred_order": "decrease",
            "relation": "equals", "target": 0.0,
        },
    }
    canonical = canonicalize_goal_proposals([
        {**base, "verb": "align"}, {**base, "verb": "contact"}, {**base, "verb": "fit"},
    ])
    assert len(canonical) == 1
    assert canonical[0]["semantic_aliases"] == ("align", "contact", "fit")


def test_different_terminal_targets_do_not_collapse():
    first = {
        "verb": "fit", "observable": "fit_residual", "direction": "decrease",
        "local_terminal": {"observable": "fit_residual", "preferred_order": "decrease", "relation": "equals", "target": 0.0},
    }
    second = {**first, "local_terminal": {**first["local_terminal"], "target": 1.0}}
    assert len(canonicalize_goal_proposals([first, second])) == 2


def test_goal_contract_rejects_unrelated_local_terminal_measure():
    with pytest.raises(ValueError, match="contributor observable"):
        compile_goal_contract(
            {
                "environment_terminal": "level_completion",
                "contributor_relation": "reached",
                "local_terminal": {
                    "observable": "outline_disagreement", "preferred_order": "decrease",
                    "relation": "equals", "target": 0.0,
                },
            },
            contributor_verb="fit", contributor_observable="fit_residual",
            contributor_target=0.0,
        )


def test_goal_contract_aliases_share_structural_identity_and_stay_open():
    proposal = {
        "environment_terminal": {"observable": "level_completion", "relation": "observed", "target": True},
        "contributor_relation": "reached",
        "local_terminal": {
            "observable": "fit_residual", "preferred_order": "decrease",
            "relation": "equals", "target": 0.0,
        },
    }
    align = compile_goal_contract(
        proposal, contributor_verb="align", contributor_observable="fit_residual", contributor_target=0.0,
    )
    fit = compile_goal_contract(
        proposal, contributor_verb="fit", contributor_observable="fit_residual", contributor_target=0.0,
    )
    assert align.contract_id == fit.contract_id
    assert align.status == fit.status == "OPEN"
    assert align.evidence == fit.evidence == ()


def test_production_workspace_reifies_supported_entity_upstream_of_planner():
    frame = [[0] * 12 for _ in range(12)]
    for y, x, value in ((1, 1, 1), (4, 1, 2), (8, 8, 3)):
        frame[y][x] = value; frame[y][x + 1] = value
    observer = FrameSchemaObserver({"enabled": False})
    observer.fit_frame(frame)
    members = observer.last_regions[:2]
    entity = CausalEntityBinding(
        binding_id="proposal", entity_id="entity:synthetic",
        cells=tuple(cell for member in members for cell in member["cells"]),
        member_binding_ids=tuple(member["binding_id"] for member in members),
        primitive_member_ids=tuple(member["binding_id"] for member in members),
        transform=TransformSignature("translation", (1.0, 0.0)),
        status="SUPPORTED", identity_status="UNIQUE", support=2, contradictions=0,
        evidence=("environment:1", "environment:2"), internal_relation_residual=0.0,
    )
    installed = observer._install_causal_entities((entity,))
    assert len(installed) == 1
    assert installed[0]["spatial_interface"] == "SpatialEntity"
    assert installed[0]["binding_id"] in observer.last_workspace.atoms
    assert observer.last_workspace.atoms[installed[0]["binding_id"]].type == "region-binding"
