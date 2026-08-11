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
    for phrase in ("EXPLANATION · CURRENT", "CONTROL V0 · CURRENT PROPOSAL", "SALIENT VERBS", "R2.1 SCHEMA LEVELS · CURRENT FRAME", "CATEGORICAL DIAGRAMS · ABDUCTIONS", "METADATA", "QWEN SCRATCHPAD", "R2 FEEDBACK · READ BY NEXT SEMANTIC QWEN", "ACTION ALIASES · QWEN GLOSS, NOT CONTROL", "DETAILED EVENT LOG", "LIVE RUNTIME TELEMETRY · PRESENTATION ONLY · NOT EVIDENCE", "arcade-log", "appendArcadeEvent", "captureArcadeEvents", "log-action", "log-qwen", "log-alias", "log-settlement", "log-fast", "POLICY AUTHORIZED", "log-level", "log-error", "FOLLOW ON", "CLEAR", "action-token", "action-gloss", "actionColor", "actionAlias", "actionBadge", "STEP ONE", "RESET", "LEVEL ACTION ${levelTurn}/${budget", "TOTAL ${turn}", "SPEED", "AGENT ARCADE", "verb-chip", "verbColor", "USES", "executableExplanation", "POTENTIAL", "PREDICTS", "HYPOTHESES", "EVIDENCE", "generic-fast-path-v15", "expectedArcadeUiVersion", "semantic update rejected; control continues"):
        assert phrase in page
    assert "TOP-3 NEXT ACTIONS" not in page
    assert "SALIENT SCHEMAS" not in page
    assert "value?.verb||value?.claim" not in page
    assert "const name=String(value?.verb||'')" in page
    assert "/^[a-z][a-z0-9_]{0,39}$/" in page
    assert page.index("EXPLANATION · CURRENT") < page.index("CONTROL V0 · CURRENT PROPOSAL") < page.index("SALIENT VERBS") < page.index("R2.1 SCHEMA LEVELS · CURRENT FRAME") < page.index("CATEGORICAL DIAGRAMS · ABDUCTIONS") < page.index("METADATA")
    assert page.index("</main>") < page.index("DETAILED EVENT LOG")


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
    assert settled["preferred_order"]["advanced"] is True
    assert settled["protected_invariants"]["hold"] is True
    assert observer.fast_policy_state is not None


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


