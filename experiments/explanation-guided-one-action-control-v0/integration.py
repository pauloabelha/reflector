"""Workspace persistence adapters for objective, explanation, and settlement."""

from __future__ import annotations

from typing import Any


def install(base: Any) -> None:
    if getattr(base, "_one_action_integration_installed", False):
        return
    base._one_action_integration_installed = True
    original_persist = base.persist_prospective_plan
    original_ingest = base.ingest_transition_graph
    original_apply_qwen = base.apply_qwen_compilation

    def apply_qwen(root: Any, workspace_id: str, state: Any, task_id: str, turn: Any, compilation: Any, profile: Any, *, action_count: int) -> Any:
        """Persist memory without manufacturing a semantic derivation chain."""
        notes = [item for item in compilation.get("accepted", ()) if item.get("kind") == "working_note"]
        semantic = {
            **dict(compilation),
            "accepted": [item for item in compilation.get("accepted", ()) if item.get("kind") != "working_note"],
        }
        state = original_apply_qwen(
            root, workspace_id, state, task_id, turn, semantic, profile,
            action_count=action_count,
        )
        for note in notes:
            state, _note_id = base.ensure_graph_object(
                root, workspace_id, state,
                kind="working_note", created_by="qwen",
                identity=note["identity"], payload=note["payload"],
                dependency_ids=tuple(note.get("dependency_ids", ())),
                event_key=f"qwen-working-note:{task_id}",
            )
        return state

    def persist(root: Any, workspace_id: str, state: Any, controller: Any, plan: Any) -> tuple[Any, dict[str, Any]]:
        if not base.EG.find_objects(state, kind="explanation", created_by="qwen"):
            raise RuntimeError(
                "action gate: no Qwen-authored explanation is durable in the workspace"
            )
        state, refs = original_persist(root, workspace_id, state, controller, plan)
        contract = controller.last_contract or {}
        latest_frame = max(
            base.EG.find_objects(state, kind="frame"),
            key=lambda item: (item.created_revision, item.object_id),
            default=None,
        )
        frame_dependencies = () if latest_frame is None else (latest_frame.object_id,)
        state, objective_id = base.ensure_graph_object(
            root, workspace_id, state,
            kind="objective", created_by="r2",
            identity={"workspace_id": workspace_id, "plan_id": plan.plan_id},
            payload={**dict(contract.get("objective", {})), "basis_revision": plan.basis_revision},
            dependency_ids=frame_dependencies,
            event_key=f"one-action-objective:{plan.plan_id}",
        )
        explanation_ids: list[str] = []
        for index, explanation in enumerate(contract.get("explanations", ())):
            binding_id = explanation.get("binding_object_id") or explanation.get("binding_id")
            schema_id = explanation.get("schema_object_id") or explanation.get("schema_id")
            # A recursive R2.1 binding ID is stable workspace identity, but it
            # is not itself an epistemic-graph object. Only graph IDs may be
            # dependency edges; both identities remain in the payload.
            binding_dependency = binding_id if isinstance(binding_id, str) and binding_id.startswith("eo:") else None
            dependencies = tuple(sorted(set((objective_id, *frame_dependencies, *((binding_dependency,) if binding_dependency else ())))))
            if explanation.get("schema_id"):
                # Exact interventions belong to the transient control
                # contract, not Qwen's canonical semantic projection. Keep
                # the grounded diagram and epistemic state durable without
                # leaking action tokens back into semantic cognition.
                payload = {
                    key: explanation[key]
                    for key in (
                        "kind", "epistemic_status", "schema_id", "ports",
                        "claim", "goal", "epistemic_evaluation",
                    )
                    if key in explanation
                }
                payload["open_question_count"] = len(explanation.get("open_questions", ()))
            else:
                payload = {key: value for key, value in explanation.items() if key != "binding_object_id"}
            state, explanation_id = base.ensure_graph_object(
                root, workspace_id, state,
                kind="control_explanation", created_by="r2",
                identity={
                    "objective_id": objective_id,
                    "schema_object_id": schema_id,
                    "binding_object_id": binding_id,
                    "plan_id": plan.plan_id,
                },
                payload=payload,
                dependency_ids=dependencies,
                event_key=f"one-action-explanation:{plan.plan_id}:{index}",
            )
            explanation_ids.append(explanation_id)
        state, rationale_id = base.ensure_graph_object(
            root, workspace_id, state,
            kind="decision_rationale", created_by="r2",
            identity={"plan_id": plan.plan_id, "protocol": "one-action-decision-v0"},
            payload={
                "selection_role": contract.get("selection_role"),
                "selection_rule": contract.get("selection_rule"),
                "candidate_count": contract.get("candidate_count"),
                # The semantic graph deliberately quarantines control-token
                # vocabulary.  This is the invariant, but not action data.
                "single_external_intervention": True,
                "repeated_identical_no_change_excluded": contract.get("repeated_identical_no_change_excluded", False),
            },
            dependency_ids=tuple(sorted({objective_id, *explanation_ids, refs["proposal_object_id"]})),
            event_key=f"one-action-rationale:{plan.plan_id}",
        )
        controller.last_contract = {
            **contract,
            "objective_object_id": objective_id,
            "explanation_object_ids": explanation_ids,
            "rationale_object_id": rationale_id,
        }
        prediction_objects = dict(refs.get("prediction_objects", {}))
        selected_prediction_objects = list(refs.get("selected_prediction_objects", ()))
        current = contract.get("current_explanation") or {}
        if not isinstance(current, dict):
            current = {}
        prediction = current.get("prediction") or {}
        if not isinstance(prediction, dict):
            prediction = {}
        binding_id = current.get("binding_id") or current.get("binding_object_id")
        selected_action = contract.get("selected_action")
        predicted_action = prediction.get("action")
        control_status = current.get("control_status")
        if (
            binding_id
            and selected_action is not None
            and predicted_action is not None
            and int(predicted_action) == int(selected_action)
            and control_status != "INELIGIBLE"
        ):
            prediction_id = f"r2.1:{plan.plan_id}"
            state, prediction_object_id = base.ensure_graph_object(
                root, workspace_id, state,
                kind="prediction", created_by="r2",
                identity={"prediction_id": prediction_id},
                payload={
                    "prediction_id": prediction_id,
                    "binding_id": str(binding_id),
                    "intervention_ref": base.opaque_intervention(
                        workspace_id, int(selected_action)
                    ),
                    "basis_revision": plan.basis_revision,
                    "observation_digest": plan.observation_digest,
                    "current_residual": prediction.get("residual_before"),
                    "predicted_residual": prediction.get("residual_after"),
                    "predicted_delta": prediction.get("actor_delta"),
                    "expected_progress": prediction.get("expected_progress"),
                    "model_support": current.get("epistemic_status"),
                    "modeled": prediction.get("actor_delta") is not None,
                    "horizon": 1,
                    "native_protocol": "r2.1-explanation-control-v1",
                },
                # Native R2 control explanations intentionally contain opaque
                # intervention questions (for example, a numbered action).
                # They are quarantined from Semantic Qwen.  Keep the durable
                # prediction on the same semantic-safe frame boundary used by
                # inherited predictions; the action proposal and settlement
                # retain the full control ancestry outside that projection.
                dependency_ids=frame_dependencies,
                event_key=f"r2.1-prediction:{plan.plan_id}",
            )
            prediction_objects[prediction_id] = prediction_object_id
            selected_prediction_objects.append(prediction_object_id)
            controller.pending_r2_prediction_id = prediction_id
        return state, {
            **refs,
            "objective_object_id": objective_id,
            "explanation_object_ids": explanation_ids,
            "rationale_object_id": rationale_id,
            "prediction_objects": prediction_objects,
            "selected_prediction_objects": selected_prediction_objects,
            "graph_revision_after_plan": state.revision,
        }

    def ingest(*args: Any, **kwargs: Any) -> Any:
        # Environment ingestion is already the durable successor evidence.
        # Keep all control wording and transient settlement detail outside the
        # semantic graph; otherwise a later semantic projection must reject it.
        return original_ingest(*args, **kwargs)

    base.persist_prospective_plan = persist
    base.ingest_transition_graph = ingest
    base.apply_qwen_compilation = apply_qwen
