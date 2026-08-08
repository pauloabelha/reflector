"""Minimal real-game test of bounded context-conditioned schema spinoff.

The runner has no game-specific policy branch.  The game and recording are
experimental inputs; action tokens remain opaque and context candidates are
restricted to current R2 Binding records for generic binary relation schemas.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from reflector2.perception import PerceptionBatch, perceive_grid
from reflector2.runtime import Runtime, Workspace
from reflector2.store import SCHEMA_ESTABLISHED, VARIABLE


DEFAULT_ENVIRONMENTS = Path(
    "/home/pauloabelha/arc-agi-3-public-games-2026/environment_files"
)
DEFAULT_RECORDING = Path(
    "/home/pauloabelha/reflector-v164-pivot-goal/reports/"
    "v164-public-r1-recordings/ar25/"
    "ar25.reflectoragent.7c920744-1244-4c2d-bd8c-43c74f252adb.recording.jsonl"
)
MAX_CONTEXT_CANDIDATES = 64
MIN_CONTEXT_SUPPORT = 2


@dataclass(frozen=True)
class RecordedAction:
    action_id: int
    data: dict[str, int]


@dataclass(frozen=True)
class Transition:
    index: int
    action_id: int
    predecessor_features: frozenset[int]
    successor_features: frozenset[int]

    @property
    def structural_change(self) -> bool:
        return self.predecessor_features != self.successor_features


@dataclass(frozen=True)
class ContextCondition:
    schema_id: int
    present: bool
    support: int
    purity: float
    action_id: int


def _frame(observation: Any) -> tuple[tuple[int, ...], ...]:
    value = observation.frame.tolist() if hasattr(observation.frame, "tolist") else observation.frame
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


def _frame_hash(frame: tuple[tuple[int, ...], ...]) -> str:
    return hashlib.sha256(repr(frame).encode("utf-8")).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _recorded_first_level(recording: Path) -> list[RecordedAction]:
    actions: list[RecordedAction] = []
    for line in recording.read_text(encoding="utf-8").splitlines():
        packet = json.loads(line)["data"]
        action = packet["action_input"]
        data = {
            str(key): int(value)
            for key, value in action.get("data", {}).items()
            if key != "game_id"
        }
        actions.append(RecordedAction(int(action["id"]), data))
        if int(packet["levels_completed"]) > 0:
            break
    if len(actions) < 2:
        raise RuntimeError("recording does not contain a holdable first-level transition")
    return actions


def _act(environment: Any, game: str, recorded: RecordedAction, reason: str) -> None:
    from arcengine import GameAction

    action = GameAction.from_id(recorded.action_id)
    if recorded.data:
        action.set_data(recorded.data)
    environment.step(
        action,
        data={**recorded.data, "game_id": game},
        reasoning={"experiment": "prospective-context-spinoff-control", "reason": reason},
    )


def _open_arcade(environments: Path, recordings: Path, game: str) -> tuple[Any, Any]:
    from arc_agi import Arcade, OperationMode

    arcade = Arcade(
        operation_mode=OperationMode.OFFLINE,
        environments_dir=str(environments),
        recordings_dir=str(recordings),
    )
    environment = arcade.make(game, include_frame_data=True)
    if environment is None:
        arcade.close_scorecard()
        raise RuntimeError(f"could not open game: {game}")
    return arcade, environment


def _observe(runtime: Runtime, frame: tuple[tuple[int, ...], ...], context: str) -> tuple[PerceptionBatch, Workspace, frozenset[int]]:
    batch = perceive_grid(runtime.graph.terms, frame, context)
    workspace = runtime.observe(batch)
    return batch, workspace, frozenset(binding.schema_id for binding in workspace.bindings)


def _rank_parent(transitions: Iterable[Transition]) -> list[dict[str, int]]:
    counts = Counter(transition.action_id for transition in transitions)
    return [
        {"action": action, "parent_support": support}
        for action, support in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    ]


def _rank_child(
    transitions: list[Transition], condition: ContextCondition
) -> list[dict[str, int]]:
    parent = Counter(transition.action_id for transition in transitions)
    selected = [
        transition
        for transition in transitions
        if (condition.schema_id in transition.predecessor_features) == condition.present
    ]
    child = Counter(transition.action_id for transition in selected)
    return [
        {
            "action": action,
            "child_support": child[action],
            "parent_support": parent[action],
        }
        for action in sorted(parent, key=lambda action: (-child[action], -parent[action], action))
    ]


def _predict_structural_delta(
    transitions: list[Transition], condition: ContextCondition, action_id: int
) -> tuple[str, int]:
    matching = [
        transition
        for transition in transitions
        if transition.action_id == action_id
        and (condition.schema_id in transition.predecessor_features) == condition.present
    ]
    if not matching:
        raise RuntimeError("context child has no successor evidence for its top action")
    counts = Counter(
        "changed" if transition.structural_change else "preserved"
        for transition in matching
    )
    prediction, support = min(counts.items(), key=lambda item: (-item[1], item[0]))
    return prediction, support


def _binary_relation_candidates(runtime: Runtime) -> list[int]:
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
    return sorted(output, key=lambda schema_id: runtime.graph.canonical_hash[schema_id])[
        :MAX_CONTEXT_CANDIDATES
    ]


def _discover_context(
    runtime: Runtime,
    transitions: list[Transition],
    current_features: frozenset[int],
) -> ContextCondition:
    parent_counts = Counter(transition.action_id for transition in transitions)
    parent_purity = max(parent_counts.values()) / len(transitions)
    candidates: list[ContextCondition] = []
    for schema_id in _binary_relation_candidates(runtime):
        present = schema_id in current_features
        matching = [
            transition
            for transition in transitions
            if (schema_id in transition.predecessor_features) == present
        ]
        if len(matching) < MIN_CONTEXT_SUPPORT:
            continue
        counts = Counter(transition.action_id for transition in matching)
        action_id, action_support = min(
            counts.items(), key=lambda item: (-item[1], item[0])
        )
        purity = action_support / len(matching)
        if purity <= parent_purity:
            continue
        candidates.append(
            ContextCondition(schema_id, present, len(matching), purity, action_id)
        )
    if not candidates:
        raise RuntimeError("no bounded predecessor context improves parent action purity")
    return min(
        candidates,
        key=lambda item: (
            -item.purity,
            -item.support,
            runtime.graph.canonical_hash[item.schema_id],
        ),
    )


def _install_parent(runtime: Runtime, transitions: list[Transition]) -> int:
    atoms = [
        ("Domain", ("?before",)),
        ("Codomain", ("?after",)),
        ("Intervention", ("?action",)),
        ("Before", ("?before", "ActiveSchema", "?predecessor_schema")),
        ("After", ("?after", "ActiveSchema", "?successor_schema")),
    ]
    parent, _created = runtime.graph.add_schema(
        "AmbiguousTransitionParent",
        atoms,
        provenance="experiment:prospective-context-spinoff",
    )
    for transition in transitions:
        runtime.graph.add_evidence(
            parent,
            "support",
            1,
            f"training-transition:{transition.index}",
            runtime.cycle,
            source="experience:transition",
        )
    return parent


def _install_child(
    runtime: Runtime, parent: int, condition: ContextCondition
) -> tuple[int, int]:
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
    domain_variable = next(
        arguments[0] for head, arguments in parent_atoms if head == "Domain"
    )
    polarity = "BindingPresent" if condition.present else "BindingAbsent"
    child, _created = runtime.graph.add_dag_schema(
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
    link = runtime.graph.add_link(
        parent,
        "spinoff",
        child,
        1.0,
        provenance="endogenous:context-spinoff",
    )
    for index in range(condition.support):
        runtime.graph.add_evidence(
            child,
            "support",
            1,
            f"context-support:{index}",
            runtime.cycle,
            source="experience:context-separation",
        )
    return child, link


def _schema_record(runtime: Runtime, schema_id: int) -> dict[str, Any]:
    return {
        "id": schema_id,
        "hash": runtime.graph.canonical_hash[schema_id],
        "atoms": [
            [head, list(arguments)]
            for head, arguments in runtime.graph.source_atoms(schema_id)
        ],
    }


def _run_control(
    environments: Path,
    recordings: Path,
    game: str,
    prefix: list[RecordedAction],
    action_id: int,
) -> dict[str, Any]:
    arcade, environment = _open_arcade(environments, recordings, game)
    try:
        for recorded in prefix:
            _act(environment, game, recorded, "control-state-reconstruction")
        before = _frame(environment.observation_space)
        level_before = int(environment.observation_space.levels_completed)
        _act(environment, game, RecordedAction(action_id, {}), "parent-only-top-rank")
        after = _frame(environment.observation_space)
        level_after = int(environment.observation_space.levels_completed)
        return {
            "action": action_id,
            "level_before": level_before,
            "level_after": level_after,
            "level_delta": level_after - level_before,
            "changed_cells": sum(
                left != right
                for before_row, after_row in zip(before, after, strict=True)
                for left, right in zip(before_row, after_row, strict=True)
            ),
            "predecessor_frame_sha256": _frame_hash(before),
            "successor_frame_sha256": _frame_hash(after),
        }
    finally:
        arcade.close_scorecard()


def run(args: argparse.Namespace) -> dict[str, Any]:
    source_actions = _recorded_first_level(args.recording)
    training_actions = source_actions[:-1]
    held_out_recorded_action = source_actions[-1]
    runtime = Runtime()
    arcade, environment = _open_arcade(args.environments, args.live_recordings, args.game)
    trace_start = len(runtime.trace)
    batches: list[PerceptionBatch] = []
    features: list[frozenset[int]] = []
    frames: list[tuple[tuple[int, ...], ...]] = []
    try:
        initial = _frame(environment.observation_space)
        batch, _workspace, active = _observe(runtime, initial, "training:0")
        batches.append(batch)
        features.append(active)
        frames.append(initial)
        for index, recorded in enumerate(training_actions, start=1):
            _act(environment, args.game, recorded, "training-prefix")
            observed = _frame(environment.observation_space)
            batch, _workspace, active = _observe(runtime, observed, f"training:{index}")
            batches.append(batch)
            features.append(active)
            frames.append(observed)

        transitions = [
            Transition(index, recorded.action_id, features[index], features[index + 1])
            for index, recorded in enumerate(training_actions)
        ]
        parent = _install_parent(runtime, transitions)
        baseline_ranking = _rank_parent(transitions)
        if len(baseline_ranking) < 2:
            raise RuntimeError("parent did not produce action ambiguity")
        runtime.trace.append(
            {
                "event": "ambiguity",
                "cycle": runtime.cycle,
                "parent": runtime.graph.canonical_hash[parent],
                "action_ranking": baseline_ranking,
                "successor_shadows": {
                    str(action): sorted(
                        {
                            "changed" if transition.structural_change else "preserved"
                            for transition in transitions
                            if transition.action_id == action
                        }
                    )
                    for action in sorted({item.action_id for item in transitions})
                },
            }
        )

        condition = _discover_context(runtime, transitions, features[-1])
        context_schema = _schema_record(runtime, condition.schema_id)
        runtime.trace.append(
            {
                "event": "context-discovered",
                "cycle": runtime.cycle,
                "schema": context_schema["hash"],
                "atoms": context_schema["atoms"],
                "polarity": "present" if condition.present else "absent",
                "support": condition.support,
                "purity": condition.purity,
                "selected_action": condition.action_id,
            }
        )
        child, link = _install_child(runtime, parent, condition)
        runtime.trace.append(
            {
                "event": "schema-spinoff",
                "cycle": runtime.cycle,
                "parent": runtime.graph.canonical_hash[parent],
                "child": runtime.graph.canonical_hash[child],
                "edge": link,
                "relation": "spinoff",
            }
        )
        treatment_ranking = _rank_child(transitions, condition)
        baseline_action = int(baseline_ranking[0]["action"])
        treatment_action = int(treatment_ranking[0]["action"])
        if treatment_action == baseline_action:
            raise RuntimeError("context child did not change the top-ranked action")
        predicted_delta, prediction_support = _predict_structural_delta(
            transitions, condition, treatment_action
        )
        runtime.trace.append(
            {
                "event": "action-ranking-changed",
                "cycle": runtime.cycle,
                "baseline": baseline_ranking,
                "with_child": treatment_ranking,
                "baseline_top": baseline_action,
                "treatment_top": treatment_action,
            }
        )

        control = _run_control(
            args.environments,
            args.live_recordings,
            args.game,
            training_actions,
            baseline_action,
        )
        predecessor = _frame(environment.observation_space)
        if _frame_hash(predecessor) != control["predecessor_frame_sha256"]:
            raise RuntimeError("baseline and treatment predecessors are not identical")
        level_before = int(environment.observation_space.levels_completed)
        expected = runtime.graph.terms.ground_atom("StructuralDelta", (predicted_delta,))
        prediction = runtime.predict(
            child,
            expected,
            f"held-out:{args.game}:level:{level_before + 1}",
        )
        runtime.trace.append(
            {
                "event": "prospective-action",
                "cycle": runtime.cycle,
                "action": treatment_action,
                "prediction": prediction,
                "expected": ["StructuralDelta", [predicted_delta]],
                "training_support": prediction_support,
            }
        )
        _act(
            environment,
            args.game,
            RecordedAction(treatment_action, {}),
            "context-child-top-rank",
        )
        successor = _frame(environment.observation_space)
        after_batch, _after_workspace, after_features = _observe(
            runtime, successor, "held-out:successor"
        )
        changed = features[-1] != after_features
        observed_delta = "changed" if changed else "preserved"
        resolution_batch = PerceptionBatch(
            after_batch.context,
            after_batch.facts + ((expected,) if observed_delta == predicted_delta else ()),
            after_batch.form_terms,
            after_batch.region_terms,
            after_batch.outline_terms,
            after_batch.source,
        )
        reified = runtime.resolve_prediction(prediction, resolution_batch)
        level_after = int(environment.observation_space.levels_completed)
        treatment = {
            "action": treatment_action,
            "recording_held_out_action": held_out_recorded_action.action_id,
            "level_before": level_before,
            "level_after": level_after,
            "level_delta": level_after - level_before,
            "predicted_structural_delta": predicted_delta,
            "prediction_training_support": prediction_support,
            "observed_structural_delta": observed_delta,
            "prediction_reified": reified,
            "changed_cells": sum(
                left != right
                for before_row, after_row in zip(predecessor, successor, strict=True)
                for left, right in zip(before_row, after_row, strict=True)
            ),
            "predecessor_frame_sha256": _frame_hash(predecessor),
            "successor_frame_sha256": _frame_hash(successor),
        }
        runtime.trace.append(
            {
                "event": "prospective-outcome",
                "cycle": runtime.cycle,
                **treatment,
            }
        )
    finally:
        arcade.close_scorecard()

    causal_events = [
        event
        for event in runtime.trace[trace_start:]
        if event.get("event")
        in {
            "ambiguity",
            "context-discovered",
            "schema-spinoff",
            "action-ranking-changed",
            "prediction",
            "prospective-action",
            "prediction-resolution",
            "prospective-outcome",
        }
    ]
    result = {
        "experiment": "prospective-context-spinoff-control",
        "game": args.game,
        "level": 1,
        "source_recording": str(args.recording),
        "source_recording_sha256": _file_hash(args.recording),
        "training_transition_count": len(transitions),
        "held_out_transition_count": 1,
        "held_out_predecessor_frame_sha256": _frame_hash(frames[-1]),
        "parent": _schema_record(runtime, parent),
        "child": _schema_record(runtime, child),
        "context": {
            **context_schema,
            "polarity": "present" if condition.present else "absent",
            "support": condition.support,
            "purity": condition.purity,
        },
        "baseline_ranking": baseline_ranking,
        "treatment_ranking": treatment_ranking,
        "control": control,
        "treatment": treatment,
        "causal_chain": [event["event"] for event in causal_events],
        "pass": (
            baseline_action != treatment_action
            and treatment["prediction_reified"]
            and treatment["level_delta"] > control["level_delta"]
        ),
    }
    if not result["pass"]:
        raise RuntimeError("prospective context-spinoff success gate failed")
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "trace.json").write_text(
        json.dumps(causal_events, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output / "summary.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="ar25")
    parser.add_argument("--recording", type=Path, default=DEFAULT_RECORDING)
    parser.add_argument("--environments", type=Path, default=DEFAULT_ENVIRONMENTS)
    parser.add_argument(
        "--live-recordings", type=Path, default=Path("/tmp/reflector2-context-spinoff")
    )
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    return parser


def main() -> None:
    result = run(_parser().parse_args())
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
