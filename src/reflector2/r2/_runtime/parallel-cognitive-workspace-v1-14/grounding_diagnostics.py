"""Complete-grounding predicate diagnostics for semantic revision turns.

This adapter is deliberately independent of any environment operation or
task identity.  It projects a complete entity/relation population into the
unordered effect pairs retained by every predicate in the cognition DSL.
"""

from __future__ import annotations

import itertools
from copy import deepcopy
from dataclasses import replace
from typing import Any, Callable, Mapping, Sequence


PROTOCOL = "complete-grounding-predicate-diagnostics-v1"
LEVERAGE_PROTOCOL = "grounding-control-leverage-v1"
GROUNDING_PROTOCOL = "exact-action-free-grounding-state-v1"
PROMPT_RULE = (
    "\n22. grounding_diagnostics is a complete closed-world table: each "
    "predicate row lists every unordered effect pair it retains. Prefer a "
    "row classified unique; empty retains none and ambiguous retains several. "
    "control_leverage summarizes executed relative-delta observations, and "
    "exact temporal relations fill pairs without an adjudicating probe model. "
    "ranked_unique_predicates_with_leverage is attention guidance rather than "
    "epistemic support.\n"
)
REVISION_DIAGNOSTIC_RULE = (
    "GROUNDING_DIAGNOSTIC_RULE: An executable revision MUST retain exactly one "
    "effect pair. When ranked_unique_predicates_with_leverage is nonempty, copy "
    "ONLY its rank=1 predicate into conditions as exactly one atom using the same "
    "effect variables; do not add any other predicate. When that ranking is empty, "
    "use any condition set whose retained-pair intersection is exactly one pair. "
    "Remove inherited conditions that preserve other pairs, and never emit a "
    "predicate classified ambiguous. Abstain if the closed vocabulary cannot "
    "satisfy these constraints.\n"
)

_SYMMETRIC = frozenset(
    {
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
        "ChangedTogether",
    }
)


def _fail(qc: Any, reason: str) -> None:
    raise qc.CognitionError(reason)


def _complete(value: Mapping[str, Any]) -> bool:
    return (
        value.get("protocol") == GROUNDING_PROTOCOL
        and value.get("population_complete") is True
        and not any(
            bool(value.get(key))
            for key in ("truncated", "entities_truncated", "relations_truncated")
        )
        and isinstance(value.get("entities"), list)
        and isinstance(value.get("relations"), list)
    )


def grounding_view(
    qc: Any, value: Mapping[str, Any]
) -> tuple[dict[str, Mapping[str, Any]], set[tuple[str, str, str]]]:
    """Parse a complete grounding without adding unobserved positive facts."""

    if not _complete(value):
        _fail(qc, "grounding-state-not-complete")
    entities: dict[str, Mapping[str, Any]] = {}
    for raw in value["entities"]:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str):
            _fail(qc, "grounding-state-entity-contract")
        entity_id = str(raw["id"])
        if entity_id in entities:
            _fail(qc, "grounding-state-duplicate-entity")
        descriptor = raw.get("descriptor", raw.get("payload"))
        if not isinstance(descriptor, Mapping):
            descriptor = {key: item for key, item in raw.items() if key != "id"}
        entities[entity_id] = {"kind": "entity", "payload": dict(descriptor)}
    if len(entities) < 2:
        _fail(qc, "grounding-state-entities")
    facts: set[tuple[str, str, str]] = set()
    for raw in value["relations"]:
        if not isinstance(raw, Mapping):
            _fail(qc, "grounding-state-relation-contract")
        predicate, arguments = raw.get("predicate"), raw.get("arguments")
        if (
            predicate not in qc.PREDICATES
            or not isinstance(arguments, list)
            or len(arguments) != 2
            or any(str(item) not in entities for item in arguments)
        ):
            _fail(qc, "grounding-state-relation-contract")
        left, right = str(arguments[0]), str(arguments[1])
        facts.add((str(predicate), left, right))
        if predicate in _SYMMETRIC:
            facts.add((str(predicate), right, left))
    return entities, facts


