# Reflector-II architecture

Status: as-built architecture for the current repository. This document
describes what the code executes now. Conceptual extensions
belong in [`ACTIVE_EQUILIBRATION.md`](ACTIVE_EQUILIBRATION.md); future CPU/GPU
layout decisions belong in [`GPU_PLAN.md`](GPU_PLAN.md).

## 1. System boundary

Reflector-II is an in-memory symbolic research runtime with several adapters
and evaluation tools around it. The core owns no game rules, natural-language
ontology, goal model, or planner.

```text
grid / DSL / ARC observation
          |
          v
  audited input adapters
          |
          v
 ground relational facts -----> TermStore
          |                         |
          v                         v
  postings retrieval -------> SchemaGraph
          |                  schemas, DAGs, links,
          v                  evidence, provenance
 bounded Runtime cycle <------------+
  match -> project/reconcile -> activate -> compose
          |
          +--> Workspace / Binding / Shadow (transient)
          +--> learned transition schemas (persistent in memory)
          +--> traces, reports, inspector JSON
          |
          v
 optional ARC action controller
 random | local-schema | explanation
```

“Persistent” in this document means persistent across cycles in one Python
process. There is no implemented schema snapshot loader, stable on-disk store,
CSR compactor, database, or cross-process graph service. JSON/JSONL files
persist traces and reports, not a reloadable live `SchemaGraph` generation.

## 2. Repository components

| Component | Responsibility |
|---|---|
| `store.py` | term interning, schema canonicalization, schema/link/decomposition columns, evidence, retrieval indices |
| `perception.py` | deterministic grid-to-fact adapter and structural fingerprints |
| `runtime.py` | matching, activation, composition, partial projection, transition learning, prediction, metrics |
| `dsl.py` | transactional cold-path S-expression compiler |
| `benchmark.py` | four-frame vertical slice and dormant-schema stress test |
| `raw_frame.py` | first-packet recording adapter |
| `evaluate_first_frames.py` | corpus evaluation and directed structural-transfer matrix |
| `arc_harness.py` | offline ARC-AGI-3 transport, lifecycle, tracing, and policy boundary |
| `explanations.py` | episode-local explanation beam, prospective commitments, action ranking |
| `explanation_experiment.py` | matched random/local-schema/explanation experiment runner |
| `inspect/` | loopback read-only runtime visualizer with external annotations |
| `arcade/` | loopback human action interface and journal |
| `experiments/` | isolated research mechanisms and evidence; not installed core architecture |

`reflector1-learnings/` is archaeological material. Nothing in it is imported
by `src/reflector2`.

## 3. State model

### 3.1 Terms

`TermStore` hash-conses three term kinds:

```text
SYMBOL       scalar identity (str, int, or float)
VARIABLE     canonical schema-local ordinal
APPLICATION  head symbol plus ordered child term IDs
```

The implementation uses parallel Python lists (`term_kind`, `term_symbol`,
`child_offset`, `child_count`, and `children`) and lookup dictionaries. This is
a structure-of-arrays-shaped prototype, not a NumPy/C array or a GPU buffer.
Booleans are rejected as symbols so they cannot alias integer identities.

Ground facts are compact tuples:

```text
(head_term_id, (argument_term_id, ...))
```

They belong to a `PerceptionBatch`; they are not inserted as persistent graph
nodes.

### 3.2 Schemas

`SchemaGraph` stores one aligned row per schema. The hot/current columns include
compiled body slices, canonical hashes, patterns, depth, lifecycle state,
evidence counters, use counts, context sets, and provenance.

There are two construction forms:

1. `add_schema` stores a canonical positive conjunction. It is used by kernel
   patterns, endogenous flat composition, and learned transition schemas.
2. `add_dag_schema` stores child-schema role occurrences, child-to-owner
   interface maps, parent-level constraints, and an exposed interface. It also
   compiles a flattened pattern for the current matcher.

For ordinary schemas, identity is the SHA-256 digest of the alpha-normalized,
deduplicated conjunction. For explicit DAG schemas, identity additionally
depends on child schema hashes, normalized interface maps, parent constraints,
and the exposed interface. Display names, provenance, evidence, activation,
and construction order do not affect identity.

The alpha-normalizer refines variables by structural role and permutes only
remaining symmetric classes. Schemas are limited to eight variables, sixteen
applications, and arity eight, bounding the residual worst case.

### 3.3 Decompositions and links

A semantic schema may retain multiple decomposition derivations. Each
derivation references child schema IDs and exact child-variable to
owner-variable mappings. Strictly decreasing `depth` is the topological
certificate: self-occurrences and non-decreasing alternatives are rejected.

Decompositions and semantic/activation links are distinct:

```text
decomposition DAG: immutable construction/explanation structure; acyclic
link network:      `part`, `supports`, and other scheduled relations; may cycle
```

