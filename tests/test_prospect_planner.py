from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json

from reflector2.planner import (
    BoundedBestFirstPlanner,
    ControlProblem,
    GoalContractBasis,
    MilestoneShadow,
    PlannerConfig,
    ProspectPlanner,
    SupportedCausalEffect,
    plan_certificate,
)
from reflector2.r2.goal_contract import (
    compile_goal_contract,
    settle_goal_contract,
)
from reflector2.r2.r2_1_adapter import FrameSchemaObserver


def _effect(
    command_id: str,
    *,
    support: int = 3,
    confidence: float = 0.95,
) -> SupportedCausalEffect:
    return SupportedCausalEffect(
        command_id=command_id,
        command={
            "protocol": "generic-test-command",
            "command_id": command_id,
            "action_id": len(command_id),
        },
        actor_delta=(0.0, 0.0),
        target_delta=(0.0, 0.0),
        support=support,
        contradictions=0,
        confidence=confidence,
    )


def _problem(
    transitions,
    potentials,
    *,
    effects=None,
    initial="S",
    nuisance=None,
    scale=1.0,
    contract_status="OPEN",
    completion_nodes=None,
) -> ControlProblem:
    effects = tuple(effects or (_effect("A"), _effect("B"), _effect("C")))
    initial_state = {"node": initial, "nuisance": nuisance}

    def transition(state, effect):
        successor = transitions.get((state["node"], effect.command_id))
        return None if successor is None else {**state, "node": successor}

    def measure(state, observable):
        if observable == "completion":
            return 1.0 if state["node"] in set(completion_nodes or ()) else 0.0
        assert observable == "residual"
        return float(potentials[state["node"]]) * scale

    local_progress_only = MilestoneShadow(
        shadow_id="local-progress",
        kind="ResidualDecreased",
        observable="residual",
        relation="decrease",
        target=None,
        terminal=False,
    )
    contract = GoalContractBasis(
        contract_id="goal-contract:generic",
        environment_terminal="level_completion",
        contributor_verb="fit",
        contributor_observable="completion" if completion_nodes is not None else "residual",
        contributor_relation="reached",
        contributor_target=1.0 if completion_nodes is not None else 0.0,
        status=contract_status,
        provenance=("synthetic-contract",),
    )
    return ControlProblem(
        explanation_id="explanation:generic",
        verb="fit",
        initial_state=initial_state,
        active_observable="residual",
        preferred_direction="decrease",
        initial_value=measure(initial_state, "residual"),
        effects=effects,
        milestones=(local_progress_only,),
        transition=transition,
        measure=measure,
        invariants_hold=lambda state: state["node"] != "BROKEN",
        state_key=lambda state: str(state["node"]),
        protected_invariants=("actor-identity", "target-identity", "topology"),
        goal_contract=contract,
    )


def test_goal_contract_model_proposal_is_open_and_only_environment_settles_it():
    proposal = {
        "environment_terminal": "level_completion",
        "contributor_relation": "reached",
        "countercondition": "verb-terminal-without-environment-terminal",
    }
    contract = compile_goal_contract(
        proposal,
        contributor_verb="fit",
        contributor_observable="fit_residual",
        contributor_target=0.0,
        proposal_citations=("semantic-note:1",),
    )
    assert contract.status == "OPEN"
    assert contract.evidence == ()
    assert "semantic-note:1" in contract.provenance

    supported = settle_goal_contract(
        contract,
        verb_terminal_observed=True,
        environment_terminal_observed=True,
        evidence_ref="environment-transition:7",
    )
    assert supported.status == "SUPPORTED"
    assert supported.evidence == ("environment-transition:7",)

    refuted = settle_goal_contract(
        contract,
        verb_terminal_observed=True,
        environment_terminal_observed=False,
        evidence_ref="environment-transition:8",
    )
    assert refuted.status == "REFUTED"

    unrelated = settle_goal_contract(
        contract,
        verb_terminal_observed=False,
        environment_terminal_observed=True,
        evidence_ref="unrelated-level-success:9",
    )
    assert unrelated == contract


def test_temporary_regression_requires_and_reports_terminal_factorization():
    problem = _problem(
        {
            ("S", "A"): "LOCAL_BETTER_DEAD_END",
            ("S", "B"): "LOCAL_WORSE",
            ("LOCAL_WORSE", "C"): "TERMINAL",
        },
        {"S": 3, "LOCAL_BETTER_DEAD_END": 1, "LOCAL_WORSE": 4, "TERMINAL": 2},
        completion_nodes={"TERMINAL"},
    )
    config = PlannerConfig(max_depth=4, max_expansions=32)
    ordinary = BoundedBestFirstPlanner().search(problem, config)
    assert ordinary.factorization.steps[0].command_id == "A"

    before_support = tuple((item.command_id, item.support) for item in problem.effects)
    result = ProspectPlanner().search(problem, config)
    assert tuple((item.command_id, item.support) for item in problem.effects) == before_support
    assert result.factorization.steps[0].command_id == "B"
    assert result.factorization.steps[0].potential_after > problem.initial_value
    assert result.prospect_improvement_kind == "enables-terminal-factorization"
    assert all(step.epistemic_status == "hypothetical" for step in result.factorization.steps)

    certificate = plan_certificate(problem, result)
    assert certificate["protocol"] == "r2-goal-prospect-certificate-v2"
    assert certificate["immediate_orientation"] == "adverse"
    assert certificate["justification"] == "enables-terminal-factorization"
    assert certificate["successor_goal_prospect"]["terminal_status"] == "reachable"
    assert certificate["authority"] == "FIRST_COMMAND_ONLY"
    assert certificate["external_action_authority"] == "first-command-only"
    assert len(certificate["factorization"]) == 2


