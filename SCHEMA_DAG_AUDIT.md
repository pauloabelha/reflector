# Schema-DAG design audit

## Current state before this migration

Schemas were canonical conjunctions of flat relational atoms. Constructed
schemas additionally kept a decomposition-occurrence DAG for explanation and
activation, but the canonical hash and matcher semantics came from the flattened
body. Bindings were transient `(schema_id, dict)` pairs in a workspace. There
was no explicit projected/unobserved state.

## Divergence from the required ontology

That made a schema look like an `AND` node first and a reusable structured
constraint second. In particular, a parent could not introduce a relation above
children without flattening it into the same body, DAG child identity did not
participate in constructed-schema identity, bindings lacked an explicit carrier
record, and a predicted missing structure could only be represented as a normal
fact/prediction rather than a partial schema binding.

## Smallest migration

Add an explicit `schema-dag` construction form with child-schema roles and
parent-level relation constraints. Store its child occurrence slice,
constraint-root slice, and exposed-interface slice in the existing SoA graph;
content-address this definition. Compile its transitive flat expansion into the
existing bounded matcher, preserving current retrieval and match code. Replace
tuple bindings with compact binding records, and add demand-driven shadow rows
plus projection-success/failure evidence counters.

The follow-up refinement makes this more than decorative storage: a shadow now
contains one state per child occurrence and parent-level constraint. Existing
child bindings realize roles incrementally; unchanged role/constraint signatures
are memoized; reconciliation reports exactly which projected roles/constraints
completed and records evidence against the parent definition pathway.

## What remains unchanged

Term interning, fact indices, positive bounded matching, sparse activation,
ordinary links, current kernel schemas, legacy conjunction composition, and
existing ARC/synthetic tests remain valid. The legacy composer is intentionally
left compatible: it still produces flattened conjunction candidates with a
lossless decomposition record. New reusable structural definitions use the
explicit DAG form.

## Risks and bounds

Canonical DAG identity relies on the existing alpha-normalized compiled
interface and sorted child/reference encoding. It avoids general graph
isomorphism; variable symmetry remains bounded by the existing eight-variable
canonicalizer (`<= 8!` residual permutations). Matching is still a capped
positive conjunctive join. Projection is `O(open frontier + one bounded match)`
for an explicitly selected schema, with no global dormant-schema scan. Future
work can migrate automatic composition from its legacy form to explicit
parent-level constraints without changing bindings, shadows, or the compiled
storage layout.
