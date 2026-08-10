from __future__ import annotations

from dataclasses import dataclass, replace
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import hashlib
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
    for phrase in ("EXPLANATION · CURRENT", "TOP-3 NEXT ACTIONS", "SALIENT SCHEMAS", "METADATA", "QWEN SCRATCHPAD", "STEP ONE", "RESET", "ACTION ${turn}/${budget", "SPEED", "AGENT ARCADE"):
        assert phrase in page
    assert page.index("EXPLANATION · CURRENT") < page.index("TOP-3 NEXT ACTIONS") < page.index("SALIENT SCHEMAS") < page.index("METADATA")


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
    live.update(frame=[[1]], turn=4, decision={"x": 1}, scratchpad={"natural_language": "text"}, metadata={"run": 1})
    state = live.request_reset()
    assert state["status"] == "resetting"
    for field in ("frame", "decision", "scratchpad", "metadata", "current_explanation"):
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
        request_payload=lambda _turn, _qwen, **_kwargs: {"response_format": {"json_schema": {"schema": {"type": "object", "properties": {"protocol": {}}, "required": ["protocol"]}}}},
        _v14_visible=lambda _turn: ({"a": {}}, {"a"}),
        _forbidden=lambda value: "action" in json.dumps(value).lower(),
        stable_hash=lambda value: hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest(),
    )
    return qc


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


def test_qwen_scratchpad_rejects_action_language():
    scratchpad = load("scratchpad_forbidden") if (HERE / "scratchpad_forbidden.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    compiled = qc.compile_response({"parsed": {"protocol": "p", "request_id": "r", "natural_language_scratchpad": "Choose action 2", "workspace_write": {
        "summary": "Choose action 2", "objective_hypothesis": "", "open_questions": [], "cited_ids": ["a"]
    }}}, turn)
    assert compiled["valid_json_contract"] is True
    assert compiled["accepted"] == []
    assert compiled["rejected"][-1]["reason"] == "working-note-safety-or-budget"


def test_initial_working_hypothesis_is_an_unverified_explanation():
    scratchpad = load("scratchpad_initial") if (HERE / "scratchpad_initial.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    base = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    turn = replace(base, mode="initial-full", document={"protocol": "p"})
    compiled = qc.compile_response({"parsed": {"protocol": "p", "request_id": "r", "natural_language_scratchpad": "I am looking for a compact relation that could organize the visible figures.", "workspace_write": {
        "summary": "A visible relation may organize the figures.",
        "objective_hypothesis": "The relation is a candidate source of goal-relevant structure.",
        "open_questions": ["Does the relation persist?"],
        "cited_ids": ["a"],
    }}}, turn)
    explanation = next(item for item in compiled["accepted"] if item["kind"] == "explanation")
    assert explanation["payload"]["status"] == "unverified"
    assert explanation["support"] == 0


def test_qwen_turn_includes_r2_action_trace_in_scratchpad_context():
    scratchpad = load("scratchpad_trace") if (HERE / "scratchpad_trace.py").exists() else load("scratchpad")
    qc = fake_qc(); scratchpad.install(qc)
    scratchpad.record_r2_action_trace("Action 3 → f00 moved down 1")
    turn = qc.build_turn(SimpleNamespace(objects=[]), (), None)
    assert turn.document["scratchpad_context"]["r2_action_traces"] == ["Action 3 → f00 moved down 1"]