def closed_world_holds(
    qc: Any,
    predicate: str,
    left_id: str,
    right_id: str,
    entities: Mapping[str, Mapping[str, Any]],
    facts: set[tuple[str, str, str]],
) -> bool:
    """Resolve descriptor predicates, then treat absent complete facts as false."""

    result = qc._condition_holds(predicate, left_id, right_id, entities, facts)
    return False if result is None else bool(result)


def _decode_probe_judgments(table: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Join the exact columnar cohort without retaining graph addresses."""

    try:
        bindings = [
            dict(zip(table["binding_columns"], row, strict=True))
            for row in table["bindings"]
        ]
        judgments = [
            dict(zip(table["judgment_columns"], row, strict=True))
            for row in table["judgments"]
        ]
        return [
            {**bindings[int(item["binding_index"])], **item}
            for item in judgments
        ]
    except (KeyError, TypeError, ValueError, IndexError) as error:
        raise ValueError("invalid executed probe judgment table") from error


def _delta_nonzero(value: Any) -> bool | None:
    if not isinstance(value, (list, tuple)) or not value:
        return None
    if any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in value):
        return None
    return any(float(item) != 0.0 for item in value)


def derive_control_leverage(
    grounding: Mapping[str, Any],
    executed_probe_judgments: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Classify every current pair from executed relative-delta observations.

    The precedence is empirical: any nonzero observed relative delta establishes
    leverage, while a fully observed modelled zero cohort establishes invariance.
    Exact ``MovedTogether`` and ``MovedWhileStationary`` facts fill pairs whose
    judgments are unmodelled or unknown.  Agreement and conflict remain explicit.
    """

    entity_ids = sorted(
        str(item["id"])
        for item in grounding.get("entities", ())
        if isinstance(item, Mapping) and isinstance(item.get("id"), str)
    )
    population = tuple(itertools.combinations(entity_ids, 2))
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {
        pair: [] for pair in population
    }
    decoded = (
        _decode_probe_judgments(executed_probe_judgments)
        if isinstance(executed_probe_judgments, Mapping)
        else []
    )
    for item in decoded:
        raw_pair = item.get("effect_pair")
        if not isinstance(raw_pair, list) or len(raw_pair) != 2:
            continue
        pair = tuple(sorted(str(value) for value in raw_pair))
        if pair in grouped:
            grouped[pair].append(item)

    temporal_by_pair: dict[tuple[str, str], set[str]] = {
        pair: set() for pair in population
    }
    for relation in grounding.get("relations", ()):
        if not isinstance(relation, Mapping):
            continue
        predicate, arguments = relation.get("predicate"), relation.get("arguments")
        if predicate not in {"MovedTogether", "MovedWhileStationary"}:
            continue
        if not isinstance(arguments, list) or len(arguments) != 2:
            continue
        pair = tuple(sorted(str(value) for value in arguments))
        if pair not in temporal_by_pair:
            continue
        temporal_by_pair[pair].add(
            "invariant"
            if predicate == "MovedTogether"
            else "relative_motion_observed"
        )

    rows: list[dict[str, Any]] = []
    for pair in population:
        items = grouped[pair]
        observed = [_delta_nonzero(item.get("observed_delta")) for item in items]
        predicted = [_delta_nonzero(item.get("predicted_delta")) for item in items]
        modeled_count = sum(item.get("modeled") is True for item in items)
        no_model_count = sum(item.get("modeled") is False for item in items)
        nonzero_count = sum(value is True for value in observed)
        zero_count = sum(value is False for value in observed)
        known_observed_count = nonzero_count + zero_count
        if nonzero_count:
            judgment_classification = "relative_motion_observed"
        elif items and modeled_count == 0 and no_model_count == len(items):
            judgment_classification = "no-model"
        elif (
            items
            and modeled_count > 0
            and known_observed_count == len(items)
            and zero_count == len(items)
        ):
            judgment_classification = "invariant"
        else:
            judgment_classification = "unknown"

        temporal_values = temporal_by_pair[pair]
        temporal_classification = (
            next(iter(temporal_values))
            if len(temporal_values) == 1
            else "conflict"
            if len(temporal_values) > 1
            else None
        )
        if judgment_classification in {
            "relative_motion_observed",
            "invariant",
        }:
            classification = judgment_classification
            provenance = "executed_probe_judgment"
            consistency = (
                "not_applicable"
                if temporal_classification is None
                else "temporal_conflict"
                if temporal_classification == "conflict"
                else "consistent"
                if temporal_classification == judgment_classification
                else "conflict"
            )
        elif temporal_classification in {
            "relative_motion_observed",
            "invariant",
        }:
            classification = temporal_classification
            provenance = "temporal_relation"
            consistency = (
                "no_probe_judgment"
                if not items
                else "judgment_non_adjudicating"
            )
        elif temporal_classification == "conflict":
            classification = "unknown"
            provenance = "temporal_relation"
            consistency = "temporal_conflict"
        else:
            classification = judgment_classification
            provenance = (
                "executed_probe_judgment" if items else "none"
            )
            consistency = "not_applicable"
        rows.append(
            {
                "effect_pair": list(pair),
                "classification": classification,
                "provenance": provenance,
                "consistency": consistency,
                "judgment_classification": judgment_classification,
                "temporal_classification": temporal_classification,
                "judgment_count": len(items),
                "modeled_count": modeled_count,
                "no_model_count": no_model_count,
                "observed_nonzero_count": nonzero_count,
                "observed_zero_count": zero_count,
                "predicted_nonzero_count": sum(value is True for value in predicted),
            }
        )
    return {
        "protocol": LEVERAGE_PROTOCOL,
        "basis": "executed-probe-relative-deltas",
        "effect_pair_order": "unordered",
        "pair_rows": rows,
    }


def _rank_leveraged_unique_predicates(
    predicate_rows: Sequence[Mapping[str, Any]],
    leverage: Mapping[str, Any],
) -> list[dict[str, Any]]:
    leverage_by_pair = {
        tuple(str(value) for value in item["effect_pair"]): item
        for item in leverage.get("pair_rows", ())
        if isinstance(item, Mapping)
        and isinstance(item.get("effect_pair"), list)
        and len(item["effect_pair"]) == 2
    }
    ranked: list[dict[str, Any]] = []
    for row in predicate_rows:
        pairs = row.get("retained_effect_pairs")
        if row.get("classification") != "unique" or not isinstance(pairs, list):
            continue
        pair = tuple(str(value) for value in pairs[0])
        leverage_row = leverage_by_pair.get(pair)
        if not isinstance(leverage_row, Mapping) or (
            leverage_row.get("classification") != "relative_motion_observed"
        ):
            continue
        ranked.append(
            {
                "predicate": str(row["predicate"]),
                "effect_pair": list(pair),
                "control_leverage": "relative_motion_observed",
                "observed_nonzero_count": int(leverage_row["observed_nonzero_count"]),
                "judgment_count": int(leverage_row["judgment_count"]),
            }
        )
    ranked.sort(
        key=lambda item: (
            -item["observed_nonzero_count"],
            -item["judgment_count"],
            item["predicate"],
        )
    )
    return [{"rank": index, **item} for index, item in enumerate(ranked, 1)]


def enumerate_predicate_pairs(
    qc: Any,
    grounding: Mapping[str, Any],
    *,
    executed_probe_judgments: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Enumerate the exact unordered effect-pair population for each predicate."""

    entities, facts = grounding_view(qc, grounding)
    pairs = tuple(itertools.combinations(sorted(entities), 2))
    rows: list[dict[str, Any]] = []
    for predicate in qc.PREDICATES:
        retained = [
            [left, right]
            for left, right in pairs
            if closed_world_holds(qc, predicate, left, right, entities, facts)
            or (
                predicate not in _SYMMETRIC
                and closed_world_holds(qc, predicate, right, left, entities, facts)
            )
        ]
        classification = (
            "empty" if not retained else "unique" if len(retained) == 1 else "ambiguous"
        )
        rows.append(
            {
                "predicate": str(predicate),
                "retained_effect_pairs": retained,
                "retained_pair_count": len(retained),
                "classification": classification,
            }
        )
    output = {
        "protocol": PROTOCOL,
        "population_complete": True,
        "relations_complete": True,
        "effect_pair_order": "unordered",
        "effect_pair_population": [list(pair) for pair in pairs],
        "predicate_rows": rows,
        "unique_predicates": [
            row["predicate"] for row in rows if row["classification"] == "unique"
        ],
    }
    leverage = derive_control_leverage(grounding, executed_probe_judgments)
    output["control_leverage"] = leverage
    output["ranked_unique_predicates_with_leverage"] = (
        _rank_leveraged_unique_predicates(rows, leverage)
    )
    return output


def grounding_from_turn(qc: Any, turn: Any) -> Mapping[str, Any] | None:
    task = turn.document.get("revision_task")
    if not isinstance(task, Mapping):
        return None
    criticism = qc._visible_object_documents(turn).get(str(task.get("criticism_id")), {})
    payload = criticism.get("payload", {})
    witness = qc._criticism_witness(payload) if isinstance(payload, Mapping) else {}
    value = witness.get("grounding_state") if isinstance(witness, Mapping) else None
    return value if isinstance(value, Mapping) else None


def augment_turn(qc: Any, turn: Any) -> Any:
    """Place the complete diagnostic table beside the live revision task."""

    grounding = grounding_from_turn(qc, turn)
    task = turn.document.get("revision_task")
    if not isinstance(task, Mapping) or grounding is None or not _complete(grounding):
        return turn
    packet = turn.document.get("causal_revision_packet")
    executed = (
        packet.get("executed_probe_judgments")
        if isinstance(packet, Mapping)
        else None
    )
    diagnostics = enumerate_predicate_pairs(
        qc, grounding, executed_probe_judgments=executed
    )
    document = {
        **turn.document,
        "revision_task": {**dict(task), "grounding_diagnostics": diagnostics},
    }
    return replace(turn, document=document)


def _has_grounding_diagnostics(turn: Any) -> bool:
    task = turn.document.get("revision_task")
    return isinstance(task, Mapping) and isinstance(
        task.get("grounding_diagnostics"), Mapping
    )


def _inject_diagnostic_rule(text: str) -> str:
    if REVISION_DIAGNOSTIC_RULE.strip() in text:
        return text
    marker = "EPISTEMIC_INPUT=\n"
    if marker in text:
        return text.replace(
            marker, f"{REVISION_DIAGNOSTIC_RULE}{marker}", 1
        )
    return f"{REVISION_DIAGNOSTIC_RULE}{text}"


def wrap_request_payload(qc: Any, fallback: Callable[..., Any]) -> Callable[..., Any]:
    """Inject executable diagnostic guidance without mutating inherited payloads."""

    def request_payload(
        turn: Any,
        qwen: Mapping[str, Any],
        *,
        visual_evidence: Sequence[Mapping[str, str]] = (),
    ) -> dict[str, Any]:
        inherited = fallback(turn, qwen, visual_evidence=visual_evidence)
        if not _has_grounding_diagnostics(turn):
            return inherited
        output = deepcopy(inherited)
        messages = output.get("messages")
        if not isinstance(messages, list) or not messages:
            return output
        content = messages[0].get("content")
        if isinstance(content, str):
            messages[0]["content"] = _inject_diagnostic_rule(content)
            return output
        if isinstance(content, list):
            for part in content:
                if isinstance(part, Mapping) and part.get("type") == "text" and isinstance(
                    part.get("text"), str
                ):
                    part["text"] = _inject_diagnostic_rule(str(part["text"]))
                    break
        return output

    return request_payload


def validate_complete_closed_world(
    qc: Any, conditions: Sequence[Mapping[str, Any]], turn: Any
) -> None:
    """Validate conjunctions exactly; complete missing facts are false, not unknown."""

    grounding = grounding_from_turn(qc, turn)
    if grounding is None or not _complete(grounding):
        _fail(qc, "grounding-state-not-complete")
    expected = turn.validation_context.get("exact_grounding_state_digest")
    if expected is not None and qc.stable_hash(grounding) != expected:
        _fail(qc, "grounding-state-digest-mismatch")
    entities, facts = grounding_view(qc, grounding)
    task = turn.document["revision_task"]
    target = qc._visible_object_documents(turn).get(str(task.get("semantic_target_id")), {})
    payload = target.get("payload", {})
    consequence = payload.get("preferred_consequence", {}) if isinstance(payload, Mapping) else {}
    effect_variables = consequence.get("arguments")
    if not isinstance(effect_variables, list) or len(effect_variables) != 2:
        _fail(qc, "grounding-state-effect-variables")
    variables = sorted(
        {
            str(argument)
            for condition in conditions
            for argument in condition.get("arguments", ())
        }
        | {str(item) for item in effect_variables}
    )
    if not variables or any(variable not in qc.VARIABLES for variable in variables):
        _fail(qc, "grounding-state-variable-contract")
    if len(variables) > len(entities):
        _fail(qc, "grounding-validation-empty")

    retained: set[tuple[str, str]] = set()
    for values in itertools.permutations(sorted(entities), len(variables)):
        assignment = dict(zip(variables, values))
        keep = True
        for condition in conditions:
            arguments = condition.get("arguments")
            predicate = str(condition.get("predicate"))
            if (
                predicate not in qc.PREDICATES
                or not isinstance(arguments, list)
                or len(arguments) != 2
                or any(str(item) not in assignment for item in arguments)
            ):
                _fail(qc, "condition-arguments")
            if not closed_world_holds(
                qc,
                predicate,
                assignment[str(arguments[0])],
                assignment[str(arguments[1])],
                entities,
                facts,
            ):
                keep = False
                break
        if keep:
            retained.add(tuple(sorted(assignment[str(item)] for item in effect_variables)))
    if not retained:
        _fail(qc, "grounding-validation-empty")
    if len(retained) != 1:
        _fail(qc, "grounding-validation-ambiguous")


def make_validator(qc: Any, fallback: Callable[..., Any]) -> Callable[..., Any]:
    def validator(conditions: Sequence[Mapping[str, Any]], turn: Any) -> None:
        grounding = grounding_from_turn(qc, turn)
        if isinstance(grounding, Mapping) and _complete(grounding):
            validate_complete_closed_world(qc, conditions, turn)
            return
        fallback(conditions, turn)

    return validator


def install(qc: Any) -> Any:
    """Install after existing revision adapters; idempotent and runner-agnostic."""

    if getattr(qc, "_GROUNDING_DIAGNOSTICS_V114_INSTALLED", False):
        return qc
    qc._GROUNDING_DIAGNOSTICS_V114_BASE_BUILD_TURN = qc.build_turn
    qc._GROUNDING_DIAGNOSTICS_V114_BASE_VALIDATOR = qc._validate_unique_revision
    qc._GROUNDING_DIAGNOSTICS_V114_BASE_REQUEST_PAYLOAD = qc.request_payload

    def build_turn(*args: Any, **kwargs: Any) -> Any:
        return augment_turn(
            qc, qc._GROUNDING_DIAGNOSTICS_V114_BASE_BUILD_TURN(*args, **kwargs)
        )

    qc.build_turn = build_turn
    qc._validate_unique_revision = make_validator(
        qc, qc._GROUNDING_DIAGNOSTICS_V114_BASE_VALIDATOR
    )
    qc.request_payload = wrap_request_payload(
        qc, qc._GROUNDING_DIAGNOSTICS_V114_BASE_REQUEST_PAYLOAD
    )
    if PROMPT_RULE.strip() not in qc.PROMPT:
        qc.PROMPT += PROMPT_RULE
    qc._GROUNDING_DIAGNOSTICS_V114_INSTALLED = True
    return qc


__all__ = [
    "LEVERAGE_PROTOCOL",
    "PROTOCOL",
    "PROMPT_RULE",
    "REVISION_DIAGNOSTIC_RULE",
    "augment_turn",
    "closed_world_holds",
    "derive_control_leverage",
    "enumerate_predicate_pairs",
    "grounding_from_turn",
    "grounding_view",
    "install",
    "make_validator",
    "validate_complete_closed_world",
    "wrap_request_payload",
]
