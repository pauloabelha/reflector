"""Pure Qwen protocol boundary for the parallel cognitive workspace.

This module deliberately contains no transport or workspace mutation.  It
serializes an immutable causal-prefix snapshot, constructs the strict request
contract, and compiles a reply into audited proposals.  Environment action
authority remains outside this module.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import re
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
V0_PATH = HERE.parent / "qwen-generic-explanation-priors-v0" / "experiment.py"
_SPEC = importlib.util.spec_from_file_location("qwen_prior_v0_protocol_base", V0_PATH)
if _SPEC is None or _SPEC.loader is None:
    raise RuntimeError(f"cannot load v0 Qwen protocol base: {V0_PATH}")
V0 = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = V0
_SPEC.loader.exec_module(V0)


REQUEST_PROTOCOL = "parallel-cognitive-workspace-request-v0.1"
RESPONSE_PROTOCOL = "parallel-cognitive-workspace-response-v0.1"
SNAPSHOT_PROTOCOL = "parallel-cognitive-workspace-snapshot-v0.1"
MAX_ENTITIES = 8
MAX_RELATIONS = 48
MAX_TRANSITIONS = 4
MAX_WRITES = 2
MAX_BASIS_EVENTS = 8
MAX_CONDITIONS = 6

ALLOWED_VARIABLES = ("?a", "?b", "?c", "?d")
ALLOWED_PREDICATES = (
    "SameOutline",
    "DifferentOutline",
    "SameInteriorLayout",
    "DifferentInteriorLayout",
    "SameArea",
    "DifferentArea",
    "AlignedHorizontal",
    "AlignedVertical",
    "Touches",
    "Disjoint",
    "MovedTogether",
    "MovedWhileStationary",
    "ChangedTogether",
)
SCHEMA_OPERATORS = ("Decrease", "Increase")
PREDICTION_OPERATORS = ("Decrease", "Increase", "Preserve")
MEASURE = "TranslationAlignmentResidual"
WRITE_KEYS = (
    "schema_writes",
    "explanation_writes",
    "counterfactual_writes",
    "discriminating_experiment_writes",
)

_RELATION_PRIORITY = {
    name: index
    for index, name in enumerate(
        (
            "MovedTogether",
            "MovedWhileStationary",
            "ChangedTogether",
            "SameInteriorLayout",
            "DifferentInteriorLayout",
            "SameOutline",
            "DifferentOutline",
            "AlignedHorizontal",
            "AlignedVertical",
            "Touches",
            "Disjoint",
            "SameArea",
            "DifferentArea",
        )
    )
}
_SENSITIVE_INPUT_KEYS = re.compile(
    r"(?:^|_)(?:game|reward|solution|next_action|action|actions|action_id|action_token|button|palette|color)(?:$|_)",
    re.IGNORECASE,
)
_FORBIDDEN_OUTPUT_KEYS = re.compile(
    r"(?:^|_)(?:action|action_id|action_token|intervention_model|model_id|button|direction|policy|repeat|stop)(?:$|_)",
    re.IGNORECASE,
)
_FORBIDDEN_OUTPUT_TEXT = re.compile(
    r"(?:arc-action\s*[:_-]?\s*\d+|\baction\s*[:#_-]?\s*\d+|\bbutton\b|\b(?:up|down|left|right)\b|\brepeat\b|\bstop\b)",
    re.IGNORECASE,
)


def stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _entity_id(value: Any) -> str:
    if isinstance(value, Mapping):
        for key in ("id", "entity_id", "ref"):
            if key in value:
                return str(value[key])
    return str(value)


def _generation(value: Mapping[str, Any]) -> int:
    return int(value.get("generation", value.get("version", 0)))


def _clean_json(value: Any, *, forbidden_keys: re.Pattern[str] = _SENSITIVE_INPUT_KEYS) -> Any:
    """Copy JSON-like data while removing transport/task-semantic leakage."""

    if isinstance(value, Mapping):
        return {
            str(key): _clean_json(item, forbidden_keys=forbidden_keys)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if not forbidden_keys.search(str(key)) and not str(key).startswith("_")
        }
    if isinstance(value, (list, tuple)):
        return [_clean_json(item, forbidden_keys=forbidden_keys) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _as_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, Mapping):
        return [
            {"id": key, **(dict(item) if isinstance(item, Mapping) else {"value": item})}
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        ]
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [dict(item) for item in value if isinstance(item, Mapping)]
    return []


def _relation_tuple(raw: Mapping[str, Any]) -> tuple[str, tuple[str, ...]] | None:
    predicate = str(raw.get("predicate", raw.get("relation", "")))
    arguments = raw.get("arguments", raw.get("entities", ()))
    if predicate not in ALLOWED_PREDICATES or not isinstance(arguments, Sequence):
        return None
    values = tuple(_entity_id(item) for item in arguments)
    if len(values) != 2 or values[0] == values[1]:
        return None
    return predicate, values


def _event_seq(raw: Any) -> int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, Mapping):
        for key in ("event_seq", "seq", "basis_event"):
            if key in raw:
                try:
                    return int(raw[key])
                except (TypeError, ValueError):
                    return None
    return None


def _model_source_id(raw: Mapping[str, Any], index: int) -> str:
    for key in ("model_id", "intervention_model_id", "id", "action_id", "action_token"):
        if key in raw:
            return str(raw[key])
    return f"source-model-{index:04d}"


def _model_ids(materialization: Mapping[str, Any]) -> tuple[dict[str, str], list[dict[str, Any]]]:
    raw_models = _as_items(
        materialization.get("intervention_models", materialization.get("effect_models", ()))
    )
    sources = {_model_source_id(item, index) for index, item in enumerate(raw_models)}
    for transition in _as_items(materialization.get("transitions", ())):
        for key in ("model_id", "intervention_model_id", "action_id", "action_token"):
            if key in transition:
                sources.add(str(transition[key]))
    mapping = {source: f"im{index:02d}" for index, source in enumerate(sorted(sources))}
    return mapping, raw_models


def _compact_transition(raw: Mapping[str, Any], model_map: Mapping[str, str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    seq = _event_seq(raw)
    if seq is not None:
        result["event_seq"] = seq
    for key in ("before_revision", "after_revision", "observation_version"):
        if key in raw:
            result[key] = int(raw[key])
    source_model = next(
        (
            str(raw[key])
            for key in ("model_id", "intervention_model_id", "action_id", "action_token")
            if key in raw
        ),
        None,
    )
    if source_model is not None and source_model in model_map:
        result["intervention_model"] = model_map[source_model]
    for source, target in (
        ("relation_changes", "relation_changes"),
        ("derived_relations", "relation_changes"),
        ("relations_added", "relations_added"),
        ("relations_removed", "relations_removed"),
        ("measure_changes", "measure_changes"),
        ("changed_entities", "changed_entities"),
        ("observation_changed", "observation_changed"),
        ("effect", "effect"),
        ("effect_summary", "effect"),
    ):
        if source in raw and target not in result:
            result[target] = _clean_json(raw[source])
    return result


def serialize_snapshot(
    materialization: Mapping[str, Any],
    *,
    request_id: str,
    basis_revision: int,
    max_entities: int = MAX_ENTITIES,
    max_relations: int = MAX_RELATIONS,
    max_transitions: int = MAX_TRANSITIONS,
) -> dict[str, Any]:
    """Return a deterministic, compact, action-anonymous causal-prefix view."""

    if max_entities < 1 or max_relations < 0 or max_transitions < 0:
        raise ValueError("snapshot caps must be non-negative and retain at least one entity")
    raw_entities = _as_items(materialization.get("entities", ()))
    raw_relations = _as_items(materialization.get("relations", ()))
    parsed_relations = [item for item in (_relation_tuple(raw) for raw in raw_relations) if item]
    degree = Counter(argument for _predicate, arguments in parsed_relations for argument in arguments)
    ranked_entities = sorted(
        raw_entities,
        key=lambda item: (
            -float(item.get("salience", item.get("activation", 0.0))),
            -degree[_entity_id(item)],
            _entity_id(item),
            _generation(item),
        ),
    )
    selected = ranked_entities[:max_entities]
    retained_ids = {_entity_id(item) for item in selected}
    entities = []
    for raw in selected:
        identity = _entity_id(raw)
        reserved = {"id", "entity_id", "ref", "generation", "version", "kind", "salience", "activation"}
        attributes = _clean_json({key: value for key, value in raw.items() if key not in reserved})
        entities.append(
            {
                "id": identity,
                "generation": _generation(raw),
                "kind": str(raw.get("kind", "Entity")),
                "attributes": attributes,
            }
        )

    filtered_relations = {
        (predicate, arguments)
        for predicate, arguments in parsed_relations
        if all(argument in retained_ids for argument in arguments)
    }
    ordered_relations = sorted(
        filtered_relations,
        key=lambda item: (_RELATION_PRIORITY[item[0]], item[0], item[1]),
    )[:max_relations]
    relations = [
        {"predicate": predicate, "arguments": list(arguments)}
        for predicate, arguments in ordered_relations
    ]

    model_map, raw_models = _model_ids(materialization)
    intervention_models = []
    for index, raw in enumerate(raw_models):
        source = _model_source_id(raw, index)
        effect = raw.get("effect_summary", raw.get("effect", raw.get("consequence", {})))
        intervention_models.append(
            {
                "id": model_map[source],
                "support": int(raw.get("support", raw.get("observations", 0))),
                "effect": _clean_json(effect),
            }
        )
    intervention_models.sort(key=lambda item: item["id"])

    raw_transitions = _as_items(materialization.get("transitions", ()))
    raw_transitions.sort(key=lambda item: (_event_seq(item) is None, _event_seq(item) or -1, stable_json(item)))
    recent_transitions = [
        _compact_transition(item, model_map) for item in raw_transitions[-max_transitions:]
    ] if max_transitions else []

    raw_objects = _as_items(materialization.get("cognitive_objects", materialization.get("objects", ())))
    cognitive_objects = []
    for raw in raw_objects:
        reference = str(raw.get("ref", raw.get("object_ref", raw.get("id", ""))))
        if not reference:
            continue
        cognitive_objects.append(
            {
                "ref": reference,
                "kind": str(raw.get("kind", raw.get("type", "schema"))).lower(),
                "status": str(raw.get("status", "live")),
                "summary": _clean_json(raw.get("summary", raw.get("content", {}))),
            }
        )
    cognitive_objects.sort(key=lambda item: (item["kind"], item["ref"]))

    event_values = materialization.get("basis_events", materialization.get("events", ()))
    if isinstance(event_values, Mapping):
        event_values = list(event_values.values())
    basis_events = sorted(
        {
            value
            for value in (_event_seq(item) for item in (event_values or ()))
            if value is not None and value <= int(basis_revision)
        }
    )
    for item in recent_transitions:
        if "event_seq" in item and item["event_seq"] <= int(basis_revision):
            basis_events.append(int(item["event_seq"]))
    basis_events = sorted(set(basis_events))
    if not basis_events:
        basis_events = [int(basis_revision)]

    observation = materialization.get("observation", {})
    snapshot = {
        "protocol": SNAPSHOT_PROTOCOL,
        "request_id": str(request_id),
        "basis_revision": int(basis_revision),
        "basis_events": basis_events[-32:],
        "observation": {
            "version": int(
                observation.get("version", materialization.get("observation_version", basis_revision))
                if isinstance(observation, Mapping)
                else basis_revision
            ),
            "digest": str(
                observation.get("digest", materialization.get("observation_digest", "anonymous"))
                if isinstance(observation, Mapping)
                else materialization.get("observation_digest", "anonymous")
            ),
        },
        "opaque_legal_action_count": int(materialization.get("opaque_legal_action_count", materialization.get("legal_action_count", 0))),
        "entities": entities,
        "relations": relations,
        "recent_transitions": recent_transitions,
        "intervention_models": intervention_models,
        "cognitive_objects": cognitive_objects,
        "history_summary": _clean_json(materialization.get("history_summary", {})),
        "r2_state": _clean_json(materialization.get("r2_state", {})),
        "allowed_vocabulary": {
            "variables": list(ALLOWED_VARIABLES),
            "condition_predicates": list(ALLOWED_PREDICATES),
            "consequence_measure": MEASURE,
            "schema_operators": list(SCHEMA_OPERATORS),
            "prediction_operators": list(PREDICTION_OPERATORS),
        },
        "truncation": {
            "entity_cap": max_entities,
            "entities_available": len(raw_entities),
            "entities_retained": len(entities),
            "relation_cap": max_relations,
            "relations_available": len(filtered_relations),
            "relations_retained": len(relations),
            "transition_cap": max_transitions,
            "transitions_available": len(raw_transitions),
            "transitions_retained": len(recent_transitions),
        },
        # Compiler-only metadata is removed from the prompt by _public_snapshot.
        "_compiler_forbidden_tokens": sorted(set(model_map) | set(model_map.values())),
    }
    return snapshot


def _public_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in snapshot.items() if not str(key).startswith("_")}


def _impossible_string_schema() -> dict[str, Any]:
    # Constrained-decoding servers do not uniformly implement JSON Schema's
    # boolean/``not`` forms.  This sentinel keeps the grammar representable;
    # the semantic compiler still rejects it because it is not a supplied ref.
    return {"type": "string", "enum": ["__no_reference_available__"]}


def response_schema(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Build the exact strict JSON schema for one immutable request basis."""

    entity_ids = sorted({str(item["id"]) for item in snapshot.get("entities", ())})
    object_refs = sorted({str(item["ref"]) for item in snapshot.get("cognitive_objects", ())})
    schema_refs = sorted(
        {
            str(item["ref"])
            for item in snapshot.get("cognitive_objects", ())
            if str(item.get("kind", "")).lower() == "schema"
        }
    )
    explanation_refs = sorted(
        {
            str(item["ref"])
            for item in snapshot.get("cognitive_objects", ())
            if str(item.get("kind", "")).lower() == "explanation"
        }
    )
    counterfactual_refs = sorted(
        {
            str(item["ref"])
            for item in snapshot.get("cognitive_objects", ())
            if str(item.get("kind", "")).lower() == "counterfactual"
        }
    )
    basis_events = sorted({int(item) for item in snapshot.get("basis_events", ())})
    entity_id_schema = {"type": "string", "enum": entity_ids} if entity_ids else _impossible_string_schema()
    object_ref_schema = {"type": "string", "enum": object_refs} if object_refs else _impossible_string_schema()
    schema_object_ref_schema = (
        {"type": "string", "enum": schema_refs} if schema_refs else _impossible_string_schema()
    )
    explanation_object_ref_schema = (
        {"type": "string", "enum": explanation_refs}
        if explanation_refs
        else _impossible_string_schema()
    )
    counterfactual_ref_schema = (
        {"type": "string", "enum": counterfactual_refs}
        if counterfactual_refs
        else _impossible_string_schema()
    )
    basis_schema = {
        "type": "array",
        "minItems": 1,
        "maxItems": MAX_BASIS_EVENTS,
        "uniqueItems": True,
        "items": {"type": "integer", "enum": basis_events},
    }
    supersedes_schema = {
        "type": "array",
        "maxItems": 2,
        "uniqueItems": True,
        "items": object_ref_schema,
    }
    condition_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["predicate", "arguments"],
        "properties": {
            "predicate": {"type": "string", "enum": list(ALLOWED_PREDICATES)},
            "arguments": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"type": "string", "enum": list(ALLOWED_VARIABLES)},
            },
        },
    }
    consequence_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["operator", "measure", "arguments"],
        "properties": {
            "operator": {"type": "string", "enum": list(SCHEMA_OPERATORS)},
            "measure": {"const": MEASURE},
            "arguments": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"type": "string", "enum": list(ALLOWED_VARIABLES)},
            },
        },
    }
    entity_ref_schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["id", "generation"],
        "properties": {
            "id": entity_id_schema,
            "generation": {"type": "integer", "minimum": 0},
        },
    }
    schema_ref_schema = {
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "object_ref"],
                "properties": {"source": {"const": "workspace"}, "object_ref": schema_object_ref_schema},
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "schema_write_index"],
                "properties": {
                    "source": {"const": "response"},
                    "schema_write_index": {"type": "integer", "minimum": 0, "maximum": 1},
                },
            },
        ]
    }
    explanation_ref_schema = {
        "oneOf": [
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "object_ref"],
                "properties": {"source": {"const": "workspace"}, "object_ref": explanation_object_ref_schema},
            },
            {
                "type": "object",
                "additionalProperties": False,
                "required": ["source", "explanation_write_index"],
                "properties": {
                    "source": {"const": "response"},
                    "explanation_write_index": {"type": "integer", "minimum": 0, "maximum": 1},
                },
            },
        ]
    }
    schema_write = {
        "type": "object",
        "additionalProperties": False,
        "required": ["conditions", "preferred_consequence", "basis_events", "supersedes"],
        "properties": {
            "conditions": {
                "type": "array",
                "minItems": 1,
                "maxItems": MAX_CONDITIONS,
                "items": condition_schema,
            },
            "preferred_consequence": consequence_schema,
            "basis_events": basis_schema,
            "supersedes": supersedes_schema,
        },
    }
    explanation_write = {
        "type": "object",
        "additionalProperties": False,
        "required": ["schema_ref", "bindings", "basis_events", "supersedes"],
        "properties": {
            "schema_ref": schema_ref_schema,
            "bindings": {
                "type": "array",
                "minItems": 2,
                "maxItems": 4,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["variable", "entity"],
                    "properties": {
                        "variable": {"type": "string", "enum": list(ALLOWED_VARIABLES)},
                        "entity": entity_ref_schema,
                    },
                },
            },
            "basis_events": basis_schema,
            "supersedes": supersedes_schema,
        },
    }
    counterfactual_write = {
        "type": "object",
        "additionalProperties": False,
        "required": ["explanation_ref", "intervention_effect", "prediction", "horizon", "basis_events", "supersedes"],
        "properties": {
            "explanation_ref": explanation_ref_schema,
            "intervention_effect": {
                "type": "object",
                "additionalProperties": False,
                "required": ["kind", "entity", "delta_centroid2"],
                "properties": {
                    "kind": {"const": "HypotheticalDisplacement"},
                    "entity": entity_ref_schema,
                    "delta_centroid2": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": {"type": "integer", "minimum": -128, "maximum": 128},
                    },
                },
            },
            "prediction": {
                "type": "object",
                "additionalProperties": False,
                "required": ["operator", "measure", "arguments"],
                "properties": {
                    "operator": {"type": "string", "enum": list(PREDICTION_OPERATORS)},
                    "measure": {"const": MEASURE},
                    "arguments": {
                        "type": "array",
                        "minItems": 2,
                        "maxItems": 2,
                        "items": entity_ref_schema,
                    },
                },
            },
            "horizon": {"const": 1},
            "basis_events": basis_schema,
            "supersedes": supersedes_schema,
        },
    }
    experiment_write = {
        "type": "object",
        "additionalProperties": False,
        "required": ["counterfactual_refs", "basis_events", "supersedes"],
        "properties": {
            "counterfactual_refs": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "uniqueItems": True,
                "items": counterfactual_ref_schema,
            },
            "basis_events": basis_schema,
            "supersedes": supersedes_schema,
        },
    }
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["protocol", "request_id", "basis_revision", *WRITE_KEYS],
        "properties": {
            "protocol": {"const": RESPONSE_PROTOCOL},
            "request_id": {"const": str(snapshot["request_id"])},
            "basis_revision": {"const": int(snapshot["basis_revision"])},
            "schema_writes": {"type": "array", "maxItems": MAX_WRITES, "items": schema_write},
            "explanation_writes": {"type": "array", "maxItems": MAX_WRITES, "items": explanation_write},
            "counterfactual_writes": {"type": "array", "maxItems": MAX_WRITES, "items": counterfactual_write},
            "discriminating_experiment_writes": {
                "type": "array",
                "maxItems": MAX_WRITES,
                "items": experiment_write,
            },
        },
    }


