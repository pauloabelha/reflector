"""Generic Qwen explanation proposals compiled into real R2 control."""

from __future__ import annotations

import argparse
import fcntl
import importlib.util
import itertools
import json
import os
import sys
import tempfile
import time
import urllib.request
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / "prior-accelerated-relational-transfer-v0" / "experiment.py"
SPEC = importlib.util.spec_from_file_location("prior_relational_base", PREVIOUS)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"cannot load experiment base: {PREVIOUS}")
BASE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BASE
SPEC.loader.exec_module(BASE)

CORPUS = BASE.DEFAULT_CORPUS
ENVIRONMENTS = BASE.DEFAULT_ENVIRONMENTS
MAX_ENTITIES = 8
MAX_GROUNDINGS = 64
MAX_LATENT_STEPS = 4
SYMMETRIC_PREDICATES = frozenset(
    {
        "SameOutline",
        "DifferentOutline",
        "SameInteriorLayout",
        "DifferentInteriorLayout",
        "SameArea",
        "DifferentArea",
        "Touches",
        "Disjoint",
        "AlignedHorizontal",
        "AlignedVertical",
    }
)
ALLOWED_PREDICATES = frozenset(
    {
        *SYMMETRIC_PREDICATES,
        "AlignedHorizontal",
        "AlignedVertical",
    }
)
ALLOWED_VARIABLES = frozenset({"?a", "?b", "?c", "?d"})
ALLOWED_OPERATORS = frozenset({"Decrease", "Increase"})
MEASURE = "TranslationAlignmentResidual"


OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["schema_version", "hypotheses"],
    "properties": {
        "schema_version": {"const": "r2-relational-prior-v0"},
        "hypotheses": {
            "type": "array",
            "minItems": 0,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["conditions", "preferred_consequence"],
                "properties": {
                    "conditions": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": 6,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["predicate", "arguments"],
                            "properties": {
                                "predicate": {"enum": sorted(ALLOWED_PREDICATES)},
                                "arguments": {
                                    "type": "array",
                                    "minItems": 2,
                                    "maxItems": 2,
                                    "items": {"enum": sorted(ALLOWED_VARIABLES)},
                                },
                            },
                        },
                    },
                    "preferred_consequence": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["operator", "measure", "arguments"],
                        "properties": {
                            "operator": {"enum": sorted(ALLOWED_OPERATORS)},
                            "measure": {"const": MEASURE},
                            "arguments": {
                                "type": "array",
                                "minItems": 2,
                                "maxItems": 2,
                                "items": {"enum": sorted(ALLOWED_VARIABLES)},
                            },
                        },
                    },
                },
            },
        },
    },
}


