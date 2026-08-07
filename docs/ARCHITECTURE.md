# Reflector-II architecture

Status: Phase-1 decision record. This document specifies the target design and
marks what the initial vertical slice must demonstrate.

## 1. Runtime shape

```text
grid / DSL / prior
  -> audited adapters and compiler
  -> ground term batch + compact signatures
  -> indexed candidate retrieval
  -> bounded MATCH work items
  -> evidence seeds
  -> sparse ACTIVATE/EXPAND frontier
  -> bounded COMPOSE and MAP candidates
  -> canonicalize/hash-cons in DeltaG
  -> local evidence update and PRUNE
  -> trace + metrics
```

There is no level pipeline in this flow. “Perception” indicates an input
boundary, not a privileged descriptive layer. Previously learned composites
can be retrieved directly from evidence; their activation can enqueue
lower-level searches through graph links in the same cycle.

The logical model is many small epistemic processes. The physical model is a
small set of work-item kinds, grouped into deterministic batches:

`TRY_BIND`, `VERIFY_BINDING`, `EXPAND`, `TRY_COMPOSE`, `SCORE_MAPPING`,
`CHECK_PREDICTION`, and `APPLY_EVIDENCE`.

## 2. One generic representation

### 2.1 Term store

Terms are hash-consed and stored structure-of-arrays (SoA):

```text
term_kind[]       uint8       # SYMBOL, VARIABLE, APPLICATION
term_symbol[]     int32       # symbol/head/variable ordinal
child_offset[]    int64
child_count[]     uint8
children[]        int32
```

Symbol bytes and display labels are cold side tables. A schema body is a sorted
slice in `body_roots[]`; nesting is represented by application nodes, not
Python references. Structural identity is computed bottom-up, then the
canonical key is hash-consed. The Python prototype may use growable integer
lists, but exposes contiguous arrays and does not place per-term Python objects
in matching loops.

### 2.2 Schema and link store

```text
body_offset[]       int64          support[]             uint32
body_count[]        uint8          contradiction[]       uint32
canonical_hash[]    128/256 bits   prediction_success[]  uint32
provenance_offset[] int64          prediction_failure[]  uint32
flags[]             packed         use_count[]           uint32
depth[]             uint16         last_used[]           uint64
schema_state[]      uint8          # candidate / established / promoted
                                    activation[]          fp32 (workspace-owned)

src[]       int32
relation[]  uint16
dst[]       int32
weight[]    fp32
flags[]     packed
edge_provenance_offset[] int64

decomposition_owner[]             int32
decomposition_occurrence_offset[] int64
decomposition_occurrence_count[]  uint8
occurrence_schema[]               int32
occurrence_map_offset[]           int64
occurrence_map_count[]            uint8
occurrence_child_variable[]       uint8
occurrence_owner_variable[]       uint8

constraint_offset[]               int64   # parent-level relation slice
constraint_count[]                uint8
constraint_roots[]                int32
interface_offset[]                int64
interface_count[]                 uint8
interface_variables[]             uint8
```

These rows represent atomic descriptors, composites, transformations, teacher
proposals, actions, and analogies uniformly. Flags identify storage state and
validation status, not semantic object classes. Provenance is an append-only
cold table and can contain multiple sources for one hash-consed schema.

Semantic identity and construction identity are deliberately separate. One
canonical conjunctive body may have several decomposition derivations. A child
row is an occurrence, not merely a set member, so the same schema can occupy
two roles with different variable-interface maps. Recursively following
occurrences forms a DAG certified by `child.depth < owner.depth`. Semantic term
relations may still contain cycles. Flattening the occurrence DAG yields the
canonical conjunction used by the current matcher; the DAG preserves
explanation, alternative chunkings, and future topological batch scheduling.

For the `schema-dag` language form, the role-occurrence slice plus the
constraint slice are the content-addressed definition. Its hash includes child
hashes, normalized child-to-owner interface maps, parent-level constraints, and
the exposed interface. `body_roots[]` is only the compiled matcher expansion.
This permits an atomic-from-above schema ID while retaining a structured-from-
below DAG without copying a child graph. The older composition path remains a
compatible flattened-conjunction producer; new reusable structural schemas use
the explicit DAG form.

