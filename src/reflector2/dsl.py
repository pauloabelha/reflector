"""Small cold-path S-expression compiler for native and teacher proposals."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterator
from typing import Any

from .store import GroundAtom, SchemaGraph, SourceArg, SourceAtom, _canonical_source_atoms

_TOKEN = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()]+')
MAX_METADATA_BYTES = 256


def _scalar(token: str) -> SourceArg:
    if token.startswith('"'):
        return json.loads(token)
    try:
        return int(token)
    except ValueError:
        try:
            return float(token)
        except ValueError:
            return token


def _parse_one(tokens: Iterator[str]) -> Any:
    token = next(tokens)
    if token != "(":
        return _scalar(token)
    output = []
    for token in tokens:
        if token == ")":
            return output
        if token == "(":
            output.append(_parse_list(tokens))
        else:
            output.append(_scalar(token))
    raise ValueError("unclosed list")


def _parse_list(tokens: Iterator[str]) -> list[Any]:
    output = []
    for token in tokens:
        if token == ")":
            return output
        if token == "(":
            output.append(_parse_list(tokens))
        else:
            output.append(_scalar(token))
    raise ValueError("unclosed list")


def parse(text: str) -> list[list[Any]]:
    raw = list(_TOKEN.findall(text))
    iterator = iter(raw)
    forms = []
    try:
        while True:
            form = _parse_one(iterator)
            if not isinstance(form, list):
                raise ValueError("top-level value must be a submission form")
            forms.append(form)
    except StopIteration:
        return forms


def _metadata(items: list[Any]) -> tuple[list[Any], dict[str, SourceArg]]:
    body: list[Any] = []
    metadata: dict[str, SourceArg] = {}
    index = 0
    while index < len(items):
        item = items[index]
        if isinstance(item, str) and item.startswith(":"):
            if index + 1 >= len(items) or isinstance(items[index + 1], list):
                raise ValueError(f"metadata {item} requires a scalar value")
            key = item[1:]
            if key not in {"source", "context"}:
                raise ValueError(f"unknown metadata key: {item}")
            metadata[key] = items[index + 1]
            index += 2
        else:
            body.append(item)
            index += 1
    return body, metadata


def _atom(value: Any) -> SourceAtom:
    if not isinstance(value, list) or not value or not isinstance(value[0], str):
        raise ValueError("an application must be a non-empty list with a symbol head")
    if len(value) - 1 > 8:
        raise ValueError("application arity may not exceed 8")
    if any(isinstance(argument, list) for argument in value[1:]):
        raise ValueError("the Phase-1 matcher accepts flat applications only")
    if any(isinstance(argument, float) and not math.isfinite(argument) for argument in value[1:]):
        raise ValueError("numeric terms must be finite")
    return value[0], tuple(value[1:])


def _metadata_text(metadata: dict[str, SourceArg], key: str, default: str) -> str:
    value = metadata.get(key, default)
    if not isinstance(value, str):
        raise ValueError(f":{key} must be a string symbol")
    if len(value.encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError(f":{key} exceeds {MAX_METADATA_BYTES} UTF-8 bytes")
    return value


class Compiler:
    """Compile complete submissions transactionally into the generic graph."""

    def __init__(self, graph: SchemaGraph) -> None:
        self.graph = graph
        self.events: list[dict[str, object]] = []

    def compile(self, text: str) -> list[tuple[str, object]]:
        parsed = parse(text)
        validated: list[tuple[str, object]] = []
        # Validate every form before mutating the graph.
        for form in parsed:
            if not form or not isinstance(form[0], str):
                raise ValueError("submission form requires an operation")
            operation = form[0]
            body, metadata = _metadata(form[1:])
            if operation == "schema":
                if len(body) < 3 or not isinstance(body[0], str) or not isinstance(body[1], list):
                    raise ValueError("schema requires name, variable list, and body")
                variables = body[1]
                if any(not isinstance(item, str) or not item.startswith("?") for item in variables):
                    raise ValueError("schema declaration contains an invalid variable")
                source = _metadata_text(metadata, "source", "native")
                entries = body[2:]
                dag_entries = any(
                    isinstance(item, list) and item and isinstance(item[0], str) and item[0] in {"child", "relation"}
                    for item in entries
                )
                if not dag_entries:
                    atoms = tuple(_atom(item) for item in entries)
                    used = {arg for _head, args in atoms for arg in args if isinstance(arg, str) and arg.startswith("?")}
                    if set(variables) != used:
                        raise ValueError("declared and used variables must be equal")
                    # Exercise every structural validation before any form commits.
                    _canonical_source_atoms(atoms)
                    validated.append(("schema", (body[0], atoms, source)))
                    continue

                children = []
                constraints = []
                used: set[str] = set()
                for entry in entries:
                    if not isinstance(entry, list) or not entry or not isinstance(entry[0], str):
                        raise ValueError("schema DAG entries must be child or relation forms")
                    if entry[0] == "child":
                        if len(entry) < 2 or not isinstance(entry[1], str) or any(
                            not isinstance(value, str) or not value.startswith("?") for value in entry[2:]
                        ):
                            raise ValueError("child requires a schema reference followed by interface variables")
                        child_id = self.graph.schema_reference(entry[1])
                        child_variables = sorted(
                            {
                                value
                                for _head, args in self.graph.patterns[child_id]
                                for tag, value in args
                                if tag == "v"
                            }
                        )
                        if len(entry[2:]) != len(child_variables):
                            raise ValueError("child interface arity does not match referenced schema")
                        mapping = dict(zip(child_variables, entry[2:], strict=True))
                        children.append((child_id, mapping))
                        used.update(mapping.values())
                    elif entry[0] == "relation":
                        if len(entry) != 2:
                            raise ValueError("relation requires exactly one application")
                        atom = _atom(entry[1])
                        constraints.append(atom)
                        used.update(
                            arg for arg in atom[1] if isinstance(arg, str) and arg.startswith("?")
                        )
                    else:
                        raise ValueError("schema DAG bodies may contain only child and relation entries")
                if set(variables) != used:
                    raise ValueError("declared and used variables must be equal")
                validated.append(("schema-dag", (body[0], tuple(variables), tuple(children), tuple(constraints), source)))
            elif operation == "fact":
                if len(body) != 1:
                    raise ValueError("fact requires exactly one application")
                atom = _atom(body[0])
                if any(isinstance(arg, str) and arg.startswith("?") for arg in atom[1]):
                    raise ValueError("facts must be ground")
                source = _metadata_text(metadata, "source", "native")
                context = _metadata_text(metadata, "context", "ingestion")
                validated.append(("fact", (atom, source, context)))
            elif operation == "evidence":
                if len(body) != 3 or not isinstance(body[0], str) or not isinstance(body[1], str) or not isinstance(body[2], int):
                    raise ValueError("evidence requires target, kind, and integer amount")
                if body[1] not in {"support", "contradiction", "prediction-success", "prediction-failure"}:
                    raise ValueError("unknown evidence kind")
                source = _metadata_text(metadata, "source", "native")
                if source.startswith("teacher:"):
                    raise ValueError("teachers may propose hypotheses but may not install evidence")
                context = _metadata_text(metadata, "context", "ingestion")
                schema_id = self.graph.schema_reference(body[0])
                validated.append(("evidence", (schema_id, body[1], body[2], source, context)))
            else:
                raise ValueError(f"unsupported Phase-1 submission: {operation}")

        output: list[tuple[str, object]] = []
        for operation, payload in validated:
            if operation == "schema":
                name, atoms, source = payload  # type: ignore[misc]
                schema_id, created = self.graph.add_schema(name, atoms, provenance=source)
                output.append(("schema", (schema_id, created)))
                self.events.append({"event": "schema", "schema": self.graph.canonical_hash[schema_id], "source": source})
            elif operation == "schema-dag":
                name, interface, children, constraints, source = payload  # type: ignore[misc]
                schema_id, created = self.graph.add_dag_schema(
                    name, interface, children, constraints, provenance=source
                )
                output.append(("schema", (schema_id, created)))
                self.events.append({"event": "schema", "schema": self.graph.canonical_hash[schema_id], "source": source})
            elif operation == "fact":
                atom, source, context = payload  # type: ignore[misc]
                head, args = atom
                fact: GroundAtom = self.graph.terms.ground_atom(head, args)
                output.append(("fact", fact))
                self.events.append({"event": "fact", "fact": fact, "source": source, "context": context})
            else:
                schema_id, kind, amount, source, context = payload  # type: ignore[misc]
                self.graph.add_evidence(schema_id, kind, amount, context, 0, source=source)
                output.append(("evidence", schema_id))
        return output
