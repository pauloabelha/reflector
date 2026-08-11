from __future__ import annotations

from dataclasses import dataclass, replace
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import hashlib
import inspect
import json


HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class Decision:
    action_id: int
    fallback_action_id: int
    reason: str
    template_hash: str | None
    residual_before: int | None
    predicted_residual_after: int | None
    prior_used: bool


@dataclass(frozen=True)
class Plan:
    mode: str = "fallback"
    action_id: int = 1
    fallback_action_id: int = 1
    predictions: tuple = ()
    selected_prediction_ids: tuple = ()
    probe_basis: str | None = None


class BaseController:
    def __init__(self, **_kwargs):
        self.action_uses = {1: 0, 2: 0}
        self.last_plan = None
    def _active_records(self): return []
    def plan(self, _legal, **_kwargs):
        plan = Plan()
        self.last_plan = plan
        return Decision(1, 1, "fallback", None, None, None, False), plan
    def observe(self, _action, _before, _after): return {"prospective_adjudication": None}
    def report(self): return {}


def test_no_visible_change_is_retained_and_not_repeated_in_same_state():
    module = load("controller")
    pc = SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason))
    live = SimpleNamespace(ProspectiveWorkspaceController=BaseController, PC=pc)
    controller = module.controller_class(live)()
    first, _ = controller.plan((1, 2), observation_digest="same", basis_revision=1)
    assert first.action_id == 1
    result = controller.observe(1, ((0,),), ((0,),))
    assert result["one_action_settlement"]["outcome"] == "no-visible-change"
    second, _ = controller.plan((1, 2), observation_digest="same", basis_revision=2)
    assert second.action_id == 2
    assert controller.last_contract["one_external_action_only"] is True
    assert controller.last_contract["winning_explanation_set"]["nonempty"] is True
    assert controller.last_contract["explanations"][0]["kind"] == "winning-explanation-family"


def test_action_changed_outcome_is_distinct_from_no_change():
    module = load("controller_changed") if (HERE / "controller_changed.py").exists() else load("controller")
    live = SimpleNamespace(ProspectiveWorkspaceController=BaseController, PC=SimpleNamespace(fallback_plan=lambda p, **_k: p))
    controller = module.controller_class(live)()
    controller.plan((1, 2), observation_digest="before", basis_revision=1)
    result = controller.observe(1, ((0,),), ((1,),))
    assert result["one_action_settlement"]["outcome"] == "changed"
    assert controller.no_change_attempts == {}


def test_r2_action_trace_reports_grounded_displacement():
    controller = load("controller_trace") if (HERE / "controller_trace.py").exists() else load("controller")
    before = ((0, 0, 0), (0, 2, 0), (0, 0, 0))
    after = ((0, 0, 0), (0, 0, 0), (0, 2, 0))
    assert controller.action_trace(3, before, after) == "Action 3 → f00 moved down 1"
    assert controller.action_trace(3, before, before) == "Action 3 → no visible change."


def test_arcade_exposes_required_live_surfaces():
    page = load("arcade").PAGE
    for phrase in ("EXPLANATION · CURRENT", "CONTROL V0 · CURRENT PROPOSAL", "SALIENT VERBS", "R2.1 SCHEMA LEVELS · CURRENT FRAME", "CATEGORICAL DIAGRAMS · ABDUCTIONS", "METADATA", "QWEN SCRATCHPAD", "R2 FEEDBACK · READ BY NEXT SEMANTIC QWEN", "ACTION ALIASES · QWEN GLOSS, NOT CONTROL", "action-token", "action-gloss", "actionColor", "STEP ONE", "RESET", "ACTION ${turn}/${budget", "SPEED", "AGENT ARCADE", "verb-chip", "verbColor", "USES", "executableExplanation", "POTENTIAL", "PREDICTS", "HYPOTHESES", "EVIDENCE", "semantic-action-alias-v10", "expectedArcadeUiVersion"):
        assert phrase in page
    assert "TOP-3 NEXT ACTIONS" not in page
    assert "SALIENT SCHEMAS" not in page
    assert "value?.verb||value?.claim" not in page
    assert "const name=String(value?.verb||'')" in page
    assert "/^[a-z][a-z0-9_]{0,39}$/" in page
    assert page.index("EXPLANATION · CURRENT") < page.index("CONTROL V0 · CURRENT PROPOSAL") < page.index("SALIENT VERBS") < page.index("R2.1 SCHEMA LEVELS · CURRENT FRAME") < page.index("CATEGORICAL DIAGRAMS · ABDUCTIONS") < page.index("METADATA")


def test_r2_1_fits_current_frame_at_multiple_recursive_levels():
    adapter = load("r2_1_adapter")
    frame = [
        [0, 0, 0, 0, 0, 0, 0],
        [0, 2, 2, 0, 3, 3, 0],
        [0, 2, 0, 0, 3, 0, 0],
        [0, 0, 0, 0, 0, 0, 0],
    ]
    stats = adapter.FrameSchemaObserver().fit_frame(frame, turn=0)
    by_level = {item["level"]: item for item in stats["levels"]}
    assert by_level[0]["output_types"]["region-binding"] == 2
    assert by_level[1]["bindings"] >= 3
    assert by_level[2]["bindings"] >= 1
    assert stats["totals"]["unique_schemas_bound"] >= 3
    assert stats["categorical"]["correspondences"] > 0
    assert set(stats["categorical"]["types_compared"]) >= {"region-binding", "relation-binding"}


def test_r2_1_stats_are_published_with_frame_zero_before_action():
    runtime = load("runtime_r21") if (HERE / "runtime_r21.py").exists() else load("runtime")
    live = runtime.LiveRuntime()
    live.set_schema_observer(SimpleNamespace(fit_frame=lambda frame, turn: {"turn": turn, "levels": [{"level": 0, "bindings": len(frame)}]}))
    live.update(status="explaining-first-frame", frame=[[1, 1]], turn=0)
    assert live.read()["r2_1_schema_stats"]["levels"][0]["bindings"] == 1


