"""Native proposal-grounding-evidence-revision control for Reflector-II.

This is the executable bridge between heterogeneous semantic workers and the
native R2 schema runtime.  Proposals are compiled into the authoritative
``SchemaGraph``; R2 grounds them with its normal matcher; predictions and
environment outcomes live in the shared epistemic workspace; and only a
prospectively confirmed nontrivial revision can override a fallback action.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .epistemic_workspace import (
    EpistemicObject,
    EpistemicWorkspaceError,
    SharedEpistemicWorkspace,
    content_hash,
)
from .perception import PerceptionBatch
from .runtime import Binding, GroundingResult, Runtime
from .store import SourceAtom


OPERATORS = frozenset({"Decrease", "Increase"})


class SharedCognitionError(ValueError):
    """A semantic write or causal control transition is invalid."""


@dataclass(frozen=True, slots=True)
class SemanticSchemaProposal:
    name: str
    conditions: tuple[SourceAtom, ...]
    operator: str
    measure: str
    effect_variables: tuple[int, int]
    basis_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.operator not in OPERATORS:
            raise SharedCognitionError(f"unsupported consequence operator: {self.operator}")
        if not self.name or not self.measure:
            raise SharedCognitionError("proposal name and measure must be non-empty")
        if not 1 <= len(self.conditions) <= 16:
            raise SharedCognitionError("proposal conditions must contain 1..16 atoms")
        if len(set(self.effect_variables)) != 2 or min(self.effect_variables) < 0:
            raise SharedCognitionError("effect variables must be two distinct ordinals")


@dataclass(frozen=True, slots=True)
class GroundedProposal:
    hypothesis_id: str
    derivation_id: str
    native_schema_id: int
    native_schema_hash: str
    binding_ids: tuple[str, ...]
    effect_pairs: tuple[tuple[object, object], ...]
    complete: bool
    status: str
    criticism_id: str | None


@dataclass(frozen=True, slots=True)
class PredictionCommitment:
    prediction_id: str
    proposal_id: str
    binding_id: str
    intervention_ref: str
    current_residual: int
    predicted_delta: int
    predicted_residual: int


@dataclass(frozen=True, slots=True)
class EvidenceReturn:
    evidence_object_id: str
    prediction_id: str
    verdict: str
    criticism_id: str


@dataclass(frozen=True, slots=True)
class CausalControlDecision:
    decision_id: str
    selected_intervention: str
    fallback_intervention: str
    binding_id: str
    prediction_id: str
    hypothesis_id: str
    changed: bool


class NativeSharedCognition:
    """One native R2 runtime and one shared epistemic world."""

    def __init__(
        self,
        runtime: Runtime,
        epistemic: SharedEpistemicWorkspace | None = None,
    ) -> None:
        self.runtime = runtime
        self.epistemic = epistemic or SharedEpistemicWorkspace()
        self.observed: PerceptionBatch | None = None
        self.observation_object_id: str | None = None
        self._hypothesis_native_schema: dict[str, int] = {}

    def observe(self, batch: PerceptionBatch, *, already_observed: bool = False) -> str:
        """Install the current native observation and expose it to both workers."""

        if not already_observed:
            self.runtime.observe(batch)
        elif self.runtime.workspace is None or self.runtime.workspace.context != batch.context:
            raise SharedCognitionError("already-observed batch is not the native current workspace")
        self.observed = batch
        facts = [
            [
                self.runtime.graph.terms.value(head),
                [self.runtime.graph.terms.value(argument) for argument in arguments],
            ]
            for head, arguments in batch.facts
        ]
        cognitive_facts = [
            fact
            for fact in facts
            if fact[0] not in {"At", "Value", "PartOf"}
            and not any(str(argument).startswith("cell:") for argument in fact[1])
        ]
        observation = self.epistemic.add_object(
            kind="observation",
            semantic_key={"context": batch.context, "facts_digest": content_hash(facts)},
            payload={
                "context": batch.context,
                "source": batch.source,
                "fact_count": len(facts),
                "full_fact_digest": content_hash(facts),
                "projection_fidelity": (
                    "exact-object-relations; cell-facts-in-native-runtime"
                ),
                "facts": cognitive_facts,
            },
            creator="environment",
        )
        self.observation_object_id = observation.object_id
        self.epistemic.ingest_native_runtime(self.runtime)
        self.epistemic.attend(
            worker="qwen",
            object_id=observation.object_id,
            weight=200,
            channel="current-reality",
            nonce={"native_cycle": self.runtime.cycle},
        )
        return observation.object_id

    def _require_observation(self) -> PerceptionBatch:
        if self.observed is None or self.observation_object_id is None:
            raise SharedCognitionError("no current observation is installed")
        return self.observed

    def _native_schema_reference(self, schema_id: int) -> EpistemicObject:
        graph = self.runtime.graph
        schema_hash = graph.canonical_hash[schema_id]
        return self.epistemic.add_object(
            kind="native-schema-reference",
            semantic_key={"native_schema_hash": schema_hash},
            payload={
                "native_schema_hash": schema_hash,
                "display_name": graph.display_name[schema_id],
                "depth": graph.depth[schema_id],
            },
            creator="kernel",
        )

    def _assignment_values(self, binding: Binding) -> dict[int, object]:
        terms = self.runtime.graph.terms
        return {
            ordinal: terms.value(term_id) for ordinal, term_id in binding.assignments
        }

    def grounding_diagnostics(self) -> dict[str, object]:
        """Describe the complete current binary-relation grounding field.

        This is a lossless semantic projection of the current native R2
        observation, not a heuristic recommendation.  It lets a semantic
        worker see which predicates retain zero, one, or several unordered
        effect pairs without guessing from a bounded candidate sample.
        """

        self._require_observation()
        observation = self.epistemic.object(str(self.observation_object_id))
        by_predicate: dict[str, set[tuple[str, str]]] = {}
        for raw in observation.payload.get("facts", ()):
            if not isinstance(raw, list) or len(raw) != 2:
                continue
            predicate, arguments = raw
            if not isinstance(arguments, list) or len(arguments) != 2:
                continue
            left, right = (str(value) for value in arguments)
            if left == right:
                continue
            pair = tuple(sorted((left, right)))
            by_predicate.setdefault(str(predicate), set()).add(pair)
        rows = []
        for predicate, values in sorted(by_predicate.items()):
            pairs = [list(value) for value in sorted(values)]
            rows.append(
                {
                    "predicate": predicate,
                    "retained_effect_pairs": pairs,
                    "retained_pair_count": len(pairs),
                    "classification": (
                        "empty" if not pairs else "unique" if len(pairs) == 1 else "ambiguous"
                    ),
                    "unique_pair": pairs[0] if len(pairs) == 1 else None,
                }
            )
        return {
            "protocol": "native-r2-complete-grounding-diagnostics-v1",
            "observation_id": self.observation_object_id,
            "population_complete": True,
            "relations_truncated": False,
            "predicate_rows": rows,
            "unique_predicates": [
                row["predicate"] for row in rows if row["classification"] == "unique"
            ],
        }

    @staticmethod
    def _effect_pairs(
        result: GroundingResult, effect_variables: tuple[int, int], values: Sequence[dict[int, object]]
    ) -> tuple[tuple[object, object], ...]:
        if not result.complete:
            return ()
        pairs = {
            tuple(sorted((item[effect_variables[0]], item[effect_variables[1]]), key=repr))
            for item in values
            if effect_variables[0] in item and effect_variables[1] in item
        }
        return tuple(sorted(pairs, key=repr))

    def propose(
        self,
        proposal: SemanticSchemaProposal,
        *,
        response_id: str,
        revises_id: str | None = None,
        criticism_id: str | None = None,
    ) -> GroundedProposal:
        """Compile a semantic worker proposal and ground it with native R2."""

        observed = self._require_observation()
        if any(item not in {value.object_id for value in self.epistemic.objects} for item in proposal.basis_ids):
            raise SharedCognitionError("proposal cites an absent epistemic basis")
        lineage: list[str] = list(proposal.basis_ids)
        if revises_id is not None:
            prior = self.epistemic.object(revises_id)
            if prior.kind != "semantic-schema":
                raise SharedCognitionError("revision target is not a semantic schema")
            lineage.append(revises_id)
            if criticism_id is None:
                raise SharedCognitionError("a revision must cite structured criticism")
        if criticism_id is not None:
            criticism = self.epistemic.object(criticism_id)
            if criticism.kind != "structured-criticism":
                raise SharedCognitionError("criticism reference has the wrong kind")
            lineage.append(criticism_id)

        schema_id, _created = self.runtime.graph.add_schema(
            proposal.name,
            proposal.conditions,
            provenance="worker:qwen",
            candidate=True,
        )
        schema_hash = self.runtime.graph.canonical_hash[schema_id]
        native_reference = self._native_schema_reference(schema_id)
        lineage.append(native_reference.object_id)
        semantic_body = {
            "native_schema_hash": schema_hash,
            "operator": proposal.operator,
            "measure": proposal.measure,
            "effect_variables": list(proposal.effect_variables),
        }
        if revises_id is not None:
            prior = self.epistemic.object(revises_id)
            prior_body = dict(prior.semantic_key)
            prior_body.pop("revision_of", None)
            if prior_body == semantic_body:
                raise SharedCognitionError(
                    "alpha-identical revision is not a semantic revision"
                )
        semantic_key = {**semantic_body, "revision_of": revises_id}
        hypothesis = self.epistemic.add_object(
            kind="semantic-schema",
            semantic_key=semantic_key,
            payload={
                **semantic_key,
                "conditions": [[head, list(arguments)] for head, arguments in proposal.conditions],
                "revision_of": revises_id,
            },
            creator="qwen",
            # Basis/provenance are properties of a derivation, not of stable
            # semantic identity. This lets repeated proposals reuse one
            # semantic object without either collision or fabricated novelty.
            dependency_ids=(native_reference.object_id,),
        )
        derivation = self.epistemic.add_object(
            kind="derivation",
            semantic_key={
                "response_id": response_id,
                "hypothesis_id": hypothesis.object_id,
            },
            payload={"response_id": response_id, "hypothesis_id": hypothesis.object_id},
            creator="qwen",
            dependency_ids=tuple(dict.fromkeys((*lineage, hypothesis.object_id))),
        )
        self._hypothesis_native_schema[hypothesis.object_id] = schema_id
        self.epistemic.attend(
            worker="r2",
            object_id=hypothesis.object_id,
            weight=500,
            channel="semantic-proposal",
            basis_ids=(derivation.object_id,),
            nonce=response_id,
        )

        grounding = self.runtime.ground_schema(schema_id, observed, provenance="worker:qwen")
        values = [self._assignment_values(item) for item in grounding.bindings]
        effect_pairs = self._effect_pairs(grounding, proposal.effect_variables, values)
        status = (
            "unbound"
            if not values
            else "incomplete"
            if not grounding.complete
            else "bound"
            if len(effect_pairs) == 1
            else "ambiguous"
        )
        binding_ids: list[str] = []
        for binding, assignments in zip(grounding.bindings, values, strict=True):
            effect_pair = None
            if all(variable in assignments for variable in proposal.effect_variables):
                effect_pair = sorted(
                    (assignments[proposal.effect_variables[0]], assignments[proposal.effect_variables[1]]),
                    key=repr,
                )
            binding = self.epistemic.add_object(
                kind="binding",
                semantic_key={
                    "hypothesis_id": hypothesis.object_id,
                    "carrier": grounding.carrier,
                    "assignments": sorted(assignments.items()),
                },
                payload={
                    "status": status,
                    "carrier": grounding.carrier,
                    "assignments": sorted(assignments.items()),
                    "effect_pair": effect_pair,
                    "population_complete": grounding.complete,
                    "competition_set_id": hypothesis.object_id,
                },
                creator="r2",
                dependency_ids=(hypothesis.object_id, native_reference.object_id),
            )
            binding_ids.append(binding.object_id)

        criticism_object_id: str | None = None
        if status != "bound":
            diagnostics = self.grounding_diagnostics()
            criticism = self.epistemic.add_object(
                kind="structured-criticism",
                semantic_key={
                    "target": hypothesis.object_id,
                    "derivation": derivation.object_id,
                    "status": status,
                    "effect_pairs": effect_pairs,
                },
                payload={
                    "target": hypothesis.object_id,
                    "derivation": derivation.object_id,
                    "status": status,
                    "grounding_count": len(values),
                    "effect_pairs": effect_pairs,
                    "population_complete": grounding.complete,
                    "grounding_diagnostics": diagnostics,
                    "instruction": (
                        "Revise the exact target with alpha-novel relational conditions. "
                        "A control revision is mechanically admissible only when the "
                        "complete current grounding retains exactly one unordered effect pair."
                    ),
                },
                creator="r2",
                dependency_ids=tuple(
                    dict.fromkeys(
                        (derivation.object_id, hypothesis.object_id, *binding_ids)
                    )
                ),
            )
            criticism_object_id = criticism.object_id
            self.epistemic.attend(
                worker="qwen",
                object_id=criticism.object_id,
                weight=700,
                channel="r2-criticism",
                basis_ids=(hypothesis.object_id,),
                nonce=response_id,
            )
        return GroundedProposal(
            hypothesis_id=hypothesis.object_id,
            derivation_id=derivation.object_id,
            native_schema_id=schema_id,
            native_schema_hash=schema_hash,
            binding_ids=tuple(binding_ids),
            effect_pairs=effect_pairs,
            complete=grounding.complete,
            status=status,
            criticism_id=criticism_object_id,
        )

    def predict(
        self,
        *,
        binding_id: str,
        intervention_ref: str,
        current_residual: int,
        predicted_delta: int,
        basis_revision: int,
    ) -> PredictionCommitment:
        binding = self.epistemic.object(binding_id)
        if binding.kind != "binding":
            raise SharedCognitionError("prediction target is not a binding")
        hypothesis_id = next(
            (
                item
                for item in binding.dependency_ids
                if self.epistemic.object(item).kind == "semantic-schema"
            ),
            None,
        )
        if hypothesis_id is None:
            raise SharedCognitionError("binding has no semantic hypothesis dependency")
        hypothesis = self.epistemic.object(hypothesis_id)
        # A probe prediction describes an opaque intervention's expected
        # consequence, including neutral or operator-opposing outcomes that
        # discriminate alternatives.  The hypothesis operator is enforced
        # later when confirmed predictions are ranked for control.
        prediction = self.epistemic.add_object(
            kind="prediction",
            semantic_key={
                "binding_id": binding_id,
                "intervention_ref": intervention_ref,
                "basis_revision": basis_revision,
                "current_residual": current_residual,
                "predicted_delta": predicted_delta,
            },
            payload={
                "binding_id": binding_id,
                "intervention_ref": intervention_ref,
                "basis_revision": basis_revision,
                "current_residual": current_residual,
                "predicted_delta": predicted_delta,
                "predicted_residual": current_residual + predicted_delta,
                "horizon": 1,
            },
            creator="r2",
            dependency_ids=(binding_id, hypothesis_id),
        )
        proposal = self.epistemic.add_object(
            kind="action-proposal",
            semantic_key={"prediction_id": prediction.object_id},
            payload={
                "prediction_id": prediction.object_id,
                "intervention_ref": intervention_ref,
            },
            creator="r2",
            dependency_ids=(prediction.object_id, binding_id),
        )
        return PredictionCommitment(
            prediction_id=prediction.object_id,
            proposal_id=proposal.object_id,
            binding_id=binding_id,
            intervention_ref=intervention_ref,
            current_residual=current_residual,
            predicted_delta=predicted_delta,
            predicted_residual=current_residual + predicted_delta,
        )

    def adjudicate(
        self,
        commitment: PredictionCommitment,
        *,
        transition_id: str,
        observed_delta: int | None,
        direct: bool,
    ) -> EvidenceReturn:
        prediction = self.epistemic.object(commitment.prediction_id)
        if prediction.kind != "prediction":
            raise SharedCognitionError("commitment does not name a prediction")
        if not direct or observed_delta is None:
            verdict = "unresolved"
        elif observed_delta == commitment.predicted_delta:
            verdict = "supports"
        else:
            verdict = "refutes"
        evidence_object = self.epistemic.add_object(
            kind="environment-evidence",
            semantic_key={
                "prediction_id": commitment.prediction_id,
                "transition_id": transition_id,
            },
            payload={
                "prediction_id": commitment.prediction_id,
                "transition_id": transition_id,
                "direct": direct,
                "predicted_delta": commitment.predicted_delta,
                "observed_delta": observed_delta,
                "verdict": verdict,
            },
            creator="environment",
            dependency_ids=(commitment.prediction_id, commitment.proposal_id),
        )
        self.epistemic.add_environment_evidence(
            target_id=commitment.prediction_id,
            verdict=verdict,
            transition_id=transition_id,
            payload={
                "direct": direct,
                "predicted_delta": commitment.predicted_delta,
                "observed_delta": observed_delta,
            },
            dependency_ids=(evidence_object.object_id, commitment.proposal_id),
        )
        binding = self.epistemic.object(commitment.binding_id)
        hypothesis_id = next(
            dependency
            for dependency in binding.dependency_ids
            if self.epistemic.object(dependency).kind == "semantic-schema"
        )
        derivation_id = max(
            (
                item.object_id
                for item in self.epistemic.objects
                if item.kind == "derivation"
                and hypothesis_id in item.dependency_ids
            ),
            key=lambda value: self.epistemic.object(value).created_revision,
        )
        criticism = self.epistemic.add_object(
            kind="structured-criticism",
            semantic_key={
                "target": hypothesis_id,
                "derivation": derivation_id,
                "prediction": commitment.prediction_id,
                "transition_id": transition_id,
                "verdict": verdict,
            },
            payload={
                "target": hypothesis_id,
                "derivation": derivation_id,
                "status": "prospective-evidence-return",
                "verdict": verdict,
                "prediction_id": commitment.prediction_id,
                "binding_id": commitment.binding_id,
                "evidence_id": evidence_object.object_id,
                "predicted_delta": commitment.predicted_delta,
                "observed_delta": observed_delta,
                "grounding_diagnostics": self.grounding_diagnostics(),
                "instruction": (
                    "Revise the exact tested schema using the returned prospective outcome "
                    "and complete current grounding. Prediction support is local mechanism "
                    "evidence, not task success."
                ),
            },
            creator="r2",
            dependency_ids=(
                derivation_id,
                hypothesis_id,
                commitment.prediction_id,
                commitment.binding_id,
                evidence_object.object_id,
            ),
        )
        self.epistemic.attend(
            worker="qwen",
            object_id=criticism.object_id,
            weight=900,
            channel="environment-return",
            basis_ids=(evidence_object.object_id,),
            nonce=transition_id,
        )
        return EvidenceReturn(
            evidence_object_id=evidence_object.object_id,
            prediction_id=commitment.prediction_id,
            verdict=verdict,
            criticism_id=criticism.object_id,
        )

    def choose_confirmed_control(
        self,
        *,
        binding_id: str,
        legal_interventions: Sequence[str],
        fallback_intervention: str,
        decision_basis: str,
    ) -> CausalControlDecision:
        binding = self.epistemic.object(binding_id)
        if binding.kind != "binding" or binding.payload.get("status") != "bound":
            raise SharedCognitionError("control requires one complete uniquely bound hypothesis")
        hypothesis_id = next(
            item
            for item in binding.dependency_ids
            if self.epistemic.object(item).kind == "semantic-schema"
        )
        hypothesis = self.epistemic.object(hypothesis_id)
        if hypothesis.payload.get("revision_of") is None:
            raise SharedCognitionError("initial semantic proposals cannot directly control")
        candidates: list[tuple[int, str, EpistemicObject]] = []
        for item in self.epistemic.objects:
            if item.kind != "prediction" or binding_id not in item.dependency_ids:
                continue
            if self.epistemic.support(item.object_id) <= 0:
                continue
            intervention = str(item.payload["intervention_ref"])
            if intervention not in legal_interventions:
                continue
            delta = int(item.payload["predicted_delta"])
            candidates.append((delta, intervention, item))
        if not candidates:
            raise SharedCognitionError("no prospectively confirmed legal control exists")
        reverse = hypothesis.payload["operator"] == "Increase"
        candidates.sort(key=lambda item: (item[0], item[1]), reverse=reverse)
        _delta, selected, prediction = candidates[0]
        decision = self.epistemic.add_object(
            kind="control-decision",
            semantic_key={
                "decision_basis": decision_basis,
                "binding_id": binding_id,
                "prediction_id": prediction.object_id,
            },
            payload={
                "selected_intervention": selected,
                "fallback_intervention": fallback_intervention,
                "changed": selected != fallback_intervention,
                "binding_id": binding_id,
                "prediction_id": prediction.object_id,
                "hypothesis_id": hypothesis_id,
            },
            creator="r2",
            dependency_ids=(binding_id, prediction.object_id, hypothesis_id),
        )
        return CausalControlDecision(
            decision_id=decision.object_id,
            selected_intervention=selected,
            fallback_intervention=fallback_intervention,
            binding_id=binding_id,
            prediction_id=prediction.object_id,
            hypothesis_id=hypothesis_id,
            changed=selected != fallback_intervention,
        )