def append_status(message: str) -> None:
    with (HERE / "STATUS.md").open("a", encoding="utf-8") as stream:
        stream.write(message.rstrip() + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def atomic_json(path: Path, value: object) -> None:
    """Durable same-directory replace, including the parent directory entry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def relation_facts(figures: Sequence[Any]) -> list[tuple[str, str, str]]:
    facts: list[tuple[str, str, str]] = []
    for left_index, left in enumerate(figures):
        for right_index, right in enumerate(figures[left_index + 1 :], start=left_index + 1):
            left_id = f"f{left_index:02d}"
            right_id = f"f{right_index:02d}"
            pairs = [
                ("SameOutline" if left.outline == right.outline else "DifferentOutline", left_id, right_id),
                (
                    "SameInteriorLayout"
                    if left.interior_pattern == right.interior_pattern
                    else "DifferentInteriorLayout",
                    left_id,
                    right_id,
                ),
                ("SameArea" if left.area == right.area else "DifferentArea", left_id, right_id),
            ]
            if left.centroid2[1] == right.centroid2[1]:
                pairs.append(("AlignedHorizontal", left_id, right_id))
            if left.centroid2[0] == right.centroid2[0]:
                pairs.append(("AlignedVertical", left_id, right_id))
            left_cells = {(x + left.anchor[0], y + left.anchor[1]) for x, y in left.normalized_cells}
            right_cells = {(x + right.anchor[0], y + right.anchor[1]) for x, y in right.normalized_cells}
            distance = min(abs(x1 - x2) + abs(y1 - y2) for x1, y1 in left_cells for x2, y2 in right_cells)
            pairs.append(("Touches" if distance == 1 else "Disjoint", left_id, right_id))
            facts.extend(pairs)
    return sorted(set(facts))


def select_figures(grid: Any) -> tuple[Any, ...]:
    figures = list(BASE.extract_figures(grid))
    group_sizes = Counter(item.outline for item in figures)
    ranked = sorted(
        figures,
        key=lambda item: (
            -group_sizes[item.outline],
            -item.area if group_sizes[item.outline] == 1 else 0,
            item.outline,
            item.anchor,
            item.local_key,
        ),
    )
    return tuple(ranked[:MAX_ENTITIES])


def structured_state(grid: Any, legal_action_count: int) -> tuple[dict[str, Any], tuple[Any, ...]]:
    figures = select_figures(grid)
    outlines = {value: f"outline_class_{index:02d}" for index, value in enumerate(sorted({item.outline for item in figures}))}
    layouts = {
        value: f"interior_class_{index:02d}"
        for index, value in enumerate(sorted({item.interior_pattern for item in figures}, key=repr))
    }
    state = {
        "frame": {"height": len(grid), "width": len(grid[0])},
        "opaque_legal_action_count": int(legal_action_count),
        "entities": [
            {
                "id": f"f{index:02d}",
                "kind": "Figure",
                "outline_class": outlines[item.outline],
                "interior_layout_class": layouts[item.interior_pattern],
                "area": item.area,
                "centroid2": list(item.centroid2),
                "bounding_box_origin": list(item.anchor),
            }
            for index, item in enumerate(figures)
        ],
        "relations": [
            {"predicate": predicate, "arguments": [left, right]}
            for predicate, left, right in relation_facts(figures)
        ],
        "truncation": {
            "maximum_entities": MAX_ENTITIES,
            "entities_retained": len(figures),
            "selection": "largest repeated-outline groups first; then largest unique figures",
        },
    }
    return state, figures


def recording_for(game: str) -> Path:
    matches = sorted(CORPUS.glob(f"{game}.*.recording.jsonl"))
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one recording for {game}, found {len(matches)}")
    return matches[0]


def initial_state(game: str) -> tuple[dict[str, Any], tuple[Any, ...], Any]:
    recording = recording_for(game)
    packet = BASE.first_packet(recording)
    grid = BASE.load_first_grid(recording)
    state, figures = structured_state(grid, len(set(packet["available_actions"])))
    return state, figures, grid


def qwen_payload(state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    prompt = (HERE / "PROMPT.txt").read_text(encoding="utf-8") + BASE.stable_json(state)
    qwen = config["qwen"]
    return {
        "model": qwen["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": qwen["temperature"],
        "top_p": qwen["top_p"],
        "seed": qwen["seed"],
        "max_tokens": qwen["max_tokens"],
        "thinking_budget_tokens": qwen["thinking_budget"],
        "stream": False,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "r2_relational_prior_v0",
                "strict": True,
                "schema": OUTPUT_SCHEMA,
            },
        },
    }


def call_qwen(game: str, state: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    payload = qwen_payload(state, config)
    request_path = HERE / "artifacts" / "qwen" / game / "request.json"
    response_path = HERE / "artifacts" / "qwen" / game / "response.json"
    atomic_json(request_path, payload)
    request = urllib.request.Request(
        config["qwen"]["endpoint"],
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    transport_error = None
    body: dict[str, Any] | None = None
    content: str | None = None
    parsed: Any = None
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            body = json.loads(response.read())
        content = body["choices"][0]["message"]["content"]
        parsed = json.loads(content)
    except Exception as error:
        transport_error = f"{type(error).__name__}: {error}"
    result = {
        "game": game,
        "instruction_sha256": BASE.file_hash(HERE / "PROMPT.txt"),
        "structured_state_sha256": BASE.stable_hash(state),
        "latency_s": time.perf_counter() - started,
        "transport_error": transport_error,
        "model_content": content,
        "parsed": parsed,
        "raw_body": body,
    }
    atomic_json(response_path, result)
    return result


@dataclass(frozen=True, slots=True)
class Template:
    conditions: tuple[tuple[str, tuple[str, str]], ...]
    operator: str
    effect_variables: tuple[str, str]
    canonical_hash: str
    provenance: str = "externally-proposed"


def template_identity(
    conditions: Sequence[tuple[str, tuple[str, str]]],
    operator: str,
    effect_variables: tuple[str, str],
) -> dict[str, Any]:
    variables: dict[str, str] = {}
    for _predicate, arguments in conditions:
        for argument in arguments:
            variables.setdefault(argument, f"?v{len(variables)}")
    for argument in effect_variables:
        variables.setdefault(argument, f"?v{len(variables)}")
    normalized_conditions = sorted(
        (predicate, tuple(variables[item] for item in arguments))
        for predicate, arguments in conditions
    )
    normalized_effect = tuple(variables[item] for item in effect_variables)
    if normalized_effect[1] < normalized_effect[0]:
        normalized_effect = (normalized_effect[1], normalized_effect[0])
    return {
        "conditions": [[predicate, list(arguments)] for predicate, arguments in normalized_conditions],
        "consequence": [operator, [MEASURE, *normalized_effect]],
    }


def connected_variables(conditions: Sequence[tuple[str, tuple[str, str]]]) -> bool:
    variables = {item for _predicate, arguments in conditions for item in arguments}
    if not variables:
        return False
    reached = {min(variables)}
    changed = True
    while changed:
        changed = False
        for _predicate, (left, right) in conditions:
            if left in reached or right in reached:
                before = len(reached)
                reached.update((left, right))
                changed = changed or len(reached) != before
    return reached == variables


def compile_response(response: dict[str, Any]) -> dict[str, Any]:
    parsed = response.get("parsed")
    accepted: list[Template] = []
    rejected: list[dict[str, Any]] = []
    if not isinstance(parsed, dict) or set(parsed) != {"schema_version", "hypotheses"}:
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "top-level-contract"}]}
    if parsed.get("schema_version") != "r2-relational-prior-v0" or not isinstance(parsed.get("hypotheses"), list):
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "schema-version-or-array"}]}
    if len(parsed["hypotheses"]) > 4:
        return {"valid_json_contract": False, "accepted": [], "rejected": [{"reason": "hypothesis-cap"}]}
    seen: set[str] = set()
    for index, raw in enumerate(parsed["hypotheses"]):
        reason = None
        try:
            if not isinstance(raw, dict) or set(raw) != {"conditions", "preferred_consequence"}:
                raise ValueError("hypothesis-contract")
            raw_conditions = raw["conditions"]
            consequence = raw["preferred_consequence"]
            if not isinstance(raw_conditions, list) or not 1 <= len(raw_conditions) <= 6:
                raise ValueError("condition-cap")
            conditions: list[tuple[str, tuple[str, str]]] = []
            for condition in raw_conditions:
                if not isinstance(condition, dict) or set(condition) != {"predicate", "arguments"}:
                    raise ValueError("condition-contract")
                predicate = condition["predicate"]
                arguments = condition["arguments"]
                if predicate not in ALLOWED_PREDICATES:
                    raise ValueError("unknown-predicate")
                if not isinstance(arguments, list) or len(arguments) != 2 or any(item not in ALLOWED_VARIABLES for item in arguments):
                    raise ValueError("condition-arguments")
                if arguments[0] == arguments[1]:
                    raise ValueError("self-relation")
                conditions.append((predicate, (arguments[0], arguments[1])))
            if not isinstance(consequence, dict) or set(consequence) != {"operator", "measure", "arguments"}:
                raise ValueError("consequence-contract")
            operator = consequence["operator"]
            arguments = consequence["arguments"]
            if operator not in ALLOWED_OPERATORS or consequence["measure"] != MEASURE:
                raise ValueError("unsupported-consequence")
            if not isinstance(arguments, list) or len(arguments) != 2 or arguments[0] == arguments[1]:
                raise ValueError("effect-arguments")
            effect_variables = (arguments[0], arguments[1])
            condition_variables = {item for _predicate, pair in conditions for item in pair}
            if any(item not in condition_variables for item in effect_variables):
                raise ValueError("ungrounded-effect-variable")
            if not connected_variables(conditions):
                raise ValueError("disconnected-condition-graph")
            identity = template_identity(conditions, operator, effect_variables)
            digest = BASE.stable_hash(identity)
            if digest in seen:
                raise ValueError("duplicate-template")
            seen.add(digest)
            accepted.append(Template(tuple(sorted(set(conditions))), operator, effect_variables, digest))
        except (KeyError, TypeError, ValueError) as error:
            reason = str(error)
        if reason is not None:
            rejected.append({"index": index, "reason": reason, "raw": raw})
    return {
        "valid_json_contract": True,
        "accepted": [asdict(item) for item in accepted],
        "rejected": rejected,
    }


def templates_from_compilation(compilation: dict[str, Any]) -> tuple[Template, ...]:
    output = []
    for item in compilation.get("accepted", []):
        output.append(
            Template(
                conditions=tuple((value[0], tuple(value[1])) for value in item["conditions"]),
                operator=item["operator"],
                effect_variables=tuple(item["effect_variables"]),
                canonical_hash=item["canonical_hash"],
                provenance=item.get("provenance", "externally-proposed"),
            )
        )
    return tuple(output)


def state_fact_index(state: dict[str, Any]) -> dict[str, tuple[tuple[str, str], ...]]:
    index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for relation in state["relations"]:
        predicate = relation["predicate"]
        arguments = tuple(relation["arguments"])
        index[predicate].append(arguments)
        if predicate in SYMMETRIC_PREDICATES:
            index[predicate].append(tuple(reversed(arguments)))
    return {key: tuple(sorted(set(values))) for key, values in index.items()}


def ground_template(template: Template, state: dict[str, Any]) -> dict[str, Any]:
    facts = state_fact_index(state)
    assignments: list[dict[str, str]] = [{}]
    for predicate, arguments in template.conditions:
        next_assignments: list[dict[str, str]] = []
        for assignment in assignments:
            for values in facts.get(predicate, ()):
                candidate = dict(assignment)
                valid = True
                for variable, value in zip(arguments, values, strict=True):
                    existing = candidate.get(variable)
                    if existing is not None and existing != value:
                        valid = False
                        break
                    if existing is None and value in candidate.values():
                        valid = False
                        break
                    candidate[variable] = value
                if valid and candidate not in next_assignments:
                    next_assignments.append(candidate)
                    if len(next_assignments) >= MAX_GROUNDINGS:
                        break
            if len(next_assignments) >= MAX_GROUNDINGS:
                break
        assignments = next_assignments
        if not assignments:
            break
    pairs = {
        tuple(sorted((item[template.effect_variables[0]], item[template.effect_variables[1]])))
        for item in assignments
        if all(variable in item for variable in template.effect_variables)
    }
    if not pairs:
        status = "unbound"
        pair = None
    elif len(pairs) > 1:
        status = "ambiguous"
        pair = None
    else:
        status = "bound"
        pair = list(next(iter(pairs)))
    return {
        "template_hash": template.canonical_hash,
        "operator": template.operator,
        "status": status,
        "effect_pair": pair,
        "grounding_count": len(assignments),
        "effect_pair_count": len(pairs),
        "truncated": len(assignments) >= MAX_GROUNDINGS,
    }


@dataclass(slots=True)
class PairBinding:
    template_hash: str
    operator: str
    left_key: tuple[Any, ...]
    right_key: tuple[Any, ...]
    left_anchor: tuple[int, int]
    right_anchor: tuple[int, int]
    relative2: tuple[int, int]
    action_deltas: dict[int, list[tuple[int, int]]]
    confirmations: int = 0
    latent_steps: int = 0

    @property
    def residual(self) -> int:
        return abs(self.relative2[0]) + abs(self.relative2[1])


@dataclass(frozen=True, slots=True)
class Decision:
    action_id: int
    fallback_action_id: int
    reason: str
    template_hash: str | None
    residual_before: int | None
    predicted_residual_after: int | None
    prior_used: bool


def locate_figure(figures: Sequence[Any], key: tuple[Any, ...], anchor: tuple[int, int]) -> Any | None:
    exact = [item for item in figures if item.local_key == key and item.anchor == anchor]
    if exact:
        return exact[0]
    compatible = [item for item in figures if item.local_key == key]
    if not compatible:
        return None
    return min(
        compatible,
        key=lambda item: (abs(item.anchor[0] - anchor[0]) + abs(item.anchor[1] - anchor[1]), item.anchor),
    )


class PairPotentialController:
    def __init__(self, bindings: Sequence[PairBinding], provenance: str) -> None:
        self.bindings = list(bindings)
        self.provenance = provenance
        self.uses: Counter[int] = Counter()
        self.prior_decisions = 0
        self.overrides = 0
        self.abstentions = 0
        self.local_confirmations = 0
        self.latent_projections = 0

    @staticmethod
    def modal_delta(binding: PairBinding, action: int) -> tuple[tuple[int, int], int] | None:
        values = binding.action_deltas.get(action, [])
        if not values:
            return None
        counts = Counter(values)
        delta, support = min(counts.items(), key=lambda item: (-item[1], item[0]))
        return delta, support

    def choose(self, legal_actions: Sequence[int]) -> Decision:
        legal = tuple(sorted(set(int(item) for item in legal_actions)))
        if not legal:
            raise RuntimeError("no legal simple actions")
        fallback = min(legal, key=lambda item: (self.uses[item], item))
        candidates: list[tuple[float, int, int, str, int, int]] = []
        for binding_index, binding in enumerate(self.bindings):
            current = binding.residual
            if binding.latent_steps >= MAX_LATENT_STEPS:
                continue
            for action in legal:
                model = self.modal_delta(binding, action)
                if model is None:
                    continue
                delta, support = model
                predicted_vector = (
                    binding.relative2[0] + delta[0],
                    binding.relative2[1] + delta[1],
                )
                predicted = abs(predicted_vector[0]) + abs(predicted_vector[1])
                improvement = current - predicted if binding.operator == "Decrease" else predicted - current
                if improvement <= 0:
                    continue
                candidates.append(
                    (
                        -(improvement / max(1, current)),
                        -support,
                        self.uses[action],
                        binding.template_hash,
                        binding_index,
                        action,
                    )
                )
        if not candidates:
            self.abstentions += 1
            return Decision(fallback, fallback, "no-locally-confirmed-improvement", None, None, None, False)
        _ratio, _support, _uses, digest, binding_index, action = min(candidates)
        binding = self.bindings[binding_index]
        delta, _ = self.modal_delta(binding, action) or ((0, 0), 0)
        predicted = abs(binding.relative2[0] + delta[0]) + abs(binding.relative2[1] + delta[1])
        self.prior_decisions += 1
        if action != fallback:
            self.overrides += 1
        return Decision(action, fallback, "locally-confirmed-pair-potential", digest, binding.residual, predicted, True)

    def observe(self, action: int, before_grid: Any, after_grid: Any) -> dict[str, Any]:
        self.uses[action] += 1
        before_figures = BASE.extract_figures(before_grid)
        after_figures = BASE.extract_figures(after_grid)
        correspondence = BASE.correspond(before_figures, after_figures)
        events: list[dict[str, Any]] = []
        for binding in self.bindings:
            before_left = locate_figure(before_figures, binding.left_key, binding.left_anchor)
            before_right = locate_figure(before_figures, binding.right_key, binding.right_anchor)
            after_left = correspondence.get(before_left) if before_left is not None else None
            after_right = correspondence.get(before_right) if before_right is not None else None
            direct = after_left is not None and after_right is not None
            if direct:
                old_relative = (
                    before_left.centroid2[0] - before_right.centroid2[0],
                    before_left.centroid2[1] - before_right.centroid2[1],
                )
                new_relative = (
                    after_left.centroid2[0] - after_right.centroid2[0],
                    after_left.centroid2[1] - after_right.centroid2[1],
                )
                delta = (new_relative[0] - old_relative[0], new_relative[1] - old_relative[1])
                binding.relative2 = new_relative
                binding.left_key = after_left.local_key
                binding.right_key = after_right.local_key
                binding.left_anchor = after_left.anchor
                binding.right_anchor = after_right.anchor
                binding.latent_steps = 0
                if delta != (0, 0):
                    binding.action_deltas.setdefault(action, []).append(delta)
                    binding.confirmations += 1
                    self.local_confirmations += 1
                events.append({"template_hash": binding.template_hash, "direct": True, "delta": list(delta), "residual": binding.residual})
                continue
            model = self.modal_delta(binding, action)
            if model is not None and binding.latent_steps < MAX_LATENT_STEPS:
                delta, support = model
                binding.relative2 = (
                    binding.relative2[0] + delta[0],
                    binding.relative2[1] + delta[1],
                )
                binding.latent_steps += 1
                self.latent_projections += 1
                events.append({"template_hash": binding.template_hash, "direct": False, "delta": list(delta), "support": support, "residual": binding.residual})
            else:
                events.append({"template_hash": binding.template_hash, "direct": False, "suspended": True})
        return {"bindings": events}

    def report(self) -> dict[str, Any]:
        states = [] if not self.bindings else [self.provenance]
        if self.local_confirmations and self.provenance == "externally-proposed":
            states.append("externally-proposed-and-locally-confirmed")
        return {
            "provenance": self.provenance,
            "provenance_states": states,
            "bound_pairs": len(self.bindings),
            "prior_decisions": self.prior_decisions,
            "overrides": self.overrides,
            "abstentions": self.abstentions,
            "local_confirmations": self.local_confirmations,
            "latent_projections": self.latent_projections,
            "action_uses": {str(key): value for key, value in sorted(self.uses.items())},
            "bindings": [
                {
                    "template_hash": item.template_hash,
                    "operator": item.operator,
                    "residual": item.residual,
                    "confirmations": item.confirmations,
                    "latent_steps": item.latent_steps,
                    "action_deltas": {
                        str(action): [list(delta) for delta in values]
                        for action, values in sorted(item.action_deltas.items())
                    },
                }
                for item in self.bindings
            ],
        }


def bindings_from_groundings(
    groundings: Sequence[dict[str, Any]], state: dict[str, Any], figures: Sequence[Any]
) -> tuple[PairBinding, ...]:
    by_id = {f"f{index:02d}": figure for index, figure in enumerate(figures)}
    output: list[PairBinding] = []
    seen: set[tuple[str, str, str]] = set()
    for item in groundings:
        if item["status"] != "bound":
            continue
        left_id, right_id = item["effect_pair"]
        key = (item["template_hash"], left_id, right_id)
        if key in seen:
            continue
        seen.add(key)
        left = by_id[left_id]
        right = by_id[right_id]
        output.append(
            PairBinding(
                template_hash=item["template_hash"],
                operator=item["operator"],
                left_key=left.local_key,
                right_key=right.local_key,
                left_anchor=left.anchor,
                right_anchor=right.anchor,
                relative2=(
                    left.centroid2[0] - right.centroid2[0],
                    left.centroid2[1] - right.centroid2[1],
                ),
                action_deltas={},
            )
        )
    return tuple(output)


def reference_template(provenance: str) -> Template:
    conditions = (
        ("DifferentInteriorLayout", ("?a", "?c")),
        ("SameInteriorLayout", ("?a", "?b")),
        ("SameOutline", ("?a", "?b")),
        ("SameOutline", ("?a", "?c")),
    )
    identity = template_identity(conditions, "Decrease", ("?a", "?b"))
    return Template(
        conditions=conditions,
        operator="Decrease",
        effect_variables=("?a", "?b"),
        canonical_hash=BASE.stable_hash(identity),
        provenance=provenance,
    )


def load_config() -> dict[str, Any]:
    return json.loads((HERE / "config.json").read_text(encoding="utf-8"))


def load_selection() -> dict[str, Any]:
    return json.loads((HERE / "selected_games.json").read_text(encoding="utf-8"))


def proposal_source(game: str, arm: str, cohort: Sequence[str]) -> str | None:
    if arm == "qwen_own":
        return game
    if arm == "qwen_mismatch":
        index = list(cohort).index(game)
        return cohort[(index - 1) % len(cohort)]
    return None


def templates_for_arm(game: str, arm: str, cohort: Sequence[str]) -> tuple[tuple[Template, ...], str, str | None]:
    source = proposal_source(game, arm, cohort)
    if source is not None:
        compilation = json.loads(
            (HERE / "artifacts" / "compilations" / f"{source}.json").read_text(encoding="utf-8")
        )
        return templates_from_compilation(compilation), "externally-proposed", source
    if arm == "human_reference":
        return (reference_template("externally-proposed"),), "externally-proposed", "human-reference"
    if arm == "self_built_reference":
        return (reference_template("transferred-self-built"),), "transferred-self-built", "self-built-reference"
    if arm == "scratch":
        return (), "scratch", None
    raise ValueError(f"unknown arm {arm}")


def build_controller(
    game: str,
    arm: str,
    cohort: Sequence[str],
    initial_grid: Any,
    initial_legal_count: int,
    history: Sequence[dict[str, Any]],
) -> tuple[PairPotentialController, dict[str, Any]]:
    templates, provenance, source = templates_for_arm(game, arm, cohort)
    state, figures = structured_state(initial_grid, initial_legal_count)
    groundings = [ground_template(template, state) for template in templates]
    controller = PairPotentialController(bindings_from_groundings(groundings, state, figures), provenance)
    for item in history:
        before = tuple(tuple(int(cell) for cell in row) for row in item["before_grid"])
        after = tuple(tuple(int(cell) for cell in row) for row in item["after_grid"])
        controller.observe(int(item["action_id"]), before, after)
    audit = {
        "proposal_source": source,
        "provenance": provenance,
        "template_count": len(templates),
        "templates": [asdict(item) for item in templates],
        "groundings": groundings,
        "live_initial_state_sha256": BASE.stable_hash(state),
    }
    return controller, audit


def execute_action(environment: Any, game: str, action_id: int, data: dict[str, int], reason: str) -> Any:
    from arcengine import GameAction

    action = GameAction.from_id(action_id)
    if data:
        action.set_data(data)
    result = environment.step(
        action,
        data={**data, "game_id": game},
        reasoning={"experiment": "qwen-generic-explanation-priors-v0", "reason": reason},
    )
    observation = result if result is not None else environment.observation_space
    if observation is None:
        raise RuntimeError("ARC returned no successor observation")
    return observation


def replay_environment(
    environments: Path,
    recordings: Path,
    game: str,
    history: Sequence[dict[str, Any]],
) -> tuple[Any, Any, Any, Any, tuple[int, ...]]:
    arcade, environment = BASE.open_environment(environments, recordings, game)
    observation = environment.observation_space
    if observation is None:
        observation = environment.reset()
    if observation is None:
        arcade.close_scorecard()
        raise RuntimeError("ARC produced no initial observation")
    initial_grid = BASE.observation_grid(observation)
    initial_legal = BASE.simple_legal_actions(environment, observation)
    for item in history:
        if BASE.observation_record(observation)["digest"] != item["before"]["digest"]:
            arcade.close_scorecard()
            raise RuntimeError(f"checkpoint replay predecessor mismatch at action {item['index']}")
        observation = execute_action(
            environment,
            game,
            int(item["action_id"]),
            {str(key): int(value) for key, value in item.get("data", {}).items()},
            "checkpoint-replay",
        )
        if BASE.observation_record(observation)["digest"] != item["after"]["digest"]:
            arcade.close_scorecard()
            raise RuntimeError(f"checkpoint replay successor mismatch at action {item['index']}")
    return arcade, environment, observation, initial_grid, initial_legal


def verify_history(environments: Path, recordings: Path, game: str, history: Sequence[dict[str, Any]]) -> bool:
    arcade, environment = BASE.open_environment(environments, recordings, game)
    try:
        observation = environment.observation_space
        if observation is None:
            observation = environment.reset()
        if observation is None:
            return False
        for item in history:
            if BASE.observation_record(observation)["digest"] != item["before"]["digest"]:
                return False
            observation = execute_action(
                environment,
                game,
                int(item["action_id"]),
                {str(key): int(value) for key, value in item.get("data", {}).items()},
                "final-ledger-verification",
            )
            if BASE.observation_record(observation)["digest"] != item["after"]["digest"]:
                return False
        return True
    finally:
        arcade.close_scorecard()


def job_key(game: str, arm: str, config: dict[str, Any], selected: dict[str, Any]) -> str:
    from importlib.metadata import version

    manifest = HERE / "FROZEN_MANIFEST.json"
    source = proposal_source(game, arm, selected["cohort"])
    compilation_hash = None
    if source is not None:
        compilation_hash = BASE.file_hash(HERE / "artifacts" / "compilations" / f"{source}.json")
    return BASE.stable_hash(
        {
            "protocol": "qwen-generic-explanation-priors-v0.1",
            "game": game,
            "arm": arm,
            "config": config,
            "selection_sha256": BASE.file_hash(HERE / "selected_games.json"),
            "prompt_sha256": BASE.file_hash(HERE / "PROMPT.txt"),
            "manifest_sha256": BASE.file_hash(manifest),
            "proposal_compilation_sha256": compilation_hash,
            "experiment_code_sha256": BASE.file_hash(Path(__file__)),
            "arc_agi_version": version("arc-agi"),
        }
    )


def run_arm(payload: dict[str, Any]) -> dict[str, Any]:
    game = str(payload["game"])
    arm = str(payload["arm"])
    config = payload["config"]
    selected = payload["selected"]
    expected_key = str(payload["job_key"])
    artifacts = Path(payload["artifacts"])
    environments = Path(payload["environments"])
    checkpoint = artifacts / "checkpoints" / game / arm / "latest.json"
    progress = artifacts / "progress" / f"{game}--{arm}.json"
    trace = artifacts / "traces" / f"{game}--{arm}.jsonl"
    result_path = artifacts / "arms" / f"{game}--{arm}.json"

    resumed = False
    if checkpoint.exists():
        state = json.loads(checkpoint.read_text(encoding="utf-8"))
        if state.get("job_key") != expected_key:
            raise RuntimeError(f"incompatible checkpoint for {game}/{arm}")
        resumed = bool(state.get("history")) or state.get("pending") is not None
        if state.get("status") == "completed" and result_path.exists():
            return json.loads(result_path.read_text(encoding="utf-8"))
    else:
        state = {
            "job_key": expected_key,
            "game": game,
            "arm": arm,
            "history": [],
            "pending": None,
            "status": "running",
        }
        atomic_json(checkpoint, state)
        atomic_json(progress, {"game": game, "arm": arm, "status": "initialized", "actions_committed": 0})
        trace.parent.mkdir(parents=True, exist_ok=True)
        trace.write_text("", encoding="utf-8")

    history: list[dict[str, Any]] = list(state.get("history", []))
    run_recordings = artifacts / "recordings" / game / arm / f"resume-{len(history):02d}"
    arcade, environment, observation, initial_grid, initial_legal = replay_environment(
        environments, run_recordings, game, history
    )
    controller, grounding_audit = build_controller(
        game, arm, selected["cohort"], initial_grid, len(initial_legal), history
    )
    started = time.perf_counter()
    stop_reason = "action-budget"
    try:
        while len(history) < int(config["action_budget"]):
            before_record = BASE.observation_record(observation)
            if int(before_record["levels_completed"]) >= 1:
                stop_reason = "first-level-completed"
                break
            before_grid = BASE.observation_grid(observation)
            legal = BASE.simple_legal_actions(environment, observation)
            if not legal:
                stop_reason = "complex-only-epistemic-abstention"
                break
            pending = state.get("pending")
            if pending is not None:
                if pending["before_digest"] != before_record["digest"]:
                    raise RuntimeError("pending checkpoint predecessor mismatch")
                action_id = int(pending["action_id"])
                decision_dict = dict(pending["decision"])
                if action_id not in legal:
                    raise RuntimeError("pending checkpoint action is no longer legal")
            else:
                decision = controller.choose(legal)
                action_id = decision.action_id
                decision_dict = asdict(decision)
                pending = {
                    "index": len(history),
                    "before_digest": before_record["digest"],
                    "action_id": action_id,
                    "data": {},
                    "decision": decision_dict,
                }
                state = {**state, "pending": pending, "status": "running"}
                atomic_json(checkpoint, state)
                atomic_json(
                    progress,
                    {
                        "game": game,
                        "arm": arm,
                        "status": "pending-action",
                        "actions_committed": len(history),
                        "pending": pending,
                    },
                )
            successor = execute_action(environment, game, action_id, {}, str(decision_dict["reason"]))
            after_record = BASE.observation_record(successor)
            after_grid = BASE.observation_grid(successor)
            level_delta = int(after_record["levels_completed"]) - int(before_record["levels_completed"])
            learning = controller.observe(action_id, before_grid, after_grid)
            committed = {
                "index": len(history),
                "before": before_record,
                "action_id": action_id,
                "data": {},
                "decision": decision_dict,
                "after": after_record,
                "level_delta": level_delta,
                "learning": learning,
                "before_grid": [list(row) for row in before_grid],
                "after_grid": [list(row) for row in after_grid],
            }
            history.append(committed)
            state = {**state, "history": history, "pending": None, "status": "running"}
            atomic_json(checkpoint, state)
            atomic_json(
                progress,
                {
                    "game": game,
                    "arm": arm,
                    "status": "running",
                    "actions_committed": len(history),
                    "levels_completed": after_record["levels_completed"],
                    "last_action": action_id,
                    "last_reason": decision_dict["reason"],
                    "controller": controller.report(),
                },
            )
            BASE.append_jsonl(trace, {key: value for key, value in committed.items() if not key.endswith("_grid")})
            observation = successor
            if level_delta > 0:
                stop_reason = "first-level-completed"
                break
    finally:
        arcade.close_scorecard()

    final_record = BASE.observation_record(observation)
    replay_verified = verify_history(
        environments, artifacts / "recordings" / game / arm / "verification", game, history
    )
    result = {
        "game": game,
        "arm": arm,
        "job_key": expected_key,
        "resumed": resumed,
        "actions": len(history),
        "levels_completed": int(final_record["levels_completed"]),
        "first_level_completed": int(final_record["levels_completed"]) >= 1,
        "final_state": final_record["state"],
        "final_digest": final_record["digest"],
        "stop_reason": stop_reason,
        "replay_verified": replay_verified,
        "grounding": grounding_audit,
        "controller": controller.report(),
        "elapsed_this_process_s": time.perf_counter() - started,
    }
    atomic_json(result_path, result)
    state = {**state, "history": history, "pending": None, "status": "completed", "result": result}
    atomic_json(checkpoint, state)
    atomic_json(progress, {**result, "status": "completed"})
    return result


def prepare(_args: argparse.Namespace) -> dict[str, Any]:
    config = load_config()
    selected = load_selection()
    games = selected["cohort"]
    state_hashes: dict[str, str] = {}
    proposal_summary: dict[str, Any] = {}
    for index, game in enumerate(games, start=1):
        state, _figures, _grid = initial_state(game)
        state_path = HERE / "artifacts" / "states" / f"{game}.json"
        atomic_json(state_path, state)
        state_hashes[game] = BASE.file_hash(state_path)
        response_path = HERE / "artifacts" / "qwen" / game / "response.json"
        if response_path.exists():
            response = json.loads(response_path.read_text(encoding="utf-8"))
        else:
            response = call_qwen(game, state, config)
        compilation = compile_response(response)
        compilation_path = HERE / "artifacts" / "compilations" / f"{game}.json"
        atomic_json(compilation_path, compilation)
        accepted = len(compilation.get("accepted", []))
        proposal_summary[game] = {
            "transport_error": response.get("transport_error"),
            "valid_json_contract": compilation["valid_json_contract"],
            "accepted": accepted,
            "rejected": len(compilation.get("rejected", [])),
            "response_sha256": BASE.file_hash(response_path),
            "compilation_sha256": BASE.file_hash(compilation_path),
        }
        append_status(
            f"- Qwen partial {index}/{len(games)}: `{game}` transport_error={response.get('transport_error')!r}, "
            f"valid_contract={compilation['valid_json_contract']}, accepted={accepted}, "
            f"rejected={len(compilation.get('rejected', []))}."
        )
    manifest_files = [
        "PROPOSAL.md",
        "config.json",
        "selected_games.json",
        "PROMPT.txt",
        "experiment.py",
    ]
    manifest = {
        "protocol": "qwen-generic-explanation-priors-v0.1",
        "frozen_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "files": {name: BASE.file_hash(HERE / name) for name in manifest_files},
        "structured_states": state_hashes,
        "proposals": proposal_summary,
        "no_live_target_actions_executed": True,
        "qwen_request_count": len(games),
    }
    atomic_json(HERE / "FROZEN_MANIFEST.json", manifest)
    append_status(
        "\n## Frozen pre-play manifest\n\n"
        "- All six raw requests, raw responses, compiler decisions, and structured inputs are durable.\n"
        "- `FROZEN_MANIFEST.json` was written before any live target action.\n"
        "- The instruction hash is identical across games; only each anonymous structured state differs.\n"
    )
    return manifest


def analyze(results: Sequence[dict[str, Any]]) -> dict[str, Any]:
    selected = load_selection()
    by_game: dict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for result in results:
        by_game[result["game"]][result["arm"]] = result
    improvements: list[dict[str, Any]] = []
    for game in selected["cohort"]:
        scratch = by_game[game]["scratch"]
        own = by_game[game]["qwen_own"]
        completion_gain = bool(own["first_level_completed"] and not scratch["first_level_completed"])
        completion_regression = bool(scratch["first_level_completed"] and not own["first_level_completed"])
        savings_fraction = None
        if own["first_level_completed"] and scratch["first_level_completed"] and int(scratch["actions"]):
            savings_fraction = (int(scratch["actions"]) - int(own["actions"])) / int(scratch["actions"])
        improvements.append(
            {
                "game": game,
                "completion_gain": completion_gain,
                "completion_regression": completion_regression,
                "action_savings_fraction": savings_fraction,
                "qualifying_improvement": completion_gain or (savings_fraction is not None and savings_fraction >= 0.25),
            }
        )
    improved = [item["game"] for item in improvements if item["qualifying_improvement"]]
    negative_control_regression = next(item for item in improvements if item["game"] == "cn04")["completion_regression"]
    acted_without_improvement = any(
        result["arm"] == "qwen_own" and result["controller"]["prior_decisions"] > 0
        for result in results
    ) and not improved
    if len(improved) >= 2 and any(game != "ar25" for game in improved) and not negative_control_regression:
        verdict = "PROMISING"
    elif improved == ["ar25"] and not negative_control_regression:
        verdict = "ANCHOR_ONLY"
    elif any(item["completion_regression"] for item in improvements) or acted_without_improvement:
        verdict = "NEGATIVE"
    else:
        verdict = "INCONCLUSIVE"
    summary = {
        "verdict": verdict,
        "improved_games": improved,
        "negative_control_regression": negative_control_regression,
        "comparisons": improvements,
        "all_replay_verified": all(item["replay_verified"] for item in results),
        "arms": sorted(results, key=lambda item: (item["game"], item["arm"])),
    }
    atomic_json(HERE / "artifacts" / "summary.json", summary)
    return summary


def write_results(summary: dict[str, Any]) -> None:
    rows = []
    for item in summary["arms"]:
        rows.append(
            f"| {item['game']} | {item['arm']} | {item['actions']} | {item['levels_completed']} | "
            f"{item['grounding']['template_count']} | {len(item['controller']['bindings'])} | "
            f"{item['controller']['local_confirmations']} | {item['controller']['prior_decisions']} | "
            f"{item['replay_verified']} |"
        )
    text = "\n".join(
        [
            "# Qwen-to-R2 Generic Explanation Priors v0 — Results",
            "",
            f"Verdict: **{summary['verdict']}**.",
            "",
            "| Game | Arm | Actions | Levels | Templates | Bound pairs | Confirmations | Prior decisions | Replay verified |",
            "|---|---|---:|---:|---:|---:|---:|---:|---|",
            *rows,
            "",
            "## Primary comparisons",
            "",
            "```json",
            json.dumps(summary["comparisons"], indent=2, sort_keys=True),
            "```",
            "",
            f"Improved games: `{summary['improved_games']}`.",
            f"Negative-control regression: `{summary['negative_control_regression']}`.",
            f"All final ledgers replay-verified: `{summary['all_replay_verified']}`.",
            "",
            "Raw proposals, compiler decisions, action traces, and per-action checkpoints are under `artifacts/`.",
            "",
        ]
    )
    (HERE / "RESULTS.md").write_text(text, encoding="utf-8")


def run_parallel(args: argparse.Namespace) -> dict[str, Any]:
    config = load_config()
    selected = load_selection()
    tasks: list[dict[str, Any]] = []
    for game in selected["cohort"]:
        arms = list(config["arms"])
        if game == "ar25":
            arms.extend(("human_reference", "self_built_reference"))
        for arm in arms:
            tasks.append(
                {
                    "game": game,
                    "arm": arm,
                    "config": config,
                    "selected": selected,
                    "job_key": job_key(game, arm, config, selected),
                    "artifacts": str(HERE / "artifacts"),
                    "environments": str(args.environments),
                }
            )
    append_status(
        "\n## Live real-ARC run started\n\n"
        f"- {len(tasks)} isolated arms launched with up to {config['max_parallel_game_workers']} workers.\n"
        "- Every action uses pending→committed atomic checkpoints; each final ledger gets a fresh replay.\n"
    )
    results: list[dict[str, Any]] = []
    with ProcessPoolExecutor(max_workers=int(config["max_parallel_game_workers"])) as executor:
        futures = {executor.submit(run_arm, task): task for task in tasks}
        for future in as_completed(futures):
            task = futures[future]
            try:
                result = future.result()
            except Exception as error:
                append_status(f"- Arm ERROR `{task['game']}/{task['arm']}`: {type(error).__name__}: {error}")
                raise
            results.append(result)
            append_status(
                f"- Arm partial `{task['game']}/{task['arm']}`: actions={result['actions']}, "
                f"levels={result['levels_completed']}, bound={len(result['controller']['bindings'])}, "
                f"confirmations={result['controller']['local_confirmations']}, "
                f"prior_decisions={result['controller']['prior_decisions']}, replay={result['replay_verified']}."
            )
    summary = analyze(results)
    write_results(summary)
    append_status(
        "\n## Live run complete\n\n"
        f"- Verdict: `{summary['verdict']}`.\n"
        f"- Improved games: `{summary['improved_games']}`.\n"
        f"- All final ledgers replay-verified: `{summary['all_replay_verified']}`.\n"
    )
    return summary


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    subparsers = value.add_subparsers(dest="command", required=True)
    subparsers.add_parser("prepare")
    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--environments", type=Path, default=ENVIRONMENTS)
    subparsers.add_parser("analyze")
    return value


def main() -> None:
    args = parser().parse_args()
    if args.command == "prepare":
        lock_path = HERE / "artifacts" / "prepare.lock"
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as lock:
            try:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError("another proposal preparation process is already active") from error
            result = prepare(args)
    elif args.command == "run":
        result = run_parallel(args)
    else:
        arm_results = [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((HERE / "artifacts" / "arms").glob("*.json"))
        ]
        result = analyze(arm_results)
        write_results(result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
