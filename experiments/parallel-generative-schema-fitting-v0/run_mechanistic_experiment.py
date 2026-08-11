"""Deterministic R2.1 schema-fitting demonstration; prints a human report."""

from __future__ import annotations

import json
from schema_engine import (
    BindingWorkspace, FrontierBudget, GroundFact, GroundSupport,
    ParallelSchemaFitter, Port, RecursiveSchemaFitter, Relation, Schema,
    SchemaInventor, SchemaStore, ShadowState, fit_schema, project_shadows,
    settle_shadow,
)


def fact(predicate: str, arguments: tuple[str, ...], types: tuple[str, ...], evidence: str, context: str) -> GroundFact:
    return GroundFact(predicate, arguments, types, evidence, context)


def main() -> int:
    store, inventor = SchemaStore(), SchemaInventor(minimum_contexts=2)
    episode_a = (
        fact("SameOutline", ("a1", "a2"), ("figure", "figure"), "env:a:outline", "episode:a"),
        fact("DifferentFill", ("a1", "a2"), ("figure", "figure"), "env:a:fill", "episode:a"),
    )
    episode_b = (
        fact("SameOutline", ("b8", "b9"), ("figure", "figure"), "env:b:outline", "episode:b"),
        fact("DifferentFill", ("b8", "b9"), ("figure", "figure"), "env:b:fill", "episode:b"),
    )
    invented_a, invented_b = inventor.observe(episode_a), inventor.observe(episode_b)
    assert invented_a.schema_id == invented_b.schema_id
    promoted, = inventor.promotable(); store.add(promoted, promoted=True)
    fitter = ParallelSchemaFitter(store, budget=FrontierBudget(active_bindings=8))
    novel_observation = (fact("SameOutline", ("c3", "c4"), ("figure", "figure"), "env:c:outline", "episode:c"),)
    bindings = fitter.update(novel_observation)
    shadows = tuple(fitter.shadows.values())
    reified = fitter.settle((fact("DifferentFill", ("c3", "c4"), ("figure", "figure"), "env:c:fill", "episode:d"),))
    temporal = Schema.create(
        (Port("before", "figure"), Port("intervention", "token"), Port("after", "figure"), Port("delta", "delta")),
        (Relation("Corresponds", ("before", "after")), Relation("Applied", ("intervention", "before")), Relation("Translation", ("before", "after", "delta"))),
        kind="transformation",
    )
    temporal_binding, = fit_schema(temporal, (
        fact("Corresponds", ("q0", "q1"), ("figure", "figure"), "env:t:corresponds", "episode:t0"),
        fact("Applied", ("opaque-7", "q0"), ("token", "figure"), "env:t:applied", "episode:t0"),
    ), budget=8)
    temporal_shadow, = project_shadows(temporal, temporal_binding, limit=1)
    temporal_settled = settle_shadow(temporal_shadow, (fact("Translation", ("q0", "q1", "d0"), ("figure", "figure", "delta"), "env:t:translation", "episode:t1"),))
    recursive_store, recursive_workspace = SchemaStore(), BindingWorkspace()
    schema0 = recursive_store.add(Schema.create((Port("support", "raw-region"),), (), kind="schema0", output_type="region-binding"))
    pair_schema = recursive_store.add(Schema.create(
        (Port("a", "region-binding"), Port("b", "region-binding")),
        (Relation("SameInvariant", ("a", "b")), Relation("Arranged", ("a", "b"))),
        output_type="pair-binding",
    ))
    recursive_store.add(Schema.create((Port("pair", "pair-binding"),), (), output_type="configuration-binding"))
    r1 = recursive_workspace.bind_schema0(schema0, GroundSupport("raw:r1", "raw-region", "env:r1", "recursive:0"), port_name="support")
    r2 = recursive_workspace.bind_schema0(schema0, GroundSupport("raw:r2", "raw-region", "env:r2", "recursive:0"), port_name="support")
    recursive_workspace.add_fact(fact("SameInvariant", (r1.atom_id, r2.atom_id), ("region-binding", "region-binding"), "env:recursive:same", "recursive:0"))
    recursive_workspace.add_fact(fact("Arranged", (r1.atom_id, r2.atom_id), ("region-binding", "region-binding"), "env:recursive:arranged", "recursive:0"))
    recursive_stats = RecursiveSchemaFitter(recursive_store, recursive_workspace).close((r1.atom_id, r2.atom_id))
    configuration = next(atom for atom in recursive_workspace.atoms.values() if atom.type == "configuration-binding")
    report = {
        "r2_version": "R2.1-schema-fitting-v0",
        "created_schema": promoted.schema_id,
        "schema_kind": promoted.kind,
        "schema_components": list(promoted.components),
        "schema_constraints": [relation.predicate for relation in promoted.constraints],
        "promotion_contexts": 2,
        "novel_binding_count": len(bindings),
        "novel_binding": dict(bindings[0].assignments),
        "projected_shadows": [{"predicate": item.relation.predicate, "missing_ports": item.missing_ports} for item in shadows],
        "environment_reified": sum(item.state == ShadowState.REIFIED for item in reified),
        "support_evidence_count": len(store.records[promoted.schema_id].support_evidence),
        "temporal_partial_binding": dict(temporal_binding.assignments),
        "temporal_prediction": temporal_shadow.relation.predicate,
        "temporal_environment_fact": "Translation(q0,q1,d0)",
        "temporal_reified": temporal_settled.state == ShadowState.REIFIED,
        "recursive_schema": pair_schema.schema_id,
        "recursive_atom_types": sorted({atom.type for atom in recursive_workspace.atoms.values()}),
        "recursive_new_bindings": recursive_stats.new_bindings,
        "recursive_maximum_depth": recursive_stats.maximum_depth,
        "recursive_configuration_grounding": list(configuration.grounding_evidence_ids),
        "claim": "A repeated relational schema was promoted, partially bound in a novel context, projected a missing relation, and that relation was reified only by a later environment fact.",
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
