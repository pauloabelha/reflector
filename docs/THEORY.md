# Reflector-II operational theory

Status: Phase-1 contract. Terms in this document name executable state and
operations, not philosophical modules.

[`ACTIVE_EQUILIBRATION.md`](ACTIVE_EQUILIBRATION.md) organizes the wider target:
situated explanations, active experiment choice, goals, solutions, and
teacher/LLM proposals. This document remains authoritative for Phase-1
behavior. A wider idea is not an implemented capability unless it is specified
here and evidenced in the audit.

## 1. Substrate

The substrate is a finite, content-addressed relational term graph. Its only
structural values are symbols, variables, applications, and finite unordered
conjunctions. An application `p(a0,...,an)` is a node whose head is the symbol
`p` and whose ordered argument edges point to its terms. A conjunction is a
canonical set of application roots. `p` has no built-in meaning merely because
it is used as a predicate: `Color`, `Action`, `Before`, `Preserve`, and
`TeacherProposal` are data in the same representation.

The engine supplies only five generic operations over these values:

1. `MATCH`: bounded substitution of pattern variables against facts.
2. `ACTIVATE/EXPAND`: local evidence updates and frontier edge traversal.
3. `COMPOSE`: conjunction followed by alpha-normalization and hash-consing.
4. `MAP`: compare two bound fact graphs and construct a relational change
   pattern; applying such a pattern is a constrained rewrite.
5. `UPDATE/PRUNE`: update local sufficient statistics and enforce budgets.

These are computational operations, not semantic predicates. There is no
execution level attached to a term. A cell description, region, composite, and
transition can all be active in the same workspace.

## 2. Operational definitions

**Schema.** A reusable, content-addressed DAG constraint over other schemas.
It is `S = (V, E, I)`: child-schema role occurrences `V`, directed typed
relations/constraints `E` imposed among their interface variables, and exposed
variables `I` through which the schema binds or composes. A ground leaf is the
Schema-0 base case. The definition DAG is immutable and acyclic; its identity
hash includes canonical child identities, normalized role maps, parent-level
constraints, and interface—not display name, source, activation, evidence, or
construction order. The runtime also stores a flattened positive-conjunctive
*matcher expansion* of the DAG for efficient indexed matching. That expansion
is compilation, not the meaning of a constructed schema. Repeated children are
references to one schema ID, never copied graphs.

**Compiler warning.** The flat expansion is a Phase-1 recognition backend, not
an epistemic substitute for the DAG. Partial recognition is represented by
child-occurrence state (`REIFIED` or `SHADOW`) and parent-constraint state
(`REIFIED` or `PROJECTED`). The backend may verify a completed expansion, but
it must not collapse an unresolved child role into a bag of missing atoms.
Storage state is explicit: a constructed/teacher schema begins as `candidate`,
kernel commitments are `established`, and only ordinary multi-context support
or repeated prediction success can mark a candidate `promoted`. State is not
part of semantic identity.

**Schema instance / binding.** A compact record `(schema_id, assignments,
carrier/context, activation, provenance)` produced by `MATCH` in a particular
carrier. Assignments map schema-interface variables to term IDs. One schema can
have many bindings, and a binding never creates a new schema. A carrier is
abstract: Phase 1 uses a spatial observation, while later carriers may include
time or intervention without changing schema meaning.

**Partial binding and shadow.** A partial binding is a compatible subset of an
active schema DAG: compact interface assignments, bound/unresolved child-role
IDs, satisfied/unresolved/incompatible parent-constraint IDs, supporting child
references, carrier, activation, and provenance. A shadow references that
partial binding and contains only its demand-driven immediate unresolved
frontier, with status `SHADOW`, `REIFIED`, or `REFUTED`. A child role is
grounded only by a child binding; a parent constraint is satisfied only by a
verified grounded fact. Compatible later evidence reifies the particular
roles/constraints completed and records parent-pathway `projection-success`;
positive carrier-adjudicated contradiction evidence records
`projection-failure`. Absence never refutes. No consequence enumeration occurs.

**Projection origin.** A shadow is *deductive* when an accepted schema and
partial binding entail its unresolved roles/constraints under the schema's
declared semantics. It is *conjectural* when an abductive or inductive proposal
extends a structural regularity beyond the observed binding. The latter is
deductive only conditional on accepting the proposal. Origin is provenance and
evaluation state, never a reason to treat a shadow as a fact.