def build_request_payload(
    snapshot: Mapping[str, Any],
    config: Mapping[str, Any],
    *,
    prompt_path: Path | None = None,
) -> dict[str, Any]:
    """Build, but never send, one deterministic strict-schema Qwen request."""

    instruction = (prompt_path or HERE / "PROMPT.txt").read_text(encoding="utf-8")
    prompt = instruction + stable_json(_public_snapshot(snapshot))
    qwen = config["qwen"]
    payload: dict[str, Any] = {
        "model": qwen["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": qwen["temperature"],
        "top_p": qwen["top_p"],
        "seed": qwen["seed"],
        "max_tokens": qwen["max_tokens"],
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "parallel_cognitive_workspace_v0_1",
                "strict": True,
                "schema": response_schema(snapshot),
            },
        },
    }
    if "reasoning_budget_tokens" in qwen:
        payload["reasoning_budget_tokens"] = int(qwen["reasoning_budget_tokens"])
    elif "thinking_budget_tokens" in qwen:
        payload["thinking_budget_tokens"] = int(qwen["thinking_budget_tokens"])
    return payload


def _connected(conditions: Sequence[tuple[str, tuple[str, str]]]) -> bool:
    variables = {value for _predicate, arguments in conditions for value in arguments}
    if not variables:
        return False
    reached = {min(variables)}
    while True:
        before = len(reached)
        for _predicate, (left, right) in conditions:
            if left in reached or right in reached:
                reached.update((left, right))
        if len(reached) == before:
            return reached == variables


