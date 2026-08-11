"""Run the parallel R2/Qwen cognitive-workspace experiment on real ARC games."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V0_PATH = HERE.parent / "qwen-generic-explanation-priors-v0" / "experiment.py"
V0_SPEC = importlib.util.spec_from_file_location("qwen_prior_v0_base", V0_PATH)
if V0_SPEC is None or V0_SPEC.loader is None:
    raise RuntimeError(f"cannot load v0 experiment: {V0_PATH}")
V0 = importlib.util.module_from_spec(V0_SPEC)
sys.modules[V0_SPEC.name] = V0
V0_SPEC.loader.exec_module(V0)

sys.path.insert(0, str(HERE))
import qwen_protocol as QP  # noqa: E402
import workspace as WS  # noqa: E402
from qwen_worker import QwenWorker  # noqa: E402

from reflector2.explanations import ExplanationEngine  # noqa: E402
from reflector2.perception import perceive_grid  # noqa: E402
from reflector2.runtime import Runtime  # noqa: E402


ENVIRONMENTS = V0.ENVIRONMENTS
V0_ROOT = HERE.parent / "qwen-generic-explanation-priors-v0"
Grid = tuple[tuple[int, ...], ...]
STATIC_PREDICATES = frozenset(V0.ALLOWED_PREDICATES)
MOTION_PREDICATES = frozenset({"MovedTogether", "MovedWhileStationary", "ChangedTogether"})


def load_config() -> dict[str, Any]:
    return json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def append_status(message: str) -> None:
    with (HERE / "STATUS.md").open("a", encoding="utf-8") as stream:
        stream.write(message.rstrip() + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def grid_value(value: Any) -> Grid:
    return tuple(tuple(int(cell) for cell in row) for row in value)


def template_from_dict(value: Mapping[str, Any]) -> Any:
    return V0.Template(
        conditions=tuple((item[0], tuple(item[1])) for item in value["conditions"]),
        operator=str(value["operator"]),
        effect_variables=tuple(value["effect_variables"]),
        canonical_hash=str(value["canonical_hash"]),
        provenance=str(value.get("provenance", "externally-proposed")),
    )


def motion_relations(before_grid: Grid, after_grid: Grid) -> list[dict[str, Any]]:
    before = V0.select_figures(before_grid)
    after = V0.select_figures(after_grid)
    mapping = V0.BASE.correspond(before, after)
    after_ids = {figure: f"f{index:02d}" for index, figure in enumerate(after)}
    facts: set[tuple[str, str, str]] = set()
    tracked: list[tuple[Any, Any, tuple[int, int]]] = []
    for source, target in mapping.items():
        if target not in after_ids:
            continue
        delta = (target.anchor[0] - source.anchor[0], target.anchor[1] - source.anchor[1])
        tracked.append((source, target, delta))
    for left_index, (_ls, left, left_delta) in enumerate(tracked):
        for _rs, right, right_delta in tracked[left_index + 1 :]:
            left_id, right_id = after_ids[left], after_ids[right]
            if left_delta != (0, 0) and left_delta == right_delta:
                facts.add(("MovedTogether", left_id, right_id))
            if left_delta != (0, 0) and right_delta == (0, 0):
                facts.add(("MovedWhileStationary", left_id, right_id))
            if right_delta != (0, 0) and left_delta == (0, 0):
                facts.add(("MovedWhileStationary", right_id, left_id))
            if left_delta != (0, 0) and right_delta != (0, 0):
                facts.add(("ChangedTogether", left_id, right_id))
    return [
        {"predicate": predicate, "arguments": [left, right]}
        for predicate, left, right in sorted(facts)
    ]


def relational_state(grid: Grid, legal_count: int, history: Sequence[dict[str, Any]]) -> tuple[dict[str, Any], tuple[Any, ...]]:
    state, figures = V0.structured_state(grid, legal_count)
    if history:
        state["relations"].extend(
            motion_relations(grid_value(history[-1]["before_grid"]), grid_value(history[-1]["after_grid"]))
        )
        state["relations"] = sorted(
            {WS.stable_json(item): item for item in state["relations"]}.values(),
            key=WS.stable_json,
        )
    for entity in state["entities"]:
        entity["generation"] = 0
    return state, figures


class R2Cognition:
    """Chronological core-R2 observer whose compressed deltas enter the bus."""

    def __init__(self, initial_grid: Grid) -> None:
        self.runtime = Runtime()
        self.explanations = ExplanationEngine(self.runtime)
        self.batch = perceive_grid(self.runtime.graph.terms, initial_grid, "cw:obs:0")
        self.runtime.observe(self.batch)
        self.grid = initial_grid
        self.version = 0
        self.trace_cursor = 0

    def reasoning_summary(self, legal_actions: Sequence[int]) -> dict[str, Any]:
        workspace = self.runtime.workspace
        active = () if workspace is None else self.explanations.construct(workspace, legal_actions)
        graph = self.runtime.graph
        top_schema_ids = [] if workspace is None else sorted(
            workspace.activation,
            key=lambda item: (-workspace.activation[item], graph.canonical_hash[item]),
        )[:8]
        recent = self.runtime.trace[self.trace_cursor :]
        self.trace_cursor = len(self.runtime.trace)
        return {
            "cycles": self.runtime.cycle,
            "schema_count": graph.schema_count,
            "active_schema_count": 0 if workspace is None else len(workspace.activation),
            "binding_count": 0 if workspace is None else len(workspace.bindings),
            "shadow_counts": dict(sorted(Counter(item.status for item in self.runtime.shadows.values()).items())),
            "recent_event_counts": dict(sorted(Counter(str(item.get("event")) for item in recent).items())),
            "active_schemas": [
                {
                    "schema_hash": graph.canonical_hash[schema_id],
                    "provenance": sorted(graph.provenance[schema_id]),
                    "activation": workspace.activation[schema_id],
                    "heads": sorted({head for head, _args in graph.source_atoms(schema_id)}),
                }
                for schema_id in top_schema_ids
            ],
            "active_explanations": [
                {
                    "constituents": [graph.canonical_hash[item] for item in explanation.constituent_schema_ids],
                    "provenance": list(explanation.provenance),
                    "confirmations": explanation.confirmations,
                    "refutations": explanation.refutations,
                    "score": explanation.score,
                }
                for explanation in active[:8]
            ],
        }

    def observe_transition(self, action_id: int, after_grid: Grid) -> dict[str, Any]:
        before_batch = self.batch
        predecessor_ids = () if self.runtime.workspace is None else tuple(self.runtime.workspace.activation)
        self.version += 1
        after_batch = perceive_grid(
            self.runtime.graph.terms, after_grid, f"cw:obs:{self.version}"
        )
        self.runtime.observe(after_batch)
        schema_id = self.runtime.learn_transition(
            before_batch,
            after_batch,
            f"arc-action:{action_id}",
            predecessor_schema_ids=predecessor_ids,
        )
        self.batch = after_batch
        self.grid = after_grid
        return {
            "transition_schema_hash": self.runtime.graph.canonical_hash[schema_id],
            "transition_schema_provenance": sorted(self.runtime.graph.provenance[schema_id]),
        }

    def advance_level(self, after_grid: Grid) -> dict[str, Any]:
        """Re-ground a new level without learning a cross-level transition.

        ARC returns the first frame of the next level as the successor of the
        level-winning action.  The recursive schema graph is game knowledge and
        remains available, but that screen replacement is not an object-level
        causal effect of the action.
        """
        self.version += 1
        after_batch = perceive_grid(
            self.runtime.graph.terms, after_grid, f"cw:level:{self.version}"
        )
        self.runtime.observe(after_batch)
        self.batch = after_batch
        self.grid = after_grid
        return {"status": "level-regrounded", "observation_version": self.version}


@dataclass(slots=True)
class Activation:
    template_hash: str
    operator: str
    activated_at_action: int
    source_task: str
    status: str
    effect_pair: list[str] | None


class WorkspaceController:
    """Experiment-local safe adapter around the validated v0 pair controller."""

    def __init__(self) -> None:
        self.inner = V0.PairPotentialController((), "externally-proposed")
        self.activations: list[Activation] = []
        self.active_keys: set[tuple[str, tuple[str, ...]]] = set()
        self.increase_lease: Counter[str] = Counter()

    def activate(
        self,
        template: Any,
        state: dict[str, Any],
        figures: Sequence[Any],
        *,
        action_count: int,
        source_task: str,
    ) -> dict[str, Any]:
        grounding = V0.ground_template(template, state)
        if grounding["status"] != "bound":
            self.activations.append(
                Activation(template.canonical_hash, template.operator, action_count, source_task, grounding["status"], None)
            )
            return grounding
        key = (template.canonical_hash, tuple(grounding["effect_pair"]))
        if key in self.active_keys:
            grounding = {**grounding, "status": "duplicate-active"}
            return grounding
        bindings = V0.bindings_from_groundings((grounding,), state, figures)
        self.inner.bindings.extend(bindings)
        self.active_keys.add(key)
        self.activations.append(
            Activation(
                template.canonical_hash,
                template.operator,
                action_count,
                source_task,
                "active-zero-evidence",
                list(grounding["effect_pair"]),
            )
        )
        return grounding

    def choose(self, legal_actions: Sequence[int]) -> Any:
        original = self.inner.bindings
        self.inner.bindings = [
            item
            for item in original
            if item.operator != "Increase" or self.increase_lease[item.template_hash] < 3
        ]
        try:
            decision = self.inner.choose(legal_actions)
        finally:
            self.inner.bindings = original
        if decision.prior_used and decision.template_hash is not None:
            binding = next((item for item in original if item.template_hash == decision.template_hash), None)
            if binding is not None and binding.operator == "Increase":
                self.increase_lease[binding.template_hash] += 1
        return decision

    def observe(self, action: int, before_grid: Grid, after_grid: Grid) -> dict[str, Any]:
        return self.inner.observe(action, before_grid, after_grid)

    def report(self) -> dict[str, Any]:
        return {
            **self.inner.report(),
            "activations": [asdict(item) for item in self.activations],
            "increase_lease": dict(sorted(self.increase_lease.items())),
        }


def observation_blob(root: Path, observation: Any) -> tuple[str, dict[str, Any], Grid]:
    record = V0.BASE.observation_record(observation)
    grid = V0.BASE.observation_grid(observation)
    return WS.put_blob(root, {"record": record, "grid": [list(row) for row in grid]}), record, grid


def event_basis(state: WS.WorkspaceState) -> dict[str, Any]:
    return {
        "head_hash": state.head_hash,
        "observation_version": state.observation_version,
        "observation_digest": state.observation_digest,
    }


def execute_action(environment: Any, game: str, action_id: int, data: dict[str, int], reason: str) -> Any:
    from arcengine import GameAction

    action = GameAction.from_id(action_id)
    if data:
        action.set_data(data)
    result = environment.step(
        action,
        data={**data, "game_id": game},
        reasoning={"experiment": "parallel-cognitive-workspace-v0", "reason": reason},
    )
    observation = result if result is not None else environment.observation_space
    if observation is None:
        raise RuntimeError("ARC returned no successor observation")
    return observation


def workspace_events_by_id(root: Path) -> dict[str, dict[str, Any]]:
    return {str(item["event_id"]): item for item in WS.list_events(root)}


def history_from_workspace(root: Path) -> list[dict[str, Any]]:
    events = workspace_events_by_id(root)
    output: list[dict[str, Any]] = []
    for event in WS.list_events(root):
        if event["type"] != "TransitionCommitted":
            continue
        payload = event["payload"]
        pending = events[str(payload["pending_event_id"])]["payload"]
        before_entry = next(
            item for item in WS.reduce_workspace(root).observations if item[0] == int(payload["before_version"])
        )
        before_blob = WS.read_blob(root, before_entry[2])
        after_blob = WS.read_blob(root, str(payload["after_blob"]))
        output.append(
            {
                "index": int(payload["before_version"]),
                "action_id": int(payload["action_id"]),
                "data": {str(key): int(value) for key, value in pending.get("data", {}).items()},
                "before": before_blob["record"],
                "after": after_blob["record"],
                "before_grid": before_blob["grid"],
                "after_grid": after_blob["grid"],
                "transition_event_id": event["event_id"],
            }
        )
    return output


def materialize_for_qwen(
    root: Path,
    state: WS.WorkspaceState,
    grid: Grid,
    legal: Sequence[int],
    history: Sequence[dict[str, Any]],
    cognition: R2Cognition,
    controller: WorkspaceController,
    r2_summary: dict[str, Any],
) -> dict[str, Any]:
    relational, _figures = relational_state(grid, len(legal), history)
    action_to_model = {action: f"m{index}" for index, action in enumerate(sorted(set(legal) | set(controller.inner.uses)))}
    intervention_models = []
    for action, model_id in action_to_model.items():
        effects: Counter[tuple[int, int]] = Counter()
        for binding in controller.inner.bindings:
            effects.update(binding.action_deltas.get(action, []))
        intervention_models.append(
            {
                "model_id": model_id,
                "observations": int(controller.inner.uses[action]),
                "effect": {
                    "relative_effects": [
                        {"delta2": list(delta), "support": support}
                        for delta, support in sorted(effects.items(), key=lambda item: (-item[1], item[0]))[:3]
                    ]
                },
            }
        )
    recent = []
    transition_events = [item for item in WS.list_events(root) if item["type"] == "TransitionCommitted"][-4:]
    for event, item in zip(transition_events, history[-4:], strict=False):
        recent.append(
            {
                "event_seq": int(event["seq"]),
                "model_id": action_to_model.get(int(item["action_id"]), "unavailable"),
                "observation_changed": item["before"]["frame_sha256"] != item["after"]["frame_sha256"],
                "derived_relations": motion_relations(grid_value(item["before_grid"]), grid_value(item["after_grid"])),
            }
        )
    active_schemas = []
    for activation in controller.activations[-8:]:
        active_schemas.append(
            {
                "object_ref": f"schema:{activation.template_hash[:16]}",
                "origin": "externally-proposed",
                "status": activation.status,
                "activated_at_event": activation.activated_at_action,
                "effect_pair": activation.effect_pair,
            }
        )
    cognitive_objects = [
        {
            "object_ref": item["object_ref"],
            "kind": "schema",
            "status": item["status"],
            "summary": item,
        }
        for item in active_schemas
    ]
    cognitive_objects.extend(
        {
            "object_ref": f"r2-explanation-{index}",
            "kind": "explanation",
            "status": "live",
            "summary": item,
        }
        for index, item in enumerate(r2_summary.get("active_explanations", [])[:8])
    )
    return {
        "observation": {"version": state.observation_version, "digest": state.observation_digest},
        "opaque_legal_action_count": len(legal),
        "entities": relational["entities"],
        "relations": relational["relations"],
        "intervention_models": intervention_models,
        "transitions": recent,
        "basis_events": [item["event_seq"] for item in recent],
        "cognitive_objects": cognitive_objects,
        "history_summary": {
            "interventions": len(history),
            "no_change": sum(item["before"]["frame_sha256"] == item["after"]["frame_sha256"] for item in history),
            "derived_relation_counts": dict(
                sorted(Counter(rel["predicate"] for item in recent for rel in item["derived_relations"]).items())
            ),
        },
        "r2_state": r2_summary,
    }


def queue_qwen_task(
    root: Path,
    workspace_id: str,
    state: WS.WorkspaceState,
    materialization: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    task_index = len(state.tasks)
    request_id = f"req-{task_index:02d}"
    snapshot = QP.serialize_snapshot(
        materialization,
        request_id=request_id,
        basis_revision=state.head_seq,
    )
    request = QP.build_request_payload(snapshot, config, prompt_path=HERE / "PROMPT.txt")
    projection_blob = WS.put_blob(root, snapshot)
    request_blob = WS.put_blob(root, request)
    task_id = WS.stable_hash(
        {
            "workspace_id": workspace_id,
            "request_id": request_id,
            "basis_digest": state.observation_digest,
            "projection_blob": projection_blob,
            "request_blob": request_blob,
        }
    )
    return WS.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenTaskQueued",
        actor="environment",
        basis=event_basis(state),
        payload={
            "task_id": task_id,
            "basis_observation_version": state.observation_version,
            "basis_observation_digest": state.observation_digest,
            "request_blob": request_blob,
            "projection_blob": projection_blob,
        },
    )


def templates_from_compilation(compilation: dict[str, Any]) -> tuple[Any, ...]:
    if hasattr(QP, "templates_from_compilation"):
        return tuple(QP.templates_from_compilation(compilation))
    return tuple(template_from_dict(item) for item in compilation.get("accepted", []))


def activate_compilation(
    root: Path,
    workspace_id: str,
    task: Any,
    compilation: dict[str, Any],
    controller: WorkspaceController,
    grid: Grid,
    legal: Sequence[int],
    history: Sequence[dict[str, Any]],
    *,
    adjudication_kind: str,
) -> dict[str, Any]:
    relation_state, figures = relational_state(grid, len(legal), history)
    templates = templates_from_compilation(compilation)
    groundings = [
        controller.activate(
            template,
            relation_state,
            figures,
            action_count=len(history),
            source_task=task.task_id,
        )
        for template in templates
    ]
    accepted_count = sum(item["status"] in {"bound", "duplicate-active"} for item in groundings)
    adjudication = {
        "task_id": task.task_id,
        "kind": adjudication_kind,
        "activation_observation_version": len(history),
        "compilation": compilation,
        "accepted_templates": [asdict(item) for item in templates],
        "groundings": groundings,
        "accepted_bound_count": accepted_count,
        "evidence_at_activation": 0,
    }
    blob = WS.put_blob(root, adjudication)
    current = WS.reduce_workspace(root)
    WS.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="ExternalProposalAdjudicated",
        actor="r2",
        basis=event_basis(current),
        payload={
            "task_id": task.task_id,
            "verdict": "accepted" if accepted_count else "rejected",
            "adjudication_blob": blob,
        },
    )
    return adjudication


def adjudicate_replied_tasks(
    root: Path,
    workspace_id: str,
    controller: WorkspaceController,
    grid: Grid,
    legal: Sequence[int],
    history: Sequence[dict[str, Any]],
    *,
    force_terminal: bool = False,
) -> list[dict[str, Any]]:
    output = []
    state = WS.reduce_workspace(root)
    for task in state.tasks:
        if task.status != "replied":
            continue
        if not force_terminal and len(history) < task.basis_version + int(load_config()["parallel_action_window"]):
            continue
        if force_terminal and len(history) < task.basis_version + int(load_config()["parallel_action_window"]):
            adjudication = {
                "task_id": task.task_id,
                "kind": "terminal-before-logical-eligibility",
                "activation_observation_version": None,
                "accepted_templates": [],
                "groundings": [],
                "accepted_bound_count": 0,
            }
            blob = WS.put_blob(root, adjudication)
            current = WS.reduce_workspace(root)
            WS.commit_event(
                root,
                workspace_id=workspace_id,
                event_type="ExternalProposalAdjudicated",
                actor="r2",
                basis=event_basis(current),
                payload={"task_id": task.task_id, "verdict": "rejected", "adjudication_blob": blob},
            )
            output.append(adjudication)
            continue
        response = WS.read_blob(root, str(task.response_blob))
        snapshot = WS.read_blob(root, task.projection_blob)
        compilation = QP.compile_response(response, snapshot)
        output.append(
            activate_compilation(
                root,
                workspace_id,
                task,
                compilation,
                controller,
                grid,
                legal,
                history,
                adjudication_kind=(
                    "fresh" if len(history) == task.basis_version else "stale-revalidated-current-relations"
                ),
            )
        )
    return output


def inject_frozen_compilation(
    root: Path,
    workspace_id: str,
    game: str,
    controller: WorkspaceController,
    grid: Grid,
    legal: Sequence[int],
    history: Sequence[dict[str, Any]],
    *,
    label: str,
) -> dict[str, Any]:
    compilation_path = V0_ROOT / "artifacts" / "compilations" / f"{game}.json"
    compilation = json.loads(compilation_path.read_text(encoding="utf-8"))
    state = WS.reduce_workspace(root)
    projection = {
        "protocol": "frozen-v0-proposal-injection",
        "source_game_transport_only": game,
        "source_compilation_sha256": V0.BASE.file_hash(compilation_path),
    }
    projection_blob = WS.put_blob(root, projection)
    request_blob = WS.put_blob(root, {"kind": label, "endpoint_disabled": True})
    task_id = WS.stable_hash({"workspace_id": workspace_id, "label": label, "compilation": compilation})
    WS.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenTaskQueued",
        actor="coordinator",
        basis=event_basis(state),
        payload={
            "task_id": task_id,
            "basis_observation_version": state.observation_version,
            "basis_observation_digest": state.observation_digest,
            "request_blob": request_blob,
            "projection_blob": projection_blob,
        },
    )
    epoch = f"frozen-injection:{label}"
    current = WS.reduce_workspace(root)
    WS.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenTaskClaimed",
        actor="qwen",
        basis=event_basis(current),
        payload={"task_id": task_id, "worker_epoch": epoch},
    )
    response_blob = WS.put_blob(
        root,
        {
            "protocol": WS.PROTOCOL,
            "task_id": task_id,
            "worker_epoch": epoch,
            "request_blob": request_blob,
            "transport_error": None,
            "parsed": None,
            "frozen_compilation": compilation,
        },
    )
    current = WS.reduce_workspace(root)
    WS.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="QwenReplyRecorded",
        actor="qwen",
        basis=event_basis(current),
        payload={"task_id": task_id, "worker_epoch": epoch, "response_blob": response_blob},
    )
    task = next(item for item in WS.reduce_workspace(root).tasks if item.task_id == task_id)
    return activate_compilation(
        root,
        workspace_id,
        task,
        compilation,
        controller,
        grid,
        legal,
        history,
        adjudication_kind=label,
    )


def rebuild_cognition(root: Path) -> tuple[R2Cognition, WorkspaceController, list[dict[str, Any]], Grid]:
    state = WS.reduce_workspace(root)
    if not state.observations:
        raise RuntimeError("workspace has no initial observation")
    initial_blob = WS.read_blob(root, state.observations[0][2])
    current_grid = grid_value(initial_blob["grid"])
    cognition = R2Cognition(current_grid)
    controller = WorkspaceController()
    history: list[dict[str, Any]] = []
    events_by_id = workspace_events_by_id(root)
    for event in WS.list_events(root):
        if event["type"] == "ExternalProposalAdjudicated":
            adjudication = WS.read_blob(root, str(event["payload"]["adjudication_blob"]))
            relation_state, figures = relational_state(current_grid, len(state.legal_actions), history)
            for raw in adjudication.get("accepted_templates", []):
                controller.activate(
                    template_from_dict(raw),
                    relation_state,
                    figures,
                    action_count=len(history),
                    source_task=str(event["payload"]["task_id"]),
                )
        elif event["type"] == "TransitionCommitted":
            payload = event["payload"]
            pending = events_by_id[str(payload["pending_event_id"])]["payload"]
            after_blob = WS.read_blob(root, str(payload["after_blob"]))
            after_grid = grid_value(after_blob["grid"])
            cognition.reasoning_summary(state.legal_actions)
            controller.observe(int(payload["action_id"]), current_grid, after_grid)
            cognition.observe_transition(int(payload["action_id"]), after_grid)
            history.append(
                {
                    "index": int(payload["before_version"]),
                    "action_id": int(payload["action_id"]),
                    "data": pending.get("data", {}),
                    "before": V0.BASE.observation_record_from_dict(initial_blob["record"])
                    if hasattr(V0.BASE, "observation_record_from_dict")
                    else {"digest": str(payload["before_digest"]), "frame_sha256": "unknown"},
                    "after": after_blob["record"],
                    "before_grid": [list(row) for row in current_grid],
                    "after_grid": after_blob["grid"],
                    "transition_event_id": event["event_id"],
                }
            )
            # Recover the actual before record from its observation blob.
            before_entry = next(item for item in state.observations if item[0] == int(payload["before_version"]))
            history[-1]["before"] = WS.read_blob(root, before_entry[2])["record"]
            current_grid = after_grid
    return cognition, controller, history, current_grid


def open_and_replay_environment(
    root: Path,
    game: str,
    environments: Path,
    recordings: Path,
) -> tuple[Any, Any, Any]:
    arcade, environment = V0.BASE.open_environment(environments, recordings, game)
    observation = environment.observation_space
    if observation is None:
        observation = environment.reset()
    if observation is None:
        arcade.close_scorecard()
        raise RuntimeError("ARC produced no initial observation")
    for event in WS.list_events(root):
        if event["type"] != "TransitionCommitted":
            continue
        payload = event["payload"]
        if V0.BASE.observation_record(observation)["digest"] != payload["before_digest"]:
            arcade.close_scorecard()
            raise RuntimeError("environment replay predecessor mismatch")
        pending_event = workspace_events_by_id(root)[str(payload["pending_event_id"])]
        observation = execute_action(
            environment,
            game,
            int(payload["action_id"]),
            {str(key): int(value) for key, value in pending_event["payload"].get("data", {}).items()},
            "workspace-checkpoint-replay",
        )
        if V0.BASE.observation_record(observation)["digest"] != payload["after_digest"]:
            arcade.close_scorecard()
            raise RuntimeError("environment replay successor mismatch")
    return arcade, environment, observation


def verify_workspace_ledger(root: Path, game: str, environments: Path, recordings: Path) -> bool:
    arcade, environment = V0.BASE.open_environment(environments, recordings, game)
    try:
        observation = environment.observation_space
        if observation is None:
            observation = environment.reset()
        if observation is None:
            return False
        events_by_id = workspace_events_by_id(root)
        for event in WS.list_events(root):
            if event["type"] != "TransitionCommitted":
                continue
            payload = event["payload"]
            if V0.BASE.observation_record(observation)["digest"] != payload["before_digest"]:
                return False
            pending = events_by_id[str(payload["pending_event_id"])]["payload"]
            observation = execute_action(
                environment,
                game,
                int(payload["action_id"]),
                {str(key): int(value) for key, value in pending.get("data", {}).items()},
                "workspace-final-replay-verification",
            )
            if V0.BASE.observation_record(observation)["digest"] != payload["after_digest"]:
                return False
        return True
    finally:
        arcade.close_scorecard()


def wait_for_due_task(
    root: Path,
    workspace_id: str,
    worker: QwenWorker,
    *,
    action_count: int,
    window: int,
    timeout: float = 90.0,
) -> None:
    deadline = time.monotonic() + timeout
    while True:
        worker.raise_if_failed()
        state = WS.reduce_workspace(root)
        due = [
            task
            for task in state.tasks
            if task.status in {"queued", "claimed"} and action_count >= task.basis_version + window
        ]
        if not due:
            return
        if time.monotonic() >= deadline:
            for task in due:
                current = WS.reduce_workspace(root)
                WS.commit_event(
                    root,
                    workspace_id=workspace_id,
                    event_type="QwenTaskAbandoned",
                    actor="coordinator",
                    basis=event_basis(current),
                    payload={"task_id": task.task_id, "reason": "logical-release-timeout"},
                )
            return
        time.sleep(0.1)


def finalize_qwen_tasks(
    root: Path,
    workspace_id: str,
    worker: QwenWorker,
    controller: WorkspaceController,
    grid: Grid,
    legal: Sequence[int],
    history: Sequence[dict[str, Any]],
) -> None:
    deadline = time.monotonic() + 90.0
    while True:
        worker.raise_if_failed()
        state = WS.reduce_workspace(root)
        outstanding = [task for task in state.tasks if task.status in {"queued", "claimed"}]
        if not outstanding:
            break
        if time.monotonic() >= deadline:
            for task in outstanding:
                current = WS.reduce_workspace(root)
                WS.commit_event(
                    root,
                    workspace_id=workspace_id,
                    event_type="QwenTaskAbandoned",
                    actor="coordinator",
                    basis=event_basis(current),
                    payload={"task_id": task.task_id, "reason": "episode-finalization-timeout"},
                )
            break
        time.sleep(0.1)
    adjudicate_replied_tasks(
        root,
        workspace_id,
        controller,
        grid,
        legal,
        history,
        force_terminal=True,
    )
    worker.request_stop()
    worker.join(timeout=10)
    worker.raise_if_failed()


def run_episode(payload: Mapping[str, Any]) -> dict[str, Any]:
    game = str(payload["game"])
    arm = str(payload["arm"])
    config = dict(payload["config"])
    environments = Path(payload.get("environments", ENVIRONMENTS))
    live_qwen = arm == "parallel_qwen"
    frozen_source = game if arm in {"one_shot_v0", "frozen_injection"} else None
    workspace_id = f"{game}--{arm}"
    root = HERE / "artifacts" / "workspaces" / workspace_id
    result_path = HERE / "artifacts" / "results" / f"{workspace_id}.json"
    job_key = WS.stable_hash(
        {
            "protocol": config["workspace_protocol"],
            "game_transport": game,
            "arm": arm,
            "config": config,
            "experiment_code": V0.BASE.file_hash(Path(__file__)),
            "workspace_code": V0.BASE.file_hash(HERE / "workspace.py"),
            "qwen_protocol_code": V0.BASE.file_hash(HERE / "qwen_protocol.py"),
            "prompt": V0.BASE.file_hash(HERE / "PROMPT.txt"),
        }
    )
    existing_events = WS.list_events(root)
    if existing_events:
        existing = WS.reduce_workspace(root)
        if existing.job_key != job_key:
            raise RuntimeError(f"incompatible workspace for {workspace_id}")
        if existing.stopped and result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))

    recordings = HERE / "artifacts" / "recordings" / workspace_id / f"resume-{len(existing_events):04d}"
    if existing_events:
        arcade, environment, observation = open_and_replay_environment(root, game, environments, recordings)
    else:
        arcade, environment = V0.BASE.open_environment(environments, recordings, game)
        observation = environment.observation_space
        if observation is None:
            observation = environment.reset()
        if observation is None:
            arcade.close_scorecard()
            raise RuntimeError("ARC produced no initial observation")
        WS.commit_event(
            root,
            workspace_id=workspace_id,
            event_type="WorkspaceStarted",
            actor="coordinator",
            payload={"job_key": job_key},
        )
        blob, record, _grid = observation_blob(root, observation)
        legal = V0.BASE.simple_legal_actions(environment, observation)
        WS.commit_event(
            root,
            workspace_id=workspace_id,
            event_type="ObservationCommitted",
            actor="environment",
            payload={
                "observation_version": 0,
                "observation_digest": record["digest"],
                "observation_blob": blob,
                "legal_actions": list(legal),
                "levels_completed": record["levels_completed"],
            },
        )

    cognition, controller, history, grid = rebuild_cognition(root)
    state = WS.reduce_workspace(root)
    legal = V0.BASE.simple_legal_actions(environment, observation)
    if frozen_source is not None and not state.tasks:
        inject_frozen_compilation(
            root,
            workspace_id,
            frozen_source,
            controller,
            grid,
            legal,
            history,
            label="frozen-own-proposal",
        )
        state = WS.reduce_workspace(root)

    worker: QwenWorker | None = None
    if live_qwen:
        worker = QwenWorker(root, config["qwen"]["endpoint"], request_timeout=600)
        worker.start()

    started = time.perf_counter()
    stop_reason = "action-budget"
    try:
        # A crash after ActionPending is recovered by exact re-execution here.
        state = WS.reduce_workspace(root)
        if state.pending_action is not None:
            pending = state.pending_action
            before_record = V0.BASE.observation_record(observation)
            if before_record["digest"] != pending["before_digest"]:
                raise RuntimeError("pending-action recovery predecessor mismatch")
            before_grid = V0.BASE.observation_grid(observation)
            successor = execute_action(
                environment,
                game,
                int(pending["action_id"]),
                {str(key): int(value) for key, value in pending.get("data", {}).items()},
                "pending-action-recovery",
            )
            after_blob, after_record, after_grid = observation_blob(root, successor)
            after_legal = V0.BASE.simple_legal_actions(environment, successor)
            controller.observe(int(pending["action_id"]), before_grid, after_grid)
            cognition.observe_transition(int(pending["action_id"]), after_grid)
            WS.commit_event(
                root,
                workspace_id=workspace_id,
                event_type="TransitionCommitted",
                actor="environment",
                basis=event_basis(state),
                payload={
                    "pending_event_id": pending["event_id"],
                    "before_version": pending["before_version"],
                    "before_digest": pending["before_digest"],
                    "action_id": pending["action_id"],
                    "after_version": int(pending["before_version"]) + 1,
                    "after_digest": after_record["digest"],
                    "after_blob": after_blob,
                    "legal_actions": list(after_legal),
                    "levels_completed": after_record["levels_completed"],
                },
            )
            history.append(
                {
                    "index": len(history),
                    "action_id": int(pending["action_id"]),
                    "data": pending.get("data", {}),
                    "before": before_record,
                    "after": after_record,
                    "before_grid": [list(row) for row in before_grid],
                    "after_grid": [list(row) for row in after_grid],
                }
            )
            observation, grid, legal = successor, after_grid, after_legal

        while len(history) < int(config["action_budget"]):
            state = WS.reduce_workspace(root)
            before_record = V0.BASE.observation_record(observation)
            if int(before_record["levels_completed"]) >= 1:
                stop_reason = "first-level-completed"
                break
            grid = V0.BASE.observation_grid(observation)
            legal = V0.BASE.simple_legal_actions(environment, observation)
            if not legal:
                stop_reason = "complex-only-epistemic-abstention"
                break

            if worker is not None:
                wait_for_due_task(
                    root,
                    workspace_id,
                    worker,
                    action_count=len(history),
                    window=int(config["parallel_action_window"]),
                    timeout=180,
                )
                adjudicate_replied_tasks(root, workspace_id, controller, grid, legal, history)
                state = WS.reduce_workspace(root)
                trigger_counts = {int(item) for item in config["qwen"]["trigger_action_counts"]}
                outstanding = any(task.status in {"queued", "claimed", "replied"} for task in state.tasks)
                if (
                    len(history) in trigger_counts
                    and len(state.tasks) < int(config["qwen"]["max_calls_per_episode"])
                    and not outstanding
                ):
                    r2_for_qwen = cognition.reasoning_summary(legal)
                    materialization = materialize_for_qwen(
                        root, state, grid, legal, history, cognition, controller, r2_for_qwen
                    )
                    queue_qwen_task(root, workspace_id, state, materialization, config)
                    state = WS.reduce_workspace(root)

            r2_summary = cognition.reasoning_summary(legal)
            decision = controller.choose(legal)
            decision_blob = WS.put_blob(
                root,
                {
                    "decision": asdict(decision),
                    "same_state_no_qwen_action": decision.fallback_action_id,
                    "qwen_changed_action": decision.action_id != decision.fallback_action_id,
                    "controller": controller.report(),
                    "r2": r2_summary,
                },
            )
            state = WS.reduce_workspace(root)
            decision_id = f"decision-{state.observation_version:04d}"
            decision_event = WS.commit_event(
                root,
                workspace_id=workspace_id,
                event_type="R2DecisionPublished",
                actor="r2",
                basis=event_basis(state),
                payload={
                    "decision_id": decision_id,
                    "observation_version": state.observation_version,
                    "observation_digest": state.observation_digest,
                    "decision_blob": decision_blob,
                },
            )
            state = WS.reduce_workspace(root)
            pending_event = WS.commit_event(
                root,
                workspace_id=workspace_id,
                event_type="ActionPending",
                actor="environment",
                basis=event_basis(state),
                payload={
                    "before_version": state.observation_version,
                    "before_digest": state.observation_digest,
                    "action_id": decision.action_id,
                    "data": {},
                    "decision_event_id": decision_event["event_id"],
                },
            )
            before_grid = grid
            successor = execute_action(
                environment, game, decision.action_id, {}, decision.reason
            )
            after_blob, after_record, after_grid = observation_blob(root, successor)
            after_legal = V0.BASE.simple_legal_actions(environment, successor)
            learning = controller.observe(decision.action_id, before_grid, after_grid)
            r2_learning = cognition.observe_transition(decision.action_id, after_grid)
            state = WS.reduce_workspace(root)
            transition_event = WS.commit_event(
                root,
                workspace_id=workspace_id,
                event_type="TransitionCommitted",
                actor="environment",
                basis=event_basis(state),
                payload={
                    "pending_event_id": pending_event["event_id"],
                    "before_version": state.observation_version,
                    "before_digest": state.observation_digest,
                    "action_id": decision.action_id,
                    "after_version": int(state.observation_version) + 1,
                    "after_digest": after_record["digest"],
                    "after_blob": after_blob,
                    "legal_actions": list(after_legal),
                    "levels_completed": after_record["levels_completed"],
                },
            )
            history.append(
                {
                    "index": len(history),
                    "action_id": decision.action_id,
                    "data": {},
                    "before": before_record,
                    "after": after_record,
                    "before_grid": [list(row) for row in before_grid],
                    "after_grid": [list(row) for row in after_grid],
                    "decision": asdict(decision),
                    "learning": learning,
                    "r2_learning": r2_learning,
                    "transition_event_id": transition_event["event_id"],
                }
            )
            observation, grid, legal = successor, after_grid, after_legal
            WS.write_snapshot(root)
            WS.write_cursor(
                root,
                "environment",
                seq=WS.reduce_workspace(root).head_seq,
                event_hash_value=WS.reduce_workspace(root).head_hash,
                metadata={"actions_committed": len(history)},
            )
            progress_path = HERE / "artifacts" / "progress" / f"{workspace_id}.json"
            WS.atomic_json(
                progress_path,
                {
                    "game": game,
                    "arm": arm,
                    "status": "running",
                    "actions": len(history),
                    "levels_completed": after_record["levels_completed"],
                    "workspace_head": WS.reduce_workspace(root).head_seq,
                    "qwen_tasks": [asdict(item) for item in WS.reduce_workspace(root).tasks],
                    "controller": controller.report(),
                },
            )
            if int(after_record["levels_completed"]) >= 1:
                stop_reason = "first-level-completed"
                break

        if worker is not None:
            finalize_qwen_tasks(root, workspace_id, worker, controller, grid, legal, history)
            worker = None
        state = WS.reduce_workspace(root)
        if not state.stopped:
            WS.commit_event(
                root,
                workspace_id=workspace_id,
                event_type="WorkspaceStopped",
                actor="environment",
                basis=event_basis(state),
                payload={"reason": stop_reason},
            )
    finally:
        if worker is not None:
            worker.request_stop()
            worker.join(timeout=10)
        arcade.close_scorecard()

    final_record = V0.BASE.observation_record(observation)
    replay_verified = verify_workspace_ledger(
        root,
        game,
        environments,
        HERE / "artifacts" / "recordings" / workspace_id / "verification",
    )
    events = WS.list_events(root)
    decisions = [
        WS.read_blob(root, str(item["payload"]["decision_blob"]))
        for item in events
        if item["type"] == "R2DecisionPublished"
    ]
    tasks = WS.reduce_workspace(root).tasks
    result = {
        "game": game,
        "arm": arm,
        "job_key": job_key,
        "actions": len(history),
        "action_sequence": [int(item["action_id"]) for item in history],
        "levels_completed": int(final_record["levels_completed"]),
        "first_level_completed": int(final_record["levels_completed"]) >= 1,
        "stop_reason": stop_reason,
        "final_digest": final_record["digest"],
        "replay_verified": replay_verified,
        "workspace_head": WS.reduce_workspace(root).head_seq,
        "workspace_hash": WS.reduce_workspace(root).head_hash,
        "workspace_rebuild_hash": WS.stable_hash(WS.state_document(WS.reduce_workspace(root))),
        "qwen_task_count": len(tasks),
        "qwen_task_statuses": dict(sorted(Counter(item.status for item in tasks).items())),
        "qwen_changed_decisions": sum(bool(item.get("qwen_changed_action")) for item in decisions),
        "prior_decisions": sum(bool(item["decision"].get("prior_used")) for item in decisions),
        "post_initial_qwen_requests": sum(item.basis_version > 0 for item in tasks),
        "controller": controller.report(),
        "elapsed_s": time.perf_counter() - started,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    WS.atomic_json(result_path, result)
    WS.atomic_json(HERE / "artifacts" / "progress" / f"{workspace_id}.json", {**result, "status": "completed"})
    return result


def build_offline_replay(root: Path) -> dict[str, Any]:
    source_checkpoint = V0_ROOT / "artifacts" / "checkpoints" / "ar25" / "qwen_own" / "latest.json"
    source = json.loads(source_checkpoint.read_text(encoding="utf-8"))
    chronology = source["history"]
    workspace_id = "offline-ar25-regression"
    if WS.list_events(root):
        state = WS.reduce_workspace(root)
        return {
            "events": WS.list_events(root),
            "state": WS.state_document(state),
            "actions": [int(item["action_id"]) for item in chronology],
        }
    WS.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="WorkspaceStarted",
        actor="coordinator",
        payload={"job_key": WS.stable_hash({"source": V0.BASE.file_hash(source_checkpoint), "gate": "offline"})},
    )
    initial = chronology[0]
    initial_blob = WS.put_blob(
        root,
        {"record": initial["before"], "grid": initial["before_grid"]},
    )
    WS.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="ObservationCommitted",
        actor="environment",
        payload={
            "observation_version": 0,
            "observation_digest": initial["before"]["digest"],
            "observation_blob": initial_blob,
            "legal_actions": initial["before"]["available_actions"],
            "levels_completed": initial["before"]["levels_completed"],
        },
    )
    controller = WorkspaceController()
    inject_frozen_compilation(
        root,
        workspace_id,
        "ar25",
        controller,
        grid_value(initial["before_grid"]),
        initial["before"]["available_actions"],
        [],
        label="offline-frozen-proposal",
    )
    for index, item in enumerate(chronology):
        state = WS.reduce_workspace(root)
        decision_blob = WS.put_blob(
            root,
            {
                "decision": item["decision"],
                "same_state_no_qwen_action": item["decision"]["fallback_action_id"],
                "qwen_changed_action": item["decision"]["action_id"] != item["decision"]["fallback_action_id"],
                "source": "frozen-ar25-qwen-own-chronology",
            },
        )
        decision_event = WS.commit_event(
            root,
            workspace_id=workspace_id,
            event_type="R2DecisionPublished",
            actor="r2",
            basis=event_basis(state),
            payload={
                "decision_id": f"decision-{index:04d}",
                "observation_version": index,
                "observation_digest": item["before"]["digest"],
                "decision_blob": decision_blob,
            },
        )
        state = WS.reduce_workspace(root)
        pending = WS.commit_event(
            root,
            workspace_id=workspace_id,
            event_type="ActionPending",
            actor="environment",
            basis=event_basis(state),
            payload={
                "before_version": index,
                "before_digest": item["before"]["digest"],
                "action_id": item["action_id"],
                "data": item.get("data", {}),
                "decision_event_id": decision_event["event_id"],
            },
        )
        after_blob = WS.put_blob(root, {"record": item["after"], "grid": item["after_grid"]})
        state = WS.reduce_workspace(root)
        WS.commit_event(
            root,
            workspace_id=workspace_id,
            event_type="TransitionCommitted",
            actor="environment",
            basis=event_basis(state),
            payload={
                "pending_event_id": pending["event_id"],
                "before_version": index,
                "before_digest": item["before"]["digest"],
                "action_id": item["action_id"],
                "after_version": index + 1,
                "after_digest": item["after"]["digest"],
                "after_blob": after_blob,
                "legal_actions": item["after"]["available_actions"],
                "levels_completed": item["after"]["levels_completed"],
            },
        )
    state = WS.reduce_workspace(root)
    WS.commit_event(
        root,
        workspace_id=workspace_id,
        event_type="WorkspaceStopped",
        actor="coordinator",
        basis=event_basis(state),
        payload={"reason": "historical-chronology-complete"},
    )
    state = WS.reduce_workspace(root)
    WS.write_snapshot(root, state)
    return {
        "events": WS.list_events(root),
        "state": WS.state_document(state),
        "actions": [int(item["action_id"]) for item in chronology],
    }


def offline_gate() -> dict[str, Any]:
    left = build_offline_replay(HERE / "artifacts" / "gates" / "offline-a")
    right = build_offline_replay(HERE / "artifacts" / "gates" / "offline-b")
    byte_identical = WS.stable_json(left["events"]) == WS.stable_json(right["events"])
    events = left["events"]
    final_state = WS.reduce_events(events)
    resume_hashes = []
    for cut in range(len(events) + 1):
        prefix = WS.reduce_events(events[:cut])
        resumed = prefix
        for event in events[cut:]:
            resumed = WS.reduce_event(resumed, event)
        resume_hashes.append(WS.stable_hash(WS.state_document(resumed)))
    result = {
        "passed": bool(
            byte_identical
            and final_state.levels_completed >= 1
            and len(final_state.transitions) == 17
            and len(set(resume_hashes)) == 1
            and left["actions"] == [1] + [2] * 11 + [3] * 5
        ),
        "byte_identical_replays": byte_identical,
        "transition_count": len(final_state.transitions),
        "levels_completed": final_state.levels_completed,
        "action_sequence": left["actions"],
        "all_prefix_resumes_identical": len(set(resume_hashes)) == 1,
        "final_workspace_hash": final_state.head_hash,
    }
    WS.atomic_json(HERE / "artifacts" / "gates" / "offline-result.json", result)
    return result


def run_gates(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config()
    offline = offline_gate()
    append_status(
        "\n## Offline ar25 workspace gate\n\n"
        f"- Passed: `{offline['passed']}`; transitions={offline['transition_count']}; "
        f"byte-identical={offline['byte_identical_replays']}; every-prefix resume identical={offline['all_prefix_resumes_identical']}."
    )
    if not offline["passed"]:
        raise RuntimeError("offline workspace gate failed")
    frozen = run_episode(
        {"game": "ar25", "arm": "frozen_injection", "config": config, "environments": str(args.environments)}
    )
    frozen_passed = bool(
        frozen["first_level_completed"]
        and frozen["actions"] == int(config["ar25_frozen_acceptance_actions"])
        and frozen["action_sequence"] == [1] + [2] * 11 + [3] * 5
        and frozen["replay_verified"]
    )
    append_status(
        "\n## Frozen-proposal live ar25 gate\n\n"
        f"- Passed: `{frozen_passed}`; actions={frozen['actions']}; levels={frozen['levels_completed']}; "
        f"prior_decisions={frozen['prior_decisions']}; replay={frozen['replay_verified']}."
    )
    if not frozen_passed:
        raise RuntimeError("frozen-proposal compatibility gate failed")
    baseline = run_episode(
        {"game": "ar25", "arm": "workspace_no_qwen", "config": config, "environments": str(args.environments)}
    )
    live = run_episode(
        {"game": "ar25", "arm": "parallel_qwen", "config": config, "environments": str(args.environments)}
    )
    live_passed = bool(
        live["first_level_completed"]
        and live["actions"] <= int(config["ar25_live_acceptance_actions"])
        and live["replay_verified"]
        and live["post_initial_qwen_requests"] >= 1
        and live["qwen_changed_decisions"] >= 1
    )
    append_status(
        "\n## Live parallel ar25 gate\n\n"
        f"- Passed: `{live_passed}`; actions={live['actions']}; levels={live['levels_completed']}; "
        f"Qwen tasks={live['qwen_task_count']}; post-initial requests={live['post_initial_qwen_requests']}; "
        f"Qwen-changed decisions={live['qwen_changed_decisions']}; replay={live['replay_verified']}.\n"
        f"- Same-workspace no-Qwen baseline: actions={baseline['actions']}, levels={baseline['levels_completed']}."
    )
    summary = {
        "gates_passed": bool(offline["passed"] and frozen_passed and live_passed),
        "offline": offline,
        "frozen_injection": frozen,
        "workspace_no_qwen": baseline,
        "parallel_qwen": live,
    }
    WS.atomic_json(HERE / "artifacts" / "gates" / "summary.json", summary)
    return summary


def freeze_cross_game() -> dict[str, Any]:
    gates = json.loads((HERE / "artifacts" / "gates" / "summary.json").read_text(encoding="utf-8"))
    if not gates.get("gates_passed"):
        raise RuntimeError("ar25 gates did not pass; held-out freeze is forbidden")
    files = [
        "PROPOSAL.md",
        "PROMPT.txt",
        "config.json",
        "experiment.py",
        "workspace.py",
        "qwen_protocol.py",
        "qwen_worker.py",
    ]
    manifest = {
        "protocol": "parallel-cognitive-workspace-cross-game-freeze-v0.1",
        "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": {name: V0.BASE.file_hash(HERE / name) for name in files},
        "development_gate_summary_sha256": V0.BASE.file_hash(HERE / "artifacts" / "gates" / "summary.json"),
        "held_out_games": load_config()["test_games"],
        "no_held_out_actions_executed": True,
    }
    WS.atomic_json(HERE / "CROSS_GAME_FROZEN_MANIFEST.json", manifest)
    append_status(
        "\n## Cross-game freeze\n\n"
        "- All ar25 gates passed. Code, prompt, compiler, schedule, safety rules, model configuration, and development outcomes are hash-frozen.\n"
        "- No held-out action had been executed when `CROSS_GAME_FROZEN_MANIFEST.json` was written."
    )
    return manifest


def run_heldout(args: argparse.Namespace) -> dict[str, Any]:
    manifest = HERE / "CROSS_GAME_FROZEN_MANIFEST.json"
    if not manifest.exists():
        raise RuntimeError("cross-game manifest is missing")
    config = load_config()
    games = [str(item) for item in config["test_games"]]
    control_tasks = [
        {"game": game, "arm": arm, "config": config, "environments": str(args.environments)}
        for game in games
        for arm in ("workspace_no_qwen", "one_shot_v0")
    ]
    results = []
    with ProcessPoolExecutor(max_workers=4) as executor:
        futures = {executor.submit(run_episode, task): task for task in control_tasks}
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            append_status(
                f"- Held-out control partial `{result['game']}/{result['arm']}`: "
                f"actions={result['actions']}, levels={result['levels_completed']}, replay={result['replay_verified']}."
            )
    # One resident server slot: live environments are sequential, while R2 and Qwen
    # remain genuinely concurrent within each workspace.
    for game in games:
        result = run_episode(
            {"game": game, "arm": "parallel_qwen", "config": config, "environments": str(args.environments)}
        )
        results.append(result)
        append_status(
            f"- Held-out live partial `{game}/parallel_qwen`: actions={result['actions']}, "
            f"levels={result['levels_completed']}, Qwen-changed={result['qwen_changed_decisions']}, "
            f"replay={result['replay_verified']}."
        )
    summary = analyze_results(results)
    WS.atomic_json(HERE / "artifacts" / "heldout-primary-summary.json", summary)
    write_results(summary)
    return summary


def analyze_results(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    by_game: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        by_game[result["game"]][result["arm"]] = result
    comparisons = []
    improvements = []
    for game in load_config()["test_games"]:
        arms = by_game[game]
        baseline = arms["workspace_no_qwen"]
        one_shot = arms["one_shot_v0"]
        live = arms["parallel_qwen"]
        completion_gain = bool(
            live["first_level_completed"]
            and not baseline["first_level_completed"]
            and not one_shot["first_level_completed"]
        )
        savings = None
        if all(item["first_level_completed"] for item in (baseline, one_shot, live)):
            reference = min(int(baseline["actions"]), int(one_shot["actions"]))
            savings = (reference - int(live["actions"])) / reference if reference else 0.0
        improved = completion_gain or (savings is not None and savings >= 0.25)
        if improved:
            improvements.append(game)
        comparisons.append(
            {
                "game": game,
                "completion_gain_over_both": completion_gain,
                "savings_fraction_over_better_control": savings,
                "improved": improved,
                "live_post_initial_requests": live["post_initial_qwen_requests"],
                "live_qwen_changed_decisions": live["qwen_changed_decisions"],
            }
        )
    cn = by_game["cn04"]
    negative_regression = bool(
        (cn["workspace_no_qwen"]["first_level_completed"] or cn["one_shot_v0"]["first_level_completed"])
        and not cn["parallel_qwen"]["first_level_completed"]
    )
    causal_outside = any(
        by_game[game]["parallel_qwen"]["qwen_changed_decisions"] > 0
        and by_game[game]["parallel_qwen"]["post_initial_qwen_requests"] > 0
        for game in improvements
        if game != "cn04"
    )
    if any(game in {"cd82", "wa30"} for game in improvements) and causal_outside and not negative_regression:
        verdict = "ONLINE_PROMISING"
    elif negative_regression:
        verdict = "NEGATIVE"
    else:
        verdict = "ANCHOR_ONLY"
    return {
        "verdict": verdict,
        "improved_games": improvements,
        "negative_control_regression": negative_regression,
        "causal_outside_anchor": causal_outside,
        "comparisons": comparisons,
        "all_replay_verified": all(item["replay_verified"] for item in results),
        "arms": sorted(results, key=lambda item: (item["game"], item["arm"])),
    }


def write_results(summary: dict[str, Any]) -> None:
    rows = [
        f"| {item['game']} | {item['arm']} | {item['actions']} | {item['levels_completed']} | "
        f"{item['qwen_task_count']} | {item['post_initial_qwen_requests']} | "
        f"{item['qwen_changed_decisions']} | {item['replay_verified']} |"
        for item in summary["arms"]
    ]
    text = "\n".join(
        [
            "# Parallel Cognitive Workspace v0 — Results",
            "",
            f"Verdict: **{summary['verdict']}**.",
            "",
            "| Game | Arm | Actions | Levels | Qwen calls | Post-initial calls | Qwen-changed decisions | Replay verified |",
            "|---|---|---:|---:|---:|---:|---:|---|",
            *rows,
            "",
            "## Held-out comparisons",
            "",
            "```json",
            json.dumps(summary["comparisons"], indent=2, sort_keys=True),
            "```",
            "",
            f"Improved games: `{summary['improved_games']}`.",
            f"Negative-control regression: `{summary['negative_control_regression']}`.",
            f"All ledgers replay-verified: `{summary['all_replay_verified']}`.",
            "",
        ]
    )
    (HERE / "RESULTS.md").write_text(text, encoding="utf-8")


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    sub = value.add_subparsers(dest="command", required=True)
    sub.add_parser("offline")
    gates = sub.add_parser("gates")
    gates.add_argument("--environments", type=Path, default=ENVIRONMENTS)
    sub.add_parser("freeze")
    heldout = sub.add_parser("heldout")
    heldout.add_argument("--environments", type=Path, default=ENVIRONMENTS)
    arm = sub.add_parser("run-arm")
    arm.add_argument("game")
    arm.add_argument("arm")
    arm.add_argument("--environments", type=Path, default=ENVIRONMENTS)
    return value


def main() -> None:
    args = parser().parse_args()
    if args.command == "offline":
        result = offline_gate()
    elif args.command == "gates":
        result = run_gates(args)
    elif args.command == "freeze":
        result = freeze_cross_game()
    elif args.command == "heldout":
        result = run_heldout(args)
    else:
        result = run_episode(
            {"game": args.game, "arm": args.arm, "config": load_config(), "environments": str(args.environments)}
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
