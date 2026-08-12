from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess

import pytest

from reflector2.planner import (
    BoundedBestFirstPlanner,
    ControlProblem,
    LunaPlanningModel,
    ModelPlanner,
    NoPlanPlanner,
    PlannerConfig,
    QwenPlanningModel,
    SupportedCausalEffect,
    backend_from_name,
    derive_milestones,
    plan_certificate,
    search,
    settle_plan_certificate,
)
from reflector2.r2.planner_wiring import (
    QwenCliInvoker,
    browser_options,
    build_planner_backend,
    resolve_browser_selection,
)
from reflector2.r2.r2_1_adapter import FrameSchemaObserver
from reflector2.r2.controller import FastPathAuthority


class RecordingPlanner:
    name = "recording-test-planner"

    def __init__(self):
        self.calls = 0

    def search(self, problem, config):
        self.calls += 1
        return search(problem, config)


def _effect(name: str, delta: tuple[int, int], *, support: int = 2, confidence: float = 1.0):
    return SupportedCausalEffect(
        command_id=name,
        command={"protocol": "test-command", "command_id": name, "action_id": len(name)},
        actor_delta=delta,
        target_delta=(0, 0),
        support=support,
        contradictions=0,
        confidence=confidence,
    )


def _problem(*, size: int = 6, obstacle=frozenset({(1, 1)}), effects=None):
    initial = {"actor": (1, 0), "target": (1, 3), "obstacle": obstacle, "size": size}

    def transition(state, effect):
        ay, ax = state["actor"]
        ty, tx = state["target"]
        successor = (
            ay + effect.actor_delta[0], ax + effect.actor_delta[1]
        )
        target = (
            ty + effect.target_delta[0], tx + effect.target_delta[1]
        )
        if not all(0 <= part < state["size"] for point in (successor, target) for part in point):
            return None
        if successor in state["obstacle"] or target in state["obstacle"]:
            return None
        return {**state, "actor": successor, "target": target}

    def measure(state, observable):
        assert observable == "distance"
        return float(sum(abs(a - b) for a, b in zip(state["actor"], state["target"], strict=True)))

    milestones = derive_milestones(
        explanation_id="explanation:test",
        active_observable="distance",
        preferred_direction="decrease",
        terminal_observable="distance",
        max_milestones=4,
    )
    return ControlProblem(
        explanation_id="explanation:test",
        verb="approach",
        initial_state=initial,
        active_observable="distance",
        preferred_direction="decrease",
        initial_value=measure(initial, "distance"),
        effects=tuple(effects or (
            _effect("down", (1, 0)), _effect("left", (0, -1)),
            _effect("right", (0, 1)), _effect("up", (-1, 0)),
        )),
        milestones=milestones,
        transition=transition,
        measure=measure,
        invariants_hold=lambda _state: True,
        state_key=lambda state: json.dumps([state["actor"], state["target"]]),
        protected_invariants=("actor-identity", "target-identity", "mechanism-applicability"),
    )


def test_bounded_composition_can_choose_a_non_greedy_first_step_around_obstacle():
    result = search(_problem(), PlannerConfig(max_depth=6, max_expansions=256))
    assert result.status == "PLAN_FOUND"
    assert result.factorization is not None
    assert result.factorization.terminal_reached is True
    assert len(result.factorization.steps) == 5
    assert result.factorization.steps[0].command_id in {"down", "up"}
    assert result.factorization.steps[0].potential_after > result.factorization.steps[0].potential_before


def test_planner_is_deterministic_and_scene_translation_independent():
    first = search(_problem())
    second = search(_problem())
    assert first.factorization == second.factorization

    shifted = _problem(obstacle=frozenset({(3, 3)}))
    shifted_state = {**shifted.initial_state, "actor": (3, 2), "target": (3, 5)}
    shifted = replace(shifted, initial_state=shifted_state)
    translated = search(shifted)
    assert translated.status == "PLAN_FOUND"
    assert translated.factorization is not None
    assert translated.factorization.steps[0].command_id == first.factorization.steps[0].command_id


