# Reflector-II

Reflector-II is a clean architectural restart for a minimal executable
epistemology: a sparse, content-addressed relational schema graph; parallel
descriptions in a bounded active workspace; local evidence; demand-driven
composition; and before/action/after morphisms represented in the same
language as ordinary concepts. Its conceptual direction is **active
equilibration**: construct structure, project beyond experience, act,
reify/refute, and reorganize.

This repository is a design-first research substrate, not an ARC solver. It
contains three deliberately small ARC control conditions—seeded random,
local-schema, and explanation-driven—but no game-specific policy, planner,
neural model, embeddings, semantic recognizers, or custom GPU code.

## Design contracts

- [`ACTIVE_EQUILIBRATION.md`](docs/ACTIVE_EQUILIBRATION.md): conceptual front door:
  schema DAGs, bindings across space/time/intervention, deductive and
  conjectural shadows, executable explanations, epistemic action, goals,
  solutions, and teacher/LLM adjudication. It clearly marks next-phase ideas.
- [`THEORY.md`](docs/THEORY.md): operational epistemic definitions and Schema-0.
- [`LANGUAGE.md`](docs/LANGUAGE.md): the minimal term/conjunction DSL.
- [`ARCHITECTURE.md`](docs/ARCHITECTURE.md): indexed active-frontier runtime and
  Reflector-1 archaeology ledger.
- [`GPU_PLAN.md`](docs/GPU_PLAN.md): measured CPU/GPU migration decisions by hot
  operation.
- [`INVARIANTS.md`](docs/INVARIANTS.md): executable representation, sparsity,
  epistemic, teacher, and determinism constraints.
- [`BENCHMARK.md`](docs/BENCHMARK.md): the synthetic form/enclosure and dormant-store
  protocols.
- [`FIRST_FRAME_EVALUATION.md`](docs/FIRST_FRAME_EVALUATION.md): the raw first-frame
  results for all 25 public games, including structural and richer-schema tiers.
- [`MULTILEVEL_DISCOVERY.md`](docs/MULTILEVEL_DISCOVERY.md): bounded generic
  relational closure, the `ar25` depth-2 oracle, and CPU-parallel evaluation.
- [`SHADOWS.md`](docs/SHADOWS.md): Phase-1 partial-binding audit, bounded
  projection policy, reification/refutation criteria, and A-H evidence.
- [`EXPLANATIONS.md`](docs/EXPLANATIONS.md): the implemented bounded explanation
  controller, prospective commitments, outcome reconciliation, and measured
  experimental boundary.
- [`ARC_HARNESS.md`](docs/ARC_HARNESS.md): ARC transport, lifecycle, policy modes,
  reproducibility, and trace/report contracts.
- [`COMPLETION_AUDIT.md`](docs/COMPLETION_AUDIT.md): requirement-by-requirement
  evidence and explicit Phase-1 boundaries.

Start with `docs/ACTIVE_EQUILIBRATION.md` for the unified model, then use
`docs/THEORY.md`, `docs/LANGUAGE.md`, and `docs/ARCHITECTURE.md` for executable contracts.
Benchmark and audit documents report only what the current Phase-1 runtime has
actually demonstrated.

The source material copied from Reflector 1 is under
[`reflector1-learnings/`](reflector1-learnings/). Files retain provenance by
replacing their original `/` with `__`. Nothing in that directory is imported
by the new runtime.

## Experiment convention

Every experiment we run has a name and lives under
`/experiments/SLUGIFIED_NAME/`. The name may be supplied explicitly; when it is
not, we assign a short descriptive name. In either case, the directory name is
the slugified form of that name. Every file and artifact belonging to an
experiment must be stored somewhere under its
`/experiments/SLUGIFIED_NAME/` directory.

Each experiment directory contains:

```text
experiments/SLUGIFIED_NAME/
├── metadata.md
├── proposal.md
└── results.md
```

`metadata.md` records, at minimum, the experiment's timestamp and the prompt
that initiated it. `proposal.md` states what we intend to test and how, while
`results.md` records the outcome, evidence, and conclusions.

## Run

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
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
.venv/bin/reflector2-arc \
  --policy random --expected-games 25 --seed 0 --max-transitions 80
.venv/bin/reflector2-arc \
  --policy explanation --game ar25 --seed 0 --max-transitions 30
.venv/bin/reflector2-explanations \
  --game ar25 --seed 0 --max-transitions 30 --workers 1 \
  --output-dir experiments/minimal-explanation-driven-control/rerun
```

The ARC harness defaults to seeded random control; `--policy local-schema` and
`--policy explanation` activate the two experimental controls. The matched
experiment command runs all three policies from isolated runtimes. See
[`ARC_HARNESS.md`](docs/ARC_HARNESS.md) for the adapter and trace contracts and
[`EXPLANATIONS.md`](docs/EXPLANATIONS.md) for interpretation of the explanation
condition.

The inspector command starts the local visual inspector. Open
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
