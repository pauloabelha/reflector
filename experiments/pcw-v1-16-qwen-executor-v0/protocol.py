"""Auditable contracts for the procedural Executor worker.

The module is deliberately transport- and environment-agnostic. It turns the
already materialized PCW state into immutable JSON, validates Executor output,
and never mutates empirical support or commits an ARC action.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Iterable, Mapping, Sequence

import executor_primitives


PROTOCOL = "pcw-v1.16-qwen-executor-v0"
WORKER_ID = "qwen-executor"

EXECUTOR_PROMPT = """You are Reflector's sole motor-policy worker in this arm.

Governing asymmetry: free internal computation is cheap; real actions are precious. Use the fixed internal budget to query, calculate, backtest, search, and falsify before spending one environment action. This does not justify paralysis: when meanings are opaque, prefer the single safest high-discrimination probe that preserves option value.

You are not the semantic worker. You are the only worker permitted to propose a concrete legal ARC action in this arm, but you do not commit actions and you do not decide what is empirically true.

Your job is to receive the best current epistemic state, compute broadly over the supplied immutable workspace and complete relevant transition history, and compress that work into a small, grounded, falsifiable next-action proposal. You are a motor scientist, not another semantic reasoner or a reranker for PCW's existing action scores. You may query history, compare entities, calculate geometry, test temporary rules over every transition, construct a tiny step model, search a small predicted state space, compare hypotheses, and find counterexamples.

Use only supplied data. Do not assume meanings for opaque actions, colors, objects, game identity, goals, or roles unless represented as workspace hypotheses or grounded relations. Prefer computation and explicit dependency use over unsupported intuition. Computation is not empirical support; the environment remains empirical authority.

