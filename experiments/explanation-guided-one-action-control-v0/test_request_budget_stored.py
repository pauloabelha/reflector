"""Differential context admission against the causal G50T overflow trace."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import re
import sys

import pytest


HERE = Path(__file__).resolve().parent
TRACE = Path(
    "/home/pauloabelha/reflector2/experiments/r2-1-kaggle-breadth-v0/"
    "artifacts/run-20260811-final-serial-8beebf8/episodes/"
    "pass-01--g50t--level-01"
)


def load_experiment():
    spec = importlib.util.spec_from_file_location("stored_budget_leaf", HERE / "experiment.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.install()
    return module


@pytest.mark.skipif(not TRACE.exists(), reason="stored G50T overflow trace unavailable")
def test_stored_overflows_fit_with_reserve_and_exact_required_coverage() -> None:
    module = load_experiment()
    base = module.BASE
    cognition = base.QC
    scratchpad = module.SCRATCHPAD
    workspace = next((TRACE / "workspaces").iterdir())
    ledger_events = base.LEDGER.list_events(workspace)
    graph_events = [
        base.EG.event_from_document(item)
        for item in base.LEDGER.graph_event_documents(ledger_events, workspace)
    ]
    config = json.loads((TRACE / "manifest.json").read_text())["config"]
    config["qwen"].update(json.loads((HERE / "config.json").read_text())["qwen"])

    queued = {
        int(item["payload"]["source_action_count"]): item
        for item in ledger_events
        if item["event_type"] == "QwenTaskQueued"
    }
    completed = {
        item["payload"]["task_id"]: item
        for item in ledger_events
        if item["event_type"] == "QwenTaskCompleted"
    }
    for action_count in (6, 11, 15, 18):
        event = queued[action_count]
        payload = event["payload"]
        old_turn = base.LEDGER.read_blob(workspace, payload["turn_blob"])
        old_request = base.LEDGER.read_blob(workspace, payload["request_blob"])
        response = base.LEDGER.read_blob(
            workspace, completed[payload["task_id"]]["payload"]["response_blob"]
        )
        actual = re.search(r'"n_prompt_tokens":(\d+)', response["raw_body"])
        assert actual is not None
        assert cognition.conservative_request_prompt_tokens(
            old_request, config["qwen"]
        ) >= int(actual.group(1))
        through = [item for item in graph_events if item.seq <= payload["basis_revision"]]
        state = base.EG.replay(through)
        document = old_turn["document"]
        context = document["scratchpad_context"]
        scratchpad._R2_SEMANTIC_PROJECTION = copy.deepcopy(
            context.get("r2_semantic_projection")
        )
        scratchpad._R2_TRANSITION_OBSERVATION = copy.deepcopy(
            context.get("r2_transition_observation")
        )
        scratchpad._R2_ACTION_TRACES[:] = list(context.get("r2_action_traces") or ())
        orientation = cognition.Orientation(
            workspace_id=event["workspace_id"],
            initialized=True,
            cursor_revision=int(document["from_cursor"]["revision"]),
            cursor_hash=document["from_cursor"]["head_hash"],
        )
        visual = []
        content = old_request["messages"][0]["content"]
        for index, part in enumerate(content):
            if part.get("type") == "image_url":
                visual.append({
                    "label": content[index - 1]["text"],
                    "data_url": part["image_url"]["url"],
                })

        def candidate(token_budget: int):
            turn = cognition.build_turn(
                state,
                through,
                orientation,
                request_id=old_turn["request_id"],
                token_budget=token_budget,
                max_deltas=10_000,
                compact_ids=True,
            )
            request = cognition.request_payload(
                turn, config["qwen"], visual_evidence=visual
            )
            admission = cognition.admit_request_context(
                request,
                config["qwen"],
                prompt_token_counter=lambda value: cognition.conservative_request_prompt_tokens(
                    value, config["qwen"]
                ),
            )
            return turn, request, admission

        turn, request, admission, _budget, rebuilds = base.admitted_qwen_request(
            candidate,
            maximum_budget=6400,
            qwen=config["qwen"],
        )
        assert rebuilds == 1
        assert admission.occupied_tokens <= admission.context_window_tokens == 16_384
        assert admission.reserved_output_tokens >= 2_048
        assert (
            turn.document["sparse_cut"].get("mandatory_live_bindings")
            == document["sparse_cut"].get("mandatory_live_bindings")
        )
        assert (
            turn.document["sparse_cut"].get("pinned_causal_units")
            == document["sparse_cut"].get("pinned_causal_units")
        )
        assert turn.document.get("causal_revision_packet") == document.get(
            "causal_revision_packet"
        )
        evidence_ref = context["r2_transition_observation"]["evidence_ref"]
        assert evidence_ref in json.dumps(request, sort_keys=True)
