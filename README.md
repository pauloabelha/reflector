# Reflector-II

Reflector-II is a clean architectural restart for a minimal executable
epistemology: a sparse, content-addressed relational schema graph; parallel
descriptions in a bounded active workspace; local evidence; demand-driven
composition; and before/action/after morphisms represented in the same
language as ordinary concepts. Its conceptual direction is **active
equilibration**: construct structure, project beyond experience, act,
reify/refute, and reorganize.

This repository is a design-first Phase-1 research substrate, not an ARC
solver. It contains no policy, planner, neural model, embeddings, game-specific
recognizers, or custom GPU code.

## Design contracts

- [`ACTIVE_EQUILIBRATION.md`](ACTIVE_EQUILIBRATION.md): conceptual front door:
  schema DAGs, bindings across space/time/intervention, deductive and
  conjectural shadows, executable explanations, epistemic action, goals,
  solutions, and teacher/LLM adjudication. It clearly marks next-phase ideas.
- [`THEORY.md`](THEORY.md): operational epistemic definitions and Schema-0.
- [`LANGUAGE.md`](LANGUAGE.md): the minimal term/conjunction DSL.
- [`ARCHITECTURE.md`](ARCHITECTURE.md): indexed active-frontier runtime and
  Reflector-1 archaeology ledger.
- [`GPU_PLAN.md`](GPU_PLAN.md): measured CPU/GPU migration decisions by hot
  operation.
- [`INVARIANTS.md`](INVARIANTS.md): executable representation, sparsity,
  epistemic, teacher, and determinism constraints.
- [`BENCHMARK.md`](BENCHMARK.md): the synthetic form/enclosure and dormant-store
  protocols.
- [`FIRST_FRAME_EVALUATION.md`](FIRST_FRAME_EVALUATION.md): the raw first-frame
  results for all 25 public games, including structural and richer-schema tiers.
- [`MULTILEVEL_DISCOVERY.md`](MULTILEVEL_DISCOVERY.md): bounded generic
  relational closure, the `ar25` depth-2 oracle, and CPU-parallel evaluation.
- [`COMPLETION_AUDIT.md`](COMPLETION_AUDIT.md): requirement-by-requirement
  evidence and explicit Phase-1 boundaries.

Start with `ACTIVE_EQUILIBRATION.md` for the unified model, then use
`THEORY.md`, `LANGUAGE.md`, and `ARCHITECTURE.md` for executable contracts.
Benchmark and audit documents report only what the current Phase-1 runtime has
actually demonstrated.

The source material copied from Reflector 1 is under
[`reflector1-learnings/`](reflector1-learnings/). Files retain provenance by
replacing their original `/` with `__`. Nothing in that directory is imported
by the new runtime.

## Run

```bash
python3 -m pytest -q
PYTHONPATH=src python3 -m reflector2.benchmark --json
PYTHONPATH=src python3 -m reflector2.benchmark \
  --stress 1000 10000 100000 --repetitions 5
PYTHONPATH=src python3 -m reflector2.raw_frame /path/to/game.recording.jsonl
PYTHONPATH=src python3 -m reflector2.evaluate_first_frames \
  /path/to/one-recording-per-game --expected-games 25 --workers 0
PYTHONPATH=src python3 -m reflector2.evaluate_first_frames \
  /path/to/one-recording-per-game --expected-games 25 --transfer-matrix
PYTHONPATH=src python3 inspect/server.py --port 8765
```

The last command starts the local visual inspector. Open
<http://127.0.0.1:8765/inspect/> to upload an image or select a bundled synthetic/raw
fixture, then inspect foreground regions, simultaneous active schemas,
reusable candidates, acyclic decomposition DAGs and variable interfaces,
bindings, provenance, evidence, and runtime budgets. See
[`inspect/README.md`](inspect/README.md) for details.

The four-frame benchmark generically constructs an enclosure/inside schema and
a form-plus-enclosure chunk, then canonicalizes two distinct form transitions
to one morphism preserving `Form`, changing `Color`, and increasing
`EnclosureCount`. The stress command proves operation-count and structural
identity independence from 1k, 10k, and 100k unrelated dormant schemas.

`--transfer-matrix` emits a directed source-game × target-game structural
transfer matrix. Every cell starts from an isolated copy of the source's
completed graph and compares the target run with a fresh-target baseline. A
transfer is counted only when a non-kernel source schema receives a verified
target binding. A stricter grounded tier excludes generic variable-only
composites and requires a non-type grounded descriptor such as a form
fingerprint. The output also includes reuse, new-schema, work, and budget
deltas. This is a structural compatibility experiment, not an ARC-solve or
prediction result.

## Parallel execution status

One observation executes through a deterministic CPU coordinator because it
mutates one schema graph. Independent observations (including the 25-game
evaluator) run process-parallel with `--workers 0`, which uses available CPU
cores while preserving deterministic output order. The hot representation is
structure-of-arrays and stable storage is specified as CSR so matching,
frontier propagation, evidence reduction, transition scoring, and top-k
pruning can later move to shared-memory CPU kernels or a GPU without changing
the language. Canonicalization, hash-consing, and graph mutation remain
coordinator responsibilities.