def _alpha_identity(
    conditions: Sequence[tuple[str, tuple[str, str]]],
    operator: str,
    effect_variables: tuple[str, str],
) -> dict[str, Any]:
    variables = sorted({value for _predicate, pair in conditions for value in pair} | set(effect_variables))
    canonical_names = [f"?v{index}" for index in range(len(variables))]
    encodings: list[tuple[Any, ...]] = []
    for permutation in itertools.permutations(canonical_names):
        mapping = dict(zip(variables, permutation, strict=True))
        normalized_conditions = tuple(
            sorted((predicate, mapping[left], mapping[right]) for predicate, (left, right) in conditions)
        )
        normalized_effect = tuple(sorted((mapping[effect_variables[0]], mapping[effect_variables[1]])))
        encodings.append((normalized_conditions, normalized_effect))
    normalized_conditions, normalized_effect = min(encodings)
    return {
        "conditions": [[predicate, [left, right]] for predicate, left, right in normalized_conditions],
        "consequence": [operator, [MEASURE, *normalized_effect]],
    }


def _basis_reason(write: Mapping[str, Any], snapshot: Mapping[str, Any]) -> str | None:
    values = write.get("basis_events")
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_BASIS_EVENTS:
        return "basis-events-contract"
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values):
        return "basis-events-contract"
    if len(set(values)) != len(values):
        return "duplicate-basis-event"
    allowed = {int(item) for item in snapshot.get("basis_events", ())}
    if any(value not in allowed or value > int(snapshot["basis_revision"]) for value in values):
        return "unknown-or-future-basis-event"
    return None


