"""Bounded adapter for visually demonstrated symbolic transformations.

The semantic kernel is the already-consumed ``progress-drive-symbolic-v0``
module.  This adapter contributes only generic plumbing:

* discover which opaque one-step intervention edits the active output glyph;
* discover which opaque intervention advances a visible focus marker;
* expose a support-zero mismatch potential; and
* execute it as a closed-loop option whose support changes only after direct
  environment transitions.

Concrete glyph IDs, coordinates, and opaque actions are situated bindings or
calibrated effects.  They never enter the transferable goal AST.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import importlib.util
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

from progress_synthesis import GoalCandidate, SynthesisError, stable_hash


HERE = Path(__file__).resolve().parent
SYMBOLIC_PATH = HERE.parent / "progress-drive-symbolic-v0" / "symbolic_progress.py"
MAX_ACTIONS = 16
MAX_PANELS = 32
MAX_SLOTS = 8
MAX_CYCLES_PER_SLOT = 8


def _load_symbolic():
    name = "autonomous_consumed_symbolic_progress"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(name, SYMBOLIC_PATH)
    if spec is None or spec.loader is None:
        raise SynthesisError("consumed symbolic kernel is unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


SYMBOLIC = _load_symbolic()


@dataclass(frozen=True)
class SymbolicTransformOption:
    candidate: GoalCandidate
    task: Any
    edit_action: int
    advance_action: int
    calibration_evidence_ids: tuple[str, ...]
    max_cycles_per_slot: int = MAX_CYCLES_PER_SLOT


@dataclass(frozen=True)
class SymbolicExecutionState:
    slot_index: int = 0
    cycles_at_slot: int = 0
    empirical_support: int = 0
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class SymbolicCommand:
    opaque_action: int
    role: str
    slot_index: int


def _grid(raw: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    rows = tuple(tuple(int(value) for value in row) for row in raw)
    if not rows or not rows[0] or any(len(row) != len(rows[0]) for row in rows):
        raise SynthesisError("symbolic observation must be rectangular")
    return rows


def _changed(before, after) -> tuple[tuple[int, int], ...]:
    left, right = _grid(before), _grid(after)
    if (len(left), len(left[0])) != (len(right), len(right[0])):
        raise SynthesisError("symbolic calibration changed frame dimensions")
    return tuple(
        (x, y)
        for y in range(len(left))
        for x in range(len(left[0]))
        if left[y][x] != right[y][x]
    )


def _signatures(task, raw) -> tuple[str, ...]:
    return tuple(SYMBOLIC.glyph_signature(raw, origin) for origin in task.output_origins)


def _has_focus_translation(before, after, step: int) -> bool:
    """Recognize an exact same-value marker translation by one slot step."""
    left, right = _grid(before), _grid(after)
    values = sorted({value for row in left for value in row} | {value for row in right for value in row})
    for value in values:
        source = {(x, y) for y, row in enumerate(left) for x, item in enumerate(row) if item == value}
        target = {(x, y) for y, row in enumerate(right) for x, item in enumerate(row) if item == value}
        removed, added = source - target, target - source
        if removed and len(removed) == len(added) and added == {(x + step, y) for x, y in removed}:
            return True
    return False


def _candidate(task) -> GoalCandidate:
    ast = {
        "protocol": "autonomous-symbolic-transformation-v0",
        "type": "GoalPotential",
        "roles": {
            "examples": {"type": "DemonstratedFunctionalRelation"},
            "query": {"type": "ObservedSymbolSequence"},
            "editable": {"type": "EditableSymbolSequence"},
        },
        "potential": {
            "type": "SymbolMismatchCount",
            "direction": "minimize",
            "lower_bound": 0,
        },
        "terminal": {"type": "EqualsLowerBound"},
    }
    binding = {
        "examples": [list(row) for row in task.examples],
        "query": list(task.query),
        "desired": list(task.desired),
        "input_origins": [list(row) for row in task.input_origins],
        "output_origins": [list(row) for row in task.output_origins],
        "slot_step": int(task.slot_step),
    }
    candidate_id = "goal:" + stable_hash(ast)[:24]
    binding_id = "grounding:" + stable_hash({"candidate_id": candidate_id, "binding": binding})[:24]
    return GoalCandidate(candidate_id, binding_id, ast, binding, attention=85, support=0)


def panel_rows(figures: Sequence[Any]) -> tuple[dict[str, object], ...]:
    """Render generic perceived figures as bounded situated panel addresses."""
    output = []
    for figure in figures[:MAX_PANELS]:
        cells = tuple(getattr(figure, "normalized_cells", ()))
        anchor = tuple(getattr(figure, "anchor", ()))
        if not cells or len(anchor) != 2:
            continue
        width = 1 + max(int(x) for x, _y in cells)
        height = 1 + max(int(y) for _x, y in cells)
        output.append({"origin": [int(anchor[0]), int(anchor[1])], "size": [width, height]})
    return tuple(output)


def propose(
    initial: Sequence[Sequence[int]],
    successors: Mapping[int, Sequence[Sequence[int]]],
    *,
    panels: Sequence[Mapping[str, object]],
) -> tuple[SymbolicTransformOption, ...]:
    """Compile unambiguous symbolic options from direct one-step calibration.

    ``panels`` are ordinary situated perceptual rows (``origin`` and ``size``),
    not semantic labels.  Ambiguous edit or focus effects cause abstention.
    """
    before = _grid(initial)
    if not 1 <= len(successors) <= MAX_ACTIONS or not 2 <= len(panels) <= MAX_PANELS:
        return ()
    edit_rows = []
    for raw_action, raw_after in sorted(successors.items(), key=lambda row: int(row[0])):
        action, after = int(raw_action), _grid(raw_after)
        changed = _changed(before, after)
        if not changed:
            continue
        origins = sorted({min(changed, key=lambda point: (point[1], point[0])), (min(x for x, _y in changed), min(y for _x, y in changed))}, key=lambda p: (p[1], p[0]))
        for origin in origins:
            try:
                task = SYMBOLIC.infer_task(before, panels, mutation_origin=origin)
                if not 2 <= len(task.query) <= MAX_SLOTS:
                    continue
                prior, later = _signatures(task, before), _signatures(task, after)
            except (SYMBOLIC.SymbolicProgressError, IndexError):
                continue
            changed_slots = tuple(index for index, pair in enumerate(zip(prior, later)) if pair[0] != pair[1])
            if changed_slots == (0,):
                edit_rows.append((action, task))
    unique_edits = {(action, task.examples, task.query, task.output_origins): (action, task) for action, task in edit_rows}
    if len(unique_edits) != 1:
        return ()
    edit_action, task = next(iter(unique_edits.values()))
    before_signatures = _signatures(task, before)
    advances = []
    for raw_action, raw_after in sorted(successors.items(), key=lambda row: int(row[0])):
        action, after = int(raw_action), _grid(raw_after)
        if action == edit_action:
            continue
        try:
            unchanged = _signatures(task, after) == before_signatures
        except SYMBOLIC.SymbolicProgressError:
            unchanged = False
        if unchanged and _has_focus_translation(before, after, int(task.slot_step)):
            advances.append(action)
    if len(set(advances)) != 1:
        return ()
    advance_action = advances[0]
    candidate = _candidate(task)
    evidence = (
        "transition:" + stable_hash({"effect": "edit-active-symbol", "action": edit_action, "before": before, "after": _grid(successors[edit_action])})[:20],
        "transition:" + stable_hash({"effect": "advance-focus", "action": advance_action, "before": before, "after": _grid(successors[advance_action])})[:20],
    )
    return (SymbolicTransformOption(candidate, task, edit_action, advance_action, evidence),)


def evaluate(option: SymbolicTransformOption, raw: Sequence[Sequence[int]]) -> int:
    observed = _signatures(option.task, _grid(raw))
    return sum(left != right for left, right in zip(observed, option.task.desired))


def decide(option: SymbolicTransformOption, state: SymbolicExecutionState, raw: Sequence[Sequence[int]]) -> SymbolicCommand | None:
    if evaluate(option, raw) == 0:
        return None
    if not 0 <= state.slot_index < len(option.task.desired):
        raise SynthesisError("symbolic execution cursor is out of bounds")
    current = SYMBOLIC.glyph_signature(raw, option.task.output_origins[state.slot_index])
    desired = option.task.desired[state.slot_index]
    if current != desired:
        if state.cycles_at_slot >= option.max_cycles_per_slot:
            raise SynthesisError("bounded symbolic edit cycle was exhausted")
        return SymbolicCommand(option.edit_action, "symbol-edit-probe", state.slot_index)
    if state.slot_index + 1 >= len(option.task.desired):
        return None
    return SymbolicCommand(option.advance_action, "symbol-focus-probe", state.slot_index)


def observe(
    option: SymbolicTransformOption,
    state: SymbolicExecutionState,
    command: SymbolicCommand,
    before: Sequence[Sequence[int]],
    after: Sequence[Sequence[int]],
    *,
    transition_id: str,
) -> SymbolicExecutionState:
    """Accept only the direct effect predicted for the issued opaque action."""
    if not transition_id or command.slot_index != state.slot_index:
        raise SynthesisError("symbolic evidence does not address the live cursor")
    before_value, after_value = evaluate(option, before), evaluate(option, after)
    if command.role == "symbol-edit-probe":
        origin = option.task.output_origins[state.slot_index]
        if SYMBOLIC.glyph_signature(before, origin) == SYMBOLIC.glyph_signature(after, origin):
            raise SynthesisError("edit intervention did not change the addressed glyph")
        next_state = replace(state, cycles_at_slot=state.cycles_at_slot + 1)
    elif command.role == "symbol-focus-probe":
        if _signatures(option.task, before) != _signatures(option.task, after) or not _has_focus_translation(before, after, option.task.slot_step):
            raise SynthesisError("focus intervention lacked its calibrated direct effect")
        next_state = replace(state, slot_index=state.slot_index + 1, cycles_at_slot=0)
    else:
        raise SynthesisError("unknown symbolic command role")
    support_delta = 10 if after_value < before_value else 0
    return replace(
        next_state,
        empirical_support=max(-100, min(100, next_state.empirical_support + support_delta)),
        evidence_ids=next_state.evidence_ids + (transition_id,),
    )


def workspace_document(option: SymbolicTransformOption, state: SymbolicExecutionState, raw) -> dict[str, Any]:
    return {
        "protocol": "autonomous-symbolic-transformation-v0",
        "candidate_id": option.candidate.candidate_id,
        "binding_id": option.candidate.binding_id,
        "ast": option.candidate.ast,
        "current_value": evaluate(option, raw),
        "empirical_support": state.empirical_support,
        "calibration_evidence_ids": list(option.calibration_evidence_ids),
        "execution_evidence_ids": list(state.evidence_ids),
        "authority": "only-direct-environment-evidence-changes-support",
    }


__all__ = [
    "SymbolicCommand", "SymbolicExecutionState", "SymbolicTransformOption",
    "decide", "evaluate", "observe", "panel_rows", "propose", "workspace_document",
]
