from __future__ import annotations

from dataclasses import dataclass, replace
import importlib.util
import inspect
from pathlib import Path
import sys
from types import SimpleNamespace
import pytest


HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(
        f"test_action_command_{name}", HERE / f"{name}.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


COMMAND = load("action_command")
ADAPTER = load("r2_1_adapter")


def region(binding_id: str, value: int, cells: tuple[tuple[int, int], ...]):
    min_y = min(y for y, _x in cells); min_x = min(x for _y, x in cells)
    shape = tuple(sorted((y - min_y, x - min_x) for y, x in cells))
    return {
        "binding_id": binding_id,
        "value": value,
        "area": len(cells),
        "cells": cells,
        "shape": shape,
        "outline": shape,
        "center2": (
            sum(y for y, _x in cells) * 2 / len(cells),
            sum(x for _y, x in cells) * 2 / len(cells),
        ),
    }


def test_click_candidates_are_deterministic_observed_cells_with_xy_transport_order():
    first = region("r:first", 2, ((1, 1), (1, 2), (2, 1)))
    # Its arithmetic centroid is not itself a cell.  The command must choose a
    # supported cell, not round into unsupported space.
    second = region("r:second", 3, ((4, 5), (4, 6)))
    observer = SimpleNamespace(
        last_regions=[first, second], frame_shape=(8, 8), last_digest="frame-a",
    )

    one = COMMAND.commands_for_frame((6,), observer)
    two = COMMAND.commands_for_frame((6,), observer)

    assert [item.document() for item in one] == [item.document() for item in two]
    assert len(one) == 2
    for command in one:
        y, x = command.payload_grounding["cell_rc"]
        source = first if command.payload_grounding["region_binding_id"] == "r:first" else second
        assert (y, x) in source["cells"]
        assert command.data == {"x": x, "y": y}


def test_exact_click_identity_and_initial_effect_scope_are_coordinate_scoped():
    left = region("r:left", 2, ((1, 1), (1, 2)))
    right = region("r:right", 2, ((5, 5), (5, 6)))
    observer = SimpleNamespace(
        last_regions=[left, right], frame_shape=(8, 8), last_digest="frame-b",
    )
    first, second = COMMAND.commands_for_frame((6,), observer)

    assert first.command_id != second.command_id
    assert first.data != second.data
    assert first.effect_scope_id != second.effect_scope_id


def test_supported_complex_legality_and_unsupported_schema_abstention():
    class UnsupportedAction:
        value = 9
        action_type = SimpleNamespace(model_fields={"color": object()})
        def is_complex(self): return True

    supported = SimpleNamespace(
        value=6,
        action_type=SimpleNamespace(model_fields={"game_id": object(), "x": object(), "y": object()}),
        is_complex=lambda: True,
    )
    environment = SimpleNamespace(action_space=(supported, UnsupportedAction()))
    observation = SimpleNamespace(available_actions=(6, 9))
    assert COMMAND.legal_action_ids(environment, observation) == (6,)


def test_click_effect_evidence_does_not_pollute_a_different_payload_scope():
    observer = ADAPTER.FrameSchemaObserver()
    actor = region("actor", 2, ((1, 1),))
    first = COMMAND.ActionCommand.create(
        6, {"x": 1, "y": 1}, effect_scope={"region": (2, 1, ((0, 0),))},
    )
    second = COMMAND.ActionCommand.create(
        6, {"x": 4, "y": 4}, effect_scope={"region": (3, 1, ((0, 0),))},
    )
    observer.action_effects[(first.effect_scope_id, observer._region_key(actor))][(0.0, 1.0)] += 1

    assert observer._effect_model(first, actor)["status"] == "SUPPORTED"
    assert observer._effect_model(second, actor)["status"] == "UNKNOWN"


@dataclass(frozen=True)
class Decision:
    action_id: int
    fallback_action_id: int
    reason: str
    template_hash: str | None = None
    residual_before: int | None = None
    predicted_residual_after: int | None = None
    prior_used: bool = False


@dataclass(frozen=True)
class Plan:
    mode: str = "fallback"
    action_id: int = 6
    fallback_action_id: int = 6
    predictions: tuple = ()
    selected_prediction_ids: tuple = ()
    probe_basis: str | None = None


class ClickBase:
    def __init__(self, **_kwargs):
        self.action_uses = {6: 0}
        self.last_plan = Plan()
    def _active_records(self): return []
    def plan(self, _legal, **_kwargs): return Decision(6, 6, "fallback"), self.last_plan
    def observe(self, _action, _before, _after): return {"prospective_adjudication": None}
    def report(self): return {}


class FallbackThreeBase:
    def __init__(self, **_kwargs):
        self.action_uses = {1: 0, 2: 0, 3: 0}
        self.last_plan = Plan(action_id=3, fallback_action_id=3)
    def _active_records(self): return []
    def plan(self, _legal, **_kwargs): return Decision(3, 3, "fallback"), self.last_plan
    def observe(self, action, _before, _after):
        self.action_uses[int(action)] += 1
        return {"prospective_adjudication": None}
    def report(self): return {}


def test_controller_commits_a_grounded_click_and_excludes_only_that_dead_coordinate():
    controller_module = load("controller")
    regions = [
        region("r:one", 2, ((1, 1),)),
        region("r:two", 3, ((4, 4),)),
    ]
    selected_inputs = []

    class Observer:
        last_regions = regions
        frame_shape = (8, 8)
        last_digest = "frame-c"
        def rank_actions(self, _legal, **kwargs):
            selected_inputs.append(kwargs)
            available = [
                item for item in kwargs["action_commands"]
                if kwargs["same_frame_no_change"].get(item.command_id, 0) == 0
            ]
            selected = available[0]
            return {
                "selected_action": 6,
                "selected_command": selected.document(),
                "top_actions": [], "explanations": [], "current_explanation": None,
                "control_override": False, "execution_authorized": True,
                "selection_rule": "test-command-scope",
            }
        def settle_action(self, _command, _before, _after):
            return {"adjudication": "untested-open-mechanism"}

    runtime = SimpleNamespace(
        schema_observer=Observer(), snapshot={},
        record_r2_action_trace=lambda _value: None,
        update=lambda **_value: None,
    )
    pc = SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(
        plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason,
    ))
    live = SimpleNamespace(ProspectiveWorkspaceController=ClickBase, PC=pc)
    controller = controller_module.controller_class(
        live, runtime, action_commands=COMMAND,
    )()

    first, _plan = controller.plan((6,), observation_digest="same", basis_revision=1)
    first_command = controller.selected_action_command(first)
    assert first_command.data in ({"x": 1, "y": 1}, {"x": 4, "y": 4})
    controller.observe(6, ((0,),), ((0,),))
    second, _plan = controller.plan((6,), observation_digest="same", basis_revision=2)
    second_command = controller.selected_action_command(second)

    assert first_command.command_id != second_command.command_id
    assert selected_inputs[-1]["same_frame_no_change"][first_command.command_id] == 1
    assert selected_inputs[-1]["same_frame_no_change"][second_command.command_id] == 0