def test_r2_1_same_state_no_change_closes_that_exact_probe():
    adapter = load("r2_1_no_change_probe_adapter") if (HERE / "r2_1_no_change_probe_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, _middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)

    first = observer.rank_actions(
        (1, 2), fallback_action=1, semantic_goal=_alignment_goal(),
        same_frame_no_change={},
    )
    assert first["selected_action"] == 1
    assert first["top_actions"][0]["eligibility"] == "PROBE_ELIGIBLE"

    second = observer.rank_actions(
        (1, 2), fallback_action=1, semantic_goal=_alignment_goal(),
        same_frame_no_change={1: 1},
    )
    assert second["selected_action"] == 2
    assert second["top_actions"][0]["eligibility"] == "PROBE_ELIGIBLE"
    repeated = next(item for item in second["top_actions"] if item["action"] == 1)
    assert repeated["eligibility"] == "INELIGIBLE"
    assert repeated["risk"] == 1


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


def test_r2_1_level_transition_retains_game_mechanics_but_clears_bindings():
    adapter = load("r2_1_level_scope_adapter") if (HERE / "r2_1_level_scope_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    observer.rank_actions((1, 4), fallback_action=4, semantic_goal=_alignment_goal())
    observer.settle_action(4, before, middle)
    effects = observer.action_effects
    uses = observer.action_uses
    assert effects and uses and observer.last_workspace is not None

    observer.advance_level()

    assert observer.action_effects is effects
    assert observer.action_uses is uses
    assert observer.action_effects and observer.action_uses
    assert observer.last_digest is None
    assert observer.last_workspace is None
    assert observer.last_regions == []
    assert observer.pending_prediction is None
    assert observer.role_trajectories == {}


def test_r2_1_retry_boundary_retains_mechanics_but_clears_pending_state():
    adapter = load("r2_1_retry_scope_adapter") if (HERE / "r2_1_retry_scope_adapter.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    before, middle, _after = _three_alignment_frames()
    observer.fit_frame(before, turn=0)
    observer.rank_actions((1, 4), fallback_action=4, semantic_goal=_alignment_goal())
    observer.settle_action(4, before, middle)
    effects = observer.action_effects
    uses = observer.action_uses
    observer.pending_prediction = {"action": 4}

    observer.retry_level()

    assert observer.action_effects is effects and observer.action_effects
    assert observer.action_uses is uses and observer.action_uses
    assert observer.last_workspace is None
    assert observer.pending_prediction is None
    assert observer.fast_policy_state is None


def test_leaf_integration_preserves_retry_boundary_through_ingest_wrapper():
    integration = load("integration")
    calls = []
    sentinel = object()

    def inherited(*args, **kwargs):
        calls.append((args, kwargs))
        return sentinel

    base = SimpleNamespace(
        persist_prospective_plan=lambda *args, **kwargs: None,
        ingest_transition_graph=inherited,
        apply_qwen_compilation=lambda *args, **kwargs: None,
    )
    integration.install(base)

    result = base.ingest_transition_graph(
        "root",
        "workspace",
        "state",
        "cognition",
        transition_id="transition",
        before_grid=((0,),),
        after_grid=((1,),),
        before_record={"digest": "before"},
        after_record={"digest": "after"},
        legal=(1,),
        intervention_ref="intervention",
        boundary_kind="game-over-retry",
    )

    assert result is sentinel
    assert calls[0][1]["boundary_kind"] == "game-over-retry"


def test_leaf_integration_persists_executable_not_advisory_selection_rule():
    integration = load("integration_selection_rule") if (HERE / "integration_selection_rule.py").exists() else load("integration")
    written = []
    state = SimpleNamespace(
        revision=3,
        objects=[
            SimpleNamespace(
                kind="explanation", created_by="qwen", created_revision=1,
                object_id="eo:qwen-explanation",
            ),
            SimpleNamespace(
                kind="frame", created_by="environment", created_revision=2,
                object_id="eo:frame",
            ),
        ],
    )

    class Graph:
        @staticmethod
        def find_objects(current, *, kind, created_by=None):
            return [
                item for item in current.objects
                if item.kind == kind
                and (created_by is None or item.created_by == created_by)
            ]

    def ensure_graph_object(_root, _workspace_id, current, *, kind, payload, **_kwargs):
        written.append((kind, payload))
        return current, f"eo:{kind}:{len(written)}"

    base = SimpleNamespace(
        EG=Graph,
        ensure_graph_object=ensure_graph_object,
        persist_prospective_plan=lambda _root, _workspace_id, current, _controller, _plan: (
            current,
            {
                "proposal_object_id": "eo:proposal",
                "prediction_objects": {},
                "selected_prediction_objects": [],
            },
        ),
        ingest_transition_graph=lambda *args, **kwargs: None,
        apply_qwen_compilation=lambda *args, **kwargs: None,
    )
    integration.install(base)
    controller = SimpleNamespace(last_contract={
        "objective": {},
        "explanations": [],
        "current_explanation": {},
        "selection_role": "information",
        "selection_rule": "executed-default-rule",
        "advisory_selection_rule": "raw-advisory-rule",
        "candidate_count": 2,
        "selected_action": 1,
    })
    plan = SimpleNamespace(
        plan_id="plan:selection-rule", basis_revision=3,
        observation_digest="frame", selected_prediction_ids=(), predictions=(),
    )

    base.persist_prospective_plan("root", "workspace", state, controller, plan)

    rationale = next(payload for kind, payload in written if kind == "decision_rationale")
    assert rationale["selection_rule"] == "executed-default-rule"
    assert "raw-advisory-rule" not in rationale.values()


def test_controller_retry_does_not_learn_action_zero_and_clears_situated_control():
    module = load("controller_retry_boundary") if (HERE / "controller_retry_boundary.py").exists() else load("controller")
    pair = lambda *_args: SimpleNamespace(uses={})
    live = SimpleNamespace(
        ProspectiveWorkspaceController=BaseController,
        PC=SimpleNamespace(fallback_plan=lambda plan, **_kwargs: plan),
        Q0=SimpleNamespace(PairPotentialController=pair),
    )
    instance = module.controller_class(live)()
    instance.records = []
    instance.active_schema_ids = set()
    instance.probe_decisions = 3
    instance.control_decisions = 2
    instance.last_plan_records = []
    instance.no_change_attempts[("failed", 1)] = 2
    instance.command_no_change[("failed", "command")] = 2
    instance.pending_r2_prediction_id = "prediction"
    before_uses = dict(instance.action_uses)

    result = instance.observe_game_over_retry(((9,),), ((1,),))

    assert result["retry_boundary"] is True
    assert instance.action_uses == before_uses
    assert 0 not in instance.action_uses
    assert instance.no_change_attempts == {}
    assert instance.command_no_change == {}
    assert instance.pending_r2_prediction_id is None
    assert instance.last_contract is None
    assert instance.last_command is None
    assert instance.fast_path.license is None


def test_live_runtime_resets_only_per_level_action_counter_on_level_advance():
    runtime = load("runtime_level_scope") if (HERE / "runtime_level_scope.py").exists() else load("runtime")
    calls = []
    observer = SimpleNamespace(
        advance_level=lambda: calls.append("advance"),
        fit_frame=lambda frame, turn: {"turn": turn, "frame": frame},
    )
    live = runtime.LiveRuntime()
    live.set_schema_observer(observer)
    live.snapshot.update({"turn": 7, "level_turn": 7, "levels_completed": 0, "level_action_budget": 48})
    controller = SimpleNamespace(settlements=[])
    live.after_action(
        SimpleNamespace(frame=[[[1]]], levels_completed=1, win_levels=3), controller,
    )
    state = live.read()
    assert calls == ["advance"]
    assert state["turn"] == 8
    assert state["level_turn"] == 0
    assert state["actions_remaining"] == 48
    assert state["level_transition"] is True


def test_live_runtime_retry_counts_one_same_level_action_and_regrounds():
    runtime = load("runtime_retry_scope") if (HERE / "runtime_retry_scope.py").exists() else load("runtime")
    calls = []
    observer = SimpleNamespace(
        retry_level=lambda: calls.append("retry"),
        fit_frame=lambda frame, turn: calls.append(("fit", turn)) or {"turn": turn},
    )
    live = runtime.LiveRuntime()
    live.set_schema_observer(observer)
    live.snapshot.update({
        "turn": 7, "level_turn": 7, "levels_completed": 2,
        "level_action_budget": 48,
    })
    controller = SimpleNamespace(
        settlements=[{"outcome": "game-over-retry-reset"}],
    )

    live.after_retry_reset(
        SimpleNamespace(frame=[[[1]]], levels_completed=2, win_levels=4), controller,
    )

    state = live.read()
    assert calls == ["retry", ("fit", 8)]
    assert state["turn"] == 8
    assert state["level_turn"] == 8
    assert state["actions_remaining"] == 40
    assert state["retry_boundary"] is True
    assert state["level_transition"] is False


def test_live_runtime_skips_recursive_refit_during_authorized_fast_path():
    runtime = load("runtime_fast_path") if (HERE / "runtime_fast_path.py").exists() else load("runtime")
    fits = []; commits = []
    observer = SimpleNamespace(
        fit_frame=lambda frame, turn: fits.append((frame, turn)) or {"turn": turn},
        commit_prediction=lambda action, explanation: commits.append((action, explanation)),
    )
    authority = SimpleNamespace(document=lambda: {"status": "AUTHORIZED", "remaining": 2})
    controller = SimpleNamespace(
        fast_path_active=True,
        fast_path=authority,
        last_contract={"selected_action": 3, "current_explanation": {"prediction": {"action": 3}}},
        settlements=[],
    )
    live = runtime.LiveRuntime()
    live.set_schema_observer(observer)
    live.snapshot.update({"turn": 4, "levels_completed": 0, "r2_1_schema_stats": {"turn": 3}})
    live.configure(speed=20)
    environment = SimpleNamespace(observation_space=SimpleNamespace(frame=[[[0, 2, 0]]]))
    live.before_action(environment, controller)
    live.after_action(SimpleNamespace(frame=[[[0, 0, 2]]], levels_completed=0, win_levels=2), controller)
    assert fits == []
    assert commits[-1][0] == 3
    assert live.read()["r2_1_schema_stats"]["fast_path"] is True


def test_multilevel_run_is_enabled_with_a_per_level_budget_and_boundary_hooks():
    config = json.loads((HERE / "config.json").read_text())
    assert config["continue_across_levels"] is True
    assert config["reset_action_budget_each_level"] is True
    base_source = (HERE.parent / "parallel-cognitive-workspace-v1-4" / "experiment.py").read_text()
    assert "while True:" in base_source
    assert 'stop_reason = "level-action-budget"' in base_source
    assert "controller.observe_level_transition" in base_source
    assert "cognition.advance_level(after_grid)" in base_source
    assert "level_transition=level_transition" in base_source
    bridge_source = (HERE.parent / "parallel-cognitive-workspace-v1-9" / "experiment.py").read_text()
    assert "level_transition: bool = False" in bridge_source
    assert "level_transition=level_transition" in bridge_source


def test_headless_run_installs_the_same_r2_1_observer_as_arcade():
    experiment = load("experiment")
    runtime = experiment.active_runtime()
    assert isinstance(runtime, experiment.RUNTIME.LiveRuntime)
    assert isinstance(runtime.schema_observer, experiment.R2_1.FrameSchemaObserver)

    supplied = experiment.RUNTIME.LiveRuntime()
    assert experiment.active_runtime(supplied) is supplied
    assert isinstance(supplied.schema_observer, experiment.R2_1.FrameSchemaObserver)


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
        "local_ref": "composition_0", "component_schema_ids": component_ids[:2],
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
        "local_ref": "composition_0", "component_schema_ids": ["schema:missing-a", "schema:missing-b"],
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


def test_equal_vector_index_is_exactly_equivalent_to_exhaustive_pareto_filter():
    adapter = load("r2_1_pareto_index") if (HERE / "r2_1_pareto_index.py").exists() else load("r2_1_adapter")
    dimensions = ("shape", "area", "mass")
    vectors = [
        (float(index % 5), float((index * 3) % 7), float((index * 5) % 11))
        for index in range(29)
    ]
    candidates = [
        {
            "candidate": index,
            "residual_vector": dict(zip(dimensions, vectors[index % len(vectors)], strict=True)),
        }
        for index in range(4032)
    ]
    unique = {
        vector: dict(zip(dimensions, vector, strict=True))
        for vector in vectors
    }
    nondominated_vectors = {
        vector
        for vector, residuals in unique.items()
        if not any(
            other_vector != vector
            and adapter.DefeasibleRoleGrounder._dominates(other, residuals, dimensions)
            for other_vector, other in unique.items()
        )
    }
    expected = [
        item for item in candidates
        if tuple(item["residual_vector"][key] for key in dimensions) in nondominated_vectors
    ]

    class CountingGrounder(adapter.DefeasibleRoleGrounder):
        dominance_calls = 0

        @staticmethod
        def _dominates(left, right, compared_dimensions):
            CountingGrounder.dominance_calls += 1
            return adapter.DefeasibleRoleGrounder._dominates(
                left, right, compared_dimensions,
            )

    actual = CountingGrounder._pareto_front(candidates, dimensions)
    assert actual == expected
    assert [id(item) for item in actual] == [id(item) for item in expected]
    assert CountingGrounder.dominance_calls <= len(vectors) * (len(vectors) - 1)
    assert CountingGrounder.dominance_calls < len(candidates)


def test_indexed_and_exhaustive_role_grounders_return_identical_bindings():
    adapter = load("r2_1_pareto_grounding_equivalence") if (HERE / "r2_1_pareto_grounding_equivalence.py").exists() else load("r2_1_adapter")
    regions = []
    shapes = (
        ((0, 0),),
        ((0, 0), (0, 1)),
        ((0, 0), (1, 0), (1, 1)),
    )
    for index in range(12):
        shape = shapes[index % len(shapes)]
        regions.append({
            "binding_id": f"region:{index:02d}",
            "value": index % 4,
            "area": len(shape),
            "shape": shape,
            "outline": shape,
            "hole_count": 0,
            "center2": (index * 2, (index % 5) * 2),
        })
    measure = lambda _observable, left, right: float(
        abs(left["center2"][0] - right["center2"][0])
        + abs(left["center2"][1] - right["center2"][1])
    )
    goal = {
        "verb": "fit", "roles": ["actor", "target"],
        "potential_roles": ["actor", "target"],
        "observable": "centroid_distance", "role_constraints": [],
    }

    class ExhaustiveGrounder(adapter.DefeasibleRoleGrounder):
        @classmethod
        def _pareto_front(cls, candidates, dimensions):
            return [
                candidate for candidate in candidates
                if not any(
                    other is not candidate
                    and cls._dominates(
                        other["residual_vector"], candidate["residual_vector"], dimensions,
                    )
                    for other in candidates
                )
            ]

    indexed = adapter.DefeasibleRoleGrounder(
        regions, measure=measure, relation_bindings={},
    ).ground(goal)
    exhaustive = ExhaustiveGrounder(
        regions, measure=measure, relation_bindings={},
    ).ground(goal)
    assert indexed == exhaustive
    assert {item["candidate_binding_id"] for item in indexed} == {
        item["candidate_binding_id"] for item in exhaustive
    }


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
    assert instance.last_contract["selection_rule"] == "test"
    assert instance.last_contract["advisory_selection_rule"] is None


def test_controller_separates_unauthorized_r2_advice_from_executed_selection():
    controller = load("controller_advisory_selection") if (HERE / "controller_advisory_selection.py").exists() else load("controller")
    advisory = {
        "selected_action": 2,
        "top_actions": [{
            "rank": 1, "action": 2, "selected": True,
            "role": "known-nonprogress", "eligibility": "INELIGIBLE",
        }],
        "explanations": [], "current_explanation": None,
        "control_override": False, "execution_authorized": False,
        "selection_rule": "test-advisory",
    }
    observer = SimpleNamespace(rank_actions=lambda legal, **kwargs: advisory)
    runtime = SimpleNamespace(schema_observer=observer, snapshot={})
    pc = SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(
        plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason,
    ))
    live = SimpleNamespace(ProspectiveWorkspaceController=BaseController, PC=pc)
    instance = controller.controller_class(live, runtime)()
    decision, _plan = instance.plan((1, 2), observation_digest="frame", basis_revision=1)

    assert decision.action_id == 1
    assert instance.last_contract["selected_action"] == 1
    assert instance.last_contract["top_actions"][0]["action"] == 1
    assert instance.last_contract["top_actions"][0]["selected"] is True
    advisory_view = instance.last_contract["advisory_top_actions"][0]
    assert advisory_view["action"] == 2
    assert advisory_view["selected"] is False
    assert advisory_view["advisory_selected"] is True
    assert advisory_view["execution_authorized"] is False
    assert instance.last_contract["selection_rule"] == (
        "lexicographic(progress, decision-relevant-information, support, novelty, stable-id)"
    )
    assert instance.last_contract["advisory_selection_rule"] == "test-advisory"
    assert instance.last_contract["r2_1_explanation_control"] == advisory
    assert advisory["top_actions"][0]["selected"] is True


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
                "abductive_compositions": [{"local_ref": "composition_0"}],
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
    assert ranking_inputs[-1]["semantic_abductions"] == [{"local_ref": "composition_0"}]
    assert published[-1]["ranking"]["current_explanation"]["verb"] == "fit"
    instance.pending_r2_prediction_id = "r2.1:test-plan"
    learning = instance.observe(2, ((0, 2, 0),), ((0, 0, 2),))
    assert published[-1]["settlement"]["adjudication"] == "confirmed"
    assert learning["prospective_adjudication"]["judgments"] == [{
        "prediction_id": "r2.1:test-plan",
        "status": "supports",
        "source": "r2.1-explanation-settlement",
    }]
    assert instance.pending_r2_prediction_id is None
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


def semantic_response(*, action_aliases=(), natural_language="I am retaining a compact interpretation of observed structure."):
    return {"parsed": {
        "protocol": "p", "request_id": "r",
        "natural_language_scratchpad": natural_language,
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


def acknowledge_semantic_failure(response, turn, decision="revise"):
    task = turn.document["semantic_failure_revision_task"]
    response["parsed"]["workspace_write"]["semantic_failure_acknowledgment"] = {
        "decision": decision,
        "evidence_ref": task["current_transition_evidence_ref"],
    }
    if decision == "abstain":
        response["parsed"]["workspace_write"]["goal_proposals"] = []
        response["parsed"]["workspace_write"]["abductive_compositions"] = []
    return response


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
    assert alias_schema["minItems"] == alias_schema["maxItems"] == 1
    branch = alias_schema["items"]["oneOf"][0]
    assert branch["properties"]["action_id"]["const"] == "ACTION_3"
    assert evidence_ref in branch["properties"]["evidence_refs"]["items"]["enum"]
    assert "authority from the name" in qc.PROMPT


def test_newly_evidenced_action_immediately_requests_one_alias_revision():
    scratchpad = load("scratchpad_alias_trigger") if (HERE / "scratchpad_alias_trigger.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    state = SimpleNamespace(objects=[])
    assert qc.alias_revision_due(state, "ws") is False
    scratchpad.record_r2_transition_observation(
        action=2, observation_changed=True, outcome="changed",
        trace="Action 2 changed one tracked role.", settlement=None,
    )
    assert qc.alias_revision_due(state, "ws") is True
    state.objects.append(SimpleNamespace(
        kind="working_note", created_by="qwen", created_revision=1,
            object_id="eo:alias-note", payload={
            "workspace_ref": scratchpad._workspace_ref(qc, "ws"),
            "action_aliases": [{
                "action_id": "ACTION_2", "alias": "move?", "status": "tentative",
                "evidence_refs": ["r2-transition:any"],
            }],
        },
    ))
    assert qc.alias_revision_due(state, "ws") is False


def test_rejected_first_call_keeps_initial_semantics_due_until_valid_note():
    scratchpad = load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    state = SimpleNamespace(objects=[])

    # A rejected compilation commits no working note, so task count alone must
    # not starve frame-zero semantics.
    assert qc.initial_semantics_due(state, "ws") is True
    state.objects.append(SimpleNamespace(
        kind="working_note", created_by="qwen", created_revision=1,
        object_id="eo:valid-note", payload={
            "workspace_ref": scratchpad._workspace_ref(qc, "ws"),
        },
    ))
    assert qc.initial_semantics_due(state, "ws") is False


def test_semantic_failure_revision_due_only_for_explicit_unsupported_failure():
    scratchpad = load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    state = SimpleNamespace(objects=[])

    scratchpad.record_r2_semantic_projection({
        "active_explanation": {
            "epistemic_status": "grounded-open-mechanism",
            "confirmations": 0,
        },
        "latest_settlement": {"adjudication": "mechanism-observed"},
    })
    assert qc.semantic_failure_revision_due(state, "ws") is False

    state.objects.append(SimpleNamespace(
        kind="working_note", created_by="qwen", created_revision=1,
        object_id="eo:prior-note", payload={
            "workspace_ref": scratchpad._workspace_ref(qc, "ws"),
            "transition_evidence_ref": "r2-transition:prior",
        },
    ))
    scratchpad.record_r2_transition_observation(
        action=2, observation_changed=True, outcome="changed",
        trace="The prediction was contradicted.",
        settlement={"adjudication": "refuted", "actual_progress": -1.0},
    )
    scratchpad.record_r2_semantic_projection({
        "active_explanation": {"confirmations": 0},
        "latest_settlement": {"adjudication": "refuted"},
    })
    assert qc.semantic_failure_revision_due(state, "ws") is True

    scratchpad.record_r2_semantic_projection({
        "active_explanation": {"control_status": "PROGRESS_ELIGIBLE"},
        "rejected_semantic_proposals": [{"reason": "grounding-rejected"}],
        "latest_settlement": {"adjudication": "refuted"},
    })
    assert qc.semantic_failure_revision_due(state, "ws") is False

    scratchpad.record_r2_semantic_projection({
        "active_explanation": {"confirmations": 0},
        "rejected_semantic_proposals": [{"reason": "grounding-rejected"}],
    })
    assert qc.semantic_failure_revision_due(state, "ws") is True


def test_compact_projection_retains_progress_gate_across_refutation():
    scratchpad = load("scratchpad_compact_progress_support") if (HERE / "scratchpad_compact_progress_support.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    bounded = scratchpad.record_r2_semantic_projection({
        "protocol": "r2.1-semantic-projection-v1",
        "active_explanation": {
            "binding_id": "binding:active-progress",
            "verb": "fit",
            "epistemic_status": "active-progress-explanation",
            "control_status": "PROGRESS_ELIGIBLE",
            "epistemic_evaluation": {"confirmations": 0, "refutations": 1},
            "detail": "x" * (scratchpad.MAX_R2_SEMANTIC_PROJECTION_BYTES * 2),
        },
        "rejected_semantic_proposals": [{"reason": "competing-grounding-rejected"}],
        "latest_settlement": {
            "adjudication": "refuted",
            "actual_progress": 6.0,
            "explanation_binding_id": "binding:active-progress",
        },
    })

    assert bounded["projection_truncated"] is True
    assert len(json.dumps(bounded, sort_keys=True, separators=(",", ":"))) <= scratchpad.MAX_R2_SEMANTIC_PROJECTION_BYTES
    assert bounded["active_explanation"]["control_status"] == "PROGRESS_ELIGIBLE"
    assert bounded["active_explanation"]["epistemic_evaluation"] == {"confirmations": 0}
    assert qc.semantic_failure_revision_due(SimpleNamespace(objects=[]), "ws") is False


def test_minimal_projection_retains_confirmation_across_refutation():
    scratchpad = load("scratchpad_minimal_confirmation_support") if (HERE / "scratchpad_minimal_confirmation_support.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    oversized = "y" * (scratchpad.MAX_R2_SEMANTIC_PROJECTION_BYTES * 2)
    bounded = scratchpad.record_r2_semantic_projection({
        "protocol": "r2.1-semantic-projection-v1",
        "active_explanation": {
            "binding_id": "binding:confirmed",
            "verb": "fit",
            "epistemic_status": "grounded-predictive",
            "control_status": "PROBE_ELIGIBLE",
            "confirmations": 2,
            "epistemic_evaluation": {"confirmations": 2, "mechanism_confidence": 1.0},
            "potential": {"detail": oversized},
            "mechanism": {"detail": oversized},
        },
        "rejected_semantic_proposals": [{"reason": "competing-grounding-rejected"}],
        "latest_settlement": {
            "adjudication": "refuted",
            "actual_progress": 12.0,
            "explanation_binding_id": "binding:confirmed",
        },
    })

    assert bounded["projection_truncated"] is True
    assert len(json.dumps(bounded, sort_keys=True, separators=(",", ":"))) <= scratchpad.MAX_R2_SEMANTIC_PROJECTION_BYTES
    assert "potential" not in bounded["active_explanation"]
    assert bounded["active_explanation"]["control_status"] == "PROBE_ELIGIBLE"
    assert bounded["active_explanation"]["confirmations"] == 2
    assert bounded["active_explanation"]["epistemic_evaluation"] == {"confirmations": 2}
    assert qc.semantic_failure_revision_due(SimpleNamespace(objects=[]), "ws") is False


def test_alias_runtime_configuration_is_nonblocking_and_matches_qwen_context():
    config = json.loads((HERE / "config.json").read_text())
    qwen = config["qwen"]
    assert qwen["trigger_on_new_action_evidence"] is True
    assert qwen["eager_semantic_integration"] is False
    assert qwen["nonblocking_semantic_integration"] is True
    assert qwen["logical_release_delay_actions"] == 0
    assert qwen["context_window_tokens"] == 16384
    assert qwen["max_tokens"] == 2048
    service = Path("/home/pauloabelha/.config/systemd/user/reflector-qwen.service").read_text()
    assert "--ctx-size 16384" in service


def test_fast_path_authorizes_policy_not_action_and_revokes_on_failure():
    controller = load("controller_fast_path_authority") if (HERE / "controller_fast_path_authority.py").exists() else load("controller")
    authority = controller.FastPathAuthority({
        "minimum_confirmations": 2, "confidence_threshold": 0.8, "max_actions": 3,
    })
    explanation = {
        "schema_id": "schema:generic",
        "control_status": "PROGRESS_ELIGIBLE",
        "goal": {"measure": "ordered-state", "direction": "preferred", "terminal_class": "maximum"},
        "ports": {"situated_role_descriptors": {"subject": {"value": 7, "area": 2}}},
        "prediction": {"action": 2},
        "epistemic_evaluation": {"mechanism_confidence": 0.9},
    }
    confirmed = {
        "adjudication": "confirmed",
        "preferred_order": {"advanced": True},
        "protected_invariants": {"hold": True},
    }
    authority.consider(explanation, confirmed)
    assert not authority.active
    # Changing the selected action or palette value does not change the
    # policy signature; structural applicability and grounded effects do.
    explanation["prediction"]["action"] = 5
    explanation["ports"]["situated_role_descriptors"]["subject"]["value"] = 11
    authority.consider(explanation, confirmed)
    assert authority.active
    assert authority.document()["remaining"] == 3
    authority.consider(explanation, {
        **confirmed, "preferred_order": {"advanced": False},
    })
    assert not authority.active
    assert authority.document()["last_revocation"] == "successor-not-preferred"


def test_authorized_policy_can_choose_a_different_best_legal_action():
    adapter = load("r2_1_fast_policy") if (HERE / "r2_1_fast_policy.py").exists() else load("r2_1_adapter")
    observer = adapter.FrameSchemaObserver()
    observer.frame_shape = (20, 20)

    def region(value, x):
        return {
            "value": value, "area": 1, "cells": ((5, x),),
            "shape": ((0, 0),), "outline": ((0, 0),), "center2": (10.0, float(2 * x)),
            "binding_id": f"binding:{value}",
        }

    actor, target = region(2, 10), region(3, 2)
    for action, delta in ((1, (0.0, -1.0)), (4, (0.0, -3.0))):
        observer.action_effects[(action, observer._region_key(actor))][delta] = 3
        observer.action_effects[(action, observer._region_key(target))][(0.0, 0.0)] = 3
    template = {
        "schema_id": "schema:generic", "binding_id": "binding:explanation",
        "goal": {"measure": "centroid_distance", "direction": "decrease", "terminal_class": "minimum"},
        "desired_delta": {"measure": "centroid_distance", "direction": "decrease"},
        "ports": {
            "actor": actor["binding_id"], "target": target["binding_id"],
            "situated_roles": {"subject": actor["binding_id"], "reference": target["binding_id"]},
            "situated_role_descriptors": {
                "subject": {"value": 2, "area": 1}, "reference": {"value": 3, "area": 1},
            },
        },
        "identity": {"subject": {"status": "UNIQUE"}, "reference": {"status": "UNIQUE"}, "control_eligible": True},
        "epistemic_evaluation": {"mechanism_confidence": 1.0},
    }
    observer.fast_policy_state = {"template": template, "actor": actor, "target": target}
    ranking = observer.rank_authorized_policy((1, 4), authorization={
        "status": "AUTHORIZED", "signature": "generic-policy", "confidence": 0.8,
    })
    assert ranking is not None
    assert ranking["selected_action"] == 4
    assert ranking["current_explanation"]["prediction"]["expected_progress"] == 3.0


def test_controller_executes_authorized_evaluator_choice_not_fallback():
    controller = load("controller_fast_path_execution") if (HERE / "controller_fast_path_execution.py").exists() else load("controller")
    explanation = {
        "kind": "situated-control-explanation", "binding_id": "e-fast",
        "control_status": "PROGRESS_ELIGIBLE",
        "prediction": {
            "action": 2, "expected_progress": 1,
            "residual_before": 3, "residual_after": 2, "actor_delta": [0, 1],
        },
    }
    ranking = {
        "selected_action": 2,
        "top_actions": [{"rank": 1, "action": 2, "role": "authorized-policy"}],
        "explanations": [explanation], "current_explanation": explanation,
        "execution_authorized": True,
        "control_proposal": {"mode": "FAST_PATH", "action": 2},
        "selection_rule": "authorized evaluator",
    }
    observer = SimpleNamespace(rank_authorized_policy=lambda legal, **kwargs: ranking)
    runtime = SimpleNamespace(schema_observer=observer, snapshot={})
    pc = SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(
        plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason,
    ))
    live = SimpleNamespace(ProspectiveWorkspaceController=BaseController, PC=pc)
    instance = controller.controller_class(live, runtime)()
    instance.fast_path.license = {
        "status": "AUTHORIZED", "signature": "generic", "remaining": 2,
        "max_actions": 2, "max_failures": 0, "confirmations": 2, "confidence": 1.0,
    }
    decision, _plan = instance.plan((1, 2), observation_digest="frame", basis_revision=4)
    assert decision.action_id == 2
    assert decision.reason == "r2.1-bounded-fast-path"
    assert instance.last_contract["selected_action"] == 2
    assert instance.last_contract["current_explanation"]["prediction"]["action"] == 2


def test_controller_accepts_explicitly_absent_control_proposal():
    controller = load("controller")
    explanation = {
        "kind": "situated-control-explanation", "binding_id": "e-open",
        "control_status": "PROBE_ELIGIBLE",
        "prediction": {"action": 1, "expected_progress": None},
    }
    ranking = {
        "selected_action": 1,
        "top_actions": [{"rank": 1, "action": 1, "role": "probe", "selected": True}],
        "explanations": [explanation], "current_explanation": explanation,
        "execution_authorized": False,
        "control_proposal": None,
        "selection_rule": "bounded probe",
    }
    observer = SimpleNamespace(rank_actions=lambda legal, **kwargs: ranking)
    runtime = SimpleNamespace(schema_observer=observer, snapshot={})
    live = SimpleNamespace(ProspectiveWorkspaceController=BaseController, PC=SimpleNamespace(
        fallback_plan=lambda plan, action_id, reason: replace(
            plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason,
        )
    ))
    instance = controller.controller_class(live, runtime)()

    decision, _plan = instance.plan((1,), observation_digest="frame", basis_revision=4)

    assert decision.action_id == 1
    assert instance.last_contract["selected_action"] == 1
    assert instance.last_contract["current_explanation"] == explanation


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
    assert "natural_language" not in second_turn.document["prior_working_note"]
    assert second_turn.document["prior_working_note"]["prior_natural_language_digest"]
    unchanged = qc.compile_response(semantic_response(action_aliases=[{
        "action_id": "ACTION_3", "alias": "move up", "status": "stable",
        "evidence_refs": [evidence_ref],
    }]), second_turn)
    assert unchanged["rejected"][-1]["reason"] == "natural-language-scratchpad-not-revised"
    revised = qc.compile_response(semantic_response(action_aliases=[{
        "action_id": "ACTION_3", "alias": "context-dependent move?", "status": "tentative",
        "evidence_refs": [evidence_ref],
    }], natural_language="The latest observed transition makes the earlier directional gloss conditional."), second_turn)
    assert not revised["rejected"]
    assert revised["working_note"]["action_aliases"][0]["alias"] == "context-dependent move?"
    assert prior_payload == prior_snapshot


def test_scheduler_or_open_mechanism_evidence_preserves_an_exact_goal_set():
    scratchpad = load("scratchpad_semantic_stagnation") if (HERE / "scratchpad_semantic_stagnation.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    scratchpad.record_r2_transition_observation(
        action=1, observation_changed=False, outcome="no-visible-change",
        trace="Action 1 produced no visible change.", settlement=None,
    )
    first_turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    first = qc.compile_response(semantic_response(), first_turn)
    first_payload = first["working_note"]
    first_evidence_ref = first_turn.document["scratchpad_context"]["r2_transition_observation"]["evidence_ref"]
    assert first_payload["transition_evidence_ref"] == first_evidence_ref

    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=first_payload,
        created_revision=4, object_id="eo:prior-semantic-note",
    )])
    same_evidence_turn = qc.build_turn(state, (), None)
    assert "semantic_stagnation" not in same_evidence_turn.document["scratchpad_context"]
    same_evidence = qc.compile_response(semantic_response(
        natural_language="The same evidence still leaves the compact relational proposal open.",
    ), same_evidence_turn)
    assert not same_evidence["rejected"]

    prior_payload = same_evidence["working_note"]
    prior_snapshot = json.loads(json.dumps(prior_payload))
    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=prior_payload,
        created_revision=5, object_id="eo:latest-semantic-note",
    )])
    scratchpad.record_r2_transition_observation(
        action=2, observation_changed=True, outcome="changed",
        trace="Action 2 changed the visible relational configuration.",
        settlement={"adjudication": "mechanism-observed", "actual_progress": 1.0},
    )
    revised_turn = qc.build_turn(state, (), None)
    assert "semantic_stagnation" not in revised_turn.document["scratchpad_context"]
    new_evidence_ref = revised_turn.document["scratchpad_context"]["r2_transition_observation"]["evidence_ref"]
    preserved = qc.compile_response(semantic_response(
        natural_language="The new transition was reviewed but the structured proposal is unchanged.",
    ), revised_turn)
    assert not preserved["rejected"]
    assert preserved["working_note"]["transition_evidence_ref"] == new_evidence_ref
    assert prior_payload == prior_snapshot


