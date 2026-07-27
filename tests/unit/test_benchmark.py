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
