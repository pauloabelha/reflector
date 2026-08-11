"""Frozen v0 test of one-step prospective explanation consequence control."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import os
import pickle
import random
import sys
import time
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

from reflector2.arc_harness import _derived_seed
from reflector2.explanation_experiment import ordered_process_map
from reflector2.explanations import ExplanationConfig, ExplanationDecision, ExplanationEngine
from reflector2.perception import PerceptionBatch, perceive_grid
from reflector2.runtime import Runtime


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
RECORDINGS = Path(
    "/home/pauloabelha/reflector-v164-pivot-goal/reports/"
    "v164-public-r1-recordings"
)
ENVIRONMENTS = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/environment_files"
)
CHECKPOINTS = (
    REPO
    / "experiments/r2-25-game-context-spinoff-diagnostic/parallel-run/checkpoints"
)
DIAGNOSTIC = (
    REPO / "experiments/r2-25-game-context-spinoff-diagnostic/run_diagnostic.py"
)
PROHIBITED = (
    "goal",
    "player",
    "target",
    "hazard",
    "door",
    "key",
    "movable",
)


def _load_diagnostic() -> Any:
    name = "reflector2_context_diagnostic_shared_for_prospective_explanations"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, DIAGNOSTIC)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import replay helpers from {DIAGNOSTIC}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


DIAG = _load_diagnostic()


EffectAtom = tuple[str, tuple[object, ...]]


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int
    beam_size: int
    max_consequences_per_explanation: int
    max_expansions_per_decision: int
    max_executed_overrides_per_game: int
    max_packets_per_game: int


@dataclass(frozen=True)
class ConsequenceRecord:
    explanation_id: int
    source_schema_id: int
    source_schema_hash: str
    action_id: int
    predicted_effects: tuple[EffectAtom, ...]
    consequence_schema_ids: tuple[int, ...]
    consequence_schema_hashes: tuple[str, ...]
    progress_support: int
    failure_support: int
    truncated: bool


@dataclass(frozen=True)
class ProspectiveRank:
    action_id: int
    progress_support: int
    failure_support: int
    robustness: int
    discrimination: int
    score_tuple: tuple[int, int, int, int]
    explanation_count: int
    consequence_count: int


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _job_key(job: dict[str, Any]) -> str:
    value = {
        "game": job["game"],
        "recording_sha256": _sha256(Path(job["recording"])),
        "config": job["config"],
        "protocol": 1,
    }
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _atomic_pickle(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("wb") as handle:
        pickle.dump(value, handle, protocol=pickle.HIGHEST_PROTOCOL)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _load_progress(path: Path, key: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with path.open("rb") as handle:
            value = pickle.load(handle)
    except (OSError, EOFError, pickle.UnpicklingError):
        return None
    if not isinstance(value, dict) or value.get("key") != key:
        return None
    state = value.get("state")
    return state if isinstance(state, dict) else None


def _load_completed(path: Path, key: str) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        value = _json(path)
    except (OSError, json.JSONDecodeError):
        return None
    if value.get("key") != key or not isinstance(value.get("result"), dict):
        return None
    return value["result"]


def _recording(game: str) -> Path:
    matches = sorted((RECORDINGS / game).glob("*.recording.jsonl"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one recording for {game}, found {len(matches)}")
    return matches[0]


def _recording_metadata(path: Path) -> tuple[int, str]:
    maximum = 0
    terminal = ""
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            packet = json.loads(line)["data"]
            maximum = max(maximum, int(packet["levels_completed"]))
            terminal = str(packet["state"])
    return maximum, terminal


def mechanically_select_games() -> dict[str, Any]:
    checkpoint_rows: list[tuple[str, int]] = []
    for path in sorted(CHECKPOINTS.glob("*.json")):
        value = _json(path)["result"]["deterministic"]
        checkpoint_rows.append((str(value["game"]), int(value["opportunities"])))
    causal = sorted(game for game, opportunities in checkpoint_rows if opportunities > 0)[:4]
    excluded = set(causal)
    metadata = {
        path.parent.name: _recording_metadata(path)
        for path in sorted(RECORDINGS.glob("*/*.recording.jsonl"))
    }
    partial = sorted(
        game
        for game, (levels, terminal) in metadata.items()
        if game not in excluded and levels > 0 and terminal != "WIN"
    )[:2]
    excluded.update(partial)
    no_opportunity = {
        game for game, opportunities in checkpoint_rows if opportunities == 0
    }
    negative = sorted(
        game
        for game in no_opportunity
        if game not in excluded and metadata[game][0] == 0
    )[:1]
    rows = [
        *({"game": game, "stratum": "causal-control-opportunity"} for game in causal),
        *({"game": game, "stratum": "existing-partial-progress"} for game in partial),
        *({"game": game, "stratum": "negative-control"} for game in negative),
    ]
    return {"games": rows}


def verify_frozen_selection() -> None:
    measured = mechanically_select_games()["games"]
    frozen = _json(HERE / "selected_games.json")["games"]
    if measured != frozen:
        raise RuntimeError(f"frozen cohort no longer matches mechanical rule: {measured}")


def _effect_json(signature: Sequence[EffectAtom]) -> list[str]:
    return [f"{head}:{','.join(map(str, arguments))}" for head, arguments in signature]


def _active_transition_schemas(
    engine: ExplanationEngine, legal_actions: Sequence[int]
) -> tuple[int, ...]:
    workspace = engine.runtime.workspace
    if workspace is None:
        return ()
    # Reuse the controller's active-frontier candidate selection. This never
    # scans dormant schema storage.
    return tuple(engine._candidate_schemas(workspace, legal_actions))


def _failure_evidence(engine: ExplanationEngine, schema_id: int) -> int:
    stats = engine._outcomes[schema_id]
    graph = engine.runtime.graph
    return int(
        stats.ineffective
        + stats.regressions
        + graph.contradiction[schema_id]
        + graph.prediction_failure[schema_id]
        + graph.projection_failure[schema_id]
    )


def build_consequence_records(
    engine: ExplanationEngine,
    decision: ExplanationDecision,
    legal_actions: Sequence[int],
    config: ExperimentConfig,
) -> tuple[tuple[ConsequenceRecord, ...], tuple[str, ...], int]:
    candidates = _active_transition_schemas(engine, legal_actions)
    records: list[ConsequenceRecord] = []
    reasons: list[str] = []
    expansions = 0
    for prediction in decision.predictions[: config.beam_size]:
        matched: list[int] = []
        truncated = False
        for schema_id in candidates:
            if schema_id == prediction.schema_id:
                continue
            if expansions >= config.max_expansions_per_decision:
                reasons.append("expansion-budget")
                truncated = True
                break
            expansions += 1
            if engine._effect_signature(schema_id) != prediction.signature:
                continue
            matched.append(schema_id)
            if len(matched) >= config.max_consequences_per_explanation:
                reasons.append("consequence-budget")
                truncated = True
                break
        progress = sum(
            max(0, int(engine._outcomes[schema_id].progress_total))
            for schema_id in matched
        )
        failure = sum(_failure_evidence(engine, schema_id) for schema_id in matched)
        graph = engine.runtime.graph
        records.append(
            ConsequenceRecord(
                explanation_id=int(prediction.explanation_id or -1),
                source_schema_id=prediction.schema_id,
                source_schema_hash=graph.canonical_hash[prediction.schema_id],
                action_id=prediction.action_id,
                predicted_effects=prediction.signature,
                consequence_schema_ids=tuple(matched),
                consequence_schema_hashes=tuple(
                    graph.canonical_hash[item] for item in matched
                ),
                progress_support=progress,
                failure_support=failure,
                truncated=truncated,
            )
        )
        if expansions >= config.max_expansions_per_decision:
            break
    if not records:
        reasons.append("no-prospective-evidence")
    elif not any(item.consequence_schema_ids for item in records):
        reasons.append("no-active-consequence-match")
    return tuple(records), tuple(sorted(set(reasons))), expansions


def rank_from_records(
    legal_actions: Sequence[int],
    baseline_order: Sequence[int],
    records: Sequence[ConsequenceRecord],
) -> tuple[tuple[ProspectiveRank, ...], bool]:
    by_action: dict[int, list[ConsequenceRecord]] = defaultdict(list)
    for record in records:
        by_action[record.action_id].append(record)
    action_signatures = {
        action: {
            record.predicted_effects
            for record in by_action.get(action, ())
            if record.progress_support or record.failure_support
        }
        for action in legal_actions
    }
    ranks: list[ProspectiveRank] = []
    for action in sorted(set(legal_actions)):
        action_records = by_action.get(action, [])
        progress = sum(item.progress_support for item in action_records)
        failure = sum(item.failure_support for item in action_records)
        useful_counts = Counter(
            item.predicted_effects
            for item in action_records
            if item.progress_support > item.failure_support
        )
        robustness = sum(max(0, count - 1) for count in useful_counts.values())
        others = set().union(
            *(action_signatures[other] for other in action_signatures if other != action)
        ) if len(action_signatures) > 1 else set()
        discrimination = len(action_signatures[action] - others)
        ranks.append(
            ProspectiveRank(
                action_id=action,
                progress_support=progress,
                failure_support=failure,
                robustness=robustness,
                discrimination=discrimination,
                score_tuple=(progress, -failure, robustness, discrimination),
                explanation_count=len(action_records),
                consequence_count=sum(
                    len(item.consequence_schema_ids) for item in action_records
                ),
            )
        )
    baseline_index = {action: index for index, action in enumerate(baseline_order)}
    ranks.sort(
        key=lambda item: (
            tuple(-value for value in item.score_tuple),
            baseline_index.get(item.action_id, len(baseline_index)),
            item.action_id,
        )
    )
    distinct = len({item.score_tuple for item in ranks}) > 1
    return tuple(ranks), distinct


def _baseline_decision(
    engine: ExplanationEngine,
    observed: PerceptionBatch,
    legal_actions: Sequence[int],
    baseline_action: int,
) -> ExplanationDecision:
    # The normal controller is executed unchanged against a copy so projected
    # shadows cannot enter the chronological runtime. Episode-local beam state
    # remains in the engine, while its runtime pointer is restored immediately.
    live = engine.runtime
    copied = copy.deepcopy(live)
    engine.runtime = copied
    try:
        if copied.workspace is None:
            raise RuntimeError("copied runtime has no workspace")
        return engine.decide(
            mode="explanation",
            workspace=copied.workspace,
            observed=observed,
            legal_action_ids=legal_actions,
            baseline_action_id=baseline_action,
        )
    finally:
        engine.runtime = live


def prospective_decision(
    engine: ExplanationEngine,
    baseline: ExplanationDecision,
    legal_actions: Sequence[int],
    config: ExperimentConfig,
) -> dict[str, Any]:
    baseline_order = [rank.action_id for rank in baseline.rankings]
    records, reasons, expansions = build_consequence_records(
        engine, baseline, legal_actions, config
    )
    ranks, distinct = rank_from_records(legal_actions, baseline_order, records)
    supported = [rank for rank in ranks if rank.consequence_count > 0]
    baseline_supported = any(
        rank.action_id == baseline.selected_action_id for rank in supported
    )
    supported_distinct = len({rank.score_tuple for rank in supported}) > 1
    selected = baseline.selected_action_id
    override_reason = "prospective_abstain"
    abstained = True
    if distinct and supported_distinct and len(supported) >= 2 and baseline_supported:
        selected = supported[0].action_id
        abstained = False
        override_reason = (
            "predicted-consequential-schema-activation"
            if selected != baseline.selected_action_id
            else "baseline-remains-top-after-prospective-closure"
        )
    elif not reasons:
        reasons = (
            "insufficient-supported-actions"
            if len(supported) < 2 or not baseline_supported
            else "equivalent-futures"
        ,)
    return {
        "selected": selected,
        "changed_top_action": selected != baseline.selected_action_id,
        "abstained": abstained,
        "override_reason": override_reason,
        "abstention_reasons": list(reasons),
        "expansions": expansions,
        "rankings": [asdict(item) for item in ranks],
        "records": records,
    }


def _selected_signatures(
    decision: ExplanationDecision, action_id: int
) -> set[tuple[EffectAtom, ...]]:
    return {
        prediction.signature
        for prediction in decision.predictions
        if prediction.action_id == action_id
    }


def _action_requires_data(action_id: int) -> bool:
    return action_id == 6


def _execute_branch(
    *,
    runtime: Runtime,
    before_batch: PerceptionBatch,
    predecessor_bindings: tuple[int, ...],
    prefix: Sequence[Any],
    game: str,
    action_id: int,
    predecessor_hash: str,
    prediction_signatures: set[tuple[EffectAtom, ...]],
    recordings_root: Path,
) -> dict[str, Any]:
    arcade, environment = DIAG.SHARED._open_arcade(
        ENVIRONMENTS, recordings_root, game
    )
    try:
        for recorded in prefix:
            DIAG.SHARED._act(environment, game, recorded, "chronological-state-reconstruction")
        frame = DIAG.SHARED._frame(environment.observation_space)
        actual_hash = DIAG.SHARED._frame_hash(frame)
        if actual_hash != predecessor_hash:
            raise RuntimeError(
                f"predecessor-replay-mismatch:{actual_hash}:{predecessor_hash}"
            )
        level_before = int(environment.observation_space.levels_completed)
        DIAG.SHARED._act(
            environment,
            game,
            DIAG.RecordedAction(action_id, {}),
            "prospective-explanation-ranked-action",
        )
        successor = DIAG.SHARED._frame(environment.observation_space)
        level_after = int(environment.observation_space.levels_completed)
        branch_runtime = copy.deepcopy(runtime)
        after = perceive_grid(
            branch_runtime.graph.terms,
            successor,
            "counterfactual-successor",
        )
        branch_runtime.observe(after)
        schema_id = branch_runtime.learn_transition(
            before_batch,
            after,
            f"arc-action:{action_id}",
            predecessor_schema_ids=predecessor_bindings,
        )
        actual_signature = ExplanationEngine(branch_runtime)._effect_signature(schema_id)
        correct = actual_signature in prediction_signatures
        return {
            "action": action_id,
            "predecessor_frame_sha256": actual_hash,
            "successor_frame_sha256": DIAG.SHARED._frame_hash(successor),
            "level_before": level_before,
            "level_after": level_after,
            "level_delta": level_after - level_before,
            "score_delta": None,
            "actual_effects": _effect_json(actual_signature),
            "prediction_correct": correct,
            "prospective_predictions_reified": (
                [_effect_json(actual_signature)] if correct else []
            ),
            "prospective_predictions_refuted": (
                [] if correct else [_effect_json(item) for item in sorted(prediction_signatures, key=repr)]
            ),
        }
    finally:
        arcade.close_scorecard()


def _classify(treatment: dict[str, Any], control: dict[str, Any]) -> str:
    if treatment["level_delta"] > control["level_delta"]:
        return "improve"
    if treatment["level_delta"] < control["level_delta"]:
        return "worsen"
    if treatment["prediction_correct"] and not control["prediction_correct"]:
        return "improve"
    if control["prediction_correct"] and not treatment["prediction_correct"]:
        return "worsen"
    return "tie"


def _decision_record(
    game: str,
    packet: int,
    predecessor_hash: str,
    baseline: ExplanationDecision,
    prospective: dict[str, Any],
) -> dict[str, Any]:
    records = prospective["records"]
    by_action: dict[int, list[ConsequenceRecord]] = defaultdict(list)
    for record in records:
        by_action[record.action_id].append(record)
    return {
        "game": game,
        "packet": packet,
        "predecessor_hash": predecessor_hash,
        "baseline": {
            "action": f"arc-action:{baseline.selected_action_id}",
            "ranking_reason": [asdict(rank) for rank in baseline.rankings],
        },
        "prospective": {
            "candidates": [
                {
                    **rank,
                    "action": f"arc-action:{rank['action_id']}",
                    "explanations": [
                        {
                            "explanation_id": record.explanation_id,
                            "transition_schema": record.source_schema_hash,
                            "predicted_effects": _effect_json(record.predicted_effects),
                            "prospective_consequences": list(record.consequence_schema_hashes),
                            "progress_support": record.progress_support,
                            "failure_support": record.failure_support,
                            "truncated": record.truncated,
                        }
                        for record in by_action.get(rank["action_id"], ())
                    ],
                }
                for rank in prospective["rankings"]
            ],
            "chosen": f"arc-action:{prospective['selected']}",
            "override_reason": prospective["override_reason"],
            "abstention_reasons": prospective["abstention_reasons"],
            "expansions": prospective["expansions"],
        },
        "actual": None,
    }


def _summarize_game_state(
    *,
    game: str,
    recording: Path,
    packets_seen: int,
    decisions: list[dict[str, Any]],
    overrides: list[dict[str, Any]],
    fallback_reasons: Counter[str],
    executed: int,
    curtailed: bool,
) -> dict[str, Any]:
    outcome = Counter(
        item["actual"]["classification"]
        for item in overrides
        if item["actual"] and item["actual"]["executed"]
    )
    return {
        "game": game,
        "recording_sha256": _sha256(recording),
        "packets": packets_seen,
        "curtailed_before_packet_cap": curtailed,
        "decisions": len(decisions),
        "prospective_abstentions": sum(
            item["prospective"]["override_reason"] == "prospective_abstain"
            for item in decisions
        ),
        "prospective_distinctions": sum(
            item["prospective"]["override_reason"] != "prospective_abstain"
            for item in decisions
        ),
        "top_action_overrides": sum(
            item["baseline"]["action"] != item["prospective"]["chosen"]
            for item in decisions
        ),
        "executed_overrides": executed,
        "improve": outcome["improve"],
        "tie": outcome["tie"],
        "worsen": outcome["worsen"],
        "completed_level_delta_vs_baseline": sum(
            int(item["actual"]["completed_level_delta_vs_baseline"])
            for item in overrides
        ),
        "fallback_reasons": dict(sorted(fallback_reasons.items())),
        "explanations_considered": sum(
            len(item["prospective"]["candidates"]) for item in decisions
        ),
        "consequence_expansions": sum(
            int(item["prospective"]["expansions"]) for item in decisions
        ),
        "decisions_trace": decisions,
    }


def evaluate_game(job: dict[str, Any]) -> dict[str, Any]:
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    game = str(job["game"])
    config = ExperimentConfig(**job["config"])
    recording = Path(job["recording"])
    key = _job_key(job)
    completed_path = Path(job["completed_checkpoint"])
    completed = _load_completed(completed_path, key)
    if completed is not None:
        return completed
    progress_path = Path(job["progress_checkpoint"])
    packet_list = list(DIAG._packets(recording))
    if not packet_list:
        raise RuntimeError(f"empty recording: {recording}")
    restored = _load_progress(progress_path, key)
    if restored is None:
        runtime = Runtime()
        engine = ExplanationEngine(
            runtime, ExplanationConfig(max_explanations=config.beam_size)
        )
        rng = random.Random(_derived_seed(config.seed, game, "actions"))
        previous = packet_list[0]
        before_batch, _features = DIAG._observe(
            runtime, previous.frame, f"observation:{previous.index}"
        )
        prefix = [previous.action]
        decisions: list[dict[str, Any]] = []
        overrides: list[dict[str, Any]] = []
        fallback_reasons: Counter[str] = Counter()
        executed = 0
        packets_seen = 1
        next_position = 1
    else:
        runtime = restored["runtime"]
        engine = restored["engine"]
        engine.runtime = runtime
        rng = restored["rng"]
        previous = restored["previous"]
        before_batch = restored["before_batch"]
        prefix = restored["prefix"]
        decisions = restored["decisions"]
        overrides = restored["overrides"]
        fallback_reasons = restored["fallback_reasons"]
        executed = restored["executed"]
        packets_seen = restored["packets_seen"]
        next_position = restored["next_position"]

    def checkpoint(position: int) -> None:
        _atomic_pickle(
            progress_path,
            {
                "key": key,
                "state": {
                    "runtime": runtime,
                    "engine": engine,
                    "rng": rng,
                    "previous": previous,
                    "before_batch": before_batch,
                    "prefix": prefix,
                    "decisions": decisions,
                    "overrides": overrides,
                    "fallback_reasons": fallback_reasons,
                    "executed": executed,
                    "packets_seen": packets_seen,
                    "next_position": position,
                },
            },
        )

    if restored is None:
        checkpoint(next_position)
    for position in range(next_position, len(packet_list)):
        packet = packet_list[position]
        if packets_seen >= config.max_packets_per_game:
            break
        packets_seen += 1
        legal = tuple(previous.available_actions)
        if not legal:
            after_batch, _features = DIAG._observe(
                runtime, packet.frame, f"observation:{packet.index}"
            )
            before_batch = after_batch
            previous = packet
            prefix.append(packet.action)
            fallback_reasons["no-legal-actions"] += 1
            checkpoint(position + 1)
            continue
        baseline_seed = rng.choice(sorted(legal))
        baseline = _baseline_decision(engine, before_batch, legal, baseline_seed)
        prospective = prospective_decision(engine, baseline, legal, config)
        record = _decision_record(
            game, packet.index, previous.frame_sha256, baseline, prospective
        )
        if prospective["abstained"]:
            for reason in prospective["abstention_reasons"] or ["equivalent-futures"]:
                fallback_reasons[reason] += 1
        changed = bool(prospective["changed_top_action"])
        if changed:
            reason: str | None = None
            if executed >= config.max_executed_overrides_per_game:
                reason = "override-budget"
            elif _action_requires_data(baseline.selected_action_id) or _action_requires_data(
                prospective["selected"]
            ):
                reason = "action-data-required"
            baseline_signatures = _selected_signatures(
                baseline, baseline.selected_action_id
            )
            treatment_signatures = _selected_signatures(
                baseline, prospective["selected"]
            )
            if not baseline_signatures or not treatment_signatures:
                reason = "missing-action-explanation"
            if reason is not None:
                record["actual"] = {"executed": False, "abstention_reason": reason}
                fallback_reasons[reason] += 1
            else:
                predecessor_bindings = tuple(
                    sorted(
                        {
                            binding.schema_id
                            for binding in (runtime.workspace.bindings if runtime.workspace else ())
                        }
                    )
                )
                try:
                    control = _execute_branch(
                        runtime=runtime,
                        before_batch=before_batch,
                        predecessor_bindings=predecessor_bindings,
                        prefix=prefix,
                        game=game,
                        action_id=baseline.selected_action_id,
                        predecessor_hash=previous.frame_sha256,
                        prediction_signatures=baseline_signatures,
                        recordings_root=Path(job["branch_recordings"]) / "control",
                    )
                    treatment = _execute_branch(
                        runtime=runtime,
                        before_batch=before_batch,
                        predecessor_bindings=predecessor_bindings,
                        prefix=prefix,
                        game=game,
                        action_id=prospective["selected"],
                        predecessor_hash=previous.frame_sha256,
                        prediction_signatures=treatment_signatures,
                        recordings_root=Path(job["branch_recordings"]) / "treatment",
                    )
                except (RuntimeError, ValueError) as error:
                    reason = str(error).split(":", 1)[0]
                    record["actual"] = {
                        "executed": False,
                        "abstention_reason": reason,
                    }
                    fallback_reasons[reason] += 1
                else:
                    if control["predecessor_frame_sha256"] != treatment["predecessor_frame_sha256"]:
                        raise RuntimeError("matched predecessor hashes differ")
                    classification = _classify(treatment, control)
                    record["actual"] = {
                        "executed": True,
                        "classification": classification,
                        "baseline": control,
                        "treatment": treatment,
                        "completed_level_delta_vs_baseline": (
                            treatment["level_delta"] - control["level_delta"]
                        ),
                        "score_delta_vs_baseline": None,
                    }
                    executed += 1
                    overrides.append(record)
        decisions.append(record)

        predecessor_bindings = tuple(
            sorted(
                {
                    binding.schema_id
                    for binding in (runtime.workspace.bindings if runtime.workspace else ())
                }
            )
        )
        after_batch, _features = DIAG._observe(
            runtime, packet.frame, f"observation:{packet.index}"
        )
        schema_id = runtime.learn_transition(
            before_batch,
            after_batch,
            f"arc-action:{packet.action.action_id}",
            predecessor_schema_ids=predecessor_bindings,
        )
        engine.observe_outcome(
            None,
            before=before_batch,
            after=after_batch,
            observed_schema_id=schema_id,
            progress_delta=packet.levels_completed - previous.levels_completed,
            reward=None,
        )
        before_batch = after_batch
        previous = packet
        prefix.append(packet.action)
        checkpoint(position + 1)

    deterministic = _summarize_game_state(
        game=game,
        recording=recording,
        packets_seen=packets_seen,
        decisions=decisions,
        overrides=overrides,
        fallback_reasons=fallback_reasons,
        executed=executed,
        curtailed=False,
    )
    result = {
        "deterministic": deterministic,
        "timing": {
            "wall_seconds": time.perf_counter() - started_wall,
            "cpu_seconds": time.process_time() - started_cpu,
        },
    }
    _write_json(completed_path, {"key": key, "result": result})
    return result


def _aggregate(results: Sequence[dict[str, Any]], config: ExperimentConfig) -> dict[str, Any]:
    games = [item["deterministic"] for item in results]
    all_decisions = [
        decision for game in games for decision in game["decisions_trace"]
    ]
    overrides = [
        decision
        for game in games
        for decision in game["decisions_trace"]
        if (decision.get("actual") or {}).get("executed")
    ]
    outcome = Counter(item["actual"]["classification"] for item in overrides)
    executed = len(overrides)
    completed_delta = sum(
        int(item["actual"]["completed_level_delta_vs_baseline"])
        for item in overrides
    )
    changed_games = {item["game"] for item in overrides}
    improve_games = {
        item["game"]
        for item in overrides
        if item["actual"]["classification"] == "improve"
    }
    precision = outcome["improve"] / executed if executed else None
    false_rate = outcome["worsen"] / executed if executed else None
    causal_benefit = any(
        item["actual"]["classification"] == "improve"
        and any(
            explanation["prospective_consequences"]
            for candidate in item["prospective"]["candidates"]
            for explanation in candidate["explanations"]
        )
        for item in overrides
    )
    if (
        len(changed_games) >= 3
        and outcome["improve"] > outcome["worsen"]
        and completed_delta > 0
        and false_rate is not None
        and false_rate <= 0.20
        and any(game != "ar25" for game in improve_games)
        and causal_benefit
    ):
        verdict = "PROMISING"
    elif executed >= 10 and (
        outcome["worsen"] >= outcome["improve"]
        or (false_rate is not None and false_rate > 0.40)
    ):
        verdict = "NEGATIVE"
    else:
        verdict = "INCONCLUSIVE"
    decisions = sum(game["decisions"] for game in games)
    abstentions = sum(game["prospective_abstentions"] for game in games)
    reified = sum(
        bool(item["actual"]["treatment"]["prediction_correct"])
        for item in overrides
    )
    fallback_reasons = sum(
        (Counter(game["fallback_reasons"]) for game in games), Counter()
    )
    consequence_hashes = Counter(
        schema_hash
        for decision in all_decisions
        for candidate in decision["prospective"]["candidates"]
        for explanation in candidate["explanations"]
        for schema_hash in explanation["prospective_consequences"]
    )
    robustness_total = sum(
        int(candidate["robustness"])
        for decision in all_decisions
        for candidate in decision["prospective"]["candidates"]
    )
    discrimination_total = sum(
        int(candidate["discrimination"])
        for decision in all_decisions
        for candidate in decision["prospective"]["candidates"]
    )
    return {
        "experiment": "prospective-explanation-control-v0",
        "configuration": asdict(config),
        "cohort": [game["game"] for game in games],
        "aggregate": {
            "games_containing_executed_overrides": len(changed_games),
            "executed_overrides": executed,
            "improve": outcome["improve"],
            "tie": outcome["tie"],
            "worsen": outcome["worsen"],
            "completed_level_delta_vs_baseline": completed_delta,
            "score_delta_vs_baseline": None,
            "score_note": "unavailable from the offline ARC observation API",
            "action_changing_precision": precision,
            "false_override_rate": false_rate,
            "prospective_abstentions": abstentions,
            "prospective_abstention_fraction": abstentions / decisions if decisions else None,
            "prospective_consequence_prediction_accuracy": reified / executed if executed else None,
            "explanations_considered": sum(game["explanations_considered"] for game in games),
            "consequence_expansions": sum(game["consequence_expansions"] for game in games),
            "fallback_reasons": dict(sorted(fallback_reasons.items())),
            "prospective_robustness_total": robustness_total,
            "prospective_discrimination_total": discrimination_total,
        },
        "recurrent_consequence_schema_hashes": {
            key: count
            for key, count in sorted(consequence_hashes.items())
            if count >= 2
        },
        "concentration": dict(
            sorted(Counter(item["game"] for item in overrides).items())
        ),
        "negative_cases": [
            {"game": item["game"], "packet": item["packet"]}
            for item in overrides
            if item["actual"]["classification"] == "worsen"
        ],
        "per_game": [
            {key: value for key, value in game.items() if key != "decisions_trace"}
            for game in games
        ],
        "verdict": verdict,
    }


def _render_results(summary: dict[str, Any], execution: dict[str, Any]) -> str:
    aggregate = summary["aggregate"]
    per_game = summary["per_game"]
    lines = [
        "# Results: Prospective Explanation Control v0",
        "",
        f"## Verdict: `{summary['verdict']}`",
        "",
        "The frozen treatment was evaluated without per-game tuning. Prediction "
        "accuracy is secondary; the verdict follows the preregistered action/outcome gate.",
        "",
        "## Cohort and configuration",
        "",
        "Selection followed the exact mechanical procedure in `PROPOSAL.md`. Selected "
        f"games: {', '.join(f'`{game}`' for game in summary['cohort'])}.",
        "",
        f"Exact configuration: `{json.dumps(summary['configuration'], sort_keys=True)}`.",
        "",
        "## Aggregate",
        "",
        f"- Games containing executed overrides: {aggregate['games_containing_executed_overrides']}",
        f"- Improve / tie / worsen: {aggregate['improve']} / {aggregate['tie']} / {aggregate['worsen']}",
        f"- Completed-level delta: {aggregate['completed_level_delta_vs_baseline']:+d}",
        f"- Action-changing precision: {aggregate['action_changing_precision']}",
        f"- False-override rate: {aggregate['false_override_rate']}",
        f"- Prospective fallback: {aggregate['prospective_abstentions']} ({aggregate['prospective_abstention_fraction']})",
        f"- Consequence prediction accuracy (secondary): {aggregate['prospective_consequence_prediction_accuracy']}",
        f"- Score delta: unavailable",
        "",
        "## Per game",
        "",
        "| Game | Decisions | Overrides | Executed | Improve | Tie | Worsen | Level delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    if summary.get("execution_status") == "user-directed-early-stop":
        early = summary["early_stop"]
        lines[6:6] = [
            "**Execution scope:** user-directed early stop after the negative gate was "
            "reached. The full 40-packet cap was not completed; all results below come "
            "from durable chronological prefixes.",
            "",
            "Observed packets: "
            + ", ".join(
                f"`{game}` {packets}"
                for game, packets in early["observed_packets_by_game"].items()
            )
            + ".",
            "",
        ]
    aggregate_insert = lines.index("- Score delta: unavailable")
    lines[aggregate_insert:aggregate_insert] = [
        f"- Fallback/abstention reasons: `{json.dumps(aggregate['fallback_reasons'], sort_keys=True)}`",
        f"- Robustness / discrimination totals: {aggregate['prospective_robustness_total']} / {aggregate['prospective_discrimination_total']}",
        f"- Consequence expansions: {aggregate['consequence_expansions']}",
    ]
    for game in per_game:
        lines.append(
            f"| `{game['game']}` | {game['decisions']} | {game['top_action_overrides']} | "
            f"{game['executed_overrides']} | {game['improve']} | {game['tie']} | "
            f"{game['worsen']} | {game['completed_level_delta_vs_baseline']:+d} |"
        )
    lines.extend(
        [
            "",
            "## Safeguards",
            "",
            "- Both arms were ranked before the held-out packet was observed.",
            "- Counterfactual successors were processed only by deep-copied runtimes.",
            "- Every matched branch verified its predecessor frame hash.",
            "- Actions requiring coordinate payloads abstained.",
            "- Expansion, consequence, explanation, and override caps were enforced and traced.",
            "- Game identity appeared only in transport/provenance, never in scoring.",
            f"- Serial/parallel structural verification: {execution['serial_parallel_identical']}.",
            f"- Repeated serial structural verification: {execution['repeated_serial_identical']}.",
            "- Runtime wall/CPU totals: unavailable across the interrupted/resumed early-stop run.",
            "",
            "## Every executed override",
            "",
        ]
    )
    for item in execution["executed_override_index"]:
        lines.append(
            f"- `{item['game']}:{item['packet']}`: {item['baseline']} → {item['treatment']}; "
            f"{item['classification']}; level delta {item['level_delta']:+d}."
        )
    if not execution["executed_override_index"]:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Negative cases and interpretation",
            "",
            f"All worsened cases: `{json.dumps(summary['negative_cases'], sort_keys=True)}`.",
            "",
            "The smallest representational gap, if overrides remain rare, is the lack of "
            "grounded successor values: v0 can close only over exact structural effect "
            "signatures, not a fabricated future raster or semantic goal state.",
            "",
            "No code was promoted into core.",
            "",
            "Recurrent consequence schema hashes are recorded in `artifacts/summary.json`; "
            "full causal records for all overrides are in `artifacts/overrides.json`.",
        ]
    )
    return "\n".join(lines) + "\n"


def _configured_jobs(config: ExperimentConfig) -> list[dict[str, Any]]:
    frozen = _json(HERE / "selected_games.json")["games"]
    return [
        {
            "game": item["game"],
            "recording": str(_recording(item["game"])),
            "config": asdict(config),
            "branch_recordings": str(
                HERE / "artifacts/branch-recordings" / item["game"]
            ),
            "progress_checkpoint": str(
                HERE / "artifacts/checkpoints" / f"{item['game']}.pickle"
            ),
            "completed_checkpoint": str(
                HERE / "artifacts/checkpoints" / f"{item['game']}.json"
            ),
        }
        for item in frozen
    ]


def _executed_records(results: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        decision
        for result in results
        for decision in result["deterministic"]["decisions_trace"]
        if (decision.get("actual") or {}).get("executed")
    ]


def _override_index(records: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "game": item["game"],
            "packet": item["packet"],
            "baseline": item["baseline"]["action"],
            "treatment": item["prospective"]["chosen"],
            "classification": item["actual"]["classification"],
            "level_delta": item["actual"]["completed_level_delta_vs_baseline"],
        }
        for item in records
    ]


def _write_final_outputs(
    results: Sequence[dict[str, Any]],
    summary: dict[str, Any],
    execution: dict[str, Any],
) -> None:
    artifacts = HERE / "artifacts"
    for result in results:
        game = result["deterministic"]["game"]
        _write_json(artifacts / "games" / f"{game}.json", result)
    records = _executed_records(results)
    _write_json(artifacts / "summary.json", summary)
    _write_json(artifacts / "overrides.json", records)
    _write_json(artifacts / "execution.json", execution)
    (HERE / "RESULTS.md").write_text(
        _render_results(summary, execution), encoding="utf-8"
    )


def finalize_checkpoints() -> dict[str, Any]:
    """Finalize a transparent user-directed early stop from durable prefixes."""

    verify_frozen_selection()
    raw = _json(HERE / "config.json")
    config = ExperimentConfig(
        **{key: raw[key] for key in ExperimentConfig.__dataclass_fields__}
    )
    jobs = _configured_jobs(config)
    results: list[dict[str, Any]] = []
    for job in jobs:
        state = _load_progress(Path(job["progress_checkpoint"]), _job_key(job))
        if state is None:
            raise RuntimeError(f"missing compatible progress checkpoint: {job['game']}")
        deterministic = _summarize_game_state(
            game=str(job["game"]),
            recording=Path(job["recording"]),
            packets_seen=int(state["packets_seen"]),
            decisions=state["decisions"],
            overrides=state["overrides"],
            fallback_reasons=state["fallback_reasons"],
            executed=int(state["executed"]),
            curtailed=True,
        )
        results.append(
            {
                "deterministic": deterministic,
                "timing": {
                    "wall_seconds": None,
                    "cpu_seconds": None,
                    "note": "unavailable across interrupted/resumed early-stop execution",
                },
            }
        )
    summary = _aggregate(results, config)
    summary["execution_status"] = "user-directed-early-stop"
    summary["early_stop"] = {
        "reason": "diagnostic sufficiency after negative gate was reached",
        "planned_packet_cap_per_game": config.max_packets_per_game,
        "observed_packets_by_game": {
            item["deterministic"]["game"]: item["deterministic"]["packets"]
            for item in results
        },
        "diagnostic_subset": [
            item["deterministic"]["game"]
            for item in results
            if item["deterministic"]["executed_overrides"] > 0
        ],
        "scope_note": "full planned 40-packet exposure was not completed",
    }

    # Keep the process/determinism safeguard real but cheap: one three-packet
    # public-game probe in a worker and two fresh serial runs.
    probe = copy.deepcopy(jobs[0])
    probe["config"]["max_packets_per_game"] = 3
    probe["config"]["max_executed_overrides_per_game"] = 0
    probe_results = []
    for label in ("parallel", "serial-one", "serial-two"):
        current = copy.deepcopy(probe)
        current["progress_checkpoint"] = str(
            HERE / "artifacts/checkpoints" / f"final-probe-{label}.pickle"
        )
        current["completed_checkpoint"] = str(
            HERE / "artifacts/checkpoints" / f"final-probe-{label}.json"
        )
        if label == "parallel":
            probe_results.append(ordered_process_map(evaluate_game, [current], 2)[0])
        else:
            probe_results.append(evaluate_game(current))
    structures = [item["deterministic"] for item in probe_results]
    records = _executed_records(results)
    execution = {
        "wall_seconds": None,
        "workers": 7,
        "checkpointing": "atomic progress after every packet; finalized from compatible snapshots",
        "preregistration_sha256": {
            "PROPOSAL.md": _sha256(HERE / "PROPOSAL.md"),
            "config.json": _sha256(HERE / "config.json"),
            "selected_games.json": _sha256(HERE / "selected_games.json"),
        },
        "serial_parallel_identical": structures[0] == structures[1],
        "repeated_serial_identical": structures[1] == structures[2],
        "executed_override_index": _override_index(records),
        "early_stop": summary["early_stop"],
    }
    if not execution["serial_parallel_identical"] or not execution["repeated_serial_identical"]:
        raise RuntimeError("final structural probe mismatch")
    _write_final_outputs(results, summary, execution)
    return {"summary": summary, "execution": execution}


def run(args: argparse.Namespace) -> dict[str, Any]:
    verify_frozen_selection()
    raw = _json(HERE / "config.json")
    config = ExperimentConfig(
        **{key: raw[key] for key in ExperimentConfig.__dataclass_fields__}
    )
    jobs = _configured_jobs(config)
    started = time.perf_counter()
    results = ordered_process_map(evaluate_game, jobs, args.workers)
    # A fixed three-packet representative probe is run once in a worker and
    # twice serially. It exercises real perception/runtime state while keeping
    # the isolation safeguard proportionate to the already expensive cohort.
    probe_job = copy.deepcopy(jobs[0])
    probe_job["config"]["max_packets_per_game"] = 3
    probe_job["config"]["max_executed_overrides_per_game"] = 0
    probe_job["branch_recordings"] = str(HERE / "artifacts/probe-recordings")
    probe_job["progress_checkpoint"] = str(HERE / "artifacts/checkpoints/probe-parallel.pickle")
    probe_job["completed_checkpoint"] = str(HERE / "artifacts/checkpoints/probe-parallel.json")
    parallel_probe = ordered_process_map(evaluate_game, [probe_job], 2)[0]
    serial_job_one = copy.deepcopy(probe_job)
    serial_job_one["progress_checkpoint"] = str(HERE / "artifacts/checkpoints/probe-serial-one.pickle")
    serial_job_one["completed_checkpoint"] = str(HERE / "artifacts/checkpoints/probe-serial-one.json")
    serial_job_two = copy.deepcopy(probe_job)
    serial_job_two["progress_checkpoint"] = str(HERE / "artifacts/checkpoints/probe-serial-two.pickle")
    serial_job_two["completed_checkpoint"] = str(HERE / "artifacts/checkpoints/probe-serial-two.json")
    serial_one = evaluate_game(serial_job_one)
    serial_two = evaluate_game(serial_job_two)
    parallel_structural = parallel_probe["deterministic"]
    serial_structural = serial_one["deterministic"]
    repeat_structural = serial_two["deterministic"]
    if parallel_structural != serial_structural or serial_structural != repeat_structural:
        raise RuntimeError("serial/parallel or repeated-serial structural mismatch")
    summary = _aggregate(results, config)
    executed_records = _executed_records(results)
    execution = {
        "wall_seconds": time.perf_counter() - started,
        "workers": args.workers,
        "checkpointing": "atomic per-game completion plus atomic progress after every packet",
        "preregistration_sha256": {
            "PROPOSAL.md": _sha256(HERE / "PROPOSAL.md"),
            "config.json": _sha256(HERE / "config.json"),
            "selected_games.json": _sha256(HERE / "selected_games.json"),
        },
        "serial_parallel_identical": parallel_structural == serial_structural,
        "repeated_serial_identical": serial_structural == repeat_structural,
        "executed_override_index": _override_index(executed_records),
    }
    _write_final_outputs(results, summary, execution)
    return {"summary": summary, "execution": execution}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=7)
    parser.add_argument("--finalize-checkpoints", action="store_true")
    return parser


def main() -> None:
    args = _parser().parse_args()
    value = finalize_checkpoints() if args.finalize_checkpoints else run(args)
    print(json.dumps(value, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