Compare actions qualitatively by goal progress, epistemic discrimination, option value, known risk, and redundancy. Do not hard-code or optimize a numeric formula. Return ranked legal alternatives, exact live dependencies, a compact value case, a one-step prospective observable checkpoint, and an invalidation condition. Select one legal primitive action or abstain with an open question and a suggested experiment among the candidates. A multi-step sequence or later milestone may be described as a subgoal, but has no execution authority beyond the next observation. Wide computation is allowed inside; the authoritative interface outside must stay tiny."""


class ProtocolError(ValueError):
    pass


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def stable_hash(value: object) -> str:
    return hashlib.sha256(stable_json(value).encode("utf-8")).hexdigest()


def _json_copy(value: Any) -> Any:
    return json.loads(stable_json(value))


def structured_grid_delta(before: Sequence[Sequence[int]], after: Sequence[Sequence[int]]) -> dict[str, Any]:
    changed: list[list[int]] = []
    rows = min(len(before), len(after))
    columns = min(len(before[0]) if before else 0, len(after[0]) if after else 0)
    for row in range(rows):
        for column in range(columns):
            left, right = int(before[row][column]), int(after[row][column])
            if left != right:
                changed.append([row, column, left, right])
    bbox = None
    if changed:
        bbox = [
            min(item[0] for item in changed),
            min(item[1] for item in changed),
            max(item[0] for item in changed),
            max(item[1] for item in changed),
        ]
    return {
        "shape_before": [len(before), len(before[0]) if before else 0],
        "shape_after": [len(after), len(after[0]) if after else 0],
        "changed_cell_count": len(changed),
        "changed_bbox": bbox,
        "changed_cells": changed,
    }


def transition_document(item: Mapping[str, Any]) -> dict[str, Any]:
    before_grid = item["before_grid"]
    after_grid = item["after_grid"]
    return {
        "transition_id": str(item["transition_event_id"]),
        "index": int(item["index"]),
        "before_observation_hash": str(item["before"]["digest"]),
        "after_observation_hash": str(item["after"]["digest"]),
        "opaque_action": {"token": f"A{int(item['action_id'])}", "action_id": int(item["action_id"]), "payload": _json_copy(item.get("data", {}))},
        "before_record": _json_copy(item["before"]),
        "after_record": _json_copy(item["after"]),
        "structured_delta": structured_grid_delta(before_grid, after_grid),
        "animation_transient_summary": _json_copy(item["after"].get("animation_summary")),
        # The exact changed cells plus the episode's origin grid reconstruct
        # every frame losslessly without repeating two full grids per step.
        "raw_before_grid_reference": f"observation:{item['before']['digest']}",
        "raw_after_grid_reference": f"observation:{item['after']['digest']}",
        "provenance": {"environment_transition_id": str(item["transition_event_id"])},
    }


def _object_document(state: Any, item: Any) -> dict[str, Any]:
    support, contradiction = state._index.evidence.get(item.object_id, (0, 0))
    invalidated = item.object_id in state._index.invalidated
    return {
        "id": str(item.object_id),
        "kind": str(item.kind),
        "created_by": str(item.created_by),
        "created_revision": int(item.created_revision),
        "identity": _json_copy(item.identity),
        "payload": _json_copy(item.payload),
        "dependencies": list(item.dependency_ids),
        "support": int(support),
        "contradiction": int(contradiction),
        "invalidated": invalidated,
        "hard_contradicted": invalidated or (int(contradiction) > int(support)),
    }


def _relevant_object_ids(state: Any, *, recent_limit: int = 512) -> tuple[str, ...]:
    priority_kinds = {
        "action_proposal", "environment_evidence", "explanation", "frame",
        "prediction", "qwen_derivation", "relation_set", "runtime_summary",
        "schema", "transition",
    }
    roots = {
        item.object_id
        for item in state.objects
        if item.kind == "r2_binding" and item.object_id not in state._index.invalidated
    }
    prioritized = [item for item in state.objects if item.kind in priority_kinds]
    roots.update(item.object_id for item in prioritized[-recent_limit:])
    agenda = list(roots)
    while agenda:
        object_id = agenda.pop()
        item = state._index.objects.get(object_id)
        if item is None:
            continue
        for dependency in item.dependency_ids:
            if dependency not in roots:
                roots.add(dependency)
                agenda.append(dependency)
    return tuple(sorted(roots))


def _replace_ids(value: Any, alias_by_id: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        return alias_by_id.get(value, value)
    if isinstance(value, (list, tuple)):
        return [_replace_ids(item, alias_by_id) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _replace_ids(item, alias_by_id) for key, item in value.items()}
    return value


def _graph_document(
    state: Any, relevant_ids: Sequence[str], alias_by_id: Mapping[str, str]
) -> dict[str, Any]:
    """Compact all live bindings without discarding their grounded values."""

    bindings: list[list[Any]] = []
    objects: list[dict[str, Any]] = []
    schema_values = sorted({
        str(state._index.objects[object_id].payload.get("schema"))
        for object_id in relevant_ids
        if object_id in state._index.objects
        and state._index.objects[object_id].kind == "r2_binding"
    })
    schema_refs = {value: f"s{index}" for index, value in enumerate(schema_values)}
    for object_id in relevant_ids:
        item = state._index.objects.get(object_id)
        if item is None:
            continue
        document = _object_document(state, item)
        document["id"] = alias_by_id[object_id]
        document["identity"] = _replace_ids(document["identity"], alias_by_id)
        document["payload"] = _replace_ids(document["payload"], alias_by_id)
        document["dependencies"] = [
            alias_by_id[part] for part in item.dependency_ids
        ]
        if item.kind != "r2_binding":
            if item.kind == "runtime_summary":
                payload = document["payload"]
                document["payload"] = {
                    "cycle": payload.get("cycle"), "counts": payload.get("counts", {}),
                    "expansion": payload.get("expansion"),
                    "schema_activation_milli": payload.get("schema_activation_milli", {}),
                    "workspace_blob": payload.get("workspace_blob"),
                    "full_payload_hash": stable_hash(payload),
                }
            objects.append(document)
            continue
        payload = document["payload"]
        bindings.append([
            document["id"], schema_refs.get(str(payload.get("schema"))),
            payload.get("assignments", []),
            [
                [part.get("role_index"), part.get("term_id"), part.get("term_value"), part.get("visual_grounding")]
                for part in payload.get("resolved_assignments", [])
            ],
            document["dependencies"],
            document["support"],
            document["contradiction"], document["invalidated"],
        ])
    relevant = set(relevant_ids)
    edges = [
        {
            "id": f"edge{index}", "kind": edge.kind,
            "source": alias_by_id[edge.source_id],
            "target": alias_by_id[edge.target_id],
            "payload": _replace_ids(_json_copy(edge.payload), alias_by_id),
            "created_by": edge.created_by,
        }
        for index, edge in enumerate(state.edges)
        if edge.source_id in relevant and edge.target_id in relevant
    ]
    return {
        "objects": objects,
        "binding_catalog": {
            "columns": [
                "id", "schema", "assignments", "resolved_assignments",
                "dependencies", "support", "contradiction", "invalidated",
            ],
            "schema_registry": {reference: value for value, reference in schema_refs.items()},
            "rows": bindings,
        },
        "edges": edges,
    }


def build_snapshot(
    *,
    state: Any,
    ledger_events: Sequence[Mapping[str, Any]],
    legal_actions: Sequence[int],
    current_record: Mapping[str, Any],
    current_grid: Sequence[Sequence[int]],
    history: Sequence[Mapping[str, Any]],
    r2_workspace: Mapping[str, Any],
    controller_report: Mapping[str, Any],
    prediction_matrix: Sequence[Mapping[str, Any]],
    max_recent_transitions: int,
    max_bytes: int,
) -> dict[str, Any]:
    """Build a dependency-closed, read-only packet at the action boundary."""

    legal = tuple(sorted(set(int(action) for action in legal_actions)))
    if not legal:
        raise ProtocolError("Executor snapshot requires legal actions")
    if any(item["event_type"] == "ActionPending" for item in ledger_events[-1:]):
        raise ProtocolError("snapshot was requested after the action boundary")
    if history and str(history[-1]["after"]["digest"]) != str(current_record["digest"]):
        raise ProtocolError("current observation does not close the supplied history")
    basis_seq = int(ledger_events[-1]["seq"]) if ledger_events else -1
    relevant_ids = _relevant_object_ids(state)
    alias_by_id = {
        object_id: f"o{index:03d}" for index, object_id in enumerate(relevant_ids)
    }
    graph = _graph_document(state, relevant_ids, alias_by_id)
    workspace_copy = _json_copy(r2_workspace)
    packet = {
        "protocol": PROTOCOL,
        "worker": WORKER_ID,
        "read_only": True,
        "decision_boundary": {
            "ledger_basis_seq": basis_seq,
            "graph_basis_revision": int(state.revision),
            "successor_available": False,
            "history_transition_count": len(history),
        },
        "current_observation": {
            "reference": "obs-current",
            "hash": str(current_record["digest"]),
            "record": _json_copy(current_record),
            "raw_grid": _json_copy(current_grid),
        },
        "legal_opaque_actions": [
            {"token": f"A{action}", "action_id": action, "payload_schema": {}}
            for action in legal
        ],
        "r2": {
            # Bindings/schemas/explanations are represented once in the graph.
            # This summary is loss-auditable against the durable full document.
            "workspace_summary": {
                "cycle": workspace_copy.get("cycle"),
                "metrics": workspace_copy.get("metrics", {}),
                "counts": {
                    key: len(workspace_copy.get(key, ()))
                    for key in ("bindings", "partial_bindings", "shadows", "schemas", "explanations")
                },
                "full_document_hash": stable_hash(workspace_copy),
            },
            "control_constraints": _json_copy(controller_report),
            "prospective_prediction_matrix": _json_copy(prediction_matrix),
        },
        "epistemic_graph": graph,
        "dependency_aliases": {
            **{alias: object_id for object_id, alias in alias_by_id.items()},
            "obs-current": f"observation:{current_record['digest']}",
            **{
                f"t{index:03d}": str(item["transition_event_id"])
                for index, item in enumerate(history)
            },
        },
        "history_origin_grid": _json_copy(history[0]["before_grid"]) if history else None,
        "full_relevant_transition_history": [
            {**transition_document(item), "transition_id": f"t{index:03d}"}
            for index, item in enumerate(history[-max(0, int(max_recent_transitions)):])
        ],
        "progress_history": [
            {
                "transition_id": f"t{index:03d}",
                "index": int(item["index"]),
                "levels_before": int(item["before"].get("levels_completed", 0)),
                "levels_after": int(item["after"].get("levels_completed", 0)),
            }
            for index, item in enumerate(history)
        ],
    }
    packet["snapshot_hash"] = stable_hash(packet)
    if len(packet["full_relevant_transition_history"]) != len(history):
        raise ProtocolError("Executor snapshot omitted relevant transition history")
    encoded_size = len(stable_json(packet).encode("utf-8"))
    if encoded_size > int(max_bytes):
        raise ProtocolError(f"Executor snapshot exceeds bound: {encoded_size} > {max_bytes}")
    packet["encoded_bytes"] = encoded_size
    return packet


def model_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Create a compact, loss-auditable view that fits the pinned context.

    One deterministic binding per schema retains grounded examples; every
    omitted live binding remains named and the complete row set is hashed in
    the durable snapshot.  This is the same view in B and C.
    """

    visible = _json_copy(snapshot)
    visible.pop("dependency_aliases", None)
    catalog = visible["epistemic_graph"]["binding_catalog"]
    all_rows = list(catalog["rows"])
    representative_rows: list[list[Any]] = []
    seen_schemas: set[str] = set()
    for row in all_rows:
        schema_ref = str(row[1])
        if schema_ref not in seen_schemas:
            representative_rows.append(row)
            seen_schemas.add(schema_ref)
    represented_ids = {str(row[0]) for row in representative_rows}
    catalog["rows"] = representative_rows
    catalog["omitted_live_bindings"] = {
        "count": len(all_rows) - len(representative_rows),
        "ids": [str(row[0]) for row in all_rows if str(row[0]) not in represented_ids],
        "full_rows_hash": stable_hash(all_rows),
        "selection_rule": "first-stable-id-per-schema",
    }
    graph = visible["epistemic_graph"]
    schemas = [item for item in graph["objects"] if item["kind"] == "schema"]
    graph["objects"] = [item for item in graph["objects"] if item["kind"] != "schema"]
    graph["schema_catalog"] = {
        "columns": [
            "id", "payload", "dependencies", "support", "contradiction", "invalidated",
        ],
        "rows": [
            [
                item["id"], item["payload"], item["dependencies"], item["support"],
                item["contradiction"], item["invalidated"],
            ]
            for item in schemas
        ],
        "full_objects_hash": stable_hash(schemas),
    }
    for item in graph["objects"]:
        if item["kind"] == "runtime_summary":
            dependencies = item.get("dependencies", [])
            item["dependencies"] = []
            payload = item["payload"]
            item["payload"] = {
                "cycle": payload.get("cycle"), "counts": payload.get("counts", {}),
                "full_payload_hash": payload.get("full_payload_hash"),
            }
            item["omitted_dependency_summary"] = {
                "count": len(dependencies), "hash": stable_hash(dependencies)
            }
    visible["encoded_bytes"] = len(stable_json(visible).encode("utf-8"))
    return visible


