"""Serializable dependency graph for concepts, schemas, and hypotheses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from .causal import HypothesisStore
from .schemas import ConceptStore, SchemaStore

if TYPE_CHECKING:
    from .abstraction import AbstractionStore


@dataclass(frozen=True, order=True, slots=True)
class DependencyEdge:
    source: str
    relation: str
    target: str


@dataclass(slots=True)
class DependencyGraph:
    nodes: dict[str, str] = field(default_factory=dict)
    edges: set[DependencyEdge] = field(default_factory=set)

    @classmethod
    def build(
        cls,
        schemas: SchemaStore,
        concepts: ConceptStore,
        hypotheses: HypothesisStore,
        abstractions: AbstractionStore | None = None,
    ) -> "DependencyGraph":
        graph = cls()
        for schema in schemas.schemas.values():
            graph.nodes[schema.schema_id] = "schema"
        for concept in concepts.concepts.values():
            graph.nodes[concept.concept_id] = "concept"
            for evidence in concept.evidence:
                graph.edges.add(
                    DependencyEdge(concept.concept_id, "supported_by", evidence)
                )
        for schema in schemas.schemas.values():
            for atom in schema.context:
                if (
                    atom.predicate == "synthetic_item"
                    and atom.arguments
                    and atom.arguments[0] in concepts.concepts
                ):
                    graph.edges.add(
                        DependencyEdge(
                            schema.schema_id,
                            "uses",
                            atom.arguments[0],
                        )
                    )
        for causal_hypothesis in hypotheses.causal.values():
            graph.nodes[causal_hypothesis.hypothesis_id] = "causal_hypothesis"
            for schema in schemas.schemas.values():
                if (
                    schema.action_id == causal_hypothesis.action_id
                    and any(
                        event.split("(", 1)[0] == causal_hypothesis.effect
                        for event in schema.result
                    )
                ):
                    graph.edges.add(
                        DependencyEdge(
                            causal_hypothesis.hypothesis_id,
                            "supported_by",
                            schema.schema_id,
                        )
                    )
        for temporal_hypothesis in hypotheses.temporal.values():
            graph.nodes[temporal_hypothesis.hypothesis_id] = "temporal_hypothesis"
        if abstractions is not None:
            for family in abstractions.schema_families.values():
                graph.nodes[family.family_id] = "schema_family"
                for member in family.member_schemas:
                    graph.edges.add(
                        DependencyEdge(family.family_id, "abstracts", member)
                    )
            for concept_type in abstractions.concept_types.values():
                graph.nodes[concept_type.type_id] = "concept_type"
                for child in concept_type.children:
                    graph.edges.add(
                        DependencyEdge(concept_type.type_id, "parent_of", child)
                    )
            for operator in abstractions.language_operators.values():
                graph.nodes[operator.operator_id] = "language_operator"
                for evidence in operator.evidence:
                    graph.edges.add(
                        DependencyEdge(
                            operator.operator_id, "compiled_from", evidence
                        )
                    )
            for procedure in abstractions.procedures.values():
                graph.nodes[procedure.procedure_id] = "procedure"
                for evidence in procedure.evidence:
                    graph.edges.add(
                        DependencyEdge(
                            procedure.procedure_id,
                            "compiled_from",
                            evidence,
                        )
                    )
            for version in abstractions.language_history:
                graph.nodes[version.version_id] = "language_version"
                if version.parent_id is not None:
                    graph.edges.add(
                        DependencyEdge(
                            version.version_id, "descends_from", version.parent_id
                        )
                    )
                for operator_id in version.operators:
                    graph.edges.add(
                        DependencyEdge(
                            version.version_id, "uses", operator_id
                        )
                    )
        return graph

    def to_dict(self) -> dict[str, Any]:
        return {
            "nodes": [
                {"id": node, "kind": kind}
                for node, kind in sorted(self.nodes.items())
            ],
            "edges": [
                {
                    "source": edge.source,
                    "relation": edge.relation,
                    "target": edge.target,
                }
                for edge in sorted(self.edges)
            ],
        }
