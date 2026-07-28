from reflector.benchmark import run_one, run_validation


def test_diagnostic_tasks_are_deterministic_and_legal() -> None:
    first = run_validation(seed_count=2, seed_start=100)
    second = run_validation(seed_count=2, seed_start=100)
    assert first == second
    assert first["seed_start"] == 100
    assert first["criteria"]["all_actions_legal"] is True


def test_v2_diagnostic_tasks_are_deterministic_and_legal() -> None:
    first = run_validation(seed_count=2, seed_start=200, suite="v2")
    second = run_validation(seed_count=2, seed_start=200, suite="v2")
    assert first == second
    assert first["benchmark"] == "reflector_symbolic_diagnostics_v2"
    assert first["criteria"]["all_actions_legal"] is True


def test_v3_accommodation_is_deterministic_equal_history_and_causal() -> None:
    first = run_validation(seed_count=3, seed_start=300, suite="v3")
    second = run_validation(seed_count=3, seed_start=300, suite="v3")
    assert first == second
    assert first["benchmark"] == "reflector_symbolic_diagnostics_v3"
    assert first["criteria"]["all_actions_legal"] is True
    assert first["criteria"]["identical_training_histories"] is True
    assert (
        first["criteria"]["accommodation_improves_intervention_accuracy_ci"]
        is True
    )


def test_v4_transformations_are_deterministic_typed_and_causal() -> None:
    first = run_validation(seed_count=10, seed_start=400, suite="v4")
    second = run_validation(seed_count=10, seed_start=400, suite="v4")
    assert first == second
    assert first["benchmark"] == "reflector_symbolic_diagnostics_v4"
    assert first["criteria"]["all_actions_legal"] is True
    assert first["criteria"]["identical_training_histories"] is True
    assert first["criteria"]["all_primitives_have_inverses"] is True
    assert first["criteria"]["typed_comparison_laws_pass"] is True
    assert (
        first["criteria"]["transformations_improve_intervention_accuracy_ci"]
        is True
    )


def test_v5_modal_reasoning_is_deterministic_equal_history_and_causal() -> None:
    first = run_validation(seed_count=10, seed_start=500, suite="v5")
    second = run_validation(seed_count=10, seed_start=500, suite="v5")
    assert first == second
    assert first["benchmark"] == "reflector_symbolic_diagnostics_v5"
    assert first["criteria"]["all_actions_legal"] is True
    assert first["criteria"]["identical_training_histories"] is True
    assert first["criteria"]["impossibility_response_is_evidence_grounded"] is True
    assert first["criteria"]["modal_response_is_operative"] is True
    assert (
        first["criteria"]["modal_reasoning_improves_intervention_accuracy_ci"]
        is True
    )


def test_v6_comparison_transfer_is_deterministic_and_non_leaky() -> None:
    first = run_validation(seed_count=10, seed_start=600, suite="v6")
    second = run_validation(seed_count=10, seed_start=600, suite="v6")
    assert first == second
    assert first["benchmark"] == "reflector_symbolic_diagnostics_v6"
    assert first["criteria"]["independent_environment_oracle_passes"] is True
    assert first["criteria"]["all_actions_legal"] is True
    assert first["criteria"]["identical_forced_histories"] is True
    assert (
        first["criteria"]["withheld_effect_never_observed_before_intervention"]
        is True
    )
    assert first["criteria"]["negative_control_is_rejected"] is True
    assert (
        first["criteria"]["comparison_improves_intervention_accuracy_ci"]
        is True
    )


def test_v7_comparison_composition_is_deterministic_and_causal() -> None:
    first = run_validation(seed_count=10, seed_start=700, suite="v7")
    second = run_validation(seed_count=10, seed_start=700, suite="v7")
    assert first == second
    assert first["benchmark"] == "reflector_symbolic_diagnostics_v7"
    assert first["criteria"]["independent_environment_oracle_passes"] is True
    assert first["criteria"]["all_actions_legal"] is True
    assert first["criteria"]["identical_fixed_histories"] is True
    assert first["criteria"]["ablation_retains_direct_inference"] is True
    assert first["criteria"]["composed_paths_have_valid_endpoints"] is True
    assert (
        first["criteria"]["composition_improves_intervention_accuracy_ci"]
        is True
    )


def test_rare_color_mechanism_solves_rare_object_clicks() -> None:
    result = run_one("full", "rare_object_click", seed=7)
    assert result.won
    assert result.actions == result.oracle_actions


def test_context_table_is_a_meaningful_contextual_baseline() -> None:
    table = run_one("context_table", "contextual_control", seed=3)
    random = run_one("seeded_random", "contextual_control", seed=3)
    assert table.levels_completed >= random.levels_completed
    assert table.actions < random.actions


def test_procedure_abstraction_improves_sequence_transfer() -> None:
    full = run_one("full", "procedure_transfer", seed=5)
    flat = run_one("no_abstraction", "procedure_transfer", seed=5)
    assert full.won
    assert full.actions < flat.actions


def test_constructive_accommodation_improves_novel_interventions() -> None:
    constructive = run_one("constructive", "constructive_accommodation", seed=5)
    fixed = run_one("fixed_ontology", "constructive_accommodation", seed=5)
    assert constructive.training_actions == fixed.training_actions
    assert constructive.training_progress == fixed.training_progress
    assert constructive.structures_constructed >= 2
    assert constructive.target_condition_constructed
    assert fixed.structures_constructed == 0
    assert not fixed.target_condition_constructed
    assert (
        constructive.held_out_first_attempt_accuracy
        > fixed.held_out_first_attempt_accuracy
    )


def test_transformation_composition_reaches_oracle_action_count() -> None:
    transformed = run_one(
        "transformation", "transformation_composition", seed=9
    )
    flat = run_one("no_transformations", "transformation_composition", seed=9)
    assert transformed.training_actions == flat.training_actions
    assert transformed.training_progress == flat.training_progress
    assert transformed.won
    assert transformed.actions == transformed.oracle_actions
    assert transformed.transformations_constructed == 4
    assert transformed.inverse_transformations == 4
    assert transformed.comparison_laws_passed
    assert transformed.multi_step_plans >= 8
    assert not flat.won


def test_modal_reachability_reaches_oracle_beyond_short_plan_horizon() -> None:
    modal = run_one("modal", "modal_reachability", seed=17)
    ablated = run_one("no_modal", "modal_reachability", seed=17)
    assert modal.training_actions == ablated.training_actions
    assert modal.training_progress == ablated.training_progress
    assert modal.won
    assert modal.actions == modal.oracle_actions == 26
    assert modal.modal_response_evidence >= 1
    assert modal.modal_actions_used >= 4
    assert ablated.modal_actions_used == 0