def trigger_reasons(
    *, legal_actions: Sequence[int], controller_report: Mapping[str, Any], prediction_matrix: Sequence[Mapping[str, Any]]
) -> tuple[str, ...]:
    """The preregistered generic trigger; no experimenter judgment is used."""

    legal = set(int(item) for item in legal_actions)
    if len(legal) <= 1:
        return ()
    records = list(controller_report.get("records", ()))
    live = [item for item in records if item.get("population_complete", True)]
    settled = [item for item in live if item.get("control_eligible") and int(item.get("prospective_confirmations", 0)) > 0]
    reasons: list[str] = []
    if len(live) > 1:
        reasons.append("multiple-control-relevant-live-groundings")
    signatures: dict[int, set[str]] = {action: set() for action in legal}
    for prediction in prediction_matrix:
        action = int(prediction["action_id"])
        if action in signatures:
            signatures[action].add(stable_hash({"delta": prediction.get("predicted_delta"), "residual": prediction.get("predicted_residual")}))
    if sum(bool(values) for values in signatures.values()) > 1 and len({tuple(sorted(values)) for values in signatures.values()}) > 1:
        reasons.append("distinct-prospective-action-predictions")
    if len(settled) != 1:
        reasons.append("no-settled-unique-policy")
    return tuple(reasons)


