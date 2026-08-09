from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("v116_test_experiment", HERE / "experiment.py")
EXPERIMENT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = EXPERIMENT
SPEC.loader.exec_module(EXPERIMENT)


def test_counterfactual_verification_event_is_atomic_and_replayable(tmp_path: Path) -> None:
    ledger = EXPERIMENT.BASE.LEDGER
    workspace_id = "counterfactual-ledger-test"
    ledger.append_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type="WorkspaceStarted",
        actor="coordinator",
        payload={"job_key": "fixture"},
    )
    branch = {"actual_exact_replay": True, "favorable": True}
    blob = ledger.put_blob(tmp_path, branch)
    event = ledger.append_event(
        tmp_path,
        workspace_id=workspace_id,
        event_type=EXPERIMENT.COUNTERFACTUAL_EVENT,
        actor="coordinator",
        payload={
            "decision_index": 7,
            "branch_blob": blob,
            "actual_exact_replay": True,
            "favorable": True,
        },
        event_id=f"counterfactual:7:{blob}",
    )
    assert event["seq"] == 1
    assert ledger.list_events(tmp_path)[1] == event
    assert ledger.read_blob(tmp_path, blob) == branch
    assert ledger.repair_head(tmp_path) == {
        "seq": 1,
        "event_hash": event["event_hash"],
    }