SoA is chosen because matching and activation read the same field across many
rows and because arrays transfer directly to accelerator memory. Object-rich
Python is retained only for configuration, compiler diagnostics, trace views,
and immutable result envelopes.

### 2.3 Stable graph plus delta

`G_stable` is canonical, deduplicated, indexed CSR grouped by source and
relation, memory-mappable on CPU, and uploadable to GPU. `DeltaG` contains
append-only term/schema/link rows plus hash maps and adjacency lists for recent
constructions. A read checks delta first and stable second. Frontier expansion
concatenates the stable CSR slice and the source's delta slice.

Compaction is an explicit cold-path transaction: freeze ingestion, sort/dedupe
delta by canonical identity, remap IDs, merge indices/CSR, atomically publish a
new generation, then retire the prior generation after readers finish. It is
never triggered inside a cognition cycle and therefore never makes one new
schema rebuild the GPU graph.

The initial vertical slice implements the delta-shaped append store and indexed
adjacency. Stable CSR compaction is specified and tested at the interface, not
claimed as a GPU implementation.

## 3. Indices and the no-scan rule

Observation adapters emit ground facts and a compact signature containing
application `(head,arity)` keys, selected ground argument fingerprints, local
degree/count buckets, and canonical form hashes. Indices are deterministic:

```text
(head, arity)                         -> schema IDs / fact IDs
(head, arity, grounded-position,value)-> schema IDs / fact IDs
canonical body hash                   -> schema ID
structural form hash                  -> form-schema IDs
action token + changed-head set       -> morphism IDs
```

Retrieval intersects the smallest available postings lists and stops at
`max_binding_candidates`. It never iterates `0..schema_count`. New relation
symbols can be added without changing the index design. Embeddings and LSH are
unnecessary until deterministic fingerprints fail on measured workloads.

Normal cost is

`O(sum postings looked up + candidates verified + active outgoing edges)`.

Adding dormant schemas under unrelated keys changes dictionary size and memory,
not the count of cognition-loop rows touched. Maintenance, reporting, explicit
compaction, and offline audits may scan the store but are labeled cold-path
operations in traces.

## 4. Matching

The schema-pattern language is a positive conjunctive query with typed-by-data
variables, arity at most 8, at most 16 atoms, nesting depth at most 4, and no
recursive rules. Verification orders pattern atoms by estimated postings size,
then performs indexed nested-loop joins with early equality rejection.

For pattern atoms `P1..Pk`, postings sizes `m1..mk`, naive worst case is
`O(product(mi))`, which remains exponential in the query size. It is made an
anytime bounded algorithm by constant `k<=16`, `mi<=max_facts_per_atom`, a
global `max_partial_bindings`, and `max_bindings_per_schema`. The runtime reports
truncation. For the common star/equality patterns, hashing bound variables makes
expected work `O(sum(mi) + outputs)` after retrieval. There is no unrestricted
subgraph isomorphism or arbitrary path query.

Candidate filtering by head/arity and grounded slots is `O(k)` expected hash
lookups plus postings visited. Canonical form equality is `O(1)` expected after
hash computation and exact `O(n)` verification on hash collision.

## 5. Workspace and activation

The workspace owns sparse arrays of active schema IDs, activations, bindings,
and queue spans. At cycle start, bottom-up matches and unresolved predictions
seed signed evidence. Expansion consumes only the current frontier:

1. Gather stable and delta outgoing edge slices for each frontier node.
2. Emit `(destination, weighted_delta)` records.
3. Sort or hash-reduce by destination deterministically.
4. Add local evidence/cost, clip, and retain values over `epsilon`.
5. Stable top-k prune by `(activation, evidence, -cost, canonical_id)`.

With `V_f` frontier nodes and `E_f` outgoing edges, one round is
`O(V_f + E_f + R log R)` using sort-reduce or expected `O(V_f+E_f)` with a
hash accumulator, plus `O(R log K)` top-k. No graph-wide activation vector is
cleared; an epoch/touched-ID scheme resets sparse state.