def test_r2_1_explanation_learns_progress_and_settles_prediction():
    adapter = load("r2_1_explanation_adapter") if (HERE / "r2_1_explanation_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before = [[0, 0, 0, 0, 0, 0], [0, 2, 0, 0, 3, 0], [0, 0, 0, 0, 0, 0]]
    middle = [[0, 0, 0, 0, 0, 0], [0, 0, 2, 0, 3, 0], [0, 0, 0, 0, 0, 0]]
    after = [[0, 0, 0, 0, 0, 0], [0, 0, 0, 2, 3, 0], [0, 0, 0, 0, 0, 0]]

    semantic_goal = {
        "verb": "align", "schema_name": "Compatible entities converge", "goal_family": "alignment",
        "observable": "centroid_distance", "direction": "decrease",
        "terminal_condition": "the proposed relation reaches its minimum",
        "role_constraints": ["two distinct visible entities"],
    }
    observer.fit_frame(before, turn=0)
    exploratory = observer.rank_actions((1, 4), fallback_action=4, semantic_goal=semantic_goal)
    assert exploratory["current_explanation"]["epistemic_status"] == "grounded-open-mechanism"
    learned = observer.settle_action(4, before, middle)
    assert learned["adjudication"] == "mechanism-observed"
    assert learned["identity"]["status"] == "UNIQUE"

    stats = observer.fit_frame(middle, turn=1)
    control = observer.rank_actions((1, 4), fallback_action=1, semantic_goal=semantic_goal)
    assert control["selected_action"] == 4
    assert control["control_override"] is True
    assert control["current_explanation"]["prediction"]["expected_progress"] == 1
    assert observer.last_stats["maximum_level"] >= 5
    output_types = {
        name
        for level in observer.last_stats["levels"]
        for name in level["output_types"]
    }
    assert {
        "potential-binding", "verb-binding", "preferred-completion-binding",
        "causal-effect-binding", "progress-binding", "explanation-binding",
    }.issubset(output_types)
    explanation = control["current_explanation"]
    assert explanation["verb_status"] == "active"
    assert explanation["ports"]["potential"]
    assert explanation["ports"]["causal_effect"]
    assert explanation["ports"]["progress"]
    assert {
        "region-binding", "verb-binding", "causal-effect-binding", "explanation-binding",
    }.issubset({item["type"] for item in observer.last_categorical_bindings})
    workspace = observer.last_workspace
    store = observer.last_store
    assert store.records[workspace.bindings[explanation["binding_id"]].schema_id].schema.kind == "explanation"
    assert any(record.schema.kind == "preferred-completion" for record in store.records.values())
    assert any(shadow.state.value == "reified" for shadow in workspace.shadows.values())

    settled = observer.settle_action(4, middle, after)
    assert settled["adjudication"] == "confirmed"
    assert settled["actual_progress"] == 1


def test_control_v0_rejects_area_collapse_as_broken_identity():
    adapter = load("r2_1_control_identity_adapter") if (HERE / "r2_1_control_identity_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    source = adapter._components([
        [0, 0, 0, 0, 0],
        [0, 2, 2, 2, 0],
        [0, 2, 2, 2, 0],
        [0, 0, 0, 0, 0],
    ])[0]
    fragment = adapter._components([
        [0, 0, 0, 0, 0],
        [0, 2, 0, 0, 0],
        [0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ])[0]
    correspondence = observer._correspondence(source, [fragment])
    assert correspondence["status"] == "BROKEN"
    assert correspondence["best_residual"] > adapter.ROLE_IDENTITY_MAX_RESIDUAL


def test_control_v0_probe_settlement_does_not_attribute_every_changed_fragment():
    adapter = load("r2_1_control_attribution_adapter") if (HERE / "r2_1_control_attribution_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 2, 2, 2, 0, 3, 3, 3, 0, 4, 4, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    after = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 2, 2, 2, 3, 3, 3, 0, 0, 4, 4],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    observer.fit_frame(before, turn=0)
    ranking = observer.rank_actions((1,), fallback_action=1, semantic_goal=_alignment_goal())
    assert ranking["control_proposal"]["status"] == "PROBE_ELIGIBLE"
    settlement = observer.settle_action(1, before, after)
    assert settlement["identity"]["status"] == "UNIQUE"
    assert len(settlement["learned_effects"]) == 2
    assert {item["role"] for item in settlement["learned_effects"]} == {"actor", "target"}


def test_control_v0_settlement_uses_frozen_predecessor_after_successor_is_fitted():
    adapter = load("r2_1_frozen_predecessor_adapter") if (HERE / "r2_1_frozen_predecessor_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    ranking = observer.rank_actions((4,), fallback_action=4, semantic_goal=_alignment_goal())
    explanation = ranking["current_explanation"]
    assert set(explanation["predecessor_binding_snapshots"]) == {
        explanation["ports"]["actor"], explanation["ports"]["target"],
    }

    # The live runtime fits the observed successor before settling the pending
    # proposal.  Mutable observer state must not replace the proposal's basis.
    observer.fit_frame(middle, turn=1)
    settlement = observer.settle_action(4, before, middle)
    assert settlement["identity"]["status"] == "UNIQUE"
    assert settlement["adjudication"] == "mechanism-observed"
    assert all(
        role["reason"] != "missing-predecessor"
        for role in settlement["identity"]["roles"].values()
    )


def test_control_v0_fits_model_supported_identity_through_mutual_occlusion():
    adapter = load("r2_1_occlusion_adapter") if (HERE / "r2_1_occlusion_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 2, 2, 2, 3, 3, 3, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]
    actor, target = adapter._components(before)
    observer.frame_shape = (len(before), len(before[0]))
    # Actor translates right by one. Target pixels render over their overlap,
    # splitting/occluding the actor's ordinary visible component.
    after = [row[:] for row in before]
    after[2] = [0, 0, 2, 2, 3, 3, 3, 0]
    fit = observer._occlusion_correspondence(
        actor, target, after, expected_delta=(0.0, 1.0), other_expected_delta=(0.0, 0.0),
    )
    assert fit is not None
    assert fit["status"] == "UNIQUE"
    assert fit["reason"] == "unique-model-supported-successor-through-mutual-occlusion"
    assert fit["identity_evidence"]["visible_source_cells"] == 2
    assert set(fit["best"]["region"]["cells"]) == {(2.0, 2.0), (2.0, 3.0), (2.0, 4.0)}

    contaminated = [row[:] for row in after]
    contaminated[2][2] = 4  # unexplained change in an exposed predicted cell
    assert observer._occlusion_correspondence(
        actor, target, contaminated,
        expected_delta=(0.0, 1.0), other_expected_delta=(0.0, 0.0),
    ) is None


def test_control_v0_installs_occlusion_factorization_for_next_decision():
    adapter = load("r2_1_occlusion_episode_adapter") if (HERE / "r2_1_occlusion_episode_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before = [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 2, 2, 2, 3, 3, 3, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]
    goal = _comparative_fit_goal()
    observer.fit_frame(before, turn=0)
    opening = observer.rank_actions((1,), fallback_action=1, semantic_goal=goal)
    explanation = opening["current_explanation"]
    by_id = {region["binding_id"]: region for region in observer.last_regions}
    actor = by_id[explanation["ports"]["actor"]]
    target = by_id[explanation["ports"]["target"]]
    delta = (0.0, 1.0 if actor["center2"][1] < target["center2"][1] else -1.0)
    observer.action_effects[(1, observer._region_key(actor))][delta] += 1
    observer.action_effects[(1, observer._region_key(target))][(0.0, 0.0)] += 1
    controlled = observer.rank_actions((1,), fallback_action=1, semantic_goal=goal)
    assert controlled["current_explanation"]["mechanism"]["models_supported"] is True
    assert controlled["current_explanation"]["prediction"]["expected_progress"] > 0
    # This focused test supplies the prior causal model directly; in a live
    # episode, the pending proposal has already earned eligibility through the
    # preceding non-overlap settlement.
    observer.pending_prediction = controlled["current_explanation"]

    projected_actor, _status = observer._simulate_translation(actor, delta)
    after = [[0 for _x in row] for row in before]
    for y, x in projected_actor["cells"]:
        after[int(y)][int(x)] = actor["value"]
    for y, x in target["cells"]:  # target renders over mutual overlap
        after[int(y)][int(x)] = target["value"]
    observer.fit_frame(after, turn=1)
    settlement = observer.settle_action(1, before, after)
    assert settlement["identity"]["status"] == "UNIQUE"
    assert settlement["identity"]["factorization"] == {
        "status": "INSTALLED", "kind": "model-supported-mutual-occlusion", "latent_roles": 2,
    }
    latent = [
        region for region in observer.last_regions
        if region.get("factorization") == "model-supported-mutual-occlusion"
    ]
    assert len(latent) == 2
    continuation = observer.rank_actions((1,), fallback_action=1, semantic_goal=goal)
    assert continuation["current_explanation"]["identity"]["control_eligible"] is True


def test_control_v0_fragmented_controlling_role_cannot_authorize_progress():
    adapter = load("r2_1_control_fragment_adapter") if (HERE / "r2_1_control_fragment_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 2, 2, 2, 0, 0, 3, 3, 3, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    observer.fit_frame(before, turn=0)
    ranking = observer.rank_actions((1,), fallback_action=1, semantic_goal=_alignment_goal())
    actor_binding = ranking["current_explanation"]["ports"]["actor"]
    actor = next(region for region in observer.last_regions if region["binding_id"] == actor_binding)
    actor_cells = set(actor["cells"])
    kept_actor_cell = min(actor_cells)
    after = [list(row) for row in before]
    for y, x in actor_cells:
        after[y][x] = 0
    after[kept_actor_cell[0]][kept_actor_cell[1]] = actor["value"]
    settlement = observer.settle_action(1, before, after)
    assert settlement["identity"]["status"] == "BROKEN"
    assert settlement["adjudication"] == "identity-broken"
    actor_role = next(
        role for role, binding_id in ranking["current_explanation"]["ports"]["situated_roles"].items()
        if binding_id == actor_binding
    )
    assert settlement["identity"]["roles"][actor_role]["source_area"] == 3
    assert settlement["identity"]["roles"][actor_role]["status"] == "BROKEN"
    assert all(item["role"] != actor_role for item in settlement["learned_effects"])


def _alignment_goal():
    return {
        "verb": "align", "schema_name": "Compatible entities converge",
        "goal_family": "alignment", "observable": "centroid_distance",
        "direction": "decrease", "terminal_class": "minimum",
        "terminal_condition": "the proposed relation reaches its minimum",
        "role_constraints": ["two distinct visible entities"],
    }


def _three_alignment_frames():
    return (
        [[0, 0, 0, 0, 0, 0], [0, 2, 0, 0, 3, 0], [0, 0, 0, 0, 0, 0]],
        [[0, 0, 0, 0, 0, 0], [0, 0, 2, 0, 3, 0], [0, 0, 0, 0, 0, 0]],
        [[0, 0, 0, 0, 0, 0], [0, 0, 0, 2, 3, 0], [0, 0, 0, 0, 0, 0]],
    )


def test_r2_1_episode_reset_clears_every_epistemic_store():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    observer.rank_actions((1, 4), fallback_action=4, semantic_goal=_alignment_goal())
    observer.settle_action(4, before, middle)
    assert observer.last_workspace is not None
    assert observer.action_effects
    assert observer.action_uses
    observer.reset_episode()
    assert observer.last_digest is None
    assert observer.last_workspace is None
    assert observer.last_store is None
    assert observer.last_stats is None
    assert observer.last_regions == []
    assert not observer.action_effects
    assert not observer.action_uses
    assert observer.pending_prediction is None
    assert observer.last_potential_states == {}
    assert observer.last_verb_bindings == {}
    assert observer.last_action_atoms == {}


def test_r2_1_identical_first_frame_gets_a_fresh_workspace_after_reset():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, _middle, _after = _three_alignment_frames()
    first_stats = observer.fit_frame(before, turn=0)
    first_workspace = observer.last_workspace
    cached_stats = observer.fit_frame(before, turn=0)
    assert cached_stats["cached"] is True
    assert observer.last_workspace is first_workspace
    observer.reset_episode()
    second_stats = observer.fit_frame(before, turn=0)
    assert second_stats is not first_stats
    assert observer.last_workspace is not first_workspace
    assert second_stats["turn"] == 0
    assert not observer.action_effects


def test_r2_1_repeated_ranking_after_completion_is_idempotent():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    observer.rank_actions((1, 4), fallback_action=4, semantic_goal=_alignment_goal())
    observer.settle_action(4, before, middle)
    observer.fit_frame(middle, turn=1)
    first = observer.rank_actions((1, 4), fallback_action=1, semantic_goal=_alignment_goal())
    second = observer.rank_actions((1, 4), fallback_action=1, semantic_goal=_alignment_goal())
    assert first["current_explanation"]["verb"] == "align"
    assert second["current_explanation"]["verb"] == "align"
    assert second["current_explanation"]["verb_status"] == "active"
    assert second["selected_action"] == 4


def test_r2_1_semantic_projection_exposes_explanations_verbs_schemas_and_settlement():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    ranking = observer.rank_actions((1, 4), fallback_action=4, semantic_goal=_alignment_goal())
    opening = observer.semantic_projection(ranking=ranking)
    assert opening["protocol"] == "r2.1-semantic-projection-v1"
    assert opening["authority"]["semantic_revision"] == "qwen-proposal-only"
    assert opening["authority"]["action_selection"] == "r2-only"
    assert opening["active_explanation"]["verb"] == "align"
    assert opening["active_explanation"]["potential"]["observable"] == "centroid_distance"
    assert opening["active_explanation"]["roles"]
    assert opening["competing_explanations"]
    assert opening["salient_structural_bindings"]
    assert opening["open_shadows"]

    settlement = observer.settle_action(4, before, middle)
    settled = observer.semantic_projection(ranking=ranking, settlement=settlement)
    assert settled["latest_settlement"]["adjudication"] == "mechanism-observed"
    json.dumps(settled)


def test_categorical_comparison_is_recursive_bounded_and_has_no_close_prior():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    frame = [[0] * 25 for _ in range(5)]
    for index, value in enumerate(range(1, 11), start=1):
        frame[2][index * 2] = value
    stats = observer.fit_frame(frame, turn=0)
    categorical = stats["categorical"]
    assert categorical["candidate_pairs"] <= categorical["budgets"]["comparisons"] == 64
    assert categorical["temporal_comparisons"] <= categorical["budgets"]["temporal"] == 64
    assert categorical["budgets"]["atoms_per_type"] == 12
    assert categorical["budgets"]["neighbors_per_atom"] == 2
    assert {"region-binding", "relation-binding"}.issubset(categorical["types_compared"])
    categorical_schemas = [
        record.schema for record in observer.last_store.records.values()
        if record.schema.kind in {"correspondence", "comparison", "temporal-comparison"}
    ]
    rendered = json.dumps([
        {"kind": schema.kind, "constraints": [item.predicate for item in schema.constraints]}
        for schema in categorical_schemas
    ]).lower()
    assert "close" not in rendered


def test_categorical_residual_change_is_an_ordinary_temporal_schema_binding():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    stats = observer.fit_frame(middle, turn=1)
    changes = [item for item in observer.last_temporal_comparisons if item["dimension"] == "normalized_boundary_gap"]
    assert changes
    assert any(item["orientation"] == "ResidualDecreased" and item["after"] < item["before"] for item in changes)
    binding = observer.last_workspace.bindings[changes[0]["binding_id"]]
    schema = observer.last_store.records[binding.schema_id].schema
    assert schema.kind == "temporal-comparison"
    assert schema.output_type == "temporal-comparison-binding"


def test_qwen_abduction_compiles_to_a_typed_schema_binding_and_open_shadow():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, _middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    component_ids = []
    for item in observer.last_categorical_bindings:
        if item["schema_id"] not in component_ids:
            component_ids.append(item["schema_id"])
    assert len(component_ids) >= 2
    proposal = {
        "local_ref": "ab0", "component_schema_ids": component_ids[:2],
        "morphisms": [{"source_schema_id": component_ids[0], "target_schema_id": component_ids[1], "kind": "co_describes"}],
        "preferred_residual_changes": [{"comparison_schema_id": component_ids[0], "dimension": "schema_difference", "direction": "decrease"}],
        "open_questions": ["Does the residual decrease under intervention?"],
    }
    ranked = observer.rank_actions((1, 2), fallback_action=1, semantic_goal=None, semantic_abductions=[proposal])
    assert ranked["grounded_abductions"]
    grounded = ranked["grounded_abductions"][0]
    assert grounded["epistemic_status"] == "grounded-structural-open-prediction"
    assert grounded["prediction_shadow_ids"]
    binding = observer.last_workspace.bindings[grounded["binding_id"]]
    schema = observer.last_store.records[binding.schema_id].schema
    assert schema.kind == "abductive-composition"
    assert schema.components == tuple(sorted(component_ids[:2]))


def test_qwen_abduction_with_stale_schema_ids_is_rejected_not_grounded():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, _middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    ranked = observer.rank_actions((1,), fallback_action=1, semantic_goal=None, semantic_abductions=[{
        "local_ref": "ab0", "component_schema_ids": ["schema:missing-a", "schema:missing-b"],
        "morphisms": [{"source_schema_id": "schema:missing-a", "target_schema_id": "schema:missing-b", "kind": "preserves"}],
        "preferred_residual_changes": [], "open_questions": [],
    }])
    assert ranked["grounded_abductions"] == []
    assert ranked["rejected_abductions"][0]["reason"] == "unknown-or-unbounded-components"


def test_r2_1_three_consecutive_identical_episodes_do_not_share_learning():
    adapter = load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, middle, _after = _three_alignment_frames()
    workspaces = []
    for _episode in range(3):
        observer.reset_episode()
        observer.fit_frame(before, turn=0)
        workspaces.append(observer.last_workspace)
        opening = observer.rank_actions((1, 4), fallback_action=4, semantic_goal=_alignment_goal())
        assert opening["current_explanation"]["epistemic_status"] == "grounded-open-mechanism"
        assert not observer.action_effects
        observer.settle_action(4, before, middle)
        assert observer.action_effects
    assert len({id(workspace) for workspace in workspaces}) == 3


def test_live_runtime_delegates_episode_reset_to_schema_observer():
    runtime = load("runtime")
    calls = []
    live = runtime.LiveRuntime()
    live.set_schema_observer(SimpleNamespace(reset_episode=lambda: calls.append("reset")))
    live.reset_schema_observer()
    assert calls == ["reset"]


def test_run_game_resets_semantic_feedback_and_schema_observer_before_episode_execution():
    source = (HERE / "experiment.py").read_text()
    feedback_reset_position = source.index("SCRATCHPAD.reset_episode_context()", source.index("def run_game"))
    reset_position = source.index("runtime.reset_schema_observer()", source.index("def run_game"))
    episode_position = source.index("BASE.run_episode(payload, fifo)", source.index("def run_game"))
    assert feedback_reset_position < episode_position
    assert reset_position < episode_position


def test_r2_1_does_not_invent_a_geometric_goal_without_semantic_proposal():
    adapter = load("r2_1_no_goal_adapter") if (HERE / "r2_1_no_goal_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    observer.fit_frame([[0, 0, 0, 0, 0], [0, 2, 0, 3, 0], [0, 0, 0, 0, 0]], turn=0)
    ranked = observer.rank_actions((1, 2), fallback_action=1, semantic_goal=None)
    assert ranked["current_explanation"] is None
    assert ranked["explanations"] == []
    assert ranked["top_actions"][0]["eligibility"] == "INELIGIBLE"
    output_types = {name for level in observer.last_stats["levels"] for name in level["output_types"]}
    assert "verb-binding" not in output_types
    assert "explanation-binding" not in output_types
    assert "comparison-binding" in output_types


def test_r2_1_fit_verb_keeps_defeasible_role_evidence_in_its_binding_graph():
    adapter = load("r2_1_verb_adapter") if (HERE / "r2_1_verb_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    frame = [
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
        [0, 2, 2, 2, 0, 0, 3, 3, 3, 0, 4, 4, 4, 0],
        [0, 2, 0, 2, 0, 0, 3, 3, 3, 0, 4, 4, 4, 0],
        [0, 2, 2, 2, 0, 0, 3, 3, 3, 0, 4, 4, 4, 0],
        [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
    ]
    observer.fit_frame(frame, turn=0)
    assert observer.last_regions[0]["outline"] == observer.last_regions[1]["outline"]
    assert observer.last_regions[0]["shape"] != observer.last_regions[1]["shape"]
    ranked = observer.rank_actions((1,), fallback_action=1, semantic_goal=[{
        "verb": "fit", "schema_name": "Fit compatible figures",
        "goal_family": "containment", "observable": "containment_violation",
        "direction": "decrease", "terminal_condition": "shape mismatch is zero",
        "roles": ["actor", "target", "reference"],
        "potential_roles": ["actor", "target"],
        "role_constraints": [
            {"predicate": "same_outline", "arguments": ["actor", "target"]},
            {"predicate": "same_outline", "arguments": ["actor", "reference"]},
            {"predicate": "same_interior", "arguments": ["actor", "target"]},
            {"predicate": "different_interior", "arguments": ["actor", "reference"]},
        ],
    }])
    explanation = ranked["current_explanation"]
    assert explanation["verb"] == "fit"
    assert explanation["prospective_schema_binding_ids"]
    assert explanation["prospective_shadow_ids"]
    assert "reference" in explanation["ports"]["situated_roles"]
    assert explanation["prediction"]["residual_before"] == 9
    assert explanation["role_grounding"]["epistemic_status"] == "defeasible-role-hypothesis"
    assert "residual_vector" in explanation["role_grounding"]


def _comparative_fit_goal(*, modality="suggested"):
    return {
        "verb": "fit", "schema_name": "Generic measurable fit",
        "goal_family": "alignment", "roles": ["actor", "target"],
        "potential_roles": ["actor", "target"], "observable": "fit_residual",
        "direction": "decrease", "terminal_class": "minimum",
        "terminal_condition": "fit_residual = 0",
        # Deliberately wrong for a congruent pair.  Suggested evidence must not
        # acquire the authority of a schema requirement.
        "role_constraints": [{
            "predicate": "different_outline", "arguments": ["actor", "target"],
            "modality": modality,
        }],
    }


def _shape_frame(shape, *, scale=1, swap_values=False, offset=(0, 0), distractors=True):
    points = {
        (offset[0] + y * scale + dy, offset[1] + x * scale + dx)
        for y, x in shape for dy in range(scale) for dx in range(scale)
    }
    height, width = 24 * scale, 34 * scale
    frame = [[0 for _x in range(width)] for _y in range(height)]
    values = (3, 2) if swap_values else (2, 3)
    origins = ((2 * scale, 3 * scale), (12 * scale, 20 * scale))
    for value, (oy, ox) in zip(values, origins):
        for y, x in points:
            frame[oy + y][ox + x] = value
    if distractors:
        frame[scale][scale] = 4
        frame[height - 2 * scale][width - 2 * scale] = 5
    return frame


def _grounded_role_areas(observer, goal):
    grounded = observer._bind_verb_schemas([goal])
    assert grounded
    regions = {region["binding_id"]: region for region in observer.last_regions}
    return [
        tuple(regions[item["situated_roles"][role]]["area"] for role in ("actor", "target"))
        for item in grounded[0]["r2_role_groundings"]
    ], grounded[0]["r2_role_groundings"]


def test_defeasible_grounder_recovers_congruent_pair_from_incorrect_semantic_clue():
    adapter = load("r2_1_defeasible_grounder") if (HERE / "r2_1_defeasible_grounder.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    shape = {(0, 0), (1, 0), (2, 0), (2, 1)}
    observer.fit_frame(_shape_frame(shape), turn=0)
    legacy_goal = _comparative_fit_goal()
    legacy_goal["role_constraints"][0].pop("modality")
    areas, hypotheses = _grounded_role_areas(observer, legacy_goal)
    assert areas[:2] == [(4, 4), (4, 4)]
    assert all(item["residual_vector"]["structural_residual"] == 0 for item in hypotheses[:2])
    assert all(item["semantic_clue_residual"] == 1 for item in hypotheses[:2])
    assert all(item["epistemic_status"] == "defeasible-role-hypothesis" for item in hypotheses)


def test_probe_selection_uses_best_comparative_role_hypothesis():
    adapter = load("r2_1_ranked_probe_adapter") if (HERE / "r2_1_ranked_probe_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    shape = {(0, 0), (1, 0), (2, 0), (2, 1)}
    observer.fit_frame(_shape_frame(shape), turn=0)
    ranked = observer.rank_actions((1,), fallback_action=1, semantic_goal=_comparative_fit_goal())
    explanation = ranked["current_explanation"]
    assert explanation["role_grounding"]["bounded_rank"] == 1
    actor = explanation["predecessor_binding_snapshots"][explanation["ports"]["actor"]]
    target = explanation["predecessor_binding_snapshots"][explanation["ports"]["target"]]
    assert actor["area"] == target["area"] == len(shape)


def test_defeasible_grounder_honors_explicit_required_modality():
    adapter = load("r2_1_required_grounder") if (HERE / "r2_1_required_grounder.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    shape = {(0, 0), (1, 0), (2, 0), (2, 1)}
    observer.fit_frame(_shape_frame(shape, distractors=False), turn=0)
    ranked = observer.rank_actions((1,), fallback_action=1, semantic_goal=_comparative_fit_goal(modality="required"))
    assert ranked["current_explanation"] is None
    assert ranked["rejected_goal_proposals"][0]["reason"] == "no measurable typed tuple satisfies schema-required constraints"


def test_defeasible_grounding_is_translation_value_and_shape_generic():
    adapter = load("r2_1_permutation_grounder") if (HERE / "r2_1_permutation_grounder.py").exists() else load("r2_1_adapter")
    shapes = [
        {(0, 1), (1, 0), (1, 1), (1, 2)},                 # T
        {(0, 0), (0, 1), (1, 1), (1, 2)},                 # Z
        {(0, 0), (1, 0), (1, 1), (2, 1), (2, 2)},         # irregular
    ]
    for shape in shapes:
        for scale, swap, offset in ((1, False, (0, 0)), (1, True, (1, 2)), (2, False, (0, 1))):
            observer = adapter.FrameSchemaObserver()
            observer.fit_frame(
                _shape_frame(shape, scale=scale, swap_values=swap, offset=offset), turn=0,
            )
            expected_area = len(shape) * scale * scale
            areas, hypotheses = _grounded_role_areas(observer, _comparative_fit_goal())
            assert areas[0] == (expected_area, expected_area)
            assert hypotheses[0]["residual_vector"]["structural_residual"] == 0


def test_defeasible_grounder_contains_no_game_or_named_shape_rule():
    adapter = load("r2_1_no_game_grounder") if (HERE / "r2_1_no_game_grounder.py").exists() else load("r2_1_adapter")
    rendered = inspect.getsource(adapter.DefeasibleRoleGrounder).lower()
    assert "ar25" not in rendered
    assert "blue_l" not in rendered
    assert "yellow_l" not in rendered


def test_r2_1_rejects_a_verb_whose_direction_moves_away_from_its_terminal():
    adapter = load("r2_1_coherence_adapter") if (HERE / "r2_1_coherence_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    observer.fit_frame([[0, 0, 0, 0, 0], [0, 2, 0, 3, 0], [0, 0, 0, 0, 0]], turn=0)
    ranked = observer.rank_actions((1,), fallback_action=1, semantic_goal=[{
        "verb": "fit", "schema_name": "Contradictory fit",
        "goal_family": "alignment", "observable": "centroid_distance",
        "direction": "increase", "terminal_condition": "centroid_distance < 1",
        "role_constraints": ["two figures"],
    }])
    assert ranked["current_explanation"] is None
    assert ranked["top_actions"][0]["eligibility"] == "INELIGIBLE"
    assert ranked["rejected_goal_proposals"][0]["r2_grounding_status"] == "rejected-incoherent"


def test_r2_1_rejects_explanation_prose_in_a_verb_port():
    adapter = load("r2_1_invalid_verb_adapter") if (HERE / "r2_1_invalid_verb_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    observer.fit_frame([[0, 0, 0, 0, 0], [0, 2, 0, 3, 0], [0, 0, 0, 0, 0]], turn=0)
    ranked = observer.rank_actions((1,), fallback_action=1, semantic_goal=[{
        "verb": "The figures should become vertically aligned.",
        "schema_name": "Alignment claim",
        "observable": "centroid_distance", "direction": "decrease",
        "terminal_condition": "centroid_distance is zero",
    }])
    assert ranked["current_explanation"] is None
    assert ranked["rejected_goal_proposals"][0]["r2_grounding_status"] == "rejected-invalid-verb"


def test_fit_residual_has_an_approach_gradient_before_overlap():
    adapter = load("r2_1_fit_residual_adapter") if (HERE / "r2_1_fit_residual_adapter.py").exists() else load("r2_1_adapter")
    actor = {"cells": ((0, 0), (0, 1))}
    far = {"cells": ((0, 5), (0, 6))}
    nearer = {"cells": ((0, 4), (0, 5))}
    coincident = {"cells": ((0, 0), (0, 1))}
    assert adapter.FrameSchemaObserver._measure("fit_residual", actor, far) > adapter.FrameSchemaObserver._measure("fit_residual", actor, nearer)
    assert adapter.FrameSchemaObserver._measure("fit_residual", actor, coincident) == 0


def test_controller_lets_r2_1_explanation_choose_the_action():
    controller = load("controller_r21") if (HERE / "controller_r21.py").exists() else load("controller")
    explanation = {
        "kind": "situated-control-explanation", "binding_id": "e1",
        "prediction": {"action": 2, "expected_progress": 1, "residual_before": 3, "residual_after": 2, "actor_delta": [1, 0]},
    }
    observer = SimpleNamespace(rank_actions=lambda legal, **kwargs: {
        "selected_action": 2,
        "top_actions": [{"rank": 1, "action": 2, "selected": True, "role": "goal-progress"}],
        "explanations": [explanation], "current_explanation": explanation,
        "control_override": True, "selection_rule": "test",
    })
    runtime = SimpleNamespace(schema_observer=observer)
    pc = SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason))
    live = SimpleNamespace(ProspectiveWorkspaceController=BaseController, PC=pc)
    instance = controller.controller_class(live, runtime)()
    decision, _plan = instance.plan((1, 2), observation_digest="frame", basis_revision=1)
    assert decision.action_id == 2
    assert decision.reason == "r2.1-control-v0-progress"
    assert instance.last_contract["current_explanation"]["binding_id"] == "e1"


def test_controller_publishes_r2_semantics_after_ranking_and_settlement(monkeypatch):
    controller = load("controller")
    published = []; transitions = []; ranking_inputs = []
    monkeypatch.setitem(sys.modules, "one_action_scratchpad", SimpleNamespace(
        record_r2_semantic_projection=lambda value: published.append(value),
        record_r2_action_trace=lambda _value: None,
        record_r2_transition_observation=lambda **value: transitions.append(value),
    ))
    explanation = {
        "kind": "situated-control-explanation", "binding_id": "e1", "verb": "fit",
        "prediction": {"action": 2, "expected_progress": 1, "residual_before": 3, "residual_after": 2, "actor_delta": [1, 0]},
    }
    ranking = {
        "selected_action": 2, "top_actions": [], "explanations": [explanation],
        "current_explanation": explanation, "control_override": True,
        "selection_rule": "test", "rejected_goal_proposals": [],
    }
    observer = SimpleNamespace(
        rank_actions=lambda legal, **kwargs: ranking_inputs.append(kwargs) or ranking,
        settle_action=lambda action, before, after: {"adjudication": "confirmed", "actual_progress": 1},
        semantic_projection=lambda **kwargs: {"protocol": "r2.1-semantic-projection-v1", **kwargs},
    )
    runtime = SimpleNamespace(
        schema_observer=observer,
        snapshot={
            "current_explanation": {"goal_proposals": [_alignment_goal()]},
            "scratchpad": {
                "goal_proposals": [{**_alignment_goal(), "verb": "touch"}],
                "abductive_compositions": [{"local_ref": "ab0"}],
            },
        },
        record_r2_action_trace=lambda _trace: None,
        update=lambda **_kwargs: None,
    )
    pc = SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason))
    live = SimpleNamespace(ProspectiveWorkspaceController=BaseController, PC=pc)
    instance = controller.controller_class(live, runtime)()
    instance.plan((1, 2), observation_digest="frame", basis_revision=1)
    assert ranking_inputs[-1]["semantic_goal"][0]["verb"] == "touch"
    assert ranking_inputs[-1]["semantic_abductions"] == [{"local_ref": "ab0"}]
    assert published[-1]["ranking"]["current_explanation"]["verb"] == "fit"
    instance.observe(2, ((0, 2, 0),), ((0, 0, 2),))
    assert published[-1]["settlement"]["adjudication"] == "confirmed"
    assert transitions[-1]["action"] == 2
    assert transitions[-1]["observation_changed"] is True
    assert transitions[-1]["settlement"]["adjudication"] == "confirmed"


def test_action_aliases_do_not_change_control_or_empirical_state():
    controller = load("controller_alias_noninterference") if (HERE / "controller_alias_noninterference.py").exists() else load("controller")

    def run(action_aliases):
        ranking_inputs = []
        empirical = {
            "action_effect_support": {(1, "tracked-type"): {(0.0, -1.0): 2}},
            "environment_evidence": ["r2-transition:observed"],
        }
        ranking = {
            "selected_action": 1, "top_actions": [], "explanations": [],
            "current_explanation": None, "control_override": False,
            "execution_authorized": False, "selection_rule": "fixed-test",
            "rejected_goal_proposals": [],
        }
        observer = SimpleNamespace(
            rank_actions=lambda legal, **kwargs: ranking_inputs.append((tuple(legal), kwargs)) or ranking,
            semantic_projection=lambda **kwargs: {"protocol": "r2.1-semantic-projection-v1"},
            **empirical,
        )
        runtime = SimpleNamespace(
            schema_observer=observer,
            snapshot={
                "scratchpad": {
                    "goal_proposals": [_alignment_goal()],
                    "abductive_compositions": [],
                    "action_aliases": list(action_aliases),
                },
                "environment_evidence": empirical["environment_evidence"],
            },
            set_r2_semantic_projection=lambda _value: None,
        )
        pc = SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason))
        live = SimpleNamespace(ProspectiveWorkspaceController=BaseController, PC=pc)
        instance = controller.controller_class(live, runtime)()
        decision, _plan = instance.plan((1, 2), observation_digest="same-frame", basis_revision=9)
        return {
            "decision": decision,
            "ranking_input": ranking_inputs[-1],
            "action_effect_support": observer.action_effect_support,
            "environment_evidence": runtime.snapshot["environment_evidence"],
        }

    stripped = run([])
    aliased = run([{
        "action_id": "ACTION_1", "alias": "move up", "status": "stable",
        "evidence_refs": ["r2-transition:observed"],
    }])
    assert aliased == stripped
    assert aliased["decision"].action_id == 1


def test_live_frame_stack_is_json_safe():
    runtime = load("runtime")

    class Array:
        def tolist(self):
            return [[1, 2], [3, 4]]

    assert runtime.plain_frame([Array()]) == [[1, 2], [3, 4]]
    json.dumps(runtime.plain_frame([Array()]))


def test_qwen_eta_exists_before_first_call():
    runtime = load("runtime_prior") if (HERE / "runtime_prior.py").exists() else load("runtime")
    qwen = runtime.LiveRuntime().read()["qwen"]
    assert qwen["phase"] == "ready"
    assert qwen["eta_seconds"] > 0
    assert qwen["eta_basis"] == "configuration-prior"


def test_reset_clears_every_live_surface():
    runtime = load("runtime_reset") if (HERE / "runtime_reset.py").exists() else load("runtime")
    live = runtime.LiveRuntime()
    live.update(frame=[[1]], turn=4, decision={"x": 1}, scratchpad={"natural_language": "text", "action_aliases": [{"action_id": "ACTION_1", "alias": "move?"}]}, r2_semantic_projection={"verb": "fit"}, metadata={"run": 1})
    state = live.request_reset()
    assert state["status"] == "resetting"
    for field in ("frame", "decision", "scratchpad", "r2_semantic_projection", "metadata", "current_explanation"):
        assert not state[field]
    live.finish_reset()
    assert live.read()["status"] == "idle"


@dataclass(frozen=True)
class Turn:
    request_id: str
    workspace_id: str
    basis_revision: int
    basis_hash: str | None
    mode: str
    document: dict
    id_aliases: tuple = ()
    validation_context: dict | None = None


def fake_qc():
    graph = SimpleNamespace(estimate_tokens=lambda value: max(1, len(json.dumps(value)) // 4))
    qc = SimpleNamespace(
        PROMPT="prompt",
        GRAPH=graph,
        build_turn=lambda _state, _events, _orientation, **_kwargs: Turn("r", "w", 4, None, "delta", {"protocol": "p"}),
        response_schema=lambda _turn: {"type": "object", "required": ["protocol"], "properties": {"protocol": {"const": "p"}}},
        compile_response=lambda _response, _turn: {"valid_json_contract": True, "accepted": [], "rejected": []},
        request_payload=lambda _turn, _qwen, **_kwargs: {
            "messages": [{"role": "user", "content": "prompt" + json.dumps(_turn.document)}],
            "response_format": {"json_schema": {"schema": {"type": "object", "properties": {"protocol": {}}, "required": ["protocol"]}}},
        },
        _v14_visible=lambda _turn: ({"a": {}}, {"a"}),
        _forbidden=lambda value: "action" in json.dumps(value).lower(),
        stable_hash=lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest(),
    )
    return qc


def semantic_response(*, action_aliases=()):
    return {"parsed": {
        "protocol": "p", "request_id": "r",
        "natural_language_scratchpad": "I am retaining a compact interpretation of observed structure.",
        "workspace_write": {
            "summary": "Observed structure supports a compact working interpretation.",
            "objective_hypothesis": "A relational residual may organize progress.",
            "goal_proposals": [_alignment_goal()],
            "abductive_compositions": [],
            "action_aliases": list(action_aliases),
            "open_questions": ["Will the interpretation survive another observation?"],
            "cited_ids": ["a"],
        },
    }}


def test_qwen_scratchpad_is_bounded_unverified_and_cited():
    scratchpad = load("scratchpad")
    qc = fake_qc()
    scratchpad.install(qc)
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    assert "natural_language_scratchpad" in qc.response_schema(turn)["required"]
    assert "workspace_write" in qc.response_schema(turn)["required"]
    response = {
        "parsed": {
            "protocol": "p",
            "request_id": "r",
            "natural_language_scratchpad": "I am comparing the stable visible relations and tracking what remains unknown.",
            "workspace_write": {
                "summary": "Two compact components retain a stable relation.",
                "objective_hypothesis": "Reduce their relational residual.",
                "goal_proposals": [{"verb": "align", "schema_name": "Relational convergence", "goal_family": "alignment", "roles": ["actor", "target"], "potential_roles": ["actor", "target"], "observable": "centroid_distance", "direction": "decrease", "terminal_class": "minimum", "terminal_condition": "the residual is minimal", "role_constraints": [{"predicate": "different_value", "arguments": ["actor", "target"]}]}],
                "abductive_compositions": [],
                "action_aliases": [],
                "open_questions": ["Which relation changes under intervention?"],
                "cited_ids": ["a"],
            },
        }
    }
    compiled = qc.compile_response(response, turn)
    note = compiled["working_note"]
    assert note["verified"] is False
    assert note["token_count"] <= note["token_budget"] == 1024
    assert compiled["accepted"][-1]["kind"] == "working_note"
    request = qc.request_payload(turn, {})
    assert request["response_format"]["json_schema"]["schema"]["required"].count("natural_language_scratchpad") == 1
    verb_schema = request["response_format"]["json_schema"]["schema"]["properties"]["workspace_write"]["properties"]["goal_proposals"]["items"]
    role_vocabulary = verb_schema["properties"]["roles"]["items"]["enum"]
    assert "reference" in role_vocabulary
    assert "f00" not in role_vocabulary
    observables = verb_schema["properties"]["observable"]["enum"]
    assert "fit_residual" in observables
    clue_schema = verb_schema["properties"]["role_constraints"]
    assert "minItems" not in clue_schema
    assert set(clue_schema["items"]["properties"]["modality"]["enum"]) == {"required", "suggested", "anti-clue", "unknown"}
    assert "modality" in clue_schema["items"]["required"]
    assert "overlap_deficit" in observables
    assert "overlap_area" not in observables


def test_qwen_action_alias_uses_existing_turn_and_action_specific_r2_evidence():
    scratchpad = load("scratchpad_alias") if (HERE / "scratchpad_alias.py").exists() else load("scratchpad")
    qc = fake_qc()
    original_request = qc.request_payload
    request_calls = []
    qc.request_payload = lambda *args, **kwargs: request_calls.append(1) or original_request(*args, **kwargs)
    scratchpad.install(qc)
    scratchpad.record_r2_transition_observation(
        action=3, observation_changed=True, outcome="changed",
        trace="Action 3 moved one tracked role upward.",
        settlement={
            "explanation_binding_id": "binding:effect-3",
            "learned_effects": [{
                "trajectory_id": "trajectory:actor-3",
                "region_type": "region-type:tracked",
                "delta": [-1.0, 0.0],
            }],
        },
    )
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    evidence_ref = turn.document["scratchpad_context"]["r2_transition_observation"]["evidence_ref"]
    response = semantic_response(action_aliases=[{
        "action_id": "ACTION_3", "alias": "move up", "status": "tentative",
        "evidence_refs": [evidence_ref],
    }])
    compiled = qc.compile_response(response, turn)
    assert not compiled["rejected"]
    assert compiled["working_note"]["action_aliases"] == response["parsed"]["workspace_write"]["action_aliases"]
    assert compiled["working_note"]["verified"] is False
    assert next(item for item in compiled["accepted"] if item["kind"] == "explanation")["support"] == 0

    request = qc.request_payload(turn, {})
    assert request_calls == [1]
    alias_schema = request["response_format"]["json_schema"]["schema"]["properties"]["workspace_write"]["properties"]["action_aliases"]
    branch = alias_schema["items"]["oneOf"][0]
    assert branch["properties"]["action_id"]["const"] == "ACTION_3"
    assert evidence_ref in branch["properties"]["evidence_refs"]["items"]["enum"]
    assert "authority from the name" in qc.PROMPT


def test_qwen_action_alias_abstention_is_valid_and_unsupported_alias_is_rejected():
    scratchpad = load("scratchpad_alias_validation") if (HERE / "scratchpad_alias_validation.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    schema = qc.response_schema(turn)["properties"]["workspace_write"]["properties"]["action_aliases"]
    assert schema["maxItems"] == 0
    abstained = qc.compile_response(semantic_response(action_aliases=[]), turn)
    assert not abstained["rejected"]
    unsupported = qc.compile_response(semantic_response(action_aliases=[{
        "action_id": "ACTION_7", "alias": "interact?", "status": "tentative",
        "evidence_refs": [],
    }]), turn)
    assert unsupported["accepted"] == []
    assert unsupported["rejected"][-1]["reason"] == "action-alias-evidence"


def test_qwen_action_alias_revision_replaces_gloss_without_mutating_prior_note():
    scratchpad = load("scratchpad_alias_revision") if (HERE / "scratchpad_alias_revision.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    scratchpad.record_r2_transition_observation(
        action=3, observation_changed=True, outcome="changed",
        trace="Action 3 changed the tracked configuration.",
        settlement={"explanation_binding_id": "binding:effect-3"},
    )
    first_turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    evidence_ref = first_turn.document["scratchpad_context"]["r2_transition_observation"]["evidence_ref"]
    first = qc.compile_response(semantic_response(action_aliases=[{
        "action_id": "ACTION_3", "alias": "move up", "status": "stable",
        "evidence_refs": [evidence_ref],
    }]), first_turn)
    prior_payload = first["working_note"]
    prior_snapshot = json.loads(json.dumps(prior_payload))
    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=prior_payload,
        created_revision=4, object_id="eo:prior-note",
    )])
    second_turn = qc.build_turn(state, (), None)
    assert second_turn.document["prior_working_note"]["action_aliases"][0]["alias"] == "move up"
    revised = qc.compile_response(semantic_response(action_aliases=[{
        "action_id": "ACTION_3", "alias": "context-dependent move?", "status": "tentative",
        "evidence_refs": [evidence_ref],
    }]), second_turn)
    assert not revised["rejected"]
    assert revised["working_note"]["action_aliases"][0]["alias"] == "context-dependent move?"
    assert prior_payload == prior_snapshot


def test_qwen_transport_omits_redundant_full_materialization_but_keeps_sparse_cut():
    scratchpad = load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    base = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    turn = replace(base, document={
        **base.document,
        "full_materialization": {"sentinel": "FULL_ONLY_" + "x" * 50000},
        "object_index": {"sentinel": "INDEX_ONLY_" + "y" * 20000},
        "sparse_cut": {"sentinel": "SPARSE_VISIBLE", "objects": [], "used_tokens": 10},
    })
    request = qc.request_payload(turn, {})
    content = request["messages"][0]["content"]
    text = content if isinstance(content, str) else content[0]["text"]
    assert "FULL_ONLY_" not in text
    assert "INDEX_ONLY_" not in text
    assert "SPARSE_VISIBLE" in text
    assert "bounded-sparse-cut" in text
    assert len(text) < 6000


def test_semantic_qwen_next_turn_reads_bounded_r2_projection_and_reset_clears_it():
    scratchpad = load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    projection = {
        "protocol": "r2.1-semantic-projection-v1",
        "authority": {"action_selection": "r2-only", "semantic_revision": "qwen-proposal-only"},
        "active_explanation": {"binding_id": "e1", "verb": "fit", "epistemic_status": "active", "detail": "x" * 20000},
        "competing_explanations": [{"binding_id": f"e{i}", "verb": "touch"} for i in range(20)],
        "salient_structural_bindings": [{"predicate": "SameOutline", "binding_id": str(i)} for i in range(40)],
        "open_shadows": [{"shadow_id": str(i)} for i in range(40)],
    }
    scratchpad.record_r2_action_trace("Action 2 → visible configuration changed")
    scratchpad.record_r2_semantic_projection(projection)
    scratchpad.record_r2_transition_observation(
        action=2, observation_changed=True, outcome="changed",
        trace="Action 2 → visible configuration changed",
        settlement={"adjudication": "confirmed", "actual_progress": 3},
    )
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    feedback = turn.document["scratchpad_context"]["r2_semantic_projection"]
    assert feedback["active_explanation"]["verb"] == "fit"
    assert feedback["authority"]["action_selection"] == "r2-only"
    assert len(json.dumps(feedback, sort_keys=True, separators=(",", ":"))) <= scratchpad.MAX_R2_SEMANTIC_PROJECTION_BYTES
    assert "r2_semantic_projection" in qc.PROMPT
    assert "Never declare your own revision grounded" in qc.PROMPT
    transition = turn.document["scratchpad_context"]["r2_transition_observation"]
    assert transition["role"] == "observed-history-not-action-proposal"
    assert transition["action"] == 2
    assert transition["prediction_settlement"]["adjudication"] == "confirmed"

    scratchpad.reset_episode_context()
    clean = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    assert clean.document["scratchpad_context"]["r2_semantic_projection"] is None
    assert clean.document["scratchpad_context"]["r2_transition_observation"] is None
    assert clean.document["scratchpad_context"]["r2_action_traces"] == []
    assert qc.response_schema(clean)["properties"]["workspace_write"]["properties"]["action_aliases"]["maxItems"] == 0


def test_semantic_qwen_can_propose_abductive_composition_only_over_exposed_schema_ids():
    scratchpad = load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    schema_a, schema_b = "schema:aaaaaaaaaaaaaaaa", "schema:bbbbbbbbbbbbbbbb"
    scratchpad.record_r2_semantic_projection({
        "protocol": "r2.1-semantic-projection-v1",
        "authority": {"action_selection": "r2-only"},
        "active_explanation": None,
        "categorical_comparisons": [
            {"schema_id": schema_a, "binding_id": "binding:a", "type": "region-binding", "residual_vector": {}},
            {"schema_id": schema_b, "binding_id": "binding:b", "type": "relation-binding", "residual_vector": {}},
        ],
        "grounded_abductions": [],
    })
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    schema = qc.response_schema(turn)
    abduction = schema["properties"]["workspace_write"]["properties"]["abductive_compositions"]
    assert abduction["maxItems"] == 1
    assert abduction["minItems"] == 1
    assert abduction["items"]["properties"]["morphisms"]["minItems"] == 1
    assert schema["properties"]["workspace_write"]["properties"]["goal_proposals"]["maxItems"] == 2
    assert set(abduction["items"]["properties"]["component_schema_ids"]["items"]["enum"]) == {schema_a, schema_b}
    response = {"parsed": {
        "protocol": "p", "request_id": "r",
        "natural_language_scratchpad": "I am composing the two grounded comparison definitions into a candidate diagram.",
        "workspace_write": {
            "summary": "Two comparison definitions may participate in one higher diagram.",
            "objective_hypothesis": "A shared structural completion may predict residual reduction.",
            "goal_proposals": [_alignment_goal()],
            "abductive_compositions": [{
                "local_ref": "ab0", "component_schema_ids": [schema_a, schema_b],
                "morphisms": [{"source_schema_id": schema_a, "target_schema_id": schema_b, "kind": "co_describes"}],
                "preferred_residual_changes": [{"comparison_schema_id": schema_a, "dimension": "schema_difference", "direction": "decrease"}],
                "open_questions": ["Does the predicted residual decrease?"],
            }],
            "action_aliases": [],
            "open_questions": ["Does the composition survive the next observation?"],
            "cited_ids": ["a"],
        },
    }}
    compiled = qc.compile_response(response, turn)
    assert compiled["valid_json_contract"] is True
    assert not compiled["rejected"]
    assert compiled["working_note"]["abductive_compositions"][0]["component_schema_ids"] == [schema_a, schema_b]


def test_causal_visual_unit_is_current_only_at_frame_zero():
    scratchpad = load("scratchpad")
    output = scratchpad.causal_visual_evidence([
        {"label": "CURRENT_FRAME frame_ref=vf:now role=initial", "data_url": "data:image/png;base64,x"},
    ])
    assert len(output) == 1
    assert output[0]["label"].startswith("CAUSAL_UNIT_CURRENT_FRAME order=1/1 predecessor=none")


def test_causal_visual_unit_orders_exact_pair_and_bounds_older_history():
    scratchpad = load("scratchpad")
    output = scratchpad.causal_visual_evidence([
        {"label": "IMMEDIATELY_PRECEDING_FRAME frame_ref=vf:before transition_ref=vt:t intervention_ref=im:a", "data_url": "before"},
        {"label": "CURRENT_FRAME frame_ref=vf:after transition_ref=vt:t role=after", "data_url": "after"},
        {"label": "HISTORICALLY_SALIENT_AFTER_FRAME frame_ref=vf:old", "data_url": "old"},
        {"label": "HISTORICALLY_SALIENT_AFTER_FRAME frame_ref=vf:too-old", "data_url": "too-old"},
    ])
    assert [item["data_url"] for item in output] == ["before", "after", "old"]
    assert output[0]["label"].startswith("CAUSAL_UNIT_PREVIOUS_FRAME order=1/2")
    assert output[1]["label"].startswith("CAUSAL_UNIT_CURRENT_FRAME order=2/2")
    assert "transition_ref=vt:t" in output[0]["label"]
    assert "transition_ref=vt:t" in output[1]["label"]


def test_causal_visual_unit_rejects_reversed_pair():
    scratchpad = load("scratchpad")
    try:
        scratchpad.causal_visual_evidence([
            {"label": "CURRENT_FRAME frame_ref=vf:after", "data_url": "after"},
            {"label": "IMMEDIATELY_PRECEDING_FRAME frame_ref=vf:before", "data_url": "before"},
        ])
    except ValueError as error:
        assert "begin with the predecessor" in str(error)
    else:
        raise AssertionError("reversed causal frame pair was accepted")


def test_qwen_scratchpad_rejects_action_language():
    scratchpad = load("scratchpad_forbidden") if (HERE / "scratchpad_forbidden.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    compiled = qc.compile_response({"parsed": {"protocol": "p", "request_id": "r", "natural_language_scratchpad": "Choose action 2", "workspace_write": {
        "summary": "Choose action 2", "objective_hypothesis": "", "goal_proposals": [{"verb": "probe", "schema_name": "Unsafe", "goal_family": "unknown", "roles": ["actor", "target"], "potential_roles": ["actor", "target"], "observable": "unknown", "direction": "unknown", "terminal_class": "open", "terminal_condition": "unknown", "role_constraints": [{"predicate": "different_value", "arguments": ["actor", "target"]}]}], "abductive_compositions": [], "action_aliases": [], "open_questions": [], "cited_ids": ["a"]
    }}}, turn)
    assert compiled["valid_json_contract"] is True
    assert compiled["accepted"] == []
    assert compiled["rejected"][-1]["reason"] == "working-note-safety-or-budget"


def test_qwen_safety_filter_allows_the_semantic_phrase_action_free():
    scratchpad = load("scratchpad_action_free") if (HERE / "scratchpad_action_free.py").exists() else load("scratchpad")
    assert scratchpad._has_action_proposal("Two action-free prospective schemas remain.") is False
    assert scratchpad._has_action_proposal("Choose action 2") is True


def test_initial_working_hypothesis_is_an_unverified_explanation():
    scratchpad = load("scratchpad_initial") if (HERE / "scratchpad_initial.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    base = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    turn = replace(base, mode="initial-full", workspace_id="generic_prospective--ar25--shared", document={"protocol": "p"})
    compiled = qc.compile_response({"parsed": {"protocol": "p", "request_id": "r", "natural_language_scratchpad": "I am looking for a compact relation that could organize the visible figures.", "workspace_write": {
        "summary": "A visible relation may organize the figures.",
        "objective_hypothesis": "The relation is a candidate source of goal-relevant structure.",
        "goal_proposals": [{"verb": "organize", "schema_name": "Candidate organization", "goal_family": "unknown", "roles": ["actor", "target"], "potential_roles": ["actor", "target"], "observable": "unknown", "direction": "unknown", "terminal_class": "open", "terminal_condition": "requires observation", "role_constraints": [{"predicate": "different_value", "arguments": ["actor", "target"]}]}],
        "abductive_compositions": [],
        "action_aliases": [],
        "open_questions": ["Does the relation persist?"],
        "cited_ids": ["a"],
    }}}, turn)
    explanation = next(item for item in compiled["accepted"] if item["kind"] == "explanation")
    assert explanation["payload"]["status"] == "unverified"
    assert explanation["support"] == 0
    semantic_write = json.dumps(compiled["accepted"]).lower()
    assert "ar25" not in semantic_write
    assert "workspace_id" not in semantic_write


def test_qwen_turn_includes_r2_action_trace_in_scratchpad_context():
    scratchpad = load("scratchpad_trace") if (HERE / "scratchpad_trace.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    scratchpad.record_r2_action_trace("Action 3 → f00 moved down 1")
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    assert turn.document["scratchpad_context"]["r2_action_traces"] == ["Action 3 → f00 moved down 1"]


def test_semantic_projection_quarantines_action_boundary_payloads():
    scratchpad = load("scratchpad_projection") if (HERE / "scratchpad_projection.py").exists() else load("scratchpad")
    payload = {
        "action_id": 5, "reason": "Action 5 moved left", "observation_changed": True,
        "level_delta": 0, "status": "settled-from-successor-observation",
    }
    projected, omitted = scratchpad.semantic_control_projection("action_settlement", payload, "abc123")
    rendered = json.dumps(projected).lower()
    assert "action_id" not in rendered
    assert "action 5" not in rendered
    assert "left" not in rendered
    assert projected["observation_changed"] is True
    assert projected["level_delta"] == 0
    assert set(omitted) >= {"action_id", "reason"}
