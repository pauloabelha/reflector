"""Serializable dependency graph for concepts, schemas, and hypotheses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .causal import HypothesisStore
from .schemas import ConceptStore, SchemaStore


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
