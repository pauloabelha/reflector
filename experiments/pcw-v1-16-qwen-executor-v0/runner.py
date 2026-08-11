"""Explicit live B/C episode orchestration over the frozen v1.16 substrate."""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
import time
from typing import Any, Mapping

import executor_worker
import policy
import protocol


@dataclass(slots=True)
class ResourceAccounting:
    semantic_qwen_calls: int = 0
    executor_qwen_calls: int = 0
    executor_input_tokens: int = 0
    executor_output_tokens: int = 0
    executor_qwen_latency_s: float = 0.0
    python_calls: int = 0
    python_runtime_s: float = 0.0
    executor_snapshot_count: int = 0
    executor_snapshot_max_bytes: int = 0
    executor_model_snapshot_max_bytes: int = 0


class ExecutorEpisodeRunner:
    """A readable one-action closed loop; frozen helpers remain read-only."""

    def __init__(
        self, *, base: Any, frozen_config: Mapping[str, Any], experiment_config: Mapping[str, Any],
        arm: str, fifo: Any, artifact_root: Path, environments: Path,
    ) -> None:
        if arm not in {"arm-b", "arm-c"}:
            raise ValueError("ExecutorEpisodeRunner only runs Arms B/C")
        self.base = base
        self.frozen_config = dict(frozen_config)
        self.experiment_config = dict(experiment_config)
        self.arm = arm
        self.fifo = fifo
        self.artifact_root = artifact_root
        self.environments = environments
        self.game = str(experiment_config["game"])
        self.profile_id = str(experiment_config["profile"])
        self.workspace_id = f"{self.profile_id}--{self.game}--{arm}"
        self.root = artifact_root / arm / "workspace"
        self.recordings = artifact_root / arm / "recordings"
        self.accounting = ResourceAccounting()
        self.failure_funnel: Counter[str] = Counter()

    def _model_config(self) -> dict[str, Any]:
        return {
            **dict(self.frozen_config["qwen"]),
            **dict(self.experiment_config["executor"]),
        }

    def _append_start(self) -> None:
        if self.base.LEDGER.list_events(self.root):
            raise RuntimeError(f"live Executor run requires an empty workspace: {self.root}")
        self.base.LEDGER.append_event(
            self.root, workspace_id=self.workspace_id,
            event_type="WorkspaceStarted", actor="coordinator",
            payload={
                "protocol": self.experiment_config["protocol"],
                "source_protocol": self.frozen_config["workspace_protocol"],
                "game": self.game, "arm": self.arm,
                "sole_action_policy": protocol.WORKER_ID,
            },
        )

    def _initialize_environment(self) -> tuple[Any, Any, Any]:
        arcade, environment = self.base.BASE.open_environment(
            self.environments, self.recordings / "live", self.game
        )
        observation = environment.observation_space
        if observation is None:
            observation = environment.reset()
        if observation is None:
            arcade.close_scorecard()
            raise RuntimeError("ARC produced no initial observation")
        blob, record, _grid = self.base.store_observation(self.root, observation)
        self.base.LEDGER.append_event(
            self.root, workspace_id=self.workspace_id,
            event_type="InitialObservation", actor="environment",
            payload={
                "observation_blob": blob, "digest": record["digest"],
                "levels_completed": record["levels_completed"],
            },
        )
        return arcade, environment, observation

    def _semantic_step(
        self, *, state: Any, graph_events: Any, pending_qwen: Any,
        controller: Any, grid: Any, legal: Any, history: Any, profile: Any,
        activated: set[str], task_count: int,
    ) -> tuple[Any, Any, Any, int]:
        release_delay = int(self.frozen_config["qwen"].get("logical_release_delay_actions", 8))
        if pending_qwen is not None:
            queued = next(
                item for item in self.base.LEDGER.list_events(self.root)
                if item["event_type"] == "QwenTaskQueued" and item["payload"]["task_id"] == pending_qwen[0]
            )
            source_action = int(queued["payload"].get("source_action_count", len(history)))
            if len(history) >= source_action + release_delay:
                state, _compilation = self.base.integrate_qwen(
                    self.root, self.workspace_id, state, *pending_qwen, profile,
                    action_count=len(history),
                )
                self.accounting.semantic_qwen_calls += 1
                pending_qwen = None
        state, graph_events, pending_qwen, task_count, _records = self.base.activate_then_maybe_queue_qwen(
            self.root, self.workspace_id, state, graph_events, pending_qwen,
            live_qwen=True, controller=controller, grid=grid, legal=legal,
            history=history, profile=profile, activated=activated,
            config=self.frozen_config, fifo=self.fifo, task_count=task_count,
        )
        return state, graph_events, pending_qwen, task_count

    def _arbiter_commit(
        self, selection: policy.PolicySelection, state: Any,
        current_digest: str, legal: Any,
    ) -> dict[str, Any]:
        proposal = selection.executor.proposal
        action = proposal.selected_action
        if action is None or int(action) not in {int(item) for item in legal}:
            self.failure_funnel["ARBITER_REJECTED"] += 1
            raise protocol.ProtocolError("ARBITER_REJECTED_ILLEGAL_ACTION")
        if selection.snapshot["current_observation"]["hash"] != current_digest:
            self.failure_funnel["ARBITER_REJECTED"] += 1
            raise protocol.ProtocolError("ARBITER_REJECTED_STALE_PROPOSAL")
        events = self.base.LEDGER.list_events(self.root)
        if any(item["event_type"] == "TransitionCommitted" and int(item["seq"]) > int(selection.snapshot["decision_boundary"]["ledger_basis_seq"]) for item in events):
            self.failure_funnel["AUTHORITY_VIOLATION"] += 1
            raise protocol.ProtocolError("AUTHORITY_VIOLATION_SUCCESSOR_LEAKAGE")
        proposal_events = [
            item for item in events
            if item["event_id"] == selection.executor.proposal_event_id
        ]
        if len(proposal_events) != 1 or proposal_events[0]["actor"] != "qwen_executor":
            self.failure_funnel["AUTHORITY_VIOLATION"] += 1
            raise protocol.ProtocolError("AUTHORITY_VIOLATION_PROPOSAL_SOURCE")
        if any(
            item["event_type"] == "ActionDecision"
            and item["actor"] != "qwen_executor"
            for item in events
        ):
            self.failure_funnel["AUTHORITY_VIOLATION"] += 1
            raise protocol.ProtocolError("AUTHORITY_VIOLATION_COMPETING_POLICY")
        candidate = next(
            item for item in proposal.candidates if item.action_id == proposal.selected_action
        )
        committed_transitions = {
            str(item["event_id"])
            for item in events if item["event_type"] == "TransitionCommitted"
        }
        observation_alias = str(selection.snapshot["current_observation"]["reference"])
        observation_reference = str(
            selection.snapshot["dependency_aliases"][observation_alias]
        )
        for dependency in candidate.dependencies:
            if dependency == observation_reference or dependency in committed_transitions:
                continue
            graph_object = self.base.EG.get_object(state, dependency)
            if graph_object is None or dependency in state._index.invalidated:
                self.failure_funnel["ARBITER_REJECTED"] += 1
                raise protocol.ProtocolError("ARBITER_REJECTED_DEAD_DEPENDENCY")
            support, contradiction = state._index.evidence.get(dependency, (0, 0))
            if contradiction > support:
                self.failure_funnel["ARBITER_REJECTED"] += 1
                raise protocol.ProtocolError("ARBITER_REJECTED_HARD_CONTRADICTION")
        checkpoint = candidate.expected_checkpoint
        if (
            int(checkpoint.get("horizon_steps", 0)) != 1
            or not str(checkpoint.get("observable_type", "")).strip()
            or not str(checkpoint.get("direction", "")).strip()
        ):
            self.failure_funnel["ARBITER_REJECTED"] += 1
            raise protocol.ProtocolError("ARBITER_REJECTED_NON_PROSPECTIVE_CHECKPOINT")
        return self.base.LEDGER.append_event(
            self.root, workspace_id=self.workspace_id,
            event_type="ActionCommit", actor="arbiter",
            payload={
                "request_id": selection.executor.request_id,
                "proposal_event_id": selection.executor.proposal_event_id,
                "snapshot_hash": selection.snapshot["snapshot_hash"],
                "observation_digest": current_digest,
                "action_id": int(action), "data": {},
                "one_primitive_action": True,
            },
        )

    def run(self) -> dict[str, Any]:
        started = time.perf_counter()
        self._append_start()
        arcade, environment, observation = self._initialize_environment()
        initial_event = next(
            item for item in self.base.LEDGER.list_events(self.root)
            if item["event_type"] == "InitialObservation"
        )
        initial_blob = self.base.LEDGER.read_blob(self.root, initial_event["payload"]["observation_blob"])
        initial_grid = self.base.grid_value(initial_blob["grid"])
        legal = self.base.BASE.simple_legal_actions(environment, observation)
        cognition, controller, history, activated = self.base.rebuild_controller(
            self.root, initial_grid, legal, self.frozen_config
        )
        state, graph_events = self.base.graph_state(self.root)
        state, _entities = self.base.ingest_initial_graph(
            self.root, self.workspace_id, state, cognition, initial_grid, legal
        )
        state, graph_events = self.base.graph_state(self.root)
        profile = dict(self.frozen_config["profiles"][self.profile_id])
        worker = executor_worker.QwenExecutorWorker(
            ledger=self.base.LEDGER, fifo=self.fifo, workspace_root=self.root,
            workspace_id=self.workspace_id, arm=self.arm,
            model_config=self._model_config(), python_config=self.experiment_config["python"],
        )
        action_policy = policy.ExecutorPolicy(base=self.base, controller=controller, worker=worker)
        pending_qwen = None
        task_count = 0
        stop_reason = "action-budget"
        executor_results: list[dict[str, Any]] = []
        first_executor_chain: dict[str, Any] | None = None
        try:
            while len(history) < int(self.experiment_config["action_budget"]):
                terminal_state, before_record, grid = self.base.control_observation(observation)
                if terminal_state is not None:
                    stop_reason = f"terminal-{terminal_state.lower().replace('_', '-')}"
                    break
                assert before_record is not None and grid is not None
                if int(before_record["levels_completed"]) >= 1:
                    stop_reason = "first-level-completed"
                    break
                legal = self.base.BASE.simple_legal_actions(environment, observation)
                if not legal:
                    stop_reason = "no-legal-primitive-action"
                    break

                state, graph_events, pending_qwen, task_count = self._semantic_step(
                    state=state, graph_events=graph_events, pending_qwen=pending_qwen,
                    controller=controller, grid=grid, legal=legal, history=history,
                    profile=profile, activated=activated, task_count=task_count,
                )
                try:
                    selection, state = action_policy.select(
                        root=self.root, workspace_id=self.workspace_id, state=state,
                        ledger_events=self.base.LEDGER.list_events(self.root), cognition=cognition,
                        legal_actions=legal, current_record=before_record,
                        current_grid=grid, history=history,
                        snapshot_config=self.experiment_config["executor"],
                    )
                except (protocol.ProtocolError, RuntimeError) as error:
                    stage = str(error)
                    if isinstance(error, RuntimeError):
                        failure_code = "EXECUTOR_TRANSPORT_OR_PARSE_FAILURE"
                    else:
                        failure_code = stage if stage.isupper() else "SNAPSHOT_OR_TOOLING_INSUFFICIENT"
                    self.failure_funnel[failure_code] += 1
                    stop_reason = stage.lower().replace("_", "-")
                    break
                self.failure_funnel.update(selection.executor.failure_stages)
                self.accounting.executor_snapshot_count += 1
                self.accounting.executor_snapshot_max_bytes = max(
                    self.accounting.executor_snapshot_max_bytes,
                    int(selection.snapshot["encoded_bytes"]),
                )
                self.accounting.executor_model_snapshot_max_bytes = max(
                    self.accounting.executor_model_snapshot_max_bytes,
                    int(protocol.model_snapshot(selection.snapshot)["encoded_bytes"]),
                )
                self.accounting.executor_qwen_calls += selection.executor.qwen_calls
                self.accounting.executor_input_tokens += selection.executor.input_tokens
                self.accounting.executor_output_tokens += selection.executor.output_tokens
                self.accounting.executor_qwen_latency_s += selection.executor.qwen_latency_s
                self.accounting.python_calls += selection.executor.python_calls
                self.accounting.python_runtime_s += selection.executor.python_runtime_s
                if selection.decision is None or selection.plan is None or selection.graph_refs is None:
                    stop_reason = "executor-abstained"
                    break
                decision = selection.decision
                prospective_plan = selection.plan
                prospective_refs = selection.graph_refs
                decision_document = {
                    "decision": asdict(decision),
                    "policy_source": protocol.WORKER_ID,
                    "baseline_candidate_in_live_controller": None,
                    "prospective_plan": self.base.PC.document(prospective_plan),
                    "prospective_graph": prospective_refs,
                    "executor_request_id": selection.executor.request_id,
                    "executor_proposal": protocol.proposal_document(selection.executor.proposal),
                    "controller_constraints": controller.report(),
                }
                decision_blob = self.base.LEDGER.put_blob(self.root, decision_document)
                decision_event = self.base.LEDGER.append_event(
                    self.root, workspace_id=self.workspace_id,
                    event_type="ActionDecision", actor="qwen_executor",
                    payload={
                        "decision_blob": decision_blob,
                        "observation_digest": before_record["digest"],
                        "proposal_object_id": prospective_refs["proposal_object_id"],
                        "graph_revision": state.revision,
                        "executor_request_id": selection.executor.request_id,
                    },
                )
                try:
                    commit = self._arbiter_commit(
                        selection, state, str(before_record["digest"]), legal
                    )
                except protocol.ProtocolError as error:
                    stage = str(error)
                    self.failure_funnel[stage] += 1
                    stop_reason = stage.lower().replace("_", "-")
                    break
                before_blob = self.base.LEDGER.put_blob(
                    self.root, {"record": before_record, "grid": [list(row) for row in grid]}
                )
                pending = self.base.LEDGER.append_event(
                    self.root, workspace_id=self.workspace_id,
                    event_type="ActionPending", actor="arbiter",
                    payload={
                        "before_blob": before_blob,
                        "before_digest": before_record["digest"],
                        "action_id": int(decision.action_id), "data": {},
                        "decision_blob": decision_blob,
                        "proposal_object_id": prospective_refs["proposal_object_id"],
                        "graph_revision": state.revision,
                        "action_commit_event_id": commit["event_id"],
                    },
                )
                successor = self.base.execute_action(
                    environment, self.game, int(decision.action_id), {}, decision.reason
                )
                _after_blob_hash, after_record, after_grid = self.base.store_observation(self.root, successor)
                after_blob = self.base.LEDGER.put_blob(
                    self.root, {"record": after_record, "grid": [list(row) for row in after_grid]}
                )
                learning = controller.observe(int(decision.action_id), grid, after_grid)
                cognition.observe_transition(int(decision.action_id), after_grid)
                adjudication = learning.get("prospective_adjudication")
                prospective_evidence = dict(adjudication) if isinstance(adjudication, Mapping) else None
                judgments: list[dict[str, str]] = []
                evidence_dependencies = [prospective_refs["proposal_object_id"]]
                if prospective_evidence is not None:
                    for item in prospective_evidence.get("judgments", ()):
                        prediction_object = prospective_refs["prediction_objects"].get(str(item.get("prediction_id")))
                        if prediction_object is None:
                            continue
                        evidence_dependencies.append(prediction_object)
                        if item.get("status") in {"supports", "refutes"}:
                            judgments.append({"kind": str(item["status"]), "target_id": prediction_object})
                evidence_blob = None if prospective_evidence is None else self.base.LEDGER.put_blob(self.root, prospective_evidence)
                transition = self.base.LEDGER.append_event(
                    self.root, workspace_id=self.workspace_id,
                    event_type="TransitionCommitted", actor="environment",
                    payload={
                        "pending_event_id": pending["event_id"],
                        "action_commit_event_id": commit["event_id"],
                        "before_blob": before_blob, "after_blob": after_blob,
                        "before_digest": before_record["digest"],
                        "after_digest": after_record["digest"],
                        "action_id": int(decision.action_id),
                        "levels_completed": after_record["levels_completed"],
                        "prospective_evidence_blob": evidence_blob,
                        "prospective_judgments": judgments,
                        "prospective_dependency_ids": evidence_dependencies,
                    },
                )
                next_legal = self.base.BASE.simple_legal_actions(environment, successor)
                state = self.base.ingest_transition_graph(
                    self.root, self.workspace_id, state, cognition,
                    transition_id=transition["event_id"], before_grid=grid,
                    after_grid=after_grid, before_record=before_record,
                    after_record=after_record, legal=next_legal,
                    intervention_ref=self.base.opaque_intervention(self.workspace_id, int(decision.action_id)),
                    judgments=judgments, prospective_evidence=prospective_evidence,
                    evidence_dependency_ids=tuple(evidence_dependencies),
                )
                settled, state, result_object_id = action_policy.settle(
                    root=self.root, workspace_id=self.workspace_id, state=state,
                    transition_event_id=transition["event_id"],
                    action_commit_event_id=commit["event_id"],
                    proposal=selection.executor.proposal,
                    after_record=after_record,
                    adjudication=prospective_evidence,
                    proposal_object_id=prospective_refs["proposal_object_id"],
                )
                executor_results.append(settled)
                if first_executor_chain is None:
                    first_executor_chain = {
                        "workspace_prefix_seq": selection.snapshot["decision_boundary"]["ledger_basis_seq"],
                        "trigger": next(
                            item["payload"]["trigger_reasons"]
                            for item in self.base.LEDGER.list_events(self.root)
                            if item["event_type"] == "ExecutorRequest"
                            and item["payload"]["request_id"] == selection.executor.request_id
                        ),
                        "request_id": selection.executor.request_id,
                        "snapshot_hash": selection.snapshot["snapshot_hash"],
                        "proposal": protocol.proposal_document(selection.executor.proposal),
                        "decision_event_id": decision_event["event_id"],
                        "action_commit_event_id": commit["event_id"],
                        "successor_transition_id": transition["event_id"],
                        "settlement": settled,
                        "settlement_workspace_object_id": result_object_id,
                    }
                history = self.base._history(self.base.LEDGER.list_events(self.root), self.root)
                observation = successor
                self.base.LEDGER.write_cursor(
                    self.root, "environment",
                    ledger_seq=self.base.LEDGER.list_events(self.root)[-1]["seq"],
                    graph_revision=state.revision,
                    metadata={"actions": len(history)},
                )
                if int(after_record["levels_completed"]) >= 1:
                    stop_reason = "first-level-completed"
                    break
            if pending_qwen is not None:
                state, _compilation = self.base.integrate_qwen(
                    self.root, self.workspace_id, state, *pending_qwen, profile,
                    action_count=len(history),
                )
                self.accounting.semantic_qwen_calls += 1
        finally:
            arcade.close_scorecard()

        replay_verified = self.base.verify_replay(
            self.root, self.game, self.environments, self.recordings / "factual-replay"
        )
        if not replay_verified:
            self.failure_funnel["REPLAY_FAILURE"] += 1
        events = self.base.LEDGER.list_events(self.root)
        executor_diagnostics = [
            {
                "event_id": item["event_id"],
                "event_type": item["event_type"],
                "request_id": item["payload"].get("request_id"),
                "reason": item["payload"].get("rejection_reason"),
                "blob": item["payload"].get("proposal_blob")
                or item["payload"].get("computation_blob"),
            }
            for item in events
            if item["event_type"] == "ExecutorProposal"
            and item["payload"].get("rejected")
        ]
        support_authority_violations = sum(
            edge.kind in {"supports", "refutes", "invalidates"} and edge.created_by != "environment"
            for edge in state.edges
        )
        if support_authority_violations:
            self.failure_funnel["AUTHORITY_VIOLATION"] += support_authority_violations
        final_record = self.base.BASE.observation_record(observation)
        result = {
            "protocol": self.experiment_config["protocol"],
            "source_protocol": self.frozen_config["workspace_protocol"],
            "arm_id": self.arm, "game": self.game,
            "initial_digest": initial_blob["record"]["digest"],
            "final_digest": final_record["digest"],
            "actions": len(history),
            "action_sequence": [int(item["action_id"]) for item in history],
            "levels_completed": int(final_record["levels_completed"]),
            "stop_reason": stop_reason,
            "replay_verified": replay_verified,
            "support_authority_violations": support_authority_violations,
            "sole_action_policy": protocol.WORKER_ID,
            "executor_results": executor_results,
            "first_executor_chain": first_executor_chain,
            "failure_funnel": dict(sorted(self.failure_funnel.items())),
            "executor_diagnostics": executor_diagnostics,
            "resource_accounting": asdict(self.accounting),
            "elapsed_s": time.perf_counter() - started,
            "workspace_head_before_stop": events[-1]["event_hash"],
        }
        self.base.LEDGER.append_event(
            self.root, workspace_id=self.workspace_id,
            event_type="WorkspaceStopped", actor="coordinator",
            payload={"reason": stop_reason, "result_hash": protocol.stable_hash(result)},
        )
        self.base.LEDGER.atomic_json(self.artifact_root / self.arm / "result.json", result)
        return result