@dataclass(frozen=True, slots=True)
class CandidateAction:
    action_id: int
    dependencies: tuple[str, ...]
    subgoal: str
    desired_delta: Mapping[str, str]
    computed_reason: Mapping[str, Any]
    value_case: Mapping[str, str]
    expected_checkpoint: Mapping[str, Any]
    invalidate_on: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExecutorProposal:
    request_id: str
    snapshot_hash: str
    candidates: tuple[CandidateAction, ...]
    selected_action: int | None
    abstention_reason: str | None
    computation_summary: tuple[int, ...]
    open_questions: tuple[Mapping[str, str], ...]


def _visible_dependency_refs(snapshot: Mapping[str, Any]) -> set[str]:
    graph = snapshot["epistemic_graph"]
    visible = {str(item["id"]) for item in graph["objects"]}
    visible.update(str(row[0]) for row in graph["binding_catalog"]["rows"])
    visible.update(
        str(item) for item in graph["binding_catalog"].get("omitted_live_bindings", {}).get("ids", ())
    )
    visible.update(str(row[0]) for row in graph.get("schema_catalog", {}).get("rows", ()))
    visible.update(str(item["transition_id"]) for item in snapshot["full_relevant_transition_history"])
    visible.add(str(snapshot["current_observation"]["reference"]))
    return visible


