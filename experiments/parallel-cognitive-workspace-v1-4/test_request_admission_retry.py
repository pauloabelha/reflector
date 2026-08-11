from __future__ import annotations

import importlib.util
import importlib
from pathlib import Path
import sys
import types
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent


def load_experiment():
    if "PIL" not in sys.modules:
        try:
            importlib.import_module("PIL")
        except ImportError:
            pil = types.ModuleType("PIL")
            pil.Image = SimpleNamespace()
            sys.modules["PIL"] = pil
    spec = importlib.util.spec_from_file_location(
        "request_admission_retry_under_test", HERE / "experiment.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_experiment()


def admission_error(*, excess: int, frontier_used_tokens: int | None = None):
    window = 16_384
    occupied = window + excess
    report = BASE.QC.ContextAdmission(
        prompt_tokens=occupied - 2_048,
        reserved_output_tokens=2_048,
        occupied_tokens=occupied,
        context_window_tokens=window,
        headroom_tokens=-excess,
        occupancy_fraction=occupied / window,
    )
    error = BASE.QC.ContextAdmissionError(report)
    if frontier_used_tokens is not None:
        error.frontier_used_tokens = frontier_used_tokens
    return error


def test_guided_misses_fall_back_to_exact_mandatory_closure() -> None:
    calls = []

    def candidate(budget: int):
        calls.append(budget)
        if budget == 1:
            raise BASE.EG.FrontierBudgetError(budget=budget, required=300)
        if budget > 300:
            raise admission_error(excess=100 if len(calls) == 1 else 19)
        return "turn", {"max_tokens": 2_048}, "admitted"

    result = BASE.admitted_qwen_request(
        candidate,
        maximum_budget=6_400,
        qwen={"max_context_budget_rebuilds": 2},
    )

    assert calls == [6_400, 6_325, 6_310, 1, 300]
    assert result == ("turn", {"max_tokens": 2_048}, "admitted", 300, 4)


def test_exact_plateau_breakpoint_preserves_the_largest_cheaper_frontier() -> None:
    calls = []

    def candidate(budget: int):
        calls.append(budget)
        if budget >= 3_655:
            raise admission_error(excess=19, frontier_used_tokens=3_655)
        return "useful-turn", {"max_tokens": 2_048}, "admitted"

    result = BASE.admitted_qwen_request(
        candidate,
        maximum_budget=6_400,
        qwen={"max_context_budget_rebuilds": 2},
    )

    assert calls == [6_400, 3_654]
    assert result == (
        "useful-turn", {"max_tokens": 2_048}, "admitted", 3_654, 1
    )


def test_mandatory_closure_still_fails_exact_admission_pre_transport() -> None:
    calls = []

    def candidate(budget: int):
        calls.append(budget)
        if budget == 1:
            raise BASE.EG.FrontierBudgetError(budget=budget, required=300)
        raise admission_error(excess=19)

    with pytest.raises(BASE.QC.ContextAdmissionError, match="exceeds context window"):
        BASE.admitted_qwen_request(
            candidate,
            maximum_budget=6_400,
            qwen={"max_context_budget_rebuilds": 0},
        )

    assert calls == [6_400, 1, 300]


def test_mandatory_closure_above_maximum_is_not_hidden() -> None:
    calls = []

    def candidate(budget: int):
        calls.append(budget)
        if budget == 1:
            raise BASE.EG.FrontierBudgetError(budget=budget, required=6_401)
        raise admission_error(excess=19)

    with pytest.raises(BASE.EG.FrontierBudgetError, match="mandatory closure cost 6401"):
        BASE.admitted_qwen_request(
            candidate,
            maximum_budget=6_400,
            qwen={"max_context_budget_rebuilds": 0},
        )

    assert calls == [6_400, 1]