def _forbidden_reason(value: Any, snapshot: Mapping[str, Any]) -> str | None:
    tokens = {str(item).lower() for item in snapshot.get("_compiler_forbidden_tokens", ())}
    supplied_references = {
        str(item["id"]).lower() for item in snapshot.get("entities", ())
    } | {
        str(item["ref"]).lower() for item in snapshot.get("cognitive_objects", ())
    }

    def visit(item: Any) -> str | None:
        if isinstance(item, Mapping):
            for key, child in item.items():
                if _FORBIDDEN_OUTPUT_KEYS.search(str(key)):
                    return "forbidden-action-or-model-field"
                reason = visit(child)
                if reason:
                    return reason
        elif isinstance(item, (list, tuple)):
            for child in item:
                reason = visit(child)
                if reason:
                    return reason
        elif isinstance(item, str):
            lowered = item.lower()
            # Versioned entity/object references are opaque supplied tokens;
            # e.g. ``cf:left`` must not be mistaken for a direction command.
            if lowered in supplied_references:
                return None
            if lowered in tokens or _FORBIDDEN_OUTPUT_TEXT.search(item):
                return "forbidden-action-or-model-token"
        return None

    return visit(value)


def _supersedes_reason(write: Mapping[str, Any], snapshot: Mapping[str, Any]) -> str | None:
    values = write.get("supersedes")
    if not isinstance(values, list) or len(values) > 2 or len(set(map(str, values))) != len(values):
        return "supersedes-contract"
    allowed = {str(item["ref"]) for item in snapshot.get("cognitive_objects", ())}
    if any(not isinstance(value, str) or value not in allowed for value in values):
        return "unknown-superseded-object"
    return None