A binding is a compact envelope: `(schema_id, sorted(variable_id, term_id)
assignments, carrier, activation, provenance)`. It is distinct from the
immutable schema store. A partial binding adds compact bound/open role IDs,
satisfied/open/incompatible constraint IDs, and supporting child references.
A shadow references it and is similarly small: `(parent_schema_id,
partial_binding_id, partial assignments, child occurrence states,
parent-constraint states, carrier, activation, provenance, status)`. A child occurrence state carries
its child schema ID, mapped child-variable assignments, and `REIFIED`/`SHADOW`
status; a parent constraint is `REIFIED` or `PROJECTED`. `PROJECT_SHADOW` is
requested by one partial binding and accesses one schema slice only; it does
not scan dormant schemas or copy a hypothetical graph. A role/constraint
signature memoizes unchanged partial parent state, while a bounded full-match
cache keys the parent, partial assignments, carrier, and fact batch. Reification
reports the roles and constraints completed, then adds evidence to the parent
definition pathway—not to its flattened atoms. The flat matcher remains a
temporary compiler backend and is explicitly not permitted to define shadow
semantics.

Phase-1 automatic projection considers only the current observation's bounded
retrieved DAG candidates. One grounded child binding seeds a candidate partial
binding. Defaults require activation and bound-role fraction at least `0.5`, at
most four immediate open child roles and eight open parent constraints, and at
most 64 new shadows per observation. These are explicit `Limits` fields.
Earlier shadows are tested against a later carrier before new shadows are
opened. Refutation is never inferred from a failed full match: it requires
explicit incompatible open-constraint IDs and positive grounded contradictory
evidence from an applicable carrier.

Support, inhibit, specialization, decomposition, prediction, and analogy links
start as a deliberately small structural link vocabulary (`part`, `supports`,
`opposes`, `derived-from`). Richer semantics are application terms and can be
learned. Adding a link kind requires a distinct scheduling consequence; merely
wanting a label is insufficient.

## 6. Construction, canonicalization, and persistence

`TRY_COMPOSE` is generated only from active bindings that share a bound anchor
term (a term occurring as a fact subject) or are connected by an active fact.
This generic role filter prevents coincident scalar values in unrelated slots
from creating spurious joins. Pairs are ranked by estimated reuse/prediction
gain over body size and verification cost. Each cycle has hard limits on pairs,
body size, and retained constructions.

Composition unifies shared variables, unions the bodies, removes duplicates,
alpha-normalizes, sorts structural encodings, and hashes. Structural partition
refinement is `O(i * v * b * a log(ba))` for refinement rounds `i`, variables
`v<=8`, body size `b<=16`, and arity `a<=8`. Only variables left in an
indistinguishable symmetry class are permuted, giving a residual factor
`product_c |class_c|!` and the explicitly bounded worst case `8!`. Hash lookup
is expected `O(1)`; collision resolution compares canonical bodies. A hit
reuses the node and adds provenance and evidence. A miss appends a weak
candidate to `DeltaG` with an occurrence decomposition, variable-interface
maps, provenance, projected `part`/`supports` links, and construction context.
Hash hits may add an alternative derivation only when every child has strictly
smaller depth. Self-occurrences and depth-nondecreasing alternatives are
rejected, so construction dependencies remain acyclic. Candidates are promoted
only by ordinary evidence: Phase 1 requires support in two distinct contexts or
two prediction successes. Later policies may additionally measure retrieval
savings or compression, but cannot bypass evidence provenance. Unused weak
candidates decay and can be tombstoned in cold maintenance.

Constructing every representable conjunction is forbidden. Promotion does not
delete decomposition. `depth = 1 + max(child.depth)` is a topological
certificate, not an execution stage.

## 7. Transition and morphism learning

Given fact batches at `t` and `t+1` plus an optional action term:

1. Retrieve correspondence candidates using stable identity, canonical form,
   shared relations, and bounded local signatures.