Adding a decomposition creates `whole -part-> child` and
`child -supports-> whole` links when absent. The occurrence records remain the
lossless representation; links are only a traversal projection.

### 3.4 Lifecycle and evidence

Schemas are `candidate`, `established`, or `promoted`. Kernel schemas are
established. Endogenous and teacher proposals begin as candidates. A candidate
is promoted after support in at least two distinct contexts or after two
prediction successes.

Evidence is append-only at the event level and reduced into integer columns:

```text
support / contradiction
prediction_success / prediction_failure
projection_support / projection_failure
```

Projection evidence is also keyed to the parent definition pathway (specific
decomposition, roles, and constraints). Evidence never mutates a schema body
or changes its canonical identity.

## 4. Perception boundary

`perceive_grid` accepts a non-empty rectangular integer grid and emits generic
facts. If background is not supplied, the modal value (lowest value on ties) is
used as a convenience inference.

The adapter performs:

- four-neighbor connected components per non-background value;
- enclosed-background detection;
- translation-normalized, hole-filled outer-form hashing;
- cell, location, value, region, and containment facts;
- color-agnostic foreground figures;
- outline hashes invariant to translation, quarter turns, and reflections;
- bounded same-outline and interior-contrast pair relations.

The adapter does not recognize named shapes, game roles, or action meanings.
Region/cell identifiers include the observation context, preventing accidental
identity reuse across carriers. Pair generation is capped at 128.

## 5. One observation cycle

`Runtime.observe(batch)` is a deterministic single-coordinator mutation cycle:

1. Increment the cycle and install form/outline-specific retrieval schemas for
   fingerprints present in the batch.
2. Retrieve candidate schemas through `(head, arity)` and grounded-slot
   postings. Stop at `max_binding_candidates`.
3. Build observation-local fact and grounded-slot indices.
4. Verify each candidate with a bounded positive-conjunctive join. Emit
   `Binding` records and seed matched schema activation.
5. Reconcile unresolved shadows from earlier carriers against the new batch.
6. For locally retrieved explicit DAG schemas, use grounded child bindings to
   open bounded partial bindings and immediate-frontier shadows.
7. Prune the workspace, then propagate activation through outgoing links for a
   bounded number of rounds.
8. Unless disabled, run up to four breadth-first pair-composition rounds over
   active bindings sharing a grounded subject/anchor value.
9. Run one bounded relational-closure pass that combines binary relations with
   one composite descriptor per endpoint.
10. Prune again and publish the resulting `Workspace` on the runtime.

Normal candidate discovery does not iterate over every schema. Expansion reads
only outgoing edges of active frontier nodes. Composition reads only current
bindings. Reporting, explicit evaluation, deep-copy transfer experiments, and
offline audits may scan the graph and are not cognition-loop operations.

### Matching bounds

Pattern atoms are ordered by the smallest available posting estimate. Bound
variables and constants select grounded-slot postings when possible. Every
potentially explosive dimension has a hard limit: facts per atom, partial
bindings, bindings per schema, candidate schemas, body size, proposals,
retentions, active nodes/edges, relational closures, and transition
correspondences. A bound hit adds a traceable truncation event and returns a
deterministic partial result.

### Activation

The current activation policy is intentionally small. A successful binding
adds up to `0.5` activation; composed schemas are seeded at `0.2` or `0.3`;
outgoing link weights add clipped deltas over at most two default rounds.
Stable top-k pruning uses activation and canonical hash. There is no dense
graph-wide activation vector, decay pass, learned activation weight, or GPU
sparse-matrix operation in the implementation.

### Composition

Pair composition converts two bound canonical patterns back to source atoms,
uses shared ground values to unify owner variables, unions/canonicalizes the
body, and hash-conses it. A retained result records both operands as child
occurrences. New bindings are verified against the same observation before
entering the workspace.

Relational closure is similarly bounded. It groups depth-zero binary relation
bindings by two typed entities, combines them with a small number of deeper
endpoint descriptors, and records all inputs in the decomposition.

## 6. Bindings, partial bindings, and shadows

A `Binding` is a transient realization:

```text
(schema_id, sorted assignments, carrier, activation, provenance)
```

It never creates another schema definition. A `PartialBinding` names grounded
and unresolved child roles, satisfied/unresolved/incompatible parent
constraints, supporting children, carrier, activation, and provenance.

A `Shadow` references one partial binding and one immutable schema definition.
It stores only the immediate unresolved frontier; it does not copy a graph or
insert expected facts. Its lifecycle is:

```text
SHADOW --compatible later full match--> REIFIED
SHADOW --explicit positive conflict---> REFUTED
```