def test_explicit_r2_grounding_rejection_blocks_an_exact_canonical_goal_set_repetition():
    scratchpad = load("scratchpad_semantic_rejection") if (HERE / "scratchpad_semantic_rejection.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    first = qc.compile_response(
        semantic_response(), qc.build_turn(SimpleNamespace(objects=[]), (), None),
    )
    prior_payload = first["working_note"]
    prior_snapshot = json.loads(json.dumps(prior_payload))
    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=prior_payload,
        created_revision=5, object_id="eo:rejected-semantic-note",
    )])
    scratchpad.record_r2_semantic_projection({
        "rejected_semantic_proposals": [{
            "reason": "no measurable typed tuple satisfies schema-required constraints",
        }],
        "open_shadows": [{"shadow_id": "shadow:still-open"}],
    })
    scratchpad.record_r2_transition_observation(
        action=2, observation_changed=True, outcome="changed",
        trace="Action 2 supplied successor evidence.", settlement=None,
    )
    revised_turn = qc.build_turn(state, (), None)
    guard = revised_turn.document["scratchpad_context"]["semantic_stagnation"]
    new_evidence_ref = revised_turn.document["scratchpad_context"]["r2_transition_observation"]["evidence_ref"]
    assert guard["new_transition_evidence_ref"] == new_evidence_ref
    assert guard["prior_goal_proposal_digests"]
    assert guard["explicit_failure_signals"][0]["kind"] == "r2-semantic-proposal-rejected"
    assert guard["authority"] == "qwen-must-revise-or-replace; r2-still-grounds-and-controls"

    task = revised_turn.document["semantic_failure_revision_task"]
    assert task["current_transition_evidence_ref"] == new_evidence_ref
    assert task["failure_signals"] == guard["explicit_failure_signals"]
    assert task["authority"]["semantic_revision_or_abstention"] == "qwen"

    repeated = qc.compile_response(acknowledge_semantic_failure(semantic_response(
        natural_language="The grounding rejection was reviewed but the structured proposal is unchanged.",
    ), revised_turn), revised_turn)
    assert repeated["accepted"] == []
    assert repeated["rejected"][-1]["reason"] == "evidence-stale-goal-proposal-repetition"
    assert repeated["rejected"][-1]["new_transition_evidence_ref"] == new_evidence_ref
    assert prior_payload == prior_snapshot

    changed_response = semantic_response(
        natural_language="The grounding rejection narrows the terminal claim while leaving grounding to R2.",
    )
    changed_response["parsed"]["workspace_write"]["goal_proposals"][0]["terminal_condition"] = (
        "the observed residual reaches a stable minimum"
    )
    changed_response["parsed"]["workspace_write"]["action_aliases"] = [{
        "action_id": "ACTION_2",
        "alias": "context-dependent effect?",
        "status": "tentative",
        "evidence_refs": [new_evidence_ref],
    }]
    acknowledge_semantic_failure(changed_response, revised_turn)
    changed = qc.compile_response(changed_response, revised_turn)
    assert not changed["rejected"]
    assert changed["working_note"]["transition_evidence_ref"] == new_evidence_ref
    assert changed["working_note"]["action_aliases"] == changed_response[
        "parsed"
    ]["workspace_write"]["action_aliases"]
    assert changed["working_note"]["verified"] is False
    changed_state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=changed["working_note"],
        created_revision=6, object_id="eo:changed-semantic-note",
    )])
    assert qc.semantic_failure_revision_due(changed_state, "w") is False