def validate_proposal(
    value: Mapping[str, Any], *, request_id: str, snapshot: Mapping[str, Any]
) -> ExecutorProposal:
    legal = {int(item["action_id"]) for item in snapshot["legal_opaque_actions"]}
    visible_dependencies = _visible_dependency_refs(snapshot)
    raw = value.get("candidate_actions")
    if not isinstance(raw, list) or not raw:
        raise ProtocolError("Executor must return ranked candidate_actions")
    candidates: list[CandidateAction] = []
    seen: set[int] = set()
    for item in raw:
        action = int(item["action_id"])
        if action not in legal or action in seen:
            raise ProtocolError("candidate action is illegal or duplicated")
        raw_dependencies = tuple(str(part) for part in item.get("dependencies", ()))
        if not raw_dependencies or any(part not in visible_dependencies for part in raw_dependencies):
            raise ProtocolError("candidate uses missing or invisible dependencies")
        dependency_aliases = snapshot["dependency_aliases"]
        dependencies = tuple(str(dependency_aliases[part]) for part in raw_dependencies)
        desired_delta = item.get("desired_delta")
        computed_reason = item.get("computed_reason")
        if not isinstance(desired_delta, Mapping) or not isinstance(computed_reason, Mapping):
            raise ProtocolError("candidate lacks structured delta or reason")
        for structured in (desired_delta, item.get("expected_checkpoint", {})):
            target = str(structured.get("target_dependency", ""))
            if target not in visible_dependencies:
                raise ProtocolError("candidate structured field uses an invisible dependency")
        checkpoint = item.get("expected_checkpoint")
        invalidate_on = tuple(str(part) for part in item.get("invalidate_on", ()))
        if not isinstance(checkpoint, Mapping) or not invalidate_on:
            raise ProtocolError("candidate lacks a prospective checkpoint or invalidation condition")
        if int(checkpoint.get("horizon_steps", 0)) != 1:
            raise ProtocolError("checkpoint must be prospective over exactly one primitive action")
        if not str(checkpoint.get("observable_type", "")).strip() or not str(checkpoint.get("direction", "")).strip():
            raise ProtocolError("checkpoint must name an observable and direction")
        value_case = item.get("value_case")
        required_value_dimensions = {
            "goal_progress", "epistemic_discrimination", "option_value",
            "known_risk", "redundancy",
        }
        if not isinstance(value_case, Mapping) or set(value_case) != required_value_dimensions:
            raise ProtocolError("candidate lacks the qualitative motor-policy value case")
        candidates.append(CandidateAction(
            action_id=action,
            dependencies=dependencies,
            subgoal=str(item.get("subgoal", "")).strip(),
            desired_delta={
                **_json_copy(desired_delta),
                "target_dependency": str(dependency_aliases[str(desired_delta["target_dependency"])]),
            },
            computed_reason=_json_copy(computed_reason),
            value_case={str(key): str(part) for key, part in value_case.items()},
            expected_checkpoint={
                **_json_copy(checkpoint),
                "target_dependency": str(dependency_aliases[str(checkpoint["target_dependency"])]),
            },
            invalidate_on=invalidate_on,
        ))
        seen.add(action)
    decision = value.get("decision")
    if not isinstance(decision, Mapping):
        raise ProtocolError("proposal lacks a mutually exclusive decision")
    decision_kind = str(decision.get("kind", ""))
    selected = decision.get("action_id") if decision_kind == "select" else None
    selected_action = None if selected is None else int(selected)
    if selected_action is not None and selected_action not in seen:
        raise ProtocolError("selected_action is absent from ranked candidates")
    abstention = decision.get("reason") if decision_kind == "abstain" else None
    if decision_kind not in {"select", "abstain"}:
        raise ProtocolError("decision kind must be select or abstain")
    if decision_kind == "abstain" and not str(abstention or "").strip():
        raise ProtocolError("abstention requires a reason")
    return ExecutorProposal(
        request_id=request_id,
        snapshot_hash=str(snapshot["snapshot_hash"]),
        candidates=tuple(candidates),
        selected_action=selected_action,
        abstention_reason=None if selected_action is not None else str(abstention),
        computation_summary=tuple(int(item) for item in value.get("computation_summary", ())),
        open_questions=tuple(
            {
                **_json_copy(item),
                "dependency": str(dependency_aliases[str(item["dependency"])]),
            }
            for item in value.get("open_questions", ())
        ),
    )


