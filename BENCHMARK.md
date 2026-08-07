# Synthetic form/enclosure benchmark

The separate raw-corpus protocol and full 25-game results are documented in
[`FIRST_FRAME_EVALUATION.md`](FIRST_FRAME_EVALUATION.md).

The numeric snapshots later in this document predate the current four-round,
256-proposal multi-level closure. They remain useful as a shallow-discovery
baseline; current bounded relational-closure behavior and CPU-parallel corpus
evaluation are documented in [`MULTILEVEL_DISCOVERY.md`](MULTILEVEL_DISCOVERY.md).

This benchmark tests the substrate, not ARC task performance. It is
deterministic, contains no policy or reward, and uses only generic perception,
pattern, composition, and transition machinery.

## 1. Fixtures

All frames have background value `0`. Solid frames use value `1` (displayed as
blue) and enclosed frames use value `5` (displayed as gray). Display labels are
fixture annotations only; the runtime sees integers.

The two base outer occupancies are thick angular forms. Perforated variants
remove one interior cell without changing the hole-filled outer occupancy.
The exact arrays live in the executable fixture module and are snapshotted in
tests.

```text
Frame A: solid blue L       Frame B: perforated gray L
11100                       55500
11100                       50500
11100                       55500
11111                       55555
11111                       55555

Frame C: solid blue Z       Frame D: perforated gray Z
11111                       55555
11111                       55555
00111                       00505
00111                       00555
00111                       00555
```

The adapter extracts same-valued four-connected foreground regions and
frame-connected/enclosed background components. It computes both occupied
signature and hole-filled outer-form signature. It does not branch on these
arrays, colors, names, or form hashes.

The ordered observations are A, B, C, D. The controlled comparisons are
`A --ACTION_1--> B` and `C --ACTION_1--> D`; the B/C boundary is a reset, not a
transition. `ACTION_1` is an opaque intervention token.

## 2. Preloaded generic schemas

Only relation-level patterns are preloaded: cell/value, connected component,
form, color/value, enclosure, inside, and count descriptions. On first seeing a
form fingerprint, generic demand-driven construction may add a form-specific
pattern `Form(?x, fingerprint)`. No schema mentions L, Z, perforation, fixture
coordinates, or the expected transformation.

The benchmark's generic composer receives active bound schemas sharing an
entity. It may construct several conjunctions under budget. The acceptance
assertion identifies the canonical conjunction containing form plus enclosure
evidence by structure, never by display name.

## 3. Required behavioral assertions

1. One frame activates multiple schema bindings in parallel.
2. Primitive relation schemas, a form-specific schema, and constructed
   composites of greater depth coexist in one workspace.
3. A's learned form schema binds B despite value change.
4. Enclosure/inside schemas bind independently of form identity.
5. B causes a canonical form+enclosure composition with decomposition links.
6. C/D use another form fingerprint, yet their comparison retrieves the same
   generalized relation-change transformation as A/B.
7. The transformation has support 2, two distinct form contexts, preserved
   `Form`, increased `EnclosureCount`, and changed `Color`.
8. Lower-level active bindings remain after composite activation.
9. `active_nodes <= max_active_nodes`, all queues/candidate sets obey caps, and
   no required step relies on overflow.
10. Retrieval/verification/edge-visit counters prove that normal cognition did
    not inspect the full schema store.

Additional assertions cover alpha-equivalent schema deduplication, teacher and
endogenous source deduplication, prediction-before-update ordering, exact
counter retention after a falsifier, acyclic occurrence decompositions with
valid variable interfaces, multiple derivations for one semantic body, and
deterministic replay.

## 4. Instrumentation contract

Each run emits one JSON-compatible report containing:

```text
total_schemas, active_schemas, active_edges
candidates_retrieved, candidates_verified
compositions_proposed, compositions_retained
work_items_processed (total and by kind)
frontier_sizes, peak_workspace, truncations
matching_time_s, activation_time_s, composition_time_s
transition_learning_time_s, cognition_time_s, store_construction_time_s,
total_time_s
term_bytes_estimate, graph_bytes_estimate, process_peak_rss_bytes
canonical_active_ids, transformation_hash, transformation statistics
candidate_schemas, established_schemas, promoted_schemas,
reusable_composite_candidates
```