def test_unsupported_refutation_triggers_guard_but_progress_support_suppresses_it():
    scratchpad = load("scratchpad_semantic_refutation") if (HERE / "scratchpad_semantic_refutation.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    first = qc.compile_response(
        semantic_response(), qc.build_turn(SimpleNamespace(objects=[]), (), None),
    )
    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=first["working_note"],
        created_revision=4, object_id="eo:refuted-goal-note",
    )])
    scratchpad.record_r2_transition_observation(
        action=3, observation_changed=True, outcome="changed",
        trace="Action 3 contradicted the grounded prediction.",
        settlement={"adjudication": "refuted", "actual_progress": -1.0},
    )
    refuted_turn = qc.build_turn(state, (), None)
    assert refuted_turn.document["scratchpad_context"]["semantic_stagnation"]["explicit_failure_signals"] == [
        {"kind": "environment-prediction-refuted"},
    ]
    rejected = qc.compile_response(acknowledge_semantic_failure(semantic_response(
        natural_language="The contradiction was reviewed without changing the structured proposal.",
    ), refuted_turn), refuted_turn)
    assert rejected["rejected"][-1]["reason"] == "evidence-stale-goal-proposal-repetition"

    supported = load("scratchpad_semantic_supported_refutation") if (HERE / "scratchpad_semantic_supported_refutation.py").exists() else load("scratchpad")
    supported_qc = fake_qc(); supported.install(supported_qc)
    supported_first = supported_qc.compile_response(
        semantic_response(), supported_qc.build_turn(SimpleNamespace(objects=[]), (), None),
    )
    supported_state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=supported_first["working_note"],
        created_revision=4, object_id="eo:supported-goal-note",
    )])
    supported.record_r2_semantic_projection({
        "active_explanation": {
            "control_status": "PROGRESS_ELIGIBLE", "confirmations": 2,
        },
        "latest_settlement": {"adjudication": "refuted"},
        "rejected_semantic_proposals": [{"reason": "a competing grounding was rejected"}],
        "open_shadows": [{"shadow_id": "shadow:question-not-failure"}],
    })
    supported.record_r2_transition_observation(
        action=4, observation_changed=True, outcome="changed",
        trace="Action 4 produced mixed evidence.",
        settlement={"adjudication": "refuted", "actual_progress": -1.0},
    )
    supported_turn = supported_qc.build_turn(supported_state, (), None)
    assert "semantic_stagnation" not in supported_turn.document["scratchpad_context"]
    preserved = supported_qc.compile_response(semantic_response(
        natural_language="The supported goal remains while its mechanism evidence is reconsidered.",
    ), supported_turn)
    assert not preserved["rejected"]


