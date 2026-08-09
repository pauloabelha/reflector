"""Cognition-side adapter for prospective-evidence revision tasks.

The v1.4 protocol treats an explicitly linked R2 criticism as the sole source
of revision lineage.  This adapter extends that boundary for the
``prospective-evidence-return`` status: environment evidence which caused the
criticism remains citable even though, causally, it was created *before* the
criticism.  The authoritative graph and the v1.4 compiler remain unchanged.

Runner integration is intentionally one line::

    evidence_revision.install(QC)

``QC`` is the dynamically loaded v1.4 ``qwen_cognition`` module.
"""

from __future__ import annotations

import itertools
import re
from typing import Any, Callable, Mapping, Sequence


STATUS = "prospective-evidence-return"
GROUNDING_PROTOCOL = "exact-action-free-grounding-state-v1"
PROMPT_RULE = (
    "\n21. When revision_task has criticism_status prospective-evidence-return, "
    "treat its explicitly linked environment evidence as causally prior but "
    "currently citable. Revise against the exact action-free grounding_state "
    "in that criticism; do not infer an environment operation from it.\n"
)

_FORBIDDEN_GROUNDING_KEY = re.compile(
    r"(?:^|_)(?:actions?|action_id|action_token|button|command|policy|games?|game_id)(?:$|_)",
    re.IGNORECASE,
)
_FORBIDDEN_GROUNDING_TEXT = re.compile(
    r"(?:arc-action|\baction\b|\bbutton\b|\bcommand\b|\bpolicy\b|\bgame\b|\b(?:up|down|left|right)\b)",
    re.IGNORECASE,
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


def _witness(qc: Any, criticism: Any) -> Mapping[str, Any]:
    value = qc._criticism_witness(criticism.payload)
    if not isinstance(value, Mapping):
        _fail(qc, "evidence-revision-witness-contract")
    return value


def _contains_forbidden_key(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            _FORBIDDEN_GROUNDING_KEY.search(str(key))
            or (str(key) != "protocol" and _contains_forbidden_key(item))
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_forbidden_key(item) for item in value)
    return isinstance(value, str) and bool(_FORBIDDEN_GROUNDING_TEXT.search(value))


def _eligible_units(qc: Any, state: Any) -> tuple[dict[str, Any], ...]:
    return tuple(
        dict(unit)
        for unit in qc.exact_causal_chains(state)
        if unit.get("criticism_status") == STATUS
    )


def _causing_evidence(qc: Any, state: Any, unit: Mapping[str, Any]) -> tuple[Any, ...]:
    objects = {item.object_id: item for item in state.objects}
    criticism = objects.get(str(unit["criticism_id"]))
    if criticism is None:
        _fail(qc, "evidence-revision-criticism-missing")
    output = []
    for dependency_id in criticism.dependency_ids:
        item = objects.get(str(dependency_id))
        if (
            item is not None
            and item.kind == "environment_evidence"
            and item.created_by == "environment"
            and item.created_revision < criticism.created_revision
            and item.payload.get("prospective") is not None
        ):
            output.append(item)
    if not output:
        _fail(qc, "evidence-revision-cause-missing")
    return tuple(sorted(output, key=lambda item: (item.created_revision, item.object_id)))


def _render_id(real_to_alias: Mapping[str, str], value: str) -> str:
    return str(real_to_alias.get(str(value), str(value)))


def _task_document(
    qc: Any,
    unit: Mapping[str, Any],
    real_to_alias: Mapping[str, str],
    evidence_ids: Sequence[str],
    grounding_state: Mapping[str, Any],
) -> dict[str, Any]:
    rendered = qc._replace_ids(dict(unit), real_to_alias)
    return {
        key: rendered[key]
        for key in (
            "chain_ref",
            "derivation_id",
            "semantic_target_id",
            "criticism_id",
            "criticism_status",
            "target_alpha_signature",
            "candidate_refs",
        )
    } | {
        "causing_evidence_ids": [
            _render_id(real_to_alias, object_id) for object_id in evidence_ids
        ],
        "grounding_state_digest": qc.stable_hash(grounding_state),
    }


def wrap_build_turn(qc: Any, base_build_turn: Callable[..., Any]) -> Callable[..., Any]:
    """Return a v1.4-compatible builder with evidence-return revision lineage."""

    def build_turn(
        state: Any,
        events: Sequence[Any],
        orientation: Any,
        *,
        request_id: str,
        token_budget: int,
        max_deltas: int | None = None,
        compact_ids: bool = False,
    ) -> Any:
        kwargs = {
            "request_id": request_id,
            "token_budget": token_budget,
            "compact_ids": compact_ids,
        }
        if max_deltas is not None:
            kwargs["max_deltas"] = max_deltas
        base = base_build_turn(state, events, orientation, **kwargs)
        units = _eligible_units(qc, state)
        if not units:
            return base
        unit = units[0]
        objects = {item.object_id: item for item in state.objects}
        criticism = objects[str(unit["criticism_id"])]
        witness = _witness(qc, criticism)
        grounding_state = witness.get("grounding_state")
        if not isinstance(grounding_state, Mapping):
            _fail(qc, "evidence-revision-grounding-state-missing")
        _validate_grounding_state_contract(qc, grounding_state)
        evidence = _causing_evidence(qc, state, unit)

        real_to_alias = {real: alias for alias, real in base.id_aliases}
        visible = {
            str(item.get("id"))
            for item in base.document.get("sparse_cut", {}).get("objects", ())
            if isinstance(item, Mapping)
        }
        rendered_evidence = [
            _render_id(real_to_alias, item.object_id) for item in evidence
        ]
        if any(object_id not in visible for object_id in rendered_evidence):
            # Explicit criticism dependencies must enter the inherited
            # dependency-closed cut.  Failing here is safer than fabricating a
            # non-closed side channel or silently weakening citation checks.
            _fail(qc, "evidence-revision-cause-not-visible")

        task = _task_document(
            qc,
            unit,
            real_to_alias,
            [item.object_id for item in evidence],
            grounding_state,
        )
        document = {**base.document, "revision_task": task}
        validation = dict(base.validation_context)
        validation["evidence_revision_unit"] = dict(unit)
        validation["causal_prospective_evidence_ids"] = list(rendered_evidence)
        # v1.4's compiler consumes this key.  For this status causality, not
        # chronology, determines qualification, so evidence before criticism
        # is deliberately included.
        validation["visible_post_criticism_prospective_evidence_ids"] = list(
            rendered_evidence
        )
        validation["exact_grounding_state_digest"] = qc.stable_hash(grounding_state)
        return qc.CognitionTurn(
            request_id=base.request_id,
            workspace_id=base.workspace_id,
            basis_revision=base.basis_revision,
            basis_hash=base.basis_hash,
            mode=base.mode,
            document=document,
            id_aliases=base.id_aliases,
            validation_context=validation,
        )

    build_turn.__name__ = "build_turn"
    build_turn.__doc__ = "v1.9 evidence-return adapter over v1.4 build_turn."
    return build_turn


def _validate_grounding_state_contract(qc: Any, value: Mapping[str, Any]) -> None:
    if value.get("protocol") != GROUNDING_PROTOCOL:
        _fail(qc, "grounding-state-protocol")
    if value.get("population_complete") is not True:
        _fail(qc, "grounding-state-incomplete")
    if any(
        bool(value.get(key))
        for key in ("truncated", "entities_truncated", "relations_truncated")
    ):
        _fail(qc, "grounding-state-truncated")
    if _contains_forbidden_key(value):
        _fail(qc, "grounding-state-not-action-free")
    entities = value.get("entities")
    relations = value.get("relations")
    if not isinstance(entities, list) or len(entities) < 2:
        _fail(qc, "grounding-state-entities")
    if not isinstance(relations, list):
        _fail(qc, "grounding-state-relations")


def _grounding_view(qc: Any, value: Mapping[str, Any]) -> tuple[
    dict[str, Mapping[str, Any]], set[tuple[str, str, str]]
]:
    _validate_grounding_state_contract(qc, value)
    entities: dict[str, Mapping[str, Any]] = {}
    for raw in value["entities"]:
        if not isinstance(raw, Mapping) or not isinstance(raw.get("id"), str):
            _fail(qc, "grounding-state-entity-contract")
        entity_id = str(raw["id"])
        if entity_id in entities:
            _fail(qc, "grounding-state-duplicate-entity")
        descriptor = raw.get("descriptor", raw.get("payload"))
        if not isinstance(descriptor, Mapping):
            descriptor = {
                key: item for key, item in raw.items() if key != "id"
            }
        entities[entity_id] = {"kind": "entity", "payload": dict(descriptor)}

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


def validate_complete_grounding(qc: Any, conditions: Sequence[Mapping[str, Any]], turn: Any) -> None:
    """Require a revision to select one pair over the exact complete state."""

    task = turn.document.get("revision_task")
    if not isinstance(task, Mapping) or task.get("criticism_status") != STATUS:
        _fail(qc, "evidence-revision-task-absent")
    documents = qc._visible_object_documents(turn)
    criticism = documents.get(str(task.get("criticism_id")), {})
    payload = criticism.get("payload", {})
    witness = qc._criticism_witness(payload) if isinstance(payload, Mapping) else {}
    grounding_state = witness.get("grounding_state") if isinstance(witness, Mapping) else None
    if not isinstance(grounding_state, Mapping):
        _fail(qc, "evidence-revision-grounding-state-missing")
    expected_digest = turn.validation_context.get("exact_grounding_state_digest")
    if expected_digest is not None and qc.stable_hash(grounding_state) != expected_digest:
        _fail(qc, "grounding-state-digest-mismatch")
    entities, facts = _grounding_view(qc, grounding_state)

    target = documents.get(str(task.get("semantic_target_id")), {})
    target_payload = target.get("payload", {})
    consequence = (
        target_payload.get("preferred_consequence", {})
        if isinstance(target_payload, Mapping)
        else {}
    )
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
        _fail(qc, "grounding-state-no-complete-assignment")

    retained_pairs: set[tuple[str, str]] = set()
    retained_count = 0
    entity_ids = sorted(entities)
    for values in itertools.permutations(entity_ids, len(variables)):
        assignment = dict(zip(variables, values))
        keep = True
        for condition in conditions:
            arguments = condition.get("arguments")
            if not isinstance(arguments, list) or len(arguments) != 2:
                _fail(qc, "condition-arguments")
            result = qc._condition_holds(
                str(condition.get("predicate")),
                assignment[str(arguments[0])],
                assignment[str(arguments[1])],
                entities,
                facts,
            )
            if result is None:
                _fail(qc, "grounding-validation-unknown")
            if not result:
                keep = False
                break
        if keep:
            retained_count += 1
            retained_pairs.add(
                tuple(sorted(assignment[str(item)] for item in effect_variables))
            )
    if retained_count == 0:
        _fail(qc, "grounding-validation-empty")
    if len(retained_pairs) != 1:
        _fail(qc, "grounding-not-unique")


def make_revision_validator(qc: Any, fallback: Callable[..., Any]) -> Callable[..., Any]:
    """Dispatch evidence-return tasks to complete-state validation."""

    def validator(conditions: Sequence[Mapping[str, Any]], turn: Any) -> None:
        task = turn.document.get("revision_task")
        if isinstance(task, Mapping) and task.get("criticism_status") == STATUS:
            validate_complete_grounding(qc, conditions, turn)
            return
        fallback(conditions, turn)

    return validator


def install(qc: Any) -> Any:
    """Idempotently monkeypatch the v1.4 cognition module and return it."""

    if getattr(qc, "_EVIDENCE_REVISION_V19_INSTALLED", False):
        return qc
    qc._EVIDENCE_REVISION_V19_BASE_BUILD_TURN = qc.build_turn
    qc._EVIDENCE_REVISION_V19_BASE_VALIDATOR = qc._validate_unique_revision
    qc.build_turn = wrap_build_turn(qc, qc.build_turn)
    qc._validate_unique_revision = make_revision_validator(
        qc, qc._EVIDENCE_REVISION_V19_BASE_VALIDATOR
    )
    if PROMPT_RULE.strip() not in qc.PROMPT:
        qc.PROMPT += PROMPT_RULE
    qc._EVIDENCE_REVISION_V19_INSTALLED = True
    return qc


__all__ = [
    "GROUNDING_PROTOCOL",
    "PROMPT_RULE",
    "STATUS",
    "install",
    "make_revision_validator",
    "validate_complete_grounding",
    "wrap_build_turn",
]
