# Active equilibration

Status: conceptual target and documentation guide. This document extends the
Phase-1 substrate; it does **not** claim that the current implementation has a
planner, a goal learner, a live LLM connection, or a general game solver. The
implemented contracts and measured limits remain in
[`THEORY.md`](THEORY.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), and
[`COMPLETION_AUDIT.md`](COMPLETION_AUDIT.md).

Reflector-II is a minimal executable epistemology, not an ARC-specific solver.
Its central process is:

```text
construct structure -> project beyond experience -> act
        -> reify/refute -> reorganize
```

Perception, learning, explanation, exploration, prediction, and solving are
different views of this one loop. **Active equilibration** names their ongoing
interaction.

Use the documentation in this order:

| Need | Document |
|---|---|
| Unified conceptual model and phase boundary | This document |
| Operational definitions and Schema-0 | [`THEORY.md`](THEORY.md) |
| Serialization and the common DSL | [`LANGUAGE.md`](LANGUAGE.md) |
| Sparse runtime, work budgets, and data layout | [`ARCHITECTURE.md`](ARCHITECTURE.md) |
| Tested Phase-1 evidence and omissions | [`COMPLETION_AUDIT.md`](COMPLETION_AUDIT.md) |

## 1. Schemas, two graphs, and parallel activation

A schema is a reusable, content-addressed directed acyclic graph (DAG) over
other schemas: `S = (V, E, I)`. `V` contains child-schema *role occurrences*,
`E` typed structural constraints, and `I` the exposed binding interface.
Definitions bottom out at the small Schema-0 substrate. A learned schema is
atomic from above and structured from below: higher schemas reference its ID,
while its decomposition remains available for matching, projection,
explanation, and reuse.

```text
LShape(X)                         PerforatedShape(X)
|- Segment(A)                     |- LShape(X)
|- Segment(B)                     |- Hole(H)
|- Corner(C)                      `- Inside(H, X)
|- EndpointOf(C, A)
|- EndpointOf(C, B)
`- Orthogonal(A, B)
```

Two graph structures must remain distinct:

| Structure | Question | Constraint |
|---|---|---|
| Internal schema DAG | What composes this schema? | Acyclic |
| Global schema network | What supports, opposes, predicts, or analogizes what? | May cycle |

There is no fixed `pixels -> object -> semantic interpretation` pipeline.
Many schemas at many compositional depths can bind simultaneously: a blue L
can activate `Blue`, `Connected`, `Segment`, `Corner`, `LShape`, and tentative
`Movable`. The workspace is a sparse activated subgraph of the persistent
network, `W_t subset G`; depth is compositional metadata, not execution order.

## 2. Bindings across space, time, and intervention

A schema is not one of its instances. A binding assigns its exposed variables
in a current **carrier/context**. The carrier is more general than a still
image: spatial relations (`Inside`, `Adjacent`), temporal relations (`Before`,
`After`, `PersistsInto`), and intervention relations use the same schema
machinery. “The same form at `t` and `t+1`, at a new position” is therefore an
ordinary time-spanning schema, not a special subsystem.

## 3. Generative schemas and shadows

Every schema works in both directions:

```text
recognition: parts/evidence -> schema
generation:  schema + partial binding -> expected missing structure
```

Generation is bounded schema completion, not a copied hypothetical world. A
**shadow** is the compact, partially bound DAG that an active schema projects
but experience has not grounded. It records a schema ID, known bindings, open
roles/constraints, carrier, activation, provenance, and one status:

```text
REIFIED  observed or grounded
SHADOW   projected but unobserved
REFUTED  projected and contradicted
```

Shadows have two epistemic origins:

- A **deductive shadow** is closure under an accepted schema and binding.
- A **conjectural shadow** extends a structural regularity beyond observations,
  such as completing a repeated commuting pattern in a new case. It is
  abductive/inductive when proposed and deductive only conditional on that
  proposal.

The distinction belongs in provenance and evaluation. Neither shadow becomes
an observed fact merely because it is useful to reason with.

