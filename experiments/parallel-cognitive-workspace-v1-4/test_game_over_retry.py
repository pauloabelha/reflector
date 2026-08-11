from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import types
from types import SimpleNamespace

import pytest


HERE = Path(__file__).resolve().parent


def load_experiment():
    if "PIL" not in sys.modules:
        pil = types.ModuleType("PIL")
        pil.Image = SimpleNamespace()
        sys.modules["PIL"] = pil
    spec = importlib.util.spec_from_file_location(
        "game_over_retry_under_test", HERE / "experiment.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = load_experiment()


def history(count: int, level: int = 0):
    return [
        {"before": {"levels_completed": level}, "after": {"levels_completed": level}}
        for _ in range(count)
    ]


def test_retry_never_authorizes_win_and_consumes_the_same_level_budget() -> None:
    assert not BASE.game_over_retry_allowed(
        "WIN", history(1), action_budget=48, per_level=True, enabled=True
    )
    assert BASE.game_over_retry_allowed(
        "GAME_OVER", history(47), action_budget=48, per_level=True, enabled=True
    )
    assert not BASE.game_over_retry_allowed(
        "GAME_OVER", history(48), action_budget=48, per_level=True, enabled=True
    )
    committed_reset = [*history(47), {
        "before": {"levels_completed": 0},
        "after": {"levels_completed": 0},
        "action_id": 0,
    }]
    assert BASE.current_level_action_count(
        committed_reset, 0, per_level=True
    ) == 48


def test_pending_retry_marker_survives_crash_resolution_and_conflicts_fail() -> None:
    before = {"levels_completed": 2}
    after = {"levels_completed": 2}
    pending = {"boundary_kind": BASE.GAME_OVER_RETRY_TRANSITION}
    assert BASE.transition_boundary_kind(
        pending, None, before, after, continue_across_levels=True
    ) == BASE.GAME_OVER_RETRY_TRANSITION
    committed = {"boundary_kind": BASE.GAME_OVER_RETRY_TRANSITION}
    assert BASE.transition_boundary_kind(
        pending, committed, before, after, continue_across_levels=True
    ) == BASE.GAME_OVER_RETRY_TRANSITION
    with pytest.raises(RuntimeError, match="boundary mismatch"):
        BASE.transition_boundary_kind(
            pending,
            {"boundary_kind": BASE.ORDINARY_TRANSITION},
            before,
            after,
            continue_across_levels=True,
        )


def test_retry_regrounds_without_calling_ordinary_action_learning() -> None:
    calls = []
    controller = SimpleNamespace(
        observe=lambda *_args: calls.append("ordinary-controller"),
        observe_game_over_retry=lambda *_args: calls.append("retry-controller") or {
            "retry_boundary": True
        },
    )
    cognition = SimpleNamespace(
        observe_transition=lambda *_args: calls.append("ordinary-cognition"),
        retry_level=lambda _grid: calls.append("retry-cognition"),
    )
    result = BASE.observe_game_over_retry(
        controller, cognition, ((9,),), ((1,),), None
    )
    assert result["retry_boundary"] is True
    assert calls == ["retry-controller", "retry-cognition"]


def test_retry_successor_invariants_fail_closed() -> None:
    playable = SimpleNamespace(state="NOT_FINISHED")
    BASE.assert_game_over_retry_successor(
        {"levels_completed": 3},
        {"levels_completed": 3, "full_reset": False},
        playable,
    )
    with pytest.raises(RuntimeError, match="full reset"):
        BASE.assert_game_over_retry_successor(
            {"levels_completed": 3},
            {"levels_completed": 0, "full_reset": True},
            playable,
        )
    with pytest.raises(RuntimeError, match="playable"):
        BASE.assert_game_over_retry_successor(
            {"levels_completed": 3},
            {"levels_completed": 3, "full_reset": False},
            SimpleNamespace(state="WIN"),
        )


def test_replay_executes_the_durable_reset_action_exactly(monkeypatch, tmp_path: Path) -> None:
    ledger = BASE.LEDGER
    ledger.initialize(tmp_path)
    before_record = {"digest": "before", "levels_completed": 1}
    after_record = {"digest": "after", "levels_completed": 1, "full_reset": False}
    before_blob = ledger.put_blob(tmp_path, {"record": before_record, "grid": [[9]]})
    after_blob = ledger.put_blob(tmp_path, {"record": after_record, "grid": [[1]]})
    decision_blob = ledger.put_blob(tmp_path, {"decision": {"action_id": 0}})
    pending = ledger.append_event(
        tmp_path, workspace_id="w", event_type="ActionPending", actor="arbiter",
        payload={
            "before_blob": before_blob, "before_digest": "before", "action_id": 0,
            "data": {}, "decision_blob": decision_blob,
            "boundary_kind": BASE.GAME_OVER_RETRY_TRANSITION,
        },
    )
    ledger.append_event(
        tmp_path, workspace_id="w", event_type="TransitionCommitted", actor="environment",
        payload={
            "pending_event_id": pending["event_id"], "before_blob": before_blob,
            "after_blob": after_blob, "before_digest": "before", "after_digest": "after",
            "action_id": 0, "data": {}, "levels_completed": 1,
            "boundary_kind": BASE.GAME_OVER_RETRY_TRANSITION,
        },
    )
    initial = SimpleNamespace(record=before_record)
    successor = SimpleNamespace(record=after_record)
    environment = SimpleNamespace(observation_space=initial)
    arcade = SimpleNamespace(close_scorecard=lambda: None)
    executed = []
    monkeypatch.setattr(BASE.BASE, "open_environment", lambda *_args: (arcade, environment))
    monkeypatch.setattr(BASE.BASE, "observation_record", lambda value: value.record)
    monkeypatch.setattr(
        BASE, "execute_action",
        lambda _environment, _game, action, data, reason: (
            executed.append((action, data, reason)) or successor
        ),
    )

    _arcade, _environment, replayed = BASE.open_replayed(
        tmp_path, "game", tmp_path / "env", tmp_path / "recording"
    )

    assert replayed is successor
    assert executed == [(0, {}, "checkpoint-replay")]
