# Reflector-II Phase-1 completion audit

## Current multi-level update

The original Phase-1 audit below records the shallow-composition baseline. The
runtime now performs four bounded composition rounds and generic relational
closure. Its `ar25` oracle discovers two depth-2 pair schemas, each with two
level-1 figure-schema occurrences in its DAG. The test suite includes generic
symmetry/contrast, bounded pair-generation, and `ar25` oracle regressions; the
25-game first-frame audit remains 25/25 within workspace limits. See
[`MULTILEVEL_DISCOVERY.md`](MULTILEVEL_DISCOVERY.md).

Audit date: 2026-08-07. This audit evaluates the requested design-first phase
and smallest executable vertical slice. It does not redefine future-phase goals
(GPU kernels, a full ARC harness, policy, or planning) as Phase-1 deliverables.

## Design and representation

| Requirement | Authoritative evidence | Result |
|---|---|---|
| Inspect before implementation; reuse old Reflector only archaeologically | `ARCHITECTURE.md` section 13 records five mechanisms with old meaning, dependency footprint, reuse/adaptation decision, and reason; no new source imports `reflector_old` or `reflector1-learnings` | proved |
| Operational theory and Schema-0 | `THEORY.md` defines every requested term, computational primitives, semantic priors, multiple simultaneous descriptions, and teacher symmetry | proved |
| Exceptionally small language | `LANGUAGE.md` has three term kinds and three cold submission envelopes; richer concepts, actions, mappings, and predictions are data conventions | proved |
| One generic internal representation | `store.py` uses integer-ID term/schema/link SoA tables for descriptors, composites, and morphisms; provenance/evidence are side arrays | proved |
| Persistent graph plus sparse workspace | `SchemaGraph` persists canonical rows; `Workspace` owns only active IDs, activations, bindings, and active edges | proved for the Phase-1 delta store; stable CSR compaction is specified, not implemented |
| No global cognition scan | candidate retrieval uses head/arity and grounded-slot postings; expansion uses only `out_index` slices of frontier nodes; composition uses only active bindings | proved by source inspection and dormant-store operation invariance |
| Tractable, anytime matching | positive conjunctions are bounded by arity/body/variables, candidates, facts per atom, partial/final bindings, correspondence/analogy candidates, expansion rounds, and work queue | proved by limits and cap regression tests |
| Canonical construction and decomposition | structural partition refinement plus bounded residual symmetry search, SHA-256 hash-consing, and separate occurrence-DAG derivations with exact variable interfaces; strict depth descent forbids self/cyclic decomposition while allowing multiple derivations of one semantic body | proved by alpha-equivalence, flattening, explicit DAG traversal, interface, edge-provenance, and composition tests |
| GPU/many-core migration without semantic redesign | `GPU_PLAN.md` maps every hot operation to representation, primitive, batching, synchronization, bottleneck, and custom-CUDA decision; `ARCHITECTURE.md` specifies stable CSR plus append delta | proved as an architecture; no acceleration is claimed |

## Epistemic behavior

| Requirement | Authoritative evidence | Result |
|---|---|---|
| Parallel descriptions and levels | each observation binds all retrieved compatible patterns; primitive, form-specific, and composed schemas coexist in one workspace | proved by `test_parallel_activation_composition_and_analogy` |
| Demand-driven schema construction | composition proposals arise only from active bindings sharing a grounded fact-anchor term, then are ranked, capped, canonicalized, verified, and stored with occurrence DAGs | proved |
| Candidate lifecycle and chunk promotion | constructed and teacher structures begin in explicit candidate state; kernel schemas are established; only support from two distinct contexts or two prediction successes promotes a candidate | proved by teacher-state, distinct-context rejection, and two-transition morphism-promotion tests |
| Evidence, prediction, contradiction | local counters and append-only events preserve support and falsification; predictions must be created before resolution | proved by prediction/falsification and DSL evidence tests |
| Piagetian operations through generic machinery | assimilation, accommodation, chunking, and equilibration are operational interpretations of match, compose/anti-unify, retain, and evidence/resource pressure | proved as specified semantics; no label-specific code paths exist |
| Actions and learned morphisms in the same language | `Intervention(ACTION_1)`, `Domain`, `Codomain`, `Before`, `After`, `Preserve`, `Change`, and `Less` are ordinary applications in one canonical schema | proved by the two-transition benchmark |
| Teacher symmetry | teacher schemas use the same transactional compiler, store, hash, provenance, and evidence mechanisms; teacher-origin evidence injection is rejected | proved by compiler tests |
| Pre-game and in-game teacher stages | packet contents, compilation, provenance, validation, and measurement contracts are specified in `ARCHITECTURE.md`; no external model is required by this slice | proved as architecture only, as requested |