def test_stagnation_guard_allows_preserving_one_exact_goal_when_the_proposal_set_changes():
    scratchpad = load("scratchpad_semantic_partial_revision") if (HERE / "scratchpad_semantic_partial_revision.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    first = qc.compile_response(
        semantic_response(), qc.build_turn(SimpleNamespace(objects=[]), (), None),
    )
    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=first["working_note"],
        created_revision=4, object_id="eo:stable-goal-note",
    )])
    scratchpad.record_r2_transition_observation(
        action=3, observation_changed=True, outcome="changed",
        trace="Action 3 exposed a second visible relation.", settlement=None,
    )
    scratchpad.record_r2_semantic_projection({
        "rejected_semantic_proposals": [{"reason": "role grounding rejected"}],
    })
    turn = qc.build_turn(state, (), None)
    assert "semantic_stagnation" in turn.document["scratchpad_context"]
    response = semantic_response(
        natural_language="The latest transition leaves one proposal stable and opens a distinct contact hypothesis.",
    )
    contact = dict(_alignment_goal())
    contact.update({
        "verb": "touch", "schema_name": "Candidate contact",
        "goal_family": "contact", "observable": "boundary_gap",
        "terminal_condition": "the boundary gap reaches its minimum",
    })
    response["parsed"]["workspace_write"]["goal_proposals"].append(contact)
    acknowledge_semantic_failure(response, turn)
    compiled = qc.compile_response(response, turn)
    assert not compiled["rejected"]
    assert compiled["working_note"]["goal_proposals"] == response["parsed"]["workspace_write"]["goal_proposals"]
    assert compiled["working_note"]["verified"] is False