def test_planner_is_palette_orientation_and_scale_independent():
    base = _problem()
    recolored = replace(
        base,
        initial_state={**base.initial_state, "actor_value": 9, "target_value": 4},
    )
    assert search(recolored).factorization == search(base).factorization

    rotated = _problem(obstacle=frozenset({(1, 1)}))
    rotated_state = {**rotated.initial_state, "actor": (0, 1), "target": (3, 1)}
    rotated = replace(
        rotated, initial_state=rotated_state,
        initial_value=rotated.measure(rotated_state, "distance"),
    )
    rotated_result = search(rotated)
    assert rotated_result.factorization is not None
    assert rotated_result.factorization.steps[0].command_id in {"left", "right"}

    scaled_effects = tuple(
        _effect(name, (2 * delta[0], 2 * delta[1]))
        for name, delta in (
            ("down", (1, 0)), ("left", (0, -1)),
            ("right", (0, 1)), ("up", (-1, 0)),
        )
    )
    scaled = _problem(
        size=12, obstacle=frozenset({(2, 2)}), effects=scaled_effects,
    )
    scaled_state = {**scaled.initial_state, "actor": (2, 0), "target": (2, 6)}
    scaled = replace(
        scaled, initial_state=scaled_state,
        initial_value=scaled.measure(scaled_state, "distance"),
    )
    scaled_result = search(scaled)
    assert scaled_result.factorization is not None
    assert len(scaled_result.factorization.steps) == 5
    assert scaled_result.factorization.steps[0].command_id in {"down", "up"}


def test_search_never_mutates_empirical_support_or_promotes_hypothetical_states():
    problem = _problem()
    evidence = {effect.command_id: {"support": effect.support} for effect in problem.effects}
    before = deepcopy(evidence)
    result = search(problem)
    assert evidence == before
    assert all(step.epistemic_status == "hypothetical" for step in result.factorization.steps)
    assert result.factorization.steps[-1].causal_support == 2


def test_unsupported_mechanisms_return_clean_no_plan():
    problem = _problem(effects=(_effect("unsupported", (0, 1), support=0, confidence=0.0),))
    result = search(problem)
    assert result.status == "NO_PLAN"
    assert result.factorization is None
    assert result.reason == "no-explicitly-supported-causal-effects"


def test_original_and_factorization_backends_are_directly_swappable():
    original = backend_from_name("original")
    modern = backend_from_name("bounded-best-first-v0")
    assert isinstance(original, NoPlanPlanner)
    assert isinstance(modern, BoundedBestFirstPlanner)
    assert original.search(_problem(), PlannerConfig()).reason == "delegated-to-host-controller"
    assert modern.search(_problem(), PlannerConfig()).status == "PLAN_FOUND"


def test_qwen_and_luna_share_one_strict_model_contract():
    requests = []

    def invoke(request):
        requests.append(request)
        return {"command_ids": ["down"], "milestone_shadow_id": None}

    qwen = QwenPlanningModel(invoke, model_name="qwen-test")
    luna = LunaPlanningModel(invoke, model_name="luna-test")
    assert qwen.propose({"problem": 1}).command_ids == ("down",)
    assert luna.propose({"problem": 1}).command_ids == ("down",)
    assert qwen.name == "qwen:qwen-test"
    assert luna.name == "luna:luna-test"
    assert requests[0]["response_format"] == requests[1]["response_format"]
    assert requests[0]["response_format"]["json_schema"]["strict"] is True


def test_model_planner_validates_a_qwen_proposal_through_generic_dynamics():
    problem = _problem()
    terminal = next(item.shadow_id for item in problem.milestones if item.terminal)
    requests = []

    def invoke(request):
        requests.append(request)
        return {
            "command_ids": ["down", "right", "right", "right", "up"],
            "milestone_shadow_id": terminal,
        }

    backend = ModelPlanner(QwenPlanningModel(invoke, model_name="fixture"))
    result = backend.search(problem, PlannerConfig())
    assert result.status == "PLAN_FOUND"
    assert result.factorization is not None
    assert result.factorization.terminal_reached is True
    assert result.factorization.steps[0].command_id == "down"
    assert result.expansions == 5
    assert requests[0]["messages"][1]["content"].find("supported_effects") >= 0