def _schema_template(raw: Mapping[str, Any]) -> Any:
    if set(raw) != {"conditions", "preferred_consequence", "basis_events", "supersedes"}:
        raise ValueError("schema-write-contract")
    raw_conditions = raw["conditions"]
    consequence = raw["preferred_consequence"]
    if not isinstance(raw_conditions, list) or not 1 <= len(raw_conditions) <= MAX_CONDITIONS:
        raise ValueError("condition-cap")
    conditions: list[tuple[str, tuple[str, str]]] = []
    for condition in raw_conditions:
        if not isinstance(condition, Mapping) or set(condition) != {"predicate", "arguments"}:
            raise ValueError("condition-contract")
        predicate = condition["predicate"]
        arguments = condition["arguments"]
        if predicate not in ALLOWED_PREDICATES:
            raise ValueError("unknown-predicate")
        if (
            not isinstance(arguments, list)
            or len(arguments) != 2
            or any(item not in ALLOWED_VARIABLES for item in arguments)
            or arguments[0] == arguments[1]
        ):
            raise ValueError("condition-arguments")
        conditions.append((str(predicate), (str(arguments[0]), str(arguments[1]))))
    if not isinstance(consequence, Mapping) or set(consequence) != {"operator", "measure", "arguments"}:
        raise ValueError("consequence-contract")
    operator = consequence["operator"]
    effect = consequence["arguments"]
    if operator not in SCHEMA_OPERATORS or consequence["measure"] != MEASURE:
        raise ValueError("unsupported-consequence")
    if (
        not isinstance(effect, list)
        or len(effect) != 2
        or effect[0] == effect[1]
        or any(item not in ALLOWED_VARIABLES for item in effect)
    ):
        raise ValueError("effect-arguments")
    condition_variables = {value for _predicate, pair in conditions for value in pair}
    if any(value not in condition_variables for value in effect):
        raise ValueError("ungrounded-effect-variable")
    if not _connected(conditions):
        raise ValueError("disconnected-condition-graph")
    identity = _alpha_identity(conditions, str(operator), (str(effect[0]), str(effect[1])))
    digest = V0.BASE.stable_hash(identity)
    template = V0.Template(
        tuple(sorted(set(conditions))),
        str(operator),
        (str(effect[0]), str(effect[1])),
        digest,
    )
    return template


