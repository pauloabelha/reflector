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


FAILURE_LAYERS = (
    "execution_coverage",
    "perception_animation_evidence",
    "identity",
    "mechanics",
    "telos_semantic_stagnation",
    "exploration_no_change",
    "planning",
    "runtime_deadline",
    "success",
)


def _layer(
    assessment: str, evidence: list[dict[str, Any]] | None = None,
    unknowns: list[str] | None = None,
) -> dict[str, Any]:
    """Render one evidence-bounded layer without supplying a hidden cause."""
    return {
        "assessment": assessment,
        "evidence": list(evidence or ()),
        "unknowns": list(unknowns or ()),
    }


def classify_trace(
    timeline: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *, outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stratify observable trace limitations; never infer a game's rules.

    The layers are deliberately non-exclusive.  For example, a timed-out run
    can contain supported identity evidence and repeated no-change evidence.
    Missing telemetry remains explicit under ``unknowns``.
    """
    outcome = dict(outcome or {})
    action_turns = 0
    frame_observations = 0
    animation_observations = 0
    changed = 0
    unchanged = 0
    repeated_no_change = 0
    mismatches = 0
    progress_eligible = 0
    probe_eligible = 0
    grounded_semantic_signatures: list[tuple[str, str, str, str]] = []
    semantic_note_signatures: list[str] = []
    prior_semantic_note_token: tuple[Any, str] | None = None
    identity_statuses: Counter[str] = Counter()
    mechanism_statuses: Counter[str] = Counter()
    prior_frame_digest = None
    prior_action = None
    prior_no_change = False
    traced_levels_completed = 0

    for turn in timeline:
        if turn.get("frame") is not None:
            frame_observations += 1
        for key in ("animation_frames", "ordered_frames", "frame_stack"):
            frames = turn.get(key)
            if isinstance(frames, (list, tuple)) and len(frames) > 1:
                animation_observations += 1
        settlement = turn.get("settlement") or {}
        decision = turn.get("executed_decision") or turn.get("decision") or {}
        r2 = decision.get("r2_1_explanation_control") or {}
        explanation = r2.get("current_explanation") or decision.get("current_explanation") or {}
        if settlement.get("action") is not None:
            action_turns += 1
        observation_changed = settlement.get("observation_changed")
        if observation_changed is True:
            changed += 1
        elif observation_changed is False:
            unchanged += 1
        action = settlement.get("action")
        frame_digest = digest(turn.get("frame"))
        if (
            observation_changed is False and prior_no_change
            and action == prior_action and frame_digest == prior_frame_digest
        ):
            repeated_no_change += 1
        prior_no_change = observation_changed is False
        prior_action = action
        prior_frame_digest = frame_digest
        selected = decision.get("selected_action")
        if action is not None and selected is not None and int(action) != int(selected):
            mismatches += 1
        status = str(explanation.get("control_status") or "")
        if status == "PROGRESS_ELIGIBLE":
            progress_eligible += 1
        elif status == "PROBE_ELIGIBLE":
            probe_eligible += 1
        signature = (
            str(explanation.get("claim") or ""),
            str(explanation.get("verb") or ""),
            str((explanation.get("desired_delta") or {}).get("measure") or ""),
            str((explanation.get("desired_delta") or {}).get("direction") or ""),
        )
        if any(signature):
            grounded_semantic_signatures.append(signature)
        scratchpad = turn.get("scratchpad") or {}
        if isinstance(scratchpad, dict) and scratchpad.get("goal_proposals"):
            note_signature = json.dumps(
                scratchpad.get("goal_proposals"), sort_keys=True,
                separators=(",", ":"), ensure_ascii=True,
            )
            note_token = (scratchpad.get("basis_revision"), note_signature)
            if note_token != prior_semantic_note_token:
                semantic_note_signatures.append(note_signature)
                prior_semantic_note_token = note_token
        for role, assessment in (explanation.get("identity") or {}).items():
            if role != "control_eligible" and isinstance(assessment, dict):
                identity_statuses[str(assessment.get("status", "UNKNOWN"))] += 1
        for assessment in r2.get("identity_assessments") or ():
            if isinstance(assessment, dict):
                identity_statuses[str(assessment.get("status", "UNKNOWN"))] += 1
        mechanism = explanation.get("mechanism") or {}
        for role in ("actor", "target"):
            model = mechanism.get(role)
            if isinstance(model, dict):
                mechanism_statuses[str(model.get("status", "UNKNOWN"))] += 1
        traced_levels_completed = max(
            traced_levels_completed,
            int(turn.get("levels_completed") or settlement.get("levels_completed") or 0),
        )

    recorded_actions = outcome.get("actions")
    actions = int(recorded_actions) if recorded_actions is not None else action_turns
    stop_reason = str(outcome.get("stop_reason") or "")
    outcome_status = str(outcome.get("status") or "")
    levels_completed = max(traced_levels_completed, int(outcome.get("levels_completed") or 0))

    if actions > 0:
        execution = _layer("support-observed", [{"actions_executed": actions}])
    elif stop_reason == "complex-only-epistemic-abstention":
        execution = _layer("limitation-observed", [
            {"actions_executed": 0}, {"stop_reason": stop_reason},
        ], ["the trace does not establish which unexecuted action would be useful"])
    elif outcome_status in {"complete", "error", "timeout"} or timeline:
        execution = _layer("limitation-observed", [{"actions_executed": 0}], [
            "the trace does not attribute zero execution to a game rule or controller layer",
        ])
    else:
        execution = _layer("unknown", unknowns=["no action count or action trace is available"])

    if animation_observations:
        perception = _layer("support-observed", [
            {"static_frames_recorded": frame_observations},
            {"ordered_animation_observations": animation_observations},
        ])
    elif frame_observations:
        perception = _layer("partial-evidence", [{"static_frames_recorded": frame_observations}], [
            "ordered animation exposure is not recorded",
            "static frames alone do not diagnose perception quality",
        ])
    else:
        perception = _layer("unknown", unknowns=["no frame evidence is available"])

    identity_bad = sum(identity_statuses[key] for key in ("BROKEN", "AMBIGUOUS"))
    if identity_bad:
        identity_layer = _layer("limitation-observed", [
            {"identity_status_counts": dict(identity_statuses)},
        ], ["the trace does not establish whether identity was decisive for the outcome"])
    elif identity_statuses.get("UNIQUE"):
        identity_layer = _layer("support-observed", [
            {"identity_status_counts": dict(identity_statuses)},
        ])
    else:
        identity_layer = _layer("unknown", unknowns=["no grounded identity assessment is recorded"])

    contested = sum(mechanism_statuses[key] for key in ("CONTESTED", "REFUTED"))
    if contested:
        mechanics = _layer("limitation-observed", [
            {"mechanism_status_counts": dict(mechanism_statuses)},
        ], ["the trace does not establish the game's true mechanism"])
    elif mechanism_statuses.get("SUPPORTED") or progress_eligible:
        mechanics = _layer("support-observed", [
            {"mechanism_status_counts": dict(mechanism_statuses)},
            {"progress_eligible_decisions": progress_eligible},
        ])
    elif probe_eligible or mechanism_statuses.get("UNKNOWN"):
        mechanics = _layer("open-hypothesis-observed", [
            {"mechanism_status_counts": dict(mechanism_statuses)},
            {"probe_eligible_decisions": probe_eligible},
        ], ["no supported or refuted mechanism is recorded"])
    else:
        mechanics = _layer("unknown", unknowns=["no mechanism assessment is recorded"])

    note_signature_counts = Counter(semantic_note_signatures)
    grounded_signature_counts = Counter(grounded_semantic_signatures)
    repeated_note_set = (
        len(semantic_note_signatures) >= 3
        and len(note_signature_counts) == 1
        and levels_completed == 0
    )
    if repeated_note_set:
        telos = _layer("repetition-observed", [
            {"semantic_note_writes": len(semantic_note_signatures)},
            {"distinct_canonical_proposal_sets": 1},
            {"levels_completed": levels_completed},
        ], [
            "exact proposal repetition does not establish that the proposal is false",
            "the trace does not establish that semantic revision was demanded",
        ])
    elif semantic_note_signatures:
        telos = _layer("evidence-observed", [
            {"semantic_note_writes": len(semantic_note_signatures)},
            {"distinct_canonical_proposal_sets": len(note_signature_counts)},
            {"grounded_control_signature_turns": len(grounded_semantic_signatures)},
            {"distinct_grounded_control_signatures": len(grounded_signature_counts)},
        ], ["the trace does not establish semantic correctness"])
    elif grounded_semantic_signatures:
        telos = _layer("grounded-hypothesis-observed", [
            {"grounded_control_signature_turns": len(grounded_semantic_signatures)},
            {"distinct_grounded_control_signatures": len(grounded_signature_counts)},
        ], ["semantic note write boundaries are unavailable"])
    else:
        telos = _layer("unknown", unknowns=["no grounded semantic signature is recorded"])

    if repeated_no_change:
        exploration = _layer("limitation-observed", [
            {"changed_observations": changed}, {"no_change_observations": unchanged},
            {"consecutive_identical_no_change": repeated_no_change},
        ])
    elif unchanged:
        exploration = _layer("no-change-observed", [
            {"changed_observations": changed}, {"no_change_observations": unchanged},
            {"consecutive_identical_no_change": 0},
        ])
    elif changed:
        exploration = _layer("support-observed", [{"changed_observations": changed}])
    else:
        exploration = _layer("unknown", unknowns=["no post-action change observation is recorded"])

    if mismatches:
        planning = _layer("failure-observed", [{"decision_execution_mismatches": mismatches}])
    elif action_turns:
        planning = _layer("support-observed", [
            {"decision_execution_mismatches": 0}, {"traced_action_turns": action_turns},
        ], ["agreement does not establish plan quality"])
    else:
        planning = _layer("unknown", unknowns=["no executed decision/action pair is recorded"])

    if outcome_status == "timeout":
        runtime = _layer("failure-observed", [{"outcome_status": "timeout"}])
    elif outcome_status == "error":
        runtime = _layer("failure-observed", [
            {"outcome_status": "error"},
            {"error_type": outcome.get("error_type")},
            {"error": outcome.get("error")},
        ])
    elif outcome_status == "complete":
        runtime = _layer("support-observed", [{"outcome_status": "complete"}])
    else:
        runtime = _layer("unknown", unknowns=["no terminal outcome status is available"])

    if levels_completed > 0:
        success = _layer("success-observed", [{"levels_completed": levels_completed}])
    elif outcome_status == "complete" or timeline:
        success = _layer("not-observed", [{"levels_completed": 0}])
    else:
        success = _layer("unknown", unknowns=["level completion is not recorded"])

    layers = {
        "execution_coverage": execution,
        "perception_animation_evidence": perception,
        "identity": identity_layer,
        "mechanics": mechanics,
        "telos_semantic_stagnation": telos,
        "exploration_no_change": exploration,
        "planning": planning,
        "runtime_deadline": runtime,
        "success": success,
    }
    assert tuple(layers) == FAILURE_LAYERS
    if success["assessment"] == "success-observed":
        observable_outcome = "success-observed"
    elif any(item["assessment"] == "failure-observed" for item in layers.values()):
        observable_outcome = "failure-observed"
    elif any(item["assessment"] == "limitation-observed" for item in layers.values()):
        observable_outcome = "limitation-observed"
    elif success["assessment"] == "not-observed":
        observable_outcome = "no-success-observed"
    else:
        observable_outcome = "unknown"
    return {
        "protocol": "r2.1-observable-failure-layers-v0",
        "observable_outcome": observable_outcome,
        "layers": layers,
        "epistemic_note": "Layer evidence is non-exclusive and does not identify hidden game rules or a unique root cause.",
    }


def analyze_episode(
    store: Any, episode: Path, *, outcome: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
        "observable_failure_layers": classify_trace(replay["timeline"], outcome=outcome),
    }


def analyze(run_root: Path) -> dict[str, Any]:
    episodes = run_root / "episodes"
    arcade = load_arcade()
    store = arcade.ReplayStore(episodes)
    rows = []
    errors = []
    outcomes = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted((run_root / "outcomes").glob("*.json"))
    }
    consumed_outcomes: set[str] = set()
    for episode in sorted(path for path in episodes.glob("*") if path.is_dir()):
        try:
            rows.append(analyze_episode(store, episode, outcome=outcomes.get(episode.name)))
            if episode.name in outcomes:
                consumed_outcomes.add(episode.name)
        except Exception as error:
            errors.append({"episode": episode.name, "error": f"{type(error).__name__}: {error}"})
    outcomes_without_replay = [
        {
            "episode": name,
            "game": outcome.get("game"),
            "start_level": outcome.get("start_level"),
            "status": outcome.get("status"),
            "observable_failure_layers": classify_trace((), outcome=outcome),
        }
        for name, outcome in outcomes.items()
        if name not in consumed_outcomes
    ]
    classifications = [
        row["observable_failure_layers"] for row in rows
    ] + [row["observable_failure_layers"] for row in outcomes_without_replay]
    layer_assessment_counts = {
        layer: dict(Counter(
            item["layers"][layer]["assessment"] for item in classifications
        ))
        for layer in FAILURE_LAYERS
    }
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
        "observable_failure_layer_counts": layer_assessment_counts,
        "outcomes_without_replay": outcomes_without_replay,
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