def normalize_response_keys(value: Any) -> Any:
    """Normalize Qwen's occasional JSON key hyphenation, never field values."""

    if isinstance(value, Mapping):
        return {
            str(key).replace("-", "_"): normalize_response_keys(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [normalize_response_keys(item) for item in value]
    return value


def proposal_document(value: ExecutorProposal) -> dict[str, Any]:
    return asdict(value)


def analysis_response_schema(tool_available: bool) -> dict[str, Any]:
    return {
        "type": "object", "additionalProperties": False,
        "required": ["mode", "dependencies", "findings", "code", "missing_operation"],
        "properties": {
            "mode": {"type": "string", "enum": ["verbal", "python"] if tool_available else ["verbal"]},
            "dependencies": {"type": "array", "items": {"type": "string"}, "maxItems": 64},
            "findings": {"type": "array", "items": {"type": "string"}, "maxItems": 6},
            "code": (
                {
                    "anyOf": [
                        {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 20},
                        {"type": "null"},
                    ]
                }
                if tool_available else {"type": "null"}
            ),
            "missing_operation": {"type": ["string", "null"]},
        },
    }


def proposal_response_schema(
    legal_actions: Sequence[int], dependency_refs: Sequence[str]
) -> dict[str, Any]:
    action_schema = {"type": "integer", "enum": sorted(set(int(item) for item in legal_actions))}
    dependency_schema = {"type": "string", "enum": sorted(set(str(item) for item in dependency_refs))}
    candidate = {
        "type": "object", "additionalProperties": False,
        "required": ["action_id", "dependencies", "subgoal", "desired_delta", "computed_reason", "value_case", "expected_checkpoint", "invalidate_on"],
        "properties": {
            "action_id": action_schema,
            "dependencies": {"type": "array", "items": dependency_schema, "minItems": 1, "maxItems": 8},
            "subgoal": {"type": "string", "enum": ["goal_progress", "discriminate_hypotheses", "preserve_option_value", "test_state_factorization"]},
            "desired_delta": {
                "type": "object", "additionalProperties": False,
                "required": ["kind", "target_dependency"],
                "properties": {
                    "kind": {"type": "string", "enum": ["change", "no_change", "increase", "decrease", "differentiate"]},
                    "target_dependency": dependency_schema,
                },
            },
            "computed_reason": {
                "type": "object", "additionalProperties": False,
                "required": ["basis", "finding_indices"],
                "properties": {
                    "basis": {"type": "string", "enum": ["history_rule", "geometry", "workspace_prediction", "counterexample", "information_gain", "option_preservation"]},
                    "finding_indices": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 5}, "minItems": 1, "maxItems": 6},
                },
            },
            "value_case": {
                "type": "object", "additionalProperties": False,
                "required": ["goal_progress", "epistemic_discrimination", "option_value", "known_risk", "redundancy"],
                "properties": {
                    "goal_progress": {"type": "string", "enum": ["positive", "neutral", "negative", "unknown"]},
                    "epistemic_discrimination": {"type": "string", "enum": ["high", "medium", "low", "unknown"]},
                    "option_value": {"type": "string", "enum": ["preserves", "reduces", "unknown"]},
                    "known_risk": {"type": "string", "enum": ["high", "medium", "low", "unknown"]},
                    "redundancy": {"type": "string", "enum": ["high", "medium", "low", "unknown"]},
                },
            },
            "expected_checkpoint": {
                "type": "object", "additionalProperties": False,
                "required": ["observable_type", "direction", "target_dependency", "horizon_steps"],
                "properties": {
                    "observable_type": {"type": "string", "enum": ["grid_delta", "entity_change", "relation_change", "progress_change", "terminal_state", "no_change"]},
                    "direction": {"type": "string", "enum": ["change", "no_change", "increase", "decrease", "differentiate"]},
                    "target_dependency": dependency_schema,
                    "horizon_steps": {"type": "integer", "enum": [1]},
                },
            },
            "invalidate_on": {
                "type": "array", "minItems": 1, "maxItems": 3,
                "items": {"type": "string", "enum": ["checkpoint_mismatch", "hard_contradiction", "dependency_dead", "unexpected_terminal", "no_observable_change"]},
            },
        },
    }
    return {
        "type": "object", "additionalProperties": False,
        "required": ["candidate_actions", "decision", "computation_summary", "open_questions"],
        "properties": {
            "candidate_actions": {"type": "array", "items": candidate, "minItems": 1, "maxItems": min(2, len(set(legal_actions)))},
            "decision": {
                "anyOf": [
                    {
                        "type": "object", "additionalProperties": False,
                        "required": ["kind", "action_id"],
                        "properties": {
                            "kind": {"type": "string", "enum": ["select"]},
                            "action_id": action_schema,
                        },
                    },
                    {
                        "type": "object", "additionalProperties": False,
                        "required": ["kind", "reason"],
                        "properties": {
                            "kind": {"type": "string", "enum": ["abstain"]},
                            "reason": {"type": "string", "enum": ["snapshot_insufficient", "tooling_insufficient", "all_candidates_hard_contradicted", "no_legal_action"]},
                        },
                    },
                ]
            },
            "computation_summary": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 5}, "maxItems": 6},
            "open_questions": {
                "type": "array", "maxItems": 3,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["kind", "dependency"],
                    "properties": {
                        "kind": {"type": "string", "enum": ["state_factorization", "action_effect", "relation_validity", "history_counterexample"]},
                        "dependency": dependency_schema,
                    },
                },
            },
        },
    }


