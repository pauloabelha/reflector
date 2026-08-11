"""Require semantic grounding before the first external action."""

from __future__ import annotations

from typing import Any


def _salient_schemas(base: Any, state: Any) -> list[dict[str, Any]]:
    schemas = sorted(
        base.EG.find_objects(state, kind="schema"),
        key=lambda item: (item.created_revision, item.object_id),
        reverse=True,
    )
    return [
        {
            "schema_object_id": item.object_id,
            "creator": item.created_by,
            "identity": dict(item.identity),
            "conditions": item.payload.get("conditions", ()),
            "preferred_consequence": item.payload.get("preferred_consequence"),
            "status": "available-for-binding",
        }
        for item in schemas[:5]
    ]


def install(base: Any, runtime: Any | None = None) -> None:
    if getattr(base, "_first_frame_explanation_installed", False):
        return
    base._first_frame_explanation_installed = True
    original = base.activate_then_maybe_queue_qwen

    def activate_then_maybe_queue_qwen(
        root: Any,
        workspace_id: str,
        state: Any,
        graph_events: Any,
        pending_qwen: Any,
        **kwargs: Any,
    ) -> Any:
        result = original(
            root, workspace_id, state, graph_events, pending_qwen, **kwargs
        )
        state, graph_events, pending, task_count, records = result
        history = kwargs["history"]
        if not kwargs["live_qwen"] or history or pending is None:
            return result
        if runtime is not None:
            runtime.update(
                status="explaining-first-frame",
                frame=[[int(cell) for cell in row] for row in kwargs["grid"]],
                turn=0,
                salient_schemas=_salient_schemas(base, state),
                r2_parallel_phase="frame-parsed; schemas activated; bindings available; awaiting Qwen merge",
            )
        # The first semantic turn is a prerequisite for action 1. It is fully
        # integrated here, so no resolved handle should delay an evidence-led
        # alias revision after the first observed action.
        state, _compilation = base.integrate_qwen(
            root,
            workspace_id,
            state,
            *pending,
            kwargs["profile"],
            action_count=0,
        )
        state, grounded = base.activate_visible_qwen(
            root,
            workspace_id,
            state,
            kwargs["controller"],
            kwargs["grid"],
            kwargs["legal"],
            history,
            kwargs["profile"],
            kwargs["activated"],
            0,
        )
        qwen_explanations = base.EG.find_objects(
            state, kind="explanation", created_by="qwen"
        )
        if not qwen_explanations:
            raise RuntimeError(
                "first-frame gate: Qwen produced no valid durable explanation; "
                "no environment action is permitted"
            )
        if runtime is not None:
            current = max(
                qwen_explanations,
                key=lambda item: (item.created_revision, item.object_id),
            )
            runtime.update(
                current_explanation={
                    "object_id": current.object_id,
                    "creator": current.created_by,
                    **dict(current.payload),
                },
                salient_schemas=_salient_schemas(base, state),
                r2_parallel_phase="Qwen merged; grounding and one-action ranking",
            )
        state, graph_events = base.graph_state(root)
        return state, graph_events, None, task_count, [*records, *grounded]

    base.activate_then_maybe_queue_qwen = activate_then_maybe_queue_qwen
