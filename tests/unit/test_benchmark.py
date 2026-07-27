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