def request_payload(
    *, model_config: Mapping[str, Any], snapshot: Mapping[str, Any], stage: str,
    intermediate: Mapping[str, Any] | None = None, tool_available: bool,
) -> dict[str, Any]:
    legal = [int(item["action_id"]) for item in snapshot["legal_opaque_actions"]]
    if stage == "analysis":
        task = "Produce one bounded motor-policy analysis. Query and test the complete relevant history. Return at most six one-sentence findings. If the Python tool is available, code must be an array of at most 20 physical Python source lines that assigns a JSON-serializable value to result. Imports, NumPy, files, network, environment access, classes, and hidden attributes are unavailable; use only snapshot, safe builtins, and the listed frozen primitives. Prefer a small history query or exact count over reimplementing perception. Otherwise reason verbally and set code=null. Do not rank or select actions in this stage and do not optimize PCW's existing action score."
        schema = analysis_response_schema(tool_available)
        max_tokens = int(model_config["max_tokens_stage_1"])
    elif stage == "proposal":
        task = "Compress the intermediate computation into at most two ranked legal primitive action candidates and normally select one information-gaining probe. Use only schema enums, visible dependency IDs, and indices into the stage-one findings; emit no explanatory prose. The decision object is mutually exclusive: either kind=select with action_id, or kind=abstain with a supplied reason code. Opaque action meanings are intentionally unknown and are not by themselves grounds to abstain."
        schema = proposal_response_schema(legal, sorted(_visible_dependency_refs(snapshot)))
        max_tokens = int(model_config["max_tokens_stage_2"])
    else:
        raise ProtocolError(f"unknown Executor stage: {stage}")
    content = {
        "task": task,
        "available_tools": (
            [{"run_analysis(code)": executor_primitives.manifest()}]
            if tool_available else []
        ),
        "snapshot": snapshot,
    }
    if intermediate is not None:
        content["intermediate_computation"] = _json_copy(intermediate)
    return {
        "model": model_config["model"],
        "messages": [
            {"role": "system", "content": EXECUTOR_PROMPT},
            {"role": "user", "content": stable_json(content)},
        ],
        "temperature": model_config.get("temperature", 0),
        "top_p": model_config.get("top_p", 1),
        "seed": model_config.get("seed", 0),
        "max_tokens": max_tokens,
        "thinking_budget_tokens": model_config.get("thinking_budget_tokens", 1024),
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": f"qwen_executor_{stage}_v0", "strict": True, "schema": schema},
        },
    }