def test_semantic_failure_abstention_is_durable_and_deduplicates_exact_evidence():
    scratchpad = load("scratchpad_semantic_failure_abstention") if (HERE / "scratchpad_semantic_failure_abstention.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    first = qc.compile_response(
        semantic_response(), qc.build_turn(SimpleNamespace(objects=[]), (), None),
    )
    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=first["working_note"],
        created_revision=4, object_id="eo:prior-goal-note",
    )])
    scratchpad.record_r2_semantic_projection({
        "rejected_semantic_proposals": [{
            "reason": "role grounding rejected",
            "schema_id": "schema:rejected",
            "binding_id": "binding:rejected",
        }],
    })
    scratchpad.record_r2_transition_observation(
        action=2, observation_changed=True, outcome="changed",
        trace="A new successor refuted the available grounding.", settlement=None,
    )
    turn = qc.build_turn(state, (), None)
    task = turn.document["semantic_failure_revision_task"]
    evidence_ref = task[
        "current_transition_evidence_ref"
    ]
    assert task["failure_addresses"]["rejected_semantic_proposals"] == [{
        "schema_id": "schema:rejected",
        "binding_id": "binding:rejected",
    }]
    abstained = qc.compile_response(acknowledge_semantic_failure(
        semantic_response(
            natural_language="The cited rejection leaves no defensible goal proposal in the closed vocabulary.",
        ),
        turn,
        decision="abstain",
    ), turn)

    assert not abstained["rejected"]
    assert abstained["working_note"]["goal_proposals"] == []
    assert abstained["working_note"]["transition_evidence_ref"] == evidence_ref
    acknowledged_state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=abstained["working_note"],
        created_revision=5, object_id="eo:abstained-note",
    )])
    assert qc.semantic_failure_revision_due(acknowledged_state, "w") is False
    assert "semantic_failure_revision_task" not in qc.build_turn(
        acknowledged_state, (), None,
    ).document

    scratchpad.record_r2_transition_observation(
        action=3, observation_changed=True, outcome="changed",
        trace="A distinct successor supplied new rejection evidence.", settlement=None,
    )
    assert qc.semantic_failure_revision_due(acknowledged_state, "w") is True