**Relation.** An application term. Unary concepts, binary relations, metadata,
temporal roles, actions, and relations about relations differ only by their
heads and arguments. Argument-position edges are the sole primitive ordering
relation. Domain semantics must be learned or supplied as defeasible schemas.

**Composition.** Canonical conjunction of two or more schema bodies after
variable unification. Composition is demand-driven: operands must be active,
share a binding or be joined by an active relation, fit the construction
budget, and earn a non-negative value/cost priority. A non-redundant result
keeps an occurrence DAG with each operand and its child-to-owner variable map;
`part`/`supports` links are activation projections of that DAG. A composition
whose canonical union equals one operand is not a new derivation, because that
would create a self-edge. Composition never suppresses its parts.

**Activation.** A finite salience value on a persistent schema ID during one
cycle. Events contribute signed deltas locally. The Phase-1 update is

`a'(i) = clip(decay*a(i) + evidence(i) + sum(j->i) w(j,i)*a(j) - cost(i))`.

Only active frontier nodes and their indexed outgoing edges are evaluated.
Contradiction is a negative event, not a special global pass. Exact coefficients
are runtime policy and versioned configuration, not semantics.

**Workspace.** `W_t = (F_t, B_t, Q_t)`: a bounded activated subgraph `F_t`, its
transient bindings `B_t`, and typed work queues `Q_t`. It is a sparse view into
the persistent graph, not a second knowledge store and not a single parse.
Competing incompatible bindings may coexist until evidence or budgets prune
them.

**Persistent graph.** The union `G_stable + DeltaG` of schema nodes, typed
links, acyclic decomposition records, local statistics, canonical hashes, and
provenance. Stable storage is compressed and mostly immutable; the delta is
append-friendly. Dormant nodes are not visited by normal cognition. Semantic
relations represented by terms may be cyclic; only construction/decomposition
dependency is required to be acyclic.

**Mapping / morphism.** A schema whose body relates a domain pattern, codomain
pattern, correspondence variables, preserved applications, changed
applications, action/intervention if present, and optional context. It is
matched, composed, scored, contradicted, and persisted like any other schema.
Composition of morphisms is ordinary variable unification plus conjunction;
incompatible intermediate patterns make the match fail. “Category-inspired”
claims refer only to these executable preservation and composition tests.

**Action.** A ground intervention term such as `Action(ACTION_3)`, used as an
argument in a transition schema. It initially denotes only token identity.
Learned before/action/after morphisms give it defeasible effects. No movement,
agent, target, or planning semantics are intrinsic to the token.

**Evidence.** A local signed observation about a schema or link, recorded as
sufficient statistics `(support, contradiction, prediction_success,
prediction_failure, use_count, distinct_contexts, last_used)`. Raw evidence
events preserve source and context IDs. Strength is a deterministic function
of these counters; Phase 1 uses Laplace-smoothed support
`(support+1)/(support+contradiction+2)` when a probability-like score is
needed.

**Cross-context projection evidence.** Projection success/failure is retained
separately from ordinary binding count. Phase 1 records distinct confirmation
carriers and exact partial/grounded binding signatures as well as definition
pathways, so repeated exact completions can later be distinguished from varied
bindings. A future promotion policy may use diversity-aware support only with
explicit, auditable context criteria.

**Prediction.** A morphism bound to a present domain and action that emits an
expected codomain/preservation/change term before the successor is observed.
Predictions are immutable pending records until comparison.

**Contradiction / falsification.** A resolved prediction whose required term is
absent, forbidden term present, preservation violated, or predicted change has
the wrong relation. It increments failure/contradiction statistics and retains
the counterexample context. It never erases prior support.

**Assimilation.** Successful binding of new evidence to an existing schema or
morphism, followed by ordinary local evidence updates.

**Accommodation.** A bounded construction or revision proposal triggered by
repeated unmatched/contradictory active evidence. It is not mutation in place:
the new canonical schema is a new node linked to its antecedent, and both can
remain active until evidence selects between them.

**Chunking.** Promotion of a repeatedly useful composition from transient
candidate to persistent schema because reuse, prediction, compression, or
retrieval value exceeds its construction/storage cost.

**Equilibration.** The observable effect of local support, contradiction,
prediction, composition cost, and resource pruning tending toward a mutually
compatible active subgraph. It is not a coordinator or separate algorithm.