def test_model_planner_rejects_unsupported_and_over_budget_proposals():
    problem = _problem()
    evidence_before = tuple((item.command_id, item.support) for item in problem.effects)
    unsupported = ModelPlanner(QwenPlanningModel(
        lambda _request: {"command_ids": ["invented"], "milestone_shadow_id": None},
    )).search(problem, PlannerConfig())
    assert unsupported.status == "NO_PLAN"
    assert unsupported.reason == "model-proposed-unsupported-command"

    too_deep = ModelPlanner(LunaPlanningModel(
        lambda _request: {
            "command_ids": ["down", "right", "right"],
            "milestone_shadow_id": None,
        },
    )).search(problem, PlannerConfig(max_depth=2))
    assert too_deep.status == "NO_PLAN"
    assert too_deep.reason == "model-composition-exceeds-depth-budget"
    assert tuple((item.command_id, item.support) for item in problem.effects) == evidence_before


def test_r2_wiring_builds_qwen_and_luna_model_planners_without_network():
    model_config = {
        "endpoint": "http://model.invalid/v1", "request_timeout_seconds": 1,
        "model": "fixture-model", "reasoning_effort": "low",
    }
    poster = lambda _endpoint, _request, _timeout: {
        "transport_error": None,
        "parsed": {"command_ids": [], "milestone_shadow_id": None},
    }
    qwen = build_planner_backend(
        {"backend": "model-qwen"}, model_config, poster=poster,
    )
    luna = build_planner_backend(
        {"backend": "model-luna"}, model_config, poster=poster,
    )
    assert isinstance(qwen, ModelPlanner)
    assert isinstance(qwen.model, QwenPlanningModel)
    assert isinstance(luna, ModelPlanner)
    assert isinstance(luna.model, LunaPlanningModel)


def test_arcade_planner_options_default_to_deterministic_and_are_allowlisted():
    base = {"backend": "bounded-best-first-v0", "max_depth": 8}
    options = browser_options(base)
    assert options["active"] == "bounded-best-first-v0"
    assert [item["id"] for item in options["choices"]] == [
        "prospect-planner-v0", "bounded-best-first-v0",
        "fallback-only-v0", "model-selected",
    ]
    assert resolve_browser_selection(
        base, {"backend": "prospect-planner-v0"}, {"provider": "openai"}
    )["backend"] == "prospect-planner-v0"
    deterministic = resolve_browser_selection(
        base, {"backend": "bounded-best-first-v0"}, {"provider": "openai"}
    )
    assert deterministic == {**base, "enabled": True}
    assert resolve_browser_selection(
        base, {"backend": "model-selected"}, {"provider": "openai"}
    )["backend"] == "model-luna"
    assert resolve_browser_selection(
        base, {"backend": "model-selected"}, {"provider": "openai-compatible"}
    )["backend"] == "model-qwen"
    with pytest.raises(ValueError, match="unknown planner selection"):
        resolve_browser_selection(
            base, {"backend": "untrusted"}, {"provider": "openai"}
        )


