from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


HERE = Path(__file__).resolve().parent


def load_module():
    path = HERE / "experiment.py"
    spec = importlib.util.spec_from_file_location("test_workspace_v120", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class Required(Exception):
    def __init__(self, budget: int, required: int):
        self.budget = budget
        self.required = required


def test_exact_retry_admits_no_optional_fill():
    module = load_module()
    calls = []

    def frontier(*, budget):
        calls.append(budget)
        if budget < 10841:
            raise Required(budget, 10841)
        return {"used_tokens": 10841, "objects": list(range(28))}

    wrapped = module.POLICY._retry_exact_required(
        frontier, Required, budget_key="budget", ceiling=14000
    )
    result = wrapped(budget=6400)
    assert calls == [6400, 10841]
    assert result["used_tokens"] == 10841


def test_hard_ceiling_fails_without_oversized_retry():
    module = load_module()
    calls = []

    def frontier(*, budget):
        calls.append(budget)
        raise Required(budget, 14001)

    wrapped = module.POLICY._retry_exact_required(
        frontier, Required, budget_key="budget", ceiling=14000
    )
    with pytest.raises(module.POLICY.MandatoryFrontierCeilingError):
        wrapped(budget=6400)
    assert calls == [6400]


@pytest.mark.parametrize(
    ("version", "required", "binding_count", "object_count"),
    (("v1-18", 9843, 9, 28), ("v1-19", 10841, 12, 31)),
)
def test_preserved_fresh_failures_fit_generic_ceiling(
    version, required, binding_count, object_count
):
    module = load_module()
    root = (
        HERE.parent
        / f"parallel-cognitive-workspace-{version}"
        / "artifacts/workspaces/generic_prospective--wa30--shared_live_qwen"
    )
    if not root.exists():
        return
    state, _events = module.BASE.rebuild_graph(root)
    orientation_objects = [
        item for item in state.objects if item.kind == "qwen_orientation"
    ]
    orientation = max(
        orientation_objects, key=lambda item: (item.created_revision, item.object_id)
    ).payload
    cut = module.BASE.QC.sparse_cut(
        state,
        token_budget=required,
        focus_ids=tuple(orientation["focus_ids"]),
        expansion_ids=tuple(orientation["expansion_ids"]),
    )
    assert cut["dependency_closed"] is True
    assert cut["used_tokens"] == required
    assert cut["used_tokens"] <= 14000
    assert len(cut["objects"]) == object_count
    assert sum(item["kind"] == "binding" for item in cut["objects"]) == binding_count
    assert sum(item["kind"] == "structured_criticism" for item in cut["objects"]) == 1
    assert sum(item["kind"] == "qwen_derivation" for item in cut["objects"]) == 1
    assert sum(item["kind"] == "relation_set" for item in cut["objects"]) == 2


def test_runtime_overlay_changes_only_two_tier_capacity_policy():
    module = load_module()
    current = module.load_config()
    prior = module.V119_MODULE.load_config()
    assert current["profiles"]["generic_prospective"] == {
        "attention_half_life_actions": 12,
        "frontier_root_limit": 24,
        "frontier_token_budget": 6400,
        "mandatory_frontier_ceiling": 14000,
        "proposal_attention_boost": 1.0,
    }
    assert current["qwen"] == {
        **prior["qwen"],
        "exact_context_admission_probe": True,
        "context_safety_margin_tokens": 512,
    }
    normalized = dict(current)
    normalized.update(
        experiment=prior["experiment"],
        protocol=prior["protocol"],
        workspace_protocol=prior["workspace_protocol"],
    )
    normalized["profiles"] = prior["profiles"]
    normalized["qwen"] = prior["qwen"]
    assert normalized == prior


def test_exact_context_admission_precedes_real_request():
    module = load_module()
    calls = []

    def poster(_endpoint, request, _timeout):
        calls.append(dict(request))
        if request["max_tokens"] == 1:
            return {
                "raw_body": '{"usage":{"prompt_tokens":1000}}',
                "transport_error": "discarded-output-is-not-json",
            }
        return {"raw_body": "{}", "transport_error": None}

    class FakeQueue:
        def __init__(self, endpoint, *, timeout=600.0, poster=None):
            self.endpoint = endpoint
            self.timeout = timeout
            self.poster = poster

    class Worker:
        post_request = staticmethod(poster)

    class Cognition:
        ResidentServerQueue = FakeQueue
        V0_WORKER = Worker
        CognitionError = module.BASE.QC.CognitionError
        admit_request_context = staticmethod(module.BASE.QC.admit_request_context)
        stable_hash = staticmethod(module.BASE.QC.stable_hash)

    module.POLICY.install_exact_context_admission(
        Cognition,
        {"context_window_tokens": 24576, "max_tokens": 3072},
        safety_margin_tokens=512,
    )
    queue = Cognition.ResidentServerQueue("local", timeout=1)
    response = queue.poster("local", {"max_tokens": 3072, "messages": []}, 1)
    assert [item["max_tokens"] for item in calls] == [1, 3072]
    assert response["context_admission"]["prompt_tokens"] == 1000
    assert response["context_admission"]["semantic_output_discarded"] is True