Failed matching or absence cannot refute a shadow. Reification inserts an
ordinary binding into the successor workspace and records exact-once parent
pathway evidence. Refutation requires caller-supplied incompatible open
constraint IDs and grounded contradictory facts. Parent-binding and full-match
memo tables prevent repeated work for identical signatures.

Automatic observation projection considers only currently retrieved DAGs. A
single grounded child role may seed a projection; open-role, open-constraint,
activation, bound-fraction, and per-cycle caps constrain it. Prospective action
shadows have a separate smaller budget so sensory projection cannot consume the
entire control boundary.

## 7. Transition learning and prediction

`learn_transition(before, after, action)` is a bounded structural
anti-unification step:

1. Match regions by exact shared form fingerprint, capped by transition and
   analogy limits.
2. For the first correspondence, compare binary attributes anchored at the
   before/after regions.
3. Emit shared variables plus `Preserve(head)` for equal values, or separate
   variables plus `Change(head)` for different values.
4. Emit `Less` only for the audited ordered relations `Count` and
   `EnclosureCount` when the numeric value increases.
5. Add ordinary `Domain`, `Codomain`, and opaque `Intervention` atoms,
   canonicalize the schema, and add support evidence.
6. Link bounded predecessor-bound schemas to the learned transition with
   `supports`, making it reachable from a later active frontier.

If no visual correspondence exists, the runtime still records a minimal
domain/action/codomain transition candidate. This learner is intentionally not
a general entity tracker, assignment solver, causal model, or action semantic
decoder.

The lower-level `predict` API creates an immutable pending ground-atom check
before observation. Resolution adds prediction success or failure; failure
also adds contradiction.

## 8. Explanation-driven control

`ExplanationEngine` is episode-local state over the same graph. It introduces
no schema language and does not persist explanation objects as graph schemas.

For `local-schema` and `explanation` policies, it:

1. reads only active transition schemas whose opaque action token is legal;
2. optionally attaches currently bound predecessor schemas connected through
   active `supports` links;
3. keeps a stable top-k explanation beam;
4. derives effect signatures from existing `Change` and `Preserve` atoms;
5. ranks actions by observed progress history, structural/evidence risk,
   support, and—in explanation mode—within-action disagreement;
6. partially grounds selected predictions and commits them as ordinary shadows
   before the environment step;
7. reifies or positively refutes those commitments from the actual learned
   successor transition.

The default ARC policy remains seeded uniform random. Explanation scores are
disposable episode state. Results in `docs/EXPLANATIONS.md` and `experiments/`
show that the mechanism changes actions and reconciles predictions, but do not
establish general ARC progress.

## 9. ARC-AGI-3 adapter

`arc_harness.py` isolates transport concerns from the runtime:

- toolkit action IDs become opaque `arc-action:N` tokens;
- ordered frame packets are preserved, while only the final support is fed to
  the action-facing runtime cycle;
- complex-action coordinates are sampled from grid bounds after action-ID
  selection;
- `NOT_PLAYED` and `GAME_OVER` force reset, and `WIN` terminates;
- per-game action and environment seeds are derived independently from the
  master seed and game ID;
- each game owns a fresh `Runtime`;
- transport and R2 traces are written separately.

The harness knows game identity for environment loading and provenance only.
The perception/runtime/explanation ranking receives no game-specific branch.

## 10. DSL and teacher boundary

`Compiler.compile` parses the cold-path S-expression language documented in
[`LANGUAGE.md`](LANGUAGE.md). It validates every form before committing any of
them. Supported envelopes are flat schemas, explicit schema DAGs, ground facts,
and native evidence.

Teacher provenance such as `teacher:qwen` receives no authority. It uses the
same canonicalizer and candidate state as endogenous construction. The
compiler rejects teacher-origin evidence injection, unknown metadata, nested
applications, undeclared variables, non-ground facts, non-finite numbers, and
over-budget structures.

There is no live LLM connector in this repository. Inspector label assignments
are loaded only after runtime analysis and remain a one-way presentation layer.

## 11. Interfaces, reports, and persistence artifacts

The benchmark and evaluation CLIs return JSON reports containing schema and
workspace sizes, retrieval/verification counts, composition counts, work-kind
counters, frontier sizes, truncations, phase timings, and memory estimates.

The ARC harness writes:

```text
GAME.trace.jsonl  normalized observations, actions, lifecycle, progress
GAME.r2.jsonl     native runtime events
summary.json      per-game and suite result
```

The inspector HTTP API serves fixtures and accepts a bounded grid for analysis.
It creates a fresh runtime per analysis with a deliberately larger diagnostic
`Limits` profile and inspector-only nominal color-value patterns. The human
arcade is a separate environment controller guarded by a reentrant lock; it
does not call `Runtime` or implement an agent policy.

## 12. Concurrency and determinism

