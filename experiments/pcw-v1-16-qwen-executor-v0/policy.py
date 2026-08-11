"""Sole concrete-action policy head for live Executor arms."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import executor_worker
import protocol


@dataclass(frozen=True, slots=True)
class PolicySelection:
    decision: Any | None
    plan: Any | None
    snapshot: dict[str, Any]
    executor: executor_worker.ExecutorCallResult
    graph_refs: dict[str, Any] | None


class ExecutorPolicy:
    """Uses R2 for predictions/constraints and Executor for action selection.

    No method in this class calls ``ProspectiveController.plan`` or the frozen
    controller's ``plan`` method. This is the mechanical firewall that keeps
    R2 from acting as a competing policy head in Arms B/C.
    """

    def __init__(self, *, base: Any, controller: Any, worker: executor_worker.QwenExecutorWorker) -> None:
        self.base = base
        self.controller = controller
        self.worker = worker

    def prediction_matrix(
        self, legal_actions: Sequence[int], *, observation_digest: str, basis_revision: int,
    ) -> tuple[Any, ...]:
        records = self.controller._active_records()
        live_bindings = []
        self.controller.last_plan_records = {}
        for record in records:
            alternative = self.base.PC.GroundingAlternative(
                candidate_id=record.candidate_id,
                template_hash=record.template_hash,
                substitution=(), effect_pair=record.effect_pair,
            )
            live = self.base.PC.LiveBinding.build(
                schema_object_id=record.schema_object_id,
                alternative=alternative,
                operator=record.operator,
                relative2=tuple(record.pair_binding.relative2),
                action_models=self.base.LC._modal_models(record.pair_binding),
                confirmations=record.prospective_confirmations if record.control_eligible else 0,
            )
            live_bindings.append(live)
            self.controller.last_plan_records[live.binding_id] = record
        return self.base.PC.ProspectiveController(live_bindings).prediction_matrix(
            legal_actions,
            observation_digest=str(observation_digest),
            basis_revision=int(basis_revision),
        )

    def _plan_from_executor(
        self, *, proposal: protocol.ExecutorProposal, predictions: Sequence[Any],
        observation_digest: str, basis_revision: int,
    ) -> tuple[Any, Any]:
        if proposal.selected_action is None:
            return None, None
        action = int(proposal.selected_action)
        selected_predictions = tuple(
            item for item in predictions if int(item.action_id) == action and item.modeled
        )
        selected_ids = tuple(sorted(item.prediction_id for item in selected_predictions))
        selected_records = [
            self.controller.last_plan_records.get(item.binding_id)
            for item in selected_predictions
        ]
        if any(record is not None and record.prospective_confirmations < 1 for record in selected_records):
            mode = "probe"
            self.controller.probe_decisions += 1
        elif selected_predictions:
            mode = "control"
            self.controller.control_decisions += 1
        else:
            mode = "fallback"
        plan_identity = {
            "source": protocol.WORKER_ID,
            "request_id": proposal.request_id,
            "basis_revision": int(basis_revision),
            "observation_digest": str(observation_digest),
            "action_id": action,
            "prediction_ids": [item.prediction_id for item in predictions],
        }
        plan = self.base.PC.ControlPlan(
            plan_id=self.base.PC.stable_id("executor-plan", plan_identity),
            basis_revision=int(basis_revision),
            observation_digest=str(observation_digest),
            mode=mode,
            action_id=action,
            fallback_action_id=action,
            predictions=tuple(predictions),
            selected_prediction_ids=selected_ids,
            discrimination_pairs=0,
            probe_basis="executor-ranked-proposal" if mode == "probe" else None,
        )
        self.controller.last_plan = plan
        record = next((item for item in selected_records if item is not None), None)
        decision = self.base.LC.Q0.Decision(
            action_id=action,
            fallback_action_id=action,
            reason="qwen-executor-ranked-proposal",
            template_hash=None if record is None else record.template_hash,
            residual_before=None if not selected_predictions else selected_predictions[0].current_residual,
            predicted_residual_after=None if not selected_predictions else selected_predictions[0].predicted_residual,
            prior_used=bool(selected_predictions),
        )
        return decision, plan

    def _persist_plan(
        self, *, root: Any, workspace_id: str, state: Any, plan: Any,
        proposal: protocol.ExecutorProposal,
    ) -> tuple[Any, dict[str, Any]]:
        latest_frame = max(
            self.base.EG.find_objects(state, kind="frame"),
            key=lambda item: (item.created_revision, item.object_id), default=None,
        )
        prediction_objects: dict[str, str] = {}
        for prediction in plan.predictions:
            record = self.controller.last_plan_records.get(prediction.binding_id)
            dependencies: list[str] = []
            if record is not None and record.graph_binding_id is not None:
                dependencies.append(record.graph_binding_id)
            if latest_frame is not None:
                dependencies.append(latest_frame.object_id)
            state, object_id = self.base.ensure_graph_object(
                root, workspace_id, state,
                kind="prediction", created_by="r2",
                identity={"prediction_id": prediction.prediction_id},
                payload={
                    "prediction_id": prediction.prediction_id,
                    "binding_id": prediction.binding_id,
                    "candidate_id": prediction.candidate_id,
                    "intervention_ref": self.base.opaque_intervention(workspace_id, int(prediction.action_id)),
                    "basis_revision": prediction.basis_revision,
                    "observation_digest": plan.observation_digest,
                    "current_residual": prediction.current_residual,
                    "predicted_residual": prediction.predicted_residual,
                    "predicted_delta": None if prediction.predicted_delta is None else list(prediction.predicted_delta),
                    "model_support": prediction.model_support,
                    "modeled": prediction.modeled,
                    "horizon": 1,
                },
                dependency_ids=tuple(sorted(set(dependencies))),
                event_key=f"executor-prospective-prediction:{prediction.prediction_id}",
            )
            prediction_objects[prediction.prediction_id] = object_id
        selected_objects = tuple(
            prediction_objects[item] for item in plan.selected_prediction_ids
            if item in prediction_objects
        )
        selected_candidate = next(
            item for item in proposal.candidates if item.action_id == proposal.selected_action
        )
        dependency_objects = tuple(sorted({
            dependency for dependency in selected_candidate.dependencies
            if self.base.EG.get_object(state, dependency) is not None
        } | set(selected_objects)))
        state, proposal_id = self.base.ensure_graph_object(
            root, workspace_id, state,
            kind="action_proposal", created_by="qwen_executor",
            identity={"executor_request_id": proposal.request_id, "plan_id": plan.plan_id},
            payload={
                "worker_context": protocol.WORKER_ID,
                "plan_id": plan.plan_id,
                "basis_revision": plan.basis_revision,
                "observation_digest": plan.observation_digest,
                "ranked_candidates": [asdict(item) for item in proposal.candidates],
                "selected_action": int(proposal.selected_action),
                "intervention_ref": self.base.opaque_intervention(workspace_id, int(plan.action_id)),
                "expected_checkpoint": selected_candidate.expected_checkpoint,
                "invalidate_on": list(selected_candidate.invalidate_on),
                "selected_prediction_ids": list(plan.selected_prediction_ids),
            },
            dependency_ids=dependency_objects,
            event_key=f"executor-action-proposal:{proposal.request_id}",
        )
        return state, {
            "proposal_object_id": proposal_id,
            "prediction_objects": prediction_objects,
            "selected_prediction_objects": list(selected_objects),
            "graph_revision_after_plan": state.revision,
            "executor_request_id": proposal.request_id,
        }

    def select(
        self, *, root: Any, workspace_id: str, state: Any,
        ledger_events: Sequence[Mapping[str, Any]], cognition: Any,
        legal_actions: Sequence[int], current_record: Mapping[str, Any],
        current_grid: Sequence[Sequence[int]], history: Sequence[Mapping[str, Any]],
        snapshot_config: Mapping[str, Any],
    ) -> tuple[PolicySelection, Any]:
        predictions = self.prediction_matrix(
            legal_actions,
            observation_digest=str(current_record["digest"]),
            basis_revision=int(state.revision),
        )
        prediction_documents = [self.base.PC.document(item) for item in predictions]
        report = self.controller.report()
        snapshot = protocol.build_snapshot(
            state=state, ledger_events=ledger_events, legal_actions=legal_actions,
            current_record=current_record, current_grid=current_grid, history=history,
            r2_workspace=self.base.r2_workspace_document(cognition, legal_actions),
            controller_report=report, prediction_matrix=prediction_documents,
            max_recent_transitions=int(snapshot_config["max_recent_transitions"]),
            max_bytes=int(snapshot_config["snapshot_max_bytes"]),
        )
        reasons = protocol.trigger_reasons(
            legal_actions=legal_actions, controller_report=report,
            prediction_matrix=prediction_documents,
        )
        if not reasons:
            raise protocol.ProtocolError("ELIGIBLE_STATE_NOT_REACHED")
        execution = self.worker.deliberate(snapshot, reasons)
        decision, plan = self._plan_from_executor(
            proposal=execution.proposal, predictions=predictions,
            observation_digest=str(current_record["digest"]),
            basis_revision=int(state.revision),
        )
        if decision is None:
            return PolicySelection(None, None, snapshot, execution, None), state
        state, graph_refs = self._persist_plan(
            root=root, workspace_id=workspace_id, state=state,
            plan=plan, proposal=execution.proposal,
        )
        return PolicySelection(decision, plan, snapshot, execution, graph_refs), state

    def settle(
        self, *, root: Any, workspace_id: str, state: Any,
        transition_event_id: str, action_commit_event_id: str,
        proposal: protocol.ExecutorProposal, after_record: Mapping[str, Any],
        adjudication: Mapping[str, Any] | None, proposal_object_id: str,
    ) -> tuple[dict[str, Any], Any, str]:
        candidate = next(item for item in proposal.candidates if item.action_id == proposal.selected_action)
        judgments = [] if adjudication is None else list(adjudication.get("judgments", ()))
        statuses = {str(item.get("status")) for item in judgments}
        if "refutes" in statuses:
            status = "VIOLATED"
        elif "supports" in statuses and statuses <= {"supports"}:
            status = "CONFIRMED"
        elif "supports" in statuses:
            status = "PARTIAL"
        else:
            status = "INCONCLUSIVE"
        document = {
            "request_id": proposal.request_id,
            "action_commit": action_commit_event_id,
            "actual_successor_transition": transition_event_id,
            "expected_checkpoint": candidate.expected_checkpoint,
            "observed_checkpoint": None if adjudication is None else dict(adjudication),
            "status": status,
            "discrepancy": None if status == "CONFIRMED" else list(candidate.invalidate_on),
            "after_observation_hash": str(after_record["digest"]),
        }
        blob = self.worker.ledger.put_blob(self.worker.workspace_root, document)
        self.worker.ledger.append_event(
            self.worker.workspace_root, workspace_id=self.worker.workspace_id,
            event_type="ExecutorResult", actor="coordinator",
            payload={"request_id": proposal.request_id, "result_blob": blob, "status": status, "transition_event_id": transition_event_id},
            event_id=f"executor-result:{proposal.request_id}:{transition_event_id}",
        )
        # The observed mismatch/confirmation is immediately restored to the
        # shared graph.  It is environment-authored because only the actual
        # successor can settle a prospective motor checkpoint.
        state, result_object_id = self.base.ensure_graph_object(
            root, workspace_id, state,
            kind="executor_result", created_by="environment",
            identity={
                "executor_request_id": proposal.request_id,
                "transition_event_id": transition_event_id,
            },
            payload=document,
            dependency_ids=(proposal_object_id,),
            event_key=f"executor-result-object:{proposal.request_id}:{transition_event_id}",
        )
        return document, state, result_object_id
