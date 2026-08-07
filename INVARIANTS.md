# Reflector-II invariants

Each invariant is intended to be executable as an assertion, test, trace audit,
or storage validation. “Normal loop” excludes explicit offline reporting,
compaction, migration, and integrity audits.

## Representation and identity

1. Every runtime epistemic structure is a term, schema row, link row, binding,
   evidence event, or work item referencing canonical integer IDs; semantic
   categories do not create parallel object systems.
2. Every persistent schema has a canonical structural hash. Atomic schemas use
   an alpha-normal body; `schema-dag` schemas use normalized child identities,
   role maps, parent-level constraints, and exposed interface. Equivalent
   definitions resolve to one schema ID even across endogenous and teacher
   sources. A compiled matcher expansion is not by itself the identity of a
   DAG schema.
3. Every runtime/persistent structure has provenance. Multiple provenance
   events may point to one canonical structure.
4. Every non-redundant constructed abstraction retains at least one occurrence
   decomposition with child-to-owner variable-interface maps. Every
   decomposition edge strictly decreases depth; self-edges and cycles are
   forbidden. `part` links are activation projections, not the lossless record.
5. Display names, provenance, activation, and evidence counters do not affect
   canonical structural identity.
6. Graph mutations are append/transactional; readers observe one published
   generation plus its bounded delta, never a partially compacted graph.
7. A schema definition DAG is acyclic and immutable after canonicalization.
   Learned activation/support/analogy links are a separate network and may
   cycle.
8. Child schemas are referenced by ID with interface maps; constructed schemas
   never duplicate a child definition graph.

## Sparsity and bounded computation

9. No normal-loop algorithm scans all stored schemas or links to discover
   relevance. Candidate access is by an observation signature, postings index,
   active frontier, pending prediction, or explicit ID.
10. Activation expansion reads only active nodes and their outgoing stable/delta
   slices. Runtime metrics count every visited node/link.
11. Every expensive search has a configured hard cap and emits a truncation
   event when the cap binds.
12. Matching is limited to bounded positive conjunctive patterns; unrestricted
    subgraph isomorphism, recursive path search, implicit negation, and unbounded
    quantification are rejected.
13. Composition is demand-driven from active bindings/relations. No loop
    enumerates all schema pairs or all representable conjunctions.
14. Workspace and queue overflow degrades by deterministic priority pruning and
    returns a valid partial workspace.
15. Dormant schemas under unrelated index keys do not increase retrieved,
    verified, active, or edge-visited counts for a fixed observation.

## Epistemic behavior

16. Multiple compatible or competing bindings may be active simultaneously;
    no canonical single parse is required.
17. Compositional/DAG depth never determines execution order. Higher-level
    activation does not delete or deactivate lower-level descriptions merely
    by existing.
18. Predictions are recorded before their outcomes. An outcome cannot update a
    prediction that did not exist prospectively.
19. Support and falsifying evidence are both retained. A contradiction cannot
    erase a prior event or silently mutate a schema body.
20. Assimilation, accommodation, chunking, and equilibration are results of
    generic match/construct/evidence/resource operations, not privileged
    philosophical code paths.
21. An action begins as an opaque intervention identity. Movement, agency,
    obstacle, target, and reward meanings require ordinary evidence.
22. A transformation records domain, codomain, preserved structure, changed
    structure, conditions/context, and intervention when present; absent fields
    are explicit unknowns, not inferred truth.
23. A constructed or teacher schema begins in explicit weak-candidate state.
    Phase-1 promotion requires support in at least two distinct contexts or two
    prediction successes; future reuse/compression criteria must likewise be
    measured and provenance-bearing. Promotion cannot be granted by display
    name or teacher origin.
24. A binding is separate from a schema definition and includes a carrier/
    context. Multiple bindings of one schema never create new schema IDs.
25. A shadow is a partial binding, not an observed fact or copied hypothetical
    graph. Only its requested schema frontier is projected. Its unresolved
    state is expressed as child-occurrence roles and parent constraints, not
    merely missing flattened atoms. Unchanged role/constraint signatures may
    be memoized. `SHADOW -> REIFIED` requires compatible later evidence,
    identifies completed roles/constraints, and logs parent-pathway
    projection-success;
    `SHADOW -> REFUTED` requires an applicable contradiction and logs
    projection-failure.

## Teacher and domain firewall

26. Teacher proposals compile through the same DSL, canonicalizer, matcher,
    graph store, candidate state, budgets, evidence updates, and resource
    controls as endogenous proposals.
27. Teacher provenance never grants truth, evidence, promotion, activation, or
    access to executable kernels.
28. Teacher statistics include acceptance, prediction success/failure,
    transferred contexts, and construction acceleration; missing measurement is
    reported as unknown, not success.
29. ARC/game IDs, routes, named L/Z/perforation recognizers, target/player/wall
    assumptions, and action meanings do not enter Schema-0.
30. Audited sensory kernels distinguish computational shortcuts from semantic
    priors and emit inspectable facts that can be ablated.

## Determinism and observability

31. Given the same store generation, configuration, input facts, actions, and
    seed, Phase-1 outputs, canonical IDs, evidence counters, work counts, and
    pruning decisions are identical.
32. Parallel completion order cannot affect commits. Only bounded reconciled
    batches mutate the persistent graph.
33. Every benchmark reports total/active schemas, active edges, retrieved and
    verified candidates, proposed/retained compositions, work items, frontier
    sizes, peak workspace, phase timings, and memory.
34. A metric is not evidence of a capability unless a test connects it to the
    required runtime behavior.
35. CPU and future GPU paths must produce identical canonical structures and
    decisions in deterministic mode.

## Phase-1 acceptance checks

- The four synthetic frames leave cell/region/form/enclosure and learned
  composite descriptions active together within the workspace cap.
- The solid/perforated L comparison and solid/perforated Z comparison resolve
  to one canonical generalized transformation with support from two distinct
  form contexts.
- No function or schema named `is_L`, `is_Z`, `is_perforated`, or
  `infer_perforation` exists in executable source.
- Adding 1k, 10k, and 100k unrelated dormant schemas leaves operation counts
  for the fixed relevant observation constant; timings are reported but not
  overinterpreted.
- Canonical replay produces identical schema hashes, active IDs, transformation
  evidence, and metrics other than elapsed time.
