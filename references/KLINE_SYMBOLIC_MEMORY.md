# K-line symbolic memory for Reflector

Last updated: 2026-07-30

Status: standalone exact-off retrieval prototype implemented and tested in
`reflector/core/kline_memory.py`. It is not connected to `MindConfig`,
exploration, policy, or the Kaggle overlay, so accepted v67 and its score are
unchanged.

## Decision

The proposed memory is a direct engineering interpretation of Marvin Minsky's
1980 [K-Lines: A Theory of Memory](https://courses.csail.mit.edu/6.803/pdf/aim-516.pdf).
A K-line records a useful subset of the agencies active during a successful
idea or problem-solving episode. A later partial cue reactivates a partial
version of that useful state.

That is the right shape for Reflector's proposal problem. The agent should not
search every representation and operator family uniformly. A partial symbolic
state should rapidly recall the few perceptual languages, causal models,
experiments, and planners that were useful in structurally related states.

The implementation must preserve a strict distinction:

- a cryptographic content hash answers **which immutable prior is this?**;
- a sparse partial-match index answers **which priors might be relevant?**;
- exact current-state grounding answers **may this prior influence search?**;
- prospective evidence answers **may the grounded operator influence a plan?**

Similarity alone never authorizes an action.

## Minsky's level-band principle

Minsky argues that a memory should reactivate an intermediate band of
agencies. Reinstating low-level detail would conceal the present perception;
reinstating the highest-level solved state would make the system behave as if
the new problem were already solved.

For Reflector, a K-line may reactivate:

- an object or relation vocabulary worth testing;
- an operator-family generator;
- a causal hypothesis template;
- an informative experiment;
- a bounded search strategy and resource cap;
- other K-lines that composed the earlier successful inference.

It must not reactivate:

- raw frames or literal palette values;
- game IDs, environment versions, fixed coordinates, or action IDs;
- an old action sequence;
- an old goal binding or claim that the present level is solved;
- executable code or an unregistered operator.

This makes K-line recall a heuristic over what to generate and test, not a
case lookup that bypasses induction.

## Relation to existing Reflector machinery

Reflector already has half of this architecture:

- `SchemeDefinition` gives immutable, content-addressed symbolic definitions;
- `SchemeLibrary` gives deterministic Merkle snapshots;
- evidence ledgers keep confidence separate from definition identity;
- advisor arbitration can expose which symbolic components were active;
- prospective prediction and structural credit distinguish useful mechanisms
  from merely present ones.

The missing half is associative partial retrieval. The current inherited
library is scanned or statically grounded. A large library needs a sparse
index that can retrieve relevant definitions from incomplete evidence without
loading or testing every prior.

## Immutable data model

A K-line definition should contain only canonical symbolic structures:

```text
KLineDefinition
  schema_version
  cue_patterns
  activation_band
  hard_preconditions
  activated_generator_ids
  expected_contracts
  falsifiers
  dependency_kline_ids
  resource_cap
  complexity_cost

kline_id = SHA256(canonical_json(definition))
```

The phase-one prototype deliberately implements the safe retrieval subset of
that contract: immutable prior label, canonical cue atoms, registered
generator IDs, hard preconditions, contradictions, and minimum match
thresholds. Generator IDs are returned as inert symbolic dispositions, never
called by the memory module. Activation bands, expected contracts, recursive
dependencies, evidence utility, and per-generator resource budgets must be
added before runtime integration.

Evidence is separately content-addressed:

```text
KLineEvidence
  kline_id
  candidate_id
  partition
  source_trace_digest
  prediction_digest
  outcome
  search_expansions_saved
  interventions_saved
```

Changing evidence must never silently change what a K-line ID denotes.
Activations are references to registered generic generators or schemes, not
serialized Python or actions.

## Cue atoms and invariance

The current state is compiled into typed, canonical cue atoms at several
bands:

- `surface`: scale buckets, repetition, symmetry, density, palette cardinality;
- `object`: normalized component shape and enclosure roles;
- `relation`: containment, contact, adjacency, alignment, order, shared nodes;
- `dynamics`: relative changed masks, cycles, permutations, conservation;
- `goal`: earned marker relations, visible constraints, progress predicates;
- `control`: legal action-role schemas, uncertainty, failed predictions.

Cues must be invariant under every transformation that does not change their
meaning: translation, object enumeration, arbitrary palette bijection, and
literal action-ID permutation. D4 normalization is used only for cue families
whose operator semantics are conjugated consistently; it must not erase a
meaningful handedness or direction.

Each atom retains its canonical text for collision verification and receives a
stable SHA-256 identifier for indexing.

## Two-stage retrieval

The initial implementation is exact and sparse rather than embedding based:

1. Canonicalize at most 64 current-state cue atoms and reject an over-limit
   query.
2. Read exact, collision-checked inverted postings in increasing-frequency
   order, round-robin across postings, with at most 8,192 posting visits. This
   prevents one long, hash-sorted posting from starving the other cue bands.
3. Apply hard preconditions and contradictions before scarce candidate or
   exact-stage quotas.
4. Retain at most 64 coarse candidates using bounded inverse-frequency,
   prior-containment, namespace-coverage, and query-coverage scores.
5. Run a caller-supplied structural matcher over at most 16 candidates and
   2,048 total expansions. A grounded result requires an explicit proof
   digest; an over-budget result is rejected.
6. Return at most four inert generator dispositions with matched cues,
   provenance, score components, index identity, and deterministic diagnostic
   accounting.

An inverted index is the best first implementation because it is deterministic,
auditable, offline, and has no approximate false negatives for indexed atoms.
At much larger scale, deterministic MinHash or SimHash tables can be added as
coarse candidate generators, but every returned candidate still needs
canonical-token verification and exact relational reranking.

Ordinary Jaccard similarity is not enough: a small partial query can be fully
contained in a useful large memory yet receive a low symmetric score. The
coarse rank therefore needs both query coverage and prior specificity, with
rarer cross-band matches carrying more evidence than repeated superficial
cues.

## Activation grades

Retrieval has three explicit grades:

1. **Recalled** — partial cue overlap; may reorder diagnostic probes only.
2. **Grounded** — bounded structural unification and hard preconditions pass;
   may prioritize registered hypothesis/operator generation.
3. **Confirmed** — present-game transitions support the grounded prediction;
   may participate in ordinary planning under its resource cap.

A frame-only resemblance can never jump directly to confirmed. Current legal
action roles must be learned and rebound. A contradiction, hard-precondition
failure, or active falsifier causes abstention or quarantine.

The scheduler should reserve a fixed fraction of search for the baseline
frontier, for example alternating one retrieved generator with one generic
generator until current-game confirmation. A bad memory must not monopolize
the agent's proposal budget.

## What should become memorable

Create a K-line only after meaningful progress, a win, a prospectively
confirmed prediction, or a clean falsification that teaches a missing
precondition. Record the invariant cue immediately before the decisive
inference and only the symbolic components that received predictive or
pragmatic credit.

Retention utility should measure:

```text
verified future search or interventions saved
- serialized complexity
- retrieval cost
- false-activation cost
```

Cases with the same activation bundle can merge when one cue subsumes another.
A contradiction should create a justified specialization or negative
falsifier, not a literal board blacklist. K-lines may depend on older K-lines,
matching Minsky's recursion principle and reducing repeated definitions.

## Deterministic storage

For a large frozen library:

- canonical JSON remains the authoritative definition format;
- the snapshot root hashes the sorted immutable definitions;
- a separate index root binds the snapshot root, index schema, all retrieval
  bounds, and the complete registered-generator vocabulary;
- shortened numeric feature IDs are index accelerators only;
- sorted postings map feature IDs to sorted K-line IDs;
- the canonical cue text is rechecked after every shortened-hash hit;
- a deterministic memory-mapped binary artifact may accelerate Kaggle loading;
- pickle, randomized Python hashes, wall-clock cutoffs, mutation during hidden
  evaluation, and network retrieval are forbidden.

All query caps are operation counts, not timing thresholds, so exact replay is
portable.

## Integration sequence

1. Build and test `reflector/core/kline_memory.py` as a standalone exact
   content-addressed index. **Complete:** definitions, external evidence
   identities, collision-checked snapshots, sparse postings, deterministic
   fair bounded ranking, explicit frozen generator vocabulary, independent
   index identity, proof-budgeted structural checks, and recall/grounding
   separation have focused tests.
2. Add a frozen K-line snapshot and root to `MindConfig`, exact-off by default.
3. Compile cue atoms from already-grounded symbolic state; do not add a second
   raw-pixel perception path.
4. Let retrieval reorder registered hypothesis and operator generators in
   `EpistemicExplorer`; do not add a direct-action K-line advisor.
5. Record query digest, matched bands, retrieved IDs, unification bindings,
   activation grade, caps, and abstention/falsifier reason in traces.
6. Package the frozen index in the Kaggle inference overlay and bind its digest
   into the candidate fingerprint.
7. Populate the library only from training/development evidence; hidden
   evaluation may use but never mutate it.

## Tests and promotion gate

Required tests:

- byte-identical roots, indexes, and query results on repeated builds;
- exact behavior preservation when disabled;
- translation, recoloring, object-order, D4, and action-role equivariance;
- partial-subset retrieval above larger common-feature distractors;
- cross-band evidence outranking many cues from one superficial band;
- dynamically incompatible lookalikes abstaining at exact verification;
- hash-collision canonical-token verification;
- caps holding under adversarial huge and ubiquitous postings;
- similarity never producing an action;
- one contradiction quarantining executable activation;
- evaluation episodes unable to mutate the frozen ancestral snapshot;
- leave-one-family-out transfer rather than source-task lookup.

Promotion requires zero ungrounded action overrides and no public regression.
The retrieval layer must either add held-out progress or materially reduce
actions/search while preserving outcome. A useful synthetic prerequisite is
at least 95% relevant-prior recall@16 on held-out equivariant cases, with zero
false **confirmed** activations.

## Related primary work

- [Minsky, K-Lines: A Theory of Memory](https://courses.csail.mit.edu/6.803/pdf/aim-516.pdf)
- [Forbus, Gentner, and Law, MAC/FAC](https://doi.org/10.1207/s15516709cog1902_1)
- [Forgy, the Rete matching algorithm](https://doi.org/10.1016/0004-3702(82)90020-0)
- [Broder, resemblance and containment / MinHash](https://www.cs.princeton.edu/courses/archive/spring13/cos598C/broder97resemblance.pdf)
- [Indyk and Motwani, locality-sensitive hashing](https://doi.org/10.1145/276698.276876)
- [Stanford IR book, inverted-index query processing](https://nlp.stanford.edu/IR-book/html/htmledition/processing-boolean-queries-1.html)
- [Aamodt and Plaza, case-based reasoning](https://doi.org/10.3233/AIC-1994-7104)
- [DreamCoder paper and library learning](https://www.neurosymbolic.org/papers/EllisWNSMHCST21.pdf)

The intended synthesis is K-line memory plus a MAC/FAC-style retrieval
discipline: many partial symbolic memories are called cheaply; a few are
chosen by exact structure and current evidence.
