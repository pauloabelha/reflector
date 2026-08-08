# Reflector-II

Reflector-II is a deterministic research runtime for building and testing
sparse, content-addressed relational schemas. It turns grid observations into
ground facts, retrieves matching schemas through postings indices, keeps a
bounded active workspace, constructs reusable schema compositions, learns
before/action/after transition schemas, and tests prospective completions as
explicit shadows.

The repository includes an offline ARC-AGI-3 adapter and a minimal
explanation-driven action experiment, but it is not a general ARC solver. The
three available ARC control conditions are seeded random, local-schema, and
explanation-driven. The current system has no game-specific policy, planner,
learned goal model, neural model, embeddings, stable on-disk schema store, or
GPU runtime.

## What is implemented

- A hash-consed term store for symbols, variables, and applications.
- One schema graph for atomic patterns, composites, explicit schema DAGs,
  transitions, links, evidence, and provenance.
- Indexed, bounded positive-conjunctive matching with deterministic truncation.
- Sparse activation and bounded multi-round composition over current bindings.
- Explicit bindings, partial bindings, and `SHADOW` / `REIFIED` / `REFUTED`
  projection records.
- Generic grid perception: connected regions, enclosure, cells, form hashes,
  color-agnostic figure outlines, and pair relations.
- Transition learning over opaque actions using `Domain`, `Codomain`,
  `Intervention`, `Before`, `After`, `Preserve`, and `Change` atoms.
- A loopback visual inspector, a human ARC controller, synthetic benchmarks,
  first-frame/transfer evaluation, and an offline ARC-AGI-3 harness.
- Optional `random`, `local-schema`, and `explanation` ARC policies. The latter
  two are experimental control layers over learned transition schemas, not
  claims of task-solving ability.

## Repository map

```text
src/reflector2/       core store, perception, runtime, DSL, evaluation, ARC adapter
tests/                executable contracts and regression tests
docs/                 theory, language, as-built architecture, audits, results
inspect/              loopback visual inspector and external display annotations
arcade/               loopback human ARC controller and note journal
environment_files/    bundled 25 public ARC-AGI-3 environments
experiments/           isolated, preregistered research runners and artifacts
reflector1-learnings/ archaeological source material; never imported by the runtime
```

See [the architecture](docs/ARCHITECTURE.md) for the complete data flow,
component boundaries, state model, concurrency model, and implemented/future
split.

## Requirements and installation

- Python 3.11 or newer
- `arc-agi==0.9.9` (installed from `pyproject.toml`)
- `pytest` only when running the test suite
- Node.js only for the optional inspector JavaScript syntax check

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
```

The editable install exposes these commands:

```text
reflector2-benchmark
reflector2-raw-frame
reflector2-evaluate-first-frames
reflector2-arc
reflector2-explanations
reflector2-arcade
```

## Quick starts

Run the deterministic four-frame vertical slice:

```bash
.venv/bin/reflector2-benchmark --json
```

Verify that unrelated dormant schemas do not change cognition-loop operation
counts or structural output:

```bash
.venv/bin/reflector2-benchmark \
  --stress 1000 10000 100000 \
  --repetitions 5
```

Analyze the final layer of the first packet in one recording:

```bash
.venv/bin/reflector2-raw-frame /path/to/game.recording.jsonl
```

Evaluate exactly one recording per game. Independent games run in separate
processes; `--workers 0` uses the available CPU cores:

```bash
.venv/bin/reflector2-evaluate-first-frames \
  /path/to/recording-directory \
  --expected-games 25 \
  --workers 0
```

Run the directed source-game by target-game structural transfer matrix:

```bash
.venv/bin/reflector2-evaluate-first-frames \
  /path/to/recording-directory \
  --expected-games 25 \
  --transfer-matrix
```

Run the bundled offline ARC-AGI-3 suite. The default policy is seeded random;
use `--policy local-schema` or `--policy explanation` for the experimental
controllers:

```bash
.venv/bin/reflector2-arc \
  --expected-games 25 \
  --seed 0 \
  --max-transitions 80 \
  --policy random
```

Outputs go to `arc-traces/` by default: one transport trace and one native R2
trace per game, plus `summary.json`. See
[the ARC harness guide](docs/ARC_HARNESS.md) and
[the explanation guide](docs/EXPLANATIONS.md).

## Local interfaces

Start the read-only visual inspector:

```bash
.venv/bin/python inspect/server.py --port 8765
```

Open <http://127.0.0.1:8765/inspect/>. The inspector runs the real perception
and runtime code in an isolated graph with a larger diagnostic budget. Its
natural-language labels are external display annotations and never enter
schema identity or evidence. See [inspect/README.md](inspect/README.md).

Start the human-controlled ARC interface:

```bash
.venv/bin/reflector2-arcade --environments-dir environment_files
```

It executes only browser-selected actions and writes notes to
`arcade/notes.json` unless another journal is supplied. See
[arcade/README.md](arcade/README.md).

Both servers bind to `127.0.0.1` by default.

## Documentation guide

- [ACTIVE_EQUILIBRATION.md](docs/ACTIVE_EQUILIBRATION.md): conceptual model and
  longer-term research direction.
- [THEORY.md](docs/THEORY.md): operational vocabulary and epistemic contracts.
- [LANGUAGE.md](docs/LANGUAGE.md): S-expression DSL and schema-DAG syntax.
- [ARCHITECTURE.md](docs/ARCHITECTURE.md): current implementation architecture.
- [INVARIANTS.md](docs/INVARIANTS.md): executable representation and runtime
  constraints.
- [BENCHMARK.md](docs/BENCHMARK.md): four-frame and dormant-store protocols.
- [SHADOWS.md](docs/SHADOWS.md): partial-binding projection semantics.
- [EXPLANATIONS.md](docs/EXPLANATIONS.md): bounded explanation-driven control.
- [GPU_PLAN.md](docs/GPU_PLAN.md): future acceleration plan; no GPU runtime is
  currently implemented.

The documents under `experiments/` are evidence records for isolated research
runners. They are not part of the installed `reflector2` package unless a
mechanism has also been promoted into `src/reflector2`.

## Experiment convention

Each experiment belongs under `experiments/<slug>/` and keeps its proposal,
result, configuration, code, and artifacts within that directory. At minimum,
new experiments should preserve the initiating context, preregistered method,
measured outcome, and an honest verdict. Large generated traces should remain
outside the core package and should not be treated as runtime capabilities.

## Current boundary

The core runtime is in-memory, single-coordinator, and CPU-only. Parallelism is
used around isolated games/evaluations, not inside one mutable schema graph.
The store is represented as Python structure-of-arrays lists plus dictionaries;
the stable CSR generation, compactor, snapshot format, and GPU kernels described
in design documents remain future work.