def test_semantic_failure_acknowledgment_is_exact_and_malformed_values_fail_closed():
    scratchpad = load("scratchpad_semantic_failure_ack") if (HERE / "scratchpad_semantic_failure_ack.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    first = qc.compile_response(
        semantic_response(), qc.build_turn(SimpleNamespace(objects=[]), (), None),
    )
    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", payload=first["working_note"],
        created_revision=4, object_id="eo:prior-note",
    )])
    scratchpad.record_r2_semantic_projection({
        "rejected_semantic_proposals": [{"reason": "grounding rejected"}],
    })
    scratchpad.record_r2_transition_observation(
        action=4, observation_changed=True, outcome="changed",
        trace="New evidence rejected the grounding.", settlement=None,
    )
    turn = qc.build_turn(state, (), None)
    schema = qc.response_schema(turn)["properties"]["workspace_write"]
    assert "semantic_failure_acknowledgment" in schema["required"]
    assert schema["properties"]["semantic_failure_acknowledgment"]["properties"][
        "evidence_ref"
    ]["const"] == turn.document["semantic_failure_revision_task"][
        "current_transition_evidence_ref"
    ]

    missing = qc.compile_response(semantic_response(
        natural_language="The new grounding rejection is being evaluated against the prior proposal.",
    ), turn)
    assert missing["rejected"][-1]["reason"] == "working-note-contract"
    mismatched = acknowledge_semantic_failure(semantic_response(
        natural_language="The new grounding rejection requires an evidence-addressed revision.",
    ), turn)
    mismatched["parsed"]["workspace_write"]["semantic_failure_acknowledgment"][
        "evidence_ref"
    ] = "r2-transition:not-current"
    rejected = qc.compile_response(mismatched, turn)
    assert rejected["rejected"][-1]["reason"] == (
        "semantic-failure-evidence-acknowledgment"
    )

    malformed_turn = replace(turn, document={
        **turn.document,
        "semantic_failure_revision_task": {
            "protocol": "evidence-addressed-semantic-failure-revision-v1",
        },
    })
    try:
        qc.response_schema(malformed_turn)
    except RuntimeError as error:
        assert "no evidence address" in str(error)
    else:
        raise AssertionError("malformed semantic failure task did not fail closed")


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
    assert len(text) < 6600


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
                "local_ref": "composition_0", "component_schema_ids": [schema_a, schema_b],
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