def _entity_ref_valid(value: Any, snapshot: Mapping[str, Any]) -> bool:
    if not isinstance(value, Mapping) or set(value) != {"id", "generation"}:
        return False
    allowed = {
        (str(item["id"]), int(item.get("generation", 0)))
        for item in snapshot.get("entities", ())
    }
    return (str(value["id"]), int(value["generation"])) in allowed


def _audit_other_write(
    kind: str,
    index: int,
    raw: Any,
    snapshot: Mapping[str, Any],
    accepted_schema_indices: set[int],
    parsed: Mapping[str, Any],
) -> dict[str, Any]:
    record = {"index": index, "status": "accepted", "write": raw}
    if not isinstance(raw, Mapping):
        return {**record, "status": "rejected", "reason": "write-not-object"}
    reason = _forbidden_reason(raw, snapshot) or _basis_reason(raw, snapshot) or _supersedes_reason(raw, snapshot)
    if reason:
        return {**record, "status": "rejected", "reason": reason}
    try:
        if kind == "explanation_writes":
            if set(raw) != {"schema_ref", "bindings", "basis_events", "supersedes"}:
                raise ValueError("explanation-write-contract")
            reference = raw["schema_ref"]
            if not isinstance(reference, Mapping) or reference.get("source") not in {"workspace", "response"}:
                raise ValueError("schema-reference-contract")
            if reference["source"] == "workspace":
                refs = {
                    str(item["ref"])
                    for item in snapshot.get("cognitive_objects", ())
                    if str(item.get("kind", "")).lower() == "schema"
                }
                if set(reference) != {"source", "object_ref"} or reference["object_ref"] not in refs:
                    raise ValueError("unknown-schema-reference")
            else:
                if set(reference) != {"source", "schema_write_index"} or int(reference["schema_write_index"]) not in accepted_schema_indices:
                    raise ValueError("unknown-schema-write-reference")
            bindings = raw["bindings"]
            if not isinstance(bindings, list) or not 2 <= len(bindings) <= 4:
                raise ValueError("binding-contract")
            variables = []
            entities = []
            for binding in bindings:
                if not isinstance(binding, Mapping) or set(binding) != {"variable", "entity"}:
                    raise ValueError("binding-contract")
                if binding["variable"] not in ALLOWED_VARIABLES or not _entity_ref_valid(binding["entity"], snapshot):
                    raise ValueError("binding-reference")
                variables.append(binding["variable"])
                entities.append((binding["entity"]["id"], binding["entity"]["generation"]))
            if len(set(variables)) != len(variables) or len(set(entities)) != len(entities):
                raise ValueError("duplicate-binding")
        elif kind == "counterfactual_writes":
            expected = {"explanation_ref", "intervention_effect", "prediction", "horizon", "basis_events", "supersedes"}
            if set(raw) != expected or raw["horizon"] != 1:
                raise ValueError("counterfactual-write-contract")
            explanation_reference = raw["explanation_ref"]
            if (
                not isinstance(explanation_reference, Mapping)
                or explanation_reference.get("source") not in {"workspace", "response"}
            ):
                raise ValueError("explanation-reference-contract")
            if explanation_reference["source"] == "workspace":
                refs = {
                    str(item["ref"])
                    for item in snapshot.get("cognitive_objects", ())
                    if str(item.get("kind", "")).lower() == "explanation"
                }
                if (
                    set(explanation_reference) != {"source", "object_ref"}
                    or explanation_reference["object_ref"] not in refs
                ):
                    raise ValueError("unknown-explanation-reference")
            elif (
                set(explanation_reference) != {"source", "explanation_write_index"}
                or not isinstance(explanation_reference["explanation_write_index"], int)
                or not 0
                <= explanation_reference["explanation_write_index"]
                < len(parsed["explanation_writes"])
            ):
                raise ValueError("unknown-explanation-write-reference")
            effect = raw["intervention_effect"]
            if not isinstance(effect, Mapping) or set(effect) != {"kind", "entity", "delta_centroid2"}:
                raise ValueError("intervention-effect-contract")
            delta = effect["delta_centroid2"]
            if effect["kind"] != "HypotheticalDisplacement" or not _entity_ref_valid(effect["entity"], snapshot):
                raise ValueError("intervention-effect-contract")
            if not isinstance(delta, list) or len(delta) != 2 or any(isinstance(item, bool) or not isinstance(item, int) or abs(item) > 128 for item in delta):
                raise ValueError("intervention-effect-contract")
            prediction = raw["prediction"]
            if not isinstance(prediction, Mapping) or set(prediction) != {"operator", "measure", "arguments"}:
                raise ValueError("prediction-contract")
            arguments = prediction["arguments"]
            if prediction["operator"] not in PREDICTION_OPERATORS or prediction["measure"] != MEASURE:
                raise ValueError("prediction-contract")
            if not isinstance(arguments, list) or len(arguments) != 2 or any(not _entity_ref_valid(item, snapshot) for item in arguments):
                raise ValueError("prediction-contract")
        elif kind == "discriminating_experiment_writes":
            if set(raw) != {"counterfactual_refs", "basis_events", "supersedes"}:
                raise ValueError("experiment-write-contract")
            refs = raw["counterfactual_refs"]
            allowed = {
                str(item["ref"])
                for item in snapshot.get("cognitive_objects", ())
                if str(item.get("kind", "")).lower() == "counterfactual"
            }
            if not isinstance(refs, list) or len(refs) != 2 or len(set(refs)) != 2 or any(item not in allowed for item in refs):
                raise ValueError("counterfactual-reference-contract")
        else:
            raise ValueError("unknown-write-kind")
    except (KeyError, TypeError, ValueError) as error:
        return {**record, "status": "rejected", "reason": str(error)}
    return record