2. Score candidates lexicographically by invariant agreement, contradiction,
   and structural cost; retain a bounded version space when ambiguous.
3. For each mapping, emit preserved, changed, appeared, and disappeared
   application roles. Component cardinality changes can emit split/merge data,
   never authoritative identity.
4. Anti-unify values across the before/after pair: equal values share a
   variable; differing values become a typed change or verified relation such
   as `Less`/`Offset`.
5. Canonicalize the resulting before/action/after conjunction and retrieve or
   create the morphism schema.
6. Update support only after comparison; retain counterexamples and ambiguous
   alternatives.

For `n` and `m` active entities, signature bucketing is `O(n+m)` and bounded
candidate scoring is `O(C*r)`, where `C` is capped correspondence candidates
and `r` the local relation count cap. General bipartite assignment is not in
the normal loop. Split/merge search is limited to component groups of configured
size/radius.

Morphisms compose by unifying the first codomain pattern with the second domain
pattern under the same bounded matcher. Approximate commuting diagrams are
claims that two bounded composed paths predict equal selected relation terms;
they receive ordinary success/failure evidence. No category library or global
diagram enumeration is required.

## 8. Prediction, evidence, and Piagetian operations

Prediction creates an immutable pending record before intervention. Resolution
compares its ground expected terms with indexed successor facts. Batched checks
cost `O(predictions + indexed fact lookups)`. Evidence events are append-only;
counter reduction is associative integer addition and can be batched.

- assimilation = existing-schema match and support update;
- accommodation = mismatch-triggered bounded composition/anti-unification;
- chunking = retention of a useful canonical composition;
- equilibration = the resulting local evidence/activation/resource dynamics.

They are trace interpretations of generic work items, never four code paths.

## 9. Worker queues, budgets, and determinism

Every work item contains kind, target IDs, context ID, priority components,
estimated cost, and deterministic tie key. Approximate priority is
`expected_gain / max(cost,1)`. The engine uses explicit configuration:

```text
max_active_nodes              max_active_edges
max_binding_candidates        max_partial_bindings
max_bindings_per_schema       max_composition_proposals
max_new_compositions
max_composition_body          max_transition_correspondences
max_analogy_candidates        max_expansion_rounds
max_queue_items               per-cycle time/operation budget
shadow_activation_threshold  min_shadow_bound_role_fraction
max_shadow_open_roles        max_shadow_open_constraints
max_shadow_projections_per_cycle
```

Overflow is a first-class trace/metric event. Lowest priority work is dropped;
already accepted lower-level descriptions are not erased merely to admit a
composite. The system therefore returns its best current workspace at any
budget.

Phase 1 is deterministic: queues are stable-sorted, reductions use a fixed
order, integer counters are exact, and coordinator-only graph mutations occur
after pure batch results. Later asynchronous CPU/GPU workers may generate
candidates against a generation snapshot; a bounded reconciliation barrier
sorts and commits results. Completion order has no semantic effect. This
adapts a validated Reflector-1 transaction lesson without importing its schema
calculus.

## 10. Teacher compiler

The DSL compiler tokenizes, validates resource limits, resolves variables,
constructs term arrays in a temporary transaction, canonicalizes, and commits
only if the whole submission is valid. Both pre-game prior packets and in-game
workspace-conditioned proposals use it. Allowed proposal payloads are facts,
schemas (including mappings/actions), evidence-free discriminating experiment
descriptions.

Teacher-origin nodes are hash-consed with endogenous nodes. Provenance is
merged, truth is not. Teacher input cannot invoke kernels, set statistics,
choose persistent IDs, bypass budgets, or install executable code. Metrics group
ordinary evidence by provenance to report acceptance, prediction, false
proposal, transfer, and acceleration rates.

## 11. Perception boundary

The first adapter enumerates cells and values, performs deterministic bounded
four-neighbor flood fill, finds frame-connected versus enclosed background
components, and emits ground relational terms. Normalized occupancy and
hole-filled outer occupancy are canonical fingerprints, not names such as L,
Z, or perforated. Generic schemas can bind these values and compose them.
Background identity is explicit sensory-channel configuration when supplied;
a modal-value fallback is convenience inference and must not be confused with
a learned semantic claim.