def test_false_regression_is_not_selected_without_better_terminal_factorization():
    problem = _problem(
        {
            ("S", "A"): "TERMINAL",
            ("S", "B"): "LOCAL_WORSE_DEAD_END",
        },
        {"S": 3, "TERMINAL": 0, "LOCAL_WORSE_DEAD_END": 4},
    )
    result = ProspectPlanner().search(problem, PlannerConfig(max_depth=4))
    assert result.factorization.steps[0].command_id == "A"
    assert result.successor_goal_prospect.expected_local_verb_orientation == "preferred"


def test_weak_short_route_does_not_dominate_long_strong_route():
    effects = (
        _effect("weak_1", support=1, confidence=0.61),
        _effect("weak_2", support=1, confidence=0.61),
        _effect("strong_1", support=4, confidence=0.96),
        _effect("strong_2", support=4, confidence=0.96),
        _effect("strong_3", support=4, confidence=0.96),
    )
    problem = _problem(
        {
            ("S", "weak_1"): "W",
            ("W", "weak_2"): "TERMINAL",
            ("S", "strong_1"): "X",
            ("X", "strong_2"): "Y",
            ("Y", "strong_3"): "TERMINAL",
        },
        {"S": 5, "W": 3, "X": 6, "Y": 2, "TERMINAL": 0},
        effects=effects,
    )
    result = ProspectPlanner().search(
        problem,
        PlannerConfig(max_depth=5, minimum_effect_confidence=0.6),
    )
    assert result.factorization.steps[0].command_id == "strong_1"
    assert result.current_goal_prospect.minimum_edge_support == 4
    assert result.current_goal_prospect.minimum_edge_confidence == 0.96


def test_no_contract_preserves_existing_bounded_search_behavior():
    problem = _problem(
        {("S", "A"): "BETTER"},
        {"S": 3, "BETTER": 1},
    )
    disabled = replace(problem, goal_contract=None)
    config = PlannerConfig(max_depth=2)
    assert ProspectPlanner().search(disabled, config).factorization == (
        BoundedBestFirstPlanner().search(disabled, config).factorization
    )


def test_prospect_certificate_is_byte_deterministic_and_budgets_are_hard():
    problem = _problem(
        {
            ("S", "B"): "M",
            ("M", "C"): "TERMINAL",
        },
        {"S": 2, "M": 3, "TERMINAL": 0},
    )
    config = PlannerConfig(
        max_depth=4,
        max_frontier=2,
        max_expansions=8,
        max_goal_factorizations=2,
    )
    first = ProspectPlanner().search(problem, config)
    second = ProspectPlanner().search(problem, config)
    assert json.dumps(plan_certificate(problem, first), sort_keys=True) == json.dumps(
        plan_certificate(problem, second), sort_keys=True,
    )
    assert first.expansions <= config.max_expansions
    assert first.frontier_peak <= config.max_frontier
    assert first.maximum_depth_reached <= config.max_depth
    assert first.current_goal_prospect.terminal_reaching_factorizations <= 2


def test_declared_nuisance_translation_recolor_and_scaling_preserve_behavior():
    transitions = {
        ("S", "B"): "M",
        ("M", "C"): "TERMINAL",
    }
    potentials = {"S": 2, "M": 3, "TERMINAL": 0}
    base = _problem(transitions, potentials)
    translated_recolored = _problem(
        transitions,
        potentials,
        nuisance={"translation": [12, -7], "palette": [9, 4]},
    )
    scaled = _problem(transitions, potentials, scale=3.0)
    commands = []
    for problem in (base, translated_recolored, scaled):
        result = ProspectPlanner().search(problem, PlannerConfig(max_depth=4))
        commands.append(tuple(step.command_id for step in result.factorization.steps))
    assert commands == [("B", "C"), ("B", "C"), ("B", "C")]


def test_r2_adapter_passes_open_contract_to_prospect_backend_without_support():
    before = [[0, 0, 0, 0, 0, 0], [0, 2, 0, 0, 3, 0], [0, 0, 0, 0, 0, 0]]
    middle = [[0, 0, 0, 0, 0, 0], [0, 0, 2, 0, 3, 0], [0, 0, 0, 0, 0, 0]]
    goal = {
        "verb": "align",
        "schema_name": "Compatible entities converge",
        "goal_family": "alignment",
        "observable": "centroid_distance",
        "direction": "decrease",
        "terminal_condition": "minimum",
        "role_constraints": ["two distinct visible entities"],
        "goal_contract": {
            "environment_terminal": "level_completion",
            "contributor_relation": "reached",
            "contributor_target": 0.0,
            "countercondition": "verb-terminal-without-environment-terminal",
        },
    }
    observer = FrameSchemaObserver(planner_backend=ProspectPlanner())
    observer.fit_frame(before, turn=0)
    observer.rank_actions((1, 4), fallback_action=4, semantic_goal=goal)
    observer.settle_action(4, before, middle)
    observer.fit_frame(middle, turn=1)
    support_before = deepcopy(observer.action_effects)
    ranking = observer.rank_actions((1, 4), fallback_action=1, semantic_goal=goal)
    assert observer.action_effects == support_before
    assert ranking["planner"]["prospect_planner_invoked"] is True
    assert ranking["planner"]["goal_contract_status"] == "OPEN"
    assert ranking["plan_certificate"]["protocol"] == "r2-goal-prospect-certificate-v2"
    assert next(iter(observer.goal_contracts.values())).evidence == ()
