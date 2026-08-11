"""Summarize R2.1 campaign traces without treating telemetry as competence."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
ARCADE = REPO / "experiments" / "explanation-guided-one-action-control-v0" / "arcade.py"


def load_arcade() -> Any:
    spec = importlib.util.spec_from_file_location("r21_campaign_arcade", ARCADE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {ARCADE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def analyze_episode(store: Any, episode: Path) -> dict[str, Any]:
    replay = store.replay(episode.name)
    counts: Counter[str] = Counter()
    claims: Counter[str] = Counter()
    measures: Counter[str] = Counter()
    identity: Counter[str] = Counter()
    mismatches = []
    repeated_no_change = []
    previous_frame_digest = None
    previous_action = None
    previous_no_change = False
    for turn in replay["timeline"]:
        decision = turn.get("executed_decision") or turn.get("decision") or {}
        settlement = turn.get("settlement") or {}
        explanation = decision.get("current_explanation") or {}
        top = (decision.get("top_actions") or [{}])[0]
        status = str(explanation.get("control_status") or top.get("eligibility") or "NONE")
        counts[status] += 1
        if explanation.get("claim"):
            claims[str(explanation["claim"])] += 1
        desired = explanation.get("desired_delta") or {}
        if desired.get("measure"):
            measures[str(desired["measure"])] += 1
        for role, assessment in (explanation.get("identity") or {}).items():
            if role != "control_eligible" and isinstance(assessment, dict):
                identity[str(assessment.get("status", "UNKNOWN"))] += 1
        action = settlement.get("action")
        selected = decision.get("selected_action")
        if action is not None and selected is not None and int(action) != int(selected):
            mismatches.append({"turn": turn["turn"], "executed": action, "contract": selected})
        frame_digest = digest(turn.get("frame"))
        if (
            settlement.get("observation_changed") is False
            and previous_no_change
            and previous_action == action
            and previous_frame_digest == frame_digest
        ):
            repeated_no_change.append({"turn": turn["turn"], "action": action})
        previous_action = action
        previous_frame_digest = frame_digest
        previous_no_change = settlement.get("observation_changed") is False
    return {
        **replay["metadata"],
        "episode": episode.name,
        "timeline_actions": len(replay["timeline"]) - 1,
        "control_status_counts": dict(counts),
        "claim_counts": dict(claims),
        "measure_counts": dict(measures),
        "identity_status_counts": dict(identity),
        "decision_execution_mismatches": mismatches,
        "consecutive_identical_no_change": repeated_no_change,
    }


def analyze(run_root: Path) -> dict[str, Any]:
    episodes = run_root / "episodes"
    arcade = load_arcade()
    store = arcade.ReplayStore(episodes)
    rows = []
    errors = []
    for episode in sorted(path for path in episodes.glob("*") if path.is_dir()):
        try:
            rows.append(analyze_episode(store, episode))
        except Exception as error:
            errors.append({"episode": episode.name, "error": f"{type(error).__name__}: {error}"})
    return {
        "protocol": "r2.1-kaggle-breadth-analysis-v0",
        "run_root": str(run_root),
        "episodes_analyzed": len(rows),
        "episodes_failed_to_analyze": errors,
        "level_clears": sum(int(row.get("levels_completed") or 0) for row in rows),
        "r2_progress_decisions": sum(
            int(row["control_status_counts"].get("PROGRESS_ELIGIBLE", 0)) for row in rows
        ),
        "r2_probe_decisions": sum(
            int(row["control_status_counts"].get("PROBE_ELIGIBLE", 0)) for row in rows
        ),
        "decision_execution_mismatches": sum(
            len(row["decision_execution_mismatches"]) for row in rows
        ),
        "consecutive_identical_no_change": sum(
            len(row["consecutive_identical_no_change"]) for row in rows
        ),
        "episodes": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = analyze(args.run_root.resolve())
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