def test_durable_aliases_bypass_canonical_graph_cut_but_reenter_prior_note():
    scratchpad = load("scratchpad_alias_quarantine") if (HERE / "scratchpad_alias_quarantine.py").exists() else load("scratchpad")
    qc = fake_qc()
    qc._payload_projection = lambda _kind, value: (dict(value), [])
    qc.build_turn = lambda _state, _events, _orientation, **kwargs: Turn(
        "r", kwargs.get("workspace_id", "w"), 4, None, "delta", {"protocol": "p"},
    )
    scratchpad.install(qc)
    payload = {
        "workspace_ref": scratchpad._workspace_ref(qc, "ws"),
        "natural_language": "A tracked effect has a cautious gloss.",
        "action_aliases": [{
            "action_id": "ACTION_1", "alias": "move?", "status": "tentative",
            "evidence_refs": ["r2-transition:evidence"],
        }],
    }
    projected, omitted = qc._payload_projection("working_note", payload)
    assert "action_aliases" not in projected
    assert "action_aliases" in omitted
    state = SimpleNamespace(objects=[SimpleNamespace(
        kind="working_note", created_by="qwen", created_revision=1,
        object_id="eo:alias-note", payload=payload,
    )])
    turn = qc.build_turn(state, (), None, workspace_id="ws")
    assert turn.document["prior_working_note"]["action_aliases"][0]["action_id"] == "ACTION_1"