Elapsed time and RSS are observational and excluded from deterministic equality.
All count/identity fields must replay exactly.

## 5. Dormant-schema stress protocol

Run the same four-frame benchmark with `N = 1_000`, `10_000`, and `100_000`
synthetic dormant schemas. Each dormant schema uses a deterministic unrelated
head key, is canonical and persistent, and has provenance `stress`. This is
storage/index pressure, not randomized noise.

For each size record five warmed repetitions and report median/min/max time and
memory. The correctness gate is structural:

- relevant candidates retrieved and verified are identical for all N;
- active IDs/hashes, frontier sizes, work-item counts, compositions, and
  transformation evidence are identical for all N;
- there is no normal-loop schema/link scan counter;
- total schema count and memory do increase, proving dormant data was present.

Time is a diagnostic, not a brittle unit-test threshold. The report flags a
possible scaling regression if median cognition time at 100k exceeds the 1k
median by more than a generous noise-adjusted ratio and absolute delta; such a
flag demands profiling, not an automatic claim of asymptotic failure. Store
construction time is reported separately because it intentionally scales with
N.

The 2026-08-07 five-repeat audit produced:

| dormant | total schemas | median store build | median cognition | retrieved / verified | work items | peak workspace |
|---:|---:|---:|---:|---:|---:|---:|
| 1,000 | 1,059 | 0.013 s | 0.022 s | 117 / 117 | 1,856 | 58 |
| 10,000 | 10,059 | 0.188 s | 0.022 s | 117 / 117 | 1,856 | 58 |
| 100,000 | 100,059 | 2.222 s | 0.027 s | 117 / 117 | 1,856 | 58 |

All sizes had the same structural digest
`164646e43604ed9d2eff6738a3d6ccfd4eef46d8bf70cd062e6c6df3b04cb064`,
1,481 active-edge visits, 256 bounded proposals, 47 retained compositions,
and identical frontier sizes. The roughly linear cold store-build time is
expected; the cognition operation counts are exactly invariant and the median
time changes by about 0.005 s from 1k to 100k.

## 6. Complexity expectations

Grid adaptation is `O(HW)`. Candidate retrieval is expected `O(number of
emitted signature keys + postings visited)`. Bounded verification is described
in `ARCHITECTURE.md`; the fixture remains well below every cap. Activation is
`O(active nodes + active outgoing edges)`. Pair composition is quadratic only
in active bindings per shared entity and capped before materialization.
Transition comparison is linear in emitted facts plus bounded correspondence
candidates. None of these terms contains total dormant schema count.

## 7. Commands and interpretation

The vertical slice provides commands equivalent to:

```bash
python -m reflector2.benchmark --json
python -m reflector2.benchmark --stress 1000 10000 100000 --repetitions 5
pytest -q
```

Passing demonstrates only the enumerated mechanisms and cost-accounting
invariants. It does not demonstrate that the learner autonomously invents L/Z
names, solves an ARC game, plans, learns useful interventions in general, or
benefits from GPU execution.

## 8. Raw-frame compatibility smoke

An optional integration check reads the first frame from a local public ARC
recording and runs only generic perception and one observation cycle:

```bash
python -m reflector2.raw_frame /path/to/game.recording.jsonl
```

No game ID, action, later frame, or old agent reasoning is passed to the
learner. On the locally available first `ar25` recording frame (64×64, six raw
values), the 2026-08-07 audit emitted 1,864 facts over 12 regions and six form
signatures; retrieved/verified 13 candidates; proposed 64 and retained 6
compositions; processed 125 work items; and ended at 19 active schemas and 24
active edges. It extracted two reusable form-plus-region composite candidates
with valid occurrence DAGs and respectively six and two distinct bindings.
Perception took about 0.004 s and the observation cycle about 0.029 s on the
audit host. Forty-four explicit truncation events show bounded
degradation on high-multiplicity cell bindings.
This is compatibility evidence only, not evidence of understanding or play.
The raw-frame acceptance test additionally requires at least one active
endogenous composite with a valid decomposition DAG and at least two distinct
ground bindings. This establishes reusable structural utility within one
frame; it deliberately does not claim predictive or action utility without a
transition.