def test_fast_path_override_replaces_fallback_command_before_settlement_attribution():
    controller_module = load("controller")
    observer = ADAPTER.FrameSchemaObserver()
    ranking = {
        "selected_action": 2,
        "selected_command": None,
        "top_actions": [{"rank": 1, "action": 2, "role": "authorized-policy"}],
        "explanations": [], "current_explanation": None,
        "execution_authorized": True,
        "control_proposal": {"mode": "FAST_PATH", "action": 2},
        "selection_rule": "authorized evaluator",
    }
    observer.rank_authorized_policy = lambda _legal, **_kwargs: ranking
    runtime = SimpleNamespace(
        schema_observer=observer, snapshot={},
        record_r2_action_trace=lambda _value: None,
        update=lambda **_value: None,
    )
    pc = SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(
        plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason,
    ))
    live = SimpleNamespace(ProspectiveWorkspaceController=FallbackThreeBase, PC=pc)
    controller = controller_module.controller_class(
        live, runtime, action_commands=COMMAND,
    )()
    controller.fast_path.license = {
        "status": "AUTHORIZED", "signature": "generic", "remaining": 2,
        "max_actions": 2, "max_failures": 0, "confirmations": 2, "confidence": 1.0,
    }

    decision, _plan = controller.plan((1, 2, 3), observation_digest="pivot", basis_revision=1)
    command = controller.selected_action_command(decision)

    assert decision.action_id == 2
    assert command.action_id == 2
    assert controller.last_command is command
    assert controller.last_contract["selected_command"] == command.document()

    learning = controller.observe(2, ((0,),), ((0,),))

    settlement = learning["one_action_settlement"]
    assert settlement["action"] == 2
    assert settlement["command"] == command.document()
    assert settlement["command"]["effect_scope_id"] == 2
    assert observer.action_uses[2] == 1
    assert observer.action_uses[3] == 0