Flood fill is `O(HW)` per frame with `O(HW)` temporary bits. Fact generation is
linear in emitted cells/components and subject to a cap. The adapter is audited
as a computational primitive and can be replaced without changing the graph
semantics.

## 12. Persistence and observability

A generation snapshot contains versioned term/schema/link arrays, canonical
indices, evidence counters, and provenance log. Transient observations,
bindings, activations, queues, and pending predictions live in episode/cycle
state and are separately replayable. Serialization is canonical and includes
language/runtime versions.

Every cycle records total schemas, active schemas/edges, retrieved and verified
candidates, proposed/retained compositions, work items by kind, frontier sizes,
peak workspace, truncations, timings by phase, and estimated/resident memory.
Trace events refer to canonical IDs and exact contexts. Reports never infer a
capability from a counter alone.

## 13. Reflector-1 archaeology ledger

No old module is imported. The following mechanisms were inspected as
archaeological candidates.

### Palette-free connected component extraction

```text
old mechanism: SceneTracker._components / enclosed-region flood fill
epistemic meaning in new system: audited sensory grouping that emits defeasible
  Connected, Boundary, Enclosed, and Inside facts
dependency footprint: grid enumeration, deque, coordinate/value equality
reusable unchanged? no
adapt? retain bounded deterministic flood-fill algorithm; remove ObjectState,
  color-preserving identity assumptions, named visual ontology, and policy ties
reason to retain: linear, inspectable sensory kernel avoids absurd learned flood fill
```

### Normalized occupancy fingerprints

```text
old mechanism: translation-normalized ObjectState.shape and shape hashes
epistemic meaning in new system: discriminative retrieval value for a relation,
  never an object class or complete parse
dependency footprint: sorted integer coordinate tuples and canonical hash
reusable unchanged? no
adapt? represent the fingerprint as an interned term value; add outer-fill
  fingerprint so enclosure can vary independently of form
reason to retain: deterministic O(area log area) retrieval without embeddings
```

### Predecessor/successor attribution and bounded correspondence

```text
old mechanism: effect-attribution experiments and SceneTracker identity/events
epistemic meaning in new system: bounded candidate MAP work over active relation
  signatures with ambiguity retained
dependency footprint: old ObjectState/Scene ontology and numerous policy modules
reusable unchanged? no
adapt? keep only staged signature retrieval, preservation/change accounting,
  explicit split/merge uncertainty, and prospective scoring discipline
reason to retain: experiments found useful trace compression but also false
  authority; the new evidence model preserves both result and falsifier
```

### Canonical trace/replay and coordinator commit

```text
old mechanism: immutable TraceStep/EpisodeTrace values and deterministic worker
  collection/transaction
epistemic meaning in new system: evidence audit trail and order-independent
  reconciliation of batched epistemic work
dependency footprint: JSON serialization and cold immutable envelopes
reusable unchanged? no
adapt? use term/schema canonical IDs and workspace metrics instead of old policy
  classes; preserve append-only event ordering and coordinator-only mutation
reason to retain: validated determinism and falsifiability infrastructure
```

### Old Schema[A,B] AST and policy hierarchy

```text
old mechanism: separate typed AST, Mind, scenes, concepts, events, strategies,
  planning and large policy object graph
epistemic meaning in new system: none as a unit
dependency footprint: broad old ontology and runtime
reusable unchanged? no
adapt? do not adapt; isolated lessons above are re-expressed as generic terms
reason to retain: none; it conflicts with one graph representation and clean reboot
```

## 14. Phase boundaries

Phase 1 implements CPU term storage, indices, bounded matching, sparse
activation, composition/hash-consing, a simple transition anti-unifier, the
synthetic benchmark, and complete instrumentation. It must not contain an ARC
harness, policy, planner, neural model, embeddings, or custom CUDA. GPU and CSR
code begins only after profiles show a batch large and regular enough to win.
