"""Exact prospective evidence return for the v1.9 shared workspace.

This module does not assign support.  It identifies which already-durable
environment judgments resulted from the predictions selected by an R2 plan,
then builds an action-blind semantic packet that can be linked to a Qwen schema
as structured criticism.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence


RETURN_STATUS = "prospective-evidence-return"


def object_map(state: Any) -> dict[str, Any]:
    return {item.object_id: item for item in state.objects}


def selected_prediction_objects(
    state: Any, dependency_ids: Sequence[str]
) -> tuple[str, ...]:
    """Return only prediction graph objects explicitly selected by the plan."""

    objects = object_map(state)
    proposals = [
        objects[value]
        for value in dependency_ids
        if value in objects and objects[value].kind == "action_proposal"
    ]
    if len(proposals) != 1:
        return ()
    selected = {
        str(value)
        for value in proposals[0].payload.get("selected_prediction_objects", ())
    }
    return tuple(
        sorted(
            value
            for value in dependency_ids
            if value in selected
            and value in objects
            and objects[value].kind == "prediction"
        )
    )


def selected_judgments(
    state: Any,
    dependency_ids: Sequence[str],
    judgments: Sequence[Mapping[str, str]],
) -> tuple[dict[str, str], ...]:
    selected = set(selected_prediction_objects(state, dependency_ids))
    return tuple(
        dict(item)
        for item in judgments
        if str(item.get("target_id")) in selected
        and item.get("kind") in {"supports", "refutes"}
    )


def prediction_schema_id(state: Any, prediction_object_id: str) -> str | None:
    objects = object_map(state)
    prediction = objects.get(str(prediction_object_id))
    if prediction is None or prediction.kind != "prediction":
        return None
    binding = next(
        (
            objects[value]
            for value in prediction.dependency_ids
            if value in objects and objects[value].kind == "binding"
        ),
        None,
    )
    if binding is None:
        return None
    return next(
        (
            value
            for value in binding.dependency_ids
            if value in objects
            and objects[value].kind == "schema"
            and objects[value].created_by == "qwen"
        ),
        None,
    )


def cumulative_evidence_packet(state: Any, schema_id: str) -> dict[str, Any]:
    """Exact selected-prediction outcomes for one Qwen schema, in graph order."""

    objects = object_map(state)
    rows: list[dict[str, Any]] = []
    evidence_ids: list[str] = []
    for evidence in sorted(
        (item for item in state.objects if item.kind == "environment_evidence"),
        key=lambda item: (item.created_revision, item.object_id),
    ):
        prospective = evidence.payload.get("prospective")
        if not isinstance(prospective, Mapping):
            continue
        proposal = next(
            (
                objects[value]
                for value in evidence.dependency_ids
                if value in objects and objects[value].kind == "action_proposal"
            ),
            None,
        )
        if proposal is None or proposal.payload.get("mode") != "probe":
            continue
        selected_objects = {
            str(value)
            for value in proposal.payload.get("selected_prediction_objects", ())
        }
        predictions = {
            str(objects[value].payload.get("prediction_id")): objects[value]
            for value in evidence.dependency_ids
            if value in selected_objects
            and value in objects
            and objects[value].kind == "prediction"
            and prediction_schema_id(state, value) == schema_id
        }
        matched = False
        for judgment in prospective.get("judgments", ()):
            if not isinstance(judgment, Mapping):
                continue
            prediction = predictions.get(str(judgment.get("prediction_id")))
            if prediction is None:
                continue
            matched = True
            rows.append(
                {
                    "evidence_id": evidence.object_id,
                    "prediction_object_id": prediction.object_id,
                    "binding_id": judgment.get("binding_id"),
                    "candidate_id": prediction.payload.get("candidate_id"),
                    "status": judgment.get("status"),
                    "reason": judgment.get("reason"),
                    "predicted_delta": judgment.get("predicted_delta"),
                    "observed_delta": judgment.get("observed_delta"),
                    "predicted_residual": judgment.get("predicted_residual"),
                    "observed_residual": judgment.get("observed_residual"),
                    "level_delta": evidence.payload.get("level_delta", 0),
                }
            )
        if matched:
            evidence_ids.append(evidence.object_id)
    counts = {"supports": 0, "refutes": 0, "unresolved": 0}
    for row in rows:
        status = str(row.get("status"))
        if status in counts:
            counts[status] += 1
    return {
        "protocol": "prospective-evidence-return-v1.9",
        "fidelity": "exact selected-prediction judgments; canonical objects remain authoritative",
        "schema_object_id": str(schema_id),
        "counts": counts,
        "rows": rows,
        "evidence_ids": sorted(set(evidence_ids)),
    }


def action_blind_grounding_state(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Retain exact relational grounding facts while excluding action surfaces."""

    truncation = dict(raw.get("truncation", {}))
    retained = int(truncation.get("entities_retained", len(raw.get("entities", ()))))
    maximum = int(truncation.get("maximum_entities", retained + 1))
    population_complete = retained < maximum
    return {
        "protocol": "exact-action-free-grounding-state-v1",
        "population_complete": population_complete,
        "truncated": not population_complete,
        "entities_truncated": not population_complete,
        "relations_truncated": False,
        "frame": dict(raw.get("frame", {})),
        "entities": [dict(item) for item in raw.get("entities", ())],
        "relations": [dict(item) for item in raw.get("relations", ())],
        "truncation": truncation,
    }