def test_controller_refuses_to_fabricate_an_empty_complex_payload():
    controller_module = load("controller")
    observer = SimpleNamespace(
        last_regions=[], frame_shape=(8, 8), last_digest="empty",
        rank_actions=lambda _legal, **_kwargs: {
            "selected_action": 6, "selected_command": None, "top_actions": [],
            "explanations": [], "current_explanation": None,
            "control_override": True, "execution_authorized": True,
            "selection_rule": "no-grounded-command",
        },
    )
    runtime = SimpleNamespace(schema_observer=observer, snapshot={})
    class SimpleFallbackBase(FallbackThreeBase):
        def __init__(self, **_kwargs):
            super().__init__()
            self.action_uses[6] = 0
        def plan(self, _legal, **_kwargs):
            return Decision(1, 1, "fallback"), replace(
                self.last_plan, action_id=1, fallback_action_id=1,
            )
    live = SimpleNamespace(
        ProspectiveWorkspaceController=SimpleFallbackBase,
        PC=SimpleNamespace(fallback_plan=lambda plan, action_id, reason: replace(
            plan, action_id=action_id, fallback_action_id=action_id, probe_basis=reason,
        )),
    )
    controller = controller_module.controller_class(
        live, runtime, action_commands=COMMAND,
    )()
    decision, _plan = controller.plan((1, 6), observation_digest="empty", basis_revision=1)
    assert decision.action_id == 6
    assert controller.last_command is None
    assert controller.last_contract["selected_command"] is None
    with pytest.raises(RuntimeError, match="no evidence-grounded payload"):
        controller.selected_action_command(decision)


def test_inherited_boundary_transports_and_provenance_distinguish_exact_click_payloads():
    experiment = load("experiment")
    inherited = experiment.BASE
    calls = []

    class Environment:
        observation_space = SimpleNamespace(frame=[[[0]]])
        def step(self, action, *, data, reasoning):
            calls.append((action, dict(data), dict(reasoning)))
            return self.observation_space

    environment = Environment()
    successor = inherited.execute_action(
        environment, "fake", 6, {"x": 3, "y": 5}, "test-click",
    )

    assert successor is environment.observation_space
    action, transported, _reasoning = calls[0]
    assert action.value == 6
    assert action.action_data.x == 3 and action.action_data.y == 5
    assert transported == {"x": 3, "y": 5, "game_id": "fake"}
    assert inherited.opaque_intervention("ws", 6, {"x": 3, "y": 5}) != inherited.opaque_intervention(
        "ws", 6, {"x": 4, "y": 5},
    )

    source = inspect.getsource(inherited.run_episode)
    assert '"data": action_data' in source
    assert "execute_action(environment, game, decision.action_id, action_data" in source
    assert "opaque_intervention(workspace_id, decision.action_id, action_data)" in source