One `Runtime.observe` call is sequential because it mutates one graph. There
are no internal worker queues, locks, async tasks, or GPU streams in the core
runtime. Work-item names such as `TRY_BIND`, `EXPAND`, and `TRY_COMPOSE` are
instrumentation categories, not independently scheduled worker objects.

Parallelism is outside the graph boundary:

- first-frame evaluation uses a process pool over independent games;
- matched explanation experiments use isolated per-game processes;
- transfer-matrix cells deep-copy a completed source graph and run serially in
  the current implementation;
- the loopback HTTP servers may handle requests concurrently, but each
  inspector analysis owns a fresh runtime and the human arcade serializes
  mutable environment access.

Determinism comes from sorted iteration, canonical hashes, stable tie keys,
fixed-order reductions, integer evidence counters, per-game derived RNG seeds,
and coordinator-only mutation. Elapsed time and RSS are observational and are
excluded from structural replay equality.

## 13. Limits and failure behavior

`Limits` is the runtime resource contract. Defaults currently include:

| Area | Default |
|---|---:|
| active schemas / active edges | 256 / 1,024 |
| candidate schemas | 512 |
| facts per atom / partial bindings | 2,048 / 1,024 |
| bindings per schema | 64 |
| pair proposals / new compositions | 256 / 128 |
| composition rounds / body atoms | 4 / 16 |
| relational closures | 64 |
| expansion rounds | 2 |
| transition correspondences / analogy candidates | 128 / 128 |
| normal shadow projections per cycle | 64 |
| action shadow projections per cycle | 8 |

Overflows record a reason and return bounded partial state. Some direct APIs
raise `ValueError` or `RuntimeError` when the caller requests an invalid or
over-budget projection. The normal observation path converts its own bounded
search exhaustion into traceable truncation rather than an unbounded fallback.

## 14. Verification architecture

Tests are organized around boundaries rather than internal implementation
details:

- store/DSL tests cover alpha-equivalence, provenance merging, transactional
  validation, candidate promotion, and resource rejection;
- vertical-slice tests cover simultaneous activation, composition,
  transition reuse, prediction chronology, dormant-store invariance, and DAG
  acyclicity;
- schema-DAG/shadow tests cover multiple bindings, structural sharing,
  immediate-frontier projection, exact-once reification, and positive-evidence
  refutation;
- ARC tests use fake transports to verify packet ordering, opaque actions,
  reset boundaries, deterministic payload sampling, scorecards, and traces;
- explanation tests verify pre-successor commitments, normal shadow
  settlement, bounded active-frontier construction, and process isolation;
- inspector/evaluator tests verify actual runtime projection, HTTP input
  validation, corpus selection, process order, and transfer-cell isolation.

The synthetic dormant-store benchmark is the executable no-scan proof: adding
1k, 10k, or 100k unrelated schemas changes store construction and memory but
not relevant structural results or cognition-loop operation counts.

## 15. Experimental layer

Research code under `experiments/` may import the installed core and add
temporary mechanisms, runners, checkpoints, null controls, or evidence
formats. It is intentionally outside `src/reflector2` so a positive or negative
experiment does not silently become production architecture.

Current experiment families include explanation-driven control, prospective
context specialization, a 25-game context-spinoff diagnostic, and a learned
structural-consequence/progress relevance bridge. Their Markdown and JSON
artifacts are scientific records. Only `explanations.py` and its harness hooks
have been promoted into the core package; other experiment-local mechanisms
must not be described as core runtime capabilities.

## 16. Not implemented

The following are design targets or explicit omissions:

- stable CSR graph generations, delta compaction, memory mapping, and reloadable
  graph snapshots;
- GPU buffers, kernels, CUDA, sparse-matrix execution, or CPU/GPU parity paths;
- concurrent mutation of one schema graph or a distributed graph service;
- unrestricted graph matching, recursion, negation-as-failure, or arbitrary
  executable teacher code;
- learned goals, general planning, rollout/tree search, options, or a solver;
- neural perception, embeddings, LSH, or a live LLM teacher;
- automatic semantic interpretation of actions, colors, objects, rewards, or
  game roles.

These boundaries are architectural constraints, not missing claims to be
papered over. New mechanisms should enter through an experiment, preserve the
one-representation and provenance rules, acquire explicit bounds, and be
promoted into `src/reflector2` only after tests and measured evidence justify
the change.

## 17. Archaeological decisions

Reflector-I contributed lessons, not modules. The current code re-expresses a
small set of mechanisms without importing the old ontology:

- deterministic four-neighbor component/enclosure extraction;
- translation-normalized structural fingerprints;
- bounded predecessor/successor comparison with ambiguity retained;
- append-only traces and coordinator-ordered commits.

The old typed schema AST, `Mind`, scenes, concepts, strategies, planner, and
policy object hierarchy were deliberately not reused because they conflict
with the single generic term/schema representation and the clean restart.