def test_qwen_cli_invoker_uses_argv_and_extracts_only_structured_output(tmp_path):
    executable = tmp_path / "llama-cli"
    model = tmp_path / "model.gguf"
    executable.write_text("fixture", encoding="utf-8")
    model.write_text("fixture", encoding="utf-8")
    calls = []

    def runner(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(
            argv, 0,
            stdout='diagnostic\n{"command_ids":["right"],"milestone_shadow_id":null}\n',
            stderr="",
        )

    invoker = QwenCliInvoker(
        Path(executable), Path(model), grammar_constrained=True, runner=runner,
    )
    result = invoker({
        "messages": [{
            "role": "user",
            "content": json.dumps({
                "supported_effects": [{"command_id": "right"}],
                "milestone_shadows": [{"shadow_id": "done"}],
            }),
        }],
        "max_tokens": 64,
        "response_format": {"type": "json_schema"},
    })
    assert result == {"command_ids": ["right"], "milestone_shadow_id": None}
    assert calls[0][0][0] == str(executable)
    assert "--grammar" in calls[0][0]
    grammar = calls[0][0][calls[0][0].index("--grammar") + 1]
    assert "right" in grammar and "done" in grammar
    assert "shell" not in calls[0][1]
    assert calls[0][1]["capture_output"] is True


def test_hard_depth_frontier_and_expansion_budgets_terminate_search():
    config = PlannerConfig(max_depth=2, max_frontier=1, max_expansions=1)
    result = search(_problem(), config)
    assert result.expansions <= 1
    assert result.frontier_peak <= 1
    assert result.maximum_depth_reached <= 2
    assert result.status == "NO_PLAN"


def test_depth_n_certificate_authorizes_exactly_one_external_command():
    problem = _problem()
    result = search(problem)
    certificate = plan_certificate(problem, result)
    assert certificate["planned_depth"] > 1
    assert len(certificate["predicted_causal_composition"]) == certificate["planned_depth"]
    assert certificate["first_command"] == certificate["predicted_causal_composition"][0]["command"]
    assert certificate["external_action_authority"] == "first-command-only"
    assert certificate["continuation_authority"] == "none-replan-after-environment-settlement"


def test_every_environment_outcome_invalidates_cached_continuation_and_replans():
    certificate = {"protocol": "r2-control-factorization-v0", "planned_depth": 3}
    cases = (
        ({"adjudication": "refuted", "identity_status": "UNIQUE", "mechanism_status": "REFUTED"}, "prediction-mismatch"),
        ({"adjudication": "confirmed", "identity_status": "BROKEN", "mechanism_status": "CONFIRMED"}, "identity-ambiguity-or-break"),
        ({"adjudication": "confirmed", "identity_status": "UNIQUE", "mechanism_status": "REFUTED"}, "mechanism-applicability-failure"),
        ({"adjudication": "confirmed", "identity_status": "UNIQUE", "mechanism_status": "CONFIRMED", "unexpected_event": True}, "unexpected-successor-structure"),
    )
    for kwargs, reason in cases:
        settlement = settle_plan_certificate(certificate, **kwargs)
        assert settlement["first_step"] == "INVALIDATED"
        assert reason in settlement["invalidation_reasons"]
        assert settlement["continuation"] == "INVALIDATED_AFTER_OBSERVATION"
        assert settlement["replan_required"] is True

    confirmed = settle_plan_certificate(
        certificate,
        adjudication="confirmed", identity_status="UNIQUE", mechanism_status="CONFIRMED",
    )
    assert confirmed["first_step"] == "CONFIRMED"
    assert confirmed["milestone"] == "PENDING_REPLAN"
    assert confirmed["continuation"] == "INVALIDATED_AFTER_OBSERVATION"


def test_observer_plans_from_learned_effects_without_incrementing_support_then_settles_one_step():
    before = [[0, 0, 0, 0, 0, 0], [0, 2, 0, 0, 3, 0], [0, 0, 0, 0, 0, 0]]
    middle = [[0, 0, 0, 0, 0, 0], [0, 0, 2, 0, 3, 0], [0, 0, 0, 0, 0, 0]]
    after = [[0, 0, 0, 0, 0, 0], [0, 0, 0, 2, 3, 0], [0, 0, 0, 0, 0, 0]]
    goal = {
        "verb": "align", "schema_name": "Compatible entities converge",
        "goal_family": "alignment", "observable": "centroid_distance",
        "direction": "decrease", "terminal_condition": "minimum",
        "role_constraints": ["two distinct visible entities"],
    }
    backend = RecordingPlanner()
    observer = FrameSchemaObserver(planner_backend=backend)
    observer.fit_frame(before, turn=0)
    observer.rank_actions((1, 4), fallback_action=4, semantic_goal=goal)
    assert observer.settle_action(4, before, middle)["adjudication"] == "mechanism-observed"
    observer.fit_frame(middle, turn=1)
    support_before_search = deepcopy(observer.action_effects)
    planned = observer.rank_actions((1, 4), fallback_action=1, semantic_goal=goal)
    assert observer.action_effects == support_before_search
    assert planned["selected_action"] == 4
    assert planned["current_explanation"]["control_status"] == "PLAN_ELIGIBLE"
    assert planned["plan_certificate"]["planned_depth"] == 2
    assert planned["plan_certificate"]["external_action_authority"] == "first-command-only"
    assert planned["planner"]["backend"] == "recording-test-planner"
    assert backend.calls > 0

    settlement = observer.settle_action(4, middle, after)
    assert settlement["adjudication"] == "confirmed"
    assert settlement["plan_settlement"]["first_step"] == "CONFIRMED"
    assert settlement["plan_settlement"]["continuation"] == "INVALIDATED_AFTER_OBSERVATION"
    assert settlement["plan_settlement"]["replan_required"] is True
    assert observer.pending_prediction is None
    assert observer.fast_policy_state is not None
    assert "plan_certificate" not in observer.fast_policy_state["template"]
    observer.reset_episode()
    assert observer.planner_backend is backend


def test_settlement_projection_exposes_fresh_nonprogress_without_lag():
    before = [[0, 0, 0, 0, 0, 0], [0, 2, 0, 0, 3, 0], [0, 0, 0, 0, 0, 0]]
    moved = [[0, 0, 0, 0, 0, 0], [0, 0, 2, 0, 3, 0], [0, 0, 0, 0, 0, 0]]
    goal = {
        "verb": "align", "schema_name": "Compatible entities converge",
        "goal_family": "alignment", "observable": "centroid_distance",
        "direction": "decrease", "terminal_condition": "minimum",
        "role_constraints": ["two distinct visible entities"],
    }
    observer = FrameSchemaObserver()
    observer.fit_frame(before, turn=0)
    initial = observer.rank_actions((4,), fallback_action=4, semantic_goal=goal)
    observer.settle_action(4, before, moved)

    for turn in (1, 2):
        observer.fit_frame(moved, turn=turn)
        ranking = observer.rank_actions((4,), fallback_action=4, semantic_goal=goal)
        settlement = observer.settle_action(4, moved, moved)
        projection = observer.semantic_projection(
            ranking=ranking, settlement=settlement,
        )
        assert projection["active_explanation"]["nonprogress_observations"] == turn

    active = projection["active_explanation"]
    assert active["progress_confirmations"] == 0
    assert active["confirmations"] == observer.explanation_confirmations[active["schema_id"]]
    assert active["refutations"] == observer.explanation_refutations[active["schema_id"]]

    different_grounding = deepcopy(ranking)
    different_grounding["current_explanation"] = {
        **different_grounding["current_explanation"],
        "control_goal_key": "control-goal:different-grounding",
    }
    other = observer.semantic_projection(ranking=different_grounding)["active_explanation"]
    assert other["nonprogress_observations"] == 0

    assert initial["current_explanation"]["epistemic_evaluation"]["nonprogress_observations"] == 0


def test_settled_plan_edges_can_earn_fresh_fast_path_authority_without_route_reuse():
    authority = FastPathAuthority({"minimum_confirmations": 2})
    explanation = {
        "schema_id": "schema:generic",
        "control_status": "PLAN_ELIGIBLE",
        "goal": {"measure": "distance", "direction": "decrease", "terminal_class": "minimum"},
        "ports": {"situated_roles": {
            "actor": {"area": 1}, "target": {"area": 1},
        }},
        "epistemic_evaluation": {"mechanism_confidence": 1.0},
    }
    settlement = {
        "adjudication": "confirmed",
        "preferred_order": {"advanced": True},
        "protected_invariants": {"hold": True},
    }
    authority.consider(explanation, settlement)
    assert authority.active is False
    authority.consider(explanation, settlement)
    assert authority.active is True

    authority.revoke("test")
    authority.consider(
        explanation,
        {**settlement, "preferred_order": {"advanced": False}},
    )
    assert authority.active is False