def compile_response(response: Mapping[str, Any], snapshot: Mapping[str, Any]) -> dict[str, Any]:
    """Semantically compile a strict response without granting it evidence."""

    parsed: Any = response.get("parsed", response)
    rejected: list[dict[str, Any]] = []
    empty_audit = {key: [] for key in WRITE_KEYS if key != "schema_writes"}
    expected = {"protocol", "request_id", "basis_revision", *WRITE_KEYS}
    if not isinstance(parsed, Mapping) or set(parsed) != expected:
        return {
            "valid_json_contract": False,
            "accepted": [],
            "accepted_schema_writes": [],
            "audited_writes": empty_audit,
            "rejected": [{"reason": "top-level-contract"}],
        }
    if (
        parsed["protocol"] != RESPONSE_PROTOCOL
        or parsed["request_id"] != snapshot["request_id"]
        or parsed["basis_revision"] != snapshot["basis_revision"]
        or any(not isinstance(parsed[key], list) for key in WRITE_KEYS)
    ):
        return {
            "valid_json_contract": False,
            "accepted": [],
            "accepted_schema_writes": [],
            "audited_writes": empty_audit,
            "rejected": [{"reason": "request-or-basis-contract"}],
        }
    total_writes = sum(len(parsed[key]) for key in WRITE_KEYS)
    if total_writes > MAX_WRITES:
        return {
            "valid_json_contract": False,
            "accepted": [],
            "accepted_schema_writes": [],
            "audited_writes": empty_audit,
            "rejected": [{"reason": "total-write-cap", "observed": total_writes}],
        }

    accepted_templates = []
    accepted_schema_writes = []
    accepted_schema_indices: set[int] = set()
    seen: set[str] = set()
    for index, raw in enumerate(parsed["schema_writes"]):
        reason = None
        try:
            if not isinstance(raw, Mapping):
                raise ValueError("write-not-object")
            reason = _forbidden_reason(raw, snapshot) or _basis_reason(raw, snapshot) or _supersedes_reason(raw, snapshot)
            if reason:
                raise ValueError(reason)
            template = _schema_template(raw)
            if template.canonical_hash in seen:
                raise ValueError("duplicate-alpha-template")
            seen.add(template.canonical_hash)
            accepted_schema_indices.add(index)
            encoded = asdict(template)
            accepted_templates.append(encoded)
            accepted_schema_writes.append({"index": index, "write": raw, "template": encoded})
        except (KeyError, TypeError, ValueError) as error:
            rejected.append({"kind": "schema_writes", "index": index, "reason": str(error), "raw": raw})

    audited = {}
    for kind in WRITE_KEYS[1:]:
        records = [
            _audit_other_write(kind, index, raw, snapshot, accepted_schema_indices, parsed)
            for index, raw in enumerate(parsed[kind])
        ]
        audited[kind] = records
        rejected.extend(
            {"kind": kind, "index": item["index"], "reason": item["reason"], "raw": item["write"]}
            for item in records
            if item["status"] == "rejected"
        )
    return {
        "valid_json_contract": True,
        "accepted": accepted_templates,
        "accepted_schema_writes": accepted_schema_writes,
        "audited_writes": audited,
        "rejected": rejected,
    }


def templates_from_compilation(compilation: Mapping[str, Any]) -> tuple[Any, ...]:
    """Rehydrate v0 Template values for the existing pair-potential grounder."""

    output = []
    for item in compilation.get("accepted", ()):
        output.append(
            V0.Template(
                conditions=tuple((value[0], tuple(value[1])) for value in item["conditions"]),
                operator=str(item["operator"]),
                effect_variables=tuple(item["effect_variables"]),
                canonical_hash=str(item["canonical_hash"]),
                provenance=str(item.get("provenance", "externally-proposed")),
            )
        )
    return tuple(output)
