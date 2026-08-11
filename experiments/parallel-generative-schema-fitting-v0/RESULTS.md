# R2.1 mechanistic result

Run command:

```bash
.venv/bin/python experiments/parallel-generative-schema-fitting-v0/run_mechanistic_experiment.py
```

Observed deterministic result:

```text
R2 version: R2.1-schema-fitting-v0
Created schema: schema:0be8c32f42b4e712
Constraints: DifferentFill(p0,p1), SameOutline(p0,p1)
Promotion contexts: 2
Novel partial binding: p0=c3, p1=c4
Projected shadow: DifferentFill(c3,c4)
Later environment reification: 1
```

This demonstrates the decisive static chain:

```text
two grounded relational contexts
→ one canonical reusable schema
→ novel partial binding
→ explicit missing-relation shadow
→ later environment reification
```

The test suite additionally verifies multiple simultaneous bindings, shadow
refutation only from explicit contradictory evidence, temporal
before/intervention/after fitting, bounded partial-binding extension, local
composition retaining its components, and dormant-store independence with
1,000 irrelevant schemas.

The deterministic runner also constructs a temporal schema with opaque token
`opaque-7`. From `Corresponds(q0,q1)` and `Applied(opaque-7,q0)`, it projects
the missing `Translation(q0,q1,delta)` relation. A later environment fact
`Translation(q0,q1,d0)` is available for settlement through the same shadow
machinery as the static case.

It now also demonstrates genuine recursive construction:

```text
raw supports r1,r2
→ two Schema_0 region-binding atoms
→ SameInvariant + Arranged pair-binding
→ configuration-binding over that pair binding
```

The configuration binding is at recursive depth 2 and its grounding ancestry
contains the two raw-support evidence IDs plus both relational evidence IDs.
The depth limit is per cycle, not architectural: a separate regression test
continues the same recursive type from depth 2 to depth 4 in a later cycle.

A recursive dormant-store test adds 1,000 schemas with unrelated port types.
The active delta considers exactly one compatible schema, demonstrating that
recursive fitting uses the type index rather than scanning dormant memory.
