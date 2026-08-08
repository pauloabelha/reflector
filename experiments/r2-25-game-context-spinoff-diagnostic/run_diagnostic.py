"""Fixed 25-game diagnostic for prospective context-schema spinoffs."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
import random
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

from reflector2.perception import PerceptionBatch, perceive_grid
from reflector2.runtime import Runtime
from reflector2.store import SCHEMA_ESTABLISHED


HERE = Path(__file__).resolve().parent
COHORT_ROOT = Path(
    "/home/pauloabelha/reflector-v164-pivot-goal/reports/"
    "v164-public-r1-recordings"
)
ENVIRONMENTS_ROOT = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/environment_files"
)
SHARED_EXPERIMENT = HERE.parent / "prospective-context-spinoff-control" / "run_experiment.py"
EXPECTED_GAMES = 25
PROTOCOL_VERSION = 1
CHECKPOINT_FORMAT = 1

FROZEN_AR25 = {
    "context_hash": "38bac99b151198744c9ea62355a77c6116ef9493de6e678115dc8d4772385454",
    "parent_hash": "4dd44c2c187a681e2c8079ec0c9c79bcdc599b87829ea73cf326c5df191e23cc",
    "child_hash": "e4d3812a7ae5f3c0efd59918f0d45ca3218e167384dd1e3fb8f88843d8b197b0",
    "baseline_action": 2,
    "treatment_action": 3,
}


def _load_shared() -> Any:
    name = "reflector2_prospective_context_spinoff_shared"
    found = sys.modules.get(name)
    if found is not None:
        return found
    spec = importlib.util.spec_from_file_location(name, SHARED_EXPERIMENT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load shared mechanism: {SHARED_EXPERIMENT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SHARED = _load_shared()
RecordedAction = SHARED.RecordedAction
Transition = SHARED.Transition
ContextCondition = SHARED.ContextCondition


@dataclass(frozen=True)
class DiagnosticConfig:
    seed: int = 0
    max_context_candidates: int = 64
    min_context_support: int = 2
    max_action_changes_per_game: int = 64


@dataclass(frozen=True)
class Packet:
    index: int
    action: Any
    frame: tuple[tuple[int, ...], ...]
    frame_sha256: str
    levels_completed: int
    available_actions: tuple[int, ...]
    state: str


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def _checkpoint_key(job: dict[str, Any]) -> str:
    recording = Path(job["recording"])
    return _stable_hash(
        {
            "protocol_version": PROTOCOL_VERSION,
            "game": job["game"],
            "recording_sha256": SHARED._file_hash(recording),
            "environments_root": str(Path(job["environments_root"]).resolve()),
            "config": job["config"],
            "max_packets": job.get("max_packets"),
        }
    )


def _load_checkpoint(job: dict[str, Any]) -> dict[str, Any] | None:
    raw_path = job.get("checkpoint")
    if raw_path is None:
        return None
    path = Path(raw_path)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if (
        payload.get("checkpoint_format") != CHECKPOINT_FORMAT
        or payload.get("key") != _checkpoint_key(job)
    ):
        return None
    result = payload.get("result")
    return result if isinstance(result, dict) else None


def _packet_frame(value: Any) -> tuple[tuple[int, ...], ...]:
    if hasattr(value, "tolist"):
        value = value.tolist()
    if isinstance(value, list) and value and hasattr(value[-1], "tolist"):
        value = value[-1].tolist()
    while (
        isinstance(value, list)
        and value
        and isinstance(value[0], list)
        and value[0]
        and isinstance(value[0][0], list)
    ):
        value = value[-1]
    return tuple(tuple(int(cell) for cell in row) for row in value)


def _packets(path: Path) -> Iterable[Packet]:
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle):
            data = json.loads(line)["data"]
            action_input = data["action_input"]
            action_data = {
                str(key): int(value)
                for key, value in action_input.get("data", {}).items()
                if key != "game_id"
            }
            frame = _packet_frame(data["frame"])
            yield Packet(
                index=index,
                action=RecordedAction(int(action_input["id"]), action_data),
                frame=frame,
                frame_sha256=SHARED._frame_hash(frame),
                levels_completed=int(data["levels_completed"]),
                available_actions=tuple(sorted(int(item) for item in data["available_actions"])),
                state=str(data["state"]),
            )


def _new_runtime(seed: int) -> Runtime:
    random.seed(seed)
    runtime = Runtime()
    return runtime


def _kernel_fingerprint(runtime: Runtime) -> str:
    return _stable_hash(
        [runtime.graph.canonical_hash[index] for index in sorted(runtime.kernel_schema_ids.values())]
    )


def _observe(
    runtime: Runtime,
    frame: tuple[tuple[int, ...], ...],
    context: str,
) -> tuple[PerceptionBatch, frozenset[int]]:
    batch = perceive_grid(runtime.graph.terms, frame, context)
    workspace = runtime.observe(batch)
    return batch, frozenset(binding.schema_id for binding in workspace.bindings)


def _rank_parent(
    transitions: list[Any], legal_actions: tuple[int, ...]
) -> list[dict[str, int]]:
    legal = set(legal_actions)
    counts = Counter(item.action_id for item in transitions if item.action_id in legal)
    return [
        {"action": action, "parent_support": support}
        for action, support in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _relation_candidates(runtime: Runtime, limit: int) -> list[int]:
    output: list[int] = []
    for schema_id, pattern in enumerate(runtime.graph.patterns):
        if runtime.graph.schema_state[schema_id] != SCHEMA_ESTABLISHED:
            continue
        if runtime.graph.depth[schema_id] != 0 or len(pattern) != 1:
            continue
        _head, arguments = pattern[0]
        if len(arguments) != 2 or any(tag != "v" for tag, _value in arguments):
            continue
        output.append(schema_id)
    return sorted(output, key=lambda item: runtime.graph.canonical_hash[item])[:limit]


def _discover_context(
    runtime: Runtime,
    transitions: list[Any],
    current_features: frozenset[int],
    legal_actions: tuple[int, ...],
    config: DiagnosticConfig,
) -> tuple[Any | None, str]:
    legal = set(legal_actions)
    usable = [item for item in transitions if item.action_id in legal]
    counts = Counter(item.action_id for item in usable)
    if len(counts) < 2:
        return None, "parent-not-ambiguous"
    parent_purity = max(counts.values()) / len(usable)
    candidates: list[Any] = []
    for schema_id in _relation_candidates(runtime, config.max_context_candidates):
        present = schema_id in current_features
        matching = [
            item
            for item in usable
            if (schema_id in item.predecessor_features) == present
        ]
        if len(matching) < config.min_context_support:
            continue
        child_counts = Counter(item.action_id for item in matching)
        action_id, action_support = min(
            child_counts.items(), key=lambda item: (-item[1], item[0])
        )
        purity = action_support / len(matching)
        if purity <= parent_purity:
            continue
        candidates.append(
            ContextCondition(schema_id, present, len(matching), purity, action_id)
        )
    if not candidates:
        return None, "no-eligible-context"
    return (
        min(
            candidates,
            key=lambda item: (
                -item.purity,
                -item.support,
                runtime.graph.canonical_hash[item.schema_id],
            ),
        ),
        "eligible",
    )


def _matching_context_transitions(
    transitions: list[Any], condition: Any, legal_actions: tuple[int, ...]
) -> list[Any]:
    legal = set(legal_actions)
    return [
        item
        for item in transitions
        if item.action_id in legal
        and (condition.schema_id in item.predecessor_features) == condition.present
    ]


def _rank_child(
    transitions: list[Any], condition: Any, legal_actions: tuple[int, ...]
) -> list[dict[str, int]]:
    legal = set(legal_actions)
    parent = Counter(item.action_id for item in transitions if item.action_id in legal)
    child = Counter(
        item.action_id
        for item in transitions
        if item.action_id in legal
        and (condition.schema_id in item.predecessor_features) == condition.present
    )
    return [
        {
            "action": action,
            "child_support": child[action],
            "parent_support": parent[action],
        }
        for action in sorted(parent, key=lambda action: (-child[action], -parent[action], action))
    ]


def _predict_delta(transitions: list[Any], action_id: int) -> tuple[str, int, int, float]:
    matching = [item for item in transitions if item.action_id == action_id]
    if not matching:
        raise RuntimeError("selected action has no predecessor-visible successor evidence")
    counts = Counter(
        "changed" if item.structural_change else "preserved" for item in matching
    )
    prediction, support = min(counts.items(), key=lambda item: (-item[1], item[0]))
    return prediction, support, len(matching), support / len(matching)


def _install_parent(runtime: Runtime) -> int:
    parent, _created = runtime.graph.add_schema(
        "AmbiguousTransitionParent",
        [
            ("Domain", ("?before",)),
            ("Codomain", ("?after",)),
            ("Intervention", ("?action",)),
            ("Before", ("?before", "ActiveSchema", "?predecessor_schema")),
            ("After", ("?after", "ActiveSchema", "?successor_schema")),
        ],
        provenance="experiment:25-game-context-spinoff",
    )
    return parent


def _install_child(runtime: Runtime, parent: int, condition: Any) -> tuple[int, bool, int]:
    parent_atoms = runtime.graph.source_atoms(parent)
    variables = sorted(
        {
            argument
            for _head, arguments in parent_atoms
            for argument in arguments
            if isinstance(argument, str) and argument.startswith("?v")
        },
        key=lambda value: int(value[2:]),
    )
    domain_variable = next(arguments[0] for head, arguments in parent_atoms if head == "Domain")
    polarity = "BindingPresent" if condition.present else "BindingAbsent"
    child, created = runtime.graph.add_dag_schema(
        "ContextSpecializedTransitionChild",
        variables,
        [(parent, {int(variable[2:]): variable for variable in variables})],
        [
            (
                "Before",
                (
                    domain_variable,
                    polarity,
                    runtime.graph.canonical_hash[condition.schema_id],
                ),
            )
        ],
        provenance="endogenous:context-spinoff",
    )
    edge = next(
        (
            edge_id
            for edge_id in runtime.graph.out_index[parent]
            if runtime.graph.terms.value(runtime.graph.relation[edge_id]) == "spinoff"
            and runtime.graph.dst[edge_id] == child
        ),
        None,
    )
    if edge is None:
        edge = runtime.graph.add_link(
            parent,
            "spinoff",
            child,
            1.0,
            provenance="endogenous:context-spinoff",
        )
    if created:
        for index in range(condition.support):
            runtime.graph.add_evidence(
                child,
                "support",
                1,
                f"preceding-context:{index}",
                runtime.cycle,
                source="experience:context-separation",
            )
    return child, created, edge


def _schema_record(runtime: Runtime, schema_id: int) -> dict[str, Any]:
    return {
        "hash": runtime.graph.canonical_hash[schema_id],
        "atoms": [
            [head, list(arguments)]
            for head, arguments in runtime.graph.source_atoms(schema_id)
        ],
    }


def _action_requires_data(action_id: int) -> bool:
    return action_id == 6


def _branch(
    *,
    runtime: Runtime,
    schema_id: int,
    expected_delta: str,
    prediction_context: str,
    environments_root: Path,
    recordings_root: Path,
    game: str,
    prefix: list[Any],
    action_id: int,
    predecessor_hash: str,
    predecessor_features: frozenset[int],
) -> dict[str, Any]:
    if _action_requires_data(action_id):
        raise ValueError("action-data-required")
    branch_runtime = copy.deepcopy(runtime)
    expected = branch_runtime.graph.terms.ground_atom(
        "StructuralDelta", (expected_delta,)
    )
    prediction_id = branch_runtime.predict(schema_id, expected, prediction_context)
    arcade, environment = SHARED._open_arcade(
        environments_root, recordings_root, game
    )
    try:
        for recorded in prefix:
            SHARED._act(environment, game, recorded, "chronological-state-reconstruction")
        before = SHARED._frame(environment.observation_space)
        actual_predecessor_hash = SHARED._frame_hash(before)
        if actual_predecessor_hash != predecessor_hash:
            raise RuntimeError(
                f"predecessor-replay-mismatch:{actual_predecessor_hash}:{predecessor_hash}"
            )
        level_before = int(environment.observation_space.levels_completed)
        SHARED._act(
            environment,
            game,
            RecordedAction(action_id, {}),
            "prospective-ranked-action",
        )
        successor = SHARED._frame(environment.observation_space)
        level_after = int(environment.observation_space.levels_completed)
        after_batch, after_features = _observe(
            branch_runtime, successor, f"{prediction_context}:successor"
        )
        observed_delta = (
            "changed" if predecessor_features != after_features else "preserved"
        )
        resolution = PerceptionBatch(
            after_batch.context,
            after_batch.facts
            + ((expected,) if expected_delta == observed_delta else ()),
            after_batch.form_terms,
            after_batch.region_terms,
            after_batch.outline_terms,
            after_batch.source,
        )
        reified = branch_runtime.resolve_prediction(prediction_id, resolution)
        return {
            "action": action_id,
            "predecessor_frame_sha256": actual_predecessor_hash,
            "successor_frame_sha256": SHARED._frame_hash(successor),
            "level_before": level_before,
            "level_after": level_after,
            "level_delta": level_after - level_before,
            "score_delta": None,
            "predicted_structural_delta": expected_delta,
            "observed_structural_delta": observed_delta,
            "prediction_reified": reified,
            "changed_cells": sum(
                left != right
                for before_row, after_row in zip(before, successor, strict=True)
                for left, right in zip(before_row, after_row, strict=True)
            ),
        }
    finally:
        arcade.close_scorecard()


def _classify(treatment: dict[str, Any], control: dict[str, Any]) -> str:
    if treatment["level_delta"] > control["level_delta"]:
        return "improve"
    if treatment["level_delta"] < control["level_delta"]:
        return "worsen"
    if treatment["prediction_reified"] and not control["prediction_reified"]:
        return "improve"
    if control["prediction_reified"] and not treatment["prediction_reified"]:
        return "worsen"
    return "tie"


def _context_name(runtime: Runtime, schema_id: int) -> str:
    atoms = runtime.graph.source_atoms(schema_id)
    return str(atoms[0][0]) if len(atoms) == 1 else ""


def _evaluate_game(job: dict[str, Any]) -> dict[str, Any]:
    started_wall = time.perf_counter()
    started_cpu = time.process_time()
    config = DiagnosticConfig(**job["config"])
    game = str(job["game"])
    recording = Path(job["recording"])
    environments_root = Path(job["environments_root"])
    branch_recordings = Path(job["branch_recordings"])
    runtime = _new_runtime(config.seed)
    initial_schema_count = runtime.graph.schema_count
    initial_kernel_fingerprint = _kernel_fingerprint(runtime)
    parent = _install_parent(runtime)
    parent_atoms_frozen = runtime.graph.source_atoms(parent)
    parent_hash = runtime.graph.canonical_hash[parent]
    trace: list[dict[str, Any]] = [
        {
            "event": "game-start",
            "game": game,
            "recording_sha256": SHARED._file_hash(recording),
            "initial_schema_count": initial_schema_count,
            "kernel_fingerprint": initial_kernel_fingerprint,
            "parent": parent_hash,
        }
    ]
    transitions: list[Any] = []
    opportunities: list[dict[str, Any]] = []
    prefix: list[Any] = []
    abstentions: Counter[str] = Counter()
    context_recurrence: Counter[str] = Counter()
    unique_children: set[str] = set()
    executed_changes = 0
    packets_seen = 0
    previous_packet: Packet | None = None
    previous_features: frozenset[int] | None = None
    max_packets = job.get("max_packets")

    for packet in _packets(recording):
        if max_packets is not None and packets_seen >= int(max_packets):
            break
        packets_seen += 1
        if previous_packet is None:
            _batch, previous_features = _observe(
                runtime, packet.frame, f"observation:{packet.index}"
            )
            previous_packet = packet
            prefix.append(packet.action)
            continue
        assert previous_features is not None
        legal_actions = previous_packet.available_actions
        baseline_ranking = _rank_parent(transitions, legal_actions)
        condition, eligibility = _discover_context(
            runtime,
            transitions,
            previous_features,
            legal_actions,
            config,
        )
        if condition is None:
            abstentions[eligibility] += 1
        else:
            child, created, edge = _install_child(runtime, parent, condition)
            child_hash = runtime.graph.canonical_hash[child]
            context_hash = runtime.graph.canonical_hash[condition.schema_id]
            context_recurrence[context_hash] += 1
            if created:
                unique_children.add(child_hash)
            treatment_ranking = _rank_child(
                transitions, condition, legal_actions
            )
            baseline_action = int(baseline_ranking[0]["action"])
            treatment_action = int(treatment_ranking[0]["action"])
            changed_top = baseline_action != treatment_action
            opportunity_id = f"{game}:{packet.index}:{child_hash[:12]}"
            opportunity: dict[str, Any] = {
                "opportunity_id": opportunity_id,
                "game": game,
                "transition_index": packet.index,
                "predecessor_frame_sha256": previous_packet.frame_sha256,
                "parent_hash": parent_hash,
                "child_hash": child_hash,
                "child_created": created,
                "spinoff_edge": edge,
                "context_schema_hash": context_hash,
                "context_relation": _context_name(runtime, condition.schema_id),
                "context_polarity": "present" if condition.present else "absent",
                "context_support": condition.support,
                "context_purity": condition.purity,
                "baseline_ranking": baseline_ranking,
                "treatment_ranking": treatment_ranking,
                "baseline_top": baseline_action,
                "treatment_top": treatment_action,
                "top_action_changed": changed_top,
                "held_out_recorded_action": packet.action.action_id,
                "executed": False,
                "classification": None,
                "abstention_reason": None,
            }
            trace.extend(
                [
                    {
                        "event": "ambiguity",
                        "opportunity_id": opportunity_id,
                        "parent": parent_hash,
                        "baseline_ranking": baseline_ranking,
                    },
                    {
                        "event": "context-discovered",
                        "opportunity_id": opportunity_id,
                        "schema": context_hash,
                        "relation": opportunity["context_relation"],
                        "polarity": opportunity["context_polarity"],
                        "support": condition.support,
                        "purity": condition.purity,
                    },
                    {
                        "event": "schema-spinoff",
                        "opportunity_id": opportunity_id,
                        "parent": parent_hash,
                        "child": child_hash,
                        "created": created,
                        "edge": edge,
                    },
                ]
            )
            if changed_top:
                trace.append(
                    {
                        "event": "action-ranking-changed",
                        "opportunity_id": opportunity_id,
                        "baseline_top": baseline_action,
                        "treatment_top": treatment_action,
                    }
                )
                reason: str | None = None
                if executed_changes >= config.max_action_changes_per_game:
                    reason = "branch-budget"
                elif _action_requires_data(baseline_action) or _action_requires_data(
                    treatment_action
                ):
                    reason = "action-data-required"
                if reason is not None:
                    opportunity["abstention_reason"] = reason
                    abstentions[reason] += 1
                else:
                    child_transitions = _matching_context_transitions(
                        transitions, condition, legal_actions
                    )
                    child_prediction = _predict_delta(
                        child_transitions, treatment_action
                    )
                    parent_prediction = _predict_delta(
                        transitions, baseline_action
                    )
                    opportunity["child_prediction"] = {
                        "delta": child_prediction[0],
                        "support": child_prediction[1],
                        "total": child_prediction[2],
                        "confidence": child_prediction[3],
                    }
                    opportunity["parent_prediction"] = {
                        "delta": parent_prediction[0],
                        "support": parent_prediction[1],
                        "total": parent_prediction[2],
                        "confidence": parent_prediction[3],
                    }
                    trace.append(
                        {
                            "event": "prospective-predictions-emitted",
                            "opportunity_id": opportunity_id,
                            "control": opportunity["parent_prediction"],
                            "treatment": opportunity["child_prediction"],
                        }
                    )
                    try:
                        control = _branch(
                            runtime=runtime,
                            schema_id=parent,
                            expected_delta=parent_prediction[0],
                            prediction_context=f"opportunity:{packet.index}:control",
                            environments_root=environments_root,
                            recordings_root=branch_recordings / "control",
                            game=game,
                            prefix=prefix,
                            action_id=baseline_action,
                            predecessor_hash=previous_packet.frame_sha256,
                            predecessor_features=previous_features,
                        )
                        treatment = _branch(
                            runtime=runtime,
                            schema_id=child,
                            expected_delta=child_prediction[0],
                            prediction_context=f"opportunity:{packet.index}:treatment",
                            environments_root=environments_root,
                            recordings_root=branch_recordings / "treatment",
                            game=game,
                            prefix=prefix,
                            action_id=treatment_action,
                            predecessor_hash=previous_packet.frame_sha256,
                            predecessor_features=previous_features,
                        )
                    except (RuntimeError, ValueError) as error:
                        reason = str(error).split(":", 1)[0]
                        opportunity["abstention_reason"] = reason
                        abstentions[reason] += 1
                    else:
                        if (
                            control["predecessor_frame_sha256"]
                            != treatment["predecessor_frame_sha256"]
                        ):
                            raise RuntimeError("matched branches do not share a predecessor")
                        classification = _classify(treatment, control)
                        opportunity.update(
                            {
                                "executed": True,
                                "classification": classification,
                                "control": control,
                                "treatment": treatment,
                                "completed_level_delta_vs_control": (
                                    treatment["level_delta"] - control["level_delta"]
                                ),
                                "score_delta_vs_control": None,
                            }
                        )
                        executed_changes += 1
                        trace.extend(
                            [
                                {
                                    "event": "prediction-resolution",
                                    "opportunity_id": opportunity_id,
                                    "control_reified": control["prediction_reified"],
                                    "treatment_reified": treatment["prediction_reified"],
                                },
                                {
                                    "event": "prospective-outcome",
                                    "opportunity_id": opportunity_id,
                                    "classification": classification,
                                    "control": control,
                                    "treatment": treatment,
                                },
                            ]
                        )
            opportunities.append(opportunity)

        successor_batch, successor_features = _observe(
            runtime, packet.frame, f"observation:{packet.index}"
        )
        del successor_batch
        transition = Transition(
            packet.index,
            packet.action.action_id,
            previous_features,
            successor_features,
        )
        transitions.append(transition)
        runtime.graph.add_evidence(
            parent,
            "support",
            1,
            f"chronological-transition:{packet.index}",
            runtime.cycle,
            source="experience:transition",
        )
        prefix.append(packet.action)
        previous_packet = packet
        previous_features = successor_features

    parent_intact = runtime.graph.source_atoms(parent) == parent_atoms_frozen
    if not parent_intact:
        raise RuntimeError("parent schema mutated during spinoff")
    outcome_counts = Counter(
        item["classification"] for item in opportunities if item["executed"]
    )
    top_changes = sum(bool(item["top_action_changed"]) for item in opportunities)
    child_reified = sum(
        bool(item["treatment"]["prediction_reified"])
        for item in opportunities
        if item["executed"]
    )
    parent_reified = sum(
        bool(item["control"]["prediction_reified"])
        for item in opportunities
        if item["executed"]
    )
    level_delta = sum(
        int(item["completed_level_delta_vs_control"])
        for item in opportunities
        if item["executed"]
    )
    deterministic = {
        "game": game,
        "recording": str(recording),
        "recording_sha256": SHARED._file_hash(recording),
        "packets": packets_seen,
        "chronological_transitions": len(transitions),
        "initial_schema_count": initial_schema_count,
        "initial_kernel_fingerprint": initial_kernel_fingerprint,
        "final_schema_count": runtime.graph.schema_count,
        "parent": _schema_record(runtime, parent),
        "parent_intact": parent_intact,
        "opportunities": len(opportunities),
        "spinoffs_created": len(unique_children),
        "top_action_changes": top_changes,
        "executed_action_changes": executed_changes,
        "improve": outcome_counts["improve"],
        "tie": outcome_counts["tie"],
        "worsen": outcome_counts["worsen"],
        "completed_level_delta_vs_control": level_delta,
        "score_delta_vs_control": None,
        "prediction": {
            "child_reified": child_reified,
            "child_refuted": executed_changes - child_reified,
            "parent_reified": parent_reified,
            "parent_refuted": executed_changes - parent_reified,
        },
        "abstentions": dict(sorted(abstentions.items())),
        "contexts": dict(sorted(context_recurrence.items())),
        "opportunity_records": opportunities,
        "trace": trace
        + [
            {
                "event": "game-end",
                "game": game,
                "opportunities": len(opportunities),
                "top_action_changes": top_changes,
                "executed_action_changes": executed_changes,
            }
        ],
    }
    result = {
        "deterministic": deterministic,
        "timing": {
            "game": game,
            "wall_seconds": time.perf_counter() - started_wall,
            "cpu_seconds": time.process_time() - started_cpu,
        },
    }
    if job.get("checkpoint") is not None:
        _atomic_json(
            Path(job["checkpoint"]),
            {
                "checkpoint_format": CHECKPOINT_FORMAT,
                "key": _checkpoint_key(job),
                "completed_at": _utc_now(),
                "result": result,
            },
        )
    return result


def _identity_worker(value: int) -> dict[str, Any]:
    runtime = _new_runtime(0)
    initial = runtime.graph.schema_count
    runtime.graph.add_schema(
        "IsolationProbe",
        [("Probe", (f"job-{value}",))],
        candidate=False,
        provenance="test:worker-isolation",
    )
    return {
        "value": value,
        "initial_schema_count": initial,
        "final_schema_count": runtime.graph.schema_count,
        "kernel": _kernel_fingerprint(runtime),
    }


def _ordered_process_map(
    worker: Callable[[Any], Any], jobs: list[Any], workers: int
) -> list[Any]:
    if workers == 1:
        return [worker(job) for job in jobs]
    context = mp.get_context("fork")
    output: list[Any | None] = [None] * len(jobs)
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as executor:
        pending = {
            executor.submit(worker, job): index for index, job in enumerate(jobs)
        }
        for future in as_completed(pending):
            output[pending[future]] = future.result()
    return [item for item in output if item is not None]


def _cohort_files(root: Path) -> list[tuple[str, Path]]:
    files = sorted(root.glob("*/*.recording.jsonl"), key=lambda path: path.parent.name)
    pairs = [(path.parent.name, path) for path in files]
    if len(pairs) != EXPECTED_GAMES or len({game for game, _path in pairs}) != EXPECTED_GAMES:
        raise RuntimeError(
            f"expected {EXPECTED_GAMES} unique games, found {len(pairs)}"
        )
    return pairs


def _mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _aggregate(
    game_results: list[dict[str, Any]], config: DiagnosticConfig
) -> dict[str, Any]:
    games = [item["deterministic"] for item in game_results]
    all_opportunities = [
        opportunity
        for game in games
        for opportunity in game["opportunity_records"]
    ]
    executed = [item for item in all_opportunities if item["executed"]]
    changes = [item for item in all_opportunities if item["top_action_changed"]]
    outcome_counts = Counter(item["classification"] for item in executed)
    contexts_to_games: dict[str, set[str]] = defaultdict(set)
    context_polarity = Counter()
    context_occurrences = Counter()
    for item in all_opportunities:
        context = item["context_schema_hash"]
        contexts_to_games[context].add(item["game"])
        context_polarity[item["context_polarity"]] += 1
        context_occurrences[context] += 1
    per_game_child_accuracy = [
        game["prediction"]["child_reified"] / game["executed_action_changes"]
        for game in games
        if game["executed_action_changes"]
    ]
    child_confidences = [
        float(item["child_prediction"]["confidence"]) for item in executed
    ]
    parent_confidences = [
        float(item["parent_prediction"]["confidence"]) for item in executed
    ]
    executed_count = len(executed)
    child_reified = sum(bool(item["treatment"]["prediction_reified"]) for item in executed)
    parent_reified = sum(bool(item["control"]["prediction_reified"]) for item in executed)
    opportunity_by_game = Counter(item["game"] for item in all_opportunities)
    changes_by_game = Counter(item["game"] for item in changes)
    completed_delta = sum(
        int(item["completed_level_delta_vs_control"]) for item in executed
    )
    independent_change_games = sum(game["executed_action_changes"] > 0 for game in games)
    precision = outcome_counts["improve"] / executed_count if executed_count else None
    false_rate = outcome_counts["worsen"] / executed_count if executed_count else None
    if (
        independent_change_games >= 3
        and precision is not None
        and precision >= 0.60
        and completed_delta > 0
        and false_rate is not None
        and false_rate <= 0.15
    ):
        verdict = "PROMOTE"
    elif (
        executed_count >= 10
        and (
            (precision is not None and precision < 0.35)
            or (false_rate is not None and false_rate > 0.40)
        )
    ):
        verdict = "REJECT"
    else:
        verdict = "CONTINUE-DIAGNOSTIC"

    ar25 = next(game for game in games if game["game"] == "ar25")
    ar25_matches = [
        item
        for item in ar25["opportunity_records"]
        if item["context_schema_hash"] == FROZEN_AR25["context_hash"]
        and item["parent_hash"] == FROZEN_AR25["parent_hash"]
        and item["child_hash"] == FROZEN_AR25["child_hash"]
        and item["baseline_top"] == FROZEN_AR25["baseline_action"]
        and item["treatment_top"] == FROZEN_AR25["treatment_action"]
        and item["executed"]
        and item["control"]["level_delta"] == 0
        and item["treatment"]["level_delta"] == 1
    ]
    repeated_cross_game = {
        context: sorted(game_set)
        for context, game_set in sorted(contexts_to_games.items())
        if len(game_set) >= 2
    }
    accidental = sorted(
        {
            item["context_schema_hash"]
            for item in all_opportunities
            if item["context_support"] == config.min_context_support
            and len(contexts_to_games[item["context_schema_hash"]]) == 1
        }
    )
    summary = {
        "experiment": "r2-25-game-context-spinoff-diagnostic",
        "cohort": {
            "games_total": len(games),
            "games": [game["game"] for game in games],
            "recording_set_sha256": _stable_hash(
                [[game["game"], game["recording_sha256"]] for game in games]
            ),
        },
        "configuration": asdict(config),
        "primary_metric": {
            "name": "action-changing precision",
            "definition": (
                "improve / executed matched top-action changes; compare level delta first, "
                "then treatment-only versus control-only prospective structural prediction correctness"
            ),
            "value": precision,
        },
        "aggregate": {
            "games_with_eligible_spinoff": sum(game["opportunities"] > 0 for game in games),
            "games_without_eligible_relational_context": [
                game["game"] for game in games if game["opportunities"] == 0
            ],
            "opportunities": len(all_opportunities),
            "spinoffs_created": sum(game["spinoffs_created"] for game in games),
            "top_action_changes": len(changes),
            "executed_action_changes": executed_count,
            "action_changes_improve": outcome_counts["improve"],
            "action_changes_tie": outcome_counts["tie"],
            "action_changes_worsen": outcome_counts["worsen"],
            "completed_level_delta_vs_control": completed_delta,
            "progress_delta_vs_control": completed_delta,
            "score_delta_vs_control": None,
            "score_delta_note": "per-step score is not exposed by the offline observation API",
            "false_spinoff_rate": false_rate,
            "prediction": {
                "child_reified": child_reified,
                "child_refuted": executed_count - child_reified,
                "parent_reified": parent_reified,
                "parent_refuted": executed_count - parent_reified,
            },
            "abstentions": dict(
                sorted(
                    sum(
                        (Counter(game["abstentions"]) for game in games),
                        Counter(),
                    ).items()
                )
            ),
        },
        "calibration": {
            "child_mean_confidence": _mean(child_confidences),
            "child_empirical_reification": (
                child_reified / executed_count if executed_count else None
            ),
            "parent_mean_confidence": _mean(parent_confidences),
            "parent_empirical_reification": (
                parent_reified / executed_count if executed_count else None
            ),
        },
        "accuracy": {
            "forward_transition_micro": (
                child_reified / executed_count if executed_count else None
            ),
            "forward_game_macro": _mean(per_game_child_accuracy),
            "inverse_transition_micro": None,
            "inverse_game_macro": None,
            "inverse_note": "not applicable: the mechanism has no inverse action decoder",
        },
        "concentration": {
            "max_game_opportunity_fraction": (
                max(opportunity_by_game.values(), default=0) / len(all_opportunities)
                if all_opportunities
                else None
            ),
            "max_game_action_change_fraction": (
                max(changes_by_game.values(), default=0) / len(changes)
                if changes
                else None
            ),
            "opportunities_by_game": dict(sorted(opportunity_by_game.items())),
            "action_changes_by_game": dict(sorted(changes_by_game.items())),
        },
        "contexts": {
            "polarity_counts": dict(sorted(context_polarity.items())),
            "absence_fraction": (
                context_polarity["absent"] / len(all_opportunities)
                if all_opportunities
                else None
            ),
            "unique_schema_hashes": len(contexts_to_games),
            "occurrences_by_hash": dict(sorted(context_occurrences.items())),
            "repeated_across_games": repeated_cross_game,
            "support_two_single_game_possible_overfit": accidental,
        },
        "negative_results": {
            "worsened_opportunity_ids": [
                item["opportunity_id"] for item in executed if item["classification"] == "worsen"
            ],
            "games_without_eligible_context": [
                game["game"] for game in games if game["opportunities"] == 0
            ],
            "absence_conditions_dominate": context_polarity["absent"] > context_polarity["present"],
        },
        "frozen_ar25_sanity": {
            "passed": bool(ar25_matches),
            "matching_opportunity_ids": [item["opportunity_id"] for item in ar25_matches],
            "expected": FROZEN_AR25,
        },
        "per_game": [
            {key: value for key, value in game.items() if key not in {"trace", "opportunity_records"}}
            for game in games
        ],
        "verdict": verdict,
        "promotion_gate_note": "prediction accuracy alone cannot produce PROMOTE",
    }
    return summary


def _write_outputs(
    output: Path,
    game_results: list[dict[str, Any]],
    summary: dict[str, Any],
    execution: dict[str, Any],
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    traces = output / "traces"
    traces.mkdir(parents=True, exist_ok=True)
    games = [item["deterministic"] for item in game_results]
    for game in games:
        (traces / f"{game['game']}.json").write_text(
            json.dumps(game["trace"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    opportunities = [
        item
        for game in games
        for item in game["opportunity_records"]
    ]
    with (output / "opportunities.jsonl").open("w", encoding="utf-8") as handle:
        for item in opportunities:
            handle.write(json.dumps(item, sort_keys=True) + "\n")
    csv_fields = [
        "opportunity_id",
        "game",
        "transition_index",
        "context_schema_hash",
        "context_relation",
        "context_polarity",
        "context_support",
        "context_purity",
        "child_created",
        "baseline_top",
        "treatment_top",
        "top_action_changed",
        "executed",
        "classification",
        "abstention_reason",
        "completed_level_delta_vs_control",
    ]
    with (output / "opportunities.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(opportunities)
    (output / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "execution.json").write_text(
        json.dumps(execution, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "config.json").write_text(
        json.dumps(
            {
                "algorithm": summary["configuration"],
                "cohort": summary["cohort"],
                "outcome_order": [
                    "completed-level delta",
                    "prospective structural prediction correctness",
                    "tie",
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    config = DiagnosticConfig(seed=args.seed)
    cohort = _cohort_files(args.cohort)
    workers = args.workers or min(len(cohort), os.cpu_count() or 1)
    args.output.mkdir(parents=True, exist_ok=True)
    checkpoints = args.output / "checkpoints"
    jobs = [
        {
            "game": game,
            "recording": str(path),
            "environments_root": str(args.environments),
            "branch_recordings": str(args.output / "branch-recordings" / game),
            "config": asdict(config),
            "checkpoint": str(checkpoints / f"{game}.json"),
        }
        for game, path in cohort
    ]
    manifest_path = args.output / "run-manifest.json"
    now_epoch = time.time()
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {
            "protocol_version": PROTOCOL_VERSION,
            "first_started_at": _utc_now(),
            "first_started_epoch": now_epoch,
            "attempts": [],
        }
    cached_by_game: dict[str, dict[str, Any]] = {}
    pending_jobs: list[dict[str, Any]] = []
    for job in jobs:
        cached = _load_checkpoint(job) if args.resume else None
        if cached is None:
            pending_jobs.append(job)
        else:
            cached_by_game[str(job["game"])] = cached
    attempt = {
        "started_at": _utc_now(),
        "started_epoch": now_epoch,
        "workers": workers,
        "cached_games": sorted(cached_by_game),
        "pending_games": [str(job["game"]) for job in pending_jobs],
    }
    manifest["attempts"].append(attempt)
    _atomic_json(manifest_path, manifest)
    wall_start = time.perf_counter()
    computed_results = _ordered_process_map(_evaluate_game, pending_jobs, workers)
    wall_seconds = time.perf_counter() - wall_start
    computed_by_game = {
        str(item["deterministic"]["game"]): item for item in computed_results
    }
    game_results = [
        cached_by_game.get(str(job["game"]))
        or computed_by_game[str(job["game"])]
        for job in jobs
    ]
    summary = _aggregate(game_results, config)
    timings = [item["timing"] for item in game_results]
    total_cpu = sum(float(item["cpu_seconds"]) for item in timings)
    finished_epoch = time.time()
    attempt.update(
        {
            "finished_at": _utc_now(),
            "finished_epoch": finished_epoch,
            "wall_seconds": wall_seconds,
            "computed_games": sorted(computed_by_game),
        }
    )
    manifest["completed_at"] = attempt["finished_at"]
    manifest["completed_epoch"] = finished_epoch
    _atomic_json(manifest_path, manifest)
    end_to_end_wall = finished_epoch - float(manifest["first_started_epoch"])
    execution = {
        "workers": workers,
        "seed": config.seed,
        "resume_enabled": args.resume,
        "cached_games_this_attempt": sorted(cached_by_game),
        "computed_games_this_attempt": sorted(computed_by_game),
        "this_attempt_wall_seconds": wall_seconds,
        "end_to_end_wall_seconds_including_interrupted_attempts_and_downtime": end_to_end_wall,
        "sum_worker_cpu_seconds": total_cpu,
        "cpu_utilization_fraction_of_capacity": (
            total_cpu / (end_to_end_wall * workers)
            if end_to_end_wall and workers
            else None
        ),
        "cpu_utilization_note": (
            "capacity denominator includes interrupted attempts and downtime; "
            "per-game CPU and wall timings are authoritative"
        ),
        "per_game": timings,
    }
    _write_outputs(args.output, game_results, summary, execution)
    return {"summary": summary, "execution": execution}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cohort", type=Path, default=COHORT_ROOT)
    parser.add_argument("--environments", type=Path, default=ENVIRONMENTS_ROOT)
    parser.add_argument("--output", type=Path, default=HERE)
    parser.add_argument("--workers", type=int, default=0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="reuse valid atomic per-game checkpoints (default: enabled)",
    )
    return parser


def main() -> None:
    result = run(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
