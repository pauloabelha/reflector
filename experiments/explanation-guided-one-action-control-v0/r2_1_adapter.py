"""Frame-local observation adapter for the R2.1 recursive schema fitter.

The adapter supplies only weak, inspectable visual facts.  The generic engine
does the binding; this module does not assign game-specific roles or goals.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
from copy import deepcopy
from hashlib import sha256
import importlib.util
from itertools import islice, permutations, product
import json
from pathlib import Path
import re
import sys
import time
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
ENGINE_PATH = HERE.parent / "parallel-generative-schema-fitting-v0" / "schema_engine.py"


def _load_engine() -> Any:
    name = "reflector_r2_1_schema_engine"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, ENGINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load R2.1 schema engine: {ENGINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


E = _load_engine()

CANONICAL_VERB = re.compile(r"^[a-z][a-z0-9_]{0,39}$")
CATEGORICAL_ATOMS_PER_TYPE = 12
CATEGORICAL_NEIGHBORS_PER_ATOM = 2
CATEGORICAL_COMPARISON_BUDGET = 64
CATEGORICAL_TEMPORAL_BUDGET = 64
ROLE_CORRESPONDENCE_BUDGET = 3
ROLE_IDENTITY_MAX_RESIDUAL = 0.2
ROLE_IDENTITY_MIN_MARGIN = 0.15
ROLE_GROUNDING_TOP_K = 4
ROLE_TUPLE_ENUMERATION_BUDGET = 4096


class DefeasibleRoleGrounder:
    """Generic, bounded role grounding from comparative evidence.

    The grounder knows nothing about games, colors, named shapes, or routes.
    A verb contributes typed ports and a measurable potential.  Semantic role
    clues contribute defeasible evidence unless explicitly marked required.
    The full comparison vector is retained so pruning remains auditable.
    """

    PREDICATES = {
        "same_outline": "SameOutline", "different_outline": "DifferentOutline",
        "same_interior": "SameInterior", "different_interior": "DifferentInterior",
        "same_area": "SameArea", "different_area": "DifferentArea",
        "same_value": "SameValue", "different_value": "DifferentValue",
        "aligned_horizontal": "AlignedHorizontal", "aligned_vertical": "AlignedVertical",
        "disjoint": "Disjoint", "touches": "Touches",
    }
    MODALITIES = {"required", "suggested", "anti-clue", "unknown"}

    def __init__(
        self, regions: Sequence[dict[str, Any]], *, measure: Any,
        relation_bindings: dict[tuple[str, tuple[str, ...]], str],
    ) -> None:
        self.regions = tuple(regions)
        self.measure = measure
        self.relation_bindings = relation_bindings
        self.maximum_area = max((int(region["area"]) for region in self.regions), default=1)

    @staticmethod
    def _normalized_mask(points: Sequence[tuple[int, int]], size: int = 8) -> frozenset[tuple[int, int]]:
        if not points:
            return frozenset()
        min_y = min(point[0] for point in points); max_y = max(point[0] for point in points)
        min_x = min(point[1] for point in points); max_x = max(point[1] for point in points)
        height = max(1, max_y - min_y); width = max(1, max_x - min_x)
        return frozenset(
            (
                round((y - min_y) * (size - 1) / height),
                round((x - min_x) * (size - 1) / width),
            )
            for y, x in points
        )

    @classmethod
    def _mask_residual(
        cls, left: Sequence[tuple[int, int]], right: Sequence[tuple[int, int]],
    ) -> float:
        a, b = cls._normalized_mask(left), cls._normalized_mask(right)
        return len(a ^ b) / max(1, len(a | b))

    def _relation_holds(
        self, predicate: str, left: dict[str, Any], right: dict[str, Any],
    ) -> bool:
        canonical = self.PREDICATES.get(predicate)
        if canonical is None:
            return False
        pair = tuple(sorted((str(left["binding_id"]), str(right["binding_id"]))))
        return (canonical, pair) in self.relation_bindings

    def _clues(self, goal: dict[str, Any], roles: tuple[str, ...]) -> list[dict[str, Any]]:
        output = []
        for raw in goal.get("role_constraints", ()):
            if not isinstance(raw, dict):
                continue
            predicate = str(raw.get("predicate", ""))
            arguments = tuple(str(item) for item in raw.get("arguments", ()))
            if predicate not in self.PREDICATES or len(arguments) != 2 or not set(arguments).issubset(roles):
                continue
            modality = str(raw.get("modality", "suggested"))
            if modality not in self.MODALITIES:
                modality = "suggested"
            output.append({"predicate": predicate, "arguments": arguments, "modality": modality})
        return output

    def _features(
        self, actor: dict[str, Any], target: dict[str, Any], observable: str,
    ) -> dict[str, Any]:
        structural = self._mask_residual(actor["shape"], target["shape"])
        outline = self._mask_residual(actor["outline"], target["outline"])
        area = abs(float(actor["area"]) - float(target["area"])) / max(
            1.0, float(actor["area"]), float(target["area"]),
        )
        topology = abs(int(actor.get("hole_count", 0)) - int(target.get("hole_count", 0))) / max(
            1, int(actor.get("hole_count", 0)), int(target.get("hole_count", 0)),
        )
        measurable = self.measure(observable, actor, target)
        return {
            "type_compatibility_residual": 0.0,
            "structural_residual": round(structural, 6),
            "topology_residual": round(topology, 6),
            "area_residual": round(area, 6),
            "interior_residual": round(structural, 6),
            "outline_residual": round(outline, 6),
            "spatial_measurability_residual": 0.0 if measurable is not None else 1.0,
            # More observed support is preferable, independently of its color
            # or geometry.  This prevents tiny fragments from carrying the
            # same evidential weight as a structure supported by many cells.
            "evidence_mass_residual": round(
                1.0 - min(float(actor["area"]), float(target["area"])) / self.maximum_area, 6,
            ),
            "identity_continuity_residual": 0.5,
            "value_relation": "same" if int(actor["value"]) == int(target["value"]) else "different",
            "measured_potential": None if measurable is None else float(measurable),
        }

    @staticmethod
    def _dominates(left: dict[str, Any], right: dict[str, Any], dimensions: tuple[str, ...]) -> bool:
        return all(float(left[key]) <= float(right[key]) for key in dimensions) and any(
            float(left[key]) < float(right[key]) for key in dimensions
        )

    def ground(self, goal: dict[str, Any]) -> list[dict[str, Any]]:
        roles = tuple(dict.fromkeys(str(role) for role in goal.get("roles", ()))) or ("actor", "target")
        potential_roles = tuple(str(role) for role in goal.get("potential_roles", ()))
        if len(potential_roles) != 2 or not set(potential_roles).issubset(roles):
            roles, potential_roles = ("actor", "target"), ("actor", "target")
        clues = self._clues(goal, roles)
        observable = str(goal.get("observable", "unknown"))
        candidates: list[dict[str, Any]] = []
        for assignment_tuple in islice(
            permutations(self.regions, len(roles)), ROLE_TUPLE_ENUMERATION_BUDGET,
        ):
            assignment = dict(zip(roles, assignment_tuple))
            actor, target = assignment[potential_roles[0]], assignment[potential_roles[1]]
            if actor is target:
                continue
            features = self._features(actor, target, observable)
            if features["spatial_measurability_residual"] > 0:
                continue
            clue_evidence = []
            hard_failure = False
            for clue in clues:
                left, right = (assignment[role] for role in clue["arguments"])
                holds = self._relation_holds(clue["predicate"], left, right)
                if clue["modality"] == "required" and not holds:
                    hard_failure = True
                residual = 0.0 if holds else 1.0
                if clue["modality"] == "anti-clue":
                    residual = 1.0 - residual
                if clue["modality"] == "unknown":
                    residual = 0.5
                clue_evidence.append({**clue, "holds": holds, "residual": residual})
            if hard_failure:
                continue
            semantic_residuals = [
                float(item["residual"]) for item in clue_evidence
                if item["modality"] in {"suggested", "anti-clue"}
            ]
            soft_residual = sum(semantic_residuals) / max(1, len(semantic_residuals))
            binding_map = {role: str(region["binding_id"]) for role, region in assignment.items()}
            structural_identity = {
                role: {
                    "value": int(region["value"]), "area": int(region["area"]),
                    "shape": tuple(region["shape"]), "outline": tuple(region["outline"]),
                }
                for role, region in assignment.items()
            }
            candidates.append({
                "candidate_binding_id": E.stable_id("defeasible-role-binding", {
                    "verb": goal.get("verb"), "observable": observable,
                    "assignments": structural_identity,
                }),
                "situated_roles": binding_map,
                "residual_vector": features,
                "semantic_clue_residual": round(soft_residual, 6),
                "clue_evidence": clue_evidence,
                "required_constraints_satisfied": True,
            })
        dimensions = (
            "type_compatibility_residual", "structural_residual", "topology_residual",
            "area_residual", "interior_residual", "outline_residual",
            "spatial_measurability_residual", "evidence_mass_residual",
            "identity_continuity_residual",
        )
        front = [
            candidate for candidate in candidates
            if not any(
                other is not candidate
                and self._dominates(other["residual_vector"], candidate["residual_vector"], dimensions)
                for other in candidates
            )
        ]
        # Rank aggregation is deliberately fixed and generic.  Semantic clues
        # break otherwise-equal comparisons but cannot erase a Pareto-plausible
        # structural candidate.
        front.sort(key=lambda item: (
            sum(float(item["residual_vector"][key]) for key in dimensions),
            float(item["semantic_clue_residual"]), item["candidate_binding_id"],
        ))
        bounded = front[:ROLE_GROUNDING_TOP_K]
        for rank, item in enumerate(bounded, start=1):
            item["pareto_rank"] = 1
            item["bounded_rank"] = rank
            item["candidate_count"] = len(candidates)
            item["pareto_count"] = len(front)
            item["epistemic_status"] = "defeasible-role-hypothesis"
        return bounded


def _components(frame: Sequence[Sequence[int]]) -> list[dict[str, Any]]:
    """Return 4-connected, same-value regions except the modal background."""
    if not frame or not frame[0]:
        return []
    height, width = len(frame), len(frame[0])
    background = Counter(int(cell) for row in frame for cell in row).most_common(1)[0][0]
    seen: set[tuple[int, int]] = set()
    output: list[dict[str, Any]] = []
    for y in range(height):
        for x in range(width):
            value = int(frame[y][x])
            if value == background or (y, x) in seen:
                continue
            queue = deque([(y, x)]); seen.add((y, x)); cells = []
            while queue:
                cy, cx = queue.popleft(); cells.append((cy, cx))
                for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                    if 0 <= ny < height and 0 <= nx < width and (ny, nx) not in seen and int(frame[ny][nx]) == value:
                        seen.add((ny, nx)); queue.append((ny, nx))
            min_y = min(c[0] for c in cells); min_x = min(c[1] for c in cells)
            signature = tuple(sorted((cy - min_y, cx - min_x) for cy, cx in cells))
            max_y = max(c[0] for c in cells); max_x = max(c[1] for c in cells)
            local = set(signature)
            exterior: set[tuple[int, int]] = set()
            frontier = deque(
                (y0, x0)
                for y0 in range(-1, max_y - min_y + 2)
                for x0 in range(-1, max_x - min_x + 2)
                if y0 in {-1, max_y - min_y + 1} or x0 in {-1, max_x - min_x + 1}
            )
            while frontier:
                point = frontier.popleft()
                if point in exterior or point in local:
                    continue
                y0, x0 = point
                if not (-1 <= y0 <= max_y - min_y + 1 and -1 <= x0 <= max_x - min_x + 1):
                    continue
                exterior.add(point)
                frontier.extend(((y0 - 1, x0), (y0 + 1, x0), (y0, x0 - 1), (y0, x0 + 1)))
            envelope = tuple(sorted(
                (y0, x0)
                for y0 in range(max_y - min_y + 1)
                for x0 in range(max_x - min_x + 1)
                if (y0, x0) not in exterior
            ))
            output.append({
                "value": value, "cells": tuple(sorted(cells)), "area": len(cells),
                "shape": signature, "outline": envelope,
                "hole_count": len(envelope) - len(signature),
                "center2": (sum(c[0] for c in cells) * 2 / len(cells), sum(c[1] for c in cells) * 2 / len(cells)),
            })
    return output


def _fact(predicate: str, left: str, right: str, frame_id: str) -> Any:
    evidence = E.stable_id("evidence", {"frame": frame_id, "predicate": predicate, "arguments": (left, right)})
    return E.GroundFact(predicate, (left, right), ("region-binding", "region-binding"), evidence, frame_id)


class FrameSchemaObserver:
    """Fit a fresh, grounded recursive workspace to each displayed frame."""

    relation_predicates = (
        "SameOutline", "DifferentOutline", "SameValue", "DifferentValue",
        "SameArea", "DifferentArea", "SameInterior", "DifferentInterior",
        "AlignedHorizontal", "AlignedVertical", "Disjoint", "Touches",
    )

    def __init__(self) -> None:
        self.last_digest: str | None = None
        self.last_stats: dict[str, Any] | None = None
        self.last_regions: list[dict[str, Any]] = []
        self.last_region_descriptors: dict[str, dict[str, Any]] = {}
        self.last_relation_bindings: dict[tuple[str, tuple[str, ...]], str] = {}
        self.action_effects: dict[tuple[int, tuple[Any, ...]], Counter[tuple[float, float]]] = defaultdict(Counter)
        self.action_uses: Counter[int] = Counter()
        self.explanation_confirmations: Counter[str] = Counter()
        self.explanation_refutations: Counter[str] = Counter()
        self.pending_prediction: dict[str, Any] | None = None
        self.last_store: Any | None = None
        self.last_workspace: Any | None = None
        self.last_atom_ids: tuple[str, ...] = ()
        self.last_rejected_goals: list[dict[str, Any]] = []
        self.last_potential_states: dict[str, dict[str, Any]] = {}
        self.last_verb_bindings: dict[str, dict[str, Any]] = {}
        self.last_action_atoms: dict[int, str] = {}
        self.last_categorical_bindings: list[dict[str, Any]] = []
        self.last_temporal_comparisons: list[dict[str, Any]] = []
        self.previous_categorical_values: dict[tuple[str, str], dict[str, Any]] = {}
        self.last_abductive_bindings: list[dict[str, Any]] = []
        self.last_rejected_abductions: list[dict[str, Any]] = []
        self.categorical_augmented_digest: str | None = None
        self.role_trajectories: dict[str, dict[str, dict[str, Any]]] = {}
        self.last_identity_assessments: list[dict[str, Any]] = []
        self.last_control_proposal: dict[str, Any] | None = None
        self.last_control_settlement: dict[str, Any] | None = None
        self.fast_policy_state: dict[str, Any] | None = None
        self.frame_shape: tuple[int, int] = (0, 0)

    def reset_episode(self) -> None:
        """Start with a genuinely fresh epistemic workspace.

        Frame digests are deliberately cached within an episode.  They must not
        make an identical first frame reuse bindings, shadows, learned action
        effects, or pending predictions from an earlier arcade run.
        """
        self.__init__()

    def advance_level(self) -> None:
        """Clear situated bindings while retaining supported game mechanics."""
        retained = {
            "action_effects": self.action_effects,
            "action_uses": self.action_uses,
            "explanation_confirmations": self.explanation_confirmations,
            "explanation_refutations": self.explanation_refutations,
        }
        self.__init__()
        for name, value in retained.items():
            setattr(self, name, value)

    @staticmethod
    def _semantic_explanation(explanation: dict[str, Any]) -> dict[str, Any]:
        """Loss-bounded projection of one executable explanation for Qwen."""
        ports = explanation.get("ports", {})
        goal = explanation.get("goal", {})
        prediction = explanation.get("prediction", {})
        evaluation = explanation.get("epistemic_evaluation", {})
        return {
            "binding_id": explanation.get("binding_id"),
            "schema_id": explanation.get("schema_id"),
            "verb": explanation.get("verb"),
            "epistemic_status": explanation.get("epistemic_status"),
            "verb_status": explanation.get("verb_status"),
            "roles": dict(ports.get("situated_role_descriptors", {})),
            "potential": {
                "binding_id": ports.get("potential"),
                "observable": goal.get("measure"),
                "value": goal.get("current"),
                "preferred_direction": goal.get("direction"),
                "terminal": goal.get("terminal"),
                "terminal_class": goal.get("terminal_class"),
            },
            "mechanism": {
                "causal_effect_binding_id": ports.get("causal_effect"),
                "action": prediction.get("action"),
                "actor_delta": prediction.get("actor_delta"),
                "predicted_value": prediction.get("residual_after"),
                "expected_progress": prediction.get("expected_progress"),
                "confidence": evaluation.get("mechanism_confidence"),
            },
            "progress_binding_id": ports.get("progress"),
            "preferred_completion_binding_id": ports.get("preferred_completion"),
            "control_status": explanation.get("control_status"),
            "role_identity": dict(explanation.get("identity", {})),
            "role_grounding": dict(explanation.get("role_grounding", {})),
            "desired_delta": dict(explanation.get("desired_delta", {})),
            "open_shadow_ids": list(explanation.get("prospective_shadow_ids", ()))[:8],
            "confirmations": evaluation.get("confirmations", 0),
            "refutations": evaluation.get("refutations", 0),
        }

    def semantic_projection(
        self, *, ranking: dict[str, Any] | None = None,
        settlement: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Expose grounded R2.1 conclusions to Semantic Qwen, read-only.

        This is an attention cut over the recursive workspace, not a graph
        dump. Qwen can reorganize or revise proposals from it; the contained
        statuses remain assertions made by R2 and the environment.
        """
        ranking = ranking or {}
        explanations = [
            self._semantic_explanation(item)
            for item in ranking.get("explanations", ())[:4]
            if isinstance(item, dict)
        ]
        current = ranking.get("current_explanation")
        active = self._semantic_explanation(current) if isinstance(current, dict) else None
        relations = [
            {
                "predicate": predicate,
                "arguments": list(arguments),
                "binding_id": binding_id,
            }
            for (predicate, arguments), binding_id in sorted(self.last_relation_bindings.items())[:16]
        ]
        open_shadows = []
        if self.last_workspace is not None:
            for shadow in sorted(self.last_workspace.shadows.values(), key=lambda item: item.shadow_id):
                if shadow.state == E.ShadowState.OPEN:
                    open_shadows.append({
                        "shadow_id": shadow.shadow_id,
                        "binding_id": shadow.binding_id,
                        "predicate": shadow.relation.predicate,
                        "missing_ports": list(shadow.missing_ports),
                    })
                if len(open_shadows) >= 12:
                    break
        return {
            "protocol": "r2.1-semantic-projection-v1",
            "authority": {
                "grounding_and_causal_status": "r2",
                "settlement_evidence": "environment",
                "semantic_revision": "qwen-proposal-only",
                "action_selection": "r2-only",
            },
            "frame_digest": self.last_digest,
            "active_explanation": active,
            "competing_explanations": explanations,
            "salient_structural_bindings": relations,
            "open_shadows": open_shadows,
            "rejected_semantic_proposals": list(self.last_rejected_goals)[:4],
            "latest_settlement": dict(settlement) if isinstance(settlement, dict) else None,
            "schema_summary": {
                "maximum_level": (self.last_stats or {}).get("maximum_level"),
                "totals": dict((self.last_stats or {}).get("totals", {})),
            },
            "categorical_comparisons": [
                {
                    "binding_id": item["binding_id"], "schema_id": item["schema_id"],
                    "type": item["type"], "residual_vector": dict(item["residual_vector"]),
                }
                for item in self.last_categorical_bindings[:12]
            ],
            "temporal_comparisons": [dict(item) for item in self.last_temporal_comparisons[:12]],
            "grounded_abductions": [dict(item) for item in self.last_abductive_bindings[:6]],
            "rejected_abductions": [dict(item) for item in self.last_rejected_abductions[:6]],
            "control_v0": {
                "proposal": dict(self.last_control_proposal) if self.last_control_proposal else None,
                "settlement": dict(self.last_control_settlement) if self.last_control_settlement else None,
                "identity_assessments": [dict(item) for item in self.last_identity_assessments[-8:]],
                "claim": "identity-gated horizon-1 successor evaluation",
            },
        }

    def _definitions(self) -> tuple[Any, Any, dict[str, Any]]:
        store = E.SchemaStore()
        schema0 = store.add(E.Schema.create(
            (E.Port("support", "region-support"),), (), kind="schema0", output_type="region-binding",
        ), promoted=True)
        relations = {}
        for predicate in self.relation_predicates:
            relations[predicate] = store.add(E.Schema.create(
                (E.Port("left", "region-binding"), E.Port("right", "region-binding")),
                (E.Relation(predicate, ("left", "right")),),
                kind="relational", output_type="relation-binding",
            ), promoted=True)
        composition = store.add(E.Schema.create(
            (E.Port("first", "relation-binding"), E.Port("second", "relation-binding")),
            (E.Relation("CoDescribes", ("first", "second")),),
            components=tuple(item.schema_id for item in relations.values()),
            kind="compositional", output_type="configuration-binding",
        ), promoted=True)
        return store, schema0, relations | {"CoDescribes": composition}

    def _add_fact(self, predicate: str, arguments: Sequence[str], types: Sequence[str], *, authority: str = "derived") -> Any:
        assert self.last_workspace is not None
        evidence = E.stable_id("evidence", {
            "frame": self.last_digest, "predicate": predicate, "arguments": tuple(arguments),
        })
        fact = E.GroundFact(
            predicate, tuple(arguments), tuple(types), evidence,
            f"frame:{self.last_digest}", authority=authority,
        )
        self.last_workspace.add_fact(fact)
        return fact

    def _fit_atom(self, schema: Any, facts: Sequence[Any], *, assignments: dict[str, str] | None = None) -> Any | None:
        assert self.last_workspace is not None
        for fact in facts:
            self.last_workspace.add_fact(fact)
        candidates = E.fit_schema(schema, tuple(self.last_workspace.facts.values()), budget=64, initial_assignments=assignments)
        binding = next((item for item in candidates if item.state == E.BindingState.REIFIED), None)
        if binding is None:
            return None
        if binding.binding_id in self.last_workspace.bindings and binding.binding_id in self.last_workspace.atoms:
            return self.last_workspace.atoms[binding.binding_id]
        return self.last_workspace.add_binding_atom(schema, binding)

    def _add_open_binding(self, schema: Any, assignments: dict[str, str]) -> tuple[Any, tuple[Any, ...]]:
        assert self.last_workspace is not None
        candidates = E.fit_schema(
            schema, tuple(self.last_workspace.facts.values()), budget=16,
            initial_assignments=assignments,
        )
        binding = next((item for item in candidates if item.state == E.BindingState.PARTIAL), None)
        if binding is not None:
            self.last_workspace.bindings[binding.binding_id] = binding
            shadows = E.project_shadows(schema, binding, limit=16)
            for shadow in shadows:
                self.last_workspace.shadows[shadow.shadow_id] = shadow
            return binding, shadows

        # Fitting is idempotent: after evidence has completed this relation the
        # same request legitimately returns REIFIED rather than PARTIAL.  That
        # is an already-satisfied open port, not an exceptional state.
        binding = next((item for item in candidates if item.state == E.BindingState.REIFIED), None)
        if binding is not None:
            if binding.binding_id not in self.last_workspace.atoms:
                self.last_workspace.add_binding_atom(schema, binding)
            return binding, ()
        raise RuntimeError(
            f"schema {schema.schema_id} produced neither a partial nor a reified binding"
        )

    @staticmethod
    def _terminal_class(direction: str) -> str:
        return {"decrease": "minimum", "increase": "maximum", "maintain": "invariant"}.get(direction, "open")

    def _refresh_recursive_stats(self) -> None:
        if self.last_workspace is None or self.last_store is None or self.last_stats is None:
            return
        workspace, store = self.last_workspace, self.last_store
        atoms_by_level: dict[int, list[Any]] = defaultdict(list)
        partial_by_level: Counter[int] = Counter()
        shadows_by_level: Counter[int] = Counter()
        for atom in workspace.atoms.values():
            atoms_by_level[atom.depth].append(atom)
        shadows_by_binding = Counter(shadow.binding_id for shadow in workspace.shadows.values())
        for binding in workspace.bindings.values():
            if binding.state != E.BindingState.PARTIAL:
                continue
            depths = [workspace.atoms[value].depth for _port, value in binding.assignments if value in workspace.atoms]
            level = 1 + max(depths, default=-1)
            partial_by_level[level] += 1
            shadows_by_level[level] += shadows_by_binding[binding.binding_id]
        levels = []
        for level in sorted(set(atoms_by_level) | set(partial_by_level)):
            atoms = atoms_by_level.get(level, [])
            schema_ids = {workspace.bindings[atom.source_id].schema_id for atom in atoms}
            levels.append({
                "level": level,
                "unique_schemas": len(schema_ids),
                "bindings": len(atoms),
                "partial_bindings": partial_by_level[level],
                "shadows": shadows_by_level[level],
                "output_types": dict(sorted(Counter(atom.type for atom in atoms).items())),
            })
        self.last_stats = {
            **self.last_stats,
            "definitions_available": len(store.records),
            "maximum_level": max(set(atoms_by_level) | set(partial_by_level), default=-1),
            "levels": levels,
            "totals": {
                "situated_bindings": len(workspace.atoms),
                "unique_schemas_bound": len({workspace.bindings[a.source_id].schema_id for a in workspace.atoms.values()}),
                "partial_bindings": sum(partial_by_level.values()),
                "shadows": len(workspace.shadows),
            },
        }

    @staticmethod
    def _generic_atom_descriptor(atom: Any, workspace: Any, store: Any) -> dict[str, Any]:
        binding = workspace.bindings[atom.source_id]
        schema = store.records[binding.schema_id].schema
        assigned_types = sorted(
            workspace.atoms[value].type
            for _port, value in binding.assignments
            if value in workspace.atoms
        )
        return {
            "schema_id": schema.schema_id,
            "schema_kind": schema.kind,
            "arity": len(schema.ports),
            "constraint_count": len(schema.constraints),
            "assigned_types": tuple(assigned_types),
            "depth": atom.depth,
        }

    @staticmethod
    def _categorical_residual_vector(left: dict[str, Any], right: dict[str, Any]) -> dict[str, float]:
        if "cells" in left and "cells" in right:
            size = max(float(left["area"]) ** 0.5, float(right["area"]) ** 0.5, 1.0)
            boundary_gap = max(0.0, min(
                abs(ay - by) + abs(ax - bx)
                for ay, ax in left["cells"] for by, bx in right["cells"]
            ) - 1.0)
            shape_left, shape_right = set(left["shape"]), set(right["shape"])
            return {
                "normalized_boundary_gap": round(boundary_gap / size, 6),
                "shape_symmetric_difference": round(len(shape_left ^ shape_right) / max(len(shape_left | shape_right), 1), 6),
                "relative_area_difference": round(abs(left["area"] - right["area"]) / max(left["area"], right["area"], 1), 6),
                "value_difference": 0.0 if left["value"] == right["value"] else 1.0,
            }
        return {
            "schema_difference": 0.0 if left["schema_id"] == right["schema_id"] else 1.0,
            "interface_difference": round(len(set(left["assigned_types"]) ^ set(right["assigned_types"])) / max(len(set(left["assigned_types"]) | set(right["assigned_types"])), 1), 6),
            "arity_difference": float(abs(left["arity"] - right["arity"])),
            "depth_difference": float(abs(left["depth"] - right["depth"])),
        }

    def _fit_categorical_comparisons(self, *, advance_temporal: bool = True) -> dict[str, Any]:
        """Fit bounded enriched correspondences as ordinary recursive schemas."""
        assert self.last_store is not None and self.last_workspace is not None
        started = time.perf_counter(); workspace, store = self.last_workspace, self.last_store
        regions = dict(self.last_region_descriptors)
        descriptors = {
            atom.atom_id: (regions[atom.atom_id] if atom.atom_id in regions else self._generic_atom_descriptor(atom, workspace, store))
            for atom in workspace.atoms.values()
        }
        by_type: dict[str, list[Any]] = defaultdict(list)
        for atom in workspace.atoms.values():
            by_type[atom.type].append(atom)
        pair_candidates: list[tuple[float, str, Any, Any, dict[str, float]]] = []
        for type_name, atoms in sorted(by_type.items()):
            frontier = sorted(atoms, key=lambda item: item.atom_id)[:CATEGORICAL_ATOMS_PER_TYPE]
            scored: dict[str, list[tuple[float, str, Any, dict[str, float]]]] = defaultdict(list)
            for index, left in enumerate(frontier):
                for right in frontier[index + 1:]:
                    vector = self._categorical_residual_vector(descriptors[left.atom_id], descriptors[right.atom_id])
                    score = sum(vector.values())
                    scored[left.atom_id].append((score, right.atom_id, right, vector))
                    scored[right.atom_id].append((score, left.atom_id, left, vector))
            selected: set[tuple[str, str]] = set()
            for left in frontier:
                for score, _right_id, right, vector in sorted(scored[left.atom_id])[:CATEGORICAL_NEIGHBORS_PER_ATOM]:
                    pair = tuple(sorted((left.atom_id, right.atom_id)))
                    if pair in selected: continue
                    selected.add(pair)
                    ordered = (left, right) if left.atom_id == pair[0] else (right, left)
                    pair_candidates.append((score, type_name, ordered[0], ordered[1], vector))
        # Fair typed interleaving prevents one prolific recursive level from
        # consuming the whole comparison/temporal budget.
        candidate_buckets: dict[str, list[Any]] = defaultdict(list)
        for item in pair_candidates: candidate_buckets[item[1]].append(item)
        for bucket in candidate_buckets.values():
            bucket.sort(key=lambda item: (item[0], item[2].atom_id, item[3].atom_id))
        pair_candidates = []
        while len(pair_candidates) < CATEGORICAL_COMPARISON_BUDGET:
            added = False
            for type_name in sorted(candidate_buckets):
                if candidate_buckets[type_name]:
                    pair_candidates.append(candidate_buckets[type_name].pop(0)); added = True
                    if len(pair_candidates) >= CATEGORICAL_COMPARISON_BUDGET: break
            if not added: break

        comparisons: list[dict[str, Any]] = []; temporal: list[dict[str, Any]] = []
        current_values: dict[tuple[str, str], dict[str, Any]] = {}
        for _score, type_name, left, right, vector in pair_candidates:
            predicate = "AdmissibleTypedCorrespondence"
            correspondence_schema = store.add(E.Schema.create(
                (E.Port("left", type_name), E.Port("right", type_name)),
                (E.Relation(predicate, ("left", "right")),),
                kind="correspondence", output_type="correspondence-binding",
            ))
            fact = self._add_fact(predicate, (left.atom_id, right.atom_id), (type_name, type_name))
            correspondence = self._fit_atom(correspondence_schema, (fact,), assignments={"left": left.atom_id, "right": right.atom_id})
            if correspondence is None: continue
            left_descriptor, right_descriptor = descriptors[left.atom_id], descriptors[right.atom_id]
            member_signatures = [
                descriptor.get("schema_id", self._region_key(descriptor) if "cells" in descriptor else atom.atom_id)
                for descriptor, atom in ((left_descriptor, left), (right_descriptor, right))
            ]
            signature = E.stable_id("correspondence-signature", {
                "type": type_name,
                "members": sorted(member_signatures, key=lambda item: json.dumps(item, sort_keys=True)),
            })
            component_ids = []
            for dimension, value in sorted(vector.items()):
                evidence = E.stable_id("measured-residual", {"frame": self.last_digest, "correspondence": signature, "dimension": dimension, "value": value})
                residual = self._schema0_atom(
                    support_id=evidence, support_type="residual-support",
                    output_type="residual-binding", evidence_id=evidence,
                )
                relation = "MeasuresTypedResidual"
                residual_schema = store.add(E.Schema.create(
                    (E.Port("correspondence", "correspondence-binding"), E.Port("residual", "residual-binding")),
                    (E.Relation(relation, ("correspondence", "residual")),),
                    components=(correspondence_schema.schema_id,),
                    kind="comparison", output_type="comparison-binding",
                ))
                measured = self._add_fact(relation, (correspondence.atom_id, residual.atom_id), ("correspondence-binding", "residual-binding"))
                component = self._fit_atom(residual_schema, (measured,), assignments={"correspondence": correspondence.atom_id, "residual": residual.atom_id})
                if component is None: continue
                component_ids.append(component.atom_id)
                key = (signature, dimension)
                current_values[key] = {"value": value, "residual_binding_id": residual.atom_id, "type": type_name}
                previous = self.previous_categorical_values.get(key) if advance_temporal else None
                if previous is not None and len(temporal) < CATEGORICAL_TEMPORAL_BUDGET:
                    previous_evidence = E.stable_id("historical-residual", {"comparison": signature, "dimension": dimension, "value": previous["value"]})
                    before = self._schema0_atom(
                        support_id=previous_evidence, support_type="historical-residual-support",
                        output_type="historical-residual-binding", evidence_id=previous_evidence,
                    )
                    orientation = "ResidualStable" if abs(value - previous["value"]) <= 1e-9 else ("ResidualDecreased" if value < previous["value"] else "ResidualIncreased")
                    temporal_schema = store.add(E.Schema.create(
                        (E.Port("before", "historical-residual-binding"), E.Port("after", "residual-binding")),
                        (E.Relation(orientation, ("before", "after")),),
                        components=(residual_schema.schema_id,), kind="temporal-comparison",
                        output_type="temporal-comparison-binding",
                    ))
                    change_fact = self._add_fact(orientation, (before.atom_id, residual.atom_id), ("historical-residual-binding", "residual-binding"))
                    change = self._fit_atom(temporal_schema, (change_fact,), assignments={"before": before.atom_id, "after": residual.atom_id})
                    if change is not None:
                        temporal.append({"binding_id": change.atom_id, "comparison_signature": signature, "dimension": dimension, "before": previous["value"], "after": value, "orientation": orientation})
            comparisons.append({
                "binding_id": correspondence.atom_id, "schema_id": correspondence_schema.schema_id,
                "type": type_name, "left": left.atom_id, "right": right.atom_id,
                "signature": signature, "residual_vector": vector,
                "residual_component_binding_ids": component_ids,
            })
        if advance_temporal:
            self.previous_categorical_values = current_values
        self.last_categorical_bindings = comparisons
        if advance_temporal:
            self.last_temporal_comparisons = temporal
        reported_temporal = temporal if advance_temporal else self.last_temporal_comparisons
        return {
            "candidate_pairs": len(pair_candidates), "correspondences": len(comparisons),
            "residual_components": sum(len(item["residual_component_binding_ids"]) for item in comparisons),
            "temporal_comparisons": len(reported_temporal),
            "types_compared": sorted({item["type"] for item in comparisons}),
            "budgets": {
                "atoms_per_type": CATEGORICAL_ATOMS_PER_TYPE,
                "neighbors_per_atom": CATEGORICAL_NEIGHBORS_PER_ATOM,
                "comparisons": CATEGORICAL_COMPARISON_BUDGET,
                "temporal": CATEGORICAL_TEMPORAL_BUDGET,
            },
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        }

    def _compile_abductions(self, proposals: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Compile Qwen diagram completions into ordinary bounded schema fits."""
        self.last_abductive_bindings = []; self.last_rejected_abductions = []
        if self.last_store is None or self.last_workspace is None:
            return []
        store, workspace = self.last_store, self.last_workspace
        atoms_by_schema: dict[str, list[Any]] = defaultdict(list)
        for atom in workspace.atoms.values():
            binding = workspace.bindings.get(atom.source_id)
            if binding is not None:
                atoms_by_schema[binding.schema_id].append(atom)
        for raw in list(proposals)[:4]:
            proposal = dict(raw); local_ref = str(proposal.get("local_ref", ""))
            components = tuple(dict.fromkeys(str(item) for item in proposal.get("component_schema_ids", ())))
            morphisms = tuple(dict(item) for item in proposal.get("morphisms", ()))[:6]
            if not re.fullmatch(r"composition_[0-9]{1,2}", local_ref):
                self.last_rejected_abductions.append({"local_ref": local_ref, "reason": "invalid-local-ref"}); continue
            if not 2 <= len(components) <= 4 or any(item not in store.records for item in components):
                self.last_rejected_abductions.append({"local_ref": local_ref, "reason": "unknown-or-unbounded-components"}); continue
            if not morphisms:
                self.last_rejected_abductions.append({"local_ref": local_ref, "reason": "diagram-has-no-morphisms"}); continue
            if any(
                item.get("source_schema_id") not in components
                or item.get("target_schema_id") not in components
                or item.get("source_schema_id") == item.get("target_schema_id")
                or item.get("kind") not in {"preserves", "factors_through", "constrains", "predicts", "realizes", "co_describes"}
                for item in morphisms
            ):
                self.last_rejected_abductions.append({"local_ref": local_ref, "reason": "ill-typed-morphism-boundary"}); continue
            if any(not atoms_by_schema.get(schema_id) for schema_id in components):
                self.last_rejected_abductions.append({"local_ref": local_ref, "reason": "components-not-situated-in-current-frame"}); continue
            port_by_schema = {schema_id: f"c{index}" for index, schema_id in enumerate(components)}
            ports = tuple(E.Port(port_by_schema[schema_id], store.records[schema_id].schema.output_type) for schema_id in components)
            relations = tuple(E.Relation(
                f"DiagramMorphism:{str(item['kind'])}",
                (port_by_schema[str(item["source_schema_id"])], port_by_schema[str(item["target_schema_id"])]),
            ) for item in morphisms)
            composition_schema = store.add(E.Schema.create(
                ports, relations, components=components,
                kind="abductive-composition", output_type="abductive-composition-binding",
            ))
            candidate_lists = [sorted(atoms_by_schema[schema_id], key=lambda item: item.atom_id)[:2] for schema_id in components]
            grounded_for_proposal = 0
            for choice in list(product(*candidate_lists))[:16]:
                assignments = {port_by_schema[schema_id]: atom.atom_id for schema_id, atom in zip(components, choice, strict=True)}
                facts = []
                for relation, morphism in zip(relations, morphisms, strict=True):
                    source = assignments[port_by_schema[str(morphism["source_schema_id"])]]
                    target = assignments[port_by_schema[str(morphism["target_schema_id"])]]
                    facts.append(self._add_fact(
                        relation.predicate, (source, target),
                        (workspace.atoms[source].type, workspace.atoms[target].type),
                    ))
                atom = self._fit_atom(composition_schema, facts, assignments=assignments)
                if atom is None: continue
                shadow_ids = []
                for preferred in list(proposal.get("preferred_residual_changes", ()))[:4]:
                    comparison_schema_id = str(preferred.get("comparison_schema_id", ""))
                    if comparison_schema_id not in components or comparison_schema_id not in store.records:
                        continue
                    direction = str(preferred.get("direction", ""))
                    dimension = str(preferred.get("dimension", ""))
                    if direction not in {"decrease", "increase", "maintain"} or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", dimension):
                        continue
                    prediction_schema = store.add(E.Schema.create(
                        (E.Port("abduction", "abductive-composition-binding"), E.Port("successor", "temporal-comparison-binding")),
                        (E.Relation(f"PredictsResidual:{direction}:{dimension}", ("abduction", "successor")),),
                        components=(composition_schema.schema_id, comparison_schema_id),
                        kind="abductive-prediction", output_type="abductive-prediction-binding",
                    ))
                    _partial, shadows = self._add_open_binding(prediction_schema, {"abduction": atom.atom_id})
                    shadow_ids.extend(shadow.shadow_id for shadow in shadows)
                record = {
                    "local_ref": local_ref, "binding_id": atom.atom_id,
                    "schema_id": composition_schema.schema_id,
                    "component_schema_ids": list(components),
                    "situated_component_binding_ids": list(assignments.values()),
                    "morphisms": [dict(item) for item in morphisms],
                    "prediction_shadow_ids": shadow_ids,
                    "epistemic_status": "grounded-structural-open-prediction" if shadow_ids else "grounded-structural",
                }
                if record["binding_id"] not in {item["binding_id"] for item in self.last_abductive_bindings}:
                    self.last_abductive_bindings.append(record)
                grounded_for_proposal += 1
            if not grounded_for_proposal:
                self.last_rejected_abductions.append({"local_ref": local_ref, "reason": "no-compatible-situated-completion"})
        self._refresh_recursive_stats()
        return list(self.last_abductive_bindings)

    def fit_frame(self, frame: Sequence[Sequence[int]], *, turn: int = 0) -> dict[str, Any]:
        started = time.perf_counter()
        normalized = [[int(cell) for cell in row] for row in frame]
        self.frame_shape = (len(normalized), len(normalized[0]) if normalized else 0)
        digest = sha256(json.dumps(normalized, separators=(",", ":")).encode()).hexdigest()[:16]
        if digest == self.last_digest and self.last_stats is not None:
            return {**self.last_stats, "turn": int(turn), "cached": True}

        self.last_potential_states = {}
        self.last_verb_bindings = {}
        self.last_action_atoms = {}
        self.categorical_augmented_digest = None

        store, schema0, schemas = self._definitions()
        workspace = E.BindingWorkspace()
        regions = _components(normalized)
        atom_ids: list[str] = []
        for index, region in enumerate(regions):
            evidence_id = E.stable_id("pixel-region", {"frame": digest, "cells": region["cells"], "value": region["value"]})
            support = E.GroundSupport(f"region:{digest}:{index}", "region-support", evidence_id, f"frame:{digest}")
            atom_ids.append(workspace.bind_schema0(schema0, support, port_name="support").atom_id)

        facts = []
        for left in range(len(regions)):
            for right in range(left + 1, len(regions)):
                a, b = regions[left], regions[right]
                predicates = (
                    "SameOutline" if a["outline"] == b["outline"] else "DifferentOutline",
                    "SameValue" if a["value"] == b["value"] else "DifferentValue",
                    "SameArea" if a["area"] == b["area"] else "DifferentArea",
                    "SameInterior" if a["shape"] == b["shape"] else "DifferentInterior",
                )
                if a["center2"][0] == b["center2"][0]: predicates += ("AlignedHorizontal",)
                if a["center2"][1] == b["center2"][1]: predicates += ("AlignedVertical",)
                gap = min(abs(ay - by) + abs(ax - bx) for ay, ax in a["cells"] for by, bx in b["cells"])
                predicates += (("Touches",) if gap == 1 else ("Disjoint",))
                for predicate in predicates:
                    facts.append(_fact(predicate, atom_ids[left], atom_ids[right], digest))
                    facts.append(_fact(predicate, atom_ids[right], atom_ids[left], digest))

        fitter = E.RecursiveSchemaFitter(store, workspace, budget=E.FrontierBudget(
            retrieval=24, binding_expansion=256, shadow_generation=128,
            relation_joins=12000, new_bindings=4096, max_depth_increment=2,
        ))
        first = fitter.close(atom_ids, facts)

        relation_atoms = [atom for atom in workspace.atoms.values() if atom.type == "relation-binding"]
        relation_bindings: dict[tuple[str, tuple[str, ...]], str] = {}
        by_ground_pair: dict[tuple[str, ...], list[str]] = defaultdict(list)
        for atom in relation_atoms:
            binding = workspace.bindings[atom.source_id]
            ground_pair = tuple(sorted(value for _port, value in binding.assignments))
            by_ground_pair[ground_pair].append(atom.atom_id)
            schema = store.records[binding.schema_id].schema
            if schema.constraints:
                relation_bindings[(schema.constraints[0].predicate, ground_pair)] = atom.atom_id
        cofacts = []
        for pair_atoms in by_ground_pair.values():
            for i, left in enumerate(sorted(pair_atoms)):
                for right in sorted(pair_atoms)[i + 1:]:
                    evidence = E.stable_id("derived", {"predicate": "CoDescribes", "arguments": (left, right)})
                    cofacts.append(E.GroundFact(
                        "CoDescribes", (left, right), ("relation-binding", "relation-binding"),
                        evidence, f"frame:{digest}", authority="derived",
                    ))
        second = fitter.close([atom.atom_id for atom in relation_atoms], cofacts) if relation_atoms else None

        # Categorical correspondences are fitted into the same workspace after
        # the ordinary frame closure. The frontier is typed and explicitly
        # bounded, so recursive comparison never becomes an unrestricted
        # all-pairs expansion.
        self.last_regions = [{**region, "binding_id": atom_id} for region, atom_id in zip(regions, atom_ids, strict=True)]
        self.last_region_descriptors = {
            region["binding_id"]: region for region in self.last_regions
        }
        self.last_relation_bindings = relation_bindings
        self.last_store, self.last_workspace = store, workspace
        self.last_atom_ids = tuple(atom_ids)
        self.last_digest = digest
        categorical = self._fit_categorical_comparisons()

        partial_by_level: Counter[int] = Counter()
        shadows_by_level: Counter[int] = Counter()
        for binding in workspace.bindings.values():
            if binding.state != E.BindingState.PARTIAL:
                continue
            depths = [workspace.atoms[value].depth for _port, value in binding.assignments if value in workspace.atoms]
            level = 1 + max(depths, default=-1)
            partial_by_level[level] += 1
            shadows_by_level[level] += sum(1 for shadow in workspace.shadows.values() if shadow.binding_id == binding.binding_id)

        atoms_by_level: dict[int, list[Any]] = defaultdict(list)
        for atom in workspace.atoms.values(): atoms_by_level[atom.depth].append(atom)
        levels = []
        for level in sorted(set(atoms_by_level) | set(partial_by_level)):
            atoms = atoms_by_level.get(level, [])
            schema_ids = {workspace.bindings[atom.source_id].schema_id for atom in atoms}
            levels.append({
                "level": level,
                "unique_schemas": len(schema_ids),
                "bindings": len(atoms),
                "partial_bindings": partial_by_level[level],
                "shadows": shadows_by_level[level],
                "output_types": dict(sorted(Counter(atom.type for atom in atoms).items())),
            })
        stats = {
            "engine": "R2.1 parallel recursive schema fitting",
            "frame_digest": digest, "turn": int(turn), "cached": False,
            "regions": len(regions), "definitions_available": len(store.records),
            "maximum_level": max(atoms_by_level, default=-1), "levels": levels,
            "totals": {
                "situated_bindings": len(workspace.atoms),
                "unique_schemas_bound": len({workspace.bindings[a.source_id].schema_id for a in workspace.atoms.values()}),
                "partial_bindings": sum(partial_by_level.values()), "shadows": len(workspace.shadows),
            },
            "closure": {
                "initial": E.asdict(first),
                "compositional": E.asdict(second) if second is not None else None,
            },
            "categorical": categorical,
            "elapsed_ms": round((time.perf_counter() - started) * 1000, 2),
        }
        self.last_digest, self.last_stats = digest, stats
        return stats

    def _bind_verb_schemas(self, goals: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
        """Fit telic schemas recursively: roles -> potential -> verb -> open completion."""
        if self.last_store is None or self.last_workspace is None:
            return list(goals)
        fitted: list[dict[str, Any]] = []
        self.last_rejected_goals = []
        for raw in goals:
            goal = dict(raw)
            verb = str(goal.get("verb", "")).strip().lower()
            if CANONICAL_VERB.fullmatch(verb) is None:
                self.last_rejected_goals.append({
                    **goal,
                    "r2_grounding_status": "rejected-invalid-verb",
                    "reason": "verb must be one canonical symbol: [a-z][a-z0-9_]{0,39}",
                })
                continue
            observable = str(goal.get("observable", "unknown"))
            direction = str(goal.get("direction", "unknown"))
            terminal_class = str(goal.get("terminal_class", self._terminal_class(direction)))
            terminal = str(goal.get("terminal_condition", "")).lower().replace(" ", "")
            minimizing_terminal = any(token in terminal for token in ("<", "minimum", "minimal", "==0", "=0", "zero"))
            maximizing_terminal = any(token in terminal for token in (">", "maximum", "maximal"))
            expected_by_verb = {
                "fit": {
                    "fit_residual": "decrease", "centroid_distance": "decrease", "boundary_gap": "decrease",
                    "containment_violation": "decrease", "symmetry_residual": "decrease",
                    "overlap_deficit": "decrease", "overlap_area": "increase",
                },
                "touch": {"centroid_distance": "decrease", "boundary_gap": "decrease"},
                "avoid": {"centroid_distance": "increase", "boundary_gap": "increase", "overlap_area": "decrease"},
                "collect": {"centroid_distance": "decrease", "boundary_gap": "decrease", "component_count": "decrease"},
                "reveal": {"component_count": "increase"},
            }.get(verb, {})
            rejection = None
            if terminal_class != self._terminal_class(direction):
                rejection = f"{direction} requires terminal_class={self._terminal_class(direction)}"
            elif verb == "fit" and str(goal.get("goal_family")) == "separation":
                rejection = "fit cannot use a separation goal family"
            elif direction == "increase" and minimizing_terminal:
                rejection = "preferred direction moves away from minimizing terminal"
            elif direction == "decrease" and maximizing_terminal:
                rejection = "preferred direction moves away from maximizing terminal"
            elif observable in expected_by_verb and direction != expected_by_verb[observable]:
                rejection = f"{verb} requires {expected_by_verb[observable]}({observable})"
            if rejection is not None:
                self.last_rejected_goals.append({**goal, "verb": verb, "r2_grounding_status": "rejected-incoherent", "reason": rejection})
                continue
            roles = tuple(dict.fromkeys(str(role) for role in goal.get("roles", ())))
            potential_roles = tuple(str(role) for role in goal.get("potential_roles", ()))
            if not roles or len(potential_roles) != 2 or not set(potential_roles).issubset(roles):
                roles, potential_roles = ("actor", "target"), ("actor", "target")
            goal["roles"] = roles
            goal["potential_roles"] = potential_roles
            role_groundings = DefeasibleRoleGrounder(
                self.last_regions, measure=self._measure,
                relation_bindings=self.last_relation_bindings,
            ).ground(goal)
            if not role_groundings:
                self.last_rejected_goals.append({
                    **goal, "verb": verb, "r2_grounding_status": "rejected-ungrounded",
                    "reason": "no measurable typed tuple satisfies schema-required constraints",
                })
                continue
            candidate_predicate = "CandidateRoleTuple:" + E.stable_id("role-language", {
                "verb": verb, "observable": observable, "roles": roles,
            }).split(":")[-1][:16]
            role_schema = self.last_store.add(E.Schema.create(
                tuple(E.Port(role, "region-binding") for role in roles),
                (E.Relation(candidate_predicate, roles),),
                kind="verb-role-structure",
                output_type="verb-role-binding",
            ))
            regions = {region["binding_id"]: region for region in self.last_regions}
            situated: list[dict[str, Any]] = []
            for grounding in role_groundings:
                role_map = dict(grounding["situated_roles"])
                actor = regions.get(role_map.get(potential_roles[0], ""))
                target = regions.get(role_map.get(potential_roles[1], ""))
                if actor is None or target is None or actor is target:
                    continue
                current_value = self._measure(observable, actor, target)
                if current_value is None:
                    continue
                role_arguments = tuple(role_map[role] for role in roles)
                role_fact = self._add_fact(
                    candidate_predicate, role_arguments,
                    tuple("region-binding" for _role in roles),
                )
                role_atom = self._fit_atom(
                    role_schema, (role_fact,), assignments=role_map,
                )
                if role_atom is None:
                    continue

                measure_predicate = f"MeasuresPotential:{observable}"
                potential_schema = self.last_store.add(E.Schema.create(
                    (E.Port("roles", "verb-role-binding"),),
                    (E.Relation(measure_predicate, ("roles",)),),
                    components=(role_schema.schema_id,),
                    kind="potential",
                    output_type="potential-binding",
                ))
                measure_fact = self._add_fact(
                    measure_predicate, (role_atom.atom_id,), ("verb-role-binding",),
                )
                potential_atom = self._fit_atom(
                    potential_schema, (measure_fact,), assignments={"roles": role_atom.atom_id},
                )
                if potential_atom is None:
                    continue
                self.last_potential_states[potential_atom.atom_id] = {
                    "observable": observable, "value": float(current_value),
                    "actor": actor["binding_id"], "target": target["binding_id"],
                    "situated_roles": dict(role_map), "prospective": False,
                }

                verb_predicate = f"AdmissibleVerb:{verb}"
                verb_schema = self.last_store.add(E.Schema.create(
                    (E.Port("potential", "potential-binding"),),
                    (E.Relation(verb_predicate, ("potential",)),),
                    components=(potential_schema.schema_id,),
                    kind="verb",
                    output_type="verb-binding",
                ))
                verb_fact = self._add_fact(
                    verb_predicate, (potential_atom.atom_id,), ("potential-binding",),
                )
                verb_atom = self._fit_atom(
                    verb_schema, (verb_fact,), assignments={"potential": potential_atom.atom_id},
                )
                if verb_atom is None:
                    continue

                completion_predicate = ":".join((
                    "PreferredCompletion", direction, observable,
                    terminal_class,
                ))
                completion_schema = self.last_store.add(E.Schema.create(
                    (
                        E.Port("verb", "verb-binding"),
                        E.Port("successor", "prospective-potential-binding"),
                    ),
                    (E.Relation(completion_predicate, ("verb", "successor")),),
                    components=(verb_schema.schema_id,),
                    kind="preferred-completion",
                    output_type="preferred-completion-binding",
                ))
                completion, shadows = self._add_open_binding(
                    completion_schema, {"verb": verb_atom.atom_id},
                )
                record = {
                    "candidate_binding_id": grounding["candidate_binding_id"],
                    "verb_binding_id": verb_atom.atom_id,
                    "role_binding_id": role_atom.atom_id,
                    "potential_binding_id": potential_atom.atom_id,
                    "preferred_completion_binding_id": completion.binding_id,
                    "preferred_completion_shadow_ids": tuple(shadow.shadow_id for shadow in shadows),
                    "situated_roles": dict(role_map),
                    "current_potential": float(current_value),
                    "role_grounding": dict(grounding),
                }
                self.last_verb_bindings[verb_atom.atom_id] = {
                    **record, "verb": verb, "observable": observable,
                    "direction": direction, "terminal_class": terminal_class,
                }
                situated.append(record)

            if not situated:
                self.last_rejected_goals.append({
                    **goal, "verb": verb, "r2_grounding_status": "rejected-ungrounded",
                    "reason": "no measurable situated potential could bind",
                })
                continue
            goal["verb"] = verb
            goal["roles"] = roles
            goal["potential_roles"] = potential_roles
            goal["terminal_class"] = terminal_class
            goal["r2_schema_id"] = role_schema.schema_id
            goal["r2_binding_ids"] = tuple(item["verb_binding_id"] for item in situated)
            goal["r2_role_bindings"] = tuple(item["situated_roles"] for item in situated)
            goal["r2_role_groundings"] = tuple(item["role_grounding"] for item in situated)
            goal["r2_situated_verb_bindings"] = tuple(situated)
            goal["r2_open_shadows"] = tuple(
                shadow_id for item in situated
                for shadow_id in item["preferred_completion_shadow_ids"]
            )
            goal["r2_grounding_status"] = "grounded-open-completion"
            fitted.append(goal)
        self._refresh_recursive_stats()
        return fitted

    @staticmethod
    def _region_key(region: dict[str, Any]) -> tuple[Any, ...]:
        return int(region["value"]), int(region["area"]), tuple(region["shape"])

    @staticmethod
    def _region_snapshot(region: dict[str, Any]) -> dict[str, Any]:
        """Keep only the bounded evidence needed for role correspondence."""
        snapshot = {
            "value": int(region["value"]), "area": int(region["area"]),
            "shape": tuple(region["shape"]), "outline": tuple(region["outline"]),
            "cells": tuple(region["cells"]),
            "center2": tuple(float(value) for value in region["center2"]),
        }
        if region.get("binding_id") is not None:
            snapshot["binding_id"] = str(region["binding_id"])
        return snapshot

    @staticmethod
    def _goal_key(goal: dict[str, Any], candidate_binding_id: str | None = None) -> str:
        return E.stable_id("control-goal", {
            "verb": goal.get("verb"), "observable": goal.get("observable"),
            "direction": goal.get("direction"),
            "potential_roles": list(goal.get("potential_roles", ("actor", "target"))),
            "role_constraints": list(goal.get("role_constraints", ())),
            "candidate_binding_id": candidate_binding_id,
        })

    @staticmethod
    def _identity_residual(
        source: dict[str, Any], candidate: dict[str, Any],
        expected_delta: tuple[float, float] | None = None,
    ) -> tuple[float, dict[str, float]]:
        source_shape, candidate_shape = set(source["shape"]), set(candidate["shape"])
        source_outline, candidate_outline = set(source["outline"]), set(candidate["outline"])
        shape_denominator = max(1, len(source_shape | candidate_shape))
        outline_denominator = max(1, len(source_outline | candidate_outline))
        area = abs(float(source["area"]) - float(candidate["area"])) / max(
            1.0, float(source["area"]), float(candidate["area"]),
        )
        predicted_center = tuple(source["center2"])
        if expected_delta is not None:
            predicted_center = (
                predicted_center[0] + 2.0 * expected_delta[0],
                predicted_center[1] + 2.0 * expected_delta[1],
            )
        position = min(1.0, (
            abs(float(candidate["center2"][0]) - predicted_center[0])
            + abs(float(candidate["center2"][1]) - predicted_center[1])
        ) / (2.0 * max(1.0, float(source["area"]) ** 0.5)))
        components = {
            "shape": len(source_shape ^ candidate_shape) / shape_denominator,
            "area": area,
            "outline": len(source_outline ^ candidate_outline) / outline_denominator,
            "position": position,
            "value": 0.0 if int(source["value"]) == int(candidate["value"]) else 1.0,
        }
        residual = (
            0.25 * components["shape"] + 0.20 * components["area"]
            + 0.10 * components["outline"] + 0.35 * components["position"]
            + 0.10 * components["value"]
        )
        return residual, components

    def _correspondence(
        self, source: dict[str, Any] | None, candidates: Sequence[dict[str, Any]],
        *, expected_delta: tuple[float, float] | None = None,
    ) -> dict[str, Any]:
        if source is None:
            return {"status": "BROKEN", "reason": "missing-predecessor", "candidates": []}
        same_value = [
            candidate for candidate in candidates
            if int(candidate["value"]) == int(source["value"])
        ]
        candidates = same_value or list(candidates)
        scored = []
        for index, candidate in enumerate(candidates):
            residual, components = self._identity_residual(source, candidate, expected_delta)
            scored.append({
                "index": index, "region": candidate, "residual": residual,
                "components": components,
            })
        scored.sort(key=lambda item: (item["residual"], item["index"]))
        bounded = scored[:ROLE_CORRESPONDENCE_BUDGET]
        structurally_exact = [
            item for item in bounded
            if item["components"]["shape"] == 0
            and item["components"]["area"] == 0
            and item["components"]["outline"] == 0
            and item["components"]["value"] == 0
        ]
        if len(structurally_exact) == 1:
            best = structurally_exact[0]
            others = [item["residual"] for item in bounded if item is not best]
            second = min(others, default=1.0)
            return {
                "status": "UNIQUE", "reason": "unique-structure-preserving-successor",
                "best_residual": round(best["residual"], 4),
                "second_residual": round(second, 4),
                "margin": round(second - best["residual"], 4),
                "best": best, "candidates": [best, *[item for item in bounded if item is not best]],
            }
        if not bounded or bounded[0]["residual"] > ROLE_IDENTITY_MAX_RESIDUAL:
            return {
                "status": "BROKEN", "reason": "no-admissible-successor",
                "best_residual": None if not bounded else round(bounded[0]["residual"], 4),
                "candidates": bounded,
            }
        second = bounded[1]["residual"] if len(bounded) > 1 else 1.0
        margin = second - bounded[0]["residual"]
        status = "UNIQUE" if margin >= ROLE_IDENTITY_MIN_MARGIN else "AMBIGUOUS"
        return {
            "status": status,
            "reason": "separated-best-correspondence" if status == "UNIQUE" else "insufficient-correspondence-margin",
            "best_residual": round(bounded[0]["residual"], 4),
            "second_residual": round(second, 4), "margin": round(margin, 4),
            "best": bounded[0], "candidates": bounded,
        }

    def _occlusion_correspondence(
        self,
        source: dict[str, Any] | None,
        other: dict[str, Any] | None,
        after: Sequence[Sequence[int]],
        *,
        expected_delta: tuple[float, float] | None,
        other_expected_delta: tuple[float, float] | None,
    ) -> dict[str, Any] | None:
        """Fit one exact model-supported successor through mutual occlusion.

        A latent translated occupancy is admissible only when all exposed
        predicted cells remain visibly the source value, ambiguity is confined
        to overlap with the other tracked role, and some source evidence stays
        visible. This is a generic alternative factorization, not an identity
        threshold relaxation.
        """
        if source is None or other is None or expected_delta is None or other_expected_delta is None:
            return None
        projected, source_status = self._simulate_translation(source, expected_delta)
        projected_other, other_status = self._simulate_translation(other, other_expected_delta)
        if projected is None or projected_other is None:
            return None
        source_cells = set(projected["cells"])
        other_cells = set(projected_other["cells"])
        overlap = source_cells & other_cells
        if not overlap:
            return None
        visible = {
            cell for cell in source_cells
            if int(after[int(cell[0])][int(cell[1])]) == int(source["value"])
        }
        if not visible or any(
            int(after[int(y)][int(x)]) != int(source["value"])
            for y, x in source_cells - overlap
        ):
            return None
        if any(
            int(after[int(y)][int(x)]) not in {int(source["value"]), int(other["value"])}
            for y, x in overlap
        ):
            return None
        evidence = {
            "kind": "predicted-occupancy-with-mutual-occlusion",
            "visible_source_cells": len(visible),
            "occluded_cells": len(source_cells - visible),
            "source_projection": source_status,
            "other_projection": other_status,
        }
        latent = {**projected, "identity_evidence": evidence}
        best = {
            "region": latent, "residual": 0.0,
            "components": {"shape": 0.0, "area": 0.0, "outline": 0.0, "position": 0.0, "value": 0.0},
        }
        return {
            "status": "UNIQUE",
            "reason": "unique-model-supported-successor-through-mutual-occlusion",
            "best_residual": 0.0, "second_residual": 1.0, "margin": 1.0,
            "best": best, "candidates": [best], "identity_evidence": evidence,
        }

    def _role_identity(self, goal_key: str, role: str, region: dict[str, Any]) -> dict[str, Any]:
        trajectory = self.role_trajectories.get(goal_key, {}).get(role)
        if trajectory is None:
            return {"trajectory_id": None, "status": "UNINITIALIZED", "reason": "no-prior-role-trajectory"}
        prior_status = str(trajectory.get("status", "BROKEN"))
        snapshots = list(trajectory.get("candidates", ()))
        if prior_status != "UNIQUE" or len(snapshots) != 1:
            return {
                "trajectory_id": trajectory.get("trajectory_id"),
                "status": prior_status, "reason": trajectory.get("reason", "trajectory-not-unique"),
            }
        residual, components = self._identity_residual(snapshots[0], region)
        status = "UNIQUE" if residual <= ROLE_IDENTITY_MAX_RESIDUAL else "BROKEN"
        return {
            "trajectory_id": trajectory.get("trajectory_id"), "status": status,
            "reason": "matches-persistent-role" if status == "UNIQUE" else "role-continuity-violated",
            "residual": round(residual, 4), "components": components,
        }

    def _desired_delta(
        self, goal: dict[str, Any], actor: dict[str, Any], target: dict[str, Any],
    ) -> dict[str, Any] | None:
        observable = str(goal.get("observable", "unknown"))
        direction = str(goal.get("direction", "unknown"))
        measure = observable
        if str(goal.get("verb", "")) == "fit" and observable == "fit_residual":
            gap = self._measure("boundary_gap", actor, target)
            measure = "boundary_gap" if gap is not None and gap > 0 else "overlap_deficit"
            direction = "decrease"
        current = self._measure(measure, actor, target)
        if current is None or direction not in {"decrease", "increase", "maintain"}:
            return None
        return {
            "measure": measure, "current": float(current), "direction": direction,
            "completion": f"{measure}=0" if direction == "decrease" else f"{measure}:{direction}",
        }

    def _simulate_translation(
        self, region: dict[str, Any], delta: tuple[float, float],
    ) -> tuple[dict[str, Any] | None, str]:
        cells = tuple((y + delta[0], x + delta[1]) for y, x in region["cells"])
        height, width = self.frame_shape
        if any(y < 0 or x < 0 or y >= height or x >= width for y, x in cells):
            return None, "projected-out-of-frame"
        return {
            **region, "cells": cells,
            "center2": (
                float(region["center2"][0]) + 2.0 * delta[0],
                float(region["center2"][1]) + 2.0 * delta[1],
            ),
        }, "computed-translation"

    @staticmethod
    def _measure(observable: str, actor: dict[str, Any], target: dict[str, Any]) -> float | None:
        if observable == "centroid_distance":
            return abs(float(actor["center2"][0]) - float(target["center2"][0])) / 2 + abs(float(actor["center2"][1]) - float(target["center2"][1])) / 2
        if observable == "boundary_gap":
            return max(0.0, min(abs(ay - ty) + abs(ax - tx) for ay, ax in actor["cells"] for ty, tx in target["cells"]) - 1.0)
        actor_cells, target_cells = set(actor["cells"]), set(target["cells"])
        if observable == "overlap_area":
            return float(len(actor_cells & target_cells))
        if observable == "overlap_deficit":
            return float(min(len(actor_cells), len(target_cells)) - len(actor_cells & target_cells))
        if observable == "fit_residual":
            boundary_gap = max(0.0, min(
                abs(ay - ty) + abs(ax - tx)
                for ay, ax in actor_cells for ty, tx in target_cells
            ) - 1.0)
            overlap_deficit = min(len(actor_cells), len(target_cells)) - len(actor_cells & target_cells)
            return float(boundary_gap + overlap_deficit)
        if observable == "containment_violation":
            return float(len(actor_cells - target_cells))
        if observable == "symmetry_residual":
            return float(len(actor_cells ^ target_cells))
        # These observables remain legitimate semantic proposals, but require
        # future measurement adapters. R2 must leave them open, not replace
        # them with an alignment proxy.
        return None

    def _effect(self, action: int, region: dict[str, Any]) -> tuple[tuple[float, float] | None, float]:
        model = self._effect_model(action, region)
        return model["delta"], float(model["confidence"])

    def _effect_model(self, action: int, region: dict[str, Any]) -> dict[str, Any]:
        observations = self.action_effects.get((int(action), self._region_key(region)))
        if not observations:
            return {
                "status": "UNKNOWN", "delta": None, "support": 0,
                "contradictions": 0, "confidence": 0.0,
            }
        delta, count = sorted(observations.items(), key=lambda item: (-item[1], item[0]))[0]
        total = sum(observations.values())
        confidence = count / total
        return {
            "status": "SUPPORTED" if count >= 1 and confidence >= 0.6 else "CONTESTED",
            "delta": delta, "support": int(count), "contradictions": int(total - count),
            "confidence": confidence,
        }

    def _schema0_atom(self, *, support_id: str, support_type: str, output_type: str, evidence_id: str) -> Any:
        assert self.last_store is not None and self.last_workspace is not None
        schema = self.last_store.add(E.Schema.create(
            (E.Port("support", support_type),), (), kind="schema0", output_type=output_type,
        ))
        support = E.GroundSupport(
            support_id, support_type, evidence_id, f"frame:{self.last_digest}",
        )
        return self.last_workspace.bind_schema0(schema, support, port_name="support")

    def _action_atom(self, action: int) -> Any:
        if action in self.last_action_atoms:
            assert self.last_workspace is not None
            return self.last_workspace.atoms[self.last_action_atoms[action]]
        evidence = E.stable_id("available-intervention", {"frame": self.last_digest, "action": int(action)})
        atom = self._schema0_atom(
            support_id=f"action:{int(action)}", support_type="action-support",
            output_type="action-binding", evidence_id=evidence,
        )
        self.last_action_atoms[int(action)] = atom.atom_id
        return atom

    def _materialize_causal_chain(
        self, *, action: int, semantic_goal: dict[str, Any], situated: dict[str, Any],
        predicted: float, progress: float,
    ) -> dict[str, Any]:
        """Fit action effect, preferred completion, progress and explanation schemas."""
        assert self.last_store is not None and self.last_workspace is not None
        verb_atom_id = str(situated["verb_binding_id"])
        before_id = str(situated["potential_binding_id"])
        action_atom = self._action_atom(action)
        successor_evidence = E.stable_id("prospective-potential", {
            "frame": self.last_digest, "action": int(action), "verb": verb_atom_id,
            "value": round(float(predicted), 9),
        })
        successor = self._schema0_atom(
            support_id=successor_evidence,
            support_type="prospective-potential-support",
            output_type="prospective-potential-binding",
            evidence_id=successor_evidence,
        )
        self.last_potential_states[successor.atom_id] = {
            "observable": semantic_goal["observable"], "value": float(predicted),
            "actor": situated["situated_roles"][semantic_goal["potential_roles"][0]],
            "target": situated["situated_roles"][semantic_goal["potential_roles"][1]],
            "situated_roles": dict(situated["situated_roles"]), "prospective": True,
            "action": int(action),
        }

        projection_predicate = "ProjectsPotential"
        causal_schema = self.last_store.add(E.Schema.create(
            (
                E.Port("action", "action-binding"),
                E.Port("before", "potential-binding"),
                E.Port("after", "prospective-potential-binding"),
            ),
            (E.Relation(projection_predicate, ("action", "before", "after")),),
            kind="causal-effect", output_type="causal-effect-binding",
        ))
        projection = self._add_fact(
            projection_predicate,
            (action_atom.atom_id, before_id, successor.atom_id),
            ("action-binding", "potential-binding", "prospective-potential-binding"),
        )
        causal_atom = self._fit_atom(causal_schema, (projection,), assignments={
            "action": action_atom.atom_id, "before": before_id, "after": successor.atom_id,
        })
        if causal_atom is None:
            return {}
        chain: dict[str, Any] = {
            "causal_effect_binding_id": causal_atom.atom_id,
            "successor_potential_binding_id": successor.atom_id,
        }
        if progress <= 0:
            return chain

        preferred = self.last_workspace.bindings[str(situated["preferred_completion_binding_id"])]
        preferred_schema = self.last_store.records[preferred.schema_id].schema
        if preferred.state == E.BindingState.REIFIED:
            completion_atom = self.last_workspace.atoms.get(preferred.binding_id)
            if completion_atom is None:
                completion_atom = self.last_workspace.add_binding_atom(preferred_schema, preferred)
        else:
            completion_predicate = preferred_schema.constraints[0].predicate
            completion_fact = self._add_fact(
                completion_predicate, (verb_atom_id, successor.atom_id),
                ("verb-binding", "prospective-potential-binding"),
            )
            completed = next((
                item for item in E.extend_binding(
                    preferred_schema, preferred, tuple(self.last_workspace.facts.values()), budget=16,
                ) if item.state == E.BindingState.REIFIED
            ), None)
            if completed is None:
                return chain
            completion_atom = self.last_workspace.add_binding_atom(preferred_schema, completed)
            for shadow_id in situated["preferred_completion_shadow_ids"]:
                shadow = self.last_workspace.shadows.get(shadow_id)
                if shadow is not None:
                    self.last_workspace.shadows[shadow_id] = E.settle_shadow(shadow, (completion_fact,))

        advances_predicate = "RealizesPreferredCompletion"
        progress_schema = self.last_store.add(E.Schema.create(
            (
                E.Port("cause", "causal-effect-binding"),
                E.Port("completion", "preferred-completion-binding"),
            ),
            (E.Relation(advances_predicate, ("cause", "completion")),),
            components=(causal_schema.schema_id, preferred_schema.schema_id),
            kind="progress", output_type="progress-binding",
        ))
        advances = self._add_fact(
            advances_predicate, (causal_atom.atom_id, completion_atom.atom_id),
            ("causal-effect-binding", "preferred-completion-binding"),
        )
        progress_atom = self._fit_atom(progress_schema, (advances,), assignments={
            "cause": causal_atom.atom_id, "completion": completion_atom.atom_id,
        })
        if progress_atom is None:
            return chain

        coherent_predicate = "CoherentSituatedExplanation"
        explanation_schema = self.last_store.add(E.Schema.create(
            (
                E.Port("verb", "verb-binding"),
                E.Port("cause", "causal-effect-binding"),
                E.Port("progress", "progress-binding"),
            ),
            (E.Relation(coherent_predicate, ("verb", "cause", "progress")),),
            components=(progress_schema.schema_id,),
            kind="explanation", output_type="explanation-binding",
        ))
        coherent = self._add_fact(
            coherent_predicate, (verb_atom_id, causal_atom.atom_id, progress_atom.atom_id),
            ("verb-binding", "causal-effect-binding", "progress-binding"),
        )
        explanation_atom = self._fit_atom(explanation_schema, (coherent,), assignments={
            "verb": verb_atom_id, "cause": causal_atom.atom_id, "progress": progress_atom.atom_id,
        })
        if explanation_atom is not None:
            chain.update({
                "preferred_completion_binding_id": completion_atom.atom_id,
                "progress_binding_id": progress_atom.atom_id,
                "explanation_binding_id": explanation_atom.atom_id,
            })
        return chain

    def _candidate(
        self, actor: dict[str, Any], target: dict[str, Any], action: int,
        semantic_goal: dict[str, Any], situated: dict[str, Any],
    ) -> dict[str, Any] | None:
        role_grounding = dict(situated.get("role_grounding", {}))
        candidate_binding_id = str(
            situated.get("candidate_binding_id") or role_grounding.get("candidate_binding_id") or ""
        )
        goal_key = self._goal_key(semantic_goal, candidate_binding_id)
        potential_roles = tuple(semantic_goal.get("potential_roles", ("actor", "target")))
        actor_role = potential_roles[0] if len(potential_roles) == 2 else "actor"
        target_role = potential_roles[1] if len(potential_roles) == 2 else "target"
        actor_identity = self._role_identity(goal_key, actor_role, actor)
        target_identity = self._role_identity(goal_key, target_role, target)
        desired = self._desired_delta(semantic_goal, actor, target)
        if desired is None:
            return None
        observable = str(desired["measure"])
        direction = str(desired["direction"])
        residual = float(desired["current"])
        actor_model = self._effect_model(action, actor)
        target_model = self._effect_model(action, target)
        delta = actor_model["delta"]
        target_delta = target_model["delta"]
        predicted = None
        simulation_status = "effect-model-open"
        projected = projected_target = None
        models_supported = actor_model["status"] == "SUPPORTED" and target_model["status"] == "SUPPORTED"
        if models_supported and delta is not None and target_delta is not None:
            projected, actor_simulation = self._simulate_translation(actor, delta)
            projected_target, target_simulation = self._simulate_translation(target, target_delta)
            simulation_status = (
                "computed" if projected is not None and projected_target is not None
                else actor_simulation if projected is None else target_simulation
            )
            if projected is not None and projected_target is not None:
                static_cells = {
                    cell for region in self.last_regions
                    if region["binding_id"] not in {actor["binding_id"], target["binding_id"]}
                    for cell in region["cells"]
                }
                if set(projected["cells"]) & static_cells:
                    simulation_status = "apparently-blocked"
                else:
                    predicted = self._measure(observable, projected, projected_target)
        progress = None if predicted is None else (
            residual - predicted if direction == "decrease" else
            predicted - residual if direction == "increase" else
            -abs(predicted - residual)
        )
        pair = tuple(sorted((actor["binding_id"], target["binding_id"])))
        situated_roles = dict(situated["situated_roles"])
        regions_by_binding = {region["binding_id"]: region for region in self.last_regions}
        role_descriptors = {
            role: {
                "binding_id": binding_id,
                "value": regions_by_binding[binding_id]["value"],
                "area": regions_by_binding[binding_id]["area"],
            }
            for role, binding_id in situated_roles.items()
            if binding_id in regions_by_binding
        }
        verb_binding_id = str(situated["verb_binding_id"])
        assert self.last_workspace is not None
        schema_id = self.last_workspace.bindings[verb_binding_id].schema_id
        chain = {} if predicted is None or progress is None else self._materialize_causal_chain(
            action=int(action), semantic_goal=semantic_goal, situated=situated,
            predicted=float(predicted), progress=float(progress),
        )
        binding_id = str(
            chain.get("explanation_binding_id")
            or chain.get("causal_effect_binding_id")
            or situated["preferred_completion_binding_id"]
        )
        identities_unique = actor_identity["status"] == "UNIQUE" and target_identity["status"] == "UNIQUE"
        active = (
            identities_unique and models_supported and simulation_status == "computed"
            and progress is not None and progress > 0 and "explanation_binding_id" in chain
        )
        return {
            "kind": "situated-control-explanation",
            "epistemic_status": (
                "active-progress-explanation" if active else
                "grounded-predictive" if delta is not None else
                "grounded-open-mechanism"
            ),
            "verb_status": "active" if active else "grounded",
            "schema_id": schema_id, "binding_id": binding_id,
            "ports": {
                "actor": actor["binding_id"], "target": target["binding_id"],
                "situated_roles": situated_roles,
                "situated_role_descriptors": role_descriptors,
                "compatibility": self.last_relation_bindings.get(("SameOutline", pair)),
                "potential": situated["potential_binding_id"],
                "preferred_completion": chain.get("preferred_completion_binding_id", situated["preferred_completion_binding_id"]),
                "causal_effect": chain.get("causal_effect_binding_id"),
                "progress": chain.get("progress_binding_id"),
            },
            "semantic_source": "qwen-goal-proposal",
            "control_goal_key": goal_key,
            "role_grounding": role_grounding,
            # Settlement happens after the observer may already have fitted the
            # successor frame.  Preserve the exact predecessor evidence on the
            # proposal instead of consulting mutable current-frame state.
            "predecessor_binding_snapshots": {
                str(actor["binding_id"]): self._region_snapshot(actor),
                str(target["binding_id"]): self._region_snapshot(target),
            },
            "verb": semantic_goal.get("verb"),
            "proposed_role_constraints": list(semantic_goal.get("role_constraints", ())),
            "prospective_schema_binding_ids": [
                situated["role_binding_id"], situated["potential_binding_id"],
                verb_binding_id, *chain.values(),
            ],
            "prospective_shadow_ids": list(situated["preferred_completion_shadow_ids"]),
            "claim": str(semantic_goal.get("schema_name", "semantic goal proposal")),
            "goal": {
                "family": semantic_goal.get("goal_family"), "measure": observable,
                "current": residual, "direction": direction,
                "terminal": desired["completion"],
                "terminal_class": self._terminal_class(direction),
                "role_constraints": list(semantic_goal.get("role_constraints", ())),
            },
            "desired_delta": dict(desired),
            "identity": {
                actor_role: actor_identity, target_role: target_identity,
                "control_eligible": identities_unique,
            },
            "mechanism": {
                "actor": {**actor_model, "delta": list(delta) if delta is not None else None},
                "target": {**target_model, "delta": list(target_delta) if target_delta is not None else None},
                "models_supported": models_supported,
                "simulation_status": simulation_status,
            },
            "prediction": {
                "action": int(action), "actor_delta": list(delta) if delta is not None else None,
                "target_delta": list(target_delta) if target_delta is not None else None,
                "residual_before": residual, "residual_after": predicted,
                "expected_progress": progress,
                "actor_next_cells_hash": (
                    E.stable_id("predicted-occupancy", projected["cells"]) if projected is not None else None
                ),
                "target_next_cells_hash": (
                    E.stable_id("predicted-occupancy", projected_target["cells"]) if projected_target is not None else None
                ),
            },
            "epistemic_evaluation": {
                "mechanism_confidence": round(min(float(actor_model["confidence"]), float(target_model["confidence"])), 3),
                "confirmations": self.explanation_confirmations[schema_id],
                "refutations": self.explanation_refutations[schema_id],
            },
            "observable_checkpoint": {
                "actor_correspondence": "UNIQUE",
                "target_correspondence": "UNIQUE",
                "measure": observable, "predicted_value": predicted,
            },
            "open_questions": ([] if models_supported else [f"What transformations does action {int(action)} induce for these tracked roles?"]),
        }

    def rank_actions(
        self, legal_actions: Sequence[int], *, fallback_action: int,
        same_frame_no_change: dict[int, int] | None = None,
        semantic_goal: dict[str, Any] | Sequence[dict[str, Any]] | None = None,
        semantic_abductions: Sequence[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Bind explanations and value one action by progress or information."""
        legal = tuple(sorted(set(int(action) for action in legal_actions)))
        no_change = same_frame_no_change or {}
        semantic_goals = (
            [semantic_goal] if isinstance(semantic_goal, dict) else
            list(semantic_goal or ())
        )
        semantic_goals = self._bind_verb_schemas(semantic_goals)
        self._compile_abductions(list(semantic_abductions or ()))
        candidates_by_action: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for action in legal:
            regions_by_binding = {region["binding_id"]: region for region in self.last_regions}
            for goal in semantic_goals:
                potential_roles = tuple(goal.get("potential_roles", ("actor", "target")))
                for situated in goal.get("r2_situated_verb_bindings", ()):
                    if len(potential_roles) != 2:
                        continue
                    role_binding = situated["situated_roles"]
                    actor = regions_by_binding.get(role_binding.get(potential_roles[0]))
                    target = regions_by_binding.get(role_binding.get(potential_roles[1]))
                    candidate = None
                    if actor is not None and target is not None and actor is not target:
                        candidate = self._candidate(actor, target, action, goal, situated)
                    if candidate is not None:
                        candidates_by_action[action].append(candidate)

        # One bounded higher-order categorical pass reifies comparisons among
        # newly created verb, causal, explanation and abductive bindings. It is
        # idempotently limited to once per frame and does not manufacture a
        # temporal transition inside an unchanged frame.
        if self.categorical_augmented_digest != self.last_digest:
            categorical = self._fit_categorical_comparisons(advance_temporal=False)
            self.categorical_augmented_digest = self.last_digest
            if self.last_stats is not None:
                self.last_stats = {**self.last_stats, "categorical": categorical}

        ranked = []
        for action in legal:
            candidates = candidates_by_action[action]
            progress_candidates = [
                item for item in candidates
                if item["prediction"]["expected_progress"] is not None
                and float(item["prediction"]["expected_progress"]) > 0
                and item["identity"]["control_eligible"]
                and item["mechanism"]["models_supported"]
                and item["mechanism"]["simulation_status"] == "computed"
            ]
            probe_candidates = [
                item for item in candidates
                if not item["mechanism"]["models_supported"]
                and all(
                    value.get("status") != "BROKEN"
                    for key, value in item["identity"].items()
                    if key != "control_eligible" and isinstance(value, dict)
                )
            ]
            predictive = [item for item in candidates if item["prediction"]["expected_progress"] is not None]
            best = max(
                progress_candidates,
                key=lambda item: (
                    item["prediction"]["expected_progress"],
                    item["epistemic_evaluation"]["mechanism_confidence"], item["binding_id"],
                ), default=None,
            )
            if best is None and probe_candidates:
                best = min(
                    probe_candidates,
                    key=lambda item: (
                        int(item.get("role_grounding", {}).get(
                            "bounded_rank", ROLE_GROUNDING_TOP_K + 1,
                        )),
                        float(item.get("role_grounding", {}).get(
                            "residual_vector", {},
                        ).get("semantic_clue_residual", 1.0)),
                        item["binding_id"],
                    ),
                )
            if best is None:
                best = max(
                    predictive,
                    key=lambda item: (
                        item["prediction"]["expected_progress"],
                        item["epistemic_evaluation"]["mechanism_confidence"], item["binding_id"],
                    ), default=(candidates[0] if candidates else None),
                )
            raw_progress = None if best is None else best["prediction"]["expected_progress"]
            progress = None if raw_progress is None else float(raw_progress)
            information = 1.0 / (1.0 + self.action_uses[action])
            risk = int(no_change.get(action, 0))
            eligibility = (
                "PROGRESS_ELIGIBLE" if progress_candidates else
                "PROBE_ELIGIBLE" if probe_candidates else
                "INELIGIBLE"
            )
            control_eligible = eligibility == "PROGRESS_ELIGIBLE"
            score = (
                2 if control_eligible else (1 if eligibility == "PROBE_ELIGIBLE" else 0),
                progress if progress is not None else 0.0,
                information,
                -risk,
                1 if action == int(fallback_action) else 0,
                -action,
            )
            ranked.append({
                "action": action, "score_tuple": score, "control_eligible": control_eligible,
                "eligibility": eligibility,
                "role": "goal-progress" if control_eligible else ("discriminating-probe" if eligibility == "PROBE_ELIGIBLE" else "known-nonprogress"),
                "expected_progress": progress, "information_value": round(information, 3), "risk": risk,
                "explanation": best,
            })
        ranked.sort(key=lambda item: item["score_tuple"], reverse=True)
        if not ranked:
            return {"selected_action": int(fallback_action), "top_actions": [], "explanations": [], "current_explanation": None, "control_override": False}
        selected = ranked[0]
        current = selected["explanation"]
        if current is not None:
            current["control_status"] = selected["eligibility"]
        self.pending_prediction = current if selected["eligibility"] != "INELIGIBLE" else None
        explanations = []
        seen = set()
        for item in ranked:
            explanation = item["explanation"]
            if explanation and explanation["binding_id"] not in seen:
                explanations.append(explanation); seen.add(explanation["binding_id"])
        top_actions = [{
            "rank": index, "action": item["action"], "selected": index == 1,
            "role": item["role"], "eligibility": item["eligibility"],
            "expected_progress": item["expected_progress"],
            "information_value": item["information_value"], "risk": item["risk"],
            "explanation_binding_id": item["explanation"]["binding_id"] if item["explanation"] else None,
        } for index, item in enumerate(ranked[:3], start=1)]

        role_hypotheses = []
        seen_role_hypotheses: set[str] = set()
        for candidates in candidates_by_action.values():
            for candidate in candidates:
                grounding = candidate.get("role_grounding", {})
                candidate_id = str(grounding.get("candidate_binding_id", ""))
                if not candidate_id or candidate_id in seen_role_hypotheses:
                    continue
                seen_role_hypotheses.add(candidate_id)
                role_hypotheses.append(dict(grounding))
        role_hypotheses.sort(key=lambda item: (
            int(item.get("bounded_rank", ROLE_GROUNDING_TOP_K + 1)),
            str(item.get("candidate_binding_id", "")),
        ))

        control_proposal = None
        if current is not None:
            control_proposal = {
                "proposal_id": E.stable_id("control-proposal", {
                    "frame": self.last_digest, "action": selected["action"],
                    "explanation": current["binding_id"], "status": selected["eligibility"],
                }),
                "mode": "PROGRESS" if selected["eligibility"] == "PROGRESS_ELIGIBLE" else (
                    "PROBE" if selected["eligibility"] == "PROBE_ELIGIBLE" else "INELIGIBLE"
                ),
                "status": selected["eligibility"],
                "explanation_id": current["binding_id"],
                "roles": dict(current["identity"]),
                "role_grounding": dict(current.get("role_grounding", {})),
                "competing_role_hypotheses": role_hypotheses[:ROLE_GROUNDING_TOP_K],
                "desired_delta": dict(current["desired_delta"]),
                "action": int(selected["action"]),
                "mechanism": dict(current["mechanism"]),
                "prediction": dict(current["prediction"]),
                "observable_checkpoint": dict(current["observable_checkpoint"]),
                "invalidation_conditions": [
                    "actor correspondence is not UNIQUE",
                    "target correspondence is not UNIQUE",
                    "observed transformation differs from prediction",
                    "observed potential differs from prediction",
                ],
            }
        self.last_control_proposal = control_proposal

        self._refresh_recursive_stats()
        return {
            "selected_action": selected["action"], "top_actions": top_actions,
            "explanations": explanations[:8], "current_explanation": current,
            "control_override": bool(selected["control_eligible"]),
            "execution_authorized": selected["eligibility"] != "INELIGIBLE",
            "control_proposal": control_proposal,
            "identity_assessments": list(self.last_identity_assessments)[-8:],
            "role_hypotheses": role_hypotheses[:ROLE_GROUNDING_TOP_K],
            "rejected_goal_proposals": list(self.last_rejected_goals),
            "grounded_abductions": list(self.last_abductive_bindings),
            "rejected_abductions": list(self.last_rejected_abductions),
            "selection_rule": "hard gates: PROGRESS_ELIGIBLE > PROBE_ELIGIBLE > INELIGIBLE; then desired delta, least-used probe, no-change risk, stable action",
        }

    def rank_authorized_policy(
        self,
        legal_actions: Sequence[int],
        *,
        authorization: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Evaluate an authorized policy from grounded effects without refitting.

        This is state-conditioned and action-agnostic: every legal action with
        an applicable supported effect is simulated, and the action producing
        the greatest strictly preferred successor is selected.  Returning
        ``None`` revokes the fast path and forces ordinary deliberation.
        """
        state = self.fast_policy_state
        if not state or authorization.get("status") != "AUTHORIZED":
            return None
        template = deepcopy(state["template"])
        actor = deepcopy(state["actor"])
        target = deepcopy(state["target"])
        goal = dict(template.get("goal", {}))
        observable = str(goal.get("measure", ""))
        direction = str(goal.get("direction", ""))
        current = self._measure(observable, actor, target)
        if current is None or direction not in {"decrease", "increase", "maintain"}:
            return None
        threshold = float(authorization.get("confidence", 1.0))
        candidates: list[dict[str, Any]] = []
        for action in sorted(set(int(item) for item in legal_actions)):
            actor_model = self._effect_model(action, actor)
            target_model = self._effect_model(action, target)
            actor_delta = actor_model.get("delta")
            target_delta = target_model.get("delta")
            confidence = min(float(actor_model["confidence"]), float(target_model["confidence"]))
            if actor_delta is None or target_delta is None or confidence < min(0.8, threshold):
                continue
            projected_actor, actor_status = self._simulate_translation(actor, actor_delta)
            projected_target, target_status = self._simulate_translation(target, target_delta)
            if projected_actor is None or projected_target is None:
                continue
            predicted = self._measure(observable, projected_actor, projected_target)
            if predicted is None:
                continue
            improvement = (
                float(current) - float(predicted) if direction == "decrease" else
                float(predicted) - float(current) if direction == "increase" else
                -abs(float(predicted) - float(current))
            )
            if improvement <= 0:
                continue
            candidates.append({
                "action": action,
                "progress": improvement,
                "predicted": float(predicted),
                "confidence": confidence,
                "actor_delta": tuple(actor_delta),
                "target_delta": tuple(target_delta),
                "actor_model": actor_model,
                "target_model": target_model,
                "simulation_status": f"{actor_status}+{target_status}",
            })
        if not candidates:
            return None
        selected = max(candidates, key=lambda item: (
            item["progress"], item["confidence"], -item["action"],
        ))
        ports = dict(template.get("ports", {}))
        actor_binding = str(ports.get("actor"))
        target_binding = str(ports.get("target"))
        template["binding_id"] = E.stable_id("fast-policy-explanation", {
            "authorization": authorization.get("signature"),
            "actor": actor.get("cells"),
            "target": target.get("cells"),
            "action": selected["action"],
        })
        template["predecessor_binding_snapshots"] = {
            actor_binding: self._region_snapshot(actor),
            target_binding: self._region_snapshot(target),
        }
        template["goal"] = {**goal, "current": float(current)}
        template["desired_delta"] = {
            **dict(template.get("desired_delta", {})), "current": float(current),
        }
        template["mechanism"] = {
            "actor": {**selected["actor_model"], "delta": list(selected["actor_delta"])},
            "target": {**selected["target_model"], "delta": list(selected["target_delta"])},
            "models_supported": True,
            "simulation_status": "computed",
        }
        template["prediction"] = {
            "action": selected["action"],
            "actor_delta": list(selected["actor_delta"]),
            "target_delta": list(selected["target_delta"]),
            "residual_before": float(current),
            "residual_after": selected["predicted"],
            "expected_progress": float(selected["progress"]),
            "actor_next_cells_hash": None,
            "target_next_cells_hash": None,
        }
        template["epistemic_evaluation"] = {
            **dict(template.get("epistemic_evaluation", {})),
            "mechanism_confidence": round(float(selected["confidence"]), 3),
        }
        template["observable_checkpoint"] = {
            "actor_correspondence": "UNIQUE",
            "target_correspondence": "UNIQUE",
            "measure": observable,
            "predicted_value": selected["predicted"],
        }
        template["control_status"] = "PROGRESS_ELIGIBLE"
        template["epistemic_status"] = "authorized-preferred-policy"
        self.pending_prediction = template
        top_actions = [{
            "rank": index,
            "action": item["action"],
            "selected": index == 1,
            "role": "authorized-policy",
            "eligibility": "PROGRESS_ELIGIBLE",
            "expected_progress": item["progress"],
            "information_value": 0.0,
            "risk": 0,
            "explanation_binding_id": template["binding_id"] if index == 1 else None,
        } for index, item in enumerate(sorted(
            candidates,
            key=lambda item: (-item["progress"], -item["confidence"], item["action"]),
        )[:3], start=1)]
        self.last_control_proposal = {
            "proposal_id": E.stable_id("fast-policy-proposal", {
                "explanation": template["binding_id"], "action": selected["action"],
            }),
            "mode": "FAST_PATH",
            "status": "PROGRESS_ELIGIBLE",
            "action": selected["action"],
            "prediction": dict(template["prediction"]),
            "invalidation_conditions": [
                "prediction mismatch", "protected invariant violation",
                "identity ambiguity", "successor not strictly preferred",
                "policy applicability changed", "unexpected environment event",
            ],
        }
        return {
            "selected_action": selected["action"],
            "top_actions": top_actions,
            "explanations": [template],
            "current_explanation": template,
            "control_override": True,
            "execution_authorized": True,
            "control_proposal": self.last_control_proposal,
            "selection_rule": "authorized state-conditioned evaluator; greatest strictly preferred grounded successor",
        }

    def settle_action(self, action: int, before: Sequence[Sequence[int]], after: Sequence[Sequence[int]]) -> dict[str, Any]:
        """Settle identity before attributing a mechanism to controlling roles."""
        after_regions = _components(after)
        self.action_uses[int(action)] += 1
        prediction = (
            self.pending_prediction
            if self.pending_prediction and self.pending_prediction["prediction"]["action"] == int(action)
            else None
        )
        learned: list[dict[str, Any]] = []
        adjudication = "untested-open-mechanism"
        actual_progress = None
        identity_settlement: dict[str, Any] = {
            "status": "UNSETTLED", "roles": {}, "reason": "no-control-prediction",
        }
        mechanism_settlement: dict[str, Any] = {
            "status": "UNSETTLED", "predicted": None, "observed": None,
        }
        potential_settlement: dict[str, Any] = {
            "status": "UNSETTLED", "expected": None, "observed": None,
        }

        if prediction is not None:
            goal_key = str(prediction.get("control_goal_key") or "")
            predecessor_snapshots = dict(prediction.get("predecessor_binding_snapshots", {}))
            situated_roles = dict(prediction.get("ports", {}).get("situated_roles", {}))
            actor_binding = prediction.get("ports", {}).get("actor")
            target_binding = prediction.get("ports", {}).get("target")
            expected_actor = prediction.get("prediction", {}).get("actor_delta")
            expected_target = prediction.get("prediction", {}).get("target_delta")
            expected_by_binding = {
                actor_binding: tuple(float(value) for value in expected_actor) if expected_actor is not None else None,
                target_binding: tuple(float(value) for value in expected_target) if expected_target is not None else None,
            }
            used: set[int] = set()
            matched_by_binding: dict[str, dict[str, Any]] = {}
            role_results: dict[str, Any] = {}
            trajectory_bucket = self.role_trajectories.setdefault(goal_key, {})

            for role, binding_id in situated_roles.items():
                if binding_id not in {actor_binding, target_binding}:
                    continue
                source = predecessor_snapshots.get(str(binding_id))
                if source is None:  # Backward compatibility for old playbacks.
                    source = next(
                        (region for region in self.last_regions if region["binding_id"] == binding_id),
                        None,
                    )
                available = [region for index, region in enumerate(after_regions) if index not in used]
                correspondence = self._correspondence(
                    source, available, expected_delta=expected_by_binding.get(binding_id),
                )
                other_binding = target_binding if binding_id == actor_binding else actor_binding
                other_source = predecessor_snapshots.get(str(other_binding))
                occlusion_fit = self._occlusion_correspondence(
                    source, other_source, after,
                    expected_delta=expected_by_binding.get(binding_id),
                    other_expected_delta=expected_by_binding.get(other_binding),
                )
                if occlusion_fit is not None:
                    correspondence = occlusion_fit
                best = correspondence.get("best")
                successor = best.get("region") if isinstance(best, dict) else None
                if successor is not None:
                    global_index = next((
                        index for index, region in enumerate(after_regions)
                        if index not in used and region is successor
                    ), None)
                    if correspondence["status"] == "UNIQUE" and global_index is not None:
                        used.add(global_index)
                    matched_by_binding[str(binding_id)] = successor
                existing = trajectory_bucket.get(role, {})
                trajectory_id = existing.get("trajectory_id") or E.stable_id(
                    "role-trajectory", {"goal": goal_key, "role": role, "origin": binding_id},
                )
                candidate_snapshots = [
                    self._region_snapshot(item["region"])
                    for item in correspondence.get("candidates", ())
                    if isinstance(item, dict) and item.get("region") is not None
                ]
                if correspondence["status"] == "UNIQUE":
                    candidate_snapshots = candidate_snapshots[:1]
                trajectory_bucket[role] = {
                    "trajectory_id": trajectory_id,
                    "status": correspondence["status"], "reason": correspondence.get("reason"),
                    "candidates": candidate_snapshots,
                    "source_area": source.get("area") if source else None,
                    "turn_action": int(action),
                }
                role_result = {
                    "trajectory_id": trajectory_id,
                    "status": correspondence["status"], "reason": correspondence.get("reason"),
                    "best_residual": correspondence.get("best_residual"),
                    "second_residual": correspondence.get("second_residual"),
                    "margin": correspondence.get("margin"),
                    "identity_evidence": correspondence.get("identity_evidence"),
                    "source_area": source.get("area") if source else None,
                    "successor_area": successor.get("area") if successor else None,
                }
                role_results[role] = role_result
                self.last_identity_assessments.append({
                    "goal_key": goal_key, "role": role, **role_result,
                })
                self.last_identity_assessments = self.last_identity_assessments[-64:]

                # A changed component becomes a causal observation only when
                # it is the unique successor of a controlling role.
                if source is not None and successor is not None and correspondence["status"] == "UNIQUE":
                    delta = (
                        (float(successor["center2"][0]) - float(source["center2"][0])) / 2.0,
                        (float(successor["center2"][1]) - float(source["center2"][1])) / 2.0,
                    )
                    self.action_effects[(int(action), self._region_key(source))][delta] += 1
                    learned.append({
                        "trajectory_id": trajectory_id, "role": role,
                        "region_type": E.stable_id("region-type", self._region_key(source)),
                        "delta": list(delta), "support_kind": "unique-role-correspondence",
                    })

            statuses = [item["status"] for item in role_results.values()]
            identity_status = (
                "UNIQUE" if statuses and all(status == "UNIQUE" for status in statuses) else
                "BROKEN" if any(status == "BROKEN" for status in statuses) else
                "AMBIGUOUS"
            )
            identity_settlement = {
                "status": identity_status, "roles": role_results,
                "reason": "all-required-roles-unique" if identity_status == "UNIQUE" else "role-continuity-not-unique",
            }

            # When both roles are supported only as mutually occluding latent
            # occupancies, install that exact factorization in the already
            # fitted successor workspace.  The raw connected components remain
            # evidence atoms, but are removed from the role-candidate cut so a
            # visible fragment cannot replace the tracked whole next turn.
            controlling_bindings = tuple(str(item) for item in (actor_binding, target_binding))
            latent_successors = {
                binding_id: matched_by_binding.get(binding_id)
                for binding_id in controlling_bindings
            }
            if (
                identity_status == "UNIQUE"
                and all(
                    isinstance(region, dict) and region.get("identity_evidence", {}).get("kind")
                    == "predicted-occupancy-with-mutual-occlusion"
                    for region in latent_successors.values()
                )
            ):
                latent_cells = set().union(*(
                    set(region["cells"]) for region in latent_successors.values()
                ))
                tracked_values = {int(region["value"]) for region in latent_successors.values()}
                retained_regions = [
                    region for region in self.last_regions
                    if not (
                        int(region["value"]) in tracked_values
                        and set(region["cells"])
                        and set(region["cells"]).issubset(latent_cells)
                    )
                ]
                installed = []
                for predecessor_id, region in latent_successors.items():
                    evidence_id = E.stable_id("latent-role-occupancy", {
                        "frame": self.last_digest,
                        "predecessor": predecessor_id,
                        "cells": region["cells"],
                        "value": region["value"],
                    })
                    atom = self._schema0_atom(
                        support_id=f"latent-role:{goal_key}:{predecessor_id}",
                        support_type="region-support", output_type="region-binding",
                        evidence_id=evidence_id,
                    )
                    materialized = {
                        **region, "binding_id": atom.atom_id,
                        "factorization": "model-supported-mutual-occlusion",
                    }
                    installed.append(materialized)
                    matched_by_binding[predecessor_id] = materialized
                    self.last_region_descriptors[materialized["binding_id"]] = materialized
                self.last_regions = [*retained_regions, *installed]
                self.last_atom_ids = tuple([*self.last_atom_ids, *(item["binding_id"] for item in installed)])
                identity_settlement["factorization"] = {
                    "status": "INSTALLED",
                    "kind": "model-supported-mutual-occlusion",
                    "latent_roles": len(installed),
                }
                self._refresh_recursive_stats()

            actor_before = predecessor_snapshots.get(str(actor_binding))
            target_before = predecessor_snapshots.get(str(target_binding))
            if actor_before is None:  # Backward compatibility for old playbacks.
                actor_before = next(
                    (region for region in self.last_regions if region["binding_id"] == actor_binding), None,
                )
            if target_before is None:
                target_before = next(
                    (region for region in self.last_regions if region["binding_id"] == target_binding), None,
                )
            actor_after = matched_by_binding.get(str(actor_binding))
            target_after = matched_by_binding.get(str(target_binding))
            expected = prediction.get("prediction", {}).get("expected_progress")
            predicted_value = prediction.get("prediction", {}).get("residual_after")
            if identity_status != "UNIQUE":
                adjudication = "identity-broken" if identity_status == "BROKEN" else "identity-ambiguous"
                mechanism_settlement["status"] = "UNSETTLED"
            elif actor_before and target_before and actor_after and target_after:
                observable = str(prediction["goal"]["measure"])
                direction = str(prediction["goal"]["direction"])
                before_value = self._measure(observable, actor_before, target_before)
                after_value = self._measure(observable, actor_after, target_after)
                if before_value is None or after_value is None:
                    adjudication = "unmeasurable"
                else:
                    actual_progress = (
                        before_value - after_value if direction == "decrease" else
                        after_value - before_value if direction == "increase" else
                        -abs(after_value - before_value)
                    )
                    potential_settlement = {
                        "status": "OBSERVED", "measure": observable,
                        "expected": predicted_value, "observed": float(after_value),
                        "before": float(before_value), "actual_progress": float(actual_progress),
                    }
                    observed_actor_delta = next(
                        (item["delta"] for item in learned if item["role"] in role_results and situated_roles.get(item["role"]) == actor_binding),
                        None,
                    )
                    mechanism_settlement = {
                        "status": "OBSERVED" if expected is None else "CONFIRMED" if abs(float(expected) - actual_progress) <= 0.01 else "REFUTED",
                        "predicted": expected_actor, "observed": observed_actor_delta,
                    }
                    if expected is None:
                        adjudication = "mechanism-observed"
                    elif abs(float(expected) - actual_progress) <= 0.01:
                        adjudication = "confirmed"
                        self.explanation_confirmations[prediction["schema_id"]] += 1
                    else:
                        adjudication = "refuted"
                        self.explanation_refutations[prediction["schema_id"]] += 1

        self.pending_prediction = None
        settlement = {
            "proposal_id": (self.last_control_proposal or {}).get("proposal_id"),
            "explanation_binding_id": prediction["binding_id"] if prediction else None,
            "adjudication": adjudication, "actual_progress": actual_progress,
            "identity": identity_settlement, "mechanism": mechanism_settlement,
            "potential": potential_settlement, "learned_effects": learned,
            "preferred_order": {
                "advanced": actual_progress is not None and float(actual_progress) > 0.0,
                "relation": (
                    "strictly-preferred" if actual_progress is not None and float(actual_progress) > 0.0 else
                    "equivalent" if actual_progress is not None and float(actual_progress) == 0.0 else
                    "not-preferred"
                ),
            },
            "protected_invariants": {
                "hold": (
                    identity_settlement.get("status") == "UNIQUE"
                    and mechanism_settlement.get("status") != "REFUTED"
                    and potential_settlement.get("status") == "OBSERVED"
                ),
                "identity": identity_settlement.get("status"),
                "mechanism": mechanism_settlement.get("status"),
                "potential": potential_settlement.get("status"),
            },
        }
        if prediction is not None and actor_after is not None and target_after is not None:
            self.fast_policy_state = {
                "template": deepcopy(prediction),
                "actor": self._region_snapshot(actor_after),
                "target": self._region_snapshot(target_after),
            }
        else:
            self.fast_policy_state = None
        self.last_control_settlement = settlement
        return settlement

    def commit_prediction(self, action: int, explanation: dict[str, Any] | None) -> None:
        """Mark the definitive externally executed prediction.

        Planning may be invoked for internal counterfactuals. The runtime calls
        this only at the real action boundary, preventing those deliberative
        plans from overwriting the prediction that must be settled.
        """
        if (
            explanation
            and explanation.get("control_status") != "INELIGIBLE"
            and int(explanation.get("prediction", {}).get("action", -1)) == int(action)
        ):
            self.pending_prediction = explanation
