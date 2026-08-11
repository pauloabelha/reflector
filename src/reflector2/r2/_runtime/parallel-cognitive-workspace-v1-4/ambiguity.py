"""Bounded, action-agnostic witnesses for ambiguous relational grounding.

The controller's ordinary grounding result deliberately stays small.  This
module reconstructs enough of the same join to explain *which* substitutions
and effect pairs competed, and which visible relation facts separate them.
It is experiment-local and has no dependency on a particular game or action
vocabulary.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any


PROTOCOL = "bounded-relational-ambiguity-v1.0"
DEFAULT_SYMMETRIC_PREDICATES = frozenset(
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
    }
)


class AmbiguityError(ValueError):
    """The relational state or template cannot be compiled safely."""


def _stable_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _digest(value: object) -> str:
    return hashlib.sha256(_stable_json(value).encode("utf-8")).hexdigest()


def _template_parts(template: Any) -> tuple[tuple[tuple[str, tuple[str, str]], ...], tuple[str, str], str]:
    if isinstance(template, Mapping):
        raw_conditions = template.get("conditions", ())
        preferred = template.get("preferred_consequence", {})
        raw_effect = template.get("effect_variables", preferred.get("arguments", ()))
        template_hash = template.get("canonical_hash", template.get("template_hash"))
    else:
        raw_conditions = getattr(template, "conditions", ())
        raw_effect = getattr(template, "effect_variables", ())
        template_hash = getattr(template, "canonical_hash", None)

    conditions: list[tuple[str, tuple[str, str]]] = []
    for condition in raw_conditions:
        if isinstance(condition, Mapping):
            predicate = condition.get("predicate")
            arguments = condition.get("arguments")
        else:
            try:
                predicate, arguments = condition
            except (TypeError, ValueError) as error:
                raise AmbiguityError("invalid template condition") from error
        if not isinstance(predicate, str) or not isinstance(arguments, Sequence) or isinstance(arguments, str):
            raise AmbiguityError("invalid template condition")
        values = tuple(str(item) for item in arguments)
        if len(values) != 2 or any(not item.startswith("?") for item in values):
            raise AmbiguityError("conditions must contain two variables")
        conditions.append((predicate, (values[0], values[1])))

    effect = tuple(str(item) for item in raw_effect)
    if len(effect) != 2 or any(not item.startswith("?") for item in effect):
        raise AmbiguityError("template must expose two effect variables")
    if not conditions:
        raise AmbiguityError("template must contain a relational condition")
    identity = {
        "conditions": [[predicate, list(arguments)] for predicate, arguments in conditions],
        "effect_variables": list(effect),
    }
    return tuple(conditions), (effect[0], effect[1]), str(template_hash or _digest(identity))


def _relation_rows(state: Mapping[str, Any]) -> tuple[tuple[str, tuple[str, str]], ...]:
    raw_relations = state.get("relations")
    if not isinstance(raw_relations, Sequence) or isinstance(raw_relations, (str, bytes)):
        raise AmbiguityError("relation_state must contain a relations sequence")
    output: set[tuple[str, tuple[str, str]]] = set()
    for relation in raw_relations:
        if not isinstance(relation, Mapping):
            raise AmbiguityError("invalid relation fact")
        predicate, arguments = relation.get("predicate"), relation.get("arguments")
        if not isinstance(predicate, str) or not isinstance(arguments, Sequence) or isinstance(arguments, str):
            raise AmbiguityError("invalid relation fact")
        values = tuple(str(item) for item in arguments)
        if len(values) != 2:
            raise AmbiguityError("relation facts must be binary")
        output.add((predicate, (values[0], values[1])))
    return tuple(sorted(output))


def _fact_index(
    facts: Sequence[tuple[str, tuple[str, str]]],
    symmetric_predicates: frozenset[str],
) -> dict[str, tuple[tuple[str, str], ...]]:
    index: dict[str, set[tuple[str, str]]] = defaultdict(set)
    for predicate, arguments in facts:
        index[predicate].add(arguments)
        if predicate in symmetric_predicates:
            index[predicate].add((arguments[1], arguments[0]))
    return {predicate: tuple(sorted(values)) for predicate, values in index.items()}


def _ground(
    conditions: Sequence[tuple[str, tuple[str, str]]],
    facts: Mapping[str, Sequence[tuple[str, str]]],
    *,
    enumeration_limit: int,
) -> tuple[list[dict[str, str]], bool]:
    assignments: list[dict[str, str]] = [{}]
    truncated = False
    for predicate, variables in conditions:
        next_assignments: list[dict[str, str]] = []
        seen: set[tuple[tuple[str, str], ...]] = set()
        for assignment in assignments:
            for values in facts.get(predicate, ()):
                candidate = dict(assignment)
                valid = True
                for variable, value in zip(variables, values, strict=True):
                    existing = candidate.get(variable)
                    if existing is not None and existing != value:
                        valid = False
                        break
                    if existing is None and value in candidate.values():
                        valid = False
                        break
                    candidate[variable] = value
                key = tuple(sorted(candidate.items()))
                if valid and key not in seen:
                    seen.add(key)
                    next_assignments.append(candidate)
                    if len(next_assignments) >= enumeration_limit:
                        truncated = True
                        break
            if len(next_assignments) >= enumeration_limit:
                break
        assignments = sorted(next_assignments, key=lambda item: tuple(sorted(item.items())))
        if not assignments:
            break
    return assignments, truncated


def _pair_relations(
    pair: tuple[str, str],
    facts: Sequence[tuple[str, tuple[str, str]]],
) -> frozenset[str]:
    members = frozenset(pair)
    return frozenset(
        predicate
        for predicate, arguments in facts
        if frozenset(arguments) == members and arguments[0] != arguments[1]
    )


def compile_ambiguity_witness(
    template: Any,
    relation_state: Mapping[str, Any],
    *,
    max_candidates: int = 6,
    max_effect_pairs: int = 6,
    max_relations_per_candidate: int = 6,
    enumeration_limit: int = 64,
    symmetric_predicates: frozenset[str] = DEFAULT_SYMMETRIC_PREDICATES,
) -> dict[str, Any]:
    """Compile a bounded witness suitable for structured criticism.

    Candidate ordering is deterministic and representative-first: one
    substitution for each distinct effect pair is retained before alternate
    orientations/third-variable assignments.  A distinguishing relation is a
    visible predicate on an effect pair whose truth signature is not shared by
    every competing pair.
    """

    limits = (max_candidates, max_effect_pairs, max_relations_per_candidate, enumeration_limit)
    if any(not isinstance(value, int) or value < 1 for value in limits):
        raise AmbiguityError("all witness bounds must be positive integers")
    conditions, effect_variables, template_hash = _template_parts(template)
    relation_rows = _relation_rows(relation_state)
    facts = _fact_index(relation_rows, symmetric_predicates)
    assignments, enumeration_truncated = _ground(
        conditions, facts, enumeration_limit=enumeration_limit
    )

    condition_diagnostics = []
    blocking_conditions = []
    for index, (predicate, variables) in enumerate(conditions):
        without = tuple(condition for offset, condition in enumerate(conditions) if offset != index)
        without_assignments, without_truncated = (
            _ground(without, facts, enumeration_limit=enumeration_limit)
            if without
            else ([], False)
        )
        without_pairs = sorted(
            {
                tuple(sorted((assignment[effect_variables[0]], assignment[effect_variables[1]])))
                for assignment in without_assignments
                if all(variable in assignment for variable in effect_variables)
                and assignment[effect_variables[0]] != assignment[effect_variables[1]]
            }
        )
        alone_assignments, alone_truncated = _ground(
            ((predicate, variables),), facts, enumeration_limit=enumeration_limit
        )
        row = {
            "condition_index": index,
            "predicate": predicate,
            "arguments": list(variables),
            "fact_count": len(facts.get(predicate, ())),
            "alone_grounding_count": len(alone_assignments),
            "alone_truncated": alone_truncated,
            "grounding_count_without_condition": len(without_assignments),
            "effect_pairs_without_condition": [list(pair) for pair in without_pairs[:max_effect_pairs]],
            "without_condition_truncated": without_truncated or len(without_pairs) > max_effect_pairs,
        }
        condition_diagnostics.append(row)
        if not assignments and without_assignments:
            blocking_conditions.append(index)

    pair_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for assignment in assignments:
        if not all(variable in assignment for variable in effect_variables):
            continue
        pair = tuple(sorted((assignment[effect_variables[0]], assignment[effect_variables[1]])))
        if pair[0] != pair[1]:
            pair_groups[pair].append(assignment)
    pairs = sorted(pair_groups)

    # Retain breadth across competing pairs before redundant orientations.
    ordered_assignments: list[tuple[tuple[str, str], dict[str, str]]] = []
    depth = 0
    while len(ordered_assignments) < max_candidates:
        added = False
        for pair in pairs:
            group = pair_groups[pair]
            if depth < len(group):
                ordered_assignments.append((pair, group[depth]))
                added = True
                if len(ordered_assignments) >= max_candidates:
                    break
        if not added:
            break
        depth += 1

    pair_predicates = {pair: _pair_relations(pair, relation_rows) for pair in pairs}
    all_predicates = set().union(*pair_predicates.values()) if pair_predicates else set()
    non_discriminating = {
        predicate
        for predicate in all_predicates
        if all(predicate in pair_predicates[pair] for pair in pairs)
    }

    candidate_rows = []
    for pair, assignment in ordered_assignments:
        inverse = {entity: variable for variable, entity in assignment.items()}
        relations = []
        for predicate, grounded_arguments in relation_rows:
            if (
                frozenset(grounded_arguments) != frozenset(pair)
                or predicate in non_discriminating
            ):
                continue
            relations.append(
                {
                    "predicate": predicate,
                    "variable_arguments": [inverse.get(item, "OPEN") for item in grounded_arguments],
                    "entity_arguments": list(grounded_arguments),
                }
            )
        relations.sort(key=_stable_json)
        bindings = [[variable, assignment[variable]] for variable in sorted(assignment)]
        candidate_rows.append(
            {
                "candidate_id": f"gw:{_digest({'bindings': bindings, 'pair': pair})[:12]}",
                "substitution": bindings,
                "effect_pair": list(pair),
                "distinguishing_relations": relations[:max_relations_per_candidate],
                "relations_truncated": len(relations) > max_relations_per_candidate,
            }
        )

    effect_pair_rows = []
    for pair in pairs[:max_effect_pairs]:
        predicates = sorted(pair_predicates[pair] - non_discriminating)
        effect_pair_rows.append(
            {
                "effect_pair": list(pair),
                "distinguishing_predicates": predicates[:max_relations_per_candidate],
                "relations_truncated": len(predicates) > max_relations_per_candidate,
            }
        )

    return {
        "protocol": PROTOCOL,
        "status": "ambiguous-grounding" if len(pairs) > 1 else ("unbound" if not pairs else "bound"),
        "template_hash": template_hash,
        "template_conditions": [
            {"predicate": predicate, "arguments": list(arguments)}
            for predicate, arguments in conditions
        ],
        "effect_variables": list(effect_variables),
        "grounding_count_observed": len(assignments),
        "effect_pair_count_observed": len(pairs),
        "enumeration_truncated": enumeration_truncated,
        "candidate_substitutions": candidate_rows,
        "candidate_substitutions_truncated": len(assignments) > len(candidate_rows),
        "effect_pairs": effect_pair_rows,
        "effect_pairs_truncated": len(pairs) > len(effect_pair_rows),
        "condition_diagnostics": condition_diagnostics,
        "blocking_condition_indices": blocking_conditions,
        "refinement_goal": (
            "if unbound, remove or replace a diagnosed blocking condition using current relation facts; "
            "otherwise add relational conditions that retain exactly one effect pair"
        ),
    }
