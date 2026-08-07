# Phase-1 partial bindings and shadows

Status: executable Phase-1 contract, audited 2026-08-07.

## Pre-implementation audit

1. A complete binding was produced by bounded positive-conjunctive `_verify`:
   every matcher atom had to unify against grounded facts under one variable
   assignment. The runtime then stored a compact `Binding(schema_id,
   assignments, carrier, activation, provenance)`; it did not copy the schema.
2. Partial bindings existed only in two incomplete forms. `_verify` used
   transient partial substitutions internally and discarded them when a later
   atom failed, while the manual `project_shadow` API could hold partial
   child-role state but was not connected to `observe`.
3. The minimum representation change was a first-class compact
   `PartialBinding` record plus a `partial_binding_id` reference from `Shadow`.
   The immutable schema DAG and canonical identity required no change.
4. The flat candidate verifier could expose missing atoms, but not the semantic
   role frontier. The implemented path instead uses child `Binding` records and
   the selected definition's occurrence/interface slices to expose bound and
   unresolved child-role IDs and parent-constraint IDs.
5. Shadow generation fits after bounded indexed candidate matching and before
   composition. It considers only retrieved DAG candidates, references their
   existing schema/decomposition IDs, and therefore cannot affect schema
   identity, hashing, or canonicalization.
6. The old observation loop equated “matched” with “fully reified” and simply
   dropped every incomplete candidate. The inspector likewise showed only
   complete bindings unless a caller manually created a shadow. The observation
   loop and inspector now preserve both states explicitly.

## Exact definitions

A Phase-1 **partial binding** is one compatible subset of a schema definition
DAG in one carrier:

```text
partial_binding_id, schema_id, decomposition_id
assignments
bound_role_ids, unresolved_role_ids
satisfied_constraint_ids, unresolved_constraint_ids
incompatible_constraint_ids
supporting (role_id, child_schema_id) references
carrier, activation, provenance
```

It is compatible when its grounded child bindings agree through their
child-to-parent interface maps and every satisfied parent constraint is an
observed grounded fact. It does not copy the definition DAG. Incompatible
constraints remain empty until positive, carrier-adjudicated contradiction
evidence is supplied.

A **shadow** is the bounded immediate unresolved frontier of one such partial
binding. It references `schema_id`, `decomposition_id`, and
`partial_binding_id`; stores the compact assignments, open child-role IDs and
open parent-constraint IDs; and carries activation, carrier, provenance, and
status `SHADOW`, `REIFIED`, or `REFUTED`. Child descendants are not expanded.
It is runtime epistemic state, not a fact, schema, or cloned world.

## Projection policy

`observe` first performs ordinary indexed retrieval and complete matching. For
each retrieved DAG candidate, each grounded child binding may seed a partial
binding unless a compatible complete parent binding already exists. Projection
occurs only when all current explicit limits pass:

```text
activation >= 0.5
bound child-role fraction >= 0.5
open child roles <= 4
open parent constraints <= 8
new shadows in this observation <= 64
```

The activation used here is the maximum of current parent activation and bound
role fraction. The defaults are fields on `Limits`, appear in the inspector,
and are deterministic. Candidate retrieval is capped separately. A memo key
over schema, carrier, decomposition, assignments, child-role state, and
constraint state prevents duplicate live shadows. No full closure, global
schema scan, completion enumeration, or recursive child expansion occurs.

## Reification and refutation

Reification requires a later grounded fact batch to contain a complete schema
match compatible with every partial assignment. The shadow becomes `REIFIED`,
completed role/constraint IDs are recorded, the ordinary canonical `Binding`
is retained exactly once in the new workspace, and one `ProjectionConfirmed`
trace/evidence event is emitted. Reconciliation of a closed shadow is
idempotent.

Refutation is deliberately not inferred from failed matching or absence. Phase
1 requires the carrier/adaptor to declare one or more open constraint IDs
incompatible and supply at least one positive grounded contradictory fact. The
shadow then becomes `REFUTED`, the partial binding retains the incompatible
constraint IDs, and one `ProjectionRefuted` event is emitted. This criterion is
explicit because the current positive language has neither negation nor generic
functional/exclusion semantics.

In both cases the observed fact batch remains unchanged. Projection structures
never enter it.

## Evidence and cross-context preservation

Ordinary complete binding count remains `use_count`. Projection evidence uses
separate `projection_support` and `projection_failure` counters,
`projection_contexts` for distinct confirmation carriers, and
`projection_binding_signatures` to distinguish repeated exact completions from
different grounded forms. Raw append-only evidence events also retain context,
source, definition pathway, and binding signature. No confidence formula or
projection-based promotion policy was added.

Projection origin is currently carried by provenance (`schema-completion` or
`observation:partial-schema-match`). This can later distinguish deductive,
conjectural, and teacher-proposed origins without changing schema or shadow
layout. Only schema-conditioned deductive completion is generated now.

## Verification

`tests/test_shadows.py` implements synthetic checks A-H: missing role,
reification, conservative refutation, recursive frontier bounding, two partial
bindings of one schema, structural sharing, 1k/10k/100k dormant-store
independence, and the epistemic firewall. The full suite passes 56 tests.

The dormant stress checks return exactly two retrieved and verified candidates,
one `PROJECT_SHADOW` work item, and one structurally identical shadow at all
three store sizes.

Three existing public first frames were run only as static bounded diagnostics:

| frame | complete bindings | partial bindings | shadows | avg open roles | reified facts | work items | truncations |
|---|---:|---:|---:|---:|---:|---:|---:|
| ar25 | 241 | 0 | 0 | 0.0 | 1,894 | 388 | 134 |
| m0r0 | 175 | 0 | 0 | 0.0 | 10,602 | 1,090 | 10 |
| vc33 | 208 | 0 | 0 | 0.0 | 6,133 | 1,185 | 10 |

All three preserved shadow/reified separation. Zero shadows are expected in
these fresh-runtime first frames: they contain no previously learned higher DAG
whose child can bind only partially; same-frame compositions are constructed
from complete bindings after projection. This is an explosion check, not a
claim of recognition quality.

## Deliberate limits and combinatorial risk

One independently grounded child binding seeds one partial binding. Phase 1
does not enumerate or greedily merge all compatible child-binding combinations;
that would introduce a Cartesian risk. High-multiplicity seed bindings can
still fill the per-observation shadow budget, which is reported as a
`shadow-projection-budget` truncation. Immediate-frontier projection, retrieval
caps, role/constraint caps, memoization, and the 64-shadow cap bound that risk.

Temporal learning, actions, planning, explanations, conjectural generation,
teacher/Qwen integration, confidence modeling, general context equivalence,
automatic contradiction semantics, neural models, ARC strategy, and GPU code
remain deliberately unimplemented.

> Given an active partially bound schema DAG, Reflector-II can project only its
> bounded unresolved structural frontier as epistemically unrealized shadow
> structure, then later distinguish successful reification from contradiction
> without confusing either projection with observation.