## Executable benchmark and observability

| Requirement | Authoritative evidence | Result |
|---|---|---|
| Frames A/B/C/D | exact solid/enclosed two-form arrays are in `benchmark.py` and `BENCHMARK.md` | proved |
| Ten named behavioral checks | tests cover parallel activation, simultaneous depth, form reuse, independent enclosure, form+enclosure construction, analogous second transition, support across two form contexts, retained lower levels, workspace budgets, and indexed retrieval | proved |
| No named procedural solution | executable-source search finds no `is_L`, `is_Z`, `is_perforated`, or `infer_perforation`; acceptance checks inspect learned structure rather than display names | proved |
| Required instrumentation | reports include schema/activity/edge counts, retrieval/verification, composition, work kinds, frontiers, peak, truncations, all phase times including transition learning, and estimated/resident memory | proved by benchmark JSON |
| 1k/10k/100k dormant stress | five repetitions at each size yield one structural digest (including decomposition DAGs) and identical 117/117 retrieval, 1,481 edge visits, 256 proposals, 47 retentions, 1,856 work items, and peak 58 | proved; current timings are recorded in `BENCHMARK.md` |
| Determinism | independent replays compare canonical active/binding hashes, morphism hash/evidence/contexts, and every non-time operation metric | proved by replay and stress tests |
| One raw ARC first frame | optional adapter reads only the first 64×64 recorded grid, emits 1,864 generic facts, and extracts two decomposable form-plus-region candidates reused across six and two distinct bindings within all budgets | proved by integration test and recorded smoke output; this is structural utility, not predictive utility |
| Visual inspector | `inspect/` loads images and fixtures, invokes real `perceive_grid`/`Runtime.observe`, labels reusable candidates, and projects pixels, regions, active concepts, provenance, evidence, acyclic child-occurrence DAGs and interfaces, timings, and limits | proved by synthetic/raw inspector tests and live HTTP GET/POST smoke |

## Final verification commands

```text
python3 -m pytest -q
  28 passed

node --check inspect/static/app.js
python3 -m compileall -q src tests inspect
  passed

PYTHONPATH=src python3 -m reflector2.benchmark --stress 1000 10000 100000 --repetitions 5
  identical structural digest and operation counts at all sizes

PYTHONPATH=src python3 -m reflector2.raw_frame <local-ar25-recording>
  64x64; 12 regions; 6 forms; 19 active schemas; 24 active edges;
  13/13 retrieved/verified; 64 proposals; 6 retained; 125 work items;
  2 reusable composite candidates with valid DAGs and repeated bindings
```

## Honest boundary

Phase 1 is deterministic and single-process CPU. It is a falsifiable substrate,
not an ARC solver: it has no policy, reward learner, planner, neural model,
embeddings, game-specific semantics, stable-store compactor, GPU runtime, or
custom CUDA. Those omissions are the requested phase boundary. The data layout,
batch semantics, sparse indices, coordinator commits, and operation-specific
migration plan preserve a path to parallel CPU/GPU execution without claiming
performance that has not been implemented and measured.