**Explanation (next phase).** A bound, situated executable theory assembled
from ordinary schemas and morphisms. It records relevant bindings, applicable
conditions, intervention, claimed preservation/change, and a projected
successor DAG. It differs from a reusable schema in epistemic role—not in term
language or storage substrate. Competing explanations may share perceptual
schemas while projecting incompatible successors. Successful fragments may be
abstracted into reusable schemas by variable generalization.

**Goal and solution (next phase).** A goal is a defeasible schema describing a
success condition; a solution is an action program selected using an
explanation to reach a bound goal. Neither is implied by merely recognizing a
transition. The current runtime has no goal learner or planner.

**Discriminating intervention (next phase).** An action proposal selected
because its predicted outcomes distinguish active explanations, test a shadow
or morphism, or otherwise reduce an explicit uncertainty. It is represented as
ordinary action/morphism/explanation data and must receive prospective
evidence; it is not a privileged exploration opcode.

**Persistence.** Inclusion of a canonical schema and its statistics in
`G_stable` or `DeltaG` across workspace resets. Persistence requires a canonical
hash, provenance, decomposition for constructed nodes, and an explicit
retention decision. Activation alone is insufficient.

## 3. Schema-0

Schema-0 separates computational primitives from semantic priors.

Computational primitives are integer/value identity, finite grids as sensory
input, coordinate enumeration, equality/difference, bounded four-neighbor
enumeration, flood fill, integer comparison/counting, canonical sorting and
hashing, variable unification, and the five substrate operations above. Flood
fill and coordinate arithmetic are efficient kernels; naming their outputs
`Connected` or `Inside` is a defeasible semantic interpretation.

Initial semantic seeds are deliberately small: `Cell`, `Value`, `Same`,
`Different`, `Adjacent4`, and observation/time identity. Phase 1 permits
audited sensory adapters to emit `Connected`, `Boundary`, `Inside`, and `Count`
because reconstructing flood fill from learned graph rewrites would obscure
the research question and be computationally absurd. `Segment`, `Corner`,
`Hole`, `Shape`, `Object`, `L`, `Z`, `Perforated`, `Movable`, and `Target` are
not Schema-0 primitives. In particular, “hole” is a learned/useful
composition over an enclosed background component and `Inside` relation.

This compromise is falsifiable: each sensory kernel reports the exact facts it
emitted, can be ablated, and cannot directly emit task actions or named ARC
objects.

Numeric encodings are nominal unless their emitting relation is audited as a
quantity (Phase 1: `Count` and `EnclosureCount`). In particular, palette IDs do
not inherit order from integer comparison.

## 4. Multiple descriptions and depth

Compositional depth is the longest child-occurrence path from a schema to a
schema with no decomposition. It is metadata computed from the DAG, never a
scheduling stage. Matching and activation operate on any indexed schema.
Creating a composite adds it to the active set without deleting its operands
or their bindings. Contradictory or alternative descriptions are independent
nodes with separate evidence.

## 5. Teacher symmetry

A teacher submission compiles to the same terms and schemas as an endogenous
proposal. The only difference is provenance such as `teacher:qwen`. It enters
in explicit weak-candidate state with no installed evidence and must pass the
same matcher, predictor, counter updates, hash-consing, and resource controls.
Pre-game and in-game submissions use the same compiler. Teacher acceptance
rate, predictive success,
false-proposal rate, transfer contexts, and construction latency saved are
ordinary aggregate evidence queries; none grants truth authority.

## 6. What Phase 1 can and cannot establish

The synthetic L/Z benchmark can establish simultaneous descriptions,
demand-driven chunking, cross-form relational change abstraction, sparse
retrieval, bounded work, deterministic evidence accumulation, and operational
instrumentation. It cannot establish ARC competence, autonomous discovery of
all sensory concepts, useful planning, broad analogy, GPU speedup, or that the
chosen calculus is sufficient. Those remain empirical hypotheses.

## 7. Schema-DAG correction

`AND(A,B)` is only a degenerate matcher pattern. A reusable constructed schema
retains why its roles belong together: child-schema references and typed
parent-level constraints. `PerforatedL`, for example, references one `LShape`
and one `Hole` plus `Inside(H, X)`; it does not copy the LShape graph. The
definition DAG and learned activation/support network are separate: only the
former is acyclic; support, analogy, and inhibition links may cycle.

Generation is schema completion, not arbitrary world generation: a partial
binding opens only its own unresolved DAG frontier as a shadow. Reification is
recorded separately from ordinary support so later cross-carrier projection
evidence cannot be confused with repeated observation.