## 4. Morphisms, abstraction, and confidence

Schemas can describe transformations as well as static structure. A morphism
records a domain, codomain, correspondence, preserved and changed structure,
context, and an intervention when present. Composition and repeated approximate
commuting diagrams are executable tests of structural preservation.

The category-theoretic idea is conceptual, not a requirement for a category
library: structured objects, composable transformations, invariants, and
extension of a regularity into a new context. If solid L maps to perforated L
and solid Z maps to perforated Z, an abstract transformation may project a
perforated T as a conjectural shadow. Call this **inductive categorical
extension** unless a real universal property has been established.

Frequency alone should not make a schema authoritative. Preserve binding
support, projection success, projection failure, and distinct carrier/context
support. Success on L, Z, and T tests an abstraction more directly than three
successes on L.

## 5. Explanations are situated executable theories

An explanation is not a second semantic language. It is a bound, mutable,
situated assembly of schemas and morphisms that says what matters, what is
preserved or changed, and what would follow from possible interventions:

`E : (W_t, action) -> projected W_(t+1)`

Schemas are reusable, open, and intensional. Explanations are committed to one
world and moment. Competing explanations can share perceptual schemas while
projecting incompatible successors. Repeated successful explanation fragments
can later be abstracted by replacing situated bindings with variables.

```text
requires: A, B
under action: X
preserve: P, Q
change: R -> R'
project: expected successor DAG
```

Explanations should serialize in the Reflector DSL, so the structures used to
reason can also become structures reasoned about. The concrete source
convention is in [`LANGUAGE.md`](LANGUAGE.md#explanations-goals-and-experiments-as-data).

## 6. Actions, goals, and solutions

Actions are epistemic as well as instrumental. An action may exploit an
explanation, discriminate between explanations, test a shadow or morphism,
fill an explanatory gap, or advance a candidate solution.

```text
explanation  = how this world works
goal         = which state counts as success
solution     = an action program that uses an explanation to attain that goal

explanation + goal -> solution
```

The boundary can become thin when an explanation contains reusable strategy
fragments, but conflating the terms hides whether Reflector has learned
dynamics, success criteria, or a policy.

## 7. Piagetian interpretation

| Term | Generic operational reading |
|---|---|
| Assimilation | Bind new experience with an existing schema. |
| Accommodation | Construct or revise a candidate after mismatch. |
| Abduction | Propose a schema or explanation for a surprise. |
| Deduction | Project shadows conditional on an active proposal. |
| Reification/refutation | Compare projections with subsequent evidence. |
| Equilibration | Reorganize support, activation, composition, and budgets toward coherence. |

Thus exploration, model construction, planning, and learning are interleaved:

```text
project <-> act <-> reify/refute <-> accommodate <-> explain <-> solve
```

## 8. LLMs and physical discipline

An LLM is a proposal source, not an oracle. It may propose schemas, DAG
decompositions, morphisms, explanations, shadows, discriminating experiments,
or abstractions in the same DSL. Such input has provenance such as
`teacher:qwen`, starts as a weak candidate, and must survive ordinary binding,
prediction, reification/refutation, and cross-context tests. **The LLM
proposes; Reflector adjudicates.**

The vocabulary—typed schema DAGs, bindings, activation, morphisms, shadows,
and explanations—must compile to integer IDs, flat arrays, structural sharing,
content hashes, sparse frontiers, and indexed retrieval. Normal cognition must
avoid global scans, dense ontology matrices, copied graph forests, and
unrestricted graph isomorphism. Its intended hot operations are:

```text
MATCH  ACTIVATE  EXPAND  COMPOSE  PROJECT
REIFY/REFUTE  MAP/REWRITE  PRUNE
```

Phase 1 implements the substrate for schemas, bindings, shadows, evidence, and
bounded morphism learning. Explanations, explicit goals/solutions, experiment
selection, broad cross-context induction, and live teacher/LLM integration are
next-phase design commitments, not completed capabilities.

> Intelligence consists partly in constructing structures that dare reality to
> keep commuting beyond what has already been observed.
